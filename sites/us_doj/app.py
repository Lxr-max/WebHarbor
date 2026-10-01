"""Source-grounded, offline U.S. Department of Justice research mirror."""
from __future__ import annotations

import os
import re
import unicodedata
from datetime import date
from pathlib import Path
from urllib.parse import urlencode, urlsplit

from flask import Flask, abort, redirect, render_template, request, send_from_directory
from flask_sqlalchemy import SQLAlchemy

BASE_DIR = Path(__file__).resolve().parent
INSTANCE_DIR = Path(os.environ.get("DOJ_INSTANCE_PATH", BASE_DIR / "instance"))
INSTANCE_DIR.mkdir(parents=True, exist_ok=True)
app = Flask(__name__, instance_path=str(INSTANCE_DIR))
app.config.update(
    SQLALCHEMY_DATABASE_URI=f"sqlite:///{INSTANCE_DIR / 'us_doj.db'}",
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    SECRET_KEY="webharbor-us-doj-offline-fixture",
    MAX_CONTENT_LENGTH=1024 * 1024,
)
db = SQLAlchemy(app)


class Page(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    path = db.Column(db.String, unique=True, nullable=False, index=True)
    source_url = db.Column(db.String, nullable=False)
    title = db.Column(db.String, nullable=False)
    kind = db.Column(db.String, nullable=False, index=True)
    body_html = db.Column(db.Text, nullable=False)
    body_text = db.Column(db.Text, nullable=False)
    summary = db.Column(db.Text, nullable=False, default="")
    date = db.Column(db.String, nullable=False, default="", index=True)
    updated_date = db.Column(db.String, nullable=False, default="")
    topics = db.Column(db.JSON, nullable=False, default=list)
    components = db.Column(db.JSON, nullable=False, default=list)
    navigation = db.Column(db.JSON, nullable=False, default=list)
    organization = db.Column(db.String, nullable=False, default="")
    position = db.Column(db.String, nullable=False, default="")
    states = db.Column(db.JSON, nullable=False, default=list)
    practice_areas = db.Column(db.JSON, nullable=False, default=list)
    deadline = db.Column(db.String, nullable=False, default="")
    image_path = db.Column(db.String, nullable=False, default="")
    release_number = db.Column(db.String, nullable=False, default="")
    source_sha256 = db.Column(db.String, nullable=False)
    source_captured_at = db.Column(db.String, nullable=False)

    @property
    def url(self):
        return self.path

    @property
    def display_date(self):
        try:
            value = date.fromisoformat(self.date[:10])
            return f"{value:%B} {value.day}, {value.year}"
        except ValueError:
            return self.date


class SnapshotMeta(db.Model):
    key = db.Column(db.String, primary_key=True)
    value = db.Column(db.JSON, nullable=False)


class User(db.Model):
    """Benchmark fixture identities; the public DOJ pages require no login."""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String, unique=True, nullable=False)
    email = db.Column(db.String, unique=True, nullable=False)
    display_name = db.Column(db.String, nullable=False)
    password_hash = db.Column(db.String, nullable=False)


STOP_WORDS = {"the", "a", "an", "of", "for", "and", "or", "in", "on", "to", "is", "at", "with", "by", "from"}


def tokens(text):
    text = unicodedata.normalize("NFKD", text or "").casefold()
    return {t for t in re.findall(r"[a-z0-9]+", text) if t not in STOP_WORDS and len(t) > 1}


def scored_search(query, items):
    wanted = tokens(query)
    if not wanted:
        return list(items)
    scored = []
    for item in items:
        score = 5 * len(wanted & tokens(item.title))
        score += 2 * len(wanted & tokens(item.summary))
        score += len(wanted & tokens(item.body_text))
        if score:
            scored.append((score, item))
    return [item for _, item in sorted(scored, key=lambda p: (-p[0], p[1].title.casefold(), p[1].path))]


def paginate(items, size):
    try:
        index = max(0, int(request.args.get("page", "0")))
    except (ValueError, TypeError):
        index = 0
    total = len(items)
    count = max(1, (total + size - 1) // size)
    index = min(index, count - 1)
    return {"items": items[index * size:(index + 1) * size], "total": total, "page": index, "pages": count}


def page_url(index):
    values = request.args.to_dict(flat=False)
    values["page"] = [str(index)]
    return request.path + "?" + urlencode(values, doseq=True)


def has_path(path):
    return path in {"/", "/search", "/news", "/news/press-releases", "/legal-careers/vacancies"} or db.session.scalar(db.select(Page.id).where(Page.path == path)) is not None


@app.context_processor
def template_utilities():
    return {"page_url": page_url, "has_path": has_path, "snapshot_date": "September 27, 2026"}


@app.after_request
def offline_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Content-Security-Policy"] = "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self'; font-src 'self'; connect-src 'self'; frame-src 'none'; form-action 'self'; base-uri 'self'"
    return response


@app.route("/")
def index():
    news = db.session.scalars(db.select(Page).where(Page.kind == "news").order_by(Page.date.desc(), Page.path).limit(6)).all()
    pages = db.session.scalars(db.select(Page).where(Page.kind.in_(["page", "agency"])).order_by(Page.title)).all()
    return render_template("index.html", news=news, pages=pages)


@app.route("/news")
@app.route("/news/press-releases")
def news_list():
    all_items = list(db.session.scalars(db.select(Page).where(Page.kind == "news")).all())
    facets = {"topics": sorted({t for p in all_items for t in p.topics}),
              "components": sorted({c for p in all_items for c in p.components}),
              "years": sorted({p.date[:4] for p in all_items if p.date}, reverse=True)}
    q = request.args.get("search_api_fulltext", request.args.get("q", ""))[:256].strip()
    topic, component, year = (request.args.get(k, "").strip() for k in ("topic", "component", "year"))
    start_date, end_date = (request.args.get(k, "").strip() for k in ("start_date", "end_date"))
    sort_by = request.args.get("sort_by", "search_api_relevance")
    items = scored_search(q, all_items)
    if topic:
        items = [p for p in items if topic.casefold() in {x.casefold() for x in p.topics}]
    if component:
        items = [p for p in items if component.casefold() in {x.casefold() for x in p.components}]
    if year:
        items = [p for p in items if p.date.startswith(year)]
    for value in (start_date, end_date):
        if value:
            try:
                date.fromisoformat(value)
            except ValueError:
                abort(400, description="Enter a valid date in YYYY-MM-DD format.")
    if start_date and end_date and start_date > end_date:
        abort(400, description="The start date must be before the end date.")
    if start_date:
        items = [p for p in items if p.date >= start_date]
    if end_date:
        items = [p for p in items if p.date <= end_date]
    if sort_by in {"date", "field_date", "created"} or not q:
        items.sort(key=lambda p: (p.date, p.path), reverse=True)
    return render_template("news_list.html", **paginate(items, 12), q=q, topic=topic,
        component=component, year=year, start_date=start_date, end_date=end_date,
        sort_by=sort_by, facets=facets, base_path=request.path)


@app.route("/legal-careers/vacancies")
def jobs_list():
    all_items = list(db.session.scalars(db.select(Page).where(Page.kind == "job")).all())
    facets = {"positions": sorted({p.position for p in all_items if p.position}),
              "organizations": sorted({p.organization for p in all_items if p.organization}),
              "practice_areas": sorted({v for p in all_items for v in p.practice_areas}),
              "states": sorted({v for p in all_items for v in p.states})}
    selected = {k: request.args.get(k, "").strip() for k in ("position", "organization", "practice_area", "state")}
    for name in request.args:
        if name.startswith("f["):
            for value in request.args.getlist(name):
                if value.startswith("va_state:"):
                    selected["state"] = value.split(":", 1)[1]
    q = request.args.get("q", "")[:256].strip()
    items = scored_search(q, all_items)
    for key in ("position", "organization"):
        if selected[key]:
            items = [p for p in items if getattr(p, key).casefold() == selected[key].casefold()]
    for key, attr in (("practice_area", "practice_areas"), ("state", "states")):
        if selected[key]:
            items = [p for p in items if selected[key].casefold() in {s.casefold() for s in getattr(p, attr)}]
    sort_by = request.args.get("sort_by", "posted")
    if sort_by in {"title", "Title"}:
        items.sort(key=lambda p: (p.title.casefold(), p.path))
    else:
        items.sort(key=lambda p: (p.date, p.path), reverse=True)
    return render_template("jobs_list.html", **paginate(items, 25), q=q, **selected,
        sort_by=sort_by, facets=facets, base_path=request.path)


@app.route("/search")
def search():
    q = request.args.get("query", request.args.get("q", ""))[:256].strip()
    items = scored_search(q, db.session.scalars(db.select(Page)).all())
    return render_template("search.html", **paginate(items, 12), q=q)


@app.route("/reference")
def reference():
    """An explicit offline boundary for links outside the captured collection."""
    target = request.args.get("url", "")
    try:
        parsed = urlsplit(target)
        valid = parsed.scheme in {"http", "https", "mailto", "tel"}
        if parsed.scheme in {"http", "https"}:
            valid = valid and bool(parsed.hostname)
    except ValueError:
        valid = False
    if not valid:
        abort(400)
    return render_template("reference.html", target=target, label=request.args.get("label", "External resource"), hostname=parsed.hostname or parsed.scheme)


@app.route("/_health")
def health():
    count = db.session.scalar(db.select(db.func.count(Page.id)))
    return {"ok": bool(count), "site": "us_doj", "pages": count}, 200 if count else 503


@app.route("/<path:path>")
def detail(path):
    canonical = "/" + path.rstrip("/")
    redirects = {"/careers/search-jobs": "/careers/search-opportunities", "/oip/oip-request.html": "/oip/submit-and-track-request-or-appeal"}
    if canonical in redirects:
        return redirect(redirects[canonical])
    asset_routes = db.session.get(SnapshotMeta, 'asset_routes')
    asset = asset_routes.value.get(canonical) if asset_routes else None
    if asset:
        return send_from_directory(BASE_DIR, asset['path'], mimetype=asset['mime'])
    item = db.session.scalar(db.select(Page).where(Page.path == canonical))
    if item is None:
        abort(404)
    return render_template("detail.html", item=item)


@app.errorhandler(400)
@app.errorhandler(404)
def error_page(error):
    return render_template("error.html", code=error.code, message=error.description), error.code


with app.app_context():
    db.create_all()
    from seed_data import seed_database, seed_benchmark_users
    seed_database(db, Page, SnapshotMeta)
    seed_benchmark_users(db, User)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "40120")), debug=False)
