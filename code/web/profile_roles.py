"""Build panel (Step 2): a role dropdown shows/edits exactly one role at a time - title/dates/
max_bullets, a checklist of that role's OWN facts (never another role's - a fact's role is fixed by
where it lives in the factbook) to manually include/exclude, a "Build bullets" button that polishes
whatever's currently checked, an editable bullet list, and its own "Save role" button - independent of
every other role, skills, and identity. Split out of web/profile.py by concern; supersedes the old
profile_build.py/profile_bullets.py."""
from web.inline_edit import attach_inline_edit
from web.notify import notify
from web.profile_role_facts import build_fact_checklist
from web.progress import busy

ROLE_SLOTS = ("role1", "role2", "role3", "role4")
DEFAULT_MAX_BULLETS = {"role1": 6, "role2": 4, "role3": 3, "role4": 2}


def _build_role_panel(role_slot, get_track_id, push_line, register, others, on_saved=None):
    from nicegui import ui
    import profile
    import profile_store
    from content import profile_drafts
    from services import cancel

    state = {"bullets": [], "draft": {"facts": []}}  # bullets: [{"id", "text"}], draft: this track's Step 1

    def _max_bullets():
        # ui.number can hand back None for a literal 0 (its own _event_args_to_value does
        # `if not e_args: return None`) - 0 is a valid, meaningful value here (excludes the role).
        return int(max_in.value) if max_in.value is not None else 0

    def _update_status():
        n = len(state["bullets"])
        status_lbl.set_text(f"{n} bullet{'s' if n != 1 else ''}" if n else "not built yet")

    def _render():
        rows_col.clear()
        with rows_col:
            if not state["bullets"]:
                ui.label("No bullets built yet.").classes("text-sm text-slate-400")
            for i, b in enumerate(state["bullets"]):
                with ui.row().classes("w-full items-start gap-2"):
                    ta = ui.textarea(value=b["text"]).props("rows=1 autogrow").classes("flex-1")
                    attach_inline_edit(ta)

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
        if not state["draft"].get("facts"):
            notify("Propose a selection first (Step 1)", type="warning")
            return
        push_line(f"Building bullets for {role_slot}...")
        async with busy(build_btn, *others(build_btn)):
            try:
                state["bullets"] = await cancel.io_bound(profile.build_role, state["draft"], role_slot)
                _render()
                _update_status()
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
            _update_status()
            if on_saved:
                on_saved()

    def load(track_id):
        role = profile_store.load_role(track_id, role_slot) if track_id else {}
        state["draft"] = (profile_drafts.get(track_id) if track_id else None) or {"facts": []}
        d_role = state["draft"].get("roles", {}).get(role_slot, {})
        # fall back to the proposed draft's title/dates before anything's ever been Saved for this role
        title_in.value = role.get("title") or d_role.get("title", "")
        dates_in.value = role.get("dates") or d_role.get("dates", "")
        max_in.value = role.get("max_bullets") if isinstance(role.get("max_bullets"), int) \
            else DEFAULT_MAX_BULLETS[role_slot]
        state["bullets"] = role.get("bullets", [])
        _render()
        render_facts(state["draft"])
        _update_status()

    with ui.column().classes("w-full gap-2") as panel:
        with ui.row().classes("w-full items-end gap-2"):
            title_in = ui.input("Title").classes("flex-1")
            dates_in = ui.input("Dates").classes("flex-1")
            max_in = ui.number("Max bullets", value=DEFAULT_MAX_BULLETS[role_slot], min=0, max=30,
                                precision=0).classes("w-32").tooltip(f"0 excludes {role_slot} entirely")
        status_lbl = ui.label().classes("text-sm text-slate-400")
        ui.label("Facts in this role").classes("font-bold text-sm")
        facts_col, render_facts = build_fact_checklist(role_slot, get_track_id)
        with ui.row().classes("gap-2"):
            build_btn = register(ui.button("Build bullets", on_click=build).props("outline"))
            save_btn = register(ui.button("Save role", on_click=save))
        rows_col = ui.column().classes("w-full gap-1")
        title_in.on_value_change(_update_status)

    return panel, load


def build_roles_panel(get_track_id, push_line, register, others, on_saved=None):
    from nicegui import ui

    with ui.column().classes("w-full gap-2") as panel:
        ui.label("2. Build - bullets, per role").classes("font-bold")
        role_select = ui.select({r: r for r in ROLE_SLOTS}, value=ROLE_SLOTS[0]).classes("w-64")
        bodies, loaders = {}, {}
        for r in ROLE_SLOTS:
            body, load = _build_role_panel(r, get_track_id, push_line, register, others, on_saved)
            body.set_visibility(r == role_select.value)
            bodies[r], loaders[r] = body, load

        def _switch(e):
            for r, body in bodies.items():
                body.set_visibility(r == e.value)

        role_select.on_value_change(_switch)

    def load_all(track_id):
        for r in ROLE_SLOTS:
            loaders[r](track_id)

    return panel, load_all
