#!/usr/bin/env python3
"""fox_sports — a WebHarbor mirror of https://www.foxsports.com/

Flask + SQLite mirror of the FOX Sports portal: league scores with full
boxscore pages (final scores, odds, leaders, FOX FACTS, event info),
division standings for the NFL and MLB plus the college football AP Top
25 poll, league schedules, team pages with next-game odds and player
news, full 53-man rosters, player stat leaders, the shows and
personalities video verticals with episode feeds, the news hub with
full story pages, NASCAR Cup standings and race schedule, UFC event
results, the betting hub with per-game odds, the FOX Super 6 free
prediction contest with graded entries and a leaderboard, search, and
the "my favs" personalization surface with four benchmark accounts.

Content comes from the tracked source_data/*.json snapshots captured
from https://www.foxsports.com/ on 2026-09-30 (see provenance.json);
the SQLite seed is materialized deterministically at image build time
(PYTHONHASHSEED=0).
"""
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
app.config["SECRET_KEY"] = os.environ.get("FOX_SPORTS_SECRET_KEY") or \
    "webharbor-fox-sports-dev-key"
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'FOX_SPORTS_DB_URI',
    f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'fox_sports.db')}")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['WTF_CSRF_TIME_LIMIT'] = None

os.makedirs(os.path.join(BASE_DIR, 'instance'), exist_ok=True)

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to continue.'
csrf = CSRFProtect(app)

MIRROR_DATE = date(2026, 9, 30)
MIRROR_TS = '2026-09-30'
SITE_NAME = 'fox_sports'
UPSTREAM = 'https://www.foxsports.com/'
# bcrypt hash of 'TestPass123!' — frozen so the seed DB is byte-reproducible.
BENCHMARK_PASSWORD_HASH = (
    '$2b$12$qSds4Mr9Wo7VwPWLhompEer88SuxxXFDp31P9etY6v7nfRctNO7B.')

LEAGUES = [('nfl', 'NFL'), ('college-football', 'College Football'),
           ('mlb', 'MLB'), ('nascar', 'NASCAR'), ('ufc', 'UFC')]
LEAGUE_NAMES = dict(LEAGUES)

GAME_RE = re.compile(r'^(.+)-game-boxscore-(\d+)$')


# ------------------------------------------------------------------- models --

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(128), unique=True, nullable=False, index=True)
    name = db.Column(db.String(128), nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    joined = db.Column(db.String(10))


class Favorite(db.Model):
    __tablename__ = 'favorites'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False,
                        index=True)
    item_type = db.Column(db.String(16), nullable=False)  # team/player/show/personality
    item_key = db.Column(db.String(96), nullable=False)
    added_at = db.Column(db.String(10))


class League(db.Model):
    __tablename__ = 'leagues'
    slug = db.Column(db.String(32), primary_key=True)
    name = db.Column(db.String(48), nullable=False)
    sport = db.Column(db.String(24))


class Team(db.Model):
    __tablename__ = 'teams'
    league = db.Column(db.String(32), nullable=False, index=True)
    slug = db.Column(db.String(96), primary_key=True)
    full_name = db.Column(db.String(96), nullable=False)
    city = db.Column(db.String(64))
    short = db.Column(db.String(48))
    logo = db.Column(db.String(255))
    division = db.Column(db.String(24))
    conference = db.Column(db.String(8))
    rank = db.Column(db.String(4))
    record = db.Column(db.String(12))
    note = db.Column(db.String(48))
    pct = db.Column(db.String(8))
    pf = db.Column(db.String(8))
    pa = db.Column(db.String(8))
    home_rec = db.Column(db.String(8))
    away_rec = db.Column(db.String(8))
    conf_rec = db.Column(db.String(8))
    div_rec = db.Column(db.String(8))
    streak = db.Column(db.String(6))
    gb = db.Column(db.String(8))
    l10 = db.Column(db.String(8))
    runs_for = db.Column(db.String(8))
    runs_against = db.Column(db.String(8))
    run_diff = db.Column(db.String(8))
    clinch = db.Column(db.String(24))
    poll_rank = db.Column(db.Integer)
    poll_votes = db.Column(db.Integer)
    poll_points = db.Column(db.Integer)
    poll_record = db.Column(db.String(8))
    poll_movement = db.Column(db.String(4))
    next_homeaway = db.Column(db.String(4))
    next_opponent = db.Column(db.String(48))
    next_day = db.Column(db.String(16))
    next_time = db.Column(db.String(16))
    next_spread = db.Column(db.String(16))
    next_total = db.Column(db.String(8))


class Game(db.Model):
    __tablename__ = 'games'
    slug = db.Column(db.String(200), primary_key=True)
    league = db.Column(db.String(32), nullable=False, index=True)
    game_id = db.Column(db.String(16))
    date = db.Column(db.String(32))
    date_iso = db.Column(db.String(10), index=True)
    week = db.Column(db.Integer)
    phase = db.Column(db.String(16))
    series = db.Column(db.String(32))
    series_game = db.Column(db.Integer)
    series_note = db.Column(db.String(64))
    away_team = db.Column(db.String(96), index=True)
    home_team = db.Column(db.String(96), index=True)
    away_record = db.Column(db.String(8))
    home_record = db.Column(db.String(8))
    status = db.Column(db.String(12), index=True)
    away_score = db.Column(db.Integer)
    home_score = db.Column(db.Integer)
    away_abbr = db.Column(db.String(4))
    home_abbr = db.Column(db.String(4))
    away_hits = db.Column(db.Integer)
    home_hits = db.Column(db.Integer)
    away_errors = db.Column(db.Integer)
    home_errors = db.Column(db.Integer)
    time = db.Column(db.String(16))
    broadcaster = db.Column(db.String(8))
    spread = db.Column(db.String(8))
    total = db.Column(db.String(8))
    away_ml = db.Column(db.String(8))
    home_ml = db.Column(db.String(8))
    venue = db.Column(db.String(96))
    venue_city = db.Column(db.String(64))
    attendance = db.Column(db.Integer)
    recap = db.Column(db.Text)
    odds_line = db.Column(db.String(16))
    innings = db.Column(db.Text)
    facts = db.Column(db.Text)
    team_stats = db.Column(db.Text)
    leaders = db.Column(db.Text)
    starting_qbs = db.Column(db.Text)
    recent_games = db.Column(db.Text)
    player_news = db.Column(db.Text)
    key_players = db.Column(db.Text)
    odds_notes = db.Column(db.Text)
    key_plays = db.Column(db.Text)
    probable_pitchers = db.Column(db.Text)
    mlb_leaders = db.Column(db.Text)

    def detail(self, field):
        raw = getattr(self, field)
        return json.loads(raw) if raw else None

    def favorite_line(self):
        """Odds the way the upstream shows them: favorite abbreviation
        with the minus spread ('PIT -2.5' / 'HOU -2.5')."""
        if not self.spread:
            return None
        abbr = self.away_abbr or (self.away_team or '?')[:3].upper()
        home_abbr = self.home_abbr or (self.home_team or '?')[:3].upper()
        if self.spread.startswith('-'):
            return f'{abbr} {self.spread}'
        return f'{home_abbr} -{self.spread[1:]}' if self.spread.startswith('+') \
            else f'{home_abbr} {self.spread}'

    def side_name(self, side, teams_by_slug):
        slug = self.away_team if side == 'away' else self.home_team
        team = teams_by_slug.get(slug)
        return team.short if team and team.short else (slug or '?')


class Player(db.Model):
    __tablename__ = 'players'
    id = db.Column(db.Integer, primary_key=True)
    league = db.Column(db.String(32), nullable=False, index=True)
    team = db.Column(db.String(96), nullable=False, index=True)
    slug = db.Column(db.String(96), nullable=False, index=True)
    name = db.Column(db.String(96), nullable=False)
    number = db.Column(db.String(4))
    group_name = db.Column(db.String(20))
    pos = db.Column(db.String(8))
    age = db.Column(db.String(4))
    height = db.Column(db.String(8))
    weight = db.Column(db.String(12))
    college = db.Column(db.String(64))


class PlayerNews(db.Model):
    __tablename__ = 'player_news'
    id = db.Column(db.Integer, primary_key=True)
    league = db.Column(db.String(32), nullable=False)
    team = db.Column(db.String(96), nullable=False, index=True)
    player = db.Column(db.String(96), nullable=False, index=True)
    headline = db.Column(db.Text, nullable=False)
    story = db.Column(db.Text)
    impact = db.Column(db.Text)
    time_ago = db.Column(db.String(24))
    source = db.Column(db.String(48))


class PlayerStat(db.Model):
    __tablename__ = 'player_stats'
    id = db.Column(db.Integer, primary_key=True)
    league = db.Column(db.String(32), nullable=False, index=True)
    label = db.Column(db.String(48), nullable=False)
    stat = db.Column(db.String(16), nullable=False)
    player = db.Column(db.String(96), nullable=False)
    team_abbr = db.Column(db.String(4))
    value = db.Column(db.String(12), nullable=False)
    rank = db.Column(db.Integer)
    is_team = db.Column(db.Boolean, default=False)


class Story(db.Model):
    __tablename__ = 'stories'
    slug = db.Column(db.String(200), primary_key=True)
    league = db.Column(db.String(32), nullable=False, index=True)
    title = db.Column(db.Text, nullable=False)
    dek = db.Column(db.Text)
    image = db.Column(db.String(255))
    published = db.Column(db.String(40))
    author = db.Column(db.String(96))
    time_ago = db.Column(db.String(24))
    source = db.Column(db.String(48))
    body = db.Column(db.Text)


class Show(db.Model):
    __tablename__ = 'shows'
    slug = db.Column(db.String(96), primary_key=True)
    title = db.Column(db.String(128), nullable=False)
    art = db.Column(db.String(255))


class Episode(db.Model):
    __tablename__ = 'episodes'
    id = db.Column(db.Integer, primary_key=True)
    show_slug = db.Column(db.String(96), nullable=False, index=True)
    title = db.Column(db.Text, nullable=False)
    time_ago = db.Column(db.String(24))
    source = db.Column(db.String(48))
    thumb = db.Column(db.String(255))


class Personality(db.Model):
    __tablename__ = 'personalities'
    slug = db.Column(db.String(96), primary_key=True)
    name = db.Column(db.String(96), nullable=False)
    role = db.Column(db.String(96))
    art = db.Column(db.String(255))


class PersonalityVideo(db.Model):
    __tablename__ = 'personality_videos'
    id = db.Column(db.Integer, primary_key=True)
    person_slug = db.Column(db.String(96), nullable=False, index=True)
    title = db.Column(db.Text, nullable=False)
    time_ago = db.Column(db.String(24))
    source = db.Column(db.String(48))
    thumb = db.Column(db.String(255))


class HomeTile(db.Model):
    __tablename__ = 'home_tiles'
    id = db.Column(db.Integer, primary_key=True)
    kind = db.Column(db.String(12), nullable=False)
    title = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text)
    image = db.Column(db.String(255))
    link = db.Column(db.String(255))
    league = db.Column(db.String(32))


class NascarDriver(db.Model):
    __tablename__ = 'nascar_drivers'
    rank = db.Column(db.Integer, primary_key=True)
    driver = db.Column(db.String(64), nullable=False)
    points = db.Column(db.Integer)
    back = db.Column(db.String(8))
    starts = db.Column(db.Integer)
    wins = db.Column(db.Integer)
    top5 = db.Column(db.Integer)
    top10 = db.Column(db.Integer)
    dnf = db.Column(db.Integer)
    stage_wins = db.Column(db.Integer)
    laps_led = db.Column(db.Integer)


class NascarRace(db.Model):
    __tablename__ = 'nascar_races'
    id = db.Column(db.Integer, primary_key=True)
    when = db.Column(db.String(24))
    name = db.Column(db.String(96), nullable=False)
    track = db.Column(db.String(64))
    city = db.Column(db.String(64))
    time = db.Column(db.String(16))
    network = db.Column(db.String(8))


class UfcEvent(db.Model):
    __tablename__ = 'ufc_events'
    id = db.Column(db.Integer, primary_key=True)
    when = db.Column(db.String(24))
    name = db.Column(db.String(128), nullable=False)
    venue = db.Column(db.String(64))
    city = db.Column(db.String(64))
    fighter1 = db.Column(db.String(48))
    result1 = db.Column(db.String(2))
    fighter2 = db.Column(db.String(48))
    result2 = db.Column(db.String(2))


class Super6Contest(db.Model):
    __tablename__ = 'super6_contests'
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(64), unique=True, nullable=False)
    title = db.Column(db.String(96), nullable=False)
    description = db.Column(db.Text)
    prize = db.Column(db.Text)
    how_to_play = db.Column(db.Text)
    deadline = db.Column(db.String(32))
    status = db.Column(db.String(16))


class Super6Question(db.Model):
    __tablename__ = 'super6_questions'
    id = db.Column(db.Integer, primary_key=True)
    contest_id = db.Column(db.Integer, db.ForeignKey('super6_contests.id'),
                           nullable=False, index=True)
    order = db.Column(db.Integer, nullable=False)
    label = db.Column(db.String(64), nullable=False)
    away_team = db.Column(db.String(96), nullable=False)
    home_team = db.Column(db.String(96), nullable=False)
    game_slug = db.Column(db.String(200))
    correct_pick = db.Column(db.String(96))


class Super6Entry(db.Model):
    __tablename__ = 'super6_entries'
    id = db.Column(db.Integer, primary_key=True)
    contest_id = db.Column(db.Integer, db.ForeignKey('super6_contests.id'),
                           nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.String(20))
    picks = db.Column(db.String(200), nullable=False)
    score = db.Column(db.Integer)
    is_fixture = db.Column(db.Boolean, default=False)


# --------------------------------------------------------------- bootstrap --

def seed_database():
    if Team.query.count() > 0:
        return
    import seed_lib
    seed_lib.seed_all(db)
    db.session.commit()


def seed_benchmark_users():
    if User.query.count() > 0:
        return
    import seed_lib
    seed_lib.seed_benchmark_users(db)
    db.session.commit()


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


def canonicalize_seed():
    """Rewrite the database file so its bytes are a pure function of the
    logical seed content. Bulk ORM inserts leave the physical index-leaf
    layout dependent on flush-time page interleaving, and the in-memory
    metadata stores index definitions in a set (so the CREATE INDEX order
    varies between processes); after seeding we therefore rebuild the file
    with a pinned schema order (tables then indexes, alphabetical; rows in
    rowid order) and swap it in place."""
    import os
    import sqlite3

    url = db.engine.url
    if url.drivername.split('+')[0] != 'sqlite' or not url.database:
        return
    path = url.database
    if not os.path.exists(path):
        return

    def lit(value):
        if value is None:
            return 'NULL'
        if isinstance(value, bool):
            return str(int(value))
        if isinstance(value, int):
            return str(value)
        if isinstance(value, float):
            return repr(value)
        if isinstance(value, bytes):
            return "X'" + value.hex() + "'"
        return "'" + str(value).replace("'", "''") + "'"

    tmp = path + '.canonical'
    src = sqlite3.connect(path)
    dst = sqlite3.connect(tmp)
    try:
        master = list(src.execute(
            "SELECT type, name, sql FROM sqlite_master WHERE sql IS NOT NULL"))
        tables = sorted((r for r in master if r[0] == 'table'
                         and r[1] != 'sqlite_sequence'), key=lambda r: r[1])
        indexes = sorted((r for r in master if r[0] == 'index'),
                         key=lambda r: r[1])
        script = ['BEGIN TRANSACTION;']
        script += [r[2] + ';' for r in tables]
        for _, name, _ in tables:
            cols = [c[1] for c in src.execute(f'PRAGMA table_info("{name}")')]
            col_sql = ', '.join(f'"{c}"' for c in cols)
            for row in src.execute(f'SELECT {col_sql} FROM "{name}" '
                                   f'ORDER BY rowid'):
                values = ', '.join(lit(v) for v in row)
                script.append(f'INSERT INTO "{name}" ({col_sql}) '
                              f'VALUES ({values});')
        script += [r[2] + ';' for r in indexes]
        script.append('COMMIT;')
        dst.executescript('\n'.join(script))
        dst.commit()
    finally:
        src.close()
        dst.close()
    os.replace(tmp, path)


def main():
    with app.app_context():
        db.create_all()
        seed_database()
        seed_benchmark_users()
        canonicalize_seed()


with app.app_context():
    db.create_all()
    seed_database()
    seed_benchmark_users()


# ------------------------------------------------------------------ helpers --

STOP_WORDS = {'the', 'a', 'an', 'in', 'on', 'at', 'to', 'for', 'of', 'and',
              'or', 'is', 'it', 'by', 'with', 'vs'}


def _tokens(query):
    return [t.lower() for t in re.split(r'\W+', query)
            if t.lower() not in STOP_WORDS and len(t) > 1]


def _score(query_tokens, text):
    hay = (text or '').lower()
    return sum(1 for t in query_tokens if t in hay)


def teams_by_slug():
    return {t.slug: t for t in Team.query.all()}


def _image(filename):
    """Only serve files recorded in the tracked inventory."""
    if not filename:
        return None
    return url_for('static', filename=f'images/upstream/{filename}')


def is_favorited(item_type, item_key):
    if not current_user.is_authenticated:
        return False
    return Favorite.query.filter_by(user_id=current_user.id,
                                    item_type=item_type,
                                    item_key=item_key).first() is not None


@app.context_processor
def inject_globals():
    leagues = [(slug, name) for slug, name in LEAGUES]
    return {
        'LEAGUES': leagues,
        'LEAGUE_NAMES': LEAGUE_NAMES,
        'current_user': current_user,
        'image': _image,
        'is_favorited': is_favorited,
    }


# -------------------------------------------------------------------- views --

@app.route('/')
def home():
    tiles = HomeTile.query.order_by(HomeTile.id).all()
    featured = [t for t in tiles if t.kind == 'story']
    moments = [t for t in tiles if t.kind == 'moment']
    live = [t for t in tiles if t.kind == 'live']
    top_games = (Game.query.filter(Game.status == 'scheduled')
                 .order_by(Game.date_iso, Game.slug).limit(6).all())
    teams = teams_by_slug()
    return render_template('home.html', featured=featured, moments=moments,
                           live=live, top_games=top_games, teams=teams,
                           image=_image)


@app.route('/_health')
def health_json():
    counts = {
        'teams': Team.query.count(),
        'games': Game.query.count(),
        'players': Player.query.count(),
        'stories': Story.query.count(),
        'shows': Show.query.count(),
    }
    return jsonify({'ok': all(v > 0 for v in counts.values()),
                    'site': SITE_NAME, 'counts': counts})


@app.route('/scores')
def scores_hub():
    boards = []
    for slug, name in LEAGUES:
        recent = (Game.query.filter_by(league=slug)
                  .order_by(Game.date_iso.desc()).limit(8).all())
        if recent:
            boards.append((slug, name, recent))
    teams = teams_by_slug()
    return render_template('scores_hub.html', boards=boards, teams=teams,
                           image=_image)


@app.route('/scores/<league>')
def scoreboard(league):
    if league not in LEAGUE_NAMES:
        abort(404)
    games = (Game.query.filter_by(league=league)
             .order_by(Game.date_iso, Game.slug).all())
    teams = teams_by_slug()
    return render_template('scoreboard.html', league=league,
                           league_name=LEAGUE_NAMES[league], games=games,
                           teams=teams, image=_image)


@app.route('/search')
def search():
    query = (request.args.get('q') or '').strip()
    results = []
    if query:
        tokens = _tokens(query)
        if tokens:
            teams = Team.query.all()
            players = Player.query.limit(4000).all()
            shows = Show.query.all()
            people = Personality.query.all()
            stories = Story.query.all()
            games = Game.query.all()
            hits = []
            for t in teams:
                s = _score(tokens, f"{t.full_name} {t.city} {t.short} {t.league}")
                if s:
                    hits.append((s, 'team', t.full_name,
                                 f'/{t.league}/{t.slug}-team', t))
            for p in players:
                s = _score(tokens, f'{p.name} {p.pos} {p.college}')
                if s:
                    hits.append((s, 'player', p.name,
                                 f'/{p.league}/{p.slug}-player', p))
            for sh in shows:
                s = _score(tokens, sh.title)
                if s:
                    hits.append((s, 'show', sh.title, f'/shows/{sh.slug}', sh))
            for per in people:
                s = _score(tokens, f'{per.name} {per.role or ""}')
                if s:
                    hits.append((s, 'personality', per.name,
                                 f'/personalities/{per.slug}', per))
            for st in stories:
                s = _score(tokens, f"{st.title} {st.dek or ''}")
                if s:
                    hits.append((s, 'story', st.title,
                                 f'/stories/{st.league}/{st.slug}', st))
            for g in games:
                label = f"{g.side_name('away', teams_by_slug())} vs " \
                        f"{g.side_name('home', teams_by_slug())} {g.date or ''}"
                s = _score(tokens, label)
                if s:
                    hits.append((s, 'game', label, f'/{g.league}/{g.slug}', g))
            from app import NascarDriver, NascarRace, UfcEvent
            for d in NascarDriver.query.all():
                s = _score(tokens, f'{d.driver} NASCAR')
                if s:
                    hits.append((s, 'nascar', f'{d.driver} — NASCAR Cup',
                                 '/nascar/cup-series/standings', d))
            for r in NascarRace.query.all():
                s = _score(tokens, f"{r.name} {r.track} NASCAR race")
                if s:
                    hits.append((s, 'race', f'{r.name} — {r.track}',
                                 '/nascar/cup-series/standings', r))
            for e in UfcEvent.query.all():
                s = _score(tokens, f'{e.name} {e.fighter1} {e.fighter2} UFC')
                if s:
                    hits.append((s, 'ufc', f'{e.name} — {e.fighter1} vs '
                                 f'{e.fighter2}', '/ufc', e))
            hits.sort(key=lambda h: (-h[0], h[2]))
            results = hits[:60]
            counts = {}
            for _, kind, *_ in results:
                counts[kind] = counts.get(kind, 0) + 1
    return render_template('search.html', query=query, results=results,
                           image=_image)


# ------------------------------------------------------------- league pages --

@app.route('/<league>')
def league_home(league):
    if league not in LEAGUE_NAMES:
        abort(404)
    teams = teams_by_slug()
    games = (Game.query.filter_by(league=league)
             .order_by(Game.date_iso.desc(), Game.slug).limit(10).all())
    stories = (Story.query.filter_by(league=league)
               .order_by(Story.published.desc()).limit(6).all())
    return render_template('league_home.html', league=league,
                           league_name=LEAGUE_NAMES[league], games=games,
                           stories=stories, teams=teams, image=_image)


@app.route('/<league>/standings')
def standings(league):
    if league not in LEAGUE_NAMES:
        abort(404)
    teams = teams_by_slug()
    if league in ('nfl', 'mlb'):
        rows = Team.query.filter_by(league=league).all()
        divisions = {}
        for t in rows:
            if t.division:
                divisions.setdefault(t.division, []).append(t)
        for div in divisions:
            divisions[div].sort(key=lambda t: int(t.rank) if t.rank and
                                 t.rank.isdigit() else 99)
        ordered = [(d, divisions[d]) for d in
                   sorted(divisions, key=lambda d: (d.split()[0], d))]
        return render_template('standings.html', league=league,
                               league_name=LEAGUE_NAMES[league],
                               divisions=ordered, teams=teams, image=_image)
    if league == 'college-football':
        poll = (Team.query.filter(Team.poll_rank.isnot(None))
                .order_by(Team.poll_rank).all())
        return render_template('poll.html', league=league,
                               league_name=LEAGUE_NAMES[league], poll=poll,
                               image=_image)
    abort(404)


@app.route('/nascar/cup-series/standings')
def nascar_standings():
    drivers = NascarDriver.query.order_by(NascarDriver.rank).all()
    races = NascarRace.query.order_by(NascarRace.id).all()
    return render_template('nascar.html', drivers=drivers, races=races)


@app.route('/nascar/drivers/<int:driver_id>')
def nascar_driver(driver_id):
    driver = db.get_or_404(NascarDriver, driver_id)
    return render_template('nascar_driver.html', driver=driver)


@app.route('/nascar')
def nascar_home():
    return redirect(url_for('nascar_standings'))


@app.route('/ufc')
def ufc_home():
    events = UfcEvent.query.order_by(UfcEvent.id).all()
    return render_template('ufc.html', events=events)


@app.route('/<league>/schedule')
def schedule(league):
    if league not in LEAGUE_NAMES or league in ('nascar', 'ufc'):
        abort(404)
    games = (Game.query.filter_by(league=league)
             .order_by(Game.date_iso, Game.slug).all())
    teams = teams_by_slug()
    return render_template('schedule.html', league=league,
                           league_name=LEAGUE_NAMES[league], games=games,
                           teams=teams, image=_image)


@app.route('/<league>/teams')
def teams_hub(league):
    if league not in LEAGUE_NAMES:
        abort(404)
    teams = Team.query.filter_by(league=league).order_by(Team.slug).all()
    return render_template('teams.html', league=league,
                           league_name=LEAGUE_NAMES[league], teams=teams,
                           image=_image)


@app.route('/<league>/players')
def stat_leaders(league):
    if league not in LEAGUE_NAMES or league in ('nascar', 'ufc'):
        abort(404)
    rows = (PlayerStat.query.filter_by(league=league, is_team=False)
            .order_by(PlayerStat.stat, PlayerStat.rank).all())
    grouped = {}
    for row in rows:
        grouped.setdefault(row.stat, []).append(row)
    team_rows = (PlayerStat.query.filter_by(league=league, is_team=True)
                 .order_by(PlayerStat.stat).all())
    player_slugs = {}
    for p in Player.query.filter_by(league=league).all():
        player_slugs.setdefault(p.name, p.slug)
    return render_template('stat_leaders.html', league=league,
                           league_name=LEAGUE_NAMES[league], grouped=grouped,
                           team_rows=team_rows,
                           player_slugs=player_slugs)


@app.route('/<league>/news')
def league_news(league):
    if league not in LEAGUE_NAMES:
        abort(404)
    stories = (Story.query.filter_by(league=league)
               .order_by(Story.published.desc()).all())
    return render_template('league_news.html', league=league,
                           league_name=LEAGUE_NAMES[league],
                           stories=stories, image=_image)


# ---------------------------------------------------- league catch-all pages --

@app.route('/<league>/<path:slug>')
def league_page(league, slug):
    if league not in LEAGUE_NAMES:
        abort(404)
    m = GAME_RE.match(slug)
    if m:
        return _boxscore(league, slug)
    if slug.endswith('-team'):
        return _team_page(league, slug[:-len('-team')])
    if slug.endswith('-team-schedule'):
        return _team_schedule(league, slug[:-len('-team-schedule')])
    if slug.endswith('-team-roster'):
        return _team_roster(league, slug[:-len('-team-roster')])
    if slug.endswith('-player'):
        return _player_page(league, slug[:-len('-player')])
    abort(404)


def _boxscore(league, slug):
    game = Game.query.filter_by(league=league, slug=slug).first_or_404()
    teams = teams_by_slug()
    away = teams.get(game.away_team)
    home = teams.get(game.home_team)
    leaders = _aligned_leaders(game.detail('leaders'))
    return render_template('boxscore.html', game=game, away=away, home=home,
                           teams=teams, leaders=leaders, image=_image)


def _aligned_leaders(rows):
    """Group the Team Leaders payload by stat label, pairing each label's
    away entry with its home entry so a side's leader always renders under
    its own team column (the raw capture order interleaves the two sides
    and must not be paired by list index)."""
    if not rows:
        return []
    labels = []
    by_side = {'away': {}, 'home': {}}
    for row in rows:
        label = row.get('label')
        if not label:
            continue
        if label not in labels:
            labels.append(label)
        side = row.get('side') if row.get('side') in by_side else 'away'
        by_side[side].setdefault(label, row)
    return [(label, by_side['away'].get(label), by_side['home'].get(label))
            for label in labels]


def _team_page(league, team_slug):
    team = Team.query.filter_by(league=league, slug=team_slug).first_or_404()
    news = (PlayerNews.query.filter_by(team=team_slug)
            .order_by(PlayerNews.id).limit(8).all())
    games = (Game.query.filter(
        (Game.away_team == team_slug) | (Game.home_team == team_slug))
        .order_by(Game.date_iso.desc()).limit(6).all())
    teams = teams_by_slug()
    return render_template('team.html', team=team, news=news, games=games,
                           teams=teams, image=_image)


def _team_schedule(league, team_slug):
    team = Team.query.filter_by(league=league, slug=team_slug).first_or_404()
    games = (Game.query.filter(
        (Game.away_team == team_slug) | (Game.home_team == team_slug))
        .order_by(Game.date_iso, Game.slug).all())
    teams = teams_by_slug()
    return render_template('team_schedule.html', team=team, games=games,
                           teams=teams, image=_image)


def _team_roster(league, team_slug):
    team = Team.query.filter_by(league=league, slug=team_slug).first_or_404()
    players = (Player.query.filter_by(league=league, team=team_slug)
               .order_by(Player.group_name, Player.slug).all())
    groups = {}
    for p in players:
        groups.setdefault(p.group_name or 'ROSTER', []).append(p)
    return render_template('roster.html', team=team, groups=groups)


def _player_page(league, player_slug):
    player = (Player.query.filter_by(league=league, slug=player_slug)
              .first_or_404())
    team = Team.query.filter_by(league=league, slug=player.team).first()
    news = (PlayerNews.query.filter_by(player=player.name)
            .order_by(PlayerNews.id).limit(6).all())
    stats = (PlayerStat.query.filter_by(league=league, player=player.name)
             .order_by(PlayerStat.stat).all())
    return render_template('player.html', player=player, team=team,
                           news=news, stats=stats)


# ------------------------------------------------------------------- stories --

@app.route('/stories')
def stories_hub():
    stories = Story.query.order_by(Story.published.desc()).limit(40).all()
    return render_template('stories_hub.html', stories=stories, image=_image)


@app.route('/stories/<league>')
def stories_league(league):
    if league not in ('nfl', 'mlb', 'college-football', 'betting'):
        abort(404)
    stories = (Story.query.filter_by(league=league)
               .order_by(Story.published.desc()).all())
    return render_template('league_news.html', league=league,
                           league_name=LEAGUE_NAMES.get(league, league.title()),
                           stories=stories, image=_image)


@app.route('/stories/<league>/<slug>')
def story_page(league, slug):
    story = Story.query.filter_by(league=league, slug=slug).first_or_404()
    related = (Story.query.filter(Story.league == league, Story.slug != slug)
               .order_by(Story.published.desc()).limit(4).all())
    return render_template('story.html', story=story, related=related,
                           image=_image)


# --------------------------------------------------------------------- shows --

@app.route('/watch')
@app.route('/live')
def watch():
    tiles = HomeTile.query.filter(HomeTile.kind.in_(['live', 'moment'])) \
        .order_by(HomeTile.id).all()
    episodes = Episode.query.order_by(Episode.id.desc()).limit(24).all()
    return render_template('watch.html', tiles=tiles, episodes=episodes,
                           image=_image)


@app.route('/shows')
def shows_hub():
    shows = Show.query.order_by(Show.slug).all()
    return render_template('shows_hub.html', shows=shows, image=_image)


@app.route('/shows/<slug>')
def show_page(slug):
    show = Show.query.filter_by(slug=slug).first_or_404()
    episodes = (Episode.query.filter_by(show_slug=slug)
                .order_by(Episode.id).all())
    return render_template('show.html', show=show, episodes=episodes,
                           image=_image)


@app.route('/personalities')
def personalities_hub():
    people = Personality.query.order_by(Personality.slug).all()
    return render_template('personalities_hub.html', people=people,
                           image=_image)


@app.route('/personalities/<slug>')
def personality_page(slug):
    person = Personality.query.filter_by(slug=slug).first_or_404()
    videos = (PersonalityVideo.query.filter_by(person_slug=slug)
              .order_by(PersonalityVideo.id).all())
    return render_template('personality.html', person=person, videos=videos,
                           image=_image)


# ------------------------------------------------------------------- betting --

@app.route('/betting')
def betting_hub():
    games = (Game.query.filter_by(status='scheduled')
             .order_by(Game.date_iso, Game.slug).all())
    stories = Story.query.filter_by(league='betting') \
        .order_by(Story.published.desc()).all()
    teams = teams_by_slug()
    return render_template('betting.html', games=games, stories=stories,
                           teams=teams, image=_image)


@app.route('/betting/<league>')
def betting_league(league):
    if league not in LEAGUE_NAMES:
        abort(404)
    games = (Game.query.filter_by(league=league, status='scheduled')
             .order_by(Game.date_iso, Game.slug).all())
    stories = Story.query.filter_by(league='betting') \
        .order_by(Story.published.desc()).limit(8).all()
    teams = teams_by_slug()
    return render_template('betting.html', games=games, stories=stories,
                           teams=teams, league=league,
                           league_name=LEAGUE_NAMES[league], image=_image)


# ------------------------------------------------------------------ super six --

@app.route('/fox-super-6')
def super6_hub():
    contests = Super6Contest.query.order_by(Super6Contest.id).all()
    my_entries = []
    if current_user.is_authenticated:
        my_entries = Super6Entry.query.filter_by(
            user_id=current_user.id).order_by(Super6Entry.id).all()
    return render_template('super6_hub.html', contests=contests,
                           my_entries=my_entries)


@app.route('/fox-super-6/<slug>/enter', methods=['GET'])
@login_required
def super6_enter(slug):
    contest = Super6Contest.query.filter_by(slug=slug).first_or_404()
    questions = (Super6Question.query.filter_by(contest_id=contest.id)
                 .order_by(Super6Question.order).all())
    teams = teams_by_slug()
    existing = Super6Entry.query.filter_by(
        contest_id=contest.id, user_id=current_user.id).first()
    return render_template('super6_enter.html', contest=contest,
                           questions=questions, teams=teams,
                           existing=existing)


@app.route('/fox-super-6/<slug>/submit', methods=['POST'])
@login_required
def super6_submit(slug):
    contest = Super6Contest.query.filter_by(slug=slug).first_or_404()
    questions = (Super6Question.query.filter_by(contest_id=contest.id)
                 .order_by(Super6Question.order).all())
    picks = []
    for q in questions:
        pick = request.form.get(f'pick-{q.order}')
        if pick not in (q.away_team, q.home_team):
            abort(400, 'Invalid pick')
        picks.append(pick)
    entry = Super6Entry.query.filter_by(
        contest_id=contest.id, user_id=current_user.id).first()
    score = sum(1 for q, p in zip(questions, picks)
                if p == q.correct_pick)
    if entry:
        entry.picks = '|'.join(picks)
        entry.score = score
    else:
        entry = Super6Entry(contest_id=contest.id, user_id=current_user.id,
                            created_at=MIRROR_TS, picks='|'.join(picks),
                            score=score)
        db.session.add(entry)
    db.session.commit()
    return redirect(url_for('super6_entry', contest_slug=slug,
                            entry_id=entry.id))


@app.route('/fox-super-6/<contest_slug>/entries/<int:entry_id>')
@login_required
def super6_entry(contest_slug, entry_id):
    entry = Super6Entry.query.filter_by(id=entry_id).first_or_404()
    contest = Super6Contest.query.filter_by(id=entry.contest_id).first_or_404()
    if entry.user_id != current_user.id:
        abort(403)
    questions = (Super6Question.query.filter_by(contest_id=contest.id)
                 .order_by(Super6Question.order).all())
    picks = entry.picks.split('|')
    teams = teams_by_slug()
    return render_template('super6_entry.html', contest=contest,
                           entry=entry, questions=questions, picks=picks,
                           teams=teams)


@app.route('/fox-super-6/<slug>/leaderboard')
def super6_leaderboard(slug):
    contest = Super6Contest.query.filter_by(slug=slug).first_or_404()
    entries = (Super6Entry.query.filter_by(contest_id=contest.id)
               .order_by(Super6Entry.score.desc(), Super6Entry.id).all())
    users = {u.id: u for u in User.query.all()}
    teams = teams_by_slug()
    return render_template('super6_leaderboard.html', contest=contest,
                           entries=entries, users=users, teams=teams)


# ----------------------------------------------------------------- accounts --

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        email = (request.form.get('email') or '').strip().lower()
        password = request.form.get('password') or ''
        user = User.query.filter_by(email=email).first()
        if user and bcrypt.check_password_hash(user.password_hash, password):
            login_user(user)
            target = local_return_url(request.args.get('next'), url_for('home'))
            return redirect(target)
        error = 'Invalid email or password.'
    return render_template('login.html', error=error)


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    error = None
    if request.method == 'POST':
        name = (request.form.get('name') or '').strip()
        email = (request.form.get('email') or '').strip().lower()
        password = request.form.get('password') or ''
        if not name or len(name) < 2:
            error = 'Please enter your name.'
        elif '@' not in email or '.' not in email.split('@')[-1]:
            error = 'Please enter a valid email address.'
        elif len(password) < 8:
            error = 'Password must be at least 8 characters.'
        elif User.query.filter_by(email=email).first():
            error = 'An account with that email already exists.'
        else:
            user = User(email=email, name=name,
                        password_hash=bcrypt.generate_password_hash(
                            password).decode('utf-8'),
                        joined=MIRROR_TS)
            db.session.add(user)
            db.session.commit()
            login_user(user)
            return redirect(url_for('favorites'))
    return render_template('signup.html', error=error)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))


@app.route('/favorites')
@login_required
def favorites():
    favs = Favorite.query.filter_by(user_id=current_user.id) \
        .order_by(Favorite.id).all()
    teams = {t.slug: t for t in Team.query.all()}
    players = {p.slug: p for p in Player.query.all()}
    shows = {s.slug: s for s in Show.query.all()}
    people = {p.slug: p for p in Personality.query.all()}
    drivers = {str(d.rank): d for d in NascarDriver.query.all()}
    return render_template('favorites.html', favorites=favs, teams=teams,
                           players=players, shows=shows, people=people, drivers=drivers,
                           image=_image)



def local_return_url(value, fallback):
    """Accept only an unambiguous local absolute path."""
    from urllib.parse import urlsplit, unquote
    if not isinstance(value, str):
        return fallback
    decoded = unquote(value)
    if not decoded.startswith('/') or decoded.startswith('//') or '\\' in decoded or any(ord(c) < 32 or ord(c) == 127 for c in decoded):
        return fallback
    parsed = urlsplit(decoded)
    return value if not parsed.scheme and not parsed.netloc else fallback

@app.route('/favorites/toggle', methods=['POST'])
@login_required
def favorites_toggle():
    item_type = request.form.get('item_type')
    item_key = request.form.get('item_key')
    if item_type not in ('team', 'player', 'show', 'personality', 'driver') or not item_key:
        abort(400, 'Invalid favorite')
    valid = {
        'team': Team.query.filter_by(slug=item_key).first(),
        'player': Player.query.filter_by(slug=item_key).first(),
        'show': Show.query.filter_by(slug=item_key).first(),
        'personality': Personality.query.filter_by(slug=item_key).first(),
        'driver': db.session.get(NascarDriver, int(item_key)) if item_key.isdigit() else None,
    }[item_type]
    if not valid:
        abort(400, 'Unknown favorite key')
    existing = Favorite.query.filter_by(user_id=current_user.id,
                                        item_type=item_type,
                                        item_key=item_key).first()
    if existing:
        db.session.delete(existing)
    else:
        db.session.add(Favorite(user_id=current_user.id, item_type=item_type,
                                item_key=item_key, added_at=MIRROR_TS))
    db.session.commit()
    return redirect(local_return_url(request.form.get('next'), url_for('favorites')))


if __name__ == '__main__':
    main()
