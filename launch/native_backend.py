"""
Filename: native_backend.py
Description: Control a bundled Python application without Docker or a system interpreter.
Author: Raphael Smilet
Date Created: 2026-10-07
Last Modified: 2026-10-07
Version: 0.1.0
"""

import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import urlopen
from http.client import HTTPException


def user_directory():
    """Choose persistent per-user storage outside the downloaded application.

    Args:
        None.

    Returns:
        Path: Platform-specific user data directory.
    """
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library/Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share"))
    return base / "ClashRoyaleClanManager"


class NativeBackend:
    """Start and stop only the supervisor belonging to this data directory."""

    def __init__(self, bundle, data=None, port=8501):
        """Locate the packaged runtime and create default user storage.

        Args:
            bundle: Directory containing python/ and application/.
            data: Optional isolated data-directory override.
            port: Local dashboard port.

        Returns:
            None.
        """
        self.bundle = Path(bundle).resolve()
        self.root = Path(data or user_directory()).resolve()
        self.port = port
        self.url = f"http://localhost:{port}"
        self.control = self.root / "data/desktop-control"
        self.python = (
            self.bundle
            / "python"
            / ("python.exe" if sys.platform == "win32" else "bin/python3")
        )
        self.application = self.bundle / "application"
        self.root.mkdir(parents=True, exist_ok=True)
        for name in ("data", "logs", "backups"):
            (self.root / name).mkdir(exist_ok=True)
        shutil.copyfile(self.application / ".env.example", self.root / ".env.example")

    def alive(self):
        """Check the heartbeat for this data directory's supervisor.

        Args:
            None.

        Returns:
            bool: Whether the supervisor is recently active.
        """
        try:
            return 0 <= time.time() - (self.control / "heartbeat").stat().st_mtime < 10
        except OSError:
            return False

    def start(self, reconfigure=False):
        """Launch or resume the owned application, refusing occupied foreign ports.

        Args:
            reconfigure: Stop existing children before loading edited configuration.

        Returns:
            None. Dashboard is healthy when the call returns.

        Raises:
            RuntimeError: Port conflict, missing runtime, startup failure or timeout.
        """
        if reconfigure:
            self.stop()
        if not self.python.is_file():
            raise RuntimeError(
                "Bundled Python is missing. Extract the entire download again."
            )
        process = None
        if self.alive():
            (self.control / "resume-dashboard").touch()
        else:
            with socket.socket() as probe:
                probe.settimeout(1)
                if probe.connect_ex(("127.0.0.1", self.port)) == 0:
                    raise RuntimeError(
                        f"Port {self.port} is in use. Stop the other instance before starting."
                    )
            env = dict(os.environ)
            # Frozen GUI library paths must not leak into the independent Python runtime.
            for key in ("LD_LIBRARY_PATH", "DYLD_LIBRARY_PATH"):
                env.pop(key, None)
                if key + "_ORIG" in env:
                    env[key] = env[key + "_ORIG"]
            for key in ("PYTHONHOME", "VIRTUAL_ENV"):
                env.pop(key, None)
            env.update(
                PYTHONPATH=str(self.application),
                PYTHONNOUSERSITE="1",
                CLAN_DESKTOP_CONTROL=str(self.control),
                CLAN_DASHBOARD_SCRIPT=str(self.application / "dashboard/navigation.py"),
                CLAN_DASHBOARD_PORT=str(self.port),
                STREAMLIT_BROWSER_GATHER_USAGE_STATS="false",
                JOB_LOCK_DIR=str(self.root / "data/locks"),
                SCHEDULER_CONFIG_FILE=str(self.root / "data/scheduler.json"),
            )
            with (self.root / "logs/desktop-startup.log").open("ab") as log:
                process = subprocess.Popen(  # pylint: disable=consider-using-with
                    [str(self.python), "-m", "scripts.run_app"],
                    cwd=self.root,
                    env=env,
                    stdin=subprocess.DEVNULL,
                    stdout=log,
                    stderr=log,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                    start_new_session=os.name != "nt",
                )
        deadline = time.monotonic() + 180
        while time.monotonic() < deadline:
            if process is not None and process.poll() is not None:
                raise RuntimeError(
                    f"Application startup failed. See {self.root / 'logs/desktop-startup.log'}."
                )
            try:
                with urlopen(self.url + "/_stcore/health", timeout=2) as response:
                    if self.alive() and response.status == 200:
                        return
            except (OSError, URLError, HTTPException):
                pass
            time.sleep(0.5)
        raise RuntimeError(
            "Startup timed out. Check desktop-startup.log; use Stop all to stop."
        )

    def stop(self):
        """Request graceful shutdown without killing processes by port or saved PID.

        Args:
            None.

        Returns:
            None. The owned supervisor has stopped.

        Raises:
            RuntimeError: Shutdown did not complete within its grace period.
        """
        if not self.alive():
            return
        temporary = self.control / "desktop-request.tmp"
        temporary.write_text(
            json.dumps({"mode": "all", "not_before": time.time()}), encoding="utf-8"
        )
        temporary.replace(self.control / "request.json")
        deadline = time.monotonic() + 60
        while self.alive() and time.monotonic() < deadline:
            time.sleep(0.2)
        if self.alive():
            raise RuntimeError(
                "Shutdown is still pending. Check logs before restarting."
            )
