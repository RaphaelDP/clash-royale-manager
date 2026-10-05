# Clash Royale Clan Manager

A Streamlit dashboard for clan membership, war history, activity, contribution
scores, and leadership recommendations. Current version: **0.9.7**.
See the [release notes](docs/release-0.9.7.md) for verification and known limitations.

## Desktop installation (no coding)

Use the [graphical Docker launcher](launch/README.md) for Start, Open dashboard
and Stop all buttons. Install Docker once, then download the project and the
launcher for your system from a successful GitHub Actions build. Native builds
are being introduced after v0.9.7; that existing tag does not contain them.

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
- [Git history audit](docs/git-history-audit.md): tag cleanup and version policy.
- [Roadmap](docs/roadmap.md): implementation status and remaining release gates.

The dashboard supports Overview, Members, Player, Promotions, Wars, and Settings.
Recommendations assist leadership; they do not change clan roles through the API.
