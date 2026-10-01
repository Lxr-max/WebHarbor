#!/usr/bin/env python3
"""Deterministic reviewer verifier for task YahooFinance--4 (yahoo_finance).

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
 "task_id": "YahooFinance--4",
 "question": "On the News page search for Nvidia. Report how many articles match and open the most recent one; report its publisher, its related tickers, and the author named in the article. Then switch to the Economy topic and report the first article's title and publisher. Log in as dana.k@test.com with password TestPass123!, open the NVDA quote, and create an alert below 200 dollars with note AI pullback. Report the new alert's status and Dana's total alert count.",
 "paths": ['/', '/news\\?topic=latest&q=Nvidia', '/technology/ai/articles/ai-driven-edge-security-integration', '/news\\?topic=economy', '/login', '/lookup\\?s=NVDA', '/quote/NVDA', '/alerts'],
 "claims": [['Nvidia article count', '\\b10\\s*(?:articles?|results?|matches)\\b'], ['publisher', 'simply\\s*wall\\s*st'], ['related tickers', 'nvda.{0,10}panw.{0,10}smtc'], ['author', 'sasha\\s*jovanovic'], ['economy first article', 'kashkari'], ['new alert status', '\\bactive\\b'], ['Dana alert total', '\\b2\\s*(?:price\\s*)?alerts?\\b']],
 "forbidden": ['\\b(?:3|4)\\s*(?:price\\s*)?alerts?\\b'],
 "added": {'price_alerts': [{'user_id': 4, 'symbol': 'NVDA', 'direction': 'below', 'threshold': 200.0, 'note': 'AI pullback'}]},
 "removed": {},
}

if __name__ == "__main__":
    raise SystemExit(verify_lib.main(SPEC))
