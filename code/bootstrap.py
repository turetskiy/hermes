"""Self-setup: make sure the project's dependencies are importable.

On first run (typically launched with the system python, nothing installed) this creates a local
`.venv`, installs the dependencies with visible progress, and relaunches Hermes under that venv - so
the newly installed packages are actually available (a running interpreter can't gain a venv it wasn't
started with). Everything here uses only the standard library, so it works before anything is installed.
"""
import importlib.util
import os
import subprocess
import sys

import paths

VENV = os.path.join(paths.ROOT, ".venv")
_BIN, _EXE = ("Scripts", ".exe") if os.name == "nt" else ("bin", "")  # venv layout: Windows vs POSIX
VENV_PY = os.path.join(VENV, _BIN, "python" + _EXE)
DEFAULT_ENTRY = os.path.join(paths.ROOT, "code", "app.py")

REQUIRED = [
    ("python-docx", "docx"),
    ("litellm", "litellm"),
    ("requests", "requests"),
    ("beautifulsoup4", "bs4"),
    ("pypdf", "pypdf"),
    ("nicegui", "nicegui"),  # the web UI's dependency - required so it's always auto-installed too
]
INSTALL = [pkg for pkg, _ in REQUIRED]


def _entry_point():
    """The script that actually launched this process, so a re-exec resumes THAT script. Falls back to
    app.py if __main__ has no file (e.g. -c)."""
    main_file = getattr(sys.modules.get("__main__"), "__file__", None)
    return os.path.abspath(main_file) if main_file else DEFAULT_ENTRY


def has(mod):
    # find_spec raises (not returns None) when a dotted module's PARENT is missing,
    # e.g. "google.genai" with no google package - so swallow that and report "absent".
    try:
        return importlib.util.find_spec(mod) is not None
    except Exception:  # noqa: BLE001
        return False


def missing():
    return [pkg for pkg, mod in REQUIRED if not has(mod)]


def deps_ok():
    return not missing()


def _quiet(cmd):
    """Like subprocess.run(), but never raises - a launch failure (e.g. cmd[0] doesn't exist) becomes
    a normal nonzero-returncode result instead of an uncaught exception, so every _quiet() call site's
    existing `.returncode != 0` handling covers it uniformly, with no separate try/except needed there."""
    try:
        return subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    except OSError as e:
        return subprocess.CompletedProcess(cmd, 1, stdout=b"", stderr=str(e).encode())


def _bar(done, total, label=""):
    filled = int(24 * done / total)
    sys.stdout.write(f"\r  [{'#' * filled}{'-' * (24 - filled)}] {int(100 * done / total):3d}%  {label:<16}")
    sys.stdout.flush()


def _install():
    _quiet([VENV_PY, "-m", "pip", "install", "--upgrade", "--quiet", "pip"])
    total = len(INSTALL)
    for i, pkg in enumerate(INSTALL):
        _bar(i, total, pkg)
        result = _quiet([VENV_PY, "-m", "pip", "install", "-q", pkg])
        if result.returncode != 0:
            tail = (result.stderr.decode(errors="replace").strip().splitlines() or [""])[-1]
            sys.stdout.write("\n")
            print(f"  installing {pkg} failed: {tail}")
            return False
    _bar(total, total, "done")
    sys.stdout.write("\n")
    return True


def _reexec():
    os.environ["HERMES_REEXEC"] = "1"  # only re-exec once, so a bad venv can't loop
    entry = _entry_point()
    try:
        os.execv(VENV_PY, [VENV_PY, entry] + sys.argv[1:])
    except OSError as e:
        print(f"  couldn't relaunch automatically ({e}).")
        _manual()
        sys.exit(1)


def _manual():
    print("\n  Could not finish automatically. Set it up, then rerun:")
    print(f"    python3 -m venv {VENV}")
    print(f"    {os.path.join(VENV, _BIN, 'pip' + _EXE)} install " + " ".join(INSTALL))
    print(f"    {VENV_PY} {_entry_point()}")


def ensure():
    """Return once every dependency is importable in the current interpreter - creating .venv,
    installing, and relaunching into it as needed. May replace the process or exit on failure."""
    paths.ensure_home()  # create ~/Hermes (data/output/inbox + blank scaffolds) before anything runs
    if deps_ok():
        return
    in_venv = os.path.realpath(sys.executable) == os.path.realpath(VENV_PY)
    reexeced = os.environ.get("HERMES_REEXEC") == "1"
    if not in_venv and not reexeced and os.path.exists(VENV_PY):
        _reexec()  # a venv already exists - hand off to it (it installs if it turns out incomplete)
    if not os.path.exists(VENV_PY):
        print("\nFirst run - preparing Hermes (one-time).")
        sys.stdout.write("  creating virtual environment ... ")
        sys.stdout.flush()
        venv_ok = _quiet([sys.executable, "-m", "venv", VENV]).returncode == 0
        if venv_ok and not os.path.exists(VENV_PY):
            # venv reported success but its own python.exe is missing - seen when sys.executable is a
            # non-standard/bundled Python (e.g. one shipped inside another app like Inkscape) whose
            # venv module doesn't fully copy itself; surfacing this now beats a raw crash on first use
            print(f"failed.\n  ({sys.executable} created a venv, but {VENV_PY} doesn't exist - that "
                  "Python looks non-standard (bundled inside another app?); try a plain install from "
                  "python.org instead)")
            venv_ok = False
        elif not venv_ok:
            print("failed.")
        if not venv_ok:
            _manual()
            sys.exit(1)
        print("done")
    print("  installing dependencies")
    if not _install():
        _manual()
        sys.exit(1)
    importlib.invalidate_caches()
    if deps_ok():  # we ARE the venv interpreter - installed in place, good to go
        print("\nSetup complete.")
        return
    if not reexeced:
        print("\nSetup complete - relaunching Hermes under .venv ...\n")
        _reexec()
    print("\nDependencies are still missing after setup.")
    _manual()
    sys.exit(1)
