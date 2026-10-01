#!/usr/bin/env python3
"""Find Stanford CAP orgCodes for the departments we mirror, then pull the
faculty roster for each via /proxy/api/cap/orgs/<code>/profiles?affiliations=capFaculty."""
import json
import os
import time
import urllib.parse
import urllib.request

UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'}
BASE = 'https://profiles.stanford.edu/proxy/api/cap'
OUT = '/tmp/stanford_scrape/faculty'
os.makedirs(OUT, exist_ok=True)

DEPTS = [
    'Computer Science', 'Electrical Engineering', 'Mechanical Engineering',
    'Mathematics', 'Economics', 'Psychology', 'Biology', 'Chemistry',
    'Physics', 'English', 'History', 'Political Science', 'Sociology',
    'Management Science and Engineering', 'Medicine', 'Statistics',
    'Bioengineering', 'Chemical Engineering', 'Civil and Environmental Engineering',
    'Education', 'Law', 'Aeronautics and Astronautics', 'Anthropology',
    'Philosophy', 'Art and Art History',
]


def fetch(url, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.load(r)
        except Exception as exc:
            print('  retry', i, exc)
            time.sleep(3)
    return None


def org_code_for(dept):
    url = f"{BASE}/search/keyword?q={urllib.parse.quote(dept)}&ps=100"
    d = fetch(url)
    if not d:
        return None
    vals = d.get('data', {}).get('values', [])
    code_votes = {}
    for v in vals:
        p = v.get('profile') or v
        aff = (p.get('affiliations') or {})
        for t in (p.get('titles') or []):
            org = ((t.get('organization') or {}).get('org') or '')
            code = ((t.get('organization') or {}).get('orgCode') or '')
            if org.lower() == dept.lower() and code:
                code_votes[code] = code_votes.get(code, 0) + (2 if aff.get('capFaculty') else 1)
    if not code_votes:
        return None
    return sorted(code_votes.items(), key=lambda kv: -kv[1])[0][0]


def main():
    codes = {}
    if os.path.exists(f'{OUT}/org_codes.json'):
        codes = json.load(open(f'{OUT}/org_codes.json'))
    for dept in DEPTS:
        if dept in codes:
            continue
        code = org_code_for(dept)
        print(f'{dept} -> {code}')
        if code:
            codes[dept] = code
        time.sleep(1.5)
        json.dump(codes, open(f'{OUT}/org_codes.json', 'w'), indent=1)
    print('codes found:', len(codes))


if __name__ == '__main__':
    main()
