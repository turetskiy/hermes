"""The Setup screen: pick a provider + model (from litellm's own catalog, or type any custom string),
paste the matching API key. Both auto-save to ~/Hermes/.env the instant they're picked/typed - no
separate save step, so what's selected and what's active can never drift apart. "Send test request" is
a purely optional round-trip check - not just the key, the whole model+key combination, since a bad
model string fails the same request a bad key would - kept separate so it isn't triggered on every
keystroke. The active model is
mirrored into the persistent top bar (web/topbar.py) via page_state, visible from every screen. The key
panel itself is web/setup_keypanel.py."""
import os

import paths
from services.osutil import open_path
from web.notify import notify
from web.setup_keypanel import build_key_panel


def setup_screen(show, push_line, page_state):
    from nicegui import ui, run
    from services import llm
    from web.progress import busy

    current = llm.model()
    current_provider = llm.provider_of(current) or "gemini"

    with ui.column().classes("gap-3") as scr:
        ui.label("Model & API key").classes("text-lg font-bold")
        ui.markdown("Hermes is **model-agnostic** (via LiteLLM) - Gemini by default, but any "
                    "provider works. Pick a provider and model below, or type your own - both save "
                    "instantly, no separate step.")
        with ui.row().classes("w-full gap-3"):
            provider_sel = ui.select(llm.provider_options(), label="Provider", with_input=True,
                                      new_value_mode="add-unique", value=current_provider) \
                .classes("flex-1 min-w-0")
            model_sel = ui.select(llm.model_options(current_provider), label="Model",
                                   with_input=True, new_value_mode="add-unique",
                                   value=current).classes("flex-1 min-w-0")
        status_lbl = ui.label().classes("text-xs")
        sync_key_panel = build_key_panel()
        key_env_lbl = ui.label().classes("text-xs text-grey-6")
        key_in = ui.input("API key", password=True).classes("w-full")

        def current_full_model():
            # canonical_model() always prepends "provider/" - guard the blank case ourselves, or an
            # empty model_sel.value would still come back as a truthy "provider/" and get auto-saved
            m = (model_sel.value or "").strip()
            return llm.canonical_model(provider_sel.value, m) if m else ""

        def set_model_label(text):
            model_lbl = page_state.get("model_label")
            if model_lbl:
                model_lbl.set_text(f"Model: {text}")

        def sync_fields():
            full = current_full_model()
            ok = llm.resolves_to(provider_sel.value, full)
            status_lbl.set_text(f"{'OK' if ok else '?'} litellm resolves this to: "
                                 f"{llm.provider_of(full) or 'unknown'}")
            status_lbl.classes(replace="text-xs " + ("text-positive" if ok else "text-warning"))
            env_name = llm.key_env_for(full)
            key_env_lbl.set_text(f"Goes into: {env_name}")
            key_in.value = os.environ.get(env_name, "")
            is_local = llm.key_info(provider_sel.value)["tier"] == "local"
            key_env_lbl.set_visibility(not is_local)
            key_in.set_visibility(not is_local)

        def on_model_change():
            full = current_full_model()
            if full:
                llm.save_model(full)  # auto-save - selecting/typing IS saving, no button needed
                set_model_label(full)
            sync_fields()

        def on_provider_change():
            # the old model string belongs to the previous provider - keeping it would build a garbled
            # hybrid (e.g. "groq/gemini/gemini-3.1-pro-preview"). Don't guess a replacement either:
            # litellm's own catalogs mix in specialized, non-chat-completions model families (Gemini's
            # includes "deep-research", "computer-use", native-audio/tts/live variants, ...) with no
            # reliable way to filter all of them out, so picking "the first one" can silently land on
            # something that 400s. Leave it blank - an explicit pick (or typed value) is the safe move.
            model_sel.set_options(llm.model_options(provider_sel.value), value="")
            sync_key_panel(provider_sel.value)
            sync_fields()

        def on_key_change():
            is_local = llm.key_info(provider_sel.value)["tier"] == "local"
            if is_local or not key_in.value.strip():
                return
            llm.save_key(key_in.value, llm.key_env_for(current_full_model()))  # auto-save, same reason

        provider_sel.on_value_change(lambda e: on_provider_change())
        model_sel.on_value_change(lambda e: on_model_change())
        key_in.on_value_change(lambda e: on_key_change())
        sync_key_panel(current_provider)
        sync_fields()
        set_model_label(current)

        async def test_key():
            model = current_full_model()
            if not model:
                notify("Pick or type a model first", type="warning")
                return
            is_local = llm.key_info(provider_sel.value)["tier"] == "local"
            if not is_local and not key_in.value.strip():
                notify("Paste a key first", type="warning")
                return
            push_line(f"Sending a test request to {model} ...")
            async with busy(test_btn, provider_sel, model_sel, key_in):
                try:
                    await run.io_bound(llm.check_key)
                    notify("Test request succeeded - model and key both work", type="positive")
                except Exception as e:  # noqa: BLE001
                    push_line(f"! {e}")
                    notify(f"Test failed: {e}", type="negative")

        test_btn = ui.button("Send test request", on_click=test_key).props("unelevated color=primary")
        ui.separator()
        ui.markdown(f"**Data** lives in `{paths.HOME}` - outside the app, safe & portable.")
        ui.button("Open data folder", on_click=lambda: open_path(paths.HOME)).props("outline")
        with ui.row():
            ui.button("Back", on_click=lambda: show(0)).props("flat")
            ui.button("Next", on_click=lambda: show(2))
    return scr
