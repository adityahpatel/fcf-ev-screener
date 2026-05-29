# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Setup

```bash
pip install -r requirements.txt
```

## Running

```bash
# Test against 13 hardcoded tickers (fast, ~10s) — outputs test_output.csv
python test_script.py

# Full run against all NASDAQ-listed US stocks (slow, hours) — outputs us_tickers_financials.csv
python main.py
```

## Architecture

This is a single-purpose financial screening tool that computes the **FCF/EV ratio** (Free Cash Flow ÷ Enterprise Value) as a value investing signal — higher ratio indicates more cash generation relative to price.

**Data pipeline:**
1. `fetch_all_us_tickers()` — pulls NASDAQ listings from DataHub.io CSV, filters out ETFs and test issues
2. `get_enterprise_value()` — fetches EV via `yf.Ticker.info['enterpriseValue']`
3. `get_free_cash_flow()` — fetches TTM FCF from `t.ttm_cashflow` and up to 4 annual years from `t.cashflow` (OCF + CapEx)
4. `compute_metrics()` — averages TTM + annual FCF values, divides by EV to produce `FCF_EV_Ratio_Pct`

**main.py vs test_script.py:** Both implement the same logic. `test_script.py` uses a hardcoded list of 13 well-known tickers and prints a formatted table in addition to writing CSV. `main.py` pulls the full ticker universe and only writes CSV. There is deliberate code duplication between them.

**Rate limiting:** 0.5s sleep between each ticker to avoid Yahoo Finance throttling. Errors are logged to `errors.log` (main) or `test_errors.log` (test) rather than crashing.

**Output columns:** `Ticker`, `Name`, `Enterprise_Value`, `FCF_TTM`, `FCF_Y1`–`FCF_Y4`, `FCF_Avg`, `FCF_EV_Ratio_Pct`
