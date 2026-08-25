"""Model/provider/key configuration: which model is active, which .env variable its key goes in, and
reading/writing .env. Split out of llm.py (the "call the model" module) by concern - llm.py re-exports
these so every existing `llm.xxx(...)` caller keeps working unchanged."""
import os

import paths

# Best-known API-key env var per litellm provider name, for the providers we call out by name in the
# UI/README. Unlisted providers fall back to a "<PROVIDER>_API_KEY" guess (litellm's own convention
# for most of them) - see https://docs.litellm.ai/docs/providers for the authoritative list.
KEY_ENV_BY_PROVIDER = {
    "gemini": "GEMINI_API_KEY", "openai": "OPENAI_API_KEY", "anthropic": "ANTHROPIC_API_KEY",
    "mistral": "MISTRAL_API_KEY", "cohere": "COHERE_API_KEY", "groq": "GROQ_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY", "xai": "XAI_API_KEY",
}

# The curated provider list, names, key-signup URLs, and free/trial/paid notes now live in
# llm_providers.py (its own concern - hand-checked facts, not litellm mechanics).


def load_env():
    if os.path.exists(paths.ENV):
        for line in open(paths.ENV):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def get_litellm():
    import litellm
    litellm.suppress_debug_info = True  # keep our own progress/report output clean, not litellm's
    return litellm


def model():
    from services.llm import PROMPTS  # deferred - llm.py imports this module too; avoids a cycle
    return os.environ.get("LLM_MODEL", PROMPTS["model_default"])


def provider_of(a_model):
    """The litellm provider name for a model string (e.g. 'gemini/gemini-...' -> 'gemini'), or ''
    if litellm can't classify it."""
    try:
        _, provider, _, _ = get_litellm().get_llm_provider(a_model)
        return provider or ""
    except Exception:  # noqa: BLE001
        return ""


_NON_CHAT_HINTS = ("dall-e", "whisper", "tts", "embed", "moderation", "rerank", "image", "audio",
                    "x-1024", "1024-x", "x-1536", "1536-x")


def canonical_model(provider, a_model):
    """'provider/model', without doubling a prefix the name already carries - litellm needs the
    prefix for most providers (a bare 'gemini-...' silently routes to vertex_ai instead of gemini),
    but some of litellm's own model lists already include it (groq, mistral, ...)."""
    a_model = a_model.strip()
    prefix = f"{provider}/"
    return a_model if a_model.startswith(prefix) else prefix + a_model


def models_for_provider(provider):
    """Chat-model strings litellm knows for one provider, canonicalised to 'provider/model' and
    filtered to drop obviously non-chat modalities (image/audio/tts/embedding/...) - best-effort,
    since litellm's own list mixes every modality with no per-entry marker. The model field stays
    freely editable in the UI too, for anything this misses or a brand-new release."""
    raw = get_litellm().models_by_provider.get(provider, set())
    names = {canonical_model(provider, m) for m in raw if not any(h in m.lower() for h in _NON_CHAT_HINTS)}
    return sorted(names)


def model_options(provider):
    """{model: label} for the model picker. Free-ness is usually a whole-provider trait (shown once
    via llm_providers.key_info()), except OpenRouter, where individual models carry their own
    ':free' suffix - those get marked here so they stand out in a mixed free/paid model list."""
    return {m: (f"\U0001F193 {m}" if provider == "openrouter" and m.endswith(":free") else m)
            for m in models_for_provider(provider)}


def resolves_to(provider, a_model):
    """Whether litellm actually routes a_model to the given provider - a free, no-network sanity
    check ("does this exist / point where you think"), distinct from check_key()'s real API call."""
    return bool(a_model) and provider_of(a_model) == provider


def key_env_for(a_model):
    """The .env variable name the given model's provider expects its API key under."""
    provider = provider_of(a_model)
    return KEY_ENV_BY_PROVIDER.get(provider, f"{provider.upper()}_API_KEY" if provider else "GEMINI_API_KEY")


def _write_env_var(name, value):
    lines = [ln for ln in (open(paths.ENV).read().splitlines() if os.path.exists(paths.ENV) else [])
             if not ln.strip().startswith(f"{name}=")]
    lines.append(f"{name}={value}")
    with open(paths.ENV, "w") as f:
        f.write("\n".join(lines) + "\n")


def save_model(a_model):
    """Store LLM_MODEL in ~/Hermes/.env (replacing any existing line) and in the environment."""
    a_model = a_model.strip()
    os.environ["LLM_MODEL"] = a_model
    _write_env_var("LLM_MODEL", a_model)


def save_key(key, env_name="GEMINI_API_KEY"):
    """Store an API key in ~/Hermes/.env under env_name (default: the built-in default model's
    provider) and in the environment. Pass the right env_name for whichever model/provider is
    currently selected - see key_env_for()."""
    key = key.strip()
    os.environ[env_name] = key
    _write_env_var(env_name, key)


def has_key():
    """Whether an API key is configured for the CURRENT model's provider (not just Gemini's)."""
    return bool(os.environ.get(key_env_for(model())))


def check_key():
    """Validate the current key against the configured model with a minimal call. Raises on failure."""
    get_litellm().completion(model=model(), messages=[{"role": "user", "content": "hi"}], max_tokens=1)


def list_models():
    from services.llm import PROMPTS
    print(f"Current model: {model()}")
    print("Hermes is model-agnostic (via LiteLLM). Change it by setting LLM_MODEL in ~/Hermes/.env to")
    print("any provider's model string (with that provider's own API key also in .env), e.g.:")
    print(f"  LLM_MODEL={PROMPTS['model_default']}   (needs GEMINI_API_KEY - today's default)")
    print("Full list of supported providers/model strings: https://docs.litellm.ai/docs/providers")
