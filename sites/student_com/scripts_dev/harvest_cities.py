"""Harvest city content: new-style Austin page + old-style city pages for editorial content.

Outputs scraped_data/cities_content.json: {city_slug: {...}} with sections extracted from
upstream pages. Austin gets the full new-style treatment; other cities get their editorial
content (explore/living/where-to-study/faq) from the old-style /us/{city} pages, restructured
into the new-style template at seed time.
"""
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

def strip_tags(html):
    html = re.sub(r'<script.*?</script>', '', html, flags=re.S)
    html = re.sub(r'<style.*?</style>', '', html, flags=re.S)
    return html

def text_lines(html):
    plain = re.sub(r'<[^>]+>', '\n', strip_tags(html))
    return [unescape(l).strip() for l in plain.split('\n') if l.strip()]

def harvest_old_city(city_slug):
    """Extract editorial sections from an old-style city page."""
    url = f"https://www.student.com/us/{city_slug}"
    html = fetch(url)
    if not html:
        return None
    lines = text_lines(html)
    rec = {"_source_url": url, "_style": "old"}
    # universities section: lines after "Universities"
    try:
        i = next(k for k, l in enumerate(lines) if l == "Universities")
        j = next((k for k in range(i + 1, min(i + 40, len(lines))) if lines[k].lower() == "explore" or lines[k].startswith("Student ")), i + 30)
        rec["universities_listed"] = [l for l in lines[i + 1:j] if l and not l.startswith("About")][:14]
    except StopIteration:
        rec["universities_listed"] = []
    # capture the long editorial block: from first "About" heading through FAQ
    try:
        a = next(k for k, l in enumerate(lines) if l == "About")
        rec["editorial_lines"] = lines[a:a + 400]
    except StopIteration:
        rec["editorial_lines"] = []
    # hero image + title
    m = re.search(r'<h1[^>]*>(.*?)</h1>', strip_tags(html), re.S)
    if m:
        rec["h1"] = unescape(re.sub(r'<[^>]+>', ' ', m.group(1))).strip()
    m = re.search(r'<meta name="description" content="([^"]*)"', html)
    if m:
        rec["meta_description"] = unescape(m.group(1))
    m = re.search(r'<title>([^<]*)</title>', html)
    if m:
        rec["title"] = unescape(m.group(1))
    return rec

def harvest_new_city(state, city_slug):
    """Extract the new-style Austin city page structure."""
    url = f"https://www.student.com/us/{state}/{city_slug}"
    html = fetch(url)
    if not html:
        return None
    lines = text_lines(html)
    rec = {"_source_url": url, "_style": "new", "lines": lines}
    # popular properties + colleges links
    props = re.findall(r'href="(/us/[a-z-]+/' + city_slug + r'/p/[a-z0-9-]+)"', html)
    unis = re.findall(r'href="(/us/[a-z-]+/' + city_slug + r'/u/[a-z0-9-]+)"', html)
    rec["property_links"] = sorted(set(props))
    rec["university_links"] = sorted(set(unis))
    m = re.search(r'<title>([^<]*)</title>', html)
    if m:
        rec["title"] = unescape(m.group(1))
    # hero image url
    imgs = re.findall(r'https://dbswqyg6sdujh\.cloudfront\.net/[^"\\ )]+', html)
    rec["cdn_images"] = sorted(set(imgs))
    return rec

def main():
    cities = {}
    # new-style austin
    a = harvest_new_city("tx", "austin")
    if a:
        cities["austin"] = a
        print("austin (new):", len(a["lines"]), "lines,", len(a["property_links"]), "props,", len(a["university_links"]), "unis")
    # old-style editorial for the other mirror cities
    old_cities = ["college-station", "houston", "san-marcos", "lubbock", "gainesville", "orlando",
                  "tampa", "tallahassee", "coral-gables", "atlanta", "athens", "columbus", "oxford",
                  "cleveland", "cincinnati"]
    for c in old_cities:
        rec = harvest_old_city(c)
        if rec:
            cities[c] = rec
            print(f"{c} (old): {len(rec['editorial_lines'])} editorial lines, unis={len(rec['universities_listed'])}")
        else:
            print(f"{c}: 404")
        time.sleep(0.4)
    (OUT / "cities_content.json").write_text(json.dumps(cities, indent=1))
    print("saved", len(cities), "cities")

if __name__ == "__main__":
    main()
