#!/usr/bin/env python3
"""
hermes.py - the front door. On launch it makes sure the dependencies are present (on first run it
creates a local .venv, installs them with visible progress, and relaunches itself under it), then
shows a short intro and an arrow-key menu. New users just run:  python3 code/hermes.py
"""
import os
import subprocess
import sys

import bootstrap
import paths
from services import ui

INTRO = (
    "\n============================================================\n"
    "  HERMES  -  resume tailoring\n"
    "============================================================\n"
    "  Build ONE factbook of your career, then generate resumes\n"
    "  tailored to each vacancy - facts only, nothing invented.\n\n"
    "    1) Factbook   drop your materials in data/inbox/,\n"
    "                  build one source of truth\n"
    "    2) Template   pick a visual style\n"
    "    3) Tailor     point at a vacancy, tune, export a .docx\n"
    "------------------------------------------------------------"
)


def _setup_check():
    print("\nDependencies:")
    for pkg, mod in bootstrap.REQUIRED:
        print(f"  [{'x' if bootstrap.has(mod) else ' '}] {pkg}")
    print(f"  [{'x' if os.path.exists(paths.ENV) else ' '}] .env  (GEMINI_API_KEY)")
    miss = bootstrap.missing()
    print("\n  " + ("All dependencies present." if not miss else "Missing: " + ", ".join(miss)))


def _run(entry, label):
    argv = sys.argv
    sys.argv = [label]
    try:
        entry()
    except KeyboardInterrupt:
        print("\n(cancelled)")
    except SystemExit as e:
        if e.code not in (0, None):
            print(e.code)
    except Exception as e:  # noqa: BLE001  a tool error must not kill the launcher
        print(f"\n  {label} failed: {e}")
    finally:
        sys.argv = argv


def _launch(name):
    try:
        module = __import__(name)
    except (ImportError, ModuleNotFoundError) as e:
        print(f"\n  '{name}' needs a package that isn't installed ({e.name}).")
        return
    _run(module.main, name)


def _template():
    from templating import build_template
    style = ui.select("Pick a template style", build_template.list_styles())
    build_template.build(style)
    print(f"Built data/template.docx ({style}).")


def _web():
    app_py = os.path.join(paths.ROOT, "code", "app.py")
    print("\nStarting the web UI - it opens in your browser and runs until you stop it.")
    print("Press Ctrl-C here (in this console) when you're done, to come back to this menu.")
    try:
        result = subprocess.run([sys.executable, app_py])
        if result.returncode not in (0, None) and result.returncode != -2:  # -2 = SIGINT (Ctrl-C), fine
            print(f"\n  Web UI exited with an error (code {result.returncode}) - see output above.")
    except KeyboardInterrupt:
        pass


def main():
    bootstrap.ensure()
    print(INTRO)
    if not os.path.exists(os.path.join(paths.DATA, "factbook.md")):
        print("  Fresh setup - start with the Factbook (step 1).")
    print()
    menu = [
        "Open the web UI (browser)",
        "Build the factbook from raw material",
        "Build blocks & positioning from the factbook",
        "Tailor a resume to a vacancy",
        "Build a blank template",
        "Check setup / dependencies",
        "Reset / clean the project",
        "Quit",
    ]
    desc = {
        menu[0]: "the graphical front-end - opens in your browser",
        menu[1]: "reads data/inbox/ -> data/factbook.md",
        menu[2]: "factbook -> blocks.json + block_tracks.json + positioning.json + identity.json",
        menu[3]: "a vacancy -> a tuned resume, exported as .docx",
        menu[4]: "ledger / column / gazette",
        menu[5]: "what's installed, plus the .env key",
        menu[6]: "wipe generated files + inputs, reset data (keeps .env)",
        menu[7]: "exit",
    }
    while True:
        choice = ui.select("What would you like to do?", menu, desc)
        if choice == menu[7]:
            print("Bye.")
            return
        if choice == menu[0]:
            _web()
        elif choice == menu[1]:
            _launch("factbook")
        elif choice == menu[2]:
            _launch("profile")
        elif choice == menu[3]:
            _launch("tailor")
        elif choice == menu[4]:
            _template()
        elif choice == menu[5]:
            _setup_check()
        elif choice == menu[6]:
            _launch("cleanup")
        print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nBye.")
