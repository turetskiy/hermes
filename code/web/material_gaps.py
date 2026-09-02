"""Open-questions review for the Material screen - parse the factbook's gap bullets, let the user
answer any they can, and merge the answers back in via the model. Split out of web/material.py by
concern."""
from web.notify import notify


def build_gaps(fb_box, sync_view, push_line, register, others):
    """Returns (gaps_box, refresh) - call refresh() any time fb_box.value changes wholesale (a fresh
    Build, or a track loaded) so the open-questions list reflects it."""
    from nicegui import ui
    from services import cancel
    import factbook
    from web.progress import busy

    gaps_box = ui.column().classes("w-full gap-2")
    gaps_box.set_visibility(False)

    def refresh():
        gaps_box.clear()
        gaps = factbook.parse_gaps(fb_box.value)
        gaps_box.set_visibility(bool(gaps))
        if not gaps:
            return
        with gaps_box:
            ui.label(f"Open questions ({len(gaps)}) - answer any you can, then Apply:").classes("font-bold")
            fields = []
            for g in gaps:
                # the question is a wrapping label, not the input's floating label (which Quasar
                # truncates to one line instead of wrapping) - the input itself is a plain answer box
                with ui.column().classes("w-full gap-1"):
                    ui.label(g).classes("text-sm whitespace-pre-wrap break-words")
                    inp = ui.input(placeholder="Your answer").classes("w-full")
                fields.append((g, inp))

            async def apply_answers():
                qa = [(g, inp.value.strip()) for g, inp in fields if inp.value.strip()]
                if not qa:
                    notify("Type an answer for at least one question first", type="warning")
                    return
                push_line(f"Applying {len(qa)} answer(s) to the factbook...")
                async with busy(apply_btn, *others(apply_btn)):
                    try:
                        fb_box.value = await cancel.io_bound(factbook.resolve_gaps, fb_box.value, qa)
                        sync_view()
                        refresh()
                        notify("Factbook updated - review & Save", type="positive")
                    except Exception as e:  # noqa: BLE001
                        push_line(f"! {e}")
                        notify(f"Failed: {e}", type="negative")

            apply_btn = register(ui.button("Apply answers", on_click=apply_answers)
                                  .props("unelevated color=primary"))

    return gaps_box, refresh
