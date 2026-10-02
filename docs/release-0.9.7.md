# v0.9.7 — Reliability and deployment qualification

Date: 2026-10-02 · Document version: 0.1.0

This pre-1.0 release closes the current reliability milestone. The operator
explicitly accepted the remaining real season-rollover observation limitation.
It is not a v1.0 stability declaration.

## Changes

- Centralized dashboard data preparation and improved empty-data/cache fallback.
- Atomic synchronization, migration repair, and conservative live-war identity.
- Persistent scheduler settings, job health, process locks, and daily retry guards.
- Supervised startup, persistent Docker data, source-only packaging, and restore.
- Complete function contracts and operational documentation.

## Verification

- 198 isolated tests; Makefile Black check and Pylint 10.00/10.
- Docker startup, shutdown, persistence, and restore with isolated data.
- Authorized live API cycle, daily idempotency, scoring, and backup/restore.
- Oldest/newest real-backup copies upgraded with original values preserved;
  restored contents matched and integrity/foreign-key checks passed.
- Host homepage and health HTTP 200; supervisor, scheduler, and UI active;
  all seven production jobs successful with no recorded errors.
- One diagnostic Discord delivery acknowledged; duplicate invocation suppressed.
  Mocked subprocess failure/crash/retry/restart checks passed without extra sends.
- Desktop browser review of Home and six deployed pages, including lower sections:
  no Streamlit exceptions or page-wide horizontal overflow; screenshots inspected.
  Backup-copy offline rendering and failure-path tests cover API unavailability.

See [Operations](operations.md) for the scope and evidence of these checks.

## Accepted limitations

- Real season rollover has not been observed with the new guard. Recent-history
  inference remains a heuristic; the eight-day cutoff is application policy.
  Actual boundary observation remains a v1.0 requirement.
- Discord delivery is not exactly once: a crash after delivery but before the
  success commit can lead to a duplicate on retry.
- Visual acceptance was delegated to the agent at desktop size. This does not
  establish human acceptance or exhaustive browser/mobile accessibility coverage.
- Dashboard access remains restricted to trusted operators; there is no login layer.

## Upgrade

Back up the database before upgrading. Startup runs Alembic to `a2026093001`.
Follow the [backup and restore procedure](operations.md#backup-and-restore).
Restart the application after installing the release so long-lived processes
load its version and code. Release publication does not itself restart deployment.
