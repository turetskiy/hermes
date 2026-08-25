"""Tiny cross-platform OS helpers (Mac / Windows / Linux)."""
import os
import subprocess
import sys


def open_path(path):
    """Open a file or folder in the OS default handler (Finder / Explorer / xdg-open)."""
    try:
        if sys.platform == "darwin":
            subprocess.run(["open", path])
        elif os.name == "nt":
            os.startfile(path)  # noqa: F821 - Windows only
        else:
            subprocess.run(["xdg-open", path])
    except Exception as e:  # noqa: BLE001
        print(f"couldn't open {path}: {e}")
