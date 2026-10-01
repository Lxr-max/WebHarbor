#!/usr/bin/env python3
"""Deterministic reviewer verifier for task YahooFinance--11 (yahoo_finance).

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
 "task_id": "YahooFinance--11",
 "question": "Open the earnings calendar and go to next week (October 4). Report which day that week has the most events and how many it has. Switch back to this week and report which of its days has the most events and how many. Then search for Apple, open its quote and report its next earnings date, open the Statistics tab and report its 1-year target estimate and 50-day average. Log in as dana.k@test.com with password TestPass123!, create an alert on Apple above 400 dollars with note Earnings run, and report the new alert's status and Dana's total alerts.",
 "paths": ['/', '/calendar/earnings\\?day=2026-10-04', '/calendar/earnings\\?day=2026-09-27', '/lookup\\?s=Apple', '/quote/AAPL', '/quote/AAPL/statistics', '/login', '/alerts'],
 "claims": [['next week busiest day', 'october\\s*8[,]?\\s*2026'], ['next week event count', '\\b97\\s*(?:events?|earnings?|reports?)\\b'], ['this week busiest day', 'october\\s*1[,]?\\s*2026'], ['this week event count', '\\b152\\s*(?:events?|earnings?|reports?)\\b'], ['Apple next earnings date', 'october\\s*29[,]?\\s*2026'], ['1-year target', '328\\.22'], ['50-day average', '321\\.98'], ['new alert status', '\\bactive\\b'], ['Dana alert total', '\\b2\\s*(?:price\\s*)?alerts?\\b']],
 "forbidden": ['\\b(?:1|3)\\s*(?:price\\s*)?alerts?\\b'],
 "added": {'price_alerts': [{'user_id': 4, 'symbol': 'AAPL', 'direction': 'above', 'threshold': 400.0, 'note': 'Earnings run'}]},
 "removed": {},
}

if __name__ == "__main__":
    raise SystemExit(verify_lib.main(SPEC))
