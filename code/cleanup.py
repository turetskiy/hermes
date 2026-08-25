#!/usr/bin/env python3
"""Reset the project to a clean state: remove everything generated and every personal input, and reset
the data scaffolds to blank - but NEVER touch .env (nor the code or the .venv). Confirms first."""
import os
import shutil

import paths
from services.ui import yes

BLANK_BLOCKS = '{\n  "blocks": []\n}\n'
BLANK_BLOCK_TRACKS = "{}\n"
BLANK_POSITIONING = (
    '{\n  "shared": {\n    "public_speaking": {},\n    "articles": {}\n  },\n  "tracks": {}\n}\n'
)
BLANK_SOURCE = (
    "# Factbook - <PERSON NAME>\n\n"
    "BLANK. Build it with `factbook.py` (drop material into data/inbox/), or edit by hand.\n"
)

PLAN = [
    "output/                     all generated resumes, logs, factbook_source.txt",
    "data/inbox/                 your dropped materials (keeps README.txt)",
    "data/template.docx + .meta.json + factbook.draft.md",
    "data/factbook.md · blocks.json · block_tracks.json · positioning.json   -> reset to blank",
    "KEEP untouched: .env · code/ · .venv/ · README · skeleton.md",
]


def _empty_dir(path, keep=()):
    if not os.path.isdir(path):
        return
    for name in os.listdir(path):
        if name in keep:
            continue
        target = os.path.join(path, name)
        shutil.rmtree(target) if os.path.isdir(target) else os.remove(target)


def _rm(*names):
    for name in names:
        path = os.path.join(paths.DATA, name)
        if os.path.isfile(path):
            os.remove(path)


def main():
    paths.ensure_home()
    print("\nThis resets the project to a clean state:")
    for line in PLAN:
        print("  - " + line)
    if not yes("\nProceed? This cannot be undone"):
        print("Cancelled - nothing changed.")
        return
    _empty_dir(paths.OUTPUT)
    _empty_dir(os.path.join(paths.DATA, "inbox"), keep=("README.txt",))
    _rm("template.docx", "template.meta.json", "factbook.draft.md", "identity.json")
    with open(os.path.join(paths.DATA, "factbook.md"), "w") as f:
        f.write(BLANK_SOURCE)
    with open(os.path.join(paths.DATA, "blocks.json"), "w") as f:
        f.write(BLANK_BLOCKS)
    with open(os.path.join(paths.DATA, "block_tracks.json"), "w") as f:
        f.write(BLANK_BLOCK_TRACKS)
    with open(os.path.join(paths.DATA, "positioning.json"), "w") as f:
        f.write(BLANK_POSITIONING)
    print("\nDone - the project is clean (.env kept).")


if __name__ == "__main__":
    main()
