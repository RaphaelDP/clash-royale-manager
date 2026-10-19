"""
Filename: test_launcher.py
Description: Verify private first-run settings and safe Docker launcher failures.
Author: Raphael Smilet
Date Created: 2026-10-06
Last Modified: 2026-10-19
Version: 0.1.4
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
    for name in (
        "launcher.py",
        "windows/windows_launcher.exe",
        "linux/linux_launcher.AppImage",
    ):
        (folder / name).parent.mkdir(parents=True, exist_ok=True)
        (folder / name).touch()
    bundle = folder / "macos/macos_launcher.app"
    bundle.mkdir(parents=True)
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


@pytest.mark.parametrize(
    "executable",
    [
        "linux/linux_launcher.AppImage",
        "windows/windows_launcher.exe",
        "macos/macos_launcher.app/Contents/MacOS/macos_launcher",
    ],
)
def test_platform_folder_finds_application_root(tmp_path, monkeypatch, executable):
    """Locate the same application from nested platform-specific executable paths.

    Args:
        tmp_path: Temporary installation directory.
        monkeypatch: Fixture restoring executable and environment overrides.
        executable: Platform-specific relative launcher path.

    Returns:
        None. Assertions verify configuration and Compose discovery after relocation.
    """
    (tmp_path / "docker-compose.yml").touch()
    binary = tmp_path / "launch" / executable
    binary.parent.mkdir(parents=True)
    binary.touch()
    monkeypatch.delenv("APPIMAGE", raising=False)
    monkeypatch.setattr(launcher.sys, "frozen", True, raising=False)
    monkeypatch.setattr(launcher.sys, "executable", str(binary))
    assert launcher.project_root() == tmp_path
    if executable.endswith("AppImage"):
        monkeypatch.setenv("APPIMAGE", str(binary))
        monkeypatch.setattr(launcher.sys, "executable", "/tmp/extracted/python")
        assert launcher.project_root() == tmp_path


def test_browser_drops_snap_editor_modules_but_keeps_desktop_access(monkeypatch):
    """Keep the host browser from loading incompatible editor Snap libraries.

    Args:
        monkeypatch: Fixture restoring synthetic environment and process overrides.

    Returns:
        None. Verifies browser-only sanitation without mutating the parent environment.
    """
    monkeypatch.setattr(launcher.sys, "platform", "linux")
    monkeypatch.setenv("SNAP", "/snap/code/current")
    monkeypatch.setenv("LD_LIBRARY_PATH_ORIG", "/snap/core20/current/lib:/opt/host/lib")
    monkeypatch.setenv(
        "GIO_MODULE_DIR", "/home/test/snap/code/common/.cache/gio-modules"
    )
    monkeypatch.setenv("GTK_MODULES", "atk-bridge:canberra-gtk-module:custom-module")
    monkeypatch.setenv("DISPLAY", ":42")
    monkeypatch.setenv("DBUS_SESSION_BUS_ADDRESS", "unix:path=/run/user/test/bus")
    spawn = MagicMock()
    monkeypatch.setattr(launcher.subprocess, "Popen", spawn)
    launcher.open_dashboard()
    env = spawn.call_args.kwargs["env"]
    assert env["LD_LIBRARY_PATH"] == "/opt/host/lib"
    assert "GIO_MODULE_DIR" not in env
    assert env["GTK_MODULES"] == "custom-module"
    assert env["DISPLAY"] == ":42"
    assert env["DBUS_SESSION_BUS_ADDRESS"] == "unix:path=/run/user/test/bus"
    assert launcher.os.environ["GTK_MODULES"].startswith("atk-bridge:")


def test_non_snap_desktop_settings_are_preserved():
    """Avoid changing desktop module preferences outside a Snap environment.

    Args:
        None.

    Returns:
        None. Confirms custom native library/module paths remain intact.
    """
    env = {"GTK_MODULES": "atk-bridge", "GIO_MODULE_DIR": "/opt/modules"}
    original = dict(env)
    launcher.clean_snap_desktop_environment(env)
    assert env == original
