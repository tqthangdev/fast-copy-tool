# setup.ps1 - Set up the environment to run Fast Copy Tool (Windows)
# Create a venv in the same directory as the code and install everything needed
# into it (PySide6 + psutil).

$ErrorActionPreference = "Stop"

Set-Location -Path $PSScriptRoot


# ============================================================
# 1. Check Python
# ============================================================

Write-Host "=== 1. Check Python ===" -ForegroundColor Cyan

$py = Get-Command py -ErrorAction SilentlyContinue

if (-not $py) {
    $py = Get-Command python -ErrorAction SilentlyContinue
}

if (-not $py) {
    Write-Host "Error: Python not found." -ForegroundColor Red
    Write-Host "Please install Python 3.8+ from:" -ForegroundColor Red
    Write-Host "https://www.python.org/downloads/" -ForegroundColor Red
    exit 1
}

& $py.Source --version

if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Failed to run Python." -ForegroundColor Red
    exit 1
}


# ============================================================
# 2. Check robocopy
# ============================================================

Write-Host ""
Write-Host "=== 2. Check robocopy (built into Windows) ===" -ForegroundColor Cyan

if (Get-Command robocopy -ErrorAction SilentlyContinue) {
    Write-Host "robocopy: OK" -ForegroundColor Green
}
else {
    Write-Host "robocopy not found (unusual on Windows). Check your system PATH." -ForegroundColor Yellow
}


# ============================================================
# 3. Create virtual environment
# ============================================================

Write-Host ""
Write-Host "=== 3. Create a virtual environment in .\venv ===" -ForegroundColor Cyan

if (Test-Path ".\venv\Scripts\python.exe") {
    Write-Host "venv already exists, skipping creation." -ForegroundColor Yellow
}
else {
    if (Test-Path ".\venv") {
        Write-Host "venv directory exists but is incomplete." -ForegroundColor Yellow
        Write-Host "Removing broken venv..."
        Remove-Item ".\venv" -Recurse -Force
    }

    & $py.Source -m venv venv

    if ($LASTEXITCODE -ne 0) {
        Write-Host "Error: Failed to create virtual environment." -ForegroundColor Red
        exit 1
    }

    Write-Host "Created venv." -ForegroundColor Green
}


# ============================================================
# 4. Check requirements.txt
# ============================================================

Write-Host ""
Write-Host "=== 4. Check requirements.txt ===" -ForegroundColor Cyan

if (-not (Test-Path ".\requirements.txt")) {
    Write-Host "Error: requirements.txt not found." -ForegroundColor Red
    exit 1
}

Write-Host "requirements.txt: OK" -ForegroundColor Green


# ============================================================
# 5. Install Python packages
# ============================================================

Write-Host ""
Write-Host "=== 5. Install Python packages into the venv ===" -ForegroundColor Cyan

$venvPython = ".\venv\Scripts\python.exe"

if (-not (Test-Path $venvPython)) {
    Write-Host "Error: venv Python not found." -ForegroundColor Red
    exit 1
}

Write-Host "Upgrading pip..."

& $venvPython -m pip install --upgrade pip --quiet

if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Failed to upgrade pip." -ForegroundColor Red
    exit 1
}

Write-Host "Installing requirements.txt..."

& $venvPython -m pip install -r requirements.txt --quiet

if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Failed to install dependencies." -ForegroundColor Red
    exit 1
}

Write-Host "Installed packages:" -ForegroundColor Green

& $venvPython -m pip list


# ============================================================
# 6. Verify PySide6
# ============================================================

Write-Host ""
Write-Host "=== 6. Verify PySide6 ===" -ForegroundColor Cyan

& $venvPython -c "from PySide6 import QtCore; print('OK: PySide6', QtCore.__version__)"

if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: PySide6 verification failed." -ForegroundColor Red
    exit 1
}


# ============================================================
# 7. Verify psutil
# ============================================================

Write-Host ""
Write-Host "=== 7. Verify psutil ===" -ForegroundColor Cyan

& $venvPython -c "import psutil; print('OK: psutil', psutil.__version__)"

if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: psutil verification failed." -ForegroundColor Red
    exit 1
}


# ============================================================
# Done
# ============================================================

Write-Host ""
Write-Host "=== Done! ===" -ForegroundColor Green

Write-Host "Run the program with:"
Write-Host "  .\venv\Scripts\python.exe main.py"

Write-Host ""
Write-Host "Or activate the venv first:"
Write-Host "  venv\Scripts\activate"
Write-Host "  python main.py"