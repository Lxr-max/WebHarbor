#!/usr/bin/env python3
"""Phase 9: normalize the scraped_data/ captures into the frozen tracked
source_data/*.json snapshots that app.py seeds from.

Everything here is deterministic: given the same scraped_data/ captures the
output is byte-identical (sorted keys, fixed iteration order).

Run:  python3.11 build_source_data.py
"""
import csv
import hashlib
import html
import hashlib
import json
import pathlib
import re
import urllib.parse

from bs4 import BeautifulSoup

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRAPED = ROOT / "scraped_data"
SOURCE = ROOT / "source_data"
SOURCE.mkdir(exist_ok=True)

# Form detail-page slugs that become FormPage rows (upstream form pages).
FORM_PAGE_SLUGS = [
    "i485", "n400", "i765", "i693", "i130", "i90", "i131", "i751",
    "i9", "n336", "ar11", "g1450",
]
FORM_PAGE_PATH = {
    "i485": "/i-485", "n400": "/n-400", "i765": "/i-765", "i693": "/i-693",
    "i130": "/i-130", "i90": "/i-90", "i131": "/i-131", "i751": "/i-751",
    "i9": "/i-9", "n336": "/n-336", "ar11": "/ar-11", "g1450": "/g-1450",
}
# Pages whose content is served by a dedicated route (never generic pages).
NON_GENERIC = {
    "forms", "feecalculator", "glossary", "find_civil_surgeon",
    "eligibility_tool", "field_offices", "asc_list",
}
# Page slug -> upstream path (the scrape list), kept in sync with scrape_www.
SLUG_PATHS = {}
_p = pathlib.Path(__file__).with_name("scrape_www.py").read_text()
for m in re.finditer(r'\("(/[a-z0-9/-]*)", "([a-z0-9_]+)"\)', _p):
    SLUG_PATHS[m.group(2)] = m.group(1)

SERVICE_CENTERS = {
    "NBC": "National Benefits Center",
    "CSC": "California Service Center",
    "NSC": "Nebraska Service Center",
    "SSC": "Texas Service Center",
    "ESC": "Vermont Service Center",
    "YSC": "Potomac Service Center",
    "IOE": "USCIS Online Account (ELIS)",
}


def load_images_manifest():
    path = SCRAPED / "images_manifest.json"
    return json.loads(path.read_text()) if path.exists() else {}


def local_for(url, manifest):
    hit = manifest.get(url)
    if hit and hit.get("file"):
        return "images/upstream/" + hit["file"]
    # try without query string
    hit = manifest.get(url.split("?")[0])
    if hit and hit.get("file"):
        return "images/upstream/" + hit["file"]
    return None


def dump(name, data):
    path = SOURCE / name
    path.write_text(json.dumps(data, indent=1, sort_keys=False, ensure_ascii=False))
    print(f"wrote {name}: {len(data) if isinstance(data, list) else list(data)[:8] if len(str(data)) < 200 else 'ok'}")


def build_pages(manifest):
    out = []
    for jf in sorted((SCRAPED / "pages").glob("*.json")):
        slug = jf.stem
        if slug in NON_GENERIC or slug == "home_es":
            continue
        rec = json.loads(jf.read_text())
        path = rec.get("url", "").replace("https://www.uscis.gov", "") or SLUG_PATHS.get(slug, "/" + slug)
        hero = None
        for img in rec.get("images", []):
            hero = local_for(img["src"], manifest)
            if hero:
                break
        out.append({
            "slug": slug,
            "path": path,
            "title": rec["title"],
            "last_reviewed": rec.get("last_reviewed", ""),
            "alerts": rec.get("alerts", []),
            "sections": rec.get("sections", []),
            "tables": rec.get("tables", []),
            "links": rec.get("links", []),
            "hero_image": hero,
        })
    dump("pages.json", out)


def build_forms_catalog():
    html = (SCRAPED / "pages" / "forms.html").read_text()
    soup = BeautifulSoup(html, "html.parser")
    rows = []
    for row in soup.select("main .views-row"):
        a = row.select_one(".views-field-title a")
        if not a:
            continue
        label = " ".join(a.get_text(" ", strip=True).split())
        m = re.match(r"^([A-Z0-9-]+(?:CW|S|F|A|J|R)?)\s*\|\s*(.+)$", label)
        number = m.group(1) if m else label.split("|")[0].strip()
        title = m.group(2) if m else label.split("|", 1)[-1].strip()
        desc = row.select_one(".views-field-body .field-content")
        online = row.select_one('a.btn[href*="my.uscis.gov/file-a-form"]') is not None
        rows.append({
            "number": number,
            "title": title,
            "description": " ".join(desc.get_text(" ", strip=True).split()) if desc else "",
            "detail_path": a["href"],
            "file_online": online,
        })
    dump("forms_catalog.json", rows)


def build_form_fees():
    out = []
    for jf in sorted((SCRAPED / "fees").glob("*.json")):
        rec = json.loads(jf.read_text())
        rows = rec.get("rows", [])
        clean = []
        for r in rows:
            cells = r.get("cells", [])
            if len(cells) >= 2:
                clean.append({"category": cells[0], "fees": cells[1:]})
        out.append({"nid": rec["nid"], "label": rec["label"], "rows": clean})
    dump("form_fees.json", out)


def build_form_pages(manifest):
    pdf_index = {p["file"]: p for p in json.loads((SCRAPED / "pdf_index.json").read_text())}
    out = []
    for slug in FORM_PAGE_SLUGS:
        jf = SCRAPED / "pages" / f"{slug}.json"
        if not jf.exists():
            continue
        rec = json.loads(jf.read_text())
        html = jf.with_suffix(".html").read_text()
        # edition date: the paragraph that starts with the MM/DD/YY edition
        edition = ""
        for section in rec.get("sections", []):
            for para in section.get("paragraphs", []):
                m = re.match(r"^([0-9]{2}/[0-9]{2}/[0-9]{2,4})\s*\.", para)
                if m:
                    edition = m.group(1)
                    break
            if edition:
                break
        if not edition:
            m = re.search(r"Edition Date[^0-9]*([0-9]{2}/[0-9]{2}/[0-9]{2,4})", html)
            if m:
                edition = m.group(1)
        pdfs = []
        seen = set()
        for href, text in re.findall(r'href="([^"]+\.pdf[^"]*)"[^>]*>([^<]{0,80})', html):
            if "document/forms/" not in href and "document/guides/" not in href:
                continue
            fname = href.rsplit("/", 1)[-1]
            if fname in seen or fname not in pdf_index:
                continue
            seen.add(fname)
            pdfs.append({"file": fname, "label": text.strip() or fname,
                         "size": pdf_index[fname]["bytes"]})
        out.append({
            "path": FORM_PAGE_PATH[slug],
            "title": rec["title"],
            "last_reviewed": rec.get("last_reviewed", ""),
            "edition": edition,
            "sections": rec.get("sections", []),
            "tables": rec.get("tables", []),
            "alerts": rec.get("alerts", []),
            "pdfs": pdfs,
        })
    dump("form_pages.json", out)


def build_news(manifest):
    index = json.loads((SCRAPED / "news" / "_index.json").read_text())
    teasers = {i["url"]: i.get("teaser", "") for i in index["items"]}
    lists = {i["url"]: i.get("list") for i in index["items"]}
    out = []
    for jf in sorted((SCRAPED / "news").glob("*.json")):
        if jf.name.startswith("_"):
            continue
        rec = json.loads(jf.read_text())
        url = rec.get("url", "")
        kind = "alert" if "/alerts/" in url else "release"
        image = None
        for img in rec.get("images", []):
            image = local_for(img["src"], manifest)
            if image:
                break
        # the display date lives in a <time> tag on the captured page
        raw_html = jf.with_suffix(".html")
        display_date = rec.get("release_date", "")
        if raw_html.exists():
            m = re.search(r'field--name-field-display-date.*?<time[^>]*>([^<]+)</time>',
                          raw_html.read_text(), re.S)
            if m:
                display_date = m.group(1).strip()
        out.append({
            "kind": kind,
            "slug": url.rstrip("/").rsplit("/", 1)[-1],
            "title": rec["title"],
            "date": display_date,
            "teaser": teasers.get(url, ""),
            "list": lists.get(url, ""),
            "sections": rec.get("sections", []),
            "alerts": rec.get("alerts", []),
            "links": rec.get("links", []),
            "image": image,
        })
    dump("news.json", out)


def build_glossary():
    html = (SCRAPED / "pages" / "glossary.html").read_text()
    soup = BeautifulSoup(html, "html.parser")
    terms = []
    for h in soup.select("h4.accordion__header"):
        term = " ".join(h.get_text(" ", strip=True).split())
        panel = h.find_next_sibling("div")
        definition = " ".join(panel.get_text(" ", strip=True).split()) if panel else ""
        if term and definition:
            terms.append({"term": term, "definition": definition})
    dump("glossary.json", terms)


def build_field_offices():
    offices = {}
    with open(SCRAPED / "offices" / "field_office_by_zip.csv", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            if row["IsRetired"].upper() == "TRUE":
                continue
            des = row["FieldOfficeDesignation"]
            if des in offices:
                continue
            offices[des] = {
                "designation": des,
                "name": row["FieldOfficeName"],
                "street": row["FieldOfficeStreetAddress"],
                "city": row["FieldOfficeCity"],
                "state": row["FieldOfficeState"],
                "zip": row["FieldOfficeZipCode"],
                "district_code": row["DistrictDesignation"],
                "district_name": row["DistrictName"],
                "region": row["Region"],
                "service_center": row["ServiceCenter"],
            }
    dump("field_offices.json", {"offices": [offices[k] for k in sorted(offices)]})


def build_surgeons():
    index = json.loads((SCRAPED / "locator" / "_index.json").read_text())
    zips = {}
    for jf in sorted((SCRAPED / "locator").glob("*.json")):
        if jf.name.startswith("_"):
            continue
        rec = json.loads(jf.read_text())
        details = []
        for payload in rec.get("details", []):
            if isinstance(payload, list):
                details.extend(payload)
            elif isinstance(payload, dict) and "name" in payload:
                details.append(payload)
        rows = []
        for d in details:
            if not isinstance(d, dict) or not d.get("name"):
                continue
            contacts = []
            raw = d.get("contacts") or "[]"
            try:
                contacts = json.loads(raw) if isinstance(raw, str) else raw
            except ValueError:
                contacts = []
            rows.append({
                "id": d.get("id"), "name": html.unescape(d.get("name") or ""),
                "address1": html.unescape(d.get("address1") or ""),
                "address2": html.unescape(d.get("address2") or ""),
                "city": html.unescape(d.get("city") or ""), "distance": d.get("distance"),
                "email": d.get("email"), "website": d.get("website"),
                "contacts_list": [
                    {"name": html.unescape(f"DR. {c.get('first_name','')} {c.get('last_name','')}").strip(),
                     "gender": c.get("gender"), "phone": c.get("phone"),
                     "languages": html.unescape(c.get("languages") or "")}
                    for c in contacts
                ],
            })
        zips[rec["zip"]] = {
            "label": rec.get("label"),
            "lat": rec.get("geocode", {}).get("lat"),
            "lng": rec.get("geocode", {}).get("lng"),
            "results": rows,
        }
    data = {
        "doctor_count": index.get("doctor_count"),
        "languages": index.get("languages", []),
        "genders": index.get("genders", []),
        "zips": zips,
    }
    dump("surgeons.json", data)


def build_processing_times():
    records = json.loads((SCRAPED / "processing_times" / "records.json").read_text())
    office_names = {}
    with open(SCRAPED / "offices" / "field_office_by_zip.csv", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            des = row["FieldOfficeDesignation"]
            if des not in office_names:
                office_names[des] = row["FieldOfficeName"]
    out = []
    for r in records:
        code = r.get("office_code", "")
        name = office_names.get(code) or SERVICE_CENTERS.get(code, code)
        subtypes = []
        pub = r.get("publication_date")
        srd = r.get("service_request_date")
        for s in r.get("subtypes", []) or []:
            subtypes.append({
                "form_type": s.get("form_type"),
                "range": s.get("range", []),
                "publication_date": s.get("publication_date"),
                "service_request_date": s.get("service_request_date"),
            })
            if not pub:
                pub = s.get("publication_date")
            if not srd:
                srd = s.get("service_request_date")
        out.append({
            "form": r.get("form_name", ""),
            "form_info": r.get("form_info_en", ""),
            "office_code": code,
            "office_name": name,
            "range": r.get("range", []),
            "subtypes": subtypes,
            "publication_date": pub,
            "service_request_date": srd,
            "snapshot_date": r.get("_snapshot_date", ""),
        })
    dump("processing_times.json", {"records": out, "service_centers": SERVICE_CENTERS})


def build_wizard():
    src = SCRAPED / "eligibility" / "wizard.json"
    if not src.exists():
        print("eligibility wizard capture missing; skipped")
        return
    data = json.loads(src.read_text())
    # States were captured when reached from the BFS queue; terminal (outcome)
    # pages appear as edge endpoints, so collect the union of both. Outcome
    # pages share their headline but carry branch-specific explanation text,
    # so their state key includes the text hash to keep every distinct outcome.
    states = {}
    for sid, st in sorted(data.get("states", {}).items(), key=lambda kv: int(kv[0][1:])):
        key = st["question"][:140] + "||" + "|".join(st["options"])[:140]
        states[key] = {"question": st.get("question", ""), "options": st.get("options", []),
                       "outcome": st.get("outcome", False), "text": st.get("text", "")}

    def outcome_key(e):
        return (e["to_state"] + "##"
                + hashlib.sha256(e.get("to_text", "").encode("utf-8")).hexdigest()[:12])

    for e in data.get("edges", []):
        key = outcome_key(e) if e.get("to_outcome") else e["to_state"]
        if key not in states:
            states[key] = {"question": e.get("to_question", ""), "options": [],
                           "outcome": e.get("to_outcome", False), "text": e.get("to_text", "")}
    key_by_raw = {}
    ordered = []
    for key, st in states.items():
        key_by_raw[key] = f"q{len(ordered)}"
        ordered.append({"key": key_by_raw[key], "question": st["question"],
                        "options": st["options"], "outcome": st["outcome"], "text": st["text"]})
    edges = []
    for e in data.get("edges", []):
        to_key = outcome_key(e) if e.get("to_outcome") else e["to_state"]
        from_key = key_by_raw.get(e["from"])
        to_key = key_by_raw.get(to_key)
        if from_key and to_key:
            edges.append({"from": from_key, "option": e["option"], "to": to_key,
                          "to_outcome": e.get("to_outcome", False)})
    dump("eligibility_wizard.json", {"states": ordered, "edges": edges})


def build_appointment():
    text = (SCRAPED / "appointment" / "landing.txt").read_text()
    reasons = ["ADIT Stamp", "Emergency Advance Parole (EAP)",
              "Immigration Judge Grant", "Other"]
    quick = re.findall(r"I want to [^\n]+", text)
    intl = "If you are outside the United States, select the international USCIS office with jurisdiction for your residence to schedule an appointment."
    asylum = [l.strip() for l in text.splitlines() if "asylum" in l.lower()][:6]
    data = {
        "reasons": reasons,
        "quick_links": quick,
        "international_note": intl,
        "asylum_notes": asylum,
    }
    dump("appointment.json", data)


def build_case_status():
    """The captured case-status tool chrome (see casestatus/ for provenance)."""
    data = {
        "header": "Case Status Online",
        "error_text": ("My Case Status does not recognize the receipt number entered. "
                       "Please check your receipt number and try again. If you need further "
                       "assistance, please call the National Customer Service Center at "
                       "1-800-375-5283."),
        "related_tools": [
            "Change of Address", "Submit a Case Inquiry",
            "USCIS Processing Times Information", "USCIS Office Locations",
        ],
        "captured_from": "egov.uscis.gov/casestatus/mycasestatus.do "
                         "(Internet Archive snapshot 20161118095553); the live tool is "
                         "Cloudflare-WAF-blocked from the build network (HTTP 403).",
    }
    dump("case_status_tool.json", data)


def main():
    manifest = load_images_manifest()
    build_pages(manifest)
    build_forms_catalog()
    build_form_fees()
    build_form_pages(manifest)
    build_news(manifest)
    build_glossary()
    build_field_offices()
    build_surgeons()
    build_processing_times()
    build_wizard()
    build_appointment()
    build_case_status()
    # raw dataset copies tracked verbatim
    csv_src = SCRAPED / "offices" / "field_office_by_zip.csv"
    (SOURCE / "field_office_by_zip.csv").write_bytes(csv_src.read_bytes())
    print("wrote field_office_by_zip.csv")


if __name__ == "__main__":
    main()
