#!/usr/bin/env python3
"""Hermes web UI entry point - a browser front-end over the same core as the console menu (hermes.py,
the reserve UI). Screen/widget logic lives in web/ui.py; this file bootstraps dependencies, runs the
server, and shuts it down once the last browser tab disconnects (so this process's lifetime matches
"the app is open in a tab", not "forever until you remember to Ctrl+C"). Run: python3 code/app.py, or
double-click Hermes.command / Hermes.bat."""
import os
import sys

if __package__ in (None, ""):  # allow `python code/app.py`
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import bootstrap
import paths

PORT = 8080
IDLE_GRACE_SECONDS = 5  # covers page reloads / brief reconnects without a false shutdown


def _watch_for_idle_shutdown(app, Client):
    import asyncio

    @app.on_disconnect
    async def _check():
        await asyncio.sleep(IDLE_GRACE_SECONDS)
        if not any(c.has_socket_connection for c in Client.instances.values()):
            print("\nNo browser tabs connected - shutting down.")
            app.shutdown()


def main():
    paths.ensure_home()
    from services import llm
    llm.load_env()  # load an existing ~/Hermes/.env into os.environ before building any screen
    from web import ui as web_ui
    from nicegui import ui, app, Client

    web_ui.setup()
    _watch_for_idle_shutdown(app, Client)
    print("\nHermes is starting - your browser should open automatically.")
    print(f"If not, open http://localhost:{PORT}")
    print("This window runs the app; it closes the server automatically when you close the last")
    print("Hermes tab. You can also press Ctrl+C here at any time to stop it.\n")
    try:
        ui.run(title="Hermes", reload=False, show=True, port=PORT, storage_secret="hermes-local")
    except KeyboardInterrupt:
        print("\nStopped.")
    except OSError as e:
        print(f"\nCouldn't start the web server: {e}")
        print(f"(Is Hermes already running? Check for another window at http://localhost:{PORT})")
        return
    print("Hermes has stopped. You can close this window.")


if __name__ == "__main__":
    bootstrap.ensure()
    main()
