#!/usr/bin/env python3
"""Capture per-symbol news for the yahoo_finance mirror.

The live quote pages load their "Recent News" module from the public search
endpoint (query2.finance.yahoo.com/v1/finance/search?q=<sym>&newsCount=...),
which returns each article's title, publisher, publish time, related tickers
and thumbnail. This script captures that stream for the mirror's marquee
symbols and merges the records into the news corpus (deduplicated against
the topic-stream articles at seed time).

Usage (from sites/yahoo_finance):
    python3 scripts_dev/capture_symbol_news.py
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent.parent
CAPTURES = HERE / 'scraped_data' / 'captures'
SOURCE = HERE / 'source_data'

UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36')

# The mirror's marquee equities + ETFs (quote pages that need a Recent News
# module); also seeds the news search corpus with cross-provider items.
SYMBOLS = [
    'AAPL', 'MSFT', 'NVDA', 'GOOGL', 'AMZN', 'META', 'TSLA', 'AVGO', 'TSM',
    'AMD', 'MU', 'JPM', 'BAC', 'GS', 'V', 'MA', 'BRK-B', 'KO', 'PEP', 'PG',
    'WMT', 'COST', 'XOM', 'CVX', 'JNJ', 'LLY', 'UNH', 'MRK', 'PFE', 'ABBV',
    'BA', 'CAT', 'GE', 'HON', 'DIS', 'NFLX', 'CRM', 'ORCL', 'ADBE', 'INTC',
    'QCOM', 'TXN', 'PFE', 'SPY', 'QQQ', 'IWM', 'BTC-USD', 'ETH-USD',
]

session = requests.Session()
session.headers.update({'User-Agent': UA, 'Accept': 'application/json',
                        'Referer': 'https://finance.yahoo.com/'})


def now_iso():
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def main():
    started = now_iso()
    out = {}
    for sym in SYMBOLS:
        url = (f'https://query2.finance.yahoo.com/v1/finance/search?q={sym}'
               f'&quotesCount=0&newsCount=10&enableFuzzyQuery=false')
        t0 = time.time()
        resp = session.get(url, timeout=30)
        name = f'search_news_{sym.replace("-", "_")}'
        (CAPTURES / f'{name}.raw').write_bytes(resp.content)
        (CAPTURES / f'{name}.meta.json').write_text(json.dumps({
            'url': url, 'method': 'GET', 'status': resp.status_code,
            'captured_at': now_iso(), 'bytes': len(resp.content),
            'elapsed_s': round(time.time() - t0, 2),
        }, indent=1))
        if resp.status_code == 200:
            for item in resp.json().get('news') or []:
                link = item.get('link') or ''
                if not link or not item.get('title'):
                    continue
                out[link] = {
                    'title': item.get('title'),
                    'publisher': item.get('publisher'),
                    'published_ts': item.get('providerPublishTime'),
                    'link': link,
                    'related_tickers': item.get('relatedTickers') or [],
                    'thumbnail': (item.get('thumbnail') or {}).get('resolutions') or [],
                    'queried_symbol': sym,
                }
        time.sleep(1.0)
    records = [out[k] for k in sorted(out.keys())]
    (SOURCE / 'symbol_news.json').write_text(json.dumps(records, indent=1))
    (SOURCE / 'symbol_news_meta.json').write_text(json.dumps({
        'capture_started_utc': started,
        'capture_finished_utc': now_iso(),
        'endpoint': 'https://query2.finance.yahoo.com/v1/finance/search',
        'symbols_queried': len(SYMBOLS),
        'unique_articles': len(records),
    }, indent=1))
    print(f'== symbol news: {len(records)} unique articles '
          f'across {len(SYMBOLS)} queries')


if __name__ == '__main__':
    sys.exit(main())
