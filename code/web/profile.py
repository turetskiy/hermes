"""The Profile screen: build/edit a track's identity, roles (with their bullets), and skills - as
separate, independently buildable/saveable entities. Step 1 ("Selection") tags every factbook fact
with a proposed role/skills/etc. assignment; Step 2 ("Build") polishes one entity at a time from its
currently-tagged facts. Pick an existing track from the dropdown to load it (no model call), or type a
new track id and Propose. `page_state` is the same dict web/tailor.py stashes its track dropdown in,
so "Next" can carry the chosen track over."""
from web.confirm import build_confirm
from web.notify import notify
from web.profile_identity import build_identity_panel
from web.profile_roles import build_roles_panel
from web.profile_select import build_select_panel
from web.profile_skills import build_skills_panel
from web.progress import busy, screen_lock

NEW_TRACK = ""  # sentinel value in the dropdown for "start a new track" (never a real track id)


def _track_options():
    import profile_store
    return {NEW_TRACK: "(new track)", **profile_store.track_picker_options()}


def profile_screen(show, push_line, page_state):
    from nicegui import ui
    import profile
    import profile_store

    with ui.column().classes("gap-3") as scr:
        ui.markdown("Turn the factbook into **identity**, **roles** (with their bullets), and "
                    "**skills** - the data Tailor assembles resumes from. Propose tags for every "
                    "factbook fact below, review/adjust them, then Build and Save each entity - "
                    "independently, any time.")

        # Everything here touches the same track's files - none should run while another is mid-flight;
        # register() each button, busy(btn, *others(btn), ...) below locks out the rest.
        register, others = screen_lock()

        with ui.row().classes("w-full items-end gap-2"):
            track_select = ui.select(_track_options(), label="Existing tracks", value=NEW_TRACK) \
                .classes("flex-1 min-w-0")
            delete_btn = register(ui.button(icon="delete", on_click=lambda: delete_selected_track())
                                   .props("flat round dense color=negative").tooltip("Delete this track"))
            delete_btn.set_visibility(False)

        confirm = build_confirm()
        track_in = ui.input("Track id (snake_case)", value="base").classes("w-full")

        def get_track_id():
            return track_in.value.strip()

        def sync_next_enabled():
            has_track = bool(track_select.value)
            next_btn.enable() if has_track else next_btn.disable()
            delete_btn.set_visibility(has_track)

        def refresh_after_save():
            # a Save may have just created/updated a track that isn't in the dropdown's options yet -
            # keep it selected so Next stays wired to what's actually on disk.
            tid = get_track_id()
            opts = _track_options()
            track_select.set_options(opts, value=tid if tid in opts else track_select.value)
            sync_next_enabled()

        ui.separator()
        select_panel, load_select = build_select_panel(
            get_track_id, push_line, register, others, on_proposed=lambda: reload_all(get_track_id()))
        ui.separator()
        identity_panel, load_identity = build_identity_panel(
            get_track_id, push_line, register, others, on_saved=refresh_after_save)
        ui.separator()
        roles_panel, load_roles = build_roles_panel(
            get_track_id, push_line, register, others, on_saved=refresh_after_save)
        ui.separator()
        skills_panel, load_skills = build_skills_panel(
            get_track_id, push_line, register, others, on_saved=refresh_after_save)

        def reload_all(track_id):
            load_select(track_id)
            load_identity(track_id)
            load_roles(track_id)
            load_skills(track_id)

        def load_selected_track(e):
            track_id = e.value
            sync_next_enabled()
            if not track_id:
                # "(new track)" - track_in is left alone (a user mid-typing a new id shouldn't have it
                # wiped), but every panel resets to its empty state.
                reload_all(None)
                return
            track_in.value = track_id
            reload_all(track_id)
            push_line(f"Loaded track '{track_id}' for review/edit.")

        track_select.on_value_change(load_selected_track)
        reload_all(None)

        async def delete_selected_track():
            track_id = track_select.value
            if not track_id:
                return
            if not await confirm(f"Delete track '{track_id}'? Its saved blocks stay in the pool, "
                                  "just unassigned - nothing here deletes a block.", "Delete"):
                return
            async with busy(delete_btn, *others(delete_btn), track_select):
                profile.delete_track(track_id)
                track_select.set_options(_track_options(), value=NEW_TRACK)
                track_in.value = "base"
                reload_all(None)
                sync_next_enabled()
                tailor_select = page_state.get("tailor_track_select")
                if tailor_select:  # auto-clears if it was pointing at the track we just deleted
                    tailor_select.set_options(profile_store.track_picker_options())
                push_line(f"Deleted track '{track_id}' (its blocks remain in the pool, unassigned).")
                notify(f"Deleted track '{track_id}'", type="positive")

        def go_next():
            tid = track_select.value
            tailor_select = page_state.get("tailor_track_select")
            if tailor_select and tid:
                opts = profile_store.track_picker_options()
                tailor_select.set_options(opts, value=tid if tid in opts else None)
            show(4)

        with ui.row():
            ui.button("Back", on_click=lambda: show(2)).props("flat")
            next_btn = ui.button("Next", on_click=go_next)
        next_btn.disable()  # nothing selected yet
    return scr
