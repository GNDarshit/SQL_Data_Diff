@echo off
title SQL Diff - Server Startup
color 0A
echo.
echo  ==========================================
echo    SQL Diff - Data Comparison Engine
echo  ==========================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo  ERROR: Python not found.
    echo  Download: https://python.org/downloads
    echo  Check "Add Python to PATH" during install.
    pause & exit /b 1
)

REM Install packages
echo  Installing Python packages (flask, pyodbc)...
pip install flask flask-cors pyodbc --quiet
echo  Packages ready.
echo.

REM Check ODBC driver
echo  Checking SQL Server ODBC driver...
python -c "import pyodbc; d=[x for x in pyodbc.drivers() if 'sql' in x.lower()]; print(len(d),d[0] if d else '')" > "%TEMP%\_sqldiff.txt" 2>&1
set /p DRV=<"%TEMP%\_sqldiff.txt"
echo  Driver check: %DRV%

if "%DRV:~0,1%"=="0" (
    echo.
    echo  ============================================================
    echo   WARNING: No SQL Server ODBC Driver Installed!
    echo  ============================================================
    echo   Error you will see: IM002 - Data source name not found
    echo.
    echo   FIX - Download and install the driver:
    echo   https://aka.ms/downloadmsodbcsql
    echo.
    echo   After installing, restart this bat file.
    echo  ============================================================
    echo.
    echo  Opening download page in browser...
    start https://aka.ms/downloadmsodbcsql
    echo.
    echo  (The app will still start, install driver then refresh)
    echo.
    pause
)

echo.
echo  Starting server at http://localhost:5000
echo  Browser will open automatically.
echo  Press Ctrl+C to stop.
echo.
start /b cmd /c "timeout /t 2 /nobreak >nul && start http://localhost:5000"
python server.py
pause
