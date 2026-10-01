#!/usr/bin/env python3
"""Deterministic reviewer verifier for task YahooFinance--12 (yahoo_finance).

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
 "task_id": "YahooFinance--12",
 "question": "Log in as carol.d@test.com with password TestPass123!, open the watchlist and report its symbols. Remove UnitedHealth Group (UNH). Then search for Merck, open its quote, report its trailing P/E and 52-week range, add it to the watchlist, and create an alert above 160 dollars with note Pharma rotation. Report the final watchlist symbols and the new alert's status.",
 "paths": ['/', '/login', '/watchlist', '/lookup\\?s=Merck', '/quote/MRK', '/alerts'],
 "claims": [['initial watchlist', '\\blly\\b[^.]{0,40}\\bunh\\b[^.]{0,40}\\bpfe\\b|\\bunh\\b[^.]{0,40}\\bpfe\\b'], ['MRK trailing P/E', '116\\.25'], ['MRK 52-week range', '82\\.01\\s*-\\s*156\\.92'], ['new alert status', '\\bactive\\b'], ['final watchlist', '\\blly\\b[^.]{0,60}\\bpfe\\b[^.]{0,60}\\bmrk\\b']],
 "forbidden": ['final[^.]{0,80}\\bunh\\b'],
 "added": {'price_alerts': [{'user_id': 3, 'symbol': 'MRK', 'direction': 'above', 'threshold': 160.0, 'note': 'Pharma rotation'}], 'watch_items': [{'user_id': 3, 'symbol': 'MRK'}]},
 "removed": {'watch_items': [{'user_id': 3, 'symbol': 'UNH'}]},
}

if __name__ == "__main__":
    raise SystemExit(verify_lib.main(SPEC))
