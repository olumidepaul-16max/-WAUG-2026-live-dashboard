"""
WAUG 2026 Live Sports Dashboard  —  Obafemi Awolowo University, Ile-Ife
Powered by the AlliSports Data API (data.allimediahub.com)
The API key lives on the server and is sent in the `x-api-key` header.
"""

import os
from datetime import datetime
from pathlib import Path

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
FALLBACK_KEY = "asd_4zqyjoayTzsKxPi1YpjND3bstQ3v-44J"

HERE = Path(__file__).parent
ASSETS = HERE / "assets"

NAVY = "#0D1940"
NAVY2 = "#2630BD"
GOLD = "#E8B84B"
GOLD2 = "#C4941A"
CRIMSON = "#F0616D"
TEAL = "#4FD1C5"
PURPLE = "#A78BFA"
ORANGE = "#F0A03C"
BLUE = "#5B8DEF"
INK = "#E2E8F7"
MUTED = "#8FA3D4"

SPORT_EMOJI = {
    "ATH": "🏃", "BDM": "🏸", "BKB": "🏀", "BOX": "🥊", "CHS": "♟️", "ESP": "🎮",
    "FBL": "⚽", "HBL": "🤾", "HKY": "🏑", "JUD": "🥋", "RUG": "🏉", "SCR": "🔤",
    "SQU": "🎾", "SWM": "🏊", "TEN": "🎾", "TKW": "🥋", "TTE": "🏓", "VVO": "🏐",
    "WLF": "🏋️", "WRE": "🤼",
}

STATUS_STYLE = {
    "finished": "Completed", "live": "🔴 LIVE", "scheduled": "Scheduled",
    "postponed": "Postponed", "cancelled": "Cancelled", "abandoned": "Abandoned",
}


def asset(*parts) -> str:
    p = ASSETS.joinpath(*parts)
    return str(p) if p.exists() else ""


@st.cache_data(show_spinner=False)
def data_uri(path: str) -> str:
    """Base64-encode an image so it can be embedded inside raw HTML."""
    if not path or not os.path.exists(path):
        return ""
    import base64
    ext = Path(path).suffix.lower()
    mime = "image/png" if ext == ".png" else "image/jpeg"
    with open(path, "rb") as fh:
        return f"data:{mime};base64,{base64.b64encode(fh.read()).decode()}"


# ============================================================
# API KEY
# ============================================================
def get_api_key() -> str:
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
    sports_raw = api_get("/sports")
    if "__error__" in sports_raw:
        return {"error": sports_raw["__error__"]}

    medal_raw = api_get("/medal-table")
    results_raw = api_get("/results")
    matches_raw = api_get("/matches")
    unis_raw = api_get("/universities")

    sports_df = pd.DataFrame(sports_raw.get("data", []))
    if not sports_df.empty:
        sports_df["emoji"] = sports_df["code"].map(SPORT_EMOJI).fillna("🏅")

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

    mrows = []
    for m in (matches_raw.get("data") or {}).get("matches", []):
        sc = m.get("score") or {}
        pen = m.get("penalties")
        score_txt = f"{sc.get('home', 0)} - {sc.get('away', 0)}"
        if pen:
            score_txt += f" ({pen.get('home')}-{pen.get('away')} pen)"
        mrows.append({
            "id": m["id"],
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

    uitems = unis_raw.get("data") if isinstance(unis_raw.get("data"), list) else \
        (unis_raw.get("data") or {}).get("universities", [])
    unis_df = pd.DataFrame([
        {
            "Code": u["code"], "University": u["name"], "Country": u.get("country"),
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
        "sports": sports_df, "medal": medal_df, "matches": matches_df,
        "results": results_df, "universities": unis_df,
        "medal_totals": (medal_raw.get("data") or {}).get("totals", {}),
        "medal_status": (medal_raw.get("data") or {}).get("status", ""),
    }


@st.cache_data(ttl=90, show_spinner=False)
def get_competition(sport_code: str):
    ev = api_get("/events")
    if "__error__" in ev:
        return None
    cands = [e for e in ev.get("data", [])
             if e["sport"]["code"] == sport_code and e.get("kind") == "team"]
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
    ev = api_get("/events")
    if "__error__" in ev:
        return []
    return [e for e in ev.get("data", []) if e["sport"]["code"] == sport_code]


@st.cache_data(ttl=90, show_spinner=False)
def get_analytics(match_id: str):
    resp = api_get_path(f"/matches/{match_id}/analytics")
    if "__error__" in resp:
        return None
    return resp.get("data")


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


# ============================================================
# PAGE SETUP
# ============================================================
st.set_page_config(
    page_title="WAUG 2026 Live Dashboard",
    page_icon="🏆",
    layout="wide",
    initial_sidebar_state="expanded",
)

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
    border-radius: 16px; padding: 16px 24px; margin-bottom: 20px;
    box-shadow: 0 12px 32px rgba(0,0,0,.5);
    border-bottom: 3px solid #E8B84B;
}
.brand-logo { height: 64px; width: 64px; object-fit: contain; flex: 0 0 auto;
              filter: drop-shadow(0 2px 8px rgba(0,0,0,.55)); }
.brand-text { flex: 1 1 auto; min-width: 0; }
.brand-text h1 { color:#fff; font-size:1.34rem; font-weight:800; margin:0; line-height:1.25; letter-spacing:-.3px; }
.brand-text p  { color:#E8B84B; margin:4px 0 0; font-size:.83rem; font-weight:600; }
.brand-text small { color:#8FA3D4; font-size:.73rem; }
.brand-oau { height: 54px; width: auto; object-fit: contain; flex: 0 0 auto;
             background:#fff; padding:5px; border-radius:10px; }
.brand-mascot { height: 60px; width: auto; object-fit: contain; flex: 0 0 auto; }

/* ================= SPORT HEADER ================= */
.sport-head { display:flex; align-items:center; gap:16px; margin: 4px 0 12px; }
.sport-emoji { font-size:2.2rem; line-height:1.1; }
.sport-head h2 { color:#fff; font-size:1.8rem; font-weight:800; margin:0; letter-spacing:-.4px; }
.sport-head .rule { height:3px; width:64px; background:#E8B84B; border-radius:2px; margin-top:7px; }
.sport-head .meta { color:#8FA3D4; font-size:.84rem; font-weight:600; margin-left:auto; text-align:right; }
.sport-banner { border-radius: 12px; overflow: hidden; border: 1px solid rgba(232,184,75,.22);
                box-shadow: 0 8px 24px rgba(0,0,0,.4); margin-bottom: 6px; }
.sport-banner img { display:block; width:100%; }
.gold-rule { height:3px; background:linear-gradient(90deg,#E8B84B 0%, rgba(232,184,75,0) 70%);
             border-radius:2px; margin: 0 0 20px; }

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
.side-logo { display:flex; align-items:center; gap:10px; margin-bottom:6px; }
.side-logo img { height:42px; width:42px; object-fit:contain; filter:drop-shadow(0 2px 6px rgba(0,0,0,.5)); }
.side-cap { color:#E8B84B; font-size:.72rem; font-weight:800; text-transform:uppercase; letter-spacing:1.3px; margin:16px 0 6px; }

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
# SIDEBAR
# ============================================================
st.sidebar.markdown(
    f'<div class="side-logo"><img src="{data_uri(asset("inline", "logo-waug.png"))}"></div>',
    unsafe_allow_html=True,
)
st.sidebar.markdown("**WAUG 2026**")
st.sidebar.caption("West African University Games · OAU, Ile-Ife")
st.sidebar.markdown('<hr class="rule-line">', unsafe_allow_html=True)
st.sidebar.markdown('<div class="side-cap">Choose a sport</div>', unsafe_allow_html=True)


def sport_label(code: str) -> str:
    return f"{SPORT_EMOJI.get(code, '🏅')}  {sports_map.get(code, code)}"


def _sync_sport_query():
    try:
        st.query_params["sport"] = st.session_state.get("sport_pick", "")
    except Exception:
        pass


qp = st.query_params.get("sport", "")
if qp in code_list:
    st.session_state["sport_pick"] = qp

selected_code = st.sidebar.selectbox(
    "Sport", code_list, format_func=sport_label,
    key="sport_pick", on_change=_sync_sport_query, label_visibility="collapsed",
)
if st.query_params.get("sport", "") != selected_code:
    try:
        st.query_params["sport"] = selected_code
    except Exception:
        pass

thumb = asset("thumb", f"{selected_code}.jpg")
if thumb:
    st.sidebar.image(thumb, use_container_width=True)
st.sidebar.markdown(
    f'<div style="text-align:center;font-weight:700;color:#0D1940;margin-top:-6px;">'
    f'{SPORT_EMOJI.get(selected_code, "🏅")} {sports_map.get(selected_code, selected_code)}</div>',
    unsafe_allow_html=True,
)

st.sidebar.markdown('<hr class="rule-line">', unsafe_allow_html=True)
if st.sidebar.button("🔄  Refresh feed", use_container_width=True):
    load_core.clear(); api_get.clear()
    get_competition.clear(); get_analytics.clear()
    st.rerun()

st.sidebar.markdown('<div class="side-cap">Feed status</div>', unsafe_allow_html=True)
c1, c2 = st.sidebar.columns(2)
c1.metric("Live", live_total)
c2.metric("Played", finished_total)

st.sidebar.markdown('<hr class="rule-line">', unsafe_allow_html=True)
with st.sidebar.expander("🥇 Medal table", expanded=False):
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
  <img class="brand-logo" src="{data_uri(asset('inline', 'logo-waug.png'))}">
  <div class="brand-text">
    <h1>West African Universities Games 2026</h1>
    <p>Obafemi Awolowo University, Ile-Ife &nbsp;·&nbsp; Official live results &amp; standings</p>
    <small>Feed updated {gen_txt}{prov}</small>
  </div>
  <img class="brand-oau" src="{data_uri(asset('inline', 'logo-oau.png'))}">
  <img class="brand-mascot" src="{data_uri(asset('inline', 'mascot.png'))}">
</div>
""", unsafe_allow_html=True)

# ============================================================
# SPORT HEADER + BANNER IMAGE
# ============================================================
sport_name = sports_map.get(selected_code, selected_code)
ev_count = sports_events.get(selected_code, 0)
sp_matches = MATCHES[MATCHES["Sport"] == selected_code].copy() if not MATCHES.empty else MATCHES
sp_results = RESULTS[RESULTS["Sport"] == selected_code].copy() if not RESULTS.empty else RESULTS

st.markdown(f"""
<div class="sport-head">
  <span class="sport-emoji">{SPORT_EMOJI.get(selected_code, '🏅')}</span>
  <div>
    <h2>{sport_name}</h2>
    <div class="rule"></div>
  </div>
  <div class="meta">{ev_count} event(s) &nbsp;·&nbsp; {len(sp_matches)} match(es) &nbsp;·&nbsp; {len(sp_results)} result(s)</div>
</div>
""", unsafe_allow_html=True)

banner = asset("sport", f"{selected_code}.jpg")
if banner:
    st.image(banner, use_container_width=True)
    st.markdown('<div class="gold-rule"></div>', unsafe_allow_html=True)

tabs = st.tabs(["🔴 Live & Fixtures", "🏅 Results & Medals", "📊 Standings", "📈 Statistics"])

# ---------------- TAB 1: LIVE & FIXTURES ----------------
with tabs[0]:
    if sp_matches.empty:
        with st.container(border=True):
            st.markdown('<div class="card-title">No fixtures</div>', unsafe_allow_html=True)
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
        ko = comp.get("knockout")
        if ko:
            with st.container(border=True):
                st.markdown('<div class="card-title">Knockout rounds</div>', unsafe_allow_html=True)
                st.json(ko, expanded=False)
    else:
        events = get_sport_events(selected_code)
        is_tournament = any(str(e.get("category", "")).lower() == "tournament" for e in events)
        derived = derive_standings(sp_matches) if is_tournament else pd.DataFrame()
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
            if not MATCHES.empty:
                per_sport = (MATCHES[MATCHES["raw_status"] == "finished"]
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
