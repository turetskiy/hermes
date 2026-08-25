@echo off
REM Double-click launcher (Windows): starts Hermes without opening a terminal manually.
REM A console window opens to run this - that's the app's server console. It closes the
REM server automatically once you close the last Hermes tab in your browser; this only
REM waits for a keypress if something actually went wrong, so you can read the error.
cd /d "%~dp0"

where python >nul 2>nul
if %errorlevel% neq 0 (
    echo Python 3 isn't installed. Get it from https://www.python.org/downloads/ and try again.
    pause
    exit /b 1
)

python code\app.py
if errorlevel 1 (
    echo.
    echo Hermes exited with an error - see above.
    pause
)
