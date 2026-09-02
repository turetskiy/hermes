"""Write-side of the profile: persist one entity at a time into blocks.json, block_tracks.json,
positioning.json, identity.json - identity, one role's bullets, skills, or speaking/articles,
independently, so rebuilding/saving role3 never touches role1/skills/identity. Mirrors profile_store.py
(the read-side) on the other side of the same data."""
import json
import os

import paths
from content import block_tracks, profile_drafts

# The 4 valid role slots, and a sensible starting bullet count for each when a role is first built (min'd
# against how many facts were actually assigned to it) - a Hermes-owned default, not tied to any template
# capacity. Raise a role's max_bullets freely after building it, via web/profile_roles.py's number input.
DEFAULT_MAX_BULLETS = {"role1": 6, "role2": 4, "role3": 3, "role4": 2}
ROLE_SLOTS = tuple(DEFAULT_MAX_BULLETS)


def _flat_skills(sk):
    """Skills as a flat list of {label, items} clusters - any number of them. Accepts a list (the
    shape we ask the model for) or a legacy dict-of-groups, so it never depends on specific group keys."""
    if isinstance(sk, list):
        clusters = sk
    elif isinstance(sk, dict):
        clusters = [c for g in sk.values() if isinstance(g, list) for c in g]
    else:
        clusters = []
    return [c for c in clusters if isinstance(c, dict) and (c.get("label") or c.get("items"))]


def _dump(name, obj):
    with open(os.path.join(paths.DATA, name), "w") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def _load_blocks_pool():
    try:
        with open(os.path.join(paths.DATA, "blocks.json")) as f:
            return {b["id"]: b for b in json.load(f).get("blocks", [])}
    except (FileNotFoundError, ValueError):
        return {}


def _load_pos():
    try:
        with open(os.path.join(paths.DATA, "positioning.json")) as f:
            return json.load(f)
    except (FileNotFoundError, ValueError):
        return {"shared": {"public_speaking": {}, "articles": {}}, "tracks": {}}


def _new_track(track_id):
    return {"label": "", "headline": "", "summary": "", "footer_title": "", "skills": [], "roles": {},
            "priorities": {"public_speaking": {"keep": [], "add_if_room": []},
                            "articles": {"keep": [], "add_if_room": []}},
            "block_source": track_id}


def delete_track(track_id):
    """Remove a track from positioning.json - its block_tracks.json entry and any Step-1 draft go with
    it, but the underlying blocks stay in the shared pool untouched, just unassigned; nothing here ever
    deletes a block. Returns False if there was no such track (nothing to do)."""
    pos = _load_pos()
    found = track_id in pos.get("tracks", {})
    if found:
        del pos["tracks"][track_id]
        _dump("positioning.json", pos)
        block_tracks.prune(pos["tracks"].keys())
    profile_drafts.delete(track_id)
    return found


def write_identity(identity, track_id, label, headline, summary, footer_title):
    """The Identity panel's Save: the global identity.json, plus this track's label/headline/summary/
    footer_title in positioning.json (per-track, unlike identity itself, but grouped here since they're
    all small text fields edited on the same panel)."""
    _dump("identity.json", identity)
    pos = _load_pos()
    track = pos.setdefault("tracks", {}).setdefault(track_id, _new_track(track_id))
    track.update(label=label, headline=headline, summary=summary, footer_title=footer_title)
    _dump("positioning.json", pos)


def write_role(track_id, role_slot, title, dates, blocks, max_bullets=None):
    """Merge just this role's blocks into the shared blocks.json pool by id, and read-modify-write
    block_tracks.json's id list for this track: drop ids no longer produced by this build AND any id
    currently tagged this role_slot in the pool that this build no longer includes (a fact un-assigned
    since the last build), then add this build's ids. block_tracks id ORDER carries no meaning -
    content/assemble.py only ever treats it as a set - so this is safe. Returns the block count."""
    new_blocks = [{"id": b["id"], "role_slot": role_slot, "rank": i + 1, "text": b["text"]}
                  for i, b in enumerate(blocks)]
    new_ids = {b["id"] for b in new_blocks}
    pool = _load_blocks_pool()
    current_ids = block_tracks.ids_for_track(track_id)
    kept = [i for i in current_ids
            if i not in new_ids and pool.get(i, {}).get("role_slot") != role_slot]
    block_tracks.set_track(track_id, kept + [b["id"] for b in new_blocks])
    pool.update({b["id"]: b for b in new_blocks})
    _dump("blocks.json", {"blocks": list(pool.values())})

    pos = _load_pos()
    track = pos.setdefault("tracks", {}).setdefault(track_id, _new_track(track_id))
    existing = track.get("roles", {}).get(role_slot, {}).get("max_bullets")
    default = min(len(new_blocks), DEFAULT_MAX_BULLETS[role_slot]) or DEFAULT_MAX_BULLETS[role_slot]
    track.setdefault("roles", {})[role_slot] = {
        "title": title, "dates": dates,
        "max_bullets": max_bullets if isinstance(max_bullets, int) else (
            existing if isinstance(existing, int) else default),
    }
    _dump("positioning.json", pos)
    return len(new_blocks)


def write_skills(track_id, skills):
    pos = _load_pos()
    track = pos.setdefault("tracks", {}).setdefault(track_id, _new_track(track_id))
    track["skills"] = _flat_skills(skills)
    _dump("positioning.json", pos)


def write_speaking_articles(track_id, speaking, articles):
    """Deterministic pass-through (no LLM involved) - speaking/articles are [{id, text}] facts tagged
    in the Selection step, formatted straight into the shared cross-track pool + this track's keep list."""
    pos = _load_pos()
    track = pos.setdefault("tracks", {}).setdefault(track_id, _new_track(track_id))
    shared = pos.setdefault("shared", {"public_speaking": {}, "articles": {}})
    shared.setdefault("public_speaking", {}).update({s["id"]: s["text"] for s in speaking})
    shared.setdefault("articles", {}).update({a["id"]: a["text"] for a in articles})
    track["priorities"] = {
        "public_speaking": {"keep": [s["id"] for s in speaking], "add_if_room": []},
        "articles": {"keep": [a["id"] for a in articles], "add_if_room": []},
    }
    _dump("positioning.json", pos)
