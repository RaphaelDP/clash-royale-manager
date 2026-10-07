"""
================================================================================
Filename: launcher.py
Description: Shared desktop control panel with standalone and optional Docker backends.
Author: Raphael Smilet
Date Created: 2026-10-06
Last Modified: 2026-10-07
Version: 0.2.0
Python Version: 3.12
================================================================================
"""

import argparse
import ctypes
import os
from pathlib import Path
import queue
import shutil
import socket
import subprocess
import sys
from threading import Thread
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from http.client import HTTPException
from urllib.error import URLError
from urllib.request import urlopen

from launch.configuration import ConfigurationDialog, missing_fields, read_configuration

URL = "http://localhost:8501"


def external_environment():
    """Restore host library paths before invoking Docker or a browser.

    Args:
        None.

    Returns:
        dict: Subprocess environment with Linux bind-mount ownership configured.
    """
    env = dict(os.environ)
    for name in ("LD_LIBRARY_PATH", "DYLD_LIBRARY_PATH"):
        if name + "_ORIG" in env:
            env[name] = env[name + "_ORIG"]
        else:
            env.pop(name, None)
    if sys.platform.startswith("linux"):
        env.update(CLAN_UID=str(os.getuid()), CLAN_GID=str(os.getgid()))
    return env


def project_root():
    """Locate the source distribution beside a script, executable, app, or AppImage.

    Args:
        None.

    Returns:
        Path | None: Nearest directory containing the project's Compose file.
    """
    executable = Path(
        os.getenv("APPIMAGE")
        or (sys.executable if getattr(sys, "frozen", False) else __file__)
    ).resolve()
    return next(
        (
            path
            for path in executable.parents
            if (path / "docker-compose.yml").is_file()
        ),
        None,
    )


def docker_command(root, *arguments, timeout=600):
    """Run this project's Compose command without exposing captured output.

    Args:
        root: Selected source distribution directory.
        *arguments: Compose arguments, passed directly without shell interpolation.
        timeout: Maximum subprocess duration in seconds.

    Returns:
        str: Captured command output on success.

    Raises:
        RuntimeError: Docker is unavailable or the command failed.
    """
    docker = shutil.which("docker")
    if not docker and sys.platform == "darwin":
        docker = next(
            (
                str(p)
                for p in (
                    Path("/usr/local/bin/docker"),
                    Path("/opt/homebrew/bin/docker"),
                )
                if p.is_file()
            ),
            None,
        )
    if not docker:
        raise RuntimeError(
            "Install and start Docker Desktop (or Docker Engine with Compose), then try again."
        )
    result = subprocess.run(
        [
            docker,
            "compose",
            "--project-directory",
            str(root),
            "-f",
            str(root / "docker-compose.yml"),
            *arguments,
        ],
        cwd=root,
        env=external_environment(),
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    if result.returncode:
        raise RuntimeError(
            "Docker could not complete the action. Check that Docker is running. "
            "The first start also needs Internet access. "
            "For an older installation, try Update application. See Docker Desktop for details."
        )
    return result.stdout


def start_application(root, rebuild=False, reconfigure=False):
    """Build/start the selected project and wait for its dashboard to become healthy.

    Args:
        root: Source project directory containing Compose and private configuration.
        rebuild: Explicitly rebuild the application after a source update.
        reconfigure: Recreate the container without a build to load changed settings.

    Returns:
        None.

    Raises:
        RuntimeError: Configuration is missing, another app owns the port, or startup fails.
    """
    if not (root / "docker-compose.yml").is_file() or not (root / ".env").is_file():
        raise RuntimeError(
            "Select the project folder and complete its first-run settings."
        )
    owned = docker_command(
        root, "ps", "--status", "running", "--quiet", "app", timeout=30
    ).strip()
    with socket.socket() as probe:
        probe.settimeout(1)
        occupied = probe.connect_ex(("127.0.0.1", 8501)) == 0
    if occupied and not owned:
        raise RuntimeError(
            "Port 8501 is already used by another application. Stop that instance first; it has not been changed."
        )
    for name in ("data", "logs", "backups"):
        (root / name).mkdir(exist_ok=True)
    if rebuild:
        docker_command(root, "up", "-d", "--build", "--force-recreate")
    elif reconfigure:
        docker_command(root, "up", "-d", "--force-recreate", "app")
    elif owned:
        docker_command(root, "up", "-d", "app")
        docker_command(
            root,
            "exec",
            "-T",
            "app",
            "python",
            "-c",
            "from app.services.application_control import request_dashboard_start; "
            "request_dashboard_start()",
        )
    else:
        # Compose builds only if no image exists; reuse an existing image otherwise.
        docker_command(root, "up", "-d", "app")
    deadline = time.monotonic() + 180
    while time.monotonic() < deadline:
        try:
            with urlopen(URL + "/_stcore/health", timeout=3) as response:
                if response.status == 200:
                    return
        except (URLError, OSError, HTTPException):
            pass
        time.sleep(1)
    raise RuntimeError(
        "Dashboard is not ready yet. The container was left running; inspect it in Docker Desktop or use Stop all."
    )


def open_dashboard():
    """Open the local dashboard using the host browser outside the frozen runtime.

    Args:
        None.

    Returns:
        None.
    """
    if sys.platform == "win32":
        os.startfile(URL)  # pylint: disable=no-member
    else:
        subprocess.Popen(  # pylint: disable=consider-using-with
            ["open" if sys.platform == "darwin" else "xdg-open", URL],
            env=external_environment(),
        )  # pylint: disable=consider-using-with


class Launcher:
    """Graphical control panel for standalone and optional Docker deployments."""

    def __init__(self, window, configure=True, backend=None):
        """Build the control panel without starting the application.

        Args:
            window: Tk root window.
            configure: Read local settings unless this is an isolated packaging smoke test.
            backend: Optional standalone backend; None uses Docker.

        Returns:
            None.
        """
        self.backend = backend
        self.window = window
        self.events = queue.Queue()
        self.busy = False
        self.configuration_changed = False
        detected = backend.root if backend else project_root()
        self.folder = tk.StringVar(value=str(detected or ""))
        self.status = tk.StringVar(
            value=(
                "Click Start and open. No Docker required."
                if backend
                else "Click Start and open. Docker must be running."
            )
        )
        window.title("Clash Royale Clan Manager")
        icon = Path(__file__).resolve().with_name("clan-manager.png")
        if icon.is_file():
            window.iconphoto(True, tk.PhotoImage(file=str(icon)))
        elif getattr(sys, "frozen", False):
            raise RuntimeError("The launcher package is missing its window icon.")
        window.geometry("700x390")
        frame = ttk.Frame(window, padding=18)
        frame.pack(fill="both", expand=True)
        if detected is None:
            ttk.Label(
                frame,
                text="Application files not found. Select the extracted application folder.",
            ).pack(anchor="w")
            ttk.Button(
                frame, text="Locate application", command=self.choose_folder
            ).pack(anchor="w")
        self.summary = tk.StringVar(value="Application settings have not been loaded.")
        ttk.Label(frame, textvariable=self.summary, wraplength=650).pack(
            anchor="w", pady=8
        )
        ttk.Button(
            frame, text="Application settings", command=self.edit_configuration
        ).pack(anchor="w")
        actions = ttk.Frame(frame)
        actions.pack(pady=14)
        ttk.Button(
            actions, text="Start and open", command=lambda: self.run_action("start")
        ).pack(side="left", padx=6)
        ttk.Button(
            actions, text="Open dashboard", command=lambda: self.run_action("start")
        ).pack(side="left", padx=6)
        ttk.Button(
            actions, text="Stop all", command=lambda: self.run_action("stop")
        ).pack(side="left", padx=6)
        if backend is None:
            ttk.Button(
                frame,
                text="Update application",
                command=lambda: self.run_action("update"),
            ).pack(anchor="w")
        else:
            ttk.Label(frame, text=f"Your data: {backend.root}", wraplength=650).pack(
                anchor="w"
            )
        ttk.Label(frame, textvariable=self.status, wraplength=610).pack(anchor="w")
        window.protocol("WM_DELETE_WINDOW", self.close_window)
        window.after(100, self.poll)
        if configure and detected:
            window.after(150, self.prepare_configuration)

    def choose_folder(self):
        """Ask for the extracted project directory.

        Args:
            None.

        Returns:
            None.
        """
        if not self.busy:
            selected = filedialog.askdirectory()
            if selected:
                self.folder.set(selected)

    def prepare_configuration(self):
        """Create missing configuration, show a safe summary and prompt for required fields.

        Args:
            None.

        Returns:
            bool: True when all required values are available.
        """
        root = Path(self.folder.get())
        try:
            defaults, values = read_configuration(root)
            if missing_fields(defaults, values):
                self.edit_configuration()
                defaults, values = read_configuration(root)
            self.summary.set(
                f"Clan: {values.get('CLAN_TAG') or 'Not configured'}\n"
                f"Database: {values.get('DATABASE_URL') or 'Not configured'}\n"
                f"Log level: {values.get('LOG_LEVEL') or 'Not configured'}\n"
                f"Timezone: {values.get('SCHEDULER_TIMEZONE') or 'Not configured'}\n"
                f"API token: {'Configured (hidden)' if values.get('CR_API_TOKEN') else 'Missing'}\n"
                f"Discord: {'Configured (hidden)' if values.get('DISCORD_WEBHOOK_URL') else 'Disabled (optional)'}"
            )
            return not missing_fields(defaults, values)
        except (OSError, ValueError):
            messagebox.showerror(
                "Settings",
                "Could not load application settings. Check the application folder and file permissions.",
            )
            return False

    def edit_configuration(self):
        """Open the private settings editor without starting Docker.

        Args:
            None.

        Returns:
            None. Changed settings will be applied by the next Start action.
        """
        if self.busy:
            return
        try:
            dialog = ConfigurationDialog(self.window, Path(self.folder.get()))
            self.configuration_changed |= dialog.changed
            if dialog.changed:
                self.window.after(0, self.prepare_configuration)
            if dialog.changed:
                self.status.set(
                    "Settings saved. Start and open will restart the application to apply them."
                )
        except (OSError, ValueError):
            messagebox.showerror(
                "Settings",
                "Could not open settings. Locate the application folder first.",
            )

    def close_window(self):
        """Keep the launcher open during operations and explain background operation.

        Args:
            None.

        Returns:
            None.
        """
        if not self.busy and messagebox.askokcancel(
            "Close launcher",
            "The application keeps running. Use Stop all first if you want to stop "
            "the dashboard and scheduler. Close this launcher window?",
        ):
            self.window.destroy()

    def run_action(self, action):
        """Validate user choices and dispatch an application operation off the GUI thread.

        Args:
            action: start, update, or stop.

        Returns:
            None.
        """
        if self.busy:
            return
        root = Path(self.folder.get()).expanduser().resolve()
        if self.backend is None and not (root / "docker-compose.yml").is_file():
            messagebox.showerror(
                "Select project",
                "Keep the launcher inside the extracted application folder, or locate that folder.",
            )
            return
        confirmations = {
            "stop": (
                "Stop all?",
                "Stop this project's dashboard and scheduler for everyone?",
            ),
            "update": (
                "Update application?",
                "Rebuild and restart the dashboard and scheduler? Data is preserved.",
            ),
        }
        if action in confirmations and not messagebox.askyesno(*confirmations[action]):
            return
        if action in {"start", "update"} and not self.prepare_configuration():
            return
        self.busy = True
        self.status.set(
            (
                "Starting the application…"
                if self.backend
                else "Starting… The first build can take several minutes."
            )
            if action in {"start", "update"}
            else "Stopping…"
        )
        Thread(target=self.work, args=(root, action), daemon=True).start()

    def work(self, root, action):
        """Perform an application operation and send a safe result to the GUI queue.

        Args:
            root: Selected source project directory.
            action: start, update, or stop.

        Returns:
            None.
        """
        try:
            if self.backend is not None:
                if action == "stop":
                    self.backend.stop()
                else:
                    self.backend.start(reconfigure=self.configuration_changed)
            elif action in {"start", "update"}:
                start_application(
                    root,
                    rebuild=action == "update",
                    reconfigure=self.configuration_changed,
                )
            else:
                docker_command(root, "stop", timeout=90)
            self.events.put((action, None))
        except (OSError, RuntimeError, subprocess.SubprocessError) as error:
            self.events.put((action, str(error)))

    def poll(self):
        """Apply worker results on the Tk main thread.

        Args:
            None.

        Returns:
            None.
        """
        try:
            action, error = self.events.get_nowait()
            self.busy = False
            self.status.set(
                error
                or (
                    "Dashboard ready."
                    if action in {"start", "update"}
                    else "Dashboard and scheduler stopped."
                )
            )
            if error:
                messagebox.showerror("Launcher", error)
            elif action in {"start", "update"}:
                self.configuration_changed = False
                open_dashboard()
        except queue.Empty:
            pass
        self.window.after(100, self.poll)


def main():
    """Run the GUI or a packaging smoke check without reading credentials.

    Args:
        None. Options come from the command line.

    Returns:
        None.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--smoke-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        tk.Tcl().eval("info patchlevel")
        return
    if sys.platform == "win32" and getattr(sys, "frozen", False):
        ctypes.windll.kernel32.SetDllDirectoryW(None)  # pylint: disable=no-member
    window = tk.Tk()
    Launcher(window, configure=not args.smoke_test)
    if args.smoke_test:
        window.after(200, window.destroy)
    window.mainloop()


if __name__ == "__main__":
    main()
