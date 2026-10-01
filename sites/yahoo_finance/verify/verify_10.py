#!/usr/bin/env python3
"""Deterministic reviewer verifier for task YahooFinance--10 (yahoo_finance).

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
 "task_id": "YahooFinance--10",
 "question": "Search for Coca-Cola, open its quote's Profile tab and report its sector, industry, employee count and website. Report its forward dividend rate and yield from the summary page. Search for PepsiCo and from its Statistics tab report its profit margin and trailing P/E. Log in as bob.c@test.com, create an alert on PEP above 100 dollars with note Cola wars, and report the alert status plus how many symbols Bob watches.",
 "paths": ['/', '/lookup\\?s=Coca-Cola', '/quote/KO', '/quote/KO/profile', '/lookup\\?s=PepsiCo', '/quote/PEP', '/quote/PEP/statistics', '/login', '/alerts', '/watchlist'],
 "claims": [['KO sector', 'consumer\\s*defensive'], ['KO industry', 'beverages\\s*-\\s*non-alcoholic'], ['KO employees', '65[,]?900'], ['KO website', 'coca-colacompany\\.com'], ['KO forward dividend', '2\\.12\\b[^.]{0,25}2\\.46\\s*percent'], ['PEP profit margin', '10\\.79\\s*percent'], ['PEP trailing P/E', '16\\.61'], ['PEP alert status', '\\btriggered\\b'], ['Bob watch count', '\\b3\\s*(?:symbols?|companies|stocks)\\b']],
 "forbidden": ['\\b(?:2|4)\\s*(?:symbols?|companies)\\s*'],
 "added": {'price_alerts': [{'user_id': 2, 'symbol': 'PEP', 'direction': 'above', 'threshold': 100.0, 'note': 'Cola wars'}]},
 "removed": {},
}

if __name__ == "__main__":
    raise SystemExit(verify_lib.main(SPEC))
