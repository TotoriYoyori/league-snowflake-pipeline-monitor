# Pipeline Monitor

> **Live demo:** [league-sf-pipeline.streamlit.app](https://league-sf-pipeline.streamlit.app/) 

> **Parent pipeline:** [github.com/TotoriYoyori/league-snowflake](https://github.com/TotoriYoyori/league-snowflake)

A Streamlit dashboard that monitors the `league-snowflake` medallion pipeline: 27 checks across the Seed, Bronze, Silver, and Gold layers, each showing a pass/warn/fail pill where relevant.

```
┌───────────────────────────────────────────────────────────────────────┐
│   local dev            /snowflake/session/token missing → mock mode    │
│   ──────────           reads assets/sample_data/*.csv                  │
│                                                                         │
│   deployed in SiS       token present → live mode                      │
│   ──────────────       runs query.build() against Snowflake            │
│                                                                         │
├───────────────────────────────────────────────────────────────────────┤
│   SEED (7)   →   BRONZE (10)   →   SILVER (6)   →   GOLD (4)            │
└───────────────────────────────────────────────────────────────────────┘
```
----
## How it's built

- Each check is a `MonitorQuery` subclass in `src/query.py`: its own SQL/`SHOW` command, 
title/description in English and Chinese, and optionally a `status()` method that turns a dataframe into 
a pass/warn/fail pill.
- `LAYERS` in `query.py` maps each layer to a list of rows of checks, so layout 
(single-width vs. side-by-side columns) is declared in addition to checks.
- `src/data.py` owns all fetch/cache: runs the live query against Snowflake when deployed, or reads mock
CSVs locally, decided by whether `/snowflake/session/token` exists on disk.
- `src/mock.py` reads a check's sample CSV from `assets/sample_data/` by name, used whenever `data.py`
detects it's not running inside Snowflake.
- `src/ui/`: renders the 4 layers, one module per layer plus a shared `components.py` (header/card/pill
chrome) and `theme.py` (color palette + CSS).

----
## Project structure

```
LeagueSnowflakeStreamlitPreview/
├── streamlit_app.py     # entry point
├── src/
│   ├── query.py         # MonitorQuery base + checks + registry
│   ├── data.py          # fetch and cache data, mock-or-live handler, IS_LOCAL flag
│   ├── mock.py          # local CSV mock data loading
│   └── ui/              # renders: theme (palette + CSS) and components (shared chrome)
├── assets/
│   └── sample_data/     # one CSV per check, used whenever IS_LOCAL is True
└── snowflake.yml        # deploy on Snowflake
```

What each layer checks:

| Layer | Checks | What it's watching for |
|---|---|---|
| Seed | 7 | CSV upload vs. source row counts; simulated load pointer state |
| Bronze | 10 | Pipe/stream/stage health, pending files, copy errors |
| Silver | 6 | Task success in the last 24h; row-count reconciliation against Gold |
| Gold | 4 | Dynamic table refresh schedule/lag; grain validation against Silver |

----
## Getting started

```bash
uv sync
uv run streamlit run streamlit_app.py
```

Runs against the bundled mock data by default. This is also how the 
[standalone deployment](https://league-sf-pipeline.streamlit.app/) on Streamlit Community Cloud runs, since it 
has no Snowflake session to detect.

This repo is attached as a subfolder under the parent [`league-snowflake`](https://github.com/TotoriYoyori/league-snowflake) 
repo, so deployment against live Snowflake data isn't done from here directly. It's run from the parent repo, 
via Snowsight, which switches the app into live mode automatically once it's running inside Snowflake.

Known limitations
------------------
- All checks share one 60s cache TTL.
- No history tracking, only snapshotting pipeline at time of interaction.
