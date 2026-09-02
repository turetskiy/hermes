"""Build panel (Step 2), one section per role1-4: title/dates/max_bullets, a "Build bullets" button
that polishes whatever facts are currently assigned to this role in the Selection draft, an editable
bullet list, and its own "Save role" button - independent of every other role, skills, and identity.
Split out of web/profile.py by concern; supersedes the old profile_build.py/profile_bullets.py."""
from web.notify import notify
from web.progress import busy

ROLE_SLOTS = ("role1", "role2", "role3", "role4")
DEFAULT_MAX_BULLETS = {"role1": 6, "role2": 4, "role3": 3, "role4": 2}


def _build_role_panel(role_slot, get_track_id, push_line, register, others, on_saved=None):
    from nicegui import ui
    import profile
    import profile_store
    from content import profile_drafts
    from services import cancel

    state = {"bullets": []}  # [{"id", "text"}], in the order Build produced them

    def _max_bullets():
        # ui.number can hand back None for a literal 0 (its own _event_args_to_value does
        # `if not e_args: return None`) - 0 is a valid, meaningful value here (excludes the role).
        return int(max_in.value) if max_in.value is not None else 0

    def _render():
        rows_col.clear()
        with rows_col:
            if not state["bullets"]:
                ui.label("No bullets built yet.").classes("text-sm text-slate-400")
            for i, b in enumerate(state["bullets"]):
                with ui.row().classes("w-full items-start gap-2"):
                    ta = ui.textarea(value=b["text"]).props("rows=1 autogrow").classes("flex-1")

                    def _edit(e, i=i):
                        state["bullets"][i]["text"] = e.value

                    ta.on_value_change(_edit)

                    def _remove(i=i):
                        state["bullets"].pop(i)
                        _render()

                    ui.button(icon="close", on_click=_remove).props("flat dense round")

    async def build():
        tid = get_track_id()
        if not tid:
            notify("Track id can't be empty", type="warning")
            return
        draft = profile_drafts.get(tid)
        if not draft:
            notify("Propose a selection first (Step 1)", type="warning")
            return
        title_in.value = title_in.value or draft.get("roles", {}).get(role_slot, {}).get("title", "")
        dates_in.value = dates_in.value or draft.get("roles", {}).get(role_slot, {}).get("dates", "")
        push_line(f"Building bullets for {role_slot}...")
        async with busy(build_btn, *others(build_btn)):
            try:
                state["bullets"] = await cancel.io_bound(profile.build_role, draft, role_slot)
                _render()
                notify(f"{role_slot}: {len(state['bullets'])} bullets built - review & Save", type="positive")
            except Exception as e:  # noqa: BLE001
                push_line(f"! {e}")
                notify(f"Failed: {e}", type="negative")

    async def save():
        tid = get_track_id()
        if not tid:
            notify("Track id can't be empty", type="warning")
            return
        async with busy(save_btn, *others(save_btn)):
            n = profile.write_role(tid, role_slot, title_in.value, dates_in.value,
                                    state["bullets"], _max_bullets())
            push_line(f"Saved {role_slot}: {n} bullets, max_bullets={_max_bullets()}")
            notify(f"{role_slot} saved ({n} bullets)", type="positive")
            if on_saved:
                on_saved()

    def load(track_id):
        role = profile_store.load_role(track_id, role_slot) if track_id else {}
        title_in.value = role.get("title", "")
        dates_in.value = role.get("dates", "")
        max_in.value = role.get("max_bullets") if isinstance(role.get("max_bullets"), int) \
            else DEFAULT_MAX_BULLETS[role_slot]
        state["bullets"] = role.get("bullets", [])
        _render()

    with ui.column().classes("w-full gap-1 border rounded p-2") as panel:
        with ui.row().classes("w-full items-end gap-2"):
            ui.label(role_slot).classes("font-bold w-14")
            title_in = ui.input("Title").classes("flex-1")
            dates_in = ui.input("Dates").classes("flex-1")
            max_in = ui.number("Max bullets", value=DEFAULT_MAX_BULLETS[role_slot], min=0, max=30,
                                precision=0).classes("w-32").tooltip(f"0 excludes {role_slot} entirely")
            build_btn = register(ui.button("Build bullets", on_click=build).props("outline"))
            save_btn = register(ui.button("Save role", on_click=save))
        rows_col = ui.column().classes("w-full gap-1")
        _render()

    return panel, load


def build_roles_panel(get_track_id, push_line, register, others, on_saved=None):
    from nicegui import ui

    with ui.column().classes("w-full gap-3") as panel:
        ui.label("2. Build - bullets, per role").classes("font-bold")
        loaders = [_build_role_panel(r, get_track_id, push_line, register, others, on_saved)[1]
                   for r in ROLE_SLOTS]

    def load_all(track_id):
        for load in loaders:
            load(track_id)

    return panel, load_all
