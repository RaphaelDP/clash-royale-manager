"""
Filename: test_native_backend.py
Description: Verify standalone path selection and protection of foreign services.
Author: Raphael Smilet
Date Created: 2026-10-07
Last Modified: 2026-10-07
Version: 0.1.0
"""

import socket
from pathlib import Path
from unittest.mock import MagicMock
import pytest
from launch.native_backend import NativeBackend, user_directory


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
