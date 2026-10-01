#!/usr/bin/env python3
"""Deterministic reviewer verifier for task YahooFinance--19 (yahoo_finance).

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
 "task_id": "YahooFinance--19",
 "question": "Open the screener's custom filter, select the Utilities sector with dividend yield at least 4 percent, sorted by dividend yield descending, and report the first three symbols with their yields. Open the third result's quote, report its dividend yield, market cap and next earnings date. Log in as dana.k@test.com, add it to your watchlist. Then open the alerts page and delete the META alert; report how many alerts remain and the watchlist symbol count.",
 "paths": ['/', '/screener', '/screener\\?[^#]*sector=Utilities', '[^#]*yield_min=4', '[^#]*sort=yield', '/quote/D', '/login', '/alerts', '/watchlist'],
 "claims": [['first utility', '\\bduk-pa\\b[^.]{0,30}6\\.59'], ['second utility', '\\bken\\b[^.]{0,30}6\\.40'], ['third utility', '\\bd\\b[^.]{0,30}4\\.40'], ['D dividend yield', '4\\.40\\s*percent'], ['D market cap', '53\\.23\\s*b'], ['D next earnings date', 'october\\s*30[,]?\\s*2026'], ['alerts remaining', '\\bno\\s*alerts?\\b|\\b0\\s*alerts?\\b'], ['Dana watchlist count', '\\b5\\s*(?:\\w+\\s+)?(?:symbols?|companies|stocks|entries|items)\\b']],
 "forbidden": ['\\b1\\s*alert\\s*remains?\\b'],
 "added": {'watch_items': [{'user_id': 4, 'symbol': 'D'}]},
 "removed": {'price_alerts': [{'user_id': 4, 'symbol': 'META', 'direction': 'below', 'threshold': 600.0, 'note': 'Re-entry'}]},
}

if __name__ == "__main__":
    raise SystemExit(verify_lib.main(SPEC))
