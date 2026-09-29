#!/usr/bin/env python3
"""ziprecruiter — a WebHarbor mirror of https://www.ziprecruiter.com/

Flask + SQLite mirror of ZipRecruiter (job-search vertical): the home
search, the job SERP with the upstream filter taxonomy (apply type,
remote, distance, date posted, salary range, employment types,
experience level) and pagination, job detail pages with the full
captured descriptions, company profiles, title landing pages
(/Jobs/<Title>), the salary pages (/Salaries/<Title>-Salary with
percentiles, histogram, top cities, by-state table and related titles),
the career-advice blog, and the job-seeker account area (profile,
resume builder, saved jobs, applications with status timelines, job
alerts) seeded for four benchmark users.

Content comes from the tracked source_data/*.json snapshots captured
from ziprecruiter.com on 2026-09-29 with a headful Chromium that
passed the upstream Cloudflare interstitial (see provenance.json); the
SQLite seed is materialized deterministically at image build time
(PYTHONHASHSEED=0).
"""
import html
import json
import os
import re
from datetime import date

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
app.config["SECRET_KEY"] = os.environ.get("ZIPRECRUITER_SECRET_KEY") or "webharbor-ziprecruiter-dev-key"
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'ZIPRECRUITER_DB_URI', f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'ziprecruiter.db')}")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['WTF_CSRF_TIME_LIMIT'] = None

os.makedirs(os.path.join(BASE_DIR, 'instance'), exist_ok=True)

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'authn_login'
login_manager.login_message = 'Please log in to continue.'
csrf = CSRFProtect(app)

# The mirror is a frozen snapshot of the upstream site taken 2026-09-29.
MIRROR_DATE = date(2026, 9, 29)
MIRROR_TS = "2026-09-29"
SITE_NAME = "ziprecruiter"
UPSTREAM = "https://www.ziprecruiter.com/"
# bcrypt hash of 'TestPass123!' — frozen so the seed DB is byte-reproducible.
BENCHMARK_PASSWORD_HASH = (
    '$2b$12$qSds4Mr9Wo7VwPWLhompEer88SuxxXFDp31P9etY6v7nfRctNO7B.')
SOURCE = os.path.join(BASE_DIR, 'source_data')

# The upstream filter taxonomy, frozen exactly as the SERP filter panel
# renders it (captured 2026-09-29).
REMOTE_MODES = ['onsite', 'hybrid', 'remote']
REMOTE_LABELS = {'onsite': 'On-site', 'hybrid': 'Hybrid', 'remote': 'Remote'}
DISTANCES = [5, 10, 25, 50, 100]
DATE_FILTERS = [1, 5, 10, 30]
EMPLOYMENT_TYPES = ['full_time', 'part_time', 'per_diem', 'contract',
                    'temporary', 'other']
EMPLOYMENT_LABELS = {
    'full_time': 'Full Time', 'part_time': 'Part Time',
    'per_diem': 'Per Diem', 'contract': 'Contract',
    'temporary': 'Temporary', 'other': 'Other',
}
EXPERIENCE_LEVELS = ['none', 'junior', 'mid', 'senior']
EXPERIENCE_LABELS = {'none': 'No experience needed', 'junior': 'Junior level',
                     'mid': 'Mid level', 'senior': 'Senior level and above'}
PER_PAGE = 20

STATE_CODES = {c for c in ['AL','AK','AZ','AR','CA','CO','CT','DE','FL','GA','HI','ID','IL','IN','IA','KS','KY','LA','ME','MD','MA','MI','MN','MS','MO','MT','NE','NV','NH','NJ','NM','NY','NC','ND','OH','OK','OR','PA','RI','SC','SD','TN','TX','UT','VT','VA','WA','WV','WI','WY','DC']}


def _load(name):
    with open(os.path.join(SOURCE, name), encoding='utf-8') as f:
        return json.load(f)


# --------------------------------------------------------- asset resolution --

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


@app.template_filter('rich_text')
def rich_text(s):
    """Render captured upstream HTML with its formatting intact.

    The upstream captures store the inline formatting of the job
    descriptions HTML-escaped (&lt;b&gt;...&lt;/b&gt;); rendering them raw
    made the browser show literal <b>...</b> tags instead of the
    upstream bold/italics. Unescape once at render time so the browser
    renders the formatting exactly as ziprecruiter.com does.
    """
    return Markup(html.unescape(s or ''))


# ------------------------------------------------------------------- models --

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(160), unique=True, nullable=False)
    display_name = db.Column(db.String(120), nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    is_benchmark = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.String(10), nullable=False, default='2026-09-01')


class Company(db.Model):
    __tablename__ = 'companies'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), nullable=False)
    slug = db.Column(db.String(180), unique=True, nullable=False)
    industry = db.Column(db.String(120))
    size = db.Column(db.String(60))
    hq_city = db.Column(db.String(80))
    hq_state = db.Column(db.String(8))
    founded = db.Column(db.String(10))
    website = db.Column(db.String(200))
    logo = db.Column(db.String(80))          # logical asset name
    rating_value = db.Column(db.String(8))   # e.g. '6.8'
    rating_count = db.Column(db.Integer)     # frontline responses
    rating_highlights = db.Column(db.Text)    # JSON list of highlight strings
    findings = db.Column(db.Text)             # JSON list of {short, detail}
    perks = db.Column(db.Text)                # JSON list of perk strings
    about = db.Column(db.Text)               # "About <co>, in their own words"
    sourced_about = db.Column(db.Text)        # "About <co>" (Sourced by ZipRecruiter)
    description = db.Column(db.Text)          # employer blurb on profile page
    n_jobs = db.Column(db.Integer, default=0)

    def logo_url(self):
        return img(self.logo) if self.logo else None

    def rating_highlights_list(self):
        return json.loads(self.rating_highlights or '[]')

    def perks_list(self):
        return json.loads(self.perks or '[]')

    def findings_list(self):
        return json.loads(self.findings or '[]')


class JobCategory(db.Model):
    __tablename__ = 'job_categories'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    slug = db.Column(db.String(140), unique=True, nullable=False)


class Job(db.Model):
    __tablename__ = 'jobs'
    id = db.Column(db.Integer, primary_key=True)
    jid = db.Column(db.String(32), unique=True, nullable=False)
    title = db.Column(db.String(220), nullable=False)
    title_slug = db.Column(db.String(220), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'),
                           nullable=False)
    company = db.relationship('Company', backref=db.backref('jobs', lazy='dynamic'))
    city = db.Column(db.String(100), nullable=False)
    state = db.Column(db.String(8), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('job_categories.id'))
    category = db.relationship('JobCategory')
    employment_types = db.Column(db.String(120), nullable=False,
                                 default='full_time')   # comma list
    remote = db.Column(db.String(12), nullable=False, default='onsite')
    experience = db.Column(db.String(12), nullable=False, default='mid')
    salary_min = db.Column(db.Integer)       # annualized dollars
    salary_max = db.Column(db.Integer)
    salary_period = db.Column(db.String(8))  # 'year' | 'hour' | 'week' | 'month'
    salary_text = db.Column(db.String(80))   # upstream display text
    posted_days = db.Column(db.Integer, nullable=False, default=0)
    posted_text = db.Column(db.String(60))
    quick_apply = db.Column(db.Boolean, nullable=False, default=False)
    is_new = db.Column(db.Boolean, nullable=False, default=False)
    description_html = db.Column(db.Text, nullable=False)
    badges = db.Column(db.Text)               # JSON list of badge strings
    soc_code = db.Column(db.String(20))
    active = db.Column(db.Boolean, nullable=False, default=True)

    def employment_list(self):
        return [t for t in (self.employment_types or '').split(',') if t]

    def employment_display(self):
        return ', '.join(EMPLOYMENT_LABELS.get(t, t.title().replace('_', '-'))
                         for t in self.employment_list())

    def badge_list(self):
        """Card badges exactly as the upstream SERP renders them."""
        badges = []
        if self.badges:
            badges.extend(json.loads(self.badges))
        if self.is_new and 'New' not in badges:
            badges.append('New')
        if self.quick_apply and 'Quick apply' not in badges:
            badges.append('Quick apply')
        return badges

    def remote_display(self):
        if self.remote == 'remote':
            return None
        return REMOTE_LABELS.get(self.remote)

    def posted_display(self):
        if self.posted_text:
            if self.posted_text.startswith(('Posted', 'Re-posted')):
                return self.posted_text
            return f'Posted {self.posted_text}'
        if self.posted_days == 0:
            return 'Posted today'
        return f'Posted {self.posted_days} days ago'

    def family_slug(self):
        """The title landing-page slug this job rolls up under."""
        fam = JobTitle.query.filter_by(slug=self.title_slug).first()
        return fam.slug if fam else self.title_slug

    def url(self):
        return url_for('job_detail', company=self.company.slug,
                       title=self.title_slug,
                       location=f"-in-{self.city},{self.state}".replace(' ', '-'),
                       jid=self.jid)


class JobTitle(db.Model):
    """A title landing page (/Jobs/<slug>) plus its salary page."""
    __tablename__ = 'job_titles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), nullable=False)
    slug = db.Column(db.String(180), unique=True, nullable=False)
    family = db.Column(db.String(180))        # canonical search family
    category_id = db.Column(db.Integer, db.ForeignKey('job_categories.id'))
    blurb = db.Column(db.Text)                # short description under the H1


class SearchSnapshot(db.Model):
    """Upstream SERP context for the captured search terms."""
    __tablename__ = 'search_snapshots'
    id = db.Column(db.Integer, primary_key=True)
    term = db.Column(db.String(120), nullable=False)
    location = db.Column(db.String(120), nullable=False)
    upstream_total = db.Column(db.Integer, nullable=False)
    page1_order = db.Column(db.Text)      # JSON [job.id, ...] upstream page-1 order

    def order_ids(self):
        return json.loads(self.page1_order or '[]')


class SalaryStat(db.Model):
    """One salary page: national or a city scope."""
    __tablename__ = 'salary_stats'
    id = db.Column(db.Integer, primary_key=True)
    title_slug = db.Column(db.String(180), nullable=False)
    scope = db.Column(db.String(12), nullable=False)   # national | city
    city = db.Column(db.String(100))
    state = db.Column(db.String(8))
    avg_year = db.Column(db.Integer, nullable=False)
    avg_hour = db.Column(db.String(10), nullable=False)
    p10 = db.Column(db.Integer)
    p25 = db.Column(db.Integer)
    median = db.Column(db.Integer)
    p75 = db.Column(db.Integer)
    p90 = db.Column(db.Integer)
    histogram = db.Column(db.Text)      # JSON [ [lo, hi, pct], ... ]
    top_cities = db.Column(db.Text)     # JSON [ [city, state, avg], ... ]
    by_state = db.Column(db.Text)      # JSON [ [state, avg], ... ]
    related = db.Column(db.Text)       # JSON [ [name, slug, avg], ... ]
    nearby_jobs = db.Column(db.Text)    # JSON [ jid, ... ] (mirror rows)

    def histogram_rows(self):
        return json.loads(self.histogram or '[]')

    def city_rows(self):
        return json.loads(self.top_cities or '[]')

    def state_rows(self):
        return json.loads(self.by_state or '[]')

    def related_rows(self):
        return json.loads(self.related or '[]')

    def _money(self, v):
        if v is None:
            return '—'
        if v >= 1000:
            return f"${v/1000:.1f}K".replace('.0K', 'K')
        return f"${v}"

    def range_display(self):
        return f"{self._money(self.p10)} - {self._money(self.p90)}"

    def p25_display(self):
        return self._money(self.p25)

    def median_display(self):
        return self._money(self.median)

    def p75_display(self):
        return self._money(self.p75)

    def page_title(self):
        jt = JobTitle.query.filter_by(slug=self.title_slug).first()
        name = jt.name if jt else self.title_slug.replace('-', ' ')
        if self.scope == 'city':
            return (f"Salary: {name} in {self.city}, {self.state} "
                    f"(Sep, 2026)")
        return f"Salary: {name} (September, 2026) United States"


class TitleFaq(db.Model):
    """Career Q&A captured on job detail pages (skills / career path)."""
    __tablename__ = 'title_faqs'
    id = db.Column(db.Integer, primary_key=True)
    title_slug = db.Column(db.String(180), nullable=False)
    question = db.Column(db.Text, nullable=False)
    answer_html = db.Column(db.Text, nullable=False)


class BlogCategory(db.Model):
    __tablename__ = 'blog_categories'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    slug = db.Column(db.String(140), unique=True, nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('blog_categories.id'))
    parent = db.relationship('BlogCategory', remote_side=[id],
                             backref=db.backref('children', lazy='dynamic'))


class Article(db.Model):
    __tablename__ = 'articles'
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(200), unique=True, nullable=False)
    title = db.Column(db.String(240), nullable=False)
    author = db.Column(db.String(120), nullable=False)
    published = db.Column(db.String(20), nullable=False)
    modified = db.Column(db.String(20))
    category_id = db.Column(db.Integer, db.ForeignKey('blog_categories.id'))
    category = db.relationship('BlogCategory')
    hero = db.Column(db.String(80))     # logical asset name
    excerpt = db.Column(db.Text)
    body_html = db.Column(db.Text, nullable=False)

    def hero_url(self):
        return img(self.hero) if self.hero else None


class Profile(db.Model):
    __tablename__ = 'profiles'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False,
                        unique=True)
    user = db.relationship('User')
    phone = db.Column(db.String(40))
    location = db.Column(db.String(120))
    headline = db.Column(db.String(200))
    about = db.Column(db.Text)
    years_experience = db.Column(db.Integer)
    willing_remote = db.Column(db.Boolean, default=False)


class Resume(db.Model):
    __tablename__ = 'resumes'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False,
                        unique=True)
    user = db.relationship('User')
    title = db.Column(db.String(120))
    summary = db.Column(db.Text)
    updated_at = db.Column(db.String(20), nullable=False, default=MIRROR_TS)
    # JSON arrays of section rows
    experience = db.Column(db.Text)     # [ [role, employer, start, end, text], ...]
    education = db.Column(db.Text)     # [ [degree, school, year], ... ]
    skills = db.Column(db.Text)        # [ [skill, yrs], ... ]

    def exp_rows(self):
        return json.loads(self.experience or '[]')

    def edu_rows(self):
        return json.loads(self.education or '[]')

    def skill_rows(self):
        return json.loads(self.skills or '[]')

    def completeness(self):
        n = 0
        n += 1 if self.summary else 0
        n += 1 if self.exp_rows() else 0
        n += 1 if self.edu_rows() else 0
        n += 1 if self.skill_rows() else 0
        return n


class SavedJob(db.Model):
    __tablename__ = 'saved_jobs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    job_id = db.Column(db.Integer, db.ForeignKey('jobs.id'), nullable=False)
    saved_at = db.Column(db.String(20), nullable=False, default=MIRROR_TS)
    job = db.relationship('Job')
    __table_args__ = (db.UniqueConstraint('user_id', 'job_id'),)


class Application(db.Model):
    __tablename__ = 'applications'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    job_id = db.Column(db.Integer, db.ForeignKey('jobs.id'), nullable=False)
    applied_at = db.Column(db.String(20), nullable=False, default=MIRROR_TS)
    status = db.Column(db.String(40), nullable=False, default='Applied')
    cover_note = db.Column(db.Text)
    job = db.relationship('Job')
    __table_args__ = (db.UniqueConstraint('user_id', 'job_id'),)

    def timeline(self):
        return (ApplicationEvent.query.filter_by(application_id=self.id)
                .order_by(ApplicationEvent.occurred_at, ApplicationEvent.id)
                .all())


class ApplicationEvent(db.Model):
    __tablename__ = 'application_events'
    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey('applications.id'),
                               nullable=False)
    status = db.Column(db.String(40), nullable=False)
    note = db.Column(db.String(240))
    occurred_at = db.Column(db.String(20), nullable=False, default=MIRROR_TS)
    application = db.relationship('Application',
                                  backref=db.backref('events', lazy='dynamic'))


class JobAlert(db.Model):
    __tablename__ = 'job_alerts'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    term = db.Column(db.String(120), nullable=False)
    location = db.Column(db.String(120), nullable=False)
    frequency = db.Column(db.String(20), nullable=False, default='daily')
    created_at = db.Column(db.String(20), nullable=False, default=MIRROR_TS)


@login_manager.user_loader
def load_user(uid):
    return User.query.get(int(uid))


# ----------------------------------------------------------- page context --

@app.context_processor
def base_context():
    saved = 0
    if current_user.is_authenticated:
        saved = SavedJob.query.filter_by(user_id=current_user.id).count()
    return {
        'logo_url': img('ziprecruiter-whitetext'),
        'saved_count': saved,
        'phil_url': img('phil-cartoon-dark-640'),
    }


@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404


# ------------------------------------------------------------------ helpers --

# ------------------------------------------------------------------ helpers --

def _job_url_slug(city, state):
    return f"-in-{city},{state}".replace(' ', '-')


def tokenize(s):
    return [t for t in re.split(r'[^a-z0-9]+', (s or '').lower()) if len(t) > 1]


def money_year(v):
    if v is None:
        return None
    if v >= 1000:
        return f"${v/1000:.1f}K".replace('.0K', 'K')
    return f"${v}"


# -------------------------------------------------------------------- routes --

@app.route('/_health')
def health():
    return jsonify(ok=True,
                   jobs=Job.query.filter_by(active=True).count(),
                   companies=Company.query.count(),
                   salaries=SalaryStat.query.count(),
                   articles=Article.query.count(),
                   titles=JobTitle.query.count(),
                   users=User.query.filter_by(is_benchmark=True).count())


@app.route('/')
def home():
    categories = JobCategory.query.order_by(JobCategory.name).all()
    searches = SearchSnapshot.query.order_by(SearchSnapshot.term).all()
    return render_template('home.html', categories=categories,
                           searches=searches,
                           job_count_for=_job_count_for)


def _job_count_for(cat_id):
    return Job.query.filter_by(active=True, category_id=cat_id).count()


# ------------------------------------------------------------------- search --

def _load_metros():
    """Metro city sets derived from the captured upstream SERPs: for every
    captured search location, the (city, state) pairs the upstream page-1
    results actually covered (e.g. "New York, NY" spans Manhattan,
    Brooklyn and the NJ suburbs exactly as the capture shows)."""
    path = os.path.join(SOURCE, 'metros.json')
    if not os.path.exists(path):
        return {}
    with open(path, encoding='utf-8') as f:
        raw = json.load(f)
    return {loc: {(c, s) for c, s in pairs} for loc, pairs in raw.items()}


_METROS = None


def metros():
    global _METROS
    if _METROS is None:
        _METROS = _load_metros()
    return _METROS


def _filtered_jobs(term, location, f):
    q = Job.query.filter_by(active=True).join(Company).outerjoin(JobCategory)
    if term:
        for t in tokenize(term):
            q = q.filter(db.or_(
                Job.title.ilike(f'%{t}%'),
                Company.name.ilike(f'%{t}%'),
                JobCategory.name.ilike(f'%{t}%')))
    if location:
        loc = location.strip()
        metro = metros().get(loc)
        if metro is not None:
            conds = [db.and_(Job.city == c, Job.state == s)
                     for c, s in sorted(metro)]
            q = q.filter(db.or_(*conds))
        elif ',' in loc:
            city, state = [p.strip() for p in loc.split(',', 1)]
            if state:
                q = q.filter(Job.state == state.upper())
            if city:
                q = q.filter(Job.city.ilike(f'%{city}%'))
        elif len(loc) == 2 and loc.upper() in STATE_CODES:
            q = q.filter(Job.state == loc.upper())
        else:
            q = q.filter(db.or_(Job.city.ilike(f'%{loc}%'),
                                Job.state == loc.upper()))
    if f.get('apply') == 'quick':
        q = q.filter(Job.quick_apply.is_(True))
    if f.get('remote') in REMOTE_MODES:
        q = q.filter(Job.remote == f['remote'])
    if f.get('days'):
        q = q.filter(Job.posted_days <= int(f['days']))
    if f.get('et'):
        et = [t for t in f['et'].split(',') if t in EMPLOYMENT_TYPES]
        if et:
            conds = []
            for t in et:
                conds.append(Job.employment_types.ilike(f'%{t}%'))
            q = q.filter(db.or_(*conds))
    if f.get('exp') in EXPERIENCE_LEVELS:
        q = q.filter(Job.experience == f['exp'])
    try:
        smin = int(f.get('smin') or 0)
    except ValueError:
        smin = 0
    try:
        smax = int(f.get('smax') or 0)
    except ValueError:
        smax = 0
    if smin:
        q = q.filter(Job.salary_max >= smin)
    if smax:
        q = q.filter(Job.salary_min <= smax)
    return q


@app.route('/jobs-search')
def jobs_search():
    term = request.args.get('search', '').strip()
    location = request.args.get('location', '').strip()
    # Employment types arrive either as repeated ?et=... params (the
    # real checkbox panel submits one value per checked box) or as one
    # comma-joined value; accept both so the UI combination filter works
    # in a real browser, and keep the normalized comma-joined string in f.
    ets = []
    for v in request.args.getlist('et'):
        ets.extend(t.strip() for t in v.split(','))
    seen = set()
    et_norm = ','.join(t for t in ets
                       if t in EMPLOYMENT_TYPES and not (t in seen or seen.add(t)))
    f = {k: request.args.get(k, '').strip()
         for k in ('apply', 'remote', 'distance', 'days', 'smin',
                   'smax', 'exp')}
    f['et'] = et_norm
    if not term and not location and not any(f.values()):
        # An empty query degrades upstream to the near-me page; do the
        # same instead of rendering the whole corpus as "785 Job Jobs".
        return redirect(url_for('search_near_me'))
    try:
        page = max(1, int(request.args.get('page', 1)))
    except ValueError:
        page = 1
    q = _filtered_jobs(term, location, f)
    total = q.count()
    # For exactly-captured search terms the first page preserves the
    # upstream page-1 order (page1_order); everything else sorts by
    # posted recency then id — fully deterministic either way.
    snapshot = SearchSnapshot.query.filter_by(
        term=(term or '').lower(), location=location).first() if (term or location) else None
    ordered = list(q.order_by(Job.posted_days, Job.id).all())
    if snapshot and page == 1 and not any(v for v in f.values()):
        rank = {jid: i for i, jid in enumerate(snapshot.order_ids())}
        ordered.sort(key=lambda j: (rank.get(j.id, 10 ** 9),
                                    j.posted_days, j.id))
    start = (page - 1) * PER_PAGE
    jobs = ordered[start:start + PER_PAGE]
    pages = max(1, (total + PER_PAGE - 1) // PER_PAGE)
    first = jobs[0] if jobs else None

    def serp_url(p):
        args = {'search': term, 'location': location, 'page': p}
        for k, v in f.items():
            if v and k not in ('distance',):
                args[k] = v
        return url_for('jobs_search', **args)

    et_labels = ', '.join(EMPLOYMENT_LABELS.get(t, t)
                          for t in (f.get('et') or '').split(',') if t)
    return render_template(
        'jobs_search.html', jobs=jobs, total=total, page=page, pages=pages,
        term=term, location=location, f=f, first=first, snapshot=snapshot,
        per_page=PER_PAGE, first_index=(page - 1) * PER_PAGE + 1,
        remote_labels=REMOTE_LABELS, employment_labels=EMPLOYMENT_LABELS,
        experience_labels=EXPERIENCE_LABELS,
        serp_url=serp_url, et_labels=et_labels)


@app.route('/Search-Jobs-Near-Me')
def search_near_me():
    term = request.args.get('search', '').strip()
    location = request.args.get('location', '').strip()
    jobs = Job.query.filter_by(active=True).order_by(Job.posted_days, Job.id)
    if term or location:
        return redirect(url_for('jobs_search', search=term, location=location))
    return render_template('near_me.html', jobs=jobs.limit(20).all(),
                           total=Job.query.filter_by(active=True).count())


# -------------------------------------------------------------- job details --

@app.route('/c/<company>/Job/<title>/<location>')
def job_detail(company, title, location):
    jid = request.args.get('jid', '')
    job = Job.query.filter_by(jid=jid).first()
    if not job or job.title_slug != title:
        abort(404)
    related = (Job.query.filter_by(active=True, title_slug=job.title_slug)
               .filter(Job.id != job.id).limit(6).all())
    faqs = TitleFaq.query.filter_by(title_slug=job.family_slug()).all()
    saved = False
    applied = None
    if current_user.is_authenticated:
        saved = SavedJob.query.filter_by(user_id=current_user.id,
                                         job_id=job.id).first() is not None
        applied = Application.query.filter_by(user_id=current_user.id,
                                             job_id=job.id).first()
    return render_template('job_detail.html', job=job, related=related,
                           faqs=faqs, saved=saved, applied=applied)


# ---------------------------------------------------------------- companies --

@app.route('/co/<company>')
def company_profile(company):
    co = Company.query.filter_by(slug=company).first_or_404()
    jobs = (Job.query.filter_by(active=True, company_id=co.id)
            .order_by(Job.posted_days, Job.id).limit(20).all())
    # Jobs-by-location section: every city the company's captured jobs
    # cover, linking the upstream-style /co/<slug>/Jobs/-in-<City>,ST
    # pages so they are reachable by navigation, not URL guessing.
    all_jobs = (Job.query.filter_by(active=True, company_id=co.id)
                .order_by(Job.city, Job.state).all())
    loc_counts = {}
    for j in all_jobs:
        loc_counts[(j.city, j.state)] = loc_counts.get((j.city, j.state), 0) + 1
    locations = sorted(loc_counts.items())
    return render_template('company.html', co=co, jobs=jobs,
                           locations=locations)


@app.route('/co/<company>/Jobs')
@app.route('/co/<company>/Jobs/<location>')
def company_jobs(company, location=None):
    co = Company.query.filter_by(slug=company).first_or_404()
    q = Job.query.filter_by(active=True, company_id=co.id)
    where = None
    if location and location.startswith('-in-'):
        loc = location[4:]
        if ',' in loc:
            city, state = [p.strip() for p in loc.rsplit(',', 1)]
            q = q.filter(Job.state == state.upper(),
                         Job.city.ilike(f'%{city.replace("-", " ")}%'))
            where = f"{city.replace('-', ' ')}, {state.upper()}"
    jobs = q.order_by(Job.posted_days, Job.id).all()
    return render_template('company_jobs.html', co=co, jobs=jobs, where=where)


# ------------------------------------------------------- title landing pages --

@app.route('/Jobs/<title>')
@app.route('/Jobs/<title>/<location>')
def title_jobs(title, location=None):
    jt = JobTitle.query.filter(
        db.func.lower(JobTitle.slug) == title.lower()).first()
    if not jt:
        abort(404)
    q = Job.query.filter_by(active=True)
    for t in tokenize(jt.name):
        q = q.filter(Job.title.ilike(f'%{t}%'))
    where = None
    if location and location.startswith('-in-'):
        loc = location[4:]
        if ',' in loc:
            city, state = [p.strip() for p in loc.rsplit(',', 1)]
            q = q.filter(Job.state == state.upper(),
                         Job.city.ilike(f'%{city.replace("-", " ")}%'))
            where = f"{city.replace('-', ' ')}, {state.upper()}"
    jobs = q.order_by(Job.posted_days, Job.id).limit(40).all()
    salary = SalaryStat.query.filter(
        db.func.lower(SalaryStat.title_slug) == jt.slug.lower(),
        SalaryStat.scope == 'national').first()
    return render_template('title_jobs.html', jt=jt, jobs=jobs,
                           where=where, salary=salary,
                           total=q.count())


# --------------------------------------------------------------------- browse --

@app.route('/browse')
def browse():
    letters = [c for c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ@']
    counts = {}
    for L in letters:
        if L == '@':
            counts[L] = 0
        else:
            counts[L] = JobTitle.query.filter(JobTitle.slug.like(f'{L.lower()}%')).count()
    categories = JobCategory.query.order_by(JobCategory.name).all()
    popular = (JobTitle.query.order_by(JobTitle.slug)
               .limit(24).all())
    return render_template('browse.html', letters=letters, counts=counts,
                           categories=categories, popular=popular)


@app.route('/browse/titles/<letter>')
def browse_letter(letter):
    letter = letter.upper()
    if letter not in [c for c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ@']:
        abort(404)
    titles = JobTitle.query.filter(JobTitle.slug.like(f'{letter.lower()}%')) \
        .order_by(JobTitle.slug).all()
    letters = [c for c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ@']
    return render_template('browse_letter.html', letter=letter, titles=titles,
                           letters=letters)


@app.route('/browse/salaries')
def browse_salaries():
    """Index of the captured salary pages (the footer's Search Salaries)."""
    national = (SalaryStat.query.filter_by(scope='national')
                .order_by(SalaryStat.title_slug).all())
    cities = (SalaryStat.query.filter_by(scope='city')
              .order_by(SalaryStat.title_slug, SalaryStat.city).all())
    return render_template('browse_salaries.html', national=national,
                           cities=cities)


@app.route('/privacy-policy')
def privacy_policy():
    return render_template('privacy_policy.html')


# -------------------------------------------------------------------- salary --

@app.route('/Salaries/<title>')
@app.route('/Salaries/<title>-in-<path:loc>')
def salary(title, loc=None):
    if title.lower().endswith('-salary'):
        slug = title[:-len('-Salary')]
    else:
        slug = title
    if loc is None:
        stat = SalaryStat.query.filter(
            db.func.lower(SalaryStat.title_slug) == slug.lower(),
            SalaryStat.scope == 'national').first()
    else:
        # loc like "San-Francisco,CA"
        city, state = None, None
        if ',' in loc:
            city, state = [p.strip() for p in loc.rsplit(',', 1)]
            city = city.replace('-', ' ')
            stat = SalaryStat.query.filter(
                db.func.lower(SalaryStat.title_slug) == slug.lower(),
                SalaryStat.scope == 'city',
                db.func.lower(SalaryStat.city) == city.lower(),
                db.func.upper(SalaryStat.state) == state.upper()).first()
        else:
            stat = None
    if not stat:
        abort(404)
    jt = JobTitle.query.filter(
        db.func.lower(JobTitle.slug) == stat.title_slug.lower()).first()
    # The captured city pages for the same title (the upstream salary page
    # links every city it covers; the mirror links the captured ones so
    # the city salary pages are reachable by navigation).
    city_stats = []
    if stat.scope == 'national':
        city_stats = (SalaryStat.query
                      .filter(SalaryStat.title_slug == stat.title_slug,
                              SalaryStat.scope == 'city')
                      .order_by(SalaryStat.city).all())
    national = None
    if stat.scope == 'city':
        national = SalaryStat.query.filter(
            SalaryStat.title_slug == stat.title_slug,
            SalaryStat.scope == 'national').first()
    nearby = []
    for jid in json.loads(stat.nearby_jobs or '[]'):
        j = Job.query.get(jid)
        if j:
            nearby.append(j)
    return render_template('salary.html', stat=stat, jt=jt, nearby=nearby[:6],
                           city_stats=city_stats, national=national)


# ---------------------------------------------------------------------- blog --

@app.route('/blog/')
def blog_home():
    cats = BlogCategory.query.filter_by(parent_id=None).order_by(BlogCategory.name).all()
    articles = Article.query.order_by(Article.published.desc()).all()
    return render_template('blog_home.html', cats=cats, articles=articles)


@app.route('/blog/category/<path:slug>/')
def blog_category(slug):
    cat = BlogCategory.query.filter_by(slug=slug).first_or_404()
    subcats = cat.children.order_by(BlogCategory.name).all() if hasattr(
        cat.children, 'order_by') else cat.children.all()
    articles = (Article.query.filter_by(category_id=cat.id)
                .order_by(Article.published.desc()).all())
    return render_template('blog_category.html', cat=cat,
                           subcats=subcats, articles=articles)


@app.route('/blog/<slug>/')
def blog_article(slug):
    art = Article.query.filter_by(slug=slug).first_or_404()
    more = (Article.query.filter(Article.id != art.id)
            .order_by(Article.published.desc()).limit(4).all())
    return render_template('blog_article.html', art=art, more=more)


# ---------------------------------------------------------------------- authn --

@app.route('/authn/login', methods=['GET', 'POST'])
def authn_login():
    realm = request.args.get('realm', 'candidates')
    next_url = request.args.get('next_url', '/')
    if not next_url.startswith('/'):
        next_url = '/'
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        user = User.query.filter_by(email=email).first()
        if user and bcrypt.check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(next_url)
        return render_template('authn_login.html', realm=realm,
                               next_url=next_url, error=True,
                               email=email)
    return render_template('authn_login.html', realm=realm,
                           next_url=next_url, error=False)


@app.route('/authn/register', methods=['GET', 'POST'])
def authn_register():
    realm = request.args.get('realm', 'candidates')
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        location = request.form.get('location', '').strip()
        errors = []
        if len(name) < 2:
            errors.append('Please enter your full name.')
        if not re.match(r'[^@\s]+@[^@\s]+\.[^@\s]+', email):
            errors.append('Please enter a valid email address.')
        if len(password) < 8:
            errors.append('Password must be at least 8 characters.')
        if User.query.filter_by(email=email).first():
            errors.append('An account with this email already exists.')
        if errors:
            return render_template('authn_register.html', realm=realm,
                                   errors=errors, form=request.form)
        user = User(email=email, display_name=name,
                    password_hash=bcrypt.generate_password_hash(
                        password).decode(), is_benchmark=False,
                    created_at=MIRROR_TS)
        db.session.add(user)
        db.session.flush()
        db.session.add(Profile(user_id=user.id, location=location or None))
        db.session.commit()
        login_user(user)
        return redirect(url_for('jobseeker_profile'))
    return render_template('authn_register.html', realm=realm,
                           errors=[], form={})


@app.route('/authn/logout', methods=['POST'])
def authn_logout():
    logout_user()
    return redirect('/')


# ------------------------------------------------------------------ jobseeker --

@app.route('/jobseeker/profile', methods=['GET', 'POST'])
@login_required
def jobseeker_profile():
    prof = Profile.query.filter_by(user_id=current_user.id).first()
    if request.method == 'POST':
        if not prof:
            prof = Profile(user_id=current_user.id)
            db.session.add(prof)
        prof.phone = request.form.get('phone', '').strip() or None
        prof.location = request.form.get('location', '').strip() or None
        prof.headline = request.form.get('headline', '').strip() or None
        prof.about = request.form.get('about', '').strip() or None
        try:
            prof.years_experience = int(request.form.get('years', 0) or 0)
        except ValueError:
            prof.years_experience = 0
        prof.willing_remote = request.form.get('remote') == 'on'
        current_user.display_name = request.form.get('name', '').strip() \
            or current_user.display_name
        db.session.commit()
        return redirect(url_for('jobseeker_profile'))
    res = Resume.query.filter_by(user_id=current_user.id).first()
    app_count = Application.query.filter_by(user_id=current_user.id).count()
    return render_template('jobseeker_profile.html', prof=prof, res=res,
                          app_count=app_count)


@app.route('/jobseeker/resume', methods=['GET', 'POST'])
@login_required
def jobseeker_resume():
    res = Resume.query.filter_by(user_id=current_user.id).first()
    if request.method == 'POST':
        if not res:
            res = Resume(user_id=current_user.id)
            db.session.add(res)
        res.title = request.form.get('title', '').strip() or None
        res.summary = request.form.get('summary', '').strip() or None
        res.updated_at = MIRROR_TS
        exp = []
        for i in range(1, 4):
            role = request.form.get(f'exp_role_{i}', '').strip()
            emp = request.form.get(f'exp_employer_{i}', '').strip()
            start = request.form.get(f'exp_start_{i}', '').strip()
            end = request.form.get(f'exp_end_{i}', '').strip()
            text = request.form.get(f'exp_text_{i}', '').strip()
            if role:
                exp.append([role, emp, start, end, text])
        res.experience = json.dumps(exp)
        edu = []
        for i in range(1, 3):
            degree = request.form.get(f'edu_degree_{i}', '').strip()
            school = request.form.get(f'edu_school_{i}', '').strip()
            year = request.form.get(f'edu_year_{i}', '').strip()
            if degree:
                edu.append([degree, school, year])
        res.education = json.dumps(edu)
        skills = []
        for i in range(1, 13):
            skill = request.form.get(f'skill_{i}', '').strip()
            yrs = request.form.get(f'skill_yrs_{i}', '').strip()
            if skill:
                skills.append([skill, yrs])
        res.skills = json.dumps(skills)
        db.session.commit()
        return redirect(url_for('jobseeker_resume'))
    return render_template('jobseeker_resume.html', res=res)


@app.route('/jobseeker/saved-jobs')
@login_required
def jobseeker_saved():
    rows = (SavedJob.query.filter_by(user_id=current_user.id)
            .order_by(SavedJob.saved_at.desc(), SavedJob.id).all())
    return render_template('saved_jobs.html', rows=rows)


@app.route('/jobseeker/applications')
@login_required
def jobseeker_applications():
    rows = (Application.query.filter_by(user_id=current_user.id)
            .order_by(Application.applied_at.desc(), Application.id).all())
    return render_template('applications.html', rows=rows)


@app.route('/jobseeker/alerts', methods=['GET', 'POST'])
@login_required
def jobseeker_alerts():
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'delete':
            alert = JobAlert.query.filter_by(
                id=request.form.get('alert_id', type=int),
                user_id=current_user.id).first()
            if alert:
                db.session.delete(alert)
                db.session.commit()
            return redirect(url_for('jobseeker_alerts'))
        term = request.form.get('term', '').strip()
        location = request.form.get('location', '').strip() or 'Anywhere'
        freq = request.form.get('frequency', 'daily')
        if term:
            db.session.add(JobAlert(user_id=current_user.id, term=term,
                                    location=location, frequency=freq,
                                    created_at=MIRROR_TS))
            db.session.commit()
        return redirect(url_for('jobseeker_alerts'))
    alerts = (JobAlert.query.filter_by(user_id=current_user.id)
              .order_by(JobAlert.id).all())
    return render_template('alerts.html', alerts=alerts)


# --------------------------------------------------------------- job actions --

@app.route('/save/<jid>', methods=['POST'])
@login_required
def save_job(jid):
    job = Job.query.filter_by(jid=jid).first_or_404()
    existing = SavedJob.query.filter_by(user_id=current_user.id,
                                        job_id=job.id).first()
    if existing:
        db.session.delete(existing)
    else:
        db.session.add(SavedJob(user_id=current_user.id, job_id=job.id,
                                saved_at=MIRROR_TS))
    db.session.commit()
    return redirect(request.form.get('next') or
                    url_for('job_detail', company=job.company.slug,
                            title=job.title_slug,
                            location=_job_url_slug(job.city, job.state),
                            jid=job.jid))


@app.route('/apply/<jid>', methods=['POST'])
@login_required
def apply_job(jid):
    job = Job.query.filter_by(jid=jid).first_or_404()
    existing = Application.query.filter_by(user_id=current_user.id,
                                           job_id=job.id).first()
    if existing:
        return redirect(url_for('jobseeker_applications'))
    app_row = Application(user_id=current_user.id, job_id=job.id,
                           applied_at=MIRROR_TS, status='Applied',
                           cover_note=request.form.get('cover_note', '').strip() or None)
    db.session.add(app_row)
    db.session.flush()
    db.session.add(ApplicationEvent(application_id=app_row.id,
                                    status='Applied',
                                    note='1-Click Application submitted',
                                    occurred_at=MIRROR_TS))
    db.session.commit()
    return redirect(url_for('apply_done', jid=job.jid))


@app.route('/apply/done/<jid>')
@login_required
def apply_done(jid):
    job = Job.query.filter_by(jid=jid).first_or_404()
    application = Application.query.filter_by(user_id=current_user.id,
                                              job_id=job.id).first()
    return render_template('apply_done.html', job=job,
                           application=application)


# --------------------------------------------------------------------- seeds --

def seed_database():
    if Job.query.count() > 0:
        return
    from seed_lib import seed_all
    seed_all(db, bcrypt, app)


def seed_benchmark_users():
    if User.query.filter_by(is_benchmark=True).count() >= 4:
        return
    from seed_lib import seed_benchmark
    seed_benchmark(db, bcrypt, app)


def main():
    with app.app_context():
        db.create_all()
        seed_database()
        seed_benchmark_users()


with app.app_context():
    db.create_all()
    if os.environ.get('ZIPRECRUITER_AUTO_SEED', '1') == '1':
        seed_database()
        seed_benchmark_users()


if __name__ == '__main__':
    main()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 40115)))
