@echo off
setlocal
chcp 65001 >nul
title RAG Build and Eval
cd /d "%~dp0"

set "PROJECT_DIR=%~dp0"
if "%PROJECT_DIR:~-1%"=="\" set "PROJECT_DIR=%PROJECT_DIR:~0,-1%"
set "PYTHON_EXE=%PROJECT_DIR%\.venv\Scripts\python.exe"
if defined RAG_PYTHON set "PYTHON_EXE=%RAG_PYTHON%"

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

echo Building index...
"%PYTHON_EXE%" scripts\build_index.py
if errorlevel 1 (
    echo.
    echo Index build failed.
    pause
    exit /b 1
)

echo Running evaluation...
"%PYTHON_EXE%" scripts\run_eval.py
if errorlevel 1 (
    echo.
    echo Evaluation failed.
    pause
    exit /b 1
)

echo.
echo Build and evaluation completed.
pause
exit /b 0
