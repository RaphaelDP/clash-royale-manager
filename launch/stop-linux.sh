#!/bin/bash
cd "$(dirname "$0")/.."
echo "Stopping Clash Royale Clan Manager..."
docker compose down
echo ""
echo "Stopped."
read -p "Press Enter to close this window..."