"""Harvest full lawyer profile pages from profiles.superlawyers.com.

Each profile captures: display name, tagline, photo, firm (name + link),
phone, the sidebar summary (practice areas, licensed-since, education,
Super Lawyers / Rising Stars selections), the About biography, the
practice-area chips + focus areas + percentage breakdown, achievements
(first admitted, professional webpage, honors, languages, fees, bar
statuses), office location + static map, additional sources, and the
find-me-online links.

Output: source_data/lawyers/<uuid>.json (one file per attorney).
"""
from __future__ import annotations

import json
import pathlib
import re
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from sl_browser import PROFILES, goto_sl, launch  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
SITE = HERE.parent
LISTINGS = SITE / "source_data" / "listings"
OUT = SITE / "source_data" / "lawyers"
OUT.mkdir(parents=True, exist_ok=True)

CARD_CAP = 50  # lawyers kept per listing (upstream order; all cards)


def collect_targets():
    """(uuid, slug, state, city) for every lawyer on a trimmed listing."""
    targets = {}
    for path in sorted(LISTINGS.glob("*.json")):
        data = json.loads(path.read_text())
        for card in data["cards"][:CARD_CAP]:
            uuid = card.get("profile_uuid")
            if not uuid or uuid in targets:
                continue
            slug = card["profile_slug"]
            # profile URL shape: /<state>/<city>/lawyer/<slug>/<uuid>.html
            targets[uuid] = {
                "slug": slug, "state": data["state_slug"],
                "city": data["city_slug"],
            }
    return targets


def strip_tags(fragment: str) -> str:
    text = re.sub(r"<script.*?</script>", "", fragment, flags=re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    text = text.replace("&amp;", "&").replace("&#39;", "'") \
               .replace("&quot;", '"').replace("&nbsp;", " ")
    return re.sub(r"\s+", " ", text).strip()


def section_between(html: str, start: str, end: str, maxc: int = 9000) -> str:
    i = html.find(start)
    if i == -1:
        return ""
    j = html.find(end, i + len(start))
    return html[i:j if j > i else i + maxc]


def parse_profile(html: str, url: str) -> dict:
    rec: dict = {"url": url}

    h1 = re.search(r'<h1[^>]*id="attorney_name"[^>]*>(.*?)</h1>', html, re.S)
    rec["name"] = strip_tags(h1.group(1)) if h1 else None
    tag = re.search(r'id="attorney_profile_tagline"[^>]*>(.*?)</h2>', html, re.S)
    rec["tagline"] = strip_tags(tag.group(1)) if tag else None
    img = re.search(
        r'<img class="w-100 rounded-3 h-auto" src="(https://cdn\.superlawyers\.com[^"]+)"',
        html)
    rec["photo_url"] = img.group(1) if img else None

    firm = re.search(
        r'href="(https://profiles\.superlawyers\.com/([^/]+)/([^/]+)/lawfirm/([^/]+)/'
        r'([0-9a-f-]+)\.html?)"[^>]*title="Super Lawyers Profile page of Firm ([^"]+)"',
        html)
    if firm:
        rec["firm"] = {
            "name": firm.group(6).strip(),
            "slug": firm.group(4), "uuid": firm.group(5),
            "state": firm.group(2), "city": firm.group(3),
        }
    else:
        fm = re.search(r'class="profile-profile-header[^"]*"[^>]*>\s*([^<]+)', html)
        rec["firm"] = {"name": fm.group(1).strip() if fm else None}

    phone = re.search(r'href="tel:\+(\d+)"[^>]*>\s*<i[^>]*></i>([\d\-]+)', html)
    if not phone:
        phone = re.search(r'href="tel:([^"]+)"[^>]*>.*?([\d\-\(\)\s]{8,})</a>', html, re.S)
    rec["phone"] = phone.group(2).strip() if phone else None

    # sidebar summary ----------------------------------------------------
    def side(pattern):
        m = re.search(pattern, html, re.S)
        return strip_tags(m.group(1)) if m else None

    rec["side_practice_areas"] = side(
        r'id="pa_areas"[^>]*>\s*<span[^>]*>Practice areas:</span>\s*(.*?)<a href="#practice-areas"')
    if rec["side_practice_areas"]:
        rec["side_practice_areas"] = rec["side_practice_areas"].rstrip(" ;")
    rec["licensed_since"] = side(
        r'id="licensed_since"[^>]*>\s*<span[^>]*>[^<]*since:</span>\s*(\d{4})')
    edu = re.search(
        r'id="law_school"[^>]*>\s*<span[^>]*>Education:</span>\s*<a[^>]*>([^<]+)</a>', html)
    if not edu:
        edu = re.search(r'id="law_school"[^>]*>\s*<span[^>]*>Education:</span>\s*([^<]+)', html)
    rec["education"] = strip_tags(edu.group(1)) if edu else None
    rec["education_url"] = (re.search(
        r'id="law_school"[^>]*>\s*<span[^>]*>Education:</span>\s*<a[^>]*href="([^"]+)"', html) or [None]).group(1) \
        if re.search(r'id="law_school"[^>]*>\s*<span[^>]*>Education:</span>\s*<a[^>]*href', html) else None
    rec["sl_selection"] = side(r'Selected to Super Lawyers:\s*([^<]+)</span>')
    rec["rs_selection"] = side(r'Selected to Rising Stars:\s*([^<]+)</span>')
    langs = re.search(r'id="languages"[^>]*>\s*<span[^>]*>Languages spoken:</span>\s*([^<]+)', html)
    if langs:
        rec["languages"] = [t.strip() for t in strip_tags(langs.group(1)).split(",") if t.strip()]

    # About ---------------------------------------------------------------
    about_html = section_between(html, 'id="about"', 'id="practice-areas"')
    paras = [strip_tags(p) for p in re.findall(r"<p[^>]*>(.*?)</p>", about_html, re.S)]
    rec["about"] = [p for p in paras if p and len(p) > 40]

    # Practice areas -------------------------------------------------------
    pa_html = section_between(html, 'id="practice-areas"', 'id="achievements"')
    chips_m = re.search(r"<h3[^>]*>Practice areas</h3>\s*(.*?)<h3", pa_html, re.S)
    if chips_m:
        chips_text = strip_tags(chips_m.group(1))
        chips = [t.strip() for t in chips_text.split(",") if t.strip()]
    else:
        chips = []
    rec["practice_areas"] = chips
    focus = re.search(r"<h3[^>]*>Focus areas</h3>\s*<p>(.*?)</p>", pa_html, re.S)
    rec["focus_areas"] = [t.strip() for t in strip_tags(focus.group(1)).split(",")] \
        if focus else []
    # only the legend rows carry the clean breakdown
    rec["pa_breakdown"] = [
        {"pct": int(m.group(1)), "area": strip_tags(m.group(2))}
        for m in re.finditer(
            r'piechart_legend_label_item">(\d+)%\s*([^<]+)</span>', pa_html)
    ]

    # Achievements ---------------------------------------------------------
    ach_html = section_between(html, 'id="achievements"', 'id="map"')
    first_adm = re.search(r"First Admitted:</span>\s*([^<]+)", ach_html)
    rec["first_admitted"] = strip_tags(first_adm.group(1)) if first_adm else None
    webpage = re.search(r"Professional Webpage:</span>\s*<a[^>]*href=\"([^\"]+)\"", ach_html)
    rec["professional_webpage"] = webpage.group(1) if webpage else None
    honors = []
    hi = ach_html.find("Honors")
    if hi != -1:
        chunk = ach_html[hi:hi + 6000]
        for m in re.finditer(r"<li[^>]*>(.*?)</li>", chunk, re.S):
            t = strip_tags(m.group(1))
            if t:
                honors.append(t)
    rec["honors"] = honors
    # optional fields some profiles carry
    for label, key in [
        ("Languages:", "languages"), ("Fees:", "fees"),
        ("Free Consultation:", "free_consultation"),
        ("Credit Cards:", "credit_cards"),
        ("Bar Status:", "bar_status"),
        ("Jurisdictions Licensed to Practice:", "jurisdictions"),
    ]:
        m = re.search(re.escape(label) + r"\s*</strong>\s*(.*?)</(?:p|li|div)>",
                      ach_html, re.S)
        if m:
            rec[key] = strip_tags(m.group(1))
        m2 = re.search(re.escape(label) + r"\s*</strong>\s*<ul[^>]*>(.*?)</ul>",
                       ach_html, re.S)
        if m2:
            rec[key] = [strip_tags(x) for x in
                        re.findall(r"<li[^>]*>(.*?)</li>", m2.group(1), re.S) if x]

    # Map / office -----------------------------------------------------------
    map_html = section_between(html, 'id="map"', "Additional sources", 12000)
    office = re.search(r'id="firm_map_info"[^>]*>(.*?)</p>', html, re.S)
    if not office:
        office = re.search(
            r"Office location for [^<]+</h3>\s*(.*?)Phone:", map_html, re.S)
    if office:
        lines = [strip_tags(x) for x in
                 re.findall(r"([^<>]+)(?:<br\s*/?>|</p>|$)", office.group(1))]
        rec["office"] = [x for x in lines if x]
    else:
        rec["office"] = []
    static_map = re.search(r'src="(https://maps\.googleapis\.com/maps/api/staticmap[^"]+)"', html)
    rec["static_map_url"] = static_map.group(1).replace("&amp;", "&") if static_map else None

    # Selections --------------------------------------------------------------
    sel = re.search(r"Super Lawyers:\s*(\d{4}\s*-\s*\d{4}(?:\s*,\s*\d{4})*)", html)
    rec["sl_years"] = sel.group(1) if sel else None
    rs = re.search(r"Rising Stars:\s*((?:\d{4}\s*-\s*\d{4}|\d{4})(?:\s*,\s*(?:\d{4}\s*-\s*\d{4}|\d{4}))*)", html)
    rec["rs_years"] = rs.group(1) if rs else None
    sl_count = re.search(r'(\d+)\s*Years\s*.*?Super Lawyers', html, re.S)
    rs_count = re.search(r'(\d+)\s*Years\s*.*?Rising Stars', html, re.S)
    rec["sl_years_count"] = int(sl_count.group(1)) if sl_count else 0
    rec["rs_years_count"] = int(rs_count.group(1)) if rs_count else 0

    # Additional sources / find me online ---------------------------------------
    add_html = section_between(html, "Find me online", "Attorney resources", 6000)
    rec["findlaw"] = "FindLaw" in html
    rec["lawinfo"] = "LawInfo" in html
    online = re.findall(
        r"<a[^>]+href=\"(https?://(?!profiles\.superlawyers|www\.superlawyers|"
        r"my\.superlawyers|lawschools\.superlawyers|answers\.superlawyers|"
        r"attorneys\.superlawyers|cdn\.superlawyers|internetbrands)[^\"]+)\"[^>]*>",
        add_html)
    rec["online_links"] = [{"url": u} for u in online]

    return rec


def main() -> None:
    targets = collect_targets()
    todo = {u: t for u, t in targets.items()
            if not (OUT / f"{u}.json").exists()}
    print(f"[profiles] {len(targets)} targets, {len(todo)} to scrape")
    pw, browser, ctx = launch()
    page = ctx.new_page()
    done = 0
    t0 = time.time()
    for uuid, meta in todo.items():
        url = (f"{PROFILES}/{meta['state']}/{meta['city']}/lawyer/"
               f"{meta['slug']}/{uuid}.html")
        ok = goto_sl(page, url, tries=10)
        html = page.content()
        if not ok or "404" in page.title():
            print(f"[fail] {url}")
        try:
            rec = parse_profile(html, url)
        except Exception as exc:  # noqa: BLE001
            print(f"[parse-error] {uuid}: {exc}")
            continue
        (OUT / f"{uuid}.json").write_text(json.dumps(rec, indent=1, ensure_ascii=False))
        done += 1
        if done % 25 == 0:
            rate = done / (time.time() - t0)
            print(f"  {done}/{len(todo)} ({rate:.2f}/s, eta {(len(todo)-done)/rate/60:.1f}m)")
    browser.close()
    pw.stop()
    print(f"[profiles] done: {done} scraped")


if __name__ == "__main__":
    main()
