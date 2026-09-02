"""Build .docx / Download / Apply feedback controls for the Tailor screen - split out of
web/tailor.py by concern (generating tailored content vs exporting/refining the file). docx_controls()
creates Build .docx + Download so tailor_screen can place them in the same row as its own Tailor
button; feedback_controls() is separate (its own row/section) but shares docx_controls()'s `state`
dict to know whether a .docx exists yet to regenerate."""
import json
import os

import paths
from services import cancel
from web.notify import notify
from web.progress import busy


def docx_controls(push_line, result_box, style_select, track_select, register, others):
    """Return (build_docx_btn, download_btn, state) - state["docx_path"] is also read by
    feedback_controls() below. register/others come from tailor_screen's shared screen_lock()."""
    from nicegui import ui
    from rendering import fill_template
    from templating import build_template

    state = {"docx_path": None}

    download_btn = ui.button("Download .docx", icon="download",
                             on_click=lambda: ui.download(state["docx_path"],
                                                          filename=os.path.basename(state["docx_path"])))
    download_btn.set_visibility(False)

    async def build_docx():
        try:
            data = json.loads(result_box.value)
        except ValueError as e:
            notify(f"Not valid JSON: {e}", type="negative")
            return
        push_line("Building the resume template and document...")
        async with busy(build_docx_btn, *others(build_docx_btn), result_box, style_select, track_select):
            try:
                await cancel.io_bound(build_template.build, style_select.value)
                track_id = track_select.value
                out = os.path.join(paths.OUTPUT, f"resume_{track_id}_tailored.docx")
                await cancel.io_bound(fill_template.build, data, out)
                state["docx_path"] = out
                download_btn.set_visibility(True)
                push_line(f"Built {os.path.basename(out)}")
                notify("Resume built - download it below", type="positive")
            except Exception as e:  # noqa: BLE001
                push_line(f"! {e}")
                notify(f"Failed: {e}", type="negative")

    build_docx_btn = register(ui.button("Build .docx", on_click=build_docx).props("unelevated color=primary"))
    build_docx_btn.set_visibility(False)

    return build_docx_btn, download_btn, state


def feedback_controls(push_line, result_box, register, others, state):
    """Feedback input + Apply button, kept as its own row below the docx_controls() row. Reads
    state["docx_path"] to decide whether to regenerate the built .docx after applying feedback."""
    from nicegui import ui
    from rendering import fill_template
    from services import llm

    feedback_in = ui.input("Feedback (after building, to refine further)").classes("w-full")
    feedback_in.set_visibility(False)

    async def apply_feedback():
        fb = feedback_in.value.strip()
        if not fb:
            notify("Type some feedback first", type="warning")
            return
        try:
            data = json.loads(result_box.value)
        except ValueError as e:
            notify(f"Not valid JSON: {e}", type="negative")
            return
        push_line(f"Applying feedback: {fb[:80]}")
        async with busy(feedback_btn, *others(feedback_btn), result_box, feedback_in):
            try:
                fields = dict(feedback=fb, content=json.dumps(data, ensure_ascii=False))
                updated = await cancel.io_bound(llm.call_block, "feedback", fields, False, data)
                result_box.value = json.dumps(updated, ensure_ascii=False, indent=2)
                feedback_in.value = ""
                if state["docx_path"]:
                    await cancel.io_bound(fill_template.build, updated, state["docx_path"])
                    push_line("Regenerated the .docx with your feedback.")
                notify("Feedback applied" + (" - .docx updated" if state["docx_path"] else ""),
                      type="positive")
            except Exception as e:  # noqa: BLE001
                push_line(f"! {e}")
                notify(f"Failed: {e}", type="negative")

    feedback_btn = register(ui.button("Apply feedback", on_click=apply_feedback))
    feedback_btn.set_visibility(False)

    return feedback_in, feedback_btn
