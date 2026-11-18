"""
WAUG 2026 — data page.

Everything behind the report, downloadable, plus the endpoint list so the
work can be checked or repeated. The sidebar carries filters built from what
the files themselves hold — school, medal colour, gender, event type — and
every table and download follows them.
"""

import pandas as pd
import streamlit as st

import ui
from waug_core import (
    AUTHORS,
    api_get, get_analytics, get_competition, get_sport_events,
    load_core, load_report, medals_from_rows, pool_from_selection, report_tables,
)

ui.page_css()

rep = load_report()
if rep.get("error"):
    st.error(f"⚠️ Could not reach the AlliSports feed — {rep['error']}")
    st.stop()

tables = report_tables()
if tables.get("error"):
    st.error(f"⚠️ {tables['error']}")
    st.stop()

sports_map = {s["code"]: s["name"] for s in rep["sports"]}

# ============================================================
# SIDEBAR — filters drawn from the contents of the files
# ============================================================
st.sidebar.markdown('<div class="filters-h">Filters</div>', unsafe_allow_html=True)

universities = sorted(tables["medal"]["School"].dropna().unique())
university = st.sidebar.selectbox(
    "University", ["All universities"] + universities, key="data_uni",
)

genders = sorted({str(g) for g in tables["results"]["Gender"].dropna() if str(g).strip()})
gender = st.sidebar.selectbox(
    "Gender", ["All genders"] + genders, key="data_gender",
    format_func=lambda g: "All genders" if g == "All genders" else g.capitalize(),
)

kinds = sorted({str(k) for k in tables["results"]["Kind"].dropna() if str(k).strip()})
kind = st.sidebar.selectbox(
    "Event type", ["All types"] + kinds, key="data_kind",
    format_func=lambda k: "All types" if k == "All types" else k.capitalize(),
)

medal_pick = st.sidebar.selectbox(
    "Medal", ["All medals", "Gold", "Silver", "Bronze"], key="data_medal",
)

st.sidebar.markdown(
    '<div class="filters-note">These follow the files below: school, medal colour, '
    'gender and individual vs team.</div>',
    unsafe_allow_html=True,
)

if st.sidebar.button("Refresh data", use_container_width=True):
    load_core.clear()
    api_get.clear()
    get_competition.clear()
    get_analytics.clear()
    get_sport_events.clear()
    load_report.clear()
    report_tables.clear()
    st.rerun()

# ============================================================
# APPLY FILTERS
# ============================================================
filtered = (
    university != "All universities" or gender != "All genders"
    or kind != "All types" or medal_pick != "All medals"
)

results = tables["results"].copy()
matches = tables["matches"].copy()

uni_code = None
if university != "All universities":
    match_row = tables["medal"][tables["medal"]["School"] == university]
    uni_code = match_row["Code"].iloc[0] if not match_row.empty else None
    if uni_code:
        results = results[results["University code"] == uni_code]
    matches = matches[
        matches["Home"].eq(university) | matches["Away"].eq(university)
    ]

if gender != "All genders":
    results = results[results["Gender"].astype(str).str.lower() == gender.lower()]

if kind != "All types":
    results = results[results["Kind"].astype(str).str.lower() == kind.lower()]

if medal_pick != "All medals":
    results = results[results["Slot"].astype(str).str.startswith(medal_pick.lower())]

# events in scope drive the medals-per-event denominator
events_scope = tables["events"].copy()
if gender != "All genders":
    events_scope = events_scope[
        events_scope["Gender"].astype(str).str.lower() == gender.lower()
    ]
if kind != "All types":
    events_scope = events_scope[
        events_scope["Kind"].astype(str).str.lower() == kind.lower()
    ]

official_medals = tables["medal"][
    ["Rank", "School", "Code", "Gold", "Silver", "Bronze", "Total", "Sports", "Share"]
].copy()
official_medals["Share"] = official_medals["Share"].round(1)

if filtered:
    medal = medals_from_rows(results)
    pool = pool_from_selection(results, events_scope, sports_map)
else:
    medal = official_medals
    pool = tables["pool"].copy()

pool["PerEvent"] = pool["PerEvent"].round(2)
pool["Share"] = pool["Share"].round(1)

medal_rows = len(results)
event_total = len(events_scope)

# ============================================================
# PAGE
# ============================================================
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
ui.byline(f"Prepared by <b>{AUTHORS}</b> &nbsp;·&nbsp; data partner: <b>AlliSports Data</b>")

if filtered:
    chips = []
    if university != "All universities":
        chips.append(university)
    if medal_pick != "All medals":
        chips.append(f"{medal_pick} only")
    if gender != "All genders":
        chips.append(gender.capitalize())
    if kind != "All types":
        chips.append(f"{kind.capitalize()} events")
    pills = "".join(f'<span class="pill">{c}</span>' for c in chips)
    note = f"{medal_rows} medal row(s) across {event_total} event(s) in this selection"
else:
    pills = '<span class="pill">Whole Games</span>'
    note = f"{medal_rows} medal rows across {event_total} events"
st.markdown(
    f'<div class="filter-bar">{pills}<span class="filter-note">{note}</span></div>',
    unsafe_allow_html=True,
)

# ---------- downloads ----------
st.markdown('<div id="d0"></div>', unsafe_allow_html=True)
ui.chart_title("Downloads  ·  csv, utf-8" + ("  ·  filtered selection" if filtered else ""))
c1, c2, c3, c4 = st.columns(4)

with c1:
    st.download_button(
        "Medal table", medal.to_csv(index=False).encode("utf-8-sig"),
        file_name="waug2026_medal_table.csv", mime="text/csv", use_container_width=True,
    )
with c2:
    st.download_button(
        "Every medal", results.to_csv(index=False).encode("utf-8-sig"),
        file_name="waug2026_medals.csv", mime="text/csv", use_container_width=True,
    )
with c3:
    st.download_button(
        "Sport pools", pool.to_csv(index=False).encode("utf-8-sig"),
        file_name="waug2026_sports.csv", mime="text/csv", use_container_width=True,
    )
with c4:
    st.download_button(
        "Matches", matches.to_csv(index=False).encode("utf-8-sig"),
        file_name="waug2026_matches.csv", mime="text/csv", use_container_width=True,
    )

if filtered:
    st.caption(
        "With a filter on, the medal table is re-ranked inside the selection (gold, then "
        "silver, then bronze) and sport pools count only the medals that remain against the "
        "events in scope, so medals-per-event falls with the filter. Matches follow the "
        "university filter only. Clear the filters for the official Games figures."
    )

# ---------- file descriptions ----------
ui.section("d1", "01", "Files", "What each file holds")
ui.body(
    f"The <strong>medal table</strong> has one row per university with the rank, the three medal "
    "counts, the total, the number of sports medalled in and the share of that total which was gold. "
    f"The <strong>medal file</strong> has one row per medal ({medal_rows} rows) with the sport, event, "
    "slot, university and athlete where the feed names one — this is the file to pivot from."
)
ui.body(
    "<strong>Sport pools</strong> counts events and medals per sport, including medals per event, which is how the "
    "taekwondo and badminton difference in section 7 of the report is measured. <strong>Matches</strong> carries the "
    f"final score and, where it exists, the penalty score for {len(matches)} fixtures."
)

tabs = st.tabs(["Medal table", "Every medal", "Sport pools", "Matches"])
with tabs[0]:
    if medal.empty:
        st.info("No medals in this selection.")
    else:
        st.dataframe(medal, hide_index=True, use_container_width=True)
with tabs[1]:
    if results.empty:
        st.info("No medals in this selection.")
    else:
        st.dataframe(results.head(200), hide_index=True, use_container_width=True)
        if len(results) > 200:
            st.caption(f"Showing the first 200 of {len(results)} rows — download the file for all of them.")
with tabs[2]:
    if pool.empty:
        st.info("No events in this selection.")
    else:
        st.dataframe(pool, hide_index=True, use_container_width=True)
with tabs[3]:
    if matches.empty:
        st.info("No matches in this selection.")
    else:
        st.dataframe(matches, hide_index=True, use_container_width=True)
    if filtered and (gender != "All genders" or kind != "All types" or medal_pick != "All medals"):
        st.caption("Matches are fixtures, so only the university filter applies to this table.")

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
if filtered:
    st.caption("These checks cover the whole Games, not the current selection.")

ui.footer(
    f"Data: <b>AlliSports Data</b> — official data partner of WAUG 2026 &nbsp;·&nbsp; prepared by <b>{AUTHORS}</b>"
)
