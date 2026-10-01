#!/usr/bin/env python3
"""university_of_michigan — a WebHarbor mirror of https://umich.edu/

Flask + SQLite mirror of the University of Michigan gateway and its
academic services: the home page with its featured stories and quick
facts, the Schools & Colleges directory, the Majors & Degrees browser
(admissions.umich.edu), the Fall 2026 course catalog with per-section
class details captured from the registrar's public class search
(csprod.dsc.umich.edu), the faculty roster derived from those sections,
the U-M Library catalog (Deep Blue repository records behind the
search.lib.umich.edu UI), Michigan News, the Happening @ Michigan events
calendar, the Office of the Registrar academic calendar, undergraduate
admissions (costs, aid, application plans and deadlines) and the campus
building directory behind maps.studentlife.umich.edu — plus the
Wolverine-Access-style Backpack, saved programs and saved events for the
four benchmark users.

Content comes from the tracked source_data/*.json snapshots captured from
umich.edu and its services on 2026-09-30 (see provenance.json); the SQLite
seed is materialized deterministically at image build time
(PYTHONHASHSEED=0).
"""
import json
import os
import re

from flask import (Flask, abort, jsonify, redirect, render_template,
                   request, session, url_for)
from flask_bcrypt import Bcrypt
from flask_login import (LoginManager, UserMixin, current_user,
                         login_required, login_user, logout_user)
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect
from markupsafe import Markup

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__, instance_path=os.path.join(BASE_DIR, 'instance'))
app.config["SECRET_KEY"] = os.environ.get("UMICH_SECRET_KEY") or "webharbor-umich-dev-key"
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'UMICH_DB_URI', f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'university_of_michigan.db')}")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['WTF_CSRF_TIME_LIMIT'] = None

os.makedirs(os.path.join(BASE_DIR, 'instance'), exist_ok=True)

db = SQLAlchemy(app)

# ---- deterministic schema creation -------------------------------------
# SQLAlchemy's create_all() emits CREATE INDEX statements in Table.indexes
# set order; that set is keyed by object identity, so the DDL order varies
# between processes and two seed builds would not be byte-identical. We
# therefore declare no index=True columns and create the indexes here in
# sorted order, with tables created in sorted-name order as well.
SCHEMA_INDEX_DDL = (
    'CREATE INDEX IF NOT EXISTS ix_academic_terms_name'
    ' ON academic_terms (name)',
    'CREATE INDEX IF NOT EXISTS ix_backpack_items_user_id'
    ' ON backpack_items (user_id)',
    'CREATE INDEX IF NOT EXISTS ix_buildings_category'
    ' ON buildings (category)',
    'CREATE INDEX IF NOT EXISTS ix_buildings_name'
    ' ON buildings (name)',
    'CREATE INDEX IF NOT EXISTS ix_calendar_entries_term'
    ' ON calendar_entries (term)',
    'CREATE INDEX IF NOT EXISTS ix_calendar_entries_ctype'
    ' ON calendar_entries (ctype)',
    'CREATE INDEX IF NOT EXISTS ix_courses_subject'
    ' ON courses (subject)',
    'CREATE INDEX IF NOT EXISTS ix_courses_school'
    ' ON courses (school)',
    'CREATE INDEX IF NOT EXISTS ix_deadlines_group'
    ' ON deadlines ("group")',
    'CREATE INDEX IF NOT EXISTS ix_event_items_type'
    ' ON event_items (type)',
    'CREATE INDEX IF NOT EXISTS ix_info_requests_email'
    ' ON info_requests (email)',
    'CREATE INDEX IF NOT EXISTS ix_instructors_school'
    ' ON instructors (school)',
    'CREATE INDEX IF NOT EXISTS ix_library_items_type'
    ' ON library_items (type)',
    'CREATE INDEX IF NOT EXISTS ix_news_articles_published'
    ' ON news_articles (published)',
    'CREATE INDEX IF NOT EXISTS ix_programs_school'
    ' ON programs (school)',
    'CREATE INDEX IF NOT EXISTS ix_saved_events_user_id'
    ' ON saved_events (user_id)',
    'CREATE INDEX IF NOT EXISTS ix_saved_programs_user_id'
    ' ON saved_programs (user_id)',
    'CREATE INDEX IF NOT EXISTS ix_sections_course_id'
    ' ON sections (course_id)',
    'CREATE INDEX IF NOT EXISTS ix_sections_instructor'
    ' ON sections (instructor)',
    'CREATE INDEX IF NOT EXISTS ix_sections_status'
    ' ON sections (status)',
)


def create_schema():
    """Create all tables and indexes in a deterministic order."""
    tables = [db.metadata.tables[name]
              for name in sorted(db.metadata.tables)]
    db.metadata.create_all(db.engine, tables=tables)
    from sqlalchemy import text as _sa_text
    with db.engine.begin() as conn:
        for stmt in SCHEMA_INDEX_DDL:
            conn.execute(_sa_text(stmt))


bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to continue.'
csrf = CSRFProtect(app)

MIRROR_TS = '2026-09-30'
SITE_NAME = 'university_of_michigan'
UPSTREAM = 'https://umich.edu/'
# bcrypt hash of 'TestPass123!' — frozen so the seed DB is byte-reproducible.
BENCHMARK_PASSWORD_HASH = (
    '$2b$12$qSds4Mr9Wo7VwPWLhompEer88SuxxXFDp31P9etY6v7nfRctNO7B.')

NEWS_CATEGORIES = [
    ('arts-culture', 'Arts & Culture'),
    ('business-economy', 'Business & Economy'),
    ('education-society', 'Education & Society'),
    ('environment', 'Environment'),
    ('health', 'Health'),
    ('international', 'International'),
    ('law-politics', 'Law & Politics'),
    ('science-technology', 'Science & Technology'),
]


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# ------------------------------------------------------------------ models --

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(128), unique=True, nullable=False)
    name = db.Column(db.String(128), nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    joined = db.Column(db.String(10))


class School(db.Model):
    __tablename__ = 'schools'
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(64), unique=True, nullable=False)
    short_name = db.Column(db.String(128), nullable=False)
    full_name = db.Column(db.String(255), nullable=False)
    url = db.Column(db.String(255))
    blurb = db.Column(db.Text)
    campus = db.Column(db.String(32))
    image = db.Column(db.String(255))

    def programs(self):
        if self.slug in ('um-dearborn', 'um-flint'):
            return []
        if self.slug == 'rackham':
            return []
        return (Program.query.filter_by(school_slug=self.slug)
                .order_by(Program.name).all())

    def course_subjects(self):
        rows = (db.session.query(Course.subject)
                .filter_by(school=self.short_name)
                .distinct().order_by(Course.subject).all())
        return [r[0] for r in rows]


class Program(db.Model):
    __tablename__ = 'programs'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    school = db.Column(db.String(255), nullable=False)
    school_slug = db.Column(db.String(64))
    submajor = db.Column(db.Boolean, nullable=False, default=False)
    sort_letter = db.Column(db.String(2), nullable=False)

    def school_short(self):
        m = re.search(r'\((LSA|SMTD|BSE)\)', self.school)
        if m:
            return m.group(1)
        return self.school


class Course(db.Model):
    __tablename__ = 'courses'
    id = db.Column(db.Integer, primary_key=True)
    subject = db.Column(db.String(12), nullable=False)
    number = db.Column(db.String(8), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    school = db.Column(db.String(255))
    description = db.Column(db.Text)
    career = db.Column(db.String(64))
    attributes = db.Column(db.Text)          # JSON list
    sections = db.relationship('Section', backref='course',
                               order_by='Section.section', lazy=True)

    def attribute_list(self):
        try:
            return json.loads(self.attributes or '[]')
        except json.JSONDecodeError:
            return []

    def code(self):
        return f"{self.subject} {self.number}"


class Section(db.Model):
    __tablename__ = 'sections'
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    class_nbr = db.Column(db.String(12), unique=True, nullable=False)
    section = db.Column(db.String(8), nullable=False)
    component = db.Column(db.String(12))
    session = db.Column(db.String(32))
    instructor = db.Column(db.String(255))
    dates = db.Column(db.String(64))
    units = db.Column(db.String(8))
    mode = db.Column(db.String(24))
    enrl_restrict = db.Column(db.String(4))
    reserved_for = db.Column(db.String(255))
    avail = db.Column(db.String(8))
    waitlist = db.Column(db.String(8))
    status = db.Column(db.String(24))
    topic = db.Column(db.Text)
    combined = db.Column(db.Boolean, nullable=False, default=False)

    def label(self):
        return f"{self.section}-{self.component}"


class Instructor(db.Model):
    __tablename__ = 'instructors'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    school = db.Column(db.String(255))
    subjects = db.Column(db.Text)            # JSON list

    def subject_list(self):
        try:
            return json.loads(self.subjects or '[]')
        except json.JSONDecodeError:
            return []

    def sections(self):
        return (Section.query.filter_by(instructor=self.name)
                .order_by(Section.class_nbr).all())


class LibraryItem(db.Model):
    __tablename__ = 'library_items'
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(64), unique=True, nullable=False)
    handle = db.Column(db.String(64))
    title = db.Column(db.Text, nullable=False)
    authors = db.Column(db.Text)             # JSON list
    date_issued = db.Column(db.String(16))
    type = db.Column(db.String(64))
    subjects = db.Column(db.Text)            # JSON list
    abstract = db.Column(db.Text)
    uri = db.Column(db.String(255))
    degree = db.Column(db.String(128))

    def author_list(self):
        try:
            return json.loads(self.authors or '[]')
        except json.JSONDecodeError:
            return []

    def subject_list(self):
        try:
            return json.loads(self.subjects or '[]')
        except json.JSONDecodeError:
            return []

    def year(self):
        return (self.date_issued or '')[:4]


class NewsArticle(db.Model):
    __tablename__ = 'news_articles'
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(128), unique=True, nullable=False)
    title = db.Column(db.Text, nullable=False)
    published = db.Column(db.String(10))
    description = db.Column(db.Text)
    author = db.Column(db.String(128))
    body = db.Column(db.Text)                # JSON list of paragraphs
    categories = db.Column(db.Text)           # JSON list
    image = db.Column(db.String(255))

    def body_list(self):
        try:
            return json.loads(self.body or '[]')
        except json.JSONDecodeError:
            return []

    def category_list(self):
        try:
            return json.loads(self.categories or '[]')
        except json.JSONDecodeError:
            return []


class EventItem(db.Model):
    __tablename__ = 'event_items'
    id = db.Column(db.Integer, primary_key=True)
    eid = db.Column(db.String(16), unique=True, nullable=False)
    name = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(64))
    presenter = db.Column(db.String(255))
    start = db.Column(db.String(40))
    end = db.Column(db.String(40))
    location_name = db.Column(db.String(255))
    street = db.Column(db.String(255))
    city = db.Column(db.String(128))
    description = db.Column(db.Text)
    image = db.Column(db.String(255))

    def when(self):
        return (self.start or '').replace('T', ' ')[:16]

    def month(self):
        return (self.start or '')[:7]


class AcademicTerm(db.Model):
    __tablename__ = 'academic_terms'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(32), nullable=False)
    academic_events = db.Column(db.Text)      # JSON list
    registration_events = db.Column(db.Text)  # JSON list

    def academic_list(self):
        try:
            return json.loads(self.academic_events or '[]')
        except json.JSONDecodeError:
            return []

    def registration_list(self):
        try:
            return json.loads(self.registration_events or '[]')
        except json.JSONDecodeError:
            return []


class CalendarEntry(db.Model):
    __tablename__ = 'calendar_entries'
    id = db.Column(db.Integer, primary_key=True)
    term = db.Column(db.String(32), nullable=False)
    ctype = db.Column(db.String(32), nullable=False)
    date_str = db.Column(db.String(128), nullable=False)
    event = db.Column(db.String(255), nullable=False)


class Building(db.Model):
    __tablename__ = 'buildings'
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(128), unique=True, nullable=False)
    name = db.Column(db.String(255), nullable=False)
    address = db.Column(db.String(255))
    city = db.Column(db.String(64))
    zip = db.Column(db.String(16))
    lat = db.Column(db.String(24))
    lng = db.Column(db.String(24))
    category = db.Column(db.String(64))
    acronym = db.Column(db.String(16))
    website = db.Column(db.String(255))
    elevator = db.Column(db.Boolean, nullable=False, default=False)
    ramp = db.Column(db.Boolean, nullable=False, default=False)


class TuitionRow(db.Model):
    __tablename__ = 'tuition_rows'
    id = db.Column(db.Integer, primary_key=True)
    residency = db.Column(db.String(64), nullable=False)
    level = db.Column(db.String(64), nullable=False)
    tuition_fees = db.Column(db.Integer, nullable=False)
    living = db.Column(db.Integer, nullable=False)
    books = db.Column(db.Integer, nullable=False)
    transport = db.Column(db.Integer, nullable=False)
    personal = db.Column(db.Integer, nullable=False)
    total = db.Column(db.Integer, nullable=False)


class Deadline(db.Model):
    __tablename__ = 'deadlines'
    id = db.Column(db.Integer, primary_key=True)
    group = db.Column(db.String(24), nullable=False)
    date = db.Column(db.String(16), nullable=False)
    items = db.Column(db.Text)               # JSON list

    def item_list(self):
        try:
            return json.loads(self.items or '[]')
        except json.JSONDecodeError:
            return []


class AppPlan(db.Model):
    __tablename__ = 'app_plans'
    id = db.Column(db.Integer, primary_key=True)
    plan = db.Column(db.String(64), nullable=False)
    binding = db.Column(db.Boolean, nullable=False, default=False)
    deadline = db.Column(db.String(32))
    aid_deadline = db.Column(db.String(32))
    decision = db.Column(db.String(32))
    commit = db.Column(db.String(32))


class BackpackItem(db.Model):
    __tablename__ = 'backpack_items'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    section_id = db.Column(db.Integer, db.ForeignKey('sections.id'), nullable=False)
    added_at = db.Column(db.String(10))


class SavedProgram(db.Model):
    __tablename__ = 'saved_programs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    program_id = db.Column(db.Integer, db.ForeignKey('programs.id'), nullable=False)
    added_at = db.Column(db.String(10))


class SavedEvent(db.Model):
    __tablename__ = 'saved_events'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey('event_items.id'), nullable=False)
    added_at = db.Column(db.String(10))


class InfoRequest(db.Model):
    __tablename__ = 'info_requests'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    email = db.Column(db.String(128), nullable=False)
    audience = db.Column(db.String(64), nullable=False)
    message = db.Column(db.Text)
    created = db.Column(db.String(10), nullable=False)


# ------------------------------------------------------------------- helpers --

def _load_source(name):
    path = os.path.join(BASE_DIR, 'source_data', name)
    if not os.path.exists(path):
        return None
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def _home_facts():
    data = _load_source('home_content.json') or {}
    return data


def fmt_money(n):
    return f"${n:,}"


def fmt_when(start):
    if not start:
        return ''
    d, t = start.replace('T', ' ').split(' ') if 'T' in start else (start, '')
    return f"{d} {t[:5]}".strip()


def plural(n, word):
    return f"{n} {word}{'s' if n != 1 else ''}"


app.jinja_env.globals.update(fmt_when=fmt_when, fmt_money=fmt_money,
                             plural=plural)


# ------------------------------------------------------------------- routes --

@app.route('/')
def home():
    facts = _home_facts()
    stories = facts.get('featured_stories', [])
    # Resolve each featured story's upstream news.umich.edu link to the
    # mirrored article when one exists. Mirror article slugs are truncated
    # versions of the upstream slugs, so the old template-side slug
    # extraction produced /news/<upstream-slug> routes that 404'd. Stories
    # without a mirrored article keep their upstream URL (external link,
    # same honest shape as the school-website links).
    for s in stories:
        s['article_slug'] = None
        link = s.get('link') or ''
        if link.startswith('https://news.umich.edu/'):
            upstream_slug = link.rstrip('/').split('/')[-1]
            # longest mirror slug that is a prefix of the upstream slug
            best = None
            for a in NewsArticle.query.all():
                if upstream_slug.startswith(a.slug) and (best is None
                                                        or len(a.slug) > len(best)):
                    best = a.slug
            s['article_slug'] = best
    news = NewsArticle.query.order_by(NewsArticle.published.desc()).limit(5).all()
    events = (EventItem.query.filter(EventItem.start.like('2026-10%'))
              .order_by(EventItem.start).limit(5).all())
    return render_template('home.html', stories=stories,
                           quick_facts=facts.get('quick_facts', []),
                           mission=facts.get('mission', ''),
                           upcoming=events, news=news)


@app.route('/_health')
def health():
    return {"ok": True, "site": SITE_NAME}


# ------------------------------------------------------------- schools ----

@app.route('/schools-colleges')
def schools():
    campus = request.args.get('campus')
    q = School.query.order_by(School.short_name)
    if campus:
        q = q.filter_by(campus=campus)
    rows = q.all()
    campuses = [r[0] for r in db.session.query(School.campus).distinct().all()]
    return render_template('schools.html', schools=rows,
                           campus=campus, campuses=sorted(c for c in campuses if c),
                           count=len(rows))


@app.route('/schools-colleges/<slug>')
def school_detail(slug):
    school = School.query.filter_by(slug=slug).first_or_404()
    programs = school.programs()
    subjects = (db.session.query(Course.subject)
               .filter(Course.school == school.short_name)
               .distinct().order_by(Course.subject).all())
    subject_list = [s[0] for s in subjects]
    return render_template('school_detail.html', school=school,
                           programs=programs, subjects=subject_list)


# ------------------------------------------------------------ programs ----

PROGRAM_LETTERS = [('a-f', 'AF'), ('g-l', 'GL'), ('m-r', 'MR'), ('s-z', 'SZ')]


@app.route('/programs')
def programs():
    q = (request.args.get('q') or '').strip()
    school = (request.args.get('school') or '').strip()
    letter = (request.args.get('letter') or '').strip()
    page = max(int(request.args.get('page', 1)), 1)
    query = Program.query
    if q:
        query = query.filter(Program.name.ilike(f'%{q}%'))
    if school:
        query = query.filter(Program.school == school)
    if letter in ('a-f', 'g-l', 'm-r', 's-z'):
        lo, hi = dict(PROGRAM_LETTERS)[letter]
        query = query.filter(Program.sort_letter >= lo[0].lower(),
                             Program.sort_letter <= hi[0].lower())
    total = query.count()
    per_page = 40
    rows = (query.order_by(Program.name)
            .offset((page - 1) * per_page).limit(per_page).all())
    schools = [r[0] for r in db.session.query(Program.school).distinct().order_by(Program.school).all()]
    return render_template('programs.html', programs=rows, total=total,
                           q=q, school=school, letter=letter,
                           schools=schools, page=page,
                           per_page=per_page,
                           letters=[l for l, _ in PROGRAM_LETTERS])


@app.route('/programs/<int:pid>')
def program_detail(pid):
    program = db.session.get(Program, pid) or Program.query.filter_by(id=pid).first_or_404()
    # program.school carries unit suffixes for shared-college listings
    # (e.g. 'College of Literature, Science, and the Arts (LSA)') that the
    # schools table full_name never has, so resolve the school by its slug
    # first and only fall back to the exact full-name match.
    school = None
    if program.school_slug:
        school = School.query.filter_by(slug=program.school_slug).first()
    if school is None:
        school = School.query.filter_by(full_name=program.school).first()
    return render_template('program_detail.html', program=program, school=school)


# ------------------------------------------------------------- courses ----

@app.route('/courses')
def courses():
    q = (request.args.get('q') or '').strip()
    school = (request.args.get('school') or '').strip()
    query = Course.query
    if q:
        like = f'%{q}%'
        query = query.filter(db.or_(Course.title.ilike(like),
                                   Course.subject.ilike(like),
                                   Course.number.ilike(like),
                                   Course.description.ilike(like)))
    if school:
        query = query.filter(Course.school == school)
    rows = query.order_by(Course.subject, Course.number).all()
    schools = [r[0] for r in db.session.query(Course.school).distinct().order_by(Course.school).all() if r[0]]
    # group by subject for the browse view
    by_subject = {}
    for c in rows:
        by_subject.setdefault(c.subject, []).append(c)
    return render_template('courses.html', by_subject=by_subject,
                           total=len(rows), q=q, school=school,
                           schools=schools,
                           subjects=sorted(by_subject.keys()))


@app.route('/courses/subject/<code>')
def course_subject(code):
    subject = code.upper()
    rows = (Course.query.filter_by(subject=subject)
            .order_by(Course.number).all())
    if not rows:
        abort(404)
    school = rows[0].school
    return render_template('course_subject.html', subject=subject,
                           school=school, courses=rows)


@app.route('/courses/class/<nbr>')
def class_detail(nbr):
    sec = Section.query.filter_by(class_nbr=str(nbr)).first_or_404()
    course = db.session.get(Course, sec.course_id)
    instructor = Instructor.query.filter_by(name=sec.instructor).first()
    in_backpack = False
    if current_user.is_authenticated:
        in_backpack = BackpackItem.query.filter_by(
            user_id=current_user.id, section_id=sec.id).first() is not None
    return render_template('class_detail.html', section=sec, course=course,
                           instructor=instructor, in_backpack=in_backpack)


# ------------------------------------------------------------- faculty ----

@app.route('/faculty')
def faculty():
    q = (request.args.get('q') or '').strip()
    school = (request.args.get('school') or '').strip()
    subject = (request.args.get('subject') or '').strip()
    page = max(int(request.args.get('page', 1)), 1)
    query = Instructor.query
    if q:
        query = query.filter(Instructor.name.ilike(f'%{q}%'))
    if school:
        query = query.filter(Instructor.school == school)
    if subject:
        query = query.filter(Instructor.subjects.ilike(f'%"{subject}"%'))
    total = query.count()
    per_page = 30
    rows = (query.order_by(Instructor.name)
            .offset((page - 1) * per_page).limit(per_page).all())
    schools = [r[0] for r in db.session.query(Instructor.school).distinct().order_by(Instructor.school).all() if r[0]]
    subjects = sorted({s for r in rows for s in r.subject_list()})
    return render_template('faculty.html', faculty=rows, total=total,
                           q=q, school=school, subject=subject,
                           schools=schools, subjects=subjects,
                           page=page, per_page=per_page)


@app.route('/faculty/<int:fid>')
def faculty_detail(fid):
    person = db.session.get(Instructor, fid) or Instructor.query.filter_by(id=fid).first_or_404()
    secs = person.sections()
    course_ids = {s.course_id for s in secs}
    courses = {cid: db.session.get(Course, cid) for cid in course_ids}
    return render_template('faculty_detail.html', person=person,
                           sections=secs, courses=courses)


# ------------------------------------------------------------ library ----

@app.route('/library')
def library():
    q = (request.args.get('q') or '').strip()
    itype = (request.args.get('type') or '').strip()
    year = (request.args.get('year') or '').strip()
    page = max(int(request.args.get('page', 1)), 1)
    query = LibraryItem.query
    if q:
        like = f'%{q}%'
        query = query.filter(db.or_(LibraryItem.title.ilike(like),
                                    LibraryItem.abstract.ilike(like),
                                    LibraryItem.authors.ilike(like)))
    if itype:
        query = query.filter_by(type=itype)
    if year:
        query = query.filter(LibraryItem.date_issued.ilike(f'{year}%'))
    total = query.count()
    per_page = 25
    rows = (query.order_by(LibraryItem.title)
            .offset((page - 1) * per_page).limit(per_page).all())
    types = [r[0] for r in db.session.query(LibraryItem.type).distinct().order_by(LibraryItem.type).all() if r[0]]
    years = sorted({(r.date_issued or '')[:4] for r in LibraryItem.query.all() if r.date_issued}, reverse=True)
    return render_template('library.html', items=rows, total=total,
                           q=q, itype=itype, year=year, types=types,
                           years=years, page=page, per_page=per_page)


@app.route('/library/item/<uuid>')
def library_item(uuid):
    item = LibraryItem.query.filter_by(uuid=uuid).first_or_404()
    return render_template('library_item.html', item=item)


# --------------------------------------------------------------- news ----

@app.route('/news')
def news():
    cat = request.args.get('category')
    page = max(int(request.args.get('page', 1)), 1)
    query = NewsArticle.query
    if cat:
        query = query.filter(NewsArticle.categories.ilike(f'%"{cat}"%'))
    total = query.count()
    per_page = 12
    rows = (query.order_by(NewsArticle.published.desc())
            .offset((page - 1) * per_page).limit(per_page).all())
    counts = {}
    for key, label in NEWS_CATEGORIES:
        counts[key] = NewsArticle.query.filter(
            NewsArticle.categories.ilike(f'%"{key}"%')).count()
    return render_template('news.html', articles=rows, total=total,
                           categories=NEWS_CATEGORIES, cat=cat,
                           counts=counts, page=page, per_page=per_page)


@app.route('/news/category/<cat>')
def news_category(cat):
    return redirect(url_for('news', category=cat))


@app.route('/news/<slug>')
def news_article(slug):
    article = NewsArticle.query.filter_by(slug=slug).first_or_404()
    return render_template('news_article.html', article=article,
                           categories=NEWS_CATEGORIES)


# ------------------------------------------------------------- events ----

@app.route('/events')
def events():
    q = (request.args.get('q') or '').strip()
    etype = (request.args.get('type') or '').strip()
    presenter = (request.args.get('presenter') or '').strip()
    month = (request.args.get('month') or '').strip()
    query = EventItem.query
    if q:
        query = query.filter(EventItem.name.ilike(f'%{q}%'))
    if etype:
        query = query.filter_by(type=etype)
    if presenter:
        query = query.filter(EventItem.presenter.ilike(f'%{presenter}%'))
    if month:
        query = query.filter(EventItem.start.like(f'{month}%'))
    rows = query.order_by(EventItem.start).all()
    types = [r[0] for r in db.session.query(EventItem.type).distinct().order_by(EventItem.type).all() if r[0]]
    months = sorted({(r.start or '')[:7] for r in EventItem.query.all() if r.start})
    return render_template('events.html', events=rows, total=len(rows),
                           q=q, etype=etype, presenter=presenter,
                           month=month, types=types, months=months)


@app.route('/events/<eid>')
def event_detail(eid):
    item = EventItem.query.filter_by(eid=str(eid)).first_or_404()
    saved = False
    if current_user.is_authenticated:
        saved = SavedEvent.query.filter_by(
            user_id=current_user.id, event_id=item.id).first() is not None
    return render_template('event_detail.html', event=item, saved=saved)


# ----------------------------------------------------------- calendars ----

@app.route('/calendars')
def calendars():
    term = request.args.get('term')
    ctype = request.args.get('type')
    terms = [r.name for r in AcademicTerm.query.order_by(AcademicTerm.id).all()]
    if not term and terms:
        term = 'Fall 2026' if 'Fall 2026' in terms else terms[-1]
    block = AcademicTerm.query.filter_by(name=term).first()
    entries = []
    if block:
        query = CalendarEntry.query.filter_by(term=term)
        if ctype:
            query = query.filter_by(ctype=ctype)
        entries = query.order_by(CalendarEntry.id).all()
    return render_template('calendars.html', terms=terms, term=term,
                           ctype=ctype, entries=entries,
                           types=['Academic Calendar', 'Registration Deadlines'])


# ---------------------------------------------------------- admissions ----

@app.route('/admissions')
def admissions():
    return render_template('admissions.html')


@app.route('/admissions/costs')
def admissions_costs():
    rows = TuitionRow.query.order_by(TuitionRow.residency, TuitionRow.level).all()
    return render_template('admissions_costs.html', rows=rows)


@app.route('/admissions/aid')
def admissions_aid():
    aid = Deadline.query.filter_by(group='aid').order_by(Deadline.id).all()
    return render_template('admissions_aid.html', aid=aid)


@app.route('/admissions/apply')
def admissions_apply():
    plans = AppPlan.query.order_by(AppPlan.id).all()
    deadlines = Deadline.query.filter_by(group='application').order_by(Deadline.id).all()
    units = _load_source('admissions_units.json') or {}
    return render_template('admissions_apply.html', plans=plans,
                           deadlines=deadlines, units=units)


@app.route('/admissions/request-info', methods=['GET', 'POST'])
def request_info():
    if request.method == 'GET':
        return render_template('request_info.html')
    name = (request.form.get('name') or '').strip()
    email = (request.form.get('email') or '').strip()
    audience = (request.form.get('audience') or '').strip()
    message = (request.form.get('message') or '').strip()
    if not name or '@' not in email or not audience:
        return render_template('request_info.html',
                               error='Enter your full name, a valid email and '
                                     'choose the audience that describes you.')
    db.session.add(InfoRequest(name=name, email=email, audience=audience,
                               message=message, created=MIRROR_TS))
    db.session.commit()
    return redirect(url_for('request_info_done', name=name))


@app.route('/admissions/request-info/thanks')
def request_info_done():
    name = request.args.get('name', '')
    latest = InfoRequest.query.order_by(InfoRequest.id.desc()).first()
    return render_template('request_info_done.html', name=name or (latest.name if latest else ''))


# ----------------------------------------------------------------- map ----

@app.route('/map')
def campus_map():
    q = (request.args.get('q') or '').strip()
    category = (request.args.get('category') or '').strip()
    query = Building.query
    if q:
        like = f'%{q}%'
        query = query.filter(db.or_(Building.name.ilike(like),
                                    Building.address.ilike(like),
                                    Building.acronym.ilike(like)))
    if category:
        query = query.filter_by(category=category)
    rows = query.order_by(Building.name).all()
    categories = [r[0] for r in db.session.query(Building.category).distinct().order_by(Building.category).all() if r[0]]
    return render_template('map.html', buildings=rows, total=len(rows),
                           q=q, category=category, categories=categories)


@app.route('/map/building/<slug>')
def building_detail(slug):
    building = Building.query.filter_by(slug=slug).first_or_404()
    return render_template('building_detail.html', building=building)


# --------------------------------------------------------- site search ----

@app.route('/search')
def search():
    q = (request.args.get('q') or '').strip()
    results = []
    if q:
        like = f'%{q}%'
        for c in Course.query.filter(db.or_(Course.title.ilike(like),
                                            Course.subject.ilike(like))).limit(8):
            results.append(('Course', c.code() + ' — ' + c.title,
                            url_for('course_subject', code=c.subject)))
        for p in Program.query.filter(Program.name.ilike(like)).limit(8):
            results.append(('Program', p.name, url_for('programs', q=p.name)))
        for a in NewsArticle.query.filter(db.or_(NewsArticle.title.ilike(like),
                                                  NewsArticle.description.ilike(like))).limit(8):
            results.append(('News', a.title, url_for('news_article', slug=a.slug)))
        for e in EventItem.query.filter(db.or_(EventItem.name.ilike(like),
                                               EventItem.description.ilike(like))).limit(8):
            results.append(('Event', e.name, url_for('event_detail', eid=e.eid)))
        for i in Instructor.query.filter(Instructor.name.ilike(like)).limit(6):
            results.append(('Faculty', i.name, url_for('faculty_detail', fid=i.id)))
        for b in Building.query.filter(Building.name.ilike(like)).limit(6):
            results.append(('Building', b.name, url_for('building_detail', slug=b.slug)))
        for l in LibraryItem.query.filter(LibraryItem.title.ilike(like)).limit(6):
            results.append(('Library', l.title, url_for('library_item', uuid=l.uuid)))
    return render_template('search.html', q=q, results=results)


# ------------------------------------------------------ account / my U-M --

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
        if target and target.startswith('/'):
            return redirect(target)
        return redirect(url_for('home'))
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


@app.route('/myumich')
@login_required
def myumich():
    backpack = (BackpackItem.query.filter_by(user_id=current_user.id)
                .order_by(BackpackItem.id).all())
    sections = {b.section_id: db.session.get(Section, b.section_id) for b in backpack}
    courses = {s.course_id: db.session.get(Course, s.course_id)
               for s in sections.values() if s}
    saved_programs = (SavedProgram.query.filter_by(user_id=current_user.id)
                      .order_by(SavedProgram.id).all())
    programs = {p.program_id: db.session.get(Program, p.program_id) for p in saved_programs}
    saved_events = (SavedEvent.query.filter_by(user_id=current_user.id)
                    .order_by(SavedEvent.id).all())
    events = {e.event_id: db.session.get(EventItem, e.event_id) for e in saved_events}
    requests_ = (InfoRequest.query.filter_by(email=current_user.email)
                 .order_by(InfoRequest.id).all())
    return render_template('myumich.html', backpack=backpack,
                           sections=sections, courses=courses,
                           saved_programs=saved_programs, programs=programs,
                           saved_events=saved_events, events=events,
                           info_requests=requests_)


@app.route('/backpack/toggle/<int:section_id>', methods=['POST'])
@login_required
def backpack_toggle(section_id):
    sec = db.session.get(Section, section_id)
    if not sec:
        abort(404)
    existing = BackpackItem.query.filter_by(
        user_id=current_user.id, section_id=section_id).first()
    if existing:
        db.session.delete(existing)
        db.session.commit()
        return redirect(url_for('class_detail', nbr=sec.class_nbr))
    db.session.add(BackpackItem(user_id=current_user.id,
                                section_id=section_id, added_at=MIRROR_TS))
    db.session.commit()
    return redirect(url_for('class_detail', nbr=sec.class_nbr))


@app.route('/programs/save/<int:program_id>', methods=['POST'])
@login_required
def program_save(program_id):
    prog = db.session.get(Program, program_id)
    if not prog:
        abort(404)
    existing = SavedProgram.query.filter_by(
        user_id=current_user.id, program_id=program_id).first()
    if not existing:
        db.session.add(SavedProgram(user_id=current_user.id,
                                    program_id=program_id, added_at=MIRROR_TS))
        db.session.commit()
    return redirect(url_for('program_detail', pid=program_id))


@app.route('/events/save/<eid>', methods=['POST'])
@login_required
def event_save(eid):
    item = EventItem.query.filter_by(eid=str(eid)).first()
    if not item:
        abort(404)
    existing = SavedEvent.query.filter_by(
        user_id=current_user.id, event_id=item.id).first()
    if not existing:
        db.session.add(SavedEvent(user_id=current_user.id,
                                  event_id=item.id, added_at=MIRROR_TS))
        db.session.commit()
    return redirect(url_for('event_detail', eid=eid))


# ---------------------------------------------------------- error pages --

@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404


# ------------------------------------------------------------------ seeds --

def seed_database():
    if School.query.count() > 0:
        return
    from seed_lib import seed_all
    seed_all(db)


def seed_benchmark_users():
    from seed_lib import seed_benchmark_users as _s
    _s(db)


def main():
    with app.app_context():
        create_schema()
        seed_database()
        seed_benchmark_users()


with app.app_context():
    create_schema()
    if os.environ.get('UMICH_AUTO_SEED', '1') == '1':
        seed_database()
        seed_benchmark_users()


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
