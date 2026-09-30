#!/usr/bin/env python3
"""Extract tracked source_data snapshots from the scraped_data captures.

Reads scraped_data/captures/*.html (raw as-rendered upstream pages captured
with the headful-Chromium harness) and writes the trimmed, tracked
source_data/*.json snapshots the mirror's seed is built from:

  products.json          - full PDP payloads for every mirrored product
  reviews.json           - the Apollo-state reviews per product
  categories.json        - the six mirrored /cat/ listing pages (grid order,
                           upstream facet trees, sort options, totals)
  brands.json            - brand landing pages (grid order, upstream totals)
  brand_directory.json   - the shop-all-brands directory (letter groups)
  searches.json          - captured search snapshots (term, total, order)
  home.json              - home campaign blocks + nav + stats
  info_pages.json        - shipping / returns / loyalty copy

Trim policy (declared in provenance.json): each mirrored category/brand/
search grid keeps the upstream page-1 order but only the products whose PDP
was captured (12 per grid); upstream totalCounts, facet counts and sort
option lists remain the upstream values.
"""
import json
import os
import re
import sys
from collections import OrderedDict

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.dirname(HERE)
CAP = os.path.join(SITE, "scraped_data", "captures")
OUT = os.path.join(SITE, "source_data")
os.makedirs(OUT, exist_ok=True)

GRID_PER_CATEGORY = 12
GRID_PER_BRAND = 10
GRID_PER_SEARCH = 10


def next_data(key):
    path = os.path.join(CAP, f"{key}.html")
    html = open(path, encoding="utf-8").read()
    m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
                  html, re.S)
    if not m:
        raise SystemExit(f"no __NEXT_DATA__ in {path}")
    return json.loads(m.group(1))


def plp(d, ctx):
    return d["props"]["pageProps"]["plpData"]["data"][ctx]


def node_small(n):
    return {
        "id": n["id"], "name": n["name"], "url": n["url"],
        "brand": n["brand"]["name"],
        "stock": n.get("stockStatus"),
        "min_sale": n["aggregates"]["minSalePrice"],
        "min_list": n["aggregates"]["minListPrice"],
        "max_sale": n["aggregates"]["maxSalePrice"],
        "colors": [{"colorId": c["colorId"], "name": c["name"],
                    "tile": c["tileImage"], "pli": c["pliImage"]}
                   for c in n.get("colors") or []],
        "rating": n["reviewAggregates"]["averageRating"],
        "reviews": n["reviewAggregates"]["totalReviews"],
        "flags": {k: v for k, v in (n.get("flags") or {}).items()
                  if k != "__typename"},
    }


def facets_trim(facets):
    out = []
    for f in facets:
        def walk(fl, depth=0):
            row = {"name": fl["name"], "value": fl.get("value"),
                   "count": fl.get("count"), "url": fl.get("url")}
            if fl.get("children"):
                row["children"] = [walk(c, depth + 1) for c in fl["children"]]
            return row
        out.append({"name": f["name"], "field": f.get("field"),
                    "filters": [walk(fl) for fl in f.get("filters") or []]})
    return out


def sort_trim(sort):
    return [{"name": s["name"], "value": s["value"],
             "selected": bool(s.get("isSelected"))} for s in sort]


def extract_products():
    products = OrderedDict()
    reviews = {}
    import glob
    for path in sorted(glob.glob(os.path.join(CAP, "pdp_*.html"))):
        html = open(path, encoding="utf-8").read()
        m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
                      html, re.S)
        if not m:
            print("skip (no data):", os.path.basename(path))
            continue
        d = json.loads(m.group(1))
        pp = d["props"]["pageProps"]
        if pp.get("type") != "pdp" or not pp.get("product"):
            print("skip (type):", os.path.basename(path), pp.get("type"))
            continue
        p = pp["product"]
        pid = p["id"]
        skus = []
        for idx, s in enumerate(p.get("skus") or []):
            size_obj = s.get("size") or {}
            size_name = size_obj.get("name")
            if not size_name:
                # some upstream skus carry the size only in their title
                t = (s.get("title") or "")
                size_name = t.split(",")[-1].strip() if "," in t else "One Size"
            img_path = (s.get("image") or {}).get("url") or ""
            color_key = s["color"].get("colorId")
            if not color_key and img_path:
                # the sku image filename carries the upstream color key
                color_key = img_path.rsplit("/", 1)[-1].split("?")[0]
                color_key = color_key.rsplit(".", 1)[0]
            if not color_key:
                color_key = s["color"]["name"]
            skus.append({
                "id": s["id"],
                "color": s["color"]["name"], "color_family": s["color"].get("family"),
                "color_id": color_key,
                "size": size_name, "size_scale": size_obj.get("scale"),
                "size_pos": size_obj.get("position") if size_obj.get("position") is not None else idx,
                "list_price": s.get("listPrice"), "sale_price": s.get("salePrice"),
                "discount": s.get("discountPercent"), "on_sale": bool(s.get("onSale")),
                "status": s.get("availability", {}).get("status"),
                "stock": s.get("availability", {}).get("stockLevel"),
                "image": s.get("image", {}).get("url"),
                "is_past_season": bool(s.get("isPastSeason")),
                "season": s.get("season"), "year": s.get("year"),
            })
        dib = p.get("detailImagesByColor") or {}
        gallery = {}
        default_color = p.get("defaultDetailImagesColor")
        if not default_color and skus:
            first = skus[0].get("color", "")
            # upstream default gallery color key (first sku color family key)
            default_color = next((s.get("color_id") for s in p.get("skus") or []
                                  if s.get("color") == first), None)
        for color, shots in dib.items():
            keep_n = 3 if (not default_color or color == default_color) else 1
            keep = []
            for shot in shots[:keep_n]:
                keep.append({"1200": shot.get("twelveHundredImg"),
                             "large": shot.get("largeImg"),
                             "title": shot.get("title")})
            if keep:
                gallery[color] = keep
        row = {
            "id": pid,
            "slug": p["url"].strip("/"),
            "title": p["title"],
            "brand": p["brand"]["name"], "brand_slug": p["brand"]["url"].strip("/"),
            "brand_logo": p["brand"].get("logo"),
            "description": p.get("description"),
            "bottom_line": p.get("bottomLine"),
            "bullets": p.get("bulletPoints") or [],
            "features": [{"name": f["name"], "value": f["value"]}
                         for f in (p.get("features") or []) if "name" in f],
            "attributes": [a for a in (p.get("attributes") or []) if isinstance(a, dict)],
            "breadcrumbs": [b for b in (p.get("breadcrumbs") or [])],
            "min_list": p.get("minListPrice"), "max_list": p.get("maxListPrice"),
            "min_sale": p.get("minSalePrice"), "max_sale": p.get("maxSalePrice"),
            "min_discount": p.get("minDiscountPercent"),
            "max_discount": p.get("maxDiscountPercent"),
            "variations_on_sale": p.get("variationsOnSale"),
            "total_variations": p.get("totalVariations"),
            "is_gearhead_pick": bool(p.get("isGearheadPick")),
            "is_new_arrival": "newest" in json.dumps(p.get("flags") or {}),
            "is_past_season": bool(p.get("isPastSeason")),
            "is_exclusive": bool(p.get("isExclusive")),
            "hsa_fsa": bool(p.get("hsaFsaEligible")),
            "free_shipping": bool(p.get("isFreeShippingCategory")),
            "in_stock": bool(p.get("isInStock")),
            "availability": p.get("availabilityStatus"),
            "review_count": (p.get("customerReviews") or {}).get("count"),
            "review_avg": (p.get("customerReviews") or {}).get("roundedAverage"),
            "skus": skus,
            "gallery": gallery,
            "default_color": p.get("defaultDetailImagesColor"),
            "sizing_chart": p.get("sizingChart"),
        }
        products[pid] = row

        # reviews + questions from Apollo state
        ap = pp.get("__APOLLO_STATE__") or {}
        revs, qs = [], []
        aggregates = None
        rq = ap.get("ROOT_QUERY", {}) if isinstance(ap.get("ROOT_QUERY"), dict) else {}
        for k, v in rq.items():
            if isinstance(v, dict) and k.startswith("reviews("):
                ag = v.get("aggregates") or {}
                aggregates = {
                    "totalCount": v.get("totalCount"),
                    "overallRating": ag.get("overallRating"),
                    "ratingDetails": [
                        {kk: rr.get(kk) for kk in ("count", "percentage", "rating")}
                        for rr in (ag.get("ratingDetails") or [])],
                    "productFit": ag.get("productFit"),
                }
                break
        for k, v in ap.items():
            if not isinstance(v, dict):
                continue
            if v.get("__typename") == "Review" and v.get("isVisible"):
                photos = [u for u in (v.get("photos") or []) if u]
                synd = v.get("syndicationSource") or {}
                revs.append({
                    "id": v["id"], "title": v.get("title"),
                    "text": v.get("text"), "rating": v.get("rating"),
                    "created": v.get("creationTime"),
                    "author": (v.get("author") or {}).get("name"),
                    "author_gearhead": (v.get("author") or {}).get("isGearhead"),
                    "author_employee": (v.get("author") or {}).get("isEmployee"),
                    "familiarity": (v.get("attributes") or {}).get("familiarity"),
                    "fit": (v.get("attributes") or {}).get("fit"),
                    "size_purchased": (v.get("attributes") or {}).get("sizePurchased"),
                    "photos": photos,
                    "syndicated": bool(v.get("isSyndicated")),
                    "syndication_source": synd.get("name"),
                    "helpful": None,
                })
            elif v.get("__typename") == "Question":
                qs.append({"id": v.get("id"), "text": v.get("text"),
                           "created": v.get("creationTime")})
            elif v.get("__typename") == "Answer":
                pass
        # answers keyed by question (Question.edges hold __ref to answers)
        ans_by_q = {}
        for k, v in ap.items():
            if isinstance(v, dict) and v.get("__typename") == "Question":
                qid = v.get("id")
                edges = ((v.get("answers") or {}).get("edges")) or []
                refs = [e.get("node", {}).get("__ref") for e in edges]
                ans_by_q.setdefault(qid, []).extend(
                    [r.split(":", 1)[1] for r in refs if r])
        for q in qs:
            q["answers"] = [
                {"id": aid,
                 "text": (ap.get(f"Answer:{aid}") or {}).get("text"),
                 "author": ((ap.get(f"Answer:{aid}") or {}).get("author") or {}).get("name"),
                 "author_gearhead": ((ap.get(f"Answer:{aid}") or {}).get("author") or {}).get("isGearhead"),
                 "created": (ap.get(f"Answer:{aid}") or {}).get("creationTime")}
                for aid in ans_by_q.get(q.get("id"), [])]
        if revs or qs or aggregates:
            reviews[pid] = {"reviews": revs, "questions": qs,
                            "aggregates": aggregates}
    return products, reviews


def extract_categories(products):
    cats = []
    for key, name in [("cat_hike_camp", "Hike & Camp"), ("cat_ski", "Ski"),
                      ("cat_mens_clothing", "Men's Clothing"),
                      ("cat_womens_clothing", "Women's Clothing"),
                      ("cat_climb", "Climb"), ("cat_bike", "Bike")]:
        d = next_data(key)
        c = plp(d, "category")
        grid = []
        for e in c["edges"]:
            n = e["node"]
            if n["id"] in products:
                grid.append(n["id"])
            if len(grid) >= GRID_PER_CATEGORY:
                break
        cats.append({
            "slug": key.replace("cat_", "", 1).replace("_", "-"),
            "name": name,
            "upstream_total": c["totalCount"],
            "facets": facets_trim(c.get("facets") or []),
            "sort": sort_trim(c.get("sort") or []),
            "products": grid,
        })
    return cats


def extract_brands(products):
    brands = []
    for key in ["brand_patagonia", "brand_north_face", "brand_outdoor_research",
                "brand_black_diamond", "brand_salomon", "brand_smartwool",
                "brand_fjallraven"]:
        import os
        if not os.path.exists(os.path.join(CAP, f"{key}.html")):
            continue
        d = next_data(key)
        b = plp(d, "brand")
        grid = []
        for e in b["edges"]:
            n = e["node"]
            if n["id"] in products:
                grid.append(n["id"])
            if len(grid) >= GRID_PER_BRAND:
                break
        ctx = b["brand"]
        brands.append({
            "slug": ctx["url"].strip("/").split("/")[-1],
            "name": ctx["name"], "title": ctx.get("title"),
            "description": ctx.get("description"),
            "upstream_total": b["totalCount"],
            "facets": facets_trim(b.get("facets") or [])[:6],
            "sort": sort_trim(b.get("sort") or []),
            "products": grid,
        })
    return brands


def extract_searches(products):
    searches = []
    for key, term in [("search_tent", "tent"),
                      ("search_sleeping_bag", "sleeping bag"),
                      ("search_down_jacket", "down jacket"),
                      ("search_headlamp", "headlamp"),
                      ("search_ski_boots", "ski boots"),
                      ("search_climbing_rope", "climbing rope")]:
        import os
        if not os.path.exists(os.path.join(CAP, f"{key}.html")):
            continue
        d = next_data(key)
        s = plp(d, "search")
        grid = []
        for e in s["edges"]:
            n = e["node"]
            if n["id"] in products:
                grid.append(n["id"])
            if len(grid) >= GRID_PER_SEARCH:
                break
        searches.append({
            "term": term, "upstream_total": s["totalCount"],
            "corrected": s.get("correctedTerm"),
            "sort": sort_trim(s.get("sort") or []),
            "products": grid,
        })
    return searches


def _doc_paras(doc):
    """Split a ContentStack doc into (heading, [paragraphs])."""
    paras = []
    for node in (doc.get("children") or []):
        if node.get("type") == "h2":
            t = _doc_text({"children": node.get("children") or []})
            if t.strip():
                paras.append(("#", t.strip()))
        elif node.get("type") in ("p", "ul", "ol"):
            t = _doc_text({"children": node.get("children") or []})
            if t.strip():
                paras.append(("", t.strip()))
    return paras


def extract_info_pages():
    pages = []
    for key, slug, title in [
            ("info_shipping_policy", "shipping-policy", "Shipping Policy"),
            ("info_return_policy", "return-policy", "100% Guaranteed Returns"),
            ("info_loyalty", "loyalty", "Summit Club Loyalty Program")]:
        d = next_data(key)
        ip = d["props"]["pageProps"]["cmsData"]["infoPage"]
        meta = ip.get("metadata") or {}
        sections, current = [], {"heading": None, "paragraphs": []}
        for comp in ip.get("components") or []:
            if comp.get("__typename") in ("Text", "RichText"):
                for kind, t in _doc_paras(comp.get("text") or {}):
                    if kind == "#":
                        if current["heading"] or current["paragraphs"]:
                            sections.append(current)
                        current = {"heading": t, "paragraphs": []}
                    else:
                        current["paragraphs"].append(t)
            elif comp.get("__typename") == "Faq":
                if current["heading"] or current["paragraphs"]:
                    sections.append(current)
                current = {"heading": None, "paragraphs": []}
                for qa in comp.get("faqs") or []:
                    q = _doc_text(qa.get("question") or {})
                    a = _doc_text(qa.get("answer") or {})
                    if q.strip():
                        sections.append({"heading": q.strip(),
                                         "paragraphs": [a.strip()] if a.strip() else []})
        if current["heading"] or current["paragraphs"]:
            sections.append(current)
        pages.append({"slug": slug, "title": (meta.get("title") or title).strip(),
                      "sections": sections})
    return {"pages": pages}


def extract_brand_directory():
    html = open(os.path.join(CAP, "brands_all.html"), encoding="utf-8").read()
    # letter sections
    groups = OrderedDict()
    for m in re.finditer(
            r'<h2[^>]*>([#A-Z])</h2>(.*?)(?=<h2[^>]*>[#A-Z]</h2>|$)', html, re.S):
        letter = m.group(1)
        block = m.group(2)
        names = re.findall(
            r'<a[^>]+href="(/brand/[a-z0-9%\-\.]+)"[^>]*>([^<]+)</a>', block)
        seen = set()
        rows = []
        for slug, nm in names:
            if slug in seen:
                continue
            seen.add(slug)
            rows.append({"slug": slug, "name": nm.strip()})
        if rows:
            groups[letter] = rows
    return {"groups": groups}


def _doc_text(doc):
    """Flatten a ContentStack rich-text doc to plain text."""
    out = []
    def walk(o):
        if isinstance(o, dict):
            if "text" in o and isinstance(o["text"], str):
                out.append(o["text"])
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(doc)
    return " ".join(t for t in out if t.strip())


def _card(c):
    img = c.get("image") or {}
    return {
        "text": _doc_text(c.get("text") or {}),
        "image": img.get("url"),
        "alt": img.get("alt"),
        "link": c.get("link"),
        "layout": c.get("cardLayout"),
    }


def extract_home():
    d = next_data("home")
    pp = d["props"]["pageProps"]
    cms = pp.get("cmsData") or {}
    hp = cms.get("homePage") or {}
    meta = hp.get("metadata") or {}
    announcements = []
    sections = []
    for comp in hp.get("components") or []:
        t = comp.get("__typename")
        if t == "StandaloneItems":
            for it in comp.get("items") or []:
                if it.get("__typename") == "TextBanner":
                    announcements.append({
                        "text": _doc_text(it.get("contents") or []),
                        "link": it.get("link"),
                        "bg": it.get("backgroundColor"),
                    })
        elif t == "Carousel":
            cards = [_card(c) for c in comp.get("content") or []
                     if c.get("__typename") == "Card"]
            if cards:
                sections.append({"kind": "carousel", "cards": cards})
        elif t == "Grid":
            cards = [_card(c) for c in comp.get("content") or []
                     if c.get("__typename") == "Card"]
            if cards:
                sections.append({"kind": "grid", "cards": cards})
    return {
        "title": meta.get("title"),
        "description": meta.get("description"),
        "announcements": announcements,
        "sections": sections,
        "modifiedAt": hp.get("modifiedAt"),
    }


def main():
    products, reviews = extract_products()
    print("products:", len(products), "| with reviews:", len(reviews))
    cats = extract_categories(products)
    brands = extract_brands(products)
    searches = extract_searches(products)
    missing_grid = []
    for c in cats:
        if len(c["products"]) < GRID_PER_CATEGORY:
            missing_grid.append((c["slug"], len(c["products"])))
    for b in brands:
        if len(b["products"]) < GRID_PER_BRAND:
            missing_grid.append((b["slug"], len(b["products"])))
    print("grids short of target:", missing_grid)

    json.dump({"products": list(products.values())},
              open(os.path.join(OUT, "products.json"), "w"), indent=1)
    json.dump(reviews, open(os.path.join(OUT, "reviews.json"), "w"), indent=1)
    json.dump({"categories": cats}, open(os.path.join(OUT, "categories.json"), "w"), indent=1)
    json.dump({"brands": brands}, open(os.path.join(OUT, "brands.json"), "w"), indent=1)
    json.dump({"searches": searches}, open(os.path.join(OUT, "searches.json"), "w"), indent=1)
    json.dump(extract_brand_directory(),
              open(os.path.join(OUT, "brand_directory.json"), "w"), indent=1)
    json.dump(extract_home(), open(os.path.join(OUT, "home.json"), "w"), indent=1)
    json.dump(extract_info_pages(),
              open(os.path.join(OUT, "info_pages.json"), "w"), indent=1)
    print("wrote source_data to", OUT)


if __name__ == "__main__":
    main()
