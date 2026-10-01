#!/usr/bin/env python3
"""Deterministic reviewer verifier for task YahooFinance--9 (yahoo_finance).

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
 "task_id": "YahooFinance--9",
 "question": "Create a new account (name Priya Nair, email priya.nair@test.com, a password of at least 8 characters). Search for Apple, open its quote's Financials tab and report the latest fiscal year end date, its total revenue and net income. Open the Statistics tab and report Apple's PEG ratio and beta. Add Apple to your watchlist, open the Profile tab and report its number of employees, then open the watchlist and report its symbols. Finally, search the news for Apple, report how many articles match, and open the most recent one to report its publisher and author.",
 "paths": ['/', '/signup', '/lookup\\?s=Apple', '/quote/AAPL', '/quote/AAPL/financials', '/quote/AAPL/statistics', '/quote/AAPL/profile', '/watchlist', '/news\\?topic=latest&q=Apple', '/technology/ai/articles/bank-america-warns-apple'],
 "claims": [['fiscal year end', '2025-09-30|september\\s*30[,]?\\s*2025'], ['total revenue', '416\\.16\\s*b'], ['net income', '112\\.01\\s*b'], ['PEG ratio', '2\\.64'], ['beta', '1\\.08'], ['employees', '150[,]?000'], ['watchlist symbols', 'watchlist[^.]{0,60}\\baapl\\b|\\baapl\\b[^.]{0,60}watchlist'], ['Apple news match count', '\\b9\\s*(?:\\w+\\s+)?(?:articles?|results?|matches)\\b'], ['newest article publisher', 'thestreet'], ['newest article author', 'hillary\\s*remy']],
 "forbidden": [],
 "added": {'users': [{'name': 'Priya Nair', 'email': 'priya.nair@test.com', 'joined': '2026-09-30', 'password_hash': 'SHAPE:bcrypt:TestPass123!'}], 'watch_items': [{'user_id': 5, 'symbol': 'AAPL'}]},
 "removed": {},
}

if __name__ == "__main__":
    raise SystemExit(verify_lib.main(SPEC))
