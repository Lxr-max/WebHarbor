#!/usr/bin/env python3
"""Capture flight results pages from us.trip.com (cards + date strip + facets).

Usage: python3 harvest_flights.py [route|all]
Routes: sfo_nyc, lax_nyc, ord_mia, las_lax, mia_nyc, sfo_las
Outputs sites/trip_com/scraped_data/flights_<route>.json
"""
import json
import pathlib
import sys
import time

sys.path.insert(0, "/tmp")
from recon_lib import Recon  # noqa: E402

BASE = pathlib.Path(__file__).resolve().parent.parent / "scraped_data"
ROUTES = {
    "sfo_nyc": ("sfo", "nyc", "2026-10-20", "2026-10-27"),
    "lax_nyc": ("lax", "nyc", "2026-10-21", "2026-10-28"),
    "ord_mia": ("ord", "mia", "2026-10-22", "2026-10-29"),
    "las_lax": ("las", "lax", "2026-10-23", "2026-10-30"),
    "mia_nyc": ("mia", "nyc", "2026-10-24", "2026-10-31"),
    "sfo_las": ("sfo", "las", "2026-10-25", "2026-11-01"),
}

EXTRACT = """() => {
  const out = {cards: [], strip: [], airlines: []};
  const body = document.body.innerText || '';
  // flight cards: locate all 'Select' buttons and climb to the card
  document.querySelectorAll('button, [role="button"], div').forEach(() => {});
  // date strip: pairs like 'Oct 16–Oct 23' + '$389'
  const stripRe = /(\\w{3} \\d{1,2}–\\w{3} \\d{1,2})\\n\\$(\\d+)/g;
  let m;
  while ((m = stripRe.exec(body)) !== null) out.strip.push({dates: m[1], price: m[2]});
  // airline facet rows: 'Delta Air Lines  (22)' + '$372'
  const airRe = /^(.+?) \\((\\d+)\\)\\n\\$(\\d+)$/gm;
  while ((m = airRe.exec(body)) !== null) out.airlines.push(
    {airline: m[1].trim(), count: m[2], price: m[3]});
  return out;
}"""


def extract_cards(page):
    return page.evaluate("""() => {
  const cards = [];
  document.querySelectorAll('[class*="flight-list"] [class*="flight-item"], [class*="list-item"], [data-testid]').forEach(() => {});
  // each flight card contains a 'Select' button; climb to its container
  const seen = new Set();
  document.querySelectorAll('button, [role="button"], span, div').forEach(el => {
    if ((el.innerText || '').trim() !== 'Select') return;
    let card = el;
    for (let i = 0; i < 14 && card.parentElement; i++) {
      card = card.parentElement;
      const t = card.innerText || '';
      if (/\\$\\d+/.test(t) && /(Nonstop|stop)/.test(t) && /\\d+h \\d+m/.test(t) && /(Airlines|Airways|Air Lines|Air)/.test(t)) break;
    }
    if (!card) return;
    const t = (card.innerText || '').slice(0, 600);
    const key = t.slice(0, 120);
    if (seen.has(key) || t.length < 40) return;
    seen.add(key);
    cards.push(t);
  });
  return cards;
}""")


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    r = Recon()
    try:
        for route, (dcity, acity, ddate, rdate) in ROUTES.items():
            if which != "all" and which != route:
                continue
            url = (f"https://us.trip.com/flights/showfarefirst?dcity={dcity}&acity={acity}"
                   f"&ddate={ddate}&rdate={rdate}&triptype=rt&class=y&quantity=1&locale=en-US&curr=USD")
            page = r.goto(url, wait=14)
            r.scroll_load(max_px=12000, pause=0.8)
            data = page.evaluate(EXTRACT)
            data["cards"] = extract_cards(page)
            data["route"] = route
            data["url"] = url
            (BASE / f"flights_{route}.json").write_text(
                json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")
            print(f"[{route}] {len(data['cards'])} cards, {len(data['strip'])} strip, "
                  f"{len(data['airlines'])} airline facets")
    finally:
        r.close()


if __name__ == "__main__":
    main()
