#!/usr/bin/env python3
"""Assemble the tracked source_data/*.json snapshots from the raw captures.

Input:  scraped_data/captures/*.raw (+ .meta.json sidecars) — the raw live
        captures from www.nyse.com (see capture_source_data*.py and
        capture_quotes.py).
Output: source_data/*.json — the tracked, deterministic snapshots the seed
        builder materializes into SQLite.

The quotes_light extraction keeps exactly the fields the light quote page
renders (quote header, company, board, total returns); the rich set keeps
the full response minus the option chains beyond the first ten expiry
dates (the upstream UI paginates options by expiry the same way) and with
the five-year daily history as compact rows.
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.dirname(HERE)
CAPTURES = os.path.join(SITE, 'scraped_data', 'captures')
SOURCE = os.path.join(SITE, 'source_data')
RICH_EXPIRIES = 10

sys.path.insert(0, HERE)
from capture_quotes import RICH_SYMBOLS, extract_light  # noqa: E402


def load_capture(slug: str):
    path = os.path.join(CAPTURES, slug + '.raw')
    with open(path, encoding='utf-8', errors='replace') as f:
        return f.read()


def load_json_capture(slug: str):
    return json.loads(load_capture(slug))


def dump(name, payload):
    path = os.path.join(SOURCE, name)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, sort_keys=True,
                  separators=(',', ':'))
    print(f'  source_data/{name}: {os.path.getsize(path)} bytes')


# ------------------------------------------------------------------ CMS --


def hydration_of(page: str):
    html = load_capture(page)
    idx = html.find('hydrationQueue.push(')
    if idx < 0:
        raise ValueError(f'no hydration state on {page}')
    end = html.find('</script>', idx)
    raw = html[idx + len('hydrationQueue.push('):end].rstrip().rstrip(';')
    data, _ = json.JSONDecoder().raw_decode(raw)
    return data


def rich_blocks(node):
    """Flatten a richTextNodes tree into [{tag, text}] blocks, preserving
    the upstream heading/paragraph structure."""
    out = []

    def walk(nodes, tag=None):
        for n in nodes:
            if not isinstance(n, dict):
                continue
            ntype = n.get('type') or tag
            text = n.get('text', '')
            if text and text.strip():
                out.append({'tag': ntype or 'p', 'text': text.strip()})
            walk(n.get('children', []), ntype if ntype in (
                'h1', 'h2', 'h3', 'h4') else tag)

    walk(node)
    merged = []
    for blk in out:
        if (merged and merged[-1]['tag'] == blk['tag']
                and blk['tag'] == 'p'
                and not merged[-1]['text'].endswith(('.', '!', '?', ':'))
                and len(merged[-1]['text']) + len(blk['text']) < 400):
            merged[-1]['text'] = merged[-1]['text'].rstrip() + ' ' + blk['text']
        else:
            merged.append(blk)
    return merged


def collect_rich_blocks(node, blocks=None):
    """Every rich-text block in hydration-tree order."""
    if blocks is None:
        blocks = []
    if isinstance(node, dict):
        if 'richTextNodes' in node:
            blocks.append(rich_blocks(node['richTextNodes']))
        for v in node.values():
            collect_rich_blocks(v, blocks)
    elif isinstance(node, list):
        for v in node:
            collect_rich_blocks(v, blocks)
    return blocks


def _imgs_in(page):
    """All <img> references in a captured CMS page, keyed by src."""
    html = load_capture(page)
    out = {}
    for m in re.finditer(r'<img[^>]+>', html):
        tag = m.group(0)
        src = re.search(r'src="([^"]+)"', tag)
        alt = re.search(r'alt="([^"]*)"', tag)
        if src:
            out[src.group(1)] = (alt.group(1) if alt else '')
    return out


def home_content():
    html = load_capture('_index')
    hero = {
        'headline': 'The home of market-defining IPOs',
        'subline': ('The New York Stock Exchange is where icons and '
                    'disruptors come to shape what’s next'),
        'cta': 'Learn more',
        'cta_href': '/listings',
    }
    m = (re.search(r'id="hero-box".*?<h1[^>]*>\s*([^<]+?)\s*</h1>',
                   html, re.S)
         or re.search(r'<section id="hero".*?<h1[^>]*>\s*([^<]+?)\s*</h1>',
                      html, re.S))
    if m:
        hero['headline'] = m.group(1).strip()
    blocks = [b for bl in collect_rich_blocks(hydration_of('_index'))
               for b in bl]
    # The daily market article: authored blocks between the byline and the
    # "Expand article" CTA on the upstream page.
    article = {'author': 'Michael P. Reinking, CFA',
               'role': 'Sr. Market Strategist',
               'date': 'September 29, 2026 at 1:30 p.m. EST',
               'title': "Today's Stock Market",
               'paragraphs': []}
    texts = [b['text'] for b in blocks]
    start = next((i for i, t in enumerate(texts)
                  if t.startswith('Yesterday')), None)
    if start is not None:
        para = []
        for t in texts[start:]:
            if t in ('Expand article', 'Weekly market recap',
                     'Catch equity highlights and market-moving news.'):
                break
            para.append(t)
        article['paragraphs'] = para
    cards = []
    for title, blurb, cta in (
            ('Weekly market recap',
             'Catch equity highlights and market-moving news.', 'READ NOW'),
            ('2026 Q1 earnings preview',
             'Seeing through the smoke.', 'READ NOW'),
            ('2026 trading calendar',
             'Holidays and other market related events.', 'READ NOW')):
        cards.append({'title': title, 'blurb': blurb, 'cta': cta})
    shows = []
    for name in ('Market Update', 'NYSE Live'):
        i = next((k for k, t in enumerate(texts) if t.startswith(name)), None)
        if i is not None:
            blurb = texts[i][len(name):].strip() or (
                texts[i + 1] if i + 1 < len(texts) else '')
            shows.append({'name': name, 'blurb': blurb})
    whats_next = []
    imgs = _imgs_in('_index')
    for title, img_key in (
            ('All-in Liquidity Summit',
             '/publicdocs/images/NYSE_Homepage_All_in_Liquidity_Summit.jpg'),
            ('America 250', None),
            ('LatAm Tech Forum: Questions from Founders',
             '/publicdocs/images/NYSE_Homepage_LatAM_Tech_Forum.jpg')):
        i = next((k for k, t in enumerate(texts) if t.startswith(title)), None)
        if i is not None:
            body = texts[i + 1] if i + 1 < len(texts) else ''
            image = img_key if img_key in imgs else None
            whats_next.append({'title': title, 'body': body, 'image': image})
    collage = sorted(
        src for src in _imgs_in('_index')
        if 'NYSE_Homepage_Collage_' in src)
    ticker_note = 'Market data delayed minimum of 15 minutes'
    return {'hero': hero, 'article': article, 'cards': cards,
            'shows': shows, 'whats_next': whats_next,
            'collage': sorted(set(collage)), 'ticker_note': ticker_note}


def history_content():
    blocks = [b for bl in collect_rich_blocks(hydration_of('_history_of_nyse'))
              for b in bl]
    sections = []
    section = None
    for blk in blocks:
        t, txt = blk['tag'], blk['text']
        if t in ('h1', 'h2', 'h3'):
            if section:
                sections.append(section)
            section = {'heading': txt, 'paragraphs': []}
        elif section is not None:
            section['paragraphs'].append(txt)
    if section:
        sections.append(section)
    html = load_capture('_history_of_nyse')
    images = [{'src': src, 'alt': alt} for src, alt in sorted(
        _imgs_in('_history_of_nyse').items())
        if 'favicon' not in src and 'NYSEConnect' not in src]
    return {'sections': sections, 'images': images}


def listings_content():
    blocks = [b for bl in collect_rich_blocks(hydration_of('_listings'))
              for b in bl]
    sections = []
    section = None
    for blk in blocks:
        t, txt = blk['tag'], blk['text']
        if t in ('h1', 'h2', 'h3'):
            if section:
                sections.append(section)
            section = {'heading': txt, 'paragraphs': []}
        elif section is not None and t == 'p':
            section['paragraphs'].append(txt)
    if section:
        sections.append(section)
    html = load_capture('_listings')
    hero = re.search(r'src="(/publicdocs/images/Hero-[^"]+)"', html)
    return {'sections': sections,
            'hero_image': hero.group(1) if hero else None}


def bell_content():
    blocks = [b for bl in collect_rich_blocks(hydration_of('_bell_calendar'))
              for b in bl]
    return {'intro': [b['text'] for b in blocks
                      if b['tag'] == 'p' and len(b['text']) > 60][:4]}


def ipo_content():
    blocks = [b for bl in collect_rich_blocks(
        hydration_of('_ipo_center_recent_ipo')) for b in bl]
    return {'intro': [b['text'] for b in blocks
                      if b['tag'] == 'p' and len(b['text']) > 60][:3]}


# ------------------------------------------------------------- snapshots --


def directories():
    out = {}
    for tab, slug in (('equity', 'directory_equity'),
                     ('etf', 'directory_etf'),
                     ('reit', 'directory_reit'),
                     ('index', 'directory_index')):
        rows = json.load(open(os.path.join(CAPTURES, f'{slug}.json')))
        norm = []
        for r in rows:
            url = r['url']
            if '/quote/index/' in url:
                mic = 'IDX'
                symbol = url.split('/quote/index/')[1]
            else:
                mic = url.split('/quote/')[1].split(':')[0]
                symbol = url.split(':')[1]
            norm.append({'symbol': r['normalizedTicker'],
                         'name': r['instrumentName'],
                         'mic': mic,
                         'quote_url': url})
        out[tab] = norm
    return out


def bell_events():
    events = []
    for page in range(1, 16):
        slug = ('_api_events_filter_filterToken__startDate__endDate__type__'
                f'pageNumber_{page}_maxResultsPerPage_20_company_'
                'sortOrder_down')
        payload = load_json_capture(slug)
        for r in payload['results']:
            events.append({
                'id': r['uniqueId'],
                'title': r['title'],
                'type': r['calendarEventType']['name'],
                'start': r['startDateTime'],
                'end': r['endDateTime'],
                'timezone': r.get('timezone'),
                'description': r.get('description') or '',
                'image': r.get('filePath') or '',
                'media': [{'name': m['name'], 'value': m['value']}
                          for m in (r.get('eventMedia') or [])],
            })
    return events


def market_movers():
    out = {}
    for cat in ('nyse', 'nyse_american'):
        slug = f'_api_market_mover_data_category_{cat}'
        out[cat] = load_json_capture(slug)
    return out


def ipo_snapshots():
    dump('ipo_calendar.json', load_json_capture(
        '_api_ipo_center_calendar'))
    dump('ipo_monthly_execution.json', load_json_capture(
        '_api_ipo_center_monthly_execution_ipo'))
    dump('ipo_largest_recent.json', load_json_capture(
        '_api_ipo_center_largest_recent_ipo'))
    dump('ipo_price_perf_by_sector.json', load_json_capture(
        '_api_ipo_center_price_perf_by_sector_ipo'))
    dump('ipo_backlog.json', load_json_capture(
        '_api_ipo_center_backlog_ipo'))


def rich_quote_extract(data):
    """Trim a rich quote response: full quote/company/board/returns, the
    first RICH_EXPIRIES option expiries, the full daily history."""
    options = data.get('options') or {}
    calls = options.get('callList') or []
    puts = options.get('putList') or []
    expiries = []
    for c in calls:
        if c.get('exp') not in expiries:
            expiries.append(c.get('exp'))
    keep = expiries[:RICH_EXPIRIES]
    trim_calls = [c for c in calls if c.get('exp') in keep]
    trim_puts = [p for p in puts if p.get('exp') in keep]
    hist = (data.get('quoteHistory') or {}).get('historyList') or []
    return {
        'quote': data.get('quote'),
        'company': (data.get('boardMember') or {}).get('company'),
        'board': (data.get('boardMember') or {}).get('boardMembers') or [],
        'returns': data.get('totalReturns'),
        'options': {'ratio': options.get('ratio'),
                    'expiries': keep,
                    'callList': trim_calls,
                    'putList': trim_puts},
        'history': [[b['date'], b['open'], b['high'], b['low'],
                     b['close'], b['volume']] for b in hist],
    }


def main():
    os.makedirs(SOURCE, exist_ok=True)
    print('[source] directories', flush=True)
    dump('directories.json', directories())
    print('[source] bell events', flush=True)
    dump('bell_events.json', bell_events())
    print('[source] market movers', flush=True)
    dump('market_movers.json', market_movers())
    print('[source] IPO center', flush=True)
    ipo_snapshots()
    print('[source] CMS content', flush=True)
    dump('home_content.json', home_content())
    dump('history_content.json', history_content())
    dump('listings_content.json', listings_content())
    dump('bell_content.json', bell_content())
    dump('ipo_content.json', ipo_content())

    print('[source] quotes (light walk + rich set)', flush=True)
    light = {}
    rich = {}
    quote_files = sorted(
        f for f in os.listdir(CAPTURES)
        if f.startswith('_api_nyseservice_v1_quotes_symbol_')
        and f.endswith('.raw'))
    for fname in quote_files:
        symbol = fname[len('_api_nyseservice_v1_quotes_symbol_'):-4]
        path = os.path.join(CAPTURES, fname)
        if os.path.getsize(path) == 0:
            continue
        with open(path, 'rb') as f:
            payload = f.read()
        try:
            data = json.loads(payload)
        except ValueError:
            continue
        bare = symbol.lstrip('$')
        symbol = bare
        if bare in RICH_SYMBOLS and data.get('quote'):
            rich[symbol] = rich_quote_extract(data)
        elif data.get('quote'):
            light[symbol] = extract_light(payload, symbol)
    dump('quotes_light.json', light)
    dump('quotes_rich.json', rich)
    captured = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    dump('capture_summary.json', {
        'captured_at_utc': captured,
        'quote_files_seen': len(quote_files),
        'light_symbols': len(light),
        'rich_symbols': len(rich),
    })
    print('[source] done', flush=True)


if __name__ == '__main__':
    main()
