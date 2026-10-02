#!/usr/bin/env python3
"""Build the tracked source_data/ snapshots from the gitignored scraped_data/
captures (carvana.com pages captured 2026-09-29 with a headful Chromium that
rendered the real site behind its Cloudflare bot management).

Every tracked snapshot is a deterministic trim of the real upstream capture;
the trim policy is declared in provenance.json. Re-run: nothing here talks to
the network. The upstream pages are Next.js app-router pages: the vehicle
data lives in the RSC flight payloads (self.__next_f.push chunks) and in the
JSON-LD blocks — the extractors below parse those payloads: no synthesis,
every field traces to a capture file in scraped_data/captures/.

Run:  python3 scripts_dev/build_source_data.py
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.dirname(HERE)
SCRAPE = os.path.join(SITE, "scraped_data", "captures")
OUT = os.path.join(SITE, "source_data")

os.makedirs(OUT, exist_ok=True)


def _flight_of(html):
    """Join the RSC flight chunks a Next.js app-router page embeds."""
    chunks = re.findall(r'self\.__next_f\.push\(\[1,("(?:[^"\\]|\\.)*")\]\)',
                        html, re.S)
    return "".join(json.loads(c) for c in chunks)


def _json_at(flight, anchor, key):
    """Parse the JSON value that follows `"key":` at the anchor position."""
    i = flight.find(anchor, flight.find(f'"{key}":'))
    j = flight.find(f'"{key}":') + len(f'"{key}":')
    depth = 0
    k = j
    in_str = False
    esc = False
    while k < len(flight):
        c = flight[k]
        if esc:
            esc = False
        elif c == '\\':
            esc = True
        elif in_str:
            if c == '"':
                in_str = False
        else:
            if c == '"':
                in_str = True
            elif c == '[':
                depth += 1
            elif c == ']':
                depth -= 1
                if depth == 0:
                    break
            elif c == '{':
                pass
        k += 1
    return json.loads(flight[j:k + 1])


def _object_at(text, pos):
    """Parse the balanced JSON object starting at the '{' at `pos`."""
    depth = 0
    end = pos
    in_str = False
    esc = False
    while end < len(text):
        c = text[end]
        if esc:
            esc = False
        elif c == '\\':
            esc = True
        elif in_str:
            if c == '"':
                in_str = False
        else:
            if c == '"':
                in_str = True
            elif c == '{':
                depth += 1
            elif c == '}':
                depth -= 1
                if depth == 0:
                    break
        end += 1
    return json.loads(text[pos:end + 1])


def load_capture(key):
    path = os.path.join(SCRAPE, f"{key}.html")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return f.read()


# ---------------------------------------------------------------- SRP build --

def extract_srp(key):
    """One SRP capture -> (vehicles, pagination, facets)."""
    html = load_capture(key)
    if not html:
        return None
    flight = _flight_of(html)
    vehicles = []
    i = flight.find('"vehicles":[{"stockNumber"')
    if i >= 0:
        vehicles = _json_at(flight, '"vehicles":', "vehicles")
    pagination = None
    m = re.search(r'"pagination":\{"currentPage":(\d+),"pageSize":(\d+),'
                  r'"totalMatchedInventory":(\d+),"totalMatchedPages":(\d+)\}',
                  flight)
    if m:
        pagination = {"currentPage": int(m.group(1)),
                      "pageSize": int(m.group(2)),
                      "totalMatchedInventory": int(m.group(3)),
                      "totalMatchedPages": int(m.group(4))}
    facets = None
    fi = flight.find('"makes":{"')
    if fi >= 0:
        # walk back to the enclosing baseline object start
        pos = fi
        depth = 0
        while pos > 0:
            c = flight[pos]
            if c == '}':
                depth += 1
            elif c == '{':
                if depth == 0:
                    break
                depth -= 1
            pos -= 1
        try:
            facets = _object_at(flight, pos)
        except Exception:
            facets = None
    return {"key": key, "vehicles": vehicles, "pagination": pagination,
            "facets": facets}


def build_vehicles():
    """Merge every SRP capture into the vehicle-card corpus."""
    corpus = {}
    snapshots = []
    facets = None
    for name in sorted(os.listdir(SCRAPE)):
        if not (name.startswith("srp_") and name.endswith(".html")):
            continue
        key = name[:-5]
        data = extract_srp(key)
        if not data:
            continue
        meta_path = os.path.join(SCRAPE, f"{key}.meta.json")
        url = f"https://www.carvana.com/cars"
        if os.path.exists(meta_path):
            with open(meta_path) as f:
                url = json.load(f).get("url", url)
        if data["pagination"]:
            snapshots.append({
                "key": key, "url": url,
                "upstream_total": data["pagination"]["totalMatchedInventory"],
                "page_size": data["pagination"]["pageSize"],
                "page1_order": [v["vehicleId"] for v in data["vehicles"]],
            })
        if data["facets"] and key == "srp_all":
            facets = data["facets"]
        for v in data["vehicles"]:
            corpus[v["vehicleId"]] = v
    return corpus, snapshots, facets


# --------------------------------------------------------------- VDP build --

def extract_vdp(key):
    html = load_capture(key)
    if not html:
        return None
    flight = _flight_of(html)
    i = flight.find('"make":"')
    if i < 0:
        return None
    pos = i
    depth = 0
    while pos > 0:
        c = flight[pos]
        if c == '}':
            depth += 1
        elif c == '{':
            if depth == 0:
                break
            depth -= 1
        pos -= 1
    details = _object_at(flight, pos)
    # reviews + pricing from the apis sidecar
    reviews = []
    pricing = None
    apis_path = os.path.join(SCRAPE, f"{key}.apis.json")
    if os.path.exists(apis_path):
        with open(apis_path) as f:
            apis = json.load(f)
        for a in apis:
            if "/merch/reviews" in a["url"]:
                try:
                    body = json.loads(a["body"])
                    reviews = body.get("reviews", [])
                except Exception:
                    pass
            if "/v2/pricing" in a["url"]:
                try:
                    body = json.loads(a["body"])
                    mapping = body.get("vehiclePaymentTermsMapping", {})
                    for _vid, terms in mapping.items():
                        pricing = terms
                except Exception:
                    pass
    # spinner data (photo manifest)
    photos = {}
    apis_path = os.path.join(SCRAPE, f"{key}.apis.json")
    if os.path.exists(apis_path):
        with open(apis_path) as f:
            apis = json.load(f)
        for a in apis:
            if "spinnerdata" in a["url"]:
                try:
                    sd = json.loads(a["body"])
                    spins = sd.get("spins", [])
                    if spins:
                        photos["spin_frames"] = spins[0].get("images", {}).get("urls", [])
                        photos["hero"] = spins[0].get("heroImageUrl")
                        photos["gif"] = spins[0].get("gifUrl")
                    inter = sd.get("interiorImages", [])
                    if inter:
                        photos["interior"] = inter[0].get("url")
                except Exception:
                    pass
    return {"details": details, "reviews": reviews, "pricing": pricing,
            "photos": photos}


def build_vdp_details():
    details = {}
    reviews = []
    for name in sorted(os.listdir(SCRAPE)):
        if not (name.startswith("vdp_") and name.endswith(".html")):
            continue
        key = name[:-5]
        vid = int(key.split("_")[1])
        data = extract_vdp(key)
        if not data:
            continue
        details[vid] = data
        for r in data["reviews"]:
            reviews.append({
                "vehicle_id": vid,
                "make_model": (r.get("vehicle") or {}).get("vehicle_make_model"),
                "rating": r.get("review_rating"),
                "review_date": r.get("review_date"),
                "author": (r.get("customer") or {}).get("name"),
                "text": r.get("review_text"),
            })
    return details, reviews


# ----------------------------------------------------------- content pages --

CONTENT_KEYS = [
    ("how_it_works", "how-it-works"),
    ("financing", "financing"),
    ("faq", "faq"),
    ("reviews", "reviews"),
    ("certified_program", "certified-program"),
    ("vending_machine", "vending-machine"),
    ("vehicle_protection_plans", "vehicle-protection-plans"),
    ("insurance", "insurance"),
    ("repairs", "repairs"),
    ("guide_to_buying_a_used_ev", "guide-to-buying-a-used-ev"),
    ("value_tracker", "value-tracker"),
    ("help", "help"),
    ("learn_financing", "learn-financing"),
    ("buying_a_car_online_how_it_works", "buying-a-car-online-how-it-works"),
    ("selling_or_trades_how_it_works", "selling-or-trades-how-it-works"),
]

HELP_SECTIONS = {
    "carvana-inventory": "About Our Vehicles",
    "pickup-and-delivery": "Pickup & Delivery",
    "sell-or-trade": "Trading In & Selling",
    "payment-and-financing": "Payment and Financing",
    "extended-coverage-and-repairs": "Vehicle Protection & Repairs",
    "purchasing-a-car": "Purchasing a Car",
}

HELP_CATEGORY_PREFIXES = [
    "Purchasing a Car", "Payment and Financing", "Pickup & Delivery",
    "Trading In & Selling", "About Our Vehicles",
    "Vehicle Protection & Repairs",
]


def build_help_articles():
    """The captured /help/<section>/<article>/ pages: each carries its
    section name, the question and the answer body in one <p> block."""
    articles = []
    for name in sorted(os.listdir(SCRAPE)):
        if not (name.startswith("helpart_") and name.endswith(".html")):
            continue
        html = load_capture(name[:-5])
        if not html:
            continue
        title_m = re.search(r'<meta property="og:title" content="([^"]+)"',
                            html)
        title = (title_m.group(1).strip() if title_m else
                 name[:-5].split("_")[-1].replace("-", " "))
        title = title.replace(" | Carvana", "").replace(
            " | Help Center", "").replace(" | Carvana.com", "").strip()
        dom = re.sub(r'<script[^>]*>.*?</script>', ' ', html, flags=re.S)
        dom = re.sub(r'<style[^>]*>.*?</style>', ' ', dom, flags=re.S)
        m = re.search(r'<main[^>]*>', dom)
        if m:
            dom = dom[m.start():]
        body = None
        for mm in re.finditer(r'<p[^>]*>(.*?)</p>', dom, re.S):
            txt = ' '.join(re.sub(r'<[^>]+>', ' ', mm.group(1)).split())
            txt = txt.replace('&amp;', '&').replace('&nbsp;', ' ')
            txt = ' '.join(txt.split())
            if txt.startswith("Was this article helpful"):
                break
            if len(txt) > 60 and any(
                    txt.startswith(p) for p in HELP_CATEGORY_PREFIXES):
                body = txt
                break
        if not body:
            continue
        for p in HELP_CATEGORY_PREFIXES:
            if body.startswith(p):
                body = body[len(p):].strip()
                break
        q = None
        qm = re.match(r'(.+?\?)', body)
        if qm:
            q = qm.group(1).strip()
            answer = body[len(qm.group(1)):].strip()
        else:
            # title carries the question when the body starts with it
            q = title
            answer = body
        section = name[:-5].split("_")[2]
        category = HELP_SECTIONS.get(section, section.replace("-", " "))
        slug = name[:-5].split("_", 3)[3]
        articles.append({
            "section": section,
            "category": category,
            "question": q,
            "answer": answer,
            "title": title,
            "slug": slug,
        })
    return articles


def _visible_text(html):
    txt = re.sub(r'<script[^>]*>.*?</script>', ' ', html, flags=re.S)
    txt = re.sub(r'<style[^>]*>.*?</style>', ' ', txt, flags=re.S)
    txt = re.sub(r'<[^>]+>', '\n', txt)
    txt = txt.replace('&nbsp;', ' ').replace('&amp;', '&').replace('&#x27;', "'")
    txt = txt.replace('&rsquo;', '’').replace('&ldquo;', '“').replace('&rdquo;', '”')
    lines = [ln.strip() for ln in txt.split('\n')]
    return [ln for ln in lines if len(ln) > 2]


CHROME_PREFIXES = (
    'Search Cars Sell/Trade Financing',
    'Carvana Help & Support',
)


def build_content_pages():
    pages = {}
    for key, _route in CONTENT_KEYS:
        html = load_capture(f"_static_{key}")
        if not html:
            continue
        title_m = re.search(
            r'<meta property="og:title" content="([^"]+)"', html)
        if not title_m:
            title_m = re.search(r'<title[^>]*>([^<]+)</title>', html)
        raw_title = (title_m.group(1).strip() if title_m else key)
        title = (raw_title.replace(' | Carvana', '')
                 .replace(' | Carvana.com', '').replace('.com', '')
                 .replace('&amp;', '&').strip())
        # Strip script/style blocks (embedded JSON payloads swallow whole
        # regions), then cut at <main> when present: the header nav and the
        # footer live outside it and are dropped wholesale.
        dom = re.sub(r'<script[^>]*>.*?</script>', ' ', html, flags=re.S)
        dom = re.sub(r'<style[^>]*>.*?</style>', ' ', dom, flags=re.S)
        m = re.search(r'<main[^>]*>', dom)
        if m:
            dom = dom[m.start():]
        # Informational pages render content as short title <p>s followed by
        # body <p>s; nav/footer items are <li>s and are not scanned.
        texts = []
        for mm in re.finditer(r'<(p|h[1-6])(?![a-z])[^>]*>(.*?)</\1>', dom, re.S):
            inner = mm.group(2)
            if '<svg' in inner or '<img' in inner:
                continue
            txt = re.sub(r'<[^>]+>', ' ', inner)
            txt = (txt.replace('&nbsp;', ' ').replace('&amp;', '&')
                   .replace('&#x27;', "'").replace('&rsquo;', '\u2019')
                   .replace('&ldquo;', '\u201c').replace('&rdquo;', '\u201d')
                   .replace('&trade;', '\u2122').replace('&reg;', '\u00ae'))
            txt = ' '.join(txt.split())
            if not txt or len(txt) < 3:
                continue
            if txt.startswith(CHROME_PREFIXES):
                txt = txt[len(next(p for p in CHROME_PREFIXES
                                   if txt.startswith(p))):].strip()
                if not txt:
                    continue
            texts.append(txt)
        sections = []
        cur = None
        para = []
        bullets = []

        def flush():
            nonlocal cur, para, bullets
            if cur is not None:
                if para:
                    cur['paragraphs'] = para
                if bullets:
                    cur['bullets'] = bullets
                if cur.get('paragraphs') or cur.get('bullets'):
                    sections.append(cur)
            cur, para, bullets = None, [], []

        for txt in texts:
            if len(txt) < 90 and not txt.endswith('.'):
                # short non-sentence line: treat as a section heading
                flush()
                cur = {'heading': txt}
                continue
            if cur is None:
                cur = {'heading': None}
            para.append(txt)
            if len(para) > 6:
                flush()
        flush()
        pages[key] = {'title': title, 'route': f'/{_route}',
                      'sections': sections}
    return pages


# --------------------------------------------------------------------- main --

def main():
    print("building source_data from scraped_data/captures ...")
    corpus, snapshots, facets = build_vehicles()
    print(f"vehicle cards: {len(corpus)}")
    print(f"srp snapshots: {len(snapshots)}")
    with open(os.path.join(OUT, "vehicles.json"), "w") as f:
        json.dump([corpus[k] for k in sorted(corpus)], f, indent=1)
    with open(os.path.join(OUT, "srp_snapshots.json"), "w") as f:
        json.dump(snapshots, f, indent=1)
    if facets:
        with open(os.path.join(OUT, "facets.json"), "w") as f:
            json.dump(facets, f, indent=1)
        print("facets: saved (srp_all)")
    details, reviews = build_vdp_details()
    print(f"vdp details: {len(details)}, reviews: {len(reviews)}")
    with open(os.path.join(OUT, "vdp_details.json"), "w") as f:
        json.dump({str(k): details[k] for k in sorted(details)}, f, indent=1)
    with open(os.path.join(OUT, "reviews.json"), "w") as f:
        json.dump(reviews, f, indent=1)
    # pricing batch capture (all corpus vehicles)
    pricing_path = os.path.join(SCRAPE, "pricing_all.json")
    if os.path.exists(pricing_path):
        with open(pricing_path) as f:
            pricing = json.load(f)
        with open(os.path.join(OUT, "pricing.json"), "w") as f:
            json.dump(pricing, f, indent=1)
        print(f"pricing terms: {len(pricing)}")
    # photo manifest for the image downloader
    manifest = {}
    for vid, data in details.items():
        manifest[vid] = data["photos"]
    with open(os.path.join(OUT, "photo_manifest.json"), "w") as f:
        json.dump({str(k): manifest[k] for k in sorted(manifest)}, f, indent=1)
    pages = build_content_pages()
    with open(os.path.join(OUT, "content_pages.json"), "w") as f:
        json.dump(pages, f, indent=1)
    print(f"content pages: {len(pages)} -> {sorted(pages)}")
    articles = build_help_articles()
    with open(os.path.join(OUT, "help_articles.json"), "w") as f:
        json.dump(articles, f, indent=1)
    print(f"help articles: {len(articles)}")


if __name__ == "__main__":
    main()
