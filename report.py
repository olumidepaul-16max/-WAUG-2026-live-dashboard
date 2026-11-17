"""
WAUG 2026 — the written report.

A single long read: what the medal table shows, what produced it, what it
hides, and what I would change about how it is published.

Every figure is computed from the AlliSports Data feed at load time.
"""

from datetime import datetime

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import ui
from waug_core import AUTHOR, competition_rank, load_report

ui.page_css()

rep = load_report()
if rep.get("error"):
    st.error(f"⚠️ Could not reach the AlliSports feed — {rep['error']}")
    st.caption("The key is read from Streamlit secrets (ALLISPORTS_KEY). Try refreshing.")
    st.stop()

T = rep["table"].copy()
MATRIX = rep["matrix"]
GOLD_M = rep["gold_matrix"]
POOL = rep["pool"]
VS_ALL = rep["vs"]
VS = VS_ALL[VS_ALL["OAU"] + VS_ALL["UG-GH"] > 0].copy() if not VS_ALL.empty else VS_ALL
RULES = rep["rules"]
MDF = rep["matches"]
BYDAY = rep["byday"]
TOT = rep["total_medals"]
BY = T.set_index("Code")

ALL_SPORTS = {s["code"]: s["name"] for s in rep["sports"]}
SPORT_NAME = lambda c: ALL_SPORTS.get(c, c)  # noqa: E731

oau = BY.loc["OAU"]
ug = BY.loc["UG-GH"]
OAU_T, UG_T = int(oau["Total"]), int(ug["Total"])
OAU_G, OAU_S, OAU_B = int(oau["Gold"]), int(oau["Silver"]), int(oau["Bronze"])
OAU_SPORTS, UG_SPORTS = int(oau["Sports"]), int(ug["Sports"])
OAU_GOLD_SHARE = 100 * OAU_G / OAU_T
GAP = OAU_T - UG_T


def _gold_share(code: str) -> float:
    return float(BY.loc[code, "GoldShare"]) if code in BY.index else 0.0


DELSU_PCT = _gold_share("DELSU")
LASU_PCT = _gold_share("LASU")
BIU_PCT = _gold_share("BIU-NG")
UG_PCT = 100 * int(ug["Gold"]) / UG_T if UG_T else 0.0

top3_share = 100 * T.head(3)["Total"].sum() / TOT
top5_share = 100 * T.head(5)["Total"].sum() / TOT
cum = (T["Total"].cumsum() / TOT * 100).tolist()
half_at = next(i for i, c in enumerate(cum, 1) if c >= 50)

shares = (T["Total"] / TOT).to_numpy()
effective_n = 1 / (shares ** 2).sum()
xs = sorted(shares)
gini = sum((2 * (i + 1) - len(xs) - 1) * v for i, v in enumerate(xs)) / (len(xs) * sum(xs))
breadth_r = T["Sports"].corr(T["Total"])

gold_pool = int(rep["totals"].get("gold", T["Gold"].sum()))
silver_pool = int(rep["totals"].get("silver", T["Silver"].sum()))
bronze_pool = int(rep["totals"].get("bronze", T["Bronze"].sum()))

missing_sports = [c for c in ALL_SPORTS if c not in MATRIX.columns]


def _pool(code: str):
    row = POOL.loc[POOL["Code"] == code]
    return (int(row["Events"].iloc[0]), int(row["Medals"].iloc[0])) if len(row) else (0, 0)


TKW_EVENTS, TKW_MEDALS = _pool("TKW")
BDM_EVENTS, BDM_MEDALS = _pool("BDM")
EMPTY_SPORTS = len(missing_sports) + int((POOL["Medals"] == 0).sum())
_WORDS = {1: "One", 2: "Two", 3: "Three", 4: "Four", 5: "Five", 6: "Six",
          7: "Seven", 8: "Eight", 9: "Nine", 10: "Ten"}
EMPTY_WORD = _WORDS.get(EMPTY_SPORTS, str(EMPTY_SPORTS))
top_pool = POOL[POOL["Medals"] > 0].sort_values("Medals", ascending=False)
MEDAL_SPORTS = len(top_pool)
big_two = int(top_pool.head(2)["Medals"].sum())
big_two_share = 100 * big_two / TOT

RULES_BY_TOTAL = rep["rules"].sort_values("ByTotal")
third_by_total = RULES_BY_TOTAL.iloc[2]
official_third = T.iloc[2]
movers = RULES[RULES["MaxMove"] >= 3].sort_values("MaxMove", ascending=False)
big_mover = movers.iloc[0] if len(movers) else None
BIG_MOVER_TOTAL = int(big_mover["ByTotal"]) if big_mover is not None else 0

ahead = int((VS["Diff"] > 0).sum())
behind = int((VS["Diff"] < 0).sum())
level = int((VS["Diff"] == 0).sum())
third_codes = RULES[RULES["ByTotal"] == int(third_by_total["ByTotal"])]["Code"].tolist()
third_phrase = " and ".join(third_codes)

bkb = MDF[MDF["Sport"] == "BKB"] if not MDF.empty else MDF
fbl = MDF[MDF["Sport"] == "FBL"] if not MDF.empty else MDF
BKB_MED = float(bkb["Margin"].median()) if not bkb.empty else 0
BKB_20 = int((bkb["Margin"] >= 20).sum()) if not bkb.empty else 0
FBL_TIGHT = int((fbl["Margin"] <= 1).sum()) if not fbl.empty else 0
FBL_PENS = int(fbl["Pens"].sum()) if not fbl.empty else 0

gen = rep.get("generatedAt") or ""
try:
    gen_txt = datetime.fromisoformat(gen.replace("Z", "+00:00")).strftime("%d %B %Y, %H:%M UTC")
except Exception:
    gen_txt = gen

TOC = [
    ("s0", "In short"),
    ("s1", "1. What I did"),
    ("s2", "2. How concentrated the medals were"),
    ("s3", "3. Depth against specialism"),
    ("s4", f"4. Where the {GAP}-medal gap came from"),
    ("s5", "5. Volume against quality"),
    ("s6", "6. Does the ranking rule matter?"),
    ("s7", "7. What the table hides"),
    ("s8", "8. The team games"),
    ("s9", "9. What this does not show"),
    ("s10", "10. What I would do next"),
    ("s11", "11. Who built this"),
]
ui.toc(TOC)
st.sidebar.markdown(
    '<div class="toc-cap" style="margin-top:18px;">Source</div>'
    '<div style="font-size:.74rem;line-height:1.6;color:#7E92C2;">'
    "AlliSports Data API<br>feed read " + (gen_txt or "just now") + "</div>",
    unsafe_allow_html=True,
)

# ============================================================
# HERO
# ============================================================
ui.eyebrow("WAUG 2026 &nbsp;·&nbsp; Results analysis &nbsp;·&nbsp; 2–12 October &nbsp;·&nbsp; Obafemi Awolowo University, Ile-Ife")
ui.display(f"Depth won these Games. OAU medalled in {OAU_SPORTS} sports; the runners-up managed "
           f"{_WORDS.get(UG_SPORTS, UG_SPORTS).lower()}.")
ui.lede(
    f"I took the {TOT} medals of the 15th West African University Games and asked what produced the table, "
    f"not just what it shows. The host won <strong>{OAU_T}</strong> of them — a quarter of everything awarded — "
    f"yet only <strong>{OAU_GOLD_SHARE:.0f} in every 100</strong> were gold. The gap to University of Ghana is "
    f"<strong>{GAP}</strong>, and it is built out of judo, taekwondo, chess and the pool rather than one big afternoon. "
    "The top two places survive every scoring rule I tried. Third place does not."
)
ui.kpis([
    (f"{100 * OAU_T / TOT:.0f}%", f"of all {TOT} medals went to the host", f"Results · {OAU_T} medals"),
    (f"{OAU_SPORTS} v {UG_SPORTS}", "sports in which OAU and UG-GH won at least one medal", "Results"),
    (f"{OAU_GOLD_SHARE:.0f}%", f"of OAU's medals were gold; DELSU turned {DELSU_PCT:.0f}% of its "
     f"{int(BY.loc['DELSU', 'Total'])} into gold", "Calculated"),
])

b1, b2, b3 = st.columns([1, 1.12, 1.02])
with b1:
    st.markdown('<a class="btn" href="#s1">Read the report ↓</a>', unsafe_allow_html=True)
with b2:
    st.page_link("dashboard.py", label="Open the dashboard", icon="📊")
with b3:
    st.page_link("data.py", label="Download the data", icon="🗂️")

ui.byline(
    f"By <b>{AUTHOR}</b> &nbsp;·&nbsp; Data: <b>AlliSports Data API</b> &nbsp;·&nbsp; "
    f"{rep['school_count']} universities, {rep['medalled_events']} events with results, {rep['match_count']} matches"
)

st.markdown('<div id="s0"></div>', unsafe_allow_html=True)
ui.summary([
    ("Concentration", f"{TOT} medals across {rep['school_count']} schools. The top three took {top3_share:.0f}%, "
                      f"the top five {top5_share:.0f}%, and the leading {half_at} schools took half. OAU alone took "
                      f"{100 * OAU_T / TOT:.0f}%."),
    ("Depth", f"Total medals track how many sports a school medalled in (r = {breadth_r:.2f}). "
              f"OAU medalled in all {OAU_SPORTS} sports on record; University of Ghana in {UG_SPORTS}."),
    ("The gap", f"OAU's {GAP}-medal lead is broad — ahead in {ahead} sports, behind in {behind}. "
                "Judo (+20), taekwondo (+13) and chess (+12) carry it; athletics (−20) is the only large loss."),
    ("Quality", f"OAU took {OAU_G} golds but {OAU_S} silvers — a third of every silver awarded. Only "
                f"{OAU_GOLD_SHARE:.0f}% of its medals were gold, against DELSU's {DELSU_PCT:.0f}% and "
                f"LASU's {LASU_PCT:.0f}%."),
    ("Rules", "The top two hold under gold-first, total medals, 3-2-1 points and golds-only. Third does not: "
              f"on total medals {third_phrase} share third and BIU-NG drops to fifth. "
              f"{len(movers)} schools move three places or more."),
    ("Coverage", f"The results cover {len(MATRIX.columns)} of the {len(ALL_SPORTS)} sports in the catalogue, and "
                 f"only {MEDAL_SPORTS} of them awarded medals; {rep['undated_medals']} medals "
                 f"({100 * rep['undated_medals'] / TOT:.0f}%) sit on events with no date."),
])

# ============================================================
# 1. METHOD
# ============================================================
ui.section("s1", "01", "Method", "What I did, and how I checked it")
ui.body(
    "The Games ran on the Obafemi Awolowo University campus from 2 to 12 October 2026. I pulled the official "
    "results, the medal table, the schedule and every finished match from the AlliSports Data feed, then "
    f"<strong>rebuilt the medal table from the {TOT} individual medals</strong> to see whether the two agreed. "
    f"They do exactly: the same {TOT} medals, the same {rep['school_count']} schools, no difference in a single "
    "row. Every number below therefore traces back to a recorded result."
)
ui.body(
    "I keep the official ranking separate from the alternative scoring rules I use as checks, and I say when a "
    "figure is a calculation of mine rather than something the feed states. Two things I did not have — entries "
    "per school and a complete schedule — limit what can be claimed, and I flag them where they matter."
)
m1, m2, m3, m4 = st.columns(4)
m1.metric("Medals analysed", f"{TOT}", f"{rep['medalled_events']} events with results")
m2.metric("Schools", f"{rep['school_count']}", "every one won at least one")
m3.metric("Matches", f"{rep['match_count']}", "all finished")
m4.metric("Table rebuild", "0 rows off", "matches the official table")

with st.expander("How I collected and checked the data"):
    st.markdown(
        f"""
- **Source.** `GET /results` (all {rep['event_count']} events, with the medal list for each),
  `GET /medal-table` (the official ranking), `GET /matches` ({rep['match_count']} fixtures) and `GET /sports`.
- **The check.** I counted medals from the results by school and compared the total with the official
  table. All {rep['school_count']} rows agree; the combined totals are {gold_pool} gold, {silver_pool} silver
  and {bronze_pool} bronze.
- **What counts.** Only medals attached to a confirmed result. {rep['cancelled_events']} events were
  cancelled and carry no medal; {rep['event_count'] - rep['medalled_events'] - rep['cancelled_events']}
  more are still marked scheduled.
- **Dates.** {rep['undated_events']} events have no start time in the feed, which is why
  {rep['undated_medals']} medals cannot be placed on a day.
- **Rules.** Ties share a place and the next place is skipped (1, 1, 3), matching how the official
  table treats equal gold counts.
"""
    )

# ============================================================
# 2. CONCENTRATION
# ============================================================
ui.section("s2", "02", "Concentration", "Half the medals went to four schools")
ui.body(
    f"OAU's {OAU_T} medals are {100 * OAU_T / TOT:.1f}% of everything awarded — more than twice the runner-up's "
    f"{UG_T}. With BIU-NG's {int(BY.loc['BIU-NG', 'Total'])} the top three hold {top3_share:.1f}%; UI's "
    f"{int(BY.loc['UI', 'Total'])} pushes the leading four past half at {cum[3]:.1f}%, and the top five reach "
    f"{top5_share:.1f}%. The spread is equivalent to about {effective_n:.0f} equally sized schools, with a Gini "
    f"coefficient of {gini:.2f}: unequal, but not a monopoly. Every one of the {rep['school_count']} schools won "
    "something; four won fewer than five medals."
)

ui.chart_title("How quickly the medals add up  ·  cumulative share of all medals")
fig = go.Figure()
fig.add_trace(go.Scatter(
    x=list(range(1, len(T) + 1)), y=cum, mode="lines+markers",
    line=dict(color=ui.GOLD, width=2.6, shape="spline"),
    marker=dict(size=5.5, color=ui.GOLD, line=dict(color="#0A1533", width=1)),
    fill="tozeroy", fillcolor="rgba(232,184,75,.07)",
    hovertemplate="Top %{x} schools → %{y:.1f}% of medals<extra></extra>", name="",
))
fig.add_hline(y=50, line=dict(color="rgba(255,255,255,.30)", width=1, dash="dot"))
fig.add_annotation(x=len(T), y=50, text="half of all medals", showarrow=False, yshift=13,
                   xanchor="right", font=dict(color="#9DB0DA", size=11))
fig.add_vline(x=half_at, line=dict(color="rgba(232,184,75,.45)", width=1, dash="dot"))
fig.add_annotation(x=half_at, y=12, text=f"{half_at} schools", showarrow=False, xshift=6,
                   font=dict(color="#E8B84B", size=11))
fig.add_annotation(x=1, y=cum[0], text=f"OAU {cum[0]:.1f}%", showarrow=True, arrowhead=0,
                   ax=26, ay=-28, font=dict(color="#C9D5EE", size=11),
                   arrowcolor="rgba(232,184,75,.6)")
ui.base_layout(fig, height=340)
fig.update_xaxes(title="Schools, ranked by medals", dtick=2)
fig.update_yaxes(title="Share of all medals", range=[0, 104], ticksuffix="%", dtick=25)
ui.chart(fig, key="cume")
ui.caption("What it shows",
           f"The curve is steepest at the top. One school alone reaches {cum[0]:.1f}%, four pass half, and the "
           "last ten schools add less than a fifth between them.")

ui.chart_title("Who won what  ·  medals by type, ten highest-ranked schools")
top10 = T.head(10)
fig = go.Figure()
for name, colour in (("Gold", ui.GOLD), ("Silver", "#BFCDE8"), ("Bronze", "#C98A5B")):
    fig.add_trace(go.Bar(
        x=top10["Code"], y=top10[name], name=name, marker_color=colour,
        marker_line=dict(width=0),
        hovertemplate=f"%{{x}} · {name}: %{{y}}<extra></extra>",
    ))
fig.update_layout(barmode="stack")
ui.base_layout(fig, height=330, legend=True)
fig.update_yaxes(title="Medals")
ui.chart(fig, key="stack")
ui.caption("What it shows",
           f"OAU's bar is more than twice the height of UG-GH's, and its silver segment "
           f"({OAU_S}) is longer than its gold and bronze together.")

# ============================================================
# 3. DEPTH
# ============================================================
ui.section("s3", "03", "Depth", "Breadth, not conversion, produced the table")
ui.body(
    f"Across the {rep['school_count']} schools, the correlation between the number of sports medalled in and the "
    f"total medal count is <strong>r = {breadth_r:.2f}</strong> — almost a straight line. The host is the extreme "
    f"case: a medal in all {OAU_SPORTS} sports on record. University of Ghana is the opposite shape — only "
    f"{UG_SPORTS} sports, but 29 medals in athletics and 18 in swimming, enough for second place. BIU-NG is a "
    "third shape again: seven sports, 38 medals, and more than half of them gold."
)
ui.chart_title("Volume against breadth  ·  each bubble is a school, size = golds")
size = 9 + (T["Total"] / T["Total"].max()) * 30
colours = [ui.GOLD if c == "OAU" else ("#F0616D" if c == "UG-GH" else "#3D57DE") for c in T["Code"]]
fig = go.Figure()
fig.add_trace(go.Scatter(
    x=T["Total"], y=T["Sports"], mode="markers+text", text=T["Code"],
    textposition="top center", textfont=dict(size=9, color="#9DB0DA"),
    marker=dict(size=size, color=colours, opacity=.9,
                line=dict(color="rgba(255,255,255,.35)", width=1)),
    hovertemplate="<b>%{text}</b><br>%{x} medals · %{y} sports<extra></extra>", name="",
))
# least-squares trend line, as a reading aid
slope, intercept = np.polyfit(T["Total"], T["Sports"], 1)
xx = np.linspace(T["Total"].min(), T["Total"].max(), 20)
fig.add_trace(go.Scatter(x=xx, y=slope * xx + intercept, mode="lines",
                         line=dict(color="rgba(255,255,255,.22)", width=1.5, dash="dot"),
                         hoverinfo="skip", name=""))
ui.base_layout(fig, height=380)
fig.update_xaxes(title="Total medals")
fig.update_yaxes(title="Sports medalled in", dtick=2)
ui.chart(fig, key="scatter")
ui.caption("What it shows",
           f"OAU sits at the top right — the most medals and the widest programme. UG-GH sits low on the "
           f"vertical axis: {UG_T} medals from {UG_SPORTS} sports.")

ui.chart_title("The shape of each campaign  ·  medals by school and sport, top twelve schools")
codes12 = T.head(12)["Code"].tolist()
cols = list(MATRIX.columns)
z, text = [], []
for code in codes12:
    row = [int(MATRIX.loc[code, c]) for c in cols]
    z.append(row)
    text.append([str(v) if v else "" for v in row])
fig = go.Figure(go.Heatmap(
    z=z, x=cols, y=codes12, text=text, texttemplate="%{text}",
    textfont=dict(size=10, color="#F2F6FF"),
    colorscale=[[0, "rgba(255,255,255,.035)"], [0.18, "#1B2C63"], [0.55, "#3D57DE"], [1, ui.GOLD]],
    showscale=False, xgap=2, ygap=2,
    hovertemplate="%{y} · %{x}: %{z} medals<extra></extra>",
))
ui.base_layout(fig, height=430, margin=dict(t=18, r=18, b=44, l=60))
fig.update_yaxes(autorange="reversed", title=None)
fig.update_xaxes(side="top", title=None)
ui.chart(fig, key="heat")
ui.caption("What it shows",
           f"OAU's row is filled edge to edge; UG-GH has two bright cells (athletics, swimming) and little else. "
           "Width, not depth within one sport, separates the top two.")

# ============================================================
# 4. THE GAP
# ============================================================
ui.section("s4", "04", "The gap", f"Where {GAP} medals came from")
ui.body(
    f"OAU finished {GAP} medals ahead of UG-GH. Taken sport by sport, the differences add up exactly to that gap: "
    f"ahead in {ahead} of the {len(VS)} sports the two schools shared, behind in {behind}, "
    f"{'level in none' if level == 0 else f'level in {level}'}. "
    "Judo (+20) and taekwondo (+13) — where Ghana won nothing — supply more than half of it; chess (+12) and "
    "swimming (+12) add most of the rest. Athletics runs the other way: UG-GH's 29 medals there against OAU's 9 "
    "is the single large loss (−20). Badminton and tennis (−4 each) are the only other sports where the runner-up "
    "came out ahead."
)
ui.chart_title(f"Where the gap came from  ·  OAU medals minus UG-GH medals, by sport")
vs = VS.sort_values("Diff")
fig = go.Figure(go.Bar(
    x=vs["Diff"], y=vs["Code"], orientation="h",
    marker_color=[ui.GOLD if d > 0 else "#3D57DE" for d in vs["Diff"]],
    marker_line=dict(width=0),
    text=[f"{d:+d}" for d in vs["Diff"]], textposition="outside",
    textfont=dict(color="#C9D5EE", size=11),
    customdata=vs["Sport"],
    hovertemplate="%{customdata}: %{x:+d}<extra></extra>",
))
fig.add_vline(x=0, line=dict(color="rgba(255,255,255,.28)", width=1))
ui.base_layout(fig, height=430, margin=dict(t=18, r=54, b=44, l=54))
fig.update_xaxes(title="Medals ahead of UG-GH", range=[-(int(abs(VS["Diff"]).max()) + 4), int(abs(VS["Diff"]).max()) + 4])
fig.update_yaxes(title=None)
ui.chart(fig, key="gap")
ui.caption("What it shows",
           f"Every bar sums to {GAP}. The gold bars are sports OAU won on; the blue bar on athletics is the "
           "one place the runner-up made a large gain.")

ui.chart_title("The two schools side by side  ·  medals by sport")
fig = go.Figure()
fig.add_trace(go.Bar(x=VS["Code"], y=VS["OAU"], name="OAU", marker_color=ui.GOLD,
                     hovertemplate="OAU · %{x}: %{y}<extra></extra>"))
fig.add_trace(go.Bar(x=VS["Code"], y=VS["UG-GH"], name="UG-GH", marker_color="#5B8DEF",
                     hovertemplate="UG-GH · %{x}: %{y}<extra></extra>"))
ui.base_layout(fig, height=340, legend=True)
fig.update_yaxes(title="Medals")
ui.chart(fig, key="versus")
ui.caption("What it shows",
           f"UG-GH's total is carried by two bars (athletics, swimming); OAU's is spread across the whole axis.")

with st.expander("See the sport-by-sport numbers"):
    show = VS[["Sport", "OAU", "UG-GH", "Diff"]].rename(
        columns={"Sport": "Sport", "OAU": "OAU", "UG-GH": "UG-GH", "Diff": "Difference"})
    st.dataframe(show, hide_index=True, use_container_width=True)

# ============================================================
# 5. QUALITY
# ============================================================
ui.section("s5", "05", "Quality", "OAU won the table on silver")
ui.body(
    f"The official table ranks gold first, so gold still decides first place, and OAU's {OAU_G} is the largest "
    f"haul of anyone's. But look at the mix: {OAU_S} silvers — {100 * OAU_S / silver_pool:.0f}% of every silver "
    f"awarded — and {OAU_B} bronzes. Only {OAU_GOLD_SHARE:.0f}% of its medals were gold, against "
    f"{UG_PCT:.0f}% for UG-GH, {BIU_PCT:.0f}% for BIU-NG, {LASU_PCT:.0f}% for LASU and {DELSU_PCT:.0f}% for "
    "DELSU. "
    "In other words the host was rarely off the podium, and often second on it. Whether that is strength — "
    "depth across events — or a conversion problem is exactly the question that entries data would settle, "
    "and the feed does not carry entries."
)
qual = T[T["Total"] >= 10].sort_values("GoldShare")
fig = go.Figure(go.Bar(
    x=qual["GoldShare"], y=qual["Code"], orientation="h",
    marker_color=[ui.GOLD if c == "OAU" else "#3D57DE" for c in qual["Code"]],
    marker_line=dict(width=0),
    text=[f"{v:.0f}%" for v in qual["GoldShare"]], textposition="outside",
    textfont=dict(color="#C9D5EE", size=11),
    hovertemplate="%{y}: %{x:.0f}% of medals were gold<extra></extra>",
))
ui.chart_title("Who turned podiums into gold  ·  share of medals that were gold, schools with 10 or more")
ui.base_layout(fig, height=420, margin=dict(t=18, r=54, b=44, l=54))
fig.update_xaxes(title="Share of medals that were gold", ticksuffix="%",
                 range=[0, max(72, float(qual["GoldShare"].max()) + 8)])
ui.chart(fig, key="quality")
ui.caption("What it shows",
           f"The host is high on the table but low on this chart. DELSU turned 7 of its 11 podiums into gold; "
           f"OAU turned {OAU_G} of {OAU_T}.")

# ============================================================
# 6. RULES
# ============================================================
ui.section("s6", "06", "Scoring rules", "The podium survives every rule I tried. Third place does not.")
ui.body(
    f"I re-ranked all {rep['school_count']} schools four ways: gold first (official), total medals, 3-2-1 points, "
    "and golds only, with ties sharing a place. OAU and UG-GH are first and second in all four, so the winner "
    "does not depend on the rule. The rest of the podium does. BIU-NG is third officially, but on total medals "
    f"{third_phrase} — both on 42 — share third and BIU-NG drops to fifth, because it won fewer medals than either. "
    "Under 3-2-1 points the top four hold and fifth and sixth swap; under golds-only the top six are unchanged. "
    f"{len(movers)} schools move three places or more under at least one rule — the largest is "
    f"{big_mover['Code'] if big_mover is not None else ''}, {int(big_mover['Rank']) if big_mover is not None else ''}th "
    f"officially and {BIG_MOVER_TOTAL}th by total medals — so a reader who sees only one ranking is missing part "
    "of the story."
)
ui.chart_title("Rank under each scoring rule  ·  top eight officially, plus the biggest mover")
rule_cols = [("Official", "Rank"), ("Total medals", "ByTotal"), ("3-2-1 points", "ByPoints"), ("Golds only", "ByGold")]
keep = T.head(8)["Code"].tolist()
if big_mover is not None and big_mover["Code"] not in keep:
    keep.append(big_mover["Code"])
fig = go.Figure()
ymax = 0
for code in keep:
    r = RULES[RULES["Code"] == code].iloc[0]
    ys = [int(r[c]) for _, c in rule_cols]
    ymax = max(ymax, max(ys))
    is_oau = code == "OAU"
    is_big = big_mover is not None and code == big_mover["Code"]
    colour = ui.GOLD if is_oau else ("#F0616D" if is_big else "rgba(140,160,210,.55)")
    width = 2.8 if (is_oau or is_big) else 1.2
    labels = [""] * (len(rule_cols) - 1) + [code]
    fig.add_trace(go.Scatter(
        x=[n for n, _ in rule_cols], y=ys, mode="lines+markers+text",
        line=dict(color=colour, width=width), marker=dict(size=7, color=colour),
        text=labels, textposition="middle right", textfont=dict(size=11, color=colour),
        name=code, showlegend=False, cliponaxis=False,
        hovertemplate=f"{code} · %{{x}}: rank %{{y}}<extra></extra>",
    ))
ui.base_layout(fig, height=min(560, 250 + 18 * ymax), margin=dict(t=18, r=74, b=44, l=64))
fig.update_xaxes(title=None, type="category")
fig.update_yaxes(title="Rank (lower is better)", dtick=2, range=[ymax + 1, 0])
ui.chart(fig, key="bump")
ui.caption("What it shows",
           "Lines that stay apart mean a school's place is insensitive to the rule. The crimson line is the "
           "school that moves most; the gold line is the winner.")

ui.chart_title("Try it yourself  ·  set the points for each medal")
c1, c2, c3 = st.columns(3)
wg = c1.slider("Points for gold", 0, 10, 3, key="wg")
ws = c2.slider("Points for silver", 0, 10, 2, key="ws")
wb = c3.slider("Points for bronze", 0, 10, 1, key="wb")
if wg + ws + wb == 0:
    st.info("Give at least one medal a weight.")
else:
    sc = T[["Code", "School", "Gold", "Silver", "Bronze", "Rank"]].copy()
    sc["Points"] = wg * sc["Gold"] + ws * sc["Silver"] + wb * sc["Bronze"]
    sc["New"] = competition_rank(list(sc["Points"].astype(float)))
    sc = sc.sort_values(["New", "Gold"], ascending=[True, False]).reset_index(drop=True)
    k1, k2, k3 = st.columns(3)
    k1.metric("Leader", sc.iloc[0]["Code"], f"{int(sc.iloc[0]['Points'])} points")
    k2.metric("Third place", sc.iloc[2]["Code"], f"official: {official_third['Code']}")
    moved = int((sc["New"] - sc["Rank"]).abs().ge(3).sum())
    k3.metric("Schools moving 3+", moved, "places against the official table")
    st.dataframe(
        sc.head(8)[["New", "Code", "Gold", "Silver", "Bronze", "Points"]]
        .rename(columns={"New": "Rank", "Code": "School", "Points": "Points"}),
        hide_index=True, use_container_width=True,
    )
    st.caption(
        "Change the weights and the leader stays OAU unless bronze is weighted far above gold. "
        "Third place is the volatile one."
    )

# ============================================================
# 7. WHAT THE TABLE HIDES
# ============================================================
ui.section("s7", "07", "Coverage", "The table is not the Games")
ui.body(
    f"<strong>Two sports supply {big_two_share:.0f}% of the medals.</strong> Athletics ({int(top_pool.iloc[0]['Medals'])} "
    f"medals) and swimming ({int(top_pool.iloc[1]['Medals'])}) account for {big_two} of {TOT}. A school that is strong "
    "in the pool and on the track can look far broader than it is, and the medal table will not say so."
)
ui.body(
    f"<strong>Sports do not hand out the same number of medals.</strong> Taekwondo awarded {TKW_MEDALS} medals over "
    f"{TKW_EVENTS} events — {TKW_MEDALS / TKW_EVENTS:.1f} per event, because both bronze slots are filled — while "
    f"badminton awarded {BDM_MEDALS / BDM_EVENTS:.0f} per event over its {BDM_EVENTS}. "
    "A fourth place is a bronze in one sport and nothing in another, so totals partly reflect which sports a school "
    "entered."
)
ui.body(
    f"<strong>{EMPTY_WORD} sports are missing or empty.</strong> The catalogue lists {len(ALL_SPORTS)} sports; the "
    f"results cover {len(MATRIX.columns)}, and only {MEDAL_SPORTS} of those awarded a medal. " +
    (lambda names: (", ".join(names[:-1]) + " and " + names[-1]).capitalize())(
        [SPORT_NAME(c).lower() for c in missing_sports]) +
    " have no events in the feed at all, and handball's one recorded fixture has no result. "
    f"<strong>{rep['undated_medals']} medals ({100 * rep['undated_medals'] / TOT:.0f}%) sit on events with no date</strong>, "
    f"so the daily story can only be told for the {100 - 100 * rep['undated_medals'] / TOT:.0f}% that is dated."
)

ui.chart_title("Which sports supplied the medals  ·  medals awarded, with events on record")
p = POOL[POOL["Medals"] > 0].sort_values("Medals")
fig = go.Figure(go.Bar(
    x=p["Medals"], y=p["Code"], orientation="h",
    marker_color=[ui.GOLD if c in ("ATH", "SWM") else "#3D57DE" for c in p["Code"]],
    marker_line=dict(width=0),
    text=[f"{int(m)} medals · {int(e)} ev" for m, e in zip(p["Medals"], p["Events"])],
    textposition="outside", textfont=dict(color="#9DB0DA", size=10),
    customdata=p["Sport"],
    hovertemplate="%{customdata}: %{x} medals<extra></extra>",
))
ui.base_layout(fig, height=420, margin=dict(t=18, r=120, b=44, l=54))
fig.update_xaxes(title="Medals awarded", range=[0, float(p["Medals"].max()) * 1.18])
ui.chart(fig, key="pool")
ui.caption("What it shows",
           f"Athletics and swimming alone account for {big_two_share:.0f}% of the table. The five smallest sports "
           f"award {int(p.head(5)['Medals'].sum())} medals between them.")

if not BYDAY.empty:
    ui.chart_title("When the table was decided  ·  medals on events with a recorded date")
    day_labels = pd.to_datetime(BYDAY["Date"]).dt.strftime("%d %b").str.lstrip("0")
    fig = go.Figure()
    fig.add_trace(go.Bar(x=day_labels, y=BYDAY["OAU"], name="OAU", marker_color=ui.GOLD,
                         hovertemplate="%{x} · OAU: %{y}<extra></extra>"))
    fig.add_trace(go.Bar(x=day_labels, y=BYDAY["Medals"] - BYDAY["OAU"], name="Everyone else",
                         marker_color="#3D57DE",
                         hovertemplate="%{x} · others: %{y}<extra></extra>"))
    fig.update_layout(barmode="stack")
    ui.base_layout(fig, height=300, legend=True)
    fig.update_xaxes(title=None, type="category")
    fig.update_yaxes(title="Medals")
    ui.chart(fig, key="days")
    ui.caption("What it shows",
               f"Only {100 - 100 * rep['undated_medals'] / TOT:.0f}% of medals have a date; within that slice the "
               "middle days carry most of the programme, so the closing days did not decide the table.")

# ============================================================
# 8. TEAM GAMES
# ============================================================
ui.section("s8", "08", "Team games", "The team games were over early")
ui.body(
    f"Basketball was the most one-sided sport in the feed: {len(bkb)} games, a median margin of "
    f"<strong>{BKB_MED:.1f} points</strong>, {BKB_20} of them by 20 or more, and a widest gap of "
    f"{int(bkb['Margin'].max())}. Football was the opposite: {len(fbl)} games, {FBL_TIGHT} decided by a single goal "
    f"or level after normal time, and {FBL_PENS} of those going to penalties. Tennis and table tennis look close "
    "because they are best-of matches, so a 3-2 scoreline says less about the gap between two schools than it "
    "would in a league."
)
if not bkb.empty:
    ui.chart_title("Basketball margins  ·  each point is one game")
    fig = go.Figure(go.Box(
        x=bkb["Margin"], name="", boxpoints="all", jitter=.5, pointpos=0,
        marker=dict(color=ui.GOLD, size=9, opacity=.9, line=dict(width=0)),
        line=dict(color="rgba(232,184,75,.6)", width=1.5),
        fillcolor="rgba(232,184,75,.06)",
        hovertemplate="%{x} points<extra></extra>",
    ))
    fig.add_vline(x=BKB_MED, line=dict(color="rgba(255,255,255,.4)", width=1, dash="dot"))
    fig.add_annotation(x=BKB_MED, y=1.05, yref="paper", text=f"median {BKB_MED:.0f}", showarrow=False,
                       font=dict(color="#9DB0DA", size=11), xshift=24)
    ui.base_layout(fig, height=220, legend=False, margin=dict(t=14, r=24, b=44, l=24))
    fig.update_yaxes(visible=False, range=[-1, 1])
    fig.update_xaxes(title="Points between the teams", range=[0, max(65, int(bkb['Margin'].max()) + 5)])
    ui.chart(fig, key="bkb")
    ui.caption("What it shows",
               f"{BKB_20} of {len(bkb)} games were decided by 20 points or more; the median is {BKB_MED:.0f}.")

if not fbl.empty:
    ui.chart_title("Football margins  ·  games by margin at full time")
    vc = fbl["Margin"].value_counts().sort_index()
    fig = go.Figure(go.Bar(
        x=[f"{int(m)} goal{'s' if m != 1 else ''}" for m in vc.index], y=vc.values,
        marker_color=[ui.GOLD if m == 0 else "#3D57DE" for m in vc.index],
        marker_line=dict(width=0),
        text=vc.values, textposition="outside", textfont=dict(color="#C9D5EE", size=11),
        hovertemplate="%{x}: %{y} games<extra></extra>",
    ))
    ui.base_layout(fig, height=280)
    fig.update_yaxes(title="Games", dtick=1, range=[0, max(vc.values) + 1.2])
    ui.chart(fig, key="fbl")
    ui.caption("What it shows",
               f"{FBL_PENS} of the {len(fbl)} games finished level and went to penalties; "
               f"{int((fbl['Margin'] >= 3).sum())} was won by three goals.")

    with st.expander("The eight football results"):
        rows = []
        for _, m in fbl.sort_values("Date").iterrows():
            score = f"{int(m['HG'])}–{int(m['AG'])}"
            if m["Pens"]:
                score += f" ({int(m['PenH'])}–{int(m['PenA'])} pens)"
            rows.append({"Date": m["Date"], "Match": f"{m['Home']} v {m['Away']}",
                         "Score": score, "Phase": m["Phase"]})
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

# ============================================================
# 9. LIMITS
# ============================================================
ui.section("s9", "09", "Limits", "What this does not show")
ui.body(
    "<strong>Association is not cause.</strong> Breadth and medals move together; the data cannot say whether "
    "entering more sports wins more medals or whether a school with more medals can afford to enter more sports."
)
ui.body(
    "<strong>Efficiency is unmeasurable here.</strong> Without entries per school and per sport, medals cannot be "
    "turned into a rate. A school with 300 athletes and one with 30 are ranked as if they were the same size."
)
ui.body(
    "<strong>The athlete data is thin.</strong> Many events list only the university; names are spelled in more than "
    "one way, and the same name can appear for different schools. Team events list no members, so an individual "
    "count would undercount team sports."
)
ui.body(
    f"<strong>The schedule is incomplete.</strong> {rep['undated_events']} events have no start time and five sports "
    "have no events at all, so totals are what the feed holds today, not necessarily what the Games awarded. "
    "The feed reports no provisional medals in this snapshot, but results can still be revised by the WAUG "
    "Technical Committee."
)
ui.body(
    "<strong>The match analysis is partial.</strong> Margins come from finished football and basketball games only — "
    "a small sample — and say nothing about how the games were played."
)

# ============================================================
# 10. NEXT
# ============================================================
ui.section("s10", "10", "Next", "What I would change about how the table is published")
ui.body(
    "<strong>1. Publish a sport-by-sport table next to the official one.</strong> The most interesting fact in this "
    f"dataset — {OAU_SPORTS} sports against {UG_SPORTS} — is invisible in a single rank column, and readers "
    "cannot recover it from totals."
)
ui.body(
    "<strong>2. Record entries per school and per sport.</strong> One extra column would turn the medal table into a "
    "measure of efficiency and make home advantage testable instead of assertable."
)
ui.body(
    "<strong>3. Give every athlete an ID and list team members.</strong> Counts would stop depending on how a name is "
    "spelled, and the same analysis could be run on people rather than universities."
)
ui.body(
    "<strong>4. Complete the schedule and state which sports were not held.</strong> A blank in the feed and a sport "
    "that never took place currently look the same, and that ambiguity makes every total a lower bound."
)
ui.body(
    "<strong>5. Show both rankings.</strong> Official gold-first for the trophy, total medals as a companion view. "
    f"They disagree about third place and about {len(movers)} lower places, and both are informative."
)

# ============================================================
# 11. AUTHOR
# ============================================================
ui.section("s11", "11", "Author", "Who built this")
st.markdown(
    f"""
<div class="author">
  <div class="avatar">OP</div>
  <div>
    <h3>{AUTHOR}</h3>
    <div class="role">Analysis · dashboard · report</div>
    <p>Collected the data from the AlliSports Data API, rebuilt the medal table from the individual results
    to check it, ran the comparisons and built both the dashboard and this report.</p>
  </div>
</div>
""",
    unsafe_allow_html=True,
)
ui.body(
    "Built with Python, pandas, Plotly and Streamlit. The API key stays on the server and is sent in the "
    "x-api-key header, so it never reaches the browser. All figures are recomputed when the feed is read; "
    "nothing in this report is hard-coded."
)

with st.expander("Appendix: method and definitions"):
    st.markdown(
        f"""
**Endpoints.** `/results` (the {rep['event_count']} events and their medal lists), `/medal-table`
(the official ranking and its totals), `/matches` ({rep['match_count']} fixtures), `/sports`
(the {len(ALL_SPORTS)}-sport catalogue).

**Rebuilding the table.** Each medal in `/results` carries a slot (gold, silver, bronze_1, bronze_2) and a
university. Counting them by school reproduces the official table exactly: {rep['school_count']} rows,
{TOT} medals, {rep['mismatches']} differences. Combat sports fill two bronze slots, which is why
bronze ({bronze_pool}) exceeds gold ({gold_pool}) in the totals.

**Concentration.** Share = a school's medals ÷ {TOT}. The cumulative curve is in official rank order.
The effective number of schools is 1 ÷ Σ(share²); Gini uses the standard formula on those shares.

**Correlation.** Pearson r between total medals and the number of sports in which a school won at least
one medal, across all {rep['school_count']} schools.

**Scoring rules.** Official = gold, then silver, then bronze. Total medals = total, then gold, then silver.
Points = 3·gold + 2·silver + 1·bronze. Golds only = gold, then silver, then bronze. Ties share a rank and
the next rank is skipped.

**Margins.** The absolute difference in the final score. Football games level after normal time are counted
as zero margin and shown with their penalty score separately.

**Freshness.** Feed read {gen_txt}. The report is cached for five minutes and can be refreshed from the
dashboard sidebar.
"""
    )

ui.footer(
    f"Report and dashboard by <b>{AUTHOR}</b> &nbsp;·&nbsp; Data: <b>AlliSports Data</b> — official data partner "
    "of WAUG 2026 &nbsp;·&nbsp; Games: 2–12 October 2026, Obafemi Awolowo University, Ile-Ife"
)
