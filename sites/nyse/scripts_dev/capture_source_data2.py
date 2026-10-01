#!/usr/bin/env python3
"""Capture pass 2 (resumable): remaining directories, market movers, IPO
center, bell calendar events, and CMS pages. Every request is spaced with a
polite pace and skipped when an identical successful capture already exists.
"""
from __future__ import annotations

import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from capture_source_data import (CAPTURES, BASE, capture_directory,  # noqa: E402
                                 paced_get)


def capture_cms_pages():
    pages = [
        ('home', f'{BASE}/index'),
        ('listings', f'{BASE}/listings'),
        ('listings_directory_stock', f'{BASE}/listings_directory/stock'),
        ('ipo_center_recent_ipo', f'{BASE}/ipo-center/recent-ipo'),
        ('ipo_center_pricing_stats', f'{BASE}/ipo-center/ipo-pricing-stats'),
        ('bell_calendar', f'{BASE}/bell/calendar'),
        ('history_of_nyse', f'{BASE}/history-of-nyse'),
        ('markets_page', f'{BASE}/markets'),
    ]
    for name, url in pages:
        raw = paced_get(url, raw=True, skip_if_captured=True)
        print(f'  cms {name}: {len(raw) if raw else 0} bytes', flush=True)


def main():
    t0 = time.time()
    for tab in ('equity', 'etf', 'reit', 'index'):
        path = os.path.join(CAPTURES, f'directory_{tab}.json')
        if not os.path.exists(path):
            print(f'[capture2] listings directory — {tab}', flush=True)
            rows = capture_directory(tab)
            json.dump(rows, open(path, 'w'))

    print('[capture2] market movers', flush=True)
    for cat in ('nyse', 'nyse_american'):
        paced_get(f'{BASE}/api/market-mover/data?category={cat}',
                  skip_if_captured=True)
        print(f'  market-mover {cat} ok', flush=True)

    print('[capture2] IPO center APIs', flush=True)
    for endpoint in ('calendar', 'monthly-execution-ipo', 'largest-recent-ipo',
                     'price-perf-by-sector-ipo', 'backlog-ipo'):
        paced_get(f'{BASE}/api/ipo-center/{endpoint}',
                  skip_if_captured=True)
        print(f'  ipo-center {endpoint} ok', flush=True)

    print('[capture2] bell events (15 pages x 20)', flush=True)
    for page in range(1, 16):
        paced_get(f'{BASE}/api/events/filter?filterToken=&startDate=&endDate='
                  f'&type=&pageNumber={page}&maxResultsPerPage=20&company'
                  f'&sortOrder=down', skip_if_captured=True)
        print(f'  bell page {page} ok', flush=True)
    paced_get(f'{BASE}/api/events/types', skip_if_captured=True)
    print('  events types ok', flush=True)

    print('[capture2] CMS pages', flush=True)
    capture_cms_pages()

    print(f'[capture2] done in {time.time()-t0:.0f}s', flush=True)


if __name__ == '__main__':
    main()
