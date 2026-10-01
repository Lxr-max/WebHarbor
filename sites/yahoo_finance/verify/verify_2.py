#!/usr/bin/env python3
"""Deterministic reviewer verifier for task YahooFinance--2 (yahoo_finance).

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
 "task_id": "YahooFinance--2",
 "question": "Open the earnings calendar and go to the previous week. On September 24, report the company with the biggest positive EPS surprise that day, with its EPS estimate, reported EPS and surprise percent. Filter that week to After market close and report how many events remain. Clear the filters, type COST in the symbol filter and report Costco's call time and EPS estimate. Open its quote, log in as dana.k@test.com, create an alert on COST above 1000 dollars with note Earnings prep, and report Dana's alert total.",
 "paths": ['/', '/calendar/earnings\\?day=2026-09-20', '/calendar/earnings\\?day=2026-09-20[^#]*time=AMC', '/calendar/earnings\\?day=2026-09-20[^#]*symbol=COST', '/quote/COST', '/login', '/alerts'],
 "claims": [['biggest surprise company', 'stitch\\s*fix'], ['EPS estimate', '-\\s*0\\.06|\\b0\\.06\\b'], ['reported EPS', '-\\s*0\\.01|\\b0\\.01\\b'], ['surprise percent', '84\\.92\\s*(?:percent)?'], ['after-market-close count', '\\b2\\s*\\w*\\s*(?:events?|reports?)\\b|(?:events?|reports?)[^.]{0,30}\\b2\\b'], ['Costco call time', '\\btas\\b'], ['Costco EPS estimate', '6\\.53'], ['Dana alert total', '\\b2\\s*(?:price\\s*)?alerts?\\b']],
 "forbidden": ['\\b(?:3|4|5)\\s*(?:price\\s*)?alerts?\\b'],
 "added": {'price_alerts': [{'user_id': 4, 'symbol': 'COST', 'direction': 'above', 'threshold': 1000.0, 'note': 'Earnings prep'}]},
 "removed": {},
}

if __name__ == "__main__":
    raise SystemExit(verify_lib.main(SPEC))
