"""
WAUG 2026 — report and live dashboard.

Entry point for Streamlit Cloud. `st.navigation` picks the page; every page
reads its numbers from the same cached API layer in `waug_core.py`.
"""

import streamlit as st

st.set_page_config(
    page_title="WAUG 2026 · Report & Dashboard",
    page_icon="🏅",
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
