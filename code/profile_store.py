"""Read-side access to the saved profile data (blocks.json / positioning.json / identity.json) - list
existing tracks and reconstruct one for viewing/editing without a fresh model call. Split out of
profile.py (the write/generate side) by concern. Which blocks belong to a track comes from
content/block_tracks.py, not from the blocks themselves - see that module for why."""
import json
import os

import paths
from content import block_tracks


def _load(name, default):
    try:
        with open(os.path.join(paths.DATA, name)) as f:
            return json.load(f)
    except (FileNotFoundError, ValueError):
        return default


def list_tracks():
    """[(track_id, label), ...] from positioning.json, for a track picker."""
    pos = _load("positioning.json", {})
    return [(tid, t.get("label") or tid) for tid, t in pos.get("tracks", {}).items()]


def track_picker_options():
    """{track_id: 'label  [track_id]'} - the shared display format for a track dropdown, used by
    both the Profile and Tailor screens so a track picked in one can be handed to the other."""
    return {tid: f"{label}  [{tid}]" for tid, label in list_tracks()}


def load_track(track_id):
    """Reconstruct a data dict (same shape as profile.generate()'s output) for an already-saved
    track, by pulling its blocks (via block_tracks.ids_for_track), positioning fields, and identity -
    so it can be viewed/edited without a fresh model call."""
    pos = _load("positioning.json", {})
    track = pos.get("tracks", {}).get(track_id)
    if track is None:
        raise KeyError(f"no such track: {track_id}")
    pool = {b["id"]: b for b in _load("blocks.json", {}).get("blocks", [])}
    blocks = [{"id": bid, "role_slot": pool[bid]["role_slot"], "rank": pool[bid]["rank"],
               "text": pool[bid]["text"]}
              for bid in block_tracks.ids_for_track(track_id) if bid in pool]
    shared = pos.get("shared", {})
    pri = track.get("priorities", {})

    def _pool(kind):
        ids = pri.get(kind, {}).get("keep", [])
        pool = shared.get(kind, {})
        return [{"id": i, "text": pool[i]} for i in ids if i in pool]

    roles = {r: {"title": s.get("title", ""), "dates": s.get("dates", "")}
             for r, s in track.get("roles", {}).items()}
    return {
        "identity": _load("identity.json", {}), "roles": roles, "blocks": blocks,
        "skills": track.get("skills", []),
        "public_speaking": _pool("public_speaking"), "articles": _pool("articles"),
        "headline": track.get("headline", ""), "summary": track.get("summary", ""),
        "footer_title": track.get("footer_title", ""),
    }
