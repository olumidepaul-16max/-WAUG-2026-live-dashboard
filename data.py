"""
WAUG 2026 — data page.

Everything behind the report, downloadable, plus the endpoint list so the
work can be checked or repeated.
"""

import pandas as pd
import streamlit as st

import ui
from waug_core import AUTHOR, load_report, report_tables

ui.page_css()

rep = load_report()
if rep.get("error"):
    st.error(f"⚠️ Could not reach the AlliSports feed — {rep['error']}")
    st.stop()

tables = report_tables()
if tables.get("error"):
    st.error(f"⚠️ {tables['error']}")
    st.stop()

ui.toc([
    ("d0", "Downloads"),
    ("d1", "What each file holds"),
    ("d2", "The endpoints"),
    ("d3", "Checks"),
])

ui.eyebrow("WAUG 2026 &nbsp;·&nbsp; Data &nbsp;·&nbsp; AlliSports Data API")
ui.display("Everything the report is built on.")
ui.lede(
    "Four files, all rebuilt from the same feed the dashboard reads. The medal table is the official "
    "ranking; the results file is one row per medal with the school and the athlete, so any number in the "
    "report can be reproduced from it."
)
ui.byline(f"Prepared by <b>{AUTHOR}</b> &nbsp;·&nbsp; data partner: <b>AlliSports Data</b>")

# ---------- downloads ----------
st.markdown('<div id="d0"></div>', unsafe_allow_html=True)
ui.chart_title("Downloads  ·  csv, utf-8")
c1, c2, c3, c4 = st.columns(4)

medal = tables["medal"].copy()
medal = medal[["Rank", "School", "Code", "Gold", "Silver", "Bronze", "Total", "Sports", "GoldShare"]]
medal["GoldShare"] = medal["GoldShare"].round(1)

pool = tables["pool"].copy()
pool["PerEvent"] = pool["PerEvent"].round(2)
pool["Share"] = pool["Share"].round(1)

with c1:
    st.download_button(
        "Medal table", medal.to_csv(index=False).encode("utf-8-sig"),
        file_name="waug2026_medal_table.csv", mime="text/csv", use_container_width=True,
    )
with c2:
    st.download_button(
        "Every medal", tables["results"].to_csv(index=False).encode("utf-8-sig"),
        file_name="waug2026_medals.csv", mime="text/csv", use_container_width=True,
    )
with c3:
    st.download_button(
        "Sport pools", pool.to_csv(index=False).encode("utf-8-sig"),
        file_name="waug2026_sports.csv", mime="text/csv", use_container_width=True,
    )
with c4:
    st.download_button(
        "Matches", tables["matches"].to_csv(index=False).encode("utf-8-sig"),
        file_name="waug2026_matches.csv", mime="text/csv", use_container_width=True,
    )

# ---------- file descriptions ----------
ui.section("d1", "01", "Files", "What each file holds")
ui.body(
    f"The <strong>medal table</strong> has one row per university with the official rank, the three medal "
    "counts, the total, the number of sports medalled in and the share of that total which was gold. "
    f"The <strong>medal file</strong> has one row per medal ({rep['total_medals']} rows) with the sport, event, "
    "slot, university and athlete where the feed names one — this is the file to pivot from."
)
ui.body(
    f"<strong>Sport pools</strong> counts events and medals per sport, including medals per event, which is how the "
    "taekwondo and badminton difference in section 7 of the report is measured. <strong>Matches</strong> carries the "
    f"final score and, where it exists, the penalty score for all {rep['match_count']} fixtures."
)

tabs = st.tabs(["Medal table", "Every medal", "Sport pools", "Matches"])
with tabs[0]:
    st.dataframe(medal, hide_index=True, use_container_width=True)
with tabs[1]:
    st.dataframe(tables["results"].head(200), hide_index=True, use_container_width=True)
    st.caption(f"Showing the first 200 of {len(tables['results'])} rows — download the file for all of them.")
with tabs[2]:
    st.dataframe(pool, hide_index=True, use_container_width=True)
with tabs[3]:
    st.dataframe(tables["matches"], hide_index=True, use_container_width=True)

# ---------- endpoints ----------
ui.section("d2", "02", "Source", "The endpoints behind it")
ui.body(
    "The feed is read server-side with the key in an <code>x-api-key</code> header, so no request from the "
    "browser ever carries it. Responses are cached for five minutes; the dashboard adds a manual refresh."
)
endpoints = pd.DataFrame([
    ("/sports", "The 20-sport catalogue with codes", "used for every label"),
    ("/medal-table", "Official ranking and medal totals", "the table in the report"),
    ("/results", "Every event with its medal list", "concentration, breadth, quality"),
    ("/matches", "Fixtures with final score and penalties", "team-game margins"),
    ("/events", "Schedule, venue and status", "the coverage caveats"),
    ("/events/{id}/competition", "Group tables and knockout rounds", "the dashboard standings tab"),
    ("/matches/{id}/analytics", "Goals by period, cards, comebacks", "dashboard match detail"),
    ("/matches/{id}/box-score", "Basketball box score", "dashboard box score"),
    ("/universities", "23 universities and their totals", "cross-checking the table"),
])
st.dataframe(
    endpoints.rename(columns={0: "Endpoint", 1: "What it returns", 2: "Used for"}),
    hide_index=True, use_container_width=True,
)

# ---------- checks ----------
ui.section("d3", "03", "Checks", "Verification")
k1, k2, k3 = st.columns(3)
k1.metric("Rows checked", rep["school_count"], "one per university")
k2.metric("Differences", rep["mismatches"], "rebuilt table vs official")
k3.metric("Provisional medals", 0 if not rep["includesProvisional"] else "some", "flagged by the feed")

ui.body(
    f"Counting the medals in the results file by school reproduces the official table exactly: "
    f"{rep['total_medals']} medals, {rep['school_count']} rows, {rep['mismatches']} differences. That is the check "
    "that makes the rest of the analysis safe to build on. The two known gaps are that "
    f"{rep['undated_medals']} medals have no date and five sports in the catalogue have no events at all."
)

ui.footer(
    f"Data: <b>AlliSports Data</b> — official data partner of WAUG 2026 &nbsp;·&nbsp; prepared by <b>{AUTHOR}</b>"
)
