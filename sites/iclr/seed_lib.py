#!/usr/bin/env python3
"""Deterministic seed builder for the iclr mirror.

Everything materialized here comes from the tracked source_data/*.json
snapshots (captured 2026-09-30, see provenance.json) in a fixed, sorted
order. The four benchmark accounts and their bookmarks / saved events /
registrations are authored fixtures following the u_s_customs / zara /
disney precedent: every paper, event, workshop, sponsor, organizer and
news item they reference is a real captured upstream row, and every
timestamp is a frozen constant so the SQLite output is byte-reproducible
(PYTHONHASHSEED=0).
"""
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
SOURCE = os.path.join(HERE, 'source_data')

BENCHMARK_HASH = (
    '$2b$12$qSds4Mr9Wo7VwPWLhompEer88SuxxXFDp31P9etY6v7nfRctNO7B.')
MIRROR_TS = '2026-09-30'


def _load(name):
    with open(os.path.join(SOURCE, name), encoding='utf-8') as f:
        return json.load(f)


_ASSET_MAP = None


def _asset_map():
    """source_url -> local filename, resolved from the tracked inventory."""
    global _ASSET_MAP
    if _ASSET_MAP is None:
        _ASSET_MAP = {}
        path = os.path.join(HERE, 'asset_inventory.json')
        if os.path.exists(path):
            with open(path, encoding='utf-8') as f:
                for row in json.load(f).get('assets', []):
                    _ASSET_MAP[row.get('source_url')] = \
                        row['path'].split('/')[-1]
    return _ASSET_MAP


def asset_name(url):
    """Deterministic local filename for an upstream image URL (None when the
    mirror does not ship that asset — the UI renders initials instead)."""
    if not url:
        return None
    mapped = _asset_map().get(url)
    if mapped:
        return mapped
    # the two organizer portraits referenced over http:// are shipped from
    # their https equivalents (both hosts serve https; see provenance)
    if url.startswith('http://'):
        mapped = _asset_map().get(url.replace('http://', 'https://', 1))
        if mapped:
            return mapped
    return None


# ------------------------------------------------------------------ helpers --

def _rio_clock(iso_instant):
    """'2026-04-25T07:42:00-07:00' -> ('2026-04-25', '11:42').

    The upstream JSON labels instants with a -07:00 offset while the
    conference ran at UTC-3; the instants are correct, so the Rio wall
    clock is the -07:00 clock plus four hours (cross-checked against the
    captured session pages: 07:42-07:00 == 11:42 -03).
    """
    m = re.match(r'(\d{4}-\d{2}-\d{2})T(\d{2}):(\d{2}):\d{2}', iso_instant or '')
    if not m:
        return None, None
    date, hour, minute = m.group(1), int(m.group(2)), m.group(3)
    hour += 4
    if hour >= 24:
        hour -= 24
        y, mo, d = (int(x) for x in date.split('-'))
        d += 1
        date = f'{y:04d}-{mo:02d}-{d:02d}'
    return date, f'{hour:02d}:{minute}'


# --------------------------------------------------------------------- seeds --

def seed_schedule(db):
    from app import SessionEvent
    schedule = _load('schedule.json')
    for day in schedule['days']:
        for sess in day['sessions']:
            room = ''
            m = re.search(r'Pavilion (\d+)', sess['title'])
            if m:
                room = f'Pavilion {m.group(1)}'
            db.session.add(SessionEvent(
                id=sess['id'], title=sess['title'], kind=sess['kind'],
                date=day['date'], day_label=day['label'],
                start=sess['start'], end=sess['end'], room=room or None))
    db.session.commit()


def seed_events(db):
    from app import Event
    for row in _load('events.json'):
        db.session.add(Event(
            id=row['id'], kind=row['kind'], title=row['title'],
            date=row['date'], day_label=row['day_label'],
            start=row['start'], end=row['end'],
            speaker=row['speaker'] or None,
            people=json.dumps(row['people'], ensure_ascii=False),
            abstract=row['abstract'] or None,
            website=row['website'] or None,
            overflow_room=row['overflow_room'] or None,
            headshot_url=asset_name(row['headshot_url']),
            headshot_alt=row['headshot_alt'] or None,
            speaker_bio=row['speaker_bio'] or None,
            schedule=json.dumps(row['schedule'], ensure_ascii=False)
            if row['schedule'] else None,
        ))
    db.session.commit()


def seed_papers(db):
    from app import Paper
    schedule = _load('schedule.json')
    windows = {s['title']: s for s in schedule['sessions'].values()}
    day_by_session = {}
    for day in schedule['days']:
        for sess in day['sessions']:
            day_by_session[sess['title']] = day['date']

    for row in _load('papers.json'):
        session = row['session'] or ''
        window = windows.get(session) or {}
        day = day_by_session.get(session) or ''
        talk_start = talk_end = None
        if row['eventtype'] == 'Oral':
            d1, talk_start = _rio_clock(row['start'])
            d2, talk_end = _rio_clock(row['end'])
            if not day:
                day = d1 or ''
        db.session.add(Paper(
            id=row['id'],
            title=row['title'],
            authors=json.dumps(row['authors'], ensure_ascii=False),
            topic=row['topic'] or None,
            decision=row['decision'],
            eventtype=row['eventtype'],
            session=session or None,
            room=row['room'] or None,
            day=day or None,
            session_start=window.get('start') or None,
            session_end=window.get('end') or None,
            talk_start=talk_start,
            talk_end=talk_end,
            poster_position=row['poster_position'] or None,
            openreview_url=row['openreview_url'] or None,
            abstract=row['abstract'] or None,
        ))
    db.session.commit()


def seed_sponsors(db):
    from app import Sponsor
    for row in _load('sponsors.json'):
        db.session.add(Sponsor(
            name=row['name'], tier=row['tier'], url=row['url']))
    db.session.commit()


def seed_organizers(db):
    from app import Organizer
    for row in _load('organizers.json'):
        db.session.add(Organizer(
            name=row['name'], role=row['role'],
            institution=row['institution'] or None,
            photo=asset_name(row['photo_url']),
            bio=row['bio'] or None))
    db.session.commit()


def seed_news(db):
    from app import NewsPost
    for row in _load('news.json'):
        db.session.add(NewsPost(
            slug=row['slug'], title=row['title'], date=row['date'],
            author=row['author'] or None,
            body=json.dumps(row['body'], ensure_ascii=False),
            upstream_url=row['upstream_url']))
    db.session.commit()


def seed_awards(db):
    from app import Award
    for group in _load('awards.json'):
        for entry in group['entries']:
            db.session.add(Award(
                award_group=group['award'], kind=entry['kind'],
                title=entry['title'],
                authors=json.dumps(entry['authors'], ensure_ascii=False),
                citation=entry.get('citation') or None,
                source_url=group['source_url']))
    db.session.commit()


def seed_dates(db):
    from app import DateItem
    data = _load('dates.json')
    for year in ('2026', '2027'):
        for group in data.get(year, []):
            for item in group['items']:
                db.session.add(DateItem(
                    year=year, group_name=group['group'],
                    name=item['name'], date_str=item['date']))
    db.session.commit()


# -------------------------------------------------------- benchmark fixtures --

BENCHMARK_USERS = [
    ('alice.j@test.com', 'Alice Johnson'),
    ('bob.c@test.com', 'Bob Chen'),
    ('carol.d@test.com', 'Carol Diaz'),
    ('dana.k@test.com', 'Dana Kim'),
]


def _paper_by_title(db, fragment):
    from app import Paper
    row = (Paper.query.filter(Paper.title.ilike(f'%{fragment}%'))
           .order_by(Paper.id).first())
    assert row is not None, f'no captured paper matches {fragment!r}'
    return row


def _event_by_title(db, fragment, kind=None):
    from app import Event
    query = Event.query.filter(Event.title.ilike(f'%{fragment}%'))
    if kind:
        query = query.filter(Event.kind == kind)
    row = query.order_by(Event.id).first()
    assert row is not None, f'no captured event matches {fragment!r}'
    return row


def seed_benchmark_users(db):
    from app import (Bookmark, Registration, ScheduleSave, User)
    if User.query.filter_by(email='alice.j@test.com').first():
        return
    users = {}
    for email, name in BENCHMARK_USERS:
        user = User(email=email, name=name, password_hash=BENCHMARK_HASH,
                    joined=MIRROR_TS)
        db.session.add(user)
        users[email] = user
    db.session.commit()

    # every fixture row below references a real captured upstream record
    fixtures = {
        'alice.j@test.com': [
            ('paper', 'Escaping Policy Contraction'),
            ('paper', 'Latent Speech-Text Transformer'),
            ('paper', 'Transformers are Inherently Succinct'),
        ],
        'bob.c@test.com': [
            ('paper', 'LLMs Get Lost In Multi-Turn Conversation'),
            ('event', "I Can't Believe It's Not Better", 'workshop'),
        ],
        'carol.d@test.com': [
            ('paper', 'The Polar Express'),
            ('event', 'Marin: Open Development of Frontier AI', 'invited-talk'),
            ('event', 'VerifAI-2', 'workshop'),
        ],
        'dana.k@test.com': [
            ('paper', 'Your Language Model Secretly Contains Personality '
                      'Subnetworks'),
            ('paper', 'P-GenRM: Personalized Generative Reward Model'),
            ('event', 'AI for Peace', 'workshop'),
        ],
    }
    for email, entries in fixtures.items():
        user = users[email]
        for entry in entries:
            if entry[0] == 'event':
                event = _event_by_title(db, entry[1], entry[2])
                db.session.add(ScheduleSave(user_id=user.id,
                                           event_id=event.id,
                                           added_at=MIRROR_TS))
            else:
                paper = _paper_by_title(db, entry[1])
                db.session.add(Bookmark(user_id=user.id,
                                       paper_id=paper.id,
                                       added_at=MIRROR_TS))
    db.session.commit()

    # a completed registration for Alice mirroring the captured 2026 form
    # (the only captured price is the $50 guest banquet ticket)
    alice = users['alice.j@test.com']
    db.session.add(Registration(
        user_id=alice.id, name='Alice Johnson', email='alice.j@test.com',
        affiliation='Full time student',
        items=json.dumps(['Conference Sessions and Workshops']),
        banquet_tickets=1, dietary='Vegetarian',
        total_usd=50, reg_code='ICLR26-A1B2C3D4', created=MIRROR_TS))
    db.session.commit()


# ---------------------------------------------------------------- entry point --

def seed_all(db):
    """Populate every content table from the tracked snapshots."""
    seed_schedule(db)
    seed_events(db)
    seed_papers(db)
    seed_sponsors(db)
    seed_organizers(db)
    seed_news(db)
    seed_awards(db)
    seed_dates(db)
