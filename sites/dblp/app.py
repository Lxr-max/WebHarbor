#!/usr/bin/env python3
"""dblp — a WebHarbor mirror of https://dblp.org/ (the dblp computer
science bibliography).

Flask + SQLite mirror of the dblp search & browse experience: the combined
search page, publication / author / venue search with the upstream query
semantics (case-insensitive prefix match, `$` exact-word suffix, space =
AND, `|` = OR, `venue:`/`year:`/`streamid:` filters), author profile pages
(person information, homonyms, publications grouped by decade, coauthor
index, per-year statistics), venue stream pages (conference series and
journals with editions/volumes, venue statistics), edition tables of
contents, record detail pages with BibTeX downloads, the dblp blog news
section, and a fixture-built personal area (watchlists of authors and
venues, saved searches, saved papers with collections and BibTeX export,
search history) seeded for four benchmark users.

Content comes from the tracked source_data/*.json snapshots captured from
dblp.org on 2026-09-30 (see provenance.json); the SQLite seed is
materialized deterministically at image build time (PYTHONHASHSEED=0).
"""
import json
import os
import re
import unicodedata
from datetime import date

from flask import (Flask, Response, abort, jsonify, redirect,
                   render_template, request, session, url_for)
from flask_bcrypt import Bcrypt
from flask_login import (LoginManager, UserMixin, current_user,
                         login_required, login_user, logout_user)
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect
from markupsafe import Markup
from sqlalchemy import event, func, or_
from sqlalchemy.engine import Engine
import sqlite3
from urllib.parse import parse_qs, urlparse

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__, instance_path=os.path.join(BASE_DIR, 'instance'))
app.config["SECRET_KEY"] = os.environ.get("DBLP_SECRET_KEY") or "webharbor-dblp-dev-key"
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'DBLP_DB_URI', f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'dblp.db')}")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['WTF_CSRF_TIME_LIMIT'] = None

os.makedirs(os.path.join(BASE_DIR, 'instance'), exist_ok=True)


@event.listens_for(Engine, 'connect')
def _sqlite_regexp(dbapi_connection, connection_record):
    """Register a REGEXP implementation for the exact-word ($-suffix)
    operator. SQLAlchemy's sqlite dialect ships its own case-sensitive
    regexp on modern versions (which overrides this one); the authoritative
    case handling lives in _term_sql, which lowers the column it matches
    against, so the operator is case-insensitive under either
    implementation (dblp search is case-insensitive across the board).
    This listener keeps the operator working on SQLAlchemy versions whose
    sqlite dialect ships no regexp at all."""
    if isinstance(dbapi_connection, sqlite3.Connection):
        dbapi_connection.create_function(
            'regexp', 2,
            lambda p, s: 1 if re.search(p, s or '', re.IGNORECASE) else 0)

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'authn_login'
login_manager.login_message = 'Please log in to continue.'
csrf = CSRFProtect(app)

# The mirror is a frozen snapshot of the upstream site taken 2026-09-30.
MIRROR_DATE = date(2026, 9, 30)
MIRROR_TS = "2026-09-30"
SITE_NAME = "dblp"
UPSTREAM = "https://dblp.org/"
# bcrypt hash of 'TestPass123!' — frozen so the seed DB is byte-reproducible.
BENCHMARK_PASSWORD_HASH = (
    '$2b$12$qSds4Mr9Wo7VwPWLhompEer88SuxxXFDp31P9etY6v7nfRctNO7B.')
SOURCE = os.path.join(BASE_DIR, 'source_data')
PER_PAGE = 30          # dblp serves 30 hits per search page

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
}


def _load(name):
    with open(os.path.join(SOURCE, name), encoding='utf-8') as f:
        return json.load(f)


# ------------------------------------------------------------ asset lookup --

_INVENTORY = None


def _inventory():
    global _INVENTORY
    if _INVENTORY is None:
        _INVENTORY = {}
        path = os.path.join(BASE_DIR, 'asset_inventory.json')
        if os.path.exists(path):
            with open(path, encoding='utf-8') as f:
                for row in json.load(f).get('assets', []):
                    fname = os.path.basename(row['path'])
                    _INVENTORY[fname.rsplit('.', 1)[0]] = row['path']
    return _INVENTORY


def img(name):
    """URL for a managed upstream asset by logical name (None if absent)."""
    inv = _inventory()
    rel = inv.get(name) or inv.get(name.rsplit('.', 1)[0])
    if not rel:
        return None
    return '/' + rel


# Upstream dblp.org renders each conference edition's table-of-contents page
# with a short display headline (e.g. "ACM SIGMOD Conference 2022:
# Philadelphia, PA, USA") rather than the full proceedings title. The
# captured headlines are tracked in source_data/edition_display.json
# (fetched verbatim from the corresponding upstream toc pages; see
# provenance.json) and loaded once at startup.
_TOC_HEADLINES = None


def _toc_headlines():
    global _TOC_HEADLINES
    if _TOC_HEADLINES is None:
        try:
            _TOC_HEADLINES = _load('edition_display.json').get(
                'toc_headline', {})
        except (OSError, ValueError):
            _TOC_HEADLINES = {}
    return _TOC_HEADLINES


# The venue-page year headers dblp.org shows for each conference edition
# (e.g. "SIGMOD Conference 2022: Philadelphia, PA, USA") are tracked in
# source_data/venues.json next to every edition; load them once for the
# venue page edition list.
_EDITION_SHORT = None


def _edition_short():
    global _EDITION_SHORT
    if _EDITION_SHORT is None:
        _EDITION_SHORT = {}
        try:
            for v in _load('venues.json'):
                for ed in v.get('editions', []):
                    _EDITION_SHORT[(v['stream'], ed.get('toc'))] = ed.get('title')
        except (OSError, ValueError, KeyError):
            pass
    return _EDITION_SHORT


def search_action_url():
    """Target of the header search form on the current page.

    Upstream dblp.org kind search pages (publication / author / venue)
    submit the search box back to their own kind; every other page submits
    to the combined search.
    """
    target = {'search_publ': 'search_publ',
              'search_author': 'search_author',
              'search_venue': 'search_venue'}.get(request.endpoint,
                                                  'search_combined')
    return url_for(target)


app.jinja_env.globals['img'] = img
app.jinja_env.globals['search_action_url'] = search_action_url


# ------------------------------------------------------------------- models --

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(160), unique=True, nullable=False)
    display_name = db.Column(db.String(120), nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    is_benchmark = db.Column(db.Boolean, default=False)
    affiliation = db.Column(db.String(200))
    research_interests = db.Column(db.String(300))
    created_at = db.Column(db.String(10), nullable=False, default='2026-09-01')


class Venue(db.Model):
    __tablename__ = 'venues'
    id = db.Column(db.Integer, primary_key=True)
    stream = db.Column(db.String(80), unique=True, nullable=False)  # conf/sigmod
    vtype = db.Column(db.String(20), nullable=False)   # conference | journal
    name = db.Column(db.String(220), nullable=False)
    abbr = db.Column(db.String(40))
    note = db.Column(db.String(300))
    info = db.Column(db.Text)          # JSON list of {label, text}
    external_home = db.Column(db.String(300))

    def info_list(self):
        return json.loads(self.info or '[]')

    def edition_count(self):
        return self.editions.count()

    def record_count(self):
        return Publication.query.filter_by(stream=self.stream).count()


class Edition(db.Model):
    __tablename__ = 'editions'
    id = db.Column(db.Integer, primary_key=True)
    venue_id = db.Column(db.Integer, db.ForeignKey('venues.id'), nullable=False)
    venue = db.relationship('Venue', backref=db.backref('editions', lazy='dynamic'))
    key = db.Column(db.String(120), unique=True, nullable=False)  # conf/sigmod/2022
    toc = db.Column(db.String(120), nullable=False)               # sigmod2022
    year = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(300), nullable=False)
    volume_label = db.Column(db.String(120))
    editors = db.Column(db.Text)       # JSON list of {pid, name}
    publisher = db.Column(db.String(120))
    n_records = db.Column(db.Integer, nullable=False, default=0)

    def editors_list(self):
        return json.loads(self.editors or '[]')

    def display_title(self):
        """The headline dblp.org shows for this edition's toc page.

        Journal volumes keep the full volume title (upstream does too);
        conference editions use the captured upstream short display name,
        falling back to the stored proceedings title when no capture
        exists.
        """
        if self.venue and self.venue.vtype == 'conference':
            short = _toc_headlines().get(self.toc)
            if short:
                return short
        return self.title

    def list_title(self):
        """The label shown in the venue page's edition/volume list.

        Journals show their volume label; conferences show the upstream
        year-header form ("SIGMOD Conference 2022: Philadelphia, PA, USA"),
        falling back to the stored proceedings title.
        """
        if self.volume_label:
            return self.volume_label
        if self.venue and self.venue.vtype == 'conference':
            short = _edition_short().get((self.venue.stream, self.toc))
            if short:
                return short
        return self.title


class Publication(db.Model):
    __tablename__ = 'publications'
    id = db.Column(db.Integer, primary_key=True)
    rec_key = db.Column(db.String(200), unique=True, nullable=False)
    rtype = db.Column(db.String(30), nullable=False)
    type_label = db.Column(db.String(60), nullable=False)
    title = db.Column(db.String(500), nullable=False)
    year = db.Column(db.Integer, nullable=False, index=True)
    pages = db.Column(db.String(40))
    volume = db.Column(db.String(40))
    number = db.Column(db.String(40))
    booktitle = db.Column(db.String(200))
    journal = db.Column(db.String(200))
    doi = db.Column(db.String(120))
    ee = db.Column(db.Text)            # JSON list
    mdate = db.Column(db.String(12))
    edition_id = db.Column(db.Integer, db.ForeignKey('editions.id'))
    edition = db.relationship('Edition')
    stream = db.Column(db.String(80), index=True)
    # folded search haystack: title + author names + venue name
    search_text = db.Column(db.String(1200), nullable=False, default='')

    def ee_list(self):
        return json.loads(self.ee or '[]')

    def authors(self):
        return (PubAuthor.query.filter_by(publication_id=self.id)
                .order_by(PubAuthor.position).all())

    def author_names(self):
        return [pa.name for pa in self.authors()]

    def venue(self):
        return Venue.query.filter_by(stream=self.stream).first()


class PubAuthor(db.Model):
    __tablename__ = 'pub_authors'
    id = db.Column(db.Integer, primary_key=True)
    publication_id = db.Column(db.Integer, db.ForeignKey('publications.id'),
                               nullable=False, index=True)
    author_pid = db.Column(db.String(80), nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False)
    orcid = db.Column(db.String(40))
    position = db.Column(db.Integer, nullable=False, default=0)


class Author(db.Model):
    __tablename__ = 'authors'
    id = db.Column(db.Integer, primary_key=True)
    pid = db.Column(db.String(80), unique=True, nullable=False)
    name = db.Column(db.String(200), nullable=False)
    name_base = db.Column(db.String(200), nullable=False, index=True)
    n_upstream = db.Column(db.Integer)   # upstream dblp record count (context)
    urls = db.Column(db.Text)             # JSON list
    affiliations = db.Column(db.Text)     # JSON list of {label, text}
    awards = db.Column(db.Text)           # JSON list of {label, text}
    uname = db.Column(db.String(120))     # unicode name
    profile_fetched = db.Column(db.Boolean, nullable=False, default=False)

    def urls_list(self):
        return json.loads(self.urls or '[]')

    def affiliations_list(self):
        return json.loads(self.affiliations or '[]')

    def awards_list(self):
        return json.loads(self.awards or '[]')

    def homepage(self):
        for u in self.urls_list():
            if not any(k in u for k in ('scholar.google', 'orcid', 'wikipedia',
                                        'wikidata', 'viaf', 'd-nb', 'id.loc',
                                        'mathscinet', 'mathgenealogy',
                                        'openreview', 'dl.acm',
                                        'semanticscholar')):
                return u
        return None

    def pub_count(self):
        return PubAuthor.query.filter_by(author_pid=self.pid).count()

    def publications(self):
        return (Publication.query
                .join(PubAuthor, PubAuthor.publication_id == Publication.id)
                .filter(PubAuthor.author_pid == self.pid)
                .order_by(Publication.year.desc(), Publication.id).all())

    def coauthors(self):
        """[(Author, joint_count)] sorted by count desc, then name."""
        pubs = self.publications()
        counts = {}
        for p in pubs:
            for pa in p.authors():
                if pa.author_pid != self.pid:
                    counts.setdefault(pa.author_pid, [pa.name, 0])[1] += 1
        out = []
        for pid, (name, n) in counts.items():
            a = Author.query.filter_by(pid=pid).first()
            if a:
                out.append((a, n))
        out.sort(key=lambda t: (-t[1], t[0].name_base))
        return out

    def per_year_counts(self):
        pubs = self.publications()
        years = {}
        for p in pubs:
            years[p.year] = years.get(p.year, 0) + 1
        return sorted(years.items())

    def homonyms(self):
        return (Author.query
                .filter(Author.name_base == self.name_base,
                        Author.pid != self.pid)
                .order_by(Author.pid).all())


class WatchAuthor(db.Model):
    __tablename__ = 'watch_authors'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    author_pid = db.Column(db.String(80), nullable=False)
    added_at = db.Column(db.String(10), nullable=False, default='2026-09-01')


class WatchVenue(db.Model):
    __tablename__ = 'watch_venues'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    venue_id = db.Column(db.Integer, db.ForeignKey('venues.id'), nullable=False)
    added_at = db.Column(db.String(10), nullable=False, default='2026-09-01')
    venue = db.relationship('Venue')


class SavedSearch(db.Model):
    __tablename__ = 'saved_searches'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    query_text = db.Column('query', db.String(400), nullable=False)
    search_type = db.Column(db.String(20), nullable=False, default='publ')
    label = db.Column(db.String(200))
    created_at = db.Column(db.String(10), nullable=False, default='2026-09-01')


class SavedPaper(db.Model):
    __tablename__ = 'saved_papers'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    publication_id = db.Column(db.Integer, db.ForeignKey('publications.id'),
                               nullable=False)
    collection = db.Column(db.String(120), nullable=False, default='My Library')
    note = db.Column(db.String(300))
    saved_at = db.Column(db.String(10), nullable=False, default='2026-09-01')
    publication = db.relationship('Publication')


class SearchHistory(db.Model):
    __tablename__ = 'search_history'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    query_text = db.Column('query', db.String(400), nullable=False)
    search_type = db.Column(db.String(20), nullable=False, default='publ')
    hits = db.Column(db.Integer, nullable=False, default=0)
    ran_at = db.Column(db.String(16), nullable=False, default='2026-09-01 00:00')


# ----------------------------------------------------------- search engine --

def _fold(s):
    s = unicodedata.normalize('NFKD', s or '')
    return ''.join(c for c in s if not unicodedata.combining(c)).lower()


def parse_query(q):
    """Parse a dblp query into AND groups of OR alternatives.

    Upstream semantics (documented on the dblp search pages):
      - case-insensitive prefix search (sig matches "SIGIR" and "signal")
      - trailing $ = exact word match (graph$ matches "graph" only)
      - space separates AND terms
      - | separates OR alternatives inside a term
    Returns (terms, filters) where terms is a list of
    ([alternatives], exact) and filters maps venue:/year:/streamid: keys.
    """
    terms = []
    filters = {}
    for tok in (q or '').split():
        word, exact = tok, False
        if word.endswith('$') and len(word) > 1:
            word, exact = word[:-1], True
        if not exact and ':' in word and word.split(':', 1)[0] in (
                'venue', 'year', 'streamid'):
            k, _, v = word.partition(':')
            filters[k] = v.rstrip(':')
            continue
        alts = [a for a in word.split('|') if a]
        if alts:
            terms.append((alts, exact))
    return terms, filters


def _term_sql(terms, column, lower_column=False):
    """Build AND-ed LIKE conditions matching folded text word prefixes.

    ``lower_column`` lowers the column for the exact-word REGEXP branch —
    needed for columns stored in original case (author names): the REGEXP
    implementation may be case-sensitive (SQLAlchemy's sqlite dialect ships
    its own), while dblp search is case-insensitive across the board.
    """
    conds = []
    for alts, exact in terms:
        alt_conds = []
        for a in alts:
            fa = a.replace('%', r'\%').replace('_', r'\_')
            if exact:
                target = func.lower(column) if lower_column else column
                alt_conds.append(target.op('REGEXP')(
                    r'(^| )' + re.escape(_fold(a)) + r'( |$)'))
            else:
                alt_conds.append(column.like(_fold(fa) + '%'))
                alt_conds.append(column.like('% ' + _fold(fa) + '%'))
        conds.append(or_(*alt_conds))
    return conds


def search_publications(q):
    terms, filters = parse_query(q)
    rows = Publication.query
    if filters.get('year', '').isdigit():
        rows = rows.filter_by(year=int(filters['year']))
    stream = filters.get('streamid') or filters.get('venue')
    if stream:
        stream = stream.rstrip(':')
        v = Venue.query.filter(or_(Venue.stream == stream,
                                   Venue.stream == 'conf/' + stream,
                                   Venue.stream == 'journals/' + stream,
                                   Venue.abbr == stream)).first()
        if v:
            rows = rows.filter_by(stream=v.stream)
        else:
            rows = rows.filter(Publication.stream == '__none__')
    for cond in _term_sql(terms, Publication.search_text):
        rows = rows.filter(cond)
    return rows.order_by(Publication.year.desc(), Publication.id)


def search_authors(q):
    terms, _ = parse_query(q)
    rows = Author.query
    for cond in _term_sql(terms, Author.name_base, lower_column=True):
        rows = rows.filter(cond)
    return rows.order_by(Author.name_base)


def search_venues(q):
    terms, _ = parse_query(q)
    rows = Venue.query
    for alts, exact in terms:
        alt_conds = []
        for a in alts:
            fa = _fold(a).replace('%', r'\%').replace('_', r'\_')
            if exact:
                alt_conds.append(or_(
                    func.lower(Venue.name).op('REGEXP')(
                        r'(^| )' + re.escape(_fold(a)) + r'( |$)'),
                    Venue.abbr == a))
            else:
                alt_conds.append(func.lower(Venue.name).like(fa + '%'))
                alt_conds.append(func.lower(Venue.name).like('% ' + fa + '%'))
                alt_conds.append(func.lower(Venue.abbr).like(fa + '%'))
        rows = rows.filter(or_(*alt_conds))
    return rows.order_by(Venue.name)


# ---------------------------------------------------------------- bibtex --

def bibtex_for(pub):
    """Generate the upstream-format BibTeX entry for a record.

    The format mirrors the .bib responses dblp serves (field order,
    DBLP: key naming, timestamp line) — see the captured rec/<key>.bib
    reference in scraped_data/captures/.
    """
    p = pub
    auth = ' and '.join(pa.name for pa in p.authors())
    if p.rtype == 'article':
        venue = p.journal or (p.edition and p.edition.title) or ''
        head = '@article{DBLP:' + p.rec_key
        lines = [
            '  author       = {' + auth + '}',
            '  title        = {' + p.title + '}',
            '  journal      = {' + venue + '}',
        ]
        if p.volume:
            lines.append('  volume       = {' + p.volume + '}')
        if p.number:
            lines.append('  number       = {' + p.number + '}')
        if p.pages:
            lines.append('  pages        = {' + p.pages + '}')
        lines.append('  year         = ' + '{' + str(p.year) + '}')
    else:
        venue = p.booktitle or (p.edition and p.edition.title) or ''
        head = '@inproceedings{DBLP:' + p.rec_key
        lines = [
            '  author       = {' + auth + '}',
            '  title        = {' + p.title + '}',
            '  booktitle    = {' + venue + '}',
        ]
        if p.pages:
            lines.append('  pages        = {' + p.pages + '}')
        lines.append('  year         = ' + '{' + str(p.year) + '}')
    if p.ee_list():
        lines.append('  url          = {' + p.ee_list()[0] + '}')
    if p.doi:
        lines.append('  doi          = {' + p.doi + '}')
    if p.mdate:
        lines.append('  timestamp    = {' + _mdate_to_bib_ts(p.mdate) + '}')
    lines.append('  biburl       = {https://dblp.org/rec/' + p.rec_key + '.bib}')
    lines.append('  bibsource    = {dblp computer science bibliography, '
                 'https://dblp.org}')
    return head + ',\n' + ',\n'.join(lines) + '\n}\n'


MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep',
          'Oct', 'Nov', 'Dec']


def _mdate_to_bib_ts(mdate):
    y, m, d = mdate.split('-')
    return f"{MONTHS[int(m) - 1]}, {int(d)} {y} 00:00:00 +0000"


# ------------------------------------------------------------- page helpers --

def _page_args():
    try:
        h = min(max(int(request.args.get('h', PER_PAGE)), 1), 1000)
    except ValueError:
        h = PER_PAGE
    try:
        f = max(int(request.args.get('f', 0)), 0)
    except ValueError:
        f = 0
    return h, f


def _search_from_combined(q):
    """True when this kind page was reached from the combined results page
    for the same query — the "all N matches" chain of one search action."""
    ref = request.referrer
    if not ref:
        return False
    try:
        parts = urlparse(ref)
    except ValueError:
        return False
    if parts.path != '/search' or not parts.query:
        return False
    ref_q = (parse_qs(parts.query).get('q', [''])[0] or '').strip()
    return ref_q == q


def _record_search(q, kind):
    """Record a search in the logged-in user's history.

    One search action yields one history entry: a kind page reached from
    the combined results page for the same query (the section's
    "all N matches" link) is the same search, not a new one, so it is not
    recorded twice. Any other search action always records — even when its
    text coincides with an earlier history row (e.g. a seed row): a fresh
    action is a new search, not a duplicate.
    """
    if not current_user.is_authenticated or not q:
        return
    if _search_from_combined(q):
        return
    rows = {'publ': search_publications, 'author': search_authors,
            'venue': search_venues}[kind]
    try:
        hits = rows(q).count()
    except Exception:
        hits = 0
    db.session.add(SearchHistory(user_id=current_user.id, query_text=q,
                                 search_type=kind, hits=hits,
                                 ran_at=MIRROR_TS + ' 00:00'))
    db.session.commit()


# ------------------------------------------------------------------ routes --


def local_redirect(target, fallback):
    """Keep form continuations on this mirror, including encoded URL variants."""
    from urllib.parse import unquote
    value = target or ''
    decoded = unquote(value)
    if (not decoded.startswith('/') or decoded.startswith('//')
            or '\\' in decoded
            or any(ord(c) < 32 for c in decoded)):
        value = fallback
    return redirect(value)

@app.route('/_health')
def health():
    return jsonify(ok=True,
                   publications=Publication.query.count(),
                   authors=Author.query.count(),
                   venues=Venue.query.count(),
                   editions=Edition.query.count(),
                   users=User.query.count())


@app.route('/')
def home():
    news = _load('news.json')
    stats = _load('stats.json')
    return render_template('home.html', news=news, stats=stats,
                           mirror_date=MIRROR_TS)


@app.route('/search')
def search_combined():
    q = request.args.get('q', '').strip()
    publ = author = venue = None
    if q:
        publ = search_publications(q)
        author = search_authors(q)
        venue = search_venues(q)
        _record_search(q, 'publ')
    return render_template('search.html', q=q,
                           publ_rows=publ, author_rows=author,
                           venue_rows=venue)


@app.route('/search/publ')
def search_publ():
    q = request.args.get('q', '').strip()
    h, f = _page_args()
    rows = search_publications(q) if q else Publication.query.filter(
        Publication.id < 0)
    try:
        year = int(request.args.get('year', ''))
    except ValueError:
        year = None
    if year:
        rows = rows.filter(Publication.year == year)
    rtype = request.args.get('type', '').strip()
    if rtype:
        rows = rows.filter(Publication.rtype == rtype)
    total = rows.count()
    page = rows.offset(f).limit(h).all()
    _record_search(q, 'publ')
    # Each facet respects the other active filter, so every advertised
    # count is attainable; retain all years, including the oldest.
    base = search_publications(q) if q else Publication.query.filter(
        Publication.id < 0)
    years = {}
    types = {}
    for r in base.with_entities(Publication.year, Publication.rtype):
        if not rtype or r.rtype == rtype:
            years[r.year] = years.get(r.year, 0) + 1
        if not year or r.year == year:
            types[r.rtype] = types.get(r.rtype, 0) + 1
    refine_years = sorted(years.items(), reverse=True)
    refine_types = sorted(types.items(), key=lambda t: -t[1])
    return render_template('search_publ.html', q=q, rows=page,
                           total=total, h=h, f=f,
                           refine_years=refine_years,
                           refine_types=refine_types,
                           sel_year=year, sel_type=rtype,
                           type_labels=TYPE_LABELS)


@app.route('/search/author')
def search_author():
    q = request.args.get('q', '').strip()
    h, f = _page_args()
    rows = search_authors(q) if q else Author.query.filter(Author.id < 0)
    total = rows.count()
    page = rows.offset(f).limit(h).all()
    _record_search(q, 'author')
    return render_template('search_author.html', q=q, rows=page,
                           total=total, h=h, f=f)


@app.route('/search/venue')
def search_venue():
    q = request.args.get('q', '').strip()
    rows = search_venues(q) if q else Venue.query.filter(Venue.id < 0)
    total = rows.count()
    _record_search(q, 'venue')
    return render_template('search_venue.html', q=q, rows=rows.all(),
                           total=total)


# ------------------------------------------------------------- author pages --

@app.route('/pid/<path:pid>')
def author_page(pid):
    if pid.endswith('.html'):
        pid = pid[:-5]
    a = Author.query.filter_by(pid=pid).first()
    if not a:
        abort(404)
    pubs = a.publications()
    by_year = {}
    for p in pubs:
        by_year.setdefault(p.year, []).append(p)
    years = sorted(by_year, reverse=True)
    decades = []
    for y in years:
        dec = f"{y // 10 * 10} – {y // 10 * 10 + 9}" \
            if y // 10 * 10 + 9 < 2026 else f"{y // 10 * 10} – today"
        if not decades or decades[-1][0] != dec:
            decades.append((dec, []))
        decades[-1][1].append((y, by_year[y]))
    coauthors = a.coauthors()
    per_year = a.per_year_counts()
    return render_template('author.html', a=a, decades=decades,
                           n_pubs=len(pubs), coauthors=coauthors,
                           per_year=per_year)


# -------------------------------------------------------------- venue pages --

@app.route('/db/conf/')
@app.route('/db/journals/')
def browse_venues():
    vtype = 'conference' if request.path == '/db/conf/' else 'journal'
    venues = Venue.query.filter_by(vtype=vtype).order_by(Venue.name).all()
    by_letter = {}
    for v in venues:
        letter = (v.name[0].upper() if v.name else '#')
        by_letter.setdefault(letter, []).append(v)
    return render_template('browse_venues.html', vtype=vtype,
                           groups=sorted(by_letter.items()))


@app.route('/db/<any(conf, journals):kind>/<venue>/index.html')
@app.route('/db/<any(conf, journals):kind>/<venue>/')
def venue_page(kind, venue):
    v = Venue.query.filter_by(stream=f'{kind}/{venue}').first()
    if not v:
        abort(404)
    editions = (Edition.query.filter_by(venue_id=v.id)
                .order_by(Edition.year.desc(), Edition.key).all())
    pub_rows = Publication.query.filter_by(stream=v.stream)
    years = {}
    for row in pub_rows.with_entities(Publication.year):
        years[row.year] = years.get(row.year, 0) + 1
    top_authors = (db.session.query(Author, func.count(PubAuthor.id).label('n'))
                   .join(PubAuthor, PubAuthor.author_pid == Author.pid)
                   .join(Publication, Publication.id == PubAuthor.publication_id)
                   .filter(Publication.stream == v.stream)
                   .group_by(Author.id)
                   .order_by(func.count(PubAuthor.id).desc(), Author.name_base)
                   .limit(10).all())
    return render_template('venue.html', v=v, editions=editions,
                           years=sorted(years.items(), reverse=True),
                           top_authors=top_authors,
                           n_records=pub_rows.count())


@app.route('/db/<any(conf, journals):kind>/<venue>/<toc>.html')
def edition_page(kind, venue, toc):
    if toc == 'index':
        return venue_page(kind, venue)
    v = Venue.query.filter_by(stream=f'{kind}/{venue}').first()
    if not v:
        abort(404)
    ed = Edition.query.filter_by(venue_id=v.id, toc=toc).first()
    if not ed:
        abort(404)
    pubs = (Publication.query.filter_by(edition_id=ed.id)
            .order_by(Publication.id).all())
    # Editor names link to their person page only when that person exists
    # in the mirrored author corpus (editors without their own publication
    # records in the corpus would otherwise render a dead /pid/ link).
    ed_pids = [e['pid'] for e in ed.editors_list() if e.get('pid')]
    known_editor_pids = set()
    if ed_pids:
        rows = (Author.query.with_entities(Author.pid)
                .filter(Author.pid.in_(ed_pids)).all())
        known_editor_pids = {row.pid for row in rows}
    return render_template('edition.html', v=v, ed=ed, pubs=pubs,
                           known_editor_pids=known_editor_pids)


# ------------------------------------------------------------- record pages --

@app.route('/rec/<path:key>')
def record_page(key):
    if key.endswith('.bib'):
        return record_bib(key[:-4])
    base = key[:-5] if key.endswith('.html') else key
    p = Publication.query.filter_by(rec_key=base).first()
    if not p:
        abort(404)
    bib = bibtex_for(p)
    return render_template('record.html', p=p, bib=bib)


@app.route('/rec/<path:key>.bib')
def record_bib(key):
    p = Publication.query.filter_by(rec_key=key).first()
    if not p:
        abort(404)
    return Response(bibtex_for(p), mimetype='text/plain',
                    headers={'Content-Disposition':
                             f'attachment; filename={key.replace("/", "_")}.bib'})


# ------------------------------------------------------------- account area --

@app.route('/authn/login', methods=['GET', 'POST'])
def authn_login():
    if request.method == 'POST':
        u = User.query.filter_by(email=request.form.get('email', '').strip()
                                 .lower()).first()
        if u and bcrypt.check_password_hash(
                u.password_hash, request.form.get('password', '')):
            login_user(u)
            dest = request.args.get('next') or url_for('account')
            return local_redirect(dest, url_for('account'))
        return render_template('authn_login.html', error='Invalid credentials.')
    return render_template('authn_login.html', error=None)


@app.route('/authn/register', methods=['GET', 'POST'])
def authn_register():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        name = request.form.get('display_name', '').strip()
        password = request.form.get('password', '')
        if not email or not name or len(password) < 8:
            return render_template(
                'authn_register.html',
                error='Please fill all fields; the password needs at least '
                      '8 characters.')
        if User.query.filter_by(email=email).first():
            return render_template('authn_register.html',
                                   error='That email is already registered.')
        u = User(email=email, display_name=name,
                 password_hash=bcrypt.generate_password_hash(password)
                 .decode(), is_benchmark=False,
                 created_at=MIRROR_TS)
        db.session.add(u)
        db.session.commit()
        login_user(u)
        return redirect(url_for('account'))
    return render_template('authn_register.html', error=None)


@app.route('/authn/logout', methods=['POST'])
@login_required
def authn_logout():
    logout_user()
    return redirect(url_for('home'))


@app.route('/account')
@login_required
def account():
    saved = SavedPaper.query.filter_by(user_id=current_user.id).count()
    searches = SavedSearch.query.filter_by(user_id=current_user.id).count()
    watched_authors = WatchAuthor.query.filter_by(
        user_id=current_user.id).count()
    watched_venues = WatchVenue.query.filter_by(
        user_id=current_user.id).count()
    history = (SearchHistory.query.filter_by(user_id=current_user.id)
               .order_by(SearchHistory.id.desc()).limit(5).all())
    return render_template('account_dashboard.html',
                           saved=saved, searches=searches,
                           watched_authors=watched_authors,
                           watched_venues=watched_venues,
                           history=history)


@app.route('/account/watchlist')
@login_required
def watchlist():
    authors = (WatchAuthor.query.filter_by(user_id=current_user.id)
               .order_by(WatchAuthor.id).all())
    venues = (WatchVenue.query.filter_by(user_id=current_user.id)
              .order_by(WatchVenue.id).all())
    out = []
    for w in authors:
        a = Author.query.filter_by(pid=w.author_pid).first()
        if a:
            out.append({'w': w, 'a': a, 'n': a.pub_count()})
    return render_template('watchlist.html', authors=out, venues=venues)


@app.route('/account/watchlist/author/add', methods=['POST'])
@login_required
def watchlist_add_author():
    pid = request.form.get('pid', '')
    a = Author.query.filter_by(pid=pid).first()
    if a and not WatchAuthor.query.filter_by(
            user_id=current_user.id, author_pid=pid).first():
        db.session.add(WatchAuthor(user_id=current_user.id, author_pid=pid,
                                   added_at=MIRROR_TS))
        db.session.commit()
    return local_redirect(request.form.get('next'), url_for('watchlist'))


@app.route('/account/watchlist/author/remove', methods=['POST'])
@login_required
def watchlist_remove_author():
    w = WatchAuthor.query.filter_by(
        user_id=current_user.id,
        author_pid=request.form.get('pid', '')).first()
    if w:
        db.session.delete(w)
        db.session.commit()
    return redirect(url_for('watchlist'))


@app.route('/account/watchlist/venue/add', methods=['POST'])
@login_required
def watchlist_add_venue():
    v = Venue.query.filter_by(stream=request.form.get('stream', '')).first()
    if v and not WatchVenue.query.filter_by(
            user_id=current_user.id, venue_id=v.id).first():
        db.session.add(WatchVenue(user_id=current_user.id, venue_id=v.id,
                                  added_at=MIRROR_TS))
        db.session.commit()
    return local_redirect(request.form.get('next'), url_for('watchlist'))


@app.route('/account/watchlist/venue/remove', methods=['POST'])
@login_required
def watchlist_remove_venue():
    w = WatchVenue.query.filter_by(
        user_id=current_user.id,
        venue_id=request.form.get('venue_id', -1, type=int)).first()
    if w:
        db.session.delete(w)
        db.session.commit()
    return redirect(url_for('watchlist'))


@app.route('/account/saved-searches')
@login_required
def saved_searches():
    rows = (SavedSearch.query.filter_by(user_id=current_user.id)
            .order_by(SavedSearch.id).all())
    return render_template('saved_searches.html', rows=rows)


@app.route('/account/saved-searches/add', methods=['POST'])
@login_required
def saved_searches_add():
    q = request.form.get('query', '').strip()
    kind = request.form.get('search_type', 'publ')
    label = request.form.get('label', '').strip() or None
    if q and kind in ('publ', 'author', 'venue'):
        db.session.add(SavedSearch(user_id=current_user.id, query_text=q,
                                   search_type=kind, label=label,
                                   created_at=MIRROR_TS))
        db.session.commit()
    return local_redirect(request.form.get('next'), url_for('saved_searches'))


@app.route('/account/saved-searches/<int:sid>/delete', methods=['POST'])
@login_required
def saved_searches_delete(sid):
    s = SavedSearch.query.filter_by(id=sid, user_id=current_user.id).first()
    if s:
        db.session.delete(s)
        db.session.commit()
    return redirect(url_for('saved_searches'))


@app.route('/account/papers')
@login_required
def saved_papers():
    rows = (SavedPaper.query.filter_by(user_id=current_user.id)
            .order_by(SavedPaper.id).all())
    collections = {}
    for r in rows:
        collections.setdefault(r.collection, []).append(r)
    return render_template('saved_papers.html',
                           groups=sorted(collections.items()))


@app.route('/account/papers/add', methods=['POST'])
@login_required
def saved_papers_add():
    p = Publication.query.filter_by(
        rec_key=request.form.get('key', '')).first()
    collection = request.form.get('collection', '').strip() or 'My Library'
    note = request.form.get('note', '').strip() or None
    if p and not SavedPaper.query.filter_by(
            user_id=current_user.id, publication_id=p.id,
            collection=collection).first():
        db.session.add(SavedPaper(user_id=current_user.id,
                                  publication_id=p.id,
                                  collection=collection, note=note,
                                  saved_at=MIRROR_TS))
        db.session.commit()
    return local_redirect(request.form.get('next'), url_for('saved_papers'))


@app.route('/account/papers/<int:sid>/remove', methods=['POST'])
@login_required
def saved_papers_remove(sid):
    s = SavedPaper.query.filter_by(id=sid, user_id=current_user.id).first()
    if s:
        db.session.delete(s)
        db.session.commit()
    return local_redirect(request.form.get('next'), url_for('saved_papers'))


@app.route('/account/papers/export.bib')
@login_required
def saved_papers_export():
    collection = request.args.get('collection') or None
    rows = (SavedPaper.query.filter_by(user_id=current_user.id))
    if collection:
        rows = rows.filter_by(collection=collection)
    out = []
    for r in rows.order_by(SavedPaper.id).all():
        out.append(bibtex_for(r.publication))
    body = '\n'.join(out)
    return Response(body, mimetype='text/plain',
                    headers={'Content-Disposition':
                             'attachment; filename=dblp-library.bib'})


@app.route('/account/history')
@login_required
def search_history():
    rows = (SearchHistory.query.filter_by(user_id=current_user.id)
            .order_by(SearchHistory.id.desc()).all())
    return render_template('history.html', rows=rows)


@app.route('/account/history/clear', methods=['POST'])
@login_required
def search_history_clear():
    SearchHistory.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()
    return redirect(url_for('search_history'))


@app.route('/account/profile', methods=['GET', 'POST'])
@login_required
def account_profile():
    if request.method == 'POST':
        current_user.display_name = request.form.get(
            'display_name', current_user.display_name).strip() or \
            current_user.display_name
        current_user.affiliation = request.form.get('affiliation', '').strip()
        current_user.research_interests = request.form.get(
            'research_interests', '').strip()
        db.session.commit()
        return redirect(url_for('account_profile'))
    return render_template('account_profile.html')


@login_manager.user_loader
def load_user(uid):
    return db.session.get(User, int(uid))


# ------------------------------------------------------------------- main --

def seed_database():
    if Publication.query.count() > 0:
        return
    from seed_lib import build_seed
    build_seed(db, bcrypt)


def seed_benchmark_users():
    if User.query.filter_by(email='alice.j@test.com').first():
        return
    from seed_lib import build_benchmark_users
    build_benchmark_users(db, bcrypt)


def main():
    with app.app_context():
        db.create_all()
        seed_database()
        seed_benchmark_users()


with app.app_context():
    db.create_all()
    seed_database()
    seed_benchmark_users()


if __name__ == '__main__':
    main()
