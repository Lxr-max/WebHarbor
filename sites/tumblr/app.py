"""Tumblr mirror — Flask app.

Mirrors www.tumblr.com for the WebHarbor benchmark: logged-out trending feed,
tag hub pages, search with tabs and suggestions, blog pages with archives,
post permalinks with real like/reblog notes, and — for the four benchmark
users — a dashboard of followed blogs, likes, following, activity, inbox
conversations, ask/submission flows, reblogging, and a post composer.

All runtime content comes from the SQLite seed DB built by seed_data.py from
the frozen source_data/ snapshots captured from www.tumblr.com on 2026-09-28
(see provenance.json). No handler reads scraped JSON at request time.
"""
from __future__ import annotations

import calendar
import hashlib
import json
import os
import re
from datetime import datetime, timedelta, timezone

from flask import (Flask, abort, flash, jsonify, redirect, render_template,
                   request, send_from_directory, session, url_for)
from flask_sqlalchemy import SQLAlchemy
from markupsafe import Markup, escape
from werkzeug.utils import secure_filename

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

os.makedirs(os.path.join(BASE_DIR, "instance"), exist_ok=True)

app = Flask(__name__, instance_path=os.path.join(BASE_DIR, "instance"))
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "TUMBLR_DB_URI", f"sqlite:///{BASE_DIR}/instance/tumblr.db")
app.config["SECRET_KEY"] = "webharbor-tumblr-dev-key"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024

db = SQLAlchemy(app)

# Frozen snapshot date: every relative label ("2 days ago") is computed
# against it so pages render identically at any time. Interpreted as UTC
# regardless of the host/container timezone so the seed and the rendering
# chain agree everywhere.
MIRROR_DATE = datetime(2026, 9, 28, 12, 0, 0)
MIRROR_TS = calendar.timegm(MIRROR_DATE.timetuple())

PAGE_SIZE = 10
BLOG_PAGE_SIZE = 12
DASH_PAGE_SIZE = 8
PASSWORD_NAMESPACE = "webharbor-tumblr"


def stable_password_hash(raw_password: str) -> str:
    digest = hashlib.sha256()
    digest.update(f"{PASSWORD_NAMESPACE}:{raw_password}".encode("utf-8"))
    return digest.hexdigest()


# --------------------------------------------------------------------------- #
# Models
# --------------------------------------------------------------------------- #
class Blog(db.Model):
    __tablename__ = "blogs"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False, index=True)
    title = db.Column(db.String(300), default="")
    description = db.Column(db.Text, default="")
    url = db.Column(db.String(300), default="")
    uuid = db.Column(db.String(80), default="")
    updated = db.Column(db.Integer, default=0)
    primary = db.Column(db.Boolean, default=False)
    posts_count = db.Column(db.Integer, default=0)
    total_posts_upstream = db.Column(db.Integer)
    avatar = db.Column(db.String(300), default="")
    avatar_shape = db.Column(db.String(20), default="circle")
    header_image = db.Column(db.String(300), default="")
    background_color = db.Column(db.String(20), default="#001935")
    title_color = db.Column(db.String(20), default="#ffffff")
    body_font = db.Column(db.String(80), default="Helvetica Neue")
    link_color = db.Column(db.String(20), default="#00b8ff")
    can_message = db.Column(db.Boolean, default=False)
    is_nsfw = db.Column(db.Boolean, default=False)
    is_adult = db.Column(db.Boolean, default=False)
    can_be_followed = db.Column(db.Boolean, default=True)
    ask = db.Column(db.Boolean, default=False)
    ask_anon = db.Column(db.Boolean, default=False)
    ask_page_title = db.Column(db.String(300), default="")
    share_likes = db.Column(db.Boolean, default=False)
    share_following = db.Column(db.Boolean, default=False)
    owner_user_id = db.Column(db.Integer)          # benchmark-user blogs only

    posts = db.relationship("Post", backref="blog", lazy="dynamic")

    def display_title(self):
        return self.title or self.name

    def post_count_label(self):
        if self.total_posts_upstream:
            return f"{self.total_posts_upstream:,} posts"
        return f"{self.posts_count:,} posts"


class Post(db.Model):
    __tablename__ = "posts"
    id = db.Column(db.String(40), primary_key=True)
    blog_id = db.Column(db.Integer, db.ForeignKey("blogs.id"),
                        nullable=False, index=True)
    type = db.Column(db.String(20), default="text")     # text photo answer ...
    original_type = db.Column(db.String(20), default="regular")
    is_blocks_post_format = db.Column(db.Boolean, default=True)
    content = db.Column(db.Text, default="[]")          # JSON blocks
    layout = db.Column(db.Text, default="[]")
    trail = db.Column(db.Text, default="[]")            # reblog chain
    tags = db.Column(db.Text, default="[]")
    timestamp = db.Column(db.Integer, default=0, index=True)
    date_str = db.Column(db.String(60), default="")
    post_url = db.Column(db.String(400), default="")
    slug = db.Column(db.String(400), default="")
    summary = db.Column(db.Text, default="")
    note_count = db.Column(db.Integer, default=0)
    like_count = db.Column(db.Integer, default=0)
    reblog_count = db.Column(db.Integer, default=0)
    reply_count = db.Column(db.Integer, default=0)
    state = db.Column(db.String(20), default="published")
    asking_name = db.Column(db.String(120))
    asking_url = db.Column(db.String(300))
    asking_avatar = db.Column(db.String(300))
    reblog_of_id = db.Column(db.String(40))            # mirror reblogs
    user_created = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.Integer, default=0)       # mirror actions

    def blocks(self):
        return json.loads(self.content or "[]")

    def trail_items(self):
        items = json.loads(self.trail or "[]")
        known = None
        for item in items:
            name = item.get("blog_name")
            if not name:
                item["blog_exists"] = False
                continue
            if known is None:
                from sqlalchemy import select as _select
                known = {row[0] for row in db.session.execute(
                    _select(Blog.name)).all()}
            item["blog_exists"] = name in known
        return items

    def tag_list(self):
        return json.loads(self.tags or "[]")

    def first_image(self):
        for b in self.blocks():
            if b.get("type") == "image" and b.get("media"):
                return b["media"]
            if b.get("type") in ("video", "audio") and b.get("poster"):
                return b["poster"]
        return None

    def body_text(self):
        parts = []
        for b in self.blocks():
            if b.get("type") == "text":
                parts.append(re.sub(r"<[^>]+>", " ", b.get("text") or ""))
            elif b.get("type") == "quote":
                parts.append(b.get("text") or "")
        for t in self.trail_items():
            for b in t.get("content") or []:
                if b.get("type") == "text":
                    parts.append(re.sub(r"<[^>]+>", " ", b.get("text") or ""))
        return " ".join(parts)

    def live_like_count(self):
        return (self.like_count or 0) + Like.query.filter_by(post_id=self.id).count()

    def live_reblog_count(self):
        return (self.reblog_count or 0) + Reblog.query.filter_by(source_post_id=self.id).count()

    def live_note_count(self):
        n = self.note_count or 0
        n += Like.query.filter_by(post_id=self.id).count()
        n += Reblog.query.filter_by(source_post_id=self.id).count()
        return n


class Note(db.Model):
    __tablename__ = "notes"
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.String(40), nullable=False, index=True)
    seq = db.Column(db.Integer, nullable=False)
    type = db.Column(db.String(20), default="like")
    timestamp = db.Column(db.Integer, default=0)
    blog_name = db.Column(db.String(120), default="")
    blog_title = db.Column(db.String(300), default="")
    blog_url = db.Column(db.String(300), default="")
    avatar = db.Column(db.String(300), default="")
    avatar_shape = db.Column(db.String(20), default="circle")
    reply_text = db.Column(db.Text)
    added_text = db.Column(db.Text)


class TagHub(db.Model):
    __tablename__ = "tag_hubs"
    id = db.Column(db.Integer, primary_key=True)
    tag = db.Column(db.String(120), unique=True, nullable=False, index=True)
    hub_name = db.Column(db.String(120), default="")
    background_color = db.Column(db.String(20), default="#35465d")
    header_image = db.Column(db.String(300), default="")
    header_link = db.Column(db.String(400), default="")
    featured_post_id = db.Column(db.String(40), default="")
    blog_name = db.Column(db.String(120), default="")
    blog_avatar = db.Column(db.String(300), default="")
    followers_count = db.Column(db.String(30), default="")
    followers_count_int = db.Column(db.Integer, default=0)
    new_posts_count = db.Column(db.String(30), default="")
    new_posts_count_int = db.Column(db.Integer, default=0)
    post_count_int = db.Column(db.Integer, default=0)
    editorial_description = db.Column(db.Text, default="")
    editorial_description_text = db.Column(db.Text, default="")
    related_tags = db.Column(db.Text, default="[]")

    def related(self):
        return json.loads(self.related_tags or "[]")


class TagPost(db.Model):
    __tablename__ = "tag_posts"
    id = db.Column(db.Integer, primary_key=True)
    tag = db.Column(db.String(120), nullable=False, index=True)
    post_id = db.Column(db.String(40), nullable=False)
    position = db.Column(db.Integer, nullable=False)


class Trending(db.Model):
    """The logged-out home + explore trending feed, in upstream order."""
    __tablename__ = "trending"
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.String(40), nullable=False)
    position = db.Column(db.Integer, nullable=False)


class SearchQuery(db.Model):
    __tablename__ = "search_queries"
    id = db.Column(db.Integer, primary_key=True)
    query_text = db.Column(db.String(200), unique=True, nullable=False)
    top_post_ids = db.Column(db.Text, default="[]")
    recent_post_ids = db.Column(db.Text, default="[]")
    blogs = db.Column(db.Text, default="[]")
    tags = db.Column(db.Text, default="[]")
    communities = db.Column(db.Text, default="[]")
    typeahead_tags = db.Column(db.Text, default="[]")
    typeahead_blogs = db.Column(db.Text, default="[]")

    def ids(self, which):
        return json.loads(getattr(self, which) or "[]")

    def rows(self, which):
        return json.loads(getattr(self, which) or "[]")


class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(200), unique=True, nullable=False)
    password_hash = db.Column(db.String(80), nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    display_name = db.Column(db.String(120), default="")
    blog_id = db.Column(db.Integer)

    @property
    def blog(self):
        return Blog.query.get(self.blog_id) if self.blog_id else None


class Like(db.Model):
    __tablename__ = "likes"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False, index=True)
    post_id = db.Column(db.String(40), nullable=False, index=True)
    created_at = db.Column(db.Integer, default=0)


class Follow(db.Model):
    __tablename__ = "follows"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False, index=True)
    blog_id = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.Integer, default=0)


class Reblog(db.Model):
    __tablename__ = "reblogs"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False, index=True)
    source_post_id = db.Column(db.String(40), nullable=False, index=True)
    new_post_id = db.Column(db.String(40), nullable=False)
    comment = db.Column(db.Text, default="")
    created_at = db.Column(db.Integer, default=0)


class Conversation(db.Model):
    __tablename__ = "conversations"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False, index=True)
    blog_name = db.Column(db.String(120), nullable=False)
    updated_at = db.Column(db.Integer, default=0)

    messages = db.relationship("Message", backref="conversation",
                               lazy="dynamic",
                               order_by="Message.created_at")

    def unread(self):
        # Unread indicator counts messages FROM THE OTHER SIDE that have not
        # been read yet — the same semantics as the Inbox nav badge in
        # base_ctx (from_user=False, read=False). The agent's own sent
        # messages must not keep their own conversation flagged unread.
        return Message.query.filter_by(conversation_id=self.id,
                                       from_user=False,
                                       read=False).count()

    def last_message(self):
        return (Message.query.filter_by(conversation_id=self.id)
                .order_by(Message.created_at.desc()).first())


class Message(db.Model):
    __tablename__ = "messages"
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey("conversations.id"),
                                nullable=False, index=True)
    from_user = db.Column(db.Boolean, default=True)    # True = benchmark user
    sender_name = db.Column(db.String(120), default="")
    body = db.Column(db.Text, default="")
    created_at = db.Column(db.Integer, default=0)
    read = db.Column(db.Boolean, default=False)


class Notification(db.Model):
    __tablename__ = "notifications"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False, index=True)
    type = db.Column(db.String(30), default="like")
    actor_blog = db.Column(db.String(120), default="")
    actor_avatar = db.Column(db.String(300), default="")
    post_id = db.Column(db.String(40))
    post_summary = db.Column(db.String(300), default="")
    detail = db.Column(db.Text, default="")
    created_at = db.Column(db.Integer, default=0)
    is_new = db.Column(db.Boolean, default=True)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def current_user():
    uid = session.get("user_id")
    if uid is None:
        return None
    return db.session.get(User, uid)


def login_required(f):
    from functools import wraps

    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("login", next=request.path))
        return f(*args, **kwargs)
    return wrapper


def utc_naive(ts):
    """Epoch seconds -> naive UTC datetime (host-timezone independent)."""
    return datetime.fromtimestamp(ts, tz=timezone.utc).replace(tzinfo=None)


def time_ago(dt_or_ts):
    if isinstance(dt_or_ts, (int, float)):
        dt = utc_naive(dt_or_ts)
    else:
        dt = dt_or_ts
    delta = MIRROR_DATE - dt
    secs = int(delta.total_seconds())
    if secs < 0:
        secs = 0
    if secs < 60:
        return "just now"
    if secs < 3600:
        return f"{secs // 60} minutes ago" if secs >= 120 else "a minute ago"
    if secs < 86400:
        h = secs // 3600
        return f"{h} hours ago" if h > 1 else "an hour ago"
    days = secs // 86400
    if days < 30:
        return f"{days} days ago" if days > 1 else "a day ago"
    months = days // 30
    if months < 12:
        return f"{months} months ago" if months > 1 else "a month ago"
    years = days // 365
    return f"{years} years ago" if years > 1 else "a year ago"


def compact(n):
    if n is None:
        n = 0
    if n >= 1_000_000:
        v = n / 1_000_000
        return f"{v:.1f}M" if v < 10 else f"{int(v)}M"
    if n >= 10_000:
        return f"{n // 1000}K"
    if n >= 1000:
        return f"{n / 1000:.1f}K"
    return str(n)


def render_inline(text):
    """Tumblr post text carries a small HTML subset; pass it through after
    scrubbing scripts/iframes/onclick attributes."""
    if not text:
        return ""
    cleaned = re.sub(r"<\s*(script|iframe|object|embed)[^>]*>.*?<\s*/\s*\1\s*>",
                     "", text, flags=re.S | re.I)
    cleaned = re.sub(r"<\s*(script|iframe|object|embed)[^>]*/?>", "",
                     cleaned, flags=re.I)
    cleaned = re.sub(r"\son\w+\s*=\s*(\"[^\"]*\"|'[^']*'|[^\s>]+)", "",
                     cleaned, flags=re.I)
    cleaned = re.sub(r"javascript:", "", cleaned, flags=re.I)
    return cleaned


# Jinja helpers (registered after their definitions)
app.jinja_env.globals["time_ago"] = time_ago
app.jinja_env.globals["compact"] = compact


def _render_inline_markup(text):
    return Markup(render_inline(text))


app.jinja_env.globals["render_inline"] = _render_inline_markup


def scored_search(query, posts, fields, limit=40):
    terms = [t for t in re.split(r"\W+", query.lower()) if len(t) > 1]
    if not terms:
        return posts.limit(limit).all()
    scored = []
    for p in posts:
        blob = " ".join(str(getattr(p, f) or "") for f in fields).lower()
        score = sum(blob.count(t) for t in terms)
        if score:
            scored.append((score, p.timestamp or 0, p))
    scored.sort(key=lambda r: (-r[0], -r[1]))
    return [p for _, _, p in scored[:limit]]


def post_search_blob(post):
    """Everything a search should cover: the posting blog's name, post text,
    tags, reblog trail and answer metadata."""
    parts = [post.blog.name if post.blog else "", post.summary or "",
             post.tags or "", post.content or "", post.trail or "",
             post.asking_name or ""]
    return " ".join(str(x) for x in parts).lower()


STOP_WORDS = {"the", "a", "an", "in", "on", "at", "to", "for", "of",
              "and", "or", "is", "it", "by", "with", "my", "your",
              "this", "that", "its", "be", "are"}


def scored_post_search(query, limit=40):
    terms = [t for t in re.split(r"\W+", query.lower())
             if len(t) > 2 and t not in STOP_WORDS]
    if not terms:
        return []
    phrase = re.sub(r"[^a-z0-9 ]+", " ", query.lower()).strip()
    phrase = " ".join(phrase.split())
    scored = []
    q = Post.query.filter(Post.state == "published")
    for p in q.all():
        blob = post_search_blob(p)
        score = sum(len(re.findall(rf"\b{re.escape(t)}\b", blob))
                    for t in terms)
        if phrase and phrase in blob:
            score += 12                   # exact phrase match outranks spam
        if score:
            scored.append((score, p.timestamp or 0, p))
    scored.sort(key=lambda r: (-r[0], -r[1]))
    return [p for _, _, p in scored[:limit]]


def base_ctx(**extra):
    user = current_user()
    ctx = {
        "user": user,
        "user_blog": user.blog if user else None,
        "unread_count": (Message.query.join(Conversation)
                         .filter(Conversation.user_id == user.id,
                                 Message.read.is_(False),
                                 Message.from_user.is_(False)).count()
                         if user else 0),
        "notif_count": (Notification.query.filter_by(user_id=user.id,
                                                     is_new=True).count()
                        if user else 0),
        "tumblr_tag_hubs": TagHub.query.order_by(
            TagHub.followers_count_int.desc()).limit(8).all(),
    }
    ctx.update(extra)
    return ctx


def post_ctx(post, user):
    liked = bool(user and Like.query.filter_by(
        user_id=user.id, post_id=post.id).first())
    reblogged = bool(user and Reblog.query.filter_by(
        user_id=user.id, source_post_id=post.id).first())
    following = bool(user and post.blog and Follow.query.filter_by(
        user_id=user.id, blog_id=post.blog.id).first())
    return {"post": post, "liked": liked, "reblogged": reblogged,
            "following": following}


def notes_for(post, limit=30, offset=0):
    rows = (Note.query.filter_by(post_id=post.id)
            .order_by(Note.timestamp.desc(), Note.seq.desc())
            .offset(offset).limit(limit).all())
    # Only linkify note actors whose blog exists on the mirror; the seed's
    # notes reference thousands of upstream likers that are not among the
    # 512 mirrored blogs, and a /blog/<name> link to a missing blog is a
    # dead in-mirror link. Unlinked actors render as plain text with the
    # same styling (same contract as reblog-trail blog names).
    known = None
    for n in rows:
        if known is None:
            from sqlalchemy import select as _select
            known = {row[0] for row in db.session.execute(
                _select(Blog.name)).all()}
        n.blog_exists = n.blog_name in known
    return rows


def paginate(page, total, per_page):
    pages = max(1, (total + per_page - 1) // per_page)
    return {"page": page, "pages": pages, "total": total,
            "has_prev": page > 1, "has_next": page < pages}


# --------------------------------------------------------------------------- #
# Anonymous routes
# --------------------------------------------------------------------------- #
def trending_posts(limit=None, offset=0):
    q = (db.session.query(Trending.post_id).order_by(Trending.position))
    rows = q.all()
    ids = [r[0] for r in rows]
    if offset:
        ids = ids[offset:]
    if limit:
        ids = ids[:limit]
    posts = [db.session.get(Post, pid) for pid in ids]
    return [p for p in posts if p is not None]


@app.route("/")
def index():
    posts = trending_posts(limit=12)
    blogs = (Blog.query.filter_by(primary=True)
             .order_by(Blog.posts_count.desc()).limit(6).all())
    return render_template(
        "index.html", **base_ctx(
            trending=posts,
            blogs=blogs,
            post_list=[post_ctx(p, current_user()) for p in posts]))


@app.route("/explore")
def explore():
    per_page = 12
    page = max(1, request.args.get("page", 1, type=int))
    total = Trending.query.count()
    posts = trending_posts(limit=per_page, offset=(page - 1) * per_page)
    hubs = TagHub.query.order_by(TagHub.followers_count_int.desc()).all()
    return render_template(
        "explore.html", **base_ctx(
            post_list=[post_ctx(p, current_user()) for p in posts],
            pagination=paginate(page, total, per_page), hubs=hubs))


@app.route("/tagged/<tag>")
def tagged(tag):
    tag = tag.strip().lower()
    hub = TagHub.query.filter_by(tag=tag).first()
    per_page = 10
    page = max(1, request.args.get("page", 1, type=int))
    if hub is not None:
        ids = [r[0] for r in (db.session.query(TagPost.post_id)
                              .filter_by(tag=tag)
                              .order_by(TagPost.position).all())]
        total = len(ids)
        chunk = ids[(page - 1) * per_page:page * per_page]
        posts = [db.session.get(Post, pid) for pid in chunk]
        posts = [p for p in posts if p is not None]
    else:
        like = f'%"{tag}"%'
        q = Post.query.filter(Post.tags.like(like))
        total = q.count()
        posts = (q.order_by(Post.note_count.desc())
                 .offset((page - 1) * per_page).limit(per_page).all())
        hub = None
    hub_post = None
    if hub is not None and hub.featured_post_id:
        hub_post = db.session.get(Post, hub.featured_post_id)
    return render_template(
        "tagged.html", **base_ctx(
            tag=tag, hub=hub, hub_post=hub_post,
            post_list=[post_ctx(p, current_user()) for p in posts],
            pagination=paginate(page, total, per_page)))


@app.route("/search")
def search_redirect():
    q = request.args.get("q", "").strip()
    if not q:
        return redirect(url_for("index"))
    return redirect(url_for("search", query=q))


@app.route("/search/<path:query>")
def search(query):
    query = query.strip()
    per_page = 10
    page = max(1, request.args.get("page", 1, type=int))
    tab = request.args.get("tab", "top")
    if tab not in ("top", "recent"):
        tab = "top"
    sq = SearchQuery.query.filter(
        db.func.lower(SearchQuery.query_text) == query.lower()).first()
    if sq is not None:
        ids = sq.ids(f"{tab}_post_ids")
        total = len(ids)
        chunk = ids[(page - 1) * per_page:page * per_page]
        posts = [db.session.get(Post, pid) for pid in chunk]
        posts = [p for p in posts if p is not None]
    else:
        posts_all = scored_post_search(query)
        total = len(posts_all)
        posts = posts_all[(page - 1) * per_page:page * per_page]
        sq = None
    suggestions = None
    if sq is not None:
        suggestions = {
            "blogs": sq.rows("blogs"),
            "tags": sq.rows("tags"),
            "communities": sq.rows("communities"),
            "typeahead_tags": sq.rows("typeahead_tags"),
            "typeahead_blogs": sq.rows("typeahead_blogs"),
        }
    return render_template(
        "search.html", **base_ctx(
            query=query, tab=tab, sq=sq, suggestions=suggestions,
            post_list=[post_ctx(p, current_user()) for p in posts],
            pagination=paginate(page, total, per_page)))


@app.route("/blog/<name>")
def blog_page(name):
    blog = Blog.query.filter_by(name=name).first_or_404()
    per_page = BLOG_PAGE_SIZE
    page = max(1, request.args.get("page", 1, type=int))
    q = blog.posts.filter(Post.state == "published")
    total = q.count()
    posts = (q.order_by(Post.timestamp.desc())
             .offset((page - 1) * per_page).limit(per_page).all())
    user = current_user()
    following = bool(user and Follow.query.filter_by(
        user_id=user.id, blog_id=blog.id).first())
    return render_template(
        "blog.html", **base_ctx(
            blog=blog, following=following,
            post_list=[post_ctx(p, user) for p in posts],
            pagination=paginate(page, total, per_page)))


@app.template_filter('readable_title_color')
def readable_title_color(value):
    """Keep upstream accents only when readable on the mirror's navy page."""
    try:
        color = str(value).lstrip('#')
        if len(color) == 3:
            color = ''.join(c * 2 for c in color)
        if len(color) != 6:
            return '#ffffff'
        rgb = [int(color[i:i + 2], 16) / 255 for i in (0, 2, 4)]
        linear = [v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in rgb]
        luminance = sum(v * w for v, w in zip(linear, (.2126, .7152, .0722)))
        return '#' + color if (luminance + .05) / (.009 + .05) >= 4.5 else '#ffffff'
    except (TypeError, ValueError):
        return '#ffffff'


@app.route("/blog/<name>/archive")
def blog_archive(name):
    blog = Blog.query.filter_by(name=name).first_or_404()
    posts = (blog.posts.filter(Post.state == "published")
             .order_by(Post.timestamp.desc()).all())
    by_month = {}
    for p in posts:
        dt = utc_naive(p.timestamp) if p.timestamp else MIRROR_DATE
        key = dt.strftime("%B %Y")
        by_month.setdefault(key, []).append(p)
    months = list(by_month.items())
    return render_template("archive.html", **base_ctx(
        blog=blog, months=months, archive_total=len(posts)))


@app.route("/blog/<name>/<post_id>")
def permalink(name, post_id):
    blog = Blog.query.filter_by(name=name).first_or_404()
    post = db.session.get(Post, str(post_id))
    if post is None or post.blog_id != blog.id:
        # reblogs live on the reblogger's blog; try to find it anywhere
        post = db.session.get(Post, str(post_id))
        if post is None:
            abort(404)
        return redirect(url_for("permalink",
                                name=post.blog.name, post_id=post.id))
    user = current_user()
    notes = notes_for(post, limit=30)
    note_offset = request.args.get("notes", 0, type=int)
    if note_offset:
        notes = notes_for(post, limit=30, offset=note_offset)
    more_notes = (post.live_note_count() > note_offset + len(notes))
    return render_template(
        "permalink.html", **base_ctx(
            blog=blog, **post_ctx(post, user),
            notes=notes, more_notes=more_notes,
            note_offset=note_offset))


@app.route("/post/<post_id>")
def post_redirect(post_id):
    post = db.session.get(Post, str(post_id))
    if post is None:
        abort(404)
    return redirect(url_for("permalink", name=post.blog.name,
                            post_id=post.id))


# --------------------------------------------------------------------------- #
# Auth
# --------------------------------------------------------------------------- #
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter(
            db.func.lower(User.email) == email).first()
        if user and user.password_hash == stable_password_hash(password):
            session["user_id"] = user.id
            dest = request.form.get("next") or url_for("dashboard")
            return redirect(dest)
        flash("Incorrect email or password. Please try again.", "error")
    return render_template("login.html", **base_ctx())


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "")
        if not email or "@" not in email:
            flash("Please enter a valid email address.", "error")
        elif not re.fullmatch(r"[a-z0-9-]{2,40}", username or ""):
            flash("Username may only contain letters, numbers and dashes.",
                  "error")
        elif User.query.filter(db.func.lower(User.email) == email).first():
            flash("That email is already registered.", "error")
        elif User.query.filter_by(username=username).first():
            flash("That username is taken.", "error")
        elif len(password) < 8:
            flash("Password must be at least 8 characters.", "error")
        else:
            blog = Blog(name=username, title=username,
                        avatar="", primary=False, posts_count=0,
                        can_message=True, ask=True, ask_anon=True,
                        ask_page_title="Ask me anything",
                        background_color="#001935", owner_user_id=None)
            db.session.add(blog)
            db.session.flush()
            user = User(email=email, username=username,
                        password_hash=stable_password_hash(password),
                        display_name=username, blog_id=blog.id)
            db.session.add(user)
            db.session.flush()
            blog.owner_user_id = user.id
            db.session.commit()
            session["user_id"] = user.id
            return redirect(url_for("dashboard"))
    return render_template("register.html", **base_ctx())


@app.route("/logout")
def logout():
    session.pop("user_id", None)
    return redirect(url_for("index"))


# --------------------------------------------------------------------------- #
# Logged-in routes
# --------------------------------------------------------------------------- #
@app.route("/dashboard")
@login_required
def dashboard():
    user = current_user()
    per_page = DASH_PAGE_SIZE
    page = max(1, request.args.get("page", 1, type=int))
    follows = Follow.query.filter_by(user_id=user.id).all()
    blog_ids = [f.blog_id for f in follows]
    total = 0
    posts = []
    if blog_ids:
        q = (Post.query.filter(Post.blog_id.in_(blog_ids),
                               Post.state == "published")
             .order_by(Post.timestamp.desc()))
        total = q.count()
        posts = q.offset((page - 1) * per_page).limit(per_page).all()
    return render_template(
        "dashboard.html", **base_ctx(
            post_list=[post_ctx(p, user) for p in posts],
            pagination=paginate(page, total, per_page),
            following_count=len(blog_ids)))


@app.route("/likes")
@login_required
def likes():
    user = current_user()
    per_page = 12
    page = max(1, request.args.get("page", 1, type=int))
    like_rows = (Like.query.filter_by(user_id=user.id)
                 .order_by(Like.created_at.desc()).all())
    total = len(like_rows)
    chunk = like_rows[(page - 1) * per_page:page * per_page]
    posts = [db.session.get(Post, r.post_id) for r in chunk]
    posts = [p for p in posts if p is not None]
    return render_template(
        "likes.html", **base_ctx(
            post_list=[post_ctx(p, user) for p in posts],
            pagination=paginate(page, total, per_page)))


@app.route("/following")
@login_required
def following():
    user = current_user()
    rows = Follow.query.filter_by(user_id=user.id).order_by(
        Follow.created_at.desc()).all()
    blogs = []
    for r in rows:
        b = db.session.get(Blog, r.blog_id)
        if b:
            blogs.append(b)
    return render_template("following.html", **base_ctx(blogs=blogs))


@app.route("/activity")
@login_required
def activity():
    user = current_user()
    rows = (Notification.query.filter_by(user_id=user.id)
            .order_by(Notification.created_at.desc())
            .limit(60).all())
    for n in rows:
        n.is_new = False
    db.session.commit()
    return render_template("activity.html", **base_ctx(rows=rows))


@app.route("/inbox")
@login_required
def inbox():
    user = current_user()
    convs = (Conversation.query.filter_by(user_id=user.id)
             .order_by(Conversation.updated_at.desc()).all())
    return render_template("inbox.html", **base_ctx(conversations=convs))


@app.route("/inbox/<blog_name>")
@login_required
def conversation(blog_name):
    user = current_user()
    conv = Conversation.query.filter_by(
        user_id=user.id, blog_name=blog_name).first()
    if conv is None:
        conv = Conversation(user_id=user.id, blog_name=blog_name,
                            updated_at=MIRROR_TS)
        db.session.add(conv)
        db.session.commit()
    for m in conv.messages.filter_by(from_user=False, read=False).all():
        m.read = True
    db.session.commit()
    return render_template("conversation.html", **base_ctx(
        conv=conv, blog_name=blog_name))


@app.route("/inbox/<blog_name>/send", methods=["POST"])
@login_required
def send_message(blog_name):
    user = current_user()
    body = request.form.get("body", "").strip()
    if body:
        conv = Conversation.query.filter_by(
            user_id=user.id, blog_name=blog_name).first()
        if conv is None:
            conv = Conversation(user_id=user.id, blog_name=blog_name,
                                updated_at=MIRROR_TS)
            db.session.add(conv)
            db.session.flush()
        msg = Message(conversation_id=conv.id, from_user=True,
                       sender_name=user.username, body=body,
                       created_at=MIRROR_TS)
        db.session.add(msg)
        conv.updated_at = MIRROR_TS
        db.session.commit()
        flash("Message sent.", "ok")
    return redirect(url_for("conversation", blog_name=blog_name))


@app.route("/blog/<name>/ask", methods=["GET", "POST"])
def ask(name):
    blog = Blog.query.filter_by(name=name).first_or_404()
    if not blog.ask:
        flash("This blog does not accept asks.", "error")
        return redirect(url_for("blog_page", name=name))
    if request.method == "POST":
        body = request.form.get("body", "").strip()
        anon = bool(request.form.get("anon")) and blog.ask_anon
        if body:
            user = current_user()
            owner = None
            if blog.owner_user_id:
                owner = db.session.get(User, blog.owner_user_id)
            if owner is not None:
                conv = Conversation.query.filter_by(
                    user_id=owner.id, blog_name=user.username if user and not anon
                    else "anonymous").first()
                if conv is None:
                    conv = Conversation(
                        user_id=owner.id,
                        blog_name=user.username if user and not anon else "anonymous",
                        updated_at=MIRROR_TS)
                    db.session.add(conv)
                    db.session.flush()
                db.session.add(Message(
                    conversation_id=conv.id, from_user=False,
                    sender_name=("anonymous" if anon
                                 else (user.username if user else "anonymous")),
                    body=body, created_at=MIRROR_TS))
                db.session.commit()
            flash(f"Your question has been sent to {blog.display_title()}.",
                  "ok")
            return redirect(url_for("blog_page", name=name))
        flash("Please write a question first.", "error")
    return render_template("ask.html", **base_ctx(blog=blog))


@app.route("/new/post", methods=["GET", "POST"])
@login_required
def new_post():
    user = current_user()
    blog = user.blog
    post_type = request.values.get("type", "text")
    if post_type not in ("text", "photo", "quote", "link"):
        post_type = "text"
    if request.method == "POST":
        body = request.form.get("body", "").strip()
        title = request.form.get("title", "").strip()
        tags = [t.strip().lower().lstrip("#") for t in
                request.form.get("tags", "").split(",") if t.strip()]
        image_url = ""
        blocks = []
        if post_type == "photo":
            upload = request.files.get("image")
            if upload and upload.filename:
                fname = secure_filename(upload.filename)
                if not fname:
                    fname = "upload.jpg"
                updir = os.path.join(BASE_DIR, "instance", "uploads")
                os.makedirs(updir, exist_ok=True)
                stamp = datetime.now().strftime("%Y%m%d%H%M%S")
                fname = f"{stamp}_{fname}"
                upload.save(os.path.join(updir, fname))
                image_url = f"/uploads/{fname}"
                blocks.append({"type": "image", "media": {
                    "url": image_url, "width": 0, "height": 0}})
            elif request.form.get("image_path"):
                image_url = request.form.get("image_path")
                blocks.append({"type": "image", "media": {
                    "url": image_url, "width": 0, "height": 0}})
            if body:
                blocks.append({"type": "text", "text": body})
        elif post_type == "quote":
            quote = request.form.get("quote", "").strip()
            source = request.form.get("source", "").strip()
            if not quote:
                flash("Please add a quote.", "error")
                return redirect(url_for("new_post", type="quote"))
            blocks.append({"type": "quote", "text": quote,
                           "source": source})
        elif post_type == "link":
            link = request.form.get("link", "").strip()
            if not link:
                flash("Please add a URL.", "error")
                return redirect(url_for("new_post", type="link"))
            blocks.append({"type": "link", "url": link, "title": title,
                           "description": body})
        else:
            if title:
                blocks.append({"type": "text", "text": title,
                               "subtype": "heading"})
            if body:
                blocks.append({"type": "text", "text": body})
        if not blocks:
            flash("Your post needs some content.", "error")
            return redirect(url_for("new_post", type=post_type))
        post = Post(
            id=new_post_id(), blog_id=blog.id, type=post_type,
            original_type=post_type, content=json.dumps(blocks),
            layout="[]", trail="[]", tags=json.dumps(tags),
            timestamp=MIRROR_TS,
            created_at=MIRROR_TS,
            date_str=MIRROR_DATE.strftime("%Y-%m-%d %H:%M:%S GMT"),
            post_url=f"https://{blog.name}.tumblr.com/",
            summary=(title or body or (request.form.get("quote", "").strip() if post_type == "quote" else "") or "New post")[:120],
            state="published", user_created=True)
        db.session.add(post)
        blog.posts_count = (blog.posts_count or 0) + 1
        db.session.commit()
        flash("Post created.", "ok")
        return redirect(url_for("permalink", name=blog.name,
                                post_id=post.id))
    return render_template("post_new.html", **base_ctx(
        post_type=post_type, blog=blog))


def new_post_id():
    """Unique id for mirror-created posts (runtime only; the seed DB uses
    upstream ids). Millisecond timestamps keep ids unique across actions."""
    import time as _time
    while True:
        pid = str(int(_time.time() * 1000))
        if db.session.get(Post, pid) is None:
            return pid


@app.route("/uploads/<path:fname>")
def uploads(fname):
    updir = os.path.join(BASE_DIR, "instance", "uploads")
    return send_from_directory(updir, fname)


@app.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    user = current_user()
    blog = user.blog
    if request.method == "POST":
        action = request.form.get("action", "profile")
        if action == "profile":
            title = request.form.get("title", "").strip()
            description = request.form.get("description", "").strip()
            if title:
                blog.title = title
            blog.description = description
            db.session.commit()
            flash("Blog settings saved.", "ok")
        elif action == "password":
            old = request.form.get("old_password", "")
            new = request.form.get("new_password", "")
            if user.password_hash != stable_password_hash(old):
                flash("Current password is incorrect.", "error")
            elif len(new) < 8:
                flash("New password must be at least 8 characters.", "error")
            else:
                user.password_hash = stable_password_hash(new)
                db.session.commit()
                flash("Password updated.", "ok")
        return redirect(url_for("settings"))
    return render_template("settings.html", **base_ctx())


# --------------------------------------------------------------------------- #
# Actions
# --------------------------------------------------------------------------- #
@app.route("/post/<post_id>/like", methods=["POST"])
@login_required
def toggle_like(post_id):
    user = current_user()
    post = db.session.get(Post, str(post_id))
    if post is None:
        abort(404)
    like = Like.query.filter_by(user_id=user.id, post_id=post.id).first()
    if like:
        db.session.delete(like)
        db.session.commit()
        return jsonify({"liked": False,
                        "like_count": post.live_like_count(), "note_count": post.live_note_count()})
    db.session.add(Like(user_id=user.id, post_id=post.id,
                        created_at=MIRROR_TS))
    db.session.commit()
    return jsonify({"liked": True,
                    "like_count": post.live_like_count(), "note_count": post.live_note_count()})


@app.route("/post/<post_id>/reblog", methods=["GET", "POST"])
@login_required
def reblog(post_id):
    user = current_user()
    post = db.session.get(Post, str(post_id))
    if post is None:
        abort(404)
    if request.method == "POST":
        comment = request.form.get("comment", "").strip()
        new_id = new_post_id()
        trail = json.loads(post.trail or "[]")
        if not trail:
            trail = [{
                "blog_name": post.blog.name,
                "blog_title": post.blog.display_title(),
                "blog_avatar": post.blog.avatar,
                "content": post.blocks(),
            }]
        new_post = Post(
            id=new_id, blog_id=user.blog.id, type=post.type,
            original_type=post.original_type, content="[]", layout="[]",
            trail=json.dumps(trail),
            tags=json.dumps(post.tag_list()),
            timestamp=MIRROR_TS,
            created_at=MIRROR_TS,
            date_str=MIRROR_DATE.strftime("%Y-%m-%d %H:%M:%S GMT"),
            post_url=f"https://{user.blog.name}.tumblr.com/",
            summary=(comment or post.summary or "Reblog")[:120],
            state="published", reblog_of_id=post.id, user_created=True)
        if comment:
            new_post.content = json.dumps(
                [{"type": "text", "text": comment}])
        db.session.add(new_post)
        db.session.add(Reblog(user_id=user.id, source_post_id=post.id,
                              new_post_id=new_id, comment=comment,
                              created_at=MIRROR_TS))
        post.reblog_count = (post.reblog_count or 0) + 1
        user.blog.posts_count = (user.blog.posts_count or 0) + 1
        db.session.commit()
        flash("Reblogged to your blog.", "ok")
        return redirect(url_for("permalink", name=user.blog.name,
                                post_id=new_id))
    return render_template("reblog.html", **base_ctx(
        **post_ctx(post, user)))


@app.route("/blog/<name>/follow", methods=["POST"])
@login_required
def toggle_follow(name):
    user = current_user()
    blog = Blog.query.filter_by(name=name).first_or_404()
    follow = Follow.query.filter_by(user_id=user.id, blog_id=blog.id).first()
    if follow:
        db.session.delete(follow)
        db.session.commit()
        return jsonify({"following": False})
    db.session.add(Follow(user_id=user.id, blog_id=blog.id,
                          created_at=MIRROR_TS))
    db.session.commit()
    return jsonify({"following": True})


@app.route("/_health")
def health():
    try:
        counts = {
            "ok": True,
            "site": "tumblr",
            "blogs": Blog.query.count(),
            "posts": Post.query.count(),
            "tags": TagHub.query.count(),
            "notes": Note.query.count(),
            "users": User.query.count(),
        }
    except Exception:                                  # noqa: BLE001
        return jsonify({"ok": False}), 500
    return jsonify(counts)


# --------------------------------------------------------------------------- #
# Bootstrap
# --------------------------------------------------------------------------- #
def create_schema():
    db.create_all()


def main():
    create_schema()
    seed_database()
    seed_benchmark_users()


def seed_database():
    if Post.query.count() > 0:
        return
    from seed_data import build_seed_rows
    build_seed_rows()


def seed_benchmark_users():
    if User.query.filter_by(email="alice.j@test.com").first():
        return
    from seed_data import build_benchmark_users
    build_benchmark_users()


BOOTSTRAP = os.environ.get("WEBSYN_SKIP_BOOTSTRAP") != "1"

if BOOTSTRAP:
    with app.app_context():
        create_schema()
        seed_database()
        seed_benchmark_users()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 40127))
    app.run(host="0.0.0.0", port=port, debug=False)
