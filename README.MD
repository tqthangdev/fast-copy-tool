# Fast Copy Tool (Qt6 / PySide6)

A high-speed file copy/move tool that uses the operating system's native copy
command (Windows: `robocopy /MT`, Linux/macOS: `rsync`), with a modern Qt6 UI.

## Download

Prebuilt executables for Windows and Linux are attached to each GitHub Release:

- Windows: `FastCopyTool-Windows.exe`
- Linux: `FastCopyTool-Linux`

Download the latest version from the
[Releases page](https://github.com/tqthangdev/fast-copy-tool/releases).
Releases are built automatically by GitHub Actions whenever a `v*` tag is pushed.
If you prefer a recent build before the next release, you can also run the
build manually from the
[Actions tab](https://github.com/tqthangdev/fast-copy-tool/actions).

## Requirements

- Python 3.8+
- All Python libraries install cleanly into a venv via `pip` — no system-level
  UI package needed.
- Windows: `robocopy` is built in; nothing extra to install.
- Linux/macOS: needs `rsync`. If missing, install it from the **About ->
  Install** button in the app, or manually:
  - Debian/Ubuntu: `sudo apt-get install rsync`
  - Arch: `sudo pacman -S rsync`
  - Fedora: `sudo dnf install rsync`
  - openSUSE: `sudo zypper install rsync`
- Minimal Linux builds without a GUI: if the app reports *"Could not load the Qt
  platform plugin xcb"*, install `libxcb-cursor0`:
  ```bash
  sudo apt-get install libxcb-cursor0
  ```

## Setup

### Automatic (recommended)
```bash
# Linux / macOS
chmod +x setup.sh
./setup.sh

# Windows (PowerShell)
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass   # allow the script to run once
.\setup.ps1
```

### Manual
```bash
# Windows (PowerShell)
py -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

# Linux / macOS
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
# after setup, from the project directory
./venv/bin/python main.py     # Linux/macOS
.\venv\Scripts\python.exe main.py   # Windows
```

Or with the venv activated, simply:
```bash
python main.py
```