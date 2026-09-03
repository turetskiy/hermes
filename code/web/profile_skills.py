"""Build panel (Step 2) for skills: a "Build skills" button that clusters whatever facts are currently
tagged 'skills' in the Selection draft into labeled groups, an editable clusters list, and its own
"Save skills" button - independent of every role and identity. Split out of web/profile.py by concern."""
from web.inline_edit import attach_inline_edit
from web.notify import notify
from web.progress import busy


def build_skills_panel(get_track_id, push_line, register, others, on_saved=None):
    from nicegui import ui
    import profile
    import profile_store
    from content import profile_drafts
    from services import cancel

    state = {"clusters": []}  # [{"label", "items"}]

    def _render():
        rows_col.clear()
        with rows_col:
            if not state["clusters"]:
                ui.label("No skills built yet.").classes("text-sm text-slate-400")
            for i, c in enumerate(state["clusters"]):
                with ui.row().classes("w-full items-start gap-2"):
                    label_in = ui.input(value=c.get("label", "")).props("dense").classes("w-48")
                    items_in = ui.input(value=c.get("items", "")).props("dense").classes("flex-1")
                    attach_inline_edit(label_in)
                    attach_inline_edit(items_in)

                    def _edit_label(e, i=i):
                        state["clusters"][i]["label"] = e.value

                    def _edit_items(e, i=i):
                        state["clusters"][i]["items"] = e.value

                    label_in.on_value_change(_edit_label)
                    items_in.on_value_change(_edit_items)

                    def _remove(i=i):
                        state["clusters"].pop(i)
                        _render()

                    ui.button(icon="close", on_click=_remove).props("flat dense round")

    def _update_header():
        n = len(state["clusters"])
        panel._props["caption"] = f"{n} cluster{'s' if n != 1 else ''}" if n else "not built yet"
        panel.update()

    async def build():
        tid = get_track_id()
        if not tid:
            notify("Track id can't be empty", type="warning")
            return
        draft = profile_drafts.get(tid)
        if not draft:
            notify("Propose a selection first (Step 1)", type="warning")
            return
        push_line("Building skills clusters...")
        async with busy(build_btn, *others(build_btn)):
            try:
                state["clusters"] = await cancel.io_bound(profile.build_skills, draft)
                _render()
                _update_header()
                notify(f"{len(state['clusters'])} skill clusters built - review & Save", type="positive")
            except Exception as e:  # noqa: BLE001
                push_line(f"! {e}")
                notify(f"Failed: {e}", type="negative")

    async def save():
        tid = get_track_id()
        if not tid:
            notify("Track id can't be empty", type="warning")
            return
        async with busy(save_btn, *others(save_btn)):
            profile.write_skills(tid, state["clusters"])
            push_line(f"Saved skills: {len(state['clusters'])} clusters")
            notify("Skills saved", type="positive")
            _update_header()
            if on_saved:
                on_saved()

    def load(track_id):
        state["clusters"] = profile_store.load_skills(track_id) if track_id else []
        _render()
        panel.value = not state["clusters"]  # expanded (needs attention) if nothing's built yet
        _update_header()

    with ui.expansion("Skills").classes("w-full") as panel:
        with ui.row().classes("w-full items-center gap-2"):
            build_btn = register(ui.button("Build skills", on_click=build).props("outline"))
            save_btn = register(ui.button("Save skills", on_click=save))
        rows_col = ui.column().classes("w-full gap-1")
        _render()

    return panel, load
