#!/usr/bin/env python3
"""Add the real teaboot blog (www.tumblr.com/teaboot) to the frozen snapshots.

teaboot is the original blog in the reblog trail of the high-note CCTV post
(828957539611869184); the trail links to /blog/teaboot, which 404s because
the original snapshot never captured the blog itself (only 3 of its trail
avatars). Upstream the blog exists (200), so this script:

  1. GETs /api/v2/blog/teaboot/info and /api/v2/blog/teaboot/posts
     (limit=5, reblog_info=true) and stores both verbatim under
     scraped_data/blogs/teaboot/ (build-time-only provenance).
  2. Normalizes the blog row with the exact field mapping build_source_data
     applies to primary blogs — with one deviation: no header image is
     referenced, so the change adds zero new managed assets (the avatar is
     already mirrored at static/images/avatars/teaboot.png, downloaded from
     the same upstream 128px variant during the original build).
  3. Normalizes the text-only posts from the captured feed (no image/video/
     audio blocks anywhere, own content or trail — again zero new managed
     assets) with the same block mapping build_posts uses.
  4. Merges both into source_data/blogs.json and source_data/posts.json,
     keeping each file's sorted order (blogs by name, posts by name+id).

Re-running is safe: verbatim captures are overwritten, source_data is
re-merged from the captures.
"""
from __future__ import annotations

import json
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_source_data import ImagePlan, avatar_path, normalize_blocks  # noqa: E402

TYPE_MAP = {"regular": "text", "note": "answer", "photo": "photo"}

BASE = Path(__file__).resolve().parents[1]          # sites/tumblr
SRC = BASE / "scraped_data" / "blogs" / "teaboot"
DST = BASE / "source_data"

API = "https://www.tumblr.com/api/v2"
TOKEN = "aIcXSOoTtqrzR8L8YEIOmBeW94c3FmbSNSWAUbxsny9KKx5VFh"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

NAME = "teaboot"


def get(url: str) -> dict:
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {TOKEN}", "User-Agent": UA,
        "Accept": "application/json",
    })
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.loads(r.read().decode("utf-8"))


def save(rel: str, data) -> None:
    SRC.mkdir(parents=True, exist_ok=True)
    (SRC / rel).write_text(
        json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[teaboot] saved {rel}")


def block_has_media(block: dict) -> bool:
    if not isinstance(block, dict):
        return False
    if block.get("type") in ("image", "video", "audio"):
        return True
    if block.get("media") or block.get("poster"):
        return True
    return False


def post_is_text_only(post: dict) -> bool:
    for c in post.get("content") or []:
        if block_has_media(c):
            return False
    for t in post.get("trail") or []:
        for c in t.get("content") or []:
            if block_has_media(c):
                return False
    return True


def build_blog_row(info: dict, plan: ImagePlan) -> dict:
    b = info["response"]["blog"]
    theme = b.get("theme") or {}
    return {
        "name": b["name"],
        "title": b.get("title") or "",
        "description": b.get("description") or "",
        "url": b.get("url") or f"https://{NAME}.tumblr.com/",
        "uuid": b.get("uuid") or "",
        "updated": b.get("updated") or 0,
        "primary": True,
        "posts_count": b.get("posts") or 0,
        "total_posts_upstream": b.get("posts"),
        "avatar": avatar_path(b, plan),
        "avatar_shape": b.get("avatar_shape") or theme.get("avatar_shape")
        or "circle",
        "header_image": "",
        "theme": {
            "background_color": theme.get("background_color") or "#001935",
            "title_color": theme.get("title_color") or "#ffffff",
            "body_font": theme.get("body_font") or "Helvetica Neue",
            "link_color": theme.get("link_color") or "#00b8ff",
        },
        "can_message": bool(b.get("can_message")),
        "is_nsfw": bool(b.get("is_nsfw")),
        "is_adult": bool(b.get("is_adult")),
        "can_be_followed": bool(b.get("can_be_followed", True)),
        "ask": bool(b.get("ask")),
        "ask_anon": bool(b.get("ask_anon")),
        "ask_page_title": b.get("ask_page_title") or "",
        "share_likes": bool(b.get("share_likes")),
        "share_following": bool(b.get("share_following")),
    }


def build_post_rows(feed: dict, plan: ImagePlan) -> list:
    rows = []
    for p in feed.get("response", {}).get("posts", []):
        if p.get("object_type") not in (None, "post"):
            continue
        pid = str(p.get("id") or p.get("id_string") or "")
        if not pid:
            continue
        if p.get("blog_name") != NAME or not post_is_text_only(p):
            continue
        trail = []
        for t in p.get("trail") or []:
            if not isinstance(t, dict):
                continue
            tb = t.get("blog") or {}
            trail.append({
                "blog_name": t.get("blog_name") or tb.get("name"),
                "blog_title": tb.get("title"),
                "blog_avatar": avatar_path(tb, plan),
                "content": normalize_blocks(t.get("content"), plan, NAME),
            })
        asking_avatar = ""
        if p.get("asking_avatar"):
            aa = p["asking_avatar"]
            if isinstance(aa, list):
                best = min(aa, key=lambda a: abs((a.get("width") or 512) - 128))
                aa = best.get("url", "")
            asking_avatar = aa
        rows.append({
            "id": pid,
            "blog_name": NAME,
            "type": TYPE_MAP.get(p.get("original_type"), p.get("original_type")),
            "original_type": p.get("original_type"),
            "is_blocks_post_format": bool(p.get("is_blocks_post_format")),
            "content": normalize_blocks(p.get("content"), plan, NAME),
            "layout": p.get("layout") or [],
            "trail": trail,
            "tags": p.get("tags") or [],
            "timestamp": p.get("timestamp"),
            "date": p.get("date"),
            "post_url": p.get("post_url"),
            "slug": p.get("slug"),
            "summary": p.get("summary"),
            "note_count": p.get("note_count", 0) or 0,
            "like_count": p.get("like_count", 0) or 0,
            "reblog_count": p.get("reblog_count", 0) or 0,
            "reply_count": p.get("reply_count", 0) or 0,
            "state": p.get("state"),
            "asking_name": p.get("asking_name"),
            "asking_url": p.get("asking_url"),
            "asking_avatar": asking_avatar,
        })
    return rows


def main() -> int:
    info = get(f"{API}/blog/{NAME}/info")
    feed = get(f"{API}/blog/{NAME}/posts?limit=5&reblog_info=true")
    save("info.json", info)
    save("posts_0.json", feed)
    time.sleep(0.5)

    plan = ImagePlan()
    blog_row = build_blog_row(info, plan)
    post_rows = build_post_rows(feed, plan)
    print(f"[teaboot] blog row: title={blog_row['title']!r} "
          f"posts={blog_row['posts_count']} updated={blog_row['updated']}")
    for row in post_rows:
        print(f"[teaboot] post {row['id']} ts={row['timestamp']} "
              f"summary={(row['summary'] or '')[:60]!r}")

    # ---- merge blogs.json (sorted by name) -------------------------------- #
    blogs_path = DST / "blogs.json"
    blogs = json.loads(blogs_path.read_text(encoding="utf-8"))
    blogs = [b for b in blogs if b["name"] != NAME]
    blogs.append(blog_row)
    blogs.sort(key=lambda b: b["name"])
    blogs_path.write_text(json.dumps(blogs, ensure_ascii=False, indent=1),
                          encoding="utf-8")

    # ---- merge posts.json (sorted by name, id) ---------------------------- #
    posts_path = DST / "posts.json"
    posts = json.loads(posts_path.read_text(encoding="utf-8"))
    keep = {row["id"] for row in post_rows}
    posts = [p for p in posts
             if not (p.get("blog_name") == NAME and p["id"] in keep)]
    posts.extend(post_rows)
    posts.sort(key=lambda p: (p["blog_name"], p["id"]))
    posts_path.write_text(json.dumps(posts, ensure_ascii=False, indent=1),
                          encoding="utf-8")
    print(f"[teaboot] merged: blogs.json now {len(blogs)} rows, "
          f"posts.json now {len(posts)} rows "
          f"({len(post_rows)} teaboot posts)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
