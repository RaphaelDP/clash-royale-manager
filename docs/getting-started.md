# Getting Started (No Coding Required)

This guide gets the Clan Manager dashboard running on your own computer,
even if you've never used a terminal before.

## 1. Install Docker Desktop (one-time)

Download and install Docker Desktop for your operating system:
https://www.docker.com/products/docker-desktop/

- Windows/macOS: run the installer like any other app, then open Docker
  Desktop once so it finishes setting up (you'll see a whale icon in your
  system tray/menu bar once it's ready).
- Linux: follow the Docker Engine install guide for your distribution,
  then make sure `docker compose` works from a terminal.

You only need to do this once.

## 2. Get the project files

Download this project (as a ZIP from GitHub, or via `git clone` if you're
comfortable with that) and unzip it somewhere on your computer.

## 3. Set up your settings

Inside the project folder:
1. Find the file `.env.example`.
2. Make a copy of it and rename the copy to `.env` (just `.env`, no other
   text before it).
3. Open `.env` in a text editor (Notepad, TextEdit, etc.) and fill in:
   - `CR_API_TOKEN` — your Clash Royale API token
   - `CLAN_TAG` — your clan's tag, including the `#`
   - `DISCORD_WEBHOOK_URL` — optional, only needed for Discord reports
4. Save the file.

## 4. Launch the dashboard

Inside the `launch/` folder, double-click the file for your operating
system:
- Windows: `start-windows.bat`
- macOS: `start-macos.command`
- Linux: `start-linux.sh`

**macOS note**: the first time, you may need to right-click the file and
choose "Open" instead of double-clicking, since it's not from a
registered developer. You may also need to make it executable first —
see Troubleshooting below.

A window will open showing progress. After about 15-30 seconds, your
browser should automatically open to the dashboard. If it doesn't, open
your browser and go to: http://localhost:8501

## 5. Stop the dashboard

Double-click the matching stop script in `launch/` whenever you're done.
Your data stays saved for next time — stopping just pauses everything.

## Where your data lives

- Live database: `data/clan_manager.db`
- Automatic daily backups: `backups/`
- Logs: `logs/clan_manager.log`

All of these are folders on your own computer, inside the project folder.

## Restoring from a backup

1. Stop the dashboard.
2. In the `backups/` folder, find the backup file you want (named with
   its date and time, e.g. `clan_manager_20260801_020000.db`).
3. Copy it into the `data/` folder and rename it to `clan_manager.db`,
   replacing the existing file.
4. Start the dashboard again.

## Troubleshooting

**"No .env file found" message**: make sure the file is named exactly
`.env`, not `.env.example` or `.env.txt`.

**macOS says the script can't be opened / permission denied**: open a
terminal in the project folder and run: