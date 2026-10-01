#!/usr/bin/env python3
"""Deterministic reviewer verifier for task YahooFinance--3 (yahoo_finance).

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
 "task_id": "YahooFinance--3",
 "question": "Open the Sectors page. Report the sector with the largest aggregate market cap, its day percent change, and its top loser. Open that sector's page and report the industry with the most companies plus how many companies it has. Open the largest company in the sector; report its trailing P/E and dividend yield from its quote, and its 50-day average from the Statistics tab. Log in as carol.d@test.com with password TestPass123!, add it to your watchlist, create an alert on it below 200 dollars with note Dip buy, and report the watchlist count and the alert's status.",
 "paths": ['/', '/sectors', '/sectors/technology', '/quote/NVDA', '/quote/NVDA/statistics', '/login', '/alerts', '/watchlist'],
 "claims": [['largest sector', '\\btechnology\\b'], ['sector day change', '\\+?0\\.38\\s*percent'], ['top loser', '\\bjbl\\b'], ['industry with most companies', 'software\\s*-\\s*infrastructure'], ['industry company count', '\\b15\\s*companies\\b'], ['largest company', '\\bnvda\\b'], ['trailing P/E', '28\\.87'], ['dividend yield', '0\\.44\\s*percent'], ['50-day average', '216\\.98'], ['alert status', '\\bactive\\b'], ['watchlist count', 'watchlist[^.]{0,60}\\b4\\b|\\b4\\b[^.]{0,60}watchlist|\\b4\\s*(?:symbols?|entries|items|companies|stocks)\\b']],
 "forbidden": ['\\b(?:5|3)\\s*(?:symbols?|companies)\\s*on\\b'],
 "added": {'price_alerts': [{'user_id': 3, 'symbol': 'NVDA', 'direction': 'below', 'threshold': 200.0, 'note': 'Dip buy'}], 'watch_items': [{'user_id': 3, 'symbol': 'NVDA'}]},
 "removed": {},
}

if __name__ == "__main__":
    raise SystemExit(verify_lib.main(SPEC))
