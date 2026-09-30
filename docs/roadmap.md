# Clash Royale Clan Manager — Roadmap

Updated: 2026-09-30 · Document version: 0.2.1

This replaces the assessment in `git-history.txt`; that historical file is
unchanged. Status describes local implementation, not a published release.
Application version: **0.9.7.dev0**. GitHub main was previously verified at
`cac66ad` before this work. Changes are being recorded as local commits after
the [history and tag audit](git-history-audit.md); remote refs remain unchanged.

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
- 🟡 Season inference without an explicit API season ID assumes recent history;
  prolonged gaps and live season-boundary responses still need verification.

### Dashboard and collection

- ✅ Pages render helper-prepared values, DataFrames, charts, and exports.
- ✅ Invalid refresh callback, duplicate Player controls, zero-valued slider ranges,
  closed-session history access, and missing-activity crashes are fixed.
- ✅ Current-roster rankings and growth exclude departed members; automatic
  snapshots include current members and skip same-day repeats.
- ✅ Attacks require positive deck usage; rows with zero decks are not attacks.
- ✅ Profile refresh bypasses both caches; invalid JSON and API failure retain a
  usable fallback. Successful loads also show cache freshness.
- ✅ Existing historical data is preserved; no private database was inspected or rewritten.

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

- Full isolated test suite: **175 passed**.
- Repository Black check: **65 files unchanged**.
- Repository Pylint check: **10.00/10**; shell syntax and diff whitespace checks pass.
- Synthetic query profile and source-only Docker build: completed.
- Credentials and existing runtime data: not read or modified.

## Required gates before v1.0

- ⬜ Run an isolated Docker container smoke test: mounted-directory ownership,
  Streamlit health, child shutdown, container replacement, and backup persistence.
  The image built, but the disk filled before this test; its temporary image/cache
  were removed to recover space. No deployment success is claimed.
- ⬜ Rehearse upgrade and restore against an operator-provided disposable database
  copy; compare member/history counts and inspect the resulting dashboard.
- ⬜ Verify live API synchronization and boundary behavior with authorized test
  credentials, including stale/incomplete history. No private credentials were used.
- ⬜ Verify optional Discord delivery and documented crash/retry behavior if enabled.
- ⬜ Complete an operator acceptance pass for stale/partially unavailable data on
  the intended deployment. Local automated page tests do not replace this check.
- ✅ Review the changes and record focused local commits.
- ⬜ Publish the reviewed commits and tag a release only after its gates pass.

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
