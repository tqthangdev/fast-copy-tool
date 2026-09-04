#!/usr/bin/env bash
#
# Click-to-run for Linux/macOS:
#   - detect the environment,
#   - if dependencies are not installed, run ./setup.sh,
#   - then launch main.py.
set -e

cd "$(dirname "$0")"

PY=""

pick_python() {
    if [ -x "$PWD/venv/bin/python" ]; then
        PY="$PWD/venv/bin/python"
    elif [ -x "$PWD/.venv/bin/python" ]; then
        PY="$PWD/.venv/bin/python"
    elif [ -d "$PWD/vendor" ]; then
        PY="python3"
        export PYTHONPATH="$PWD/vendor"
    else
        PY=""
    fi
}

check_dependencies() {
    [ -n "$PY" ] || return 1

    "$PY" -c '
import importlib.util
import sys

required = ("PySide6", "psutil")

missing = [
    name for name in required
    if importlib.util.find_spec(name) is None
]

if missing:
    print("Missing:", ", ".join(missing))
    sys.exit(1)
'
}

pick_python

if ! check_dependencies; then
    if [ ! -f "requirements.txt" ]; then
        echo "ERROR: requirements.txt not found."
        exit 1
    fi

    echo "Dependencies not installed. Installing (this may take a few minutes)..."

    ./setup.sh

    PY=""
    pick_python

    if ! check_dependencies; then
        echo "ERROR: Installation failed."
        exit 1
    fi
fi

exec "$PY" main.py