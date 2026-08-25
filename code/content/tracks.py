"""Choose an existing track or build a new one from the questionnaire; give its base content.
The first track in a fresh project can't clone anything, so it is built from DEFAULT_TRACK - a blank
but structurally complete scaffold the user then fills (blocks.json, skills, roles)."""
import copy
import json
import os

import paths
from content import assemble
from services.llm import PROMPTS
from services.ui import ask, ask_choice, select, yes

POS_PATH = os.path.join(paths.DATA, "positioning.json")

DEFAULT_TRACK = {
    "label": "",
    "headline": "",
    "summary": "",
    "skills": [
        {"label": "Group one", "items": "edit these in positioning.json"},
        {"label": "Group two", "items": "edit these in positioning.json"},
    ],
    "roles": {
        "role1": {"title": "", "dates": "", "max_bullets": 6},
        "role2": {"title": "", "dates": "", "max_bullets": 4},
        "role3": {"title": "", "dates": "", "max_bullets": 3},
        "role4": {"title": "", "dates": "", "max_bullets": 2},
    },
    "priorities": {
        "public_speaking": {"keep": [], "add_if_room": []},
        "articles": {"keep": [], "add_if_room": []},
    },
    "footer_title": "",
}


def load_positioning():
    return json.load(open(POS_PATH))


def _save(pos):
    json.dump(pos, open(POS_PATH, "w"), ensure_ascii=False, indent=2)


def _labels(pos, tracks):
    return {tid: pos["tracks"][tid].get("label", "") for tid in tracks}


def choose(pos):
    tracks = list(pos["tracks"].keys())
    print("\n== Track ==")
    if not tracks:  # fresh project: nothing to reuse or clone -> build the first track from scratch
        print("No tracks yet - creating the first one from scratch.")
        return _new_track(pos, tracks)
    labels = _labels(pos, tracks)
    print(f"Existing tracks ({len(tracks)}):")
    for tid in tracks:
        print(f"  - {tid}" + (f"   {labels[tid]}" if labels[tid] else ""))
    if ask_choice("Reuse an existing track, or create a new one?",
                  ["reuse existing", "new track"]) == "reuse existing":
        return select("Which track?", tracks, descriptions=labels)
    return _new_track(pos, tracks)


def _new_track(pos, tracks):
    print("\n-- New track questionnaire --")
    a = {}
    for q in PROMPTS["new_track_questions"]:
        if q["type"] == "choice_track":  # clone from an existing track (shown with its label); none on the first
            a[q["key"]] = select(q["q"], tracks, descriptions=_labels(pos, tracks)) if tracks else None
        elif q["type"] == "int":
            a[q["key"]] = int(ask(q["q"], q.get("default")))
        else:
            a[q["key"]] = ask(q["q"])

    if a.get("base_track"):
        base = copy.deepcopy(pos["tracks"][a["base_track"]])
    else:
        base = copy.deepcopy(DEFAULT_TRACK)
        print("  (no existing track to clone - starting from a blank scaffold)")
    base["label"] = a["label"]
    base["block_source"] = a["base_track"] or a["track_id"]  # borrow base tags, else use own id
    base["headline"] = a["headline_seed"]                    # seeds -> tailored in the block phase
    base["summary"] = a["summary_seed"]
    for i in (1, 2, 3, 4):
        base["roles"][f"role{i}"]["max_bullets"] = a[f"role{i}_max"]

    tid = a["track_id"]
    src = a["base_track"] or "scratch"
    print(f"\nNew track '{tid}' (from '{src}'): {base['label']}")
    if yes("Write it to positioning.json?"):
        pos["tracks"][tid] = base
        _save(pos)
        print("  written.")
    else:
        pos["tracks"][tid] = base  # in-memory for this run only
        print("  in-memory for this run only.")
    return tid


def base_content(track, pos):
    """Deterministic base content for a saved or in-memory track."""
    if track in load_positioning()["tracks"]:
        return assemble.assemble(track)
    return assemble.assemble_from(pos["tracks"][track])
