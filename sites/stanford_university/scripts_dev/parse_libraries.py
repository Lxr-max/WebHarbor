#!/usr/bin/env python3
"""Parse library pages + the library-hours page into structured records."""
import json
import os
import re
import html as h

SRC = '/tmp/stanford_scrape/libraries'

LIBS = [
    'academy-hall-redwood-city-campus', 'archive-recorded-sound',
    'bowes-art-architecture-library', 'branner-earth-sciences-library-map-collections',
    'cecil-h-green-library', 'classics-library', 'cubberley-education-library',
    'david-rumsey-map-center', 'east-asia-library',
    'harold-miller-library-hopkins-marine-station',
    'media-microtext-center-cecil-h-green-library', 'music-library',
    'robin-li-and-melissa-ma-science-library', 'silicon-valley-archives',
    'special-collections', 'terman-engineering-library',
    'tanner-philosophy-library',
]


def clean(s):
    return re.sub(r'\s+', ' ', h.unescape(re.sub(r'<[^>]+>', ' ', s))).strip()


def parse_lib(slug):
    raw = open(os.path.join(SRC, f'{slug}.html')).read()
    m = re.search(r'<title>([^<]+)</title>', raw)
    name = slug
    if m:
        name = h.unescape(m.group(1)).split('|')[0].strip()
    loc = None
    m = re.search(r'<title>Location</title>.*?</svg><a[^>]*>(.*?)</a>', raw, re.S)
    if m:
        loc = clean(m.group(1))
    if not loc:
        m = re.search(r'Location</h\d>(.*?)</div>', raw, re.S)
        if m:
            loc = clean(m.group(1))
    phone = None
    m = re.search(r'<title>Phone</title>.*?</svg>([^<]+)</div>', raw, re.S)
    if m:
        phone = m.group(1).strip()
    if not phone:
        m = re.search(r'href="tel:([^"]+)"', raw)
        if m:
            phone = m.group(1)
    if not phone:
        m = re.search(r'Phone</h\d>\s*<p[^>]*>([^<]+)<', raw)
        if m:
            phone = m.group(1).strip()
    email = None
    m = re.search(r'href="mailto:([^"]+)"', raw)
    if m:
        email = m.group(1)
    about = None
    m = re.search(r'About us</h\d>(.*?)(?=<h\d|<div class="flex flex-col gap-90")', raw, re.S)
    if m:
        about = clean(m.group(1))
    quick_links = []
    m = re.search(r'Quick links</h\d>(.*?)(?=<h\d)', raw, re.S)
    if m:
        quick_links = [clean(x) for x in re.findall(r'<a[^>]*>(.*?)</a>', m.group(1), re.S)]
        quick_links = [x for x in quick_links if x][:6]
    subjects = []
    m = re.search(r'Research support</h\d>(.*?)(?=<h\d|</article>)', raw, re.S)
    if m:
        subjects = [clean(x) for x in re.findall(r'<a[^>]*>(.*?)</a>', m.group(1), re.S)]
        subjects = [x for x in subjects if x][:20]
    return {'slug': slug, 'name': name, 'location': loc, 'phone': phone,
            'email': email, 'about': about, 'quick_links': quick_links,
            'research_subjects': subjects}


def parse_hours():
    raw = open(os.path.join(SRC, 'hours.html')).read()
    m = re.search(r'(Sep|Oct|Nov|Dec|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug) \d{2}, 20\d\d – \w+ \d{2}, 20\d\d', raw)
    week_label = m.group(0) if m else None
    libraries = []
    # each library: <h2 class="h3" itemprop="name">...</h2> ... <table ...> ... </table>
    blocks = re.split(r'<h2 class="h3" itemprop="name">', raw)
    for blk in blocks[1:]:
        m = re.match(r'(.*?)</h2>', blk, re.S)
        if not m:
            continue
        name = clean(m.group(1))
        tm = re.search(r'<table[^>]*>(.*?)</table>', blk[:60000], re.S)
        if not tm:
            continue
        table = tm.group(1)
        days_hdr = re.findall(r'<th[^>]*class="[^"]*hours[^"]*"[^>]*>\s*([A-Za-z]{1,2} \d{2})\s*</th>', table)
        rows = []
        for tr in re.findall(r'<tr>(.*?)</tr>', table, re.S):
            tds = re.findall(r'<td[^>]*>(.*?)</td>', tr, re.S)
            if not tds:
                continue
            row_name = clean(tds[0])
            days = []
            for td in tds[1:8]:
                opens = re.search(r'itemprop="opens">([^<]+)<', td)
                closes = re.search(r'itemprop="closes">([^<]+)<', td)
                if opens and closes:
                    days.append(f"{opens.group(1)}-{closes.group(1)}")
                elif 'closed' in td:
                    days.append('closed')
                else:
                    days.append(None)
            rows.append({'desk': row_name, 'hours': days})
        libraries.append({'name': name, 'days': days_hdr, 'rows': rows})
    return week_label, libraries


def main():
    libs = []
    for s in LIBS:
        p = os.path.join(SRC, f'{s}.html')
        if os.path.exists(p):
            libs.append(parse_lib(s))
    week, hours = parse_hours()
    out = {'libraries': libs, 'hours_week_label': week, 'hours': hours}
    json.dump(out, open('/tmp/stanford_scrape/libraries.json', 'w'), indent=1)
    print('libs:', len(libs), 'hours libs:', len(hours), 'week:', week)
    for l in libs[:4]:
        print(l['name'], '|', (l['location'] or '')[:50], '|', l['phone'])
    for hh in hours[:4]:
        print(hh['name'], '|', hh['days'], '|', len(hh['rows']), 'rows')


if __name__ == '__main__':
    main()
