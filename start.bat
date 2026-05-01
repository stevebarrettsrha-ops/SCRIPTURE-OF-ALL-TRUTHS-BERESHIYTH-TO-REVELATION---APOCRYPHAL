@echo off
REM ===============================================================
REM  The Besorah - one-click launcher (Windows)
REM  Double-click this file to start a local server and open the
REM  reader in your default browser. Close this window to stop.
REM ===============================================================

cd /d "%~dp0"

set PORT=8000

REM Pick whichever python launcher exists on this machine.
where py >nul 2>nul
if %ERRORLEVEL%==0 (
    set PYTHON=py -3
    goto :run
)
where python >nul 2>nul
if %ERRORLEVEL%==0 (
    set PYTHON=python
    goto :run
)
where python3 >nul 2>nul
if %ERRORLEVEL%==0 (
    set PYTHON=python3
    goto :run
)

echo.
echo Python is not installed or not on PATH.
echo Install Python 3 from https://www.python.org/downloads/
echo and tick "Add Python to PATH" during setup, then run this file again.
echo.
pause
exit /b 1

:run
echo Starting The Besorah on http://localhost:%PORT%/
echo Close this window to stop the server.
start "" http://localhost:%PORT%/
%PYTHON% -m http.server %PORT%
