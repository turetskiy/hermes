"""Central filesystem paths. The CODE lives in the repo (ROOT), but the user's DATA / OUTPUT / .env
live in HERMES_HOME (default ~/Hermes) - OUTSIDE the code tree - so the project can move or sync
freely and a packaged app keeps user data in a stable place. Fine-grained overrides
(HERMES_HOME / HERMES_DATA / HERMES_OUTPUT / HERMES_ENV) still win, e.g. for tests. Call ensure_home()
once at startup to create and seed the home layout."""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # code/.. = the code repo

HOME = os.environ.get("HERMES_HOME") or os.path.join(os.path.expanduser("~"), "Hermes")
DATA = os.environ.get("HERMES_DATA") or os.path.join(HOME, "data")
OUTPUT = os.environ.get("HERMES_OUTPUT") or os.path.join(HOME, "output")
ENV = os.environ.get("HERMES_ENV") or os.path.join(HOME, ".env")

_BLANK_BLOCKS = {"blocks": []}
_BLANK_BLOCK_TRACKS = {}
_BLANK_POSITIONING = {"shared": {"public_speaking": {}, "articles": {}}, "tracks": {}}
_INBOX_README = (
    "Drop material here: CV exports, notes, project write-ups - .txt/.md/.docx/.pdf/.json/.csv\n"
    "(files with no extension are read too, as long as they are plain text).\n"
    "Then, in Hermes, run: Build the factbook.\n"
)


def _seed(path, text):
    if not os.path.exists(path):
        with open(path, "w") as f:
            f.write(text)


def ensure_home():
    """Create the home layout (data/ · output/ · data/inbox/) and seed the blank scaffolds the pipeline
    needs (blocks.json / positioning.json / inbox README) if missing. Idempotent - safe every startup."""
    for directory in (DATA, OUTPUT, os.path.join(DATA, "inbox")):
        os.makedirs(directory, exist_ok=True)
    _seed(os.path.join(DATA, "blocks.json"), json.dumps(_BLANK_BLOCKS, indent=2) + "\n")
    _seed(os.path.join(DATA, "block_tracks.json"), json.dumps(_BLANK_BLOCK_TRACKS, indent=2) + "\n")
    _seed(os.path.join(DATA, "positioning.json"), json.dumps(_BLANK_POSITIONING, indent=2) + "\n")
    _seed(os.path.join(DATA, "inbox", "README.txt"), _INBOX_README)
