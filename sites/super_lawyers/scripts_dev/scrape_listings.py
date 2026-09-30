"""Harvest lawyer listing (SERP) pages from attorneys.superlawyers.com.

For each (practice, state, city) combo this captures the real upstream
listing: the lawyer cards (name, profile slug + uuid, photo, firm, city
line, tagline, phone, sponsored flag), the court locations block, the
nearby-cities and related-practice-area rails, the practice-area FAQ
accordion, and the "Are you searching for..." intro text.

Output: source_data/listings/<pa>__<state>__<city>.json
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from sl_browser import ATTORNEYS, goto_sl, launch  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
SITE = HERE.parent
OUT = SITE / "source_data" / "listings"
OUT.mkdir(parents=True, exist_ok=True)

# practice-area slug, state slug, city slug, display names
COMBOS = [
    ("personal-injury-plaintiff", "washington", "seattle"),
    ("personal-injury-plaintiff", "illinois", "chicago"),
    ("personal-injury-plaintiff", "new-york", "new-york"),
    ("personal-injury-plaintiff", "florida", "miami"),
    ("motor-vehicle-accidents", "washington", "seattle"),
    ("family-law", "washington", "seattle"),
    ("family-law", "illinois", "chicago"),
    ("divorce", "new-york", "new-york"),
    ("divorce", "texas", "houston"),
    ("criminal-defense", "georgia", "atlanta"),
    ("criminal-defense", "washington", "seattle"),
    ("dui-dwi", "colorado", "denver"),
    ("employment-and-labor", "massachusetts", "boston"),
    ("employment-and-labor", "california", "los-angeles"),
    ("estate-planning-and-probate", "texas", "dallas"),
    ("estate-planning-and-probate", "florida", "miami"),
    ("immigration", "texas", "houston"),
    ("immigration", "california", "los-angeles"),
    ("business-litigation", "california", "los-angeles"),
    ("business-litigation", "new-york", "new-york"),
    ("real-estate", "california", "los-angeles"),
    ("real-estate", "illinois", "chicago"),
    ("bankruptcy", "arizona", "phoenix"),
    ("medical-malpractice", "florida", "miami"),
    ("workers-compensation", "ohio", "columbus"),
    ("elder-law", "california", "san-diego"),
    ("intellectual-property", "california", "san-francisco"),
    ("civil-rights", "new-york", "new-york"),
]


def strip_tags(fragment: str) -> str:
    text = re.sub(r"<script.*?</script>", "", fragment, flags=re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).replace("&amp;", "&").replace("&#39;", "'").strip()


def parse_listing(html: str, url: str, combo: tuple) -> dict:
    pa, state, city = combo

    # ---- lawyer cards ------------------------------------------------
    cards = []
    chunks = re.split(r'<div[^>]*class="card[^"]*serp-container[^"]*lawyer[^"]*"', html)[1:]
    for chunk in chunks:
        name = re.search(r'aria-label="View profile of ([^"]+)"', chunk)
        if not name:
            continue
        prof = re.search(r'href="(https://profiles\.superlawyers\.com/[^"]+/lawyer/([^/]+)/([0-9a-f-]+)\.html?[^"]*)"', chunk)
        img = re.search(r'src="(https://cdn\.superlawyers\.com[^"]+)"', chunk)
        firm = re.search(r'href="(https://profiles\.superlawyers\.com/[^"]+/lawfirm/([^/]+)/([0-9a-f-]+)\.html?[^"]*)"[^>]*>\s*(?:<i[^>]*>.*?</i>\s*)?([^<]+)', chunk, re.S)
        city_line = re.search(r'<span class="city[^"]*">(.*?)</span>', chunk, re.S)
        tagline = re.search(r'<p class="ts_tagline[^"]*">(.*?)</p>', chunk, re.S)
        phone = re.search(r'href="tel:([^"]+)"[^>]*>\s*<i[^>]*></i>([^<]+)', chunk)
        sponsored = "top_spot" in chunk[:400] or "Sponsored" in chunk[:1200]
        # plain (non-sponsored) firm anchor: text right after the name block
        firm_name = None
        if firm:
            firm_name = firm.group(4).strip()
        else:
            fm = re.search(r'class="single-link[^"]*"[^>]*>\s*([^<]+)', chunk)
            if fm:
                firm_name = fm.group(1).strip()
        cards.append({
            "name": name.group(1),
            "profile_slug": prof.group(2) if prof else None,
            "profile_uuid": prof.group(3) if prof else None,
            "photo_url": img.group(1) if img else None,
            "firm_name": firm_name,
            "firm_slug": firm.group(2) if firm else None,
            "firm_uuid": firm.group(3) if firm else None,
            "city_line": strip_tags(city_line.group(1)) if city_line else None,
            "tagline": strip_tags(tagline.group(1)) if tagline else None,
            "phone": phone.group(2).strip() if phone else None,
            "sponsored": sponsored,
        })

    # ---- courts -------------------------------------------------------
    courts = []
    ci = html.find("Court locations in ")
    if ci != -1:
        chunk = html[ci:ci + 14000]
        for m in re.finditer(
                r"<strong>([^<]+)</strong>\s*<br>\s*([^<]+)\s*<br>\s*([^<]+)"
                r"\s*<br>\s*Phone:\s*<a[^>]*>([^<]+)</a>\s*<br>\s*"
                r"<a[^>]+href=\"([^\"]+)\"", chunk):
            courts.append({
                "name": m.group(1).strip(),
                "line1": m.group(2).strip(),
                "line2": m.group(3).strip(),
                "phone": m.group(4).strip(),
                "website": m.group(5).strip(),
            })

    # ---- nearby cities / related practice areas ------------------------
    nearby = []
    ni = html.find("Nearby cities:")
    if ni != -1:
        chunk = html[ni:ni + 4000]
        for m in re.finditer(r'<a[^>]+href="([^"]+)"[^>]*>([^<]+)</a>', chunk):
            nearby.append({"name": m.group(2).strip(), "href": m.group(1)})
    related = []
    ri = html.find("lawyers in related practice areas")
    if ri != -1:
        chunk = html[html.rfind("<", 0, ri):ri + 4000]
        for m in re.finditer(r'<a[^>]+href="([^"]+)"[^>]*>([^<]+)</a>', chunk):
            related.append({"name": m.group(2).strip(), "href": m.group(1)})

    # ---- intro + FAQ text ----------------------------------------------
    intro = []
    ii = html.find("Are you searching for a top ")
    if ii != -1:
        chunk = html[ii:ii + 6000]
        for m in re.finditer(r"<p[^>]*>(.*?)</p>", chunk, re.S):
            t = strip_tags(m.group(1))
            if t:
                intro.append(t)
            if len(intro) >= 3:
                break
    faq = []
    fi = html.find("Open all / Close all")
    if fi != -1:
        chunk = html[fi:fi + 12000]
        heading = None
        for m in re.finditer(r"<h[234][^>]*>(.*?)</h[234]>|<p[^>]*>(.*?)</p>", chunk, re.S):
            if m.group(1) is not None:
                heading = strip_tags(m.group(1))
            else:
                t = strip_tags(m.group(2))
                if t and heading:
                    faq.append({"heading": heading, "text": t})

    h1 = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.S)
    return {
        "url": url,
        "practice_slug": pa,
        "state_slug": state,
        "city_slug": city,
        "h1": strip_tags(h1.group(1)) if h1 else None,
        "cards": cards,
        "courts": courts,
        "nearby_cities": nearby,
        "related_practice_areas": related,
        "intro": intro,
        "faq": faq,
    }


def main() -> None:
    pw, browser, ctx = launch()
    page = ctx.new_page()
    for combo in COMBOS:
        pa, state, city = combo
        out = OUT / f"{pa}__{state}__{city}.json"
        if out.exists():
            print(f"[skip] {out.name}")
            continue
        url = f"{ATTORNEYS}/{pa}/{state}/{city}/"
        ok = goto_sl(page, url)
        html = page.content()
        if not ok:
            print(f"[RETRY-FAIL] {url} title={page.title()[:50]!r}")
        data = parse_listing(html, url, combo)
        out.write_text(json.dumps(data, indent=1, ensure_ascii=False))
        print(f"[ok] {pa}/{state}/{city}: {len(data['cards'])} cards, "
              f"{len(data['courts'])} courts")
    browser.close()
    pw.stop()


if __name__ == "__main__":
    main()
