"""
WAUG 2026 — report and live dashboard.

Entry point for Streamlit Cloud. `st.navigation` picks the page; every page
reads its numbers from the same cached API layer in `waug_core.py`.
"""

from pathlib import Path

import streamlit as st

# the official WAUG mark, used as the tab / link icon
LOGO = Path(__file__).parent / "assets" / "waug-logo.png"

st.set_page_config(
    page_title="WAUG 2026 · Report & Dashboard",
    page_icon=str(LOGO) if LOGO.exists() else "🏅",
    layout="wide",
    initial_sidebar_state="expanded",
)

pages = [
    st.Page("report.py", title="Report", icon="📄", default=True),
    st.Page("dashboard.py", title="Dashboard", icon="📊"),
    st.Page("data.py", title="Data", icon="🗂️"),
    st.Page("team.py", title="Team", icon="👤"),
]

st.navigation(pages).run()
