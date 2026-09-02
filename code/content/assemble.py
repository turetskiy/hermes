"""
assemble.py - the piece that answers "why an intermediate content JSON?": there isn't one.

Given a track code, it reads blocks.json (achievement bank) + block_tracks.json (which blocks belong
to this track) + positioning.json (framing) and fills template.docx directly. Block selection is
deterministic: for each role row, take this track's assigned blocks, order by rank, cap at the
track's max_bullets. No hand-copied per-track file exists.

Usage:  python -m content.assemble director_remote  [output.docx]      (run from code/)

The same call is what the Gemini step wraps: it takes assemble's selected bullets and rewords them for
a specific vacancy before filling, obeying the guardrails. assemble is the deterministic floor.
"""
import json
import math
import os
import sys

if __package__ in (None, ""):  # allow `python code/content/assemble.py ...` direct runs
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import docx

import paths
from content import block_tracks
from rendering import fill_template

# Calibrated against real Word rendering: the outstaff pilot measured "one full page + a third"
# (~1.33 pages) at ~76 weighted lines, i.e. ~57 lines/page. CPL ~100 chars/line at 10pt.
CHARS_PER_LINE = 100
LINES_PER_PAGE = 57

BLOCKS = os.path.join(paths.DATA, "blocks.json")
POSITIONING = os.path.join(paths.DATA, "positioning.json")
IDENTITY = os.path.join(paths.DATA, "identity.json")


def estimate_pages(docx_path: str) -> float:
    d = docx.Document(docx_path)
    lines = 0.0
    for p in d.paragraphs:
        t = p.text
        if not t.strip():
            lines += 0.4
            continue
        lines += max(1, math.ceil(len(t) / CHARS_PER_LINE))
        if p.style.name == "CvExpHeader":
            lines += 0.6
    return lines / LINES_PER_PAGE


def load(path):
    with open(path) as f:
        return json.load(f)


def bullets_for_role(blocks, allowed_ids, role_slot, max_bullets):
    selected = [b for b in blocks if b["role_slot"] == role_slot and b["id"] in allowed_ids]
    selected.sort(key=lambda b: b["rank"])
    return [b["text"] for b in selected[:max_bullets]]


def select_list(shared_map, pri, cap):
    """keep ids (always shown) then add_if_room ids (until the cap), de-duplicated, in file order."""
    ordered, seen = [], set()
    for item_id in list(pri.get("keep", [])) + list(pri.get("add_if_room", [])):
        if item_id in shared_map and item_id not in seen:
            ordered.append(shared_map[item_id])
            seen.add(item_id)
    return ordered[:cap]


def load_identity():
    """data/identity.json, or {} if it doesn't exist yet - fill_template.py's docx_fixed.py leaves a
    token as-is when the data it needs isn't there, so an empty dict is a safe default, not an error."""
    return load(IDENTITY) if os.path.exists(IDENTITY) else {}


def build_content(pos_track, shared, blocks, sel_track, identity):
    """Assemble the content dict from a track's framing (pos_track) + shared pools + blocks. sel_track
    is a track id resolved to its assigned block ids via block_tracks.py - either the track's own id,
    or a borrowed 'block_source' track for one that hasn't saved blocks of its own yet. A role's bullet
    count is purely this track's own max_bullets - the template has no capacity ceiling to respect
    (see rendering/fill_template.py's docstring)."""
    allowed_ids = set(block_tracks.ids_for_track(sel_track))
    roles = {}
    for role_slot, spec in pos_track["roles"].items():
        bullets = bullets_for_role(blocks, allowed_ids, role_slot, spec["max_bullets"])
        if not bullets:
            roles[role_slot] = None  # nothing assigned to this track -> drop the whole role row
        else:
            roles[role_slot] = {"title": spec["title"], "dates": spec["dates"], "bullets": bullets}

    pri = pos_track["priorities"]
    return {
        "identity": identity,
        "tagline": pos_track["headline"],
        "summary": pos_track["summary"],
        "skills": pos_track["skills"],
        "roles": roles,
        "public_speaking": select_list(shared["public_speaking"], pri["public_speaking"], fill_template.SPEAK_CAPACITY),
        "articles": select_list(shared["articles"], pri["articles"], fill_template.ARTICLE_CAPACITY),
        "footer_title": pos_track["footer_title"],
    }


def assemble(track: str) -> dict:
    blocks = load(BLOCKS)["blocks"]
    pos_all = load(POSITIONING)
    if track not in pos_all["tracks"]:
        raise SystemExit(f"unknown track '{track}'. Known: {list(pos_all['tracks'])}")
    pos = pos_all["tracks"][track]
    return build_content(pos, pos_all["shared"], blocks, pos.get("block_source", track), load_identity())


def assemble_from(pos_track: dict) -> dict:
    """Build content from an in-memory track dict (e.g. an unsaved new track). It must carry
    'block_source' = the existing track whose block-id list it borrows for bullet selection."""
    blocks = load(BLOCKS)["blocks"]
    shared = load(POSITIONING)["shared"]
    sel = pos_track.get("block_source")
    if not sel:
        raise SystemExit("in-memory track needs a 'block_source' (existing track for block tags).")
    return build_content(pos_track, shared, blocks, sel, load_identity())


if __name__ == "__main__":
    track = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else os.path.join(paths.OUTPUT, f"resume_{track}.docx")
    content = assemble(track)
    fill_template.build(content, output_path)
    for role_slot, r in content["roles"].items():
        n = 0 if r is None else len(r["bullets"])
        print(f"  {role_slot}: {n} bullets" + ("" if r else " (role row dropped)"))
    print(f"  estimated length: ~{estimate_pages(output_path):.2f} pages (calibrated to Word)")
