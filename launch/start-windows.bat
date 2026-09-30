REM Filename: start-windows.bat
REM Description: Launch the Docker dashboard with persistent runtime directories.
REM Author: Raphael Smilet
REM Date Created: 2026-08-06
REM Last Modified: 2026-09-30
REM Version: 0.1.1
@echo off
setlocal

cd /d "%~dp0.."

if not exist ".env" (
    echo.
    echo ============================================================
    echo   No .env file found!
    echo   Copy .env.example to .env and fill in your settings first.
    echo ============================================================
    echo.
    pause
    exit /b 1
)

echo Starting Clash Royale Clan Manager...
if not exist data mkdir data
if not exist logs mkdir logs
if not exist backups mkdir backups
docker compose up -d --build

echo Waiting for the dashboard to be ready...
timeout /t 15 /nobreak >nul

start "" "http://localhost:8501"

echo.
echo Dashboard should now be open in your browser.
echo If it didn't load, wait a few more seconds and refresh.
echo.
pause