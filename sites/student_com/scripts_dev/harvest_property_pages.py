"""Harvest full property records from each property page's Next.js flight data.

Reads scraped_data/srp_properties.json; writes scraped_data/properties_full.json
{slug: full_record} where full_record merges the discovery record + the page record
(property_summary, reviews_summary, room_types, room_details, office_hours, phone_number,
website, wheelchair_accessible, user_rating_count, is_featured, hide_contact, amenities...).
"""
import json, pathlib, re, sys, time, urllib.request, urllib.error

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "scraped_data"
HDRS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.student.com/",
}

def fetch(url, retries=4):
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=HDRS)
            with urllib.request.urlopen(req, timeout=45) as r:
                return r.read().decode("utf-8", "ignore")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            time.sleep(1 + attempt)
        except Exception as e:
            print(f"  [retry {attempt}] {e}", file=sys.stderr)
            time.sleep(1 + attempt)
    return None

def flight_blob(html):
    chunks = re.findall(r'self\.__next_f\.push\(\[1,"((?:[^"\\]|\\.)*)"\]\)', html)
    if not chunks:
        return None
    blob = "".join(chunks)
    try:
        return blob.encode().decode("unicode_escape", errors="ignore")
    except Exception:
        return blob.replace('\\"', '"').replace("\\\\", "\\")

def extract_record(blob, pid):
    """Find the full property record JSON object starting at {"id":"<pid>"."""
    needle = '{"id":"' + pid + '"'
    start = 0
    while True:
        i = blob.find(needle, start)
        if i < 0:
            return None
        try:
            obj, _ = json.JSONDecoder().raw_decode(blob[i:])
            if isinstance(obj, dict) and obj.get("id") == pid and ("room_types" in obj or "property_summary" in obj or "property_amenities" in obj):
                return obj
        except Exception:
            pass
        start = i + 1

def extract_office_hours(html):
    m = re.search(r'\["(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)[^\]]*\]', html)
    if m:
        try:
            return json.loads(m.group(0).replace('\\"', '"'))
        except Exception:
            return None
    return None

def main():
    data = json.load(open(OUT / "srp_properties.json"))
    props = data["properties"]
    done_path = OUT / "properties_full.json"
    done = json.load(open(done_path)) if done_path.exists() else {}
    todo = [p for p in props.values() if p["slug"] not in done]
    print(f"total={len(props)} done={len(done)} todo={len(todo)}")
    for n, rec in enumerate(todo, 1):
        url = f"https://www.student.com/us/{rec['state_slug']}/{rec['city_slug']}/p/{rec['slug']}"
        html = fetch(url)
        if html is None:
            print(f"[{n}] 404 {rec['slug']}")
            done[rec["slug"]] = {**rec, "_page_missing": True}
            continue
        blob = flight_blob(html)
        full = extract_record(blob, rec["id"]) if blob else None
        merged = {**rec}
        if full:
            for k, v in full.items():
                if v is not None or k not in merged:
                    merged[k] = v
        if not merged.get("office_hours"):
            oh = extract_office_hours(blob or html)
            if oh:
                merged["office_hours"] = oh
        merged["_page_url"] = url
        done[rec["slug"]] = merged
        if n % 10 == 0:
            done_path.write_text(json.dumps(done, indent=1))
            print(f"[{n}/{len(todo)}] saved; last={rec['slug']}")
        time.sleep(0.35)
    done_path.write_text(json.dumps(done, indent=1))
    print("final count:", len(done))

if __name__ == "__main__":
    main()
