# Fast Copy Tool (Qt6 / PySide6)

A high-speed file copy/move tool that uses the operating system's native copy
command (Windows: `robocopy /MT`, Linux/macOS: `rsync`), with a modern Qt6 UI.

## Download

Prebuilt builds for Windows and Linux are available from the
[GitHub Releases](https://github.com/tqthangdev/fast-copy-tool/releases).

Each release contains:

* `FastCopyTool-Windows.zip` — Windows build
* `FastCopyTool-Linux.zip` — Linux build

The Windows archive contains the PyInstaller application directory with
`FastCopyTool.exe`.

The Linux archive contains the PyInstaller application directory with the
`FastCopyTool` executable.

Releases are created automatically by GitHub Actions when a tag matching
`v*` is pushed.

For example:

```text
v1.0.0
v1.1.0
v2.0.0
```

A build can also be triggered manually from the
[GitHub Actions](https://github.com/tqthangdev/fast-copy-tool/actions) page using
the `workflow_dispatch` option. Manual builds are uploaded as GitHub Actions
artifacts and do not create a GitHub Release.

## Requirements

### Windows

* Python 3.8+ for running from source
* `robocopy` — built into Windows; nothing extra is required when using the
  source version.
* Python dependencies are installed automatically into a local virtual
  environment.

Prebuilt Windows releases do not require Python to be installed.

### Linux / macOS

* Python 3.8+ for running from source
* `rsync`
* Python dependencies are installed automatically into a local virtual
  environment.

Prebuilt Linux releases do not require Python to be installed, but the required
system libraries must still be available.

If `rsync` is missing, install it manually:

* Debian/Ubuntu:

  ```bash
  sudo apt-get install rsync
  ```
* Arch:

  ```bash
  sudo pacman -S rsync
  ```
* Fedora:

  ```bash
  sudo dnf install rsync
  ```
* openSUSE:

  ```bash
  sudo zypper install rsync
  ```

### Linux Qt dependency

On minimal Linux installations, if the application reports:

```text
Could not load the Qt platform plugin "xcb"
```

install the required Qt/XCB dependency:

```bash
sudo apt-get install libxcb-cursor0
```

The GitHub Actions Linux build installs the required XCB packages during the
build process.

## Setup

If you downloaded a prebuilt release, no Python setup is required.

If you are running the project from source, use the platform launcher.

### Windows

Run:

```bat
start.bat
```

Or simply double-click `start.bat`.

The launcher automatically:

1. Checks for the local Python virtual environment.
2. Checks that `PySide6` and `psutil` are installed.
3. Runs `setup.ps1` if the environment or dependencies are missing.
4. Creates the virtual environment if necessary.
5. Installs dependencies from `requirements.txt`.
6. Verifies the installation.
7. Launches `main.py`.

### Linux / macOS

Make the launcher executable once:

```bash
chmod +x start.sh
```

Then run:

```bash
./start.sh
```

The launcher automatically:

1. Detects the available Python environment.
2. Checks that `PySide6` and `psutil` are installed.
3. Runs `setup.sh` if the environment or dependencies are missing.
4. Installs dependencies from `requirements.txt`.
5. Verifies the installation.
6. Launches `main.py`.

## Manual Setup

Automatic setup is recommended, but the environment can also be created
manually if needed.

### Windows

```powershell
py -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

### Linux / macOS

```bash
python3 -m venv venv
./venv/bin/python -m pip install -r requirements.txt
```

## Run

### From Source

The recommended way to run the source version is to use the platform launcher:

```text
Windows:     start.bat
Linux/macOS: ./start.sh
```

The launcher automatically checks the environment and installs missing Python
dependencies when necessary.

### Run Directly

After setup:

```bash
# Linux / macOS
./venv/bin/python main.py
```

```powershell
# Windows
.\venv\Scripts\python.exe main.py
```

Or activate the virtual environment first:

```bash
# Linux / macOS
source venv/bin/activate
python main.py
```

```powershell
# Windows
.\venv\Scripts\activate
python main.py
```

## Build

The project uses
[GitHub Actions](https://github.com/tqthangdev/fast-copy-tool/actions)
to build the application with PyInstaller.

### Windows Build

The Windows workflow:

* Uses Python 3.12.
* Installs the Python dependencies.
* Builds a PyInstaller application directory.
* Includes the application icons and assets.
* Packages the result as:

```text
FastCopyTool-Windows.zip
```

### Linux Build

The Linux workflow:

* Uses Python 3.12.
* Installs the required Qt/XCB system dependencies.
* Installs the Python dependencies.
* Builds a PyInstaller application directory.
* Includes the application assets.
* Packages the result as:

```text
FastCopyTool-Linux.zip
```

### Triggering a Build

Builds can be triggered in two ways:

#### Push a version tag

```bash
git tag v1.0.0
git push origin v1.0.0
```

This builds both Windows and Linux versions and automatically creates a
GitHub Release containing:

```text
FastCopyTool-Windows.zip
FastCopyTool-Linux.zip
```

#### Manual workflow

The workflow can also be started manually from the GitHub Actions page.

Manual builds are uploaded as workflow artifacts and are not published as
GitHub Releases.

## Project Structure

```text
FastCopyTool/
├── main.py
├── requirements.txt
├── setup.sh
├── setup.ps1
├── start.sh
└── start.bat
```

The setup scripts automatically create the required Python virtual environment
locally when needed.

The virtual environment is generated at runtime and should not be committed
to the repository.