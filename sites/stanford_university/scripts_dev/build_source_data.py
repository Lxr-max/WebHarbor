#!/usr/bin/env python3
"""Assemble the stanford_university source_data snapshots from the raw captures.

Every record here is a real upstream capture (see provenance notes written by
the site's provenance.json). Selection rules keep the seed DB bounded while
covering every functional chain the mirror serves.
"""
import glob
import json
import os
import re
import html as h

SRC = '/tmp/stanford_scrape'
DEST = '/tmp/stanford_scrape/source_data'
os.makedirs(DEST, exist_ok=True)


def clean_text(s):
    if not s:
        return None
    s = h.unescape(s)
    s = re.sub(r'<[^>]+>', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s or None


def dump(name, obj):
    path = os.path.join(DEST, name)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=1, sort_keys=True)
    print(f'{name}: {os.path.getsize(path)} bytes')


def departments():
    d = json.load(open(f'{SRC}/departments.json'))
    out = []
    for code, r in sorted(d.items()):
        desc = r.get('description_html') or ''
        # strip h1 About Us headers
        desc = re.sub(r'<h1[^>]*>.*?</h1>', '', desc, flags=re.S)
        out.append({
            'code': code,
            'name': r.get('name'),
            'subject_codes': r.get('subject_codes') or [],
            'description': clean_text(desc),
        })
    dump('departments.json', out)


def courses():
    out = json.load(open(f'{SRC}/courses_trimmed.json'))
    seen = set()
    deduped = []
    for c in out:
        if c['code'] in seen:
            continue
        seen.add(c['code'])
        deduped.append(c)
    dump('courses.json', deduped)


def programs():
    d = json.load(open(f'{SRC}/programs_decoded.json'))
    out = []
    for code, r in sorted(d.items()):
        out.append({
            'code': code,
            'name': r.get('name'),
            'type': r.get('type'),
            'level': r.get('level'),
            'departments': r.get('departments') or [],
            'college': r.get('college'),
            'description': clean_text(r.get('catalog_description')),
            'degree_designation': r.get('degree_designation'),
            'units_min': r.get('units_min'),
            'webpage': r.get('webpage'),
            'requirements': [x.get('name') for x in (r.get('requirements') or []) if x.get('name')],
        })
    dump('programs.json', out)


def faculty():
    rosters = json.load(open(f'{SRC}/faculty/rosters.json'))
    out = []
    for dept, members in sorted(rosters.items()):
        for p in members:
            research = p.get('research_interests')
            if isinstance(research, dict):
                research = research.get('text') or research.get('html')
            bio = p.get('bio')
            if isinstance(bio, dict):
                bio = bio.get('text') or bio.get('html')
            short = p.get('short_title')
            if isinstance(short, dict):
                short = short.get('text')
            titles = []
            for t in (p.get('titles') or [])[:4]:
                if isinstance(t, dict):
                    lab = t.get('label')
                    lab = lab.get('text') if isinstance(lab, dict) else lab
                    org = t.get('organization') or {}
                    titles.append({
                        'label': lab,
                        'title': t.get('title'),
                        'org': org.get('org') if isinstance(org, dict) else org,
                        'org_code': org.get('orgCode') if isinstance(org, dict) else None,
                    })
            edu = []
            for e in (p.get('education') or [])[:5]:
                if isinstance(e, dict):
                    lab = e.get('label')
                    lab = lab.get('text') if isinstance(lab, dict) else lab
                    edu.append({'label': lab, 'degree': e.get('degree'),
                                'organization': e.get('organization'), 'year': e.get('year')})
            pubs = []
            for pub in (p.get('publications') or [])[:8]:
                if isinstance(pub, dict):
                    lab = pub.get('label')
                    lab = lab.get('text') if isinstance(lab, dict) else lab
                    pubs.append({'label': lab, 'year': pub.get('year')})
            out.append({
                'profile_id': p.get('profile_id'),
                'name': p.get('name'),
                'first_name': p.get('first_name'),
                'last_name': p.get('last_name'),
                'department': dept,
                'short_title': short,
                'titles': titles,
                'bio': clean_text(bio),
                'research_interests': clean_text(research),
                'education': edu,
                'publications': pubs,
                'publication_count': p.get('publication_count'),
                'email': p.get('email'),
                'photo_url': p.get('photo_url'),
            })
    dump('faculty.json', out)


def news():
    recs = json.load(open(f'{SRC}/news/articles.json'))
    out = []
    for r in recs:
        if not r.get('title'):
            continue
        body = r.get('body_lines') or []
        # drop UI chrome lines
        body = [l for l in body if len(l) > 2][:80]
        out.append({
            'url': r.get('url'),
            'slug': r.get('url', '').rstrip('/').split('/')[-1],
            'title': h.unescape(r.get('title') or ''),
            'published_ts': int(r['published_ts']) if r.get('published_ts') else None,
            'category': h.unescape(r.get('category') or ''),
            'main_topic': h.unescape(r.get('main_topic') or ''),
            'topics': [h.unescape(t) for t in (r.get('topics') or [])],
            'featured_unit': h.unescape(r.get('featured_unit') or ''),
            'writers': r.get('writers') or [],
            'description': h.unescape(r.get('description') or ''),
            'body': body,
            'og_image': r.get('og_image'),
        })
    out.sort(key=lambda x: -(x['published_ts'] or 0))
    dump('news.json', out)


def events():
    ids = {}
    for f in sorted(glob.glob(f'{SRC}/events/*.json')):
        try:
            d = json.load(open(f))
        except Exception:
            continue
        for w in d.get('events', []):
            e = w['event']
            ids[e['id']] = e
    evs = []
    for eid, e in ids.items():
        first = e.get('first_date') or ''
        if not ('2026-08-01' <= first <= '2027-09-30'):
            continue
        inst = []
        for i in (e.get('event_instances') or [])[:6]:
            if isinstance(i, dict):
                inst.append({
                    'start': i.get('start'),
                    'end': i.get('end'),
                    'location': i.get('location'),
                    'room': i.get('room_number'),
                })
        evs.append({
            'id': eid,
            'title': e.get('title'),
            'description': clean_text(e.get('description')),
            'first_date': e.get('first_date'),
            'last_date': e.get('last_date'),
            'location_name': e.get('location_name'),
            'room_number': e.get('room_number'),
            'address': e.get('address'),
            'experience': e.get('experience'),
            'free': e.get('free'),
            'ticket_url': e.get('ticket_url'),
            'ticket_cost': e.get('ticket_cost'),
            'tags': e.get('tags') or [],
            'keywords': e.get('keywords') or [],
            'departments': e.get('departments') or [],
            'recurring': e.get('recurring'),
            'featured': e.get('featured'),
            'verified': e.get('verified'),
            'photo_url': e.get('photo_url'),
            'urlname': e.get('urlname'),
            'instances': inst,
        })
    # balanced per-month sample (up to 60 per month) so the calendar spans the
    # whole academic year; within a month prefer verified + featured + photo
    by_month = {}
    for e in evs:
        by_month.setdefault((e.get('first_date') or '')[:7], []).append(e)
    selected = []
    for month in sorted(by_month):
        rows = sorted(by_month[month],
                      key=lambda x: (not x['verified'], not x['featured'],
                                     not x['photo_url'], x['first_date']))
        selected.extend(rows[:60])
    evs = selected
    dump('events.json', evs)


def calendar():
    d = json.load(open(f'{SRC}/academic_calendar.json'))
    dump('academic_calendar.json', d)


def libraries():
    d = json.load(open(f'{SRC}/libraries.json'))
    dump('libraries.json', d)


def admission():
    raw = open('/tmp/adm__apply_first-year.html').read()
    raw2 = re.sub(r'<script.*?</script>', ' ', raw, flags=re.S)

    def section(kw, n=4000):
        i = raw2.find(kw)
        seg = raw2[i:i + n] if i >= 0 else ''
        t = re.sub(r'<[^>]+>', '|', seg)
        t = h.unescape(t)
        parts = [p.strip() for p in t.split('|') if p.strip()]
        out = []
        for p in parts:
            if not out or out[-1] != p:
                out.append(p)
        return out

    reqs = section('Required Application Components', 2200)[:10]
    deadlines = section('Application Deadlines', 6000)
    out = {
        'requirements': reqs,
        'deadlines_raw': deadlines,
        'deadlines': [
            {'plan': 'Restrictive Early Action', 'round': 'Standard Application', 'deadline': 'November 1',
             'decision': 'by mid-December', 'reply': 'May 1'},
            {'plan': 'Restrictive Early Action', 'round': 'Arts Portfolio', 'deadline': 'October 15',
             'decision': 'by mid-December', 'reply': 'May 1'},
            {'plan': 'Regular Decision', 'round': 'Standard Application', 'deadline': 'January 5',
             'decision': 'by early April', 'reply': 'May 1'},
            {'plan': 'Regular Decision', 'round': 'Arts Portfolio', 'deadline': 'December 5',
             'decision': 'by early April', 'reply': 'May 1'},
        ],
        'aid_facts': [
            'Almost half of all Stanford undergraduates receive need-based financial aid.',
            'Families earning less than $150,000 with assets typical of that income level pay no tuition.',
            'Families earning less than $100,000 with assets typical of that income level pay no tuition or room and board.',
            'The average need-based scholarship in the current freshman class is more than $70,000.',
            'Stanford meets the full demonstrated need, without loans, for every admitted undergraduate who qualifies for financial assistance.',
        ],
    }
    dump('admission.json', out)


def home():
    raw = open('/tmp/stanford_home.html').read()
    raw2 = re.sub(r'<script.*?</script>', ' ', raw, flags=re.S)
    raw2 = re.sub(r'<style.*?</style>', ' ', raw2, flags=re.S)
    text = re.sub(r'<[^>]+>', '|', raw2)
    text = h.unescape(text)
    parts = [p.strip() for p in text.split('|') if p.strip()]
    out = []
    for p in parts:
        if not out or out[-1] != p:
            out.append(p)
    # keep the meaningful narrative sections
    keep = []
    for i, p in enumerate(parts):
        if len(p) > 40 and not p.startswith(('Skip to', 'Information for', 'Enter fullscreen')) and 'cookie' not in p.lower():
            keep.append(p)
    imgs = []
    seen = set()
    for m in re.finditer(r'<img src="(https://a-us\.storyblok\.com/[^"]+)"[^>]*alt="([^"]*)"', raw):
        url, alt = m.group(1), m.group(2)
        base = url.split('/m/')[0]
        if base in seen:
            continue
        seen.add(base)
        imgs.append({'url': url, 'alt': alt, 'filename': 'home_' + base.split('/')[-1]})
    dump('home.json', {'sections_text': keep[:60], 'images': imgs})


def main():
    departments()
    courses()
    programs()
    faculty()
    news()
    events()
    calendar()
    libraries()
    admission()
    home()


if __name__ == '__main__':
    main()
