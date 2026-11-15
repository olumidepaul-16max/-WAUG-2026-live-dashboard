# WAUG 2026 Live Dashboard

Live results, standings and medal tables for the **West African Universities Games 2026**
at Obafemi Awolowo University, Ile-Ife.

Built with Streamlit on top of the [AlliSports Data](https://data.allimediahub.com) feed, so
everything on the page updates straight from the official results — no hardcoded numbers.

## Covered sports

All 20 sports in the feed: Athletics, Badminton, Basketball, Boxing, Chess, Esports,
Football, Handball, Hockey, Judo, Rugby, Scrabble, Squash, Swimming, Tennis, Taekwondo,
Table tennis, Volleyball, Weightlifting and Wrestling.

## What's inside

**Live & Fixtures** — in-play matches, full fixture list, and a write-up for any finished
match (goals per half, cards, who scored first, comebacks, lead changes).

**Results & Medals** — gold, silver and bronze for every event, plus the full schedule.

**Standings** — official group tables where the feed publishes them, otherwise a league table
computed from the finished matches. Plus the medals each university won in that sport.

**Statistics** — goals by team, biggest winning margins, and matches played across all sports.

## Running it locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

Then open `http://localhost:8501`.

## Putting it online

Push the folder to a public GitHub repo, then create the app on
[share.streamlit.io](https://share.streamlit.io):

- Repository — `your-user/waug-2026-live-dashboard`
- Branch — `main`
- Main file path — `app.py`

Add your feed key under **Settings → Secrets** before deploying:

```toml
ALLISPORTS_KEY = "asd_your_key"
```

Streamlit Cloud will build it and hand you a public link.

## Layout

```
waug-api-dashboard/
├── .streamlit/
│   ├── config.toml        # theme
│   └── secrets.toml       # feed key (kept out of git)
├── app.py
├── requirements.txt
├── .gitignore
└── README.md
```

## Notes

- The feed key lives on the server and goes out as an `x-api-key` header. It never reaches
  the browser, and `secrets.toml` is git-ignored.
- Responses are cached for 45–90 seconds to stay inside the feed's rate limit
  (60 requests/minute, 10,000/day per key).
- Each sport has its own link, e.g. `?sport=FBL` for football, `?sport=SWM` for swimming.

---

Data: **AlliSports Data** — official data partner of WAUG 2026. Please credit them
wherever you publish this.
