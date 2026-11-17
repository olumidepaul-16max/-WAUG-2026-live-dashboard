"""
WAUG 2026 — live dashboard page.

Per-sport fixtures, results, standings and statistics from the AlliSports
Data API. The only picture on the page is the thumbnail under the filters for
the sport you pick.
"""

import os
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from waug_core import *  # noqa: F401,F403

st.markdown("""
<style>
.block-container { padding-top: 1.6rem; padding-bottom: 3rem; max-width: 1400px; }
[data-testid="stAppViewContainer"] { background: #0A1533; }
[data-testid="stHeader"] { background: transparent; }
[data-testid="stToolbar"] { background: transparent; }

/* ================= BRAND BANNER ================= */
.brand {
    display: flex; align-items: center; gap: 20px;
    background: linear-gradient(115deg, #0A1533 0%, #14285F 46%, #2630BD 100%);
    border-radius: 16px; padding: 20px 26px; margin-bottom: 20px;
    box-shadow: 0 12px 32px rgba(0,0,0,.5);
    border-bottom: 3px solid #E8B84B;
}
.brand-text { flex: 1 1 auto; min-width: 0; }
.brand-text h1 { color:#fff; font-size:1.34rem; font-weight:800; margin:0; line-height:1.25; letter-spacing:-.3px; }
.brand-text p  { color:#E8B84B; margin:4px 0 0; font-size:.83rem; font-weight:600; }
.brand-text small { color:#8FA3D4; font-size:.73rem; }

/* ================= SPORT HEADER ================= */
.sport-head { display:flex; align-items:center; gap:16px; margin: 4px 0 12px; }
.sport-emoji { font-size:2.2rem; line-height:1.1; }
.sport-head h2 { color:#fff; font-size:1.8rem; font-weight:800; margin:0; letter-spacing:-.4px; }
.sport-head .rule { height:3px; width:64px; background:#E8B84B; border-radius:2px; margin-top:7px; }
.sport-head .meta { color:#8FA3D4; font-size:.84rem; font-weight:600; margin-left:auto; text-align:right; }

/* ================= CARDS ================= */
.card {
    background: rgba(255,255,255,.035);
    border: 1px solid rgba(232,184,75,.16);
    border-radius: 14px; padding: 20px 22px; margin-bottom: 16px;
    box-shadow: 0 2px 14px rgba(0,0,0,.28);
}
.card-title {
    font-size:.75rem; font-weight:800; letter-spacing:1.7px; text-transform:uppercase;
    color:#E8B84B; margin-bottom:14px; display:flex; align-items:center; gap:9px;
}
.card-title::before { content:""; width:9px; height:9px; border-radius:2px; background:#E8B84B; flex:0 0 auto; }
.card-title.navy::before   { background:#5B8DEF; }
.card-title.crimson::before { background:#F0616D; }
.card-title.teal::before    { background:#4FD1C5; }

/* ================= METRICS ================= */
[data-testid="stMetric"] {
    background: rgba(255,255,255,.04);
    border: 1px solid rgba(232,184,75,.18);
    border-left: 3px solid #E8B84B;
    border-radius: 12px; padding: 15px 18px;
    box-shadow: 0 2px 12px rgba(0,0,0,.28);
}
[data-testid="stMetricValue"] { color:#fff !important; font-weight:800 !important; font-size:1.85rem !important; }
[data-testid="stMetricLabel"] { color:#8FA3D4 !important; font-weight:700 !important; font-size:.78rem !important;
                                text-transform:uppercase; letter-spacing:.7px; }
[data-testid="stMetricDelta"] { color:#E8B84B !important; font-weight:700 !important; }

/* ================= TABS ================= */
.stTabs [data-baseweb="tab-list"] { gap:6px; border-bottom:1px solid rgba(232,184,75,.16); padding-bottom:0; }
.stTabs [data-baseweb="tab"] {
    background: rgba(255,255,255,.045); color:#C3CFF0; border-radius:10px 10px 0 0; padding:10px 20px;
    font-weight:700; font-size:.91rem; border:1px solid rgba(255,255,255,.08); border-bottom:none;
}
.stTabs [data-baseweb="tab"]:hover { background: rgba(38,48,189,.22); color:#fff; }
.stTabs [data-baseweb="tab"][aria-selected="true"] {
    background:#14285F !important; color:#fff !important;
    border-color:rgba(232,184,75,.45); box-shadow: inset 0 -3px 0 #E8B84B;
}

/* ================= TABLES ================= */
[data-testid="stDataFrame"] { border-radius:12px; border:1px solid rgba(232,184,75,.16); overflow:hidden; }
[data-testid="stDataFrame"] thead th { background:#14285F !important; color:#E8B84B !important; }

/* ================= SIDEBAR ================= */
[data-testid="stSidebar"] { background:#0D1940; border-right:1px solid rgba(232,184,75,.16); }
[data-testid="stSidebar"] .block-container { padding-top:1.2rem; }
[data-testid="stSidebar"] * { color:#E2E8F7; }
.side-cap { color:#E8B84B; font-size:.72rem; font-weight:800; text-transform:uppercase; letter-spacing:1.3px; margin:16px 0 6px; }

/* ================= FILTERS ================= */
.filters-h { color:#fff; font-size:1.36rem; font-weight:800; letter-spacing:-.3px; margin:0 0 16px; }
.filters-note { color:#9DB0DA; font-size:.79rem; line-height:1.55; margin:10px 0 14px; }
.side-sport { text-align:center; font-weight:700; color:#E9EEFB; font-size:.9rem; margin:-4px 0 12px; }
[data-testid="stSidebar"] .stSelectbox label p {
    color:#E9EEFB !important; font-size:.87rem !important; font-weight:600 !important;
}
[data-testid="stSidebar"] [data-baseweb="select"] > div {
    background:#0F1D42 !important; border:1px solid rgba(255,255,255,.20) !important;
    border-radius:10px !important; min-height:46px;
}
[data-testid="stSidebar"] [data-baseweb="select"] > div:hover { border-color:rgba(232,184,75,.6) !important; }
[data-testid="stSidebar"] [data-baseweb="select"] span { font-size:.88rem !important; }
[data-testid="stSidebar"] .stButton > button {
    background:#E9EEFB !important; color:#0A1533 !important; border:1px solid #E9EEFB !important;
    font-weight:700 !important; font-size:.86rem !important; border-radius:10px !important;
    padding:9px 14px !important;
}
[data-testid="stSidebar"] .stButton > button:hover { background:#fff !important; border-color:#fff !important; }

/* ================= MISC ================= */
.live-pill {
    display:inline-flex; align-items:center; gap:8px; background:rgba(206,17,38,.16); color:#FF8A94;
    border:1px solid rgba(206,17,38,.45); border-radius:999px; padding:5px 14px; font-weight:700; font-size:.82rem;
}
.live-dot { width:9px; height:9px; border-radius:50%; background:#F0616D; animation:pulse 1.3s infinite; }
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.25} }
.foot { text-align:center; color:#7C8DBB; font-size:.82rem; padding:20px 0 4px;
        border-top:1px solid rgba(232,184,75,.16); margin-top:26px; }
.foot b { color:#E8B84B; }
hr.rule-line { border:none; border-top:1px solid rgba(232,184,75,.14); margin:18px 0; }
</style>
""", unsafe_allow_html=True)


def badge_col(label, options=None):
    if hasattr(st.column_config, "BadgeColumn"):
        return st.column_config.BadgeColumn(label, options=options, format="%s")
    return st.column_config.TextColumn(label)


def style_chart(fig, title=None, height=380, y_title=None, legend=True):
    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font_color="#B9C6E8", title_font_color="#E8B84B", title_font_size=15,
        margin=dict(t=62 if title else 30, b=40, l=50, r=20), height=height,
        hoverlabel=dict(bgcolor="#14285F", font_color="#FFFFFF", bordercolor="#E8B84B"),
        legend=dict(bgcolor="rgba(0,0,0,0)", font_color="#B9C6E8",
                    orientation="h", yanchor="bottom", y=1.02),
        xaxis=dict(gridcolor="rgba(255,255,255,.07)", zerolinecolor="rgba(255,255,255,.07)",
                   linecolor="rgba(255,255,255,.14)", tickfont_color="#B9C6E8"),
        yaxis=dict(gridcolor="rgba(255,255,255,.07)", zerolinecolor="rgba(255,255,255,.07)",
                   linecolor="rgba(255,255,255,.14)", tickfont_color="#B9C6E8", title=y_title),
        bargap=0.35, showlegend=legend,
    )
    if title:
        fig.update_layout(title=dict(text=title, x=0.5, xanchor="center"))
    return fig


# ============================================================
# LOAD DATA
# ============================================================
with st.spinner("Connecting to the AlliSports feed…"):
    CORE = load_core()

if CORE.get("error"):
    st.error(f"⚠️ Could not reach the AlliSports feed: {CORE['error']}")
    st.caption("The feed key is read from Streamlit secrets (ALLISPORTS_KEY).")
    st.stop()

SPORTS = CORE["sports"]
MATCHES = CORE["matches"]
RESULTS = CORE["results"]
MEDALS = CORE["medal"]

sports_map = dict(zip(SPORTS["code"], SPORTS["name"])) if not SPORTS.empty else {}
sports_events = dict(zip(SPORTS["code"], SPORTS["events"])) if not SPORTS.empty else {}
code_list = list(SPORTS["code"]) if not SPORTS.empty else []

live_total = int((MATCHES["raw_status"] == "live").sum()) if not MATCHES.empty else 0
finished_total = int((MATCHES["raw_status"] == "finished").sum()) if not MATCHES.empty else 0

# ============================================================
# SIDEBAR — filters
# ============================================================
UNIS = CORE["universities"]
uni_country = dict(zip(UNIS["University"], UNIS["Country"])) if not UNIS.empty else {}
code_country = dict(zip(UNIS["Code"], UNIS["Country"])) if not UNIS.empty else {}
COUNTRY_LABEL = {"NG": "Nigeria", "GH": "Ghana"}
country_codes = sorted({c for c in code_country.values() if c})


def sport_label(code: str) -> str:
    return f"{SPORT_EMOJI.get(code, '🏅')}  {sports_map.get(code, code)}"


def _sync_sport_query():
    try:
        st.query_params["sport"] = st.session_state.get("sport_pick", "")
    except Exception:
        pass


st.sidebar.markdown('<div class="filters-h">Filters</div>', unsafe_allow_html=True)

qp = st.query_params.get("sport", "")
if qp in code_list:
    st.session_state["sport_pick"] = qp

selected_code = st.sidebar.selectbox(
    "Sport", code_list, format_func=sport_label,
    key="sport_pick", on_change=_sync_sport_query,
)
if st.query_params.get("sport", "") != selected_code:
    try:
        st.query_params["sport"] = selected_code
    except Exception:
        pass

sport_event_rows = get_sport_events(selected_code)
cat_map = {}
for _ev in sport_event_rows:
    _cat = (_ev.get("category") or "").strip()
    if _cat:
        cat_map.setdefault(_cat.lower(), _cat)
categories = ["All categories"] + sorted(cat_map.values(), key=str.lower)
category = st.sidebar.selectbox("Category", categories)

countries = ["All countries"] + country_codes
country = st.sidebar.selectbox(
    "Country", countries, format_func=lambda c: COUNTRY_LABEL.get(c, c),
)

thumb = asset("thumb", f"{selected_code}.jpg")
if thumb:
    st.sidebar.image(thumb, use_container_width=True)
st.sidebar.markdown(
    f'<div class="side-sport">{SPORT_EMOJI.get(selected_code, "🏅")} '
    f'{sports_map.get(selected_code, selected_code)}</div>',
    unsafe_allow_html=True,
)

st.sidebar.markdown(
    '<div class="filters-note">Country comes from the AlliSports Data feed.</div>',
    unsafe_allow_html=True,
)

if st.sidebar.button("Refresh data", use_container_width=True):
    load_core.clear()
    api_get.clear()
    get_competition.clear()
    get_analytics.clear()
    get_sport_events.clear()
    st.rerun()

st.sidebar.markdown('<hr class="rule-line">', unsafe_allow_html=True)
st.sidebar.markdown('<div class="side-cap">Feed status</div>', unsafe_allow_html=True)
c1, c2 = st.sidebar.columns(2)
c1.metric("Live", live_total)
c2.metric("Played", finished_total)

st.sidebar.markdown('<hr class="rule-line">', unsafe_allow_html=True)
side_medals = MEDALS
if country != "All countries" and not MEDALS.empty:
    side_medals = MEDALS[MEDALS["Code"].map(lambda c: code_country.get(c) == country)]
with st.sidebar.expander("🥇 Medal table", expanded=False):
    st.dataframe(
        side_medals[["Rank", "University", "Gold", "Silver", "Bronze", "Total"]],
        use_container_width=True, hide_index=True,
        column_config={
            "Rank": st.column_config.NumberColumn("#", format="%d"),
            "Gold": st.column_config.NumberColumn("🥇", format="%d"),
            "Silver": st.column_config.NumberColumn("🥈", format="%d"),
            "Bronze": st.column_config.NumberColumn("🥉", format="%d"),
        },
    )

st.sidebar.markdown('<hr class="rule-line">', unsafe_allow_html=True)
st.sidebar.caption("Data: **AlliSports Data**")

# ============================================================
# BRAND BANNER
# ============================================================
gen = CORE.get("generatedAt")
gen_txt = ""
if gen:
    try:
        gen_txt = datetime.fromisoformat(gen.replace("Z", "+00:00")).strftime("%d %b %Y · %H:%M UTC")
    except Exception:
        gen_txt = gen
prov = " · includes provisional results" if CORE.get("includesProvisional") else ""

st.markdown(f"""
<div class="brand">
  <div class="brand-text">
    <h1>West African Universities Games 2026</h1>
    <p>Obafemi Awolowo University, Ile-Ife &nbsp;·&nbsp; Official live results &amp; standings</p>
    <small>Feed updated {gen_txt}{prov}</small>
  </div>
</div>
""", unsafe_allow_html=True)

# ============================================================
# SPORT HEADER
# ============================================================
sport_name = sports_map.get(selected_code, selected_code)
ev_count = sports_events.get(selected_code, 0)
sp_matches = MATCHES[MATCHES["Sport"] == selected_code].copy() if not MATCHES.empty else MATCHES
sp_matches_all = sp_matches.copy()
sp_results = RESULTS[RESULTS["Sport"] == selected_code].copy() if not RESULTS.empty else RESULTS

# category narrows the results and the schedule count; fixtures stay sport-wide
if category != "All categories":
    ev_count = sum(
        1 for e in sport_event_rows
        if (e.get("category") or "").strip().lower() == category.lower()
    )
    if not sp_results.empty:
        row_cat = sp_results["Event"].str.split(" - ", n=1).str[-1].str.lower()
        sp_results = sp_results[row_cat == category.lower()].copy()


def _in_country(name) -> bool:
    return country == "All countries" or uni_country.get(name) == country


if country != "All countries":
    if not sp_matches.empty:
        sp_matches = sp_matches[
            sp_matches["Home Uni"].map(_in_country) | sp_matches["Away Uni"].map(_in_country)
        ].copy()
    if not sp_results.empty:
        sp_results = sp_results[
            sp_results["Gold Uni"].map(_in_country)
            | sp_results["Silver Uni"].map(_in_country)
            | sp_results["Bronze Uni"].map(_in_country)
        ].copy()

filter_bits = []
if category != "All categories":
    filter_bits.append(category)
if country != "All countries":
    filter_bits.append(f"{COUNTRY_LABEL.get(country, country)} only")
filter_txt = "".join(f" &nbsp;·&nbsp; {b}" for b in filter_bits)

st.markdown(f"""
<div class="sport-head">
  <span class="sport-emoji">{SPORT_EMOJI.get(selected_code, '🏅')}</span>
  <div>
    <h2>{sport_name}</h2>
    <div class="rule"></div>
  </div>
  <div class="meta">{ev_count} event(s) &nbsp;·&nbsp; {len(sp_matches)} match(es) &nbsp;·&nbsp; {len(sp_results)} result(s){filter_txt}</div>
</div>
""", unsafe_allow_html=True)

tabs = st.tabs(["🔴 Live & Fixtures", "🏅 Results & Medals", "📊 Standings", "📈 Statistics"])

# ---------------- TAB 1: LIVE & FIXTURES ----------------
with tabs[0]:
    if category != "All categories":
        st.caption(
            "Fixtures are listed for the whole sport; the category filter applies to results and medals."
        )
    if sp_matches.empty:
        with st.container(border=True):
            st.markdown('<div class="card-title">No fixtures</div>', unsafe_allow_html=True)
            if country != "All countries":
                st.info(f"No matches recorded for {sport_name} involving "
                        f"{COUNTRY_LABEL.get(country, country)} universities.")
            else:
                st.info(f"No matches recorded for {sport_name} yet.")
    else:
        live_df = sp_matches[sp_matches["raw_status"] == "live"]
        if not live_df.empty:
            with st.container(border=True):
                st.markdown(
                    '<div class="card-title crimson">Live now</div>'
                    '<span class="live-pill"><span class="live-dot"></span>In play</span>',
                    unsafe_allow_html=True,
                )
                st.dataframe(live_df[["Event", "Home", "Away", "Score", "Phase", "Venue"]],
                             use_container_width=True, hide_index=True)

        c1, c2 = st.columns([3, 2])
        with c1:
            with st.container(border=True):
                st.markdown('<div class="card-title">All fixtures &amp; results</div>', unsafe_allow_html=True)
                st.dataframe(
                    sp_matches[["Event", "Home", "Away", "Score", "Phase", "Status", "Venue"]],
                    use_container_width=True, hide_index=True,
                    column_config={"Status": badge_col("Status")})
        with c2:
            with st.container(border=True):
                st.markdown('<div class="card-title navy">Match breakdown</div>', unsafe_allow_html=True)
                counts = (sp_matches.groupby("Status").size().reset_index(name="Matches")
                          .sort_values("Matches", ascending=False))
                fig = px.bar(counts, x="Status", y="Matches", color_discrete_sequence=[GOLD])
                st.plotly_chart(style_chart(fig, "Matches by status", height=330, y_title="Matches"),
                                use_container_width=True)

        with st.container(border=True):
            st.markdown('<div class="card-title teal">Match story</div>', unsafe_allow_html=True)
            finished = sp_matches[sp_matches["raw_status"] == "finished"]
            if finished.empty:
                st.caption("No finished matches yet for this sport.")
            else:
                opts = finished["Event"] + " — " + finished["Home"] + " v " + finished["Away"]
                pick = st.selectbox("Pick a match", list(range(len(finished))),
                                    format_func=lambda i: opts.iloc[i], label_visibility="collapsed")
                chosen = finished.iloc[pick]
                analytics = get_analytics(chosen["id"])
                if not analytics or not analytics.get("available"):
                    st.info("No narrative available for this match.")
                else:
                    st.markdown(f"### {analytics.get('headline','')}")
                    comps = analytics.get("comparisons") or []
                    if comps:
                        cdf = pd.DataFrame([
                            {"Metric": c["label"], "Home": c["home"], "Away": c["away"],
                             "Unit": c.get("unit", "")} for c in comps])
                        st.dataframe(cdf, use_container_width=True, hide_index=True)
                    insights = analytics.get("insights") or []
                    if insights:
                        st.markdown("**Key moments**")
                        for ins in insights:
                            st.markdown(f"- {ins['text']}")
                    for note in analytics.get("notes") or []:
                        st.caption(note)

# ---------------- TAB 2: RESULTS & MEDALS ----------------
with tabs[1]:
    if sp_results.empty:
        with st.container(border=True):
            st.markdown('<div class="card-title">No results</div>', unsafe_allow_html=True)
            if filter_bits:
                st.info(f"No results for {sport_name} match these filters.")
            else:
                st.info(f"No results recorded for {sport_name} yet.")
    else:
        c1, c2 = st.columns(2)
        with c1:
            with st.container(border=True):
                st.markdown('<div class="card-title">Podium</div>', unsafe_allow_html=True)
                st.dataframe(
                    sp_results[["Event", "Gender", "Gold", "Gold Uni", "Silver",
                                "Silver Uni", "Bronze", "Bronze Uni"]],
                    use_container_width=True, hide_index=True)
        with c2:
            with st.container(border=True):
                st.markdown('<div class="card-title navy">Event status</div>', unsafe_allow_html=True)
                counts = (sp_results.groupby("Status").size().reset_index(name="Events")
                          .sort_values("Events", ascending=False))
                fig = px.bar(counts, x="Status", y="Events", color_discrete_sequence=[NAVY2])
                st.plotly_chart(style_chart(fig, "Events by status", height=330, y_title="Events"),
                                use_container_width=True)

        with st.container(border=True):
            st.markdown('<div class="card-title teal">Schedule</div>', unsafe_allow_html=True)
            st.dataframe(
                sp_results[["Event", "Gender", "Kind", "Starts (UTC)", "Status"]],
                use_container_width=True, hide_index=True,
                column_config={"Status": badge_col("Status")})

# ---------------- TAB 3: STANDINGS ----------------
with tabs[2]:
    comp = get_competition(selected_code)
    if comp:
        for group in comp.get("groups") or []:
            with st.container(border=True):
                st.markdown(
                    f'<div class="card-title">{group.get("name", "Group")} '
                    f'· advance {group.get("advance", "—")}</div>', unsafe_allow_html=True)
                grows = group.get("rows") or []
                if country != "All countries":
                    grows = [r for r in grows if uni_country.get(r["team"]["name"]) == country]
                if grows:
                    gdf = pd.DataFrame([
                        {"Pos": r["position"], "Team": r["team"]["name"],
                         "P": r["played"], "W": r["won"], "D": r["drawn"], "L": r["lost"],
                         "GF": r["goalsFor"], "GA": r["goalsAgainst"],
                         "GD": r["goalDifference"], "Pts": r["points"],
                         "Qualifies": "✅ Yes" if r.get("qualifies") else "—"}
                        for r in grows])
                    st.dataframe(
                        gdf, use_container_width=True, hide_index=True,
                        column_config={
                            "Pos": st.column_config.NumberColumn("Pos", format="%d"),
                            "Pts": st.column_config.ProgressColumn("Points", min_value=0, max_value=9, format="%d"),
                            "GF": st.column_config.NumberColumn("For", format="%d"),
                            "GA": st.column_config.NumberColumn("Against", format="%d"),
                            "GD": st.column_config.NumberColumn("GD", format="%+d")})
                else:
                    st.caption("No teams from this country in the group.")
        ko = comp.get("knockout")
        if ko:
            with st.container(border=True):
                st.markdown('<div class="card-title">Knockout rounds</div>', unsafe_allow_html=True)
                st.json(ko, expanded=False)
    else:
        events = get_sport_events(selected_code)
        is_tournament = any(str(e.get("category", "")).lower() == "tournament" for e in events)
        derived = derive_standings(sp_matches_all) if is_tournament else pd.DataFrame()
        if country != "All countries" and not derived.empty:
            derived = derived[derived["Team"].map(lambda t: uni_country.get(t) == country)]
        if not derived.empty:
            with st.container(border=True):
                st.markdown('<div class="card-title">League table</div>', unsafe_allow_html=True)
                st.caption("Calculated from the finished matches — 3 points for a win, 1 for a draw.")
                st.dataframe(
                    derived, use_container_width=True, hide_index=True,
                    column_config={
                        "Pos": st.column_config.NumberColumn("Pos", format="%d"),
                        "Pts": st.column_config.ProgressColumn("Points", min_value=0, max_value=12, format="%d"),
                        "GF": st.column_config.NumberColumn("For", format="%d"),
                        "GA": st.column_config.NumberColumn("Against", format="%d"),
                        "GD": st.column_config.NumberColumn("GD", format="%+d")})
        else:
            with st.container(border=True):
                st.markdown('<div class="card-title">Standings</div>', unsafe_allow_html=True)
                st.info(f"No group table or knockout bracket is published for {sport_name}.")

    with st.container(border=True):
        st.markdown('<div class="card-title crimson">Medals in this sport</div>', unsafe_allow_html=True)
        if sp_results.empty:
            st.caption("No medals awarded yet in this sport.")
        else:
            per_uni = {}
            for _, r in sp_results.iterrows():
                for uni, slot in ((r["Gold Uni"], "Gold"), (r["Silver Uni"], "Silver"),
                                  (r["Bronze Uni"], "Bronze")):
                    if uni and uni != "—":
                        per_uni.setdefault(uni, {"University": uni, "Gold": 0,
                                                  "Silver": 0, "Bronze": 0})[slot] += 1
            if per_uni:
                udf = pd.DataFrame(list(per_uni.values())).sort_values("Gold", ascending=False)
                st.dataframe(udf, use_container_width=True, hide_index=True)
                fig = px.bar(udf.head(10), x="University", y=["Gold", "Silver", "Bronze"],
                             barmode="stack",
                             color_discrete_map={"Gold": GOLD, "Silver": "#9CA3AF", "Bronze": "#CD7F32"})
                st.plotly_chart(style_chart(fig, f"{sport_name} medals by university",
                                            y_title="Medals"), use_container_width=True)
            else:
                st.caption("No medals awarded yet in this sport.")

# ---------------- TAB 4: STATISTICS ----------------
with tabs[3]:
    if sp_matches.empty:
        with st.container(border=True):
            st.markdown('<div class="card-title">Statistics</div>', unsafe_allow_html=True)
            st.info("No match statistics available yet.")
    else:
        c1, c2 = st.columns(2)
        with c1:
            with st.container(border=True):
                st.markdown('<div class="card-title">Goals by team</div>', unsafe_allow_html=True)
                goals = []
                for _, r in sp_matches.iterrows():
                    if r["Home Uni"]:
                        goals.append({"Team": r["Home Uni"], "Goals": r["Home Goals"]})
                    if r["Away Uni"]:
                        goals.append({"Team": r["Away Uni"], "Goals": r["Away Goals"]})
                if goals:
                    gdf = pd.DataFrame(goals).groupby("Team", as_index=False)["Goals"].sum()
                    gdf = gdf.sort_values("Goals", ascending=False).head(12)
                    fig = px.bar(gdf, x="Team", y="Goals", color_discrete_sequence=[CRIMSON])
                    st.plotly_chart(style_chart(fig, "Goals scored", y_title="Goals"),
                                    use_container_width=True)
                else:
                    st.caption("No goals recorded yet.")

        with c2:
            with st.container(border=True):
                st.markdown('<div class="card-title navy">Biggest margins</div>', unsafe_allow_html=True)
                fin = sp_matches[sp_matches["raw_status"] == "finished"].copy()
                if fin.empty:
                    st.caption("No finished matches yet.")
                else:
                    fin["Margin"] = (fin["Home Goals"] - fin["Away Goals"]).abs()
                    top = fin.nlargest(8, "Margin")[["Home", "Away", "Score", "Margin"]]
                    st.dataframe(top, use_container_width=True, hide_index=True)
                    fig = px.bar(top, x="Margin", y="Home", orientation="h",
                                 color_discrete_sequence=[PURPLE])
                    fig.update_layout(yaxis=dict(showticklabels=False))
                    st.plotly_chart(style_chart(fig, "Largest winning margins", y_title="",
                                                legend=False), use_container_width=True)

        with st.container(border=True):
            st.markdown('<div class="card-title teal">Games across all sports</div>', unsafe_allow_html=True)
            base = MATCHES
            if country != "All countries" and not MATCHES.empty:
                base = MATCHES[
                    MATCHES["Home Uni"].map(_in_country) | MATCHES["Away Uni"].map(_in_country)
                ]
            if not base.empty:
                per_sport = (base[base["raw_status"] == "finished"]
                             .groupby("Sport").size().reset_index(name="Matches"))
                per_sport["Name"] = per_sport["Sport"].map(sports_map)
                fig = px.bar(per_sport.sort_values("Matches", ascending=False),
                             x="Name", y="Matches", color_discrete_sequence=[TEAL])
                fig.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(style_chart(fig, "Completed matches by sport", y_title="Matches"),
                                use_container_width=True)

# ============================================================
# FOOTER
# ============================================================
st.markdown(
    '<div class="foot">WAUG 2026 Live Analytics · Obafemi Awolowo University, Ile-Ife · '
    'Data: <b>AlliSports Data</b></div>',
    unsafe_allow_html=True,
)
