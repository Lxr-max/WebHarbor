"""Deterministic build-time seeder for the tumblr mirror.

Materializes the runtime DB from the frozen source_data/ snapshots (captured
from www.tumblr.com on 2026-09-28; see provenance.json). Called at image
build time (Dockerfile stanza, PYTHONHASHSEED=0) and defensively at boot;
both seed functions early-return when their data already exists, so
/reset/tumblr stays byte-identical.

Benchmark fixtures (users, their blogs, follows, likes, reblogs, inbox
conversations, notifications) are mirror-native and reference real seeded
blogs and posts; every timestamp is pinned relative to MIRROR_DATE so the
seed is byte-stable across builds.
"""
from __future__ import annotations

import calendar
import json
import os
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault("WEBSYN_SKIP_BOOTSTRAP", "1")

from app import (Blog, Conversation, Follow, Like, Message, Note,  # noqa: E402
                 Notification, Post, Reblog, SearchQuery, TagHub, TagPost,
                 Trending, User, app, db, stable_password_hash)

BASE_DIR = Path(__file__).resolve().parent
SOURCE = BASE_DIR / "source_data"

MIRROR_DATE = datetime(2026, 9, 28, 12, 0, 0)
# Interpret MIRROR_DATE as UTC regardless of the build host's timezone so
# the seed is byte-identical on any machine (and matches the app's
# MIRROR_TS, which uses the same timegm pinning).
MIRROR_TS = calendar.timegm(MIRROR_DATE.timetuple())
BENCHMARK_PASSWORD = "TestPass123!"

BENCHMARK_USERS = [
    {"email": "alice.j@test.com", "username": "alice-j",
     "display": "Alice Johnson",
     "bio": "<p>Art history grad. Pixel art appreciator. Ask me about "
            "museum archives.</p>",
     "title": "Alice's Archive"},
    {"email": "bob.c@test.com", "username": "bob-c",
     "display": "Bob Chen",
     "bio": "<p>Concept art and skate photography. Mostly reblogging.</p>",
     "title": "bob's sketchbook"},
    {"email": "carol.d@test.com", "username": "carol-d",
     "display": "Carol Davis",
     "bio": "<p>Cottagecore cabin dreams and one very round cat.</p>",
     "title": "cabin fever"},
    {"email": "david.k@test.com", "username": "david-k",
     "display": "David Kim",
     "bio": "<p>Math visualizations and old maps.</p>",
     "title": "david's notebook"},
]

# Which real blogs each benchmark user follows (upstream blog names).
USER_FOLLOWS = {
    "alice-j": ["staff", "waneella", "meolog", "nasa", "writingprompts",
                "cabinporn"],
    "bob-c": ["sparth", "sebastiancuri", "shutternoise", "ludwigdanner",
              "nasa"],
    "carol-d": ["waneella", "puffychi", "paokai", "boschintegral-photo",
                "sablingart", "cabinporn"],
    "david-k": ["visualizingmath", "natgeofound", "staff", "meolog",
                "nasa"],
}

# Cross-follows between benchmark users (their dashboards mix user posts in).
USER_CROSS_FOLLOWS = {
    "alice-j": [],
    "bob-c": ["alice-j"],
    "carol-d": ["alice-j", "bob-c"],
    "david-k": ["bob-c"],
}


def load(name: str):
    return json.loads((SOURCE / name).read_text(encoding="utf-8"))


def days_ago(n, hours=0):
    return MIRROR_TS - n * 86400 - hours * 3600


def utc_date_str(ts):
    """Epoch seconds -> "YYYY-MM-DD HH:MM:SS GMT" (host-TZ independent)."""
    return datetime.fromtimestamp(
        ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S GMT")


# --------------------------------------------------------------------------- #
# Upstream content
# --------------------------------------------------------------------------- #
def build_seed_rows() -> None:
    if Post.query.count() > 0:
        return

    blogs_src = load("blogs.json")
    posts_src = load("posts.json")
    tags_src = load("tags.json")
    searches_src = load("searches.json")
    explore_src = load("explore.json")
    notes_src = load("notes.json")

    # ---- blogs ----------------------------------------------------------- #
    blog_ids = {}
    for b in blogs_src:
        row = Blog(
            name=b["name"], title=b.get("title") or "",
            description=b.get("description") or "",
            url=b.get("url") or "",
            updated=b.get("updated") or 0,
            primary=bool(b.get("primary")),
            posts_count=b.get("posts_count") or 0,
            total_posts_upstream=b.get("total_posts_upstream"),
            avatar=b.get("avatar") or "",
            avatar_shape=b.get("avatar_shape") or "circle",
            header_image=b.get("header_image") or "",
            background_color=(b.get("theme") or {}).get("background_color")
            or "#001935",
            title_color=(b.get("theme") or {}).get("title_color") or "#ffffff",
            body_font=(b.get("theme") or {}).get("body_font")
            or "Helvetica Neue",
            link_color=(b.get("theme") or {}).get("link_color") or "#00b8ff",
            can_message=bool(b.get("can_message")),
            is_nsfw=bool(b.get("is_nsfw")),
            is_adult=bool(b.get("is_adult")),
            can_be_followed=bool(b.get("can_be_followed", True)),
            ask=bool(b.get("ask")),
            ask_anon=bool(b.get("ask_anon")),
            ask_page_title=b.get("ask_page_title") or "",
            share_likes=bool(b.get("share_likes")),
            share_following=bool(b.get("share_following")),
        )
        db.session.add(row)
        blog_ids[b["name"]] = row
    db.session.flush()

    # ---- posts ------------------------------------------------------------ #
    for p in posts_src:
        blog = blog_ids.get(p["blog_name"])
        if blog is None:
            continue
        row = Post(
            id=str(p["id"]), blog_id=blog.id,
            type=p.get("type") or "text",
            original_type=p.get("original_type") or "regular",
            is_blocks_post_format=bool(p.get("is_blocks_post_format", True)),
            content=json.dumps(p.get("content") or []),
            layout=json.dumps(p.get("layout") or []),
            trail=json.dumps(p.get("trail") or []),
            tags=json.dumps(p.get("tags") or []),
            timestamp=p.get("timestamp") or 0,
            date_str=p.get("date") or "",
            post_url=p.get("post_url") or "",
            slug=p.get("slug") or "",
            summary=p.get("summary") or "",
            note_count=p.get("note_count") or 0,
            like_count=p.get("like_count") or 0,
            reblog_count=p.get("reblog_count") or 0,
            reply_count=p.get("reply_count") or 0,
            state=p.get("state") or "published",
            asking_name=p.get("asking_name"),
            asking_url=p.get("asking_url"),
            asking_avatar=p.get("asking_avatar") or "",
        )
        db.session.add(row)
    db.session.flush()

    # ---- trending feed (home + explore, upstream order) ------------------ #
    for i, pid in enumerate(explore_src.get("trending_post_ids") or []):
        db.session.add(Trending(post_id=str(pid), position=i))

    # ---- tag hubs + tag membership ---------------------------------------- #
    for t in tags_src:
        hub = t.get("hub") or {}
        row = TagHub(
            tag=t["tag"], hub_name=hub.get("hub_name") or t["tag"],
            background_color=hub.get("background_color") or "#35465d",
            header_image=hub.get("header_image") or "",
            header_link=hub.get("header_link") or "",
            featured_post_id=hub.get("post_id") or "",
            blog_name=hub.get("blog_name") or "",
            blog_avatar=hub.get("blog_avatar") or "",
            followers_count=hub.get("followers_count") or "",
            followers_count_int=hub.get("followers_count_int") or 0,
            new_posts_count=hub.get("new_posts_count") or "",
            new_posts_count_int=hub.get("new_posts_count_int") or 0,
            post_count_int=hub.get("post_count_int") or 0,
            editorial_description=hub.get("editorial_description") or "",
            editorial_description_text=
                hub.get("editorial_description_text") or "",
            related_tags=json.dumps(t.get("related_tags") or []),
        )
        db.session.add(row)
        db.session.flush()
        for i, pid in enumerate(t.get("post_ids") or []):
            db.session.add(TagPost(tag=t["tag"], post_id=str(pid),
                                   position=i))

    # ---- saved searches ---------------------------------------------------- #
    for s in searches_src:
        db.session.add(SearchQuery(
            query_text=s["query"],
            top_post_ids=json.dumps(s.get("top_post_ids") or []),
            recent_post_ids=json.dumps(s.get("recent_post_ids") or []),
            blogs=json.dumps(s.get("blogs") or []),
            tags=json.dumps(s.get("tags") or []),
            communities=json.dumps(s.get("communities") or []),
            typeahead_tags=json.dumps(s.get("typeahead_tags") or []),
            typeahead_blogs=json.dumps(s.get("typeahead_blogs") or []),
        ))

    # ---- notes (likes/reblogs/replies on high-note posts) ------------------ #
    for n in notes_src:
        for i, note in enumerate(n.get("notes") or []):
            db.session.add(Note(
                post_id=str(n["post_id"]), seq=i,
                type=note.get("type") or "like",
                timestamp=note.get("timestamp") or 0,
                blog_name=note.get("blog_name") or "",
                blog_title=note.get("blog_title") or "",
                blog_url=note.get("blog_url") or "",
                avatar=note.get("avatar") or "",
                avatar_shape=note.get("avatar_shape") or "circle",
                reply_text=note.get("reply_text"),
                added_text=note.get("added_text"),
            ))
    db.session.commit()


# --------------------------------------------------------------------------- #
# Benchmark fixtures (mirror-native)
# --------------------------------------------------------------------------- #
def _pick_post(blog_name, position=0):
    blog = Blog.query.filter_by(name=blog_name).first()
    if blog is None:
        return None
    q = blog.posts.filter(Post.state == "published")
    q = q.order_by(Post.timestamp.desc())
    return q.offset(position).first()


def build_benchmark_users() -> None:
    if User.query.filter_by(email="alice.j@test.com").first():
        return

    users = {}
    for spec in BENCHMARK_USERS:
        blog = Blog(
            name=spec["username"], title=spec["title"],
            description=spec["bio"],
            url=f"https://{spec['username']}.tumblr.com/",
            updated=MIRROR_TS, primary=False, posts_count=0,
            avatar="", avatar_shape="circle", header_image="",
            background_color="#001935", title_color="#ffffff",
            body_font="Helvetica Neue", link_color="#00b8ff",
            can_message=True, ask=True, ask_anon=True,
            ask_page_title="Ask me anything", share_likes=True,
            share_following=True)
        db.session.add(blog)
        db.session.flush()
        user = User(email=spec["email"], username=spec["username"],
                    password_hash=stable_password_hash(BENCHMARK_PASSWORD),
                    display_name=spec["display"], blog_id=blog.id)
        db.session.add(user)
        db.session.flush()
        blog.owner_user_id = user.id
        users[spec["username"]] = user
    db.session.flush()

    # ---- own blog posts (mirror-native text/quote/link) ------------------- #
    own_posts = {}
    specs = {
        "alice-j": [
            {"type": "text",
             "blocks": [{"type": "text", "text": "hello tumblr",
                         "subtype": "heading"},
                        {"type": "text",
                         "text": "<p>Setting up my archive of pixel art "
                         "references and museum scans. Follow along if you "
                         "like slow, deliberate art.</p>"}],
             "tags": ["introduction", "art history", "pixel art"],
             "summary": "hello tumblr", "days": 21},
            {"type": "quote",
             "blocks": [{"type": "quote",
                         "text": "Art is not what you see, but what you "
                         "make others see.",
                         "source": "often attributed to Edgar Degas"}],
             "tags": ["art", "quote"],
             "summary": "Art is not what you see...", "days": 12},
            {"type": "link",
             "blocks": [{"type": "link",
                         "url": "https://waneella.tumblr.com/",
                         "title": "WANEELLA pixel art",
                         "description": "The pixel art blog that got me to "
                         "join this site in the first place."}],
             "tags": ["pixel art", "inspiration"],
             "summary": "WANEELLA pixel art", "days": 5},
        ],
        "bob-c": [
            {"type": "text",
             "blocks": [{"type": "text", "text": "sketch dump: week one",
                         "subtype": "heading"},
                        {"type": "text",
                         "text": "<p>Been copying Sparth's shapes every "
                         "evening. My linework is finally starting to hold "
                         "together.</p>"}],
             "tags": ["sketchbook", "concept art", "practice"],
             "summary": "sketch dump: week one", "days": 18},
            {"type": "quote",
             "blocks": [{"type": "quote",
                         "text": "Draw with your arm, not your wrist.",
                         "source": "every art teacher ever"}],
             "tags": ["art advice", "quote"],
             "summary": "Draw with your arm...", "days": 8},
        ],
        "carol-d": [
            {"type": "text",
             "blocks": [{"type": "text", "text": "cabin wishlist, part one",
                         "subtype": "heading"},
                        {"type": "text",
                         "text": "<p>Wood stove, wall of books, one very "
                         "round cat asleep on the windowsill. That's it. "
                         "That's the dream.</p>"}],
             "tags": ["cabinporn", "cottagecore", "wishlist"],
             "summary": "cabin wishlist, part one", "days": 15},
            {"type": "text",
             "blocks": [{"type": "text", "text": "the cat update",
                         "subtype": "heading"},
                        {"type": "text",
                         "text": "<p>Mochi has claimed the rocking chair. "
                         "Negotiations have failed.</p>"}],
             "tags": ["cats", "cottagecore"],
             "summary": "the cat update", "days": 3},
        ],
        "david-k": [
            {"type": "text",
             "blocks": [{"type": "text", "text": "why i love visual proofs",
                         "subtype": "heading"},
                        {"type": "text",
                         "text": "<p>A good diagram is worth a thousand "
                         "lemmas. I'll be posting my favorites from the "
                         "visualizingmath archives.</p>"}],
             "tags": ["math", "visualization", "mathematics"],
             "summary": "why i love visual proofs", "days": 20},
            {"type": "link",
             "blocks": [{"type": "link",
                         "url": "https://www.tumblr.com/tagged/math",
                         "title": "the math tag",
                         "description": "Where I do most of my lurking "
                         "these days."}],
             "tags": ["math", "link"],
             "summary": "the math tag", "days": 9},
        ],
    }
    for username, rows in specs.items():
        user = users[username]
        blog = user.blog
        own_posts[username] = []
        for spec in rows:
            post = Post(
                id=f"u_{username}_{spec['days']}", blog_id=blog.id,
                type=spec["type"], original_type=spec["type"],
                is_blocks_post_format=True,
                content=json.dumps(spec["blocks"]), layout="[]", trail="[]",
                tags=json.dumps(spec["tags"]),
                timestamp=days_ago(spec["days"]),
                date_str=utc_date_str(days_ago(spec["days"])),
                post_url=f"https://{blog.name}.tumblr.com/",
                summary=spec["summary"], note_count=0, like_count=0,
                reblog_count=0, reply_count=0, state="published",
                user_created=True, created_at=days_ago(spec["days"]))
            db.session.add(post)
            blog.posts_count = (blog.posts_count or 0) + 1
            own_posts[username].append(post)
    db.session.flush()

    # ---- follows ----------------------------------------------------------- #
    for username, blog_names in USER_FOLLOWS.items():
        user = users[username]
        for i, name in enumerate(blog_names):
            blog = Blog.query.filter_by(name=name).first()
            if blog is None:
                continue
            db.session.add(Follow(user_id=user.id, blog_id=blog.id,
                                  created_at=days_ago(30 - i)))
    for username, names in USER_CROSS_FOLLOWS.items():
        user = users[username]
        for i, name in enumerate(names):
            blog = Blog.query.filter_by(name=name).first()
            if blog is None:
                continue
            db.session.add(Follow(user_id=user.id, blog_id=blog.id,
                                  created_at=days_ago(10 - i)))
    db.session.flush()

    # ---- likes (deterministic picks from followed blogs) -------------------- #
    like_plan = {
        "alice-j": [("waneella", 0), ("waneella", 1), ("meolog", 0),
                    ("nasa", 0), ("nasa", 1), ("staff", 0), ("staff", 1),
                    ("cabinporn", 0), ("writingprompts", 0), ("meolog", 1)],
        "bob-c": [("sparth", 0), ("sparth", 1), ("sebastiancuri", 0),
                  ("shutternoise", 0), ("ludwigdanner", 0), ("nasa", 0),
                  ("nasa", 2)],
        "carol-d": [("puffychi", 0), ("puffychi", 1), ("paokai", 0),
                    ("boschintegral-photo", 0), ("sablingart", 0),
                    ("cabinporn", 0), ("cabinporn", 1)],
        "david-k": [("visualizingmath", 0), ("natgeofound", 0),
                    ("natgeofound", 1), ("meolog", 0), ("nasa", 1),
                    ("staff", 2)],
    }
    for username, picks in like_plan.items():
        user = users[username]
        for i, (blog_name, pos) in enumerate(picks):
            post = _pick_post(blog_name, pos)
            if post is None:
                continue
            db.session.add(Like(user_id=user.id, post_id=post.id,
                                created_at=days_ago(6 - i % 7, hours=i)))
    db.session.flush()

    # ---- cross-user likes on each other's posts ----------------------------- #
    cross_likes = [
        ("bob-c", "alice-j", 0), ("carol-d", "alice-j", 0),
        ("david-k", "bob-c", 0), ("alice-j", "carol-d", 1),
        ("carol-d", "bob-c", 0), ("david-k", "alice-j", 1),
    ]
    for actor, owner, pos in cross_likes:
        post = own_posts.get(owner, [None] * 10)[pos] if len(
            own_posts.get(owner, [])) > pos else None
        if post is None:
            continue
        db.session.add(Like(user_id=users[actor].id, post_id=post.id,
                            created_at=days_ago(4)))
    db.session.flush()

    # ---- seeded reblogs (with the upstream trail) --------------------------- #
    reblog_plan = [
        ("alice-j", "waneella", 0,
         "this is the one that made me start the archive"),
        ("bob-c", "sparth", 0, "shapes shapes shapes"),
        ("carol-d", "cabinporn", 0, "someday."),
    ]
    for username, blog_name, pos, comment in reblog_plan:
        user = users[username]
        src = _pick_post(blog_name, pos)
        if src is None:
            continue
        trail = json.loads(src.trail or "[]")
        if not trail:
            trail = [{"blog_name": src.blog.name,
                      "blog_title": src.blog.display_title(),
                      "blog_avatar": src.blog.avatar,
                      "content": json.loads(src.content or "[]")}]
        new_id = f"u_{username}_reblog_{src.id[-6:]}"
        db.session.add(Post(
            id=new_id, blog_id=user.blog.id, type=src.type,
            original_type=src.original_type,
            content=json.dumps([{"type": "text", "text": comment}]),
            layout="[]", trail=json.dumps(trail),
            tags=json.dumps(src.tag_list()),
            timestamp=days_ago(2), created_at=days_ago(2),
            date_str=utc_date_str(days_ago(2)),
            post_url=f"https://{user.blog.name}.tumblr.com/",
            summary=(comment or src.summary or "Reblog")[:120],
            note_count=0, like_count=0, reblog_count=0, reply_count=0,
            state="published", reblog_of_id=src.id, user_created=True))
        db.session.add(Reblog(user_id=user.id, source_post_id=src.id,
                              new_post_id=new_id, comment=comment,
                              created_at=days_ago(2)))
        user.blog.posts_count = (user.blog.posts_count or 0) + 1
    db.session.flush()

    # ---- inbox conversations ------------------------------------------------ #
    conv_specs = {
        "alice-j": [
            ("staff", [
                (True, "alice-j",
                 "Hi! Is there a way to keep two side blogs from showing in "
                 "the same feed?", days_ago(9)),
                (False, "staff",
                 "Welcome to Tumblr! You can keep feeds separate by "
                 "following different blogs from each account. Everything "
                 "stays on your dashboard in one place though.", days_ago(9)),
                (True, "alice-j",
                 "Got it, thanks! Loving the new pixel art tag page by the "
                 "way.", days_ago(8)),
                (False, "staff",
                 "Glad to hear it! The tag pages got a fresh coat of paint "
                 "this month. Let us know if anything else comes up.",
                 days_ago(8)),
            ]),
            ("bob-c", [
                (True, "alice-j",
                 "Your Degas quote post is going around the art history "
                 "tag again, just so you know.", days_ago(3)),
                (False, "bob-c", "ha! classic. thanks for the heads up.",
                 days_ago(3)),
            ]),
        ],
        "bob-c": [
            ("nasa", [
                (True, "bob-c",
                 "Which of the Artemis posts has the launch pad photo?",
                 days_ago(6)),
                (False, "nasa",
                 "The Artemis II wake-up songs post has the pad at "
                 "sunrise. Follow the tag for more!", days_ago(6)),
            ]),
        ],
        "carol-d": [
            ("puffychi", [
                (True, "carol-d",
                 "your kawaii scans are the best thing on my dashboard",
                 days_ago(5)),
                (False, "puffychi",
                 "aaah thank you!! 💕 check the pinned post for the full set",
                 days_ago(5)),
            ]),
        ],
        "david-k": [
            ("meolog", [
                (True, "david-k",
                 "Is the Reflections series available as prints?",
                 days_ago(4)),
                (False, "meolog",
                 "Some of the poetry series is, yes — send an ask and I'll "
                 "list the available ones.", days_ago(4)),
            ]),
        ],
    }
    for username, convs in conv_specs.items():
        user = users[username]
        for blog_name, messages in convs:
            conv = Conversation(user_id=user.id, blog_name=blog_name,
                                updated_at=messages[-1][3])
            db.session.add(conv)
            db.session.flush()
            for from_user, sender, body, ts in messages:
                db.session.add(Message(
                    conversation_id=conv.id, from_user=from_user,
                    sender_name=sender, body=body, created_at=ts,
                    read=True))
    db.session.flush()

    # unread messages waiting in inboxes
    unread_specs = [
        ("alice-j", "bob-c",
         "also — sketch dump part two is up, would love your take on the "
         "linework before i ink it",
         days_ago(1, hours=2)),
        ("bob-c", "alice-j",
         "also — sketch dump is up, would love your opinion on the linework",
         days_ago(1)),
        ("carol-d", "puffychi",
         "the new sticker set is adorable, is it in the shop yet?",
         days_ago(1, hours=6)),
    ]
    for username, other, body, ts in unread_specs:
        user = users[username]
        conv = Conversation.query.filter_by(
            user_id=user.id, blog_name=other).first()
        if conv is None:
            conv = Conversation(user_id=user.id, blog_name=other,
                                updated_at=ts)
            db.session.add(conv)
            db.session.flush()
        db.session.add(Message(conversation_id=conv.id, from_user=False,
                               sender_name=other, body=body, created_at=ts,
                               read=False))
        if conv.updated_at < ts:
            conv.updated_at = ts

    # ---- activity notifications ---------------------------------------------- #
    notif_specs = [
        ("alice-j", "like", "bob-c", 0, "hello tumblr"),
        ("alice-j", "reblog", "carol-d", 0, "hello tumblr"),
        ("alice-j", "follow", "david-k", None, ""),
        ("alice-j", "message", "bob-c", None, ""),
        ("bob-c", "like", "david-k", 0, "sketch dump: week one"),
        ("bob-c", "follow", "alice-j", None, ""),
        ("carol-d", "like", "alice-j", 1, "the cat update"),
        ("carol-d", "follow", "bob-c", None, ""),
        ("david-k", "like", "carol-d", 1, "cabin wishlist, part one"),
        ("david-k", "message", "meolog", None, ""),
    ]
    for username, kind, actor, pos, summary in notif_specs:
        user = users[username]
        post_id = None
        if kind in ("like", "reblog"):
            posts = own_posts.get(username, [])
            post_id = posts[pos].id if pos < len(posts) else None
        actor_blog = Blog.query.filter_by(name=actor).first()
        db.session.add(Notification(
            user_id=user.id, type=kind, actor_blog=actor,
            actor_avatar=actor_blog.avatar if actor_blog else "",
            post_id=post_id, post_summary=summary,
            created_at=days_ago(2), is_new=True))
    db.session.commit()


if __name__ == "__main__":
    with app.app_context():
        from app import create_schema
        create_schema()
        build_seed_rows()
        build_benchmark_users()
        print("[seed] done")
