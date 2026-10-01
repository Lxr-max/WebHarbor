#!/usr/bin/env python3
"""Derive the tracked source_data/*.json snapshots from the raw captures.

Byte-reproducible: no wall clock, no RNG, stable ordering everywhere. The
output is committed and the seed DB is built from it at image build time.
"""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
RAW = BASE / "scraped_data"
OUT = BASE / "source_data"
OUT.mkdir(parents=True, exist_ok=True)

CATEGORIES = [
    ("01010000", "smartphones", "Smartphones", "/us/smartphones/"),
    ("01020000", "tablets", "Tablets", "/us/tablets/"),
    ("01030000", "watches", "Watches", "/us/watches/"),
    ("01040000", "audio", "Audio", "/us/audio-sound/"),
    ("01050000", "mobile-accessories", "Mobile Accessories", "/us/mobile-accessories/"),
    ("04010000", "tvs", "TVs", "/us/tvs/"),
    ("08010000", "laundry", "Laundry", "/us/home-appliances/laundry/"),
    ("08030000", "refrigerators", "Refrigerators", "/us/home-appliances/refrigerators/"),
]

# pf filter name -> normalized facet key
FACET_MAP = {
    "Mobile series name": "series",
    "Model Family": "family",
    "Storage Size": "storage",
    "Price Range": "price_range",
    "Price": "price_range",
    "Display Size": "display_size",
    "Diagonal Screen Size": "screen_size",
    "Key Features": "features",
    "Key category features": "features",
    "Features": "features",
    "Carrier": "carrier",
    "Camera Resolution": "camera",
    "Screen Size": "screen_size",
    "Capacity": "capacity",
    "Size \u2013 Width and Capacity": "capacity",
    "Type": "type",
    "Technology & Type": "type",
    "Accessories Type": "type",
    "Appliance Type": "type",
    "Color": "color",
    "Connectivity": "connectivity",
    "Category names": "device",
    "Smartphone compatibility": "compatibility",
    "Tablet compatibility": "compatibility",
    "Dispenser Type": "dispenser",
    "Product Range": "range",
    "Depth Type": "depth",
    "Height to Top of Hinge": "hinge_height",
    "ENERGY STAR\u00ae Certified": "energy_star",
    "Offers": "offers",
    "Shop": "shop",
    "Shop Online": "shop",
}


def load_image_map() -> dict[str, str]:
    return json.loads((RAW / "image_sources.json").read_text(encoding="utf-8"))


def local_for(images: dict, url_map: dict) -> str:
    url = images.get("largeImage", {}).get("url") or images.get("smallImage", {}).get("url")
    return url_map.get(url, "") if url else ""


def build_products(url_map: dict) -> list[dict]:
    products = []
    seen_codes: set[str] = set()
    for code, slug, label, hub in CATEGORIES:
        pf = json.loads((RAW / f"pf_{slug}.json").read_text(encoding="utf-8"))
        for item in pf.get("searchResults", []):
            mc = item.get("modelCode") or item.get("id")
            if not mc or mc in seen_codes:
                continue
            seen_codes.add(mc)
            facets: dict[str, list[str]] = {}
            for f in item.get("filters", []):
                key = FACET_MAP.get(f.get("name", ""))
                if not key:
                    continue
                vals = sorted({v.get("value") or v.get("label") or ""
                               for v in f.get("values_pf", [])} - {""})
                if vals:
                    facets.setdefault(key, []).extend(vals)
            facets = {k: sorted(set(v)) for k, v in facets.items()}
            products.append({
                "model_code": mc,
                "category": slug,
                "category_label": label,
                "series": item.get("sub_genre") or "",
                "family": item.get("familyMktName") or "",
                "name": item.get("productDisplayName") or item.get("name") or "",
                "mlp_url": item.get("mlpUrl") or item.get("pdpURL") or "",
                "msrp": item.get("msrp_price"),
                "sale_price": item.get("sale_price"),
                "monthly_price": item.get("monthly_price"),
                "currency": item.get("msrp_price_currency") or "USD",
                "rating": item.get("reviewRating"),
                "reviews": item.get("numberOfReviews"),
                "in_stock": item.get("stockFlag") == "Y",
                "buy_online": item.get("ecomFlag") == "Y",
                "key_features": item.get("keyFeatures") or [],
                "facets": facets,
                "image": local_for(item.get("images", {}), url_map),
            })
    products.sort(key=lambda p: (p["category"], p["model_code"]))
    return products


def build_configurators(url_map: dict) -> list[dict]:
    out = []
    for path in sorted(RAW.glob("buy_*.json")):
        # the upstream /buy/ URLs for these appliance models redirect to the
        # product page (no live configurator), so they are not mirrored
        if path.stem.startswith("buy_refrigerators_"):
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        pd = data.get("props", {}).get("pageProps", {}).get("productData", {})
        products = []
        for p in pd.get("products", []):
            products.append({
                "model_code": p.get("modelCode"),
                "title": p.get("productTitle"),
                "buy_url": p.get("buySpaUrl") or p.get("pagePath"),
                "msrp": p.get("msrpPrice"),
                "price": p.get("currentPrice"),
                "stock": p.get("stockStatus") or ("InStock" if p.get("availability") is None else p.get("availability")),
                "image": url_map.get(p.get("defaultImage"), ""),
                "rating": (p.get("reviews", {}) or {}).get("starRating"),
                "review_count": (p.get("reviews", {}) or {}).get("reviewCount"),
            })
        out.append({
            "key": path.stem[len("buy_"):],
            "category": pd.get("subCategory") or "",
            "default_model": pd.get("defaultModelCode"),
            "taxonomy": pd.get("taxonomy_path"),
            "products": products,
            "relation": pd.get("relation", []),
        })
    out.sort(key=lambda c: c["key"])
    return out


def spec_rows(node: dict) -> list[dict]:
    """Flatten one compareSpec tree into rows, preserving upstream order."""
    rows = []
    for g in node:
        value = g.get("attrValue")
        children = g.get("childAttr") or []
        if children:
            rows.append({"group": g.get("attrName") or "", "name": "", "value": ""})
            rows.extend(spec_rows(children))
        else:
            text = re.sub(r"\s*\n\s*", "\n", str(value or "–")).strip()
            rows.append({"group": "", "name": g.get("attrName") or "", "value": text})
    return rows


def build_specs() -> dict:
    spec = json.loads((RAW / "spec_smartphones.json").read_text(encoding="utf-8"))
    fam = json.loads((RAW / "family_smartphones.json").read_text(encoding="utf-8"))
    fam_names: dict[str, dict] = {}
    for p in fam.get("response", {}).get("resultData", {}).get("productList", []):
        fam_names[p.get("productGroupId", "")] = {
            "name": p.get("fmyMarketingName") or p.get("fmyEngName"),
            "series": p.get("categorySubTypeName") or "",
        }
    models = {}
    for m in spec.get("response", {}).get("resultData", {}).get("modelList", []):
        models[m.get("modelName")] = spec_rows(m.get("compareSpec") or [])
    return {"families": fam_names, "models": dict(sorted(models.items()))}


def clean(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = text.replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def build_support() -> dict:
    html = (RAW / "support_warranty.html").read_text(encoding="utf-8", errors="replace")
    faqs = []
    for m in re.finditer(
            r'<h3 class="su-g-faq__list-item-question">(.*?)</h3>\s*'
            r'<div class="su-g-faq__list-item-answer">(.*?)</div>', html, re.S):
        q, a = clean(m.group(1)), m.group(2)
        links = re.findall(r'href="(https?://[^"]+|/us/[^"]+)"', a)
        a = clean(a)
        if q and a:
            faqs.append({"question": q, "answer": a, "links": links})
    # warranty checker category cards (real upstream cards)
    checker_cats = []
    for m in re.finditer(
            r'<a class="warranty-checker-manuf-warranty-box-list-item[^"]*"[^>]*'
            r'href-value="([^"]+)"[^>]*>\s*'
            r'<strong[^>]*>(.*?)</strong>.*?'
            r'<img[^>]*src="([^"]+)"', html, re.S):
        checker_cats.append({
            "legal_url": m.group(1),
            "name": clean(m.group(2)),
            "icon": m.group(3),
        })
    # standard limited warranty text from the legal pages
    legal = {}
    for key, fname in (("tv", "legal_tv"), ("appliances", "legal_appliances")):
        p = RAW / f"support_{fname}.html"
        if not p.exists():
            continue
        lhtml = p.read_text(encoding="utf-8", errors="replace")
        sections = []
        for sm in re.finditer(
                r'<h2[^>]*class="[^"]*article-text__title[^"]*"[^>]*>(.*?)</h2>\s*'
                r'<div[^>]*class="[^"]*article-text__text[^"]*"[^>]*>(.*?)</div>',
                lhtml, re.S):
            title, body = clean(sm.group(1)), clean(sm.group(2))
            if title and body:
                sections.append({"title": title, "body": body})
        legal[key] = sections
    contact_html = (RAW / "support_contact.html").read_text(encoding="utf-8", errors="replace")
    topics = []
    for m in re.finditer(
            r'<button[^>]*class="[^"]*topic[^"]*"[^>]*>(.*?)</button>', contact_html, re.S):
        t = clean(m.group(1))
        if t and len(t) < 80:
            topics.append(t)
    home_html = (RAW / "support_support_home.html").read_text(encoding="utf-8", errors="replace")
    quick = []
    for m in re.finditer(
            r'<a[^>]*href="(/us/support/[a-z0-9-]+/)"[^>]*>\s*<span[^>]*>(.*?)</span>',
            home_html, re.S):
        quick.append({"path": m.group(1), "label": clean(m.group(2))})
    return {
        "warranty": {
            "heading": clean(re.search(r"<h1[^>]*>(.*?)</h1>", html, re.S).group(1)) if re.search(r"<h1[^>]*>(.*?)</h1>", html, re.S) else "Warranty",
            "faqs": faqs,
            "checker_categories": checker_cats,
            "legal": legal,
        },
        "contact_topics": sorted(set(topics)),
        "quick_help": quick[:24],
    }


def build_home(url_map: dict) -> dict:
    html = (RAW / "home.html").read_text(encoding="utf-8", errors="replace")
    heroes = []
    for m in re.finditer(
            r'<section class="hd08-hero-kv-home[^"]*">(.*?)</section>', html, re.S):
        block = m.group(1)
        title = re.search(r'data-contents-title="([^"]+)"', block)
        desc = re.search(r'hd08-hero-kv-home__desc-text--pc-only">([^<]*)<', block)
        cta = re.search(r'<a class="cta[^"]*"[^>]*href="([^"]+)"', block)
        cta_label = re.search(r'<a class="cta[^"]*"[^>]*>(.*?)</a>', block, re.S)
        img = re.search(r'(?:data-src-pc|data-bg-pc)="([^"]+)"', block)
        if not img:
            # hero background is preloaded in the page head (desktop media query)
            probe = re.search(
                r'<link rel="preload" as="image" href="([^"]+)" '
                r'media="\(min-width:768px\)"', html)
            img = probe
        heroes.append({
            "title": clean(title.group(1)) if title else "",
            "subtitle": clean(desc.group(1)) if desc else "",
            "cta_url": cta.group(1) if cta else "",
            "cta_label": clean(cta_label.group(1)) if cta_label else "Learn more",
            "image": url_map.get(img.group(1).split("?")[0], "") if img else "",
        })
    # co76 feature-kv bands on the live home page
    for m in re.finditer(r'<section class="co76-feature-kv', html):
        seg = html[m.start():m.start() + 8000]
        head = re.search(r'class="co76-feature-kv__headline[^"]*"[^>]*>(.*?)</', seg, re.S)
        desc = re.search(r'class="co76-feature-kv__desc[^"]*"[^>]*>(.*?)</', seg, re.S)
        img = re.search(r'<img[^>]*class="[^"]*image__(?:main|preview)[^"]*"[^>]*'
                       r'data-desktop-src="(//images\.samsung\.com[^"]+)"', seg)
        cta = re.search(r'<a[^>]*class="cta[^"]*"[^>]*href="([^"]+)"', seg)
        title = clean(head.group(1)) if head else ""
        subtitle = clean(desc.group(1)) if desc else ""
        if not img and (not title and not subtitle):
            continue
        heroes.append({
            "title": title,
            "subtitle": subtitle,
            "cta_url": cta.group(1) if cta else "",
            "cta_label": "Learn more",
            "image": url_map.get(("https:" + img.group(1)).split("?")[0], "") if img else "",
        })
    return {"heroes": heroes[:12]}


def build_family_index() -> dict:
    """model_name -> family record, from the live family-list API."""
    fam = json.loads((RAW / "family_smartphones.json").read_text(encoding="utf-8"))
    rd = fam.get("response", {}).get("resultData", {})
    fam_by_id = {p.get("familyId"): p for p in rd.get("productList", [])}
    models = {}
    for pm in rd.get("parameterModelList", []):
        record = fam_by_id.get(pm.get("fmyId")) or {}
        model_name = (pm.get("modelName") or "")[:7]
        if model_name and model_name not in models:
            models[model_name] = {
                "name": record.get("fmyMarketingName") or model_name,
                "series": record.get("categorySubTypeName") or "",
            }
    return {"models": dict(sorted(models.items()))}


def main() -> None:
    url_map = load_image_map()
    products = build_products(url_map)
    (OUT / "products.json").write_text(json.dumps(products, indent=1), encoding="utf-8")
    print(f"products: {len(products)}")
    configs = build_configurators(url_map)
    (OUT / "configurators.json").write_text(json.dumps(configs, indent=1), encoding="utf-8")
    print(f"configurators: {len(configs)}")
    specs = build_specs()
    (OUT / "specs.json").write_text(json.dumps(specs, indent=1), encoding="utf-8")
    print(f"spec models: {len(specs['models'])}")
    fam_idx = build_family_index()
    (OUT / "family_index.json").write_text(json.dumps(fam_idx, indent=1), encoding="utf-8")
    print(f"family index: {len(fam_idx['models'])}")
    support = build_support()
    (OUT / "support.json").write_text(json.dumps(support, indent=1), encoding="utf-8")
    print(f"support: {len(support['warranty']['faqs'])} faqs, {len(support['contact_topics'])} topics")
    home = build_home(url_map)
    (OUT / "home.json").write_text(json.dumps(home, indent=1), encoding="utf-8")
    print(f"home heroes: {len(home['heroes'])}")


if __name__ == "__main__":
    main()
