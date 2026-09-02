"""Write-side of the profile: turn a generated/edited data dict into blocks.json, block_tracks.json,
positioning.json, identity.json. Split out of profile.py (the generate/CLI side) by concern - mirrors
profile_store.py (the read-side) on the other side of the same data."""
import json
import os

import paths
from content import block_tracks

# The 4 valid role slots, and a sensible starting bullet count for each when a profile is first built
# (min'd against how many the model actually found for that role) - a Hermes-owned default, same as
# content/tracks.py's DEFAULT_TRACK/new_track_questions use for a track built the CLI way. Not tied to
# any template capacity - the template has none; raise a role's max_bullets freely after Build profile,
# directly in the editable JSON, if you want more than the default.
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


def _positioning(data, track_id, label):
    speaking = {s["id"]: s["text"] for s in data.get("public_speaking", []) if s.get("id") and s.get("text")}
    articles = {a["id"]: a["text"] for a in data.get("articles", []) if a.get("id") and a.get("text")}
    counts = {r: 0 for r in ROLE_SLOTS}
    for b in data.get("blocks", []):
        if b.get("role_slot") in counts:
            counts[b["role_slot"]] += 1
    roles = {r: {"title": s.get("title", ""), "dates": s.get("dates", ""),
                 "max_bullets": min(counts[r], DEFAULT_MAX_BULLETS[r]) or DEFAULT_MAX_BULLETS[r]}
             for r, s in data.get("roles", {}).items() if r in ROLE_SLOTS}
    track = {
        "label": label, "headline": data.get("headline", ""), "summary": data.get("summary", ""),
        "footer_title": data.get("footer_title", ""), "skills": _flat_skills(data.get("skills")),
        "roles": roles,
        "priorities": {"public_speaking": {"keep": list(speaking), "add_if_room": []},
                       "articles": {"keep": list(articles), "add_if_room": []}},
        "block_source": track_id,
    }
    return {"shared": {"public_speaking": speaking, "articles": articles}, "tracks": {track_id: track}}


def _dump(name, obj):
    with open(os.path.join(paths.DATA, name), "w") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def _load_blocks_pool():
    try:
        with open(os.path.join(paths.DATA, "blocks.json")) as f:
            return {b["id"]: b for b in json.load(f).get("blocks", [])}
    except (FileNotFoundError, ValueError):
        return {}


def delete_track(track_id):
    """Remove a track from positioning.json - its block_tracks.json entry goes with it (prune), but the
    underlying blocks stay in the shared pool untouched, just unassigned; nothing here ever deletes a
    block. Returns False if there was no such track (nothing to do)."""
    pos_path = os.path.join(paths.DATA, "positioning.json")
    try:
        with open(pos_path) as f:
            pos = json.load(f)
    except (FileNotFoundError, ValueError):
        return False
    if track_id not in pos.get("tracks", {}):
        return False
    del pos["tracks"][track_id]
    _dump("positioning.json", pos)
    block_tracks.prune(pos["tracks"].keys())
    return True


def write_profile(data, track_id, label):
    # compute everything first (may raise) so a bad response never leaves half-written files -
    # fallback ids are namespaced by track_id since they're positional (b0, b1, ...) and would
    # otherwise collide across tracks now that blocks.json is one shared, cumulative pool
    blocks = [{"id": b.get("id") or f"{track_id}_b{i}", "role_slot": b["role_slot"],
               "rank": b.get("rank", i + 1), "text": b.get("text", "")}
              for i, b in enumerate(data.get("blocks", [])) if b.get("role_slot") in ROLE_SLOTS]
    pos = _positioning(data, track_id, label)
    try:  # keep any existing tracks; refresh shared pools + this track
        with open(os.path.join(paths.DATA, "positioning.json")) as f:
            existing = json.load(f)
        existing.setdefault("tracks", {}).update(pos["tracks"])
        existing["shared"] = pos["shared"]
        pos = existing
    except (FileNotFoundError, ValueError):
        pass
    pool = _load_blocks_pool()
    pool.update({b["id"]: b for b in blocks})  # merge - never wipe other tracks' blocks
    _dump("identity.json", data.get("identity", {}))
    _dump("blocks.json", {"blocks": list(pool.values())})
    _dump("positioning.json", pos)
    block_tracks.set_track(track_id, [b["id"] for b in blocks])
    block_tracks.prune(pos["tracks"].keys())  # drop any leftover reference to a since-deleted track
    return len(blocks)
