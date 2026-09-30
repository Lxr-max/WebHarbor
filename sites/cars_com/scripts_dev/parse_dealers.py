#!/usr/bin/env python3
"""Parse captured cars.com dealer pages into scraped_data/dealers_raw.json.

Handles three page shapes, all real upstream renders:
  - dealers-dir*.html        the /dealers/buy/ directory (dealer cards)
  - dealer-<slug>.html       a dealership detail page
  - dealer-<slug>-reviews.html  the dealership reviews page

The dealer detail and reviews pages embed the page's own AutoDealer
JSON-LD (aggregateRating, contactPoint, openingHoursSpecification, the
visible hours table, the about description and the review list); the
parser reads that structured payload first and falls back to the visible
render for the hours table and the awards count.

Run:  python3 scripts_dev/parse_dealers.py
"""
import json
import os
import re
from html import unescape

HERE = os.path.dirname(os.path.abspath(__file__))
CAP = os.path.join(HERE, "..", "scraped_data", "captures")
OUT = os.path.join(HERE, "..", "scraped_data")

DAY = r"(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)"
TIME = r"(?:\d{1,2}:\d{2}[ap]m[–-]\d{1,2}:\d{2}[ap]m|Closed)"


def T(block):
    return " ".join(unescape(re.sub(r"<[^>]+>", " ", block)).split())


def autodealer_ld(html):
    """The page's own AutoDealer JSON-LD payload, or None."""
    for m in re.finditer(r'<script type="application/ld\+json">(.*?)</script>',
                         html, re.S):
        try:
            data = json.loads(m.group(1))
        except Exception:
            continue
        if data.get("@type") == "AutoDealer":
            return data
    return None


def parse_directory(path):
    html = open(path, encoding="utf-8").read()
    dealers = {}
    for m in re.finditer(r'<fuse-card class="dealer-card".*?(?=<fuse-card class="dealer-card"|$)', html, re.S):
        block = m.group(0)
        d = {}
        mm = re.search(r'href="/dealers/(\d+)/([a-z0-9-]+)/"', block)
        if not mm:
            continue
        d["dealer_id"], d["slug"] = int(mm.group(1)), mm.group(2)
        mm = re.search(r'<h2 class="dealer-heading">\s*([^<]+?)\s*</h2>', block)
        d["name"] = unescape(mm.group(1)).strip() if mm else None
        mm = re.search(r'<fuse-rating rating="([\d.]+)"', block)
        d["rating"] = float(mm.group(1)) if mm else None
        mm = re.search(r'\(([\d,]+) reviews\)', block)
        d["review_count"] = int(mm.group(1).replace(",", "")) if mm else None
        mm = re.search(r'class="link-ext"[^>]*>([^<]+)<', block)
        if not mm:
            mm = re.search(r'query=.*?" rel="noopener[^"]*" target="_blank"[^>]*>([^<]+)<', block)
        d["address"] = unescape(mm.group(1)).strip() if mm else None
        if d["address"]:
            mm2 = re.search(r"^(.*), ([A-Za-z .]+), ([A-Z]{2}) (\d{5})$", d["address"])
            if mm2:
                d["street"] = mm2.group(1).strip()
                d["city"] = mm2.group(2).strip()
                d["state"] = mm2.group(3)
                d["zip"] = mm2.group(4)
        mm = re.search(r'class="dealer-distance">\s*([\d.]+) miles away', block)
        d["distance_miles"] = int(float(mm.group(1))) if mm else None
        mm = re.search(r'View inventory \(([\d,]+) cars\)', T(block))
        d["inventory_count"] = int(mm.group(1).replace(",", "")) if mm else None
        phones = {}
        for pm in re.finditer(r'<span class="phone-number-title">\s*(New|Used|Service)\s*</span>.*?class="(?:phone-number|desktop-phone-number)"[^>]*>\s*\(?\d[\d)\- ]+', block, re.S):
            label = pm.group(1)
            pm2 = re.search(r'(\(?\d{3}\)?[ -]?\d{3}[ -]?\d{4})', pm.group(0))
            if pm2:
                phones[label.lower()] = pm2.group(1)
        d["phones"] = phones
        if d["name"]:
            dealers[d["slug"]] = d
    return dealers


def hours_from_text(t):
    """The visible hours table: 'Sales [Service] Monday 9:00am–8:00pm
    [7:00am–5:30pm] ...' — one or two time columns per day; the sales
    column is the hours row the mirror shows."""
    i = t.find("View all hours")
    seg = t[i:i + 700] if i > 0 else ""
    hours = []
    for m in re.finditer(rf"{DAY}\s+({TIME})(?:\s+({TIME}))?", seg):
        day, sales, service = m.group(1), m.group(2), m.group(3)
        hours.append({"day": day, "hours": sales})
    return hours


def parse_dealer_page(path):
    html = open(path, encoding="utf-8").read()
    t = T(re.sub(r"<script.*?</script>", " ", html, flags=re.S))
    d = {"source_file": os.path.basename(path)}
    mm = re.search(r'href="/dealers/(\d+)/([a-z0-9-]+)/?"', html)
    if mm:
        d["dealer_id"], d["slug"] = int(mm.group(1)), mm.group(2)
    ld0 = autodealer_ld(html) or {}
    if "dealer_id" not in d and str(ld0.get("@id", "")).lstrip("#").isdigit():
        d["dealer_id"] = int(ld0["@id"].lstrip("#"))
    if "slug" not in d:
        fm = re.match(r"dealer-([a-z0-9-]+)\.html$", os.path.basename(path))
        if fm:
            d["slug"] = fm.group(1)
    mm = re.search(r"<h1[^>]*>\s*([^<]+?)\s*</h1>", html)
    d["name"] = unescape(mm.group(1)).strip() if mm else None
    ld = autodealer_ld(html) or {}
    # rating + review count (structured payload; falls back to the visible
    # '★ 4.9 (1,266 reviews)' render)
    agg = ld.get("aggregateRating") or {}
    d["rating"] = float(agg["ratingValue"]) if agg.get("ratingValue") else None
    d["review_count"] = int(agg["reviewCount"]) if agg.get("reviewCount") else None
    if d["rating"] is None:
        mm = re.search(r'<fuse-rating rating="([\d.]+)"', html)
        d["rating"] = float(mm.group(1)) if mm else None
    if d["review_count"] is None:
        mm = re.search(r'\(([\d,]+) reviews\)', t)
        d["review_count"] = int(mm.group(1).replace(",", "")) if mm else None
    # hours from the visible table (sales column)
    d["hours"] = hours_from_text(t)
    # about: the structured description, else the visible 'About our dealership' run
    about = (ld.get("description") or "").strip()
    if not about:
        i = t.find("About our dealership")
        if i > 0:
            seg = t[i + len("About our dealership"):i + 1400]
            about = re.sub(r"^ This seller has been on Cars\.com since [A-Za-z]+ \d{4} \.?", "", seg).strip()
    if about:
        d["about"] = about[:1400]
    # awards ('View 8 awards')
    mm = re.search(r"View (\d+) awards", t)
    d["awards"] = int(mm.group(1)) if mm else None
    # phones from the structured contactPoint + department
    phones = {}
    for cp in ld.get("contactPoint", []) or []:
        label = {"Sales - New Cars": "new", "Sales - Used Cars": "used"}.get(cp.get("contactType"))
        if label and cp.get("telephone"):
            phones[label] = cp["telephone"]
    dept = ld.get("department") or {}
    if dept.get("telephone"):
        phones["service"] = dept["telephone"]
    if not phones:
        for pm in re.finditer(r"(New|Used|Service) (\(?\d{3}\)?[ -]?\d{3}[ -]?\d{4})", t):
            phones[pm.group(1).lower()] = pm.group(2)
    d["phones"] = phones
    # address from the structured payload
    addr = ld.get("address") or {}
    if addr.get("streetAddress"):
        bits = [addr["streetAddress"]]
        if addr.get("addressLocality"):
            bits.append(addr["addressLocality"] + ",")
        if addr.get("addressRegion"):
            bits.append(addr["addressRegion"])
        if addr.get("postalCode"):
            bits.append(addr["postalCode"])
        d["address"] = " ".join(bits)
    # reviews embedded in the page's own payload (newest first)
    revs = []
    for r in ld.get("review", []) or []:
        row = {"author": (r.get("author") or {}).get("name"),
               "date": (r.get("datePublished") or "")[:10]}
        rr = r.get("reviewRating") or {}
        row["rating"] = float(rr["ratingValue"]) if rr.get("ratingValue") else None
        body = (r.get("reviewBody") or "").strip()
        row["text"] = body[:1200]
        if row["author"]:
            revs.append(row)
    d["detail_reviews"] = revs[:10]
    return d


def parse_reviews_page(path):
    html = open(path, encoding="utf-8").read()
    t = T(re.sub(r"<script.*?</script>", " ", html, flags=re.S))
    out = {"source_file": os.path.basename(path), "reviews": []}
    mm = re.search(r'href="/dealers/(\d+)/([a-z0-9-]+)/reviews/"', html)
    if mm:
        out["dealer_id"], out["slug"] = int(mm.group(1)), mm.group(2)
    else:
        # the reviews page may not re-render its own dealer link; the capture
        # filename carries it (dealer-<slug>-reviews.html)
        fm = re.match(r"dealer-([a-z0-9-]+)-reviews\.html$", os.path.basename(path))
        if fm:
            out["slug"] = fm.group(1)
        ld0 = autodealer_ld(html) or {}
        if ld0.get("@id", "").lstrip("#").isdigit():
            out["dealer_id"] = int(ld0["@id"].lstrip("#"))
    ld = autodealer_ld(html) or {}
    for r in ld.get("review", []) or []:
        row = {"author": (r.get("author") or {}).get("name"),
               "date": (r.get("datePublished") or "")[:10]}
        rr = r.get("reviewRating") or {}
        row["rating"] = float(rr["ratingValue"]) if rr.get("ratingValue") else None
        body = (r.get("reviewBody") or "").strip()
        row["text"] = body[:1200]
        # DealerRater imports carry extra context in the visible render
        if row["author"]:
            i = t.find(f"By {row['author']} ")
            if i > 0:
                seg = t[i:i + 1600]
                m2 = re.search(r"Worked with: ([A-Za-z .'-]+?)(?:\d|$)", seg)
                if m2:
                    row["worked_with"] = m2.group(1).strip()[:60]
                m2 = re.search(r"(Shopped for a [a-z]+ car|Brought my vehicle in for service)", seg)
                if m2:
                    row["visit_type"] = m2.group(1)
            out["reviews"].append(row)
    return out


def main():
    directory = {}
    pages = []
    review_pages = []
    for fn in sorted(os.listdir(CAP)):
        path = os.path.join(CAP, fn)
        if fn.startswith("dealers-dir") and fn.endswith(".html"):
            directory.update(parse_directory(path))
        elif fn.startswith("dealer-") and fn.endswith("-reviews.html"):
            try:
                review_pages.append(parse_reviews_page(path))
            except Exception as e:
                print(f"[warn] {fn}: {e}")
        elif fn.startswith("dealer-") and fn.endswith(".html") and "dir" not in fn \
                and not fn.endswith("-inv.html"):
            try:
                pages.append(parse_dealer_page(path))
            except Exception as e:
                print(f"[warn] {fn}: {e}")
    with open(os.path.join(OUT, "dealers_raw.json"), "w") as f:
        json.dump({"directory": directory, "pages": pages,
                   "review_pages": review_pages}, f, indent=1)
    print(f"[parse_dealers] directory={len(directory)} pages={len(pages)} "
          f"review_pages={len(review_pages)}")


if __name__ == "__main__":
    main()
