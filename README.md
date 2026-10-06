# Clash Royale Clan Manager

A Streamlit dashboard for clan membership, war history, activity, contribution
scores, and leadership recommendations. Current version: **0.9.8rc1** (tag `v0.9.8-rc.1`, release candidate).
See the [release candidate notes](docs/roadmap.md#v098-rc1-release-candidate) for verification and remaining checks.

## Desktop installation (no coding)

The recommended desktop setup is a graphical launcher **plus Docker**. Docker
runs the dashboard, scheduler and database environment; the launcher supplies
Start, Open dashboard and Stop all buttons. Python is not required on your
computer when using a compiled launcher. Docker installation is still required.
The former platform start/stop scripts have been replaced by this launcher.

## First installation (no coding)

1. Install Docker Desktop on Windows or macOS, or Docker Engine with Compose on
   Linux. Start Docker before opening the launcher.
2. Download and extract the `project-source` artifact from the same successful
   GitHub Actions run as your launcher. Extract its inner `project.zip` as well.
   Keep this project folder: it contains your configuration and persistent data.
3. Download the launcher artifact for your system. Extract the archive(s), then
   put `windows_launcher.exe`, `macos_launcher.app`, or `linux_launcher.AppImage`
   in `launch/windows/`, `launch/macos/`, or `launch/linux/` respectively. For macOS, choose `launcher-macos-15` for Apple Silicon (M-series)
   or `launcher-macos-15-intel` for Intel. The new Apple Silicon build must first
   pass its workflow run. These builds are unsigned and not notarized.
4. Open the launcher. On Linux, allow execution in the file's Properties if
   needed; AppImage may require your distribution's FUSE compatibility package.
5. The launcher finds its application folder automatically. Folder selection
   appears only if the launcher was moved away from the application files.
   Click **Start and open**. The first build needs Internet access and can take
   several minutes.
6. The launcher copies the entire `.env.example` to `.env` if it is missing.
   **Application settings** shows all template fields, with secrets masked.
   Complete the required fields; Discord is optional and may stay blank. Existing
   configuration, comments and custom settings are preserved. Obtain an API token
   at <https://developer.clashroyale.com>, allowing your computer's public IP.
   The main window displays a local configuration summary without revealing tokens.
   After saving changes, **Start and open** restarts the container as needed to
   load them, without rebuilding the image. Cancel leaves existing values unchanged.

Closing the browser or launcher leaves the application running. **Stop all**
stops this project's dashboard and scheduler, preserving `data/`, `logs/` and
`backups/`. Normal startup reuses the installed image. Reopening a closed dashboard keeps
the existing scheduler running and does not repeat initial collection.
After downloading new application source, click **Update application** once to
rebuild and replace the container; this restarts the scheduler and preserves data.
Older installations need this one-time update to support dashboard-only resume.
The dashboard's Close control is available in the sidebar. In Docker, use
**Stop all** to release the published port completely.

If startup fails, check Docker Desktop's container status/logs. Do not post tokens
or unredacted configuration files. A failed health check leaves the container
available for inspection or for stopping through the launcher.


## Get started with Python

Use Python 3.12 or newer. Run these commands from the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
cp .env.example .env
```

On Windows, activate with `.venv\Scripts\activate`. Edit your local `.env`:
set `CR_API_TOKEN` and `CLAN_TAG` (including `#`). Configure the API token's
allowed IP address in the Clash Royale developer portal. Keep credentials local.
Discord is optional; leave `DISCORD_WEBHOOK_URL` blank to disable reports.

```bash
python -m scripts.init_db
python -m scripts.run_app
```

Open <http://localhost:8501>. Startup upgrades the schema and attempts collection,
then supervises the scheduler and dashboard. Collection failures are recorded;
existing data remains available. An incompatible schema prevents startup.
Back up an existing database before upgrading it.

## Development

```bash
make test                         # isolated databases, dummy credentials, no .env loading
make check                        # project formatting and lint checks
python -m scripts.package_release # fresh source-only ZIP
```

Application dependencies are declared in `pyproject.toml`; requirements files
install that package. Per-file header versions describe edits to individual files;
`app.__version__` is the application version. No stable v1.0 release is claimed.

## Documentation

- [Operations](docs/operations.md): configuration, Docker, schedules, backups,
  restore, and troubleshooting.
- [Architecture and metrics](docs/architecture.md): responsibilities, data
  semantics, limitations, and synthetic performance measurements.
- [Roadmap](docs/roadmap.md): implementation status and remaining release gates.

The dashboard supports Overview, Members, Player, Promotions, Wars, and Settings.
Recommendations assist leadership; they do not change clan roles through the API.
