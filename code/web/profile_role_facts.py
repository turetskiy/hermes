"""Per-role fact checklist for the Roles panel (web/profile_roles.py) - lets the user manually
include/exclude which of a role's OWN facts get built into it. A fact's role is fixed at Propose time
from the factbook's own structure and never reassignable to a different role here - this only toggles
a role-tagged fact between "in" (assign: role) and "out" (assign: exclude)."""


def build_fact_checklist(role_slot, get_track_id):
    """Returns (widget, render(draft)). Call render(draft) any time the role's facts should be
    redrawn - on load, and after a fresh Propose."""
    from nicegui import ui
    from content import profile_drafts

    def render(draft):
        col.clear()
        facts = [f for f in draft.get("facts", []) if f.get("role") == role_slot]
        with col:
            if not facts:
                ui.label("No facts tagged to this role yet - Propose in Selection first.") \
                    .classes("text-sm text-slate-400")
            for f in facts:
                with ui.row().classes("w-full items-center gap-2"):
                    cb = ui.checkbox(value=f.get("assign", "role") == "role")
                    ui.label(f["text"]).classes("text-sm flex-1")

                    def _toggle(e, f=f):
                        f["assign"] = "role" if e.value else "exclude"
                        tid = get_track_id()
                        if tid:
                            profile_drafts.set(tid, draft)

                    cb.on_value_change(_toggle)

    col = ui.column().classes("w-full gap-1")
    return col, render
