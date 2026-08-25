"""One log file per session (data/output/tailor.log). Self-opens (append) on the first write() even if
init() was never called - so any LLM call gets logged regardless of which entry point started it (the
web UI's Profile/Material screens included), not just the Tailor CLI. Call init() explicitly for a
guaranteed fresh (overwritten) log at the start of a full CLI pipeline run."""
import os

import paths

LOG_PATH = os.path.join(paths.OUTPUT, "tailor.log")
_f = None


def init():
    global _f
    os.makedirs(paths.OUTPUT, exist_ok=True)
    _f = open(LOG_PATH, "w")  # overwrite - a fresh log for this run


def write(msg):
    global _f
    if _f is None:
        os.makedirs(paths.OUTPUT, exist_ok=True)
        _f = open(LOG_PATH, "a")  # no explicit init() this session - append, never clobber silently
    _f.write(str(msg).rstrip() + "\n")
    _f.flush()
