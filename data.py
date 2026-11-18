"""
WAUG 2026 — data page.

Everything behind the report, downloadable, plus the endpoint list so the
work can be checked or repeated. The filters sit in the page itself because
they change what the files hold: sport, category and country narrow all four
tables and all four downloads.
"""

import pandas as pd
import streamlit as st

import ui
from waug_core import (
    AUTHOR, SPORT_EMOJI,
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
code_country = dict(zip(tables["medal"]["Code"], tables["medal"]["Country"]))
name_country = dict(zip(tables["medal"]["School"], tables["medal"]["Country"]))
COUNTRIES = {"NG": "Nigeria", "GH": "Ghana"}

# ============================================================
# PAGE HEAD
# ============================================================
ui.eyebrow("WAUG 2026 &nbsp;·&nbsp; Data &nbsp;·&nbsp; AlliSports Data API")
ui.display("Everything the report is built on.")
ui.lede(
    "Four files, all rebuilt from the same feed the dashboard reads. The medal table is the official "
    "ranking; the results file is one row per medal with the school and the athlete, so any number in the "
    "report can be reproduced from it."
)
ui.byline(f"Prepared by <b>{AUTHOR}</b> &nbsp;·&nbsp; data partner: <b>AlliSports Data</b>")

ui.toc([
    ("d0", "Downloads"),
    ("d1", "What each file holds"),
    ("d2", "The endpoints"),
    ("d3", "Checks"),
])

# ============================================================
# FILTERS — part of the page, because they change what the files hold
# ============================================================
with st.container(border=True):
    ui.chart_title("Narrow the files")
    st.caption(
        "Pick a sport, one of its categories, or a country. Every table and every "
        "download below follows the choice; leave them alone for the whole Games."
    )
    f1, f2, f3, f4 = st.columns([1.5, 1.3, 1.1, 0.9], vertical_alignment="bottom")
    with f1:
        sport_pick = st.selectbox(
            "Sport", ["ALL"] + sorted(sports_map, key=lambda c: sports_map[c]),
            format_func=lambda c: "All sports" if c == "ALL"
            else f"{SPORT_EMOJI.get(c, '🏅')} {sports_map[c]}",
            key="data_sport",
        )
    with f2:
        category_source = (
            tables["results"] if sport_pick == "ALL"
            else tables["results"][tables["results"]["Sport"] == sports_map[sport_pick]]
        )
        categories = ["All categories"] + sorted(
            {str(c) for c in category_source["Event"].dropna() if str(c).strip()}, key=str.lower
        )
        category = st.selectbox("Category", categories, key=f"data_category_{sport_pick}")
    with f3:
        countries = ["All countries"] + sorted({c for c in code_country.values() if c})
        country = st.selectbox(
            "Country", countries, key="data_country",
            format_func=lambda c: COUNTRIES.get(c, c),
        )
    with f4:
        if st.button("Refresh", use_container_width=True):
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
filtered = sport_pick != "ALL" or category != "All categories" or country != "All countries"

results = tables["results"].copy()
matches = tables["matches"].copy()
pool_all = tables["pool"].copy()

if sport_pick != "ALL":
    results = results[results["Sport"] == sports_map[sport_pick]]
    matches = matches[matches["Sport"] == sport_pick]
    pool_all = pool_all[pool_all["Code"] == sport_pick]

if category != "All categories":
    results = results[results["Event"].astype(str).str.lower() == category.lower()]

# the event list defines how many events the medals are measured against
events_scope = tables["events"].copy()
if sport_pick != "ALL":
    events_scope = events_scope[events_scope["Code"] == sport_pick]
if category != "All categories":
    events_scope = events_scope[
        events_scope["Event"].astype(str).str.lower() == category.lower()
    ]

if country != "All countries":
    results = results[results["University code"].map(code_country).eq(country)]
    matches = matches[
        matches["Home"].map(name_country).eq(country)
        | matches["Away"].map(name_country).eq(country)
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
    pool = pool_all.copy()

pool["PerEvent"] = pool["PerEvent"].round(2)
pool["Share"] = pool["Share"].round(1)

live_medals = len(results)
event_total = len(events_scope)

if filtered:
    chips = []
    if sport_pick != "ALL":
        chips.append(f"{SPORT_EMOJI.get(sport_pick, '🏅')} {sports_map[sport_pick]}")
    if category != "All categories":
        chips.append(category)
    if country != "All countries":
        chips.append(COUNTRIES.get(country, country))
    pills = "".join(f'<span class="pill">{c}</span>' for c in chips)
    st.markdown(
        f'<div class="filter-bar">{pills}'
        f'<span class="filter-note">{live_medals} medal row(s) across {event_total} event(s) '
        f'in this selection</span></div>',
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        f'<div class="filter-bar"><span class="pill">Whole Games</span>'
        f'<span class="filter-note">{live_medals} medal rows across {event_total} events</span></div>',
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
        "silver, then bronze). Sport pools keep the official event count for the sport or "
        "category in scope and count only the medals that remain, so medals-per-event falls "
        "with the filter. Clear the filters for the official Games figures."
    )

# ---------- file descriptions ----------
ui.section("d1", "01", "Files", "What each file holds")
ui.body(
    f"The <strong>medal table</strong> has one row per university with the rank, the three medal "
    "counts, the total, the number of sports medalled in and the share of that total which was gold. "
    f"The <strong>medal file</strong> has one row per medal ({live_medals} rows) with the sport, event, "
    "slot, university and athlete where the feed names one — this is the file to pivot from."
)
ui.body(
    f"<strong>Sport pools</strong> counts events and medals per sport, including medals per event, which is how the "
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
    f"Data: <b>AlliSports Data</b> — official data partner of WAUG 2026 &nbsp;·&nbsp; prepared by <b>{AUTHOR}</b>"
)
