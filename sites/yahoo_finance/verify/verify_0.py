#!/usr/bin/env python3
"""Deterministic reviewer verifier for task YahooFinance--0 (yahoo_finance).

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
 "task_id": "YahooFinance--0",
 "question": "Search for Apple and open its stock quote. Report its sector and 52-week range. Open the Statistics tab and report Apple's profit margin and 1-year target estimate, then open the Profile tab and report the company's website and headquarters city. Log in as alice.j@test.com with password TestPass123!, add Apple to your watchlist, open the watchlist page and report how many symbols it lists and Apple's last price. Then create an alert on Apple above 350 dollars with the note iPhone cycle, open the alerts page and report the new alert's status and Alice's total alert count.",
 "paths": ['/', '/lookup\\?s=Apple', '/quote/AAPL', '/quote/AAPL/statistics', '/quote/AAPL/profile', '/login', '/watchlist', '/alerts'],
 "claims": [['Apple sector', '\\btechnology\\b'], ['Apple 52-week range', '243\\.42\\s*-\\s*345\\.34'], ['Apple profit margin', '27\\.62\\s*percent'], ['Apple 1-year target', '328\\.22'], ['Apple website', 'apple\\.com'], ['Apple headquarters city', 'cupertino'], ['watchlist symbol count', '\\b5\\s*(?:symbols?|companies|stocks)\\b'], ['Apple last price', '333\\.02'], ['new alert status', '\\bactive\\b'], ['Alice alert total', '\\b3\\s*(?:price\\s*)?alerts?\\b']],
 "forbidden": ['\\b4\\s*(?:symbols?|price\\s*alerts?)\\b', '\\b(?:6|2)\\s*alerts?\\b'],
 "added": {'price_alerts': [{'user_id': 1, 'symbol': 'AAPL', 'direction': 'above', 'threshold': 350.0, 'note': 'iPhone cycle'}], 'watch_items': [{'user_id': 1, 'symbol': 'AAPL'}]},
 "removed": {},
}

if __name__ == "__main__":
    raise SystemExit(verify_lib.main(SPEC))
