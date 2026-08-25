"""The provider key panel on the Setup screen: name, a real signup link (per llm_providers.py, hand-
checked - never a guessed URL), a free/trial/paid/local tier badge, and the note explaining what that
tier actually gets you. One click handler installed once (reading from a mutable ref) rather than
re-registered per provider switch, which would otherwise stack duplicate handlers."""
import webbrowser

_TIER_COLOR = {"free": "text-positive", "trial": "text-warning", "paid": "text-grey-6",
               "local": "text-info", "unclear": "text-grey-6", "unknown": "text-grey-6"}


def build_key_panel():
    """Builds the panel's widgets and returns sync(provider) to refresh them for a given provider."""
    from nicegui import ui
    from services import llm

    active_url = {"url": None}

    with ui.column().classes("w-full gap-1 p-3 rounded bg-grey-2"):
        with ui.row().classes("items-center gap-2"):
            name_lbl = ui.label().classes("font-bold")
            tier_lbl = ui.label().classes("text-xs px-2 py-0.5 rounded bg-white")
        key_btn = ui.button("Get a key", on_click=lambda: (
            webbrowser.open(active_url["url"]) if active_url["url"] else None)).props("outline dense")
        note_lbl = ui.label().classes("text-xs text-grey-8 whitespace-pre-wrap")

    def sync(provider):
        ki = llm.key_info(provider)
        name_lbl.set_text(ki["name"] or provider)
        tier_lbl.set_text(ki["tier"])
        tier_lbl.classes(replace="text-xs px-2 py-0.5 rounded bg-white " + _TIER_COLOR.get(ki["tier"], ""))
        note_lbl.set_text(ki["note"])
        active_url["url"] = ki["key_url"]
        if ki["key_url"]:
            key_btn.set_text(f"Get a {ki['name']} key")
            key_btn.enable()
            key_btn.set_visibility(True)
        elif ki["tier"] == "local":
            key_btn.set_text("No signup needed - runs locally")
            key_btn.disable()
            key_btn.set_visibility(True)
        else:
            key_btn.set_visibility(False)  # unlisted provider - nothing to link to

    return sync
