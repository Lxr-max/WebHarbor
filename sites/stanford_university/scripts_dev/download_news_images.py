#!/usr/bin/env python3
"""Download news.stanford.edu og:images through headless Chromium (Cloudflare).

Navigates to each image URL (page.goto) — the challenge cookie set by the warm-up
story visit carries the navigation through.
"""
import json
import os
import time

from playwright.sync_api import sync_playwright

DEST = '/tmp/stanford_scrape/images/news'
os.makedirs(DEST, exist_ok=True)
m = json.load(open('/tmp/stanford_scrape/image_download_manifest.json'))
items = [r for r in m if r['category'] == 'news']
print('news images to fetch:', len(items), flush=True)

with sync_playwright() as p:
    b = p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-blink-features=AutomationControlled'])
    ctx = b.new_context(user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36', viewport={'width': 1280, 'height': 900})
    ctx.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined});")
    page = ctx.new_page()
    page.goto('https://news.stanford.edu/stories/2026/09/song-lin-macarthur-fellowship', timeout=90000, wait_until='domcontentloaded')
    for _ in range(36):
        time.sleep(2)
        if 'Just a moment' not in page.title():
            break
    print('warmup:', page.title()[:50], flush=True)
    ok = fail = 0
    for i, row in enumerate(items):
        out = os.path.join(DEST, row['filename'])
        if os.path.exists(out) and os.path.getsize(out) > 1000:
            continue
        url = row['url']
        try:
            resp = page.goto(url, timeout=90000)
            if resp and resp.ok:
                data = resp.body()
                if len(data) > 1000:
                    open(out, 'wb').write(data)
                    ok += 1
                else:
                    fail += 1
            else:
                fail += 1
                print('HTTP', resp.status if resp else '?', url[:90], flush=True)
            time.sleep(0.4)
        except Exception as exc:
            fail += 1
            print('ERR', url[:90], str(exc)[:80], flush=True)
        if i % 20 == 0:
            print(i, 'ok', ok, 'fail', fail, flush=True)
    print('done ok:', ok, 'fail:', fail, flush=True)
    b.close()
