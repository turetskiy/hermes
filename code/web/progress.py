"""Shared live-progress log + bar + a "busy" button helper. The log is built ONCE by web/ui.py
(pinned to the page footer) and its sink stays attached for the whole page session, so ANY report.*
call from anywhere in the app shows up here automatically - no per-action add_sink/remove_sink
bookkeeping. The progress bar is one shared element too (module-level state - this app is single-user/
single-session, matching services/report.py's own singleton), so any screen's busy() lights the same
bar without each screen needing its own."""
import asyncio
import time
from contextlib import asynccontextmanager

_state = {"bar": None, "busy_count": 0}
MIN_BUSY_SECONDS = 0.7  # let one indeterminate animation cycle finish, so a fast call doesn't look glitchy


def init_bar():
    """Build the shared indeterminate progress bar (called once, in web/ui.py's footer)."""
    from nicegui import ui
    bar = ui.linear_progress(value=0).props("indeterminate").classes("w-full")
    bar.set_visibility(False)
    _state["bar"] = bar
    return bar


class UiSink:  # buffered; a ui.timer drains it into the log (safe from the report-calling thread)
    def __init__(self):
        self.buf = []

    def info(self, m):
        self.buf.append(m)
    step = info

    def warn(self, m):
        self.buf.append("! " + m)


def progress_log():
    """Build the log widget; return (push_line, sink, timer). Caller wires report.add_sink(sink) once
    and starts the timer once, for the page's lifetime (see web/ui.py)."""
    from nicegui import ui

    with ui.scroll_area().classes(
        "w-full h-36 rounded-lg border border-slate-700"
    ).style("background: #1a2233") as log_area:
        log_col = ui.column().classes("gap-0.5 p-2 w-full")

    def push_line(text):
        warn = text.startswith("! ")
        color = "text-amber-400" if warn else "text-slate-300"
        with log_col:
            ui.label(text).classes(f"font-mono text-xs {color} whitespace-pre-wrap break-words")
        log_area.scroll_to(percent=1.0)

    sink = UiSink()
    timer = ui.timer(0.1, lambda: [push_line(sink.buf.pop(0)) for _ in range(len(sink.buf))])

    return push_line, sink, timer


@asynccontextmanager
async def busy(button):
    """Disable a button, show its built-in spinner, AND light the shared progress bar while the
    wrapped work runs - so it can't be double-clicked and it's unmistakable something is happening.
    Stays up for at least MIN_BUSY_SECONDS even if the work finishes sooner, so a fast response
    doesn't cut the indeterminate bar's animation off mid-cycle (which reads as a glitch, not motion).
    Nests safely (busy_count) in case two operations ever overlap."""
    button.disable()
    button.props("loading")
    _state["busy_count"] += 1
    if _state["bar"]:
        _state["bar"].set_visibility(True)
    started = time.monotonic()
    try:
        yield
    finally:
        remaining = MIN_BUSY_SECONDS - (time.monotonic() - started)
        if remaining > 0:
            await asyncio.sleep(remaining)
        _state["busy_count"] -= 1
        if _state["bar"] and _state["busy_count"] <= 0:
            _state["bar"].set_visibility(False)
        button.props(remove="loading")
        button.enable()
