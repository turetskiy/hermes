"""The Profile screen: turn the factbook into blocks (achievement bullets), skills, roles, and
identity - the data Tailor assembles resumes from. Pick an existing track to view/edit it (pulls its
blocks by id, no model call), or Build a fresh one from the factbook. Progress goes to the shared
page-level log (web/ui.py); Build/Save buttons disable with a spinner while working. `page_state` is
the same dict web/tailor.py stashes its track dropdown in, so "Next" can carry the chosen track over."""
import json

from web.confirm import build_confirm
from web.notify import notify
from web.profile_build import build_profile_button
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
        ui.markdown("Turn the factbook into **blocks** (achievement bullets), **skills**, **roles**, "
                    "and your **identity** - the data Tailor assembles resumes from. Review the result "
                    "below (it's plain JSON, editable) before saving.")

        # Build / Save / Delete all touch the same track's files - none should run while another is
        # mid-flight; register() each, then busy(btn, *others(btn), ...) below locks out the rest.
        register, others = screen_lock()

        with ui.row().classes("w-full items-end gap-2"):
            track_select = ui.select(_track_options(), label="Existing tracks", value=NEW_TRACK) \
                .classes("flex-1 min-w-0")
            delete_btn = register(ui.button(icon="delete", on_click=lambda: delete_selected_track())
                                   .props("flat round dense color=negative").tooltip("Delete this track"))
            delete_btn.set_visibility(False)

        confirm = build_confirm()

        with ui.row().classes("w-full gap-3"):
            track_in = ui.input("Track id (snake_case)", value="base").classes("flex-1")
            label_in = ui.input("Label for this track (e.g. the target role)").classes("flex-1")

        result_box = ui.codemirror(language="JSON", line_wrapping=True) \
            .classes("w-full overflow-x-auto").style("height: 20rem")
        result_box.set_visibility(False)

        def sync_next_enabled():
            # Next/Delete only make sense once a real, already-saved track is selected - "(new track)"
            # or a freshly-built-but-unsaved result don't count. Delete is hidden outright rather than
            # just disabled when there's nothing to delete - a greyed-out trash icon next to an empty
            # picker reads as broken, not as "not applicable yet".
            has_track = bool(track_select.value)
            next_btn.enable() if has_track else next_btn.disable()
            delete_btn.set_visibility(has_track)

        def load_selected_track(e):
            track_id = e.value
            sync_next_enabled()
            if not track_id:
                return  # "(new track)" - leave whatever is in the fields alone
            try:
                data = profile_store.load_track(track_id)
            except KeyError as e2:
                notify(str(e2), type="negative")
                return
            track_in.value = track_id
            label_in.value = dict(profile_store.list_tracks()).get(track_id, track_id)
            result_box.value = json.dumps(data, ensure_ascii=False, indent=2)
            result_box.set_visibility(True)
            save_btn.set_visibility(True)
            push_line(f"Loaded existing track '{track_id}' for review/edit ({len(data['blocks'])} blocks).")

        track_select.on_value_change(load_selected_track)

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
                track_in.value, label_in.value = "base", ""
                result_box.set_visibility(False)
                save_btn.set_visibility(False)
                sync_next_enabled()
                tailor_select = page_state.get("tailor_track_select")
                if tailor_select:  # auto-clears if it was pointing at the track we just deleted
                    tailor_select.set_options(profile_store.track_picker_options())
                push_line(f"Deleted track '{track_id}' (its blocks remain in the pool, unassigned).")
                notify(f"Deleted track '{track_id}'", type="positive")

        async def save_profile():
            try:
                data = json.loads(result_box.value)
            except ValueError as e:
                notify(f"Not valid JSON: {e}", type="negative")
                return
            track_id = track_in.value.strip()
            if not track_id:
                notify("Track id can't be empty", type="warning")
                return
            if track_id in dict(profile_store.list_tracks()) and not await confirm(
                    f"Track '{track_id}' already exists - overwrite it?", "Overwrite"):
                return
            async with busy(save_btn, *others(save_btn), track_select, track_in, label_in):
                label = label_in.value.strip() or data.get("roles", {}).get("role1", {}).get("title", "Resume")
                n = profile.write_profile(data, track_id, label)
                track_select.set_options(_track_options(), value=track_id)
                sync_next_enabled()  # explicit - don't rely on the value-set above firing on_value_change
                push_line(f"Saved profile: identity.json, blocks.json ({n} blocks), "
                          f"positioning.json (track '{track_id}')")
                notify(f"Saved ({n} blocks, track '{track_id}')", type="positive")

        save_btn = register(ui.button("Save profile", on_click=save_profile))
        save_btn.set_visibility(False)

        build_profile_button(push_line, result_box, save_btn, label_in, register, others,
                              [track_select, track_in, label_in, delete_btn])

        def go_next():
            # track_select.value is always a real, already-saved track here - Next is disabled otherwise
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
