#!/usr/bin/env python3
"""Scrape athlete profile pages and story pages (both server-rendered)
into scraped_data/athletes/ and scraped_data/stories/.

Athlete pages yield: display name, country, discipline, the facts panel
(date of birth, birthplace, age, nationality, career start, disciplines),
the "Who is ...?" bio paragraphs and the hero image URL.
Story pages yield: title, standfirst, body paragraphs, publish date,
discipline tag and the hero image URL.
"""
from __future__ import annotations

import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fetch_lib import BASE, fetch, save  # noqa: E402

SITE = Path(__file__).resolve().parents[1]
ATH_OUT = SITE / "scraped_data" / "athletes"
STO_OUT = SITE / "scraped_data" / "stories"

FACT_LABELS = ["Date of birth", "Birthplace", "Age", "Nationality",
               "Career start", "Disciplines"]


def strip(frag: str) -> str:
    t = re.sub(r"<[^>]+>", " ", frag)
    return re.sub(r"\s+", " ", t).strip()


def parse_facts(html: str) -> dict:
    facts = {}
    for label in FACT_LABELS:
        m = re.search(re.escape(label) + r"</[^>]+>\s*<[^>]*>([^<]+)<", html)
        if not m:
            m = re.search(re.escape(label) + r"[|]([^|<]+)", strip(html[i]) if False else html)
        if m:
            facts[label] = m.group(1).strip()
    return facts


def parse_athlete(slug: str, html: str) -> dict:
    rec = {"slug": slug, "url": f"{BASE}/us-en/athlete/{slug}"}
    m = re.search(r"<title[^>]*>(.*?)</title>", html, re.S)
    rec["title"] = strip(m.group(1)) if m else None
    m = re.search(r'property="og:title" content="([^"]+)"', html)
    rec["name"] = m.group(1).split(":")[0].strip() if m else None
    m = re.search(r'property="og:image" content="([^"]+)"', html)
    rec["hero_image"] = m.group(1) if m else None
    m = re.search(r'property="og:description" content="([^"]+)"', html)
    rec["standfirst"] = m.group(1) if m else None

    # facts panel: "Label</tag><tag>value<"
    i = html.find("Date of birth")
    if i >= 0:
        frag = html[i:i + 6000]
        text = re.sub(r"<[^>]+>", "|", frag)
        text = re.sub(r"(\|\s*)+", "|", text)
        for label in FACT_LABELS:
            if label == "Disciplines":
                # disciplines value is a nested tag list inside the table cell
                # (some athlete pages label the row "Discipline", singular)
                m2 = re.search(r"Disciplines?</p>.*?<td[^>]*>(.*?)</td>", html[i:], re.S)
                if m2:
                    inner = re.sub(r"<!--.*?-->", " ", m2.group(1), flags=re.S)
                    inner = strip(inner)
                    rec[label] = re.sub(r"\s+", " ", inner).strip()
            else:
                m = re.search(re.escape(label) + r"\|([^|]+)", text)
                if m:
                    rec[label] = m.group(1).strip()

    # bio paragraphs: inline-content paragraph items inside the athlete body
    paras = re.findall(r'<div[^>]*inline-content__item--paragraph[^>]*>(.*?)</div>', html, re.S)
    rec["bio"] = [strip(p) for p in paras if len(strip(p)) > 40 and "{" not in p]
    return rec


def parse_story(slug: str, html: str) -> dict:
    rec = {"slug": slug, "url": f"{BASE}/us-en/{slug}"}
    m = re.search(r"<title[^>]*>(.*?)</title>", html, re.S)
    rec["title"] = strip(m.group(1)) if m else None
    m = re.search(r'property="og:title" content="([^"]+)"', html)
    if m and not rec["title"]:
        rec["title"] = m.group(1)
    m = re.search(r'property="og:description" content="([^"]+)"', html)
    rec["standfirst"] = m.group(1) if m else None
    m = re.search(r'property="og:image" content="([^"]+)"', html)
    rec["hero_image"] = m.group(1) if m else None
    m = re.search(r'property="article:published_time" content="([^"]+)"', html)
    rec["published"] = m.group(1) if m else None
    # body paragraphs (inline-content paragraph items)
    paras = re.findall(r'<div[^>]*inline-content__item--paragraph[^>]*>(.*?)</div>', html, re.S)
    rec["body"] = [strip(p) for p in paras if len(strip(p)) > 60 and "{" not in p]
    m = re.search(r'"datePublished":"([^"]+)"', html)
    if m and not rec.get("published") or (rec.get("published") == "None"):
        rec["published"] = m.group(1) if m else rec.get("published")
    # discipline tag from the page header
    m = re.search(r'class="[^"]*tag[^"]*"[^>]*>\s*<[^>]*>\s*([A-Za-z &]+?)\s*<', html)
    if m:
        rec["discipline"] = m.group(1).strip()
    return rec


def main() -> None:
    # ---- athletes: the 20 the athletes hub actually lists (feed docCount) ----
    import json
    athletes = json.loads((SITE / "scraped_data" / "feeds" / "athletes.json")
                          .read_text())["items"]
    # featured-first order from the hub carousel, then alphabetical
    hub_order = ["bjorn-riley", "capjay", "cooper-dejean", "eli-tomac",
                 "sky-brown", "ronnie-albaldonado", "terry-adams",
                 "haley-adams", "ludwig-ahgren", "luke-aikins", "iitztimmy"]
    chosen, seen = [], set()
    for a in hub_order + [x["reference"]["uriSlug"] for x in athletes]:
        if a not in seen:
            seen.add(a)
            chosen.append(a)
        if len(chosen) >= 60:
            break
    print(f"scraping {len(chosen)} athlete pages")
    for slug in chosen:
        out = ATH_OUT / f"{slug}.json"
        if out.exists():
            continue
        try:
            html = fetch(f"{BASE}/us-en/athlete/{slug}", min_bytes=20000).decode("utf-8", "replace")
        except Exception as e:                                 # noqa: BLE001
            print(f"  !! {slug}: {e}")
            continue
        rec = parse_athlete(slug, html)
        save(ATH_OUT / f"{slug}.html", html.encode())
        save(out, rec)
        print(f"  ok {slug}: {rec.get('name')} facts={bool(rec.get('Date of birth'))} "
              f"bio={len(rec.get('bio', []))}")
        time.sleep(0.25)

    # ---- stories: the freshest 40 ----
    stories = json.loads((SITE / "scraped_data" / "feeds" / "stories.json")
                         .read_text())["items"][:40]
    print(f"scraping {len(stories)} story pages")
    for st in stories:
        slug = st["reference"]["uriSlug"]
        out = STO_OUT / f"{slug}.json"
        if out.exists():
            continue
        try:
            html = fetch(f"{BASE}/us-en/{slug}", min_bytes=20000).decode("utf-8", "replace")
        except Exception as e:                                 # noqa: BLE001
            print(f"  !! {slug}: {e}")
            continue
        rec = parse_story(slug, html)
        save(STO_OUT / f"{slug}.html", html.encode())
        save(out, rec)
        print(f"  ok {slug}: paras={len(rec.get('body', []))}")
        time.sleep(0.25)
    print("done")


if __name__ == "__main__":
    main()
