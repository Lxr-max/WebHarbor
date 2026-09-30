#!/usr/bin/env python3
"""Parse captured cars.com research model pages + compare pages.

  research-<slug>.html    -> one model page (trims, expert take, reviews)
  cmp-<a>-vs-<b>.html     -> one side-by-side comparison

Run:  python3 scripts_dev/parse_research.py
"""
import json
import os
import re
from html import unescape

HERE = os.path.dirname(os.path.abspath(__file__))
CAP = os.path.join(HERE, "..", "scraped_data", "captures")
OUT = os.path.join(HERE, "..", "scraped_data")


def T(block):
    return " ".join(unescape(re.sub(r"<[^>]+>", " ", block)).split())


def parse_model_page(path):
    html = open(path, encoding="utf-8").read()
    t = T(re.sub(r"<script.*?</script>", " ", html, flags=re.S))
    out = {"source_file": os.path.basename(path)}
    # make/model/year: the h1 is a year-picker widget on the current pages,
    # so the canonical slug (make-model-year) is the authoritative source
    canon = re.search(r'<link rel="canonical" href="https://www\.cars\.com/research/([a-z0-9_-]+)-(\d{4})/"', html)
    if canon:
        rest = canon.group(1)
        out["slug"] = rest
        out["year"] = int(canon.group(2))
        head, tail = (rest.split("-", 1) + [""])[:2]
        display = {"cr_v": "CR-V", "rav4": "RAV4", "f_150": "F-150",
                   "model_3": "Model 3", "3_series": "3 Series",
                   "silverado_1500": "Silverado 1500", "ioniq_5": "Ioniq 5"}
        out["make"] = head.replace("_", " ").title()
        out["model"] = display.get(tail, tail.replace("_", " ").title()) if tail else ""
    else:
        mm = re.search(r"cars\.com/research/([a-z0-9_-]+)-(\d{4})/", html)
        if mm:
            out["slug"] = mm.group(1)
            out["year"] = int(mm.group(2))
        mm = re.search(r"<h1[^>]*>\s*(\d{4}) ([A-Za-z ]+) ([A-Za-z0-9 -]+?)\s*</h1>", html)
        if mm:
            out["year"], out["make"], out["model"] = int(mm.group(1)), mm.group(2).strip(), mm.group(3).strip()
        else:
            mm = re.search(r"<h1[^>]*>\s*([^<]+?)\s*</h1>", html)
            if mm:
                out["title_text"] = unescape(mm.group(1)).strip()
    # safety rating
    mm = re.search(r"(\d)/5 Safety rating", t)
    if mm:
        out["safety_rating"] = int(mm.group(1))
    # starting price
    mm = re.search(r"\$(\d[\d,]*) Starting price", t)
    if mm:
        out["starting_price"] = int(mm.group(1).replace(",", ""))
    # trims carousel
    trims = []
    for m in re.finditer(r'<div class="compare-competitors-year-or-trim[^"]*"[^>]*>\s*([^<]+?)\s*</div>.*?Starts at </div>\s*<div class="vehicle-price-value">\$([\d,]+)</div>(.*?)(?=<li>|</ul>)', html, re.S):
        name, price, seg = m.group(1).strip(), int(m.group(2).replace(",", "")), m.group(3)
        row = {"name": name, "price": f"${price:,}"}
        for dm in re.finditer(r'<dt class="compare-competitors-data-point-label">\s*(.*?)\s*</dt>\s*<dd class="compare-competitors-data-point-value">\s*(.*?)\s*</dd>', seg, re.S):
            label, value = T(dm.group(1)), T(dm.group(2))
            key = {"MPG": "mpg", "Seat capacity": "seats", "Engine": "engine",
                   "Drivetrain": "drivetrain"}.get(label)
            if key:
                row[key] = value
        if not name.isdigit():
            trims.append(row)
    out["trims"] = trims
    # expert's take (short summary only — the upstream byline + lead)
    mm = re.search(r"Our Expert's Take By ([A-Z][A-Za-z.]+(?: [A-Z][A-Za-z.]+){0,2}) (.+?)(?:Read full review|Shop the|$)", t)
    if mm:
        author = mm.group(1).strip()
        take = mm.group(2).strip()
        if author.endswith(" The"):
            author = author[: -len(" The")]
            take = "The " + take
        out["expert_author"] = author
        out["expert_take"] = take[:600]
    # notable features
    i = t.find("Notable features")
    if i > 0:
        seg = t[i:i + 700]
        cut = seg.find("The good &")
        seg = seg[:cut] if cut > 0 else seg
        feats = [x.strip() for x in seg.replace("Notable features", "", 1).split(".") if len(x.strip()) > 8]
        out["notable_features"] = feats[:10]
    # good/bad: HTML lists (each point its own <li>)
    goods = re.findall(r'good-bad-attribute-wrapper-good.*?good-bad-attribute">([^<]+)<', html, re.S)
    bads = re.findall(r'good-bad-attribute-wrapper-bad.*?good-bad-attribute">([^<]+)<', html, re.S)
    if goods:
        out["good_points"] = [x.strip() for x in goods if x.strip()][:8]
    if bads:
        out["bad_points"] = [x.strip() for x in bads if x.strip()][:8]

    # consumer reviews
    i = t.find("Consumer reviews")
    if i > 0:
        seg = t[i:i + 2500]
        mm = re.search(r"(\d+)% of drivers recommend", seg)
        if mm:
            out["consumer_recommend_pct"] = int(mm.group(1))
        mm = re.search(r"(\d\.\d) / 5 (\d\.\d) out of 5 Based on (\d+) reviews", seg)
        if mm:
            out["consumer_rating"] = float(mm.group(1))
            out["consumer_review_count"] = int(mm.group(3))
        cats = dict(re.findall(r"(Comfort|Interior|Performance|Value|Exterior|Reliability) (\d\.\d) out of 5", seg))
        if cats:
            out["consumer_categories"] = {k: float(v) for k, v in cats.items()}
        revs = re.findall(r"By ([A-Za-z0-9_ -]+?) from ([A-Za-z, ]+?) (Owns this car|Leased|Purchased a New car|Purchased a Used car) (\d\d/\d\d/\d\d) (.+?)(?=By [A-Za-z0-9_ -]+ from|$)", seg)
        out["consumer_reviews"] = [
            {"author": a.strip(), "from": b.strip(), "ownership": c, "date": d, "text": e.strip()[:900]}
            for a, b, c, d, e in revs
        ][:6]
    # photos
    out["photos"] = sorted(set(re.findall(r'(https://platform\.cstatic-images\.com/[^"\\\s]+?\.jpg)', html)))[:20]
    return out


def parse_compare_page(path):
    html = open(path, encoding="utf-8").read()
    t = T(re.sub(r"<script.*?</script>", " ", html, flags=re.S))
    out = {"source_file": os.path.basename(path)}
    mm = re.search(r"<h1[^>]*>\s*([A-Za-z0-9 .-]+?) vs\. ([A-Za-z0-9 .-]+?)\s*</h1>", html)
    if mm:
        out["title_a"], out["title_b"] = mm.group(1).strip(), mm.group(2).strip()
    mm = re.search(r'canonical" href="https://www.cars.com/research/compare/([^"]+)/"', html)
    if mm:
        out["slug"] = mm.group(1).strip("/")
    rows = {}
    # spec table rows: each <tr> holds paired <td class="data-point-td"> cells
    # (column A value, column B value, empty add-column, "-" diff column).
    for tr in re.findall(r"<tr>(.*?)</tr>", html, re.S):
        cells = []
        for td in re.findall(r'<td class="data-point-td[^>]*?>(.*?)</td>', tr, re.S):
            vm = re.search(r'<div class="data-point">\s*(.*?)\s*(?:<br>)?\s*</div>', td, re.S)
            hm = re.search(r'<div class="data-heading">\s*(.*?)\s*</div>', td, re.S)
            if vm and hm:
                cells.append((T(hm.group(1)), T(vm.group(1))))
        if len(cells) >= 2:
            label_a, val_a = cells[0]
            label_b, val_b = cells[1]
            if label_a == label_b and val_a not in ("-",):
                rows.setdefault(label_a, [val_a, val_b])
    out["rows"] = rows
    # the two comparison columns: "2026 Honda Civic $24,695 ..." + the trim-select buttons
    cols = []
    for cm in re.finditer(r"(\d{4}) ([A-Za-z0-9 .&-]+?) \$([\d,]+) (.*?) See all results", t):
        cols.append({
            "year": int(cm.group(1)),
            "name": cm.group(2).strip(),
            "price": int(cm.group(3).replace(",", "")),
        })
    trim_buttons = re.findall(r'phx-value-vehicle="vehicle_(\d+)".*?<div>([^<]+)</div>', html, re.S)
    by_vehicle = {}
    for veh, trim in trim_buttons:
        by_vehicle.setdefault(veh, [])
        if trim not in by_vehicle[veh]:
            by_vehicle[veh].append(trim.strip())
    for i, col in enumerate(cols[:2], start=1):
        col["trims"] = by_vehicle.get(str(i), [])[:14]
    out["columns"] = cols[:2]
    # photos of each side
    out["photos"] = sorted(set(re.findall(r'(https://platform\.cstatic-images\.com/[^"\\\s]+?\.(?:jpe?g|png|webp))', html)))[:8]
    return out


def main():
    models, compares = [], []
    for fn in sorted(os.listdir(CAP)):
        path = os.path.join(CAP, fn)
        if fn.startswith("research-") and fn.endswith(".html"):
            try:
                models.append(parse_model_page(path))
            except Exception as e:
                print(f"[warn] {fn}: {e}")
        elif fn.startswith("cmp-") and fn.endswith(".html"):
            try:
                compares.append(parse_compare_page(path))
            except Exception as e:
                print(f"[warn] {fn}: {e}")
    with open(os.path.join(OUT, "research_raw.json"), "w") as f:
        json.dump({"models": models, "compares": compares}, f, indent=1)
    print(f"[parse_research] models={len(models)} compares={len(compares)}")


if __name__ == "__main__":
    main()
