@echo off
setlocal
chcp 65001 >nul
title RAG Demo Server
cd /d "%~dp0"

set "PROJECT_DIR=%~dp0"
if "%PROJECT_DIR:~-1%"=="\" set "PROJECT_DIR=%PROJECT_DIR:~0,-1%"
set "PYTHON_EXE=%PROJECT_DIR%\.venv\Scripts\python.exe"
if defined RAG_PYTHON set "PYTHON_EXE=%RAG_PYTHON%"
set "UI_PORT=8765"
if defined RAG_UI_PORT set "UI_PORT=%RAG_UI_PORT%"

echo.
echo ============================================================
echo  RAG demo is starting, please wait...
echo  First start loads local models, about 1-3 minutes.
 echo  Open http://127.0.0.1:%UI_PORT% when ready.
echo  Log file: _ui_server.log
echo ============================================================
echo.

netstat -ano | findstr /R /C:":%UI_PORT% .*LISTENING" >nul
if not errorlevel 1 (
    echo Port %UI_PORT% is already in use.
    echo The existing listener is:
    netstat -ano | findstr /R /C:":%UI_PORT% .*LISTENING"
    echo.
    echo Close the existing RAG server or set another port before starting.
    echo.
    pause
    exit /b 1
)

if not exist "%PYTHON_EXE%" (
    echo Project virtual environment was not found:
    echo   %PYTHON_EXE%
    echo.
    echo Create it with:
    echo   python -m venv .venv
    echo   .venv\Scripts\python.exe -m pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

"%PYTHON_EXE%" -u scripts\run_server.py
if errorlevel 1 (
    echo.
    echo  Startup failed, check _ui_server.log for details.
)
echo.
pause
