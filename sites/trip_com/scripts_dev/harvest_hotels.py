#!/usr/bin/env python3
"""Capture hotel search-result cards from us.trip.com results pages.

Usage: python3 harvest_hotels.py [city|all]
Outputs sites/trip_com/scraped_data/hotels_<city>.json
"""
import json
import pathlib
import sys
import time

sys.path.insert(0, "/tmp")
from recon_lib import Recon  # noqa: E402

BASE = pathlib.Path(__file__).resolve().parent.parent / "scraped_data"
CITIES = {
    "las_vegas": 26282,
    "new_york": 633,
    "los_angeles": 347,
    "orlando": 1187,
    "san_francisco": 313,
    "chicago": 549,
    "miami": 25773,
    "new_orleans": 1186,
}
CHECKIN, CHECKOUT = "2026-10-04", "2026-10-05"

EXTRACT = """() => {
  const out = [];
  document.querySelectorAll('.hotel-card').forEach(card => {
    const a = card.querySelector('a.hotelName, a[href*="hotelId="]');
    if (!a) return;
    const href = a.getAttribute('href') || '';
    const m = href.match(/hotelId=(\\d+)/);
    if (!m) return;
    const img = card.querySelector('img');
    out.push({
      id: m[1],
      name: a.innerText.trim(),
      href: href,
      img: img ? (img.currentSrc || img.src) : '',
      text: (card.innerText || '').slice(0, 1000),
    });
  });
  return out;
}"""


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    r = Recon()
    try:
        for city, cid in CITIES.items():
            if which != "all" and which != city:
                continue
            url = (f"https://us.trip.com/hotels/list?city={cid}"
                   f"&checkin={CHECKIN}&checkout={CHECKOUT}&locale=en-US&curr=USD")
            page = r.goto(url, wait=12)
            # incremental scroll+extract until the card count is stable twice
            stable, seen_ids = 0, {}
            for _ in range(14):
                for _ in range(3):
                    page.evaluate("window.scrollBy(0, 1400)")
                    time.sleep(0.8)
                cards = page.evaluate(EXTRACT)
                ids = {c["id"]: c for c in cards}
                if len(ids) == len(seen_ids) and ids.keys() == seen_ids.keys():
                    stable += 1
                    if stable >= 2:
                        break
                else:
                    stable = 0
                seen_ids = ids
            (BASE / f"hotels_{city}.json").write_text(
                json.dumps(list(seen_ids.values()), indent=1, ensure_ascii=False),
                encoding="utf-8")
            print(f"[{city}] captured {len(seen_ids)} cards; first: "
                  f"{next(iter(seen_ids.values()))['name']}", flush=True)
    finally:
        r.close()


if __name__ == "__main__":
    main()
