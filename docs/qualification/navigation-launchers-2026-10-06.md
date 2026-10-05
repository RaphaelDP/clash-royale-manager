# Navigation and desktop launcher checks

Updated: 2026-10-06 · Document version: 0.1.2

## Docker navigation

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

## Launchers

- Linux x86_64: PyInstaller 6.16.0 build with system Python's shared library,
  AppImage packaging, Tcl self-test and GUI startup/exit under Xvfb passed.
- Local output: `launch/linux_launcher.AppImage` (ignored build artifact).
- Windows/macOS: workflow defined with native runners; not executed locally.
- Launcher smoke tests do not start or stop production containers.
- First-run configuration overwrite protection, occupied-port refusal, safe
  command errors, and compiled-artifact exclusion have isolated unit tests.

The existing `v0.9.7` tag remains unchanged. No new release tag or published
launcher assets were created by this work. Push the workflow and run it manually
before distributing Windows/macOS outputs. All platforms still require Docker.

## Startup and resume follow-up

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

## Template-based settings follow-up

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
