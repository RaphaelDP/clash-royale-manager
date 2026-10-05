# Clash Royale Clan Manager — Roadmap

Updated: 2026-10-05 · Document version: 0.2.12

This replaces the assessment in `git-history.txt`; that historical file is
unchanged. Status describes local implementation, not a published release.
Application version: **0.9.7**. The four implementation commits are now on
`origin/main`. The [history and tag audit](git-history-audit.md) records the original
refs and the exact archive mapping for tag cleanup. Remote cleanup was verified
on 2026-10-02. [v0.9.7 release notes](release-0.9.7.md) record the accepted scope
and limitations; v1.0 qualification remains separate.

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
| v0.9 Production preparation | ✅ Implementation, deployment, restore, Discord, and visual checks complete |
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
- ✅ API observation, player win rate, and war participation totals are owned by
  services. Scripts orchestrate execution; dashboard helpers format the results.
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
- ✅ Home/Settings Close confirmation can stop the dashboard alone or both children.
  Tests verify actual socket release and scheduler survival. Compose uses on-failure
  restart so intentional full shutdown stays stopped; dashboard-only mode retains
  Docker's published binding until the container stops.
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

- Full isolated test suite: **222 passed**.
- Repository Black check: **72 files unchanged**.
- Repository Pylint check: **10.00/10**; shell syntax and diff whitespace checks pass.
- Synthetic query profile, Docker build/smoke test, and isolated live cycle: completed.
- Current working tree: `make ci` passes Black, Pylint (10.00/10), and all 222 tests.
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

## Fast path to v1.0

A real season boundary was observed on October 5. The remaining release blocker
is authoritative completed-history confirmation of the new inferred race. The other pending
features below are optional follow-ups, not additions to the v1.0 release gate.
[Qualification instructions](v1-qualification.md) give the isolated observation
command, first live baseline, and exact acceptance criteria. No observer runs in
the background and no production schedule was changed.

- ✅ Added repeatable, identity-only API observation with temporary runtime data.
- ✅ Explicit confirmation mode checks fresh completed history for an exact race,
  with distinct success, pending, and failure exit codes. The October 5 follow-up
  succeeded but still reported 137/0 pending; this is not a release qualification.
- ✅ Added regressions for inferred rollover confirmation, lagging live responses,
  repeated updates, recovery from a long gap, and worker isolation.
- ✅ First uncached live observation: completed season 136/section 2, inferred
  live season 136/section 3; explicit live season ID absent.
- ✅ Real transition captured on October 5: prior live 136/3 is now completed in
  API history; live section reset to zero and resolved to 137/0.
- ⬜ Confirm 137/0 in subsequent completed API history. The live response still
  omits season ID; inference success alone does not close this final field gate.
- ⬜ After qualification, prepare and check v1.0.0 release metadata and tag.

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
- 🟡 Real before/after season transition observed on October 5; prior live race
  136/3 confirmed by history. New inferred race 137/0 awaits authoritative history.
  Synthetic long-gap refusal/recovery tests pass; the field gate remains open.
  See the [qualification evidence](v1-qualification.md#real-transition-observed--2026-10-05).
- ✅ Discord delivery verified on 2026-10-02: one labeled diagnostic message was
  acknowledged by Discord; a repeated daily-job call sent no duplicate. Separate
  mocked subprocess checks passed for failed delivery, crash lock release, retry,
  and repeat suppression after restart. The post-delivery/pre-commit duplicate
  window remains documented; exactly-once delivery is not guaranteed.
- ✅ Host deployment technical checks passed: supervisor, scheduler, and Streamlit
  active; homepage and health HTTP 200; all seven jobs successful with no recorded
  errors; enabled scheduler and configured Discord confirmed. Production data and
  job state were not changed by these checks.
- ✅ Agent visual review of the deployed Home and six pages passed on 2026-10-02
  at desktop size, including charts, tables, cache freshness, and job health.
  Offline fallback is covered by backup-copy rendering and automated tests.
  The operator delegated this review; no human or exhaustive device test is claimed.
- ✅ Review the changes and record focused local commits.
- ✅ The four reviewed implementation commits are published on `origin/main`.
- ✅ Remote tag cleanup verified: all 15 archived names exist under `legacy/`,
  original aliases are absent, and the 19 primary tags remain unchanged.
- ✅ Operator approved v0.9.7 as a pre-1.0 release with the real-rollover limitation
  explicitly accepted. Release commit/tag were created locally; publication is a
  separate Git push. No v1.0 tag is authorized by this qualification.

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
