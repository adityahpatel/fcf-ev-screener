# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Deployment

Live at: https://adityahpatel.github.io/fcf-ev-screener/

## Setup

```bash
pip install -r requirements.txt
```

## Running

```bash
# Fetch all tickers, compute metrics, rank, and write data.json + timestamped CSVs (slow, hours)
python fetch_and_rank.py

# Start the Flask web UI (reads latest processed_data_*.csv)
python app.py   # serves at http://localhost:5050
```

## Architecture

A value investing screener that computes **FCF/EV %** (Free Cash Flow ÷ Enterprise Value) across US-listed stocks and serves results through a Flask web UI.

### Data pipeline — `fetch_and_rank.py`

1. **Universe**: reads `company_tickers.csv` (sourced from SEC EDGAR). Applies two filters before fetching:
   - Regex (`FOREIGN`) strips companies whose names contain legal-form suffixes (Ltd, plc, AG, N.V., etc.) or whose tickers end in `F` (OTC foreign listings).
   - `blacklisted_foreign_companies.csv` removes manually-identified false positives.

2. **Per-ticker fetch** (0.5s sleep between tickers):
   - `get_ev()` — `yf.Ticker.info['enterpriseValue']`
   - `get_fcf()` — TTM FCF from `t.ttm_cashflow`; up to 4 annual values from `t.cashflow`
   - `get_analyst()` — market cap, next-year revenue growth estimate, and analyst count from `t.revenue_estimate`

3. **Scoring** in `compute()`: averages TTM + up to 4 annual FCF values; returns `None` ratio if any value is negative (cash-burning companies are excluded from rankings).

4. **Ranking** in `rank()`: filters to `FCF_EV_Ratio_Pct > 0`, sorts descending, writes `processed_data_MMDDYYYY.csv` and overwrites `data.json` (the only file committed to git).

### Two frontends — know which one you're editing

There are **two** vanilla-JS frontends (no build step) that look similar but have different data sources. Editing the wrong one is the easiest mistake to make here:

- **`index.html`** (repo root) — the **production** page served by GitHub Pages at the live URL. Fetches the committed `data.json` directly (`fetch('data.json')`); no server involved. **Changes meant for the live site go here.**
- **`templates/index.html`** — the **local Flask dev** page only. Fetches `/api/data` from `app.py`. Not deployed.

Keep them in sync if a change should appear both locally and in production.

### Local dev server — `app.py`

Flask serves one route (`/`, renders `templates/index.html`) and one endpoint (`/api/data`), which reads the most recently dated `processed_data_*.csv` via glob and returns it as JSON. Used for local preview only.

### `data.json` shape

`data.json` is `{ "updated": "<date>", "rows": [...] }`. The production `index.html` reads `.rows`; the automation guard reads `.updated`.

### Sentinel value

Missing numeric data is stored as `-999` in CSVs. The frontend formats any `-999` or falsy value as `—`.

### Automation

`.github/workflows/weekly_fetch.yml` runs `fetch_and_rank.py`, retries up to 3 times on failure, and commits only `data.json` back to the repo. A guard step reads `data.json['updated']` to skip if already ran today.

The workflow has **no internal `schedule:` trigger** — only `workflow_dispatch`. An external cron job on **cron-job.org** is the sole trigger, calling GitHub's `workflow_dispatch` API on a schedule configured there (not in this repo). If `data.json` stops updating, check the cron-job.org job first — GitHub Actions will not fire on its own.

### Output columns

`Ticker`, `Name`, `Market_Cap`, `Enterprise_Value`, `FCF_TTM`, `FCF_Y1`–`FCF_Y4`, `FCF_Avg`, `FCF_EV_Ratio_Pct`, `Revenue_Growth_Est_Pct`, `Analyst_Count`

Timestamped `data_*.csv` and `processed_data_*.csv` files are gitignored; only `data.json` and `company_tickers.csv` are tracked.
