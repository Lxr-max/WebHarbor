#!/usr/bin/env python3
"""Build the tracked source_data/*.json snapshots from the raw captures.

Every output record derives from a real HTTP-200 capture under
scraped_data/captures/ (see provenance.json for the per-source map):

  papers.json        5691 accepted papers (upstream orals-posters.json +
                     abstracts.json data files): title, authors with
                     institutions, topic, decision, session, room,
                     poster position, OpenReview link, abstract
  schedule.json      the six-day Rio calendar (Apr 22-27, 2026): simple
                     events with times/rooms plus the oral and poster
                     session blocks
  events.json        every non-paper event with its detail-page facts:
                     invited talks (speaker, headshot, overflow room),
                     workshops (organizers, abstract, project page,
                     internal schedule), socials, breaks, town hall,
                     test of time, expo talks, mentorship, registration
                     desks, remarks, reception
  sponsors.json      the tiered ICLR 2026 sponsor & exhibitor list
  organizers.json    the 23 organizer cards with roles, institutions,
                     portraits and bios
  awards.json        Outstanding Papers / Honorable Mention (blog) and
                     the Test of Time awards (blog)
  news.json          the nine blog.iclr.cc announcements the conference
                     pages reference
  dates.json         the ICLR 2026 + ICLR 2027 dates-and-deadlines groups
  registration.json  the captured registration structure: affiliation
                     types, purchasable items with the exclusivity rule,
                     the $50 guest banquet ticket, cancellation policy
  faq.json           the FAQ question/answer sections
  about.json         the About ICLR text and past-editions list
  venue.json         Riocentro venue facts + ICLR 2027 (California) notes

Run from sites/iclr:  python3 scripts_dev/build_source_data.py
"""
import html
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
CAP = ROOT / "scraped_data" / "captures"
OUT = ROOT / "source_data"

DAYS = {  # calendar day container -> ISO date + label
    "1": ("2026-04-22", "WED 22 APR"),
    "2": ("2026-04-23", "THU 23 APR"),
    "3": ("2026-04-24", "FRI 24 APR"),
    "4": ("2026-04-25", "SAT 25 APR"),
    "5": ("2026-04-26", "SUN 26 APR"),
    "6": ("2026-04-27", "MON 27 APR"),
}
DAY_OF_DATE = {d[0]: d[1] for d in DAYS.values()}


def cap(name):
    return (CAP / name).read_text(encoding="utf-8", errors="replace")


def text_of(seg):
    seg = re.sub(r"<script.*?</script>", "", seg, flags=re.S)
    seg = re.sub(r"<style.*?</style>", "", seg, flags=re.S)
    seg = re.sub(r"<[^>]+>", " ", seg)
    return html.unescape(re.sub(r"\s+", " ", seg)).strip()


def slugify(text):
    text = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return text[:80] or "untitled"


# ---------------------------------------------------------------- papers --

def build_papers():
    data = json.loads(cap("data_orals_posters"))
    abstracts = json.loads(cap("data_abstracts"))
    papers = []
    for row in data["results"]:
        pid = str(row["id"])
        abstract = abstracts.get(pid) or abstracts.get(str(row["sourceid"])) or ""
        if isinstance(abstract, dict):
            abstract = abstract.get("abstract", "")
        authors = [
            {"name": a.get("fullname") or "", "institution": a.get("institution") or ""}
            for a in row.get("authors") or []
        ]
        papers.append({
            "id": row["id"],
            "title": row["name"],
            "authors": authors,
            "topic": row.get("topic") or "",
            "decision": row.get("decision") or "",
            "eventtype": row.get("eventtype") or "",
            "session": row.get("session") or "",
            "room": row.get("room_name") or "",
            "start": row.get("starttime") or "",
            "end": row.get("endtime") or "",
            "poster_position": row.get("poster_position") or "",
            "openreview_url": row.get("paper_url") or "",
            "abstract": (abstract or "").strip(),
        })
    papers.sort(key=lambda p: p["id"])
    (OUT / "papers.json").write_text(json.dumps(papers, indent=1), encoding="utf-8")
    return papers


# -------------------------------------------------------------- schedule --

TIME_RE = re.compile(r"^(\d{1,2})(?::(\d{2}))?\s*([ap])\.?m\.?$", re.I)


def to_24h(label):
    label = (label or "").strip()
    low = label.lower()
    if low == "noon":
        return "12:00"
    if low in ("midnight", "12 midnight"):
        return "00:00"
    # session windows carry no AM/PM ("3:15-5:45"); the conference runs
    # 7:30 AM to 7:00 PM, so hours below seven are afternoon
    plain = re.match(r"^(\d{1,2}):(\d{2})$", label)
    if plain:
        hour = int(plain.group(1))
        if hour < 7:
            hour += 12
        return f"{hour:02d}:{plain.group(2)}"
    m = TIME_RE.match(label)
    if not m:
        return label
    hour = int(m.group(1))
    minute = m.group(2) or "00"
    half = m.group(3).lower()
    if hour == 12:
        hour = 0
    if half == "p":
        hour += 12
    return f"{hour:02d}:{minute}"


def build_schedule():
    t = cap("v_calendar")
    days = []
    # Walk the document in order: day containers, timeboxes, event blocks.
    token_re = re.compile(
        r'class="container2\s+day-(?P<day>\d+)"'
        r'|<div class="time">(?P<time>[^<]+)</div>'
        r'|<div class="eventsession pad (?P<kind>[\w-]+)\s*(?P<room>room-[^"]*)"'
        r'|class="(?P<sess>oral-session|poster-session) pad (?P<sroom>room-[^"]*)"'
    )
    cur_day = None
    cur_time = None
    sessions = {}
    for m in token_re.finditer(t):
        if m.group("day"):
            idx = m.group("day")
            date, label = DAYS.get(idx, (None, None))
            if date:
                days.append({"date": date, "label": label, "events": [],
                             "sessions": []})
            cur_day = days[-1] if days else None
        elif m.group("time"):
            cur_time = to_24h(m.group("time"))
        elif m.group("kind"):
            if cur_day is None:
                continue
            start = m.end()
            block = t[start:start + 2400]
            link = re.search(r'href="/virtual/2026/[a-z-]+/(\d+)">([^<]+)<', block)
            speaker = re.search(r'class="speaker-style">([^<]+)<', block)
            endm = re.search(r"\(ends ([^)<]+)\)", block)
            if link:
                cur_day["events"].append({
                    "id": int(link.group(1)),
                    "kind": m.group("kind"),
                    "title": html.unescape(link.group(2)).strip(),
                    "start": cur_time or "",
                    "end": to_24h(endm.group(1)) if endm else "",
                    "speaker": html.unescape(speaker.group(1)).strip() if speaker else "",
                })
        elif m.group("sess"):
            if cur_day is None:
                continue
            start = m.end()
            block = t[start:start + 1200]
            link = re.search(r'href="/virtual/2026/session/(\d+)">([^<]+?)\s*<', block, re.S)
            window = re.search(r'\[([^\]]+)\]', block)
            if link:
                entry = {
                    "id": int(link.group(1)),
                    "kind": m.group("sess"),
                    "title": html.unescape(re.sub(r"\s+", " ", link.group(2))).strip(),
                    "start": to_24h(window.group(1).split("-")[0]) if window else "",
                    "end": to_24h(window.group(1).split("-")[-1]) if window else "",
                }
                cur_day["sessions"].append(entry)
                sessions[entry["title"]] = entry
    (OUT / "schedule.json").write_text(json.dumps(
        {"days": days, "sessions": sessions}, indent=1), encoding="utf-8")
    return {"days": days, "sessions": sessions}


# ---------------------------------------------------------------- events --

def event_detail(kind, eid):
    """Parse one captured event detail page into a record."""
    t = cap(f"event_{kind}_{eid}")
    rec = {"id": int(eid), "kind": kind}
    i = t.find('<div class="detail-page-wrapper">')
    seg = t[i:] if i >= 0 else t
    # date window meta-pill: "Thu, Apr 23, 2026 &bull; 9:00 AM &ndash; 10:00 AM -03"
    mw = re.search(
        r"(\w{3}, \w{3} \d{1,2}, \d{4})\s*(?:&bull;|\u2022)\s*"
        r"([\d:]+\s*[AP]M)\s*(?:&ndash;|\u2013)\s*([\d:]+\s*[AP]M)", seg)
    if mw:
        rec["date"] = mw.group(1)
        rec["start"] = mw.group(2)
        rec["end"] = mw.group(3)
    # title
    mh = re.search(r'<h1 class="event-title">(.*?)</h1>', seg, re.S)
    if mh:
        rec["title"] = text_of(mh.group(1))
    # organizers / speaker line
    people = []
    mo = re.search(r'<div class="event-organizers">(.*?)</div>', seg, re.S)
    if mo:
        line = html.unescape(mo.group(1))
        people = [p.strip() for p in re.split(r"\u22c5", line) if p.strip()]
    rec["people"] = people
    # project page / website button
    mw2 = re.search(r'<a class="action-btn project" href="(https?://[^"]+)"', seg)
    if mw2:
        rec["website"] = mw2.group(1)
    # abstract paragraphs (upstream folds a leading "Overflow Room: ... - "
    # note into the first abstract paragraph; split it back out)
    abstract = ""
    ma = re.search(r'<div class="abstract-text-inner">(.*?)</div>\s*</div>', seg, re.S)
    if not ma:
        ma = re.search(r'<div class="abstract-text-inner">(.*?)</div>', seg, re.S)
    if ma:
        paras = [text_of(p) for p in re.findall(r"<p>(.*?)</p>", ma.group(1), re.S)]
        paras = [p for p in paras if p]
        if paras:
            first = paras[0]
            mo2 = re.match(r"Overflow Room:\s*([^-]+?)\s*-\s*(.*)$", first, re.S)
            if mo2:
                rec["overflow_room"] = html.unescape(mo2.group(1)).strip()
                paras[0] = mo2.group(2).strip()
        abstract = " ".join(paras)
    rec["abstract"] = abstract
    # speaker bios (invited talks): headshot + bio text; the upstream
    # serves /static/virtual/img/person_placeholder.svg for speakers
    # without a photo -- recorded as headshot_url="" so the mirror renders
    # a styled initial instead of mirroring the placeholder asset
    bi = seg.find('<div class="speaker-bios-list">')
    if bi >= 0:
        block = seg[bi:bi + 8000]
        mi = re.search(r'<img src="([^"]+)" class="speaker-bio-pic" alt="([^"]*)"', block)
        if mi and mi.group(1).startswith("http"):
            rec["headshot_url"] = mi.group(1)
            rec["headshot_alt"] = html.unescape(mi.group(2))
        elif mi:
            rec["headshot_url"] = ""
            rec["headshot_alt"] = html.unescape(mi.group(2))
        bio = re.search(r'<div class="speaker-bio-text">(.*?)</div>', block, re.S)
        if bio:
            rec["speaker_bio"] = text_of(bio.group(1))
    # workshop internal schedule table
    if kind == "workshop":
        sched = []
        for row in re.findall(r'<tr class="schedule-row".*?</tr>', seg, re.S):
            time_m = re.search(r'<span class="schedule-time">([^<]+)</span>', row)
            name_m = re.search(r'<span class="schedule-event-name"><a[^>]*>(.*?)</a></span>', row, re.S)
            auth_m = re.search(r'<div class="schedule-authors">([^<]*)</div>', row)
            if time_m and name_m:
                sched.append({
                    "time": html.unescape(time_m.group(1)).strip(),
                    "title": text_of(name_m.group(1)),
                    "speaker": html.unescape(auth_m.group(1)).strip() if auth_m else "",
                })
        rec["schedule"] = sched
    return rec


def build_events(schedule):
    events = []
    seen = set()
    for day in schedule["days"]:
        for ev in day["events"]:
            key = (ev["kind"], ev["id"])
            if key in seen:
                continue
            seen.add(key)
            try:
                detail = event_detail(ev["kind"], ev["id"])
            except FileNotFoundError:
                detail = {}
            rec = {
                "id": ev["id"], "kind": ev["kind"], "title": ev["title"],
                "date": day["date"], "day_label": day["label"],
                "start": ev["start"], "end": ev["end"],
                "speaker": detail.get("speaker") or (detail.get("people") or [""])[0],
                "people": detail.get("people") or [],
                "abstract": detail.get("abstract") or "",
                "website": detail.get("website") or "",
                "room": detail.get("room") or "",
                "overflow_room": detail.get("overflow_room") or "",
                "headshot_url": detail.get("headshot_url") or "",
                "headshot_alt": detail.get("headshot_alt") or "",
                "speaker_bio": detail.get("speaker_bio") or "",
                "detail_date": detail.get("date") or "",
                "detail_start": detail.get("start") or "",
                "detail_end": detail.get("end") or "",
                "schedule": detail.get("schedule") or [],
            }
            # calendar speaker beats page-derived fallbacks
            if ev.get("speaker"):
                rec["speaker"] = ev["speaker"]
            events.append(rec)
    events.sort(key=lambda e: (e["date"], e["start"], e["id"]))
    (OUT / "events.json").write_text(json.dumps(events, indent=1), encoding="utf-8")
    return events


# --------------------------------------------------------------- sponsors --

def build_sponsors():
    t = cap("v_sponsor_list")
    sponsors = []
    tier = None
    for m in re.finditer(
            r'<h3[^>]*level-bar[^>]*>([^<]+)</h3>|'
            r'<a target="_blank" href="(https?://[^"]+)"[^>]*class="sponsor-logo-link[^"]*">([^<]+)</a>',
            t):
        if m.group(1):
            tier = html.unescape(m.group(1)).strip()
        else:
            sponsors.append({"tier": tier, "name": html.unescape(m.group(3)).strip(),
                             "url": m.group(2)})
    (OUT / "sponsors.json").write_text(json.dumps(sponsors, indent=1), encoding="utf-8")
    return sponsors


# ------------------------------------------------------------- organizers --

def build_organizers():
    t = cap("v_organizers")
    bios = {}
    for m in re.finditer(r'<template id="bio-([\w-]+)">(.*?)</template>', t, re.S):
        bios[m.group(1)] = text_of(m.group(2))
    organizers = []
    for m in re.finditer(r'<article class="organizer-card[^"]*"([^>]*)>(.*?)</article>', t, re.S):
        attrs, body = m.group(1), m.group(2)
        def attr(name):
            am = re.search(rf'data-bs-{name}="([^"]*)"', attrs)
            return html.unescape(am.group(1)).strip() if am else ""
        name = attr("name")
        if not name:
            nm = re.search(r'organizer-name">([^<]+)<', body)
            name = html.unescape(nm.group(1)).strip() if nm else ""
        rm = re.search(r'organizer-role">([^<]+)<', body)
        im = re.search(r'organizer-institution">([^<]+)<', body)
        pm = re.search(r'<img src="([^"]+)"', body)
        organizers.append({
            "name": name,
            "role": attr("role") or (html.unescape(rm.group(1)).strip() if rm else ""),
            "institution": attr("meta") or (html.unescape(im.group(1)).strip() if im else ""),
            "photo_url": attr("photo") or (pm.group(1) if pm else ""),
            "bio": bios.get(attr("bio-id").removeprefix("bio-"), ""),
        })
    (OUT / "organizers.json").write_text(json.dumps(organizers, indent=1), encoding="utf-8")
    return organizers


# ------------------------------------------------------------------- news --

BLOG_POSTS = [
    ("blog_home", None),
    ("blog_awards", "awards"),
    ("blog_tot", "test-of-time"),
    ("blog_keynotes", "keynotes"),
    ("blog_retro", "review-retrospective"),
    ("blog_security", "security-incident-response"),
    ("blog_llm_papers", "llm-papers-response"),
    ("blog_llm_policy", "llm-usage-policies"),
    ("blog_2027_policies", "iclr-2027-submission-policies"),
]
BLOG_URLS = {
    "blog_awards": "https://blog.iclr.cc/2026/04/23/announcing-the-iclr-2026-outstanding-papers/",
    "blog_tot": "https://blog.iclr.cc/2026/04/22/announcing-the-test-of-time-awards-from-iclr-2016/",
    "blog_keynotes": "https://blog.iclr.cc/2026/04/17/announcing-the-iclr-2026-keynotes/",
    "blog_retro": "https://blog.iclr.cc/2026/03/31/a-retrospective-on-the-iclr-2026-review-process/",
    "blog_security": "https://blog.iclr.cc/2025/12/03/iclr-2026-response-to-security-incident/",
    "blog_llm_papers": "https://blog.iclr.cc/2025/11/19/iclr-2026-response-to-llm-generated-papers-and-reviews/",
    "blog_llm_policy": "https://blog.iclr.cc/2025/08/26/policies-on-large-language-model-usage-at-iclr-2026/",
    "blog_2027_policies": "https://blog.iclr.cc/2026/09/02/submission-policies-for-iclr-2027/",
}


def build_news():
    posts = []
    for cap_name, slug in BLOG_POSTS:
        if slug is None:
            continue
        t = cap(cap_name)
        title = re.search(r'<h1[^>]*class="[^"]*entry-title[^"]*"[^>]*>(.*?)</h1>', t, re.S)
        date = re.search(r'datetime="(\d{4}-\d{2}-\d{2})', t)
        author = re.search(r'rel="author">([^<]+)<', t)
        art = re.search(r"<article[^>]*>(.*?)</article>", t, re.S)
        body, headings = [], []
        if art:
            seg = art.group(1)
            for pm in re.finditer(r"<p[^>]*>(.*?)</p>", seg, re.S):
                para = text_of(pm.group(1))
                if para and para not in body:
                    body.append(para)
            for hm in re.finditer(r"<h2[^>]*>(.*?)</h2>", seg, re.S):
                h = text_of(hm.group(1))
                if h:
                    headings.append(h)
        # drop the upstream byline paragraph ("Author Name ICLR 2026")
        if body and re.match(r"^[A-Z][^.]{2,60}\s+ICLR\s*20\d\d$", body[0]):
            body = body[1:]
        posts.append({
            "slug": slug,
            "title": text_of(title.group(1)) if title else "",
            "date": date.group(1) if date else "",
            "author": html.unescape(author.group(1)).strip() if author else "",
            "headings": headings,
            "body": body,
            "upstream_url": BLOG_URLS[cap_name],
        })
    posts.sort(key=lambda p: p["date"], reverse=True)
    (OUT / "news.json").write_text(json.dumps(posts, indent=1), encoding="utf-8")
    return posts


# ----------------------------------------------------------------- awards --

def build_awards(news):
    awards = []
    by_slug = {p["slug"]: p for p in news}
    outstanding = by_slug.get("awards")
    if outstanding:
        committee = []
        for para in outstanding["body"]:
            if "Outstanding Paper Committee" in para and "(" in para:
                inner = para[para.find("(") + 1:para.rfind(")")]
                for name in inner.split(","):
                    name = name.strip()
                    name = re.sub(r"\(chair\)", "", name).strip()
                    if name:
                        committee.append(name)
                break
        entries = []
        for i, para in enumerate(outstanding["body"]):
            m = re.match(r"^(.*?)\s*,\s*by\s+(.*)$", para)
            if not m:
                continue
            title = m.group(1).strip()
            authors = [a.strip() for a in m.group(2).split(",") if a.strip()]
            citation = ""
            if i + 1 < len(outstanding["body"]):
                nxt = outstanding["body"][i + 1]
                if not re.match(r"^.*\s,\s*by\s", nxt):
                    citation = nxt
            entries.append({"title": title, "authors": authors,
                            "kind": "Outstanding Paper", "citation": citation})
        if len(entries) >= 3:
            entries[-1]["kind"] = "Honorable Mention"
        awards.append({"award": "Outstanding Paper Awards", "conference": "ICLR 2026",
                       "committee": committee, "entries": entries,
                       "source_url": outstanding["upstream_url"]})
    tot = by_slug.get("test-of-time")
    if tot:
        entries = []
        body = tot["body"]
        skip_prefixes = ("We are", "Congratulations", "If you", "ICLR 2026 Program")
        i = 0
        while i < len(body):
            para = body[i]
            if (para.startswith(skip_prefixes) or para.startswith("This ")
                    or para.startswith("The Test")):
                i += 1
                continue
            # a title paragraph is followed by a comma-separated author list
            if i + 2 < len(body) and "," in body[i + 1] and not body[i + 1].startswith("This"):
                author_fragments = [f.strip() for f in body[i + 1].split(",")]
                if all(len(f) < 40 for f in author_fragments) and len(author_fragments) >= 2:
                    citation = body[i + 2] if i + 2 < len(body) else ""
                    entries.append({"title": para.strip(),
                                    "authors": [f for f in author_fragments if f],
                                    "kind": "Test of Time",
                                    "citation": citation})
                    i += 3
                    continue
            i += 1
        awards.append({"award": "Test of Time Awards", "conference": "ICLR 2026",
                       "entries": entries,
                       "source_url": tot["upstream_url"]})
    (OUT / "awards.json").write_text(json.dumps(awards, indent=1), encoding="utf-8")
    return awards


# ------------------------------------------------------------------ dates --

def build_dates():
    out = {"2026": [], "2027": []}
    for year, cap_name in (("2026", "conf2026_dates"), ("2027", "conf2027_dates")):
        t = cap(cap_name)
        i = t.find('Dates and Deadlines')
        if i < 0:
            i = t.find('id="main"')
        seg = t[i:]
        # the upstream renders one <table class="table"> whose rows are
        # either colspan-5 group headers or name/date item rows
        tm = re.search(r'<table class="table">(.*?)</table>', seg, re.S)
        if not tm:
            continue
        groups, group = [], None
        for row in re.findall(r'<tr[^>]*>(.*?)</tr>', tm.group(1), re.S):
            g = re.search(r'<td colspan="\d+">\s*(?:<[^>]+>\s*)*([^<>]+?)\s*(?:<[^>]+>\s*)*</td>', row)
            if g and not g.group(1).startswith("<"):
                name = text_of(g.group(1))
                if name and len(name) < 60:
                    group = name
                    groups.append({"group": name, "items": []})
                continue
            cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.S)
            if len(cells) >= 3:
                item = text_of(cells[1])
                date = text_of(cells[2])
                if item and date:
                    if not groups:
                        groups.append({"group": "General", "items": []})
                        group = "General"
                    groups[-1]["items"].append({"name": item, "date": date})
        out[year] = [g for g in groups if g["items"] or g["group"] != "General"]
    (OUT / "dates.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    return out


# ------------------------------------------------------------ registration --

def build_registration():
    t = cap("conf2026_pricing")
    text = text_of(t)
    items = []
    for name in ("Conference Sessions and Workshops", "Sunday Workshop 1 Day Pass",
                 "Monday Workshop 1 Day Pass", "Virtual Only Pass"):
        items.append({"name": name,
                      "includes_virtual": name != "Virtual Only Pass"})
    affiliations = ["Full time student", "Academic", "Industrial"]
    policy = []
    i = text.find("Registration Cancellation Policy")
    if i >= 0:
        seg = text[i:i + 1800]
        for para in re.split(r"(?<=\.)\s+(?=[A-Z])", seg):
            para = para.strip()
            if para and len(para) > 40:
                policy.append(para)
    banquet = re.search(r"guest banquet ticket.*?price is \$50 USD", text, re.S)
    reg = {
        "conference": "ICLR 2026",
        "status": "closed",
        "affiliations": affiliations,
        "items": items,
        "exclusivity_note": ('"Conference Sessions and Workshops," "Sunday Workshop '
                             '1 Day Pass," and "Monday Workshop 1 Day Pass" include '
                             'Virtual Access. If you choose Conference Sessions and '
                             'Workshops, do not check any other items.'),
        "banquet_ticket_price_usd": 50 if banquet else None,
        "cancellation_policy": policy,
        "source_url": "https://iclr.cc/Conferences/2026/Pricing",
    }
    (OUT / "registration.json").write_text(json.dumps(reg, indent=1), encoding="utf-8")
    return reg


# -------------------------------------------------------------------- faq --

def build_faq():
    t = cap("faq")
    i = t.find('id="main"')
    seg = t[i:]
    faq = []
    section = None
    # h2 headings open sections; h3/h4 headings are questions with the
    # content up to the next heading as the answer. An h2 that carries
    # its own answer text (the upstream LLM-policy entries) is kept as a
    # question in its own right.
    heads = list(re.finditer(r"<(h[234])[^>]*>(.*?)</\1>", seg, re.S))
    for idx, m in enumerate(heads):
        level, raw = m.group(1), text_of(m.group(2))
        if not raw:
            continue
        nxt = heads[idx + 1].start() if idx + 1 < len(heads) else len(seg)
        body = text_of(seg[m.end():nxt])
        if level == "h2":
            section = raw
            if body and len(body) > 30:
                faq.append({"section": raw, "question": raw, "answer": body[:2400]})
        else:
            faq.append({"section": section or "General", "question": raw,
                        "answer": body[:2400]})
    (OUT / "faq.json").write_text(json.dumps(faq, indent=1), encoding="utf-8")
    return faq


# ------------------------------------------------------------------ about --

def build_about():
    t = cap("about")
    i = t.find("The International Conference on Learning Representations")
    text = text_of(t)
    j = text.find("The International Conference on Learning Representations")
    about_paras = []
    if j >= 0:
        seg = text[j:j + 3000]
        for para in re.split(r"(?<=[.!?])\s+(?=[A-Z])", seg):
            para = para.strip()
            if para:
                about_paras.append(para)
            if len(about_paras) >= 6:
                break
    home = text_of(cap("conf2026"))
    k = home.find("The International Conference on Learning Representations")
    stats = {}
    editions = [f"ICLR {y}" for y in range(2013, 2027)]
    about = {
        "paras": about_paras,
        "editions": editions,
        "source_urls": ["https://iclr.cc/About", "https://iclr.cc/Conferences/2026"],
    }
    (OUT / "about.json").write_text(json.dumps(about, indent=1), encoding="utf-8")
    return about


# ------------------------------------------------------------------ venue --

def build_venue():
    vi = text_of(cap("v_index"))
    conf = text_of(cap("conf2026"))
    i = vi.find("Riocentro drop off")
    j = vi.find("System Requirements")
    site_notes = []
    if i >= 0:
        seg = vi[i:j if j > i else len(vi)]
        for chunk in re.split(r"(?=Registration and Badge Pickup|Food and Beverage|"
                              r"Luggage Check|Personal Conference Programs)", seg):
            chunk = re.sub(r"\s+", " ", chunk).strip()
            if chunk:
                site_notes.append(chunk[:600])
    venue = {
        "conference": "ICLR 2026",
        "city": "Rio de Janeiro",
        "country": "Brazil",
        "dates": "April 23rd - 27th, 2026",
        "site": "Riocentro",
        "site_notes": site_notes,
        "next": {
            "conference": "ICLR 2027",
            "full_name": "The Fifteenth International Conference on Learning Representations",
            "location": "California",
            "dates": "April 26-30, 2027",
            "note": "Venue information will be posted on the upstream site; the "
                    "official housing portal opens six months prior to the "
                    "conference.",
        },
        "source_urls": ["https://iclr.cc/virtual/2026/index.html",
                        "https://iclr.cc/Conferences/2026",
                        "https://iclr.cc/Conferences/2027"],
    }
    (OUT / "venue.json").write_text(json.dumps(venue, indent=1), encoding="utf-8")
    return venue


# ------------------------------------------------------------ conferences --

def build_conference(papers, schedule, events, sponsors, news):
    days = schedule["days"]
    n_sessions = sum(len(d["sessions"]) for d in days)
    conf = {
        "name": "ICLR 2026",
        "full_name": "The Fourteenth International Conference on Learning Representations",
        "city": "Rio de Janeiro",
        "country": "Brazil",
        "dates": "April 23rd - 27th, 2026",
        "main_conference": "Thursday April 23 through Saturday April 25",
        "workshop_days": "Sunday April 26 through Monday April 27",
        "papers": len(papers),
        "oral_decisions": sum(1 for p in papers if p["decision"] == "Accept (Oral)"),
        "poster_decisions": sum(1 for p in papers if p["decision"] == "Accept (Poster)"),
        "sessions": n_sessions,
        "workshops": sum(1 for e in events if e["kind"] == "workshop"),
        "invited_talks": sum(1 for e in events if e["kind"] == "invited-talk"),
        "socials": sum(1 for e in events if e["kind"] == "social"),
        "sponsors": len(sponsors),
        "topics": sorted({p["topic"] for p in papers if p["topic"]}),
        "announcements": [
            {"title": p["title"], "date": p["date"], "slug": p["slug"]}
            for p in news[:4]
        ],
        "upstream": "https://iclr.cc/",
    }
    (OUT / "conference.json").write_text(json.dumps(conf, indent=1), encoding="utf-8")
    return conf


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    papers = build_papers()
    schedule = build_schedule()
    events = build_events(schedule)
    sponsors = build_sponsors()
    organizers = build_organizers()
    news = build_news()
    awards = build_awards(news)
    dates = build_dates()
    registration = build_registration()
    faq = build_faq()
    about = build_about()
    venue = build_venue()
    conf = build_conference(papers, schedule, events, sponsors, news)
    print(f"[src] papers={len(papers)} days={len(schedule['days'])} "
          f"events={len(events)} sponsors={len(sponsors)} "
          f"organizers={len(organizers)} news={len(news)} awards={len(awards)} "
          f"faq={len(faq)}")
    print(f"[src] sessions={conf['sessions']} workshops={conf['workshops']} "
          f"invited={conf['invited_talks']} socials={conf['socials']} "
          f"topics={len(conf['topics'])}")


if __name__ == "__main__":
    main()
