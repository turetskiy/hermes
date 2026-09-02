"""profile.py - turn the factbook (data/factbook.md) into the data the tailor pipeline needs, in two
steps: propose() tags each factbook fact with a role/skills/etc. assignment (Step 1, "Selection"),
then build_role()/build_skills() polish one entity's currently-assigned facts into final resume
content (Step 2, "Build") - independently, so rebuilding role3 never touches role1/skills/identity.
Used by web/profile_select.py (propose), web/profile_roles.py (build_role), web/profile_skills.py
(build_skills), web/profile_identity.py and web/profile.py (the write_*/delete_track re-exports)."""
import json
import warnings

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", message=r".*OpenSSL.*")

from profile_write import (  # noqa: F401  re-exported for web/profile*.py
    ROLE_SLOTS, delete_track, write_identity, write_role, write_skills, write_speaking_articles,
)
from services import llm, report
from services.llm import PROMPTS


def _generate_json(prompt_key, task, label):
    """Shared retry-on-malformed-JSON pattern for the profile-building calls below - direct
    llm.generate()/_extract_json(), NOT llm.call_block() (its system prompt is hardcoded to
    JD-tailoring guardrails that don't apply to any of these no-JD calls)."""
    for attempt in (1, 2):
        try:
            raw = llm.generate(PROMPTS[prompt_key]["system"], task, label=f"{label} attempt {attempt}")
            return llm._extract_json(raw)
        except ValueError as e:
            if attempt == 2:
                raise
            report.warn(f"  Model returned malformed JSON ({e}); retrying...")


def propose(factbook):
    """Step 1 ('Selection'): tag every atomic factbook fact with a proposed role/skills/speaking/
    articles/exclude assignment, plus identity + role title/dates + headline/summary/footer_title.
    Pure - the caller persists the result via content/profile_drafts.py, not this module."""
    task = PROMPTS["profile_select"]["task"].replace("{factbook}", factbook)
    return _generate_json("profile_select", task, "profile_select")


def _facts_for(draft, assign):
    facts = [f for f in draft.get("facts", []) if f.get("assign") == assign]
    return sorted(facts, key=lambda f: f.get("rank", 999))


def build_role(draft, role_slot):
    """Step 2: polish this role's currently-assigned draft facts (current rank order) into resume
    bullets 1:1 - same count/order, only reworded. Returns [{id, text}]; the caller (profile_write.
    write_role) merges these back into blocks.json by id."""
    facts = _facts_for(draft, role_slot)
    if not facts:
        return []
    role = draft.get("roles", {}).get(role_slot, {})
    task = (PROMPTS["profile_role_build"]["task"]
            .replace("{role_title}", role.get("title") or role_slot)
            .replace("{role_dates}", role.get("dates", ""))
            .replace("{facts}", json.dumps([f["text"] for f in facts], ensure_ascii=False))
            .replace("{n}", str(len(facts))))
    res = _generate_json("profile_role_build", task, f"profile_role_build {role_slot}")
    bullets = res.get("bullets", [])
    return [{"id": f["id"], "text": bullets[i] if i < len(bullets) else f["text"]}
            for i, f in enumerate(facts)]


def build_skills(draft):
    """Step 2: cluster this draft's 'skills'-assigned facts into 3-6 labeled {label, items} groups."""
    facts = _facts_for(draft, "skills")
    if not facts:
        return []
    task = PROMPTS["profile_skills_build"]["task"].replace(
        "{facts}", json.dumps([f["text"] for f in facts], ensure_ascii=False))
    res = _generate_json("profile_skills_build", task, "profile_skills_build")
    return res.get("skills", [])


def build_and_save_all(draft, track_id, label):
    """Convenience for a first full build: runs build_role for every role, plus build_skills and the
    deterministic speaking/articles pass-through, then persists everything via profile_write's
    granular writers. Returns the total block count written."""
    identity = draft.get("identity", {})
    write_identity(identity, track_id, label, draft.get("headline", ""), draft.get("summary", ""),
                    draft.get("footer_title", ""))
    total = 0
    for role_slot in ROLE_SLOTS:
        role = draft.get("roles", {}).get(role_slot, {})
        total += write_role(track_id, role_slot, role.get("title", ""), role.get("dates", ""),
                             build_role(draft, role_slot))
    write_skills(track_id, build_skills(draft))
    write_speaking_articles(track_id, _facts_for(draft, "speaking"), _facts_for(draft, "articles"))
    return total
