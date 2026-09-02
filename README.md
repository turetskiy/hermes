# Hermes — resume tailoring

Named for the messenger god who presents your case. Hermes builds **one factbook** of your career
from whatever material you give it, then assembles resumes tailored to each vacancy from that
factbook — facts only, nothing invented. It works from a blank slate: there's no data checked into
this repo, and none of your material or output ever leaves your machine except to call the model.
Hermes is model-agnostic (via LiteLLM) — Gemini by default, but any provider works (see below).

## Quick start

**Easiest:** double-click **`Hermes.command`** (macOS), **`Hermes.bat`** (Windows), or **`Hermes.sh`**
(Linux - may need "Allow executing as program" in your file manager first, or run `./Hermes.sh`) in
this folder.
A console window opens (that's the app's server — see "About that console window" below) and your
browser opens to the app.

**From a terminal:**
```
python3 code/app.py
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
   asks the model to synthesise one **factbook**: facts only, exact numbers, one atomic claim per
   bullet, uncertain items marked `[?]`, with a "Gaps / open questions" section — answer any of them
   right there, and the model merges your answers back in. You can also add a fact yourself at any
   time - type it, optionally hit **Polish** to have the model turn it into clean atomic bullets (you
   can still edit that preview before committing), then add it. The factbook shows as rendered
   markdown by default; an **Edit** switch reveals the raw text for direct editing.
2. **Profile** — turning the factbook into a **track** (identity + roles + skills) happens in two
   steps. **Selection**: **Propose** tags every atomic factbook fact with which role (or skills /
   speaking / articles / exclude) it belongs to - the model's best guess, which you then review and
   adjust per fact. **Build**: independently for each role, and separately for skills, turn that
   entity's currently-tagged facts into polished resume bullets / skill clusters - each with its own
   Build and Save, so rebuilding role3 never touches role1, skills, or identity. Each role's bullet
   count is a plain number you set directly (0 excludes that role from the resume entirely) - there's
   no template limit to work around. Pick an existing track from the dropdown to load and keep editing
   it (no model call needed unless you click Build again), or type a new track id and Propose.
3. **Tailor** — pick a resume template style and a track, optionally point at a vacancy (a URL, pasted
   text, or leave it blank for a baseline resume), and the model tunes the whole resume to it in one
   pass. Review/edit the result (plain JSON), **Build .docx** and download it, then give feedback to
   refine further — each round re-tunes the content and regenerates the file.

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
│   ├── profile_drafts.json     Profile's Step 1 ("Selection") scratch state - fact tagging, per track
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
format). The Setup screen's top bar always shows the currently active model. No code changes needed
either way.

## Templates (three built-in styles, or bring your own)
Hermes generates the resume template itself — no file to hand-edit:

- **ledger** — sans body + mono labels/dates, slate-blue accent
- **column** — serif name + sans body, forest-green accent
- **gazette** — serif body, editorial caps kickers, oxblood accent

All three are single-column (ATS-parser friendly) and emit the same placeholder tokens, so any style
works with the same Tailor pipeline. Pick one when Tailor asks, or build one explicitly:
`python3 code/templating/build_template.py gazette`.

You can also use your own `.docx` as a template: mark it up with the same placeholder tokens (see
`templating/tpl_skeleton.py`'s docstring for the full list - one `{{ROLEn_B1}}` anchor per role is
enough, it expands to however many bullets that role has) and drop it into `~/Hermes/data/` (plus an
optional `<name>.meta.json` sidecar for fonts/colors). It shows up in the Tailor screen's style
dropdown automatically. Keep personal data as tokens too, not typed-in text - Hermes fills
name/contact/company/education from `identity.json` itself, the same way for every template.

## Project layout
```
hermes/
├── Hermes.command · Hermes.bat · Hermes.sh     double-click launchers (macOS / Windows / Linux)
├── code/
│   ├── app.py             web UI entry point (runs the server, idle-shutdown)
│   ├── web/                the web UI, one screen per file (each split into a few small modules
│   │   │                    by concern - e.g. material_facts.py/material_gaps.py for Material,
│   │   │                    tailor_export.py/tailor_track_cache.py for Tailor)
│   │   ├── ui.py             Welcome screen + the shared page chrome (header, footer log/bar)
│   │   ├── topbar.py         persistent top bar: active model + wizard breadcrumb
│   │   ├── setup.py · setup_keypanel.py   Setup screen; provider/model + key-signup panel
│   │   ├── material.py · material_facts.py · material_gaps.py   Material (factbook) screen
│   │   ├── profile.py            Profile screen shell (track picker, wires the panels below)
│   │   ├── profile_select.py     Step 1 "Selection" panel - propose + review fact tagging
│   │   ├── profile_identity.py · profile_roles.py · profile_skills.py   Step 2 "Build" panels,
│   │   │                          one per entity - each independently Build- and Save-able
│   │   ├── tailor.py · tailor_export.py · tailor_track_cache.py   Tailor screen
│   │   ├── progress.py · screen_lock.py · notify.py   shared busy-button/log/progress-bar + notify
│   │   └── brand.py          header wordmark + inline SVG caduceus
│   ├── profile_store.py    read-side of saved tracks (per entity), used by web/profile*.py & web/tailor.py
│   ├── profile_write.py     write-side: persists one entity (identity/role/skills/speaking+articles)
│   │                         at a time into the data files below
│   ├── bootstrap.py         creates .venv, installs deps, relaunches into it
│   ├── factbook.py · profile.py     the two extraction steps (tailoring itself lives in
│   │                                content/pipeline.py + web/tailor.py)
│   ├── paths.py             resolves ~/Hermes (data/output/.env); HERMES_HOME overrides it
│   ├── services/            cancel · report · llm · llm_config · llm_providers · vacancy · runlog · osutil
│   ├── content/              assemble · pipeline · block_tracks · profile_drafts (content model +
│   │                          tuning loop; profile_drafts is Profile's Step 1 scratch state)
│   ├── ingest/                extract · collect (read raw files for the factbook)
│   ├── templating/            build_template · custom_templates · tpl_common · tpl_skeleton
│   └── rendering/              fill_template · docx_write · docx_expand · docx_fixed · docx_layout
```
Modules import each other by package (`from content import assemble`, `from rendering import
fill_template`) and resolve paths through `paths.py`, so any entry point works from the project root.

Progress (model calls, retries, file counts) flows through `services/report.py`, which fans out to
both the web UI's on-page log and the terminal window running `app.py`, from the same core code.

## Commit messages

This project follows [Conventional Commits](https://www.conventionalcommits.org/): `type(scope):
description`, e.g. `feat(profile): add per-role bullet rebuild` or `fix(tailor): stop losing cached
content on track switch`. Common types: `feat`, `fix`, `refactor`, `docs`, `chore`. Append `!` after
the type/scope (e.g. `feat(profile)!:`) or add a `BREAKING CHANGE:` footer for a change that isn't
backward compatible.
