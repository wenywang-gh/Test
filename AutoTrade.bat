@echo off
REM Double-click this file on Windows to start Auto Trading Analyzer.
cd /d "%~dp0"

echo ========================================
echo   Auto Trading Analyzer
echo ========================================
echo.

REM Try the Windows Python Launcher first, then python3, then python
where py >nul 2>&1
if %errorlevel%==0 (
    echo Starting server...
    start "" http://localhost:8000
    py server.py --serve 8000
    goto :done
)

where python3 >nul 2>&1
if %errorlevel%==0 (
    echo Starting server...
    start "" http://localhost:8000
    python3 server.py --serve 8000
    goto :done
)

where python >nul 2>&1
if %errorlevel%==0 (
    echo Starting server...
    start "" http://localhost:8000
    python server.py --serve 8000
    goto :done
)

echo.
echo ERROR: Python is not installed or not in your PATH.
echo.
echo Install Python from https://www.python.org/downloads/
echo Make sure to check "Add Python to PATH" during installation.

:done
echo.
pause >nul
