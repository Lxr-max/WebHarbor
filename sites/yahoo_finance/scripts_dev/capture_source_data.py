#!/usr/bin/env python3
"""Capture the yahoo_finance mirror's market-data snapshot from finance.yahoo.com.

Everything this script saves is a real upstream capture: the quote snapshot
batch (v7 /finance/quote), per-symbol quoteSummary modules (v10), daily chart
series (v8), the predefined stock screens (v1/finance/screener), the trending
ticker list (v1/finance/trending/US), the earnings calendar
(v1/finance/visualization entityIdType=sp_earnings) and the market strip
symbols. Raw responses are archived under scraped_data/captures/ with a
.meta.json sidecar (url, status, timestamp); the normalized records land in
source_data/*.json, which the deterministic seed builder consumes.

Usage (from sites/yahoo_finance):
    python3 scripts_dev/capture_source_data.py
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent.parent
CAPTURES = HERE / 'scraped_data' / 'captures'
SOURCE = HERE / 'source_data'
CAPTURES.mkdir(parents=True, exist_ok=True)
SOURCE.mkdir(parents=True, exist_ok=True)

UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36')

session = requests.Session()
session.headers.update({
    'User-Agent': UA,
    'Accept': 'application/json,text/plain,*/*',
    'Accept-Language': 'en-US,en;q=0.9',
    'Origin': 'https://finance.yahoo.com',
    'Referer': 'https://finance.yahoo.com/',
})


def now_iso():
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def fetch(url, *, kind='GET', body=None, name=None, sleep=1.2):
    """Fetch a URL and archive the raw response + a .meta.json sidecar."""
    stem = name or re.sub(r'[^A-Za-z0-9_.-]+', '_', url.split('finance.yahoo.com')[-1].split('?')[0])[:80]
    path = CAPTURES / f'{stem}.raw'
    t0 = time.time()
    if kind == 'GET':
        resp = session.get(url, timeout=40)
    else:
        resp = session.post(url, json=body, timeout=40)
    status = resp.status_code
    path.write_bytes(resp.content)
    meta = {
        'url': url,
        'method': kind,
        'status': status,
        'captured_at': now_iso(),
        'bytes': len(resp.content),
        'elapsed_s': round(time.time() - t0, 2),
    }
    if kind == 'POST':
        meta['post_body'] = body
    (CAPTURES / f'{stem}.meta.json').write_text(json.dumps(meta, indent=1))
    time.sleep(sleep)
    if status != 200:
        print(f'  !! {status} for {url[:110]}')
    return resp


# ------------------------------------------------------------------ crumb --

def get_crumb():
    """Yahoo's documented anonymous flow: the fc.yahoo.com request sets the
    consent cookie, then /v1/test/getcrumb issues the crumb bound to it."""
    session.get('https://fc.yahoo.com', timeout=20)
    resp = session.get('https://query2.finance.yahoo.com/v1/test/getcrumb',
                       timeout=20)
    crumb = resp.text.strip()
    print(f'crumb acquired ({len(crumb)} chars)')
    return crumb


# -------------------------------------------------------------- universe ----

SECTORS = [
    'Technology', 'Communication Services', 'Consumer Cyclical',
    'Consumer Defensive', 'Healthcare', 'Financial Services',
    'Basic Materials', 'Industrials', 'Energy', 'Utilities', 'Real Estate',
]

INDICES = ['^GSPC', '^DJI', '^IXIC', '^RUT', '^VIX', '^TNX', '^TYX']
FUTURES = ['ES=F', 'NQ=F', 'YM=F', 'RTY=F', 'GC=F', 'CL=F', 'SI=F', 'BZ=F']
CRYPTO = ['BTC-USD', 'ETH-USD', 'SOL-USD', 'DOGE-USD']
ETFS = ['SPY', 'QQQ', 'VOO', 'IWM', 'DIA', 'VTI', 'GLD', 'EEM']

SCREENS = [
    ('day_gainers', 'Day Gainers'),
    ('day_losers', 'Day Losers'),
    ('most_actives', 'Most Actives'),
    ('small_cap_gainers', 'Small Cap Gainers'),
    ('aggressive_small_caps', 'Aggressive Small Caps'),
    ('growth_technology_stocks', 'Growth Technology Stocks'),
]

SCREENER_COLUMNS = [
    'symbol', 'shortName', 'displayName', 'longName', 'region', 'exchange',
    'sector', 'industry', 'quoteType', 'marketCap', 'intradaymarketcap',
    'regularMarketPrice', 'regularMarketChange', 'regularMarketChangePercent',
    'regularMarketVolume', 'regularMarketPreviousClose', 'regularMarketOpen',
    'regularMarketDayLow', 'regularMarketDayHigh',
    'trailingPE', 'forwardPE', 'pegRatio', 'priceToBook', 'bookValue',
    'trailingEps', 'epsForward', 'epsCurrentYear',
    'dividendYield', 'trailingAnnualDividendRate', 'trailingAnnualDividendYield',
    'fiftyTwoWeekLow', 'fiftyTwoWeekHigh',
    'fiftyDayAverage', 'twoHundredDayAverage',
    'averageDailyVolume3Month', 'averageDailyVolume10Day',
    'sharesOutstanding', 'marketState', 'bid', 'ask',
    'earningsTimestamp', 'earningsTimestampStart', 'earningsTimestampEnd',
    'fullExchangeName', 'financialCurrency', 'currency',
    'averageAnalystRating', 'esgPopulated',
]


def capture_sector_tops(crumb):
    """Top-15-by-market-cap US listings per GICS sector (the screener
    universe's backbone)."""
    out = {}
    for sector in SECTORS:
        body = {
            'size': 15, 'offset': 0,
            'sortField': 'intradaymarketcap', 'sortType': 'desc',
            'quoteType': 'equity',
            'query': {'operator': 'and', 'operands': [
                {'operator': 'eq', 'operands': ['sector', sector]},
                {'operator': 'or', 'operands': [
                    {'operator': 'eq', 'operands': ['exchange', 'NMS']},
                    {'operator': 'eq', 'operands': ['exchange', 'NYQ']},
                ]},
            ]},
            'columns': SCREENER_COLUMNS,
        }
        resp = fetch('https://query1.finance.yahoo.com/v1/finance/screener'
                     f'?crumb={crumb}&lang=en-US&region=US',
                     kind='POST', body=body, name=f'screener_sector_{sector.replace(" ", "_")}')
        if resp.status_code == 200:
            result = resp.json()['finance']['result'][0]
            out[sector] = result['quotes']
            print(f'  sector {sector}: {len(result["quotes"])} quotes')
        else:
            out[sector] = []
    return out


def capture_presets(crumb):
    out = {}
    for scr_id, title in SCREENS:
        resp = fetch('https://query1.finance.yahoo.com/v1/finance/screener'
                     '/predefined/saved'
                     f'?count=25&formatted=true&scrIds={scr_id}&sortField='
                     f'&sortType=&start=0&useRecordsResponse=true&crumb={crumb}'
                     '&lang=en-US&region=US', name=f'screener_preset_{scr_id}')
        if resp.status_code == 200:
            result = resp.json()['finance']['result'][0]
            rows = result.get('quotes') or result.get('records') or []
            out[scr_id] = {
                'title': result.get('title') or title,
                'description': result.get('description') or '',
                'canonicalName': result.get('canonicalName') or scr_id,
                'total': result.get('total'),
                'quotes': rows,
            }
            print(f'  preset {scr_id}: {len(rows)} quotes')
        else:
            out[scr_id] = {'title': title, 'description': '',
                           'canonicalName': scr_id, 'total': 0, 'quotes': []}
    return out


def capture_trending():
    resp = fetch('https://query1.finance.yahoo.com/v1/finance/trending/US',
                 name='trending_US')
    return resp.json() if resp.status_code == 200 else {}


def capture_quotes_batch(symbols, crumb, name):
    """v7 batch quote — the full per-symbol market snapshot."""
    resp = fetch('https://query1.finance.yahoo.com/v7/finance/quote'
                 f'?symbols={",".join(symbols)}&crumb={crumb}'
                 '&lang=en-US&region=US&fields=', name=name)
    if resp.status_code != 200:
        return []
    return resp.json()['quoteResponse']['result']


def capture_quote_summary(symbol, crumb):
    modules = ','.join([
        'assetProfile', 'summaryDetail', 'defaultKeyStatistics',
        'financialData', 'calendarEvents', 'incomeStatementHistory',
        'summaryProfile',
    ])
    resp = fetch('https://query1.finance.yahoo.com/v10/finance/quoteSummary'
                 f'/{symbol}?modules={modules}&crumb={crumb}'
                 '&lang=en-US&region=US',
                 name=f'summary_{re.sub(r"[^A-Za-z0-9]", "_", symbol)}')
    if resp.status_code != 200:
        return None
    payload = resp.json()
    if payload.get('quoteSummary', {}).get('result'):
        return payload['quoteSummary']['result'][0]
    return None


def capture_chart(symbol, rng='1mo', interval='1d'):
    resp = fetch('https://query1.finance.yahoo.com/v8/finance/chart'
                 f'/{symbol}?range={rng}&interval={interval}'
                 '&includePrePost=false&lang=en-US&region=US',
                 name=f'chart_{re.sub(r"[^A-Za-z0-9]", "_", symbol)}')
    if resp.status_code != 200:
        return None
    return resp.json().get('chart', {}).get('result', [None])[0]


def capture_earnings(crumb, start, end, name):
    """Earnings calendar window — the exact visualization the calendar page
    itself issues (entityIdType sp_earnings, btwn startdatetime)."""
    body = {
        'sortType': 'DESC', 'entityIdType': 'sp_earnings',
        'sortField': 'intradaymarketcap',
        'includeFields': [
            'ticker', 'companyshortname', 'eventname', 'startdatetime',
            'startdatetimetype', 'dateisestimate', 'epsestimate', 'epsactual',
            'epssurprisepct', 'timeZoneShortName', 'gmtOffsetMilliSeconds',
            'intradaymarketcap'],
        'query': {'operator': 'and', 'operands': [
            {'operator': 'btwn', 'operands': [
                'startdatetime', f'{start}T00:00:00-04:00',
                f'{end}T23:59:59-04:00']},
        ]},
        'size': 250, 'offset': 0, 'userId': '', 'userDataset': '',
        'quoteType': '', 'method': 'getDataForCalendar',
    }
    resp = fetch('https://query1.finance.yahoo.com/v1/finance/visualization'
                 f'?crumb={crumb}&lang=en-US&region=US',
                 kind='POST', body=body, name=name, sleep=2.0)
    if resp.status_code != 200:
        return None
    return resp.json()['finance']['result'][0]


def normalize_earnings(result):
    """Flatten the visualization response (columns + rows) into records."""
    records = []
    if not result:
        return records
    for doc in result.get('documents', []):
        cols = [c['id'] for c in doc['columns']]
        for row in doc.get('rows', []):
            rec = dict(zip(cols, row))
            rec['ticker'] = rec.get('ticker')
            records.append(rec)
    records.sort(key=lambda r: (r.get('startdatetime') or '', r.get('ticker') or ''))
    return records


def main():
    started = now_iso()
    print('== crumb')
    crumb = get_crumb()

    print('== sector tops')
    sector_tops = capture_sector_tops(crumb)
    print('== predefined screens')
    presets = capture_presets(crumb)
    print('== trending')
    trending = capture_trending()

    # ---- universe -----------------------------------------------------
    universe = {}
    for sector, quotes in sector_tops.items():
        for q in quotes:
            universe[q['symbol']] = q
    for scr_id, data in presets.items():
        for q in data['quotes']:
            sym = q.get('symbol') or q.get('ticker')
            if sym:
                universe.setdefault(sym, q)
    for sym in INDICES + FUTURES + CRYPTO + ETFS:
        universe.setdefault(sym, None)
    symbols = sorted(universe.keys())
    print(f'== universe: {len(symbols)} symbols')

    # ---- market strip + full quote snapshot (batched) ------------------
    strip = capture_quotes_batch(
        ['ES=F', 'NQ=F', 'YM=F', 'RTY=F', '^TNX', '^VIX', 'GC=F', 'BTC-USD', 'CL=F'],
        crumb, 'quote_strip')
    quotes = []
    for i in range(0, len(symbols), 60):
        chunk = symbols[i:i + 60]
        quotes.extend(capture_quotes_batch(chunk, crumb, f'quote_batch_{i//60}'))
    quotes = sorted({q['symbol']: q for q in quotes}.values(), key=lambda q: q['symbol'])
    print(f'== quote snapshot: {len(quotes)} quotes')

    # ---- per-symbol details (equities only need profiles) --------------
    details = {}
    charts = {}
    quote_type = {q['symbol']: q.get('quoteType') for q in quotes}
    for sym in symbols:
        details[sym] = capture_quote_summary(sym, crumb)
        charts[sym] = capture_chart(sym)
    print(f'== details: {sum(1 for v in details.values() if v)} / charts: '
          f'{sum(1 for v in charts.values() if v)}')

    # ---- earnings calendar: past week (actuals) + current + next -------
    # capture week anchored on 2026-09-29/30 (the mirror's snapshot week)
    windows = {
        'earnings_2026-09-14_2026-09-18': ('2026-09-14', '2026-09-18'),
        'earnings_2026-09-21_2026-09-25': ('2026-09-21', '2026-09-25'),
        'earnings_2026-09-28_2026-10-02': ('2026-09-28', '2026-10-02'),
        'earnings_2026-10-05_2026-10-09': ('2026-10-05', '2026-10-09'),
        'earnings_2026-10-12_2026-10-16': ('2026-10-12', '2026-10-16'),
    }
    earnings = {}
    for name, (start, end) in windows.items():
        result = capture_earnings(crumb, start, end, name)
        earnings[f'{start}..{end}'] = normalize_earnings(result)
        print(f'  earnings {start}..{end}: {len(earnings[f"{start}..{end}"])} events')

    # ---- persist -------------------------------------------------------
    (SOURCE / 'capture_meta.json').write_text(json.dumps({
        'site': 'yahoo_finance',
        'upstream': 'https://finance.yahoo.com/',
        'capture_started_utc': started,
        'capture_finished_utc': now_iso(),
        'crumb_note': 'Anonymous crumb flow (fc.yahoo.com cookie + '
                      '/v1/test/getcrumb), exactly the flow the live pages '
                      'use; no login, no anti-bot bypass.',
        'universe_size': len(symbols),
    }, indent=1))
    (SOURCE / 'market_strip.json').write_text(json.dumps(strip, indent=1))
    (SOURCE / 'quote_snapshot.json').write_text(json.dumps(quotes, indent=1))
    (SOURCE / 'quote_details.json').write_text(json.dumps(details, indent=1))
    (SOURCE / 'chart_series.json').write_text(json.dumps(charts, indent=1))
    (SOURCE / 'screener_presets.json').write_text(json.dumps(presets, indent=1))
    (SOURCE / 'sector_tops.json').write_text(json.dumps(sector_tops, indent=1))
    (SOURCE / 'trending.json').write_text(json.dumps(trending, indent=1))
    (SOURCE / 'earnings_calendar.json').write_text(json.dumps(earnings, indent=1))
    print('== done. source_data/ updated.')


if __name__ == '__main__':
    sys.exit(main())
