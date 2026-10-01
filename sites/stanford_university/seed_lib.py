"""Deterministic seed builder for the stanford_university mirror.

Everything materialized here comes from the tracked source_data/*.json
snapshots (captured 2026-09-30, see provenance.json) in a fixed, sorted
order. The four benchmark accounts and their planner rows / saved events
are authored fixtures following the u_s_customs / nyse precedent: every
course and event they reference is a real captured upstream record, and
every timestamp is a frozen constant so the SQLite output is
byte-reproducible (PYTHONHASHSEED=0).
"""
import json
import os
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
SOURCE = os.path.join(HERE, 'source_data')

# bcrypt hash of 'TestPass123!' — frozen so the seed DB is byte-reproducible.
BENCHMARK_PASSWORD_HASH = (
    '$2b$12$qSds4Mr9Wo7VwPWLhompEer88SuxxXFDp31P9etY6v7nfRctNO7B.')
MIRROR_DATE = '2026-09-30'

SCHOOLS = [
    ('doerr', 'Stanford Doerr School of Sustainability'),
    ('gsb', 'Graduate School of Business'),
    ('gse', 'Graduate School of Education'),
    ('engineering', 'School of Engineering'),
    ('hns', 'School of Humanities and Sciences'),
    ('law', 'School of Law'),
    ('medicine', 'School of Medicine'),
]

# Department code -> school key, derived from the upstream bulletin nav
# (bulletin.stanford.edu groups departments under the seven schools) and
# the college attribution carried by each department's courses.
DEPT_SCHOOL = {
    'AEROASTRO': 'engineering', 'AA': 'engineering', 'ENGR': 'engineering',
    'BIOE': 'engineering', 'CME': 'engineering', 'CS': 'engineering',
    'EARTH': 'doerr', 'EE': 'engineering', 'ENGLISH': 'hns', 'HEME': 'medicine',
    'MATSCI': 'engineering', 'ME': 'engineering', 'MS&E': 'engineering',
    'PWR': 'hns', 'STS': 'engineering', 'COMPUTSCI': 'engineering',
}


def _load(name):
    with open(os.path.join(SOURCE, name), encoding='utf-8') as f:
        return json.load(f)


def _college_school(college):
    if not college:
        return None
    c = college.lower()
    if 'sustainability' in c:
        return 'doerr'
    if 'business' in c:
        return 'gsb'
    if 'education' in c:
        return 'gse'
    if 'engineering' in c:
        return 'engineering'
    if 'law' in c:
        return 'law'
    if 'medicine' in c:
        return 'medicine'
    if 'humanities' in c or ' hns' in c or 'ug' in c:
        return 'hns'
    return None


def _school_for_department(code, name, courses_by_dept):
    if code in DEPT_SCHOOL:
        return DEPT_SCHOOL[code]
    votes = {}
    for college in courses_by_dept.get(code, []):
        school = _college_school(college)
        if school:
            votes[school] = votes.get(school, 0) + 1
    if votes:
        return sorted(votes.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
    n = (name or '').lower()
    if any(k in n for k in ('medicine', 'health', 'surgery', 'anesthesia',
                            'neuro', 'cardio', 'pediat', 'radiology')):
        return 'medicine'
    if 'law' in n:
        return 'law'
    if 'business' in n:
        return 'gsb'
    if 'education' in n or 'teaching' in n:
        return 'gse'
    if any(k in n for k in ('energy', 'earth', 'ocean', 'climate', 'sustainab',
                            'geolog', 'environment')):
        return 'doerr'
    if any(k in n for k in ('engineering', 'computer', 'mechanical', 'electrical',
                           'chemical', 'civil', 'aeronautic', 'materials',
                           'management science')):
        return 'engineering'
    return 'hns'


def _frozen_now():
    return datetime(2026, 9, 30, 12, 0, 0)


def build_records():
    """Return the deterministic record dicts handed to the ORM."""
    depts_raw = _load('departments.json')
    courses_raw = _load('courses.json')
    programs_raw = _load('programs.json')
    faculty_raw = _load('faculty.json')
    news_raw = _load('news.json')
    events_raw = _load('events.json')
    calendar_raw = _load('academic_calendar.json')
    libraries_raw = _load('libraries.json')
    admission_raw = _load('admission.json')
    home_raw = _load('home.json')

    # ── departments ────────────────────────────────────────────────────────
    college_votes = {}
    for c in courses_raw:
        for d in (c.get('departments') or []):
            college_votes.setdefault(d, []).append(c.get('college') or '')
    departments = []
    for d in depts_raw:
        departments.append({
            'code': d['code'],
            'name': d['name'],
            'subject_codes': sorted(set(d.get('subject_codes') or [])),
            'description': d.get('description'),
            'school': _school_for_department(d['code'], d['name'], college_votes),
        })
    dept_by_code = {d['code']: d for d in departments}

    # ── courses ────────────────────────────────────────────────────────────
    courses = []
    for c in courses_raw:
        courses.append({
            'code': c['code'],
            'subject': c['subject'],
            'number': c['number'],
            'title': c['title'],
            'description': c['description'],
            'units_min': c.get('units_min'),
            'units_max': c.get('units_max'),
            'career': c.get('career'),
            'college': c.get('college'),
            'grade_mode': c.get('grade_mode'),
            'terms': c.get('terms') or [],
            'ways': c.get('ways') or [],
            'components': [x.get('name') or x.get('code') for x in (c.get('components') or [])],
            'requisites': c.get('requisites'),
            'departments': sorted(set(c.get('departments') or [])),
        })

    # ── programs ───────────────────────────────────────────────────────────
    programs = []
    for p in programs_raw:
        programs.append({
            'code': p['code'],
            'name': p['name'],
            'type': p.get('type'),
            'level': p.get('level'),
            'departments': sorted(set(p.get('departments') or [])),
            'college': p.get('college'),
            'description': p.get('description'),
            'degree_designation': p.get('degree_designation'),
            'units_min': p.get('units_min'),
            'webpage': p.get('webpage'),
            'requirements': p.get('requirements') or [],
        })

    # ── faculty ────────────────────────────────────────────────────────────
    faculty = []
    seen_ids = set()
    for p in faculty_raw:
        # joint appointments appear once per department roster; keep the first
        if p['profile_id'] in seen_ids:
            continue
        seen_ids.add(p['profile_id'])
        faculty.append({
            'profile_id': p['profile_id'],
            'name': p['name'],
            'first_name': p.get('first_name'),
            'last_name': p.get('last_name'),
            'department': p['department'],
            'short_title': p.get('short_title'),
            'titles': p.get('titles') or [],
            'bio': p.get('bio'),
            'research_interests': p.get('research_interests'),
            'education': p.get('education') or [],
            'publications': p.get('publications') or [],
            'publication_count': p.get('publication_count') or 0,
            'email': p.get('email'),
            'photo': os.path.basename(p['photo_url']) if p.get('photo_url') else None,
        })
    faculty.sort(key=lambda f: (f['department'], f['last_name'] or '', f['name'] or ''))

    # ── news ───────────────────────────────────────────────────────────────
    news_dir = os.path.join(HERE, 'static', 'images', 'upstream', 'news')
    news_files = set(os.listdir(news_dir)) if os.path.isdir(news_dir) else set()
    news = []
    for r in news_raw:
        slug = r['slug']
        img = None
        if r.get('og_image'):
            base = os.path.basename(r['og_image'].split('?')[0])
            stem, ext = f'news_{slug}', os.path.splitext(base)[1]
            # the upstream CDN serves WebP bytes for some .jpg URLs; match
            # the downloaded file by stem so the extension follows the bytes
            if stem + ext in news_files:
                img = stem + ext
            else:
                for cand_ext in ('.webp', '.jpg', '.png', '.gif'):
                    if stem + cand_ext in news_files:
                        img = stem + cand_ext
                        break
        news.append({
            'slug': slug,
            'title': r['title'],
            'published_ts': r.get('published_ts'),
            'category': r.get('category') or 'University News',
            'main_topic': r.get('main_topic') or '',
            'topics': sorted(set(
                [t for t in (r.get('topics') or []) if t]
                + ([r.get('main_topic')] if r.get('main_topic') else []))),
            'featured_unit': r.get('featured_unit') or '',
            'writers': r.get('writers') or [],
            'description': r.get('description'),
            'body': r.get('body') or [],
            'image': img,
        })

    # ── events ─────────────────────────────────────────────────────────────
    events = []
    for e in events_raw:
        events.append({
            'eid': e['id'],
            'title': e['title'],
            'description': e.get('description'),
            'first_date': e.get('first_date'),
            'last_date': e.get('last_date'),
            'location_name': e.get('location_name'),
            'room_number': e.get('room_number'),
            'address': e.get('address'),
            'experience': e.get('experience'),
            'free': bool(e.get('free')),
            'ticket_url': e.get('ticket_url'),
            'ticket_cost': e.get('ticket_cost'),
            'tags': sorted(set(t for t in (e.get('tags') or []) if t)),
            'keywords': sorted(set(k for k in (e.get('keywords') or []) if k)),
            'recurring': bool(e.get('recurring')),
            'featured': bool(e.get('featured')),
            'verified': bool(e.get('verified')),
            'photo': e.get('photo'),
            'instances': e.get('instances') or [],
        })

    # ── academic calendar ───────────────────────────────────────────────────
    calendar = []
    for qid in sorted(calendar_raw['quarters']):
        q = calendar_raw['quarters'][qid]
        for i, item in enumerate(q['items']):
            calendar.append({
                'quarter': q['title'],
                'quarter_key': qid,
                'position': i,
                'when': item['when'],
                'what': item['what'],
            })

    # ── libraries ──────────────────────────────────────────────────────────
    # The SUL hours roster titles the Tanner philosophy library differently
    # ("Philosophy Library (Tanner)") from its library.stanford.edu detail
    # page ("Tanner Memorial Library of Philosophy"); map the detail record
    # onto its roster row (detail name -> roster name) so the directory
    # carries one complete record instead of a duplicate with empty fields.
    HOURS_NAME_ALIASES = {
        'tanner memorial library of philosophy': 'philosophy library (tanner)',
    }
    hours_by_name = {}
    for hh in libraries_raw.get('hours', []):
        hours_by_name[hh['name'].lower()] = hh
    libraries = []
    lib_img_dir = os.path.join(HERE, 'static', 'images', 'upstream', 'libraries')
    lib_img_files = set(os.listdir(lib_img_dir)) if os.path.isdir(lib_img_dir) else set()
    for lib in libraries_raw['libraries']:
        slug = lib['slug']
        hours = None
        for cand in (lib['name'].lower(), slug.replace('-', ' ')):
            if cand in hours_by_name:
                hours = hours_by_name[cand]
                break
        if hours is None:
            alias = HOURS_NAME_ALIASES.get(lib['name'].lower())
            if alias and alias in hours_by_name:
                hours = hours_by_name[alias]
        libraries.append({
            'slug': slug,
            'name': lib['name'],
            'location': lib.get('location'),
            'phone': lib.get('phone'),
            'email': lib.get('email'),
            'about': lib.get('about'),
            'quick_links': lib.get('quick_links') or [],
            'research_subjects': lib.get('research_subjects') or [],
            'hours_days': (hours or {}).get('days') or [],
            'hours_rows': (hours or {}).get('rows') or [],
            'photo': (f'library_{slug}.jpg'
                      if f'library_{slug}.jpg' in lib_img_files else None),
        })
    # the hours page is the canonical roster: add libraries only present there
    have = {l['slug'] for l in libraries}
    name_to_slug = {l['name'].lower(): l['slug'] for l in libraries}
    for hh in libraries_raw.get('hours', []):
        nm = hh['name'].lower()
        if nm in name_to_slug or nm in have:
            continue
        # skip roster rows whose hours were merged onto an aliased record
        if any(HOURS_NAME_ALIASES.get(l['name'].lower()) == nm for l in libraries):
            continue
        libraries.append({
            'slug': hh['name'].lower().replace(' ', '-').replace('&', 'and').replace('(', '').replace(')', ''),
            'name': hh['name'],
            'location': None,
            'phone': None,
            'email': None,
            'about': None,
            'quick_links': [],
            'research_subjects': [],
            'hours_days': hh.get('days') or [],
            'hours_rows': hh.get('rows') or [],
            'photo': None,
        })

    # ── admission ──────────────────────────────────────────────────────────
    admission = {
        'requirements': admission_raw.get('requirements') or [],
        'deadlines': admission_raw.get('deadlines') or [],
        'aid_facts': admission_raw.get('aid_facts') or [],
    }

    return {
        'departments': departments,
        'courses': courses,
        'programs': programs,
        'faculty': faculty,
        'news': news,
        'events': events,
        'calendar': calendar,
        'libraries': libraries,
        'admission': admission,
        'home': home_raw,
    }


BENCHMARK_USERS = [
    {'name': 'Alice Johnson', 'email': 'alice.j@test.com'},
    {'name': 'Bob Chen', 'email': 'bob.c@test.com'},
    {'name': 'Carol Davis', 'email': 'carol.d@test.com'},
    {'name': 'Dana Kim', 'email': 'dana.k@test.com'},
]

# Authored fixtures: real captured courses/events, added at a frozen instant.
PLANNER_FIXTURES = {
    'alice.j@test.com': ['CS106A', 'MATH51', 'PHYSICS41'],
    'bob.c@test.com': ['ECON1', 'PSYCH1'],
    'carol.d@test.com': [],
    'dana.k@test.com': ['BIO102'],
}


def planner_targets(records):
    """Resolve fixture course codes to (user, course) pairs deterministically."""
    by_code = {c['code']: c for c in records['courses']}
    out = []
    for email, codes in sorted(PLANNER_FIXTURES.items()):
        for code in codes:
            if code in by_code:
                out.append((email, by_code[code]))
    return out


def saved_event_targets(records):
    """Deterministically pick real captured events for the fixtures."""
    by_eid = {e['eid']: e for e in records['events']}
    picks = {
        'alice.j@test.com': None,
        'bob.c@test.com': None,
        'carol.d@test.com': None,
        'dana.k@test.com': None,
    }
    # first verified event whose date is after the frozen mirror date, in id order
    upcoming = sorted((e for e in records['events'] if e['first_date'] and e['first_date'] >= '2026-10-01'),
                      key=lambda e: (e['first_date'], e['eid']))
    for email in sorted(picks):
        for e in upcoming:
            picks[email] = e
            upcoming = upcoming[1:]
            break
    return [(email, e) for email, e in sorted(picks.items()) if e]
