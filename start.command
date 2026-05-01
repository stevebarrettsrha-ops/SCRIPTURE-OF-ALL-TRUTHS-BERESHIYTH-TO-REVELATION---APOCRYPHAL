#!/bin/bash
# ===============================================================
#  The Besorah - one-click launcher (macOS)
#  Double-click this file in Finder to start a local server and
#  open the reader in your default browser. Close the Terminal
#  window to stop the server.
#
#  First time only: in Terminal, run
#      chmod +x start.command
#  to make this file executable.
# ===============================================================

cd "$(dirname "$0")"
PORT=8000

if command -v python3 >/dev/null 2>&1; then
  PY=python3
elif command -v python >/dev/null 2>&1; then
  PY=python
else
  echo
  echo "Python 3 is not installed."
  echo "Install it from https://www.python.org/downloads/ and try again."
  echo
  read -p "Press Enter to close..."
  exit 1
fi

echo "Starting The Besorah on http://localhost:$PORT/"
echo "Close this window to stop the server."
( sleep 1 && open "http://localhost:$PORT/" ) &
exec $PY -m http.server $PORT
