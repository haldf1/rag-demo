@echo off
setlocal
chcp 65001 >nul
title RAG Firewall Setup

set "PORT=%~1"
if "%PORT%"=="" set "PORT=8765"

net session >nul 2>&1
if errorlevel 1 (
    echo Administrator permission is required.
    echo A UAC prompt will open. Choose "Yes" to allow the firewall rule.
    powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -ArgumentList '%PORT%' -Verb RunAs"
    exit /b
)

echo.
echo Adding Windows Firewall rule for TCP port %PORT%...
netsh advfirewall firewall delete rule name="RAG Demo %PORT%" >nul 2>&1
netsh advfirewall firewall add rule name="RAG Demo %PORT%" dir=in action=allow protocol=TCP localport=%PORT% profile=any

if errorlevel 1 (
    echo.
    echo Failed to add the firewall rule.
) else (
    echo.
    echo Firewall rule created successfully.
    echo LAN and mobile hotspot clients can now access this computer on port %PORT%.
)
echo.
pause
