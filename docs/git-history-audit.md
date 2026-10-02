# Git history and tag audit

Updated: 2026-10-02 · Document version: 0.1.1

## Findings

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

## Cleanup policy

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

## Archived names

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

## Complete original ref inventory

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

## Validation and remaining release work

The release check uses 198 isolated tests, repository-wide Black and Pylint,
and diff whitespace checks. Docker isolation, live API synchronization, real-backup
upgrade/restore, host deployment health, Discord delivery/recovery, and deployed
browser review are recorded in the operations guide and v0.9.7 release notes.
Actual season-boundary field verification remains open for v1.0 and was explicitly
accepted as a v0.9.7 limitation. Git ref correctness does not prove runtime behavior.
