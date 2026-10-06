"""
Filename: test_dashboard_actions.py
Description: Verify refresh guards survive reruns and reject overlapping callbacks.
Author: Raphael Smilet
Date Created: 2026-10-06
Last Modified: 2026-10-06
Version: 0.1.0
"""

from contextlib import nullcontext
from threading import Event, Thread
from unittest.mock import MagicMock

import pytest
from streamlit.runtime.scriptrunner import RerunData, RerunException
from streamlit.runtime.state.safe_session_state import SafeSessionState
from streamlit.runtime.state.session_state import SessionState
from dashboard import functions


@pytest.fixture
def action_ui(monkeypatch):
    """Replace Streamlit state and output with an isolated session and inert renderer.

    Args:
        monkeypatch: Fixture restoring the Streamlit API after each test.

    Returns:
        dict: Isolated session with a stale legacy flag to exercise recovery.
    """
    state = {"dashboard_action_running": True}
    monkeypatch.setattr(functions.st, "session_state", state)
    monkeypatch.setattr(functions.st, "spinner", lambda _: nullcontext())
    monkeypatch.setattr(functions.st, "error", MagicMock())
    return state


def test_interrupted_action_releases_guard(action_ui):
    """Handle repeated Streamlit interruptions without permanently disabling refresh.

    Args:
        action_ui: Isolated Streamlit session and output fixture.

    Returns:
        None. Assertions check guard release and successful subsequent actions.
    """
    assert action_ui["dashboard_action_running"]
    interrupted = MagicMock(side_effect=RerunException(RerunData()))
    for _ in range(10):
        with pytest.raises(RerunException):
            functions.execute_dashboard_action(interrupted, "Refreshing")
        assert not functions.dashboard_action_running()
    successful = MagicMock(return_value=True)
    functions.execute_dashboard_action(successful, "Retry")
    successful.assert_called_once()


def test_repeated_clicks_do_not_overlap(action_ui):
    """Ignore callbacks while another action owns the session's refresh guard.

    Args:
        action_ui: Isolated Streamlit session and output fixture.

    Returns:
        None. Assertions verify no duplicate work and eventual guard release.
    """
    assert action_ui is not None
    started, finish = Event(), Event()

    def slow_action():
        """Wait for the test to release a simulated slow API request.

        Args:
            None.

        Returns:
            bool: Whether the wait completed within its safety timeout.
        """
        started.set()
        return finish.wait(5)

    worker = Thread(
        target=functions.execute_dashboard_action, args=(slow_action, "Refresh")
    )
    worker.start()
    try:
        assert started.wait(2)
        duplicate = MagicMock()
        for _ in range(20):
            functions.execute_dashboard_action(duplicate, "Duplicate")
        duplicate.assert_not_called()
        assert functions.dashboard_action_running()
    finally:
        finish.set()
        worker.join(6)
    assert not worker.is_alive()
    assert not functions.dashboard_action_running()


def test_cleanup_does_not_yield_to_pending_rerun(action_ui, monkeypatch):
    """Release busy state even when a pending rerun would interrupt session-state writes.

    Args:
        action_ui: Isolated renderer fixture.
        monkeypatch: Fixture installing real Streamlit safe session state.

    Returns:
        None. Assertions verify cleanup finishes before another rerun can interrupt it.
    """
    assert action_ui is not None
    pending = [False]

    def yield_callback():
        """Simulate Streamlit handling a queued click at its next yield point.

        Args:
            None.

        Returns:
            None. Raises a rerun signal when the simulated action has completed.
        """
        if pending[0]:
            raise RerunException(RerunData())

    state = SafeSessionState(SessionState(), yield_callback)
    monkeypatch.setattr(functions.st, "session_state", state)

    def complete_action():
        """Queue another click immediately before refresh cleanup.

        Args:
            None.

        Returns:
            bool: Successful completion of the simulated refresh.
        """
        pending[0] = True
        return True

    functions.execute_dashboard_action(complete_action, "Refresh")
    pending[0] = False
    assert not functions.dashboard_action_running()
