#!/usr/bin/env python3
"""Build the tracked source_data_*.json snapshots from scraped_data captures.

Run from sites/trip_com/:  python3 scripts_dev/build_source_data.py

Inputs (scraped_data/, gitignored):
  hotels_<city>.json          — results-page cards (all hotels)
  hotel_details_<city>.json   — per-hotel detail snapshots (rooms, amenities…)
  seo_<city>.json             — SEO landing cards (stars, addresses)
  flights_<route>.json         — round-trip results (cards + strip + facets)
  flights_ow_<route>.json      — one-way results
  attractions_<city>.json      — attraction listing cards
  attraction_details_<city>.json — attraction detail snapshots

Outputs (tracked in git):
  source_data_hotels.json, source_data_flights.json,
  source_data_attractions.json, source_data_content.json
"""
import json
import pathlib
import re

BASE = pathlib.Path(__file__).resolve().parent.parent
SCRAPE = BASE / "scraped_data"

CITY_IDS = {
    "las_vegas": 26282, "new_york": 633, "los_angeles": 347,
    "orlando": 1187, "san_francisco": 313, "chicago": 549,
    "miami": 25773, "new_orleans": 1186,
    "hong_kong": 58, "beijing": 1, "shanghai": 2,
}
HOTEL_CITIES = {"las_vegas", "new_york", "los_angeles", "orlando",
                "san_francisco", "chicago", "miami", "new_orleans"}
CITY_META = {
    "las_vegas": ("Las Vegas", "NV", "Casino resorts on the Strip and beyond"),
    "new_york": ("New York", "NY", "Manhattan classics and skyline views"),
    "los_angeles": ("Los Angeles", "CA", "Hollywood, beaches and LAX stays"),
    "orlando": ("Orlando", "FL", "Theme-park capital of the world"),
    "san_francisco": ("San Francisco", "CA", "Bay views and Golden Gate trips"),
    "chicago": ("Chicago", "IL", "Lakefront architecture and deep-dish"),
    "miami": ("Miami", "FL", "South Beach, Art Deco and Wynwood walls"),
    "new_orleans": ("New Orleans", "LA", "French Quarter jazz and creole food"),
    # attraction-only cities (real upstream hotel cityIds from the site footer)
    "hong_kong": ("Hong Kong", "", "Victoria Harbour and dim sum classics"),
    "beijing": ("Beijing", "", "The Great Wall and the Forbidden City"),
    "shanghai": ("Shanghai", "", "The Bund and neon-lit Nanjing Road"),
}

ROUTES = {
    "sfo_nyc": ("SFO", "JFK", "San Francisco", "New York"),
    "lax_nyc": ("LAX", "JFK", "Los Angeles", "New York"),
    "ord_mia": ("ORD", "MIA", "Chicago", "Miami"),
    "las_lax": ("LAS", "LAX", "Las Vegas", "Los Angeles"),
    "mia_nyc": ("MIA", "LGA", "Miami", "New York"),
    "sfo_las": ("SFO", "LAS", "San Francisco", "Las Vegas"),
}

FLIGHT_NO_PREFIX = {
    "Delta Air Lines": "DL", "United Airlines": "UA", "American Airlines": "AA",
    "Jetblue Airways": "B6", "Frontier Airlines": "F9", "Alaska Airlines": "AS",
    "Southwest Airlines": "WN", "Spirit Airlines": "NK", "Sun Country Airlines": "SY",
}


def load(name):
    p = SCRAPE / name
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


# ------------------------------------------------------------------ hotels --

def parse_card(card):
    """Parse one results-page hotel card into structured fields."""
    text = card["text"]
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    out = {"id": int(card["id"]), "name": card["name"], "img_url": card.get("img", "")}
    m = re.search(r"(\d+\.\d+)/10\n", text + "\n")
    out["rating"] = float(m.group(1)) if m else 0.0
    m = re.search(r"(\d[\d,]*) reviews", text)
    out["reviews_count"] = int(m.group(1).replace(",", "")) if m else 0
    labels = {"Exceptional": 9, "Excellent": 8.5, "Very good": 8, "Good": 7, "Pleasant": 6}
    for lab in labels:
        m = re.search(lab + r"\s*(\d[\d,]*) reviews", text)
        if m:
            out["reviews_count"] = int(m.group(1).replace(",", ""))
            break
    # tags in quotes
    out["tags"] = re.findall(r'"([^"]{3,40})"', text)[:4]
    # district + near: single line like 'Las Vegas StripNear The Venetian ExpoShow on Map'
    area_line = ""
    for line in text.split("\n"):
        if "Show on Map" in line:
            area_line = line.replace("Show on Map", "").strip()
            break
    if area_line:
        idx = area_line.find("Near ")
        if idx > 0:
            out["district"] = area_line[:idx].strip()
            out["near"] = area_line[idx + 5:].strip()
        elif idx == 0:
            out["district"] = ""
            out["near"] = area_line[5:].strip()
        else:
            out["district"] = area_line
            out["near"] = ""
    else:
        out["district"], out["near"] = "", ""
    # room hint (line before Free Cancellation / price)
    m = re.search(r"\n([A-Z][^\n$]{4,60})\n(?:/?\n)?(?:Free Cancellation|Earn)", text)
    out["room_hint"] = (m.group(1).strip() if m else "")
    m = re.search(r"\n\$(\d[\d,]*)\n", text)
    out["price"] = float(m.group(1).replace(",", "")) if m else 0.0
    m = re.search(r"Total \(incl\. taxes & fees\): \$([\d,]+)", text)
    out["total"] = float(m.group(1).replace(",", "")) if m else 0.0
    m = re.search(r"Earn \$(\d+\.\d\d) in Trip Coins", text)
    out["coins"] = float(m.group(1)) if m else 0.0
    m = re.search(r"Last booked ([^\n]+)", text)
    out["last_booked"] = m.group(1) if m else ""
    return out


def parse_detail(detail):
    """Parse one hotel detail snapshot: address, stars, times, amenities, rooms, reviews."""
    bt = detail["bodyText"]
    out = {}
    m = re.search(r"\n([^\n]+Show on map)", bt)
    out["address"] = m.group(1).replace("Show on map", "").strip() if m else ""
    out["stars"] = detail.get("stars", 0)
    m = re.search(r"Check-in: (\d\d:\d\d)[–-](\d\d:\d\d)", bt)
    out["checkin_from"] = m.group(1) if m else "15:00"
    m = re.search(r"Check-out: Before (\d\d:\d\d)", bt)
    out["checkout_by"] = m.group(1) if m else "11:00"
    # impression tags near top: "French-style decor / Scenic nightscapes / ... / +6 more"
    m = re.search(r"Select Rooms\n((?:[^\n]+\n){1,8}?)\+? ?\d+ more", bt)
    if m:
        out["tags"] = [t for t in m.group(1).split("\n") if t.strip() and "Rooms" not in t][:8]
    # amenities: between the standalone "Amenities\n" after View on map and "All amenities"
    m = re.search(r"View on map\nAmenities\n(.*?)\nAll amenities", bt, re.S)
    if m:
        out["amenities"] = [a.strip() for a in m.group(1).split("\n") if a.strip()][:20]
    # surroundings
    m = re.search(r"Surroundings\n(.*?)\nView on map", bt, re.S)
    if m:
        sur = []
        for line in m.group(1).split("\n"):
            line = line.strip()
            mm = re.match(r"(Attraction|Recreation|Restaurant|Shopping|Transport(?:ation)?): (.+) \(([\d.]+ (?:ft|mile|mi|km))\)", line)
            if mm:
                sur.append({"kind": mm.group(1), "name": mm.group(2), "dist": mm.group(3)})
        out["surroundings"] = sur[:8]
    # top quotes (before "All N reviews")
    m = re.search(r"All \d[\d,]* reviews\n((?:[^\n]{20,200}\n){1,3})", bt)
    if m:
        out["quotes"] = [q.strip() for q in m.group(1).split("\n") if q.strip()][:3]
    # guest reviews from "What guests say"
    reviews = []
    i2 = bt.find("What guests say")
    if i2 >= 0:
        seg = bt[i2:i2 + 20000]
        for rm in re.finditer(
                r"Guest User\n(\d+\.\d+)\n([A-Za-z ,]{2,26})\n([^\n]{2,34})\n([^\n]{20,600})\n?(?:Original TextTranslation provided by AI\n)?Posted ([A-Za-z]+ \d{1,2}, \d{4})?", seg):
            reviews.append({"rating": float(rm.group(1)), "country": rm.group(2).strip(),
                            "traveller": rm.group(3).strip(), "text": rm.group(4).strip(),
                            "review_date": (rm.group(5) or "Sep 2026")})
    out["reviews"] = reviews[:6]
    out["photos"] = detail.get("photos", [])[:10]
    # rooms
    out["rooms"] = parse_rooms(bt)
    return out


def parse_rooms(bt):
    """Parse the 'Choose your room' section into rate variants."""
    i = bt.find("Choose your room")
    if i < 0:
        return []
    seg = bt[i:]
    # stop at the next big section if present
    for stop in ["Guest reviews", "Services & Amenities", "Policies"]:
        j = seg.find("\n" + stop)
        if j > 0:
            seg = seg[:j]
    lines = [l.strip() for l in seg.split("\n")]
    rooms = []
    current = None
    n = 0
    while n < len(lines):
        line = lines[n]
        # new room header: a bare capacity digit followed by a name line
        if re.fullmatch(r"\d{1,2}", line) and n + 1 < len(lines) and \
                lines[n + 1] and not lines[n + 1].startswith("$") and len(lines[n + 1]) < 90:
            current = {"capacity": int(line), "name": lines[n + 1], "specs": [],
                       "rates": []}
            rooms.append(current)
            n += 2
            continue
        if current is not None:
            if line == "Room Details":
                # specs are done; parse rate variants below
                n += 1
                rate = {}
                while n < len(lines) and not (
                        re.fullmatch(r"\d{1,2}", lines[n]) and n + 1 < len(lines)
                        and lines[n + 1] and not lines[n + 1].startswith("$")):
                    ln = lines[n]
                    if ln == "Reserve":
                        if rate.get("price"):
                            current["rates"].append(rate)
                        rate = {}
                    elif re.fullmatch(r"\$[\d,]+", ln):
                        # first bare $-line is the nightly price; later ones are
                        # struck-through pre-discount prices, so keep the first
                        if "price" not in rate:
                            rate["price"] = float(ln.replace("$", "").replace(",", ""))
                    elif ln.startswith("Total (incl"):
                        mm = re.search(r"\$([\d,.]+)", ln)
                        if mm:
                            rate["total"] = float(mm.group(1).replace(",", ""))
                    elif re.fullmatch(r"\d+ adults?", ln):
                        mm = re.search(r"\d+", ln)
                        rate["capacity"] = int(mm.group(0))
                    elif ln.startswith("Includes ") and "breakfast" in ln.lower():
                        rate["breakfast"] = True
                    elif ln.startswith("Free Cancellation before"):
                        rate["free_cancel"] = True
                    elif re.match(r"Lowest price|Breakfast and free|Free cancellation$|Member rate|Non-refundable", ln):
                        rate["label"] = ln
                    n += 1
                continue
            elif line and not line.startswith("Choose your room"):
                if len(line) < 80 and not re.match(r"^Free (Cancellation|Wi-Fi)", line) \
                        and line not in ("Non-smoking", "Has window(s)", "Prepay online",
                                         "Instant confirmation", "Free cancellation",
                                         "Prepay Online", "Breakfast included"):
                    current["specs"].append(line)
        n += 1
    # flatten: one RoomRate per rate variant
    flat = []
    for room in rooms:
        bed = next((s for s in room["specs"] if "bed" in s.lower() or "bedroom" in s.lower()), "")
        view = next((s for s in room["specs"] if "view" in s.lower() or "Suite" in s), "")
        size = 0
        for s in room["specs"]:
            mm = re.search(r"(\d[\d,–-]*)\s*ft", s)
            if mm:
                size = int(re.sub(r"[^\d]", "", mm.group(1).split("–")[0]))
                break
        for k, rate in enumerate(room["rates"]):
            name = room["name"]
            if k > 0 and rate.get("label"):
                name = f"{room['name']} ({rate['label']})"
            price = rate.get("price", 0.0)
            total = rate.get("total") or price
            # guard: a member-deal sale price can sit below the tax-inclusive
            # total of the undiscounted rate; keep the captured pair as-is but
            # never let the parse produce total < price (that would be a
            # crossed-out-original artifact)
            if total < price:
                total = price
            flat.append({
                "name": name,
                "bed": bed,
                "view": view if len(view) < 40 else "",
                "size_sqft": size,
                "capacity": rate.get("capacity") or room["capacity"] or 2,
                "price": price,
                "total": total,
                "breakfast": bool(rate.get("breakfast")),
                "free_cancel": bool(rate.get("free_cancel", True)),
            })
    return flat


def build_hotels():
    hotels = []
    cities = []
    for slug, cid in CITY_IDS.items():
        name, state, blurb = CITY_META[slug]
        if slug not in HOTEL_CITIES:
            # attraction-only city: no hotel cards to harvest
            cities.append({"id": cid, "name": name, "slug": slug, "state": state,
                           "blurb": blurb})
            continue
        cards = load(f"hotels_{slug}.json") or []
        details = load(f"hotel_details_{slug}.json") or {}
        seo = load(f"seo_{slug}.json") or []
        seo_by_name = {s["name"]: s for s in seo}
        for card in cards:
            h = parse_card(card)
            h["_city_id"] = cid
            h["_city_slug"] = slug
            d = details.get(card["id"])
            if d:
                parsed = parse_detail(d)
                h.update({k: v for k, v in parsed.items() if v or k == "stars"})
                h["bookable"] = bool(parsed["rooms"])
            else:
                s = seo_by_name.get(h["name"])
                if s:
                    h["stars"] = s.get("stars") or 0
                    if s.get("address"):
                        h["address"] = s["address"]
                    if s.get("quote"):
                        h["impression"] = s["quote"]
            hotels.append(h)
        cities.append({"id": cid, "name": name, "slug": slug, "state": state,
                       "blurb": blurb})
    return cities, hotels


# ------------------------------------------------------------------ flights --

def parse_flight_card(text):
    """Parse one flight card's innerText into a flight record."""
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    out = {}
    # times: first two lines matching h:mm (AM|PM)
    times = [l for l in lines if re.fullmatch(r"\d{1,2}:\d{2}\s*(AM|PM)?", l)]
    aps = [l for l in lines if re.fullmatch(r"[A-Z]{3}( T\d\w?)?", l)]
    if len(times) >= 2:
        out["dep_time"] = times[0]
        out["arr_time"] = times[1]
    if len(aps) >= 2:
        out["dep_ap"], out["arr_ap"] = aps[0], aps[1]
        out["dep_term"] = ""
        out["arr_term"] = ""
    m = re.search(r"\+1", text)
    out["plus1"] = bool(m)
    m = re.search(r"(\d+)h (\d+)m", text)
    if m:
        out["duration_min"] = int(m.group(1)) * 60 + int(m.group(2))
    elif re.search(r"\b3h\b", text):
        out["duration_min"] = 180
    m = re.search(r"Nonstop", text)
    if m:
        out["stops"] = 0
        out["stopover"] = ""
    else:
        m = re.search(r"(\d+) stop\n?(?:\d+h \d+m in ([A-Za-z .]+))?", text)
        if m:
            out["stops"] = int(m.group(1))
            out["stopover"] = (m.group(2) or "").strip()
        else:
            out["stops"] = 0
            out["stopover"] = ""
    m = re.search(r"\$(\d[\d,]*)", text)
    out["price"] = float(m.group(1).replace(",", "")) if m else 0.0
    # terminals: the line right after the airport-code line
    for n, ln in enumerate(lines):
        if re.fullmatch(r"[A-Z]{3}", ln) and n + 1 < len(lines) \
                and re.match(r"^T\d", lines[n + 1]):
            if out.get("dep_ap") and not out.get("dep_term"):
                out["dep_term"] = lines[n + 1].strip()
            elif out.get("arr_ap") and not out.get("arr_term"):
                out["arr_term"] = lines[n + 1].strip()
    m = re.search(r"(Delta Air Lines|United Airlines|American Airlines|Jetblue Airways|"
                   r"Frontier Airlines|Alaska Airlines|Southwest Airlines|Spirit Airlines|"
                   r"Sun Country Airlines)", text)
    out["airline"] = m.group(1) if m else ""
    m = re.search(r"Carry-on baggage included", text)
    out["baggage"] = "Carry-on baggage included" if m else "Personal item included"
    return out


def norm_time(t):
    """Normalize '10:15 PM' -> '22:15'; keep '6:00 AM' -> '06:00'."""
    if not t:
        return ""
    m = re.match(r"(\d{1,2}):(\d{2})\s*(AM|PM)?", t.strip())
    if not m:
        return t
    h, mi, ap = int(m.group(1)), m.group(2), m.group(3)
    if ap == "PM" and h != 12:
        h += 12
    elif ap == "AM" and h == 12:
        h = 0
    return f"{h:02d}:{mi}"


def build_flights():
    airports = {}
    routes = []
    flights = []
    fid = 1
    for key, (oap, dap, ocity, dcity) in ROUTES.items():
        ow = load(f"flights_ow_{key}.json")
        if not ow:
            continue
        route_id = len(routes) + 1
        routes.append({"id": route_id, "origin_code": oap, "dest_code": dap,
                       "origin_city": ocity, "dest_city": dcity})
        airports.setdefault(oap, oap)
        airports.setdefault(dap, dap)
        seen = set()
        for card in ow["cards"]:
            f = parse_flight_card(card)
            f["dep_ap"], f["arr_ap"] = oap, dap
            if not f.get("airline") or not f.get("price") or not f.get("dep_time"):
                continue
            sig = (f["dep_time"], f["arr_time"], f["airline"], f["price"])
            if sig in seen:
                continue
            seen.add(sig)
            f["dep_time"] = norm_time(f["dep_time"])
            f["arr_time"] = norm_time(f["arr_time"])
            f["id"] = fid
            f["route_id"] = route_id
            f["leg"] = "out"
            f["flight_no"] = f"{FLIGHT_NO_PREFIX.get(f['airline'], 'XX')}{100 + len(seen)}"
            flights.append(f)
            fid += 1
        # return legs: real one-way fares captured from the reverse-route
        # one-way search (the ShowFareNext return cards show RT totals, so the
        # reverse OW search is the honest source for return-leg fares)
        rev = load(f"flights_ow_rev_{key}.json")
        seen_ret = set()
        for card in (rev["cards"] if rev else []):
            f = parse_flight_card(card)
            f["dep_ap"], f["arr_ap"] = dap, oap
            if not f.get("airline") or not f.get("price") or not f.get("dep_time"):
                continue
            sig = (f["dep_time"], f["arr_time"], f["airline"], f["price"])
            if sig in seen_ret:
                continue
            seen_ret.add(sig)
            f["dep_time"] = norm_time(f["dep_time"])
            f["arr_time"] = norm_time(f["arr_time"])
            f["id"] = fid
            f["route_id"] = route_id
            f["leg"] = "ret"
            f["flight_no"] = f"{FLIGHT_NO_PREFIX.get(f['airline'], 'XX')}{200 + len(seen_ret)}"
            flights.append(f)
            fid += 1
    # airport names
    AP_NAMES = {
        "SFO": ("San Francisco International Airport", "San Francisco"),
        "JFK": ("John F. Kennedy International Airport", "New York"),
        "LAX": ("Los Angeles International Airport", "Los Angeles"),
        "ORD": ("O'Hare International Airport", "Chicago"),
        "MIA": ("Miami International Airport", "Miami"),
        "LAS": ("Harry Reid International Airport", "Las Vegas"),
        "LGA": ("LaGuardia Airport", "New York"),
    }
    airports = [{"code": c, "name": AP_NAMES[c][0], "city": AP_NAMES[c][1]}
                for c in sorted(airports)]
    return airports, routes, flights


# ------------------------------------------------------------- attractions --

def parse_attraction_card(card):
    text = card["text"]
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    out = {"id": int(card["id"]), "img_url": card.get("img", "")}
    # name: first meaningful line (skip icon glyphs / short tokens)
    name = ""
    for ln in lines:
        if len(ln) > 12 and not re.match(r"^[\u0000-\u001f\ud800-\udfff\U000f130d]+$", ln) \
                and ln not in ("English",) and not ln.startswith("Book now"):
            name = ln
            break
    out["name"] = name
    m = re.search(r"(\d+\.\d)\s*(?:\n)?\s*/\s*5", text)
    out["rating"] = float(m.group(1)) if m else 0.0
    m = re.search(r"[·]\xa0?(\d[\d,]*)\s*reviews?", text)
    if not m:
        m = re.search(r"\((\d[\d,]*)\)\s*reviews?", text)
    out["reviews_count"] = int(m.group(1).replace(",", "")) if m else 0
    # price: 'From\n$60.84\n$64.05' (sale then original) or 'From\n$64.00'
    m = re.search(r"From\n\$(\d[\d,.]*)\n(?:\$(\d[\d,.]*))?", text)
    if m:
        out["price_from"] = float(m.group(1).replace(",", ""))
        if m.group(2):
            out["price_original"] = float(m.group(2).replace(",", ""))
    else:
        m = re.search(r"\$(\d+[\d,.]*)", text)
        out["price_from"] = float(m.group(1).replace(",", "")) if m else 0.0
    m = re.search(r"(\d[\d,.]*)k?\s*booked", text)
    out["booked_count"] = 0
    m = re.search(r"Free cancellation", text)
    out["free_cancel"] = bool(m)
    return out


def build_attractions():
    attractions = []
    for slug in ["orlando", "hong_kong", "beijing", "shanghai"]:
        cards = load(f"attractions_{slug}.json") or []
        details = load(f"attraction_details_{slug}.json") or {}
        for card in cards:
            a = parse_attraction_card(card)
            if not a["name"] or not a.get("price_from"):
                continue
            a["city_slug"] = slug
            name_l = a["name"].lower()
            if "pass" in name_l:
                a["category"] = "City passes"
            elif "day tour" in name_l:
                a["category"] = "Day tours"
            elif "tour" in name_l:
                a["category"] = "Tours"
            elif "ticket" in name_l:
                a["category"] = "Tickets"
            else:
                a["category"] = "Activities"
            d = details.get(card["id"])
            if d:
                bt = d.get("bodyText", "")
                m = re.search(r"(\d+\.\d)\s*\n?/?\s*5\s*\n(?:[A-Za-z ]+)\n\((\d[\d,]*) reviews?\)", bt)
                if not m:
                    m = re.search(r"(\d+\.\d)\s*\n?/?\s*5\s*\n(?:[A-Za-z ]+)\n\((\d[\d,]*) review\)", bt)
                if m:
                    a["rating"] = float(m.group(1))
                    a["reviews_count"] = int(m.group(2).replace(",", ""))
                m = re.search(r"(\d[\d,.]*)k? booked", bt)
                if m:
                    v = m.group(1).replace(",", "")
                    a["booked_count"] = int(float(v) * (1000 if bt[m.end():m.end() + 2].startswith("k") else 1))
                # highlights block
                m = re.search(r"Highlights\n((?:[^\n]{10,140}\n){1,6})", bt)
                if m:
                    a["highlights"] = "|".join(
                        [h.strip() for h in m.group(1).split("\n") if h.strip()][:5])
                # description from the product-details prose
                m = re.search(r"Product details\n+(.{80,600}?)\n\n", bt, re.S)
                if m:
                    a["description"] = re.sub(r"\s+", " ", m.group(1)).strip()[:400]
                # validity
                m = re.search(r"Valid for ([^\n]{5,60})", bt)
                a["validity"] = ("Valid for " + m.group(1).strip()) if m else \
                    "Valid for 90 days from the booking date"
                a["photos"] = d.get("photos", [])[:6]
            if not a.get("description"):
                a["description"] = (f"Book {a['name']} with instant confirmation and free "
                                    "cancellation until 11:00 PM on your travel date.")
            attractions.append(a)
    return attractions


# ------------------------------------------------------------------ content --

def build_content():
    coupons = [
        {"code": "TRIPNEW20", "kind": "percent", "value": 20.0, "scope": "hotels",
         "min_spend": 100.0,
         "description": "New user promo code — 20% off your first hotel booking over $100."},
        {"code": "FLYTRIP10", "kind": "percent", "value": 10.0, "scope": "flights",
         "min_spend": 150.0,
         "description": "10% off round-trip and one-way flights over $150."},
        {"code": "ACTIVITY15", "kind": "percent", "value": 15.0, "scope": "attractions",
         "min_spend": 50.0,
         "description": "15% off attractions and tours over $50."},
        {"code": "SAVE25", "kind": "amount", "value": 25.0, "scope": "all",
         "min_spend": 200.0,
         "description": "$25 off any booking over $200."},
    ]
    guides = [
        {"slug": "las-vegas-first-timer", "title": "Las Vegas for first-timers: the Strip, downtown and beyond",
         "city": "Las Vegas",
         "body": "<p>Las Vegas runs on spectacle. First-time visitors should base themselves on the Strip — the 4.2-mile stretch of Tropicana to Sahara — where the mega-resorts sit side by side. Paris Las Vegas puts you mid-Strip with a direct view of the Bellagio fountains, while downtown's Fremont Street offers the vintage neon experience at a fraction of the price.</p><p>Expect resort fees of $30-45 per night at most Strip properties, plus a nightly accommodation tax. Booking with free cancellation gives you the flexibility to rebook if prices drop — Trip.com price-matches eligible claims.</p>"},
        {"slug": "orlando-theme-park-planning", "title": "Orlando theme-park planning: tickets, parks and pacing",
         "city": "Orlando",
         "body": "<p>Orlando is the theme-park capital of the world, and planning is everything. Universal Orlando Resort and Walt Disney World sit on opposite sides of Interstate 4, so pick a hotel near the park you'll visit most. City passes bundle multiple parks at a discount and skip-the-gate entry.</p><p>Most travellers need 2 days per major park. Buy tickets online in advance — gate prices are higher, and e-vouchers confirm instantly with free cancellation until 11 PM local time on your travel date.</p>"},
        {"slug": "nyc-weekend-midrange", "title": "A New York weekend without the midtown price tag",
         "city": "New York",
         "body": "<p>Manhattan hotel prices scare many travellers off, but the outer boroughs and Lower Manhattan offer real value. Hotels near the Financial Center put you steps from the Staten Island Ferry (free!) and a short subway hop from SoHo. Jersey City and Newark options trade a 15-minute PATH ride for 30-40% lower nightly rates.</p><p>Weekends are cheaper than weekdays in the Financial District — business travellers leave, and leisure rates drop. Book early for holiday weekends.</p>"},
        {"slug": "trip-coins-explained", "title": "Trip Coins explained: how rewards work on every booking",
         "city": "",
         "body": "<p>Trip Coins are Trip.com's rewards currency. You earn roughly 1 coin for every $1 spent on eligible bookings — about $1.27 in coins on a $127 stay. Coins post to your account after check-out and can be spent like cash on future bookings with no limits.</p><p>Sign in before booking to make sure coins post to your account. Guest bookings still earn coins if you register with the same email afterwards, but signing in first is the reliable path.</p>"},
        {"slug": "free-cancellation-guide", "title": "Free cancellation: what it covers and when the deadline hits",
         "city": "",
         "body": "<p>Free-cancellation rates let you cancel before a stated deadline — commonly 11:59 PM local hotel time, one to three days before check-in — for a full refund. After the deadline you'll be charged the first night or the full amount depending on the rate.</p><p>On Trip.com, filter hotel results by 'Free cancellation' to see only refundable rates, and check the exact deadline on the room card before you reserve.</p>"},
        {"slug": "sf-bay-area-basics", "title": "San Francisco basics: which neighborhood to book",
         "city": "San Francisco",
         "body": "<p>San Francisco is compact — 7 miles square — so location matters more than proximity to any single sight. SoMa suits convention-goers, Union Square is the classic tourist base, and the Marina offers bay walks. Airport hotels near SFO trade charm for easy early-departure logistics.</p><p>Muni and BART cover most trips; skip renting a car unless you're heading out of the city.</p>"},
    ]
    return {"coupons": coupons, "guides": guides}


def main():
    cities, hotels = build_hotels()
    airports, routes, flights = build_flights()
    attractions = build_attractions()
    content = build_content()
    # one package per attraction: the captured product at its real price
    for a in attractions:
        a["packages"] = [{"name": a["name"], "price": a["price_from"],
                          "validity": a.get("validity", "")}]
    (BASE / "source_data_cities.json").write_text(
        json.dumps(cities, indent=1, ensure_ascii=False), encoding="utf-8")
    (BASE / "source_data_hotels.json").write_text(
        json.dumps(hotels, indent=1, ensure_ascii=False), encoding="utf-8")
    (BASE / "source_data_flights.json").write_text(
        json.dumps({"airports": airports, "routes": routes, "flights": flights},
                   indent=1, ensure_ascii=False), encoding="utf-8")
    (BASE / "source_data_attractions.json").write_text(
        json.dumps(attractions, indent=1, ensure_ascii=False), encoding="utf-8")
    (BASE / "source_data_content.json").write_text(
        json.dumps(content, indent=1, ensure_ascii=False), encoding="utf-8")
    bookable = sum(1 for h in hotels if h.get("bookable"))
    print(f"hotels: {len(hotels)} ({bookable} bookable)")
    print(f"flights: {len(flights)} across {len(routes)} routes")
    print(f"attractions: {len(attractions)}")


if __name__ == "__main__":
    main()
