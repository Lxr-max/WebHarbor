#!/usr/bin/env python3
"""Parse captured cars.com vehicle-detail pages into scraped_data/vd_pages.json.

Every field is extracted from the real upstream render in
scraped_data/captures/vd-*.html. Run: python3 scripts_dev/parse_vd.py
"""
import json
import os
import re
from html import unescape

HERE = os.path.dirname(os.path.abspath(__file__))
CAP = os.path.join(HERE, "..", "scraped_data", "captures")
OUT = os.path.join(HERE, "..", "scraped_data")


def T(block):
    t = re.sub(r"<[^>]+>", " ", block)
    return " ".join(unescape(t).split())


def parse_vd(path):
    html = open(path, encoding="utf-8").read()
    out = {"source_file": os.path.basename(path)}
    t = T(re.sub(r"<script.*?</script>", " ", html, flags=re.S))
    # ids
    m = re.search(r'href="/vehicledetail/([0-9a-f-]{36})/', html)
    if m:
        out["listing_id"] = m.group(1)
    else:
        m = re.search(r'"listing_id":"([0-9a-f-]{36})"', html)
        if m:
            out["listing_id"] = m.group(1)
    # title / price / mileage headline
    m = re.search(r"<h1[^>]*>\s*([^<]+?)\s*</h1>", html)
    if m:
        out["title"] = unescape(m.group(1)).strip()
    m = re.search(r"\$(\d{1,3}(?:,\d{3})+|\d{3,})\s*</", html[html.find("<h1"):html.find("<h1")+3000])
    if m:
        out["price_display"] = "$" + m.group(1)
    m = re.search(r"Mileage ([\d,]+) mi", t)
    if m:
        out["mileage_display"] = m.group(1)
    # photos
    out["photos"] = sorted(set(re.findall(r'(https://platform\.cstatic-images\.com/[^"\\\s]+?\.jpg)', html)))
    # price breakdown
    i = html.find("Vehicle price breakdown")
    if i > 0:
        seg = html[i:i + 5000]
        rows = re.findall(r'price-stack-display__description">\s*<p>\s*(?:<span[^>]*>)?\s*([^<]+?)\s*(?:</span>)?\s*</p>\s*</th>\s*<td class="price-stack-display__amount">\s*<p>\s*([^<]+?)\s*</p>', seg)
        out["price_breakdown"] = [[unescape(a).strip(), unescape(b).strip()] for a, b in rows][:8]
    # deal rating
    m = re.search(r"data-badge-value=\"(Great Deal|Good Deal|Fair Deal)\"", html)
    if m:
        out["deal_badge"] = m.group(1)
    m = re.search(r"The good deal range for this vehicle is between \$([\d,]+) and \$([\d,]+)", t)
    if m:
        out["good_deal_range"] = [m.group(1), m.group(2)]
    # price history
    i = t.find("Price history")
    if i > 0:
        seg = t[i:i + 500]
        m = re.search(r"Price history \$(?:[\d,]+)? ?(?:below original listed price)? Date Change Price((?: \d\d/\d\d/\d\d [A-Za-z$0-9\-– ]+?)+?)(?:Total price|Contact|$)", seg)
        seg2 = seg[seg.find("Date Change Price"):]
        rows = re.findall(r"(\d\d/\d\d/\d\d)\s+(\$[\d,]+|Listed|Price (?:dropped|increased)[^$]*?)\s*(\$[\d,]+)", seg2)
        out["price_history"] = [
            {"date": a, "change": b.strip(), "price": c} for a, b, c in rows
        ][:8]
    # specs summary
    i = t.find("VIN:")
    if i > 0:
        seg = t[i:i + 600]
        out["specs_summary"] = seg[:400]
        m = re.search(r"VIN: ([A-Z0-9]+) / Stock #: ([A-Z0-9]+)", seg)
        if m:
            out["vin"], out["stock_number"] = m.group(1), m.group(2)
        m = re.search(r"([A-Za-z ]+?) exterior color ([A-Za-z ]+?) interior color", seg)
        if m:
            out["exterior_color"] = m.group(1).strip()
            out["interior_color"] = m.group(2).strip()
        m = re.search(r"([A-Za-z]+) fuel type (.+?) engine", seg)
        if m:
            out["fuel_type"] = m.group(1).strip()
            out["engine"] = m.group(2).strip()
        m = re.search(r"(\d+-\d+) mpg", seg)
        if m:
            out["mpg"] = m.group(1)
        m = re.search(r"([A-Za-z-]+) drivetrain", seg)
        if m:
            out["drivetrain"] = m.group(1).strip()
        m = re.search(r"([A-Za-z0-9-]+) transmission", seg)
        if m:
            out["transmission"] = m.group(1).strip()
    # feature groups
    feats = {}
    for m in re.finditer(r'<h3 class="features-spec-heading">\s*<span class="features-spec-heading-icon">\s*'
                         r'<fuse-svg[^>]*>\s*</fuse-svg>\s*</span>\s*(\w+)\s*</h3>\s*'
                         r'<fuse-list[^>]*>\s*<ul>(.*?)</ul>', html, re.S):
        group, items_html = m.group(1), m.group(2)
        items = [x.strip() for x in re.findall(r'<li[^>]*>\s*([^<]{3,50}?)\s*</li>', items_html)]
        if items:
            feats[group] = items
    out["features"] = feats
    # seller's notes
    i = t.find("Seller's notes")
    if i > 0:
        txt = t[i:i + 4000]
        txt = txt.replace("Seller's notes", "", 1).strip()
        cut = txt.find("Confirm Availability")
        if cut > 0:
            txt = txt[:cut].strip()
        out["seller_notes"] = txt[:2400]
    # CPO program
    i = html.find("Manufacturer Certified Pre-Owned")
    if i > 0:
        seg = t[t.find("Manufacturer Certified Pre-Owned"):][:900]
        out["cpo_program"] = seg[:700]
    # history report
    m = re.search(r"Owner (\d+) Accidents (\d+) Title ([A-Za-z]+)", t)
    if m:
        out["history"] = {"owners": int(m.group(1)), "accidents": int(m.group(2)), "title": m.group(3)}
    # payment estimator defaults
    m = re.search(r"\$(\d+)/mo\*", html)
    if m:
        out["est_monthly"] = int(m.group(1))
    m = re.search(r"Based on ([\d.]+)% APR", t)
    if m:
        out["apr"] = m.group(1)
    m = re.search(r"Estimated sales tax \(([\d.]+)%\) \$([\d,]+)", t)
    if m:
        out["sales_tax_pct"] = m.group(1)
        out["sales_tax_amount"] = m.group(2)
    m = re.search(r"Total loan amount \$([\d,]+) Total interest paid \$([\d,]+)", t)
    if m:
        out["total_loan"] = m.group(1)
        out["total_interest"] = m.group(2)
    # seller info (dealer)
    i = t.find("Seller's info")
    if i > 0:
        seg = t[i:i + 900]
        m = re.search(r"Seller's info ([A-Za-z0-9&'. -]+?) (\d[\d,]*)? reviews", seg)
        if m:
            out["dealer_name"] = m.group(1).strip()
            out["dealer_reviews"] = m.group(2)
        m = re.search(r"(\d[\d,]*) reviews", seg)
        if m:
            out["dealer_review_count"] = m.group(1)
        m = re.search(r"reviews ([A-Za-z]+ [A-Za-z]* ?[A-Za-z]* ?Open|reviews Open)", seg)
        m2 = re.search(r"(\d+) reviews", seg)
        # hours
        hours = re.findall(r"(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday) (\d{1,2}(?::\d{2})?[ap]m\s*-\s*\d{1,2}(?::\d{2})?[ap]m|Closed)", seg)
        if hours:
            out["dealer_hours"] = [{"day": d, "hours": h} for d, h in hours]
        addr_seg = seg.split("Visit dealership website")[0]
        m = re.findall(r"\d{1,5} [A-Za-z][A-Za-z0-9 .&'/-]{0,60}, [A-Za-z .]+?, [A-Z]{2} \d{5}", addr_seg)
        if m:
            out["dealer_address"] = m[-1].strip()
        m = re.search(r"Call Directly to (\d[\d-]+)", t)
        if m:
            out["dealer_phone"] = m.group(1)
    # dealer rating stars
    m = re.search(r"Seller's info.*?(\d\.\d)\s*<", html[html.find("Seller's info"):html.find("Seller's info") + 3000], re.S)
    # consumer reviews
    i = t.find("Consumer reviews")
    if i > 0:
        seg = t[i:i + 3000]
        m = re.search(r"(\d+)% of drivers recommend", seg)
        if m:
            out["consumer_recommend_pct"] = int(m.group(1))
        m = re.search(r"(\d+\.\d+) / 5 Based on (\d+) reviews", seg)
        if m:
            out["consumer_rating"] = float(m.group(1))
            out["consumer_review_count"] = int(m.group(2))
        cats = dict(re.findall(r"(Comfort|Interior|Performance|Value|Exterior|Reliability) (\d\.\d)", seg))
        if cats:
            out["consumer_categories"] = {k: float(v) for k, v in cats.items()}
        revs = re.findall(r"By ([A-Za-z0-9_ -]+?) from ([A-Za-z, ]+?) (Owns this car|Leased|Purchased a New car|Purchased a Used car)? ?(\d\d/\d\d/\d\d)", seg)
        out["consumer_reviews"] = [{"author": a.strip(), "from": b.strip(), "ownership": (c or "").strip(), "date": d} for a, b, c, d in revs][:6]
    # similar cars
    i = t.find("Similar cars at this dealership")
    if i > 0:
        seg = t[i:i + 900]
        sims = re.findall(r"\$(\d[\d,]*) (Used|Certified|New) (\d{4}) ([A-Za-z0-9 -]+?) ([\d,]+) mi", seg)
        out["similar_at_dealer"] = [
            {"price": int(a.replace(",", "")), "stock": b, "title": f"{c} {d}".strip(), "mileage": e}
            for a, b, c, d, e in sims
        ][:8]
    return out


def main():
    pages = []
    for fn in sorted(os.listdir(CAP)):
        if fn.startswith("vd-") and fn.endswith(".html"):
            try:
                pages.append(parse_vd(os.path.join(CAP, fn)))
            except Exception as e:
                print(f"[warn] {fn}: {e}")
    with open(os.path.join(OUT, "vd_pages.json"), "w") as f:
        json.dump(pages, f, indent=1)
    print(f"[parse_vd] {len(pages)} detail pages")


if __name__ == "__main__":
    main()
