#!/usr/bin/env python3
"""Deterministic reviewer verifier for task YahooFinance--6 (yahoo_finance).

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
 "task_id": "YahooFinance--6",
 "question": "Compare AMD and NVIDIA. Search for AMD, open its quote, and from the Statistics tab report its trailing P/E and profit margin. Do the same for NVDA and report which company has the lower P/E. Log in as bob.c@test.com, add the lower-P/E stock to your watchlist, and create an alert on it above 700 dollars. Open the watchlist and report its symbols; open the alerts and report the new alert's status.",
 "paths": ['/', '/lookup\\?s=AMD', '/quote/AMD', '/quote/AMD/statistics', '/lookup\\?s=NVDA', '/quote/NVDA', '/quote/NVDA/statistics', '/login', '/alerts', '/watchlist'],
 "claims": [['AMD trailing P/E', '154\\.88'], ['AMD profit margin', '15\\.58\\s*percent'], ['NVDA trailing P/E', '28\\.87'], ['NVDA profit margin', '63\\.66\\s*percent'], ['lower P/E company', '\\bnvda\\b[^.]{0,60}lower|lower[^.]{0,60}\\bnvda\\b'], ['new alert status', '\\bactive\\b'], ['Bob watchlist', 'watchlist[^.]{0,120}\\bnvda\\b|\\bnvda\\b[^.]{0,120}watchlist']],
 "forbidden": ['\\bamd\\b[^.]{0,40}lower\\s*p/?e'],
 "added": {'price_alerts': [{'user_id': 2, 'symbol': 'NVDA', 'direction': 'above', 'threshold': 700.0, 'note': None}], 'watch_items': [{'user_id': 2, 'symbol': 'NVDA'}]},
 "removed": {},
}

if __name__ == "__main__":
    raise SystemExit(verify_lib.main(SPEC))
