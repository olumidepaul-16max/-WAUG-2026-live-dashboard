"""
WAUG 2026 Live Sports Dashboard  —  Obafemi Awolowo University, Ile-Ife
Powered by the AlliSports Data API (data.allimediahub.com)

The API key lives on the server (Streamlit Cloud / your machine) and is sent in the
`x-api-key` header. It is never exposed to the browser.
"""

import os
from datetime import datetime, timezone

import pandas as pd
import plotly.express as px
import requests
import streamlit as st

# ============================================================
# CONFIG
# ============================================================
API_BASE = "https://data.allimediahub.com/api"
SERIES = "waug"
EDITION = "2026"

# Fallback key: set via Streamlit Cloud secrets (ALLISPORTS_KEY), an env var, or here.
FALLBACK_KEY = "asd_4zqyjoayTzsKxPi1YpjND3bstQ3v-44J"

SPORT_EMOJI = {
    "ATH": "🏃", "BDM": "🏸", "BKB": "🏀", "BOX": "🥊", "CHS": "♟️", "ESP": "🎮",
    "FBL": "⚽", "HBL": "🤾", "HKY": "🏑", "JUD": "🥋", "RUG": "🏉", "SCR": "🔤",
    "SQU": "🎾", "SWM": "🏊", "TEN": "🎾", "TKW": "🥋", "TTE": "🏓", "VVO": "🏐",
    "WLF": "🏋️", "WRE": "🤼",
}

STATUS_STYLE = {
    "finished": "Completed",
    "live": "🔴 LIVE",
    "scheduled": "Scheduled",
    "postponed": "Postponed",
    "cancelled": "Cancelled",
    "abandoned": "Abandoned",
}


# ============================================================
# API KEY RESOLUTION
# ============================================================
def get_api_key() -> str:
    """Resolve the API key from Streamlit secrets, env vars, or the local fallback."""
    try:
        return st.secrets["ALLISPORTS_KEY"]
    except Exception:
        pass
    return os.environ.get("ALLISPORTS_KEY", FALLBACK_KEY)


# ============================================================
# HTTP LAYER
# ============================================================
@st.cache_data(ttl=45, show_spinner=False)
def api_get(path: str):
    """GET a feed endpoint from the server. Returns dict, or {'__error__': ...}."""
    key = get_api_key()
    url = f"{API_BASE}/{SERIES}/{EDITION}{path}"
    try:
        resp = requests.get(url, headers={"x-api-key": key}, timeout=25)
        if resp.status_code == 429:
            retry = resp.headers.get("Retry-After", "?")
            return {"__error__": f"Rate limit reached (60/min). Retry in {retry}s."}
        if resp.status_code == 401:
            return {"__error__": "Invalid API key. Check ALLISPORTS_KEY in Streamlit secrets."}
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.Timeout:
        return {"__error__": "The feed timed out. Try refreshing."}
    except Exception as exc:  # noqa: BLE001
        return {"__error__": str(exc)}


@st.cache_data(ttl=45, show_spinner=False)
def api_get_path(full_path: str):
    """GET an endpoint relative to the edition (e.g. /events/{id}/competition)."""
    key = get_api_key()
    url = f"{API_BASE}/{SERIES}/{EDITION}{full_path}"
    try:
        resp = requests.get(url, headers={"x-api-key": key}, timeout=25)
        if resp.status_code == 429:
            return {"__error__": "Rate limit reached (60/min). Please wait a moment."}
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:  # noqa: BLE001
        return {"__error__": str(exc)}


# ============================================================
# DATA SHAPING
# ============================================================
@st.cache_data(ttl=45, show_spinner=False)
def load_core():
    """Fetch the four headline feeds and flatten them into DataFrames."""
    sports_raw = api_get("/sports")
    if "__error__" in sports_raw:
        return {"error": sports_raw["__error__"]}

    medal_raw = api_get("/medal-table")
    results_raw = api_get("/results")
    matches_raw = api_get("/matches")
    unis_raw = api_get("/universities")

    # --- sports ---
    sports_df = pd.DataFrame(sports_raw.get("data", []))
    if not sports_df.empty:
        sports_df["emoji"] = sports_df["code"].map(SPORT_EMOJI).fillna("🏅")

    # --- medal table ---
    rows = (medal_raw.get("data") or {}).get("rows", []) if "__error__" not in medal_raw else []
    medal_df = pd.DataFrame([
        {
            "Rank": r["rank"],
            "University": r["university"]["name"],
            "Code": r["university"]["code"],
            "Gold": r["medals"]["gold"],
            "Silver": r["medals"]["silver"],
            "Bronze": r["medals"]["bronze"],
            "Total": r["medals"]["total"],
            "Provisional": r.get("provisionalMedals", 0),
        }
        for r in rows
    ])

    # --- matches ---
    mrows = []
    for m in (matches_raw.get("data") or {}).get("matches", []):
        sc = m.get("score") or {}
        pen = m.get("penalties")
        score_txt = f"{sc.get('home', 0)} - {sc.get('away', 0)}"
        if pen:
            score_txt += f" ({pen.get('home')}-{pen.get('away')} pen)"
        mrows.append({
            "id": m["id"],
            "eventId": m.get("eventId"),
            "Sport": m.get("sport"),
            "Event": m.get("event"),
            "Phase": m.get("phase"),
            "Starts (UTC)": m.get("startsAt"),
            "Venue": m.get("venue"),
            "Home": (m.get("home") or {}).get("name"),
            "Home Uni": (m.get("home") or {}).get("university"),
            "Away": (m.get("away") or {}).get("name"),
            "Away Uni": (m.get("away") or {}).get("university"),
            "Score": score_txt,
            "Home Goals": sc.get("home", 0) or 0,
            "Away Goals": sc.get("away", 0) or 0,
            "Status": STATUS_STYLE.get(m.get("status"), (m.get("status") or "").title()),
            "raw_status": m.get("status"),
            "Official": bool(m.get("official")),
        })
    matches_df = pd.DataFrame(mrows)

    # --- results / medal winners ---
    rrows = []
    for r in (results_raw.get("data") or []):
        result = r.get("result") or {}
        medals = result.get("medals") or []
        rrows.append({
            "id": r["id"],
            "Sport": r["sport"]["code"],
            "Event": f"{r['sport']['name']} - {r.get('category')}",
            "Gender": (r.get("gender") or "").title(),
            "Kind": (r.get("kind") or "").title(),
            "Starts (UTC)": r.get("startsAt"),
            "Status": (result.get("status") or r.get("status") or "scheduled").title(),
            "Gold": next((m.get("athleteName") or m["university"]["name"]
                          for m in medals if m["slot"].startswith("gold")), "—"),
            "Gold Uni": next((m["university"]["name"]
                              for m in medals if m["slot"].startswith("gold")), "—"),
            "Silver": next((m.get("athleteName") or m["university"]["name"]
                            for m in medals if m["slot"].startswith("silver")), "—"),
            "Silver Uni": next((m["university"]["name"]
                                for m in medals if m["slot"].startswith("silver")), "—"),
            "Bronze": next((m.get("athleteName") or m["university"]["name"]
                            for m in medals if m["slot"].startswith("bronze")), "—"),
            "Bronze Uni": next((m["university"]["name"]
                                for m in medals if m["slot"].startswith("bronze")), "—"),
            "n_medals": len(medals),
        })
    results_df = pd.DataFrame(rrows)

    # --- universities ---
    uitems = unis_raw.get("data") if isinstance(unis_raw.get("data"), list) else \
        (unis_raw.get("data") or {}).get("universities", [])
    unis_df = pd.DataFrame([
        {
            "Code": u["code"],
            "University": u["name"],
            "Country": u.get("country"),
            "Gold": u.get("medals", {}).get("gold", 0),
            "Silver": u.get("medals", {}).get("silver", 0),
            "Bronze": u.get("medals", {}).get("bronze", 0),
            "Total": u.get("medals", {}).get("total", 0),
        }
        for u in uitems
    ])

    return {
        "error": None,
        "generatedAt": sports_raw.get("generatedAt"),
        "includesProvisional": sports_raw.get("includesProvisional"),
        "sports": sports_df,
        "medal": medal_df,
        "matches": matches_df,
        "results": results_df,
        "universities": unis_df,
        "medal_totals": (medal_raw.get("data") or {}).get("totals", {}),
        "medal_status": (medal_raw.get("data") or {}).get("status", ""),
    }


@st.cache_data(ttl=90, show_spinner=False)
def get_competition(sport_code: str):
    """Group tables + knockout rounds for a tournament event of the given sport."""
    ev = api_get("/events")
    if "__error__" in ev:
        return None
    events = ev.get("data", [])
    cands = [
        e for e in events
        if e["sport"]["code"] == sport_code and e.get("kind") == "team"
    ]
    if not cands:
        return None
    for e in cands:
        resp = api_get_path(f"/events/{e['id']}/competition")
        if "__error__" in resp:
            continue
        data = resp.get("data") or {}
        if data.get("groups") or data.get("knockout"):
            return data
    return None


@st.cache_data(ttl=90, show_spinner=False)
def get_sport_events(sport_code: str):
    """All events of a sport (used to tell team tournaments from individual events)."""
    ev = api_get("/events")
    if "__error__" in ev:
        return []
    return [e for e in ev.get("data", []) if e["sport"]["code"] == sport_code]


def derive_standings(matches_df: pd.DataFrame) -> pd.DataFrame:
    """Build a league table from finished matches when the feed has no published groups."""
    if matches_df is None or matches_df.empty:
        return pd.DataFrame()

    table: dict = {}

    def slot(name):
        if name not in table:
            table[name] = {"Team": name, "P": 0, "W": 0, "D": 0, "L": 0, "GF": 0, "GA": 0, "Pts": 0}
        return table[name]

    for _, m in matches_df.iterrows():
        if m.get("raw_status") != "finished":
            continue
        home = m.get("Home Uni") if m.get("Home Uni") == m.get("Home Uni") else m.get("Home")
        away = m.get("Away Uni") if m.get("Away Uni") == m.get("Away Uni") else m.get("Away")
        if not home or not away or str(home) == "nan" or str(away) == "nan":
            continue
        hg, ag = int(m.get("Home Goals") or 0), int(m.get("Away Goals") or 0)
        h, a = slot(home), slot(away)
        for row, gf, ga in ((h, hg, ag), (a, ag, hg)):
            row["P"] += 1
            row["GF"] += gf
            row["GA"] += ga
            if gf > ga:
                row["W"] += 1
                row["Pts"] += 3
            elif gf == ga:
                row["D"] += 1
                row["Pts"] += 1
            else:
                row["L"] += 1

    if not table:
        return pd.DataFrame()

    df = pd.DataFrame(list(table.values()))
    df["GD"] = df["GF"] - df["GA"]
    df = df.sort_values(["Pts", "GD", "GF"], ascending=False).reset_index(drop=True)
    df.insert(0, "Pos", range(1, len(df) + 1))
    return df


@st.cache_data(ttl=90, show_spinner=False)
def get_analytics(match_id: str):
    """Narrative analytics for one match."""
    resp = api_get_path(f"/matches/{match_id}/analytics")
    if "__error__" in resp:
        return None
    return resp.get("data")


# ============================================================
# PAGE SETUP + THEME
# ============================================================
st.set_page_config(
    page_title="WAUG 2026 Live Dashboard",
    page_icon="🏆",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
.hero {
    background: linear-gradient(135deg, #7A0016 0%, #50000E 55%, #0B1220 100%);
    border-left: 6px solid #FACC15;
    border-radius: 14px;
    padding: 28px 36px;
    margin-bottom: 24px;
    box-shadow: 0 8px 24px rgba(0,0,0,.35);
}
.hero-badge {
    display: inline-block; background: #FACC15; color: #0B1220;
    font-weight: 800; font-size: .72rem; letter-spacing: 2px; text-transform: uppercase;
    padding: 5px 14px; border-radius: 999px; margin-bottom: 12px;
}
.hero h1 { color:#FFFFFF; font-size:2.2rem; font-weight:800; letter-spacing:-.5px; margin:0 0 6px 0; line-height:1.15; }
.hero p { color:#FACC15; font-size:1rem; font-weight:500; margin:0; }
.hero .hero-sub { color:#CBD5E1; font-size:.88rem; font-weight:400; margin-top:10px; }
.card-label { font-size:.78rem; font-weight:800; letter-spacing:1.6px; text-transform:uppercase; color:#FACC15; margin-bottom:12px; }
.stTabs [data-baseweb="tab-list"] { gap:8px; border-bottom:2px solid #243049; padding-bottom:8px; }
.stTabs [data-baseweb="tab"] { background-color:#16213A; border-radius:10px; padding:10px 20px; font-weight:700; font-size:.92rem; }
.stTabs [data-baseweb="tab"]:hover { background-color:#1F2D4A; }
.stTabs [data-baseweb="tab"][aria-selected="true"] { background-color:#FACC15 !important; color:#0B1220 !important; }
[data-testid="stMetricValue"] { color:#FACC15 !important; font-weight:800 !important; }
[data-testid="stMetricLabel"] { color:#94A3B8 !important; font-weight:700 !important; }
[data-testid="stMetricDelta"] { color:#4ADE80 !important; font-weight:600 !important; }
[data-testid="stDataFrame"] { border-radius:10px; }
[data-testid="stSidebar"] { border-right:2px solid #243049; }
.live-dot { display:inline-block; width:9px; height:9px; border-radius:50%; background:#EF4444; margin-right:7px; animation:pulse 1.4s infinite; }
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.25} }
</style>
""", unsafe_allow_html=True)


def badge_col(label, options=None):
    """BadgeColumn on Streamlit >= 1.44, otherwise a plain TextColumn."""
    if hasattr(st.column_config, "BadgeColumn"):
        return st.column_config.BadgeColumn(label, options=options, format="%s")
    return st.column_config.TextColumn(label)


def style_chart(fig, title=None, height=380, y_title=None, legend=True):
    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font_color="#CBD5E1",
        title_font_color="#FACC15",
        title_font_size=16,
        margin=dict(t=60 if title else 30, b=40, l=50, r=20),
        height=height,
        hoverlabel=dict(bgcolor="#16213A", font_color="#FFFFFF", bordercolor="#FACC15"),
        legend=dict(bgcolor="rgba(0,0,0,0)", font_color="#CBD5E1", orientation="h", yanchor="bottom", y=1.02),
        xaxis=dict(gridcolor="#243049", zerolinecolor="#243049", linecolor="#334155"),
        yaxis=dict(gridcolor="#243049", zerolinecolor="#243049", linecolor="#334155", title=y_title),
        bargap=0.35,
        showlegend=legend,
    )
    if title:
        fig.update_layout(title=dict(text=title, x=0.5, xanchor="center"))
    return fig


GOLD = "#FACC15"
CRIMSON = "#E11D48"
NAVY = "#38BDF8"
GREEN = "#4ADE80"
GREY = "#94A3B8"
PURPLE = "#A78BFA"

# ============================================================
# LOAD DATA
# ============================================================
with st.spinner("Connecting to the AlliSports feed…"):
    CORE = load_core()

if CORE.get("error"):
    st.error(f"⚠️ Could not reach the AlliSports feed: {CORE['error']}")
    st.caption("The API key is read from Streamlit secrets (ALLISPORTS_KEY). "
               "Check your `.streamlit/secrets.toml` or Streamlit Cloud secrets.")
    st.stop()

SPORTS = CORE["sports"]
MATCHES = CORE["matches"]
RESULTS = CORE["results"]
MEDALS = CORE["medal"]
UNIS = CORE["universities"]

sports_map = dict(zip(SPORTS["code"], SPORTS["name"])) if not SPORTS.empty else {}
sports_events = dict(zip(SPORTS["code"], SPORTS["events"])) if not SPORTS.empty else {}

# ============================================================
# SIDEBAR
# ============================================================
st.sidebar.image("https://img.icons8.com/color/96/trophy.png", width=66)
st.sidebar.markdown("### 🏆 WAUG 2026")
st.sidebar.caption("*Live data · AlliSports Data feed*")

code_list = list(SPORTS["code"]) if not SPORTS.empty else []


def sport_label(code: str) -> str:
    n = sports_map.get(code, code)
    ev = sports_events.get(code, 0)
    return f"{SPORT_EMOJI.get(code, '🏅')} {n} ({ev})"


def _sync_sport_query():
    """Keep ?sport= in the URL so a sport view can be shared as a link."""
    try:
        st.query_params["sport"] = st.session_state.get("sport_pick", "")
    except Exception:
        pass


# A ?sport=CODE URL deep-link wins over the widget's stored value.
qp = st.query_params.get("sport", "")
if qp in code_list:
    st.session_state["sport_pick"] = qp

selected_code = st.sidebar.selectbox(
    "Select Sport", code_list, format_func=sport_label,
    key="sport_pick", on_change=_sync_sport_query,
)

if st.query_params.get("sport", "") != selected_code:
    try:
        st.query_params["sport"] = selected_code
    except Exception:
        pass

st.sidebar.markdown("---")

if st.sidebar.button("🔄 Refresh now", use_container_width=True):
    load_core.clear()
    api_get.clear()
    get_competition.clear()
    get_analytics.clear()
    st.rerun()

live_count = int((MATCHES["raw_status"] == "live").sum()) if not MATCHES.empty else 0
finished_count = int((MATCHES["raw_status"] == "finished").sum()) if not MATCHES.empty else 0

with st.sidebar.container(border=True):
    st.markdown('<div class="card-label">Feed Status</div>', unsafe_allow_html=True)
    st.metric("Live matches", live_count)
    st.metric("Matches played", finished_count)
    st.metric("Events", int(SPORTS["events"].sum()) if not SPORTS.empty else 0)

st.sidebar.markdown("---")
with st.sidebar.expander("🥇 Overall medal table", expanded=False):
    st.dataframe(
        MEDALS[["Rank", "University", "Gold", "Silver", "Bronze", "Total"]],
        use_container_width=True, hide_index=True,
        column_config={
            "Rank": st.column_config.NumberColumn("#", format="%d"),
            "Gold": st.column_config.NumberColumn("🥇", format="%d"),
            "Silver": st.column_config.NumberColumn("🥈", format="%d"),
            "Bronze": st.column_config.NumberColumn("🥉", format="%d"),
        },
    )

st.sidebar.markdown("---")
st.sidebar.caption("Data: **AlliSports Data**")
st.sidebar.caption("West African Universities Games 2026")

# ============================================================
# HERO
# ============================================================
sport_name = sports_map.get(selected_code, selected_code)
gen = CORE.get("generatedAt")
gen_txt = ""
if gen:
    try:
        gen_txt = datetime.fromisoformat(gen.replace("Z", "+00:00")).strftime("%d %b %Y, %H:%M UTC")
    except Exception:
        gen_txt = gen

prov = " · includes provisional results" if CORE.get("includesProvisional") else ""

st.markdown(f"""
<div class="hero">
    <span class="hero-badge">{SPORT_EMOJI.get(selected_code,'🏅')} {sport_name} Division</span>
    <h1>West African Universities Games 2026</h1>
    <p>Obafemi Awolowo University, Ile-Ife · Official live results &amp; standings</p>
    <p class="hero-sub">Feed updated {gen_txt}{prov} · Data: AlliSports Data</p>
</div>
""", unsafe_allow_html=True)

# ============================================================
# FILTER DATA TO THE SELECTED SPORT
# ============================================================
sp_matches = MATCHES[MATCHES["Sport"] == selected_code].copy() if not MATCHES.empty else MATCHES
sp_results = RESULTS[RESULTS["Sport"] == selected_code].copy() if not RESULTS.empty else RESULTS

tabs = st.tabs(["🔴 Live & Fixtures", "🏅 Results & Medals", "📊 Standings", "📈 Statistics"])

# ---------------- TAB 1: LIVE & FIXTURES ----------------
with tabs[0]:
    if sp_matches.empty:
        st.info(f"No matches recorded for {sport_name} yet.")
    else:
        live_df = sp_matches[sp_matches["raw_status"] == "live"]
        if not live_df.empty:
            with st.container(border=True):
                st.markdown(
                    '<div class="card-label">🔴 Live Now</div>'
                    '<p><span class="live-dot"></span>In-play matches</p>',
                    unsafe_allow_html=True,
                )
                st.dataframe(
                    live_df[["Event", "Home", "Away", "Score", "Phase", "Venue"]],
                    use_container_width=True, hide_index=True,
                )

        c1, c2 = st.columns([3, 2])
        with c1:
            with st.container(border=True):
                st.markdown('<div class="card-label">All Fixtures & Results</div>', unsafe_allow_html=True)
                st.dataframe(
                    sp_matches[["Event", "Home", "Away", "Score", "Phase", "Status", "Venue"]],
                    use_container_width=True, hide_index=True,
                    column_config={"Status": badge_col("Status")},
                )
        with c2:
            with st.container(border=True):
                st.markdown('<div class="card-label">Match Counts</div>', unsafe_allow_html=True)
                counts = (
                    sp_matches.groupby("Status")
                    .size().reset_index(name="Matches")
                    .sort_values("Matches", ascending=False)
                )
                fig = px.bar(counts, x="Status", y="Matches", color_discrete_sequence=[GOLD])
                st.plotly_chart(style_chart(fig, "Matches by Status", height=340, y_title="Matches"), use_container_width=True)

        with st.container(border=True):
            st.markdown('<div class="card-label">Match Analytics</div>', unsafe_allow_html=True)
            finished = sp_matches[sp_matches["raw_status"] == "finished"]
            if finished.empty:
                st.caption("No finished matches yet for this sport.")
            else:
                opts = finished["Event"] + " — " + finished["Home"] + " v " + finished["Away"]
                pick = st.selectbox("Pick a match", list(range(len(finished))), format_func=lambda i: opts.iloc[i])
                chosen = finished.iloc[pick]
                analytics = get_analytics(chosen["id"])
                if not analytics or not analytics.get("available"):
                    st.info("No narrative analytics available for this match.")
                else:
                    st.markdown(f"**{analytics.get('headline','')}**")
                    comps = analytics.get("comparisons") or []
                    if comps:
                        cdf = pd.DataFrame([
                            {"Metric": c["label"], "Home": c["home"], "Away": c["away"], "Unit": c.get("unit", "")}
                            for c in comps
                        ])
                        st.dataframe(cdf, use_container_width=True, hide_index=True)
                    insights = analytics.get("insights") or []
                    if insights:
                        st.markdown("**Insights**")
                        for ins in insights:
                            st.markdown(f"- {ins['text']}")
                    for note in analytics.get("notes") or []:
                        st.caption(note)

# ---------------- TAB 2: RESULTS & MEDALS ----------------
with tabs[1]:
    if sp_results.empty:
        st.info(f"No results recorded for {sport_name} yet.")
    else:
        c1, c2 = st.columns(2)
        with c1:
            with st.container(border=True):
                st.markdown('<div class="card-label">Podium Winners</div>', unsafe_allow_html=True)
                show = sp_results[["Event", "Gender", "Gold", "Gold Uni", "Silver", "Silver Uni", "Bronze", "Bronze Uni"]]
                st.dataframe(show, use_container_width=True, hide_index=True)

        with c2:
            with st.container(border=True):
                st.markdown('<div class="card-label">Event Status</div>', unsafe_allow_html=True)
                counts = (
                    sp_results.groupby("Status").size().reset_index(name="Events")
                    .sort_values("Events", ascending=False)
                )
                fig = px.bar(counts, x="Status", y="Events", color_discrete_sequence=[NAVY])
                st.plotly_chart(style_chart(fig, "Events by Status", height=340, y_title="Events"), use_container_width=True)

        with st.container(border=True):
            st.markdown('<div class="card-label">Results Schedule</div>', unsafe_allow_html=True)
            st.dataframe(
                sp_results[["Event", "Gender", "Kind", "Starts (UTC)", "Status"]],
                use_container_width=True, hide_index=True,
                column_config={"Status": badge_col("Status")},
            )

# ---------------- TAB 3: STANDINGS ----------------
with tabs[2]:
    comp = get_competition(selected_code)
    if comp:
        for group in comp.get("groups") or []:
            with st.container(border=True):
                st.markdown(
                    f'<div class="card-label">{group.get("name","Group")} '
                    f'(advance: {group.get("advance","—")})</div>',
                    unsafe_allow_html=True,
                )
                grows = group.get("rows") or []
                if grows:
                    gdf = pd.DataFrame([
                        {
                            "Pos": r["position"],
                            "Team": r["team"]["name"],
                            "P": r["played"], "W": r["won"], "D": r["drawn"], "L": r["lost"],
                            "GF": r["goalsFor"], "GA": r["goalsAgainst"],
                            "GD": r["goalDifference"], "Pts": r["points"],
                            "Qualifies": "✅ Yes" if r.get("qualifies") else "—",
                        }
                        for r in grows
                    ])
                    st.dataframe(
                        gdf, use_container_width=True, hide_index=True,
                        column_config={
                            "Pos": st.column_config.NumberColumn("Pos", format="%d"),
                            "Pts": st.column_config.ProgressColumn("Points", min_value=0, max_value=9, format="%d"),
                            "GF": st.column_config.NumberColumn("For", format="%d"),
                            "GA": st.column_config.NumberColumn("Against", format="%d"),
                            "GD": st.column_config.NumberColumn("GD", format="%+d"),
                        },
                    )
        ko = comp.get("knockout")
        if ko:
            with st.container(border=True):
                st.markdown('<div class="card-label">Knockout Rounds</div>', unsafe_allow_html=True)
                st.json(ko, expanded=False)
    else:
        # Fall back to a league table computed from the finished matches
        events = get_sport_events(selected_code)
        is_tournament = any(str(e.get("category", "")).lower() == "tournament" for e in events)
        derived = derive_standings(sp_matches) if is_tournament else pd.DataFrame()

        if not derived.empty:
            with st.container(border=True):
                st.markdown(
                    '<div class="card-label">League Table (computed from match results)</div>',
                    unsafe_allow_html=True,
                )
                st.caption(
                    "The feed does not publish an official group table for this sport, "
                    "so this table is calculated from the finished matches "
                    "(3 points for a win, 1 for a draw)."
                )
                st.dataframe(
                    derived, use_container_width=True, hide_index=True,
                    column_config={
                        "Pos": st.column_config.NumberColumn("Pos", format="%d"),
                        "Pts": st.column_config.ProgressColumn("Points", min_value=0, max_value=12, format="%d"),
                        "GF": st.column_config.NumberColumn("For", format="%d"),
                        "GA": st.column_config.NumberColumn("Against", format="%d"),
                        "GD": st.column_config.NumberColumn("GD", format="%+d"),
                    },
                )
        else:
            st.info(f"No group table or knockout bracket is published for {sport_name}.")

    with st.container(border=True):
        st.markdown('<div class="card-label">Medals won by universities in this sport</div>', unsafe_allow_html=True)
        if sp_results.empty:
            st.caption("No medals awarded yet in this sport.")
        else:
            per_uni = {}
            for _, r in sp_results.iterrows():
                for uni, slot in ((r["Gold Uni"], "Gold"), (r["Silver Uni"], "Silver"), (r["Bronze Uni"], "Bronze")):
                    if uni and uni != "—":
                        per_uni.setdefault(uni, {"University": uni, "Gold": 0, "Silver": 0, "Bronze": 0})[slot] += 1
            if per_uni:
                udf = pd.DataFrame(list(per_uni.values())).sort_values("Gold", ascending=False)
                st.dataframe(udf, use_container_width=True, hide_index=True)
                fig = px.bar(
                    udf.head(10), x="University", y=["Gold", "Silver", "Bronze"], barmode="stack",
                    color_discrete_map={"Gold": GOLD, "Silver": GREY, "Bronze": "#CD7F32"},
                )
                st.plotly_chart(style_chart(fig, f"{sport_name} medals by university", y_title="Medals"), use_container_width=True)
            else:
                st.caption("No medals awarded yet in this sport.")

# ---------------- TAB 4: STATISTICS ----------------
with tabs[3]:
    if sp_matches.empty:
        st.info("No match statistics available yet.")
    else:
        c1, c2 = st.columns(2)
        with c1:
            with st.container(border=True):
                st.markdown('<div class="card-label">Total Goals by Team</div>', unsafe_allow_html=True)
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
                    st.plotly_chart(style_chart(fig, "Goals Scored", y_title="Goals"), use_container_width=True)
                else:
                    st.caption("No goals recorded yet.")

        with c2:
            with st.container(border=True):
                st.markdown('<div class="card-label">Biggest Margins</div>', unsafe_allow_html=True)
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
                    st.plotly_chart(style_chart(fig, "Largest Winning Margins", y_title="", legend=False), use_container_width=True)

        with st.container(border=True):
            st.markdown('<div class="card-label">Games Across All Sports</div>', unsafe_allow_html=True)
            if not MATCHES.empty:
                per_sport = (
                    MATCHES[MATCHES["raw_status"] == "finished"]
                    .groupby("Sport").size().reset_index(name="Matches")
                )
                per_sport["Name"] = per_sport["Sport"].map(sports_map)
                fig = px.bar(per_sport.sort_values("Matches", ascending=False),
                             x="Name", y="Matches", color_discrete_sequence=[NAVY])
                fig.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(style_chart(fig, "Completed Matches by Sport", y_title="Matches"), use_container_width=True)

# ============================================================
# FOOTER
# ============================================================
st.markdown("---")
st.caption(
    "📌 **WAUG 2026 Live Analytics** · Obafemi Awolowo University, Ile-Ife · "
    "Data: **AlliSports Data** · Medal table calculated from confirmed results"
)
