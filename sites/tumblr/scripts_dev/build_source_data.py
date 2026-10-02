#!/usr/bin/env python3
"""Normalize the raw scraped_data/ API responses into frozen source_data/ JSON.

Reads scraped_data/**.json (verbatim API responses from www.tumblr.com,
captured 2026-09-28) and writes:

  source_data/blogs.json      every blog seen anywhere (meta + local assets)
  source_data/posts.json      every unique post (content blocks, trail, tags)
  source_data/tags.json       the 12 tag hub pages (header + related + posts)
  source_data/searches.json   the 8 search queries (posts + suggestions)
  source_data/explore.json    trending feed + hub topic cards
  source_data/notes.json      like/reblog/reply notes for 40 high-note posts

Plus scraped_data/image_manifest.json: every image/video to download, with
the upstream URL and the deterministic local path. Post media is keyed by the
upstream media_key hash so reblogs that share an image download it once.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections import OrderedDict
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
SRC = BASE / "scraped_data"
DST = BASE / "source_data"

POSTS_PER_BLOG_PAGES = 3
IMAGE_MAX_W = 1280          # preferred upstream variant width
GIF_MAX_W = 540


# ---------------------------------------------------------------- helpers ---
def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def walk_files(*dirs):
    for d in dirs:
        for p in sorted((SRC / d).rglob("*.json")):
            yield p


def extract_posts(data):
    resp = data.get("response", data)
    out = []
    if isinstance(resp, list):
        out = [e for e in resp if isinstance(e, dict)
               and e.get("object_type") == "post"]
    elif isinstance(resp, dict):
        out = [e for e in resp.get("posts", [])
               if isinstance(e, dict) and e.get("object_type") == "post"]
        tl = resp.get("timeline")
        if isinstance(tl, dict):
            out += [e for e in tl.get("elements", [])
                    if isinstance(e, dict) and e.get("object_type") == "post"]
    return out


def web(path: str) -> str:
    """Repo-relative plan path -> web path served by Flask."""
    if not path:
        return path
    return path if path.startswith("/") else "/" + path


def media_key_hash(media_key: str) -> str:
    return hashlib.sha1(media_key.encode()).hexdigest()[:16]


def choose_image_variant(media_list):
    """Pick the best upstream variant for one media_key."""
    if not media_list:
        return None
    is_gif = any(str(m.get("url", "")).endswith((".gifv", ".gif"))
                 for m in media_list)
    def score(m):
        url = str(m.get("url", ""))
        if is_gif and url.endswith(".gifv"):
            url = url[:-5] + ".gif"
        w = m.get("width") or 0
        cap = GIF_MAX_W if is_gif else IMAGE_MAX_W
        if w <= cap:
            return (0, -(w or 1))          # largest within cap
        return (1, w)                       # otherwise smallest above cap
    best = min(media_list, key=score)
    url = str(best.get("url", ""))
    if is_gif and url.endswith(".gifv"):
        url = url[:-5] + ".gif"
    return {"url": url, "width": best.get("width") or 0,
            "height": best.get("height") or 0,
            "type": best.get("type", "image/jpeg")}


def ext_for(url: str, content_type: str = "") -> str:
    u = url.lower()
    for e in (".gif", ".png", ".webp", ".jpg", ".jpeg", ".mp4", ".mov"):
        if u.endswith(e):
            return ".jpg" if e == ".jpeg" else e
    if content_type:
        if "png" in content_type:
            return ".png"
        if "gif" in content_type:
            return ".gif"
        if "webp" in content_type:
            return ".webp"
        if "mp4" in content_type:
            return ".mp4"
        if "quicktime" in content_type:
            return ".mov"
    return ".jpg"


def safe_name(name: str) -> str:
    return re.sub(r"[^a-z0-9-]+", "-", str(name or "").lower()).strip("-")[:60]


class ImagePlan:
    """Collects the {local_path: source_url} download plan."""

    def __init__(self):
        self.entries = OrderedDict()      # path -> {"url":..., "kind":...}

    def add(self, url: str, path: str, kind: str) -> str:
        if not url:
            return ""
        if path not in self.entries:
            self.entries[path] = {"url": url, "kind": kind}
        return path


# ------------------------------------------------------------ collection ---
def collect_raw():
    posts = {}            # (blog, id) -> post (keep richest copy)
    blog_objects = {}     # name -> blog dict (keep richest)
    feeds = []            # (feed_name, post_ref) in order
    for path in walk_files("blogs", "tagged", "search", "explore"):
        rel = path.relative_to(SRC).as_posix()
        try:
            data = load(path)
        except Exception:
            continue
        if rel.startswith("blogs/"):
            name = rel.split("/")[1]
            if rel.endswith("/info.json"):
                blog_objects.setdefault(name, {}).update(
                    data.get("response", {}).get("blog", {}))
                blog_objects[name]["_primary"] = True
                continue
        for p in extract_posts(data):
            blog = p.get("blog_name")
            pid = str(p.get("id") or p.get("id_string") or "")
            if not blog or not pid:
                continue
            key = (blog, pid)
            if key not in posts or len(json.dumps(p)) > len(json.dumps(posts[key])):
                posts[key] = p
            b = p.get("blog")
            if isinstance(b, dict) and b.get("name"):
                cur = blog_objects.setdefault(b["name"], {})
                if len(json.dumps(b)) > len(json.dumps(cur)):
                    cur.update(b)
            if rel.startswith("blogs/"):
                feeds.append((f"blog:{blog}", key))
            elif rel.startswith("tagged/") and "_hub" not in rel:
                tag = rel.split("/")[1].rsplit("_", 1)[0]
                feeds.append((f"tag:{tag}", key))
            elif rel.startswith("search/"):
                q = rel.split("/")[1].rsplit("_", 1)[0]
                kind = rel.rsplit("_", 1)[1].replace(".json", "")
                feeds.append((f"search:{kind}:{q}", key))
            elif rel.startswith("explore/"):
                feeds.append(("explore", key))
    return posts, blog_objects, feeds


def normalize_blocks(blocks, plan: ImagePlan, post_dir_hint: str):
    """Rewrite content blocks with local media paths."""
    if not isinstance(blocks, list):
        return []
    out = []
    for c in blocks:
        if not isinstance(c, dict):
            continue
        t = c.get("type")
        block = {k: v for k, v in c.items() if k not in ("media", "poster")}
        if t == "image":
            best = choose_image_variant(c.get("media") or [])
            if best:
                mk = (c.get("media") or [{}])[0].get("media_key") or best["url"]
                ext = ext_for(best["url"], best.get("type", ""))
                rel = f"static/images/media/{media_key_hash(mk)}{ext}"
                block["media"] = {
                    "url": web(plan.add(best["url"], rel, "post-image")),
                    "width": best["width"], "height": best["height"],
                }
            else:
                block["media"] = None
        elif t in ("video", "audio"):
            poster = c.get("poster")
            if isinstance(poster, list) and poster:
                best = choose_image_variant(poster)
                if best:
                    mk = poster[0].get("media_key") or best["url"]
                    ext = ext_for(best["url"], best.get("type", ""))
                    rel = f"static/images/media/{media_key_hash(mk)}{ext}"
                    block["poster"] = {
                        "url": web(plan.add(best["url"], rel, "poster")),
                        "width": best["width"], "height": best["height"],
                    }
            if t == "video" and c.get("provider") == "tumblr":
                media = c.get("media") or {}
                url = media.get("url", "")
                if str(url).endswith(".mp4"):
                    vid = f"static/images/media/{media_key_hash(url)}.mp4"
                    block["media"] = {
                        "url": web(plan.add(url, vid, "video")),
                        "width": media.get("width", 0),
                        "height": media.get("height", 0),
                    }
                else:
                    block["media"] = None        # .mov and friends: poster only
        elif t == "link":
            poster = c.get("poster")
            if isinstance(poster, list) and poster:
                best = choose_image_variant(poster)
                if best:
                    mk = poster[0].get("media_key") or best["url"]
                    ext = ext_for(best["url"], best.get("type", ""))
                    rel = f"static/images/media/{media_key_hash(mk)}{ext}"
                    block["poster"] = web(plan.add(best["url"], rel, "poster"))
        out.append(block)
    return out


def build_posts(posts, plan: ImagePlan):
    TYPE_MAP = {"regular": "text", "note": "answer", "photo": "photo"}
    rows = []
    for (blog, pid), p in sorted(posts.items(), key=lambda kv: (kv[0][0], kv[0][1])):
        trail = []
        for t in p.get("trail") or []:
            if not isinstance(t, dict):
                continue
            tb = t.get("blog") or {}
            trail.append({
                "blog_name": t.get("blog_name") or tb.get("name"),
                "blog_title": tb.get("title"),
                "blog_avatar": avatar_path(tb, plan),
                "content": normalize_blocks(t.get("content"), plan, blog),
            })
        asking_avatar = ""
        if p.get("asking_avatar"):
            aa = p["asking_avatar"]
            if isinstance(aa, list):
                best = min(aa, key=lambda a: abs((a.get("width") or 512) - 128))
                aa = best.get("url", "")
            asking_avatar = web(plan.add(
                aa,
                f"static/images/avatars/{safe_name(p.get('asking_name'))}"
                f"_{media_key_hash(str(aa))}.png",
                "avatar")) if aa else ""
        rows.append({
            "id": pid,
            "blog_name": blog,
            "type": TYPE_MAP.get(p.get("original_type"), p.get("original_type")),
            "original_type": p.get("original_type"),
            "is_blocks_post_format": bool(p.get("is_blocks_post_format")),
            "content": normalize_blocks(p.get("content"), plan, blog),
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


def avatar_path(blog: dict, plan: ImagePlan) -> str:
    """Local path for a blog avatar (128px upstream variant)."""
    name = blog.get("name")
    if not name:
        return ""
    avatars = blog.get("avatar") or []
    url = ""
    best = None
    for a in avatars:
        w = a.get("width") or 0
        if w == 128:
            best = a
            break
        if best is None or abs(w - 128) < abs((best.get("width") or 0) - 128):
            best = a
    if best:
        url = best.get("url", "")
    else:
        url = blog.get("avatar_url_128") or ""
    if not url:
        return ""
    rel = f"static/images/avatars/{safe_name(name)}.png"
    return web(plan.add(url, rel, "avatar"))


def header_path(blog: dict, plan: ImagePlan) -> str:
    theme = blog.get("theme") or {}
    url = (theme.get("header_image_scaled")
           or theme.get("header_image_focused")
           or theme.get("header_image") or "")
    if not url or url.startswith("https://static.tumblr.com"):
        return ""          # default pattern headers are shared, skip
    name = blog.get("name")
    ext = ext_for(url)
    rel = f"static/images/headers/{safe_name(name)}{ext}"
    return web(plan.add(url, rel, "header"))


def build_blogs(blog_objects, posts, plan: ImagePlan):
    post_counts = {}
    for (blog, pid) in posts:
        post_counts[blog] = post_counts.get(blog, 0) + 1
    rows = []
    for name, b in sorted(blog_objects.items()):
        if not name or "/" in name:
            continue
        primary = bool(b.get("_primary"))
        info = {}
        if primary:
            info_path = SRC / "blogs" / name / "info.json"
            if info_path.is_file():
                info = load(info_path).get("response", {}).get("blog", {})
        theme = b.get("theme") or {}
        rows.append({
            "name": name,
            "title": b.get("title") or "",
            "description": b.get("description") or "",
            "url": b.get("url") or f"https://{name}.tumblr.com/",
            "uuid": b.get("uuid") or "",
            "updated": b.get("updated") or 0,
            "primary": primary,
            "posts_count": (info.get("posts") or post_counts.get(name, 0)
                            if primary else post_counts.get(name, 0)),
            "total_posts_upstream": info.get("posts") if primary else None,
            "avatar": avatar_path(b, plan),
            "avatar_shape": b.get("avatar_shape") or theme.get("avatar_shape") or "circle",
            "header_image": (header_path(b, plan)
                              if (primary or post_counts.get(name, 0) >= 3) else ""),
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
            "ask": bool(info.get("ask", b.get("ask", False))),
            "ask_anon": bool(info.get("ask_anon", False)),
            "ask_page_title": info.get("ask_page_title") or b.get("ask_page_title") or "",
            "share_likes": bool(b.get("share_likes")),
            "share_following": bool(b.get("share_following")),
        })
    return rows


def build_tags(plan: ImagePlan):
    rows = []
    tag_files = sorted((SRC / "tagged").glob("*.json"))
    tags = sorted({p.name.rsplit("_", 1)[0] for p in tag_files})
    for tag in tags:
        hub = None
        related = []
        hub_path = SRC / "tagged" / f"{tag}_hub.json"
        if hub_path.is_file():
            tl = load(hub_path).get("response", {}).get("timeline", {})
            for e in tl.get("elements", []):
                if e.get("object_type") == "community_hub_header_card":
                    hdr = e
                    blog_avatar = ""
                    if hdr.get("blogAvatarUrl") or hdr.get("blog_avatar_url"):
                        ba = hdr.get("blogAvatarUrl") or hdr.get("blog_avatar_url")
                        blog_avatar = web(plan.add(
                            ba,
                            f"static/images/tag_headers/{safe_name(tag)}"
                            "_hubavatar.png", "tag-header"))
                    header_image = (hdr.get("headerImage")
                                    or hdr.get("header_image") or "")
                    hub = {
                        "hub_name": (hdr.get("hubName") or hdr.get("hub_name")
                                     or tag),
                        "tag_id": hdr.get("tagId") or hdr.get("tag_id") or tag,
                        "background_color": (hdr.get("backgroundColor")
                                              or hdr.get("background_color") or ""),
                        "header_image": web(plan.add(
                            header_image,
                            f"static/images/tag_headers/{safe_name(tag)}.png",
                            "tag-header")) if header_image else "",
                        "header_link": hdr.get("headerLink")
                                       or hdr.get("header_link") or "",
                        "post_id": (hdr.get("postId") or hdr.get("post_id")
                                    or ""),
                        "blog_name": (hdr.get("blogName")
                                      or hdr.get("blog_name") or ""),
                        "blog_avatar": blog_avatar,
                        "followers_count": (hdr.get("followersCount")
                                             or hdr.get("followers_count") or ""),
                        "followers_count_int": (hdr.get("followersCountInt")
                                                 or hdr.get("followers_count_int") or 0),
                        "new_posts_count": (hdr.get("newPostsCount")
                                             or hdr.get("new_posts_count") or ""),
                        "new_posts_count_int": (hdr.get("newPostsCountInt")
                                                 or hdr.get("new_posts_count_int") or 0),
                        "post_count_int": (hdr.get("postCountInt")
                                           or hdr.get("post_count_int") or 0),
                        "editorial_description": (hdr.get("editorialDescription")
                                                  or hdr.get("editorial_description") or ""),
                        "editorial_description_text": (
                            hdr.get("editorialDescriptionText")
                            or hdr.get("editorial_description_text") or ""),
                    }
                elif e.get("object_type") == "tag_info_row":
                    thumb = (e.get("thumb") or e.get("thumbUrl")
                             or e.get("image") or "")
                    related.append({
                        "tag": (e.get("tag") or e.get("hub_name")
                                or e.get("hubName") or ""),
                        "url": e.get("url") or "",
                        "featured": bool(e.get("featured")),
                        "followers": e.get("followers") or 0,
                        "recent_posts": (e.get("recent_posts")
                                          or e.get("new_posts_count_int") or 0),
                        "new_posts_count": (e.get("newPostsCount")
                                            or e.get("new_posts_count") or ""),
                        "background_color": (e.get("backgroundColor")
                                              or e.get("background_color") or ""),
                        "thumb": web(plan.add(
                            thumb,
                            f"static/images/tag_thumbs/{safe_name(e.get('hub_name') or e.get('tag') or '')}"
                            f"_{media_key_hash(str(thumb))}.jpg",
                            "tag-thumb")) if thumb else "",
                    })
        post_ids = []
        for p in sorted((SRC / "tagged").glob(f"{tag}_[0-9].json")):
            data = load(p)
            for post in extract_posts(data):
                pid = str(post.get("id") or post.get("id_string") or "")
                if pid and pid not in post_ids:
                    post_ids.append(pid)
        rows.append({"tag": tag, "hub": hub, "related_tags": related[:6],
                    "post_ids": post_ids})
    return rows


def build_searches(plan: ImagePlan):
    rows = []
    s_files = sorted((SRC / "search").glob("*.json"))
    queries = sorted({p.stem.rsplit("_", 1)[0] for p in s_files})
    for q in queries:
        row = {"query": q, "top_post_ids": [], "recent_post_ids": [],
               "blogs": [], "tags": [], "communities": [],
               "typeahead_tags": [], "typeahead_blogs": []}
        for p in s_files:
            if not p.stem.startswith(q + "_"):
                continue
            kind = p.stem.rsplit("_", 1)[-1]
            data = load(p)
            resp = data.get("response", data)
            if kind in ("top", "recent"):
                tl = resp.get("timeline", {}) if isinstance(resp, dict) else {}
                ids = []
                for e in tl.get("elements", []):
                    if e.get("object_type") == "post":
                        pid = str(e.get("id") or e.get("id_string") or "")
                        if pid and pid not in ids:
                            ids.append(pid)
                row[f"{kind}_post_ids"] = ids
            elif kind == "suggestions" and isinstance(resp, dict):
                for b in resp.get("blogs", []):
                    avatar = ""
                    for a in b.get("avatar") or []:
                        if (a.get("width") or 0) == 128:
                            avatar = a.get("url", "")
                            break
                    row["blogs"].append({
                        "name": b.get("name"),
                        "title": b.get("title") or "",
                        "url": b.get("url") or "",
                        "description": b.get("description") or "",
                        "avatar": web(plan.add(
                            avatar,
                            f"static/images/avatars/{safe_name(b.get('name'))}.png",
                            "avatar")) if avatar else "",
                    })
                for t in resp.get("tags", []):
                    row["tags"].append({
                        "tag": t.get("tag"),
                        "url": t.get("url") or "",
                        "featured": bool(t.get("featured")),
                        "followers": t.get("followers") or 0,
                        "recent_posts": t.get("recent_posts") or 0,
                    })
                for c in resp.get("communities", []):
                    avatar = ""
                    for a in c.get("avatar") or []:
                        if (a.get("width") or 0) == 128:
                            avatar = a.get("url", "")
                            break
                    row["communities"].append({
                        "name": c.get("name"),
                        "title": c.get("title") or "",
                        "description": c.get("description") or "",
                        "avatar": web(plan.add(
                            avatar,
                            f"static/images/communities/{safe_name(c.get('name'))}.png",
                            "avatar")) if avatar else "",
                    })
            elif kind == "typeahead" and isinstance(resp, dict):
                for t in resp.get("results", []):
                    if t.get("tag"):
                        row["typeahead_tags"].append(t["tag"])
                    for b in t.get("blogs", []) or []:
                        row["typeahead_blogs"].append(b.get("name"))
        rows.append(row)
    return rows


def build_explore():
    trending = []
    for name in ("explore.json", "trending.json"):
        p = SRC / "explore" / name
        if not p.is_file():
            continue
        data = load(p)
        for post in extract_posts(data):
            pid = str(post.get("id") or post.get("id_string") or "")
            if pid and pid not in trending:
                trending.append(pid)
    return {"trending_post_ids": trending}


def build_notes(plan: ImagePlan):
    rows = []
    for p in sorted((SRC / "notes").glob("*.json")):
        data = load(p)
        resp = data.get("response", {})
        notes = []
        seen = set()
        for n in resp.get("notes", []):
            name = n.get("blog_name")
            if not name or (name, n.get("type"), n.get("timestamp")) in seen:
                continue
            seen.add((name, n.get("type"), n.get("timestamp")))
            avatar = ""
            urls = n.get("avatar_url") or {}
            if isinstance(urls, dict):
                avatar = urls.get("64") or urls.get("128") or ""
            elif isinstance(urls, str):
                avatar = urls
            notes.append({
                "type": n.get("type"),
                "timestamp": n.get("timestamp"),
                "blog_name": name,
                "blog_title": n.get("blog_title") or "",
                "blog_url": n.get("blog_url") or "",
                "avatar_shape": n.get("avatar_shape") or "circle",
                "avatar": web(plan.add(
                    avatar,
                    f"static/images/note_avatars/{safe_name(name)}.png",
                    "note-avatar")) if avatar else "",
                "reply_text": n.get("reply_text"),
                "added_text": n.get("added_text"),
            })
        blog, pid = p.stem.rsplit("_", 1)
        rows.append({
            "post_id": pid, "blog_name": blog,
            "total_notes": resp.get("total_notes", 0) or 0,
            "total_likes": resp.get("total_likes", 0) or 0,
            "total_reblogs": resp.get("total_reblogs", 0) or 0,
            "total_replies": resp.get("total_replies", 0) or 0,
            "notes": notes,
        })
    return rows


def main():
    posts, blog_objects, feeds = collect_raw()
    plan = ImagePlan()

    tag_rows = build_tags(plan)
    search_rows = build_searches(plan)
    explore = build_explore()
    notes_rows = build_notes(plan)
    post_rows = build_posts(posts, plan)
    blog_rows = build_blogs(blog_objects, posts, plan)

    # feed membership index (order preserved from upstream responses)
    feed_index = {}
    for feed, key in feeds:
        feed_index.setdefault(feed, [])
        if key not in feed_index[feed]:
            feed_index[feed].append(key)

    DST.mkdir(parents=True, exist_ok=True)
    (DST / "blogs.json").write_text(
        json.dumps(blog_rows, ensure_ascii=False, indent=1), encoding="utf-8")
    (DST / "posts.json").write_text(
        json.dumps(post_rows, ensure_ascii=False, indent=1), encoding="utf-8")
    (DST / "tags.json").write_text(
        json.dumps(tag_rows, ensure_ascii=False, indent=1), encoding="utf-8")
    (DST / "searches.json").write_text(
        json.dumps(search_rows, ensure_ascii=False, indent=1), encoding="utf-8")
    (DST / "explore.json").write_text(
        json.dumps(explore, ensure_ascii=False, indent=1), encoding="utf-8")
    (DST / "notes.json").write_text(
        json.dumps(notes_rows, ensure_ascii=False, indent=1), encoding="utf-8")
    (DST / "feed_index.json").write_text(
        json.dumps({k: [list(x) for x in v] for k, v in feed_index.items()},
                   ensure_ascii=False, indent=1), encoding="utf-8")

    manifest = [{"path": p, **v} for p, v in plan.entries.items()]
    (SRC / "image_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")

    n_images = len(manifest)
    n_videos = sum(1 for m in manifest if m["kind"] == "video")
    print(f"[build] blogs={len(blog_rows)} posts={len(post_rows)} "
          f"tags={len(tag_rows)} searches={len(search_rows)} "
          f"notes_posts={len(notes_rows)} note_items="
          f"{sum(len(r['notes']) for r in notes_rows)}")
    print(f"[build] images to download: {n_images} "
          f"(incl. {n_videos} tumblr mp4 videos)")
    kinds = {}
    for m in manifest:
        kinds[m["kind"]] = kinds.get(m["kind"], 0) + 1
    print(f"[build] kinds: {kinds}")


if __name__ == "__main__":
    main()
