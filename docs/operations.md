# Operations guide

Updated: 2026-10-02 · Document version: 0.1.6

## Configuration

Run from the repository root. Normal execution loads `.env`; environment values
take precedence. `PYTHON_DOTENV_DISABLED=1` prevents loading credential files and
is set by the isolated test runner.

| Variable | Default / purpose |
| --- | --- |
| `CR_API_TOKEN` | Required for API requests. |
| `CLAN_TAG` | Required clan tag, including `#`. |
| `DATABASE_URL` | `sqlite:///data/clan_manager.db`. Supported deployment and backup workflow uses SQLite. |
| `LOG_LEVEL` | `INFO`. |
| `LOG_FILE` | `logs/clan_manager.log`. Local rotation: 1 MB, five retained files. |
| `SCHEDULER_TIMEZONE` | `Europe/Paris`. Daily scheduling and application dates use this timezone. |
| `DISCORD_WEBHOOK_URL` | Optional; blank disables delivery. |
| `SCHEDULER_CONFIG_FILE` | `data/scheduler.json`; persisted editable schedule. |
| `JOB_LOCK_DIR` | `data/locks`; must be shared by dashboard and scheduler processes. |

Score weights, recommendation bands, inactivity thresholds, and backup retention
(14 files per database stem) are in `app/core/constants.py`. They are not editable
through Settings. HTTP responses are cached for 300 seconds under `data/cache`.
Player profiles have a separate JSON cache; Player refresh bypasses both caches.

## Scheduler and manual execution

Settings displays each job's last attempt, last success, success age, and error.
It also saves validated intervals (1–1440 minutes), daily times (`HH:MM`), and an
enabled switch. Saves replace the JSON atomically. The scheduler reloads changes
within roughly five seconds. Invalid edits retain the last valid running schedule;
an invalid file at startup prevents scheduler startup. A running job finishes even
if scheduling is disabled. Manual actions remain available while disabled.

| Job | Default |
| --- | --- |
| Member / war synchronization | Every 60 minutes |
| Daily snapshots | 00:00 |
| Membership-day increment | 00:05 |
| Scores | 00:30 |
| Discord report | 01:00 |
| Backup | 02:00 |

One worker executes scheduled jobs. On startup, daily jobs whose time has passed
and which lack a success today are queued in scheduled-time order. Earlier missed
days are not recreated. Reload changes future schedules without catch-up. Scores
and synchronization can be rerun manually. Successful daily snapshots, reports,
and backups are guarded by persisted day markers; failed jobs may retry. Membership
increments own an atomic day marker, including migration of the older job name.
Automatic snapshots also skip members already collected today.

OS locks prevent overlapping executions of the same job across processes on one
host/shared lock directory. They are not a distributed scheduling system. A crash
between Discord delivery and saving success can duplicate a report on retry.
A skipped report with no webhook is considered successful for that day.

## Docker deployment

Create your `.env` and runtime directories first:

```bash
mkdir -p data logs backups
docker compose up -d --build
docker compose ps
```

On Linux with a non-1000 user, match ownership with:

```bash
CLAN_UID=$(id -u) CLAN_GID=$(id -g) docker compose up -d --build
```

The Linux launcher sets these values automatically. Compose mounts `data`, `logs`,
and `backups`, so database, caches, schedule, and backups survive container
replacement. The image runs as UID/GID 1000 by default. Host directories must be
writable by the selected identity. Streamlit uses port 8501; there is no FastAPI
service or port 8000. Restrict dashboard access to trusted operators: Settings
exposes administrative actions and there is no application login layer.

Startup migrates, attempts collection, and supervises both children. A child exit
stops the supervisor, allowing Compose's restart policy to act. Shutdown requests
termination, waits up to 20 seconds per child, then kills remaining children.
Compose supplies an init process and a 45-second grace period. Its stdout logs
rotate at 10 MB with three files. Health probes check Streamlit's health endpoint;
they do not prove API freshness or successful scheduled jobs.

Source archives and Docker contexts exclude runtime data and credential files.
`python -m scripts.package_release` creates a fresh ZIP atomically instead of
updating entries in an old archive. The archive includes migration code.

## Backup and restore

Create a SQLite hot backup:

```bash
python -m scripts.backup_db
```

Restore while **all application processes are stopped**. The restore command
validates SQLite integrity and writes a temporary database before replacing the
destination; the source backup is opened read-only. Existing destinations require
`--replace`; remaining SQLite sidecars cause refusal. Keep the current database
as an additional rollback copy before replacing it.

```bash
docker compose stop
python -m scripts.restore_db backups/CHOSEN_BACKUP.db data/clan_manager.db --replace
python -m scripts.init_db
docker compose up -d
```

Use the project's Python environment for these commands. For a restore rehearsal,
restore into a separate temporary directory and point `DATABASE_URL` there before
initialization. Check member/history counts and inspect all pages before using a
restored database in production. Never delete WAL files from a running database.

## Troubleshooting

- **403:** check the token and its authorized public IP. Permanent 4xx failures
  are not retried; transient connection errors, timeouts, 429, and 5xx are retried.
- **Stale player:** inspect cache freshness, then refresh. Failed refreshes retain
  the last valid profile; invalid cached JSON does not crash the page.
- **Stale clan/war:** check Settings job status and retry the relevant manual action.
  Historical race-log synchronization can succeed before current-race sync fails;
  the overall job records failure, with historical results retained.
- **Ambiguous live season:** synchronize race history first. A live response without
  an explicit season ID requires completed history no more than eight days old,
  with no future timestamp and a supported section transition. The limit is the
  application policy `MAX_LIVE_HISTORY_AGE_DAYS`, not an API guarantee. If refreshed
  history still cannot identify the season, the live sync stays failed and retains
  existing results. See limitations in the architecture guide.
- **Unknown schema:** initialization refuses unrecognized legacy tables or
  constraints. Preserve a backup and review a copy instead of stamping it blindly.
- **Permission denied:** verify bind-directory ownership and UID/GID settings.
- **Disk full:** free sufficient space before migrations, backups, packaging, or
  image builds. Avoid retrying file-writing tools against a full filesystem.

## Verification status

Docker build, isolated startup, mount ownership, container replacement, shutdown,
and backup restore checks passed on 2026-10-01 after clearing the pip download cache.
An authorized live API cycle also passed using temporary data and disabled Discord.
The live check collected 49 current members and 11 races; repeated daily jobs
were idempotent, and restored table counts matched the temporary source database.
The earlier isolated checks did not inspect or upgrade the active production
database. The subsequent authorized deployment checks are recorded below.

### Backup-copy upgrade and restore rehearsal — 2026-10-02

With operator authorization, the oldest and newest available backups were opened
read-only and restored into temporary directories. Credentials were not loaded;
API requests were forced offline and Discord was disabled. Temporary copies,
logs, and caches were removed after each run. Source backup SHA-256 checks before
and after the rehearsal matched.

| Backup | Starting revision | Final revision | Members | Races | Snapshots | Participations |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| `clan_manager_20260911_172712.db` | `6099e0c591ac` | `a2026093001` | 139 | 18 | 3,523 | 1,187 |
| `clan_manager_20261002_082628.db` | `a2026093001` | `a2026093001` | 155 | 22 | 5,553 | 1,436 |

Both copies passed SQLite integrity and foreign-key checks. Upgrade preserved all
original non-Alembic column values, including scores and job records. A second
initialization changed no table contents. The application backup and restore
functions produced identical table contents to the upgraded copy.

Streamlit AppTest rendered Home and all six pages against each upgraded copy with
zero exceptions while API requests failed locally. Rendering did not change the
database contents. This verifies automated rendering and offline fallback, not
visual operator acceptance or successful live refresh on the target deployment.


### Host deployment and Discord acceptance — 2026-10-02

The deployment runs directly on the host, with the project supervisor, scheduler,
and Streamlit processes active. No Docker containers were running. Both the
Streamlit health endpoint and homepage returned HTTP 200. Read-only inspection
of production job state found all seven jobs successful with no recorded errors;
member and war synchronization last succeeded at 13:26 Europe/Paris. The database
revision is `a2026093001`. No production database writes, process restarts, or
scheduler-setting changes were performed by these acceptance checks.

The scheduler uses its enabled default schedule, including the Discord report at
01:00 Europe/Paris. A webhook was already configured, so enabling or replacing it
was unnecessary. Today's production report job had already recorded success.

One explicitly labeled diagnostic message was sent through the real daily-report
job using a temporary database and substituted diagnostic report text. Discord
returned HTTP 200 with a message ID and matching content (`wait=true`). Repeating
the job produced no second HTTP request. Production report state was unchanged;
credentials and webhook values were never printed.

Separate subprocesses with mocked delivery verified failure-state persistence,
OS lock release after an abrupt process exit, successful retry after restart, and
same-day suppression in another process after success. These recovery tests sent
no external messages. They do not establish exactly-once delivery: a crash after
Discord accepts a message but before the success marker commits can still produce
a duplicate on retry, as documented above.

Technical deployment and delivery checks passed. The earlier backup-copy tests
cover offline page rendering. On 2026-10-02, an agent browser review of the actual
host deployment inspected Home and all six pages at 1440 × 1100, including lower
page sections. Navigation, metrics, tables, charts, profile-cache age, live-race
status, and Settings rendered without Streamlit exceptions or page-wide horizontal
overflow. No refresh, report, or settings-save actions were clicked. This is an
agent visual check, not a claim of human acceptance or exhaustive device coverage.

The operator accepted the unobserved real season-rollover limitation for v0.9.7.
Actual boundary observation remains required before v1.0; simulated transitions
and one successful live cycle cannot establish that field behavior.
