#!/usr/bin/env python3
"""Parse the raw upstream captures (scraped_data/) into the tracked
source_data/*.json snapshots the seeder reads.

Every record keeps its upstream path/URL. Run from the site dir:
    python3 scripts_dev/build_source_data.py
"""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from scrape_pages import PAGE_PATHS            # noqa: E402
from scrape_pages_round2 import ROUND2_PATHS   # noqa: E402

RAW = ROOT / "scraped_data"
OUT = ROOT / "source_data"
TAG_RE = re.compile(r"<[^>]+>")


def text_of(html: str) -> str:
    html = re.sub(r"<script.*?</script>", " ", html, flags=re.S)
    html = re.sub(r"<style.*?</style>", " ", html, flags=re.S)
    text = TAG_RE.sub(" ", html)
    import html as html_mod
    return " ".join(html_mod.unescape(text).split())


def main_of(html: str) -> str:
    m = re.search(r"<main[^>]*>(.*?)</main>", html, re.S)
    return m.group(1) if m else html


def unescape(s: str) -> str:
    import html as html_mod
    return html_mod.unescape(s)


# ---------------------------------------------------------------- pages ----

def parse_page(name: str) -> dict | None:
    p = RAW / "pages" / f"{name}.html"
    if not p.exists():
        return None
    html = p.read_text(encoding="utf-8")
    title_m = re.search(r"<title>(.*?)</title>", html, re.S)
    main = main_of(html)
    # alert banner (site-wide scam alert)
    alerts = []
    for m in re.finditer(
            r'c-alert__heading">\s*<span>([^<]+)</span>.*?c-alert__message">\s*(.*?)\s*</div>',
            main, re.S):
        alerts.append({"heading": unescape(m.group(1)).strip(),
                       "message": text_of(m.group(2))})
    # drop the alert view + hero + breadcrumb chrome from body parsing
    body_html = main
    for chrome in re.findall(
            r'<div\s+class="c-view c-view--alerts.*?</div>\s*</div>\s*</div>', body_html, re.S):
        body_html = body_html.replace(chrome, "")
    # section structure: slice the body at h2/h3 heading positions
    sections = []
    heads = list(re.finditer(r"<(h2|h3)[^>]*>", body_html))
    if heads:
        pre = body_html[:heads[0].start()]
        sections.append({"heading": "", "html": pre})
        for i, hm in enumerate(heads):
            end = heads[i + 1].start() if i + 1 < len(heads) else len(body_html)
            chunk = body_html[hm.end():end]
            close = re.search(r"</h\d>", chunk)
            heading = text_of(chunk[:close.start()]) if close else ""
            rest = chunk[close.end():] if close else chunk
            sections.append({"heading": heading, "html": rest})
    else:
        sections.append({"heading": "", "html": body_html})
    # extract links (href, label) per section
    out_sections = []
    for sec in sections:
        links = []
        for lm in re.finditer(r'<a[^>]*href="([^"#]+)"[^>]*>(.*?)</a>', sec["html"], re.S):
            label = text_of(lm.group(2))
            if label and len(label) < 200:
                links.append({"href": lm.group(1), "label": label})
        paragraphs = []
        for pm in re.finditer(r"<p[^>]*>(.*?)</p>", sec["html"], re.S):
            t = text_of(pm.group(1))
            if t:
                paragraphs.append(t)
        lists = []
        for lm in re.finditer(r"<(ul|ol)[^>]*>(.*?)</\1>", sec["html"], re.S):
            items = [text_of(i) for i in re.findall(r"<li[^>]*>(.*?)</li>", lm.group(2), re.S)]
            items = [i for i in items if i]
            if items:
                lists.append(items)
        tables = []
        for tm in re.finditer(r"<table[^>]*>(.*?)</table>", sec["html"], re.S):
            rows = []
            for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", tm.group(1), re.S):
                cells = [text_of(c) for c in re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", tr, re.S)]
                if cells:
                    rows.append(cells)
            if rows:
                tables.append(rows)
        if sec["heading"] == "Breadcrumb":
            continue
        if paragraphs or lists or tables or links:
            out_sections.append({"heading": sec["heading"], "paragraphs": paragraphs,
                                 "lists": lists, "tables": tables, "links": links})
    # card grids (c-cta-card): the hub pages render their quick links as cards
    cards = []
    for cm in re.finditer(
            r'<div\s+class="c-cta-card">\s*<a href="([^"]+)"(.*?)</a>', body_html, re.S):
        href = cm.group(1)
        inner = cm.group(2)
        tm = re.search(r'c-cta-card__title">\s*([^<]+?)\s*</', inner)
        em = re.search(r'c-cta-card__eyebrow">([^<]+)<', inner)
        sm = re.search(r'c-cta-card__summary">([^<]+)<', inner)
        label = unescape(tm.group(1)).strip() if tm else ""
        if label:
            cards.append({"href": href, "label": label,
                          "eyebrow": unescape(em.group(1)).strip() if em else "",
                          "summary": unescape(sm.group(1)).strip() if sm else ""})
    # sidebar navigation menu (section landing pages render their menu here)
    sidebar = re.search(r'l-sidebar__sidebar(.*?)l-sidebar__main', body_html, re.S)
    sidebar_links = []
    if sidebar:
        for lm in re.finditer(
                r'<a[^>]*href="([^"]+)"[^>]*>\s*(?:<[^>]*>\s*)*([^<]{2,90}?)\s*(?:<[^>]*>\s*)*</a>',
                sidebar.group(1)):
            label = unescape(lm.group(2)).strip()
            if label and (lm.group(1), label) not in [(s["href"], s["label"]) for s in sidebar_links]:
                sidebar_links.append({"href": lm.group(1), "label": label})
    title = unescape(title_m.group(1)).strip() if title_m else ""
    title = re.sub(r"\s*\|.*$", "", title)
    path = PAGE_PATHS.get(name) or ROUND2_PATHS.get(name) or ("/" + name)
    return {"name": name, "path": path, "title": title, "alerts": alerts,
            "sections": out_sections, "cards": cards,
            "sidebar_links": sidebar_links}


def build_pages() -> None:
    pages = []
    for p in sorted((RAW / "pages").glob("*.html")):
        if p.name in {"forms-pg2.html", "plates-search.html", "plate-detail.html",
                      "loc-alexandria.html", "manuals-spa.html", "plates.html",
                      "forms.html", "dmv201.html"}:
            continue
        parsed = parse_page(p.stem)
        if parsed:
            pages.append(parsed)
    (OUT / "pages.json").write_text(json.dumps(pages, indent=1), encoding="utf-8")
    print(f"[pages] {len(pages)} pages")


# -------------------------------------------------------------- locations --

def parse_offices() -> None:
    listing = (RAW / "locations" / "all-locations.html").read_text(encoding="utf-8")
    offices = []
    for m in re.finditer(
            r'<div\s+class="c-map-teaser"\s+data-map-id="(\d+)"\s+data-location-id="(\d+)"\s+data-type="(\w+)"(.*?)</div>\s*</div>\s*</div>',
            listing, re.S):
        map_id, loc_id, otype, card = m.groups()
        link = re.search(r'<a href="(/locations/[^"]+)"[^>]*>([^<]+)</a>', card)
        addr = re.search(r'<address class="c-map-teaser__address">([^<]+)</address>', card)
        hours = re.findall(r'<span class="office-hours__item-label">([^<]+): </span>'
                           r'<span class="office-hours__item-slots">([^<]+)</span>', card)
        note = re.search(r'c-map-teaser__title-note">([^<]+)<', card)
        if not link:
            continue
        offices.append({
            "map_id": int(map_id), "location_id": int(loc_id), "type": otype,
            "path": link.group(1), "name": unescape(link.group(2)).strip(),
            "address": unescape(addr.group(1)).strip() if addr else "",
            "hours": [[unescape(d).strip(), unescape(t).strip()] for d, t in hours],
            "vehicle_only_note": unescape(note.group(1)).strip() if note else "",
            "phone": "", "fax": "", "services_available": [], "services_unavailable": [],
            "nearby": [], "notices": [],
        })
    # detail pages
    for p in sorted((RAW / "locations").glob("csc-*.html")):
        html = p.read_text(encoding="utf-8")
        main = main_of(html)
        path = "/locations/" + p.stem[4:]
        office = next((o for o in offices if o["path"] == path), None)
        if office is None:
            continue
        phone = re.search(r'Telephone</[^>]+>[^<]*<?[^>]*>?\s*([\d-]+)', main)
        m = re.search(r'Telephone</(?:span|div|h\d)>(?:\s|<[^>]*>|&nbsp;)*([\d-]{8,16})', main)
        if m:
            office["phone"] = m.group(1)
        m = re.search(r'Fax</(?:span|div|h\d)>(?:\s|<[^>]*>|&nbsp;)*([\d-]{8,16})', main)
        if m:
            office["fax"] = m.group(1)
        avail = main.find("Available at this Location")
        if avail > 0:
            end = main.find("Not Available at this Location")
            seg = main[avail:end] if end > avail else main[avail:avail + 6000]
            office["services_available"] = [
                text_of(x) for x in re.findall(
                    r'l-section__services-available[^>]*>\s*((?:<div>[^<]*</div>\s*)+)', seg)
                for x in re.findall(r'<div>([^<]+)</div>', x)]
        unavail = main.find("Not Available at this Location")
        if unavail > 0:
            seg = main[unavail:unavail + 8000]
            office["services_unavailable"] = [
                text_of(x) for x in re.findall(
                    r'l-section__services-not-available[^>]*>\s*((?:<div>[^<]*</div>\s*)+)', seg)
                for x in re.findall(r'<div>([^<]+)</div>', x)]
        # nearby alternatives
        idx = main.find("Nearby Alternatives")
        if idx > 0:
            seg = main[idx:main.find("Nearby DMV Select")]
            for nm in re.finditer(
                    r'c-cta-card__eyebrow">([^<]+)</div>.*?<span>([^<]+)</span>.*?'
                    r'c-cta-card__summary">([^<]+)<', seg, re.S):
                office["nearby"].append({"type": unescape(nm.group(1)).strip(),
                                         "name": unescape(nm.group(2)).strip(),
                                         "address": unescape(nm.group(3)).strip()})
    (OUT / "offices.json").write_text(json.dumps(offices, indent=1), encoding="utf-8")
    csc = sum(1 for o in offices if o["type"] == "customer_service_center")
    print(f"[offices] {len(offices)} offices ({csc} CSC, {len(offices)-csc} DMV Select)")


# ------------------------------------------------------------------ plates --

def parse_plates() -> None:
    # category membership from the facet listing pages
    cat_of = {}
    for f in sorted((RAW / "plates").glob("cat-*.html")):
        cat = f.name.split("-")[1]
        for slug in re.findall(r'href="/vehicles/license-plates/search/([a-z0-9-]+)"',
                               f.read_text(encoding="utf-8")):
            cat_of.setdefault(slug, set()).add(cat)
    plates = []
    for f in sorted((RAW / "plates").glob("detail-*.html")):
        slug = f.stem[7:]
        html = f.read_text(encoding="utf-8")
        main = main_of(html)
        # the plate name is the c-plate-header h2; the page h1 is generic
        title = ""
        m = re.search(r'<h2>\s*<span>([^<]+)</span>\s*</h2>\s*\s*<div class="c-plate-header__grid"', main)
        if not m:
            m = re.search(r'c-plate-header__title[^>]*>\s*<span>([^<]+)</span>', main)
        if not m:
            m = re.search(r'<h2>\s*<span>([^<]+)</span>\s*</h2>', main)
        if m:
            title = unescape(m.group(1)).strip()
        img = re.search(r'<img[^>]*src="(/sites/default/files/[^"]+)"', main)
        fields = {}
        for fm in re.finditer(
                r'c-plate-header__label">([^<]+)</div>\s*<div class="c-plate-header__item-content">(.*?)</div>',
                main, re.S):
            label = unescape(fm.group(1)).strip()
            value = text_of(fm.group(2))
            fields[label] = value
        req = ""
        m = re.search(r'Requirements\s*</[^>]+>(.*?)(?:Personalization Guidelines|$)', main, re.S)
        if m:
            req = text_of(m.group(1))[:600]
        revenue = ""
        m = re.search(r'Revenue Sharing Plates\s*</[^>]+>(.*?)(?:For tax purposes|Personalization Guidelines|$)',
                      main, re.S)
        if m:
            revenue = text_of(m.group(1))[:900]
        codes = []
        tcm = re.search(r'For tax purposes.*?</p>', main, re.S)
        if tcm:
            codes = re.findall(r'<strong>([A-Z0-9]{2,8})</strong>', tcm.group(0))
        plates.append({
            "slug": slug, "title": title,
            "category": sorted(cat_of.get(slug, ["Other"]))[0] if cat_of.get(slug) else "Other",
            "categories": sorted(cat_of.get(slug, [])),
            "image": img.group(1) if img else "",
            "personalization_available": fields.get("Personalization Available", ""),
            "plate_fee": fields.get("Plate Fee (in addition to registration fee)", ""),
            "plate_fee_period": "Annually" if "Annually" in
                fields.get("Plate Fee (in addition to registration fee)", "") else "",
            "personalized_fee": fields.get("Personalized Plate Fee (in addition to registration fee)", ""),
            "disabled_symbol": fields.get("Disabled Symbol Available Upon Request", ""),
            "char_combinations": fields.get("Number of Character Combinations Available on Plate", ""),
            "requirements": req, "revenue_sharing": revenue,
            "type_codes": codes[:4],
        })
    (OUT / "plates.json").write_text(json.dumps(plates, indent=1), encoding="utf-8")
    print(f"[plates] {len(plates)} plates")


# ------------------------------------------------------------------- forms --

def parse_forms() -> None:
    forms = []
    seen = set()
    for f in sorted((RAW / "forms").glob("list-*.html")):
        html = f.read_text(encoding="utf-8")
        main = main_of(html)
        for cm in re.finditer(
                r'<div\s+class="c-list-card">(.*?)</div>\s*</div>\s*</div>', main, re.S):
            card = cm.group(1)
            link = re.search(r'<a href="(/sites/default/files/forms/[^"]+)">\s*([^<]+?)\s*</a>', card)
            if not link:
                continue
            pdf, title = link.group(1), unescape(link.group(2)).strip()
            if pdf in seen:
                continue
            seen.add(pdf)
            summary = re.search(r'c-list-card__summary">([^<]*)</div>', card)
            pills = [unescape(p).strip() for p in re.findall(r'c-pill">\s*([^<]+?)\s*</span>', card)]
            number = pills[0] if pills else ""
            language = next((p for p in pills if p in ("English", "Spanish")), "English")
            category = next((p for p in pills if p not in (number, language)), "Other")
            forms.append({
                "title": title, "number": number, "description":
                    unescape(summary.group(1)).strip() if summary else "",
                "language": language, "category": category, "pdf": pdf,
            })
    (OUT / "forms.json").write_text(json.dumps(forms, indent=1), encoding="utf-8")
    print(f"[forms] {len(forms)} forms")


# ------------------------------------------------------------------- news --

def parse_news() -> None:
    articles = []
    for f in sorted((RAW / "news").glob("article-*.html")):
        slug = f.stem[8:]
        html = f.read_text(encoding="utf-8")
        title_m = re.search(r"<title>(.*?)</title>", html, re.S)
        main = main_of(html)
        date_m = re.search(r'c-press-release__date">([^<]+)<|datetime="([^"]+)"', main)
        img = re.search(r'<img[^>]*src="(/sites/default/files/[^"]+)"', main)
        body = []
        pieces = re.split(r"<h2[^>]*>|<h3[^>]*>", main)
        for i, piece in enumerate(pieces):
            if i % 2 == 1:
                piece = re.split(r"</h2>|</h3>", piece, 1)[-1]
            for pm in re.finditer(r"<p[^>]*>(.*?)</p>", piece, re.S):
                t = text_of(pm.group(1))
                if t and "Scam Alert" not in t:
                    body.append(t)
        title = unescape(title_m.group(1)).strip() if title_m else slug
        title = re.sub(r"\s*\|.*$", "", title)
        articles.append({
            "slug": slug, "title": title,
            "date": unescape(date_m.group(1) or date_m.group(2)).strip() if date_m else "",
            "image": img.group(1) if img else "",
            "paragraphs": body[:40],
        })
    (OUT / "news.json").write_text(json.dumps(articles, indent=1), encoding="utf-8")
    print(f"[news] {len(articles)} articles")


# ------------------------------------------------------------------ manual --

def parse_manual() -> None:
    tboc = json.loads((RAW / "manual" / "tboc.json").read_text())
    sections = json.loads((RAW / "manual" / "sections.json").read_text())
    quiz = json.loads((RAW / "manual" / "quiz.json").read_text())
    section_titles = {}
    for md in tboc["manualData"]:
        if md["manualID"] == "1":
            for s in md["sections"]:
                section_titles[s["sectionID"]] = s["sectionTitle"]
    # subsection copy, ordered by section.subsection
    subs = []
    for s in sections:
        copy = s.get("copy", "")
        m = re.search(r"<(?:h\d)[^>]*>\s*(\d+)\.(\d+) - ([^<\n]+)", copy)
        if m:
            head = text_of(m.group(3))
            subs.append({"section": int(m.group(1)), "subsection": int(m.group(2)),
                         "title": head, "html": copy})
        else:
            hm = re.search(r"<h2>(.*?)</h2>", copy, re.S)
            subs.append({"section": int(s.get("section", 0)), "subsection": 0,
                         "title": text_of(hm.group(1)) if hm else "",
                         "html": copy})
    subs.sort(key=lambda x: (x["section"], x["subsection"]))
    questions = []
    for q in quiz:
        questions.append({
            "id": q["id"], "section": q.get("section") or "",
            "category": q.get("category", {}).get("description", ""),
            "question": q.get("question", ""),
            "answers": [{"text": a["text"], "value": a["value"]} for a in q.get("answers", [])],
            "correct": q.get("correctAnswer", ""),
            "feedback": q.get("feedback", ""),
        })
    manual = {"sections": [{"id": k, "title": v} for k, v in sorted(
        ((k, v) for k, v in section_titles.items() if k.isdigit()),
        key=lambda kv: int(kv[0]))],
              "subsections": subs}
    (OUT / "manual.json").write_text(json.dumps(manual, indent=1), encoding="utf-8")
    (OUT / "quiz.json").write_text(json.dumps(questions, indent=1), encoding="utf-8")
    print(f"[manual] {len(subs)} subsections, {len(questions)} questions")


def parse_services() -> None:
    html = (RAW / "pages" / "online-services-all.html").read_text(encoding="utf-8")
    main = main_of(html)
    headings = [m for m in re.finditer(
        r'<h2[^>]*>\s*(?:<[^>]*>\s*)*([^<]+?)\s*(?:<[^>]*>\s*)*</h2>', main)]
    services = []
    for i, hm in enumerate(headings):
        cat = unescape(hm.group(1)).strip()
        if cat in ("", "Breadcrumb"):
            continue
        start = hm.end()
        end = headings[i + 1].start() if i + 1 < len(headings) else len(main)
        seg = main[start:end]
        for lm in re.finditer(
                r'<a href="([^"]+)"[^>]*>\s*(?:<[^>]*>\s*)*([^<]{3,90}?)\s*(?:<[^>]*>\s*)*</a>', seg):
            url, label = lm.group(1), unescape(lm.group(2)).strip()
            if url.startswith("#") or not label:
                continue
            services.append({"category": cat, "label": label, "url": url})
    (OUT / "services.json").write_text(json.dumps(services, indent=1), encoding="utf-8")
    print(f"[services] {len(services)} online services")


def main() -> int:
    OUT.mkdir(exist_ok=True)
    build_pages()
    parse_offices()
    parse_plates()
    parse_forms()
    parse_news()
    parse_manual()
    parse_services()
    return 0


if __name__ == "__main__":
    sys.exit(main())
