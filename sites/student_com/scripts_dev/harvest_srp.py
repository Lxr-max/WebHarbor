"""Harvest property lists per flagship university via the discovery/search API.

Outputs scraped_data/srp_properties.json:
  { "universities": {slug: {...record, "properties": [...]}}, "properties": {slug: {...}} }
Property records dedupe by id; per-university distance/index kept on the university entry.
"""
import json, pathlib, sys, time, urllib.request

OUT = pathlib.Path(__file__).resolve().parent.parent / "scraped_data"
API = "https://platform.student.com/discovery/search"
HDRS = {
    "Content-Type": "application/json",
    "Origin": "https://www.student.com",
    "Referer": "https://www.student.com/",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36",
    "Accept": "application/json",
}

# flagship universities: slug -> cap
UNIS = {
    # TX
    "the-university-of-texas-at-austin": 30,
    "texas-am-university": 25,
    "university-of-houston": 25,
    "texas-state-university": 20,
    "texas-tech-university": 20,
    # FL
    "university-of-florida": 25,
    "university-of-central-florida": 25,
    "university-of-south-florida": 25,
    "florida-state-university": 20,
    "university-of-miami": 20,
    # GA
    "georgia-institute-of-technology": 30,
    "georgia-state-university": 25,
    "university-of-georgia": 20,
    # OH
    "the-ohio-state-university": 30,
    "ohio-university": 22,
    "miami-university": 12,
    "case-western-reserve-university": 20,
    "university-of-cincinnati": 20,
}

def api_call(payload, retries=4):
    for attempt in range(retries):
        try:
            req = urllib.request.Request(API, data=json.dumps(payload).encode(),
                                         headers=HDRS, method="POST")
            with urllib.request.urlopen(req, timeout=45) as r:
                return json.loads(r.read().decode())
        except Exception as e:
            print(f"  [retry {attempt}] {e}", file=sys.stderr)
            time.sleep(2 + attempt * 2)
    raise RuntimeError(f"api failed for {payload}")

def main():
    unis, props = {}, {}
    for slug, cap in UNIS.items():
        first = api_call({"university_slug": slug, "limit": 0, "offset": 0})
        total = first["total"]
        print(f"[{slug}] total={total} cap={cap}")
        records = []
        offset = 0
        while len(records) < min(cap, total):
            batch = api_call({"university_slug": slug, "limit": 50, "offset": offset})
            got = batch.get("properties") or []
            if not got:
                break
            records.extend(got)
            offset += len(got)
        records = records[:cap]
        unis[slug] = {"total": total, "capped": len(records), "properties": []}
        for rec in records:
            pid = rec["id"]
            unis[slug]["properties"].append({
                "id": pid, "slug": rec["slug"], "distance_miles": rec.get("distance_miles"),
                "property_index": rec.get("property_index"),
            })
            if pid not in props:
                props[pid] = rec
        time.sleep(0.4)
    # cross-link: property -> universities near
    for pid, rec in props.items():
        rec["universities"] = [
            {"slug": u, "distance_miles": p["distance_miles"], "property_index": p["property_index"]}
            for u, d in unis.items() for p in d["properties"] if p["id"] == pid
        ]
    out = {"universities": unis, "properties": props}
    (OUT / "srp_properties.json").write_text(json.dumps(out, indent=1))
    print(f"unique properties: {len(props)}")
    cities = {}
    for rec in props.values():
        key = (rec.get("state_slug"), rec.get("city_slug"))
        cities.setdefault(key, set()).add(rec["id"])
    for k, v in sorted(cities.items(), key=lambda x: -len(x[1])):
        print(k, len(v))

if __name__ == "__main__":
    main()
