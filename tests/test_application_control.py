"""
================================================================================
Filename: test_application_control.py
Description: Verify confirmed shutdown, owned-process cleanup, and released web ports.
Author: Raphael Smilet
Date Created: 2026-10-05
Last Modified: 2026-10-05
Version: 0.1.0
Python Version: 3.12
================================================================================
"""

import socket
import subprocess
import sys
import time
from threading import Event, Thread

import pytest
from streamlit.testing.v1 import AppTest

from app.services import application_control as control
from scripts.run_app import stop_processes, supervise_processes


def test_missing_supervisor_rejects_shutdown(monkeypatch):
    """Refuse shutdown without an inherited live supervisor channel.

    Args:
        monkeypatch: Fixture restoring environment changes.

    Returns:
        None. Assertions verify unsupported launch modes cannot signal processes.
    """
    monkeypatch.delenv(control.CONTROL_ENV, raising=False)
    assert not control.control_available()
    with pytest.raises(RuntimeError, match="Supervisor unavailable"):
        control.request_shutdown("all")
    with pytest.raises(ValueError):
        control.request_shutdown("invalid")


def test_invalid_request_is_discarded(tmp_path):
    """Discard corrupt requests without treating them as a shutdown.

    Args:
        tmp_path: Isolated control directory.

    Returns:
        None. Assertions verify the invalid request is removed and ignored.
    """
    path = tmp_path / "request.json"
    path.write_text('{"mode":"invalid","not_before":0}')
    assert control.pending_shutdown(tmp_path) is None
    assert not path.exists()


@pytest.mark.parametrize("mode", ["dashboard", "all"])
def test_shutdown_releases_port_and_preserves_selected_process(
    tmp_path, monkeypatch, mode
):
    """Exercise supervisor shutdown against real harmless child processes.

    Args:
        tmp_path: Private temporary control directory.
        monkeypatch: Fixture restoring the inherited control environment.
        mode: Whether the scheduler should remain alive after web shutdown.

    Returns:
        None. Assertions verify actual socket release and scheduler process state.
    """
    monkeypatch.setenv(control.CONTROL_ENV, str(tmp_path))
    (tmp_path / "heartbeat").touch()
    # Children are cleaned up in the finally block even after failed assertions.
    # pylint: disable=consider-using-with
    web = subprocess.Popen(
        [
            sys.executable,
            "-u",
            "-c",
            (
                "import socket,time; s=socket.socket(); "
                "s.bind(('127.0.0.1',0)); s.listen(); "
                "print(s.getsockname()[1],flush=True); time.sleep(60)"
            ),
        ],
        stdout=subprocess.PIPE,
        text=True,
    )
    scheduler = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
    processes = {"dashboard": web, "scheduler": scheduler}
    stop = Event()
    errors = []

    def supervise():
        """Run the supervisor loop and ensure its remaining children are reaped.

        Args:
            None.

        Returns:
            None. Unexpected exceptions are captured for test assertions.
        """
        try:
            supervise_processes(processes, stop, tmp_path)
        except Exception as error:  # Surface thread failures to the test.
            errors.append(error)
        finally:
            stop_processes(processes.values())

    thread = Thread(target=supervise)
    try:
        port = int(web.stdout.readline())
        thread.start()
        control.request_shutdown(mode)
        deadline = time.monotonic() + 10
        while web.poll() is None and time.monotonic() < deadline:
            time.sleep(0.05)
        assert web.poll() is not None
        if mode == "all":
            thread.join(timeout=5)
            assert not thread.is_alive()
            assert scheduler.poll() is not None
        else:
            assert scheduler.poll() is None
            assert thread.is_alive()
        with socket.socket() as released:
            released.bind(("127.0.0.1", port))
        assert not errors
    finally:
        stop.set()
        if thread.ident is not None:
            thread.join(timeout=25)
        stop_processes([web, scheduler])
        web.stdout.close()


@pytest.mark.parametrize("selection, expected", [(0, "dashboard"), (1, "all")])
def test_close_dialog_requires_confirmation(monkeypatch, selection, expected):
    """Submit no shutdown until the confirmation button is explicitly clicked.

    Args:
        monkeypatch: Fixture replacing supervisor availability and request submission.
        selection: Index of the chosen dialog mode.
        expected: Expected service request after confirmation.

    Returns:
        None. Assertions verify confirmation and mode selection.
    """
    calls = []
    monkeypatch.setattr("dashboard.controls.control_available", lambda: True)
    monkeypatch.setattr("dashboard.controls.request_shutdown", calls.append)
    app = AppTest.from_string(
        "from dashboard.controls import render_close_button\nrender_close_button()"
    ).run()
    app.button(key="close_application").click().run()
    assert not calls
    app.radio[0].set_value(app.radio[0].options[selection]).run()
    app.button(key="confirm_close").click().run()
    assert not app.exception
    assert calls == [expected]


def test_cancel_close_leaves_processes_running(monkeypatch):
    """Cancel the dialog without submitting a lifecycle request.

    Args:
        monkeypatch: Fixture replacing service calls for an isolated UI test.

    Returns:
        None. Assertions verify cancellation produces no shutdown request.
    """
    calls = []
    monkeypatch.setattr("dashboard.controls.control_available", lambda: True)
    monkeypatch.setattr("dashboard.controls.request_shutdown", calls.append)
    app = AppTest.from_string(
        "from dashboard.controls import render_close_button\nrender_close_button()"
    ).run()
    app.button(key="close_application").click().run()
    app.button(key="cancel_close").click().run()
    assert not app.exception
    assert not calls
