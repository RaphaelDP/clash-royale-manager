# Clash Royale Clan Manager — Roadmap

Updated: 2026-10-02 · Document version: 0.2.6

This replaces the assessment in `git-history.txt`; that historical file is
unchanged. Status describes local implementation, not a published release.
Application version: **0.9.7.dev0**. The four implementation commits are now on
`origin/main`. The [history and tag audit](git-history-audit.md) records the original
refs and the exact archive mapping for tag cleanup.

Legend: ✅ implemented and locally checked; 🟡 remaining qualification; ⬜ pending.

## Capability baseline

| Milestone | Status |
| --- | --- |
| v0.0 Foundation | ✅ Python packages, dependency declarations, test tooling |
| v0.1 Database | ✅ Models, relationships, migration-driven initialization and repair |
| v0.2 API | ✅ Cached client, transient retries, validated atomic roster synchronization |
| v0.3 Collection | 🟡 Daily snapshots and race history; live season inference needs field verification |
| v0.4 Analytics | ✅ Activity, participation, contribution scores, rank recommendations |
| v0.5 Dashboard | ✅ Six pages with shared data preparation in `dashboard/functions.py` |
| v0.6 Analytics UI | ✅ Historical views, rankings, explicit profile-cache freshness and fallback |
| v0.7 Automation | ✅ Persistent schedule, reload, job health, same-job locking and daily guards |
| v0.8 Decision support | 🟡 Recommendations available; optional enhancements listed below |
| v0.9 Production preparation | 🟡 Implementation completed below; deployment verification remains |
| v1.0 Stable release | ⬜ Release gates remain; not released |

## Completed reliability work

### Packaging and dependencies

- ✅ Source-only ZIP built fresh and atomically replaced; synthetic tests verify
  stale secrets disappear, runtime files/symlinks are excluded, and migrations remain.
- ✅ Docker context excludes credentials, archives, and runtime data.
- ✅ The user deleted the obsolete archive; no archive contents were opened.
- ✅ Runtime dependencies have one source in `pyproject.toml`; requirements install
  the package, the collection entry point is corrected, and release version is centralized.
- ✅ Source-only Docker image build and dependency installation succeeded.

### Database and synchronization

- ✅ Historical missing-column migration corrected; a new repair revision covers
  already-stamped databases. Known unversioned schemas are checked before adoption.
- ✅ Startup upgrades the configured database through Alembic.
- ✅ Tests cover fresh schema, repeated initialization, old-schema upgrades,
  already-stamped repair, retained records, and refusal of unknown schemas.
- ✅ Roster validation and atomic updates prevent partial membership/departure writes.
- ✅ Race-log failures roll back the batch; historical participants need no live lookup.
- ✅ Current-race selection uses chronological history and handles tested rollover
  cases while preserving completed results. Missing/ambiguous identity fails visibly.
- ✅ Inferred live identity requires completed history aged zero to eight days and
  a supported section transition. Missing evidence, stale/future history, malformed
  IDs, and unexplained section gaps fail visibly without overwriting results.
- 🟡 The eight-day limit is an application policy; real season-boundary and stale
  API response behavior still need field verification.

### Dashboard and collection

- ✅ Pages render helper-prepared values, DataFrames, charts, and exports.
- ✅ Invalid refresh callback, duplicate Player controls, zero-valued slider ranges,
  closed-session history access, and missing-activity crashes are fixed.
- ✅ Current-roster rankings and growth exclude departed members; automatic
  snapshots include current members and skip same-day repeats.
- ✅ Attacks require positive deck usage; rows with zero decks are not attacks.
- ✅ Profile refresh bypasses both caches; invalid JSON and API failure retain a
  usable fallback. Successful loads also show cache freshness.
- ✅ Existing historical data is preserved; backup inspection was limited to the
  authorized disposable-copy rehearsal. Later deployment checks read job state
  and schema revision only; they did not modify the active database.

### Automation and operations

- ✅ Settings shows per-job attempts, success age, and errors.
- ✅ Intervals, daily times, and enabled state persist with validation and atomic writes.
- ✅ Separate scheduler reloads settings, retaining valid configuration after bad edits.
- ✅ Daily-job guards, membership marker consolidation, same-day catch-up, and
  process locks are implemented. Catch-up uses scheduled-time order.
- ✅ Startup failures and child-process exits are surfaced; shutdown is supervised.
- ✅ Compose persists backups, database, caches, logs, and schedule; Linux launcher
  supplies host UID/GID. Streamlit is the only advertised service port.
- ✅ Restore command validates a read-only source, refuses accidental replacement,
  checks sidecars, and atomically installs the copy. Synthetic restore tests added.
- ✅ Local and Compose log retention are configured.

### Documentation and performance

- ✅ README covers setup and isolated tests.
- ✅ [Operations](operations.md) covers configuration, scheduler semantics,
  deployment, backup/restore, and troubleshooting.
- ✅ [Architecture](architecture.md) describes data boundaries, known history
  limitations, migration behavior, and synthetic query measurements.
- ✅ Profiling identifies recommendation/scoring loops as the largest query-count
  targets. Batching optimization is a follow-up, not claimed complete.
- ✅ Regression coverage includes migration, synchronization rollback, cache fallback,
  daily-job retry, locks, schedule validation/reload, restore, and API failures.

## Local verification

- Full isolated test suite: **198 passed**.
- Repository Black check: **66 files unchanged**.
- Repository Pylint check: **10.00/10**; shell syntax and diff whitespace checks pass.
- Synthetic query profile, Docker build/smoke test, and isolated live cycle: completed.
- Current working tree: `make ci` passes Black, Pylint (10.00/10), and all 198 tests.
- The previous documentation pass covered 374 named functions across 48 Python
  files without changing executable syntax trees. New functions follow the same
  description, Args, and Returns convention. The module-length budget is 1,300 lines.
- Live-identity regression tests cover the age boundary, future timestamps, section
  gaps, missing history, malformed IDs, repeated rollover, and job failure reporting.
- The isolated live cycle also passed with the identity guard: 49 active members,
  11 races, same-day idempotency, and matching backup/restored table counts.
- The active production database was not modified; authorized deployment checks
  read job status and schema revision. Two existing backups were
  read with operator authorization for the isolated rehearsal documented in
  [Operations](operations.md#backup-copy-upgrade-and-restore-rehearsal--2026-10-02);
  original backup hashes were unchanged. Credentials were loaded privately for
  authorized live API and Discord checks, never for the offline backup rehearsal.

## Required gates before v1.0

- ✅ Isolated Docker smoke test passed on 2026-10-01: mount ownership, Streamlit
  health, both children, clean shutdown, container replacement, and backup/restore.
  Compose configuration also validates. Tests used synthetic bind-mounted data,
  disabled networking, and no published host ports; production rollout remains separate.
- ✅ Rehearsed upgrade and restore on disposable copies of the oldest and newest
  authorized backups (2026-09-11 and 2026-10-02). Original column values survived,
  repeated initialization was unchanged, restored contents matched, and SQLite
  integrity/foreign-key checks passed. Home and all six pages rendered without
  exceptions offline. Visual operator acceptance remains part of the deployment
  acceptance gate below.
- ✅ Live synchronization passed using authorized credentials, temporary data,
  and disabled Discord: members, history/current race, daily jobs, scoring, restore.
- ⬜ Verify actual season boundaries and prolonged stale/incomplete history; one
  successful live cycle does not establish those behaviors.
- ✅ Discord delivery verified on 2026-10-02: one labeled diagnostic message was
  acknowledged by Discord; a repeated daily-job call sent no duplicate. Separate
  mocked subprocess checks passed for failed delivery, crash lock release, retry,
  and repeat suppression after restart. The post-delivery/pre-commit duplicate
  window remains documented; exactly-once delivery is not guaranteed.
- ✅ Host deployment technical checks passed: supervisor, scheduler, and Streamlit
  active; homepage and health HTTP 200; all seven jobs successful with no recorded
  errors; enabled scheduler and configured Discord confirmed. Production data and
  job state were not changed by these checks.
- 🟡 Human visual acceptance for stale/partially unavailable data remains. Offline
  backup-copy page checks and host health checks pass, but do not replace this.
- ✅ Review the changes and record focused local commits.
- ✅ The four reviewed implementation commits are published on `origin/main`.
- ⬜ Publish the tag cleanup and create a release only after its acceptance gates pass.

## Optional enhancements after reliability gates

- ⬜ Dedicated player comparison UI.
- ⬜ Richer historical visualization and contribution-component explanations.
- ⬜ Editable scoring/recommendation thresholds with validation.
- ⬜ Batch recommendation/scoring queries based on the measured baseline.
- ⬜ Forecasting only after specifying a useful target, sufficient historical
  inputs, and an evaluation method. Existing trend charts are not predictions.

## Change and commit conventions

Use focused imperative conventional subjects such as `fix(sync): ...`,
`feat(scheduler): ...`, `test(reliability): ...`, and `docs(operations): ...`.
Preserve author and creation date; update Last Modified and individual file version.
Select staged paths deliberately and keep existing user edits in mind. Run
`make test` separately from formatting/lint checks. No commit is implied by a
completed local change. Reports list modified files and the concrete changes.
