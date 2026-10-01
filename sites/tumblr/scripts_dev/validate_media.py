#!/usr/bin/env python3
"""Validate every local media path referenced by source_data/ exists.

Any block that still points at a file we could not ship (e.g. a tumblr mp4
that exceeded the size cap) is repaired in place:
  - video blocks lose their `media` key (the card then renders the poster)
  - image blocks lose their `media` key (renders nothing for that image)
  - avatar/header/thumb fields are blanked

Run after download_images.py + apply_ext_fixups.py, before building the seed.
"""
from __future__ import annotations

import json
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
DST = BASE / "source_data"


def check_path(p, fixes, where):
    if not p:
        return p
    rel = p[1:] if p.startswith("/") else p
    if (BASE / rel).is_file():
        return p
    fixes.append(f"{where}: missing {p}")
    return ""


def main():
    fixes = []
    posts = json.loads((DST / "posts.json").read_text(encoding="utf-8"))
    for post in posts:
        for block in post.get("content") or []:
            if block.get("type") == "image" and isinstance(block.get("media"), dict):
                block["media"]["url"] = check_path(
                    block["media"].get("url"), fixes, f"post {post['id']} image")
                if not block["media"]["url"]:
                    block["media"] = None
            elif block.get("type") == "video":
                if isinstance(block.get("media"), dict):
                    block["media"]["url"] = check_path(
                        block["media"].get("url"), fixes,
                        f"post {post['id']} video")
                    if not block["media"]["url"]:
                        block["media"] = None
                if isinstance(block.get("poster"), dict):
                    block["poster"]["url"] = check_path(
                        block["poster"].get("url"), fixes,
                        f"post {post['id']} poster")
                    if not block["poster"]["url"]:
                        block["poster"] = None
            elif block.get("type") == "audio" and isinstance(block.get("poster"), dict):
                block["poster"]["url"] = check_path(
                    block["poster"].get("url"), fixes,
                    f"post {post['id']} audio poster")
                if not block["poster"]["url"]:
                    block["poster"] = None
            elif block.get("type") == "link" and isinstance(block.get("poster"), str):
                block["poster"] = check_path(
                    block["poster"], fixes, f"post {post['id']} link poster")
        for item in post.get("trail") or []:
            for block in item.get("content") or []:
                if (block.get("type") == "image"
                        and isinstance(block.get("media"), dict)):
                    block["media"]["url"] = check_path(
                        block["media"].get("url"), fixes,
                        f"post {post['id']} trail image")
                    if not block["media"]["url"]:
                        block["media"] = None
        post["asking_avatar"] = check_path(post.get("asking_avatar"), fixes,
                                           f"post {post['id']} asker avatar")
    (DST / "posts.json").write_text(
        json.dumps(posts, ensure_ascii=False, indent=1), encoding="utf-8")

    blogs = json.loads((DST / "blogs.json").read_text(encoding="utf-8"))
    for b in blogs:
        b["avatar"] = check_path(b.get("avatar"), fixes, f"blog {b['name']} avatar")
        b["header_image"] = check_path(b.get("header_image"), fixes,
                                       f"blog {b['name']} header")
    (DST / "blogs.json").write_text(
        json.dumps(blogs, ensure_ascii=False, indent=1), encoding="utf-8")

    tags = json.loads((DST / "tags.json").read_text(encoding="utf-8"))
    for t in tags:
        hub = t.get("hub") or {}
        hub["header_image"] = check_path(hub.get("header_image"), fixes,
                                         f"tag {t['tag']} header")
        hub["blog_avatar"] = check_path(hub.get("blog_avatar"), fixes,
                                        f"tag {t['tag']} hub avatar")
        for rel in t.get("related_tags") or []:
            rel["thumb"] = check_path(rel.get("thumb"), fixes,
                                      f"tag {t['tag']} related thumb")
    (DST / "tags.json").write_text(
        json.dumps(tags, ensure_ascii=False, indent=1), encoding="utf-8")

    searches = json.loads((DST / "searches.json").read_text(encoding="utf-8"))
    for s in searches:
        for b in s.get("blogs") or []:
            b["avatar"] = check_path(b.get("avatar"), fixes,
                                     f"search {s['query']} blog avatar")
        for c in s.get("communities") or []:
            c["avatar"] = check_path(c.get("avatar"), fixes,
                                    f"search {s['query']} community avatar")
    (DST / "searches.json").write_text(
        json.dumps(searches, ensure_ascii=False, indent=1), encoding="utf-8")

    notes = json.loads((DST / "notes.json").read_text(encoding="utf-8"))
    for n in notes:
        for note in n.get("notes") or []:
            note["avatar"] = check_path(note.get("avatar"), fixes,
                                        f"note {n['post_id']} avatar")
    (DST / "notes.json").write_text(
        json.dumps(notes, ensure_ascii=False, indent=1), encoding="utf-8")

    if fixes:
        print(f"[validate] {len(fixes)} missing references repaired:")
        for f in fixes[:20]:
            print("  ", f)
    else:
        print("[validate] all media references present")


if __name__ == "__main__":
    main()
