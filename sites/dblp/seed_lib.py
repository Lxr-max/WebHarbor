#!/usr/bin/env python3
"""Deterministic seed builder for the dblp mirror.

Everything materialized here comes from the tracked source_data/*.json
snapshots (captured from dblp.org 2026-09-30) in a fixed, sorted order; the
four benchmark accounts and their watchlists, saved searches, saved papers
and search history are authored fixtures following the u_s_customs/zara
precedent: every record they reference is a real captured upstream row
(real dblp key, real pid), selected by deterministic queries, and every
timestamp is a frozen constant so the SQLite output is byte-reproducible
(PYTHONHASHSEED=0).
"""
import json
import os
import re
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
SOURCE = os.path.join(HERE, 'source_data')

BENCHMARK_HASH = (
    '$2b$12$qSds4Mr9Wo7VwPWLhompEer88SuxxXFDp31P9etY6v7nfRctNO7B.')
MIRROR_TS = '2026-09-30'

TYPE_LABELS = {
    'article': 'Journal Articles',
    'inproceedings': 'Conference and Workshop Papers',
    'informal': 'Informal Publications',
    'data': 'Data and Artifacts',
    'software': 'Data and Artifacts',
    'incollection': 'Books and Theses',
    'book': 'Books and Theses',
    'phdthesis': 'Books and Theses',
    'mastersthesis': 'Books and Theses',
    'proceedings': 'Editorships',
    'editorship': 'Editorships',
}


def _fold(s):
    s = unicodedata.normalize('NFKD', s or '')
    return ''.join(c for c in s if not unicodedata.combining(c)).lower()


def _name_base(name):
    """Strip dblp's disambiguation suffix: 'Jiawei Han 0001' -> 'Jiawei Han'."""
    return re.sub(r'\s+\d{4}$', '', name or '').strip()


def _load(name):
    with open(os.path.join(SOURCE, name), encoding='utf-8') as f:
        return json.load(f)


def build_seed(db, bcrypt):
    venues = _load('venues.json')
    pubs = _load('publications.json')
    containers = _load('containers.json')
    profiles = {a['pid']: a for a in _load('authors.json')}

    # -- venues + editions ---------------------------------------------------
    venue_ids = {}
    edition_ids = {}
    for v in sorted(venues, key=lambda x: x['stream']):
        row = VenueRow(stream=v['stream'],
                      vtype='journal' if v['stream'].startswith('journals/')
                      else 'conference',
                      name=v['name'], abbr=v.get('abbr'), note=v.get('note'),
                      info=json.dumps(v.get('info', [])))
        db.session.add(row)
        db.session.flush()
        venue_ids[v['stream']] = row.id
        editions = list(v.get('editions', []))
        vols = list(v.get('volumes', []))
        # journals: one edition per captured volume
        if v['stream'].startswith('journals/'):
            stream_tail = v['stream'].split('/', 1)[1]
            for vol in vols:
                key = f"journals/{stream_tail}/{vol['key']}"
                cont = containers.get(key)
                if not cont:
                    continue  # volume not captured in the mirror corpus
                row = EditionRow(
                    venue_id=venue_ids[v['stream']], key=key,
                    toc=vol['key'], year=_vol_year(vol, cont),
                    title=cont.get('title') or vol['label'],
                    volume_label=vol['label'],
                    editors=json.dumps(
                        [{'pid': p, 'name': n} for p, n in
                         zip(cont.get('editor_pids', []),
                             cont.get('editors', []))]),
                    publisher=cont.get('publisher'))
                db.session.add(row)
                db.session.flush()
                edition_ids[key] = row.id
        else:
            for ed in editions:
                cont = containers.get(ed['key'], {})
                if not cont:
                    continue
                row = EditionRow(
                    venue_id=venue_ids[v['stream']], key=ed['key'],
                    toc=ed['toc'], year=int(ed['year']),
                    title=cont.get('title') or ed['title'],
                    volume_label=None,
                    editors=json.dumps(
                        [{'pid': p, 'name': n} for p, n in
                         zip(cont.get('editor_pids', []),
                             cont.get('editors', []))]),
                    publisher=cont.get('publisher'))
                db.session.add(row)
                db.session.flush()
                edition_ids[ed['key']] = row.id

    # -- publications ---------------------------------------------------------
    seen = set()
    pub_ids = {}
    for p in sorted(pubs, key=lambda r: r['key']):
        if p['key'] in seen:
            continue
        seen.add(p['key'])
        stream = '/'.join(p['key'].split('/')[:2])
        ed_id = edition_ids.get(p.get('crossref'))
        search_parts = [p['title']]
        search_parts.extend(a['name'] for a in p['authors'])
        vrow = next((v for v in venues if v['stream'] == stream), None)
        if vrow:
            search_parts.append(vrow['name'])
        if p.get('booktitle'):
            search_parts.append(p['booktitle'])
        if p.get('journal'):
            search_parts.append(p['journal'])
        row = PubRow(
            rec_key=p['key'], rtype=p['type'],
            type_label=TYPE_LABELS.get(p['type'], 'Other'),
            title=p['title'], year=int(p['year']),
            pages=p.get('pages'), volume=p.get('volume'),
            number=p.get('number'), booktitle=p.get('booktitle'),
            journal=p.get('journal'), doi=p.get('doi'),
            ee=json.dumps(p.get('ee', [])), mdate=p.get('mdate'),
            edition_id=ed_id, stream=stream,
            search_text=_fold(' | '.join(search_parts)))
        db.session.add(row)
        db.session.flush()
        pub_ids[p['key']] = row.id
        for pos, a in enumerate(p['authors']):
            db.session.add(PubAuthorRow(
                publication_id=row.id,
                author_pid=a['pid'] or _synth_pid(a['name']),
                name=a['name'], orcid=a.get('orcid'), position=pos))

    # -- authors ---------------------------------------------------------------
    author_pids = set()
    name_by_pid = {}
    for p in pubs:
        for a in p['authors']:
            pid = a['pid'] or _synth_pid(a['name'])
            author_pids.add(pid)
            name_by_pid.setdefault(pid, a['name'])
    for pid in sorted(author_pids):
        prof = profiles.get(pid, {})
        name = prof.get('name') or name_by_pid.get(pid) or pid
        db.session.add(AuthorRow(
            pid=pid, name=name, name_base=_name_base(name),
            n_upstream=prof.get('n_upstream'),
            urls=json.dumps(prof.get('urls', [])),
            affiliations=json.dumps(prof.get('affiliations', [])),
            awards=json.dumps(prof.get('awards', [])),
            uname=prof.get('uname'),
            profile_fetched=bool(prof.get('profile_fetched'))))

    # -- per-edition record counts (denormalized for the venue pages) --------
    for ed in Edition.query.all():
        ed.n_records = Publication.query.filter_by(edition_id=ed.id).count()

    db.session.commit()


def _synth_pid(name):
    return 'zz/' + re.sub(r'[^A-Za-z0-9]+', '', _fold(name))[:40]


def _vol_year(vol, cont):
    m = re.search(r'(\d{4})', vol.get('label', ''))
    if m:
        return int(m.group(1))
    if cont.get('year'):
        return int(cont['year'])
    return 0


# --------------------------------------------------------------------------
# Thin row factories kept separate so the import of app.py stays at module
# import time (the app materializes the seed inside its own context).
# --------------------------------------------------------------------------

from app import (Author as AuthorRow, Edition as EditionRow,
                 Publication as PubRow, PubAuthor as PubAuthorRow,
                 Venue as VenueRow,  # noqa: E402
                 Author, Edition, Publication, PubAuthor, SavedPaper,
                 SavedSearch, SearchHistory, User, Venue, WatchAuthor,
                 WatchVenue)


def build_benchmark_users(db, bcrypt):
    """Four fixture accounts, all referencing real corpus rows."""
    users = [
        dict(email='alice.j@test.com', display_name='Alice Johnson',
             affiliation='Stanford University',
             research_interests='graph neural networks, transformers'),
        dict(email='bob.c@test.com', display_name='Bob Chen',
             affiliation='University of Washington',
             research_interests='query optimization, learned indexes'),
        dict(email='carol.d@test.com', display_name='Carol Davis',
             affiliation='Carnegie Mellon University',
             research_interests='side channels, fuzzing'),
        dict(email='dana.k@test.com', display_name='Dana Kim',
             affiliation='KAIST',
             research_interests='question answering, retrieval'),
    ]
    for i, u in enumerate(users):
        db.session.add(User(email=u['email'], display_name=u['display_name'],
                            password_hash=BENCHMARK_HASH, is_benchmark=True,
                            affiliation=u['affiliation'],
                            research_interests=u['research_interests'],
                            created_at='2026-09-01'))

    def top_authors_in(stream, n):
        rows = (db.session.query(Author, db.func.count(PubAuthor.id))
                .join(PubAuthor, PubAuthor.author_pid == Author.pid)
                .join(Publication, Publication.id == PubAuthor.publication_id)
                .filter(Publication.stream == stream)
                .group_by(Author.id)
                .order_by(db.func.count(PubAuthor.id).desc(), Author.pid)
                .limit(n).all())
        return [r[0] for r in rows]

    def pubs_in(stream, keyword=None, n=6):
        q = Publication.query.filter_by(stream=stream)
        if keyword:
            q = q.filter(Publication.title.like(f'%{keyword}%'))
        return q.order_by(Publication.rec_key).limit(n).all()

    def hits(q):
        from app import search_publications
        return search_publications(q).count()

    db.session.flush()

    # -- Alice: ML researcher -------------------------------------------------
    alice = User.query.filter_by(email='alice.j@test.com').first()
    for a in top_authors_in('conf/nips', 3):
        db.session.add(WatchAuthor(user_id=alice.id, author_pid=a.pid,
                                   added_at='2026-09-02'))
    for stream in ('conf/nips', 'conf/icml'):
        v = Venue.query.filter_by(stream=stream).first()
        db.session.add(WatchVenue(user_id=alice.id, venue_id=v.id,
                                  added_at='2026-09-02'))
    db.session.add(SavedSearch(user_id=alice.id, query_text='graph neural network',
                               search_type='publ', label='GNN papers',
                               created_at='2026-09-03'))
    db.session.add(SavedSearch(user_id=alice.id, query_text='transformer',
                               search_type='publ', created_at='2026-09-04'))
    for p in pubs_in('conf/nips', 'graph', 6):
        db.session.add(SavedPaper(user_id=alice.id, publication_id=p.id,
                                 collection='My Library',
                                 saved_at='2026-09-05'))
    for q in ['graph neural network', 'transformer', 'attention']:
        db.session.add(SearchHistory(user_id=alice.id, query_text=q,
                                     search_type='publ', hits=hits(q),
                                     ran_at='2026-09-05 10:00'))

    # -- Bob: database researcher ----------------------------------------------
    bob = User.query.filter_by(email='bob.c@test.com').first()
    for a in top_authors_in('conf/sigmod', 2):
        db.session.add(WatchAuthor(user_id=bob.id, author_pid=a.pid,
                                   added_at='2026-09-02'))
    for stream in ('conf/sigmod', 'journals/pvldb', 'journals/pacmmod'):
        v = Venue.query.filter_by(stream=stream).first()
        db.session.add(WatchVenue(user_id=bob.id, venue_id=v.id,
                                  added_at='2026-09-02'))
    db.session.add(SavedSearch(user_id=bob.id, query_text='query optimization',
                               search_type='publ', created_at='2026-09-03'))
    for p in pubs_in('journals/pvldb', 'query', 5):
        db.session.add(SavedPaper(user_id=bob.id, publication_id=p.id,
                                  collection='DB reading list',
                                  saved_at='2026-09-05'))
    for q in ['query optimization', 'learned index', 'join']:
        db.session.add(SearchHistory(user_id=bob.id, query_text=q,
                                     search_type='publ', hits=hits(q),
                                     ran_at='2026-09-06 09:00'))

    # -- Carol: security researcher --------------------------------------------
    carol = User.query.filter_by(email='carol.d@test.com').first()
    for a in top_authors_in('conf/sp', 2):
        db.session.add(WatchAuthor(user_id=carol.id, author_pid=a.pid,
                                   added_at='2026-09-02'))
    for stream in ('conf/sp', 'journals/tifs'):
        v = Venue.query.filter_by(stream=stream).first()
        db.session.add(WatchVenue(user_id=carol.id, venue_id=v.id,
                                  added_at='2026-09-02'))
    db.session.add(SavedSearch(user_id=carol.id, query_text='side-channel',
                               search_type='publ', created_at='2026-09-03'))
    db.session.add(SavedSearch(user_id=carol.id, query_text='fuzzing',
                               search_type='publ', created_at='2026-09-03'))
    for p in pubs_in('conf/sp', None, 4):
        db.session.add(SavedPaper(user_id=carol.id, publication_id=p.id,
                                  collection='My Library',
                                  saved_at='2026-09-04'))
    for q in ['side-channel', 'fuzzing']:
        db.session.add(SearchHistory(user_id=carol.id, query_text=q,
                                     search_type='publ', hits=hits(q),
                                     ran_at='2026-09-04 14:30'))

    # -- Dana: NLP / IR researcher ----------------------------------------------
    dana = User.query.filter_by(email='dana.k@test.com').first()
    for a in top_authors_in('conf/acl', 2):
        db.session.add(WatchAuthor(user_id=dana.id, author_pid=a.pid,
                                   added_at='2026-09-02'))
    for stream in ('conf/acl', 'journals/tois'):
        v = Venue.query.filter_by(stream=stream).first()
        db.session.add(WatchVenue(user_id=dana.id, venue_id=v.id,
                                  added_at='2026-09-02'))
    db.session.add(SavedSearch(user_id=dana.id, query_text='question answering',
                               search_type='publ', label='QA',
                               created_at='2026-09-03'))
    for p in pubs_in('conf/acl', 'question', 5):
        db.session.add(SavedPaper(user_id=dana.id, publication_id=p.id,
                                  collection='QA papers',
                                  saved_at='2026-09-06'))
    for q in ['question answering', 'retrieval', 'summarization',
              'language model', 'embedding']:
        db.session.add(SearchHistory(user_id=dana.id, query_text=q,
                                     search_type='publ', hits=hits(q),
                                     ran_at='2026-09-06 16:00'))

    db.session.commit()
