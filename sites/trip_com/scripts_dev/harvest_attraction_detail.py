#!/usr/bin/env python3
"""Capture attraction detail pages (packages, highlights, policies).

Usage: python3 harvest_attraction_detail.py <city> [limit]
Outputs sites/trip_com/scraped_data/attraction_details_<city>.json
"""
import json
import pathlib
import sys
import time

sys.path.insert(0, "/tmp")
from recon_lib import Recon  # noqa: E402

BASE = pathlib.Path(__file__).resolve().parent.parent / "scraped_data"

EXTRACT = """() => {
  const out = {photos: [], packages: []};
  document.querySelectorAll('img').forEach(im => {
    const src = im.currentSrc || im.src || '';
    if (/ak-\\w\\.tripcdn\\.com\\/images\\//.test(src) && !out.photos.includes(src))
      out.photos.push(src);
  });
  document.body.querySelectorAll('li, div').forEach(() => {});
  out.title = document.title;
  out.bodyText = (document.body.innerText || '').slice(0, 16000);
  return out;
}"""


def main():
    city = sys.argv[1] if len(sys.argv) > 1 else "orlando"
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 8
    cards = json.loads((BASE / f"attractions_{city}.json").read_text(encoding="utf-8"))
    out_path = BASE / f"attraction_details_{city}.json"
    details = json.loads(out_path.read_text(encoding="utf-8")) if out_path.exists() else {}
    r = Recon()
    try:
        for card in cards[:limit]:
            aid = card["id"]
            if aid in details:
                continue
            href = card['href']
            if href.startswith('http'):
                url = f"{href}?locale=en-US&curr=USD" if '?' not in href else f"{href}&locale=en-US&curr=USD"
            else:
                url = f"https://us.trip.com{href}?locale=en-US&curr=USD"
            try:
                page = r.goto(url, wait=10)
                r.scroll_load(max_px=9000, pause=0.7)
                data = page.evaluate(EXTRACT)
                data["id"] = aid
                data["card_text"] = card.get("text", "")
                data["card_img"] = card.get("img", "")
                details[aid] = data
                print(f"[{city}] attraction {aid}: {len(data['photos'])} photos", flush=True)
            except Exception as exc:  # noqa: BLE001
                print(f"[{city}] attraction {aid} FAILED: {str(exc)[:110]}", flush=True)
            out_path.write_text(json.dumps(details, indent=1, ensure_ascii=False), encoding="utf-8")
    finally:
        r.close()
    print(f"[{city}] saved {len(details)} attraction details", flush=True)


if __name__ == "__main__":
    main()
