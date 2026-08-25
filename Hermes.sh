#!/bin/bash
# Double-click launcher (Linux): starts Hermes without opening a terminal manually.
# Most file managers need "Allow executing file as program" (or similar, in the file's
# Properties -> Permissions) before a double-click will run this instead of opening it in an
# editor - or just run it from a terminal: ./Hermes.sh
# A terminal window opens to run this - that's the app's server console. It closes the
# server (and this prompt just lets the window close) once you close the last Hermes tab
# in your browser; it only waits for a keypress if something actually went wrong, so you
# can read the error.
cd "$(dirname "$0")" || exit 1

PY=python3
command -v "$PY" >/dev/null 2>&1 || PY=python
if ! command -v "$PY" >/dev/null 2>&1; then
  echo "Python 3 isn't installed. Install it with your distro's package manager (e.g. sudo apt"
  echo "install python3) and try again."
  read -r -p "Press Enter to close..." _
  exit 1
fi

"$PY" code/app.py
CODE=$?
if [ "$CODE" -ne 0 ]; then
  echo
  echo "Hermes exited with an error (code $CODE) - see above."
  read -r -p "Press Enter to close..." _
fi
