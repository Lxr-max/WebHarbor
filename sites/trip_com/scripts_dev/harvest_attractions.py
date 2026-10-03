#!/usr/bin/env python3
"""Capture attractions & tours listings from us.trip.com.

Usage: python3 harvest_attractions.py <city> [limit]
Outputs sites/trip_com/scraped_data/attractions_<city>.json
"""
import json
import pathlib
import sys
import time

sys.path.insert(0, "/tmp")
from recon_lib import Recon  # noqa: E402

BASE = pathlib.Path(__file__).resolve().parent.parent / "scraped_data"
CITY_SLUGS = {
    "orlando": "orlando-activities",
    "hong_kong": "hongkong-activities",
    "beijing": "beijing-day-tour",
    "shanghai": "shanghai-activities",
    "rome": "rome-activities",
}

EXTRACT = """() => {
  const out = [];
  const seen = new Set();
  document.querySelectorAll('a[href*="things-to-do/detail"]').forEach(a => {
    const href = a.getAttribute('href') || '';
    const m = href.match(/detail\\/(\\d+)/);
    if (!m || seen.has(m[1])) return;
    let card = a;
    for (let i = 0; i < 8 && card.parentElement; i++) {
      card = card.parentElement;
      const t = card.innerText || '';
      if (/\\$\\d+/.test(t) && t.length > 60) break;
    }
    const t = (card.innerText || '').slice(0, 700);
    if (t.length < 40) return;
    seen.add(m[1]);
    const img = card.querySelector('img');
    out.push({id: m[1], href: href, text: t,
              img: img ? (img.currentSrc || img.src || '') : ''});
  });
  return out;
}"""


def main():
    city = sys.argv[1] if len(sys.argv) > 1 else "orlando"
    slug = CITY_SLUGS[city]
    r = Recon()
    try:
        url = f"https://us.trip.com/things-to-do/experiences/{slug}/?locale=en-US&curr=USD"
        page = r.goto(url, wait=12)
        seen, stable = {}, 0
        for _ in range(12):
            for _ in range(3):
                page.evaluate("window.scrollBy(0, 1400)")
                time.sleep(0.8)
            cards = page.evaluate(EXTRACT)
            ids = {c["id"]: c for c in cards}
            if len(ids) == len(seen) and ids.keys() == seen.keys():
                stable += 1
                if stable >= 2:
                    break
            else:
                stable = 0
            seen = ids
        (BASE / f"attractions_{city}.json").write_text(
            json.dumps(list(seen.values()), indent=1, ensure_ascii=False), encoding="utf-8")
        print(f"[{city}] captured {len(seen)} attractions")
    finally:
        r.close()


if __name__ == "__main__":
    main()
