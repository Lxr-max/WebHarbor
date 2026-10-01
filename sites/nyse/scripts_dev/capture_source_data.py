#!/usr/bin/env python3
"""Shared capture helpers for the live NYSE.com scrape.

Every network call is a real upstream capture from www.nyse.com. Each raw
response is saved under scraped_data/captures/ (gitignored) with a
.meta.json sidecar recording the exact URL, HTTP status and capture
timestamp; the tracked source_data/*.json files are derived from those
captures by build_source_data.py.

The quotes endpoints sit behind Cloudflare bot scoring that hard-429s
Python's own TLS client while accepting curl's handshake, so every fetch
shells out to curl with a browser user agent, keeps a conservative fixed
pace and backs off exponentially on 429s.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time

BASE = 'https://www.nyse.com'
UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/120.0 Safari/537.36')
HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.dirname(HERE)
CAPTURES = os.path.join(SITE, 'scraped_data', 'captures')

os.makedirs(CAPTURES, exist_ok=True)


def _slug(url: str) -> str:
    return ''.join(c if c.isalnum() else '_' for c in url.split('nyse.com', 1)[1])[:150]


def get(url: str, body: dict | None = None, retries: int = 8,
        raw: bool = False, skip_if_captured: bool = False):
    """Fetch a URL (POST a JSON body if given), save the raw capture with a
    meta sidecar, and return the parsed payload (or raw bytes)."""
    name = _slug(url)
    out_path = os.path.join(CAPTURES, name + '.raw')
    meta_path = os.path.join(CAPTURES, name + '.meta.json')
    if skip_if_captured and os.path.exists(meta_path):
        with open(meta_path, encoding='utf-8') as f:
            prior = json.load(f)
        if prior.get('status') == 200:
            payload = open(out_path, 'rb').read()
            if not payload:
                return None
            if raw:
                return payload
            try:
                return json.loads(payload)
            except (ValueError, UnicodeDecodeError):
                return payload.decode('utf-8', errors='replace')

    cmd = ['curl', '-s', '--max-time', '60', '-A', UA,
           '-w', '\n%{http_code}', '-o', out_path]
    if body is not None:
        cmd += ['-H', 'Content-Type: application/json',
                '-H', 'Origin: https://www.nyse.com',
                '-X', 'POST', '--data', json.dumps(body)]
    cmd.append(url)

    last_err = None
    for attempt in range(retries):
        proc = subprocess.run(cmd, capture_output=True, text=True)
        code = (proc.stdout.strip().splitlines() or ['000'])[-1]
        if code == '200':
            payload = open(out_path, 'rb').read()
            meta = {'url': url, 'method': 'POST' if body is not None else 'GET',
                    'status': 200,
                    'captured_at_utc': time.strftime(
                        '%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                    'bytes': len(payload)}
            if body is not None:
                meta['request_body'] = body
            open(meta_path, 'w').write(json.dumps(meta, indent=1))
            if not payload:
                return None
            if raw:
                return payload
            try:
                return json.loads(payload)
            except (ValueError, UnicodeDecodeError):
                return payload.decode('utf-8', errors='replace')
        if code == '429':
            pause = min(300.0, 45.0 * (attempt + 1))
            print(f'  429 on {url[:80]}: pausing {pause:.0f}s',
                  flush=True)
            time.sleep(pause)
            continue
        if code in ('500', '502', '503', '504', '000'):
            last_err = code
            time.sleep(20.0)
            continue
        # Genuine upstream 4xx: record the status and return nothing.
        meta = {'url': url, 'method': 'POST' if body is not None else 'GET',
                'status': int(code) if code.isdigit() else 0,
                'captured_at_utc': time.strftime(
                    '%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                'bytes': 0}
        if body is not None:
            meta['request_body'] = body
        open(out_path, 'wb').write(b'')
        open(meta_path, 'w').write(json.dumps(meta, indent=1))
        return None
    raise RuntimeError(f'failed after {retries} retries: {url}: {last_err}')


PACE = float(os.environ.get('NYSE_CAPTURE_PACE', '1.0'))
_LAST_REQUEST = [0.0]


def paced_get(*args, **kwargs):
    """get() with a polite inter-request delay (NYSE_CAPTURE_PACE seconds)."""
    wait = PACE - (time.monotonic() - _LAST_REQUEST[0])
    if wait > 0:
        time.sleep(wait)
    _LAST_REQUEST[0] = time.monotonic()
    return get(*args, **kwargs)


def capture_directory(instrument_type: str, page_size: int = 200):
    """Walk every page of the listings directory for one instrument type."""
    rows = []
    page = 1
    while True:
        payload = get(f'{BASE}/api/quotes/filter', body={
            'instrumentType': instrument_type, 'pageNumber': page,
            'sortColumn': 'NORMALIZED_TICKER', 'sortOrder': 'ASC',
            'maxResultsPerPage': page_size, 'filterToken': ''})
        if not payload:
            break
        rows.extend(payload)
        total = payload[0].get('total', 0)
        print(f'  {instrument_type} page {page}: +{len(payload)} (total {total})',
              flush=True)
        if len(rows) >= total or not payload:
            break
        page += 1
    return rows


def main():
    t0 = time.time()
    print('[capture] listings directory — EQUITY', flush=True)
    equity = capture_directory('EQUITY')
    json.dump(equity, open(os.path.join(CAPTURES, 'directory_equity.json'), 'w'))
    print('[capture] listings directory — INDEX', flush=True)
    index = capture_directory('INDEX', page_size=100)
    json.dump(index, open(os.path.join(CAPTURES, 'directory_index.json'), 'w'))

    print(f'[capture] done: {len(equity)} equity rows, {len(index)} index rows '
          f'in {time.time()-t0:.0f}s', flush=True)


if __name__ == '__main__':
    main()
