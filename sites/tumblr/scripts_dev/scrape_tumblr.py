#!/usr/bin/env python3
"""Scrape the real tumblr.com (anonymous, official web API) into scraped_data/.

Every network response is stored verbatim under scraped_data/ so the frozen
source_data/ snapshots can be rebuilt deterministically later. Endpoints used
(2026-09-28, all reachable without an account):

  GET /api/v2/blog/{name}/info            blog metadata
  GET /api/v2/blog/{name}/posts           blog post feed (limit/offset paging)
  GET /api/v2/tagged?tag={tag}            tagged feed (cursor paging)
  GET /api/v2/timeline/search             search timelines (top/recent/tagged/photo/gif)
  GET /api/v2/search/{query}             search page suggestions (blogs/tags/communities)
  GET /api/v2/typeahead/{query}          search box suggestions
  GET /api/v2/explore                     trending posts
  GET /api/v2/explore/trending            trending posts (timeline form)
  GET /api/v2/blog/{name}/notes?id={post} likes/reblogs shown on a permalink page

The bearer token below is the public web-client token embedded in every
www.tumblr.com HTML page (___INITIAL_STATE___ -> apiFetchStore.API_TOKEN).
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]          # sites/tumblr
OUT = BASE / "scraped_data"

API = "https://www.tumblr.com/api/v2"
TOKEN = "aIcXSOoTtqrzR8L8YEIOmBeW94c3FmbSNSWAUbxsny9KKx5VFh"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

# Diverse, well-known public blogs across content verticals.
BLOGS = [
    "staff",               # official announcements (text posts)
    "nasa",                # space photography + long captions
    "waneella",            # pixel art
    "sparth",              # concept art
    "sebastiancuri",       # illustration
    "sablingart",          # art
    "meolog",              # photography + poetry
    "shutternoise",         # street photography
    "ludwigdanner",        # portrait photography
    "boschintegral-photo",  # fine-art photography
    "cabinporn",           # nature / cabins
    "writingprompts",      # text prompts
    "visualizingmath",      # math visualisations
    "natgeofound",         # archival photography
    "puffychi",            # cute / kawaii
    "paokai",              # travel photography
]

TAGS = ["art", "photography", "gif", "nature", "space", "travel",
        "food", "cats", "architecture", "books", "vintage", "fashion"]

SEARCHES = ["pixel art", "space", "cats", "coffee", "mountains",
            "poetry", "cyberpunk", "ocean"]

POSTS_PER_BLOG_PAGES = 3      # 3 x 20 posts
TAG_PAGES = 2                 # 2 x 20 posts per tag


def get(url: str, retries: int = 4) -> dict:
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {TOKEN}", "User-Agent": UA,
        "Accept": "application/json",
    })
    last = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=40) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 404 and attempt < retries - 1:
                # some cursor pages 404 transiently; retry once before giving up
                last = e
                time.sleep(3)
                continue
            if e.code == 404:
                raise
            last = e
            time.sleep(2 + attempt * 3)
        except Exception as e:                       # noqa: BLE001
            last = e
            time.sleep(2 + attempt * 3)
    raise RuntimeError(f"GET failed after {retries} tries: {url} ({last})")


def save(rel: str, data) -> None:
    path = OUT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1),
                    encoding="utf-8")
    print(f"[save] {rel} ({path.stat().st_size} bytes)")


def scrape_blogs() -> None:
    for name in BLOGS:
        save(f"blogs/{name}/info.json", get(f"{API}/blog/{name}/info"))
        for page in range(POSTS_PER_BLOG_PAGES):
            offset = page * 20
            data = get(f"{API}/blog/{name}/posts?limit=20&offset={offset}"
                       "&reblog_info=true")
            posts = data.get("response", {}).get("posts", [])
            save(f"blogs/{name}/posts_{page}.json", data)
            if not posts:
                break
            time.sleep(0.6)


def scrape_tags() -> None:
    for tag in TAGS:
        url = f"{API}/tagged?tag={urllib_quote(tag)}&reblog_info=true"
        for page in range(TAG_PAGES):
            data = get(url)
            save(f"tagged/{tag}_{page}.json", data)
            resp = data.get("response", {})
            links = (resp.get("_links", {}) if isinstance(resp, dict)
                     else {})
            nxt = links.get("next", {})
            href = nxt.get("href")
            if not href:
                break
            url = "https://www.tumblr.com/api" + href[len("/v2"):]
            time.sleep(0.6)
        # tag page header card (community hub) via the search timeline
        try:
            tl = get(f"{API}/timeline/search?limit=5&query={urllib_quote(tag)}"
                     "&timeline_type=tag")
            save(f"tagged/{tag}_hub.json", tl)
        except Exception as e:                        # noqa: BLE001
            print(f"[warn] hub card for {tag}: {e}")


def scrape_searches() -> None:
    for q in SEARCHES:
        for tt, fname in [("top", "top"), ("recent", "recent")]:
            data = get(f"{API}/timeline/search?limit=20&query={urllib_quote(q)}"
                       f"&timeline_type={tt}&reblog_info=true")
            save(f"search/{q}_{fname}.json", data)
            time.sleep(0.5)
        try:
            save(f"search/{q}_suggestions.json",
                 get(f"{API}/search/{urllib_quote(q)}"))
        except Exception as e:                        # noqa: BLE001
            print(f"[warn] suggestions for {q}: {e}")
        try:
            save(f"search/{q}_typeahead.json",
                 get(f"{API}/typeahead/{urllib_quote(q)}"
                     "?query_source=search_box"))
        except Exception as e:                        # noqa: BLE001
            print(f"[warn] typeahead for {q}: {e}")


def scrape_explore() -> None:
    save("explore/explore.json", get(f"{API}/explore"))
    save("explore/trending.json", get(f"{API}/explore/trending"))


def collect_post_ids() -> list:
    """Walk scraped_data and return [{blog, id, note_count}] for every post."""
    skip = {"image_manifest.json", "ext_fixups.json",
            "download_failures.json"}
    seen = {}
    for path in OUT.rglob("*.json"):
        if path.name in skip:
            continue
        rel = path.relative_to(OUT).as_posix()
        data = json.loads(path.read_text(encoding="utf-8"))
        posts = []
        resp = data.get("response", data) if isinstance(data, dict) else None
        if isinstance(resp, list):
            posts = [e for e in resp if isinstance(e, dict)
                     and e.get("object_type") == "post"]
        elif isinstance(resp, dict):
            posts = [e for e in resp.get("posts", [])
                     if isinstance(e, dict) and e.get("object_type") == "post"]
            tl = resp.get("timeline")
            if isinstance(tl, dict):
                posts += [e for e in tl.get("elements", [])
                          if isinstance(e, dict) and e.get("object_type") == "post"]
        for p in posts:
            pid = str(p.get("id") or p.get("id_string"))
            if not pid:
                continue
            blog = p.get("blog_name")
            if blog and pid not in seen:
                seen[pid] = {"id": pid, "blog": blog,
                             "note_count": p.get("note_count", 0) or 0}
    return sorted(seen.values(),
                  key=lambda r: -r["note_count"])


def scrape_notes() -> None:
    rows = collect_post_ids()
    picked = [r for r in rows if r["note_count"] >= 500][:150]
    print(f"[notes] fetching notes for {len(picked)} high-note posts")
    for r in picked:
        blog, pid = r["blog"], r["id"]
        if "/" in blog or not blog:
            continue
        pages = 3 if r["note_count"] >= 5000 else 1
        url = f"{API}/blog/{blog}/notes?id={pid}"
        merged = None
        for page in range(pages):
            try:
                data = get(url)
            except Exception as e:                    # noqa: BLE001
                print(f"[warn] notes {blog}/{pid}: {e}")
                break
            if merged is None:
                merged = data
            else:
                resp = data["response"]
                merged["response"]["notes"].extend(resp.get("notes", []))
            save(f"notes/{blog}_{pid}.json", merged)
            nxt = (merged["response"].get("_links", {}) or {}).get("next")
            if not nxt or not nxt.get("href"):
                break
            url = "https://www.tumblr.com/api" + nxt["href"][len("/v2"):]
            time.sleep(0.5)
        time.sleep(0.5)


def urllib_quote(text: str) -> str:
    import urllib.parse
    return urllib.parse.quote(text)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    if which in ("all", "blogs"):
        scrape_blogs()
    if which in ("all", "tags"):
        scrape_tags()
    if which in ("all", "searches"):
        scrape_searches()
    if which in ("all", "explore"):
        scrape_explore()
    if which in ("all", "notes"):
        scrape_notes()
    print("[done]")


if __name__ == "__main__":
    main()
