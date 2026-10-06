# Clash Royale Clan Manager — Roadmap

Updated: 2026-10-06 · Document version: 0.3.1

This replaces the assessment in `git-history.txt`; that historical file is
unchanged. Status describes local implementation, not a published release.
Application version: **0.9.8rc1**, matching annotated candidate tag
`v0.9.8-rc.1`. The last finalized release remains `v0.9.7`. The [history and tag audit](roadmap.md#git-history-and-tag-audit) records the original
refs and the exact archive mapping for tag cleanup. Remote cleanup was verified
on 2026-10-02. [v0.9.7 release notes](roadmap.md#v097-release-record) record the accepted scope
and limitations; v1.0 qualification remains separate.

Legend: ✅ implemented and locally checked; 🟡 remaining qualification; ⬜ pending.

## v0.9.8-rc.1 release candidate

Prepared 2026-10-06. Canonical Python/package version: `0.9.8rc1`;
annotated Git tag: `v0.9.8-rc.1`. Existing tags are unchanged.

- Native launcher folders, SVG-derived platform/window icons, shared settings UI
  and automatic `.env.example` initialization.
- Reliable dashboard resume, startup retries and interrupted-refresh cleanup.
- Documentation consolidated into four guides; obsolete start/stop scripts removed.
- Local qualification: 238 tests passed, Makefile Black clean and Pylint 10/10;
  Linux AppImage icon/startup checks, source archive exclusions and documentation
  links verified.
- Still required: run the updated four-platform GitHub build matrix, inspect its
  artifacts and verify installed behavior. Windows/Intel macOS passed earlier
  packaging smoke checks; this candidate and Apple Silicon require a fresh run.
- v1.0 still requires authoritative completed-history confirmation for 137/0.
  This candidate does not waive that gate or declare a stable release.

Push the branch and this specific candidate tag to trigger the launcher workflow.
Do not move a published tag; use a new candidate version if fixes are needed.

## Desktop distribution and navigation follow-up

- ✅ Graphical Docker launcher and locally smoke-tested Linux AppImage.
- ✅ Docker page-content bleeding reproduced and corrected by disabling telemetry
  writes to an unwritable home; explicit navigation isolates page rendering.
- 🟡 Windows/Intel macOS previously passed build smoke checks; the reorganized
  icon-enabled builds and Apple Silicon variant await a new workflow run.
- 🟡 Rebuild the installed Docker image to receive the navigation fix.
- See [launcher instructions](../README.md#desktop-installation-no-coding) and
  [verification evidence](roadmap.md#launcher-verification-record).
  These changes are after v0.9.7 and do not close the remaining v1.0 war gate.

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
[Qualification instructions](roadmap.md#release-qualification) give the isolated observation
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
  See the [qualification evidence](roadmap.md#real-transition-observed--2026-10-05).
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


## Release qualification


Updated: 2026-10-05 · Document version: 0.1.3

The v1.0 scope is the existing clan-management product with reliable collection,
dashboard, scheduling, and recovery. Player comparison, forecasting, configurable
scoring thresholds, and query batching remain follow-up enhancements. They do not
block the current reliability milestone.

### Completed evidence

Deployment, visual review, live synchronization, Discord delivery/recovery, and
real-backup upgrade/restore passed; see [Operations](operations.md). Automated
regressions additionally cover an inferred rollover later confirmed by completed
history, a lagging live endpoint after completion, repeat synchronization, and
recovery after a 45-day history gap. Simulated cases are not live boundary proof.

### Remaining field gate: season identity

Run from the project root with the project's virtual environment:

```bash
mkdir -p data/qualification
.venv/bin/python -m scripts.observe_war_identity >> data/qualification/war-observations.jsonl
```

The script provides the isolated CLI; `WarService.observe_identity()` owns the
Clash Royale observation logic. The command loads credentials privately, bypasses the HTTP
cache, and synchronizes into a fresh in-memory database in a temporary directory.
It disables Discord and never opens the production database. Temporary caches and
logs are removed afterward. Output contains only UTC observation time, explicit-ID
presence, live section, and resolved/completed race identities. Race timestamps
use the configured scheduler timezone, matching application storage. Failure
outputs contain an error type and exit nonzero; do not treat them as acceptance.
The internal worker refuses a file-backed database or enabled Discord.

Collect samples during normal operation and around the next observed reset to
section zero. Do not assume a calendar date from the numeric season identifier.
No background observer is installed by this command. Run it again as needed;
there is no scheduler or production configuration change.

Acceptance requires all of the following:

1. A successful pre-transition sample establishes the previous completed season
   and the live identity.
2. A successful post-transition sample shows the new season/section identity.
3. A later API history sample confirms the inferred identity after that race
   completes. A successful live request alone is insufficient.
4. Review any failed/ambiguous samples. Preserve completed results, refresh history,
   and verify recovery; do not loosen the age limit just to make the gate pass.
5. Run `make ci` in the activated virtual environment, review the evidence, then
   prepare the v1.0.0 version and release notes. Do not move the v0.9.7 tag.

#### First live baseline

Collected 2026-10-02 at 14:54:28 UTC (16:54:28 Europe/Paris):

| Field | Observation |
| --- | --- |
| Explicit live season ID | Absent |
| Latest completed identity | Season 136, section 2 |
| Resolved live identity | Season 136, section 3 |
| Completed races synchronized | 10 |
| Observation result | Success |

This is an ordinary within-season observation. It does not close the boundary
gate. Historical seasons in the response provide context, not evidence that the
new guard ran during those earlier transitions. The operator's v0.9.7 exception
does not automatically waive this v1.0 requirement.


#### Real transition observed — 2026-10-05

The uncached isolated observation at 13:18:44 UTC (15:18:44 Europe/Paris), using
service code committed at `206b179`, succeeded. The complete identity-only sample
is retained in [war-2026-10-05.json](qualification/war-2026-10-05.json).

| Evidence | Result |
| --- | --- |
| October 2 inferred live identity | 136 / section 3 |
| October 5 API completed history | Confirms 136 / section 3 |
| October 5 live section | Reset to 0 |
| October 5 inferred live identity | 137 / section 0 |
| Explicit live season ID | Still absent |
| API completed history for 137 / 0 | Not yet present |

The before/after transition is now observed, and the previously live race was
confirmed by authoritative history. The new season identity remains inferred.
Acceptance steps 1 and 2 above are satisfied; step 3 still requires a later
completed-history sample confirming **137 / section 0**. Do not mark the field
gate complete merely because the numeric increment looks correct.

Next action: collect another sample after the new race completes and look for
`season: "137", section: 0, completed: true`. If history instead reports a different
identity, investigate and fix inference before tagging v1.0.0. No background
observer or automatic release has been installed.


#### Explicit final-gate check

```bash
.venv/bin/python -m scripts.observe_war_identity --confirm-season 137 --confirm-section 0
```

The service checks the fresh completed API log for this exact identity; an inferred
live race or an older row in the disposable database cannot satisfy the check.
The JSON `confirmation.status` is `confirmed` or `pending` when collection succeeds.
Exit codes are 0 for successful requested confirmation, 1 for collection failure,
2 for invalid command arguments, and 3 for a successful observation whose target
is still pending. Without confirmation options, ordinary successful observation
still returns 0. A failed observation is not confirmation, even if partial history
was available before live synchronization failed.

The live check at 2026-10-05 13:27:27 UTC returned `ok: true`, confirmation
`pending`, and exit code 3. No production data or Discord state was modified.
A confirmed result closes only this identity check; final code review, Makefile
checks, version metadata, and release tagging still follow the checklist above.


## v0.9.7 release record


Date: 2026-10-02 · Document version: 0.1.0

This pre-1.0 release closes the current reliability milestone. The operator
explicitly accepted the remaining real season-rollover observation limitation.
It is not a v1.0 stability declaration.

### Changes

- Centralized dashboard data preparation and improved empty-data/cache fallback.
- Atomic synchronization, migration repair, and conservative live-war identity.
- Persistent scheduler settings, job health, process locks, and daily retry guards.
- Supervised startup, persistent Docker data, source-only packaging, and restore.
- Complete function contracts and operational documentation.

### Verification

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

### Accepted limitations

- Real season rollover has not been observed with the new guard. Recent-history
  inference remains a heuristic; the eight-day cutoff is application policy.
  Actual boundary observation remains a v1.0 requirement.
- Discord delivery is not exactly once: a crash after delivery but before the
  success commit can lead to a duplicate on retry.
- Visual acceptance was delegated to the agent at desktop size. This does not
  establish human acceptance or exhaustive browser/mobile accessibility coverage.
- Dashboard access remains restricted to trusted operators; there is no login layer.

### Upgrade

Back up the database before upgrading. Startup runs Alembic to `a2026093001`.
Follow the [backup and restore procedure](operations.md#backup-and-restore).
Restart the application after installing the release so long-lived processes
load its version and code. Release publication does not itself restart deployment.


## Git history and tag audit


Updated: 2026-10-02 · Document version: 0.1.1

### Findings

Reviewed all 138 reachable commits and 34 local/remote tags at main `cac66ad`.
The repository is not shallow, Git connectivity checks pass, local and remote
refs agree, and GitHub reports no releases. Commit subjects mostly follow the
project's conventional type/scope style. Historical subject typos, duplicate
subjects, and missing version numbers do not justify rewriting commit history.
This is a history/ref audit, not certification that every historical revision
builds or that historical blobs contain no secrets; private files were not read.

Several version names duplicate targets, the unprefixed `0.1.1` conflicts with
`v0.1.1`, and some higher versions point backward along the single mainline.
Duplicate aliases are valid Git refs, and older maintenance releases can be valid;
this cleanup adopts one chronological primary release sequence for this project.

### Cleanup policy

Retain 19 primary `v*` tags with distinct commits ordered by version and ancestry.
Archive the 15 conflicting aliases under `legacy/<original-name>`, preserving each
exact original object ID. No surviving version tag moves and no commit is rewritten.
Missing version numbers are intentional; no unverified release is invented.
Annotated tags retained their annotation objects. On 2026-10-02, `git ls-remote`
confirmed all 15 archive refs on origin, absence of their original aliases, and
retention of the 19 primary tags. The cleanup is now published.

The pending application version was incorrectly `0.9.2.dev0`, behind `v0.9.6`.
It was corrected to `0.9.7.dev0`. The operator subsequently approved `0.9.7`
with the documented real-rollover limitation accepted for this pre-1.0 release.
The new annotated `v0.9.7` tag targets its release commit, not an earlier revision.
Per-file header versions are independent and are not release tag candidates.

### Archived names

| Original name | Local archive | Reason |
| --- | --- | --- |
| `0.1.1` | `legacy/0.1.1` | Inconsistent prefix; conflicts with v0.1.1 at a different commit. |
| `v0.1.1` | `legacy/v0.1.1` | Duplicate target of v0.1.0. |
| `v0.2.1` | `legacy/v0.2.1` | Duplicate target of v0.2.0. |
| `v0.2.2` | `legacy/v0.2.2` | Target predates v0.2.0. |
| `v0.3.1` | `legacy/v0.3.1` | Target predates v0.3.0. |
| `v0.3.2` | `legacy/v0.3.2` | Duplicate target of v0.3.0. |
| `v0.5.1` | `legacy/v0.5.1` | Target follows v0.6.4; interrupts mainline version order. |
| `v0.5.2` | `legacy/v0.5.2` | Duplicate target of v0.5.0. |
| `v0.6.2` | `legacy/v0.6.2` | Target follows v0.7.1; interrupts mainline version order. |
| `v0.8.1` | `legacy/v0.8.1` | Target predates v0.8.0. |
| `v0.8.2` | `legacy/v0.8.2` | Target predates v0.8.0. |
| `v0.8.3` | `legacy/v0.8.3` | Target predates v0.8.0. |
| `v0.8.4` | `legacy/v0.8.4` | Target predates v0.8.0 and v0.8.2. |
| `v0.8.5` | `legacy/v0.8.5` | Duplicate target of v0.8.0. |
| `v0.9.5` | `legacy/v0.9.5` | Target predates v0.9.4. |

### Complete original ref inventory

These IDs provide an exact recovery record. For archived tags, restore the old
local ref with `git update-ref refs/tags/NAME OBJECT_ID` only after checking that
the old ref is absent. Remote changes require a separate deliberate publication.
Do not use `git push --tags` as a cleanup command: it does not delete old names.

| Original tag | Original object ID | Peeled commit | Local result |
| --- | --- | --- | --- |
| `0.1.1` | `87f31ed3cb60d74308bc855ef7a111d878bda8f1` | `87f31ed3cb60d74308bc855ef7a111d878bda8f1` | Archive under `legacy/` |
| `v0.1.0` | `076b61793586b94fc5cda555f0b82bb487a08906` | `076b61793586b94fc5cda555f0b82bb487a08906` | Keep |
| `v0.1.1` | `076b61793586b94fc5cda555f0b82bb487a08906` | `076b61793586b94fc5cda555f0b82bb487a08906` | Archive under `legacy/` |
| `v0.1.2` | `48e2719f8268e467af763079ac19ce280461432b` | `48e2719f8268e467af763079ac19ce280461432b` | Keep |
| `v0.2.0` | `e03ddf23f1af80a2b76fe2a2d1c17413ea3fc991` | `e03ddf23f1af80a2b76fe2a2d1c17413ea3fc991` | Keep |
| `v0.2.1` | `e03ddf23f1af80a2b76fe2a2d1c17413ea3fc991` | `e03ddf23f1af80a2b76fe2a2d1c17413ea3fc991` | Archive under `legacy/` |
| `v0.2.2` | `338d0f0e2003f0591f9cde4aa58eb08a415132c2` | `338d0f0e2003f0591f9cde4aa58eb08a415132c2` | Archive under `legacy/` |
| `v0.3.0` | `eb834113a87054a0457c3ae78565a4709b743dcf` | `eb834113a87054a0457c3ae78565a4709b743dcf` | Keep |
| `v0.3.1` | `2cb6a5b69e1bf333582920087850ca8bbb1c63c7` | `2cb6a5b69e1bf333582920087850ca8bbb1c63c7` | Archive under `legacy/` |
| `v0.3.2` | `eb834113a87054a0457c3ae78565a4709b743dcf` | `eb834113a87054a0457c3ae78565a4709b743dcf` | Archive under `legacy/` |
| `v0.4.1` | `a78a4e128770dbf54ee83200589b99e51ac6e477` | `a78a4e128770dbf54ee83200589b99e51ac6e477` | Keep |
| `v0.4.2` | `9e795c9fdcf624848cdf2d1bfc3bd317acb91dc7` | `9e795c9fdcf624848cdf2d1bfc3bd317acb91dc7` | Keep |
| `v0.5.0` | `3f2bc69c4e9193f16c25a40f39fa6b37e5f6147d` | `01b04d643d01c8456237f3f7d10c4dbe875ffd23` | Keep |
| `v0.5.1` | `415efab8413efdd14864b747fd58344a209d3036` | `415efab8413efdd14864b747fd58344a209d3036` | Archive under `legacy/` |
| `v0.5.2` | `01b04d643d01c8456237f3f7d10c4dbe875ffd23` | `01b04d643d01c8456237f3f7d10c4dbe875ffd23` | Archive under `legacy/` |
| `v0.6.1` | `5778bae94208a5a015d2887311e27063da4f91e8` | `5778bae94208a5a015d2887311e27063da4f91e8` | Keep |
| `v0.6.2` | `aa45af3446d72881038577dadfe683c89ded3f56` | `aa45af3446d72881038577dadfe683c89ded3f56` | Archive under `legacy/` |
| `v0.6.3` | `ff9479120b6e15688adbf391e4d44070562cbd80` | `ff9479120b6e15688adbf391e4d44070562cbd80` | Keep |
| `v0.6.4` | `160eae0d6705b202954f5976d4dcaad26e5b0735` | `160eae0d6705b202954f5976d4dcaad26e5b0735` | Keep |
| `v0.6.5` | `6c5d50e4b4feba703ea809d8df02430f14a6b227` | `6c5d50e4b4feba703ea809d8df02430f14a6b227` | Keep |
| `v0.6.6` | `ba90ee247959e5753425b55955936f6df0ccbefc` | `ba90ee247959e5753425b55955936f6df0ccbefc` | Keep |
| `v0.7.1` | `98d2362865c83c5eb051d78ef9d8d3a6aec5449a` | `98d2362865c83c5eb051d78ef9d8d3a6aec5449a` | Keep |
| `v0.8.0` | `3b6125b69974583a7d46c4ba32ae09b03c39b396` | `3137124cdd9305a82f2fce2b4a0d0680f859e12c` | Keep |
| `v0.8.1` | `dd7712000739b25591218607aa878baec6b23730` | `dd7712000739b25591218607aa878baec6b23730` | Archive under `legacy/` |
| `v0.8.2` | `81ec3cf0a9301c476f797f5c0262537566e89dba` | `81ec3cf0a9301c476f797f5c0262537566e89dba` | Archive under `legacy/` |
| `v0.8.3` | `1eab97ec4b9c05ddf62acb02cf42efa404f1f942` | `1eab97ec4b9c05ddf62acb02cf42efa404f1f942` | Archive under `legacy/` |
| `v0.8.4` | `4442d1e5fc32d9203ed2822b8c4efc9b93b21bd5` | `4442d1e5fc32d9203ed2822b8c4efc9b93b21bd5` | Archive under `legacy/` |
| `v0.8.5` | `3137124cdd9305a82f2fce2b4a0d0680f859e12c` | `3137124cdd9305a82f2fce2b4a0d0680f859e12c` | Archive under `legacy/` |
| `v0.9.1` | `d775d8614e6c176defcb075dde32b803292042c6` | `d775d8614e6c176defcb075dde32b803292042c6` | Keep |
| `v0.9.2` | `02876080d1b0d9b2288b52ccd77fd57697fc7971` | `02876080d1b0d9b2288b52ccd77fd57697fc7971` | Keep |
| `v0.9.3` | `a1f37e7b81e422c3e622f070050c162afe51b0b6` | `a1f37e7b81e422c3e622f070050c162afe51b0b6` | Keep |
| `v0.9.4` | `610ac5edc6b55f8565f748d411acb32138873279` | `610ac5edc6b55f8565f748d411acb32138873279` | Keep |
| `v0.9.5` | `f0cd9ed0b4938694d3d341c23fe4d94a381e04a7` | `f0cd9ed0b4938694d3d341c23fe4d94a381e04a7` | Archive under `legacy/` |
| `v0.9.6` | `cac66ad5c4b37cf387f3c3436a8b6211c4e12733` | `cac66ad5c4b37cf387f3c3436a8b6211c4e12733` | Keep |

### Validation and remaining release work

The release check uses 198 isolated tests, repository-wide Black and Pylint,
and diff whitespace checks. Docker isolation, live API synchronization, real-backup
upgrade/restore, host deployment health, Discord delivery/recovery, and deployed
browser review are recorded in the operations guide and v0.9.7 release notes.
Actual season-boundary field verification remains open for v1.0 and was explicitly
accepted as a v0.9.7 limitation. Git ref correctness does not prove runtime behavior.


## Launcher verification record


Updated: 2026-10-06 · Document version: 0.1.2

### Docker navigation

An isolated container used the existing application image, the updated dashboard
mounted read-only, dummy credentials and a new SQLite database under `/tmp`.
No production database, credentials, scheduler jobs or Discord deliveries were used.

With telemetry enabled, switching Settings → Home reproduced ten stale metric/input
elements. The server raised `PermissionError: '/.streamlit'` from Streamlit's
installation-ID creation inside `_create_new_session_message`. The numeric
container user cannot write that directory. A page-root container alone did not
resolve the failure.

With `STREAMLIT_BROWSER_GATHER_USAGE_STATS=false` (now set in Dockerfile), headless
Chrome completed three Settings → Home and three Members → Home cycles in one
session: twelve transitions, zero stale metrics, text inputs, member filters or
dataframes on Home. A final screenshot also showed the clean Home page.
The tests used empty data for browser checks; populated-data transitions are
covered separately by Streamlit AppTest. Firefox and a newly rebuilt production
image have not been tested in this check. Rebuild Docker and reload existing tabs
to apply the fix; changing source alone does not update a running image.

### Launchers

- Linux x86_64: PyInstaller 6.16.0 build with system Python's shared library,
  AppImage packaging, Tcl self-test and GUI startup/exit under Xvfb passed.
- Local output: `launch/linux/linux_launcher.AppImage` (ignored build artifact).
- Windows/macOS: workflow defined with native runners; not executed locally.
- Launcher smoke tests do not start or stop production containers.
- First-run configuration overwrite protection, occupied-port refusal, safe
  command errors, and compiled-artifact exclusion have isolated unit tests.

The existing `v0.9.7` tag remains unchanged. No new release tag or published
launcher assets were created by this work. Push the workflow and run it manually
before distributing Windows/macOS outputs. All platforms still require Docker.

### Startup and resume follow-up

The launcher now retries connection resets and incomplete HTTP startup responses.
Normal Start reuses the existing image; only Update application requests a rebuild
and container replacement. Folder selection is hidden for a launcher installed
inside the project distribution.

An isolated Docker supervisor with a temporary database and a harmless sleeping
scheduler substitute passed dashboard shutdown → resume, with the scheduler PID
unchanged. No real API collection or production jobs ran. Makefile checks passed:
230 tests, Black clean, Pylint 10/10. The rebuilt Linux AppImage passed Tcl and GUI
smoke checks and was installed atomically because the old launcher was still open.
Existing images require one Update application to install the resume protocol.

### Template-based settings follow-up

Missing `.env` files are now copied byte-for-byte from `.env.example` before
configuration. Existing files retain comments, custom keys and unchanged values.
A graphical editor requires nonempty mandatory fields, permits blank Discord
configuration, masks secrets, and rejects stale writes after external edits.
The launcher summary never shows the API token or webhook. Its next Start applies
saved configuration through Compose without an image rebuild.

A real Tk dialog check under Xvfb used a temporary application directory and
synthetic credentials: template creation, required-field entry, save and masked
summary passed. The Linux AppImage was rebuilt with python-dotenv and passed
Tcl and GUI smoke tests. Windows/macOS remain unverified until native workflow
builds and platform acceptance checks run. No live configuration was modified.

Final Makefile checks: 232 tests passed, Black clean, Pylint 10/10.
