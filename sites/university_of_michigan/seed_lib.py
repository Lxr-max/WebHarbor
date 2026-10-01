#!/usr/bin/env python3
"""Deterministic seed builder for the university_of_michigan mirror.

Materializes the tracked source_data/*.json snapshots (captured from
umich.edu and its services on 2026-09-30 — see provenance.json) into the
SQLite database. Every function is gated so importing app.py twice or
running seed_data.py again is a no-op; with PYTHONHASHSEED=0 the output
file is byte-reproducible.
"""
import json
import os

MIRROR_TS = '2026-09-30'

# bcrypt hash of 'TestPass123!' — frozen so the seed DB is byte-reproducible.
BENCHMARK_HASH = ('$2b$12$qSds4Mr9Wo7VwPWLhompEer88SuxxXFDp31P9etY6v7nfRctNO7B.')

BENCHMARK_USERS = [
    ('alice.j@test.com', 'Alice Johnson'),
    ('bob.c@test.com', 'Bob Chen'),
    ('carol.d@test.com', 'Carol Davis'),
    ('dana.k@test.com', 'Dana Kim'),
]


def _load(name):
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, 'source_data', name), encoding='utf-8') as f:
        return json.load(f)


def seed_all(db):
    from app import (AcademicTerm, AppPlan, Building, CalendarEntry, Course,
                    Deadline, EventItem, Instructor, LibraryItem, NewsArticle,
                    Program, School, Section, TuitionRow)

    if School.query.count() > 0:
        return

    images = _load('image_assignments.json') or {}

    # ------------------------------------------------------------- schools --
    for row in _load('schools.json'):
        db.session.add(School(
            slug=row['slug'], short_name=row['short_name'],
            full_name=row['full_name'], url=row['url'],
            blurb=row.get('meta_description') or '',
            campus=row.get('campus') or 'Ann Arbor',
            image=(images.get('schools') or {}).get(row['slug'])))

    # ------------------------------------------------------------ programs --
    PROGRAM_SCHOOL_SLUG = {
        'College of Engineering': 'engineering',
        'College of Literature, Science, and the Arts (LSA)': 'lsa',
        'College of Pharmacy': 'pharmacy',
        'Ford School of Public Policy': 'publicpolicy',
        'Marsal Family School of Education': 'education',
        'Ross School of Business': 'ross',
        'School of Dentistry': 'dentistry',
        'School of Information': 'umsi',
        'School of Kinesiology': 'kinesiology',
        'School of Music, Theatre & Dance (SMTD)': 'smtd',
        'School of Nursing': 'nursing',
        'School of Public Health': 'publichealth',
        'School of Social Work': 'socialwork',
        'Stamps School of Art & Design': 'stamps',
        'Taubman College of Architecture & Urban Planning': 'taubman',
    }
    for row in _load('programs.json'):
        db.session.add(Program(
            name=row['name'], school=row['school'],
            school_slug=PROGRAM_SCHOOL_SLUG.get(row['school']),
            submajor=row['submajor'], sort_letter=row['sort_letter']))

    # ------------------------------------------------------------- courses --
    courses = _load('courses.json')
    seen_instructors = {}
    for row in courses:
        attrs = row.get('attributes') or []
        course = Course(
            subject=row['subject'], number=row['number'],
            title=row['title'], school=row['school'],
            description=row.get('description'),
            career=row.get('career'),
            attributes=json.dumps(attrs))
        db.session.add(course)
        db.session.flush()
        for s in row['sections']:
            db.session.add(Section(
                course_id=course.id, class_nbr=s['class_nbr'],
                section=s['section'], component=s['component'],
                session=s.get('session'), instructor=s.get('instructor') or '',
                dates=s.get('dates'), units=s.get('units'),
                mode=s.get('mode'), enrl_restrict=s.get('enrl_restrict'),
                reserved_for=s.get('reserved_for'), avail=s.get('avail'),
                waitlist=s.get('waitlist'), status=s.get('status', ''),
                topic=s.get('topic'), combined=bool(s.get('combined'))))
            name = (s.get('instructor') or '').strip()
            if name and name not in ('Staff', 'See Department'):
                key = name
                if key not in seen_instructors:
                    seen_instructors[key] = {'name': name,
                                             'school': row['school'],
                                             'subjects': set()}
                seen_instructors[key]['subjects'].add(row['subject'])
    for name in sorted(seen_instructors):
        info = seen_instructors[name]
        db.session.add(Instructor(
            name=name, school=info['school'],
            subjects=json.dumps(sorted(info['subjects']))))
    db.session.commit()

    # ----------------------------------------------- academic terms/calendar --
    cal = _load('academic_calendar.json')
    for term in cal['term_order']:
        block = cal['terms'].get(term, {})
        academic = block.get('Academic Calendar', [])
        registration = block.get('Registration Deadlines', [])
        db.session.add(AcademicTerm(name=term,
                                    academic_events=json.dumps(academic),
                                    registration_events=json.dumps(registration)))
        for ev in academic:
            db.session.add(CalendarEntry(term=term, ctype='Academic Calendar',
                                         date_str=ev['date'], event=ev['event']))
        for ev in registration:
            db.session.add(CalendarEntry(term=term, ctype='Registration Deadlines',
                                         date_str=ev['date'], event=ev['event']))

    # ----------------------------------------------------------- buildings --
    for row in _load('buildings.json'):
        db.session.add(Building(
            slug=row['slug'], name=row['name'], address=row.get('address') or '',
            city=row.get('city') or '', zip=row.get('zip') or '',
            lat=row.get('lat'), lng=row.get('lng'),
            category=row.get('category') or '',
            acronym=row.get('acronym'), website=row.get('website'),
            elevator=bool(row.get('elevator')), ramp=bool(row.get('ramp'))))

    # -------------------------------------------------------- library items --
    for row in _load('library_items.json'):
        db.session.add(LibraryItem(
            uuid=row['uuid'], handle=row.get('handle') or '',
            title=row['name'] or '', authors=json.dumps(row.get('authors') or []),
            date_issued=row.get('date_issued') or '', type=row.get('type') or '',
            subjects=json.dumps(row.get('subjects') or []),
            abstract=row.get('abstract') or '', uri=row.get('uri') or '',
            degree=row.get('degree') or ''))

    # -------------------------------------------------------------- news ----
    cats = _load('news_categories.json')
    for row in _load('news_articles.json'):
        published = (row.get('published') or '')[:10]
        db.session.add(NewsArticle(
            slug=row['slug'], title=row['title'] or '',
            published=published, description=row.get('description') or '',
            author=row.get('author'), body=json.dumps(row.get('body') or []),
            categories=json.dumps(cats.get(row['slug'], [])),
            image=(images.get('news') or {}).get(row['slug'])))

    # ------------------------------------------------------------- events ---
    for row in _load('events.json'):
        db.session.add(EventItem(
            eid=row['id'], name=row['name'] or '', type=row.get('type') or '',
            presenter=row.get('presenter') or '',
            start=row.get('startDate') or '', end=row.get('endDate') or '',
            location_name=row.get('location_name') or '',
            street=row.get('street') or '', city=row.get('city') or '',
            description=row.get('description') or '',
            image=(images.get('events') or {}).get(row['id'])))

    # ---------------------------------------------------------- admissions --
    adm = _load('admissions.json')
    for row in adm['costs_2026_27']:
        db.session.add(TuitionRow(
            residency=row['residency'], level=row['level'],
            tuition_fees=row['tuition_fees'], living=row['living'],
            books=row['books'], transport=row['transport'],
            personal=row['personal'], total=row['total']))
    for row in adm['application_deadlines']:
        db.session.add(Deadline(
            group='application', date=row['date'],
            items=json.dumps(row['items'])))
    for row in adm['aid_deadlines']:
        db.session.add(Deadline(
            group='aid', date=row['date'],
            items=json.dumps([row['item']])))
    for row in adm['application_plans']:
        db.session.add(AppPlan(
            plan=row['plan'], binding=bool(row.get('binding')),
            deadline=row.get('deadline') or '', aid_deadline=row.get('aid_deadline') or '',
            decision=row.get('decision') or '', commit=row.get('commit') or ''))
    db.session.commit()


def seed_benchmark_users(db):
    from app import (BackpackItem, Course, EventItem, Program, SavedEvent,
                     SavedProgram, Section, User)
    if User.query.filter_by(email='alice.j@test.com').first():
        return
    users = {}
    for email, name in BENCHMARK_USERS:
        user = User(email=email, name=name, password_hash=BENCHMARK_HASH,
                    joined=MIRROR_TS)
        db.session.add(user)
        users[email] = user
    db.session.commit()

    def section_by_nbr(nbr):
        return Section.query.filter_by(class_nbr=str(nbr)).first()

    def section_by_subject_number(subject, number, section='001'):
        c = Course.query.filter_by(subject=subject, number=number).first()
        if not c:
            return None
        s = Section.query.filter_by(course_id=c.id, section=section).first()
        return s or Section.query.filter_by(course_id=c.id).first()

    def program_by_name(name):
        return Program.query.filter_by(name=name).first()

    def event_by_name(name):
        return EventItem.query.filter_by(name=name).first()

    fixtures = {
        'alice.j@test.com': [
            ('backpack', 'CHEM', '125', '100'),
            ('backpack', 'MATH', '115', '001'),
            ('program', 'Biology'),
            ('event', 'T.REX'),
        ],
        'bob.c@test.com': [
            ('backpack', 'ECON', '101', '100'),
            ('backpack', 'EECS', '183', '001'),
            ('program', 'Computer Science (BS)'),
            ('event', 'Maize & Blue Cupboard Volunteering'),
        ],
        'carol.d@test.com': [
            ('backpack', 'EEB', '313', '001'),
            ('program', 'Psychology'),
            ('program', 'Nursing'),
            ('event', 'Learn to Meditate in 3 days'),
        ],
        'dana.k@test.com': [
            ('backpack', 'SI', '110', '001'),
            ('program', 'English'),
            ('event', 'Susan Werner'),
        ],
    }
    for email, entries in fixtures.items():
        user = users[email]
        for entry in entries:
            if entry[0] == 'backpack':
                sec = section_by_subject_number(entry[1], entry[2], entry[3])
                if sec:
                    db.session.add(BackpackItem(
                        user_id=user.id, section_id=sec.id, added_at=MIRROR_TS))
            elif entry[0] == 'program':
                prog = program_by_name(entry[1])
                if prog:
                    db.session.add(SavedProgram(
                        user_id=user.id, program_id=prog.id, added_at=MIRROR_TS))
            elif entry[0] == 'event':
                ev = event_by_name(entry[1])
                if ev:
                    db.session.add(SavedEvent(
                        user_id=user.id, event_id=ev.id, added_at=MIRROR_TS))
    db.session.commit()
