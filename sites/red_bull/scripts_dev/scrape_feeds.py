#!/usr/bin/env python3
"""Scrape the Red Bull content feeds (events, athletes, films, shows,
episode videos, stories) into scraped_data/feeds/.

Every item is fetched from the public redbull.com content API at the
pagination the live site uses (page[limit]/page[offset]).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fetch_lib import feed_page, save, API, fetch_json  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "scraped_data" / "feeds"


def scrape_all_feed(kind: str, params: str, name: str, *, limit: int = 50,
                    max_items: int = 200, locale: str = "en-US%3Een-INT") -> list:
    items, offset = [], 0
    while offset < max_items:
        d = feed_page(kind, params, limit=limit, offset=offset, locale=locale)
        page = d.get("data") or []
        items.extend(page)
        meta = d.get("meta") or {}
        print(f"  {name}: +{len(page)} (total {len(items)}/{meta.get('docCount')})")
        if not meta.get("hasNext") or not page:
            break
        offset += len(page)
    save(OUT / f"{name}.json", {"kind": kind, "params": params, "items": items})
    return items


def main() -> None:
    print("== events ==")
    scrape_all_feed(
        "event-profiles",
        "filter[status][not]=canceled&scoring=featuredFresh",
        "events", limit=20, max_items=200)

    print("== athletes ==")
    scrape_all_feed(
        "person-profiles,team-profiles",
        "filter[person-profiles][subType]=athlete&spaces=redbull_com&sort=attributes.familyName",
        "athletes", limit=100, max_items=100)

    print("== films ==")
    scrape_all_feed("films", "sort=-publishedDate", "films", limit=50, max_items=100)

    print("== shows ==")
    scrape_all_feed("shows", "sort=-publishedDate", "shows", limit=50, max_items=100)

    print("== episode videos ==")
    scrape_all_feed("episode-videos", "sort=-startDate", "episode_videos",
                    limit=50, max_items=150)

    print("== stories ==")
    scrape_all_feed("stories", "scoring=freshness", "stories", limit=50, max_items=100)

    print("== event disciplines aggregate ==")
    d = fetch_json(
        f"{API}/v3/query/en-US%3Een-INT%3Een-INT?filter[type]=event-profiles"
        "&aggregate[limit]=200&rb3Locale=us-en&rb3Schema=v1:discipline_masterId")
    save(OUT / "event_disciplines.json", d)

    print("== event countries ==")
    d = fetch_json(
        f"{API}/v3/feed/en-US%3Een-INT%3Een-INT?filter[type]=event-profiles"
        "&rb3Language=en&rb3Locale=us-en&rb3Schema=v1:countries")
    save(OUT / "event_countries.json", d)

    print("== athlete countries ==")
    d = fetch_json(
        f"{API}/v3/feed/en-US%3Een-INT?filter[type]=person-profiles,team-profiles"
        "&rb3Language=en&filter[person-profiles][subType]=athlete"
        "&rb3Locale=us-en&rb3Schema=v1:countries")
    save(OUT / "athlete_countries.json", d)


if __name__ == "__main__":
    main()
