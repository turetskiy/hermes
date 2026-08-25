"""A single reusable Yes/No confirmation dialog - built once per screen, awaited before any
destructive or overwriting action. Cancel resolves False; the (re-labelled per call) confirm button
resolves True. Mirrors web/setup_keypanel.py's build_X() -> callable factory pattern."""


def build_confirm():
    from nicegui import ui

    with ui.dialog() as dialog, ui.card():
        message_lbl = ui.label()
        with ui.row():
            ui.button("Cancel", on_click=lambda: dialog.submit(False)).props("flat")
            confirm_btn = ui.button(on_click=lambda: dialog.submit(True)).props("color=negative")

    async def confirm(message, confirm_text="Confirm"):
        message_lbl.set_text(message)
        confirm_btn.set_text(confirm_text)
        return await dialog

    return confirm
