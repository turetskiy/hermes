"""The "Build profile" button on the Profile screen: extract blocks/positioning/identity from the
factbook via the model. Split out of web/profile.py by concern - mirrors web/tailor.py's own split
into web/tailor_export.py (generation vs. the rest of the screen)."""
import json
import os

from web.notify import notify
from web.progress import busy


def build_profile_button(push_line, result_box, save_btn, label_in, register, others, extra_freeze):
    """register/others/extra_freeze come from profile_screen's shared screen_lock() - so a Build here
    locks out Save/Delete (and vice versa), plus the track-picking fields a Build shouldn't be able to
    run underneath (switching tracks mid-build would misattribute the result to the wrong one)."""
    from nicegui import ui, run
    import factbook
    import profile
    from services import llm

    async def build_profile():
        if not llm.has_key():
            notify("Set your API key in Setup first", type="warning")
            return
        if not os.path.exists(factbook.OUT):
            notify("Build a factbook first (previous step)", type="warning")
            return
        result_box.set_visibility(False)
        save_btn.set_visibility(False)
        push_line("Extracting blocks / positioning / identity from the factbook...")
        async with busy(build_btn, *others(build_btn), *extra_freeze):
            try:
                data = await run.io_bound(profile.generate, open(factbook.OUT).read())
                result_box.value = json.dumps(data, ensure_ascii=False, indent=2)
                result_box.set_visibility(True)
                save_btn.set_visibility(True)
                if not label_in.value.strip():
                    label_in.value = data.get("roles", {}).get("role1", {}).get("title", "Resume")
                notify("Profile ready - review & Save", type="positive")
            except Exception as e:  # noqa: BLE001
                push_line(f"! {e}")
                notify(f"Failed: {e}", type="negative")

    build_btn = register(ui.button("Build profile", on_click=build_profile).props("unelevated color=primary"))
    return build_btn
