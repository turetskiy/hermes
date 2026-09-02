"""The Material screen: drop files into the inbox, then Build factbook, review/answer its open
questions, add facts one at a time, and save the result. Progress goes to the shared page-level log
(web/ui.py / web/progress.py) via push_line; Build/Apply buttons disable with a spinner while working.
Factbook display defaults to a rendered markdown view; the Edit switch swaps in the raw textarea
(fb_box), which stays the single source of truth throughout - the view is just its rendering, kept in
sync via sync_view() after every write (build, gap answers, or an added fact)."""
import os

import paths
from services import cancel
from web.confirm import build_confirm
from web.material_facts import build_add_fact
from web.material_files import build_file_manager
from web.material_gaps import build_gaps
from web.notify import notify
from web.progress import busy, screen_lock


def material_screen(show, push_line):
    from nicegui import ui
    import factbook
    from services import llm

    inbox = os.path.join(paths.DATA, "inbox")

    confirm = build_confirm()
    # Build / Apply answers / Save / Polish (add-fact) all touch the factbook - none should run while
    # another is mid-flight; register() each, then busy(btn, *others(btn), ...) below locks out the rest.
    register, others = screen_lock()

    with ui.column().classes("gap-3") as scr:
        ui.markdown(f"Drop your CVs / notes / docs below, or straight into `{inbox}`.")
        add_files_btn, upload_ctl = build_file_manager(inbox)
        ui.separator()

        fb_view = ui.markdown().classes("w-full")
        fb_view.set_visibility(False)
        fb_box = ui.textarea("Factbook (Markdown source)").props("rows=18").classes("w-full")
        fb_box.set_visibility(False)
        edit_switch = ui.switch("Edit")
        edit_switch.set_visibility(False)

        def sync_view():
            """Re-render the view from fb_box.value (the single source of truth) and show whichever of
            view/edit is currently selected - call after ANY fb_box.value write."""
            fb_view.set_content(fb_box.value)
            fb_box.set_visibility(edit_switch.value)
            fb_view.set_visibility(not edit_switch.value)

        edit_switch.on_value_change(sync_view)

        def show_factbook():
            edit_switch.set_visibility(True)
            sync_view()

        def hide_factbook():
            fb_box.set_visibility(False)
            fb_view.set_visibility(False)
            edit_switch.set_visibility(False)

        add_fact_col = build_add_fact(fb_box, sync_view, push_line, register, others)
        add_fact_col.set_visibility(False)
        gaps_box, refresh_gaps = build_gaps(fb_box, sync_view, push_line, register, others)

        async def save_fb():
            if os.path.exists(factbook.OUT) and not await confirm(
                    "This overwrites the existing factbook.md - continue?", "Overwrite"):
                return
            async with busy(save_btn, *others(save_btn)):
                factbook.write(fb_box.value)
                notify("Saved to ~/Hermes/data/factbook.md", type="positive")

        async def build_fb():
            if not llm.has_key():
                notify("Set your API key in Setup first", type="warning")
                return
            hide_factbook()
            add_fact_col.set_visibility(False)
            save_btn.set_visibility(False)
            gaps_box.set_visibility(False)
            push_line("Building factbook from the inbox...")
            async with busy(build_btn, *others(build_btn), add_files_btn, upload_ctl):
                try:
                    fb_box.value = await cancel.io_bound(factbook.build, inbox)
                    show_factbook()
                    add_fact_col.set_visibility(True)
                    save_btn.set_visibility(True)
                    refresh_gaps()
                    notify("Factbook ready - review & Save", type="positive")
                except Exception as e:  # noqa: BLE001
                    push_line(f"! {e}")
                    notify(f"Failed: {e}", type="negative")

        with ui.row():
            build_btn = register(ui.button("Build factbook", on_click=build_fb).props("unelevated color=primary"))
            save_btn = register(ui.button("Save factbook", on_click=save_fb))
        save_btn.set_visibility(False)

        if os.path.exists(factbook.OUT):  # show a factbook from an earlier session, not just a fresh Build
            fb_box.value = open(factbook.OUT).read()
            show_factbook()
            add_fact_col.set_visibility(True)
            save_btn.set_visibility(True)
            refresh_gaps()

        with ui.row():
            ui.button("Back", on_click=lambda: show(1)).props("flat")
            ui.button("Next", on_click=lambda: show(3))
    return scr
