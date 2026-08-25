"""Which blocks belong to which tracks - kept in its own file (data/block_tracks.json), separate from
blocks.json itself. Blocks stay independent content (id, role_slot, rank, text, nothing track-specific);
this module is the one place that knows which track(s) reference a given block id, so moving a block
to a different track - or several at once - is a one-line edit here, never a rewrite of the block.
Shape on disk: {track_id: [block_id, ...]}."""
import json
import os

import paths

PATH = os.path.join(paths.DATA, "block_tracks.json")


def load():
    try:
        with open(PATH) as f:
            return json.load(f)
    except (FileNotFoundError, ValueError):
        return {}


def save(mapping):
    with open(PATH, "w") as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)


def ids_for_track(track_id):
    """Block ids assigned to one track, in their stored (curated) order."""
    return list(load().get(track_id, []))


def set_track(track_id, block_ids):
    """Replace one track's block-id list, leaving every other track's list untouched."""
    mapping = load()
    mapping[track_id] = list(block_ids)
    save(mapping)


def prune(valid_track_ids):
    """Drop any track_id key whose track no longer exists (e.g. deleted from positioning.json) -
    quietly, no warning. Orphaned block ids (a block no track references) are left alone - that's an
    expected, harmless state here, not a corruption to report."""
    mapping = load()
    valid = set(valid_track_ids)
    pruned = {tid: ids for tid, ids in mapping.items() if tid in valid}
    if pruned != mapping:
        save(pruned)


def tracks_for_block(block_id):
    """Which tracks currently include this block id - the reverse lookup."""
    return [tid for tid, ids in load().items() if block_id in ids]


def reassign(block_id, track_ids):
    """Set exactly which tracks a block belongs to: added to every track in track_ids, removed from
    every other track that had it. The direct way to redistribute a block without touching blocks.json."""
    mapping = load()
    wanted = set(track_ids)
    for tid in list(mapping):
        has, wants = block_id in mapping[tid], tid in wanted
        if wants and not has:
            mapping[tid].append(block_id)
        elif has and not wants:
            mapping[tid] = [b for b in mapping[tid] if b != block_id]
    for tid in wanted - set(mapping):
        mapping[tid] = [block_id]
    save(mapping)
