# v1.0 qualification

Updated: 2026-10-05 · Document version: 0.1.2

The v1.0 scope is the existing clan-management product with reliable collection,
dashboard, scheduling, and recovery. Player comparison, forecasting, configurable
scoring thresholds, and query batching remain follow-up enhancements. They do not
block the current reliability milestone.

## Completed evidence

Deployment, visual review, live synchronization, Discord delivery/recovery, and
real-backup upgrade/restore passed; see [Operations](operations.md). Automated
regressions additionally cover an inferred rollover later confirmed by completed
history, a lagging live endpoint after completion, repeat synchronization, and
recovery after a 45-day history gap. Simulated cases are not live boundary proof.

## Remaining field gate: season identity

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

### First live baseline

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


### Real transition observed — 2026-10-05

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
