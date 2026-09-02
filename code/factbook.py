"""
factbook.py - build the single-source-of-truth factbook from a folder of raw career material.

Dump anything into data/inbox/ (or pass a folder): CV exports, notes, project write-ups - .txt/.md/
.docx/.pdf/.json/.csv, or plain-text files with no extension at all. This extracts the text from every
file, then the model synthesises the factbook following the schema - using ONLY facts present in the
material, exact numbers, marking anything uncertain [?], and listing gaps/questions at the end.

The combined raw text is saved to output/factbook_source.txt as an audit trail. Used by web/material.py."""
import os
import re
import warnings

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", message=r".*OpenSSL.*")

import paths
from services import llm, report
from services.llm import PROMPTS
from ingest.collect import collect

INBOX = os.path.join(paths.DATA, "inbox")
OUT = os.path.join(paths.DATA, "factbook.md")
RAW = os.path.join(paths.OUTPUT, "factbook_source.txt")

ADDED_HEADING = "## Added facts"


def synthesize(dump):
    task = PROMPTS["factbook"]["task"].replace("{material}", dump)
    return llm.generate(PROMPTS["factbook"]["system"], task, label="factbook synthesize")


def polish_fact(raw_text):
    """One or more clean, atomic fact bullet lines from a raw/messy note - via the model."""
    task = PROMPTS["fact_add"]["task"].replace("{text}", raw_text)
    return llm.generate(PROMPTS["fact_add"]["system"], task, label="fact add/polish")


def add_fact(md, fact_text):
    """Append fact_text (any text - normalized into '- ...' bullet lines) under a dedicated
    ADDED_HEADING section, created at the end if missing. Pure/deterministic, no model call - by
    convention this heading is always kept last since only this function ever writes to it."""
    bullets = "\n".join(
        ln if ln.lstrip().startswith(("-", "*")) else f"- {ln.strip()}"
        for ln in fact_text.strip().splitlines() if ln.strip()
    )
    if not bullets:
        return md
    if ADDED_HEADING in md:
        return md.rstrip() + "\n" + bullets + "\n"
    return md.rstrip() + "\n\n" + ADDED_HEADING + "\n" + bullets + "\n"


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


def write(md):
    """Write the factbook markdown to data/factbook.md; return the path. (Non-interactive.)"""
    with open(OUT, "w") as f:
        f.write(md.strip() + "\n")
    return OUT


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
