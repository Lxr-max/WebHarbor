"""Harvest static content pages + homepage data (hot cities, state CTAs, carousels)."""
import json, pathlib, re, sys, time, urllib.request, urllib.error
from html import unescape

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "scraped_data"
HDRS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
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

def text_lines(html):
    html = re.sub(r'<script.*?</script>', '', html, flags=re.S)
    html = re.sub(r'<style.*?</style>', '', html, flags=re.S)
    plain = re.sub(r'<[^>]+>', '\n', html)
    return [unescape(l).strip() for l in plain.split('\n') if l.strip()]

def flight_blob(html):
    chunks = re.findall(r'self\.__next_f\.push\(\[1,"((?:[^"\\]|\\.)*)"\]\)', html)
    if not chunks:
        return None
    blob = "".join(chunks)
    try:
        return blob.encode().decode("unicode_escape", errors="ignore")
    except Exception:
        return blob

PAGES = {
    "about": "https://www.student.com/about",
    "contact": "https://www.student.com/contact",
    "how-it-works": "https://www.student.com/how-it-works",
    "help": "https://www.student.com/help",
    "guides-avoid-scams": "https://www.student.com/guides/avoid-scams-and-fraud",
    "scholarships": "https://www.student.com/scholarships",
    "budget-calculator": "https://www.student.com/budget-calculator",
    "list-your-property": "https://www.student.com/list-your-property",
    "terms": "https://www.student.com/terms",
    "privacy": "https://www.student.com/terms/privacy",
    "jobs": "https://www.student.com/jobs",
}

def main():
    static_dir = OUT / "static_pages"
    static_dir.mkdir(exist_ok=True)
    for name, url in PAGES.items():
        html = fetch(url)
        if html is None:
            print(f"{name}: 404")
            continue
        (static_dir / f"{name}.html").write_text(html)
        lines = text_lines(html)
        title = re.search(r"<title>([^<]*)</title>", html)
        print(f"{name}: {len(html)} bytes, {len(lines)} lines, title={unescape(title.group(1)) if title else None}")
        time.sleep(0.3)

    # homepage data
    home = fetch("https://www.student.com/")
    (OUT / "home_live.html").write_text(home)
    blob = flight_blob(home)
    (OUT / "home_flight.txt").write_text(blob or "")
    print("home:", len(home), "bytes, flight:", len(blob or ""))
    # hot cities from HotCities GraphQL
    gql = "https://gateway.student.com/graphql"
    query = {"query": "query HotCities { cities(sortBy: STAR_ROW) { edges { node { id name slug properties country { originalName slug } smallHeroImage { source } } } } }"}
    req = urllib.request.Request(gql, data=json.dumps(query).encode(),
                                headers={"Content-Type": "application/json", "Origin": "https://www.student.com",
                                         "Referer": "https://www.student.com/", **HDRS})
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            hot = json.loads(r.read().decode())
        (OUT / "hot_cities.json").write_text(json.dumps(hot, indent=1))
        edges = hot["data"]["cities"]["edges"]
        print("hot cities:", len(edges), [e["node"]["name"] for e in edges[:12]])
    except Exception as e:
        print("hot cities failed:", e)

if __name__ == "__main__":
    main()
