"""
================================================================================
Filename: controls.py
Description: Confirmed application lifecycle controls for the dashboard.
Author: Raphael Smilet
Date Created: 2026-10-05
Last Modified: 2026-10-05
Version: 0.1.0
Python Version: 3.12
================================================================================
"""

import streamlit as st

from app.services.application_control import control_available, request_shutdown


@st.dialog("Close application", dismissible=False)
def confirm_close():
    """Display shutdown choices and submit only an explicit confirmation.

    Args:
        None.

    Returns:
        None.
    """
    st.warning("This affects everyone using this application instance.")
    choice = st.radio(
        "What should stop?",
        [
            "Dashboard only — keep scheduler running",
            "Everything — dashboard and scheduler",
        ],
    )
    st.caption(
        "The scheduler does not need the web port. Closing the dashboard stops its "
        "web server; closing everything also stops scheduled jobs. Your browser tab "
        "may remain open and show a disconnected page."
    )
    st.caption("With Docker, choose Everything to release the published host port.")
    cancel, confirm = st.columns(2)
    if cancel.button("Cancel", key="cancel_close"):
        st.session_state["close_dialog_open"] = False
        st.rerun()
    if confirm.button("Confirm close", type="primary", key="confirm_close"):
        try:
            request_shutdown("dashboard" if choice.startswith("Dashboard") else "all")
        except (OSError, RuntimeError, ValueError) as error:
            st.error(str(error))
        else:
            st.session_state["close_dialog_open"] = False
            st.success("Shutdown requested. The selected services will stop shortly.")


def render_close_button():
    """Render a shutdown button when an owning supervisor is available.

    Args:
        None.

    Returns:
        None.
    """
    available = control_available()
    if st.button("Close", key="close_application", disabled=not available):
        st.session_state["close_dialog_open"] = True
    if available and st.session_state.get("close_dialog_open", False):
        confirm_close()
    if not available:
        st.caption(
            "Shutdown controls require launching with python -m scripts.run_app."
        )
