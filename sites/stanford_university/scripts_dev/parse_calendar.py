#!/usr/bin/env python3
"""Parse the Stanford 2026-27 academic calendar page into structured records."""
import html as h
import json
import re

raw = open('/tmp/cal_page.html').read()

# Find quarter sections
sections = {}
for qid, qname in [('autumn', 'Autumn Quarter 2026'), ('winter', 'Winter Quarter 2027'),
                   ('spring', 'Spring Quarter 2027'), ('summer', 'Summer Quarter 2027')]:
    m = re.search(rf'<h2 id="{qid}">(?:<strong>)?(.*?)(?:</strong>)?</h2>(.*?)(?=<h2 id="|\Z)', raw, re.S)
    if not m:
        continue
    title = h.unescape(re.sub(r'<[^>]+>', '', m.group(1))).strip()
    body = m.group(2)
    items = []
    for li in re.findall(r'<li>(.*?)</li>', body, re.S):
        strong = re.match(r'\s*<strong>(.*?)</strong>\s*(.*)', li, re.S)
        if strong:
            when = h.unescape(re.sub(r'<[^>]+>', '', strong.group(1))).strip()
            what_html = strong.group(2)
            what = h.unescape(re.sub(r'<[^>]+>', ' ', what_html))
            what = re.sub(r'\s+', ' ', what).strip()
        else:
            when = ''
            what = h.unescape(re.sub(r'<[^>]+>', ' ', li))
            what = re.sub(r'\s+', ' ', what).strip()
        items.append({'when': when, 'what': what})
    sections[qid] = {'title': title, 'items': items}

# Also the "Quarters & holidays" list at the top
qh = []
m = re.search(r'Quarters &amp; holidays(.*?)</ul>', raw, re.S)
if m:
    for li in re.findall(r'<li>(.*?)</li>', m.group(1), re.S):
        t = h.unescape(re.sub(r'<[^>]+>', ' ', li))
        t = re.sub(r'\s+', ' ', t).strip()
        if t:
            qh.append(t)

out = {'quarters': sections, 'quarters_and_holidays': qh}
json.dump(out, open('/tmp/stanford_scrape/academic_calendar.json', 'w'), indent=1)
for qid, s in sections.items():
    print(s['title'], '-', len(s['items']), 'items')
print('qh:', len(qh))
EOF = None
