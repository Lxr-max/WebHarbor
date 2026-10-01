#!/usr/bin/env python3
"""Deterministic reviewer verifier for task YahooFinance--17 (yahoo_finance).

Ground truth frozen from the reviewer's honest two-round Chromium walks of
orch/contribute/yahoo_finance @ dacbf663 (review container webharbor:yf-review,
per-task control-plane reset + fresh context; evidence tree
wh-yf-review-evidence/runs/round1|2; every walked fact independently
cross-checked against the frozen in-image seed database).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import verify_lib  # noqa: E402

SPEC = {
 "task_id": "YahooFinance--17",
 "question": "Search for Microsoft, open its quote's Historical Data tab and report the closing price on the most recent captured day and on the first captured day. Open the Statistics tab and report the 50-day and 200-day moving averages. Log in as alice.j@test.com, report how many symbols her watchlist lists, then create an alert on Microsoft above 600 dollars with note Azure wave and report its status and Alice's total alerts.",
 "paths": ['/', '/lookup\\?s=Microsoft', '/quote/MSFT', '/quote/MSFT/history', '/quote/MSFT/statistics', '/login', '/watchlist', '/alerts'],
 "claims": [['most recent close', '512\\.90'], ['first captured close', '501\\.02'], ['50-day average', '480\\.25'], ['200-day average', '432\\.30'], ['Alice watchlist count', '\\b4\\s*(?:symbols?|companies|stocks)\\b'], ['new alert status', '\\bactive\\b'], ['Alice alert total', '\\b3\\s*(?:price\\s*)?alerts?\\b']],
 "forbidden": ['\\b(?:2|4)\\s*alerts?\\b'],
 "added": {'price_alerts': [{'user_id': 1, 'symbol': 'MSFT', 'direction': 'above', 'threshold': 600.0, 'note': 'Azure wave'}]},
 "removed": {},
}

if __name__ == "__main__":
    raise SystemExit(verify_lib.main(SPEC))
