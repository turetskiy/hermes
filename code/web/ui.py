"""Builds the Hermes web page (called by app.py once nicegui is importable). Screens: Welcome ->
Setup (web/setup.py) -> Material (web/material.py) -> Profile (web/profile.py) -> Tailor
(web/tailor.py) - each split out by concern, visibility controlled explicitly (show(i)). A single log
panel pinned to the page footer (web/progress.py) shows report.* output from anywhere in the app for
the whole session - every screen gets a push_line callback into it instead of building its own."""
import os

import paths
from web.progress import init_bar, progress_log
from web.topbar import build_topbar


def setup():
    """Register the "/" page. Call once, after nicegui is importable (post bootstrap.ensure())."""
    from nicegui import ui
    from services import report
    from web.material import material_screen
    from web.profile import profile_screen
    from web.setup import setup_screen
    from web.tailor import tailor_screen

    @ui.page("/")
    def index():
        with ui.footer(fixed=True).classes("bg-slate-900 px-6 py-2"):
            with ui.column().classes("w-full max-w-3xl mx-auto gap-1"):
                init_bar()
                ui.label("Activity log").classes("text-xs text-slate-400")
                push_line, sink, timer = progress_log()
        report.add_sink(sink)

        def on_client_disconnect():
            report.remove_sink(sink)
            timer.cancel()  # else it keeps polling into a torn-down slot -> "parent slot deleted" error

        ui.context.client.on_disconnect(on_client_disconnect)

        screens = []
        page_state = {}  # cross-screen handoffs, e.g. Profile's "Next" carries its track into Tailor

        def show(i):
            for j, s in enumerate(screens):
                s.set_visibility(j == i)
            sync_active_step(i)

        with ui.column().classes("w-full max-w-3xl mx-auto px-6 py-4 gap-4").style("padding-bottom: 14rem"):
            model_lbl, sync_active_step = build_topbar(show)
            page_state["model_label"] = model_lbl
            screens.append(_welcome(show))
            screens.append(setup_screen(show, push_line, page_state))
            screens.append(material_screen(show, push_line))
            screens.append(profile_screen(show, push_line, page_state))
            screens.append(tailor_screen(show, push_line, page_state))
            show(0)  # Welcome first - explicit, not left to a widget default


def _readme_text():
    path = os.path.join(paths.ROOT, "README.md")
    try:
        return open(path).read()
    except OSError:
        return "Couldn't find README.md."


def _welcome(show):
    from nicegui import ui
    with ui.column().classes("gap-3") as welcome:
        ui.markdown("**Hermes** builds one *factbook* of your career, then tailors resumes "
                    "to each vacancy - facts only, nothing invented.\n\n"
                    "1. **Factbook** - one source of truth  \n"
                    "2. **Profile** - blocks / skills / roles  \n"
                    "3. **Tailor** - vacancy -> `.docx`")
        ui.button("Get started", on_click=lambda: show(1)).props("unelevated color=primary")
        with ui.expansion("Read the full guide (README)", icon="menu_book").classes("w-full"):
            ui.markdown(_readme_text()).classes("text-sm")
    return welcome
