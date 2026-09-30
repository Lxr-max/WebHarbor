#!/usr/bin/env python3
"""Phase 4: capture the store locator (real upstream).

The store-locator city pages embed the full store directory as a Next.js
flight-data JSON array (store name, retailer, phone, address, per-day
hours, services, pickup flags, coordinates, interior/exterior image
URLs). This scraper walks state -> city pages and decodes that payload.

Run: python3.11 scrape_stores.py
Output: scraped_data/stores.json, scraped_data/pages/stores_*.html
"""
import json
import pathlib
import re
import time
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "scraped_data"
(OUT / "pages").mkdir(parents=True, exist_ok=True)

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

STATES = ["washington", "california", "new-york", "texas", "illinois",
          "florida", "oregon", "colorado", "massachusetts", "arizona"]
CITIES = {
    "washington": ["seattle", "bellevue", "tacoma", "spokane", "vancouver",
                   "redmond", "kirkland", "olympia", "yakima", "bellingham",
                   "everett", "kent", "renton", "puyallup", "walla-walla"],
    "california": ["san-francisco", "los-angeles", "san-diego", "sacramento",
                   "san-jose", "fresno", "oakland", "long-beach", "berkeley",
                   "pasadena", "stockton", "santa-monica"],
    "new-york": ["new-york", "brooklyn", "buffalo", "rochester", "albany",
                 "yonkers", "syracuse", "white-plains"],
    "texas": ["austin", "houston", "dallas", "san-antonio", "el-paso",
              "fort-worth", "plano", "arlington"],
    "illinois": ["chicago", "aurora", "naperville", "springfield",
                 "evanston", "peoria"],
    "florida": ["miami", "orlando", "tampa", "jacksonville",
                "st-petersburg", "fort-lauderdale"],
    "oregon": ["portland", "eugene", "salem", "bend", "beaverton"],
    "colorado": ["denver", "colorado-springs", "aurora", "boulder",
                 "fort-collins"],
    "massachusetts": ["boston", "worcester", "springfield", "cambridge",
                      "lowell"],
    "arizona": ["phoenix", "tucson", "mesa", "scottsdale", "chandler",
                "gilbert"],
}

FIELDS = ("storeName businessName phoneNumber address1 address2 city state "
          "zipCode storeType storeStatus hoursMon hoursTue hoursWed hoursThu "
          "hoursFri hoursSat hoursSun storeAvailableServices "
          "appointmentsAccepted fiosSold inStorePickupFlag curbside lockers "
          "doorside storeUrl interiorImageUrl exteriorImageUrl lat lng "
          "cmaDescription area region").split()


def fetch(url, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read().decode("utf-8", "replace")
        except Exception as e:
            if i == tries - 1:
                print(f"[stores] FAIL {url}: {str(e)[:100]}")
                return ""
            time.sleep(2)


def decode_stores(html):
    """Decode the store array from the Next.js flight payload."""
    chunks = re.findall(r'self\.__next_f\.push\(\[1,"(.*?)"\]\)</script>',
                        html, flags=re.S)
    for chunk in chunks:
        if "storeName" not in chunk:
            continue
        try:
            decoded = json.loads('"' + chunk + '"')
        except Exception:
            continue
        j = decoded.find('"storeName"')
        if j < 0:
            continue
        s = decoded.rfind('[{"', 0, j)
        if s < 0:
            continue
        depth = 0
        for k in range(s, min(s + 500000, len(decoded))):
            ch = decoded[k]
            if ch == "[":
                depth += 1
            elif ch == "]":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(decoded[s:k + 1])
                    except Exception:
                        return []
    return []


def main():
    all_stores = []
    city_index = {}
    for state, cities in CITIES.items():
        html = fetch(f"https://www.verizon.com/nextgendigital/nos/storelocator/{state}/")
        if html:
            (OUT / "pages" / f"stores_{state}.html").write_text(html, encoding="utf-8")
        links = re.findall(
            rf'href="/nextgendigital/nos/storelocator/{state}/([a-z-]+)"', html or "")
        city_index[state] = sorted(set(links))
        print(f"[stores] {state}: {len(city_index[state])} cities listed")
        for city in cities:
            chtml = fetch(f"https://www.verizon.com/nextgendigital/nos/storelocator/{state}/{city}")
            if not chtml:
                continue
            (OUT / "pages" / f"stores_{state}_{city}.html").write_text(
                chtml, encoding="utf-8")
            stores = decode_stores(chtml)
            for st in stores:
                row = {"locator_state": state, "locator_city": city}
                for f in FIELDS:
                    row[f] = st.get(f)
                loc = st.get("location") or {}
                row["lat"] = row.get("lat") or loc.get("latitude")
                row["lng"] = row.get("lng") or loc.get("longitude")
                all_stores.append(row)
            print(f"[stores] {state}/{city}: {len(stores)} stores")
            time.sleep(0.7)
    payload = {"city_index": city_index, "stores": all_stores}
    (OUT / "stores.json").write_text(json.dumps(payload, indent=1), encoding="utf-8")
    print(f"[stores] total {len(all_stores)} stores captured")


if __name__ == "__main__":
    main()
