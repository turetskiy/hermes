# Hermes — resume tailoring

Named for the messenger god who presents your case. Hermes builds **one factbook** of your career
from whatever material you give it, then assembles resumes tailored to each vacancy from that
factbook — facts only, nothing invented. It works from a blank slate: there's no data checked into
this repo, and none of your material or output ever leaves your machine except to call the model.
Hermes is model-agnostic (via LiteLLM) — Gemini by default, but any provider works (see below).

## Quick start

**Easiest:** double-click **`Hermes.command`** (macOS) or **`Hermes.bat`** (Windows) in this folder.
A console window opens (that's the app's server — see "About that console window" below) and your
browser opens to the app.

**From a terminal**, either works the same way:
```
python3 code/app.py        # the web UI (recommended)
python3 code/hermes.py     # a text menu in the console - the reserve UI, same features
```
First run installs everything needed automatically: a local `.venv`, `python-docx`, `litellm`,
`nicegui`, etc. — no manual `pip install` or `venv` setup. It shows progress and takes a minute or two,
once.

### About that console window
The window Hermes opens *is* its local web server — it needs to keep running while you use the app in
your browser. It **shuts itself down automatically once you close the last Hermes tab** (after a
few seconds, so a page refresh doesn't trigger it), so you don't need to remember to stop anything —
just close the tab when you're done, or press Ctrl+C in the console at any time.

## How it works

1. **Factbook** — drop your CVs, notes, project write-ups into the inbox (any mix of
   `.txt/.md/.docx/.pdf/.json/.csv`, or plain text with no extension). Hermes extracts the text and
   asks the model to synthesise one **factbook**: facts only, exact numbers, uncertain items marked
   `[?]`, with a "Gaps / open questions" section — answer any of them right there, and the model
   merges your answers back in.
2. **Profile** — from the factbook, the model extracts achievement **blocks** (tagged by role),
   **skills** clusters, your **roles** (title/dates/company), and your **identity**
   (name/contact/education) — a **track**. Pick an existing track from the dropdown to view/edit it
   (pulls its saved blocks by id, no model call), or build a fresh one.
3. **Tailor** — pick a resume template style and a track, optionally point at a vacancy (a URL, pasted
   text, or leave it blank for a baseline resume), and the model tunes the whole resume to it in one
   pass. Review/edit the result (plain JSON), **Build .docx** and download it, then give feedback to
   refine further — each round re-tunes the content and regenerates the file.

The web UI covers all three steps end-to-end, with a live log + progress bar while the model works.
The console (`python3 code/hermes.py`) runs the exact same underlying pipeline as a reserve UI —
arrow keys to navigate, nothing to install separately, and it doubles as the finer-grained tool for
block-by-block review during Tailor if you want more control than the web UI's "review the whole
result at once" flow.

## Your data lives in `~/Hermes`

Everything Hermes reads or writes — your dropped material, the factbook, blocks/positioning/identity,
generated resumes, logs, and your API key(s) (`.env`) — lives in `~/Hermes`, **outside this project
folder**. That keeps your personal material out of the code repo, safe from getting wiped if the repo
folder is ever reset, and portable if you move/reinstall Hermes itself.

```
~/Hermes/
├── .env                      GEMINI_API_KEY (written by the Setup screen, or by hand)
├── data/
│   ├── inbox/                 drop your material here
│   ├── factbook.md             the synthesised factbook
│   ├── blocks.json · block_tracks.json · positioning.json · identity.json     from Profile
│   └── template.docx · template.meta.json                  the chosen resume template
└── output/                    generated resumes + logs
```

## API key & model (Gemini by default, any provider works)

Hermes calls the model through [LiteLLM](https://docs.litellm.ai/docs/providers), so it isn't tied to
Gemini. The web UI's **Setup** screen has both fields: a **Model** box (any litellm model string -
`gemini/gemini-3.1-pro-preview` by default, or `gpt-4o`, `anthropic/claude-...`, ...) that shows which
`.env` variable its key goes into, and the **API key** box itself. **Test & save** writes both
`LLM_MODEL` and that key to `~/Hermes/.env` and validates them with a minimal call. For the default,
**Get a Gemini key** opens Google AI Studio; for another provider, get a key from its own site instead.
No key is ever sent anywhere but the model provider you chose.

To do it by hand instead, edit `~/Hermes/.env` directly - `LLM_MODEL=...` plus that provider's key
variable (`GEMINI_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, ...; see `.env.example` here for the
format). `python3 code/tailor.py --list-models` prints the currently configured model. No code changes
needed either way.

## Templates (three single-column, ATS-safe styles)
Hermes generates the resume template itself — no file to hand-edit:

- **ledger** — sans body + mono labels/dates, slate-blue accent
- **column** — serif name + sans body, forest-green accent
- **gazette** — serif body, editorial caps kickers, oxblood accent

All three are single-column (ATS-parser friendly) and emit the same placeholder tokens, so any style
works with the same Tailor pipeline. Pick one when Tailor asks, or build one explicitly:
`python3 code/templating/build_template.py gazette`.

## Project layout
```
hermes/
├── Hermes.command · Hermes.bat     double-click launchers (macOS / Windows)
├── code/
│   ├── app.py             web UI entry point (runs the server, idle-shutdown)
│   ├── web/                the web UI, one screen per file
│   │   ├── ui.py             Welcome screen + the shared page chrome (header, footer log/bar)
│   │   ├── setup.py · setup_keypanel.py   Setup screen; provider/model + key-signup panel
│   │   ├── material.py       Material (factbook) screen
│   │   ├── profile.py        Profile screen (profile_store.py below holds its read-side)
│   │   ├── tailor.py · tailor_export.py   Tailor screen; Build/Download/Feedback controls
│   │   ├── progress.py · notify.py       shared log/progress-bar/busy-button + notify helpers
│   │   └── brand.py          header wordmark + inline SVG caduceus
│   ├── profile_store.py    read-side of saved tracks (view/edit), used by web/profile.py & web/tailor.py
│   ├── hermes.py           console entry point (reserve UI) - also launches the web UI
│   ├── bootstrap.py         creates .venv, installs deps, relaunches into it
│   ├── cleanup.py           reset ~/Hermes to a blank state (keeps .env)
│   ├── factbook.py · profile.py · tailor.py     the three pipeline steps
│   ├── paths.py             resolves ~/Hermes (data/output/.env); HERMES_HOME overrides it
│   ├── services/            ui · report · llm · llm_config · llm_providers · vacancy · runlog · osutil
│   ├── content/              tracks · assemble · pipeline (content model + tuning loop)
│   ├── ingest/                extract · collect (read raw files for the factbook)
│   ├── templating/            build_template · tpl_common · tpl_skeleton
│   └── rendering/              fill_template · docx_write · docx_layout
```
Modules import each other by package (`from services.ui import ask`, `from rendering import
fill_template`) and resolve paths through `paths.py`, so any entry point works from the project root.

Progress (model calls, retries, file counts) flows through `services/report.py`, which fans out to
whichever UI is running — console output and/or the web UI's on-page log — from the same core code.
