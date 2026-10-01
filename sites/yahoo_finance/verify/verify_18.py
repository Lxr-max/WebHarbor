#!/usr/bin/env python3
"""Deterministic reviewer verifier for task YahooFinance--18 (yahoo_finance).

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
 "task_id": "YahooFinance--18",
 "question": "Search the news for inflation. Report how many articles match, open the most recent one and report its publisher and the author named in the text. Then search quotes for gold, open the Gold futures quote and report its price and percent change. Log in as carol.d@test.com, add Gold futures to your watchlist, create an alert above 4300 dollars with note Rally hedge, and report the alert's status and Carol's watchlist symbol count.",
 "paths": ['/', '/news\\?topic=latest&q=inflation', '/economy/policy/articles/feds-kashkari-says-central-bank', '/lookup\\?s=gold', '/quote/GC', '/login', '/alerts', '/watchlist'],
 "claims": [['inflation article count', '\\b18\\s*\\w*\\s*(?:articles?|results?|matches)\\b|\\b18\\b[^.]{0,30}(?:articles?|results?|matches)\\b'], ['publisher', 'reuters'], ['author', 'michael\\s*s\\.?\\s*derby'], ['gold price', '4[,]?183\\.20'], ['gold percent change', '-\\s*0\\.08\\s*percent'], ['alert status', '\\bactive\\b'], ['Carol watchlist count', '\\b4\\s*(?:symbols?|companies|stocks)\\b']],
 "forbidden": ['\\b(?:3|5)\\s*(?:symbols?|companies)\\b'],
 "added": {'price_alerts': [{'user_id': 3, 'symbol': 'GC=F', 'direction': 'above', 'threshold': 4300.0, 'note': 'Rally hedge'}], 'watch_items': [{'user_id': 3, 'symbol': 'GC=F'}]},
 "removed": {},
}

if __name__ == "__main__":
    raise SystemExit(verify_lib.main(SPEC))
