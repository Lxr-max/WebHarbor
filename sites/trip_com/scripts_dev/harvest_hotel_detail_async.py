#!/usr/bin/env python3
"""Async parallel capture of hotel detail pages (several tabs, one profile).

Usage: python3 harvest_hotel_detail_async.py <city> [limit] [workers]
Outputs sites/trip_com/scraped_data/hotel_details_<city>.json
"""
import asyncio
import json
import pathlib
import sys

from playwright.async_api import async_playwright

BASE = pathlib.Path(__file__).resolve().parent.parent / "scraped_data"
PROFILE = "/tmp/trip_com_profile"
CHECKIN, CHECKOUT = "2026-10-04", "2026-10-05"

EXTRACT = """() => {
  const out = {photos: [], reviews: [], amenities: [], stars: 0};
  document.querySelectorAll('img').forEach(im => {
    const src = im.currentSrc || im.src || '';
    if (/ak-\\w\\.tripcdn\\.com\\/images\\//.test(src) && !out.photos.includes(src))
      out.photos.push(src);
  });
  document.querySelectorAll('li, [class*="amenity"]').forEach(el => {
    const t = (el.innerText || '').trim();
    if (t && t.length < 40 && /^[A-Z]/.test(t) && !out.amenities.includes(t)) out.amenities.push(t);
  });
  const starEl = document.querySelector('[class*="hotelStarLevel"], [aria-label][class*="starLevel"]');
  if (starEl) {
    const m = (starEl.getAttribute('aria-label') || '').match(/\\d+/);
    if (m) out.stars = parseInt(m[0], 10);
  }
  out.title = document.title;
  out.bodyText = (document.body.innerText || '').slice(0, 22000);
  return out;
}"""


async def scroll(page, max_px=9000, pause=0.55):
    y = 0
    last_h = 0
    for _ in range(18):
        await page.evaluate(f"window.scrollTo(0, {y})")
        await asyncio.sleep(pause)
        y += 900
        h = await page.evaluate("document.body.scrollHeight")
        if y > min(h, max_px) and h == last_h:
            break
        last_h = h


async def one(page, card, sem, details, city):
    async with sem:
        hid = card["id"]
        m_city = card["href"].split("cityId=")[1].split("&")[0]
        url = (f"https://us.trip.com/hotels/detail/?cityId={m_city}&hotelId={hid}"
               f"&checkIn={CHECKIN}&checkOut={CHECKOUT}&adult=2&children=0&locale=en-US&curr=USD")
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=90000)
            await asyncio.sleep(8)
            if "Verification" in await page.title():
                await asyncio.sleep(15)
            await scroll(page)
            data = await page.evaluate(EXTRACT)
            data["id"] = hid
            data["name"] = card["name"]
            data["card_text"] = card.get("text", "")
            data["card_img"] = card.get("img", "")
            details[hid] = data
            print(f"[{city}] {hid} {card['name'][:38]}: {len(data['photos'])} photos", flush=True)
        except Exception as exc:  # noqa: BLE001
            print(f"[{city}] {hid} FAILED: {str(exc)[:100]}", flush=True)


async def main_async(city, limit, workers):
    cards = json.loads((BASE / f"hotels_{city}.json").read_text(encoding="utf-8"))
    target = cards[:limit]
    out_path = BASE / f"hotel_details_{city}.json"
    details = json.loads(out_path.read_text(encoding="utf-8")) if out_path.exists() else {}
    sem = asyncio.Semaphore(workers)
    async with async_playwright() as p:
        browser = await p.chromium.launch_persistent_context(
            PROFILE, headless=False, viewport={'width': 1360, 'height': 860},
            locale="en-US", args=["--disable-blink-features=AutomationControlled"])
        pages = [await browser.new_page() for _ in range(workers)]
        # set locale cookies on the first page (shared context cookie jar)
        await browser.add_cookies([
            {"name": "ibulocale", "value": "en-us", "domain": ".trip.com", "path": "/"},
            {"name": "ibulanguage", "value": "en", "domain": ".trip.com", "path": "/"},
            {"name": "ibu_h5_lang", "value": "en", "domain": ".trip.com", "path": "/"},
        ])
        queue = [c for c in target if c["id"] not in details]
        tasks = [one(pages[i % workers], c, sem, details, city)
                 for i, c in enumerate(queue)]
        await asyncio.gather(*tasks)
        await browser.close()
    out_path.write_text(json.dumps(details, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"[{city}] saved {len(details)} hotel details", flush=True)


def main():
    city = sys.argv[1] if len(sys.argv) > 1 else "las_vegas"
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 12
    workers = int(sys.argv[3]) if len(sys.argv) > 3 else 4
    asyncio.run(main_async(city, limit, workers))


if __name__ == "__main__":
    main()
