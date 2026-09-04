@echo off
setlocal EnableExtensions

rem ============================================================
rem Fast Copy Tool - Windows launcher
rem
rem - Run from the project directory
rem - Use .\venv\Scripts\python.exe
rem - If dependencies are missing, run setup.ps1
rem - Then launch main.py
rem ============================================================

cd /d "%~dp0"

set "PY=%~dp0venv\Scripts\python.exe"


rem ============================================================
rem Check dependencies
rem ============================================================

:check_dependencies

if not exist "%PY%" (
    goto :install
)

"%PY%" -c "import importlib.util,sys; required=('PySide6','psutil'); missing=[name for name in required if importlib.util.find_spec(name) is None]; print('Missing:', ', '.join(missing)) if missing else None; sys.exit(1 if missing else 0)"

if not errorlevel 1 (
    goto :launch
)


rem ============================================================
rem Install dependencies
rem ============================================================

:install

echo.
echo Dependencies not installed.
echo.

if not exist "%~dp0requirements.txt" (
    echo ERROR: requirements.txt not found.
    echo.
    exit /b 1
)

if not exist "%~dp0setup.ps1" (
    echo ERROR: setup.ps1 not found.
    echo.
    exit /b 1
)

echo Installing dependencies...
echo This may take a few minutes.
echo.

powershell.exe ^
    -NoProfile ^
    -ExecutionPolicy Bypass ^
    -File "%~dp0setup.ps1"

if errorlevel 1 (
    echo.
    echo ERROR: Installation failed.
    echo.
    exit /b 1
)


rem ============================================================
rem Verify installation
rem ============================================================

echo.
echo Verifying installation...
echo.

if not exist "%PY%" (
    echo ERROR: Virtual environment was not created.
    echo.
    exit /b 1
)

"%PY%" -c "import importlib.util,sys; required=('PySide6','psutil'); missing=[name for name in required if importlib.util.find_spec(name) is None]; print('Missing:', ', '.join(missing)) if missing else print('All dependencies are installed.'); sys.exit(1 if missing else 0)"

if errorlevel 1 (
    echo.
    echo ERROR: Installation failed.
    echo Required dependencies are still missing.
    echo.
    exit /b 1
)


rem ============================================================
rem Launch application
rem ============================================================

:launch

if not exist "%~dp0main.py" (
    echo.
    echo ERROR: main.py not found.
    echo.
    exit /b 1
)

echo.
echo Starting Fast Copy Tool...
echo.

"%PY%" "%~dp0main.py"

set "EXIT_CODE=%errorlevel%"

if not "%EXIT_CODE%"=="0" (
    echo.
    echo Fast Copy Tool exited with code %EXIT_CODE%.
    echo.
)

exit /b %EXIT_CODE%