#!/usr/bin/env python3
"""
profile.py - turn the factbook (data/factbook.md) into the data the tailor pipeline needs:
  data/blocks.json        achievement bullets (id, role_slot, rank, text) - independent of any track
  data/block_tracks.json  which blocks belong to which track (content/block_tracks.py owns this)
  data/positioning.json   a base track: skills clusters, roles (title/dates), priorities + shared pools
  data/identity.json      name / contact / education / companies - baked into the template's fixed tokens

The model does the extraction under strict 'facts only' rules; this file wraps the prompt and writes files.

Run:
  python code/profile.py               # needs an API key in .env
  python code/profile.py --mock        # write a tiny canned profile (see the flow / test)
"""
import argparse
import json
import os
import sys
import warnings

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", message=r".*OpenSSL.*")

import paths
from profile_write import delete_track, write_profile  # noqa: F401  delete_track re-exported for web/profile.py
from services import llm, report
from services.llm import PROMPTS
from services.ui import ask

SOURCE = os.path.join(paths.DATA, "factbook.md")

MOCK = {
    "identity": {"name": "Jane Doe", "contact": "City, Country - jane@x.io - linkedin.com/in/jane",
                 "education": {"degree": "BSc Computer Science", "institution": "State University", "dates": "2008 - 2012"},
                 "companies": {"role1": "Acme", "role2": "Globex", "role3": "Initech", "role4": "Umbrella"}},
    "roles": {"role1": {"title": "Head of Engineering", "dates": "2021 - Present"},
              "role2": {"title": "Engineering Manager", "dates": "2018 - 2021"},
              "role3": {"title": "Senior Engineer", "dates": "2015 - 2018"},
              "role4": {"title": "Engineer", "dates": "2012 - 2015"}},
    "blocks": [{"id": "grew-team", "role_slot": "role1", "rank": 1, "text": "Grew the team from **3 to 12**."},
               {"id": "cut-cost", "role_slot": "role1", "rank": 2, "text": "Cut infrastructure cost by **40%**."},
               {"id": "shipped-x", "role_slot": "role2", "rank": 1, "text": "Shipped platform X on Python/Go."}],
    "skills": [{"label": "Cloud", "items": "AWS, GCP"}, {"label": "Backend", "items": "Python, Go"},
               {"label": "Leadership", "items": "Hiring, Roadmapping"}],
    "public_speaking": [{"id": "talk1", "text": "Conference talk - https://example.com/talk"}],
    "articles": [],
    "headline": "Engineering Leader | Cloud | Teams | 12 yrs",
    "summary": "A pragmatic engineering leader who **ships** and **grows teams**.",
    "footer_title": "Jane Doe - Engineering Leader",
}


def generate(factbook):
    """Extract the whole profile in one call. Retries once on malformed JSON (the model occasionally
    drops a comma/brace in a response this long) - same pattern as llm.call_block(), just without a
    fallback to fall back to, since there's no sensible partial result for a whole-profile extraction."""
    task = PROMPTS["profile"]["task"].replace("{factbook}", factbook)
    for attempt in (1, 2):
        try:
            raw = llm.generate(PROMPTS["profile"]["system"], task, label=f"profile attempt {attempt}")
            return llm._extract_json(raw)
        except ValueError as e:
            if attempt == 2:
                raise
            report.warn(f"  Model returned malformed JSON ({e}); retrying...")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mock", action="store_true", help="write a tiny canned profile (no model call)")
    args = ap.parse_args()
    paths.ensure_home()
    if not os.path.exists(SOURCE):
        sys.exit(f"No factbook at {SOURCE}. Build it first with factbook.py.")

    if args.mock:
        data = MOCK
    else:
        llm.load_env()
        if not os.environ.get("GEMINI_API_KEY"):
            sys.exit("GEMINI_API_KEY not set (put it in .env) - or run with --mock.")
        report.step("Reading the factbook and extracting blocks / positioning / identity with the model...")
        try:
            data = generate(open(SOURCE).read())
        except Exception as e:  # noqa: BLE001
            sys.exit(f"Model call failed: {e}\nTry again in a moment.")

    default_label = data.get("roles", {}).get("role1", {}).get("title", "Resume")
    track_id = ask("Track id (snake_case)", "base")
    label = ask("One-line label for this track", default_label)
    n = write_profile(data, track_id, label)
    report.info(f"\nWrote:\n  data/identity.json\n  data/blocks.json ({n} blocks)\n"
                f"  data/block_tracks.json (track '{track_id}')\n  data/positioning.json (track '{track_id}')")
    report.info("Now run Tailor for a full resume - or open positioning.json to fine-tune skills/roles.")


if __name__ == "__main__":
    main()
