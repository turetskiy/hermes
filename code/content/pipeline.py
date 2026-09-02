"""Block-by-block tuning pipeline. The block list is data (prompts.json 'pipeline' + one bullets
block per present role), so it iterates uniformly (DRY) and a new fixed block is a config entry, not
code (OCP)."""
import json

from services import cancel
from services.llm import PROMPTS, call_block


def _dget(d, path):
    for k in path.split("."):
        d = d[k]
    return d


def _dset(d, path, val):
    keys = path.split(".")
    for k in keys[:-1]:
        d = d[k]
    d[keys[-1]] = val


def _blocks(content):
    steps = list(PROMPTS["pipeline"])  # fixed text blocks (headline, summary)
    if content.get("skills"):  # one Skills step over the whole flat clusters list (any length)
        steps.append({"prompt": "skills", "name": "Skills", "path": "skills", "key": "clusters", "kind": "json"})
    for rk in ("role1", "role2", "role3", "role4"):
        role = content["roles"].get(rk)
        if role:
            steps.append({"prompt": "bullets", "name": f"Bullets / {rk} ({role['title']})",
                          "path": f"roles.{rk}.bullets", "key": "bullets", "kind": "json"})
    return steps


def _fields(spec, content, base, facts):
    cur = _dget(content, spec["path"])
    f = dict(base, content=cur if spec["kind"] == "text" else json.dumps(cur, ensure_ascii=False))
    if spec.get("facts"):
        f["facts"] = facts
    if spec["prompt"] == "bullets":
        f["max_bullets"] = len(cur)
    return f, cur


def run_auto(content, jd, depth, extra, facts, mock):
    """Non-interactive: accepts each block's proposed value automatically, no per-block review - the
    web UI reviews the WHOLE tailored result afterward instead (like the Profile screen)."""
    base = dict(jd=jd, depth=depth, extra=extra)
    for spec in _blocks(content):
        cancel.check()  # between blocks - shortens a Stop click to one block's wait, not all of them
        fields, cur = _fields(spec, content, base, facts)
        res = call_block(spec["prompt"], fields, mock, {spec["key"]: cur, "gaps": []})
        _dset(content, spec["path"], res.get(spec["key"], cur))
    return content
