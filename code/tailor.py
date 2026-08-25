#!/usr/bin/env python3
"""
tailor.py - interactive JD-tailoring tool (see AGENT_GUIDE.md 4). Thin orchestrator; each
concern lives in its own module: ui, runlog, llm, vacancy, tracks, pipeline.

Flow: pick/create a track -> get a vacancy (or skip) -> choose rework depth -> the model tailors
each block (accept / re-tune / skip) -> build the docx -> loop on feedback. Every run writes a
fresh tailor.log. Tailoring never mutates a track's 04 baseline; only new-track creation writes 04.

Run:
  ./.venv/bin/python3 code/tailor.py            # real model calls (needs an API key in .env)
  ./.venv/bin/python3 code/tailor.py --mock     # skip the model (echo content), to test the flow
  ./.venv/bin/python3 code/tailor.py --list-models
"""
import argparse
import os
import sys
import warnings

warnings.filterwarnings("ignore", category=FutureWarning)      # google-auth Python-3.9 EOL noise
warnings.filterwarnings("ignore", message=r".*OpenSSL.*")      # urllib3 LibreSSL noise (by message)

import paths
from content.pipeline import feedback_loop, run
from content.tracks import base_content, choose, load_positioning
from services import llm, runlog
from services.llm import PROMPTS
from services.ui import ask, ask_choice
from services.vacancy import get_vacancy
from templating import build_template

FACTS_PATH = os.path.join(paths.DATA, "factbook.md")


def _depth():
    print("\n== Rework depth ==")
    lvl = ask_choice("How deep should the model rework each block?", list(PROMPTS["depth_levels"]))
    return PROMPTS["depth_levels"][lvl], lvl


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mock", action="store_true", help="skip model calls (test the flow)")
    ap.add_argument("--list-models", action="store_true", help="print the configured model and how to change it")
    args = ap.parse_args()
    paths.ensure_home()

    llm.load_env()
    if args.list_models:
        llm.list_models()
        return
    if not args.mock and not os.environ.get("GEMINI_API_KEY"):
        sys.exit("GEMINI_API_KEY not set (put it in .env) - or run with --mock.")

    runlog.init()

    print("\n== Template style ==")
    style = ask_choice("Which resume template should I build?", build_template.list_styles())
    build_template.build(style)
    runlog.write(f"template: {style}")
    print(f"Built data/template.docx ({style}).")

    pos = load_positioning()
    track = choose(pos)
    runlog.write(f"track: {track}")
    content = base_content(track, pos)

    jd = get_vacancy()
    if jd:
        depth_text, depth_name = _depth()
        extra = ask("Any extra instructions for this vacancy (blank = none)")
        facts = open(FACTS_PATH).read()
        runlog.write(f"vacancy: {len(jd)} chars | depth: {depth_name} | extra: {extra}\nJD:\n{jd}")
        print(f"\nTailoring '{track}' | depth={depth_name}. Going block by block...")
        content = run(content, jd, depth_text, extra, facts, args.mock)
    else:
        runlog.write("vacancy: skipped (baseline only)")
        print(f"\nNo vacancy - generating the '{track}' baseline; refine by feedback.")

    out = os.path.join(paths.OUTPUT, f"resume_{track}_tailored.docx")
    feedback_loop(content, out, args.mock)


if __name__ == "__main__":
    main()
