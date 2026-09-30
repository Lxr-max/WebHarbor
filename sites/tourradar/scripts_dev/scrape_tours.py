#!/usr/bin/env python3
"""Phase B: scrape full tour detail pages for a list of tour ids.

Usage: python3 scrape_tours.py <ids_file> <out_file> [--workers N]

Each tour record captures the rendered content of /t/<id>: breadcrumbs,
price box, attributes, itinerary, included/not-included, operated-by stats,
moments, reviews + subratings, departure rows (dates & prices panel),
good-to-know, Q&A, videos, similar links, and every image URL served.
"""
import json
import pathlib
import sys
import time
from concurrent.futures import ThreadPoolExecutor

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "scraped_data"

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

EXTRACT_JS = """() => {
  const pick = (sel) => { const e = document.querySelector(sel); return e ? e.innerText.trim() : null; };
  const bodyText = document.body.innerText || '';
  const out = {};
  out.title = pick('h1');
  // breadcrumbs
  const crumbs = [...document.querySelectorAll('nav a, [class*=breadcrumb] a, ol a')].map(a => a.innerText.trim()).filter(t => t && t !== 'Home' && t.length < 60);
  out.breadcrumbs = crumbs;
  // price box
  const pm = bodyText.match(/From\\n\\$([\\d,]+)\\nUS\\$(\\d[\\d,]*) per person/);
  if (pm) { out.price_from = parseInt(pm[1].replace(/,/g, '')); out.price_current = parseInt(pm[2].replace(/,/g, '')); }
  // meta line: "7 days • Start and end in London"
  const mm = bodyText.match(/\\n(\\d+) days\\s*[•\\n]+\\s*Start and end in ([^\\n]+)/);
  if (mm) { out.duration_days = parseInt(mm[1]); out.start_end = mm[2].trim(); }
  const rm = bodyText.match(/(\\d\\.\\d)\\n\\(([\\d,]+) reviews\\)/);
  if (rm) { out.rating = parseFloat(rm[1]); out.review_count = parseInt(rm[2].replace(/,/g, '')); }
  // operator
  const om = bodyText.match(/(Platinum Operator|Gold Operator|Silver Operator|Verified Operator)\\n([^\\n]+)/);
  if (om) { out.operator_badge = om[1]; out.operator = om[2].trim(); }
  // attributes (icon rows under title)
  const attrNames = ['City & Culture','Adventure','Hiking & Trekking','River Cruise','Safari','Beach','In-Depth Cultural','Coach / Bus','Train / Rail','Bicycle','Family','Private','Northern Lights','Wildlife','Food & Culinary','Sailing','Polar','Health, Spa & Wellness','Festival & Events','Overland Truck','Nature & Wildlife','Adventure & Adrenaline','Food & Wine','Wellness & Retreats','Ancient Wonders','Road Trip & Self-Drive','Group Tour','Independent Tour','Private Tour','Fully Guided','Partially Guided','Self-Guided','Easy Intensity','Light Intensity','Medium Intensity','Challenging Intensity'];
  out.attributes = [];
  for (const name of attrNames) {
    const zoneEnd = bodyText.indexOf('\\nItinerary\\n');
    const zone = zoneEnd > 0 ? bodyText.slice(0, zoneEnd) : bodyText.slice(0, 4000);
    const idx = zone.indexOf('\\n' + name + '\\n');
    if (idx >= 0) {
      const after = zone.slice(idx + name.length + 2).split('\\n')[0];
      out.attributes.push({name: name, tip: after.trim().slice(0, 160)});
    }
  }
  const gm = bodyText.match(/Group Size (\\d+) - (\\d+)/);
  if (gm) { out.group_min = parseInt(gm[1]); out.group_max = parseInt(gm[2]); }
  const am = bodyText.match(/Ages (\\d+)\\+/);
  if (am) out.min_age = parseInt(am[1]);
  const lm = bodyText.match(/Guided in (\\w+)/);
  if (lm) out.guided_language = lm[1];
  // images
  out.images = [...document.querySelectorAll('img')].map(i => ({src: i.currentSrc || i.src, alt: (i.alt || '').slice(0, 120)})).filter(x => x.src && !x.src.includes('data:'));
  // links for similar
  out.tour_links = [...new Set([...document.querySelectorAll("a[href^='/t/']")].map(a => a.getAttribute('href')))].slice(0, 30);
  out.dest_links = [...new Set([...document.querySelectorAll("a[href^='/d/']")].map(a => ({h: a.getAttribute('href'), t: a.innerText.trim()})))].slice(0, 30);
  return out;
}"""

ITINERARY_JS = """() => {
  // expand all itinerary days
  const btns = [...document.querySelectorAll('button')].filter(b => /^Expand all$/i.test((b.innerText || '').trim()));
  btns.forEach(b => b.click());
  return true;
}"""

DAYS_JS = """() => {
  // itinerary day blocks: heading "Day N" then title then description
  const out = [];
  const days = [...document.querySelectorAll('h3, h2, [class*=day]')].filter(e => /^Day \\d+$/.test((e.innerText || '').trim()));
  days.forEach(dh => {
    let node = dh;
    const day = parseInt((dh.innerText || '').replace('Day ', ''));
    // the day header carries data-id, the key the itineraries-descriptions
    // API uses for that day block (the API key order does NOT always match
    // the DOM day order, so the id is required for a correct join)
    let hdr = dh.closest('[data-id]');
    const dataId = hdr ? hdr.getAttribute('data-id') : null;
    // climb to container with the full day text
    let cont = dh.parentElement;
    for (let i = 0; i < 6; i++) {
      if (cont && cont.innerText && cont.innerText.length > 150 && /Day \\d/.test(cont.innerText)) break;
      cont = cont ? cont.parentElement : null;
    }
    if (!cont) return;
    const t = cont.innerText || '';
    if (t.length > 4000) return;
    out.push({day: day, data_id: dataId, text: t.slice(0, 2500)});
  });
  // dedupe by day keeping first
  const seen = new Set(); const res = [];
  for (const d of out) { if (!seen.has(d.day)) { seen.add(d.day); res.push(d); } }
  return res;
}"""

DEPARTURES_JS = """() => {
  const rows = [];
  document.querySelectorAll('li').forEach(e => {
    const t = (e.innerText || '').trim();
    if (/From \\w+\\n\\d+ \\w+, \\d{4}\\nTo \\w+\\n\\d+ \\w+, \\d{4}/.test(t) && t.length < 420) {
      rows.push(t.slice(0, 400));
    }
  });
  return rows;
}"""

QA_JS = """() => {
  const out = [];
  const idx = document.body.innerText.indexOf('What our customers ask about this tour');
  if (idx < 0) return out;
  const seg = document.body.innerText.slice(idx, idx + 9000);
  return seg.slice(0, 8000);
}"""

GOODTOKNOW_JS = """() => {
  const idx = document.body.innerText.indexOf('Good to Know');
  if (idx < 0) return null;
  const seg = document.body.innerText.slice(idx, idx + 3500);
  return seg;
}"""

REVIEW_PANEL_JS = """() => {
  const idx = document.body.innerText.indexOf('Overall rating based on');
  if (idx < 0) return null;
  return document.body.innerText.slice(idx, idx + 12000);
}"""

MOMENTS_JS = """() => {
  const idx = document.body.innerText.indexOf('Traveler Moments');
  if (idx < 0) return null;
  return document.body.innerText.slice(idx, idx + 2500);
}"""

INCLUDED_JS = """() => {
  const idx = document.body.innerText.indexOf("What's Included");
  const idx2 = document.body.innerText.indexOf("What's Not Included");
  if (idx < 0) return null;
  const end = idx2 > idx ? idx2 : idx + 6000;
  return document.body.innerText.slice(idx, end);
}"""

OPPANEL_JS = """() => {
  const idx = document.body.innerText.indexOf('Operated by');
  if (idx < 0) return null;
  return document.body.innerText.slice(idx, idx + 900);
}"""


def scrape_tour(page, tour_id):
    url = f"https://www.tourradar.com/t/{tour_id}"
    rec = {"tour_id": tour_id, "url": url}
    page.goto(url, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(7000)
    # dismiss any popup (newsletter etc.)
    for sel in ["button:has-text('No thanks')", "button:has-text('Close')", "[aria-label='Close']", "button:has-text('Accept')"]:
        try:
            b = page.locator(sel).first
            if b.count() and b.is_visible(timeout=800):
                b.click(timeout=1500)
                page.wait_for_timeout(600)
        except Exception:
            pass
    rec.update(page.evaluate(EXTRACT_JS))
    # itinerary (expand first)
    try:
        page.evaluate(ITINERARY_JS)
        page.wait_for_timeout(1200)
        rec["days_raw"] = page.evaluate(DAYS_JS)
    except Exception as e:
        rec["days_raw"] = []
    rec["included_raw"] = page.evaluate(INCLUDED_JS)
    rec["op_panel_raw"] = page.evaluate(OPPANEL_JS)
    rec["moments_raw"] = page.evaluate(MOMENTS_JS)
    rec["reviews_raw"] = page.evaluate(REVIEW_PANEL_JS)
    rec["goodtoknow_raw"] = page.evaluate(GOODTOKNOW_JS)
    rec["qa_raw"] = page.evaluate(QA_JS)
    # departures: open the dates panel
    dep_rows = []
    try:
        page.evaluate("""() => {
          const b = document.querySelector('.ao-tour-above-fold__booking-intention-button') ||
                    [...document.querySelectorAll('button')].find(x => /dates & prices/i.test(x.innerText || ''));
          if (b) b.click();
        }""")
        page.wait_for_timeout(3500)
        for _ in range(5):
            more = page.evaluate("""() => {
              const b = [...document.querySelectorAll('button')].find(x => /show more (dates|upcoming dates)/i.test(x.innerText || ''));
              if (b) { b.scrollIntoView({block: 'center'}); b.click(); return true; }
              return false;
            }""")
            page.wait_for_timeout(1500)
            if not more:
                break
        dep_rows = page.evaluate(DEPARTURES_JS)
    except Exception:
        dep_rows = []
    rec["departures_raw"] = dep_rows
    # room options from the first non-sold-out departure: click Confirm Dates
    try:
        page.evaluate("""() => {
          const rows = [...document.querySelectorAll('li')].filter(e => /Guaranteed departure/.test(e.innerText || '') && !/Sold out/.test(e.innerText || ''));
          const btn = rows.length ? [...rows[0].querySelectorAll('button')].find(b => /Confirm Dates/i.test(b.innerText || '')) : null;
          if (btn) btn.click();
        }""")
        page.wait_for_timeout(4000)
        room = page.evaluate("""() => {
          if (!/book-now/.test(location.href)) return null;
          const idx = document.body.innerText.indexOf('Select accommodation');
          if (idx < 0) return null;
          return document.body.innerText.slice(idx, idx + 1600);
        }""")
        rec["rooms_raw"] = room
        rec["book_url"] = page.url
    except Exception:
        rec["rooms_raw"] = None
    return rec


def worker(ids, out_path):
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
        ctx = browser.new_context(viewport={"width": 1440, "height": 1000}, user_agent=UA, locale="en-US")
        page = ctx.new_page()
        for tid in ids:
            for attempt in range(3):
                try:
                    rec = scrape_tour(page, tid)
                    results.append(rec)
                    print(f"[t/{tid}] ok days={len(rec.get('days_raw') or [])} deps={len(rec.get('departures_raw') or [])}", flush=True)
                    break
                except Exception as e:
                    print(f"[t/{tid}] attempt {attempt} ERR {str(e)[:90]}", flush=True)
                    time.sleep(3)
        browser.close()
    pathlib.Path(out_path).write_text(json.dumps(results, indent=1))
    return len(results)


def main():
    ids_file, out_file = sys.argv[1], sys.argv[2]
    workers = int(sys.argv[3]) if len(sys.argv) > 3 else 4
    ids = [int(x) for x in pathlib.Path(ids_file).read_text().split() if x.strip()]
    chunks = [[] for _ in range(workers)]
    for i, tid in enumerate(ids):
        chunks[i % workers].append(tid)
    threads = []
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for i, chunk in enumerate(chunks):
            if chunk:
                threads.append(ex.submit(worker, chunk, f"{out_file}.{i}"))
    total = sum(t.result() for t in threads)
    # merge
    merged = []
    for i in range(workers):
        f = pathlib.Path(f"{out_file}.{i}")
        if f.exists():
            merged.extend(json.loads(f.read_text()))
            f.unlink()
    pathlib.Path(out_file).write_text(json.dumps(merged, indent=1))
    print("DONE", total)


if __name__ == "__main__":
    main()
