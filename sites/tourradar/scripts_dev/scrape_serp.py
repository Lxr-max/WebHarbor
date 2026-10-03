#!/usr/bin/env python3
"""Phase A: scrape SERP tour cards for a set of destinations.

Writes scraped_data/serp_cards.json (list of card dicts, deduped by tour id)
plus per-destination raw text dumps for landing-page copy.
"""
import json
import pathlib
import re
import sys
import time

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "scraped_data"
OUT.mkdir(exist_ok=True)

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

# destination slugs to sweep (mix of countries + regions so filters have depth)
DESTS = [
    "japan", "egypt", "morocco", "south-africa", "china", "india",
    "new-zealand", "philippines", "sri-lanka", "thailand", "vietnam",
    "croatia", "greece", "iceland", "ireland", "italy", "portugal",
    "scotland", "spain", "turkey", "canada", "costa-rica", "usa",
    "argentina", "brazil", "chile", "peru", "mexico", "kenya",
    "tanzania", "namibia", "jordan", "nepal", "france", "england",
    "germany", "switzerland", "indonesia", "australia", "europe",
    "africa", "asia", "latin-america",
]

CARD_JS = """() => {
  const cards = [...document.querySelectorAll('article, li, [class*=tour-card i]')].filter(e => {
    const t = e.innerText || '';
    return e.querySelector("a[href^='/t/']") && /\\$/.test(t) && /days/i.test(t) && t.length > 150 && t.length < 1600;
  });
  const out = [];
  cards.forEach(e => {
    const a = e.querySelector("a[href^='/t/']");
    const img = e.querySelector('img');
    const m = (a.getAttribute('href') || '').match(/\\/t\\/(\\d+)/);
    if (!m) return;
    out.push({
      tour_id: parseInt(m[1]),
      href: a.getAttribute('href'),
      text: (e.innerText || '').replace(/\\r/g, ''),
      img: img ? (img.currentSrc || img.src || '') : '',
      img_alt: img ? (img.alt || '') : '',
    });
  });
  return out;
}"""


def parse_card(card):
    """Turn the raw card text into structured fields."""
    text = card["text"]
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    d = {"tour_id": card["tour_id"], "image": card["img"], "image_alt": card["img_alt"]}
    # name: line before the rating line "4.8"
    name = None
    for i, l in enumerate(lines):
        if re.fullmatch(r"\d\.\d", l) and i > 0:
            name = lines[i - 1]
            d["rating"] = float(l)
            break
    if name is None:
        # fallback: first long line
        for l in lines:
            if len(l) > 12 and not re.match(r"^(View|US\\$|\\$|\\d|From)", l):
                name = l
                break
    d["name"] = name or lines[0]
    for i, l in enumerate(lines):
        m = re.fullmatch(r"\(([\d,]+) reviews?\)", l)
        if m:
            d["review_count"] = int(m.group(1).replace(",", ""))
            break
    # quote review
    qm = re.search(r"\u201c(.+?)\u201d", text)
    if qm:
        d["card_quote"] = qm.group(1)[:200]
        qtail = re.search(r"\u201d\\s*\\n?([A-Z][\\w .-]+), traveled in (\\w+)", text)
        if qtail:
            d["card_quote_author"] = qtail.group(1)
            d["card_quote_month"] = qtail.group(2)
    # key: value rows
    def field(label):
        m = re.search(re.escape(label) + r"\n(.+?)(?:\n|$)", text)
        return m.group(1).strip() if m else None
    d["duration"] = field("Duration")
    d["age_range"] = field("Age Range")
    d["operator"] = field("Operator")
    d["destinations"] = field("Destinations")
    d["operated_in"] = field("Operated in")
    d["islands"] = field("Islands")
    d["region"] = field("Region")
    # style: first short line before name
    for l in lines[:4]:
        if l in {"City & Culture", "Adventure", "Hiking & Trekking", "River Cruise",
                 "Safari", "Beach", "In-Depth Cultural", "Coach / Bus", "Train / Rail",
                 "Bicycle", "Family", "Private", "Northern Lights", "Wildlife",
                 "Food & Culinary", "Sailing", "Polar", "Health, Spa & Wellness",
                 "Festival & Events", "Overland Truck", "Adventure & Adrenaline",
                 "Food & Wine", "Nature & Wildlife", "Wellness & Retreats",
                 "Ancient Wonders"}:
            d["style"] = l
            break
    # price: "From $4,901" then "US$4,362per person" or "$1,735 per person"
    fm = re.search(r"From \$([\d,]+)", text) or re.search(r"From\n\$([\d,]+)", text)
    if fm:
        d["price_from"] = int(fm.group(1).replace(",", ""))
    cm = re.search(r"US\\\$(\d[\d,]*)\s*per person", text.replace("\n", " "))
    if cm:
        d["price_current"] = int(cm.group(1).replace(",", ""))
    pm = re.search(r"Price based on (.+?)(?:\n|$)", text)
    if pm:
        d["price_basis"] = pm.group(1).strip()
    dm = re.search(r"^(\d+)% Off$", text, re.M)
    if dm:
        d["discount_pct"] = int(dm.group(1))
    return d


def main():
    cards = {}
    dest_text = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
        ctx = browser.new_context(viewport={"width": 1440, "height": 1000}, user_agent=UA, locale="en-US")
        page = ctx.new_page()
        for slug in DESTS:
            url = f"https://www.tourradar.com/srp/d-{slug}?adults=2"
            for attempt in range(3):
                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=60000)
                    page.wait_for_timeout(7000)
                    # scroll to trigger lazy loads
                    for _ in range(6):
                        page.mouse.wheel(0, 2500)
                        page.wait_for_timeout(900)
                    page.mouse.wheel(0, 0)
                    page.wait_for_timeout(800)
                    raw = page.evaluate(CARD_JS)
                    added = 0
                    for c in raw:
                        if c["tour_id"] not in cards:
                            cards[c["tour_id"]] = parse_card(c)
                            added += 1
                    dest_text[slug] = page.evaluate("() => document.body.innerText")
                    print(f"[{slug}] cards={len(raw)} new={added} total={len(cards)}", flush=True)
                    break
                except Exception as e:
                    print(f"[{slug}] attempt {attempt} ERR {str(e)[:100]}", flush=True)
                    time.sleep(3)
        browser.close()
    (OUT / "serp_cards.json").write_text(json.dumps(list(cards.values()), indent=1))
    (OUT / "dest_text.json").write_text(json.dumps(dest_text, indent=1))
    print("TOTAL unique tours:", len(cards))


if __name__ == "__main__":
    main()
