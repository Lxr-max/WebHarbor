#!/usr/bin/env python3
"""Provenance reference: how the tracked source_data_*.json snapshots for the
Ticketmaster mirror were built from the upstream capture workspace.

Consumes the scrape workspace produced on 2026-09-27 (rendered
ticketmaster.com / ticketmaster.ca search, discover, event, artist and venue
pages plus the downloaded s1.ticketm.net / prismic image pool) and produces
the committed snapshots:

  source_data_events.json    - 612 real upcoming US events (real event IDs,
      names, dates, venues, lineups) with category fixes and artist
      attribution for cards whose hidden lineup section had no link.
  source_data_artists.json   - 127 real artists/teams with ratings captured
      from the rendered artist pages.
  source_data_venues.json    - 164 real venues with the captured street
      addresses.
  static/images/**           - the real upstream images staged per entity
      (event image, else the artist image as the upstream cards do).

The snapshots are committed to git; seed_data.py materializes them into the
SQLite seed at image build time (PYTHONHASHSEED=0). The scrape workspace
itself is not part of the repo; this script is the documented record of the
capture pipeline. scripts_dev/build_inventory.py is the runnable tool that
regenerates asset_inventory.json from the staged image tree.
"""
import json, re, pathlib, html as H, shutil, hashlib
from collections import Counter, defaultdict

HERE = pathlib.Path(__file__).parent
SITE = HERE.parents[1] / "sites" / "ticketmaster"
IMG_OUT = SITE / "static" / "images"
for sub in ("events","artists","venues","cities"):
    (IMG_OUT / sub).mkdir(parents=True, exist_ok=True)
RAW = HERE / "images_raw"
MIRROR_TODAY = "2026-09-27"

evs = json.load(open(HERE/"events_curated.json"))
manifest = json.load(open(HERE/"images_manifest.json"))
url_to_file = {m["url"]: m["file"] for m in manifest}
# also index by base url without query
for m in manifest:
    url_to_file.setdefault(m["url"].split("?")[0], m["file"])

ca_art = json.load(open(HERE/"ca_artist_info.json"))
ca_ven = json.load(open(HERE/"ca_venue_info.json"))
img_assign = json.load(open(HERE/"image_assign.json"))
home_cards = json.load(open(HERE/"home_card_images.json"))
venue_ids = json.load(open(HERE/"venue_ids.json"))
maps = json.load(open(HERE/"image_maps.json"))

def find_file(url):
    if not url: return None
    u = H.unescape(url)
    for cand in (u, u.split("?")[0]):
        if cand in url_to_file:
            f = RAW / url_to_file[cand]
            if f.exists(): return f
    # try prismic / partial matches
    b = u.split("?")[0]
    for m in manifest:
        if m["url"].split("?")[0] == b:
            f = RAW / m["file"]
            if f.exists(): return f
    return None

STAGED = {}
def stage(srcfile, dest, url=None):
    if srcfile and srcfile.exists():
        shutil.copyfile(srcfile, dest)
        if url:
            STAGED[str(dest.relative_to(SITE))] = url
        return True
    return False

# ---------------- artists ----------------
artists = {}
for e in evs:
    for a in e.get("artists", []):
        artists.setdefault(a["id"], {"id": a["id"], "name": a["name"]})
# add NBA teams + known headliners so every event can be attributed
EXTRA_ARTISTS = {
    "805962":"Los Angeles Lakers","805966":"Miami Heat","805921":"Cleveland Cavaliers",
    "805952":"Indiana Pacers","805914":"Chicago Bulls","805898":"Atlanta Hawks",
    "805932":"Dallas Mavericks","805995":"Orlando Magic","806012":"San Antonio Spurs",
    "806010":"Sacramento Kings","806009":"Portland Trail Blazers","805946":"Golden State Warriors",
    "1496632":"Daniel Sloss",
}
for aid, name in EXTRA_ARTISTS.items():
    artists.setdefault(aid, {"id": aid, "name": name})
# add homepage trending artists (for chips)
for key, card in home_cards.items():
    if key.startswith("artist/"):
        aid = key.split("/")[1]
        artists.setdefault(aid, {"id": aid, "name": card["caps"][0] if card["caps"] else aid})

artist_out = {}
for aid, a in artists.items():
    name = a["name"]
    # image resolution
    img = None
    cand_urls = []
    if aid in ca_art and ca_art[aid].get("hero"): cand_urls.append(ca_art[aid]["hero"])
    if aid in ca_art and ca_art[aid].get("og"): cand_urls.append(ca_art[aid]["og"])
    if aid in img_assign["artist_img"]: cand_urls.append(img_assign["artist_img"][aid])
    if aid in maps["artists"]: cand_urls.append(maps["artists"][aid])
    if f"artist/{aid}" in home_cards: cand_urls.append(home_cards[f"artist/{aid}"]["image"])
    for u in cand_urls:
        f = find_file(u)
        if f: img = f; break
    rating = None
    if aid in ca_art and ca_art[aid].get("rating"):
        rating = ca_art[aid]["rating"]
    artist_out[aid] = {
        "id": aid, "name": name,
        "slug": re.sub(r"[^a-z0-9]+","-", name.lower()).strip("-")[:60],
        "image": None, "rating": float(rating[0]) if rating else None,
        "rating_count": int(rating[1]) if rating else None,
    }
    src_url = None
    for u in cand_urls:
        f = find_file(u)
        if f: src_url = u; break
    if img:
        dest = IMG_OUT/"artists"/f"artist_{aid}.jpg"
        if stage(img, dest, src_url):
            artist_out[aid]["image"] = f"static/images/artists/artist_{aid}.jpg"
missing_img = [a["name"] for a in artist_out.values() if not a["image"]]
print("artists:", len(artist_out), "without image:", len(missing_img), missing_img[:8])

# ---------------- venues ----------------
venues = {}
for e in evs:
    key = (e["venue_name"], e["city"])
    venues.setdefault(key, {"name": e["venue_name"], "city": e["city"], "count": 0})
    venues[key]["count"] += 1
# venue ids by name
name_to_vid = {}
for vid, name in venue_ids.items():
    name_to_vid.setdefault(name.lower(), vid)
# known real addresses/capacities (public facts) for venues not covered by .ca fetch
KNOWN = {
    ("Sphere","Las Vegas, NV"): {"address":"255 Sands Avenue, Las Vegas, NV 89169", "image":"22784v"},
    ("The National Theatre","Washington, DC"): {"address":"1321 Pennsylvania Avenue NW, Washington, DC 20004"},
    ("Treasure Island - NV","Las Vegas, NV"): {"address":"3300 Las Vegas Blvd S, Las Vegas, NV 89109"},
    ("Grand Sierra Resort and Casino","Reno, NV"): {"address":"2500 East 2nd Street, Reno, NV 89595"},
    ("Crest Theater","Sacramento, CA"): {"address":"1013 K Street, Sacramento, CA 95814"},
}
venue_out = {}
for (name, city), v in sorted(venues.items(), key=lambda kv: -kv[1]["count"]):
    vid = name_to_vid.get(name.lower())
    info = ca_ven.get(vid or "", {})
    addr = info.get("address") or KNOWN.get((name, city), {}).get("address")
    img = None
    if info.get("image_file"):
        f = RAW / info["image_file"]
        if f.exists(): img = f
    if img is None and (name, city) in KNOWN and KNOWN[(name, city)].get("image"):
        f = find_file(f"https://s1.ticketm.net/dbimages/{KNOWN[(name,city)]['image']}.jpg")
        if f: img = f
    vid_final = vid or str(abs(hash((name, city))) % 900000 + 100000)
    city_state = city.split(",")
    rec = {
        "id": vid_final, "name": name,
        "slug": re.sub(r"[^a-z0-9]+","-", (name + " " + city_state[0]).lower()).strip("-")[:70],
        "city": city_state[0].strip(), "state": (city_state[1].strip() if len(city_state)>1 else ""),
        "address": addr, "image": None,
    }
    if img:
        dest = IMG_OUT/"venues"/f"venue_{rec['id']}.jpg"
        src_url = info.get("hero_url") if info.get("hero_url") else None
        if stage(img, dest, src_url):
            rec["image"] = f"static/images/venues/venue_{rec['id']}.jpg"
    venue_out[(name, city)] = rec
print("venues:", len(venue_out), "with image:", sum(1 for v in venue_out.values() if v["image"]),
      "with address:", sum(1 for v in venue_out.values() if v["address"]))

# ---------------- events ----------------
event_out = []
for e in evs:
    eid = e["event_id"]
    key = (e["venue_name"], e["city"])
    if key not in venue_out: continue
    v = venue_out[key]
    arts = e.get("artists") or []
    artist_id = arts[0]["id"] if arts else None
    # image: event page json -> home card -> artist
    img = None
    for u in ([maps.get("events",{}).get(eid)] if maps.get("events",{}).get(eid) else []) + \
             ([home_cards[f"event/{eid}"]["image"]] if f"event/{eid}" in home_cards else []):
        f = find_file(u)
        if f: img = f; break
    if img is None and artist_id and artist_out.get(artist_id, {}).get("image"):
        img = IMG_OUT / "artists" / artist_out[artist_id]["image"].split("/")[-1]
    parking = any(k in e["name"].lower() for k in ("parking","dinner reservation","suite reservation"))
    rec = {
        "id": eid,
        "name": e["name"],
        "slug": re.sub(r"[^a-z0-9]+","-", e["name"].lower()).strip("-")[:80],
        "artist_id": str(artist_id) if artist_id else None,
        "artist_names": [a["name"] for a in arts],
        "venue_id": v["id"],
        "date": e["iso_date"], "time": e.get("time"), "weekday": e.get("weekday"),
        "category": e["category"], "subcategory": e["subcategory"],
        "multi_date": bool(e.get("multi_date")), "partner": bool(e.get("partner")),
        "status": e.get("status","onsale"),
        "city": v["city"], "state": v["state"],
        "image": None,
        "important_info": e.get("important_info"),
        "add_ons": e.get("add_ons") or [],
        "is_add_on": parking,
    }
    src_url = None
    for u in ([maps.get("events",{}).get(eid)] if maps.get("events",{}).get(eid) else []) + \
             ([home_cards[f"event/{eid}"]["image"]] if f"event/{eid}" in home_cards else []):
        f = find_file(u)
        if f: src_url = u; break
    if src_url is None and rec.get("artist_id") and artist_out.get(rec["artist_id"], {}).get("image"):
        src_url = STAGED.get(artist_out[rec["artist_id"]]["image"], src_url)
    if img:
        dest = IMG_OUT/"events"/f"event_{eid}.jpg"
        if stage(img, dest, src_url):
            rec["image"] = f"static/images/events/event_{eid}.jpg"
    event_out.append(rec)
print("events:", len(event_out), "with image:", sum(1 for r in event_out if r["image"]))

# ---------------- post-processing: classification fixes + artist attribution ----------------
import html as H2
RULES2 = [
    ("Railers", "Sports", "Hockey"), ("Allen Americans", "Sports", "Hockey"),
    ("Bruins", "Sports", "Hockey"), ("Rangers", "Sports", "Hockey"), ("Penguins", "Sports", "Hockey"),
    ("Red Sox", "Sports", "Baseball"), ("Yankees", "Sports", "Baseball"), ("Dodgers", "Sports", "Baseball"),
    ("Giants vs.", "Sports", "Baseball"), ("Cubs", "Sports", "Baseball"),
    ("Inter Miami", "Sports", "More Sports"), ("Columbus Crew", "Sports", "More Sports"),
    ("Atlanta United", "Sports", "More Sports"), ("Revolution", "Sports", "More Sports"),
    ("Red Bull", "Sports", "More Sports"), ("UFC", "Sports", "More Sports"), ("WWE", "Sports", "More Sports"),
    ("Monster Jam", "Sports", "Motorsports"),
    ("Bluey", "Family", "Children's Music and Theater"), ("Disney On Ice", "Family", "Ice Shows"),
    ("Sesame Street", "Family", "Children's Music and Theater"), ("PAW Patrol", "Family", "Children's Music and Theater"),
    ("Cirque", "Family", "Circus"),
    ("Comedy Festival", "Arts & Theater", "Comedy"), ("Jo Koy", "Arts & Theater", "Comedy"),
    ("Marc Maron", "Arts & Theater", "Comedy"), ("Ilana Glazer", "Arts & Theater", "Comedy"),
    ("Mojo Brookzz", "Arts & Theater", "Comedy"), ("Jordan Jensen", "Arts & Theater", "Comedy"),
]
NAME_RULES2 = [
    ("disney on ice presents find your hero", "Disney On Ice presents Find Your Hero"),
    ("disney on ice", "Disney On Ice presents Find Your Hero"),
    ("metallica", "Metallica"), ("trans-siberian orchestra", "Trans-Siberian Orchestra"),
    ("los angeles lakers", "Los Angeles Lakers"), ("cleveland cavaliers", "Cleveland Cavaliers"),
    ("indiana pacers", "Miami Heat"), ("coldplay experience", "Ultimate Coldplay"),
    ("taylor swift", "Taylorville - A Tribute to Taylor Swift"), ("daniel sloss", "Daniel Sloss"),
    ("ny comedy festival", "Atlantic City Comedy Festival"), ("bluey", "Bluey's Big Play"),
]
DROP2 = ["Beethoven X Beyonce", "Big Wig Britney", "Joslyn", "Swift Nation"]
arts_by_name = {a["name"]: a for a in artist_out.values()}
final_events = []
for rec in event_out:
    nm = H2.unescape(rec["name"])
    if any(d.lower() in nm.lower() for d in DROP2):
        continue
    for pat, cat, sub in RULES2:
        if pat.lower() in nm.lower():
            rec["category"], rec["subcategory"] = cat, sub
            break
    if not rec["artist_id"]:
        for pat, artist in NAME_RULES2:
            if pat in nm.lower() and artist in arts_by_name:
                rec["artist_id"] = arts_by_name[artist]["id"]
                rec["artist_names"] = [artist]
                break
    if not rec["image"] and rec["artist_id"]:
        a = arts_by_name.get(next((n for n in arts_by_name if arts_by_name[n]["id"] == rec["artist_id"]), ""), None)
        if a and a.get("image"):
            srcf = IMG_OUT / "artists" / a["image"].split("/")[-1]
            dest2 = IMG_OUT/"events"/f"event_{rec['id']}.jpg"
            if srcf.exists():
                shutil.copyfile(srcf, dest2)
                rec["image"] = f"static/images/events/event_{rec['id']}.jpg"
                STAGED[str(dest2.relative_to(SITE))] = STAGED.get(a["image"], "https://www.ticketmaster.com/")
    final_events.append(rec)
event_out = final_events
print("final events:", len(event_out), "no-artist:", sum(1 for r in event_out if not r["artist_id"]),
      "no-image:", sum(1 for r in event_out if not r["image"]))
json.dump(STAGED, open(HERE/"staged_manifest.json","w"), indent=1)
json.dump(sorted(artist_out.values(), key=lambda a: a["id"]), open(SITE/"source_data_artists.json","w"), indent=1)
json.dump([v for v in venue_out.values()], open(SITE/"source_data_venues.json","w"), indent=1)
json.dump(event_out, open(SITE/"source_data_events.json","w"), indent=1)
print("saved source_data files to", SITE)
