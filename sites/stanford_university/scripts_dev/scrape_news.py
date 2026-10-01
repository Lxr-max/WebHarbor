#!/usr/bin/env python3
"""Scrape Stanford Report (news.stanford.edu) via headless Chromium.

Cloudflare fronts news.stanford.edu; a real headless Chromium passes the
challenge (same approach as the u_s_customs capture). We warm up on one
story, then walk the section/topic listing pages and each story page,
saving raw HTML + parsed JSON records.
"""
import json
import os
import re
import time
import html as html_mod

from playwright.sync_api import sync_playwright

OUT = '/tmp/stanford_scrape/news'
os.makedirs(OUT + '/pages', exist_ok=True)
os.makedirs(OUT + '/listing', exist_ok=True)

LISTINGS = [
    'https://news.stanford.edu/',
    'https://news.stanford.edu/university-news',
    'https://news.stanford.edu/research-and-scholarship',
    'https://news.stanford.edu/on-campus',
    'https://news.stanford.edu/student-experience',
    'https://news.stanford.edu/artificial-intelligence',
    'https://news.stanford.edu/features/research-at-stanford',
    'https://news.stanford.edu/university-news/topic/awards-and-honors',
    'https://news.stanford.edu/university-news/topic/campus-and-facilities',
    'https://news.stanford.edu/university-news/topic/community-message',
    'https://news.stanford.edu/university-news/topic/institutional-news',
    'https://news.stanford.edu/research-and-scholarship/topic/arts-and-humanities',
    'https://news.stanford.edu/research-and-scholarship/topic/earth-and-climate',
    'https://news.stanford.edu/research-and-scholarship/topic/health-and-medicine',
    'https://news.stanford.edu/research-and-scholarship/topic/science-and-engineering',
    'https://news.stanford.edu/research-and-scholarship/topic/social-sciences',
    'https://news.stanford.edu/research-and-scholarship/topic/economics',
    'https://news.stanford.edu/research-and-scholarship/topic/education',
    'https://news.stanford.edu/research-and-scholarship/topic/law',
    'https://news.stanford.edu/research-and-scholarship/topic/business',
    'https://news.stanford.edu/on-campus/topic/arts',
    'https://news.stanford.edu/on-campus/topic/athletics',
    'https://news.stanford.edu/on-campus/topic/events',
    'https://news.stanford.edu/on-campus/topic/community-and-culture',
    'https://news.stanford.edu/student-experience/topic/academics',
    'https://news.stanford.edu/student-experience/topic/college',
    'https://news.stanford.edu/student-experience/topic/mental-health',
    'https://news.stanford.edu/student-experience/topic/volunteer-and-service',
    'https://news.stanford.edu/news-archive',
]


def wait_ready(page, tries=30):
    for _ in range(tries):
        time.sleep(2)
        t = page.title()
        if 'Just a moment' not in t and t.strip():
            return True
    return False


def parse_article(url, raw):
    rec = {'url': url}
    m = re.search(r'window\.pageController=(\{.*?\})</script>', raw, re.S)
    if m:
        try:
            pc = json.loads(m.group(1))
            ga = pc.get('gaData') or {}
            rec['title'] = pc.get('title')
            rec['published_ts'] = ga.get('publishedDate')
            rec['category'] = ga.get('srContentCategoryText')
            rec['featured_unit'] = ga.get('srFeaturedUnitText')
            rec['main_topic'] = ga.get('srContentMainTopicText')
            rec['topics'] = ga.get('srContentTopicText') or []
            rec['content_type'] = ga.get('srContentTypeText') or pc.get('contentType')
            contrib = ga.get('srContributors') or {}
            rec['writers'] = contrib.get('writers') or []
            rec['authors'] = contrib.get('authors') or []
            rec['editors'] = contrib.get('editors') or []
        except Exception as exc:
            rec['pc_error'] = str(exc)
    mm = re.search(r'<meta property="og:image" content="([^"]+)"', raw)
    if mm:
        rec['og_image'] = mm.group(1)
    md = re.search(r'<meta name="description" content="([^"]*)"', raw)
    if md:
        rec['description'] = html_mod.unescape(md.group(1))
    # hero image inside the page (figure with img)
    am = re.search(r'<article[^>]*>', raw)
    if am:
        seg = raw[am.start():am.start() + 12000]
        imgs = re.findall(r'<img[^>]+src="([^"]+)"', seg)
        if imgs:
            rec['hero_imgs'] = imgs[:4]
        tm = re.search(r'data-main-topic="([^"]*)"', raw)
        if tm:
            rec['article_main_topic'] = html_mod.unescape(tm.group(1))
    # body text: from <article ...> to 'For more information' / metadata-fields
    if am:
        start = am.start()
        end = raw.find('data-component="metadata-fiel', start)
        seg = raw[start:end if end > 0 else start + 40000]
        seg = re.sub(r'<script.*?</script>', ' ', seg, flags=re.S)
        seg = re.sub(r'<[^>]+>', '\n', seg)
        seg = html_mod.unescape(seg)
        lines = [l.strip() for l in seg.split('\n') if l.strip()]
        dedup = []
        for l in lines:
            if not dedup or dedup[-1] != l:
                dedup.append(l)
        rec['body_lines'] = dedup[:120]
    return rec


def main():
    story_urls = set()
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-blink-features=AutomationControlled'])
        ctx = b.new_context(user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36', viewport={'width': 1280, 'height': 900})
        ctx.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined});")
        page = ctx.new_page()
        # warm-up on a known story (passes the challenge, seeds cf cookies)
        page.goto('https://news.stanford.edu/stories/2026/09/song-lin-macarthur-fellowship', timeout=90000, wait_until='domcontentloaded')
        wait_ready(page)
        print('warmup:', page.title()[:60])
        # listing pages
        for url in LISTINGS:
            try:
                page.goto(url, timeout=90000, wait_until='domcontentloaded')
                wait_ready(page, tries=20)
                raw = page.content()
                name = url.replace('https://news.stanford.edu/', '').strip('/') or 'home'
                name = name.replace('/', '_').replace('?', '_')
                open(f'{OUT}/listing/{name}.html', 'w').write(raw)
                found = re.findall(r'href="(https://news\.stanford\.edu/stories/[^"#]+)"', raw)
                before = len(story_urls)
                story_urls.update(found)
                print(f'{url} -> {len(found)} stories (+{len(story_urls)-before})')
            except Exception as exc:
                print('LISTING FAIL', url, exc)
        # story pages
        records = []
        urls = sorted(story_urls)
        print('total story urls:', len(urls))
        for i, url in enumerate(urls):
            slug = url.rstrip('/').split('/')[-1]
            try:
                page.goto(url, timeout=90000, wait_until='domcontentloaded')
                wait_ready(page, tries=15)
                raw = page.content()
                open(f'{OUT}/pages/{slug}.html', 'w').write(raw)
                rec = parse_article(url, raw)
                records.append(rec)
                print(i, slug, '->', rec.get('title', '?')[:60] if rec.get('title') else '?')
            except Exception as exc:
                print('STORY FAIL', url, exc)
        json.dump(records, open(f'{OUT}/articles.json', 'w'), indent=1)
        print('records:', len(records))
        b.close()


if __name__ == '__main__':
    main()
