#!/usr/bin/env python3
"""Deterministic reviewer verifier for task YahooFinance--5 (yahoo_finance).

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
 "task_id": "YahooFinance--5",
 "question": "Open the Trending page and report the top three trending symbols with each percent change. Open the number one's quote and from its Statistics tab report its market cap, 52-week range, trailing P/E and 50-day average. Log in as carol.d@test.com with password TestPass123!, add it to your watchlist, then create an alert on it above 1200 dollars with note Memory cycle. Go back to the Trending page, open the number three symbol and report its market cap. Report the watchlist symbol count and Carol's total alerts.",
 "paths": ['/', '/trending', '/quote/MU', '/quote/MU/statistics', '/login', '/alerts', '/quote/LQDA', '/watchlist'],
 "claims": [['trending #1', '\\bmu\\b[^.]{0,40}\\+?0\\.00\\s*percent'], ['trending #2', '\\bgoog\\b[^.]{0,40}\\+?1\\.01\\s*percent'], ['trending #3', '\\blqda\\b[^.]{0,40}-\\s*57\\.19\\s*percent'], ['MU market cap', '1\\.2\\s*t'], ['MU 52-week range', '179\\.61\\s*-\\s*1[,]?255\\.00'], ['MU trailing P/E', '24\\.10'], ['MU 50-day average', '949\\.71'], ['LQDA market cap', '2\\.71\\s*b'], ['watchlist count', '\\b4\\s*(?:symbols?|companies|stocks)\\b'], ['Carol alert total', '\\b3\\s*(?:price\\s*)?alerts?\\b']],
 "forbidden": ['\\b(?:5)\\s*(?:symbols?|companies)\\b', '\\b(?:2|4)\\s*alerts?\\b'],
 "added": {'price_alerts': [{'user_id': 3, 'symbol': 'MU', 'direction': 'above', 'threshold': 1200.0, 'note': 'Memory cycle'}], 'watch_items': [{'user_id': 3, 'symbol': 'MU'}]},
 "removed": {},
}

if __name__ == "__main__":
    raise SystemExit(verify_lib.main(SPEC))
