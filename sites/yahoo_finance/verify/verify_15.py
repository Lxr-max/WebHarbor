#!/usr/bin/env python3
"""Deterministic reviewer verifier for task YahooFinance--15 (yahoo_finance).

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
 "task_id": "YahooFinance--15",
 "question": "Search for bitcoin. Report the matching quote symbols, open Bitcoin USD, and report its price, market cap and 52-week range. Then search the news for stablecoin, report how many articles match, and open the most recent one; report its publisher and the author named in the article, and the three firms that handle the stablecoin's reserves as stated in the article text. Log in as dana.k@test.com with password TestPass123!, add Bitcoin USD to your watchlist and create an alert above 90000 dollars with note ETF bid. Report the alert's status and Dana's watchlist symbol count.",
 "paths": ['/', '/lookup\\?s=bitcoin', '/quote/BTC-USD', '/news', '/news\\?topic=latest&q=stablecoin', '/markets/crypto/articles/stripes-bridge-launches-ousd', '/login', '/alerts', '/watchlist'],
 "claims": [['bitcoin matches', '\\bbtc-usd\\b'], ['BTC price', '83[,]?452\\.08'], ['BTC market cap', '1\\.68\\s*t'], ['BTC 52-week range', '57[,]?747\\.77\\s*-\\s*126[,]?198\\.07'], ['stablecoin article count', '\\b2\\s*\\w*\\s*(?:articles?|results?|matches)\\b|(?:articles?|results?|matches)[^.]{0,30}\\b2\\b'], ['publisher', 'bankless'], ['author', 'william\\s*peaster'], ['reserve custodians', 'blackrock[^.]{0,40}bny[^.]{0,40}lead\\s*bank'], ['alert status', '\\bactive\\b'], ['Dana watchlist count', '\\b5\\s*(?:\\w+\\s+)?(?:symbols?|companies|stocks|entries|items)\\b']],
 "forbidden": ['\\b(?:4|6)\\s*(?:symbols?|companies)\\b'],
 "added": {'price_alerts': [{'user_id': 4, 'symbol': 'BTC-USD', 'direction': 'above', 'threshold': 90000.0, 'note': 'ETF bid'}], 'watch_items': [{'user_id': 4, 'symbol': 'BTC-USD'}]},
 "removed": {},
}

if __name__ == "__main__":
    raise SystemExit(verify_lib.main(SPEC))
