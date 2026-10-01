#!/usr/bin/env python3
"""Build the trimmed course dataset for the stanford_university mirror.

Source: the live Coursedog catalog API behind bulletin.stanford.edu
(https://app.coursedog.com/api/v1/cm/stanford/courses, fetched 2026-09-30).
Selection: every Active, non-archived course with a description, capped at
20 undergraduate + 20 graduate rows per subject code, plus a curated list of
flagship courses. Fields are trimmed to what the mirror renders.
"""
import json
import re

PRIORITY = [
    'CS106A', 'CS106B', 'CS107', 'CS109', 'CS110', 'CS143', 'CS145', 'CS148',
    'CS154', 'CS155', 'CS161', 'CS166', 'CS168', 'CS193P', 'CS194', 'CS195',
    'CS221', 'CS223A', 'CS224N', 'CS225A', 'CS227B', 'CS228', 'CS229', 'CS230',
    'CS231N', 'CS234', 'CS236', 'CS237', 'CS238', 'CS239', 'CS241', 'CS242',
    'CS244N', 'CS245', 'CS246', 'CS247', 'CS251', 'CS255', 'CS257', 'CS261',
    'CS267', 'CS271', 'CS273B', 'CS281', 'CS288', 'CS294', 'CS295', 'CS329A',
    'CS336', 'CS371W', 'MATH19', 'MATH20', 'MATH21', 'MATH51', 'MATH52',
    'MATH53', 'MATH104', 'MATH113', 'MATH115', 'MATH120', 'MATH121',
    'MATH144', 'MATH171', 'PHYSICS41', 'PHYSICS43', 'PHYSICS45', 'PHYSICS61',
    'PHYSICS70', 'CHEM31A', 'CHEM33', 'BIO41', 'BIO42', 'BIO43', 'ECON1',
    'ECON50', 'PSYCH1', 'PSYCH10', 'ENGLISH10A', 'HISTORY1', 'ME1', 'ME101',
    'EE141', 'EE178', 'MS&E120', 'MS&E220', 'STATS60', 'STATS116', 'STATS200',
    'CME100', 'CME102', 'CME106', 'BIOE41', 'ENGR14', 'ENGR15', 'CEE101B',
    'AA100', 'AA210A', 'PHIL1', 'POLISCI1', 'SOC1', 'ANTHRO1', 'EDUC101',
    'LAW101', 'LAW102', 'CHEMENG101', 'COMPMED80',
]


def sort_key(code):
    m = re.match(r'([A-Z]+)(\d+)', code or '')
    if m:
        return (m.group(1), int(m.group(2)), code)
    return ('ZZZ', 0, code or '')


def trim(c):
    cf = c.get('customFields') or {}
    credits = c.get('credits') or {}
    ch = credits.get('creditHours') or {}
    terms = cf.get('quarterOffered')
    if isinstance(terms, str):
        terms = [terms]
    ways = cf.get('WAYS')
    if isinstance(ways, str):
        ways = [ways]
    prereq = None
    req = c.get('requisites') or {}
    if isinstance(req, dict):
        for v in req.values():
            if isinstance(v, list) and v:
                prereq = v
                break
    comps = []
    for x in (c.get('components') or []):
        comps.append({'code': x.get('code'), 'name': x.get('name')})
    return {
        'code': c.get('code'),
        'subject': c.get('subjectCode'),
        'number': c.get('courseNumber'),
        'title': c.get('longName') or c.get('name'),
        'description': c.get('description'),
        'units_min': ch.get('min'),
        'units_max': ch.get('max'),
        'career': c.get('career'),
        'college': c.get('college'),
        'grade_mode': c.get('gradeMode'),
        'terms': terms,
        'ways': ways,
        'components': comps,
        'requisites': prereq,
        'departments': c.get('departments'),
    }


def main():
    d = json.load(open('/tmp/cd_courses.json'))
    active = [c for c in d.values()
              if c.get('status') == 'Active' and not c.get('archived')
              and (c.get('description') or '').strip()]
    by_subj = {}
    for c in active:
        by_subj.setdefault(c.get('subjectCode'), []).append(c)

    chosen = {}
    for subj, lst in by_subj.items():
        lst = sorted(lst, key=lambda c: sort_key(c.get('courseNumber')))
        ug, gr = [], []
        for c in lst:
            m = re.match(r'(\d+)', c.get('courseNumber') or '')
            n = int(m.group(1)) if m else 0
            (ug if n < 200 else gr).append(c)
        for c in ug[:20]:
            chosen[c.get('code') + '|' + c.get('_id')] = c
        for c in gr[:20]:
            chosen[c.get('code') + '|' + c.get('_id')] = c
    # priority flagship courses
    codes = {c.get('code'): c for c in active}
    for pc in PRIORITY:
        if pc in codes:
            c = codes[pc]
            chosen[c.get('code') + '|' + c.get('_id')] = c

    out = []
    for key in sorted(chosen, key=lambda k: sort_key(k.split('|')[0])):
        out.append(trim(chosen[key]))
    json.dump(out, open('/tmp/stanford_scrape/courses_trimmed.json', 'w'), indent=0,
              ensure_ascii=False, separators=(',', ':'))
    print('courses:', len(out))
    import os
    print('bytes:', os.path.getsize('/tmp/stanford_scrape/courses_trimmed.json'))
    subs = {}
    for c in out:
        subs[c['subject']] = subs.get(c['subject'], 0) + 1
    print('subjects:', len(subs))
    print('CS sample:', [c['code'] for c in out if c['subject'] == 'CS'][:30])


if __name__ == '__main__':
    main()
