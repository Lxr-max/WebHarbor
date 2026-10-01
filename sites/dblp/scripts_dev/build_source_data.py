#!/usr/bin/env python3
"""Build the tracked source_data/*.json snapshots from the raw captures.

Everything materialized here traces to a file in scraped_data/captures/
(each with a .meta.json sidecar recording the exact URL + fetch time):

  - venues.json      venue streams + edition metadata, parsed from the
                     captured venue index pages (db/conf/<v>/index.html,
                     db/journals/<j>/index.html)
  - publications.json every record in the captured edition XMLs
                     (db/.../<edition>.xml), with authors/pids, pages,
                     doi/ee, mdate, crossref
  - authors.json     corpus authors; profile fields (affiliations, urls,
                     awards, upstream record count) from the captured
                     pid/<key>.xml profiles for the fetched authors
  - news.json        the dblp blog/news items from the captured homepage
  - stats.json       the upstream homepage statistics block
  - search_snapshots.json  upstream hit totals for the captured reference
                     search pages, kept as provenance context only

The mirror renders corpus-computed counts (declared in provenance.json);
the upstream totals are carried for context and provenance.
"""
import html
import json
import os
import re
import sys
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.dirname(HERE)
CAP = os.path.join(SITE, "scraped_data", "captures")
OUT = os.path.join(SITE, "source_data")

CONFS = ["sigmod", "nips", "icml", "kdd", "cvpr", "acl", "sigcomm",
         "sosp", "stoc", "sp", "www", "iclr"]
JOURNALS = ["tods", "vldb", "jmlr", "tmlr", "tois", "pacmmod", "tifs",
            "cacm", "pvldb"]
# Corpus bound (declared in provenance.json): the huge ML/CV venues keep
# their most recent main edition only, other conferences keep 3 recent
# years (www keeps 2), journals keep 3-5 recent volumes as listed below.
CONF_EDITIONS = {"nips": 1, "icml": 1, "cvpr": 1, "iclr": 1,
                 "sigmod": 3, "kdd": 2, "acl": 2, "sigcomm": 3,
                 "sosp": 3, "stoc": 3, "sp": 3, "www": 2}
JOURNAL_VOLUMES = {"tods": 5, "vldb": 5, "tois": 5, "pacmmod": 5,
                   "jmlr": 3, "tmlr": 2, "tifs": 3, "cacm": 3, "pvldb": 3}

TYPE_LABELS = {
    "informal": "Informal Publications",
    "informal publication": "Informal Publications",
    "article and magazine": "Journal Articles (selected)",
    "journal": "Journal Articles",
    "inproceedings": "Conference and Workshop Papers",
    "proceedings": "Editorships",
    "book": "Books and Theses",
    "incollection": "Books and Theses",
    "phdthesis": "Books and Theses",
    "mastersthesis": "Books and Theses",
    "data": "Data and Artifacts",
    "software": "Data and Artifacts",
    "editorship": "Editorships",
    "issue": "Editorships",
}


def cap(name):
    return os.path.join(CAP, name)


def text_of(el):
    if el is None:
        return None
    return "".join(el.itertext()).strip()


# --------------------------------------------------------------- venues ----

def parse_conf_venue(venue):
    t = open(cap(f"db_conf_{venue}_index_html.html"), encoding="utf-8").read()
    m = re.search(r'<header id="headline"[^>]*>\s*<h1[^>]*>(.*?)</h1>', t, re.S)
    name = html.unescape(re.sub(r"<[^>]+>", "", m.group(1)).strip())
    m2 = re.search(r'<div class="note-line">(.*?)</div>', t, re.S)
    note = html.unescape(re.sub(r"<[^>]+>", "", m2.group(1)).strip()) if m2 else None
    # abbreviation in parens, e.g. "ACM SIGMOD Conference (SIGMOD)"
    abbr = None
    m3 = re.search(r"\(([^()]{2,20})\)$", name)
    if m3:
        abbr = m3.group(1)
    # venue information list (predecessor / has part / ...)
    info = []
    mi = re.search(r'<h2>Venue Information</h2>.*?<div class="hide-body">(.*?)</div>', t, re.S)
    if mi:
        for li in re.findall(r"<li>(.*?)</li>", mi.group(1), re.S):
            lab = re.search(r"<em>(.*?)</em>", li)
            txt = html.unescape(re.sub(r"<[^>]+>", "", li).strip())
            label = lab.group(1).rstrip(":").strip() if lab else ""
            if lab:
                txt = txt.replace(lab.group(1), "", 1)
                txt = txt.lstrip(":").strip()
            info.append({"label": label, "text": txt})
    # editions: h2 sections with editor toc entries
    sections = re.split(r'(?=<h2 id=")', t)
    editions = []
    for s in sections[1:]:
        mh = re.match(r'<h2 id="(\d{4})">(.*?)</h2>', s)
        if not mh:
            continue
        year, title = mh.group(1), html.unescape(
            re.sub(r"<[^>]+>", "", mh.group(2)).strip())
        # proceedings published in (cross-listed journal volumes)
        cross = re.findall(
            r'<p>Proceedings published in: <a href="https://dblp.org/db/journals/[^"]*/([a-z]+\d+)\.html[^"]*">(.*?)</a></p>',
            s)
        pairs = re.findall(
            r'<li class="entry editor toc" id="(conf/%s/[^"]+)"[^>]*>.*?'
            r'<a href="https://dblp.org/db/conf/%s/([^"]+)\.html" itemprop="url"' % (venue, venue),
            s, re.S)
        for eid, toc in pairs:
            editions.append({
                "key": eid, "toc": toc, "year": year, "title": title,
                "cross_listed": [c[0] for c in cross],
            })
    return {"stream": f"conf/{venue}", "type": "Conference and Workshop Papers",
            "name": name, "abbr": abbr, "note": note, "info": info,
            "editions": editions}


def parse_journal_venue(journal):
    t = open(cap(f"db_journals_{journal}_index_html.html"), encoding="utf-8").read()
    m = re.search(r'<header id="headline"[^>]*>\s*<h1[^>]*>(.*?)</h1>', t, re.S)
    name = html.unescape(re.sub(r"<[^>]+>", "", m.group(1)).strip())
    abbr = None
    m3 = re.search(r"\(([^()]{2,20})\)$", name)
    if m3:
        abbr = m3.group(1)
    info = []
    mi = re.search(r'<h2>Venue Information</h2>.*?<div class="hide-body">(.*?)</div>', t, re.S)
    if mi:
        for li in re.findall(r"<li>(.*?)</li>", mi.group(1), re.S):
            lab = re.search(r"<em>(.*?)</em>", li)
            txt = html.unescape(re.sub(r"<[^>]+>", "", li).strip())
            label = lab.group(1).rstrip(":").strip() if lab else ""
            if lab:
                txt = txt.replace(lab.group(1), "", 1)
                txt = txt.lstrip(":").strip()
            info.append({"label": label, "text": txt})
    vols = []
    seen = set()
    for v, label in re.findall(
            r'href="https://dblp.org/db/journals/%s/([a-z]+\d+)\.html"[^>]*>([^<]+)<' % journal, t):
        if v not in seen:
            seen.add(v)
            vols.append({"key": v, "label": html.unescape(label.strip())})
    return {"stream": f"journals/{journal}", "type": "Journal Articles",
            "name": name, "abbr": abbr, "info": info, "volumes": vols}


# ----------------------------------------------------------- publications --

def parse_edition_xml(path):
    """Parse one captured dblp ToC .xml variant (bht format).

    The bht pages interleave <h2> section headers with <r>...</r> record
    blocks; each record is tagged with the section it appears under
    (issues for journal volumes, tracks for proceedings)."""
    raw = open(path, encoding="utf-8").read()
    bht_title = re.search(r'<bht[^>]*title="([^"]*)"', raw)
    bht_title = bht_title.group(1) if bht_title else None
    events = []
    for m in re.finditer(r"<h2>(.*?)</h2>", raw, re.S):
        events.append((m.start(), "h2", re.sub(r"<[^>]+>", "", m.group(1)).strip()))
    for m in re.finditer(r"<r(?:\s[^>]*)?>(.*?)</r>", raw, re.S):
        events.append((m.start(), "r", m.group(0)))
    events.sort()
    records = []
    proceedings = None
    section = None
    for _, kind, payload in events:
        if kind == "h2":
            section = payload
            continue
        block = payload
        try:
            root = ET.fromstring(re.sub(r'&(?!(?:\w+|#\d+|#x[0-9a-fA-F]+);)', '&amp;', block))
        except ET.ParseError:
            continue
        for child in root:
            tag = child.tag
            if tag in ("proceedings", "journal", "book", "series"):
                if proceedings is None:
                    proceedings = parse_container(child, tag)
                continue
            rec = parse_record(child, tag)
            if rec:
                rec["section"] = section
                records.append(rec)
    return bht_title, proceedings, records


def parse_container(el, tag):
    return {
        "key": el.get("key"), "mdate": el.get("mdate"), "type": tag,
        "title": text_of(el.find("title")),
        "publisher": text_of(el.find("publisher")),
        "year": text_of(el.find("year")),
        "volume": text_of(el.find("volume")),
        "ee": [e.text for e in el.findall("ee")],
        "editors": [a.text for a in el.findall("editor")],
        "editor_pids": [a.get("pid") for a in el.findall("editor")],
    }


def parse_record(el, tag):
    rec = {
        "key": el.get("key"), "mdate": el.get("mdate"), "type": tag,
        "title": text_of(el.find("title")),
        "year": text_of(el.find("year")),
        "pages": text_of(el.find("pages")),
        "volume": text_of(el.find("volume")),
        "number": text_of(el.find("number")),
        "booktitle": text_of(el.find("booktitle")),
        "journal": text_of(el.find("journal")),
        "crossref": text_of(el.find("crossref")),
        "url": text_of(el.find("url")),
        "doi": text_of(el.find("doi")),
        "ee": [e.text for e in el.findall("ee")],
        "authors": [],
    }
    for a in el.findall("author"):
        rec["authors"].append({"pid": a.get("pid"), "name": a.text,
                               "orcid": a.get("orcid")})
    if not rec["title"] or not rec["year"]:
        return None
    return rec

# ------------------------------------------------------------------ main --

def parse_homepage():
    t = open(cap("root.html"), encoding="utf-8").read()
    news = []
    m = re.search(r'<dl class="news">(.*?)</dl>', t, re.S)
    if m:
        for dt in re.findall(r"<dt[^>]*>(.*?)</dt>", m.group(1), re.S):
            link = re.search(r'href="([^"]+)"', dt)
            label = re.sub(r"<[^>]+>", "", dt)
            label = html.unescape(re.sub(r"\s+", " ", label)).strip()
            tags = re.findall(r"<small>\[(.*?)\]</small>", dt)
            mm = re.match(r"(\d{4}-\d{2}-\d{2}):\s*(.*)", label)
            news.append({
                "date": mm.group(1) if mm else None,
                "title": (mm.group(2) if mm else label).strip(),
                "url": link.group(1) if link else None,
                "tags": tags,
            })
    stats = {}
    ms = re.search(r'<h2>dblp statistics</h2>(.*?)</div>', t, re.S)
    if ms:
        for li in re.findall(r"<li>(.*?)</li>", ms.group(1), re.S):
            txt = html.unescape(re.sub(r"<[^>]+>", "", li)).strip()
            kv = re.match(r"# of ([^:]+)\s*:\s*([\d,]+)", txt)
            if kv:
                stats[kv.group(1).strip()] = kv.group(2)
    return news, stats


def parse_search_snapshot(fn):
    t = open(cap(fn), encoding="utf-8").read()
    out = {}
    for m in re.finditer(r"found ([\d,]+) matches", t):
        out["matches"] = m.group(1)
    for m in re.finditer(r"All (\d+) matches", t):
        out["matches"] = m.group(1)
    return out


def parse_author_profiles():
    """Merge the captured pid/<key>.xml profiles into the corpus authors.

    Each capture is the upstream dblp person record: display name, upstream
    record count (n), homepage/authority urls, affiliation notes (with the
    'former' label where applicable), unicode name and awards."""
    profiles = {}
    for fn in sorted(os.listdir(CAP)):
        if not fn.startswith('pid_') or not fn.endswith('_xml.html'):
            continue
        path = os.path.join(CAP, fn)
        raw = open(path, encoding='utf-8').read()
        m = re.search(r'<dblpperson name="([^"]*)" pid="([^"]*)" n="(\d+)"', raw)
        if not m:
            continue
        name, pid, n = m.group(1), m.group(2), int(m.group(3))
        urls = re.findall(r'<url>([^<]+)</url>', raw)
        affiliations, awards, uname = [], [], None
        for attrs, text in re.findall(r'<note([^>]*)>([^<]*)</note>', raw):
            text = html.unescape(text)
            if 'type="affiliation"' in attrs:
                lab = re.search(r'label="([^"]*)"', attrs)
                affiliations.append({'label': lab.group(1) if lab else '',
                                     'text': text})
            elif 'type="award"' in attrs:
                lab = re.search(r'label="([^"]*)"', attrs)
                awards.append({'label': lab.group(1) if lab else '',
                               'text': text})
            elif 'type="uname"' in attrs:
                uname = text
        profiles[pid] = {
            'pid': pid, 'name': name, 'n_upstream': n, 'urls': urls,
            'affiliations': affiliations, 'awards': awards, 'uname': uname,
            'profile_fetched': True,
        }
    return profiles


def main():
    os.makedirs(OUT, exist_ok=True)
    venues = []
    for v in CONFS:
        venues.append(parse_conf_venue(v))
    for j in JOURNALS:
        venues.append(parse_journal_venue(j))
    with open(os.path.join(OUT, "venues.json"), "w") as f:
        json.dump(venues, f, indent=1, sort_keys=True)
    print(f"venues.json: {len(venues)} venues")

    # publications from the captured edition XMLs
    pubs = []
    containers = {}
    for fn in sorted(os.listdir(CAP)):
        if not (fn.endswith(".html") and "_xml" in fn):
            continue
        path = os.path.join(CAP, fn)
        meta = json.load(open(path + ".meta.json"))
        url = meta["url"]
        mm = re.match(r"https://dblp.org/db/(conf|journals)/([a-z0-9]+)/([a-z0-9-]+)\.xml$",
                      url)
        if not mm:
            continue
        stream = f"{mm.group(1)}/{mm.group(2)}"
        bht_title, proc, recs = parse_edition_xml(path)
        vol_key = f"{stream}/{mm.group(3)}"
        if proc:
            containers[proc["key"]] = proc
        for r in recs:
            r["stream"] = stream
            if not r.get("crossref") and stream.startswith("journals/"):
                r["crossref"] = vol_key
            if stream.startswith("journals/") and vol_key not in containers:
                containers[vol_key] = {
                    "key": vol_key, "type": "journal", "title": bht_title,
                    "publisher": None, "year": None, "editors": [],
                    "editor_pids": [],
                }
            pubs.append(r)
    # corpus bound: keep only the selected editions per venue (most recent
    # first, matching the edition order the venue index pages list)
    keep_editions = set()
    for v in venues:
        if v["stream"].startswith("conf/"):
            venue = v["stream"].split("/")[1]
            n_keep = CONF_EDITIONS.get(venue, 3)
            main_years = []
            for ed in v["editions"]:
                y = ed["year"]
                if re.fullmatch(r"conf/%s/%s(-\d+)?" % (venue, y), ed["key"]):
                    if y not in main_years:
                        main_years.append(y)
            keep_years = set(main_years[:n_keep])
            for ed in v["editions"]:
                if ed["year"] in keep_years and re.fullmatch(
                        r"conf/%s/%s(-\d+)?" % (venue, ed["year"]), ed["key"]):
                    keep_editions.add(ed["key"])
        else:
            venue = v["stream"].split("/")[1]
            n_vols = JOURNAL_VOLUMES.get(venue, 3)
            keep_vols = {vol["key"] for vol in v["volumes"][:n_vols]}
            for vol in keep_vols:
                keep_editions.add(f"journals/{venue}/{vol}")
    kept_pubs = []
    for p in pubs:
        if p.get("crossref") in keep_editions:
            kept_pubs.append(p)
    kept_pubs.sort(key=lambda r: r["key"])
    with open(os.path.join(OUT, "publications.json"), "w") as f:
        json.dump(kept_pubs, f, separators=(',', ':'), sort_keys=True)
        f.write('\n')
    with open(os.path.join(OUT, "containers.json"), "w") as f:
        json.dump({k: c for k, c in sorted(containers.items())
                   if k in keep_editions}, f, separators=(',', ':'), sort_keys=True)
        f.write('\n')
    print(f"publications.json: {len(kept_pubs)} of {len(pubs)} captured records "
          f"({len(keep_editions)} editions kept)")

    # authors: distinct pids in the kept corpus, merged with the captured
    # upstream person profiles where available
    profiles = parse_author_profiles()
    seen = {}
    for p in kept_pubs:
        for a in p["authors"]:
            if a["pid"]:
                seen.setdefault(a["pid"], a["name"])
    authors = []
    for pid, name in sorted(seen.items()):
        if pid in profiles:
            authors.append(profiles[pid])
        else:
            authors.append({"pid": pid, "name": name})
    with open(os.path.join(OUT, "authors.json"), "w") as f:
        json.dump(authors, f, separators=(',', ':'), sort_keys=True)
        f.write('\n')
    print(f"authors.json: {len(authors)} corpus authors")

    # homepage news + upstream statistics
    news, stats = parse_homepage()
    with open(os.path.join(OUT, "news.json"), "w") as f:
        json.dump(news, f, indent=1, sort_keys=True)
    with open(os.path.join(OUT, "stats.json"), "w") as f:
        json.dump(stats, f, indent=1, sort_keys=True)
    print(f"news.json: {len(news)} items; stats.json: {len(stats)} counters")

    # upstream search totals for the captured reference queries (context)
    snaps = {}
    for fn, q in [
        ("search_publ_q_attention_is_all_you_need.html", "attention is all you need"),
        ("search_q_graph_neural_networks.html", "graph neural networks"),
        ("search_publ_q_learning_h_30_f_30.html", "learning"),
        ("search_venue_q_sigmod.html", "sigmod"),
        ("search_author_q_jiawei_han.html", "jiawei han"),
    ]:
        if os.path.exists(cap(fn)):
            snaps[q] = parse_search_snapshot(fn)
    with open(os.path.join(OUT, "search_snapshots.json"), "w") as f:
        json.dump(snaps, f, indent=1, sort_keys=True)
    print(f"search_snapshots.json: {len(snaps)} reference queries")


if __name__ == "__main__":
    main()
