#!/bin/bash
# ===============================================================
#  The Besorah - one-click launcher (Linux)
#  Run this script to start a local server and open the reader
#  in your default browser. Press Ctrl+C to stop.
#
#  First time only: run
#      chmod +x start.sh
#  to make this file executable, then ./start.sh (or double-click
#  if your file manager is configured to run shell scripts).
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
  echo "Install it with your package manager, e.g.:"
  echo "    sudo apt install python3        # Debian / Ubuntu"
  echo "    sudo dnf install python3        # Fedora"
  echo
  read -p "Press Enter to close..."
  exit 1
fi

URL="http://localhost:$PORT/"
echo "Starting The Besorah on $URL"
echo "Press Ctrl+C to stop the server."

# Open the URL in whichever opener exists.
if command -v xdg-open >/dev/null 2>&1; then
  ( sleep 1 && xdg-open "$URL" ) &
elif command -v gnome-open >/dev/null 2>&1; then
  ( sleep 1 && gnome-open "$URL" ) &
fi

exec $PY -m http.server $PORT
