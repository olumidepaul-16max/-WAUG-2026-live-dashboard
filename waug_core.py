"""
WAUG 2026 — shared data layer.

Everything that talks to the AlliSports Data API lives here, so the report,
the dashboard and the data page all read the same numbers from the same place.

API key: read from Streamlit secrets (`ALLISPORTS_KEY`) or the environment,
and sent server-side in the `x-api-key` header. It never reaches the browser.
"""

import os
import re
from datetime import datetime, timezone
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

# Official WAUG palette
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

AUTHOR = "Olumide Paul Opemipo"

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

COLOURS = {"gold": GOLD, "silver": "#C9D3E8", "bronze": "#D08A5A"}


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
# DATA SHAPING — dashboard
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
# DATA SHAPING — report
# ============================================================
def competition_rank(values) -> list:
    """Standard competition ranking: 1, 1, 3 (ties share a place)."""
    order = sorted(range(len(values)), key=lambda i: -values[i])
    ranks = [0] * len(values)
    for pos, idx in enumerate(order, 1):
        if pos > 1 and values[idx] == values[order[pos - 2]]:
            ranks[idx] = ranks[order[pos - 2]]
        else:
            ranks[idx] = pos
    return ranks


def _fmt_date(iso: str) -> str:
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00")).strftime("%d %b")
    except Exception:
        return ""


@st.cache_data(ttl=300, show_spinner=False)
def load_report():
    """Everything the written report needs, derived from the live feed."""
    results_raw = api_get("/results")
    medal_raw = api_get("/medal-table")
    matches_raw = api_get("/matches")
    sports_raw = api_get("/sports")

    for name, payload in (("results", results_raw), ("medal table", medal_raw),
                          ("matches", matches_raw), ("sports", sports_raw)):
        if "__error__" in payload:
            return {"error": f"{name}: {payload['__error__']}"}

    events = results_raw.get("data", [])
    rows = (medal_raw.get("data") or {}).get("rows", [])
    matches = (matches_raw.get("data") or {}).get("matches", [])
    sports = sports_raw.get("data", [])

    # ---------- official table ----------
    table = pd.DataFrame([
        {
            "Rank": r["rank"],
            "Code": r["university"]["code"],
            "School": r["university"]["name"],
            "Country": (r["university"].get("country") or "").upper(),
            "Gold": r["medals"]["gold"],
            "Silver": r["medals"]["silver"],
            "Bronze": r["medals"]["bronze"],
            "Total": r["medals"]["total"],
        }
        for r in rows
    ])
    total_medals = int(table["Total"].sum())

    # ---------- per school × sport ----------
    matrix = pd.DataFrame(0, index=table["Code"], columns=sorted({e["sport"]["code"] for e in events}))
    gold_matrix = matrix.copy()
    dated = []
    sport_pool = {}
    for e in events:
        code = e["sport"]["code"]
        pool = sport_pool.setdefault(code, {"Events": 0, "Medals": 0})
        pool["Events"] += 1
        medals = (e.get("result") or {}).get("medals") or []
        pool["Medals"] += len(medals)
        for m in medals:
            uni = m["university"]["code"]
            if uni in matrix.index:
                matrix.loc[uni, code] += 1
                if m["slot"].startswith("gold"):
                    gold_matrix.loc[uni, code] += 1
        if medals:
            dated.append({
                "Date": (e.get("startsAt") or "")[:10],
                "Sport": code,
                "Medals": len(medals),
                "OAU": sum(1 for m in medals if m["university"]["code"] == "OAU"),
            })

    table["Sports"] = [int((matrix.loc[c] > 0).sum()) for c in table["Code"]]
    table["Share"] = 100 * table["Total"] / total_medals if total_medals else 0
    table["GoldShare"] = [100 * g / t if t else 0 for g, t in zip(table["Gold"], table["Total"])]

    # reconciliation: do the results replay the official table exactly?
    replay = matrix.sum(axis=1)
    mismatches = int(sum(1 for c in table["Code"] if int(replay.get(c, 0)) != int(table.loc[table["Code"] == c, "Total"].iloc[0])))

    # ---------- sport pool ----------
    pool = pd.DataFrame([
        {"Code": c, "Sport": next((s["name"] for s in sports if s["code"] == c), c),
         "Events": v["Events"], "Medals": v["Medals"],
         "PerEvent": v["Medals"] / v["Events"] if v["Events"] else 0}
        for c, v in sport_pool.items()
    ]).sort_values("Medals", ascending=False).reset_index(drop=True)
    pool["Share"] = 100 * pool["Medals"] / total_medals if total_medals else 0

    # ---------- OAU vs UG-GH ----------
    oau = next((c for c in table["Code"] if c == "OAU"), None)
    ug = next((c for c in table["Code"] if c == "UG-GH"), None)
    vs = pd.DataFrame()
    if oau and ug:
        vs = pd.DataFrame([
            {"Code": c, "Sport": next((s["name"] for s in sports if s["code"] == c), c),
             "OAU": int(matrix.loc[oau, c]), "UG-GH": int(matrix.loc[ug, c])}
            for c in matrix.columns
        ])
        vs["Diff"] = vs["OAU"] - vs["UG-GH"]
        vs = vs.sort_values("Diff", ascending=False).reset_index(drop=True)

    # ---------- scoring rules ----------
    rules = table[["Code", "School", "Gold", "Silver", "Bronze", "Total", "Rank"]].copy()
    rules["Points"] = 3 * rules["Gold"] + 2 * rules["Silver"] + rules["Bronze"]
    rules["ByTotal"] = competition_rank(list(rules["Total"].astype(float)))
    rules["ByPoints"] = competition_rank(list(rules["Points"].astype(float)))
    rules["ByGold"] = competition_rank(list(rules["Gold"].astype(float)))
    rules["MaxMove"] = rules[["ByTotal", "ByPoints", "ByGold"]].sub(rules["Rank"], axis=0).abs().max(axis=1)

    # ---------- matches ----------
    mdf = pd.DataFrame([
        {
            "Sport": m["sport"], "Phase": m.get("phase"), "Date": (m.get("startsAt") or "")[:10],
            "Home": (m.get("home") or {}).get("name"), "Away": (m.get("away") or {}).get("name"),
            "HG": (m.get("score") or {}).get("home", 0) or 0,
            "AG": (m.get("score") or {}).get("away", 0) or 0,
            "Pens": bool(m.get("penalties")),
            "PenH": (m.get("penalties") or {}).get("home"),
            "PenA": (m.get("penalties") or {}).get("away"),
        }
        for m in matches
    ])
    if not mdf.empty:
        mdf["Margin"] = (mdf["HG"] - mdf["AG"]).abs()

    # ---------- medals by day ----------
    byday = pd.DataFrame()
    if dated:
        d = pd.DataFrame(dated)
        d = d[d["Date"] != ""]
        if not d.empty:
            byday = (d.groupby("Date")
                     .agg(Events=("Date", "size"), Medals=("Medals", "sum"), OAU=("OAU", "sum"))
                     .reset_index().sort_values("Date"))

    return {
        "error": None,
        "generatedAt": medal_raw.get("generatedAt"),
        "includesProvisional": medal_raw.get("includesProvisional", False),
        "table": table, "matrix": matrix, "gold_matrix": gold_matrix, "pool": pool,
        "vs": vs, "rules": rules, "matches": mdf, "byday": byday,
        "sports": sports, "total_medals": total_medals,
        "event_count": len(events), "match_count": len(matches),
        "medalled_events": int(sum(1 for e in events if (e.get("result") or {}).get("medals"))),
        "cancelled_events": int(sum(1 for e in events if e.get("status") == "cancelled")),
        "undated_events": int(sum(1 for e in events if not (e.get("startsAt") or ""))),
        "undated_medals": int(sum(
            len((e.get("result") or {}).get("medals") or [])
            for e in events if not (e.get("startsAt") or "")
        )),
        "mismatches": mismatches,
        "school_count": int(len(table)),
        "totals": (medal_raw.get("data") or {}).get("totals", {}),
    }


MEDAL_COLS = ["Rank", "School", "Code", "Gold", "Silver", "Bronze", "Total", "Sports", "Share"]
POOL_COLS = ["Code", "Sport", "Events", "Medals", "PerEvent", "Share"]


def medals_from_rows(rows: pd.DataFrame) -> pd.DataFrame:
    """One row per university, counted from the medal rows that survived a filter."""
    if rows.empty:
        return pd.DataFrame(columns=MEDAL_COLS)
    keep = rows["Slot"].astype(str).str.startswith(("gold", "silver", "bronze"))
    rows = rows[keep]
    if rows.empty:
        return pd.DataFrame(columns=MEDAL_COLS)
    out = []
    for (code, school), grp in rows.groupby(["University code", "University"]):
        slot = grp["Slot"].astype(str)
        g = int(slot.str.startswith("gold").sum())
        s = int(slot.str.startswith("silver").sum())
        b = int(slot.str.startswith("bronze").sum())
        out.append({
            "School": school, "Code": code,
            "Gold": g, "Silver": s, "Bronze": b, "Total": g + s + b,
            "Sports": int(grp["Sport"].nunique()),
        })
    df = pd.DataFrame(out).sort_values(
        ["Gold", "Silver", "Bronze"], ascending=False
    ).reset_index(drop=True)
    # standard competition ranking: ties share a place, the next place is skipped
    ranks, previous, current = [], None, 0
    for i, row in df.iterrows():
        key = (row["Gold"], row["Silver"], row["Bronze"])
        if key != previous:
            current = i + 1
            previous = key
        ranks.append(current)
    df["Rank"] = ranks
    df["Share"] = (100 * df["Total"] / df["Total"].sum()).round(1)
    return df[MEDAL_COLS]


def pool_from_selection(medal_rows: pd.DataFrame, scope_events: pd.DataFrame,
                        sports_map: dict) -> pd.DataFrame:
    """Medals per sport against the events that were in scope for the selection.

    The denominator is the official event count for the sport (or for the chosen
    category), so a country filter lowers medals-per-event rather than inflating it.
    """
    if scope_events is None or scope_events.empty:
        return pd.DataFrame(columns=POOL_COLS)
    names = set(scope_events["Sport"].dropna())
    if medal_rows is not None and not medal_rows.empty:
        names |= set(medal_rows["Sport"].dropna())
    if not names:
        return pd.DataFrame(columns=POOL_COLS)
    events = scope_events.groupby("Sport").size()
    medals = (medal_rows.groupby("Sport").size() if medal_rows is not None and not medal_rows.empty
              else pd.Series(dtype="int64"))
    total = int(medals.sum()) if len(medals) else 0
    codes = {v: k for k, v in sports_map.items()}
    rows = []
    for name in names:
        e = int(events.get(name, 0))
        m = int(medals.get(name, 0))
        rows.append({
            "Code": codes.get(name), "Sport": name, "Events": e, "Medals": m,
            "PerEvent": round(m / e, 2) if e else 0,
            "Share": round(100 * m / total, 1) if total else 0,
        })
    return pd.DataFrame(rows).reindex(columns=POOL_COLS).sort_values(
        "Medals", ascending=False
    ).reset_index(drop=True)


@st.cache_data(ttl=300, show_spinner=False)
def report_tables():
    """Reusable DataFrames for the Data page."""
    rep = load_report()
    if rep.get("error"):
        return rep
    results_raw = api_get("/results")
    out = {"error": None, "medal": rep["table"], "pool": rep["pool"], "rules": rep["rules"]}
    rows = []
    events = []
    for e in results_raw.get("data", []):
        events.append({
            "Sport": e["sport"]["name"], "Code": e["sport"]["code"],
            "Event": e.get("category"), "Gender": e.get("gender"),
            "Kind": e.get("kind"), "Event ID": e.get("id"),
            "Date (UTC)": (e.get("startsAt") or "")[:10],
        })
        for m in (e.get("result") or {}).get("medals") or []:
            rows.append({
                "Sport": e["sport"]["name"], "Event": e.get("category"),
                "Gender": e.get("gender"), "Kind": e.get("kind"),
                "Event ID": e.get("id"),
                "Date (UTC)": (e.get("startsAt") or "")[:10],
                "Slot": m.get("slot"), "University": m["university"]["name"],
                "University code": m["university"]["code"],
                "Athlete": m.get("athleteName") or "",
            })
    out["results"] = pd.DataFrame(rows)
    out["events"] = pd.DataFrame(events)
    out["matches"] = rep["matches"]
    return out


# ============================================================
# RENDERING HELPERS
# ============================================================
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
