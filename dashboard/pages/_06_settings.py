"""
================================================================================
Filename: _06_settings.py
Description: Streamlit settings page.
Author: Raphael Smilet
Date Created: 2026-07-03
Last Modified: 2026-10-06
Version: 0.5.4
================================================================================
"""

import streamlit as st


from dashboard.functions import (
    get_settings_page_data,
    get_log_data,
    get_job_health_data,
    get_scheduler_settings_data,
    save_scheduler_settings,
)

st.set_page_config(page_title="Settings", layout="wide")
st.title("⚙️ Settings")
data = get_settings_page_data()

st.header("Database")
for labels, keys in (
    (
        ("Members", "Snapshots", "Contribution Scores"),
        ("members", "snapshots", "contribution_scores"),
    ),
    (
        ("War Seasons", "River Races", "Participations"),
        ("war_seasons", "river_races", "participations"),
    ),
):
    for column, label, key in zip(st.columns(3), labels, keys):
        with column:
            st.metric(label, data["database"][key])

st.divider()
st.header("Application")
for label, key in (
    ("Clan Tag", "clan_tag"),
    ("Database", "database_url"),
    ("Log Level", "log_level"),
    ("API Token", "api_token_mask"),
):
    st.text_input(label, value=data[key], disabled=True)

st.divider()
st.header("Environment")
st.code(data["environment"], language="text")
st.divider()
st.header("Maintenance")
left, right = st.columns(2)
with left:
    if st.button("Refresh page"):
        st.rerun()
with right:
    st.download_button(
        "Export configuration",
        data=data["configuration_export"],
        file_name="settings.txt",
    )

st.divider()
st.header("📋 Recent Logs")
st.caption(
    "Scroll within the box below to see more. Useful for troubleshooting, or to copy/share if something isn't working."
)
line_count = st.selectbox("Lines to show", [50, 200, 500, 1000], index=1)
logs = get_log_data(line_count)
if logs is not None:
    st.code(logs["recent"], language="log", height=400)
    st.download_button(
        "📥 Download full log",
        data=logs["full"],
        file_name="clan_manager.log",
        mime="text/plain",
    )
else:
    st.info("No log file found yet.")


st.divider()
st.header("Job Health")
st.dataframe(get_job_health_data(), hide_index=True, width="stretch")
st.header("Scheduler")
schedule = get_scheduler_settings_data()
if schedule["error"]:
    st.error(f"Stored schedule is invalid: {schedule['error']}")
st.caption(
    "Times use the configured scheduler timezone. "
    "Saved settings are picked up within five seconds. "
    "Disabling scheduling does not interrupt a running job."
)
with st.form("scheduler_settings"):
    enabled = st.checkbox("Enable scheduler", value=schedule["config"]["enabled"])
    intervals = {}
    for name, value in schedule["config"]["intervals"].items():
        intervals[name] = st.number_input(
            f"{name} interval (minutes)", min_value=1, max_value=1440, value=value
        )
    daily = {}
    for name, value in schedule["config"]["daily"].items():
        daily[name] = st.text_input(f"{name} time (HH:MM)", value=value)
    if st.form_submit_button("Save schedule"):
        try:
            save_scheduler_settings(enabled, intervals, daily)
            st.success("Schedule saved.")
        except (ValueError, OSError) as error:
            st.error(str(error))
