"""Selection panel (Step 1) for the Profile screen: propose a role/skills/speaking/articles/exclude
tag for every atomic factbook fact via the model, then let the user review/adjust each tag - live,
auto-persisted to content/profile_drafts.py, no separate "confirm" step - before anything gets built.
Split out of web/profile.py by concern."""
import os

from web.notify import notify
from web.progress import busy

NON_ROLE_OPTIONS = {"skills": "Skills", "speaking": "Speaking", "articles": "Articles", "exclude": "Exclude"}


def _assign_options(fact):
    """A fact's home role (fixed at Propose time from the factbook's own structure) is never one of the
    choices here for a DIFFERENT role - only its own role (if it has one) plus the 4 non-role buckets,
    so a fact can be pulled out of role content but never reassigned across roles."""
    role = fact.get("role")
    return {"role": f"Keep in {role}", **NON_ROLE_OPTIONS} if role else dict(NON_ROLE_OPTIONS)


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
                    role_tag = f"[{fact['role']}] " if fact.get("role") else ""
                    ui.label(role_tag + fact.get("text", "")).classes("flex-1 text-sm")
                    default = "role" if fact.get("role") else "exclude"
                    sel = ui.select(_assign_options(fact), value=fact.get("assign", default)).classes("w-40")

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

    def _built_without_draft_note(track_id):
        """A track can have real, saved content (roles/skills) with no live draft - e.g. seeded some
        other way, or its draft was never re-Proposed after being built. Surface that here so an empty
        Selection list doesn't read as "this track is broken/incomplete" when it's actually fine."""
        import profile_store
        parts = [f"{r}: {n}" for r in ("role1", "role2", "role3", "role4")
                 if (n := len(profile_store.load_role(track_id, r).get("bullets", [])))]
        if profile_store.load_skills(track_id):
            parts.append(f"skills: {len(profile_store.load_skills(track_id))} clusters")
        return f"Already built without a live draft - {', '.join(parts)}" if parts else ""

    def load(track_id):
        draft.clear()
        draft.update((profile_drafts.get(track_id) if track_id else None) or {"facts": []})
        _render()
        caption = "" if draft.get("facts") else (_built_without_draft_note(track_id) if track_id else "")
        panel._props["caption"] = caption
        panel.update()

    with ui.expansion("1. Selection - which role/skills/etc. does each fact belong to?", value=True) \
            .classes("w-full") as panel:
        propose_btn = register(ui.button("Propose from factbook", on_click=propose).props("outline"))
        rows_col = ui.column().classes("w-full gap-1 q-mt-sm")
        _render()

    return panel, load
