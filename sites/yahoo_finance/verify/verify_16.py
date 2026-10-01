#!/usr/bin/env python3
"""Deterministic reviewer verifier for task YahooFinance--16 (yahoo_finance).

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
 "task_id": "YahooFinance--16",
 "question": "Open the Sectors page, then the Healthcare sector page. Report how many companies are listed and which industry has the most members. Open the largest company's quote and report its trailing P/E and profit margin from the Statistics tab. Go back and open the second largest; report the same two numbers. Log in as bob.c@test.com, add the second largest to your watchlist and create an alert on it above 300 dollars with note Dividend value. Report the watchlist count and alert status.",
 "paths": ['/', '/sectors', '/sectors/healthcare', '/quote/LLY', '/quote/LLY/statistics', '/quote/JNJ', '/quote/JNJ/statistics', '/login', '/alerts', '/watchlist'],
 "claims": [['Healthcare company count', '\\b39\\s*(?:companies|captured|listed)\\b'], ['biggest industry', 'biotechnology'], ['largest company', '\\b(?:lly|eli\\s*lilly)\\b'], ['second largest', '\\b(?:jnj|johnson\\s*(?:and|&)?\\s*johnson)\\b'], ['LLY trailing P/E', '38\\.92'], ['LLY profit margin', '33\\.53\\s*percent'], ['JNJ trailing P/E', '30\\.71'], ['JNJ profit margin', '21\\.48\\s*percent'], ['alert status', '\\bactive\\b'], ['watchlist count', 'watchlist[^.]{0,60}\\b4\\b|\\b4\\b[^.]{0,60}watchlist|\\b4\\s*(?:symbols?|entries|items|companies|stocks)\\b']],
 "forbidden": [],
 "added": {'price_alerts': [{'user_id': 2, 'symbol': 'JNJ', 'direction': 'above', 'threshold': 300.0, 'note': 'Dividend value'}], 'watch_items': [{'user_id': 2, 'symbol': 'JNJ'}]},
 "removed": {},
}

if __name__ == "__main__":
    raise SystemExit(verify_lib.main(SPEC))
