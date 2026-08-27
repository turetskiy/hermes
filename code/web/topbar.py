"""The persistent bar shown above every screen: the Hermes wordmark, the currently active model
(auto-saved by web/setup.py the moment it's picked/typed - no separate save step), and a clickable
step breadcrumb to jump straight to any screen. Screens are built once and only hidden (web/ui.py's
show()), never rebuilt, so jumping around never loses whatever's typed into another screen's controls."""
from web.brand import header

STEPS = ["Welcome", "Setup", "Material", "Profile", "Tailor"]

# Colors set via inline style, not Tailwind text-color classes: Quasar's own component CSS can win the
# specificity fight and silently keep a class-based text color from ever showing.
_MODEL_STYLE = "color:#166534"  # green-800
_CRUMB_ACTIVE = "color:#1e3a8a; font-weight:600; cursor:pointer"  # blue-900
_CRUMB_INACTIVE = "color:#64748b; font-weight:400; cursor:pointer"  # slate-500


def build_topbar(show):
    from nicegui import ui

    with ui.column().classes("w-full gap-2"):
        with ui.row().classes("w-full items-center justify-between"):
            header()
            with ui.row().classes("items-center px-3 py-1 rounded-full bg-green-50"):
                model_lbl = ui.label().classes("text-sm font-semibold").style(_MODEL_STYLE)
        with ui.row().classes("gap-4"):
            crumbs = [ui.label(f"{i + 1}. {name}").classes("hover:underline")
                      .on("click", lambda i=i: show(i))
                      for i, name in enumerate(STEPS)]

    def sync_active_step(i):
        for j, lbl in enumerate(crumbs):
            lbl.style(replace=_CRUMB_ACTIVE if j == i else _CRUMB_INACTIVE)

    return model_lbl, sync_active_step
