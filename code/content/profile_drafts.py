"""Step 1 ("Selection") scratch state for the Profile screen: per-track draft = the model's proposed
identity/roles/fact-tagging, before Step 2 ("Build") polishes any of it into real blocks.json/
positioning.json/identity.json content. Deliberately its own file, never blocks.json - a draft's facts
are raw, unreviewed text; letting them touch the shared blocks pool before Build would risk a Tailor
export picking up unpolished fact fragments. Shape on disk: {track_id: draft_dict}, where draft_dict
is {identity, roles, facts: [{id,text,assign,rank}], headline, summary, footer_title}."""
import json
import os

import paths

PATH = os.path.join(paths.DATA, "profile_drafts.json")


def load():
    try:
        with open(PATH) as f:
            return json.load(f)
    except (FileNotFoundError, ValueError):
        return {}


def save(mapping):
    with open(PATH, "w") as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)


def get(track_id):
    return load().get(track_id)


def set(track_id, draft):
    mapping = load()
    mapping[track_id] = draft
    save(mapping)


def delete(track_id):
    mapping = load()
    if track_id in mapping:
        del mapping[track_id]
        save(mapping)
