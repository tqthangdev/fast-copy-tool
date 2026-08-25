# setup.ps1 - Set up the environment to run Fast Copy Tool (Windows)
# Create a venv in the same directory as the code and install everything needed
# into it (PySide6 + psutil). With Qt6/PySide6, everything is installed in
# the venv via pip.

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

Write-Host "=== 1. Check Python ===" -ForegroundColor Cyan
$py = Get-Command py -ErrorAction SilentlyContinue
if (-not $py) {
    $py = Get-Command python -ErrorAction SilentlyContinue
}
if (-not $py) {
    Write-Host "Error: Python not found. Please install Python 3.8+ from https://www.python.org/downloads/" -ForegroundColor Red
    exit 1
}
& $py.Source --version

Write-Host ""
Write-Host "=== 2. Check robocopy (built into Windows) ===" -ForegroundColor Cyan
if (Get-Command robocopy -ErrorAction SilentlyContinue) {
    Write-Host "robocopy: OK" -ForegroundColor Green
} else {
    Write-Host "robocopy not found (unusual on Windows). Check your system PATH." -ForegroundColor Red
}

Write-Host ""
Write-Host "=== 3. Create a virtual environment in .\venv ===" -ForegroundColor Cyan
if (Test-Path "venv") {
    Write-Host "venv already exists, skipping creation."
} else {
    & $py.Source -m venv venv
    Write-Host "Created venv."
}

Write-Host ""
Write-Host "=== 4. Install Python packages into the venv (requirements.txt: PySide6 + psutil) ===" -ForegroundColor Cyan
& .\venv\Scripts\python.exe -m pip install --upgrade pip --quiet
& .\venv\Scripts\pip.exe install -r requirements.txt --quiet
& .\venv\Scripts\pip.exe list

Write-Host ""
Write-Host "=== 5. Verify PySide6 can be imported from the venv ===" -ForegroundColor Cyan
& .\venv\Scripts\python.exe -c "from PySide6 import QtCore; print('OK: PySide6', QtCore.__version__)"
& .\venv\Scripts\python.exe -c "import psutil; print('OK: psutil', psutil.__version__)"

Write-Host ""
Write-Host "=== Done! ===" -ForegroundColor Green
Write-Host "Run the program with:"
Write-Host "  .\venv\Scripts\python.exe main.py"
Write-Host "or activate the venv first:"
Write-Host "  venv\Scripts\activate; python main.py"