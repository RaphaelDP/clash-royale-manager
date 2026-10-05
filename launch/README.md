# Desktop launchers

Updated: 2026-10-06 · Document version: 0.1.2

The recommended desktop setup is a graphical launcher **plus Docker**. Docker
runs the dashboard, scheduler and database environment; the launcher supplies
Start, Open dashboard and Stop all buttons. Python is not required on your
computer when using a compiled launcher. Docker installation is still required.
The existing start scripts remain an alternative for experienced users.

## First installation (no coding)

1. Install Docker Desktop on Windows or macOS, or Docker Engine with Compose on
   Linux. Start Docker before opening the launcher.
2. Download and extract the `project-source` artifact from the same successful
   GitHub Actions run as your launcher. Extract its inner `project.zip` as well.
   Keep this project folder: it contains your configuration and persistent data.
3. Download the launcher artifact for your system. Extract the archive(s), then
   put `windows_launcher.exe`, `macos_launcher.app`, or `linux_launcher.AppImage`
   in the project's `launch/` folder. The macOS build targets Intel; Apple Silicon
   currently requires Rosetta. These builds are unsigned and not notarized.
4. Open the launcher. On Linux, allow execution in the file's Properties if
   needed; AppImage may require your distribution's FUSE compatibility package.
5. The launcher finds its application folder automatically. Folder selection
   appears only if the launcher was moved away from the application files.
   Click **Start and open**. The first build needs Internet access and can take
   several minutes.
6. The launcher copies the entire `.env.example` to `.env` if it is missing.
   **Application settings** shows all template fields, with secrets masked.
   Complete the required fields; Discord is optional and may stay blank. Existing
   configuration, comments and custom settings are preserved. Obtain an API token
   at <https://developer.clashroyale.com>, allowing your computer's public IP.
   The main window displays a local configuration summary without revealing tokens.
   After saving changes, **Start and open** restarts the container as needed to
   load them, without rebuilding the image. Cancel leaves existing values unchanged.

Closing the browser or launcher leaves the application running. **Stop all**
stops this project's dashboard and scheduler, preserving `data/`, `logs/` and
`backups/`. Normal startup reuses the installed image. Reopening a closed dashboard keeps
the existing scheduler running and does not repeat initial collection.
After downloading new application source, click **Update application** once to
rebuild and replace the container; this restarts the scheduler and preserves data.
Older installations need this one-time update to support dashboard-only resume.
The dashboard's Close control is available in the sidebar. In Docker, use
**Stop all** to release the published port completely.

If startup fails, check Docker Desktop's container status/logs. Do not post tokens
or unredacted configuration files. A failed health check leaves the container
available for inspection or for stopping through the launcher.

## Build on GitHub (maintainers)

1. Push `.github/workflows/launchers.yml` and its supporting code to the default
   branch. GitHub runs the builds; you do not need Windows or macOS locally.
2. Open the repository on GitHub → **Actions → Desktop launchers → Run workflow**.
3. Choose the branch and click **Run workflow**. Wait for the checks and all three
   builds to turn green.
4. Open that run. Download `project-source` and the matching `launcher-*` artifact
   from **Artifacts** at the bottom. Artifacts require a GitHub login and expire
   according to the repository's retention policy; they are not Release assets.

Future pushed `v*` tags also trigger builds. Existing tags are not rebuilt
retroactively. The workflow does not create tags, move tags or publish releases.
No application credentials or GitHub secrets are needed for these builds.
Windows and macOS acceptance requires their actual runner builds to pass.

For local development, run `python -m launch.launcher` with Python/Tk installed.
The workflow documents the native PyInstaller and AppImage build commands.
Compiled outputs are ignored by Git and excluded from source ZIPs and Docker
build contexts.
