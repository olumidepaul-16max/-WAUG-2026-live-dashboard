# WAUG 2026 Live Dashboard — API Edition

A **Streamlit** dashboard for the **West African Universities Games (WAUG) 2026)** hosted at
**Obafemi Awolowo University (OAU), Ile-Ife, Nigeria**, driven by the live
**AlliSports Data** feed (`https://data.allimediahub.com/api`).

Unlike the static edition, every number on this dashboard comes from the official feed:
the medal table, results, event schedule, match scores (including live ones), group
tables and per-match analytics.

---

## What the dashboard shows

| Tab | Contents |
|-----|----------|
| 🔴 **Live & Fixtures** | In-play matches, full fixture list, match status breakdown, and **narrative match analytics** (goals by half, cards, first scorer, comebacks, lead changes) |
| 🏅 **Results & Medals** | Podium winners per event (gold / silver / bronze), event status, full schedule |
| 📊 **Standings** | Official **group tables** (P/W/D/L, GF, GA, GD, points, qualification) and knockout brackets, plus medals won per university in that sport |
| 📈 **Statistics** | Goals by team, biggest winning margins, completed matches across all sports |

Sidebar extras: overall medal table, live feed status, and a manual refresh.

---

## Deep links

Each sport has its own shareable URL. The selected sport is written to the query string, so
you can link straight to a page:

```
https://your-app.streamlit.app/?sport=FBL   → Football
https://your-app.streamlit.app/?sport=BKB   → Basketball
https://your-app.streamlit.app/?sport=SWM   → Swimming
https://your-app.streamlit.app/?sport=TTE   → Table tennis
```

Sport codes: `ATH` `BDM` `BKB` `BOX` `CHS` `ESP` `FBL` `HBL` `HKY` `JUD` `RUG` `SCR`
`SQU` `SWM` `TEN` `TKW` `TTE` `VVO` `WLF` `WRE`

---

## Sports available

All 20 sports in the feed: Athletics ⚃, Badminton 🏸, Basketball 🏀, Boxing 🥊, Chess ♟️,
Esports 🎮, Football ⚽, Handball 🤾, Hockey 🏑, Judo 🥋, Rugby 🏉, Scrabble 🔤,
Squash 🎾, Swimming 🏊, Tennis 🎾, Taekwondo 🥋, Table tennis 🏓, Volleyball 🏐,
Weightlifting 🏋️, Wrestling 🤼

---

## Project structure

```
waug-api-dashboard/
├── .streamlit/
│   ├── config.toml        # Custom navy + gold theme
│   └── secrets.toml       # LOCAL ONLY — API key (git-ignored)
├── app.py                 # Dashboard
├── requirements.txt
├── .gitignore
└── README.md
```

---

## API key handling

The key is **never sent to the browser**. It lives on the server (your machine when running
locally, or Streamlit Cloud's server when deployed) and is attached to every request as the
`x-api-key` header.

Resolution order:

1. `st.secrets["ALLISPORTS_KEY"]` — Streamlit Cloud secrets / local `.streamlit/secrets.toml`
2. `ALLISPORTS_KEY` environment variable
3. The `FALLBACK_KEY` constant inside `app.py`

To set it on **Streamlit Cloud**: go to your app → **Settings** → **Secrets** and add:

```toml
ALLISPORTS_KEY = "asd_..."
```

To set it **locally**, create `.streamlit/secrets.toml`:

```toml
ALLISPORTS_KEY = "asd_..."
```

> `.streamlit/secrets.toml` is listed in `.gitignore` so it is never pushed to GitHub.

---

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

Open `http://localhost:8501`.

---

## Deploy to Streamlit Cloud

1. Create a **public** GitHub repository and push this folder.
2. Go to [share.streamlit.io](https://share.streamlit.io) → **Create app**
   - Repository: `your-user/waug-api-dashboard`
   - Branch: `main`
   - Main file path: `app.py`
3. Add the secret: **Settings → Secrets → `ALLISPORTS_KEY`**
4. **Deploy**

---

## Rate limits

The feed allows **60 requests/minute** and **10,000/day** per key. This dashboard caches
responses (45–90 s TTL) and only requests group tables and match analytics on demand, so it
stays comfortably inside the limit.

---

## Credit

Data: **AlliSports Data** — official data partner of WAUG 2026.
Please credit "Data: AlliSports Data" wherever you show this feed.
