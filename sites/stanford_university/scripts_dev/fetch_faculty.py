#!/usr/bin/env python3
"""Fetch faculty rosters per org via the CAP orgs API and trim to the fields
the mirror needs (name, title, bio, research, education, publications, photo)."""
import json
import os
import time
import urllib.request

UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'}
BASE = 'https://profiles.stanford.edu/proxy/api/cap'
OUT = '/tmp/stanford_scrape/faculty'
os.makedirs(OUT, exist_ok=True)


def fetch(url, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.load(r)
        except Exception as exc:
            print('  retry', i, exc, flush=True)
            time.sleep(5)
    return None


def trim(p):
    def label(x):
        if isinstance(x, dict):
            return (x.get('label') or {}).get('text') or x.get('text')
        return x

    education = []
    for e in (p.get('education') or [])[:6]:
        if not isinstance(e, dict):
            education.append({'label': str(e), 'degree': None, 'organization': None, 'year': None})
            continue
        org_e = e.get('organization')
        education.append({
            'label': label(e),
            'degree': e.get('degree'),
            'organization': org_e.get('org') if isinstance(org_e, dict) else org_e,
            'year': e.get('year'),
        })
    pubs = []
    for pub in (p.get('publications') or [])[:8]:
        if isinstance(pub, dict):
            first = pub.get('firstPublished') or {}
            first_txt = first.get('text') if isinstance(first, dict) else first
            pubs.append({'label': pub.get('title'), 'year': (first_txt or '')[:12],
                         'citation': pub.get('chicagoCitation')})
        else:
            pubs.append({'label': str(pub), 'year': None, 'citation': None})
    titles = []
    for t in (p.get('titles') or [])[:5]:
        org = t.get('organization') or {}
        titles.append({
            'label': label(t),
            'title': t.get('title'),
            'org': org.get('org'),
            'org_code': org.get('orgCode'),
            'type': t.get('type'),
        })
    research = p.get('currentResearchInterests') or {}
    research_text = None
    if isinstance(research, dict):
        rt = research.get('shortText')
        if isinstance(rt, dict):
            research_text = rt.get('text') or rt.get('html')
        elif isinstance(rt, str):
            research_text = rt
        if not research_text and research.get('terseText'):
            research_text = research['terseText']
    photos = p.get('profilePhotos') or {}
    photo = None
    for size in ('350x350', '175x261', '350x522'):
        if photos.get(size) and not photos[size].get('placeholder'):
            photo = photos[size].get('url')
            break
    bio = p.get('bio')
    if isinstance(bio, dict):
        bio = bio.get('text') or bio.get('html')
    return {
        'profile_id': p.get('profileId'),
        'name': p.get('displayName'),
        'first_name': ((p.get('names') or {}).get('preferred') or {}).get('firstName'),
        'last_name': ((p.get('names') or {}).get('preferred') or {}).get('lastName'),
        'short_title': label(p.get('shortTitle')),
        'titles': titles,
        'bio': bio,
        'research_interests': research_text,
        'clinical_focus': p.get('clinicalFocus'),
        'education': education,
        'publications': pubs,
        'publication_count': len(p.get('publications') or []),
        'email': (p.get('primaryContact') or {}).get('email') if isinstance(p.get('primaryContact'), dict) else None,
        'photo_url': photo,
        'profile_url': (p.get('meta') or {}).get('links', [{}])[0].get('href') if False else None,
    }


def main():
    codes = json.load(open(f'{OUT}/org_codes.json'))
    rosters = {}
    for dept, code in sorted(codes.items()):
        out_path = f'{OUT}/roster_{code}.json'
        if os.path.exists(out_path):
            rosters[dept] = json.load(open(out_path))
            print('cached', dept, len(rosters[dept]), flush=True)
            continue
        members = []
        page = 1
        while page <= 4:
            url = f"{BASE}/orgs/{code}/profiles?ps=100&affiliations=capFaculty&p={page}"
            d = fetch(url)
            if not d:
                break
            vals = d.get('data', {}).get('values', [])
            if not vals:
                break
            for v in vals:
                members.append(trim(v))
            total = (d.get('data') or {}).get('totalCount') or 0
            print(dept, 'page', page, 'got', len(vals), 'total', total, flush=True)
            if len(vals) < 100 or page * 100 >= total:
                break
            page += 1
            time.sleep(2)
        rosters[dept] = members
        json.dump(members, open(out_path, 'w'), indent=1)
        time.sleep(2)
    json.dump(rosters, open(f'{OUT}/rosters.json', 'w'), indent=1)
    total = sum(len(v) for v in rosters.values())
    print('TOTAL faculty:', total, flush=True)


if __name__ == '__main__':
    main()
