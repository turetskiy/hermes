"""Shared live-progress log + bar + a "busy" button helper. The log is built ONCE by web/ui.py
(pinned to the page footer) and its sink stays attached for the whole page session, so ANY report.*
call from anywhere in the app shows up here automatically - no per-action add_sink/remove_sink
bookkeeping. The progress bar is one shared element too (module-level state - this app is single-user/
single-session, matching services/report.py's own singleton), so any screen's busy() lights the same
bar without each screen needing its own."""
import asyncio
import time
from contextlib import asynccontextmanager

from services import cancel
from web.screen_lock import screen_lock  # noqa: F401  re-exported - existing `from web.progress import
# busy, screen_lock` call sites keep working; this module owns the shared busy()/log/stop machinery,
# screen_lock.py owns the separate per-screen mutual-exclusion registry concern.

_state = {"bar": None, "busy_count": 0, "stop_btn": None, "current_task": None}
MIN_BUSY_SECONDS = 0.7  # let one indeterminate animation cycle finish, so a fast call doesn't look glitchy


def init_bar():
    """Build the shared indeterminate progress bar + its Stop button (called once, in web/ui.py's
    footer). One handler installed once (reads current_task from _state) rather than re-registered
    per busy() call, which would otherwise stack duplicate handlers - same fix as web/setup_keypanel.py.
    Sets services.cancel's flag - see that module for why task.cancel() alone can't actually interrupt
    a run.io_bound() call already in progress."""
    from nicegui import ui
    from web.notify import notify

    def stop_current():
        cancel.request()
        notify("Stopping (finishing the current step)...", type="warning")
        task = _state.get("current_task")
        if task and not task.done():
            task.cancel()

    with ui.row().classes("w-full items-center gap-2"):
        bar = ui.linear_progress(value=0).props("indeterminate").classes("flex-1 min-w-0")
        stop_btn = ui.button("Stop", icon="stop", on_click=stop_current).props("dense outline color=negative")
    bar.set_visibility(False)
    stop_btn.set_visibility(False)
    _state["bar"] = bar
    _state["stop_btn"] = stop_btn
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
        try:
            with log_col:
                ui.label(text).classes(f"font-mono text-xs {color} whitespace-pre-wrap break-words")
            log_area.scroll_to(percent=1.0)
        except RuntimeError:
            pass  # the browser tab (or its client) is already gone - nothing left to log to

    sink = UiSink()
    timer = ui.timer(0.1, lambda: [push_line(sink.buf.pop(0)) for _ in range(len(sink.buf))])

    return push_line, sink, timer


def _safe(widget, method):
    """Best-effort .disable()/.enable() - a widget passed to freeze can be a dynamically-recreated
    one (e.g. Material's per-refresh "Apply answers" button) that's since been torn down; a stale
    reference must not crash the whole busy() block over a widget nobody can see anymore anyway."""
    try:
        getattr(widget, method)()
    except RuntimeError:
        pass


@asynccontextmanager
async def busy(button, *freeze):
    """Disable a button, show its built-in spinner, AND light the shared progress bar + Stop button
    while the wrapped work runs - so it can't be double-clicked and it's unmistakable something is
    happening. `freeze` is any other widgets that must not be touched meanwhile either - a sibling
    action button that could race this one (see screen_lock()), or a field this operation reads only
    partway through rather than just at the start, so editing it mid-flight can't produce a mismatch
    between what's shown and what's actually used. Stays up for at least MIN_BUSY_SECONDS even if the
    work finishes sooner, so a fast response doesn't cut the indeterminate bar's animation off mid-
    cycle. Nests safely (busy_count) in case two operations ever overlap. Stop sets services.cancel's
    flag (checked inside services.llm/content.pipeline) and cancels the awaiting task - the latter
    alone can't interrupt a run.io_bound() call already running, so it mainly helps this function's own
    trailing sleep below. A caller with its own extra behavior on cancellation (e.g. web/tailor.py
    navigating back a step) should catch cancel.Cancelled itself, inside the `yield`; this is the
    fallback for every caller that doesn't - cancelling still ends cleanly instead of a bare traceback,
    just without anything beyond the generic "Cancelled" this reports."""
    cancel.clear()
    _safe(button, "disable")
    button.props("loading")
    for w in freeze:
        _safe(w, "disable")
    _state["busy_count"] += 1
    _state["current_task"] = asyncio.current_task()
    if _state["bar"]:
        _state["bar"].set_visibility(True)
    if _state["stop_btn"]:
        _state["stop_btn"].set_visibility(True)
    started = time.monotonic()
    cancelled = False
    try:
        yield
    except (asyncio.CancelledError, cancel.Cancelled):
        cancelled = True
    finally:
        remaining = MIN_BUSY_SECONDS - (time.monotonic() - started)
        if remaining > 0 and not cancelled:
            await asyncio.sleep(remaining)
        _state["busy_count"] -= 1
        if _state["busy_count"] <= 0:
            if _state["bar"]:
                _state["bar"].set_visibility(False)
            if _state["stop_btn"]:
                _state["stop_btn"].set_visibility(False)
        _state["current_task"] = None
        button.props(remove="loading")
        _safe(button, "enable")
        for w in freeze:
            _safe(w, "enable")
    if cancelled:
        from services import report
        report.warn("  Cancelled.")
