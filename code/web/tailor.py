"""The Tailor screen: pick a template style + track, optionally point at a vacancy, and the model
tailors headline/summary/skills/bullets to it in one pass - review/edit the WHOLE result below (like
Profile). Build/Download/Feedback controls live in web/tailor_export.py, split out by concern.
Progress goes to the shared page-level log. `page_state` stashes this screen's track dropdown so
Profile's "Next" button can hand over whichever track was just picked/saved there."""
import json
import os

import paths
from web.notify import notify
from web.progress import busy, screen_lock
from web.tailor_export import export_controls


def tailor_screen(show, push_line, page_state):
    from nicegui import ui, run
    import profile_store
    from content import assemble
    from content.pipeline import run_auto
    from services import llm, vacancy
    from templating import build_template

    # Fetch / Tailor / Build .docx / Apply feedback all touch the same result_box (or fields feeding
    # it) and none should run while another is mid-flight - register() each as it's created (build_docx
    # and feedback's buttons live in tailor_export.py, wired in via export_controls() below), then
    # others(btn) lists every sibling to freeze alongside btn's own operation.
    register, others = screen_lock()

    with ui.column().classes("gap-3") as scr:
        ui.markdown("Pick a template and a track, optionally point at a vacancy, and the model "
                    "tailors your resume to it. Review the result below (plain JSON, editable) "
                    "before building the `.docx`.")

        with ui.row().classes("w-full items-end gap-3"):
            style_select = ui.select(build_template.list_styles(), label="Template style",
                                     value=build_template.list_styles()[0]).classes("flex-1 min-w-0")
            track_select = ui.select(profile_store.track_picker_options(), label="Track") \
                .classes("flex-1 min-w-0")
            ui.button(icon="refresh",
                     on_click=lambda: track_select.set_options(profile_store.track_picker_options())) \
                .props("flat round dense").tooltip("Refresh tracks (e.g. after saving one in Profile)")
        page_state["tailor_track_select"] = track_select

        with ui.row().classes("w-full items-end gap-3"):
            url_in = ui.input("Vacancy URL (optional)").classes("flex-1")
            fetch_btn = register(ui.button("Fetch").props("outline"))
        jd_box = ui.textarea("Vacancy text (leave blank for a baseline resume)").props("rows=8").classes("w-full")

        with ui.row().classes("w-full gap-3"):
            depth_select = ui.select(list(llm.PROMPTS["depth_levels"]), label="Rework depth",
                                     value="medium").classes("flex-1 min-w-0")
            extra_in = ui.input("Extra instructions (optional)").classes("flex-1")

        result_box = ui.codemirror(language="JSON", line_wrapping=True) \
            .classes("w-full overflow-x-auto").style("height: 20rem")
        result_box.set_visibility(False)

        async def fetch():
            url = url_in.value.strip()
            if not url:
                notify("Paste a URL first", type="warning")
                return
            push_line(f"Fetching {url} ...")
            async with busy(fetch_btn, *others(fetch_btn), url_in, jd_box):
                text = await run.io_bound(vacancy.fetch_url, url)
                if text and len(text) > 200:
                    jd_box.value = text
                    notify(f"Fetched {len(text)} characters", type="positive")
                else:
                    push_line("! fetch failed or too short")
                    notify("Fetch failed or too short - paste the JD instead", type="warning")

        fetch_btn.on_click(fetch)

        build_docx_btn, download_btn, feedback_in, feedback_btn, export_state = export_controls(
            push_line, result_box, style_select, track_select, register, others)

        async def tailor():
            if not llm.has_key():
                notify("Set your API key in Setup first", type="warning")
                return
            track_id = track_select.value
            if not track_id:
                notify("Pick a track first (build one in Profile)", type="warning")
                return
            result_box.set_visibility(False)
            build_docx_btn.set_visibility(False)
            download_btn.set_visibility(False)
            feedback_in.set_visibility(False)
            feedback_btn.set_visibility(False)
            export_state["docx_path"] = None
            async with busy(tailor_btn, *others(tailor_btn), style_select, track_select, url_in,
                            jd_box, depth_select, extra_in):
                try:
                    content = await run.io_bound(assemble.assemble, track_id)
                    jd = jd_box.value.strip()
                    if jd:
                        push_line(f"Tailoring to the vacancy (depth={depth_select.value})...")
                        depth_text = llm.PROMPTS["depth_levels"][depth_select.value]
                        facts_path = os.path.join(paths.DATA, "factbook.md")
                        facts = open(facts_path).read() if os.path.exists(facts_path) else ""
                        content = await run.io_bound(run_auto, content, jd, depth_text,
                                                     extra_in.value.strip(), facts, False)
                    else:
                        push_line("No vacancy given - using the baseline resume.")
                    result_box.value = json.dumps(content, ensure_ascii=False, indent=2)
                    result_box.set_visibility(True)
                    build_docx_btn.set_visibility(True)
                    feedback_in.set_visibility(True)
                    feedback_btn.set_visibility(True)
                    notify("Tailored - review below, then Build .docx", type="positive")
                except (Exception, SystemExit) as e:  # noqa: BLE001
                    push_line(f"! {e}")
                    notify(f"Failed: {e}", type="negative")

        tailor_btn = register(ui.button("Tailor", on_click=tailor).props("unelevated color=primary"))
        with ui.row():
            ui.button("Back", on_click=lambda: show(3)).props("flat")
    return scr
