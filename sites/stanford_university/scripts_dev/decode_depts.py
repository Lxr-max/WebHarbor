#!/usr/bin/env python3
"""Decode bulletin department SSR pages into structured department records."""
import json
import os
import re
import sys

sys.path.insert(0, '/tmp')
from devalue import decode  # noqa: E402

SRC = '/tmp/stanford_scrape/departments'
OUT = '/tmp/stanford_scrape/departments.json'

records = {}
for fname in sorted(os.listdir(SRC)):
    if not fname.endswith('.html'):
        continue
    code = fname[:-5]
    raw = open(os.path.join(SRC, fname), encoding='utf-8').read()
    start = raw.find('__NUXT_DATA__')
    start = raw.find('[', start)
    end = raw.find('</script>', start)
    try:
        payload = json.loads(raw[start:end])
        data = decode(payload)
    except Exception as exc:
        print('DECODE FAIL', code, exc)
        continue
    # find department-<CODE> node
    found = []

    def walk(o):
        if found:
            return
        if isinstance(o, dict):
            for k, v in o.items():
                if k.startswith('department-') and isinstance(v, dict):
                    found.append(v)
                    return
                walk(v)
        elif isinstance(o, list):
            for x in o:
                walk(x)

    walk(data)
    if not found or 'department' not in found[0]:
        print('NO DEPT NODE', code)
        continue
    found = found[0]
    dept = found['department']
    page = found.get('page') or {}
    rec = {
        'code': code,
        'name': dept.get('displayName') or dept.get('name'),
        'subject_codes': dept.get('subjectCodes') or [],
        'status': dept.get('status'),
        'description_html': page.get('content') or '',
    }
    records[code] = rec

json.dump(records, open(OUT, 'w'), indent=1, sort_keys=True)
print('departments decoded:', len(records))
print('with description:', sum(1 for r in records.values() if r['description_html']))
print('with subject codes:', sum(1 for r in records.values() if r['subject_codes']))
for code in ['COMPUTSCI', 'AEROASTRO', 'MATH', 'ENGLISH', 'PSYCH']:
    r = records.get(code)
    if r:
        print(code, r['name'], r['subject_codes'], (r['description_html'] or '')[:80])
