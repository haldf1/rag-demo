@echo off
setlocal
chcp 65001 >nul
title RAG Production Server
cd /d "%~dp0"

set "PORT=%~1"
if "%PORT%"=="" set "PORT=8765"
set "RAG_UI_HOST=0.0.0.0"
set "RAG_UI_PORT=%PORT%"
set "PROJECT_DIR=%~dp0"
if "%PROJECT_DIR:~-1%"=="\" set "PROJECT_DIR=%PROJECT_DIR:~0,-1%"
set "PYTHON_EXE=%PROJECT_DIR%\.venv\Scripts\python.exe"
if defined RAG_PYTHON set "PYTHON_EXE=%RAG_PYTHON%"

echo.
echo ============================================================
echo  RAG production server is starting...
echo  Host: 0.0.0.0
echo  Port: %PORT%
echo  Local URL: http://localhost:%PORT%
echo  Log file: _ui_server.log
echo  If LAN or mobile cannot connect, run allow_firewall.bat once.
echo ============================================================
echo.
echo LAN access URLs:
powershell -NoProfile -Command "$port=%PORT%; Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue | Where-Object { $_.IPAddress -ne '127.0.0.1' -and $_.AddressState -eq 'Preferred' } | ForEach-Object { Write-Host ('  {0,-24} http://{1}:{2}' -f $_.InterfaceAlias, $_.IPAddress, $port) }"
echo.

netstat -ano | findstr /R /C:":%PORT% .*LISTENING" >nul
if not errorlevel 1 (
    echo Port %PORT% is already in use.
    echo The existing listener is:
    netstat -ano | findstr /R /C:":%PORT% .*LISTENING"
    echo.
    echo Close the existing RAG server or start with another port:
    echo   start_production.bat 9000
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

start "" /b powershell -NoProfile -WindowStyle Hidden -Command "$url='http://localhost:%PORT%'; for($i=0; $i -lt 240; $i++){ try { $response=Invoke-WebRequest -UseBasicParsing -Uri $url -TimeoutSec 2; if($response.StatusCode -ge 200){ Start-Process $url; exit 0 } } catch {}; Start-Sleep -Seconds 1 }"

"%PYTHON_EXE%" -u scripts\run_server.py
if errorlevel 1 (
    echo.
    echo Startup failed, check _ui_server.log for details.
)
echo.
echo Server stopped.
pause
