"""Harvest job listings per city from the internships pages' flight data."""
import json, pathlib, re, sys, time, urllib.request, urllib.error

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "scraped_data"
HDRS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

CITIES = {  # city_slug -> state
    "austin": "tx", "college-station": "tx", "houston": "tx", "san-marcos": "tx", "lubbock": "tx",
    "gainesville": "fl", "orlando": "fl", "tampa": "fl", "tallahassee": "fl", "coral-gables": "fl",
    "atlanta": "ga", "athens": "ga", "columbus": "oh", "oxford": "oh", "cleveland": "oh", "cincinnati": "oh",
}

def fetch(url, retries=3):
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

def listings_from_flight(html):
    chunks = re.findall(r'self\.__next_f\.push\(\[1,"((?:[^"\\]|\\.)*)"\]\)', html)
    if not chunks:
        return None
    blob = "".join(chunks)
    try:
        blob = blob.encode().decode("unicode_escape", errors="ignore")
    except Exception:
        pass
    i = blob.find('"listings":[')
    if i < 0:
        return None
    arr, _ = json.JSONDecoder().raw_decode(blob[i + len('"listings":'):])
    return arr

def main():
    jobs = {}
    for city, state in CITIES.items():
        url = f"https://www.student.com/us/{state}/{city}/internships"
        html = fetch(url)
        if not html:
            print(f"{city}: 404")
            continue
        arr = listings_from_flight(html)
        if arr is None:
            print(f"{city}: no listings in flight")
            continue
        jobs[city] = {"_source_url": url, "listings": arr}
        print(f"{city}: {len(arr)} jobs")
        time.sleep(0.4)
    (OUT / "jobs.json").write_text(json.dumps(jobs, indent=1))
    print("saved", len(jobs), "cities,", sum(len(v["listings"]) for v in jobs.values()), "jobs")

if __name__ == "__main__":
    main()
