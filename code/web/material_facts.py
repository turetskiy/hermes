"""Add-a-fact controls for the Material screen - a raw note, an optional model "Polish" pass (the
result lands in an editable preview, not committed straight away, so the user can still adjust it),
and two ways to commit into the factbook: as typed, or the polished version. Split out of
web/material.py by concern."""
from web.notify import notify


def build_add_fact(fb_box, sync_view, push_line, register, others):
    """Returns the column widget (caller controls its visibility)."""
    from nicegui import ui
    from services import cancel
    import factbook
    from web.progress import busy

    with ui.column().classes("w-full gap-2") as col:
        ui.label("Add a fact").classes("font-bold")
        raw_in = ui.textarea("New fact (raw notes are fine)").props("rows=3").classes("w-full")
        polished_in = ui.textarea("Polished preview (editable)").props("rows=3").classes("w-full")
        polished_in.set_visibility(False)

        def _commit(text):
            if not text.strip():
                notify("Nothing to add", type="warning")
                return
            fb_box.value = factbook.add_fact(fb_box.value, text)
            sync_view()
            raw_in.value = ""
            polished_in.value = ""
            polished_in.set_visibility(False)
            add_polished_btn.set_visibility(False)
            notify("Added to factbook - Save to persist", type="positive")

        async def polish():
            text = raw_in.value.strip()
            if not text:
                notify("Type a fact first", type="warning")
                return
            async with busy(polish_btn, *others(polish_btn)):
                try:
                    polished_in.value = await cancel.io_bound(factbook.polish_fact, text)
                    polished_in.set_visibility(True)
                    add_polished_btn.set_visibility(True)
                except Exception as e:  # noqa: BLE001
                    push_line(f"! {e}")
                    notify(f"Failed: {e}", type="negative")

        with ui.row():
            polish_btn = register(ui.button("Polish", on_click=polish).props("outline"))
            ui.button("Add raw text", on_click=lambda: _commit(raw_in.value))
            add_polished_btn = ui.button("Add polished version", on_click=lambda: _commit(polished_in.value))
        add_polished_btn.set_visibility(False)

    return col
