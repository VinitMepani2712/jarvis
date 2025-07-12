@echo off
REM ====== Jarvis Auto-Start ======
REM 1) Edit these two lines to match your setup:
set JARVIS_DIR=V:\Vinit\jarvis
set VENV_ACTIVATE=%JARVIS_DIR%\venv\Scripts\activate.bat

REM 2) Switch drive & directory
cd /d "%JARVIS_DIR%"
if errorlevel 1 (
    echo ERROR: Cannot cd into %JARVIS_DIR%
    pause
    exit /b 1
)

REM 3) (Optional) Activate virtualenv
if exist "%VENV_ACTIVATE%" (
    call "%VENV_ACTIVATE%"
) else (
    echo WARNING: venv activate script not found at %VENV_ACTIVATE%
)

REM 4) Launch Jarvis
python "%JARVIS_DIR%\jarvis_entry.py"
if errorlevel 1 (
    echo ERROR: Jarvis failed to start.
    pause
    exit /b 1
)

echo Jarvis started successfully.
pause
