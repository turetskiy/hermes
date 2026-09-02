"""A per-screen registry of action buttons that must never run concurrently (Fetch/Tailor/Build .docx/
Apply feedback all touch the same result, for instance). Split out of web/progress.py by concern."""


def screen_lock():
    """register() each button as it's created; others(btn) - called from inside the click handler, so
    by then every sibling is registered even if defined later in the file - lists every OTHER
    registered button, to pass into busy() as extra freeze targets so ANY one of them running locks
    out ALL the others, not just its own button."""
    registered = []

    def register(btn):
        registered.append(btn)
        return btn

    def others(btn):
        return [b for b in registered if b is not btn]

    return register, others
