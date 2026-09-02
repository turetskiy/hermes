"""Selection panel (Step 1) for the Profile screen: propose a role/skills/speaking/articles/exclude
tag for every atomic factbook fact via the model, then let the user review/adjust each tag - live,
auto-persisted to content/profile_drafts.py, no separate "confirm" step - before anything gets built.
Split out of web/profile.py by concern."""
import os

from web.notify import notify
from web.progress import busy

ASSIGN_OPTIONS = {
    "role1": "Role 1", "role2": "Role 2", "role3": "Role 3", "role4": "Role 4",
    "skills": "Skills", "speaking": "Speaking", "articles": "Articles", "exclude": "Exclude",
}


def build_select_panel(get_track_id, push_line, register, others, on_proposed=None):
    """Returns (panel, load). load(track_id) shows that track's existing draft (or an empty state for
    one that's never been Proposed, including a brand-new "(new track)"). on_proposed(), if given, runs
    after a fresh Propose - so sibling panels (identity/roles/skills) can pick up the new draft's title/
    dates/identity seeds instead of staying blank until the track is reselected."""
    from nicegui import ui
    import factbook
    import profile
    from content import profile_drafts
    from services import cancel, llm

    draft = {"facts": []}

    def _save_draft():
        tid = get_track_id()
        if tid:
            profile_drafts.set(tid, draft)

    def _render():
        rows_col.clear()
        with rows_col:
            facts = draft.get("facts", [])
            if not facts:
                ui.label("No facts proposed yet - click Propose.").classes("text-sm text-slate-400")
            for i, fact in enumerate(facts):
                with ui.row().classes("w-full items-center gap-2"):
                    ui.label(fact.get("text", "")).classes("flex-1 text-sm")
                    sel = ui.select(ASSIGN_OPTIONS, value=fact.get("assign", "exclude")).classes("w-40")

                    def _on_change(e, i=i):
                        draft["facts"][i]["assign"] = e.value
                        _save_draft()

                    sel.on_value_change(_on_change)

    async def propose():
        if not llm.has_key():
            notify("Set your API key in Setup first", type="warning")
            return
        if not os.path.exists(factbook.OUT):
            notify("Build a factbook first (Material step)", type="warning")
            return
        tid = get_track_id()
        if not tid:
            notify("Track id can't be empty", type="warning")
            return
        push_line("Proposing role/skills/etc. tags from the factbook...")
        async with busy(propose_btn, *others(propose_btn)):
            try:
                result = await cancel.io_bound(profile.propose, open(factbook.OUT).read())
                draft.clear()
                draft.update(result)
                _save_draft()
                _render()
                if on_proposed:
                    on_proposed()
                notify("Tags proposed - review below, then Build each entity", type="positive")
            except Exception as e:  # noqa: BLE001
                push_line(f"! {e}")
                notify(f"Failed: {e}", type="negative")

    def load(track_id):
        draft.clear()
        draft.update((profile_drafts.get(track_id) if track_id else None) or {"facts": []})
        _render()

    with ui.column().classes("w-full gap-2") as panel:
        ui.label("1. Selection - which role/skills/etc. does each fact belong to?").classes("font-bold")
        propose_btn = register(ui.button("Propose from factbook", on_click=propose).props("outline"))
        rows_col = ui.column().classes("w-full gap-1")
        _render()

    return panel, load
