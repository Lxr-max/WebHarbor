#!/usr/bin/env python3
"""Deterministic reviewer verifier for task YahooFinance--7 (yahoo_finance).

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
 "task_id": "YahooFinance--7",
 "question": "Open the screener's Most Actives preset and report the most-traded symbol with its volume and percent change. Open its quote, then its Historical Data tab, and report the closing price on the most recent captured day and on the first captured day. From the Statistics tab report its 50-day average. Log in as dana.k@test.com with password TestPass123!, add the stock to your watchlist, create an alert above 20 dollars with note LatAm growth, open the watchlist and report the symbols and the company's industry.",
 "paths": ['/', '/screener\\?preset=most_actives', '/quote/NU', '/quote/NU/history', '/quote/NU/statistics', '/login', '/alerts', '/watchlist'],
 "claims": [['most-traded symbol', '\\bnu\\b'], ['volume', '100[,]?868[,]?354'], ['percent change', '\\+?2\\.51\\s*percent'], ['industry', 'banks\\s*-\\s*regional'], ['most recent close', '12\\.66'], ['first captured close', '14\\.46'], ['50-day average', '14\\.33'], ['watchlist', 'watchlist[^.]{0,150}\\bnu\\b|\\bnu\\b[^.]{0,150}watchlist']],
 "forbidden": [],
 "added": {'price_alerts': [{'user_id': 4, 'symbol': 'NU', 'direction': 'above', 'threshold': 20.0, 'note': 'LatAm growth'}], 'watch_items': [{'user_id': 4, 'symbol': 'NU'}]},
 "removed": {},
}

if __name__ == "__main__":
    raise SystemExit(verify_lib.main(SPEC))
