"""Model-agnostic LLM access via LiteLLM: one call works with Gemini, OpenAI, Anthropic, and 100+
other providers - switching is a one-line change (LLM_MODEL in .env), no code changes. SRP: model/
provider/key config lives in llm_config.py (re-exported here); this module owns the call itself, its
retry, and the prompt/JSON plumbing for call_block. litellm is the only external seam."""
import json
import os
import random
import re
import threading
import time

from services import cancel, report, runlog
from services.llm_config import (  # noqa: F401  re-exported - every existing llm.xxx(...) call site
    KEY_ENV_BY_PROVIDER, canonical_model, check_key, get_litellm, has_key, key_env_for, list_models,
    load_env, model, model_options, models_for_provider, provider_of, resolves_to, save_key, save_model,
)
from services.llm_providers import (  # noqa: F401  re-exported - curated provider names/urls/notes
    key_info, provider_names, provider_options,
)

HERE = os.path.dirname(os.path.abspath(__file__))
PROMPTS = json.load(open(os.path.join(HERE, "prompts.json")))

TRANSIENT = ("overloaded", "unavailable", "503", "resource_exhausted", "429",
             "try again", "deadline", "timeout", "temporarily", "rate limit")

# A single request that's simply too big for the model's per-minute token budget (e.g. Groq's "Request
# too large ... reduce your message size and try again") also matches "try again"/"rate limit" above,
# but waiting and resending the SAME request can never succeed - checked first so it always wins.
NOT_TRANSIENT = ("too large", "reduce your message", "reduce your prompt")


def _transient(e):
    msg = str(e).lower()
    if any(m in msg for m in NOT_TRANSIENT):
        return False
    return any(m in msg for m in TRANSIENT)


def _short(e, limit=200):
    """One-line excerpt of an exception's message, for the activity log - the full text always goes
    to runlog regardless. "Model busy" alone told you nothing; this shows what the model actually
    said, so a real logic/prompt error doesn't hide behind a generic busy-retrying message."""
    text = " ".join(str(e).split())
    return text if len(text) <= limit else text[:limit] + "..."


MIN_CALL_INTERVAL = 4.5  # seconds - a tailoring run fires ~10-30 calls back to back with zero pacing
# otherwise; free/trial tiers (Gemini's free RPM is quite low) get bounced almost immediately once
# that burst exceeds their per-minute quota - and providers report this as the SAME generic "high
# demand"/503 a real outage would give, so it's easy to mistake sustained rate-limiting for one. This
# keeps free/trial usage comfortably under a ~13 req/min ceiling; paid tiers skip it entirely.
_pace_lock = threading.Lock()
_last_call_at = [0.0]


def _pace():
    tier = key_info(provider_of(model()))["tier"]
    if tier not in ("free", "trial"):
        return
    with _pace_lock:
        wait = MIN_CALL_INTERVAL - (time.monotonic() - _last_call_at[0])
        if wait > 0:
            time.sleep(wait)
        _last_call_at[0] = time.monotonic()


def generate(system, user, attempts=6, label=None, max_tokens=8192):
    """Call the model, retrying transient failures (overloaded / 503 / 429 / timeout) with exponential
    backoff (2s, 4s, 8s, 16s, 30s). Non-transient errors (bad key, unknown model, 400) raise immediately.
    Every call's request/response goes to runlog (data/output/tailor.log) - the one place to check what
    a given provider/model actually returned, e.g. after a malformed-JSON error. label tags which
    caller/prompt this was (e.g. a call_block prompt_key) so the log stays readable with many calls.
    max_tokens defaults well above most providers' own implicit default - a "thinking" model (Groq's
    Qwen included) can burn thousands of tokens on its visible <think> reasoning before ever reaching
    the actual answer, and a too-small ceiling truncates it mid-thought, producing no JSON at all."""
    cancel.check()  # a Stop click between blocks/attempts lands here before a new call even starts
    litellm = get_litellm()
    messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    tag = f" [{label}]" if label else ""
    runlog.write(f"\n=== LLM call{tag} (model={model()}) ===\nSYSTEM:\n{system}\nUSER:\n{user}")
    for attempt in range(1, attempts + 1):
        _pace()
        try:
            response = litellm.completion(model=model(), messages=messages, max_tokens=max_tokens)
            content = response.choices[0].message.content
            runlog.write(f"RESPONSE:\n{content}")
            return content
        except Exception as e:
            if attempt == attempts or not _transient(e):
                runlog.write(f"ERROR: {e}")
                raise
            cancel.check()  # don't sleep out a whole backoff window if a stop was requested meanwhile
            wait = min(2 ** attempt, 30) + random.uniform(0, 1)
            runlog.write(f"transient LLM error ({e}); retry {attempt}/{attempts - 1} in {wait:.1f}s")
            report.warn(f"  Model busy ({_short(e)}) - retrying in {wait:.0f}s ({attempt}/{attempts - 1})...")
            time.sleep(wait)


def _build_prompt(prompt_key, fields):
    text = PROMPTS["block_prompts"][prompt_key]
    for k, v in fields.items():  # manual sub: str.format would choke on the {"..."} JSON examples
        text = text.replace("{" + k + "}", str(v))
    return text


_THINK_BLOCK = re.compile(r"<think>.*?</think>", re.S | re.I)


def _extract_json(text):
    """Strip a "thinking" model's visible <think>...</think> reasoning block before hunting for JSON -
    otherwise a stray brace inside the reasoning (which often quotes the target schema) can get grabbed
    instead of the real answer. An OPENED but never-closed block means generate()'s max_tokens ran out
    before the model ever reached its answer - a distinct, more useful error than a generic JSON one."""
    text = text.strip()
    if re.search(r"<think>", text, re.I) and not re.search(r"</think>", text, re.I):
        raise ValueError("model response was truncated mid-reasoning (ran out of output budget before "
                          "reaching its answer) - retrying, or a larger max_tokens/non-'thinking' model "
                          "would help")
    text = _THINK_BLOCK.sub("", text, count=1).strip()
    text = re.sub(r"^```(json)?|```$", "", text, flags=re.M).strip()
    a, b = text.find("{"), text.rfind("}")
    if a == -1 or b == -1:
        raise ValueError(f"no JSON in model output:\n{text[:300]}")
    return json.loads(text[a:b + 1])


def call_block(prompt_key, fields, mock, fallback):
    """Tailor one block: build prompt -> call -> parse. On mock/error, return fallback. A tailoring run
    can call this ~30 times (one per resume block), so generate()'s own retry budget is capped at 3
    (2 retries, ~6s) here instead of the default 5 - during a sustained provider slowdown, every block
    inheriting the full ladder compounds into many independent multi-minute waits back to back."""
    if mock:
        return fallback
    user = _build_prompt(prompt_key, fields)
    for attempt in (1, 2):
        try:
            raw = generate(PROMPTS["guardrails"], user, label=f"{prompt_key} attempt {attempt}", attempts=3)
            return _extract_json(raw)
        except Exception as e:  # noqa: BLE001
            runlog.write(f"[{prompt_key}] attempt {attempt} JSON error: {e}")
            if attempt == 2:
                print(f"  ! LLM/JSON error ({e}); keeping current block.")
                if any(s in str(e) for s in ("NOT_FOUND", "not found", "404")):
                    print("    (bad LLM_MODEL? run: ./.venv/bin/python3 code/tailor.py --list-models)")
                return fallback
