"""Inline AI-rewrite popover, shared by two entry points:
- attach_inline_edit(field): the whole field's text is the target - Profile's bullets/labels/summary.
- attach_inline_edit_lines(field): a big multi-line document (the factbook's raw textarea) - clicking a
  bullet line targets just that line, selecting it in place (native text selection = the highlight).

Exactly one popover is ever open across the whole page, and at most one request in flight at a time:
while one is running, no other field's popover can open, and this one's own popover forces itself back
open (at the same field) the moment the request completes - whether it succeeded or failed - even if the
user clicked elsewhere in the meantime. One pending edit at a time, no history beyond that.
"""
from web.notify import notify

HIGHLIGHT = "ring-2 ring-amber-400"

_registry = {"open_close": None, "busy_owner": None}


def _request_open(open_fn, close_fn):
    """Enforce "one popover at a time" and "no new popover while a request is in flight" - close_fn
    doubles as this attachment's identity (stable per instance, since it's a closure)."""
    if _registry["busy_owner"] not in (None, close_fn):
        notify("An edit is already running - wait for it to finish", type="warning")
        return
    if _registry["open_close"] and _registry["open_close"] is not close_fn:
        _registry["open_close"]()
    _registry["open_close"] = close_fn
    open_fn()


def _build_core(get_text, set_text, set_highlight):
    """The shared popover: an always-visible, always-editable instruction box, a Send that rewrites
    from the ORIGINAL text every time (so tweaking the instruction and resending never compounds drift),
    and Accept/Revert once a rewrite exists. Returns (open_popover, close).

    Built as a SIBLING of the target field (in whatever container is ambient when this runs - the
    caller creates the field then calls this immediately after, still inside the same row/column), not
    nested `with field:` - a plain HTML input/textarea's content model is text-only, so trying to nest
    a menu "inside" one confused Quasar's own click-outside detection into treating clicks on the
    popover's own content (e.g. the instruction box) as an outside click, closing it instantly."""
    from nicegui import ui
    from services import cancel, llm, report
    from web.progress import busy

    original = {"text": None}

    with ui.menu().props('no-parent-event anchor="bottom left" self="top left"') as menu:
        with ui.card().classes("gap-1 p-2").style("min-width: 20rem"):
            instruction_in = ui.textarea("Instruction (e.g. 'make it punchier')") \
                .props("rows=1 autogrow dense").classes("w-full")
            with ui.row().classes("gap-1 items-center"):
                send_btn = ui.button("Send", on_click=lambda: _send()).props("dense no-caps size=sm")
                accept_btn = ui.button("Accept", on_click=lambda: _accept()) \
                    .props("dense no-caps size=sm color=positive")
                revert_btn = ui.button("Revert", on_click=lambda: _revert()) \
                    .props("dense no-caps size=sm color=negative")
            accept_btn.set_visibility(False)
            revert_btn.set_visibility(False)

    def close():
        # .run_method (not the .value-toggling .close()) drives Quasar's own show()/hide() directly -
        # setting .value alone could silently no-op if the client's v-model ever drifted out of sync
        # with our last-known state (e.g. after an outside click), leaving a stale server-side "open".
        menu.run_method("hide")

    def _on_hide():
        set_highlight(False)
        if _registry["open_close"] is close:
            _registry["open_close"] = None

    menu.on("hide", _on_hide)

    def open_popover():
        set_highlight(True)
        menu.run_method("show")

    async def _send():
        if not llm.has_key():
            notify("Set your API key in Setup first", type="warning")
            return
        instruction = instruction_in.value.strip()
        if not instruction:
            notify("Type an instruction first", type="warning")
            return
        if original["text"] is None:
            original["text"] = get_text()
        _registry["busy_owner"] = close
        report.step("Rewriting text...")
        async with busy(send_btn, accept_btn, revert_btn, instruction_in):
            try:
                result = await cancel.io_bound(llm.rewrite, original["text"], instruction)
                set_text(result)
                accept_btn.set_visibility(True)
                revert_btn.set_visibility(True)
            except Exception as e:  # noqa: BLE001
                notify(f"Failed: {e}", type="negative")
        _registry["busy_owner"] = None
        # always resurface at the same spot once done, even if the user clicked elsewhere meanwhile
        _registry["open_close"] = close
        open_popover()

    def _accept():
        original["text"] = None
        instruction_in.value = ""
        accept_btn.set_visibility(False)
        revert_btn.set_visibility(False)
        close()

    def _revert():
        if original["text"] is not None:
            set_text(original["text"])
        _accept()

    return open_popover, close


def attach_inline_edit(field):
    """Wire the popover onto field - any ui.input/ui.textarea with a .value. Call this right after
    creating field, still inside its own row/column, so the popover (built as field's sibling - see
    _build_core) ends up anchored right next to it."""

    def set_highlight(on):
        field.classes(add=HIGHLIGHT) if on else field.classes(remove=HIGHLIGHT)

    open_popover, close = _build_core(lambda: field.value, lambda t: setattr(field, "value", t),
                                       set_highlight)
    # "mouseup" - same trigger as attach_inline_edit_lines(), one mechanism for both modes.
    field.on("mouseup", lambda: _request_open(open_popover, close))
