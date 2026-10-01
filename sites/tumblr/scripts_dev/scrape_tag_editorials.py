#!/usr/bin/env python3
"""Capture the tag-hub editorial descriptions from the real www.tumblr.com.

The original snapshot took hub data from the search-timeline API, whose
community_hub_header_card payload does not carry the editorial fields; the
tagged HTML page (___INITIAL_STATE___.queries) does serve them alongside
`showEditorialDescription`. This script:

  1. GETs https://www.tumblr.com/tagged/<tag> for each of the 12 snapshot
     tags and stores the response verbatim under
     scraped_data/tagged_editorial/<tag>.html (build-time-only provenance).
  2. Extracts editorialDescription / editorialDescriptionText /
     showEditorialDescription exactly as the page serves them.
  3. Merges the two editorial fields into the frozen source_data/tags.json
     hub rows (tags upstream shows no editorial for stay empty, mirroring
     the upstream page).

Re-running is safe: verbatim captures are overwritten, source_data is
re-merged from the captures.
"""
from __future__ import annotations

import json
import re
import sys
import time
import urllib.request
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]          # sites/tumblr
OUT = BASE / "scraped_data" / "tagged_editorial"
DST = BASE / "source_data" / "tags.json"

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

TAGS = ["art", "photography", "gif", "nature", "space", "travel",
        "food", "cats", "architecture", "books", "vintage", "fashion"]

FIELDS_RE = re.compile(
    r'"editorialDescription":"((?:[^"\\]|\\.)*)"'
    r',"editorialDescriptionText":"((?:[^"\\]|\\.)*)"'
    r',"showEditorialDescription":(true|false)')


def fetch(tag: str) -> str:
    url = f"https://www.tumblr.com/tagged/{tag}"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=40) as r:
        return r.read().decode("utf-8")


def extract(html: str) -> dict:
    m = FIELDS_RE.search(html)
    if not m:
        return {"editorial_description": "", "editorial_description_text": "",
                "show": False}
    desc = json.loads(f'"{m.group(1)}"')
    text = json.loads(f'"{m.group(2)}"')
    return {"editorial_description": desc,
            "editorial_description_text": text,
            "show": m.group(3) == "true"}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    captured = {}
    for tag in TAGS:
        html = fetch(tag)
        (OUT / f"{tag}.html").write_text(html, encoding="utf-8")
        captured[tag] = extract(html)
        print(f"[editorial] {tag}: show={captured[tag]['show']} "
              f"text={captured[tag]['editorial_description_text'][:60]!r}")
        time.sleep(0.6)
    (OUT / "editorials.json").write_text(
        json.dumps(captured, ensure_ascii=False, indent=1), encoding="utf-8")

    rows = json.loads((BASE / "source_data" / "tags.json")
                      .read_text(encoding="utf-8"))
    changed = 0
    for row in rows:
        cap = captured.get(row["tag"])
        if cap is None:
            print(f"[merge] no capture for {row['tag']}, skipping")
            continue
        hub = row.get("hub") or {}
        if (hub.get("editorial_description") != cap["editorial_description"]
                or hub.get("editorial_description_text")
                != cap["editorial_description_text"]):
            changed += 1
        hub["editorial_description"] = cap["editorial_description"]
        hub["editorial_description_text"] = cap["editorial_description_text"]
        row["hub"] = hub
    (BASE / "source_data" / "tags.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    n_text = sum(1 for c in captured.values() if c["show"])
    print(f"[merge] {changed} hub rows updated in source_data/tags.json "
          f"({n_text} tags show an editorial upstream)")
    return 0 if changed or all(True for _ in captured) else 1


if __name__ == "__main__":
    sys.exit(main() or 0)
