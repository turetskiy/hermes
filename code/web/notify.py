"""A single, more noticeable ui.notify default. The plain default (small, bottom, no close button)
is easy to miss - and now sits right over the fixed footer log/progress bar, competing with it. This
one shows at the top, bigger text, and a close button so it doesn't vanish before you've read it."""


def notify(message, type=None):  # noqa: A002 - "type" matches ui.notify's own parameter name
    from nicegui import ui
    ui.notify(message, type=type, position="top", close_button=True, timeout=6000,
             classes="text-base", multi_line=True)
