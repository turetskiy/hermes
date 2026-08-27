"""The Material screen: drop files into the inbox, then Build factbook, review/answer its open
questions, and save the result. Progress goes to the shared page-level log (web/ui.py /
web/progress.py) via push_line; Build/Apply buttons disable with a spinner while working."""
import os

import paths
from web.confirm import build_confirm
from web.material_files import build_file_manager
from web.notify import notify
from web.progress import busy, screen_lock


def material_screen(show, push_line):
    from nicegui import ui, run
    import factbook
    from services import llm

    inbox = os.path.join(paths.DATA, "inbox")

    confirm = build_confirm()
    # Build / Apply answers / Save all touch the factbook - none should run while another is
    # mid-flight; register() each, then busy(btn, *others(btn), ...) below locks out the rest.
    register, others = screen_lock()

    with ui.column().classes("gap-3") as scr:
        ui.markdown(f"Drop your CVs / notes / docs below, or straight into `{inbox}`.")
        add_files_btn, upload_ctl = build_file_manager(inbox)
        ui.separator()

        fb_box = ui.textarea("Factbook (review, then Save)").props("rows=18").classes("w-full")
        fb_box.set_visibility(False)
        gaps_box = ui.column().classes("w-full gap-2")
        gaps_box.set_visibility(False)

        def refresh_gaps():
            gaps_box.clear()
            gaps = factbook.parse_gaps(fb_box.value)
            gaps_box.set_visibility(bool(gaps))
            if not gaps:
                return
            with gaps_box:
                ui.label(f"Open questions ({len(gaps)}) - answer any you can, then Apply:").classes("font-bold")
                fields = []
                for g in gaps:
                    # the question is a wrapping label, not the input's floating label (which Quasar
                    # truncates to one line instead of wrapping) - the input itself is a plain answer box
                    with ui.column().classes("w-full gap-1"):
                        ui.label(g).classes("text-sm whitespace-pre-wrap break-words")
                        inp = ui.input(placeholder="Your answer").classes("w-full")
                    fields.append((g, inp))

                async def apply_answers():
                    qa = [(g, inp.value.strip()) for g, inp in fields if inp.value.strip()]
                    if not qa:
                        notify("Type an answer for at least one question first", type="warning")
                        return
                    push_line(f"Applying {len(qa)} answer(s) to the factbook...")
                    async with busy(apply_btn, *others(apply_btn)):
                        try:
                            fb_box.value = await run.io_bound(factbook.resolve_gaps, fb_box.value, qa)
                            refresh_gaps()
                            notify("Factbook updated - review & Save", type="positive")
                        except Exception as e:  # noqa: BLE001
                            push_line(f"! {e}")
                            notify(f"Failed: {e}", type="negative")

                apply_btn = register(ui.button("Apply answers", on_click=apply_answers)
                                      .props("unelevated color=primary"))

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
            fb_box.set_visibility(False)
            save_btn.set_visibility(False)
            gaps_box.set_visibility(False)
            push_line("Building factbook from the inbox...")
            async with busy(build_btn, *others(build_btn), add_files_btn, upload_ctl):
                try:
                    fb_box.value = await run.io_bound(factbook.build, inbox)
                    fb_box.set_visibility(True)
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
            fb_box.set_visibility(True)
            save_btn.set_visibility(True)
            refresh_gaps()

        with ui.row():
            ui.button("Back", on_click=lambda: show(1)).props("flat")
            ui.button("Next", on_click=lambda: show(3))
    return scr
