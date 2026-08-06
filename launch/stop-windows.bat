@echo off
cd /d "%~dp0.."
echo Stopping Clash Royale Clan Manager...
docker compose down
echo.
echo Stopped.
pause