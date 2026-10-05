"""
Filename: test_launcher.py
Description: Verify private first-run settings and safe Docker launcher failures.
Author: Raphael Smilet
Date Created: 2026-10-06
Last Modified: 2026-10-06
Version: 0.1.2
"""

from unittest.mock import MagicMock
import pytest
from launch import launcher
from scripts.package_release import source_files


def test_occupied_port_does_not_start_another_project(tmp_path, monkeypatch):
    """Reject a foreign listener before modifying containers or data folders.

    Args:
        tmp_path: Isolated project folder with fake configuration.
        monkeypatch: Fixture restoring patched commands and sockets.

    Returns:
        None. Assertions check startup was refused without a Docker mutation.
    """
    (tmp_path / "docker-compose.yml").touch()
    (tmp_path / ".env").touch()
    command = MagicMock(return_value="")
    monkeypatch.setattr(launcher, "docker_command", command)
    probe = MagicMock()
    probe.__enter__.return_value.connect_ex.return_value = 0
    monkeypatch.setattr(launcher.socket, "socket", lambda: probe)
    with pytest.raises(RuntimeError, match="already used"):
        launcher.start_application(tmp_path)
    assert command.call_count == 1
    assert not (tmp_path / "data").exists()


def test_docker_failure_does_not_expose_output(tmp_path, monkeypatch):
    """Keep captured Docker output out of user-facing exception messages.

    Args:
        tmp_path: Isolated project folder.
        monkeypatch: Fixture restoring command lookup and process execution.

    Returns:
        None. Assertions verify a generic, actionable error.
    """
    monkeypatch.setattr(launcher.shutil, "which", lambda _: "/bin/docker")
    monkeypatch.setattr(
        launcher.subprocess,
        "run",
        MagicMock(
            return_value=MagicMock(
                returncode=1, stdout="private value", stderr="private value"
            )
        ),
    )
    with pytest.raises(RuntimeError, match="Check that Docker is running") as error:
        launcher.docker_command(tmp_path, "up", "-d")
    assert "private value" not in str(error.value)


def test_source_archive_excludes_compiled_launchers(tmp_path):
    """Keep native build products out of portable source distributions.

    Args:
        tmp_path: Temporary source tree containing synthetic build outputs.

    Returns:
        None. Assertions check that only launcher source is selected.
    """
    folder = tmp_path / "launch"
    folder.mkdir()
    for name in ("launcher.py", "windows_launcher.exe", "linux_launcher.AppImage"):
        (folder / name).touch()
    bundle = folder / "macos_launcher.app"
    bundle.mkdir()
    (bundle / "binary").touch()
    assert [path.name for path in source_files(tmp_path)] == ["launcher.py"]


@pytest.mark.parametrize("owned", ["", "container-id"])
def test_start_retries_reset_without_rebuilding(tmp_path, monkeypatch, owned):
    """Survive an early connection reset and reuse existing container images.

    Args:
        tmp_path: Isolated project files.
        monkeypatch: Fixture replacing Docker, socket, HTTP and sleep calls.
        owned: Running container identity, or empty for a stopped application.

    Returns:
        None. Assertions verify retries and absence of implicit rebuilds.
    """
    (tmp_path / "docker-compose.yml").touch()
    (tmp_path / ".env").touch()
    command = MagicMock(return_value=owned)
    monkeypatch.setattr(launcher, "docker_command", command)
    probe = MagicMock()
    probe.__enter__.return_value.connect_ex.return_value = 1
    monkeypatch.setattr(launcher.socket, "socket", lambda: probe)
    response = MagicMock()
    response.__enter__.return_value.status = 200
    request = MagicMock(side_effect=[ConnectionResetError(104, "reset"), response])
    monkeypatch.setattr(launcher, "urlopen", request)
    monkeypatch.setattr(launcher.time, "sleep", lambda _: None)
    launcher.start_application(tmp_path)
    assert request.call_count == 2
    arguments = [call.args for call in command.call_args_list]
    assert not any(
        "--build" in args or "--force-recreate" in args for args in arguments
    )
    if owned:
        assert arguments[1][1:] == ("up", "-d", "app")
        assert arguments[2][1:4] == ("exec", "-T", "app")
    else:
        assert arguments[1][1:] == ("up", "-d", "app")
