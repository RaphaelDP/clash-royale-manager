#!/bin/bash
# Filename: start-macos.command
# Description: Launch the Docker dashboard with persistent runtime directories.
# Author: Raphael Smilet
# Date Created: 2026-08-06
# Last Modified: 2026-09-30
# Version: 0.1.1
set -e

cd "$(dirname "$0")/.."

if [ ! -f ".env" ]; then
    echo ""
    echo "============================================================"
    echo "  No .env file found!"
    echo "  Copy .env.example to .env and fill in your settings first."
    echo "============================================================"
    echo ""
    read -p "Press Enter to close..."
    exit 1
fi

echo "Starting Clash Royale Clan Manager..."
mkdir -p data logs backups
docker compose up -d --build

echo "Waiting for the dashboard to be ready..."
sleep 15

open "http://localhost:8501"

echo ""
echo "Dashboard should now be open in your browser."
echo "If it didn't load, wait a few more seconds and refresh."
echo ""
read -p "Press Enter to close this window..."