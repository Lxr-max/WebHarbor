#!/usr/bin/env python3
"""Capture the public pages and data files of the ICLR conference site.

The declared task upstream `iclr.com` is a GoDaddy parking lander (see
provenance.json); the real ICLR service this mirror targets is
https://iclr.cc/ — the same normalization precedent as the dblp mirror
(declared parked dblp.com -> real dblp.org).

Every capture is stored under scraped_data/captures/ with a .meta.json
sidecar recording the exact URL, HTTP status, byte length and UTC
timestamp. The two upstream JSON data files (accepted papers + abstracts)
are captured as data. Run from sites/iclr:

    python3 scripts_dev/capture_upstream.py
"""
import datetime
import hashlib
import json
import pathlib
import time
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
CAP = ROOT / "scraped_data" / "captures"
CAP.mkdir(parents=True, exist_ok=True)

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
BASE = "https://iclr.cc"

# name -> URL (pages whose absence is acceptable carry allow_404=True)
PAGES = [
    ("home", "/", False),
    ("about", "/About", False),
    ("faq", "/FAQ", False),
    ("faq_cancellation", "/FAQ/CancellationPolicy", False),
    ("downloads", "/Downloads", False),
    ("help_contact", "/Help/Contact", False),
    ("coc_public", "/public/CodeOfConduct", False),
    ("diversity", "/public/DiversityInclusion", False),
    ("privacy", "/public/PrivacyPolicy", False),
    ("j2c", "/public/JournalToConference", False),
    ("sponsorinfo", "/Sponsors/sponsorinfo", False),
    ("exhibitorinfo", "/Exhibitors/exhibitorinfo/", False),
    ("register_view", "/Register/view-registration", False),
    ("register2", "/Register2", False),
    ("future_meetings", "/Conferences/FutureMeetings", False),
    # ---- ICLR 2026 (the completed conference this mirror freezes) ----
    ("conf2026", "/Conferences/2026", False),
    ("conf2026_dates", "/Conferences/2026/Dates", False),
    ("conf2026_cfp", "/Conferences/2026/CallForPapers", False),
    ("conf2026_cfw", "/Conferences/2026/CallForWorkshops", False),
    ("conf2026_cfs", "/Conferences/2026/CallForSocials", False),
    ("conf2026_cfb", "/Conferences/2026/CallForBlogPosts", False),
    ("conf2026_pricing", "/Conferences/2026/Pricing", False),
    ("conf2026_sponsors", "/Conferences/2026/Sponsors", False),
    ("conf2026_visatravel", "/Conferences/2026/VisaTravel", False),
    ("conf2026_finassis", "/Conferences/2026/FinancialAssistance", False),
    ("conf2026_childcare", "/Conferences/2026/ChildCare", False),
    ("conf2026_posterinstr", "/Conferences/2026/PosterInstructions", False),
    ("conf2026_coc", "/Conferences/2026/CodeOfConduct", False),
    ("conf2026_committees", "/Conferences/2026/Committees", False),
    ("conf2026_progcom", "/Conferences/2026/ProgramCommittee", False),
    ("conf2026_board", "/Conferences/2026/Board", False),
    ("conf2026_authorguide", "/Conferences/2026/AuthorGuide", False),
    ("conf2026_reviewerguide", "/Conferences/2026/ReviewerGuide", False),
    ("conf2026_acguide", "/Conferences/2026/AreaChairGuide", False),
    ("conf2026_sacguide", "/Conferences/2026/SeniorAreaChairGuide", False),
    ("conf2026_press", "/Conferences/2026/Press", True),
    # ---- ICLR 2027 (the upcoming conference) ----
    ("conf2027", "/Conferences/2027", False),
    ("conf2027_dates", "/Conferences/2027/Dates", False),
    ("conf2027_cfp", "/Conferences/2027/CallForPapers", False),
    ("conf2027_cfw", "/Conferences/2027/CallForWorkshops", False),
    ("conf2027_cfb", "/Conferences/2027/CallForBlogPosts", False),
    ("conf2027_pricing", "/Conferences/2027/Pricing", False),
    ("conf2027_sponsors", "/Conferences/2027/Sponsors", False),
    ("conf2027_board", "/Conferences/2027/Board", False),
    ("conf2027_authorguide", "/Conferences/2027/AuthorGuidelines", False),
    ("conf2027_reviewerguide", "/Conferences/2027/ReviewerGuidelines", False),
    ("conf2027_acguide", "/Conferences/2027/AreaChairGuidelines", False),
    ("conf2027_sacguide", "/Conferences/2027/SeniorAreaChairGuidelines", False),
    ("conf2027_ai_authors", "/Conferences/2027/AIPolicyForAuthors", False),
    ("conf2027_ai_reviewers", "/Conferences/2027/AIPolicyForReviewers", False),
    ("conf2027_wsguide", "/Conferences/2027/WorkshopGuidelines", False),
    # ---- virtual site 2026 ----
    ("v_index", "/virtual/2026/index.html", False),
    ("v_papers", "/virtual/2026/papers.html", False),
    ("v_calendar", "/virtual/2026/calendar", False),
    ("v_search", "/virtual/2026/search", False),
    ("v_mycalendar", "/virtual/2026/mycalendar", False),
    ("v_workshops", "/virtual/2026/events/workshop", False),
    ("v_orals", "/virtual/2026/events/oral", False),
    ("v_socials", "/virtual/2026/events/social", False),
    ("v_blogtrack", "/virtual/2026/events/BlogTrack-2026", False),
    ("v_journaltrack", "/virtual/2026/events/journal-track-posters", False),
    ("v_invited_bios", "/virtual/2026/eventlistwithbios/Invited%20Talk", False),
    ("v_awards", "/virtual/2026/awards_detail", False),
    ("v_sponsor_list", "/virtual/2026/sponsor_list", False),
    ("v_organizers", "/virtual/2026/organizers", False),
    ("v_townhall", "/virtual/2026/town-hall/", False),
    # upstream JSON data (accepted papers with sessions + abstracts)
    ("data_orals_posters", "/static/virtual/data/iclr-2026-orals-posters.json", False),
    ("data_abstracts", "/static/virtual/data/iclr-2026-abstracts.json", False),
]

# blog.iclr.cc news posts referenced from the conference pages
BLOG = "https://blog.iclr.cc"
BLOG_POSTS = [
    ("blog_home", "/"),
    ("blog_awards", "/2026/04/23/announcing-the-iclr-2026-outstanding-papers/"),
    ("blog_tot", "/2026/04/22/announcing-the-test-of-time-awards-from-iclr-2016/"),
    ("blog_keynotes", "/2026/04/17/announcing-the-iclr-2026-keynotes/"),
    ("blog_retro", "/2026/03/31/a-retrospective-on-the-iclr-2026-review-process/"),
    ("blog_security", "/2025/12/03/iclr-2026-response-to-security-incident/"),
    ("blog_llm_papers", "/2025/11/19/iclr-2026-response-to-llm-generated-papers-and-reviews/"),
    ("blog_llm_policy", "/2025/08/26/policies-on-large-language-model-usage-at-iclr-2026/"),
    ("blog_2027_policies", "/2026/09/02/submission-policies-for-iclr-2027/"),
]


def utc_now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def fetch(url, tries=3, binary=True):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            last = e
            if e.code in (403, 404):
                return e.code, e.read() if binary else b""
            time.sleep(2 * (i + 1))
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(2 * (i + 1))
    print(f"[cap] FAIL {url}: {last}")
    return None, None


def capture(name, url, allow_404=False):
    out = CAP / name
    status, data = fetch(BASE + url if url.startswith("/") else url)
    if status is None:
        return False
    if status == 404 and allow_404:
        (CAP / f"{name}.meta.json").write_text(json.dumps({
            "url": url, "status": 404, "bytes": 0,
            "captured_at_utc": utc_now(), "note": "absent upstream (allowed)"},
            indent=1))
        print(f"[cap] {name}: 404 (allowed)")
        return True
    if status != 200:
        print(f"[cap] {name}: HTTP {status} -- FAIL")
        return False
    out.write_bytes(data)
    (CAP / f"{name}.meta.json").write_text(json.dumps({
        "url": url, "status": status, "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "captured_at_utc": utc_now()}, indent=1))
    print(f"[cap] {name}: 200 {len(data)}B")
    return True


def event_pages_from_calendar():
    """All non-poster event detail URLs embedded in the calendar page."""
    import re
    cal = (CAP / "v_calendar").read_text(encoding="utf-8", errors="replace")
    urls = set()
    for kind, idn in re.findall(r"/virtual/2026/([a-z-]+)/(\d+)", cal):
        if kind in ("poster", "oral"):
            continue  # papers data comes from the captured JSONs
        urls.add((kind, idn))
    return sorted(urls)


def capture_events():
    ok = True
    pages = event_pages_from_calendar()
    print(f"[cap] {len(pages)} non-poster event pages to capture")
    for i, (kind, idn) in enumerate(pages):
        name = f"event_{kind}_{idn}"
        if (CAP / name).exists():
            continue
        if not capture(name, f"/virtual/2026/{kind}/{idn}"):
            ok = False
        time.sleep(0.4)
    # a deterministic sample of poster detail pages for fidelity checks
    import re
    cal = (CAP / "v_calendar").read_text(encoding="utf-8", errors="replace")
    posters = sorted(set(re.findall(r"/virtual/2026/poster/(\d+)", cal)))
    sample = [posters[i] for i in range(0, len(posters), max(1, len(posters) // 40))][:40]
    for idn in sample:
        name = f"event_poster_{idn}"
        if (CAP / name).exists():
            continue
        if not capture(name, f"/virtual/2026/poster/{idn}"):
            ok = False
        time.sleep(0.4)
    return ok


def main():
    failures = []
    for name, url, allow_404 in PAGES:
        if not capture(name, url, allow_404):
            failures.append(name)
        time.sleep(0.4)
    for name, path in BLOG_POSTS:
        if not capture(name, BLOG + path):
            failures.append(name)
        time.sleep(0.4)
    if not capture_events():
        failures.append("events")
    print(f"[cap] done; failures: {failures if failures else 'none'}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
