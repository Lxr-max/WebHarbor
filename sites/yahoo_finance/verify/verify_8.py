#!/usr/bin/env python3
"""Deterministic reviewer verifier for task YahooFinance--8 (yahoo_finance).

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
 "task_id": "YahooFinance--8",
 "question": "Search the news for buyback. Report how many articles match, open the most recent one, and report its publisher and the author named in the article. Report Nvidia's closing price, percent change and trading volume as stated in the article text. Switch to the Earnings topic and report its only article's title. Then log in as dana.k@test.com with password TestPass123!, open the NVDA quote, add it to your watchlist, and report the watchlist symbol count.",
 "paths": ['/', '/news\\?topic=latest&q=buyback', '/markets/stocks/articles/stock-market-today-sept-30', '/news\\?topic=earnings', '/login', '/lookup\\?s=NVDA', '/quote/NVDA', '/watchlist'],
 "claims": [['buyback article count', '\\b2\\s*\\w*\\s*(?:articles?|results?|matches)\\b|\\b2\\b[^.]{0,30}(?:articles?|results?|matches)\\b'], ['publisher', 'motley\\s*fool'], ['article author', 'will\\s*healy'], ['NVDA close', '228\\.38'], ['NVDA change', 'up\\s*0\\.51\\s*percent'], ['NVDA trading volume', '117\\.7\\s*m'], ['earnings topic article', 'cboe'], ['Dana watchlist count', '\\b5\\s*(?:\\w+\\s+)?(?:symbols?|companies|stocks|entries|items)\\b']],
 "forbidden": ['\\b(?:4|6)\\s*(?:symbols?|companies)\\b'],
 "added": {'watch_items': [{'user_id': 4, 'symbol': 'NVDA'}]},
 "removed": {},
}

if __name__ == "__main__":
    raise SystemExit(verify_lib.main(SPEC))
