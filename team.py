"""
WAUG 2026 — team page.
"""

import streamlit as st

import ui
from waug_core import AUTHOR, load_report

ui.page_css()

rep = load_report()
meta = "" if rep.get("error") else f"{rep['school_count']} universities · {rep['total_medals']} medals"

ui.eyebrow("WAUG 2026 &nbsp;·&nbsp; Team")
ui.display("One analyst, two views of the same Games.")
ui.lede(
    "A written report for reading and a live dashboard for checking. Both read the same cached feed, so a "
    "number in the prose is the number in the table."
)

st.markdown(
    f"""
<div class="author" style="padding:26px 26px;">
  <div class="avatar" style="width:72px;height:72px;font-size:1.35rem;">OP</div>
  <div>
    <h3 style="font-size:1.5rem;">{AUTHOR}</h3>
    <div class="role">Data analysis · dashboard · report</div>
    <p style="font-size:.94rem;">Collected the data from the AlliSports Data API, rebuilt the medal table from the
    individual results to verify it, ran the comparisons in the report and built both the dashboard and this
    site.</p>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

a, b, c = st.columns(3)
a.metric("Report", "11 sections", "from concentration to coverage")
b.metric("Dashboard", "20 sports", "fixtures, results, standings")
c.metric("Data", "4 files", meta or "medals, pools, matches")

ui.section("t1", "01", "Work", "What was built")
ui.body(
    "<strong>The report.</strong> A single long read that asks what produced the medal table rather than what it "
    "shows: how concentrated the medals were, whether breadth or conversion won them, where the host's 63-medal "
    "lead came from, how sensitive the ranking is to the scoring rule, and what the table leaves out."
)
ui.body(
    "<strong>The dashboard.</strong> A per-sport view of the same Games — fixtures and live scores, results with "
    "medal lists, group tables or a derived league table where the feed publishes none, and cross-sport statistics. "
    "Deep links work, so a single sport can be shared (<code>?sport=FBL</code>)."
)
ui.body(
    "<strong>The data page.</strong> The medal table, all 478 medal rows, the sport pools and every match as CSV, "
    "with the endpoints listed so the figures can be reproduced."
)

ui.section("t2", "02", "Stack", "How it is put together")
ui.body(
    "Python and pandas for the shaping, Plotly for the charts, Streamlit for the interface. One cached data layer "
    "(`waug_core.py`) sits under all three pages, which is why the report, the dashboard and the downloads can "
    "never disagree. The API key lives in Streamlit secrets and is sent server-side in the "
    "<code>x-api-key</code> header; it never reaches the browser."
)

ui.section("t3", "03", "Credit", "Data and attribution")
ui.body(
    "Results, schedules and medal standings come from the <strong>AlliSports Data API</strong>, the official data "
    "partner of WAUG 2026. The analysis, the dashboard and the report are independent work built on that feed. "
    "Any error in the interpretation is mine, not the data partner's."
)
ui.byline(
    "Games: 2–12 October 2026 &nbsp;·&nbsp; Obafemi Awolowo University, Ile-Ife &nbsp;·&nbsp; "
    "15th West African University Games"
)

ui.footer(f"Report and dashboard by <b>{AUTHOR}</b> &nbsp;·&nbsp; Data: <b>AlliSports Data</b>")
