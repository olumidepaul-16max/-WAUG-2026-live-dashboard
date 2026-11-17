"""
Presentation helpers for the report, data and team pages.

The report is meant to read like a printed briefing: a serif headline, a
short summary, numbered sections, and charts with a one-line reading note.
"""

import streamlit as st

GOLD = "#E8B84B"
INK = "#EAF0FF"
MUTED = "#9DB0DA"

BASE_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Source+Serif+4:opsz,wght@8..60,400;8..60,600;8..60,700&display=swap');

:root {
  --gold:#E8B84B; --gold-dim:#C4941A; --ink:#EAF0FF; --muted:#9DB0DA;
  --line:rgba(232,184,75,.18); --panel:rgba(255,255,255,.045);
  --navy:#0A1533;
}

html, body { background:#060F29; }
[data-testid="stAppViewContainer"] {
  background:
    radial-gradient(1100px 540px at 10% -12%, rgba(38,48,189,.38), transparent 62%),
    radial-gradient(900px 520px at 104% -6%, rgba(232,184,75,.10), transparent 58%),
    #060F29;
  color: var(--ink);
}
[data-testid="stHeader"], [data-testid="stToolbar"] { background: transparent; }
.block-container { max-width: 1140px; padding-top: 2.0rem; padding-bottom: 4rem; }

body, p, li, span, div, label, input, button, [data-testid="stMarkdownContainer"] {
  font-family: 'Inter', system-ui, -apple-system, sans-serif;
}
[data-testid="stMarkdownContainer"] p { color: var(--ink); }

h1, h2, h3, h4 { font-family:'Source Serif 4', Georgia, 'Times New Roman', serif !important; }

/* ---------- masthead ---------- */
.eb {
  font-size:.715rem; font-weight:800; letter-spacing:2.1px; text-transform:uppercase;
  color:var(--gold); margin: 0 0 18px;
}
.display {
  font-family:'Source Serif 4', Georgia, serif; font-size:3.05rem; line-height:1.08;
  font-weight:700; color:#fff; margin:0 0 20px; letter-spacing:-1.1px; max-width: 24ch;
  text-wrap: balance;
}
.lede {
  font-size:1.11rem; line-height:1.72; color:#D7E0F5; margin:0 0 26px; max-width: 78ch;
}
.lede strong, .body strong { color:#fff; }

/* ---------- kpi cards ---------- */
.kpis { display:grid; grid-template-columns:repeat(3,1fr); gap:14px; margin: 6px 0 22px; }
.kpi {
  background: linear-gradient(160deg, rgba(255,255,255,.075), rgba(255,255,255,.028));
  border:1px solid rgba(255,255,255,.10); border-top:2px solid var(--gold);
  border-radius:12px; padding:18px 20px 16px;
}
.kpi .n { font-family:'Source Serif 4', Georgia, serif; font-size:2.15rem; font-weight:700;
          color:var(--gold); line-height:1; letter-spacing:-.5px; }
.kpi .l { font-size:.865rem; color:#C9D5EE; line-height:1.48; margin-top:10px; }
.kpi .tag { font-size:.63rem; font-weight:800; letter-spacing:1.5px; text-transform:uppercase;
            color:#7E92C2; margin-top:12px; }

/* ---------- byline ---------- */
.byline { font-size:.8rem; color:#8798C4; margin: 2px 0 0; }
.byline b { color:#C9D5EE; font-weight:600; }

/* ---------- section furniture ---------- */
.sec { margin-top: 62px; }
.sec-no {
  font-size:.7rem; font-weight:800; letter-spacing:2px; text-transform:uppercase;
  color:var(--gold); margin-bottom:10px;
}
h2.sec-h {
  font-family:'Source Serif 4', Georgia, serif; font-size:1.92rem; font-weight:700;
  color:#fff; line-height:1.24; margin:0 0 14px; letter-spacing:-.4px; max-width: 30ch;
}
.body { font-size:1.015rem; line-height:1.78; color:#D3DDF3; margin:0 0 16px; max-width: 84ch; }
.body em { color:#C9D5EE; }
.rule { border:none; border-top:1px solid var(--line); margin: 46px 0 0; }

/* ---------- summary block ---------- */
.short {
  background: linear-gradient(150deg, rgba(38,48,189,.20), rgba(255,255,255,.03));
  border:1px solid rgba(255,255,255,.10); border-left:3px solid var(--gold);
  border-radius:12px; padding: 22px 26px 12px; margin: 26px 0 8px;
}
.short h3 { font-size:1.02rem; margin:0 0 14px; color:#fff; font-family:'Inter',sans-serif !important;
            font-weight:700; letter-spacing:.2px; }
.short ul { list-style:none; padding:0; margin:0; }
.short li { font-size:.925rem; line-height:1.62; color:#CBD6EF; padding: 0 0 13px 0; display:flex; gap:11px; }
.short li .tag {
  flex:0 0 auto; font-size:.6rem; font-weight:800; letter-spacing:1.2px; color:#7E92C2;
  text-transform:uppercase; padding-top:4px; min-width:86px;
}

/* ---------- chart captions ---------- */
.cap {
  font-size:.84rem; line-height:1.6; color:#A9B8DA; margin:-6px 0 20px;
  padding: 11px 0 0 14px; border-left:2px solid rgba(232,184,75,.55);
}
.cap b { color:var(--gold); font-size:.66rem; letter-spacing:1.5px; text-transform:uppercase;
         display:block; margin-bottom:5px; font-weight:800; }
.chart-title { font-size:.7rem; font-weight:800; letter-spacing:1.7px; text-transform:uppercase;
               color:#8DA0CC; margin: 26px 0 2px; }

/* ---------- misc ---------- */
.pill {
  display:inline-flex; align-items:center; gap:7px; border:1px solid var(--line);
  border-radius:999px; padding:4px 12px; font-size:.72rem; font-weight:700; color:#C9D5EE;
  background:rgba(232,184,75,.06);
}
.quote {
  font-family:'Source Serif 4', Georgia, serif; font-size:1.34rem; line-height:1.5;
  color:#fff; border-left:2px solid var(--gold); padding: 4px 0 4px 22px; margin: 26px 0;
}
.foot { text-align:center; color:#7E92C2; font-size:.78rem; padding:26px 0 6px;
        border-top:1px solid var(--line); margin-top:56px; }
.foot b { color:var(--gold); }

/* ---------- author card ---------- */
.author {
  display:flex; gap:18px; align-items:flex-start;
  background: linear-gradient(150deg, rgba(255,255,255,.065), rgba(255,255,255,.022));
  border:1px solid rgba(255,255,255,.10); border-left:3px solid var(--gold);
  border-radius:12px; padding:20px 22px; margin: 6px 0 14px;
}
.avatar {
  flex:0 0 auto; width:56px; height:56px; border-radius:50%; background:var(--gold);
  color:#16204A; display:flex; align-items:center; justify-content:center;
  font-weight:800; font-size:1.08rem; letter-spacing:.5px;
}
.author h3 { margin:0; font-family:'Source Serif 4', Georgia, serif !important;
             font-size:1.22rem; color:#fff; font-weight:700; }
.author .role { color:var(--gold); font-size:.72rem; font-weight:800; letter-spacing:1.3px;
                text-transform:uppercase; margin-top:4px; }
.author p { margin:8px 0 0; color:#A9B8DA; font-size:.875rem; line-height:1.6; }

/* ---------- sidebar ---------- */
[data-testid="stSidebar"] {
  background:#081226; border-right:1px solid rgba(232,184,75,.14);
}
[data-testid="stSidebar"] * { font-family:'Inter', sans-serif; }
.toc { margin: 4px 0 10px; }
.toc a {
  display:block; color:#A9B8DA !important; text-decoration:none; font-size:.815rem;
  padding:5px 0 5px 11px; border-left:2px solid transparent; line-height:1.4;
}
.toc a:hover { color:#fff !important; border-left-color:var(--gold); background:rgba(232,184,75,.05); }
.toc-cap { font-size:.64rem; font-weight:800; letter-spacing:1.6px; text-transform:uppercase;
           color:var(--gold); margin: 8px 0 6px; }

/* ---------- buttons ---------- */
.btn-row { display:flex; gap:10px; flex-wrap:wrap; margin: 4px 0 10px; }
a.btn {
  display:inline-flex; align-items:center; justify-content:center; gap:8px; text-decoration:none;
  background:var(--gold); color:#1B1608 !important; font-weight:800; font-size:.82rem;
  padding:10px 16px; border-radius:8px; border:1px solid var(--gold);
  white-space:nowrap; min-height:44px; margin-top:-4px;
}
a.btn:hover { background:#F1C862; }
a.btn.ghost { background:transparent; color:#E6EDFF !important; border:1px solid rgba(230,237,255,.35); }
a.btn.ghost:hover { border-color:var(--gold); color:var(--gold) !important; }

/* Streamlit widgets, dressed for the dark page */
[data-testid="stPageLink"] a {
  display:inline-flex; align-items:center; justify-content:center; gap:8px;
  background:transparent; border:1px solid rgba(230,237,255,.35); border-radius:8px;
  padding:10px 14px; color:#E6EDFF !important; font-weight:700; font-size:.82rem;
  text-decoration:none; white-space:nowrap; min-height:44px; line-height:1.2;
}
[data-testid="stPageLink"] a:hover { border-color:var(--gold); }
[data-testid="stDownloadButton"] button {
  background:transparent !important; border:1px solid rgba(230,237,255,.35) !important;
  color:#E6EDFF !important; font-weight:700 !important; font-size:.86rem !important;
  border-radius:8px !important; padding:10px 18px !important;
}
[data-testid="stDownloadButton"] button:hover { border-color:var(--gold) !important; color:var(--gold) !important; }
[data-testid="stExpander"] details {
  background:rgba(255,255,255,.028); border:1px solid rgba(255,255,255,.10);
  border-radius:10px;
}
[data-testid="stExpander"] summary { color:#C9D5EE; font-size:.84rem; font-weight:600; }
[data-testid="stExpander"] summary:hover { color:var(--gold); }
[data-testid="stDataFrame"] { border-radius:10px; border:1px solid rgba(255,255,255,.10); overflow:hidden; }
[data-testid="stMetric"] { background:rgba(255,255,255,.04); border:1px solid rgba(255,255,255,.09);
  border-left:3px solid var(--gold); border-radius:10px; padding:14px 16px; }
[data-testid="stMetricValue"] { color:#fff !important; font-weight:800 !important; }
[data-testid="stMetricLabel"] { color:#9DB0DA !important; font-weight:700 !important;
  font-size:.74rem !important; text-transform:uppercase; letter-spacing:.7px; }
hr { border-color: rgba(255,255,255,.10) !important; }
[data-testid="stAlert"] { background:rgba(255,255,255,.04); border-radius:10px; }

@media (max-width: 760px) {
  .display { font-size:2.1rem; }
  .kpis { grid-template-columns:1fr; }
  .block-container { padding-top: 1.2rem; }
}
</style>
"""


def page_css():
    st.markdown(BASE_CSS, unsafe_allow_html=True)


def toc(items):
    """Sidebar table of contents: list of (anchor, label)."""
    links = "".join(f'<a href="#{a}">{l}</a>' for a, l in items)
    st.sidebar.markdown(
        f'<div class="toc-cap">On this page</div><div class="toc">{links}</div>',
        unsafe_allow_html=True,
    )


def eyebrow(text):
    st.markdown(f'<div class="eb">{text}</div>', unsafe_allow_html=True)


def display(text):
    st.markdown(f'<div class="display">{text}</div>', unsafe_allow_html=True)


def lede(text):
    st.markdown(f'<p class="lede">{text}</p>', unsafe_allow_html=True)


def kpis(cards):
    """cards: list of (number, label, tag)."""
    inner = "".join(
        f'<div class="kpi"><div class="n">{n}</div><div class="l">{l}</div>'
        f'<div class="tag">{t}</div></div>'
        for n, l, t in cards
    )
    st.markdown(f'<div class="kpis">{inner}</div>', unsafe_allow_html=True)


def byline(text):
    st.markdown(f'<p class="byline">{text}</p>', unsafe_allow_html=True)


def section(anchor, number, kicker, heading):
    st.markdown(
        f'<div class="sec" id="{anchor}"><div class="sec-no">{number} &nbsp;·&nbsp; {kicker}</div>'
        f'<h2 class="sec-h">{heading}</h2></div>',
        unsafe_allow_html=True,
    )


def body(text):
    st.markdown(f'<p class="body">{text}</p>', unsafe_allow_html=True)


def summary(items):
    """items: list of (tag, text)."""
    lis = "".join(f'<li><span class="tag">{t}</span><span>{x}</span></li>' for t, x in items)
    st.markdown(
        f'<div class="short"><h3>In short</h3><ul>{lis}</ul></div>', unsafe_allow_html=True
    )


def chart_title(text):
    st.markdown(f'<div class="chart-title">{text}</div>', unsafe_allow_html=True)


def caption(label, text):
    st.markdown(f'<div class="cap"><b>{label}</b>{text}</div>', unsafe_allow_html=True)


def chart(fig, key=None):
    st.plotly_chart(
        fig, use_container_width=True, key=key,
        config={"displayModeBar": False, "responsive": True},
    )


def rule():
    st.markdown('<hr class="rule">', unsafe_allow_html=True)


def footer(text):
    st.markdown(f'<div class="foot">{text}</div>', unsafe_allow_html=True)


# ---------- chart styling ----------
FONT = "Inter, system-ui, sans-serif"
SERIF = "Source Serif 4, Georgia, serif"


def base_layout(fig, height=340, legend=False, margin=None):
    fig.update_layout(
        height=height,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT, color="#A9B8DA", size=12),
        margin=margin or dict(t=18, r=18, b=46, l=54),
        showlegend=legend,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0,
                    bgcolor="rgba(0,0,0,0)", font=dict(color="#A9B8DA", size=11)),
        hoverlabel=dict(bgcolor="#12234E", font=dict(color="#FFFFFF", family=FONT), bordercolor="rgba(232,184,75,.6)"),
        bargap=0.28,
    )
    fig.update_xaxes(gridcolor="rgba(255,255,255,.055)", linecolor="rgba(255,255,255,.12)",
                     tickfont=dict(color="#93A6D0"), zeroline=False,
                     title_font=dict(color="#8DA0CC", size=11))
    fig.update_yaxes(gridcolor="rgba(255,255,255,.055)", linecolor="rgba(255,255,255,.12)",
                     tickfont=dict(color="#93A6D0"), zeroline=False,
                     title_font=dict(color="#8DA0CC", size=11))
    fig.update_annotations(font=dict(family=FONT, color="#C9D5EE", size=11))
    return fig
