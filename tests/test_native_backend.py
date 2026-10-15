"""
Filename: test_native_backend.py
Description: Verify standalone path selection and protection of foreign services.
Author: Raphael Smilet
Date Created: 2026-10-07
Last Modified: 2026-10-15
Version: 0.1.2
"""

import socket
from pathlib import Path
from unittest.mock import MagicMock
import pytest
from launch.native_backend import NativeBackend, user_directory
from scripts.smoke_standalone import cleanup, save_diagnostics


def test_native_storage_is_separate_from_bundle(tmp_path, monkeypatch):
    """Keep user files outside program files and retain existing configuration.

    Args:
        tmp_path: Temporary directory.
        monkeypatch: Platform and environment override fixture.

    Returns:
        None. Asserts default storage and preservation.
    """
    monkeypatch.setattr("launch.native_backend.sys.platform", "linux")
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "user"))
    assert user_directory() == tmp_path / "user/ClashRoyaleClanManager"
    application = tmp_path / "bundle/application"
    application.mkdir(parents=True)
    (application / ".env.example").write_text("CR_API_TOKEN=\n", encoding="utf-8")
    backend = NativeBackend(application.parent)
    private = backend.root / ".env"
    private.write_text("CR_API_TOKEN=synthetic", encoding="utf-8")
    NativeBackend(application.parent)
    assert private.read_text(encoding="utf-8") == "CR_API_TOKEN=synthetic"


def test_native_foreign_port_is_not_modified(tmp_path, monkeypatch):
    """Refuse an occupied port without spawning or terminating a process.

    Args:
        tmp_path: Temporary directory.
        monkeypatch: Process-spawn interception fixture.

    Returns:
        None. Foreign listener remains open.
    """
    application = tmp_path / "bundle/application"
    application.mkdir(parents=True)
    (application / ".env.example").write_text("", encoding="utf-8")
    spawn = MagicMock()
    monkeypatch.setattr("launch.native_backend.subprocess.Popen", spawn)
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        backend = NativeBackend(
            application.parent, tmp_path / "user", listener.getsockname()[1]
        )
        backend.python = Path(__file__)
        with pytest.raises(RuntimeError, match="in use"):
            backend.start()
        backend.stop()
        assert not spawn.called
        with socket.socket() as probe:
            assert probe.connect_ex(listener.getsockname()) == 0


def test_native_shutdown_waits_for_process_after_stale_heartbeat(tmp_path, monkeypatch):
    """Wait for actual owned-process exit even if its heartbeat has expired.

    Args:
        tmp_path: Isolated bundle and control directory.
        monkeypatch: Clock and process interception fixture.

    Returns:
        None. Confirms a stop request and process-exit observation.
    """
    application = tmp_path / "bundle/application"
    application.mkdir(parents=True)
    (application / ".env.example").write_text("", encoding="utf-8")
    backend = NativeBackend(application.parent, tmp_path / "user")
    backend.control.mkdir(parents=True)
    process = MagicMock()
    process.poll.side_effect = [None, None, 0]
    backend.process = process
    monkeypatch.setattr(backend, "alive", lambda: False)
    monkeypatch.setattr("launch.native_backend.time.sleep", lambda _: None)
    backend.stop()
    assert (backend.control / "request.json").exists()
    assert process.poll.call_count == 3
    assert backend.process is None


def test_native_health_uses_ipv4_without_proxy(tmp_path, monkeypatch):
    """Keep local health requests away from IPv6 resolution and external proxies.

    Args:
        tmp_path: Isolated application directory.
        monkeypatch: Synthetic proxy environment fixture.

    Returns:
        None. Confirms the exact bind address and no proxy handlers.
    """
    application = tmp_path / "bundle/application"
    application.mkdir(parents=True)
    (application / ".env.example").write_text("", encoding="utf-8")
    monkeypatch.setenv("http_proxy", "http://proxy.invalid:1234")
    backend = NativeBackend(application.parent, tmp_path / "user", 12345)
    assert backend.url == "http://127.0.0.1:12345"
    assert not any(
        hasattr(handler, "proxies") for handler in backend.health_client.handlers
    )


@pytest.mark.parametrize("failed", [True, False])
def test_smoke_cleanup_retains_files_if_shutdown_fails(tmp_path, failed):
    """Preserve files used by a running process and avoid masking a test failure.

    Args:
        tmp_path: Isolated directory representing test data.
        failed: Whether a primary startup error is already propagating.

    Returns:
        None. Verifies retained data and cleanup error propagation rules.
    """
    marker = tmp_path / "database"
    marker.write_text("test data", encoding="utf-8")
    backend = MagicMock()
    backend.stop.side_effect = RuntimeError("still running")
    if failed:
        cleanup(backend, tmp_path, failed=True)
    else:
        with pytest.raises(RuntimeError, match="still running"):
            cleanup(backend, tmp_path, failed=False)
    assert marker.read_text(encoding="utf-8") == "test data"


def test_smoke_diagnostics_preserve_logs_without_configuration(tmp_path):
    """Keep synthetic startup evidence outside the disposable data directory.

    Args:
        tmp_path: Isolated test files and output directory.

    Returns:
        None. Verifies log persistence and exclusion of configuration/database files.
    """
    backend = MagicMock()
    backend.root = tmp_path / "user"
    backend.url = "http://127.0.0.1:12345"
    backend.alive.return_value = True
    backend.process.poll.return_value = None
    logs = backend.root / "logs"
    logs.mkdir(parents=True)
    (logs / "desktop-startup.log").write_text("starting dashboard", encoding="utf-8")
    (backend.root / ".env").write_text("synthetic configuration", encoding="utf-8")
    destination = tmp_path / "diagnostics"
    save_diagnostics(backend, destination)
    assert (destination / "desktop-startup.log").read_text() == "starting dashboard"
    assert {path.name for path in destination.iterdir()} == {
        "desktop-startup.log",
        "status.json",
    }
