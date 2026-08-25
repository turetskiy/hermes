"""The Setup screen: pick a provider + model (from litellm's own catalog, or type any custom string),
see that provider's real key-signup link and an honest free/trial/paid note, paste the matching API
key, Test & save both to ~/Hermes/.env. The key panel itself is web/setup_keypanel.py; this file wires
provider/model selection and the Test & save flow around it."""
import os

import paths
from services.osutil import open_path
from web.notify import notify
from web.setup_keypanel import build_key_panel


def setup_screen(show, push_line):
    from nicegui import ui, run
    from services import llm
    from web.progress import busy

    current = llm.model()
    current_provider = llm.provider_of(current) or "gemini"

    with ui.column().classes("gap-3") as scr:
        ui.label("Model & API key").classes("text-lg font-bold")
        ui.markdown("Hermes is **model-agnostic** (via LiteLLM) - Gemini by default, but any "
                    "provider works. Pick a provider and model below, or type your own.")
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
            return llm.canonical_model(provider_sel.value, model_sel.value or "")

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

        def on_provider_change():
            options = llm.model_options(provider_sel.value)
            # the old model string belongs to the previous provider - keeping it would build a
            # garbled hybrid (e.g. "groq/gemini/gemini-3.1-pro-preview"); reset to a real option
            # for the new provider, or blank if it has none in our curated list (still freely typeable)
            model_sel.set_options(options, value=next(iter(options), ""))
            sync_key_panel(provider_sel.value)
            sync_fields()

        provider_sel.on_value_change(lambda e: on_provider_change())
        model_sel.on_value_change(lambda e: sync_fields())
        sync_key_panel(current_provider)
        sync_fields()

        async def test_key():
            model = current_full_model()
            if not model:
                notify("Pick or type a model first", type="warning")
                return
            is_local = llm.key_info(provider_sel.value)["tier"] == "local"
            if not is_local and not key_in.value.strip():
                notify("Paste a key first", type="warning")
                return
            env_name = llm.key_env_for(model)
            llm.save_model(model)
            if not is_local:
                llm.save_key(key_in.value, env_name)
            push_line(f"Testing {model} ...")
            async with busy(test_btn):
                try:
                    await run.io_bound(llm.check_key)
                    saved = "Model saved" if is_local else f"Key works and is saved ({env_name})"
                    notify(saved, type="positive")
                except Exception as e:  # noqa: BLE001
                    push_line(f"! {e}")
                    notify(f"Test failed: {e}", type="negative")

        test_btn = ui.button("Test & save", on_click=test_key).props("unelevated color=primary")
        ui.separator()
        ui.markdown(f"**Data** lives in `{paths.HOME}` - outside the app, safe & portable.")
        ui.button("Open data folder", on_click=lambda: open_path(paths.HOME)).props("outline")
        with ui.row():
            ui.button("Back", on_click=lambda: show(0)).props("flat")
            ui.button("Next", on_click=lambda: show(2))
    return scr
