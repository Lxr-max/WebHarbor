"""Statista (statista.com) mirror — Flask application.

Mirrors https://www.statista.com/ as served on 2026-09-26: the homepage
(hero search, trending statistics slider, topic directory, industry
directory, Market Insights strip, account pricing), the search results
page (scored token-overlap search with content-type filters), statistics
and forecast detail pages (breadcrumb, meta bar, switchable line / bar /
table chart, summary, description, sources, citations), topic pages
(editor's picks, recommended statistics grouped by segment, key insights,
key figures, related topics), report/study pages (report details, table of
contents, recommended statistics), the industry overview and industry
pages, the Market Insights (outlook) segment and market forecast pages
(highlights, definitions, analyst opinion), the recent content lists, and
the account domain (register, login, favorites, download history).

All runtime data lives in instance/statista.db (see seed_data.py, which
loads the tracked source_data/ snapshots captured from the live site).
Heavy imagery lives under static/images/ (HF-managed asset bundle).
"""
from __future__ import annotations

import json
import math
import os
import re
from datetime import datetime

from flask import (Flask, abort, flash, jsonify, redirect, render_template,
                   request, Response, url_for)
from flask_bcrypt import Bcrypt
from flask_login import (LoginManager, current_user, login_required,
                         login_user, logout_user)
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import event

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "STATISTA_DB_PATH", f"sqlite:///{BASE_DIR}/instance/statista.db")
app.config["SECRET_KEY"] = "webharbor-statista-dev-key"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message = ""

# The mirror pins "now" to the capture date so relative statements
# ("updated today", "this week") stay deterministic.
MIRROR_NOW = datetime(2026, 9, 26, 12, 0)

STOP_WORDS = {
    "the", "a", "an", "in", "on", "at", "to", "for", "of", "and", "or",
    "is", "it", "by", "with", "from", "as", "that", "this", "are", "be",
    "was", "were", "how", "what", "which", "who", "when", "where", "why",
    "do", "does", "did", "can", "could", "should", "would", "will", "has",
    "have", "had", "number", "statistics", "statistic", "data", "statista",
}


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(200), unique=True, nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    display_name = db.Column(db.String(120), nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    account_type = db.Column(db.String(20), default="Basic")
    company = db.Column(db.String(160), default="")
    created_at = db.Column(db.DateTime, default=MIRROR_NOW)

    favorites = db.relationship("Favorite", backref="user",
                                cascade="all, delete-orphan",
                                order_by="Favorite.created_at.desc()")
    downloads = db.relationship("DownloadEvent", backref="user",
                                cascade="all, delete-orphan",
                                order_by="DownloadEvent.created_at.desc()")

    # Account tiers as on the upstream pricing page: Basic sees free
    # statistics only; Starter/Personal add premium statistics; Professional
    # adds report downloads.
    @property
    def can_view_premium(self):
        return self.account_type in ("Starter", "Personal", "Professional")

    @property
    def can_download_reports(self):
        return self.account_type == "Professional"

    def check_password(self, raw: str) -> bool:
        try:
            return bcrypt.check_password_hash(self.password_hash, raw)
        except Exception:  # noqa: BLE001
            return False

    # flask-login protocol
    @property
    def is_active(self):
        return True

    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.id)


class Statistic(db.Model):
    __tablename__ = "statistics"
    id = db.Column(db.Integer, primary_key=True)      # upstream statista id
    slug = db.Column(db.String(200), nullable=False)
    title = db.Column(db.String(300), nullable=False)
    value_label = db.Column(db.String(200), default="")
    content_type = db.Column(db.String(20), default="statistic")  # statistic | forecast
    region = db.Column(db.String(120), default="Worldwide")
    last_update = db.Column(db.String(40), default="")
    release_date = db.Column(db.String(60), default="")
    survey_period = db.Column(db.String(120), default="")
    publisher = db.Column(db.String(160), default="Statista Research Department")
    source = db.Column(db.String(400), default="")
    details = db.Column(db.String(200), default="")
    summary = db.Column(db.Text, default="")
    description = db.Column(db.Text, default="")
    premium = db.Column(db.Boolean, default=False)
    chart_type = db.Column(db.String(20), default="line")   # line | bar
    points_json = db.Column(db.Text, default="")            # [[x, y], ...]
    table_json = db.Column(db.Text, default="")              # [[header,...], ...]
    topic_id = db.Column(db.Integer)
    industry_slug = db.Column(db.String(120), default="")
    breadcrumb_json = db.Column(db.Text, default="")
    related_json = db.Column(db.Text, default="")
    has_thumb = db.Column(db.Boolean, default=False)
    has_hero = db.Column(db.Boolean, default=False)

    # NOTE: this table's two indexes (ix_statistics_topic,
    # ix_statistics_content_type) are deliberately NOT declared here as
    # Index() entries. db.create_all() emits a table's indexes by iterating
    # Table.indexes — a set ordered by ASLR-dependent object hashes — so a
    # model declaration made fresh seed builds flip between two byte layouts
    # of the seed database (identical schema/rows, different index creation
    # order). They are created in a fixed order by the after_create hook
    # below instead, which pins the seed to a single byte-identical layout
    # (seed md5 d6302969…, byte-reproducible across rebuilds).

    @property
    def points(self):
        if not self.points_json:
            return []
        try:
            return json.loads(self.points_json)
        except ValueError:
            return []

    @property
    def table(self):
        if not self.table_json:
            return []
        try:
            return json.loads(self.table_json)
        except ValueError:
            return []

    @property
    def breadcrumb(self):
        if not self.breadcrumb_json:
            return []
        try:
            return json.loads(self.breadcrumb_json)
        except ValueError:
            return []

    @property
    def related_ids(self):
        if not self.related_json:
            return []
        try:
            return json.loads(self.related_json)
        except ValueError:
            return []

    @property
    def url_kind(self):
        return "forecasts" if self.content_type == "forecast" else "statistics"

    @property
    def type_label(self):
        if self.content_type == "forecast":
            return "Market Insights" if self.premium else "Forecast"
        return "Premium Statistic" if self.premium else "Statistic"

    def visible_to(self, user):
        return (not self.premium) or (user is not None and user.can_view_premium)

    def search_blob(self):
        parts = [self.title, self.value_label, self.region, self.source,
                 self.summary or "", self.description or "",
                 self.slug.replace("-", " ")]
        return " ".join(p for p in parts if p)


@event.listens_for(Statistic.__table__, "after_create")
def _create_statistics_indexes(target, connection, **kw):
    """Create the statistics indexes in a fixed, ASLR-independent order.

    SQLAlchemy's create_all() emits a table's indexes by iterating
    Table.indexes, a set whose order follows object-identity hashes and
    therefore the process address-space layout; PYTHONHASHSEED=0 does not
    constrain it. Declaring these two indexes on the model made fresh seed
    builds randomly produce one of two byte layouts (index creation order
    swapped, seed md5 d6302969… vs 7b44fe5d…). Creating them here, right
    after the statistics table and before any other table is created, in
    this fixed order with the exact DDL text create_all() used to emit,
    keeps the seed byte-identical across rebuilds (schema digest
    1dbeea05… unchanged). The hook only fires when the table itself is
    being created, so re-running the bootstrap on an existing database
    stays a no-op (byte-identical reset contract).
    """
    for ddl in (
        "CREATE INDEX ix_statistics_topic ON statistics (topic_id)",
        "CREATE INDEX ix_statistics_content_type ON statistics (content_type)",
    ):
        connection.exec_driver_sql(ddl)


class Topic(db.Model):
    __tablename__ = "topics"
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(200), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default="")
    published_by = db.Column(db.String(160), default="")
    published_date = db.Column(db.String(40), default="")
    editor_picks_json = db.Column(db.Text, default="")    # [stat_id, ...]
    recommended_json = db.Column(db.Text, default="")     # [stat_id, ...]
    segments_json = db.Column(db.Text, default="")         # {segment: [stat_id,...]}
    key_insights_json = db.Column(db.Text, default="")     # [label, value, ...]
    key_figures_json = db.Column(db.Text, default="")      # [line, ...]
    related_topics_json = db.Column(db.Text, default="")   # [name, ...]
    report_id = db.Column(db.Integer)

    @property
    def editor_picks(self):
        try:
            return json.loads(self.editor_picks_json or "[]")
        except ValueError:
            return []

    @property
    def recommended(self):
        try:
            return json.loads(self.recommended_json or "[]")
        except ValueError:
            return []

    @property
    def segments(self):
        try:
            return json.loads(self.segments_json or "{}")
        except ValueError:
            return {}

    @property
    def key_insights(self):
        try:
            return json.loads(self.key_insights_json or "[]")
        except ValueError:
            return []

    @property
    def key_figures(self):
        try:
            return json.loads(self.key_figures_json or "[]")
        except ValueError:
            return []

    @property
    def related_topics(self):
        try:
            return json.loads(self.related_topics_json or "[]")
        except ValueError:
            return []


class Report(db.Model):
    __tablename__ = "reports"
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(200), nullable=False)
    title = db.Column(db.String(300), nullable=False)
    subtitle = db.Column(db.String(300), default="")
    description = db.Column(db.Text, default="")
    details_json = db.Column(db.Text, default="")   # {Pages: ..., Format: ...}
    toc_json = db.Column(db.Text, default="")       # [chapter, ...]
    stat_ids_json = db.Column(db.Text, default="")  # [stat_id, ...]
    has_cover = db.Column(db.Boolean, default=False)
    price = db.Column(db.String(60), default="")

    @property
    def details(self):
        try:
            return json.loads(self.details_json or "{}")
        except ValueError:
            return {}

    @property
    def toc(self):
        try:
            return json.loads(self.toc_json or "[]")
        except ValueError:
            return []

    @property
    def stat_ids(self):
        try:
            return json.loads(self.stat_ids_json or "[]")
        except ValueError:
            return []

    @property
    def page_count(self):
        pages = self.details.get("Pages", "")
        m = re.search(r"(\d+)", pages)
        return int(m.group(1)) if m else None


class Industry(db.Model):
    __tablename__ = "industries"
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(120), nullable=False)
    name = db.Column(db.String(160), nullable=False)
    subs_json = db.Column(db.Text, default="")      # [{id, slug, name}, ...]
    trending_json = db.Column(db.Text, default="")  # [stat_id, ...]
    definition = db.Column(db.Text, default="")

    @property
    def subs(self):
        try:
            return json.loads(self.subs_json or "[]")
        except ValueError:
            return []

    @property
    def trending(self):
        try:
            return json.loads(self.trending_json or "[]")
        except ValueError:
            return []


class OutlookMarket(db.Model):
    __tablename__ = "outlook_markets"
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(200), nullable=False)
    category_slug = db.Column(db.String(120), default="")
    category_name = db.Column(db.String(160), default="")
    name = db.Column(db.String(200), nullable=False)
    region = db.Column(db.String(80), default="Worldwide")
    segment = db.Column(db.String(80), default="mobility")
    revenue_2026 = db.Column(db.String(60), default="")
    revenue_change = db.Column(db.String(60), default="")
    highlights_json = db.Column(db.Text, default="")
    key_regions_json = db.Column(db.Text, default="")
    definition = db.Column(db.Text, default="")
    analyst_opinion = db.Column(db.Text, default="")
    in_scope_json = db.Column(db.Text, default="")
    out_scope_json = db.Column(db.Text, default="")
    parent_slug = db.Column(db.String(200), default="")

    @property
    def highlights(self):
        try:
            return json.loads(self.highlights_json or "[]")
        except ValueError:
            return []

    @property
    def key_regions(self):
        try:
            return json.loads(self.key_regions_json or "[]")
        except ValueError:
            return []

    @property
    def in_scope(self):
        try:
            return json.loads(self.in_scope_json or "[]")
        except ValueError:
            return []

    @property
    def out_scope(self):
        try:
            return json.loads(self.out_scope_json or "[]")
        except ValueError:
            return []

    _XMO = {"mobility": "mmo", "technology": "tmo", "consumer": "cmo",
            "finance": "fmo", "health": "hmo", "industrial": "imo",
            "advertising-media": "amo", "ecommerce": "emo",
            "country-outlook": "co"}

    @property
    def url(self):
        xmo = self._XMO.get(self.segment, "mmo")
        parts = [self.category_slug, self.slug] if self.category_slug else [self.slug]
        # region slug: hrefs must be valid URIs — a raw space ("united states")
        # breaks strict clients even though browsers auto-encode it
        region_slug = self.region.lower().replace(" ", "-")
        return f"/outlook/{xmo}/" + "/".join(parts) + "/" + region_slug + "/"


class Favorite(db.Model):
    __tablename__ = "favorites"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    stat_id = db.Column(db.Integer)
    report_id = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=MIRROR_NOW)
    __table_args__ = (
        db.UniqueConstraint("user_id", "stat_id", "report_id"),
    )


class DownloadEvent(db.Model):
    __tablename__ = "download_events"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    stat_id = db.Column(db.Integer)
    report_id = db.Column(db.Integer)
    fmt = db.Column(db.String(10), default="png")
    created_at = db.Column(db.DateTime, default=MIRROR_NOW)


class Inquiry(db.Model):
    """Contact-form submission. Not seeded; a successful POST is the only write."""
    __tablename__ = "inquiries"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=MIRROR_NOW)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# ---------------------------------------------------------------------------
# Shared template context (header navigation)
# ---------------------------------------------------------------------------

@app.context_processor
def _header_context():
    try:
        industries = Industry.query.order_by(Industry.id).limit(10).all()
        popular_ids = [871513, 1474143, 1449844, 256598, 379046, 268173,
                       272014, 541390, 186743, 276629]
        popular = [db.session.get(Statistic, i) for i in popular_ids]
        popular = [s for s in popular if s is not None]
        topics = Topic.query.order_by(Topic.id).limit(10).all()
        reports = Report.query.order_by(Report.id).limit(10).all()
        segments = [
            {"slug": "advertising-media", "name": "Advertising & Media"},
            {"slug": "ecommerce-outlook", "name": "eCommerce"},
            {"slug": "consumer-markets", "name": "Consumer"},
            {"slug": "financial-markets", "name": "Finance"},
            {"slug": "country-outlook", "name": "Global Indicators"},
            {"slug": "health-markets", "name": "Health"},
            {"slug": "industry-outlook", "name": "Industrial"},
            {"slug": "mobility-markets", "name": "Mobility"},
            {"slug": "technology-outlook", "name": "Technology"},
        ]
        return {"header_industries": industries,
                "header_popular_stats": popular,
                "header_topics": topics,
                "header_reports": reports,
                "header_segments": segments}
    except Exception:  # noqa: BLE001
        return {"header_industries": [], "header_popular_stats": [],
                "header_topics": [], "header_reports": [], "header_segments": []}


# ---------------------------------------------------------------------------
# Chart rendering (server-side SVG, Highcharts-style look)
# ---------------------------------------------------------------------------

def _fmt_num(v):
    if v is None:
        return "–"
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    s = f"{v:,}" if isinstance(v, int) else f"{v:,.2f}".rstrip("0").rstrip(".")
    return s


def render_chart_svg(points, y_label="", chart_kind="line", width=760, height=420):
    """Render an SVG chart in Statista's Highcharts style.

    points: [[x, y], ...] with numeric x (years) or string x (categories).
    """
    if not points or len(points) < 2:
        return None
    xs = [p[0] for p in points]
    ys = [p[1] for p in points if p[1] is not None]
    if len(ys) < 2:
        return None
    numeric_x = all(isinstance(x, (int, float)) for x in xs)
    pad_l, pad_r, pad_t, pad_b = 70, 30, 40, 60
    plot_w = width - pad_l - pad_r
    plot_h = height - pad_t - pad_b
    ymin, ymax = min(ys), max(ys)
    if ymin == ymax:
        ymin -= 1
        ymax += 1
    span = ymax - ymin
    ymin -= span * 0.08
    ymax += span * 0.08

    def xpx(i):
        if numeric_x:
            x0, x1 = float(xs[0]), float(xs[-1])
            if x1 == x0:
                return pad_l + plot_w / 2
            return pad_l + (float(xs[i]) - x0) / (x1 - x0) * plot_w
        return pad_l + (i / (len(xs) - 1)) * plot_w

    def ypx(v):
        return pad_t + (ymax - v) / (ymax - ymin) * plot_h

    out = [f'<svg viewBox="0 0 {width} {height}" class="statChartSvg" role="img" '
           f'aria-label="{"Line" if chart_kind == "line" else "Bar"} chart with '
           f'{len(points)} data points.">']
    # gridlines + y ticks (5)
    ticks = 5
    for k in range(ticks + 1):
        v = ymin + (ymax - ymin) * k / ticks
        y = ypx(v)
        out.append(f'<line x1="{pad_l}" y1="{y:.1f}" x2="{width - pad_r}" y2="{y:.1f}" '
                   f'stroke="#e6e6e6" stroke-width="1"/>')
        out.append(f'<text x="{pad_l - 8}" y="{y + 4:.1f}" text-anchor="end" '
                   f'class="axisTick">{_fmt_num(round(v, 2))}</text>')
    if y_label:
        out.append(f'<text x="18" y="{pad_t + plot_h / 2:.0f}" class="axisTitle" '
                   f'transform="rotate(-90 18 {pad_t + plot_h / 2:.0f})">{y_label}</text>')
    # x labels (max ~12)
    n_labels = min(len(xs), 12)
    step = max(1, len(xs) // n_labels)
    for i in range(0, len(xs), step):
        x = xpx(i)
        label = str(xs[i])
        out.append(f'<text x="{x:.1f}" y="{height - pad_b + 22}" text-anchor="middle" '
                   f'class="axisTick">{label}</text>')
    # series
    if chart_kind == "line":
        path = []
        for i, (x, y) in enumerate(points):
            if y is None:
                continue
            path.append(("M" if not path or points[i - 1][1] is None else "L")
                        + f" {xpx(i):.1f} {ypx(y):.1f}")
        out.append(f'<path d="{" ".join(path)}" fill="none" stroke="#0666e5" '
                   f'stroke-width="2.5"/>')
        for i, (x, y) in enumerate(points):
            if y is None:
                continue
            out.append(f'<circle cx="{xpx(i):.1f}" cy="{ypx(y):.1f}" r="3.5" '
                       f'fill="#0666e5" stroke="#fff" stroke-width="1"/>')
    else:  # bar
        n = len(points)
        bw = min(46.0, plot_w / n * 0.62)
        for i, (x, y) in enumerate(points):
            if y is None:
                continue
            x0 = xpx(i) - bw / 2
            y0 = ypx(y)
            ybase = ypx(ymin)
            out.append(f'<rect x="{x0:.1f}" y="{y0:.1f}" width="{bw:.1f}" '
                       f'height="{max(0.5, ybase - y0):.1f}" fill="#0666e5" rx="1"/>')
            # value labels above bars (matches upstream bar charts)
            if n <= 30:
                out.append(f'<text x="{xpx(i):.1f}" y="{y0 - 6:.1f}" '
                           f'text-anchor="middle" class="barValue">{_fmt_num(y)}</text>')
    out.append("</svg>")
    return "\n".join(out)


app.jinja_env.globals["render_chart_svg"] = render_chart_svg
app.jinja_env.globals["MIRROR_NOW"] = MIRROR_NOW


# ---------------------------------------------------------------------------
# Snippet sanitizer (search-result / list-card answer-leak guard)
# ---------------------------------------------------------------------------
# The upstream capture cut some summary/description sentences mid-value
# (e.g. "…amounted to 4."). At snippet level such a dangling partial figure
# leaks a value prefix (review finding #7), so every list surface — SERP
# results and the homepage / recent / industry card snippets — drops the
# truncated value tail; the statistic pages keep the full captured text.
# The guard also catches tails created by the snippet's own length cut.
_SNIPPET_TAIL_RX = re.compile(
    r"(?:\s+(?:by|from|to))?\s+(?:amounted\s+to|totaled|reached|reach|"
    r"reaching|stood\s+at|was|were|of|to|at|around|almost|about|nearly|"
    r"approximately|some|over|up\s+to)[\s\u00a0]*[+-]?\d[\d.,\u00a0]*"
    r"\s*%?\s*\.?\s*$", re.I)
_YEAR_RX = re.compile(r"(19|20)\d\d")


def _snippetize(text, length=230, end=""):
    """Normalize captured text into a value-tail-free snippet.

    The length cut runs first (at a word boundary) and the dangling-tail
    guard second, so a tail created by the truncation itself is stripped
    like one captured upstream; the guard loops in case stripping one
    tail exposes another. `end` (e.g. "…") is appended when anything was
    cut, so list cards keep the ellipsis convention of the frozen design.
    Complete year endings are preserved ("… by 2026." keeps its tail).
    """
    text = re.sub(r"\s+", " ", (text or "")).strip()
    cut = len(text) > length
    if cut:
        text = text[:length].rsplit(" ", 1)[0].rstrip(",;:")
    while True:
        m = _SNIPPET_TAIL_RX.search(text)
        if not m:
            break
        num = re.search(r"[\d.,\u00a0]+", m.group(0))
        if not num or _YEAR_RX.fullmatch(num.group(0).strip(".,\u00a0 ")):
            break
        text = text[:m.start()].rstrip()
        cut = True
    return text + end if cut else text


app.jinja_env.filters["snippetize"] = _snippetize


# ---------------------------------------------------------------------------
# Search (scored token overlap — never strict AND)
# ---------------------------------------------------------------------------

def tokenize(query):
    return [t for t in re.split(r"\W+", query.lower())
            if t and t not in STOP_WORDS and len(t) > 1]


def _item_title(item):
    for attr in ("title", "name"):
        v = getattr(item, attr, None)
        if v:
            return v
    return ""


def scored_search(query, items, weight_title=3.0):
    """Token-overlap scoring across title/name (3x) and body text."""
    tokens = tokenize(query)
    if not tokens:
        return items
    scored = []
    for item in items:
        title = _item_title(item).lower()
        blob = item.search_blob().lower() if hasattr(item, "search_blob") else title
        score = 0
        for t in tokens:
            if t in title:
                score += weight_title
            elif t in blob:
                score += 1
        # phrase bonus
        if len(tokens) > 1 and " ".join(tokens) in title:
            score += 2
        if score > 0:
            scored.append((item, score))
    scored.sort(key=lambda pair: (-pair[1], pair[0].id if hasattr(pair[0], "id") else 0))
    return [s[0] for s in scored]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _stat_or_404(sid, slug=None):
    stat = db.session.get(Statistic, sid)
    if stat is None:
        abort(404)
    if slug and stat.slug and slug != stat.slug:
        return redirect(f"/{stat.url_kind}/{stat.id}/{stat.slug}/", code=301)
    return stat


def _parse_update_date(s):
    """Parse 'Aug 13, 2026' / 'April 2026' / '' into a sortable date."""
    if not s:
        return datetime(1970, 1, 1)
    s = s.strip()
    m = re.match(r"([A-Z][a-z]{2,8})\s+(\d{1,2}),?\s+(\d{4})", s)
    if m:
        try:
            return datetime.strptime(f"{m.group(1)} {m.group(2)} {m.group(3)}",
                                      "%B %d %Y")
        except ValueError:
            try:
                return datetime.strptime(f"{m.group(1)} {m.group(2)} {m.group(3)}",
                                         "%b %d %Y")
            except ValueError:
                return datetime(1970, 1, 1)
    m = re.match(r"([A-Z][a-z]{2,8})\s+(\d{4})", s)
    if m:
        try:
            return datetime.strptime(f"{m.group(1)} {m.group(2)}", "%B %Y")
        except ValueError:
            return datetime(1970, 1, 1)
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    return datetime(1970, 1, 1)


def _favorite_stat_ids():
    if not current_user.is_authenticated:
        return set()
    return {f.stat_id for f in current_user.favorites if f.stat_id}


def _favorite_report_ids():
    if not current_user.is_authenticated:
        return set()
    return {f.report_id for f in current_user.favorites if f.report_id}


def _trending_stats(limit=10):
    """Homepage trending slider: the real upstream trending picks when
    available, else the most recently updated statistics."""
    ids = [871513, 1474143, 1449844, 256598, 379046, 268173, 272014,
           541390, 186743, 276629]
    found = [db.session.get(Statistic, i) for i in ids]
    found = [s for s in found if s is not None]
    if len(found) >= limit:
        return found[:limit]
    extra = (Statistic.query.filter(Statistic.id.notin_([s.id for s in found]))
             .order_by(Statistic.last_update.desc()).limit(limit).all())
    seen = {s.id for s in found}
    for s in extra:
        if s.id not in seen:
            found.append(s)
            seen.add(s.id)
    return found[:limit]


def _citation(stat, fmt):
    year = (stat.last_update or "").split(", ")[-1] or "2026"
    title = stat.title
    url = f"https://www.statista.com/{stat.url_kind}/{stat.id}/{stat.slug}/"
    if fmt == "APA":
        return (f"Statista Research Department. ({year}). {title}. "
                f"Statista. {url}")
    if fmt == "Chicago":
        return (f"Statista Research Department. \"{title}.\" Statista, "
                f"{stat.last_update or year}. {url}.")
    if fmt == "Harvard":
        return (f"Statista Research Department {year}, {title}, Statista, "
                f"viewed {MIRROR_NOW.strftime('%B %d, %Y')}, {url}")
    if fmt == "MLA":
        return (f"Statista Research Department. \"{title}.\" Statista, "
                f"{stat.last_update or year}, {url}.")
    return (f"Statista Research Department, \"{title},\" Statista, {url} "
            f"(last visited {MIRROR_NOW.strftime('%B %d, %Y')}).")


# ---------------------------------------------------------------------------
# Market Insights page content (market definitions / analyst opinions)
# ---------------------------------------------------------------------------
_OUTLOOK_ALLOWED_TAGS = {"p", "strong", "b", "br", "ul", "li", "em", "i"}


def _sanitize_captured_html(text):
    """Whitelist-sanitize captured upstream HTML for template rendering.

    Keeps only plain structural tags (no attributes, no links, no images)
    and escapes all text content, so the upstream Market definition /
    Analyst Opinion prose renders faithfully without any active markup.
    """
    if not text:
        return ""
    from markupsafe import escape
    text = re.sub(r"<(script|style)\b.*?</\1>", "", text, flags=re.S | re.I)
    out = []
    for part in re.split(r"(<[^>]+>)", text):
        if part.startswith("<"):
            m = re.match(r"</?\s*([a-zA-Z0-9-]+)", part)
            if m and m.group(1).lower() in _OUTLOOK_ALLOWED_TAGS:
                tag = m.group(1).lower()
                out.append(f"</{tag}>" if part.startswith("</") else f"<{tag}>")
        else:
            out.append(str(escape(part)))
    return "".join(out)


# ---------------------------------------------------------------------------
# Routes — content
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    trending = _trending_stats(10)
    topics = Topic.query.order_by(Topic.id).all()
    industries = Industry.query.order_by(Industry.id).all()
    segments = [
        {"slug": "advertising-media", "name": "Advertising & Media"},
        {"slug": "ecommerce-outlook", "name": "eCommerce"},
        {"slug": "consumer-markets", "name": "Consumer"},
        {"slug": "financial-markets", "name": "Finance"},
        {"slug": "country-outlook", "name": "Global Indicators"},
        {"slug": "health-markets", "name": "Health"},
        {"slug": "industry-outlook", "name": "Industrial"},
        {"slug": "mobility-markets", "name": "Mobility"},
        {"slug": "technology-outlook", "name": "Technology"},
    ]
    reports = Report.query.order_by(Report.id).limit(10).all()
    return render_template("index.html", trending=trending, topics=topics,
                           industries=industries, segments=segments,
                           reports=reports,
                           fav_stats=_favorite_stat_ids())


@app.route("/serp")
def serp():
    q = (request.args.get("q") or "").strip()
    ctype = request.args.get("content_type") or ""
    page = max(1, int(request.args.get("page", 1) or 1))
    per_page = 10

    stats = Statistic.query.all()
    topics = Topic.query.all()
    reports = Report.query.all()
    markets = OutlookMarket.query.all()

    results = []
    if q:
        for s in scored_search(q, stats):
            results.append(("statistic", s))
        for t in scored_search(q, topics):
            results.append(("topic", t))
        for r in scored_search(q, reports):
            results.append(("report", r))
        for m in scored_search(q, markets):
            results.append(("market", m))
        # rank: exact-phrase title matches first, then interleave by type so
        # the page mixes content types like upstream
        qlow = q.lower()

        def phrase_score(kind, item):
            title = _item_title(item).lower()
            if qlow and qlow in title:
                return 0
            return 1
        results.sort(key=lambda ki: phrase_score(ki[0], ki[1]))
        by_type = {}
        for kind, item in results:
            by_type.setdefault(kind, []).append(item)
        merged = []
        order = ["statistic", "topic", "report", "market"]
        queues = {k: list(by_type.get(k, [])) for k in order}
        while any(queues[k] for k in order):
            for k in order:
                if queues[k]:
                    merged.append((k, queues[k].pop(0)))
        # re-rank: phrase matches keep their lead
        merged.sort(key=lambda ki: phrase_score(ki[0], ki[1]))
        results = merged
    else:
        for s in stats[:per_page]:
            results.append(("statistic", s))

    if ctype == "Statistics":
        results = [(k, i) for k, i in results if k == "statistic"]
    elif ctype == "Topics":
        results = [(k, i) for k, i in results if k == "topic"]
    elif ctype == "Reports":
        results = [(k, i) for k, i in results if k == "report"]
    elif ctype == "Market Insights":
        results = [(k, i) for k, i in results if k == "market"]

    total = len(results)
    start = (page - 1) * per_page
    page_items = results[start:start + per_page]
    return render_template("serp.html", q=q, ctype=ctype,
                           results=page_items, total=total,
                           page=page,
                           pages=(total + per_page - 1) // per_page,
                           fav_stats=_favorite_stat_ids())


@app.route("/statistics/<int:sid>/", defaults={"slug": None})
@app.route("/statistics/<int:sid>/<slug>/")
@app.route("/forecasts/<int:sid>/", defaults={"slug": None})
@app.route("/forecasts/<int:sid>/<slug>/")
def statistic_detail(sid, slug):
    stat = _stat_or_404(sid, slug)
    if isinstance(stat, Response):
        # _stat_or_404 redirects to the canonical slug when the requested
        # slug does not match; returning it keeps wrong-slug URLs a 301
        # instead of an AttributeError 500 (same contract as the topic /
        # report / industry routes).
        return stat
    chart_mode = request.args.get("chart", "auto")
    if chart_mode not in ("line", "bar", "table", "auto"):
        chart_mode = "auto"
    if chart_mode == "auto":
        chart_mode = stat.chart_type
    citation_fmt = request.args.get("citation", "")
    citation_text = _citation(stat, citation_fmt) if citation_fmt else ""
    related = [db.session.get(Statistic, i) for i in stat.related_ids[:8]]
    related = [r for r in related if r is not None]
    topic = db.session.get(Topic, stat.topic_id) if stat.topic_id else None
    industry = Industry.query.filter_by(slug=stat.industry_slug).first()
    visible = stat.visible_to(current_user if current_user.is_authenticated else None)
    return render_template(
        "statistic.html", stat=stat, chart_mode=chart_mode, related=related,
        topic=topic, industry=industry, visible=visible,
        citation_fmt=citation_fmt, citation_text=citation_text,
        fav_stats=_favorite_stat_ids(),
        is_fav=stat.id in _favorite_stat_ids())


@app.route("/topics/<int:tid>/", defaults={"slug": None})
@app.route("/topics/<int:tid>/<slug>/")
def topic_detail(tid, slug):
    topic = db.session.get(Topic, tid)
    if topic is None:
        abort(404)
    if slug and topic.slug and slug != topic.slug:
        return redirect(f"/topics/{topic.id}/{topic.slug}/", code=301)
    picks = [db.session.get(Statistic, i) for i in topic.editor_picks]
    picks = [p for p in picks if p is not None]
    recs = [db.session.get(Statistic, i) for i in topic.recommended]
    recs = [r for r in recs if r is not None]
    report = db.session.get(Report, topic.report_id) if topic.report_id else None
    related = [Topic.query.filter_by(name=n).first() for n in topic.related_topics]
    related = [r for r in related if r is not None]
    return render_template("topic.html", topic=topic, picks=picks, recs=recs,
                           report=report, related_topics=related,
                           fav_stats=_favorite_stat_ids())


@app.route("/markets/")
def markets_index():
    industries = Industry.query.order_by(Industry.id).all()
    return render_template("markets.html", industries=industries)


@app.route("/markets/<int:mid>/", defaults={"slug": None})
@app.route("/markets/<int:mid>/<slug>/")
def market_detail(mid, slug):
    industry = db.session.get(Industry, mid)
    if industry is None:
        abort(404)
    if slug and industry.slug and slug != industry.slug:
        return redirect(f"/markets/{industry.id}/{industry.slug}/", code=301)
    trending = [db.session.get(Statistic, i) for i in industry.trending]
    trending = [t for t in trending if t is not None]
    in_industry = Statistic.query.filter_by(industry_slug=industry.slug)\
        .order_by(Statistic.id).limit(12).all()
    return render_template("market.html", industry=industry,
                           trending=trending, in_industry=in_industry,
                           fav_stats=_favorite_stat_ids())


@app.route("/study/<int:rid>/", defaults={"slug": None})
@app.route("/study/<int:rid>/<slug>/")
def report_detail(rid, slug):
    report = db.session.get(Report, rid)
    if report is None:
        abort(404)
    if slug and report.slug and slug != report.slug:
        return redirect(f"/study/{report.id}/{report.slug}/", code=301)
    stats = [db.session.get(Statistic, i) for i in report.stat_ids[:12]]
    stats = [s for s in stats if s is not None]
    related_reports = Report.query.filter(Report.id != report.id)\
        .order_by(Report.id).limit(8).all()
    return render_template("report.html", report=report, stats=stats,
                           related_reports=related_reports,
                           is_fav=report.id in _favorite_report_ids())


@app.route("/recent/statistics/")
def recent_statistics():
    ctype = request.args.get("content_type") or ""
    q = Statistic.query
    if ctype == "Forecasts":
        q = q.filter_by(content_type="forecast")
    elif ctype == "Statistics":
        q = q.filter_by(content_type="statistic")
    stats = q.all()
    stats.sort(key=lambda s: _parse_update_date(s.last_update), reverse=True)
    return render_template("recent_stats.html", stats=stats[:60], ctype=ctype,
                           fav_stats=_favorite_stat_ids())


@app.route("/recent/topics/")
def recent_topics():
    topics = Topic.query.order_by(Topic.published_date.desc()).all()
    return render_template("recent_topics.html", topics=topics)


@app.route("/recent/reports/")
def recent_reports():
    reports = Report.query.order_by(Report.id.desc()).all()
    return render_template("recent_reports.html", reports=reports)


@app.route("/outlook/")
def outlook_index():
    segments = [
        {"slug": "advertising-media", "name": "Advertising & Media"},
        {"slug": "ecommerce-outlook", "name": "eCommerce"},
        {"slug": "consumer-markets", "name": "Consumer"},
        {"slug": "financial-markets", "name": "Finance"},
        {"slug": "country-outlook", "name": "Global Indicators"},
        {"slug": "health-markets", "name": "Health"},
        {"slug": "industry-outlook", "name": "Industrial"},
        {"slug": "mobility-markets", "name": "Mobility"},
        {"slug": "technology-outlook", "name": "Technology"},
    ]
    markets = OutlookMarket.query.order_by(OutlookMarket.id).all()
    return render_template("outlook.html", segments=segments, markets=markets)


SEGMENT_SLUG_TO_DB = {
    "advertising-media": "advertising-media",
    "ecommerce-outlook": "ecommerce-outlook",
    "consumer-markets": "consumer-markets",
    "financial-markets": "financial-markets",
    "country-outlook": "country-outlook",
    "health-markets": "health-markets",
    "industry-outlook": "industry-outlook",
    "mobility-markets": "mobility",
    "technology-outlook": "technology-outlook",
}


@app.route("/outlook/<segment>/")
def outlook_segment(segment):
    markets = OutlookMarket.query.filter_by(
        segment=SEGMENT_SLUG_TO_DB.get(segment, segment))\
        .order_by(OutlookMarket.id).all()
    names = {
        "advertising-media": "Advertising & Media",
        "ecommerce-outlook": "eCommerce",
        "consumer-markets": "Consumer",
        "financial-markets": "Finance",
        "country-outlook": "Global Indicators",
        "health-markets": "Health",
        "industry-outlook": "Industrial",
        "mobility-markets": "Mobility",
        "technology-outlook": "Technology",
    }
    if not markets:
        abort(404)
    return render_template("outlook_segment.html", segment=segment,
                           segment_name=names.get(segment, segment),
                           markets=markets)


@app.route("/outlook/mmo/<path:market_path>/")
@app.route("/outlook/tmo/<path:market_path>/")
@app.route("/outlook/cmo/<path:market_path>/")
@app.route("/outlook/fmo/<path:market_path>/")
@app.route("/outlook/hmo/<path:market_path>/")
@app.route("/outlook/imo/<path:market_path>/")
@app.route("/outlook/amo/<path:market_path>/")
@app.route("/outlook/emo/<path:market_path>/")
@app.route("/outlook/co/<path:market_path>/")
def outlook_market(market_path):
    parts = market_path.rstrip("/").split("/")
    region = parts[-1] if len(parts) >= 2 else "worldwide"
    slug = parts[-2] if len(parts) >= 2 else parts[0]
    category = parts[-3] if len(parts) >= 3 else ""
    q = OutlookMarket.query.filter_by(slug=slug)
    if category:
        q = q.filter_by(category_slug=category)
    market = q.first()
    if market is None and not category:
        market = OutlookMarket.query.filter_by(slug=slug).first()
    if market is None:
        abort(404)
    siblings = OutlookMarket.query.filter_by(category_slug=market.category_slug)\
        .order_by(OutlookMarket.id).all() if market.category_slug else []
    children = OutlookMarket.query.filter_by(parent_slug=market.slug)\
        .order_by(OutlookMarket.id).all()
    parent = None
    if market.category_slug:
        parent = OutlookMarket.query.filter_by(
            slug=market.category_slug, category_slug="").first()
        if parent is None:
            parent = OutlookMarket.query.filter_by(slug=market.category_slug).first()
    return render_template("outlook_market.html", market=market,
                           siblings=siblings, children=children, parent=parent,
                           definition_html=_sanitize_captured_html(
                               market.definition),
                           analyst_opinion_html=_sanitize_captured_html(
                               market.analyst_opinion))


@app.route("/pricing/")
def pricing():
    plans = [
        {"name": "Basic Account", "who": "For single users", "price": "$0 USD",
         "per": "Always free", "cta": "Register now", "features":
         ["Free Statistics"]},
        {"name": "Starter Account", "who": "For single users", "price": "$199 USD",
         "per": "per month, billed annually", "cta": "Buy now", "features":
         ["Free + Premium Statistics"]},
        {"name": "Personal Account", "who": "For single users", "price": "$649 USD",
         "per": "per month, billed annually", "cta": "Buy now", "features":
         ["Free + Premium Statistics", "Report previews"]},
        {"name": "Professional Account", "who": "For teams of up to 99 users",
         "price": "$2,388 USD", "per": "yearly", "cta": "Buy now", "features":
         ["Free + Premium Statistics", "Reports", "API access"]},
    ]
    return render_template("pricing.html", plans=plans)


@app.route("/contact/", methods=["GET", "POST"])
def contact():
    sent = False
    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        email = (request.form.get("email") or "").strip()
        message = (request.form.get("message") or "").strip()
        if not name or not email or not message:
            flash("Please fill in all fields.", "error")
        elif "@" not in email or "." not in email:
            flash("Please enter a valid email address.", "error")
        else:
            db.session.add(Inquiry(name=name, email=email, message=message,
                                   created_at=MIRROR_NOW))
            db.session.commit()
            sent = True
    return render_template("contact.html", sent=sent)


# ---------------------------------------------------------------------------
# Routes — account
# ---------------------------------------------------------------------------

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        username = (request.form.get("username") or "").strip().lower()
        display = (request.form.get("display_name") or "").strip()
        password = request.form.get("password") or ""
        if not email or "@" not in email or "." not in email:
            flash("Please enter a valid email address.", "error")
        elif not username or not re.fullmatch(r"[a-z0-9_.-]{3,40}", username):
            flash("Username must be 3-40 characters (letters, digits, . _ -).", "error")
        elif len(password) < 8:
            flash("Password must be at least 8 characters long.", "error")
        elif User.query.filter_by(email=email).first():
            flash("An account with this email already exists.", "error")
        elif User.query.filter_by(username=username).first():
            flash("This username is already taken.", "error")
        else:
            user = User(email=email, username=username,
                        display_name=(display or username).title(),
                        password_hash=bcrypt.generate_password_hash(password),
                        account_type="Basic",
                        created_at=MIRROR_NOW)
            db.session.add(user)
            db.session.commit()
            login_user(user)
            flash("Your Basic Account is ready. Welcome to Statista!", "success")
            return redirect(url_for("account"))
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        ident = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        user = User.query.filter_by(email=ident).first()
        if user is None:
            user = User.query.filter_by(username=ident).first()
        if not ident or not password or user is None or not user.check_password(password):
            if not ident:
                flash("Email address or username is required", "error")
                flash("Enter a valid email address or username", "error")
            if not password:
                flash("Password is required", "error")
            if ident and password:
                flash("Invalid credentials. Please check your email/username and password.", "error")
            return render_template("login.html")
        login_user(user)
        flash(f"Welcome back, {user.display_name}!", "success")
        nxt = request.args.get("next")
        if nxt and nxt.startswith("/"):
            return redirect(nxt)
        return redirect(url_for("account"))
    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))


@app.route("/account")
@login_required
def account():
    return render_template("account.html",
                           fav_stats=current_user.favorites,
                           downloads=current_user.downloads)


@app.route("/account/favorites")
@login_required
def account_favorites():
    fav_stats = [f for f in current_user.favorites if f.stat_id]
    fav_reports = [f for f in current_user.favorites if f.report_id]
    stats = [db.session.get(Statistic, f.stat_id) for f in fav_stats]
    stats = [s for s in stats if s is not None]
    reports = [db.session.get(Report, f.report_id) for f in fav_reports]
    reports = [r for r in reports if r is not None]
    return render_template("favorites.html", stats=stats, reports=reports)


@app.route("/account/downloads")
@login_required
def account_downloads():
    events = []
    for d in current_user.downloads:
        stat = db.session.get(Statistic, d.stat_id) if d.stat_id else None
        report = db.session.get(Report, d.report_id) if d.report_id else None
        events.append({"event": d, "stat": stat, "report": report})
    return render_template("downloads.html", events=events)


@app.route("/favorite/stat/<int:sid>", methods=["POST"])
@login_required
def favorite_stat(sid):
    stat = db.session.get(Statistic, sid)
    if stat is None:
        abort(404)
    existing = Favorite.query.filter_by(user_id=current_user.id, stat_id=sid).first()
    if existing:
        db.session.delete(existing)
        db.session.commit()
        if request.headers.get("X-Requested-With") == "fetch":
            return jsonify({"ok": True, "favorited": False})
        flash("Statistic removed from your favorites.", "success")
        return redirect(request.form.get("back") or request.referrer or "/")
    fav = Favorite(user_id=current_user.id, stat_id=sid, created_at=MIRROR_NOW)
    db.session.add(fav)
    db.session.commit()
    if request.headers.get("X-Requested-With") == "fetch":
        return jsonify({"ok": True, "favorited": True})
    flash("Statistic added to your favorites.", "success")
    return redirect(request.form.get("back") or request.referrer or "/")


@app.route("/favorite/report/<int:rid>", methods=["POST"])
@login_required
def favorite_report(rid):
    report = db.session.get(Report, rid)
    if report is None:
        abort(404)
    existing = Favorite.query.filter_by(user_id=current_user.id, report_id=rid).first()
    if existing:
        db.session.delete(existing)
        db.session.commit()
        flash("Report removed from your favorites.", "success")
    else:
        db.session.add(Favorite(user_id=current_user.id, report_id=rid,
                                created_at=MIRROR_NOW))
        db.session.commit()
        flash("Report added to your favorites.", "success")
    return redirect(request.form.get("back") or request.referrer or "/")


@app.route("/download/stat/<int:sid>", methods=["POST"])
@login_required
def download_stat(sid):
    stat = db.session.get(Statistic, sid)
    if stat is None:
        abort(404)
    fmt = request.form.get("format", "png")
    if fmt not in ("png", "pdf", "xls", "ppt"):
        fmt = "png"
    if stat.premium and not current_user.can_view_premium:
        flash("This statistic requires a Starter Account or higher. "
              "Upgrade to download premium statistics.", "error")
        return redirect(f"/{stat.url_kind}/{stat.id}/{stat.slug}/")
    db.session.add(DownloadEvent(user_id=current_user.id, stat_id=sid,
                                 fmt=fmt, created_at=MIRROR_NOW))
    db.session.commit()
    flash(f"Your {fmt.upper()} download of “{stat.title}” has been prepared. "
          "Find it in your download history.", "success")
    return redirect(f"/{stat.url_kind}/{stat.id}/{stat.slug}/")


@app.route("/download/report/<int:rid>", methods=["POST"])
@login_required
def download_report(rid):
    report = db.session.get(Report, rid)
    if report is None:
        abort(404)
    if not current_user.can_download_reports:
        flash("Report downloads are included in the Professional Account. "
              "Upgrade your plan to download reports.", "error")
        return redirect(f"/study/{report.id}/{report.slug}/")
    db.session.add(DownloadEvent(user_id=current_user.id, report_id=rid,
                                 fmt="pdf", created_at=MIRROR_NOW))
    db.session.commit()
    flash(f"“{report.title}” has been added to your downloads.", "success")
    return redirect(f"/study/{report.id}/{report.slug}/")


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.route("/_health")
def health():
    try:
        stats = Statistic.query.count()
        topics = Topic.query.count()
        reports = Report.query.count()
        markets = OutlookMarket.query.count()
        users = User.query.count()
        return {"ok": True, "site": "statista",
                "counts": {"statistics": stats, "topics": topics,
                           "reports": reports, "outlook_markets": markets,
                           "users": users}}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}, 500


# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------

with app.app_context():
    db.create_all()
    import seed_data  # noqa: E402
    seed_data.db = db
    seed_data.seed_database()
    seed_data.seed_benchmark_users()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
