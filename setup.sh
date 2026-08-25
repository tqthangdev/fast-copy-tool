#!/usr/bin/env bash
# setup.sh — Set up the environment to run Fast Copy Tool (Linux/macOS)
# Create a venv in the same directory as the code and install everything needed
# into it (PySide6 + psutil). With Qt6/PySide6, almost everything is installed
# in the venv via pip — no system-level UI packages required (unlike tkinter).

set -e
cd "$(dirname "$0")"

echo "=== 1. Check Python ==="
if ! command -v python3 >/dev/null 2>&1; then
    echo "Error: python3 not found. Please install Python 3.8+ first."
    exit 1
fi
python3 --version

echo ""
echo "=== 2. Create a virtual environment in ./venv ==="
if [ -d "venv" ]; then
    echo "venv already exists, skipping creation."
else
    python3 -m venv venv
    echo "Created venv."
fi

echo ""
echo "=== 3. Install Python packages into the venv (requirements.txt: PySide6 + psutil) ==="
./venv/bin/pip install --upgrade pip --quiet
./venv/bin/pip install -r requirements.txt --quiet
./venv/bin/pip list

echo ""
echo "=== 4. Verify PySide6 can be imported from the venv ==="
./venv/bin/python -c "from PySide6 import QtCore; print('OK: PySide6', QtCore.__version__)"
./venv/bin/python -c "import psutil; print('OK: psutil', psutil.__version__)"

echo ""
echo "=== 5. Check the copy tool (rsync on Linux) ==="
if [ "$(uname)" = "Linux" ]; then
    if command -v rsync >/dev/null 2>&1; then
        echo "rsync: already installed."
    else
        echo "rsync: not found. You can install it now, or later via the [About -> Install] button in the app."
        read -p "Install rsync now? (y/N) " yn
        if [ "$yn" = "y" ] || [ "$yn" = "Y" ]; then
            if [ "$(id -u)" = "0" ]; then
                apt-get install -y rsync -qq
            else
                sudo apt-get install -y rsync -qq
            fi
        fi
    fi
fi

echo ""
echo "=== 6. (Linux) Check system libraries needed for Qt display (xcb) ==="
if [ "$(uname)" = "Linux" ]; then
    ldconfig -p 2>/dev/null | grep -q libxcb-cursor && echo "libxcb-cursor: already installed." || {
        echo "libxcb-cursor: may be missing on minimal Linux builds (server/container/WSL without a GUI)."
        echo "If the app reports 'Could not load the Qt platform plugin xcb', install it with:"
        echo "  sudo apt-get install libxcb-cursor0"
    }
fi

echo ""
echo "=== Done! ==="
echo "Run the program with:"
echo "  ./venv/bin/python main.py"
echo "or activate the venv first:"
echo "  source venv/bin/activate && python main.py"