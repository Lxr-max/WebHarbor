#!/usr/bin/env python3
"""Capture the RETURN-leg flight cards from us.trip.com (ShowFareNext page).

Usage: python3 harvest_flights_return.py [route|all]
Outputs sites/trip_com/scraped_data/flights_ret_<route>.json
"""
import json
import pathlib
import sys

sys.path.insert(0, "/tmp")
from recon_lib import Recon  # noqa: E402
from harvest_flights import ROUTES  # noqa: E402

BASE = pathlib.Path(__file__).resolve().parent.parent / "scraped_data"

EXTRACT_CARDS = """() => {
  const cards = [];
  const seen = new Set();
  document.querySelectorAll('button, [role="button"], span, div').forEach(el => {
    if ((el.innerText || '').trim() !== 'Select') return;
    let card = el;
    for (let i = 0; i < 14 && card.parentElement; i++) {
      card = card.parentElement;
      const t = card.innerText || '';
      if (/\\$\\d+/.test(t) && /\\d+h \\d+m/.test(t) && /(Airlines|Airways|Air Lines)/.test(t)) break;
    }
    const t = (card.innerText || '').slice(0, 600);
    const key = t.slice(0, 100);
    if (seen.has(key) || t.length < 40) return;
    seen.add(key);
    cards.push(t);
  });
  return cards;
}"""


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    r = Recon()
    try:
        for route, (dcity, acity, ddate, rdate) in ROUTES.items():
            if which != "all" and which != route:
                continue
            url = (f"https://us.trip.com/flights/ShowFareNext?pagesource=list"
                   f"&triptype=RT&class=Y&quantity=1&childqty=0&babyqty=0"
                   f"&jumptype=GoToNextJournay&dcity={dcity}&acity={acity}"
                   f"&ddate={ddate}&rdate={rdate}&locale=en-US&curr=USD")
            page = r.goto(url, wait=14)
            r.scroll_load(max_px=11000, pause=0.8)
            data = {"route": route, "url": url, "cards": page.evaluate(EXTRACT_CARDS)}
            (BASE / f"flights_ret_{route}.json").write_text(
                json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")
            print(f"[{route} RET] {len(data['cards'])} cards", flush=True)
    finally:
        r.close()


if __name__ == "__main__":
    main()
