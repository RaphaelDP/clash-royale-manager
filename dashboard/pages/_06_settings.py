"""
================================================================================
Filename: _06_settings.py
Description: Streamlit settings page.
Author: Raphael Smilet
Date Created: 2026-07-03
Last Modified: 2026-07-07
Version: 0.5.0
================================================================================
"""

from pathlib import Path
import streamlit as st

from app.core.config import settings
from app.core.utils import count

from app.database.session import get_session
from app.database.models import (
    Member,
    Snapshot,
    WarSeason,
    RiverRace,
    WarParticipation,
    ContributionScore,
)

st.set_page_config(
    page_title="Settings",
    layout="wide",
)

st.title("⚙️ Settings")

with get_session() as db:

    st.header("Database")

    c1, c2, c3 = st.columns(3)

    with c1:
        st.metric(
            "Members",
            db.query(count(Member.id)).scalar(),
        )

    with c2:
        st.metric(
            "Snapshots",
            db.query(count(Snapshot.id)).scalar(),
        )

    with c3:
        st.metric(
            "Contribution Scores",
            db.query(count(ContributionScore.id)).scalar(),
        )

    c1, c2, c3 = st.columns(3)

    with c1:
        st.metric(
            "War Seasons",
            db.query(count(WarSeason.id)).scalar(),
        )

    with c2:
        st.metric(
            "River Races",
            db.query(count(RiverRace.id)).scalar(),
        )

    with c3:
        st.metric(
            "Participations",
            db.query(count(WarParticipation.id)).scalar(),
        )

st.divider()

st.header("Application")

st.text_input(
    "Clan Tag",
    value=settings.CLAN_TAG,
    disabled=True,
)

st.text_input(
    "Database",
    value=settings.DATABASE_URL,
    disabled=True,
)

st.text_input(
    "Log Level",
    value=settings.LOG_LEVEL,
    disabled=True,
)

st.text_input(
    "API Token",
    value="*" * 32 if settings.CR_API_TOKEN else "",
    disabled=True,
)

st.divider()

st.header("Environment")

st.code(
    f"""
Python : 3.12
Dashboard : Streamlit
Database : SQLAlchemy
Version : {settings.VERSION}
""",
    language="text",
)

st.divider()

st.header("Maintenance")

c1, c2 = st.columns(2)

with c1:
    if st.button("Refresh page"):
        st.rerun()

with c2:
    st.download_button(
        "Export configuration",
        data=f"""
CLAN_TAG={settings.CLAN_TAG}
DATABASE_URL={settings.DATABASE_URL}
LOG_LEVEL={settings.LOG_LEVEL}
""",
        file_name="settings.txt",
    )

st.divider()

st.header("📋 Recent Logs")

st.caption(
    "Scroll within the box below to see more. Useful for troubleshooting, "
    "or to copy/share if something isn't working."
)

log_path = Path(settings.LOG_FILE)

if log_path.exists():
    with log_path.open("r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()

    line_count = st.selectbox(
        "Lines to show",
        [50, 200, 500, 1000],
        index=1,
    )

    recent_lines = lines[-line_count:]
    st.code(
        "".join(recent_lines) or "Log file is empty.",
        language="log",
        height=400,
    )

    st.download_button(
        "📥 Download full log",
        data=log_path.read_text(encoding="utf-8", errors="replace"),
        file_name="clan_manager.log",
        mime="text/plain",
    )
else:
    st.info("No log file found yet.")
