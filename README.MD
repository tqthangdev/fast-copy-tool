# Fast Copy Tool (Qt6 / PySide6)

A high-speed file copy/move tool that uses the operating system's native copy
command (Windows: `robocopy /MT`, Linux/macOS: `rsync`), with a modern Qt6 UI.

## Download

Prebuilt standalone builds are published as **GitHub Releases** — no Python or package installation required on the target machine.

### Get the latest build

1. Go to the [Releases](https://github.com/tqthangdev/fast-copy-tool/releases) page.
2. Pick the newest release (tagged `v*`).
3. Download the build for your OS:
   * **`FastCopyTool-Windows.zip`** — Windows
   * **`FastCopyTool-Linux.zip`** — Linux
4. Extract the ZIP archive.
5. Run the application:
   * **Windows:** Run `FastCopyTool.exe`
   * **Linux:** Run `./FastCopyTool`

> **No dependencies needed:** Each build is fully self-contained and includes everything required to run the application.

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
