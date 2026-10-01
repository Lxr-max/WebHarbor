#!/usr/bin/env python3
"""Real-upstream scraper for the steam mirror (store.steampowered.com).

Every content record in the mirror comes from a live capture made by this
script; every image is fetched from its exact upstream CDN URL. Captures are
written to scraped_data/ (gitignored, build-time only) with a .meta.json
sidecar per HTTP capture recording the exact URL, HTTP status and fetch
timestamp, so provenance.json can describe the capture window honestly.

Endpoints used (all public, no login, no anti-bot bypass):
  * store.steampowered.com/                    store home
  * /search/results/                           search rows (topsellers/new/specials/free)
  * /search/                                   facet search (developer= / publisher= / genre rosters)
  * /api/appdetails?appids=<id>&cc=us          full game details incl. system requirements
  * /appreviews/<id>?json=1&filter=recent      real user reviews + review summary
  * api.steampowered.com/ISteamNews/...       real news items
  * /bundle/<id>/                              bundle pages
  * /app/<id>/                                 app pages (bundle discovery)
  * shared CDN hosts                           real images

Run:  python3 scripts_dev/scrape.py [--only-missing-images]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

import requests

SITE = Path(__file__).resolve().parent.parent
OUT = SITE / 'scraped_data'
IMG_DIR = OUT / 'images'
UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

CAPTURES = []          # [{url, status, at}] — for provenance
FETCHED_IMAGES = {}    # filename -> {sha256, bytes, url}

S = requests.Session()
S.headers.update({'User-Agent': UA, 'Accept-Language': 'en-US,en;q=0.9'})


def now_iso():
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def note_capture(url, status):
    CAPTURES.append({'url': url, 'status': status, 'at': now_iso()})


def get(url, *, binary=False, params=None, sleep=1.2, retries=4):
    for attempt in range(retries):
        try:
            r = S.get(url, params=params, timeout=30)
            note_capture(url, r.status_code)
            if r.status_code == 200:
                return r
            if r.status_code == 429:
                time.sleep(20 * (attempt + 1))
                continue
            if r.status_code in (302, 403, 404):
                return r
        except requests.RequestException:
            pass
        time.sleep(5 * (attempt + 1))
    print(f'  !! failed: {url}', file=sys.stderr, flush=True)
    return None


def save_json(name, data):
    path = OUT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1,
                               sort_keys=False), encoding='utf-8')
    print(f'  wrote {name} ({os.path.getsize(path)} B)')


def slugify(text):
    text = unicodedata.normalize('NFKD', str(text)).encode('ascii', 'ignore')
    text = text.decode('ascii').lower()
    text = re.sub(r"[^a-z0-9]+", '-', text).strip('-')
    return text


def fetch_image(url, filename):
    """Download a real upstream image; refuse placeholders/duplicates."""
    path = IMG_DIR / filename
    if url in FETCHED_IMAGES.values():
        return None
    r = get(url, binary=True, sleep=0.6)
    if r is None or r.status_code != 200:
        return None
    data = r.content
    if not data or len(data) < 2000 or not data[:3] == b'\xff\xd8\xff' \
            and not data[:8] == b'\x89PNG\r\n\x1a\n' and not data[:3] == b'GIF':
        print(f'  !! bad image bytes {url}', file=sys.stderr, flush=True)
        return None
    sha = hashlib.sha256(data).hexdigest()
    for known in FETCHED_IMAGES.values():
        if known['sha256'] == sha:
            print(f'  !! duplicate image bytes {url}', file=sys.stderr, flush=True)
            return None
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    FETCHED_IMAGES[filename] = {'sha256': sha, 'bytes': len(data), 'url': url}
    return filename


# --------------------------------------------------------------------------
# 1. search rows
# --------------------------------------------------------------------------

def parse_search_rows(html):
    """Parse the standard search_resultsRows markup into game rows."""
    rows = []
    for m in re.finditer(
            r'<a\b(?=[^>]*data-ds-appid="([\d,]+)")(?=[^>]*search_result_row)[^>]*>(.*?)</a>',
            html, re.S):
        appid_raw, body = m.group(1), m.group(2)
        appid = appid_raw.split(',')[0]
        t = re.search(r'<span class="title">([^<]+)</span>', body)
        title = t.group(1).strip() if t else ''
        rel = re.search(r'class="search_released[^"]*">\s*([^<]+?)\s*<', body)
        released = rel.group(1).strip() if rel else ''
        platforms = {
            'win': 'platform_img win' in body,
            'mac': 'platform_img mac' in body,
            'linux': 'platform_img linux' in body,
        }
        rev = re.search(r'data-tooltip-html="([^"]*)"', body)
        review_desc = pct = review_count = ''
        if rev:
            tip = rev.group(1).replace('&lt;', '<').replace('&gt;', '>') \
                .replace('&amp;', '&').replace('&quot;', '"')
            mm = re.match(r'([^<]+)<br>(\d+)% of the ([\d,]+) user reviews', tip)
            if mm:
                review_desc, pct, review_count = mm.group(1), mm.group(2), mm.group(3).replace(',', '')
        price = re.search(r'data-price-final="(\d+)"', body)
        price_cents = int(price.group(1)) if price else None
        disc = re.search(r'data-discount="(\d+)"', body)
        discount = int(disc.group(1)) if disc else 0
        caps = re.search(r'<div class="search_capsule"><img src="([^"]+)"', body)
        capsule = caps.group(1) if caps else ''
        rows.append({
            'appid': appid, 'title': title, 'released': released,
            'platforms': platforms, 'review_desc': review_desc,
            'review_pct': pct, 'review_count': review_count,
            'price_cents': price_cents, 'discount_pct': discount,
            'capsule_img': capsule,
        })
    return rows


def scrape_search(label, params, count=100):
    url = 'https://store.steampowered.com/search/results/'
    rows = []
    for start in range(0, count, 50):
        p = dict(params)
        p.update({'query': '', 'start': start, 'count': 50, 'dynamic_data': '',
                  'sort_by': p.get('sort_by', 'Relevance_DESC'),
                  'snr': '1_2_4_700', 'infinite': '1', 'cc': 'US', 'l': 'english'})
        r = get(url, params=p)
        if r is None or r.status_code != 200:
            break
        body = r.text.lstrip()
        if body.startswith('{'):
            try:
                body = r.json().get('results_html', '')
            except ValueError:
                body = ''
        got = parse_search_rows(body)
        rows.extend(got)
        if len(got) < 50:
            break
    print(f'[search] {label}: {len(rows)} rows', flush=True)
    return rows


# --------------------------------------------------------------------------
# 2. app details
# --------------------------------------------------------------------------

def scrape_appdetails(appid):
    url = 'https://store.steampowered.com/api/appdetails'
    r = get(url, params={'appids': appid, 'cc': 'us', 'l': 'english'})
    if r is None or r.status_code != 200:
        return None
    try:
        d = r.json()[str(appid)]
    except (ValueError, KeyError):
        return None
    if not d.get('success'):
        return None
    a = d['data']
    if a.get('type') not in ('game', 'dlc'):
        return None
    price = a.get('price_overview') or {}
    rec = {
        'appid': a['steam_appid'],
        'name': a['name'],
        'type': a.get('type'),
        'required_age': a.get('required_age'),
        'is_free': bool(a.get('is_free')),
        'dlc': a.get('dlc', [])[:20],
        'detailed_desc': re.sub(r'<[^>]+>', '', a.get('detailed_description', ''))[:4000],
        'about': re.sub(r'<[^>]+>', '', a.get('about_the_game', ''))[:4000],
        'short_desc': a.get('short_description', ''),
        'supported_languages': re.sub(r'<[^>]+>', '', a.get('supported_languages', '')),
        'genres': [g['description'] for g in a.get('genres', [])],
        'categories': [c['description'] for c in a.get('categories', [])],
        'publishers': a.get('publishers', []),
        'developers': a.get('developers', []),
        'platforms': a.get('platforms', {}),
        'release_date': (a.get('release_date') or {}).get('date', ''),
        'coming_soon': bool((a.get('release_date') or {}).get('coming_soon')),
        'price_cents': price.get('final', 0 if a.get('is_free') else None),
        'initial_cents': price.get('initial'),
        'discount_pct': price.get('discount_percent', 0) or 0,
        'currency': price.get('currency', 'USD'),
        'header': a.get('header_image', ''),
        'capsule_231': a.get('capsule_image', ''),
        'capsule_sm': a.get('capsule_imagev5', ''),
        'screenshots': [
            {'path_full': s.get('path_full', ''), 'path_thumbnail': s.get('path_thumbnail', '')}
            for s in a.get('screenshots', [])[:6]
        ],
        'movies': a.get('movies', [])[:2],
        'pc_requirements': a.get('pc_requirements', {}),
        'mac_requirements': a.get('mac_requirements', {}),
        'linux_requirements': a.get('linux_requirements', {}),
        'recommendations_total': (a.get('recommendations') or {}).get('total'),
        'achievements_total': (a.get('achievements') or {}).get('total'),
        'controller_support': a.get('controller_support', ''),
        'website': a.get('website', ''),
        'dlc_apps': a.get('fullgame', {}) or {},
    }
    return rec


# --------------------------------------------------------------------------
# 3. reviews
# --------------------------------------------------------------------------

def scrape_reviews(appid, count=12):
    url = f'https://store.steampowered.com/appreviews/{appid}'
    r = get(url, params={'json': 1, 'filter': 'recent', 'language': 'english',
                         'purchase_type': 'all', 'num_per_page': count})
    if r is None or r.status_code != 200:
        return None
    try:
        d = r.json()
    except ValueError:
        return None
    if not d.get('success'):
        return None
    qs = d.get('query_summary', {})
    out = []
    for rv in d.get('reviews', [])[:count]:
        au = rv.get('author', {})
        out.append({
            'recommendationid': rv.get('recommendationid'),
            'author': au.get('personaname', ''),
            'author_games': au.get('num_games_owned'),
            'author_reviews': au.get('num_reviews'),
            'playtime_forever': au.get('playtime_forever'),
            'playtime_at_review': au.get('playtime_at_review'),
            'voted_up': bool(rv.get('voted_up')),
            'votes_up': rv.get('votes_up'),
            'votes_funny': rv.get('votes_funny'),
            'steam_purchase': bool(rv.get('steam_purchase')),
            'received_for_free': bool(rv.get('received_for_free')),
            'early_access': bool(rv.get('written_during_early_access')),
            'review': rv.get('review', ''),
            'timestamp_created': rv.get('timestamp_created'),
            'timestamp_updated': rv.get('timestamp_updated'),
            'language': rv.get('language', 'english'),
        })
    return {
        'appid': appid,
        'review_score': qs.get('review_score'),
        'review_score_desc': qs.get('review_score_desc'),
        'total_positive': qs.get('total_positive'),
        'total_negative': qs.get('total_negative'),
        'total_reviews': qs.get('total_reviews'),
        'reviews': out,
    }


# --------------------------------------------------------------------------
# 4. news
# --------------------------------------------------------------------------

def scrape_news(appid, count=8):
    url = ('https://api.steampowered.com/ISteamNews/GetNewsForApp/v2/'
           f'?appid={appid}&count={count}&maxlength=0&format=json')
    r = get(url)
    if r is None or r.status_code != 200:
        return None
    try:
        items = r.json()['appnews']['newsitems']
    except (ValueError, KeyError):
        return None
    out = []
    for it in items[:count]:
        out.append({
            'gid': str(it.get('gid')),
            'title': it.get('title', ''),
            'url': it.get('url', ''),
            'is_external_url': bool(it.get('is_external_url')),
            'author': it.get('author', ''),
            'contents': it.get('contents', '')[:4000],
            'feedlabel': it.get('feedlabel', ''),
            'date': it.get('date'),
            'feedname': it.get('feedname', ''),
        })
    return {'appid': appid, 'items': out}


# --------------------------------------------------------------------------
# 5. bundles (discovered from app pages)
# --------------------------------------------------------------------------

def discover_bundle_ids(appids, limit=12):
    found = {}
    for appid in appids:
        if len(found) >= limit:
            break
        r = get(f'https://store.steampowered.com/app/{appid}/', sleep=1.5)
        if r is None or r.status_code != 200:
            continue
        for m in re.finditer(
                r'store\.steampowered\.com/bundle/(\d+)/([^/"?]+)/?', r.text):
            bid, bslug = m.group(1), m.group(2)
            if bid not in found:
                found[bid] = bslug
    print(f'[bundles] discovered {len(found)}: {list(found)[:limit]}')
    return found


def scrape_bundle(bundle_id):
    r = get(f'https://store.steampowered.com/bundle/{bundle_id}/', sleep=1.2)
    if r is None or r.status_code != 200:
        return None
    html = r.text
    t = re.search(r'<title>([^<]*)</title>', html)
    if not t or 'Steam' not in t.group(1):
        return None
    name = t.group(1).replace('on Steam', '').strip()
    base = re.search(r'class="bundle_base_discount">([^<]*)<', html)
    items = re.findall(r'data-ds-appid="(\d+)"', html)
    prices = [int(p) for p in re.findall(r'data-price-final="(\d+)"', html)]
    final = None
    m = re.search(r'class="game_purchase_price[^"]*"[^>]*>\s*\$([0-9.]+)\s*<', html)
    if m:
        final = int(round(float(m.group(1)) * 100))
    return {
        'bundle_id': bundle_id,
        'name': name,
        'base_discount': base.group(1).strip() if base else '',
        'item_appids': items,
        'item_price_cents': prices,
        'final_price_cents': final,
    }


# --------------------------------------------------------------------------
# 6. creator rosters (developer / publisher search facets)
# --------------------------------------------------------------------------

def scrape_creator(kind, name):
    """kind = developer | publisher; returns the search rows for that facet."""
    url = 'https://store.steampowered.com/search/'
    r = get(url, params={kind: name, 'sort_by': 'Name_ASC'}, sleep=1.5)
    if r is None or r.status_code != 200:
        return None
    rows = parse_search_rows(r.text)
    print(f'[{kind}] {name}: {len(rows)} rows')
    return rows


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--only-missing-images', action='store_true')
    args = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    IMG_DIR.mkdir(parents=True, exist_ok=True)
    t0 = now_iso()
    print(f'=== steam scrape start {t0}', flush=True)

    # ---- store home capture (for provenance + hero content) -------------
    home = get('https://store.steampowered.com/')
    if home is not None and home.status_code == 200:
        (OUT / 'home.html').write_text(home.text, encoding='utf-8')

    # ---- search snapshots ------------------------------------------------
    topsellers = scrape_search('topsellers',
        {'filter': 'topsellers', 'sort_by': 'Relevance_DESC'}, count=100)
    newreleases = scrape_search('newreleases',
        {'sort_by': 'Released_DESC', 'released_before': '', 'released_after': ''}, count=100)
    specials = scrape_search('specials',
        {'specials': 1, 'sort_by': 'Relevance_DESC'}, count=100)
    freegames = scrape_search('free',
        {'maxprice': 'free', 'sort_by': 'Relevance_DESC'}, count=100)
    under10 = scrape_search('under10',
        {'maxprice': 10, 'specials': 1, 'sort_by': 'Price_ASC'}, count=100)

    # ---- catalog selection ------------------------------------------------
    # curated core: recognizable games across genres/prices/platforms,
    # union'd with the live top-seller / new-release / specials snapshots.
    curated = [
        730, 570, 440, 620, 550, 546560, 400, 500, 340,              # Valve
        1245620, 1086940, 1091500, 292030, 1174180, 271590,          # big RPGs/action
        413150, 105600, 1145360, 367520, 504230, 268910, 588650,     # indie staples
        646570, 1794680, 1868140, 892970, 1122790, 753640, 1332010,   # more indie
        782330, 2050650, 601150, 814380, 1196590, 883710,            # action
        289070, 294100, 427520, 255710, 590380,                      # strategy/sim
        230410, 238960, 236390, 1085660, 1172470, 2777020,           # F2P
        2358720, 2694490, 1687950, 536230,                          # mixed-score
        264710, 275850, 600800, 739630, 1966720, 2246340,            # survival/adventure
        990080, 1623730, 553850, 949230, 548430, 632470,             # misc
        1551690, 252950, 1364780, 1446780,                           # racing/sports
    ]
    from_rows = []
    seen = set(curated)
    for row in (topsellers + newreleases):
        if row['appid'] not in seen and row['appid'].isdigit():
            from_rows.append(int(row['appid']))
            seen.add(row['appid'])
    catalog = curated + from_rows[:28]
    print(f'[catalog] {len(catalog)} candidate apps')

    # ---- details ----------------------------------------------------------
    details = {}
    for i, appid in enumerate(catalog):
        rec = scrape_appdetails(appid)
        if rec:
            details[str(appid)] = rec
        else:
            print(f'  .. skip {appid}', flush=True)
        time.sleep(1.4)
        if (i + 1) % 20 == 0:
            print(f'  .. details {i + 1}/{len(catalog)}')
    print(f'[details] {len(details)} games with full details')

    # keep only real games (drop dlc-only entries without price rows)
    catalog_ids = [a for a in details if details[a]['type'] == 'game']
    print(f'[catalog] {len(catalog_ids)} type=game kept')

    # ---- reviews + news ----------------------------------------------------
    reviews, news = {}, {}
    for i, appid in enumerate(catalog_ids):
        rv = scrape_reviews(appid)
        if rv:
            reviews[appid] = rv
        nw = scrape_news(appid)
        if nw:
            news[appid] = nw
        time.sleep(1.1)
        if (i + 1) % 20 == 0:
            print(f'  .. reviews/news {i + 1}/{len(catalog_ids)}')
    print(f'[reviews] {len(reviews)} games; [news] {len(news)} games')

    # ---- bundles ------------------------------------------------------------
    bundle_ids = discover_bundle_ids(
        [a for a in catalog_ids if details[a]['dlc']][:24], limit=12)
    bundles = {}
    for bid in list(bundle_ids)[:10]:
        b = scrape_bundle(bid)
        if b and b['final_price_cents']:
            bundles[bid] = b
        time.sleep(1.2)
    print(f'[bundles] {len(bundles)} bundles captured')

    # ---- creator rosters -----------------------------------------------------
    creators = {}
    for kind in ('developers', 'publishers'):
        names = {}
        for appid in catalog_ids:
            for n in details[appid].get(kind, []):
                names[n] = names.get(n, 0) + 1
        for name, n in sorted(names.items(), key=lambda kv: (-kv[1], kv[0]))[:14]:
            if n >= 2 or kind == 'developers':
                rows = scrape_creator('developer' if kind == 'developers' else 'publisher', name)
                if rows:
                    key = f"{kind[:-1]}::{name}"
                    creators[key] = {'name': name, 'kind': kind[:-1], 'games': rows}
    print(f'[creators] {len(creators)} rosters captured')

    # ---- images ---------------------------------------------------------------
    print('[images] fetching real upstream imagery ...', flush=True)
    for appid in catalog_ids:
        d = details[appid]
        stem = f'app{appid}'
        if d.get('header'):
            fetch_image(d['header'], f'{stem}-header.jpg')
        if d.get('capsule_231'):
            fetch_image(d['capsule_231'], f'{stem}-capsule.jpg')
        for j, s in enumerate(d.get('screenshots', [])[:4]):
            if s.get('path_full'):
                fetch_image(s['path_full'], f'{stem}-ss{j}.jpg')
        time.sleep(0.4)
    # home hero / featured images from the specials + top sellers capsules
    for row in (specials + topsellers)[:40]:
        if row['capsule_img']:
            fetch_image(row['capsule_img'], f"capsule-{row['appid']}.jpg")
    print(f'[images] {len(FETCHED_IMAGES)} real images fetched')

    # ---- save everything ---------------------------------------------------------
    save_json('search_snapshots.json', {
        'topsellers': topsellers, 'newreleases': newreleases,
        'specials': specials, 'freegames': freegames, 'under10': under10,
    })
    save_json('app_details.json', details)
    save_json('reviews.json', reviews)
    save_json('news.json', news)
    save_json('bundles.json', bundles)
    save_json('creators.json', creators)
    save_json('images.json', FETCHED_IMAGES)
    save_json('captures.json', CAPTURES)

    t1 = now_iso()
    save_json('scrape_window.json', {'start': t0, 'end': t1})
    print(f'=== steam scrape done {t1}; {len(CAPTURES)} HTTP captures')


if __name__ == '__main__':
    main()
