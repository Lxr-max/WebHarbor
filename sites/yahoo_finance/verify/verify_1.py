#!/usr/bin/env python3
"""Deterministic reviewer verifier for task YahooFinance--1 (yahoo_finance).

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
 "task_id": "YahooFinance--1",
 "question": "Create a new Yahoo Finance account (name Jordan Vale, email jordan.vale@test.com, a password of at least 8 characters). Open the screener and report the Day Gainers preset's top symbol with its price and percent change. Then in the custom filter select the Technology sector with P/E between 12 and 40, sort by P/E ascending, open the first result's quote, report its industry, and add it to your watchlist. Open the watchlist and report its symbols.",
 "paths": ['/', '/signup', '/screener', '/screener\\?[^#]*sector=Technology', '[^#]*pe_min=12', '[^#]*pe_max=40', '[^#]*sort=pe', '[^#]*dir=asc', '/quote/SMCI', '/watchlist'],
 "claims": [['Day Gainers top symbol', '\\buthr\\b'], ['top price', '541\\.89'], ['top percent change', '\\+?12\\.55\\s*percent'], ['first filtered symbol', '\\bsmci\\b'], ['industry', 'computer\\s+hardware'], ['watchlist symbols', 'watchlist[^.]{0,80}\\bsmci\\b|\\bsmci\\b[^.]{0,80}watchlist']],
 "forbidden": ['\\buthr\\b[^.]{0,40}\\bwatchlist\\b'],
 "added": {'users': [{'name': 'Jordan Vale', 'email': 'jordan.vale@test.com', 'joined': '2026-09-30', 'password_hash': 'SHAPE:bcrypt:TestPass123!'}], 'watch_items': [{'user_id': 5, 'symbol': 'SMCI'}]},
 "removed": {},
}

if __name__ == "__main__":
    raise SystemExit(verify_lib.main(SPEC))
