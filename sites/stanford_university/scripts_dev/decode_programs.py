#!/usr/bin/env python3
"""Decode bulletin program SSR pages into structured program records."""
import json
import os
import re
import sys

sys.path.insert(0, '/tmp')
from devalue import decode  # noqa: E402

SRC = '/tmp/stanford_scrape/programs'
OUT = '/tmp/stanford_scrape/programs_decoded.json'


def txt(v):
    if isinstance(v, dict):
        return (v.get('text') or v.get('html') or '').strip()
    return (v or '')


def main():
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
            data = decode(json.loads(raw[start:end]))
        except Exception as exc:
            print('DECODE FAIL', code, exc)
            continue
        found = []

        def walk(o):
            if found:
                return
            if isinstance(o, dict):
                for k, v in o.items():
                    if k.startswith('program-') and isinstance(v, dict):
                        found.append(v)
                        return
                    walk(v)
            elif isinstance(o, list):
                for x in o:
                    walk(x)

        walk(data)
        if not found:
            print('NO PROGRAM NODE', code)
            continue
        f = found[0]
        p = f.get('program') or {}
        page = f.get('page') or {}
        rec = {
            'code': p.get('code') or code,
            'name': (p.get('longName') or '').strip() or (p.get('catalogDisplayName') or '').strip() or (p.get('name') or '').strip(),
            'type': p.get('type'),
            'level': p.get('level'),
            'departments': p.get('departments') or [],
            'college': p.get('college'),
            'catalog_description': p.get('catalogDescription'),
            'full_description': p.get('catalogFullDescription'),
            'degree_designation': txt(p.get('degreeDesignation')) or None,
            'units_min': p.get('unitsProgramMin'),
            'webpage': p.get('programWebpage'),
            'specializations': p.get('specializations'),
            'status': p.get('status'),
            'page_content': page.get('content') or '',
        }
        # requirements
        req = p.get('requisites') or {}
        reqs = []
        if isinstance(req, dict):
            simple = req.get('requisitesSimple') or []
            for r in simple[:8]:
                if isinstance(r, dict):
                    reqs.append({
                        'name': r.get('name'),
                        'type': r.get('type'),
                    })
        rec['requirements'] = reqs
        records[code] = rec
    json.dump(records, open(OUT, 'w'), indent=1, sort_keys=True)
    print('programs decoded:', len(records))
    n_desc = sum(1 for r in records.values() if (r['catalog_description'] or '').strip())
    n_page = sum(1 for r in records.values() if (r['page_content'] or '').strip())
    print('with catalog desc:', n_desc, 'with page content:', n_page)
    for c in ['CS-BS', 'CS-MS', 'CS-PHD', 'ECON-BA', 'MATH-BS']:
        r = records.get(c)
        if r:
            print(c, '|', r['name'], '|', r['type'], '|', (r['catalog_description'] or '')[:80])


if __name__ == '__main__':
    main()
