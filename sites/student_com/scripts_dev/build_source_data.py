"""Normalize scraped_data into the tracked source_data/ used by seed_data.py.

source_data/ is committed to git: properties.json, universities.json, cities.json,
jobs.json, home.json, reviews folded into properties. All content real, captured
from the upstream site (see provenance.json for the exact sources).
"""
import json, pathlib, re, sys
from html import unescape

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRAP = ROOT / "scraped_data"
SRC = ROOT / "source_data"
SRC.mkdir(exist_ok=True)

STATES = {"tx": "Texas", "fl": "Florida", "ga": "Georgia", "oh": "Ohio"}
CITY_NAMES = {
    "austin": "Austin", "college-station": "College Station", "houston": "Houston",
    "san-marcos": "San Marcos", "lubbock": "Lubbock", "bryan": "Bryan",
    "gainesville": "Gainesville", "orlando": "Orlando", "tampa": "Tampa",
    "tallahassee": "Tallahassee", "coral-gables": "Coral Gables", "boca-raton": "Boca Raton",
    "atlanta": "Atlanta", "athens": "Athens", "columbus": "Columbus", "oxford": "Oxford",
    "cleveland": "Cleveland", "cincinnati": "Cincinnati", "kent": "Kent",
}

def norm_price(v):
    if v is None:
        return None
    try:
        return int(round(float(v)))
    except (TypeError, ValueError):
        return None

def main():
    # ---------- universities ----------
    unis = json.load(open(SCRAP / "universities.json"))
    srp = json.load(open(SCRAP / "srp_properties.json"))
    alias_path = SCRAP / "uni_aliases.json"
    aliases = json.load(open(alias_path)) if alias_path.exists() else {}
    uni_out = {}
    for slug, u in unis.items():
        rec = {
            "slug": slug, "name": u["name"], "state": u["state"], "city_slug": u["city"],
            "country": "us",
            "has_properties": slug in srp["universities"],
            "aliases": (aliases.get(slug) or {}).get("aliases") or [],
            "latitude": (aliases.get(slug) or {}).get("lat"),
            "longitude": (aliases.get(slug) or {}).get("lng"),
        }
        if slug in srp["universities"]:
            rec["total_properties"] = srp["universities"][slug]["total"]
        uni_out[slug] = rec
    # flagship list with ordering for the finder "Popular Colleges" sections
    json.dump(uni_out, open(SRC / "universities.json", "w"), indent=1, sort_keys=True)
    print("universities:", len(uni_out))

    # ---------- properties ----------
    props = json.load(open(SCRAP / "properties_full.json"))
    img_manifest = json.load(open(SCRAP / "image_manifest.json"))
    prop_out = {}
    for slug, p in props.items():
        # local image paths in display order
        images = []
        for i, im in enumerate(p.get("images") or []):
            rel = f"properties/{slug}/{i+1:02d}.jpg"
            if rel in img_manifest:
                images.append({"path": f"/static/images/{rel}", "type": im.get("image_type") or "interior",
                               "caption": im.get("caption")})
        reviews = []
        for r in (p.get("reviews") or [])[:8]:
            reviews.append({
                "author": r.get("author_name") or "Anonymous",
                "rating": r.get("rating"),
                "content": (r.get("review_content") or "").strip(),
                "date": (r.get("review_date") or "")[:10],
                "network": r.get("network") or "Google",
            })
        rec = {
            "id": p["id"], "slug": slug, "name": p["name"],
            "city_slug": p.get("city_slug"), "state_slug": p.get("state_slug"),
            "address": p.get("address"),
            "latitude": p.get("latitude"), "longitude": p.get("longitude"),
            "min_price": norm_price(p.get("min_price")), "max_price": norm_price(p.get("max_price")),
            "property_type": p.get("property_type") or "Apartment",
            "rating": p.get("rating"), "user_rating_count": p.get("user_rating_count") or len(reviews),
            "wheelchair_accessible": bool(p.get("wheelchair_accessible")),
            "contact_email": p.get("contact_email"), "phone_number": p.get("phone_number"),
            "website": p.get("website"), "google_maps_url": p.get("google_maps_url"),
            "property_summary": p.get("property_summary"),
            "reviews_summary": p.get("reviews_summary"),
            "room_types": p.get("room_types") or [],
            "room_details": p.get("room_details") or {},
            "amenities": [a.get("name") for a in (p.get("property_amenities") or []) if a.get("name")],
            "vibes": [v.get("slug") for v in (p.get("vibes") or [])],
            "neighbourhood_tags": [t.get("slug") for t in (p.get("neighbourhood_tags") or [])],
            "office_hours": p.get("office_hours") if isinstance(p.get("office_hours"), list) else [],
            "is_featured": bool(p.get("is_featured")),
            "hide_contact": bool(p.get("hide_contact")),
            "images": images, "reviews": reviews,
            "universities": p.get("universities") or [],
            "university": p.get("university"), "university_slug": p.get("university_slug"),
        }
        prop_out[slug] = rec
    json.dump(prop_out, open(SRC / "properties.json", "w"), indent=1, sort_keys=True)
    print("properties:", len(prop_out), "| with images:", sum(1 for p in prop_out.values() if p["images"]))

    # ---------- cities ----------
    city_gql = json.load(open(SCRAP / "city_graphql.json"))
    cities_content = json.load(open(SCRAP / "cities_content.json"))
    city_slugs = sorted({p["city_slug"] for p in prop_out.values() if p["city_slug"]})
    city_out = {}
    for cs in city_slugs:
        state = next((p["state_slug"] for p in prop_out.values() if p["city_slug"] == cs), None)
        gql = city_gql.get(cs) or {}
        content = cities_content.get(cs) or {}
        hero_rel = f"cities/{cs}-hero.jpg"
        hero = f"/static/images/{hero_rel}" if hero_rel in img_manifest else None
        if hero is None:
            hero = next((p["images"][0]["path"] for p in prop_out.values()
                         if p["city_slug"] == cs and p["images"]), None)
        rec = {
            "slug": cs, "state": state, "name": CITY_NAMES.get(cs, cs.replace("-", " ").title()),
            "headline": (gql.get("headline") or "").strip() or None,
            "summary": re.sub(r"</?p>", "", (gql.get("summary") or "").strip()) or None,
            "hero": hero,
            "meta_description": (gql.get("metaDescription") or "").strip() or None,
            "editorial_lines": content.get("editorial_lines") or [],
            "universities_listed": content.get("universities_listed") or [],
            "source_style": content.get("_style"),
            "source_url": content.get("_source_url"),
        }
        city_out[cs] = rec
    # austin carries the rich new-style content
    a = cities_content.get("austin") or {}
    city_out["austin"]["austin_lines"] = a.get("lines") or []
    json.dump(city_out, open(SRC / "cities.json", "w"), indent=1, sort_keys=True)
    print("cities:", len(city_out))

    # ---------- jobs ----------
    jobs = json.load(open(SCRAP / "jobs.json"))
    job_out = {}
    for cs, j in jobs.items():
        listings = []
        for l in j["listings"]:
            listings.append({
                "id": l["id"], "title": l["title"], "company": l.get("company"),
                "location": l.get("location"), "type": l.get("type"),
                "raw_type": l.get("raw_type"), "url": l.get("url"),
                "posted_at": (l.get("posted_at") or "")[:10],
            })
        job_out[cs] = {"source_url": j["_source_url"], "listings": listings}
    json.dump(job_out, open(SRC / "jobs.json", "w"), indent=1, sort_keys=True)
    print("job cities:", len(job_out), "jobs:", sum(len(v["listings"]) for v in job_out.values()))

    # ---------- home ----------
    hot = json.load(open(SCRAP / "hot_cities.json"))
    home = {
        "hot_cities": [
            {"name": e["node"]["name"], "slug": e["node"]["slug"], "properties": e["node"]["properties"],
             "country": e["node"]["country"]["slug"],
             "image": f"/static/images/home/hot-{e['node']['slug']}.jpg"}
            for e in hot["data"]["cities"]["edges"]
        ],
        "state_ctas": [
            {"state": "tx", "name": "Texas", "cta": "Search Texas Now", "href": "/us/tx/u",
             "image": "/static/images/home/state-texas.png"},
            {"state": "fl", "name": "Florida", "cta": "Search Florida Now", "href": "/us/fl/u",
             "image": "/static/images/home/state-florida.png"},
            {"state": "ga", "name": "Georgia", "cta": "Search Georgia Now", "href": "/us/ga/u",
             "image": "/static/images/home/state-georgia.png"},
            {"state": "oh", "name": "Ohio", "cta": "Search Ohio Now", "href": "/us/oh/u",
             "image": "/static/images/home/state-ohio.png"},
        ],
    }
    json.dump(home, open(SRC / "home.json", "w"), indent=1)
    print("home config written")

if __name__ == "__main__":
    main()
