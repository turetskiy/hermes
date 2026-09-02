"""Per-track memory of the Tailor screen's result_box - split out of web/tailor.py by concern.
Switching the track dropdown must not lose a track's tailored result, only hide it while another
track is shown; coming back to a track that was already tailored (without clicking Tailor again)
should restore exactly what was there, edits included, instead of either nothing or another track's
stale content."""
import os

import paths


def track_cache(track_select, result_box, build_docx_btn, download_btn, feedback_in, feedback_btn, export_state):
    """Returns (reset_result, restore_or_reset, save). Wire restore_or_reset to track_select's
    on_value_change; call reset_result() at the start of a fresh Tailor run; call save(track_id) once
    that run's result lands in result_box."""
    results = {}
    current = {"id": None}

    def reset_result():
        result_box.set_visibility(False)
        build_docx_btn.set_visibility(False)
        download_btn.set_visibility(False)
        feedback_in.set_visibility(False)
        feedback_btn.set_visibility(False)
        export_state["docx_path"] = None

    def restore_or_reset():
        prev = current["id"]
        if prev and result_box.visible:  # snapshot what we're leaving before it's overwritten
            results[prev] = result_box.value
        track_id = track_select.value
        current["id"] = track_id
        cached = results.get(track_id)
        if cached is None:
            reset_result()
            return
        result_box.value = cached
        result_box.set_visibility(True)
        build_docx_btn.set_visibility(True)
        feedback_in.set_visibility(True)
        feedback_btn.set_visibility(True)
        docx_path = os.path.join(paths.OUTPUT, f"resume_{track_id}_tailored.docx")
        has_docx = os.path.exists(docx_path)  # the file this track's own Build .docx would have written
        export_state["docx_path"] = docx_path if has_docx else None
        download_btn.set_visibility(has_docx)

    def save(track_id):
        results[track_id] = result_box.value
        current["id"] = track_id

    return reset_result, restore_or_reset, save
