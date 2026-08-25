#!/usr/bin/env python3
"""
factbook.py - build the single-source-of-truth factbook from a folder of raw career material.

Dump anything into data/inbox/ (or pass a folder): CV exports, notes, project write-ups - .txt/.md/
.docx/.pdf/.json/.csv, or plain-text files with no extension at all. This extracts the text from every
file, then the model synthesises the factbook following the schema - using ONLY facts present in the
material, exact numbers, marking anything uncertain [?], and listing gaps/questions at the end.

When it's ready it asks how to save: write data/factbook.md quietly, or write it and open it in
your editor for review. The combined raw text is saved to output/factbook_source.txt as an audit trail.

Run:
  python code/factbook.py                 # reads data/inbox/
  python code/factbook.py /path/to/dir
  python code/factbook.py --mock          # extract + report only (no model call)
"""
import argparse
import os
import re
import subprocess
import sys
import warnings

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", message=r".*OpenSSL.*")

import paths
from services import llm, report, ui
from services.llm import PROMPTS
from ingest.collect import collect

INBOX = os.path.join(paths.DATA, "inbox")
OUT = os.path.join(paths.DATA, "factbook.md")
RAW = os.path.join(paths.OUTPUT, "factbook_source.txt")


def synthesize(dump):
    task = PROMPTS["factbook"]["task"].replace("{material}", dump)
    return llm.generate(PROMPTS["factbook"]["system"], task, label="factbook synthesize")


def parse_gaps(md):
    """Extract the bullet items under '## Gaps / open questions' (any heading level, case-insensitive).
    Returns [] if the factbook has no such section - e.g. after every gap has been resolved."""
    m = re.search(r"^#{1,3}\s*Gaps.*$", md, re.I | re.M)
    if not m:
        return []
    tail = md[m.end():]
    nxt = re.search(r"^#{1,3}\s", tail, re.M)
    section = tail[:nxt.start()] if nxt else tail
    return [ln.strip()[1:].strip() for ln in section.splitlines() if ln.strip()[:1] in ("-", "*")]


def resolve_gaps(md, qa_pairs):
    """qa_pairs: [(question, answer), ...] with non-empty answers. Merges them into the factbook and
    removes/refines the resolved gap bullets. Returns the full updated factbook markdown."""
    answers = "\n".join(f"- {q}\n  -> {a}" for q, a in qa_pairs)
    task = (PROMPTS["factbook_resolve"]["task"]
            .replace("{factbook}", md).replace("{answers}", answers))
    return llm.generate(PROMPTS["factbook_resolve"]["system"], task, label="factbook resolve_gaps")


def _open_editor(path):
    editor = os.environ.get("VISUAL") or os.environ.get("EDITOR")
    try:
        if editor:
            subprocess.run(editor.split() + [path])
        elif sys.platform == "darwin":
            subprocess.run(["open", path])
        else:
            subprocess.run(["xdg-open", path])
    except Exception as e:  # noqa: BLE001
        print(f"  couldn't open an editor automatically ({e}). The file is at {path}")


def write(md):
    """Write the factbook markdown to data/factbook.md; return the path. (Non-interactive.)"""
    with open(OUT, "w") as f:
        f.write(md.strip() + "\n")
    return OUT


def _save(md):
    report.info("")
    mode = ui.select("Factbook is ready. How should I save it?",
                     ["Write it quietly", "Write and open it in an editor for review"])
    write(md)
    report.info(f"\nSaved factbook -> {OUT}")
    report.info("Check the 'Gaps / open questions' section before you rely on it.")
    if mode.startswith("Write and open"):
        _open_editor(OUT)


def _extract(inbox):
    """Collect text from the inbox, report used/skipped, save the raw dump; return the combined text."""
    dump, used, skipped = collect(inbox)
    report.info(f"\nRead {len(used)} file(s) from {inbox}:")
    for r in used:
        report.info(f"  + {r}")
    if skipped:
        report.info("Skipped:")
        for r in skipped:
            report.info(f"  - {r}")
    if not dump.strip():
        raise ValueError("No readable text found. Put files into the inbox and try again.")
    os.makedirs(paths.OUTPUT, exist_ok=True)
    with open(RAW, "w") as f:
        f.write(dump.strip() + "\n")
    report.info(f"\nRaw extracted text -> {RAW}")
    return dump


def build(inbox):
    """Extract + model synthesis -> factbook markdown. Used by the web UI (caller ensures the key)."""
    dump = _extract(inbox)
    report.step("Synthesising the factbook with the model (facts only, no invention)...")
    return synthesize(dump)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("inbox", nargs="?", default=INBOX, help="folder of raw material (default data/inbox/)")
    ap.add_argument("--mock", action="store_true", help="extract + report only, skip the model")
    args = ap.parse_args()
    paths.ensure_home()

    try:
        dump = _extract(args.inbox)
    except ValueError as e:
        sys.exit(str(e))
    if args.mock:
        report.info("--mock: skipping model synthesis.")
        return

    llm.load_env()
    if not os.environ.get("GEMINI_API_KEY"):
        sys.exit("GEMINI_API_KEY not set (put it in .env) - or run with --mock to just extract.")
    report.step("Synthesising the factbook with the model (facts only, no invention)...")
    try:
        md = synthesize(dump)
    except Exception as e:  # noqa: BLE001
        sys.exit(f"Model call failed: {e}\nTry again in a moment (the raw text is saved above).")
    _save(md)


if __name__ == "__main__":
    main()
