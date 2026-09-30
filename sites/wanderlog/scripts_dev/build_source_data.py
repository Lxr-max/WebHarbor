#!/usr/bin/env python3
"""Build the tracked source_data/*.json snapshots from scraped_data/.

Everything in source_data/ is derived mechanically from the captured upstream
pages/APIs (scraped_data/, gitignored): destination explore pages, geo-category
ranked lists, place detail pages, shared-guide view pages, user profiles, the
traveler leaderboard, geo autocomplete, the hotels landing copy and the
marketing landing copy. The one authored file is benchmark_users.json — the
four benchmark accounts and their fixture trips, which reference real captured
places/dates and are documented in provenance.json.

Trim policy (declared in provenance.json): geo-category ranked lists are
included for the 11 mirrored destinations' attractions/restaurants/hotels
rankings plus two specialty rankings (Tokyo cafes, Paris free attractions),
each trimmed to the upstream top 10 entries; destination explore sections are
trimmed to the top 5 places per section; shared guides keep every section
heading/notes but trim place blocks to the first 3 per section and at most 8
per guide. The upstream __MOBX_STATE__ captures in scraped_data/ retain the
full untrimmed records this script was run against.

Run from sites/wanderlog:  python3 scripts_dev/build_source_data.py
"""
from __future__ import annotations

import html as html_mod
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.dirname(HERE)
SCRAPE = os.path.join(SITE, "scraped_data")
OUT = os.path.join(SITE, "source_data")

TAG_RE = re.compile(r"<[^>]+>")

LIST_KEEP = 10       # upstream top-N places per geo-category list
EXPLORE_KEEP = 5     # top-N places per explore section
GUIDE_SEC_KEEP = 3   # first-N place blocks per guide section
GUIDE_KEEP = 8       # max place blocks per guide


def load(name):
    with open(os.path.join(SCRAPE, name + ".json"), encoding="utf-8") as f:
        return json.load(f)


def save(name, obj):
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, name + ".json"), "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, sort_keys=True, indent=1)
    n = len(json.dumps(obj))
    print(f"[source] {name}.json: {n // 1024} KiB")


def text_of(html):
    body = re.sub(r"<script.*?</script>", " ", html, flags=re.S)
    body = re.sub(r"<style.*?</style>", " ", body, flags=re.S)
    text = html_mod.unescape(TAG_RE.sub(" ", body))
    return re.sub(r"\s+", " ", text).strip()


def quill_text(ops):
    """Flatten a Quill delta ({ops:[{insert}]}) into plain text."""
    if not ops:
        return ""
    out = []
    for op in ops:
        ins = op.get("insert", "")
        if not isinstance(ins, str):
            continue
        if op.get("attributes", {}).get("list") == "bullet" and ins.strip() == "":
            ins = ""
        out.append(ins)
    text = "".join(out)
    text = re.sub(r"\n{2,}", "\n", text)
    return text.strip()


# ------------------------------------------------------------------ landing --

def build_landing():
    with open(os.path.join(SCRAPE, "home.html"), encoding="utf-8") as f:
        home = f.read()
    with open(os.path.join(SCRAPE, "hotels_landing.html"), encoding="utf-8") as f:
        hotels = f.read()

    hero = re.search(r"<title>(.*?)</title>", home, re.S).group(1).strip()

    # feature blocks: "Features to replace all your other tools" section
    features = []
    for m in re.finditer(
            r'<h2 class="section-heading[^"]*">([^<]{8,80})</h2>(?:.*?<p class="body-text[^"]*">(.*?)</p>)?',
            home, re.S):
        title = html_mod.unescape(m.group(1)).strip()
        body = text_of(m.group(2) or "")
        if title in ("What travelers are raving about", "Recommended by the press",
                     "Join Wanderlog", "Find your next adventure",
                     "Explore hundreds of places to visit for every corner of the world",
                     "Create your ultimate travel itinerary"):
            continue
        features.append({"title": title, "text": body})
    seen, uniq = set(), []
    for f in features:
        if f["title"] not in seen:
            seen.add(f["title"])
            uniq.append(f)

    # testimonials: review cards (quote paragraph + author name + avatar)
    testimonials = []
    for m in re.finditer(
            r'class="review-card-paragraph[^>]*>.*?<p[^>]*>(.*?)</p>.*?'
            r'src="(images/[0-9a-f]+_[^" ]+\.jpg)"[^>]*class="avatar"[^>]*>.*?'
            r'class="avatar-name-name[^>]*>([^<]+)</div>',
            home, re.S):
        quote = text_of(m.group(1))
        testimonials.append({"text": quote, "name": html_mod.unescape(m.group(3)).strip(),
                             "avatar": m.group(2)})
    seen, uniqt = set(), []
    for t in testimonials:
        if t["text"] not in seen:
            seen.add(t["text"])
            uniqt.append(t)

    press = sorted(set(re.findall(r'src="(images/66c7850[0-9a-f]+_[^"]+\.jpg)"', home)))
    explore_cards = sorted(set(re.findall(r'src="(images/66e9a04a[0-9a-f]+_[0-9a-f]+_img%20[^"]+\.jpg)"', home)))
    guide_cards = sorted(set(re.findall(r'src="(images/66e9a04a[0-9a-f]+_66bbe6[0-9a-f]+_[^"]+\.jpg)"', home)))
    feature_imgs = sorted(set(re.findall(r'src="(images/66eab414[0-9a-f]+_[^"]+\.jpg)"', home)))
    avatar_imgs = []
    for t in uniqt:
        if t.get("avatar") and t["avatar"] not in avatar_imgs:
            avatar_imgs.append(t["avatar"])

    hotels_blocks = []
    for m in re.finditer(
            r'<h2 class="[^"]*LandingPageSectionHeading[^"]*">([^<]{3,60})</h2>\s*'
            r'<p class="LandingPageSectionSubheading[^"]*">(.*?)</p>', hotels, re.S):
        hotels_blocks.append({"title": html_mod.unescape(m.group(1)).strip(),
                              "text": html_mod.unescape(re.sub(r"<[^>]+>", " ", m.group(2))).strip()})

    save("landing", {
        "captured_from": "https://wanderlog.com/",
        "title": hero,
        "hero_heading": "One app for all your travel planning needs",
        "hero_sub": ("Create detailed itineraries, explore user-shared guides, and "
                     "manage your bookings seamlessly — all in one place."),
        "features": uniq[:8],
        "testimonials": uniqt[:12],
        "assets": {
            "press": press,
            "explore_cards": explore_cards,
            "guide_cards": guide_cards,
            "feature_images": feature_imgs,
            "avatars": avatar_imgs[:14],
        },
        "hotels_copy": {
            "captured_from": "https://wanderlog.com/hotels",
            "title": "Search for hotel and Airbnb stays in one place",
            "sub": ("Experience a better hotel search that helps you find the "
                    "perfect lodging, with your preferences as the highest priority."),
            "blocks": hotels_blocks[:10],
        },
    })


# ----------------------------------------------------------------- explores --

DEST_SLUGS = {1: "tokyo", 9613: "london", 9614: "paris", 9616: "rome",
              9617: "barcelona", 58144: "new-york-city", 58147: "san-francisco",
              58148: "las-vegas", 7: "singapore", 4: "bangkok", 9625: "amsterdam"}


def build_explores():
    geos, sections = {}, {}
    for gid in DEST_SLUGS:
        d = load(f"explore_{gid}")
        data = d["state"]["explorePage"]["data"]
        geo = data["geo"]
        geos[gid] = {
            "id": gid,
            "name": geo["name"],
            "stateName": geo.get("stateName"),
            "countryName": geo.get("countryName"),
            "depth": geo.get("depth"),
            "latitude": geo.get("latitude"),
            "longitude": geo.get("longitude"),
            "popularity": geo.get("popularity"),
            "subcategory": geo.get("subcategory"),
            "imageKey": geo.get("imageKey"),
            "placeDescription": geo.get("placeDescription"),
            "manualDescription": geo.get("manualDescription"),
            "bounds": geo.get("bounds"),
            "ancestors": [{"id": a["id"], "name": a["name"],
                          "countryName": a.get("countryName")}
                          for a in data.get("ancestors", [])],
            "nearby": [{"id": n["id"], "name": n["name"],
                        "countryName": n.get("countryName"),
                        "subcategory": n.get("subcategory"),
                        "imageKey": n.get("imageKey")}
                       for n in data.get("nearby", [])[:4]],
            "geoPairs": [{"fromGeo": p["fromGeo"]["name"],
                          "toGeo": p["toGeo"]["name"],
                          "imageKey": p.get("freeImageKey")}
                         for p in data.get("geoPairs", [])[:8]],
            "categories": [{"id": c["id"], "name": c["name"],
                            "shortName": c.get("shortName"),
                            "emoji": c.get("emoji"),
                            "geoCategoryName": c.get("geoCategoryName")}
                           for c in data.get("categories", [])],
            "placesLists": [{"id": p["id"], "type": p["type"], "title": p["title"],
                             "placeCount": p.get("placeCount"),
                             "topImageKey": p.get("topImageKey")}
                            for p in data.get("placesLists", [])],
        }
        secs = []
        for s in data.get("sections", []):
            blocks = []
            for b in s["places"].get("blocks", [])[:EXPLORE_KEEP]:
                if b.get("type") != "place":
                    continue
                p = b["place"]
                blocks.append({
                    "name": p.get("name"),
                    "placeId": p.get("placeId"),
                    "latitude": p.get("latitude"),
                    "longitude": p.get("longitude"),
                    "description": quill_text(b.get("text", {}).get("ops")),
                    "selectedImageKey": b.get("selectedImageKey"),
                    "imageKeys": (b.get("imageKeys") or [])[:2],
                })
            secs.append({"type": s["type"], "heading": s["places"].get("heading"),
                         "blocks": blocks})
        sections[gid] = secs

    save("geos", {"destinations": geos})
    save("explore_sections", {"sections": sections})


# -------------------------------------------------------------------- lists --

# Curated set: attractions/restaurants/hotels for every mirrored destination,
# plus two specialty rankings.
LIST_WANT = {
    "1": ["top-things-to-do-and-attractions", "where-to-eat-best-restaurants",
          "best-hotels", "best-coffee-shops-and-best-cafes"],
    "9613": ["top-things-to-do-and-attractions", "where-to-eat-best-restaurants",
             "best-hotels"],
    "9614": ["top-things-to-do-and-attractions", "where-to-eat-best-restaurants",
             "best-hotels", "best-free-attractions"],
    "9616": ["top-things-to-do-and-attractions", "where-to-eat-best-restaurants",
             "best-hotels"],
    "9617": ["top-things-to-do-and-attractions", "where-to-eat-best-restaurants",
             "best-hotels"],
    "58144": ["top-things-to-do-and-attractions", "where-to-eat-best-restaurants",
              "best-hotels"],
    "58147": ["top-things-to-do-and-attractions", "where-to-eat-best-restaurants",
              "best-hotels"],
    "58148": ["top-things-to-do-and-attractions", "where-to-eat-best-restaurants",
              "best-hotels"],
    "7": ["top-things-to-do-and-attractions", "where-to-eat-best-restaurants",
          "best-hotels"],
    "4": ["top-things-to-do-and-attractions", "where-to-eat-best-restaurants",
          "best-hotels"],
    "9625": ["top-things-to-do-and-attractions", "where-to-eat-best-restaurants",
             "best-hotels"],
}


def build_lists():
    cats = json.load(open(os.path.join(HERE, "capture_lists.json"), encoding="utf-8"))
    out = {}
    for name, cid, slug in cats:
        geo_prefix = name.split("_", 1)[0]
        wanted = LIST_WANT.get(geo_prefix, [])
        if not any(slug.startswith(w) for w in wanted):
            continue
        d = load(f"list_{name}")
        data = d["state"]["placesListPage"]["data"]
        meta_by_name = {}
        for pm in data.get("placeMetadata") or []:
            meta_by_name.setdefault(pm.get("name"), pm)
        src_sections = data.get("boardSections") or []
        blocks_all = []
        for sec in src_sections:
            blocks_all.extend(sec.get("blocks") or [])
        places = []
        for idx, b in enumerate(blocks_all[:LIST_KEEP]):
            if b.get("type") != "place":
                continue
            p = b["place"]
            pm = meta_by_name.get(p.get("name")) or {}
            places.append({
                "rank": idx + 1,
                "name": p.get("name") or pm.get("name"),
                "placeId": p.get("placeId"),
                "latitude": p.get("latitude"),
                "longitude": p.get("longitude"),
                "selectedImageKey": b.get("selectedImageKey"),
                "description": pm.get("description"),
                "placeCategories": (pm.get("categories") or [])[:6],
                "wanderlogPlaceId": pm.get("id"),
                "sources": [
                    {"siteName": s.get("siteName"),
                     "shortName": s.get("shortName"),
                     "url": s.get("url"),
                     "indexInSource": s.get("indexInSource"),
                     "snippet": s.get("snippet")}
                    for s in (pm.get("sources") or [])[:4]
                ],
            })
        out[str(cid)] = {
            "id": cid,
            "slug": slug,
            "title": data.get("title"),
            "type": data.get("type"),
            "geoId": (data.get("geo") or {}).get("id"),
            "geoName": (data.get("geo") or {}).get("name"),
            "headerImageKey": data.get("headerImageKey"),
            "distinction": data.get("distinction"),
            "upstreamCount": len(blocks_all),
            "places": places,
        }
    save("geo_categories", {"lists": out})


# ------------------------------------------------------------------- places --

def build_places():
    pids = json.load(open(os.path.join(HERE, "capture_places.json"), encoding="utf-8"))
    out = {}
    for pid in pids:
        d = load(f"place_{pid}")
        data = d["state"]["placePage"]["data"]
        mp = data.get("mapsPlace") or {}
        pm = data.get("placeMetadata") or {}
        rank = data.get("rankInGeoCategory") or {}
        out[str(pid)] = {
            "id": pid,
            "name": pm.get("name") or mp.get("name"),
            "placePageType": pm.get("placePageType"),
            "googlePlaceId": pm.get("placeId"),
            "description": pm.get("description"),
            "generatedDescription": pm.get("generatedDescription"),
            "categories": pm.get("categories"),
            "tips": data.get("tips"),
            "reasonsToVisit": data.get("reasonsToVisit"),
            "reviewsSummary": data.get("reviewsSummary"),
            "admissionDetails": mp.get("admissionDetails"),
            "latitude": mp.get("latitude"),
            "longitude": mp.get("longitude"),
            "rank": rank.get("rank"),
            "rankPageTitle": rank.get("pageTitle"),
            "rankCategory": (rank.get("name") or "").strip(),
            "relatedNearbyAttractions": [
                r.get("name") for r in
                ((data.get("relatedPagesData") or {}).get("nearbyAttractions") or [])[:8]],
            "relatedNearbyRestaurants": [
                r.get("name") for r in
                ((data.get("relatedPagesData") or {}).get("nearbyRestaurants") or [])[:8]],
        }
    save("places", {"places": out})


# ------------------------------------------------------------------- guides --

GUIDES_KEEP = ["uzyvvtuwtc", "nlcviusycz", "vayytsqzpq", "lgtwsokjcd",
               "okgarduipy", "dxpkirpjls", "wnglqezund", "hxwbckbikf",
               "tbgojyfsfr", "zlcocpeivp", "pgcjjrdlqk", "nwhizniizm",
               "znordifcrv", "jkaudfndgt"]


def build_guides():
    guides_cfg = json.load(open(os.path.join(HERE, "capture_guides.json"), encoding="utf-8"))
    slugs = dict(guides_cfg)
    out = {}
    for key in GUIDES_KEEP:
        d = load(f"guide_{key}")
        trip = d["state"]["tripPlanStore"]["data"]["tripPlan"]
        sections = []
        kept = 0
        for s in trip["itinerary"].get("sections", []):
            blocks = []
            for b in (s.get("blocks") or [])[:GUIDE_SEC_KEEP]:
                if kept >= GUIDE_KEEP:
                    break
                if b.get("type") == "place":
                    p = b["place"]
                    hours = p.get("opening_hours") or {}
                    blocks.append({
                        "kind": "place",
                        "name": p.get("name"),
                        "placeId": p.get("id"),
                        "formatted_address": p.get("formatted_address"),
                        "latitude": (p.get("geometry", {}) or {}).get("location", {}).get("lat"),
                        "longitude": (p.get("geometry", {}) or {}).get("location", {}).get("lng"),
                        "rating": p.get("rating"),
                        "website": p.get("website"),
                        "phone": p.get("formatted_phone_number"),
                        "price_level": p.get("price_level"),
                        "types": (p.get("types") or [])[:4],
                        "weekday_text": (hours.get("weekday_text") or [])[:7],
                        "note": quill_text(b.get("text", {}).get("ops")),
                        "selectedImageKey": b.get("selectedImageKey"),
                        "imageKeys": (b.get("imageKeys") or [])[:1],
                        "addedBy": (b.get("addedBy") or {}).get("userId"),
                    })
                    kept += 1
            sections.append({
                "heading": s.get("heading"),
                "type": s.get("type"),
                "placeMarkerColor": s.get("placeMarkerColor"),
                "notes": quill_text((s.get("text") or {}).get("ops")),
                "blocks": blocks,
            })
        out[key] = {
            "key": key,
            "slug": slugs[key],
            "id": trip.get("id"),
            "title": trip.get("title"),
            "type": trip.get("type"),
            "privacy": trip.get("privacy"),
            "authorBlurb": trip.get("authorBlurb"),
            "distinction": trip.get("distinction"),
            "viewCount": trip.get("viewCount"),
            "likeCount": trip.get("likeCount"),
            "placeCount": trip.get("placeCount"),
            "createdAt": trip.get("createdAt"),
            "editedAt": trip.get("editedAt"),
            "headerImageKey": trip.get("headerImageKey"),
            "author": next((e for e in (trip.get("editors") or [])
                            if e.get("id") == trip.get("userId")), None)
                          or (trip.get("editors") or [{}])[0],
            "editors": trip.get("editors") or [],
            "contributors": trip.get("contributors") or [],
            "sections": sections,
        }
    save("guides", {"guides": out})


# ------------------------------------------------------------------ profiles --

def build_profiles():
    users = []
    usernames = ["alilies", "pham2ez", "Marutravelsjapan", "taraabraham", "LizzyS",
                 "bentral", "marcusglyptis", "plavix", "affectionate_antelope",
                 "niki_wanders", "rachelirl_", "peachy2391", "achillesvig",
                 "Julia_Jablonka", "shogobusiness", "delicious_dogfish"]
    for uname in usernames:
        d = load(f"profile_{uname}")
        api = d["api"]["profile"]
        users.append({
            "user": api["user"],
            "numFollowedUsers": api.get("numFollowedUsers"),
            "numFollowingUsers": api.get("numFollowingUsers"),
            "tripPlans": [
                {"id": t["id"], "key": t["key"], "title": t["title"],
                 "type": t.get("type"), "viewCount": t.get("viewCount"),
                 "likeCount": t.get("likeCount"), "placeCount": t.get("placeCount"),
                 "editedAt": t.get("editedAt"), "headerImageKey": t.get("headerImageKey"),
                 "isPrimary": t.get("isPrimary")}
                for t in (api.get("tripPlans") or [])[:10]
            ],
        })
    lb = load("leaderboard")["api"]
    save("profiles", {
        "users": users,
        "leaderboard": {
            "visitGeosLeaders": lb.get("visitGeosLeaders", [])[:20],
            "countriesLeaders": lb.get("countriesLeaders", [])[:20],
        },
    })


# ------------------------------------------------------------- autocomplete --

def build_autocomplete():
    out = {}
    for q in ["paris", "tokyo", "london", "new-york", "rome", "barcelona",
              "amsterdam", "san-francisco", "vegas", "bangkok", "singapore",
              "kyoto", "iceland", "japan", "france", "italy", "spain", "usa",
              "united-states", "united-kingdom"]:
        d = load(f"autocomplete_{q}")
        out[q] = [
            {"id": g["id"], "name": g["name"], "stateName": g.get("stateName"),
             "countryName": g.get("countryName"), "depth": g.get("depth"),
             "subcategory": g.get("subcategory"), "popularity": g.get("popularity")}
            for g in (d["api"].get("data") or [])[:8]
        ]
    countries = load("countries")["api"]["data"]
    save("autocomplete", {
        "queries": out,
        "countries": [{"id": c["id"], "name": c["name"],
                       "countryCode": c.get("countryCode")} for c in countries],
    })


def main() -> int:
    build_landing()
    build_explores()
    build_lists()
    build_places()
    build_guides()
    build_profiles()
    build_autocomplete()
    print("[source] done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
