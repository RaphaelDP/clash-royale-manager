#!/bin/bash
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
docker compose up -d --build

echo "Waiting for the dashboard to be ready..."
sleep 15

xdg-open "http://localhost:8501" 2>/dev/null || echo "Open http://localhost:8501 in your browser."

echo ""
echo "Dashboard should now be open in your browser."
echo ""
read -p "Press Enter to close this window..."