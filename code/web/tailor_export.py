"""Build .docx / Download / Apply feedback controls for the Tailor screen - split out of
web/tailor.py by concern (generating tailored content vs exporting/refining the file). Wires its own
buttons into whatever NiceGUI slot is open when called (from within tailor_screen's `with` block)."""
import json
import os

import paths
from web.notify import notify
from web.progress import busy


def export_controls(push_line, result_box, style_select, track_select):
    """Build the widgets; return (build_docx_btn, download_btn, feedback_in, feedback_btn, state) so
    tailor_screen can reset their visibility (and state["docx_path"]) when a fresh Tailor run starts."""
    from nicegui import ui, run
    from rendering import fill_template
    from services import llm
    from templating import build_template

    state = {"docx_path": None}

    download_btn = ui.button("Download .docx", icon="download",
                             on_click=lambda: ui.download(state["docx_path"],
                                                          filename=os.path.basename(state["docx_path"])))
    download_btn.set_visibility(False)

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
        async with busy(feedback_btn):
            try:
                fields = dict(feedback=fb, content=json.dumps(data, ensure_ascii=False))
                updated = await run.io_bound(llm.call_block, "feedback", fields, False, data)
                result_box.value = json.dumps(updated, ensure_ascii=False, indent=2)
                feedback_in.value = ""
                if state["docx_path"]:
                    await run.io_bound(fill_template.build, updated, state["docx_path"])
                    push_line("Regenerated the .docx with your feedback.")
                notify("Feedback applied" + (" - .docx updated" if state["docx_path"] else ""),
                      type="positive")
            except Exception as e:  # noqa: BLE001
                push_line(f"! {e}")
                notify(f"Failed: {e}", type="negative")

    feedback_btn = ui.button("Apply feedback", on_click=apply_feedback)
    feedback_btn.set_visibility(False)

    async def build_docx():
        try:
            data = json.loads(result_box.value)
        except ValueError as e:
            notify(f"Not valid JSON: {e}", type="negative")
            return
        push_line("Building the resume template and document...")
        async with busy(build_docx_btn):
            try:
                await run.io_bound(build_template.build, style_select.value)
                track_id = track_select.value
                out = os.path.join(paths.OUTPUT, f"resume_{track_id}_tailored.docx")
                await run.io_bound(fill_template.build, data, out)
                state["docx_path"] = out
                download_btn.set_visibility(True)
                push_line(f"Built {os.path.basename(out)}")
                notify("Resume built - download it below", type="positive")
            except Exception as e:  # noqa: BLE001
                push_line(f"! {e}")
                notify(f"Failed: {e}", type="negative")

    build_docx_btn = ui.button("Build .docx", on_click=build_docx).props("unelevated color=primary")
    build_docx_btn.set_visibility(False)

    return build_docx_btn, download_btn, feedback_in, feedback_btn, state
