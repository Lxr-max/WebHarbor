#!/usr/bin/env python3
"""Fetch info + a few posts for every blog suggested by the saved searches.

The upstream search pages suggest blogs in their sidebar; on the mirror those
suggestions must be clickable, so each suggested blog gets a real info +
posts snapshot (5 posts each keeps the addition light).
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scrape_tumblr import BLOGS, OUT, get, save  # noqa: E402


def main() -> None:
    names = json.loads(
        Path("/tmp/suggestion_blogs.json").read_text(encoding="utf-8"))
    print(f"[suggestions] fetching {len(names)} suggested blogs")
    for name in names:
        if "/" in name or not name:
            continue
        try:
            save(f"blogs/{name}/info.json",
                 get(f"https://www.tumblr.com/api/v2/blog/{name}/info"))
            data = get("https://www.tumblr.com/api/v2/blog/"
                       f"{name}/posts?limit=5&reblog_info=true")
            save(f"blogs/{name}/posts_0.json", data)
        except Exception as e:                        # noqa: BLE001
            print(f"[warn] {name}: {e}")
        time.sleep(0.5)
    print("[suggestions] done")


if __name__ == "__main__":
    main()
