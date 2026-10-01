#!/usr/bin/env python3
"""Fetch bodies for finance.yahoo.com-hosted articles that came from the
per-symbol news stream (capture_news.py only pulls bodies for the
topic-stream articles).

Fills source_data/news_bodies.json — keyed by the article's upstream link —
with the JSON-LD metadata and the server-rendered <article> paragraphs, and
merges any previously missing records. Raw pages archive under
scraped_data/captures/ with .meta.json sidecars, same as capture_news.py.

Usage (from sites/yahoo_finance):
    python3 scripts_dev/capture_article_bodies.py
"""
from __future__ import annotations

import json
import re
import sys
import time
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from urllib.parse import urlsplit

import requests

HERE = Path(__file__).resolve().parent.parent
CAPTURES = HERE / 'scraped_data' / 'captures'
SOURCE = HERE / 'source_data'

UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36')

session = requests.Session()
session.headers.update({'User-Agent': UA, 'Accept-Language': 'en-US,en;q=0.9',
                        'Referer': 'https://finance.yahoo.com/'})


def now_iso():
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def strip_tags(fragment):
    return ' '.join(unescape(re.sub(r'<[^>]+>', ' ', fragment)).split())


def fetch_article(url, stem):
    resp = session.get(url, timeout=45)
    (CAPTURES / f'{stem}.raw').write_bytes(resp.content)
    (CAPTURES / f'{stem}.meta.json').write_text(json.dumps({
        'url': url, 'method': 'GET', 'status': resp.status_code,
        'captured_at': now_iso(), 'bytes': len(resp.content),
    }, indent=1))
    if resp.status_code != 200:
        return None
    src = resp.text
    record = {'paragraphs': [], 'author': None, 'published': None,
              'modified': None, 'image': None}
    m = re.search(r'<script type="application/ld\+json">(.*?)</script>',
                  src, re.S)
    if m:
        try:
            ld = json.loads(m.group(1))
            if isinstance(ld, list):
                ld = ld[0]
            author = ld.get('author')
            if isinstance(author, dict):
                record['author'] = author.get('name')
            elif isinstance(author, str):
                record['author'] = author
            record['published'] = ld.get('datePublished')
            record['modified'] = ld.get('dateModified')
            img = ld.get('image')
            if isinstance(img, dict):
                record['image'] = img.get('url')
            elif isinstance(img, str):
                record['image'] = img
        except (ValueError, TypeError, AttributeError):
            pass
    am = re.search(r'<article[^>]*>(.*?)</article>', src, re.S)
    if am:
        paras = re.findall(r'<p[^>]*>(.*?)</p>', am.group(1), re.S)
        record['paragraphs'] = [strip_tags(p) for p in paras
                                if strip_tags(p)][:14]
    return record


def main():
    symbol_news = json.loads((SOURCE / 'symbol_news.json').read_text())
    existing = {}
    path = SOURCE / 'news_bodies.json'
    if path.exists():
        existing = json.loads(path.read_text())
    targets = [i['link'] for i in symbol_news
               if 'finance.yahoo.com' in (i.get('link') or '')
               and i.get('link') not in existing]
    print(f'== fetching {len(targets)} article bodies '
          f'({len(existing)} already captured)')
    fetched = 0
    for i, link in enumerate(targets):
        stem = 'article_' + re.sub(r'[^A-Za-z0-9]+', '_',
                                   urlsplit(link).path)[:90]
        try:
            record = fetch_article(link, stem)
        except requests.RequestException:
            record = None
        if record:
            existing[link] = record
            fetched += 1
        time.sleep(0.9)
        if (i + 1) % 40 == 0:
            print(f'   {i + 1}/{len(targets)} fetched={fetched}')
    path.write_text(json.dumps(existing, indent=1))
    withparas = sum(1 for r in existing.values() if r.get('paragraphs'))
    print(f'== done: {len(existing)} bodies captured, {withparas} with '
          f'paragraphs')


if __name__ == '__main__':
    sys.exit(main())
