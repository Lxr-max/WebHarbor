#!/usr/bin/env python3
"""Capture city SEO hotel-list pages (stars, addresses, review quotes, prices).

Usage: python3 harvest_city_seo.py [city|all]
Outputs sites/trip_com/scraped_data/seo_<city>.json
"""
import json
import pathlib
import sys

sys.path.insert(0, "/tmp")
from recon_lib import Recon  # noqa: E402

BASE = pathlib.Path(__file__).resolve().parent.parent / "scraped_data"
CITY_IDS = {
    "las_vegas": 26282,
    "new_york": 633,
    "los_angeles": 347,
    "orlando": 1187,
    "san_francisco": 313,
    "chicago": 549,
    "miami": 25773,
    "new_orleans": 1186,
}

EXTRACT = """() => {
  const out = [];
  document.querySelectorAll('.Template-Grid-Hotel-Cards-hotel-card').forEach(card => {
    const a = card.querySelector('a[href*="hotel-detail-"], a[href*="/hotels/"]');
    const img = card.querySelector('img');
    const h3 = card.querySelector('h3');
    const loc = card.querySelector('[class*="hotel-location"]');
    const desc = card.querySelector('[class*="hotel-description"]');
    const score = card.querySelector('[class*="rating-score"]');
    const cnt = card.querySelector('[class*="rating-count"]');
    if (!h3) return;
    const name = h3.childNodes.length ? h3.childNodes[0].textContent.trim() : h3.innerText.trim();
    const starsEl = h3.querySelector('[class*="stars"]');
    const priceEl = Array.from(card.querySelectorAll('*')).find(e =>
      /^\\$\\d+$/.test((e.childNodes[0] && e.childNodes[0].textContent || '').trim()));
    out.push({
      name: name,
      stars: starsEl ? starsEl.textContent.trim().length : 0,
      href: a ? a.getAttribute('href') : '',
      img: img ? img.src : '',
      address: loc ? (loc.innerText || '').replace(/^\\ud83d\\udccd\\s*/, '').trim() : '',
      quote: desc ? (desc.innerText || '').trim() : '',
      score: score ? score.innerText.trim() : '',
      reviews: cnt ? (cnt.innerText || '').replace(/[^\\d]/g, '') : '',
      price: priceEl ? priceEl.innerText.trim() : '',
    });
  });
  return out;
}"""


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    r = Recon()
    try:
        for city, cid in CITY_IDS.items():
            if which != "all" and which != city:
                continue
            url = f"https://us.trip.com/hotels/{city.replace('_', '-')}-hotels-list-{cid}/?locale=en-US&curr=USD"
            page = r.goto(url, wait=9)
            r.scroll_load(max_px=14000, pause=0.7)
            cards = page.evaluate(EXTRACT)
            (BASE / f"seo_{city}.json").write_text(
                json.dumps(cards, indent=1, ensure_ascii=False), encoding="utf-8")
            print(f"[{city}] {len(cards)} seo cards", flush=True)
    finally:
        r.close()


if __name__ == "__main__":
    main()
