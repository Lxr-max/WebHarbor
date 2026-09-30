#!/usr/bin/env python3
"""Scrape per-event detail records into scraped_data/event_details/.

For every event in the feed we fetch, through the public content API:
  - v1:unifiedEventHero  (title, dates, venue/location, hero image, event
    logo, CTAs incl. the registration/ticketing slug, status)
  - v1:description       (description paragraphs, part-of-series)
  - v1:pageTabs          (Info / Schedule / FAQs tab URLs)
  - each Schedule/FAQs tab body via the event-details feed (v1:inlineContent)
  - participate.redbull.com registration record for events with a ticketing
    CTA (entry fee, registration window, ticket type name)
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fetch_lib import API, fetch, fetch_json, save  # noqa: E402

SITE = Path(__file__).resolve().parents[1]
FEEDS = SITE / "scraped_data" / "feeds"
OUT = SITE / "scraped_data" / "event_details"
PARTICIPATE = "https://participate.redbull.com/api/web/v1/events/{parent}/{slug}"


def event_tabs(rrn: str, base_url: str) -> list[dict]:
    url = (f"{API}/v3/query/en-US%3Een-INT?filter[id]={rrn}"
           f"&rb3PageTabsBaseUrl={base_url}&rb3Locale=us-en&rb3Schema=v1:pageTabs")
    d = fetch_json(url)
    return (d.get("data") or {}).get("tabs") or []


def tab_content(slug: str) -> list[dict]:
    url = (f"{API}/v3/feed/en-US%3Een-INT?disableUsageRestrictions=true"
           f"&filter[type]=event-details&filter[uriSlug]={slug}"
           f"&page[limit]=1&rb3Schema=v1:inlineContent&rb3Locale=us-en")
    d = fetch_json(url)
    return (d.get("data") or {}).get("items") or []


def participate(parent_slug: str, slug: str) -> dict | None:
    try:
        return fetch_json(PARTICIPATE.format(parent=parent_slug, slug=slug))
    except Exception as e:                                     # noqa: BLE001
        print(f"    participate fetch failed: {e}")
        return None


def main() -> None:
    events = json.loads((FEEDS / "events.json").read_text())["items"]
    print(f"{len(events)} events in feed")
    done = 0
    for ev in events:
        rrn = ev["id"]
        slug = ev["reference"]["uriSlug"]
        out_file = OUT / f"{slug}.json"
        if out_file.exists():
            done += 1
            continue
        rec = {"slug": slug, "id": rrn}
        try:
            hero = fetch_json(
                f"{API}/v3/query/en-US%3Een-INT?filter[id]={rrn}"
                f"&rb3Locale=us-en&rb3Schema=v1:unifiedEventHero").get("data")
            desc = fetch_json(
                f"{API}/v3/query/en-US%3Een-INT?filter[id]={rrn}"
                f"&rb3Locale=us-en&rb3Schema=v1:description").get("data")
        except Exception as e:                                 # noqa: BLE001
            print(f"  !! {slug}: hero/description failed: {e}")
            continue
        if not hero:
            print(f"  !! {slug}: no hero data")
            continue
        rec["hero"] = hero
        rec["description"] = desc
        # tabs -> schedule/faqs bodies
        base_url = f"/us-en/events/{slug}/"
        try:
            tabs = event_tabs(rrn, base_url)
        except Exception as e:                                 # noqa: BLE001
            tabs = []
            print(f"  ! {slug}: tabs failed: {e}")
        rec["tabs"] = tabs
        rec["tab_content"] = {}
        for tab in tabs:
            tab_slug = tab["url"].rstrip("/").rsplit("/", 1)[-1]
            if tab_slug == slug:
                continue
            try:
                rec["tab_content"][tab_slug] = tab_content(tab_slug)
            except Exception as e:                             # noqa: BLE001
                print(f"  ! {slug}: tab {tab_slug} failed: {e}")
            time.sleep(0.2)
        # participate/ticketing record when a xivado CTA exists
        cta = next((c for c in (hero.get("ctas") or [])
                    if c.get("type") == "xivado"), None)
        if cta:
            rec["participate"] = participate(cta["parentSlug"], cta["slug"])
        save(out_file, rec)
        done += 1
        tags = " +participate" if cta else ""
        tabs_n = len([t for t in tabs if t["url"].rstrip("/").rsplit("/", 1)[-1] != slug])
        print(f"  ok {slug} (tabs {tabs_n}{tags}) [{done}/{len(events)}]")
        time.sleep(0.25)
    print(f"done: {done}/{len(events)}")


if __name__ == "__main__":
    main()
