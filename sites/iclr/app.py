#!/usr/bin/env python3
"""iclr — a WebHarbor mirror of https://iclr.cc/

Flask + SQLite mirror of the International Conference on Learning
Representations site, frozen on the completed ICLR 2026 edition (Rio de
Janeiro, April 23-27 2026) plus the upcoming ICLR 2027 cycle:

  - the accepted-papers browser (5691 papers with search, topic /
    decision / session filters, sorting, pagination) and per-paper detail
    pages carrying the captured authors, institutions, topic, decision,
    session, room, poster position, OpenReview link and abstract;
  - the six-day Rio schedule (registration desks, remarks, invited talks,
    oral sessions with their talk slots, poster sessions, workshops,
    socials, town hall, test-of-time, expo talks, mentorship, breaks)
    with per-event detail pages;
  - the workshops hub (40 workshops with organizers, project pages,
    abstracts and internal talk schedules) and the invited-talks hub
    (speaker headshots and bios);
  - the tiered sponsor & exhibitor list, the organizing committee with
    portraits, the outstanding-paper and test-of-time awards, the blog
    announcements, the dates-and-deadlines groups for 2026/2027, the
    Riocentro venue facts, the About text and the FAQ;
  - a registration form mirroring the captured 2026 structure
    (affiliation types, purchasable items with the upstream exclusivity
    rule, $50 guest banquet tickets, dietary preference) with a
    confirmation page, and the HelpDesk contact form;
  - accounts (create profile / login), paper bookmarks, a personal
    schedule and a site-wide search, seeded for four benchmark users.

Content comes from the tracked source_data/*.json snapshots captured from
iclr.cc and blog.iclr.cc on 2026-09-30 (see provenance.json; the declared
upstream iclr.com is a parked domain — the real service is iclr.cc, the
same normalization precedent as the dblp mirror). The SQLite seed is
materialized deterministically at image build time (PYTHONHASHSEED=0).
"""
import json
import os
import secrets
from datetime import datetime

from flask import (Flask, abort, jsonify, redirect, render_template, request,
                   session, url_for)
from flask_bcrypt import Bcrypt
from flask_login import (LoginManager, UserMixin, current_user,
                         login_required, login_user, logout_user)
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect
from markupsafe import Markup

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__, instance_path=os.path.join(BASE_DIR, 'instance'))
app.config["SECRET_KEY"] = os.environ.get("ICLR_SECRET_KEY") or "webharbor-iclr-dev-key"
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'ICLR_DB_URI', f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'iclr.db')}")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['WTF_CSRF_TIME_LIMIT'] = None

os.makedirs(os.path.join(BASE_DIR, 'instance'), exist_ok=True)

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to continue.'
csrf = CSRFProtect(app)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


MIRROR_DATE = '2026-09-30'
MIRROR_TS = '2026-09-30'
SITE_NAME = 'iclr'
UPSTREAM = 'https://iclr.cc/'
CONFERENCE = 'ICLR 2026'
# bcrypt hash of 'TestPass123!' — frozen so the seed DB is byte-reproducible.
BENCHMARK_PASSWORD_HASH = (
    '$2b$12$qSds4Mr9Wo7VwPWLhompEer88SuxxXFDp31P9etY6v7nfRctNO7B.')
BANQUET_PRICE_USD = 50
SOURCE = os.path.join(BASE_DIR, 'source_data')


def _load(name):
    with open(os.path.join(SOURCE, name), encoding='utf-8') as f:
        return json.load(f)


# ------------------------------------------------------------- asset tables --

_INVENTORY = None


def _inventory():
    global _INVENTORY
    if _INVENTORY is None:
        _INVENTORY = {}
        path = os.path.join(BASE_DIR, 'asset_inventory.json')
        if os.path.exists(path):
            with open(path, encoding='utf-8') as f:
                for row in json.load(f).get('assets', []):
                    _INVENTORY[row['path'].split('/')[-1]] = row['path']
    return _INVENTORY


def asset_exists(path):
    return path in _inventory()


# ------------------------------------------------------------------- models --

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(128), unique=True, nullable=False)
    name = db.Column(db.String(128), nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    joined = db.Column(db.String(10))


class Paper(db.Model):
    __tablename__ = 'papers'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.Text, nullable=False)
    authors = db.Column(db.Text)          # JSON [{name, institution}]
    topic = db.Column(db.String(128))
    decision = db.Column(db.String(32))
    eventtype = db.Column(db.String(16))
    session = db.Column(db.String(128))
    room = db.Column(db.String(64))
    day = db.Column(db.String(10))
    session_start = db.Column(db.String(8))
    session_end = db.Column(db.String(8))
    talk_start = db.Column(db.String(8))   # oral talk slot (Rio local)
    talk_end = db.Column(db.String(8))
    poster_position = db.Column(db.String(16))
    openreview_url = db.Column(db.String(255))
    abstract = db.Column(db.Text)

    def author_list(self):
        try:
            return json.loads(self.authors or '[]')
        except json.JSONDecodeError:
            return []

    def author_names(self):
        return [a.get('name', '') for a in self.author_list()]

    def badge(self):
        if self.decision == 'Accept (Oral)':
            return 'Oral'
        return 'Poster'


class SessionEvent(db.Model):
    __tablename__ = 'session_events'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.Text, nullable=False)
    kind = db.Column(db.String(16), nullable=False)   # oral-session / poster-session
    date = db.Column(db.String(10), nullable=False)
    day_label = db.Column(db.String(12))
    start = db.Column(db.String(8))
    end = db.Column(db.String(8))
    room = db.Column(db.String(64))


class Event(db.Model):
    __tablename__ = 'events'
    id = db.Column(db.Integer, primary_key=True)
    kind = db.Column(db.String(24), nullable=False)
    title = db.Column(db.Text, nullable=False)
    date = db.Column(db.String(10), nullable=False)
    day_label = db.Column(db.String(12))
    start = db.Column(db.String(8))
    end = db.Column(db.String(8))
    speaker = db.Column(db.Text)
    people = db.Column(db.Text)            # JSON list
    abstract = db.Column(db.Text)
    website = db.Column(db.String(255))
    overflow_room = db.Column(db.String(64))
    headshot_url = db.Column(db.String(255))
    headshot_alt = db.Column(db.String(128))
    speaker_bio = db.Column(db.Text)
    schedule = db.Column(db.Text)          # JSON [{time, title, speaker}]

    def people_list(self):
        try:
            return json.loads(self.people or '[]')
        except json.JSONDecodeError:
            return []

    def schedule_list(self):
        try:
            return json.loads(self.schedule or '[]')
        except json.JSONDecodeError:
            return []

    def kind_label(self):
        return {
            'invited-talk': 'Invited Talk',
            'workshop': 'Workshop',
            'social': 'Social',
            'break': 'Break',
            'expo-talk-panel': 'Expo Talk / Panel',
            'mentorship': 'Mentorship',
            'registration-desk': 'Registration Desk',
            'remarks': 'Remarks',
            'reception': 'Reception',
            'test-of-time': 'Test of Time',
            'town-hall': 'Town Hall',
        }.get(self.kind, self.kind.replace('-', ' ').title())


class Sponsor(db.Model):
    __tablename__ = 'sponsors'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text, nullable=False)
    tier = db.Column(db.String(96), nullable=False)
    url = db.Column(db.String(255))


class Organizer(db.Model):
    __tablename__ = 'organizers'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text, nullable=False)
    role = db.Column(db.String(96), nullable=False)
    institution = db.Column(db.Text)
    photo = db.Column(db.String(255))
    bio = db.Column(db.Text)


class NewsPost(db.Model):
    __tablename__ = 'news_posts'
    slug = db.Column(db.String(64), primary_key=True)
    title = db.Column(db.Text, nullable=False)
    date = db.Column(db.String(10), nullable=False)
    author = db.Column(db.String(128))
    body = db.Column(db.Text)              # JSON list of paragraphs
    upstream_url = db.Column(db.String(255))

    def body_list(self):
        try:
            return json.loads(self.body or '[]')
        except json.JSONDecodeError:
            return []


class Award(db.Model):
    __tablename__ = 'awards'
    id = db.Column(db.Integer, primary_key=True)
    award_group = db.Column(db.String(64), nullable=False)
    kind = db.Column(db.String(32), nullable=False)
    title = db.Column(db.Text, nullable=False)
    authors = db.Column(db.Text)           # JSON list
    citation = db.Column(db.Text)
    source_url = db.Column(db.String(255))

    def author_list(self):
        try:
            return json.loads(self.authors or '[]')
        except json.JSONDecodeError:
            return []


class DateItem(db.Model):
    __tablename__ = 'date_items'
    id = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.String(4), nullable=False)
    group_name = db.Column(db.String(64), nullable=False)
    name = db.Column(db.Text, nullable=False)
    date_str = db.Column(db.String(64), nullable=False)


class Registration(db.Model):
    __tablename__ = 'registrations'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    name = db.Column(db.String(128), nullable=False)
    email = db.Column(db.String(128), nullable=False)
    affiliation = db.Column(db.String(32), nullable=False)
    items = db.Column(db.Text)             # JSON list of item names
    banquet_tickets = db.Column(db.Integer, nullable=False, default=0)
    dietary = db.Column(db.Text)
    total_usd = db.Column(db.Integer, nullable=False)
    reg_code = db.Column(db.String(16), nullable=False)
    created = db.Column(db.String(10), nullable=False)

    def item_list(self):
        try:
            return json.loads(self.items or '[]')
        except json.JSONDecodeError:
            return []


class Bookmark(db.Model):
    __tablename__ = 'bookmarks'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False,
                        index=True)
    paper_id = db.Column(db.Integer, db.ForeignKey('papers.id'), nullable=False)
    added_at = db.Column(db.String(10))


class ScheduleSave(db.Model):
    __tablename__ = 'schedule_saves'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False,
                        index=True)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'),
                         nullable=False)
    added_at = db.Column(db.String(10))


class ContactMessage(db.Model):
    __tablename__ = 'contact_messages'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    email = db.Column(db.String(128), nullable=False)
    topic = db.Column(db.String(128), nullable=False)
    subject = db.Column(db.Text, nullable=False)
    body = db.Column(db.Text, nullable=False)
    created = db.Column(db.String(10), nullable=False)


# ------------------------------------------------------------------ helpers --

def _img(filename):
    """Resolve a downloaded upstream image to its inventory path."""
    if not filename:
        return None
    path = _inventory().get(filename)
    return f"/{path}" if path else None


HELPDESK_TOPICS = [
    ('program-chairs@iclr.cc',
     'Program Chairs: Paper submissions, OpenReview, Titles, Authors, Supplemental'),
    ('workshop-chairs@iclr.cc', 'Workshops'),
    ('diversity-chairs@iclr.cc', 'Equity, Diversity, Inclusion'),
    ('ethics@iclr.cc', 'Code of Conduct, Ethics Violations'),
    ('press@iclr.cc', 'Press'),
    ('journal-track-chairs@iclr.cc', 'General Journal Track Chairs'),
    ('visa-support@iclr.cc', 'Visa Support'),
    ('technical-support@iclr.cc',
     'Technical, Website, Conference Management, Sponsorships, Registrations, Other'),
]

REG_ITEMS = [
    ('Conference Sessions and Workshops', True),
    ('Sunday Workshop 1 Day Pass', True),
    ('Monday Workshop 1 Day Pass', True),
    ('Virtual Only Pass', False),
]
REG_AFFILIATIONS = ['Full time student', 'Academic', 'Industrial']
REG_EXCLUSIVITY = ('"Conference Sessions and Workshops", "Sunday Workshop 1 Day Pass" '
                   'and "Monday Workshop 1 Day Pass" include Virtual Access. If you '
                   'choose Conference Sessions and Workshops, do not check any other '
                   'items.')

TOPIC_PARENTS = [
    ('Applications', 'Applications'),
    ('Data, Datasets, and Evaluation', 'Data, Datasets, and Evaluation'),
    ('Deep Learning Architectures', 'Deep Learning Architectures'),
    ('General Machine Learning', 'General Machine Learning'),
    ('Generative Models', 'Generative Models'),
    ('Infrastructure', 'Infrastructure'),
    ('Learning Theory', 'Learning Theory'),
    ('Neuroscience and Cognitive Science', 'Neuroscience and Cognitive Science'),
    ('Optimization', 'Optimization'),
    ('Probabilistic Methods and Inference', 'Probabilistic Methods and Inference'),
    ('Reinforcement Learning', 'Reinforcement Learning'),
    ('Representation Learning', 'Representation Learning'),
    ('Social Aspects', 'Social Aspects'),
    ('Speech and Audio', 'Speech and Audio'),
    ('Vision', 'Vision'),
    ('Natural Language Processing', 'Natural Language Processing'),
]


def topic_parent(topic):
    return topic.split('->')[0] if '->' in topic else topic


def fmt_time(t):
    """'09:00' -> '9:00 AM' (conference-local display format)."""
    if not t or ':' not in t:
        return t or ''
    try:
        hour, minute = int(t.split(':')[0]), t.split(':')[1]
    except ValueError:
        return t
    half = 'AM' if hour < 12 else 'PM'
    hour12 = hour % 12 or 12
    return f"{hour12}:{minute} {half}"


def fmt_date(iso):
    try:
        d = datetime.strptime(iso, '%Y-%m-%d')
        return d.strftime('%a, %b %-d, %Y')
    except ValueError:
        return iso


def day_word(iso):
    try:
        d = datetime.strptime(iso, '%Y-%m-%d')
        return d.strftime('%A')
    except ValueError:
        return ''


# -------------------------------------------------------------------- views --

def _conference_meta():
    conf = _load('conference.json')
    return {
        'name': conf['name'],
        'full_name': conf['full_name'],
        'city': conf['city'],
        'country': conf['country'],
        'dates': conf['dates'],
        'papers': conf['papers'],
        'oral_decisions': conf['oral_decisions'],
        'poster_decisions': conf['poster_decisions'],
        'workshops': conf['workshops'],
        'invited_talks': conf['invited_talks'],
        'socials': conf['socials'],
        'sponsors': conf['sponsors'],
        'sessions': conf['sessions'],
    }



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

@app.route('/')
def home():
    conf = _conference_meta()
    announcements = NewsPost.query.order_by(NewsPost.date.desc()).limit(4).all()
    dates27 = DateItem.query.filter_by(year='2027', group_name='Paper Submissions').all()
    sponsors = Sponsor.query.filter(
        Sponsor.tier.in_(['Double Diamond', 'Diamond'])).order_by(Sponsor.id).all()
    return render_template('home.html', conf=conf, announcements=announcements,
                           dates27=dates27, sponsors=sponsors, img=_img)


PAPER_PAGE_SIZE = 50


@app.route('/papers')
def papers():
    q = (request.args.get('q') or '').strip()
    topic = request.args.get('topic') or ''
    decision = request.args.get('decision') or ''
    session_name = request.args.get('session') or ''
    sort = request.args.get('sort') or 'title'
    page = max(1, int(request.args.get('page') or 1))

    query = Paper.query
    if q:
        like = f'%{q}%'
        query = query.filter(Paper.title.ilike(like))
    if topic:
        query = query.filter(Paper.topic == topic)
    if decision:
        query = query.filter(Paper.decision == decision)
    if session_name:
        query = query.filter(Paper.session == session_name)
    if sort == 'id':
        order = Paper.id
    elif sort == 'session':
        order = Paper.session
    else:
        order = Paper.title
    query = query.order_by(order, Paper.id)
    total = query.count()
    rows = (query.offset((page - 1) * PAPER_PAGE_SIZE)
            .limit(PAPER_PAGE_SIZE).all())
    sessions = sorted({s[0] for s in Paper.query.with_entities(Paper.session)
                       .distinct().all() if s[0]})
    all_topics = sorted({t[0] for t in Paper.query.with_entities(Paper.topic)
                         .distinct().all() if t[0]})
    grouped = []
    for parent in sorted({topic_parent(t) for t in all_topics}):
        grouped.append((parent, [t for t in all_topics
                                 if topic_parent(t) == parent]))
    bookmarked = set()
    if current_user.is_authenticated:
        bookmarked = {b.paper_id for b in
                      Bookmark.query.filter_by(user_id=current_user.id).all()}
    return render_template(
        'papers.html', rows=rows, total=total, q=q, topic=topic,
        decision=decision, session=session_name, sort=sort, page=page,
        pages=(total + PAPER_PAGE_SIZE - 1) // PAPER_PAGE_SIZE,
        sessions=sessions, topics_grouped=grouped, bookmarked=bookmarked,
        img=_img, fmt_time=fmt_time)


@app.route('/papers/<int:pid>')
def paper_detail(pid):
    paper = db.session.get(Paper, pid)
    if not paper:
        abort(404)
    session = SessionEvent.query.filter_by(title=paper.session).first()
    room = paper.room or (session.room if session else '')
    bookmarked = None
    if current_user.is_authenticated:
        bookmarked = Bookmark.query.filter_by(user_id=current_user.id,
                                             paper_id=pid).first()
    return render_template('paper_detail.html', p=paper, session=session,
                           room=room, bookmarked=bookmarked,
                           fmt_time=fmt_time, fmt_date=fmt_date, img=_img)


@app.route('/bookmarks/toggle', methods=['POST'])
@login_required
def bookmarks_toggle():
    pid = request.form.get('paper_id') or ''
    paper = db.session.get(Paper, int(pid)) if pid.isdigit() else None
    if paper is None:
        abort(400)
    row = Bookmark.query.filter_by(user_id=current_user.id,
                                   paper_id=paper.id).first()
    if row:
        db.session.delete(row)
        db.session.commit()
        return local_redirect(request.form.get('back'), url_for('mystuff'))
    db.session.add(Bookmark(user_id=current_user.id, paper_id=paper.id,
                            added_at=MIRROR_TS))
    db.session.commit()
    return local_redirect(request.form.get('back'), url_for('mystuff'))


@app.route('/schedule')
def schedule():
    from sqlalchemy import func
    session_days = [d[0] for d in (db.session.query(SessionEvent.date)
                                   .distinct().order_by(SessionEvent.date).all())]
    event_days = [d[0] for d in (db.session.query(Event.date)
                                 .distinct().order_by(Event.date).all())]
    labels = {}
    for row in Event.query.with_entities(Event.date, Event.day_label).distinct().all():
        labels[row[0]] = row[1]
    for row in SessionEvent.query.with_entities(SessionEvent.date, SessionEvent.day_label).distinct().all():
        labels.setdefault(row[0], row[1])
    days = [(d, labels.get(d) or fmt_date(d).split(',')[0].upper())
            for d in sorted(set(session_days) | set(event_days))]
    day_events = {}
    for date, label in days:
        events = Event.query.filter_by(date=date).order_by(Event.start, Event.id).all()
        sessions = (SessionEvent.query.filter_by(date=date)
                    .order_by(SessionEvent.start, SessionEvent.id).all())
        day_events[date] = {'label': label, 'events': events, 'sessions': sessions}
    kinds = request.args.get('kinds') or ''
    active = set(filter(None, kinds.split(',')))
    selected = request.args.get('date') or (days[0][0] if days else '')
    saved = set()
    if current_user.is_authenticated:
        saved = {s.event_id for s in
                 ScheduleSave.query.filter_by(user_id=current_user.id).all()}
    # oral sessions list their talks inline, like the upstream calendar
    session_talks = {}
    for date, label in days:
        for sess in SessionEvent.query.filter_by(date=date, kind='oral-session').all():
            talks = (Paper.query.filter_by(session=sess.title, eventtype='Oral')
                     .order_by(Paper.talk_start, Paper.id).all())
            session_talks[sess.title] = talks
    return render_template('schedule.html', day_events=day_events,
                           day_tabs=days, selected=selected, active=active,
                           saved=saved, session_talks=session_talks,
                           fmt_time=fmt_time, fmt_date=fmt_date, img=_img)


@app.route('/events/<int:eid>')
def event_detail(eid):
    event = db.session.get(Event, eid)
    if not event:
        abort(404)
    saved = None
    if current_user.is_authenticated:
        saved = ScheduleSave.query.filter_by(user_id=current_user.id,
                                             event_id=eid).first()
    return render_template('event_detail.html', e=event, saved=saved,
                           fmt_time=fmt_time, fmt_date=fmt_date, img=_img)


@app.route('/schedule/save', methods=['POST'])
@login_required
def schedule_save():
    eid = request.form.get('event_id') or ''
    event = db.session.get(Event, int(eid)) if eid.isdigit() else None
    if event is None:
        abort(400)
    row = ScheduleSave.query.filter_by(user_id=current_user.id,
                                       event_id=event.id).first()
    if row:
        db.session.delete(row)
        db.session.commit()
        return local_redirect(request.form.get('back'), url_for('mystuff'))
    db.session.add(ScheduleSave(user_id=current_user.id, event_id=event.id,
                                added_at=MIRROR_TS))
    db.session.commit()
    return local_redirect(request.form.get('back'), url_for('mystuff'))


@app.route('/workshops')
def workshops():
    rows = Event.query.filter_by(kind='workshop').order_by(
        Event.date, Event.start, Event.id).all()
    saved = set()
    if current_user.is_authenticated:
        saved = {s.event_id for s in
                 ScheduleSave.query.filter_by(user_id=current_user.id).all()}
    return render_template('workshops.html', rows=rows, saved=saved,
                           fmt_time=fmt_time, fmt_date=fmt_date, img=_img)


@app.route('/invited-talks')
def invited_talks():
    rows = Event.query.filter_by(kind='invited-talk').order_by(
        Event.date, Event.start, Event.id).all()
    return render_template('invited_talks.html', rows=rows,
                           fmt_time=fmt_time, fmt_date=fmt_date, img=_img)


@app.route('/sponsors')
def sponsors():
    tiers = []
    for tier in db.session.query(Sponsor.tier).distinct().order_by(Sponsor.id):
        rows = Sponsor.query.filter_by(tier=tier[0]).order_by(Sponsor.id).all()
        tiers.append((tier[0], rows))
    return render_template('sponsors.html', tiers=tiers, img=_img)


@app.route('/organizers')
def organizers():
    roles = []
    for role in db.session.query(Organizer.role).distinct().order_by(Organizer.id):
        rows = Organizer.query.filter_by(role=role[0]).order_by(Organizer.id).all()
        roles.append((role[0], rows))
    return render_template('organizers.html', roles=roles, img=_img)


@app.route('/awards')
def awards():
    groups = []
    for group in db.session.query(Award.award_group).distinct().order_by(Award.id):
        rows = Award.query.filter_by(award_group=group[0]).order_by(Award.id).all()
        groups.append((group[0], rows))
    committee = [
        'Gautam Kamath', 'Yoav Artzi', 'Emma Brunskill', 'Murat Erdogdu',
        'Pang Wei Koh', 'Yong Jae Lee', 'Subhransu Maji', 'Doina Precup',
        'Ohad Shamir', 'Guy Van den Broeck', 'Kilian Weinberger',
        'Luke Zettlemoyer']
    return render_template('awards.html', groups=groups, committee=committee,
                           img=_img)


@app.route('/news')
def news():
    rows = NewsPost.query.order_by(NewsPost.date.desc()).all()
    return render_template('news.html', rows=rows, img=_img)


@app.route('/news/<slug>')
def news_detail(slug):
    post = db.session.get(NewsPost, slug)
    if not post:
        abort(404)
    return render_template('news_detail.html', n=post,
                           fmt_date=fmt_date, img=_img)


@app.route('/dates')
def dates():
    years = {}
    for year in ('2026', '2027'):
        groups = []
        for group in (db.session.query(DateItem.group_name)
                      .filter_by(year=year).distinct().order_by(DateItem.id)):
            rows = (DateItem.query.filter_by(year=year, group_name=group[0])
                    .order_by(DateItem.id).all())
            groups.append((group[0], rows))
        years[year] = groups
    venue = _load('venue.json')
    return render_template('dates.html', years=years, venue=venue)


@app.route('/venue')
def venue():
    v = _load('venue.json')
    return render_template('venue.html', v=v, img=_img)


@app.route('/about')
def about():
    a = _load('about.json')
    conf = _conference_meta()
    return render_template('about.html', a=a, conf=conf)


@app.route('/faq')
def faq():
    sections = []
    current = None
    for row in _load('faq.json'):
        if current is None or row['section'] != current[0]:
            current = (row['section'], [])
            sections.append(current)
        current[1].append(row)
    return render_template('faq.html', sections=sections)


def _search_snippet(text, q, radius=90):
    """Deterministic snippet centred on the first case-insensitive match."""
    idx = text.lower().find(q.lower())
    if idx < 0:
        return text[:2 * radius]
    start = max(0, idx - radius)
    end = min(len(text), idx + len(q) + radius)
    snippet = text[start:end]
    if start > 0:
        snippet = '\u2026' + snippet
    if end < len(text):
        snippet += '\u2026'
    return snippet


def _venue_search_hits(q):
    """Case-insensitive search over the Conference Site page text (venue.json).

    Returns a deterministic list of (heading, snippet) pairs for the
    site-wide search results page so practical-info notes (venue name,
    badge/luggage policies, the ICLR 2027 preview) are searchable like
    every other content section."""
    v = _load('venue.json')
    ql = q.lower()
    hits = []

    def add(heading, text):
        if ql in text.lower():
            hits.append((heading, _search_snippet(text, q)))

    add(v['site'], f'{v["conference"]} — {v["site"]}, {v["city"]}, '
                   f'{v["country"]} · {v["dates"]}')
    for note in v.get('site_notes', []):
        add(v['site'], note)
    nxt = v.get('next') or {}
    if nxt:
        add(f'Looking ahead — {nxt.get("conference", "")}',
            f'{nxt.get("full_name", "")} — {nxt.get("location", "")}, '
            f'{nxt.get("dates", "")}')
    return hits


@app.route('/search')
def search():
    q = (request.args.get('q') or '').strip()
    papers = events = workshops = sponsors = news = []
    venue_hits = []
    if q:
        like = f'%{q}%'
        papers = (Paper.query.filter(Paper.title.ilike(like))
                  .order_by(Paper.title).limit(12).all())
        events = (Event.query.filter(Event.title.ilike(like))
                  .order_by(Event.date, Event.start).limit(12).all())
        sponsors = (Sponsor.query.filter(Sponsor.name.ilike(like))
                   .order_by(Sponsor.name).limit(12).all())
        news = (NewsPost.query.filter(
                    db.or_(NewsPost.title.ilike(like),
                           NewsPost.body.ilike(like)))
                .order_by(NewsPost.date.desc()).limit(8).all())
        venue_hits = _venue_search_hits(q)
    return render_template('search.html', q=q, papers=papers, events=events,
                           sponsors=sponsors, news=news, venue_hits=venue_hits,
                           img=_img)


# ----------------------------------------------------------- registration --

@app.route('/register', methods=['GET', 'POST'])
def register():
    error = None
    if request.method == 'POST':
        name = (request.form.get('name') or '').strip()
        email = (request.form.get('email') or '').strip().lower()
        affiliation = request.form.get('affiliation') or ''
        dietary = (request.form.get('dietary') or '').strip()
        items = request.form.getlist('items')
        banquet_raw = request.form.get('banquet_tickets') or '0'
        banquet = int(banquet_raw) if banquet_raw.isdigit() else -1
        if not name or '@' not in email:
            error = 'Enter your full name and a valid email address.'
        elif affiliation not in REG_AFFILIATIONS:
            error = 'Choose your affiliation type.'
        elif not items:
            error = 'Check at least one registration item.'
        elif ('Conference Sessions and Workshops' in items
              and len(items) > 1):
            error = ('If you choose Conference Sessions and Workshops, do not '
                     'check any other items.')
        elif banquet < 0 or banquet > 5:
            error = 'Guest banquet tickets: enter a number from 0 to 5.'
        else:
            total = BANQUET_PRICE_USD * banquet
            code = 'ICLR26-' + secrets.token_hex(4).upper()
            reg = Registration(
                user_id=current_user.id if current_user.is_authenticated else None,
                name=name, email=email, affiliation=affiliation,
                items=json.dumps(items), banquet_tickets=banquet,
                dietary=dietary or None, total_usd=total, reg_code=code,
                created=MIRROR_TS)
            db.session.add(reg)
            db.session.commit()
            return redirect(url_for('register_confirmation', code=code))
    return render_template('register.html', error=error,
                           affiliations=REG_AFFILIATIONS, items=REG_ITEMS,
                           exclusivity=REG_EXCLUSIVITY,
                           banquet_price=BANQUET_PRICE_USD)


@app.route('/register/confirmation/<code>')
def register_confirmation(code):
    reg = Registration.query.filter_by(reg_code=code).first()
    if not reg:
        abort(404)
    return render_template('register_confirmation.html', r=reg)


@app.route('/helpdesk', methods=['GET', 'POST'])
def helpdesk():
    error = None
    if request.method == 'POST':
        name = (request.form.get('name') or '').strip()
        email = (request.form.get('email') or '').strip().lower()
        topic = request.form.get('topic') or ''
        subject = (request.form.get('subject') or '').strip()
        body = (request.form.get('body') or '').strip()
        if not name or '@' not in email:
            error = 'Enter your name and a valid email address.'
        elif topic not in dict(HELPDESK_TOPICS):
            error = 'Choose an email topic.'
        elif not subject or not body:
            error = 'Fill in the subject and the message body.'
        else:
            db.session.add(ContactMessage(name=name, email=email, topic=topic,
                                           subject=subject, body=body,
                                           created=MIRROR_TS))
            db.session.commit()
            return render_template('helpdesk.html', sent=True,
                                   topics=HELPDESK_TOPICS)
    return render_template('helpdesk.html', sent=False, error=error,
                           topics=HELPDESK_TOPICS)


# ------------------------------------------------------------------ account --

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')
    email = (request.form.get('email') or '').strip().lower()
    password = request.form.get('password') or ''
    user = User.query.filter_by(email=email).first()
    if user and bcrypt.check_password_hash(user.password_hash, password):
        login_user(user)
        target = request.args.get('next') or request.form.get('next')
        return local_redirect(target, url_for('home'))
    return render_template('login.html', error='Invalid email or password.')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'GET':
        return render_template('signup.html')
    name = (request.form.get('name') or '').strip()
    email = (request.form.get('email') or '').strip().lower()
    password = request.form.get('password') or ''
    if not name or '@' not in email or len(password) < 8:
        return render_template(
            'signup.html',
            error='Enter your full name, a valid email and a password of at '
                  'least 8 characters.')
    if User.query.filter_by(email=email).first():
        return render_template('signup.html',
                               error='An account with that email already exists.')
    user = User(email=email, name=name,
                password_hash=bcrypt.generate_password_hash(password).decode(),
                joined=MIRROR_TS)
    db.session.add(user)
    db.session.commit()
    login_user(user)
    return redirect(url_for('home'))


@app.route('/mystuff')
@login_required
def mystuff():
    bookmarks = (Bookmark.query.filter_by(user_id=current_user.id)
                 .order_by(Bookmark.id).all())
    papers = {b.paper_id: db.session.get(Paper, b.paper_id) for b in bookmarks}
    saves = (ScheduleSave.query.filter_by(user_id=current_user.id)
             .order_by(ScheduleSave.id).all())
    events = {s.event_id: db.session.get(Event, s.event_id) for s in saves}
    regs = (Registration.query.filter_by(user_id=current_user.id)
            .order_by(Registration.id).all())
    return render_template('mystuff.html', bookmarks=bookmarks,
                           papers=papers, saves=saves, events=events,
                           regs=regs, fmt_time=fmt_time, fmt_date=fmt_date,
                           img=_img)


# -------------------------------------------------------------- error pages --

@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404


# -------------------------------------------------------------------- seeds --

def seed_database():
    if Paper.query.count() > 0:
        return
    from seed_lib import seed_all
    seed_all(db)


def seed_benchmark_users():
    from seed_lib import seed_benchmark_users as _s
    _s(db)


# Explicit, alphabetically ordered index creation. SQLAlchemy 2.0 stores
# Table.indexes in an id-hashed set, so index=True flags make db.create_all()
# emit CREATE INDEX in a per-process memory-address order and the resulting
# SQLite file is not byte-reproducible. Creating the indexes here in a fixed
# order keeps the seed byte-identical across rebuilds.
INDEX_STATEMENTS = (
    'CREATE INDEX IF NOT EXISTS ix_awards_award_group ON awards ("award_group")',
    'CREATE INDEX IF NOT EXISTS ix_bookmarks_user_id ON bookmarks ("user_id")',
    'CREATE INDEX IF NOT EXISTS ix_date_items_date ON date_items ("date")',
    'CREATE INDEX IF NOT EXISTS ix_events_date ON events ("date")',
    'CREATE INDEX IF NOT EXISTS ix_events_kind ON events ("kind")',
    'CREATE INDEX IF NOT EXISTS ix_news_posts_date ON news_posts ("date")',
    'CREATE INDEX IF NOT EXISTS ix_organizers_role ON organizers ("role")',
    'CREATE INDEX IF NOT EXISTS ix_papers_day ON papers ("day")',
    'CREATE INDEX IF NOT EXISTS ix_papers_decision ON papers ("decision")',
    'CREATE INDEX IF NOT EXISTS ix_papers_session ON papers ("session")',
    'CREATE INDEX IF NOT EXISTS ix_papers_topic ON papers ("topic")',
    'CREATE INDEX IF NOT EXISTS ix_registrations_reg_code ON registrations ("reg_code")',
    'CREATE INDEX IF NOT EXISTS ix_registrations_user_id ON registrations ("user_id")',
    'CREATE INDEX IF NOT EXISTS ix_schedule_saves_user_id ON schedule_saves ("user_id")',
    'CREATE INDEX IF NOT EXISTS ix_sponsors_tier ON sponsors ("tier")',
    'CREATE INDEX IF NOT EXISTS ix_users_email ON users ("email")',
)


def create_indexes():
    """Create the schema indexes in a deterministic (alphabetical) order."""
    from sqlalchemy import text
    for stmt in INDEX_STATEMENTS:
        db.session.execute(text(stmt))
    db.session.commit()


def main():
    with app.app_context():
        db.create_all()
        create_indexes()
        seed_database()
        seed_benchmark_users()


with app.app_context():
    db.create_all()
    create_indexes()
    if os.environ.get('ICLR_AUTO_SEED', '1') == '1':
        seed_database()
        seed_benchmark_users()
