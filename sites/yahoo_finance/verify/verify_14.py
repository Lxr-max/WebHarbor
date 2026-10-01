#!/usr/bin/env python3
"""Deterministic reviewer verifier for task YahooFinance--14 (yahoo_finance).

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
 "task_id": "YahooFinance--14",
 "question": "From the home page report the top symbol in the Day Gainers list with its percent change. Open the screener, filter to that stock's sector with market cap between 10000000000 and 200000000000 dollars, sorted by percent change descending, and report the first three symbols with their changes. Open the first result and report its 52-week change from the Statistics tab. Log in as bob.c@test.com, add it to your watchlist, and report the watchlist symbols.",
 "paths": ['/', '/screener', '/screener\\?[^#]*sector=Healthcare', '[^#]*mcap_min=10000000000', '[^#]*mcap_max=200000000000', '[^#]*sort=change', '/quote/UTHR', '/quote/UTHR/statistics', '/login', '/watchlist'],
 "claims": [['Day Gainers top', '\\buthr\\b[^.]{0,40}\\+?12\\.55\\s*percent'], ['first filtered symbol', '\\buthr\\b[^.]{0,30}\\+?12\\.55'], ['second filtered symbol', '\\bibrx\\b[^.]{0,30}\\+?6\\.91'], ['third filtered symbol', '\\bpfe\\b[^.]{0,30}-\\s*0\\.70'], ['52-week change', '\\+?8\\.58\\s*percent'], ['Bob watchlist', 'watchlist[^.]{0,150}\\buthr\\b|\\buthr\\b[^.]{0,150}watchlist']],
 "forbidden": [],
 "added": {'watch_items': [{'user_id': 2, 'symbol': 'UTHR'}]},
 "removed": {},
}

if __name__ == "__main__":
    raise SystemExit(verify_lib.main(SPEC))
