"""Block-by-block tuning pipeline + feedback loop. The block list is data (prompts.json
'pipeline' + one bullets block per present role), so it iterates uniformly (DRY) and a new
fixed block is a config entry, not code (OCP)."""
import json

from rendering import fill_template
from services import cancel, runlog, ui
from services.llm import PROMPTS, call_block
from services.ui import ask


def _short(v):
    if isinstance(v, list):
        return "\n  ".join(json.dumps(x, ensure_ascii=False) if isinstance(x, dict) else str(x)
                           for x in v)
    return str(v)


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


def _edit_value(spec, value):
    """Let the user edit the proposed value in place (cursor), per block kind."""
    if spec["kind"] == "text":
        return ui.edit(spec["name"], value)
    if spec["key"] == "bullets":
        return [ui.edit(f"bullet {i + 1}", b) for i, b in enumerate(value)]
    if spec["key"] == "clusters":
        return [{"label": c["label"], "items": ui.edit(c["label"], c["items"])} for c in value]
    return value


def _decide(spec, current, proposed, gaps):
    print(f"\n--- {spec['name']} ---\ncurrent:\n  {_short(current)}\nproposed:\n  {_short(proposed)}")
    if gaps:
        print("gaps (JD wants, not in your material): " + "; ".join(gaps))
    runlog.write(f"\n--- BLOCK: {spec['name']} ---\ncurrent:\n  {_short(current)}"
                 f"\nproposed:\n  {_short(proposed)}" + (f"\ngaps: {gaps}" if gaps else ""))
    while True:
        cmd = ask("[Enter]=edit & accept  s=skip(keep current)  r=re-tune (type r)").lower()
        if cmd == "":
            edited = _edit_value(spec, proposed)
            runlog.write(f"decision: EDIT&ACCEPT -> {_short(edited)}")
            return edited, None
        if cmd == "s":
            runlog.write("decision: SKIP (kept current)")
            return current, None
        if cmd == "r":
            note = ask("  your note")
            runlog.write(f"decision: RE-TUNE with note: {note}")
            return None, note


def run(content, jd, depth, extra, facts, mock):
    base = dict(jd=jd, depth=depth, extra=extra)
    for spec in _blocks(content):
        cur_extra = base
        while True:
            fields, cur = _fields(spec, content, cur_extra, facts)
            res = call_block(spec["prompt"], fields, mock, {spec["key"]: cur, "gaps": []})
            chosen, note = _decide(spec, cur, res.get(spec["key"], cur), res.get("gaps", []))
            if note is None:
                _dset(content, spec["path"], chosen)
                break
            cur_extra = dict(base, extra=(extra + " | " + note).strip(" |"))
    return content


def run_auto(content, jd, depth, extra, facts, mock):
    """Like run(), but non-interactive: accepts each block's proposed value automatically, no
    per-block review. For the web UI, which reviews the WHOLE tailored result afterward instead
    (like the Profile screen) rather than block by block."""
    base = dict(jd=jd, depth=depth, extra=extra)
    for spec in _blocks(content):
        cancel.check()  # between blocks - shortens a Stop click to one block's wait, not all of them
        fields, cur = _fields(spec, content, base, facts)
        res = call_block(spec["prompt"], fields, mock, {spec["key"]: cur, "gaps": []})
        _dset(content, spec["path"], res.get(spec["key"], cur))
    return content


def feedback_loop(content, out_path, mock):
    fill_template.build(content, out_path)
    print(f"\nGenerated: {out_path}")
    runlog.write(f"generated: {out_path}")
    while True:
        fb = ask("Feedback (blank = finish)")
        if not fb:
            runlog.write("feedback: (none) - done")
            print("Done.")
            return
        runlog.write(f"feedback: {fb}")
        content = call_block("feedback", dict(feedback=fb,
                             content=json.dumps(content, ensure_ascii=False)), mock, content)
        fill_template.build(content, out_path)
        print(f"Regenerated: {out_path}")
        runlog.write(f"regenerated: {out_path}")
