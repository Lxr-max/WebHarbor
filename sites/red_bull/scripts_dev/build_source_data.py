#!/usr/bin/env python3
"""Build the tracked source_data/ snapshots from the scraped_data/ captures.

This is the curation step: it merges the content feeds with the per-event
detail records, the athlete/story page parses, the product page parses and
the Shopify catalog into the stable JSON files the Flask app seeds from.
Image URLs are resolved to the upstream URLs the mirror will render; the
download_images.py step fetches exactly those URLs.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

SITE = Path(__file__).resolve().parents[1]
SCRAPED = SITE / "scraped_data"
SOURCE = SITE / "source_data"

CARD_OP = "c_fill,g_auto,w_800,h_500/q_auto,f_auto"
HERO_OP = "c_fill,g_auto,w_1200,h_630/q_auto,f_auto"

CANS: dict[str, str] = {}


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def img_url(item: dict, op: str = CARD_OP) -> str | None:
    """Resolve the feed item's cloudinary mainImage at the given op."""
    essence = ((item.get("media") or {}).get("mainImage") or {}).get("imageEssence") or {}
    url = essence.get("imageURL")
    if not url:
        return None
    return url.replace("{op}", op)


def clean_text(t: str | None) -> str:
    if not t:
        return ""
    t = t.replace("\u00a0", " ").replace("\u202f", " ")
    return re.sub(r"\s+", " ", t).strip()


def resolve_can_urls() -> dict:
    """Each product page renders the full product strip, so the per-product
    can image is identified by its distinctive upstream file key
    (us_ed_250ml_energy-drink, us_as_250ml_the-amber-edition, ...)."""
    urls = set()
    for f in (SCRAPED / "products").glob("*.html"):
        html = f.read_text(encoding="utf-8", errors="replace")
        for m in re.finditer(
                r"https://www\.redbull\.com/energydrink/v1/resources/storyblok/"
                r"images/f/287059/(?:528x1348|870x2200)/[^\"\'\s\\]+", html):
            urls.add(m.group(0))
    key = {
        "red-bull-energy-drink": "us_ed_250ml_energy-drink",
        "red-bull-zero": "us_zr_250ml_zero",
        "red-bull-sugarfree": "us_sf_250ml_sugarfree",
        "red-bull-summer-edition": "us_sl_250ml_ac_the-summer-edition",
        "red-bull-summer-edition-sugarfree": "the-summer-edition-sugarfree",
        "red-bull-apple-edition": "us_fai_250ml_ac_the-apple-edition",
        "red-bull-iced-edition": "us_igb_250ml_ac_the-iced-edition",
        "red-bull-iced-edition-sugarfree": "the-iced-edition-sugarfree",
        "red-bull-peach-edition": "us_wp_250ml_ac_the-peach-edition",
        "red-bull-peach-edition-sugarfree": "the-peach-edition-sugarfree",
        "red-bull-pink-edition": "us_ff_250ml_the-pink-edition",
        "red-bull-pink-edition-sugarfree": "the-pink-edition-sugarfree",
        "red-bull-amber-edition": "us_as_250ml_the-amber-edition",
        "red-bull-sea-blue-edition": "us_jb_250ml_the-sea-blue-edition",
        "red-bull-sea-blue-edition-sugarfree": "the-sea-blue-edition-sugarfree",
        "red-bull-coconut-edition": "us_cc_250ml_ac_the-coconut-edition",
        "red-bull-yellow-edition": "us_yl_250ml_the-yellow-edition",
        "red-bull-red-edition": "us_wm_250ml_ac_the-red-edition",
    }
    resolved = {}
    for slug, kw in key.items():
        cands = sorted({re.sub(r"/m/\d+x\d+$", "", u) for u in urls if kw in u})
        assert cands, f"no can image found for {slug}"
        resolved[slug] = cands[0]
    return resolved


def build_products() -> None:
    out = []
    for f in sorted((SCRAPED / "products").glob("*.json")):
        p = load(f)
        if not p.get("ingredients"):
            continue
        name = clean_text(p.get("og_title") or p["title"])
        name = re.split(r"[:|]", name)[0].strip()
        flavor = None
        ft = clean_text(p.get("flavor_text"))
        if ft:
            flavor = re.split(r"\s+(?=The Red Bull|Red Bull|Try the|Enjoy|Wiiings)", ft, 1)[0].strip()
        if not flavor or "Red Bull" in flavor or "red bull" in flavor:
            flavor = None
        if not flavor:
            title = clean_text(p.get("og_title") or p["title"])
            if ":" in title:
                flavor = clean_text(re.split(r":\s*", title, 1)[1].split("|")[0])
            elif "|" in title:
                flavor = clean_text(title.split("|")[1])
            if flavor and ("Red Bull" in flavor or "red bull" in flavor
                          or "Energy Drink" in flavor or "without sugar" in flavor):
                flavor = None
        ing = []
        for i in p["ingredients"]:
            ing.append({"title": clean_text(i["title"]), "text": clean_text(i["text"])})
        out.append({
            "slug": p["slug"],
            "name": name,
            "line": p["line"],
            "flavor": flavor,
            "meta_description": clean_text(p.get("meta_description")),
            "flavor_text": clean_text(p.get("flavor_text")),
            "benefits": [clean_text(b) for b in p.get("benefits", [])],
            "ingredients": ing,
            "sizes": p.get("sizes", []),
            "can_image": CANS.get(p["slug"]),
            "scene_image": (p.get("scene_images") or [None])[0],
            "og_image": p.get("og_image"),
        })
    save(SOURCE / "products.json", {"count": len(out), "products": out})
    print(f"products: {len(out)}")


def build_events() -> None:
    feed = load(SCRAPED / "feeds" / "events.json")["items"]
    out = []
    for ev in feed:
        slug = ev["reference"]["uriSlug"]
        detail_file = SCRAPED / "event_details" / f"{slug}.json"
        detail = load(detail_file) if detail_file.exists() else {}
        hero = detail.get("hero") or {}
        desc = detail.get("description") or {}
        content = ev.get("content") or {}
        tag = (content.get("tag") or {}).get("text", "")

        start = (hero.get("startDate") or {}).get("date")
        end = (hero.get("endDate") or {}).get("date")
        loc = hero.get("location") or {}
        status = ev.get("eventStatus") or hero.get("status") or "upcoming"
        # status from the feed card
        badge = ev.get("statusMessage") or ""
        if not badge:
            if ev.get("isLiveEvent"):
                badge = "LIVE NOW"
        # registration info
        reg = None
        cta = next((c for c in (hero.get("ctas") or []) if c.get("type") == "xivado"), None)
        if cta:
            reg = {"cta_text": cta.get("text"), "parent_slug": cta.get("parentSlug"),
                   "slug": cta.get("slug")}
        part = detail.get("participate") or {}
        for r in (part.get("data") or {}).get("registrations") or []:
            types = r.get("types") or []
            if types:
                price = types[0].get("price") or {}
                merged = dict(reg or {})
                merged.update({
                    "registration_title": r.get("title"),
                    "registration_date": r.get("date"),
                    "price": price.get("valueGross"),
                    "currency": (price.get("currency") or {}).get("iso3"),
                    "type_name": types[0].get("name"),
                    "type_slug": types[0].get("slug"),
                })
                reg = merged
        # description paragraphs
        paragraphs = []
        for block in desc.get("description") or []:
            if block.get("type") == "paragraph":
                texts = [clean_text(e.get("text")) for e in block.get("elements", [])
                         if e.get("variant") == "text"]
                paragraphs.append(" ".join(t for t in texts if t))
        paragraphs = [p for p in paragraphs if p]
        # schedule + faqs from tab content
        schedule, faqs = [], []
        for tab_slug, items in (detail.get("tab_content") or {}).items():
            if "schedule" in tab_slug:
                for block in items:
                    if block.get("type") == "paragraph":
                        t = clean_text(" ".join(e.get("text", "") for e in block.get("elements", [])))
                        if t:
                            schedule.append(t)
            elif "faq" in tab_slug:
                q = None
                for block in items:
                    if block.get("type") == "headline":
                        q = clean_text(block.get("text"))
                    elif block.get("type") == "paragraph" and q:
                        a = clean_text(" ".join(e.get("text", "") for e in block.get("elements", [])))
                        faqs.append({"question": q, "answer": a})
                        q = None
        series = desc.get("partOfEventSeries") or {}
        out.append({
            "slug": slug,
            "title": clean_text(content.get("title")),
            "standfirst": clean_text(content.get("standfirst")),
            "discipline": tag,
            "status": status,
            "badge": badge,
            "start_date": start,
            "end_date": end or start,
            "venue": clean_text(loc.get("place")),
            "city": clean_text(loc.get("city") or ""),
            "country": clean_text(loc.get("countryName") or ""),
            "country_code": loc.get("countryCode"),
            "image": img_url(ev, CARD_OP),
            "hero_image": ((hero.get("image") or {}).get("imageEssence") or {}).get("imageURL", "").replace("{op}", HERO_OP) or None,
            "logo_image": ((hero.get("logo") or {}).get("imageEssence") or {}).get("imageURL", "").replace("{op}", "c_limit,w_400/q_auto,f_auto") or None,
            "description": paragraphs,
            "schedule": schedule,
            "faqs": faqs,
            "registration": reg,
            "series_slug": (series.get("reference") or {}).get("uriSlug"),
            "series_title": series.get("title"),
            "is_tv_event": bool((ev.get("reference") or {}).get("isTV")),
        })
    save(SOURCE / "events.json", {"count": len(out), "events": out})
    print(f"events: {len(out)} (with registration: "
          f"{sum(1 for e in out if e['registration'])})")


def build_series() -> None:
    out = []
    for f in sorted((SCRAPED / "series").glob("*.html")):
        html = f.read_text(encoding="utf-8", errors="replace")
        slug = f.stem
        m = re.search(r'property="og:title" content="([^"]+)"', html)
        title = m.group(1) if m else slug
        m = re.search(r'property="og:description" content="([^"]+)"', html)
        standfirst = clean_text(m.group(1)) if m else ""
        stops = sorted(set(re.findall(r'href="(/us-en/events/[^"]+)"', html)))
        stops = [s.rsplit("/", 1)[-1] for s in stops]
        # hero image from the page
        m = re.search(r'property="og:image" content="([^"]+)"', html)
        image = m.group(1) if m else None
        # description paragraphs
        paras = re.findall(r'<div[^>]*inline-content__item--paragraph[^>]*>(.*?)</div>', html, re.S)
        def strip(x):
            t = re.sub(r"<[^>]+>", " ", x)
            return re.sub(r"\s+", " ", t).strip()
        body = [clean_text(strip(p)) for p in paras]
        body = [b for b in body if len(b) > 60]
        out.append({"slug": slug, "title": clean_text(title), "standfirst": standfirst,
                    "description": body[:6], "stops": stops, "image": image})
    save(SOURCE / "event_series.json", {"count": len(out), "series": out})
    print(f"series: {len(out)}")


def build_athletes() -> None:
    out = []
    for f in sorted((SCRAPED / "athletes").glob("*.json")):
        a = load(f)
        if not a.get("name"):
            continue
        out.append({
            "slug": a["slug"],
            "name": clean_text(a["name"]),
            "standfirst": clean_text(a.get("standfirst")),
            "discipline": clean_text(a.get("Disciplines") or ""),
            "dob": clean_text(a.get("Date of birth")),
            "birthplace": clean_text(a.get("Birthplace")),
            "age": clean_text(a.get("Age")),
            "nationality": clean_text(a.get("Nationality")),
            "career_start": clean_text(a.get("Career start")),
            "bio": [clean_text(b) for b in a.get("bio", [])],
            "hero_image": a.get("hero_image"),
        })
    save(SOURCE / "athletes.json", {"count": len(out), "athletes": out})
    print(f"athletes: {len(out)}")


def build_films() -> None:
    items = load(SCRAPED / "feeds" / "films.json")["items"]
    out = []
    for it in items:
        c = it.get("content") or {}
        out.append({
            "slug": it["reference"]["uriSlug"],
            "title": clean_text(c.get("title")),
            "subheading": clean_text(c.get("subHeading")),
            "standfirst": clean_text(c.get("standfirst")),
            "discipline": (c.get("tag") or {}).get("text", ""),
            "published": c.get("publishedDate"),
            "duration": it.get("duration"),
            "image": img_url(it, CARD_OP),
            "tv_url": (it["reference"].get("externalUrl")),
        })
    save(SOURCE / "films.json", {"count": len(out), "films": out})
    print(f"films: {len(out)}")


def build_shows() -> None:
    items = load(SCRAPED / "feeds" / "shows.json")["items"]
    episodes = load(SCRAPED / "feeds" / "episode_videos.json")["items"]
    by_show: dict[str, list] = {}
    for ep in episodes:
        c = ep.get("content") or {}
        show = c.get("showTitle")
        if not show:
            continue
        by_show.setdefault(show, []).append({
            "title": clean_text(c.get("title")),
            "season": c.get("seasonNumber"),
            "episode": c.get("episodeNumber"),
            "standfirst": clean_text(c.get("standfirst")),
            "duration": ep.get("duration"),
            "published": c.get("publishedDate"),
            "discipline": (c.get("tag") or {}).get("text", ""),
        })
    out = []
    for it in items:
        c = it.get("content") or {}
        title = clean_text(c.get("title"))
        eps = sorted(by_show.get(title, []), key=lambda e: (e["season"] or 0, e["episode"] or 0))
        out.append({
            "slug": it["reference"]["uriSlug"],
            "title": title,
            "subheading": clean_text(c.get("subHeading")),
            "standfirst": clean_text(c.get("standfirst")),
            "discipline": (c.get("tag") or {}).get("text", ""),
            "nr_seasons": it.get("nrOfSeasons"),
            "nr_episodes": it.get("nrOfEpisodes"),
            "image": img_url(it, CARD_OP),
            "tv_url": it["reference"].get("externalUrl"),
            "episodes": eps,
        })
    save(SOURCE / "shows.json", {"count": len(out), "shows": out})
    print(f"shows: {len(out)} (episodes for {sum(1 for s in out if s['episodes'])} shows)")


def build_stories() -> None:
    feed = {it["reference"]["uriSlug"]: it
            for it in load(SCRAPED / "feeds" / "stories.json")["items"]}
    out = []
    for f in sorted((SCRAPED / "stories").glob("*.json")):
        s = load(f)
        slug = s["slug"]
        ev = feed.get(slug, {})
        c = ev.get("content") or {}
        out.append({
            "slug": slug,
            "title": clean_text(s.get("title") or c.get("title")),
            "standfirst": clean_text(s.get("standfirst") or c.get("standfirst")),
            "discipline": (c.get("tag") or {}).get("text", "") or clean_text(s.get("discipline")),
            "published": s.get("published") if s.get("published") != "None" else None,
            "body": [clean_text(b) for b in s.get("body", [])],
            "hero_image": s.get("hero_image") or img_url(ev, HERO_OP),
        })
    save(SOURCE / "stories.json", {"count": len(out), "stories": out})
    print(f"stories: {len(out)}")


def build_shop() -> None:
    data = load(SCRAPED / "shop" / "products.json")
    products = data["products"]
    out = []
    for p in products:
        variants = []
        for v in p.get("variants", []):
            variants.append({
                "id": v["id"], "title": v["title"],
                "option1": v.get("option1"), "option2": v.get("option2"),
                "price": v.get("price"), "sku": v.get("sku"),
                "available": v.get("available"),
            })
        images = [i["src"] for i in p.get("images", [])][:2]
        tags = p.get("tags", [])
        t = (p.get("product_type") or "").lower()
        title_l = p["title"].lower()
        category = None
        if any(x in t for x in ("hat", "cap", "beanie", "bucket")):
            category = "headwear"
        elif any(x in t for x in ("glass", "goggle", "sunglass")):
            category = "eyewear"
        elif any(x in t for x in ("bag", "backpack", "duffel")):
            category = "bags"
        elif any(x in t for x in ("pant", "short", "jogger")):
            category = "bottoms"
        elif any(x in t for x in ("jersey",)):
            category = "jerseys"
        elif any(x in t for x in ("shirt", "hoodie", "jacket", "polo",
                                  "sweater", "sweatshirt", "tank", "tee")):
            category = "tops"
        if category is None:
            for tag in tags:
                tl = tag.lower()
                if tl in ("headwear", "eyewear", "bags", "accessories",
                          "tops", "bottoms", "jackets", "jerseys"):
                    category = tl
                    break
        if category is None:
            if "beanie" in title_l or "cap" in title_l or "hat" in title_l:
                category = "headwear"
            else:
                category = "accessories"
        out.append({
            "handle": p["handle"],
            "title": clean_text(p["title"]),
            "vendor": p.get("vendor"),
            "product_type": p.get("product_type"),
            "category": category,
            "tags": [t for t in tags if not t.startswith("#")],
            "published": p.get("published_at"),
            "variants": variants,
            "images": images,
            "description": clean_text(re.sub(r"<[^>]+>", " ", p.get("body_html") or ""))[:600],
        })
    save(SOURCE / "shop_products.json", {"count": len(out), "products": out})
    print(f"shop products: {len(out)}")


def save(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=1, ensure_ascii=False), encoding="utf-8")


def main() -> None:
    global CANS
    SOURCE.mkdir(exist_ok=True)
    CANS = resolve_can_urls()
    build_products()
    build_events()
    build_series()
    build_athletes()
    build_films()
    build_shows()
    build_stories()
    build_shop()


if __name__ == "__main__":
    main()
