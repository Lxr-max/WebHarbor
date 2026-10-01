#!/usr/bin/env python3
"""Deterministic reviewer verifier for task YahooFinance--13 (yahoo_finance).

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
 "task_id": "YahooFinance--13",
 "question": "Log in as alice.j@test.com with password TestPass123!, open the alerts page and report each alert's symbol, direction, threshold and status. Delete the Tesla alert. Then open the TSLA quote, create a new alert above 900 dollars with note Upside breakout, and report the new alert's status plus Alice's final alert count. Also report Tesla's 50-day average from its Statistics tab.",
 "paths": ['/', '/login', '/alerts', '/lookup\\?s=(?:Tesla|TSLA)', '/quote/TSLA', '/quote/TSLA/statistics'],
 "claims": [['initial alerts', '\\bnvda\\b[^.]{0,80}below\\s*150|below\\s*150[^.]{0,80}\\bnvda\\b'], ['initial Tesla alert', '\\babove\\s*480\\b'], ['new alert status', '\\bactive\\b'], ['final alert count', '\\b2\\s*(?:price\\s*)?alerts?\\b'], ['Tesla 50-day average', '347\\.45']],
 "forbidden": ['\\b(?:1|3)\\s*(?:price\\s*)?alerts?\\b'],
 "added": {'price_alerts': [{'user_id': 1, 'symbol': 'TSLA', 'direction': 'above', 'threshold': 900.0, 'note': 'Upside breakout'}]},
 "removed": {'price_alerts': [{'user_id': 1, 'symbol': 'TSLA', 'direction': 'above', 'threshold': 480.0, 'note': None}]},
}

if __name__ == "__main__":
    raise SystemExit(verify_lib.main(SPEC))
