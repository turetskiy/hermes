"""Read-side access to the saved profile data (blocks.json / positioning.json / identity.json /
profile_drafts.json) - list existing tracks and load one entity at a time for viewing/editing, without
a fresh model call. Split out of profile.py (the write/generate side) by concern. Which blocks belong
to a track comes from content/block_tracks.py, not from the blocks themselves - see that module for why."""
import json
import os

import paths
from content import block_tracks, profile_drafts


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


def load_identity():
    """name/contact/education/companies - global, not per-track."""
    return _load("identity.json", {})


def load_draft(track_id):
    """The Step 1 ('Selection') scratch state for a track, or None if it's never been Proposed."""
    return profile_drafts.get(track_id)


def load_track_meta(track_id):
    """label/headline/summary/footer_title for a track, or blanks for one that doesn't exist yet."""
    pos = _load("positioning.json", {})
    track = pos.get("tracks", {}).get(track_id, {})
    return {k: track.get(k, "") for k in ("label", "headline", "summary", "footer_title")}


def load_role(track_id, role_slot):
    """title/dates/max_bullets/bullets for one role of a saved track - bullets pulled via
    block_tracks.ids_for_track, filtered to this role_slot, in their stored (curated) order."""
    pos = _load("positioning.json", {})
    role = pos.get("tracks", {}).get(track_id, {}).get("roles", {}).get(role_slot, {})
    pool = {b["id"]: b for b in _load("blocks.json", {}).get("blocks", [])}
    bullets = [{"id": bid, "text": pool[bid]["text"]}
               for bid in block_tracks.ids_for_track(track_id)
               if bid in pool and pool[bid]["role_slot"] == role_slot]
    return {"title": role.get("title", ""), "dates": role.get("dates", ""),
            "max_bullets": role.get("max_bullets"), "bullets": bullets}


def load_skills(track_id):
    pos = _load("positioning.json", {})
    return pos.get("tracks", {}).get(track_id, {}).get("skills", [])
