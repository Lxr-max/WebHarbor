#!/usr/bin/env python3
"""Capture hotel detail pages from us.trip.com (rooms, amenities, reviews, photos).

Reads hotels_<city>.json card lists, visits each hotel detail page, extracts a
structured snapshot. Usage: python3 harvest_hotel_detail.py <city> [limit]
"""
import json
import pathlib
import re
import sys
import time

sys.path.insert(0, "/tmp")
from recon_lib import Recon  # noqa: E402

BASE = pathlib.Path(__file__).resolve().parent.parent / "scraped_data"
CHECKIN, CHECKOUT = "2026-10-04", "2026-10-05"

EXTRACT = """() => {
  const out = {photos: [], rooms: [], reviews: [], amenities: [], surroundings: []};
  // gallery photos
  document.querySelectorAll('img').forEach(im => {
    const src = im.currentSrc || im.src || '';
    if (/ak-\\w\\.tripcdn\\.com\\/images\\//.test(src) && !out.photos.includes(src))
      out.photos.push(src);
  });
  // room cards: name + bed + price rows
  document.querySelectorAll('[class*="roomName"], [class*="room-name"]').forEach(el => {
    let card = el.closest('[class*="room"], [class*="Room"]');
    if (!card) card = el.parentElement;
    for (let i = 0; i < 6 && card && card.parentElement && !card.innerText; i++) card = card.parentElement;
    if (!card) return;
    out.rooms.push((card.innerText || el.innerText || '').slice(0, 700));
  });
  // reviews
  document.querySelectorAll('[class*="review"]').forEach(el => {
    const t = (el.innerText || '').trim();
    if (t.length > 40 && t.length < 500 && !out.reviews.includes(t)) out.reviews.push(t);
  });
  // amenity list items
  document.querySelectorAll('li, [class*="amenity"]').forEach(el => {
    const t = (el.innerText || '').trim();
    if (t && t.length < 40 && /^[A-Z]/.test(t) && !out.amenities.includes(t)) out.amenities.push(t);
  });
  // surroundings
  document.querySelectorAll('[class*="surround"]').forEach(el => {
    const t = (el.innerText || '').trim();
    if (t) out.surroundings.push(t.slice(0, 400));
  });
  out.title = document.title;
  out.bodyText = (document.body.innerText || '').slice(0, 22000);
  return out;
}"""


def main():
    city = sys.argv[1] if len(sys.argv) > 1 else "las_vegas"
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    cards = json.loads((BASE / f"hotels_{city}.json").read_text(encoding="utf-8"))
    target = cards[:limit]
    out_path = BASE / f"hotel_details_{city}.json"
    details = json.loads(out_path.read_text(encoding="utf-8")) if out_path.exists() else {}
    r = Recon()
    try:
        for card in target:
            hid = card["id"]
            if hid in details:
                continue
            url = (f"https://us.trip.com/hotels/detail/?cityId={card['href'].split('cityId=')[1].split('&')[0]}"
                   f"&hotelId={hid}&checkIn={CHECKIN}&checkOut={CHECKOUT}&adult=2&children=0&locale=en-US&curr=USD")
            try:
                page = r.goto(url, wait=10)
                r.scroll_load(max_px=9000, pause=0.7)
                data = page.evaluate(EXTRACT)
                data["id"] = hid
                data["name"] = card["name"]
                data["card_text"] = card.get("text", "")
                data["card_img"] = card.get("img", "")
                details[hid] = data
                print(f"[{city}] hotel {hid} {card['name'][:40]}: "
                      f"{len(data['photos'])} photos, {len(data['rooms'])} rooms")
            except Exception as exc:  # noqa: BLE001
                print(f"[{city}] hotel {hid} FAILED: {str(exc)[:120]}")
            out_path.write_text(json.dumps(details, indent=1, ensure_ascii=False), encoding="utf-8")
    finally:
        r.close()
    print(f"[{city}] saved {len(details)} hotel details")


if __name__ == "__main__":
    main()
