#!/usr/bin/env python3
"""Machine audit of sites/ziprecruiter/tasks.jsonl — measured honest-atomic
caliber, after the zara/u_s_customs precedent.

For every task row this script drives the task's honest path against the
seeded mirror through the Flask test client — the same natural route a
competent agent takes — and counts steps in the MEASURED caliber of the
depth review:

  atomic = every navigation, link click, form fill, radio/checkbox pick,
           dropdown select and form submit after the initial page load,
           plus one final step for composing the answer. Reads are NOT
           counted.

For every task it asserts:
  1. premises — every fact the task asks for actually resolves on the
     mirror with the frozen ground-truth value (driven through the test
     client, exactly like an agent would);
  2. measured depth — atomic >= 15, measured from the driven walk, not
     declared as a constant;
  3. zero answer leakage — answer anchors never appear in the task text;
  4. shape — the 5 contributor task keys, goal-style wording at or under
     100 words.

Run:  PYTHONPATH=. venv/bin/python scripts_dev/validate_tasks.py
"""
import html as html_mod
import json
import os
import pathlib
import re
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]

# The audit drives stateful flows (register, apply, save, alerts), so it
# runs against its own throwaway seed database — never the live instance.
_AUDIT_DB = pathlib.Path(tempfile.mkdtemp(prefix="ziprecruiter-task-audit-")) / "ziprecruiter.db"
os.environ["ZIPRECRUITER_DB_URI"] = f"sqlite:///{_AUDIT_DB}"

sys.path.insert(0, str(ROOT))
import app as zr_mod  # noqa: E402
from app import app  # noqa: E402

TASKS = [json.loads(line) for line in
         (ROOT / "tasks.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]

TAG_RE = re.compile(r"<[^>]+>")

# Hidden inputs of the SERP filter form — a real user never touches them,
# so they are never counted as gestures (r1/r2 depth standard).
HIDDEN_FILTER_FIELDS = ("search", "location")


def text_of(page):
    return " ".join(html_mod.unescape(TAG_RE.sub(" ", page)).split())


def csrf_from(page_html, form_action=None):
    m = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', page_html)
    assert m, "no csrf token rendered"
    return m.group(1)


# ------------------------------------------------------------------- walker --

class Walk:
    """Test-client walk of one task's honest path, in the measured caliber.

    Every nav / click / fill / choose / select / submit counts exactly one
    atomic action (matching a real browser: one user gesture, one step).
    Reads are free. The redirect target after a POST loads for free.
    """

    def __init__(self, client, task_id):
        self.client = client
        self.task_id = task_id
        self.atomic = 0
        self.facts = {}
        self.log = []

    def nav(self, path, count=True):
        r = self.client.get(path)
        assert r.status_code == 200, f"GET {path} -> {r.status_code}"
        self.page_html = r.get_data(as_text=True)
        self.page_text = text_of(self.page_html)
        if count:
            self.atomic += 1
            self.log.append(("nav", path))
        return self.page_text

    def click(self, path):
        return self.nav(html_mod.unescape(path))

    def fill(self, name, value):
        self.atomic += 1
        self.log.append(("fill", name))
        return (name, value)

    def search(self, what, where=None):
        """Fill the search fields and submit.

        Two visible fills + submit when a location is given; one visible
        fill + submit for a nationwide search (the location box is left
        visibly empty — no gesture).
        """
        parts = []
        parts.append(self.fill("search", what))
        params = {"search": what}
        if where is not None:
            parts.append(self.fill("location", where))
            params["location"] = where
        self.atomic += 1
        self.log.append(("submit", "header search"))
        self.serp_query = dict(params)
        r = self.client.get("/jobs-search", query_string=params)
        assert r.status_code == 200
        self.page_html = r.get_data(as_text=True)
        self.page_text = text_of(self.page_html)
        return self.page_text

    def filter(self, **params):
        """Pick VISIBLE filter controls and press Apply Filters.

        The filter form's search/location inputs are HIDDEN fields a real
        user never touches (r1 depth standard): they ride along in the
        query string but never count as gestures. Values already selected
        in the form are carried by the panel, not re-picked: a param whose
        value equals the current SERP's is not counted again.
        """
        current = getattr(self, "serp_query", {})
        for k in params:
            if k in HIDDEN_FILTER_FIELDS:
                continue
            v = params[k]
            if isinstance(v, list):
                v = ",".join(v)
            if k in current and current[k] == v:
                continue
            self.atomic += 1
            self.log.append(("choose", f"{k}={params[k]}"))
        self.atomic += 1
        self.log.append(("submit", "Apply Filters"))
        r = self.client.get("/jobs-search", query_string=params)
        assert r.status_code == 200
        self.page_html = r.get_data(as_text=True)
        self.page_text = text_of(self.page_html)
        self.serp_query = {k: (v if isinstance(v, str) else ",".join(v))
                           for k, v in params.items()}
        return self.page_text

    def post(self, path, data, expect_redirect=True):
        """A CSRF-protected form submit: one atomic action."""
        token = csrf_from(self.page_html)
        payload = dict(data)
        payload["csrf_token"] = token
        r = self.client.post(path, data=payload, follow_redirects=False)
        if expect_redirect:
            assert r.status_code in (302, 303), f"POST {path} -> {r.status_code}"
            loc = r.headers.get("Location")
            if loc and loc.startswith("/"):
                rr = self.client.get(loc)
                assert rr.status_code == 200
                self.page_html = rr.get_data(as_text=True)
                self.page_text = text_of(self.page_html)
        else:
            assert r.status_code == 200
            self.page_html = r.get_data(as_text=True)
            self.page_text = text_of(self.page_html)
        self.atomic += 1
        self.log.append(("submit", path))
        return self.page_text

    def select(self, name, value):
        """A visible dropdown pick: one atomic action."""
        self.atomic += 1
        self.log.append(("select", f"{name}={value}"))

    def compose(self):
        self.atomic += 1
        self.log.append(("compose", "the final answer"))


# ------------------------------------------------------------------ helpers --

def first_card_href(page_html):
    m = re.search(r'class="job-title"><a href="([^"]+)"', page_html)
    assert m, "no job card rendered"
    return m.group(1)


def detail_title(page_html):
    m = re.search(r'<h1>([^<]+)</h1>', page_html)
    assert m, "no detail title rendered"
    return m.group(1).strip()


def detail_co(page_html):
    m = re.search(r'class="detail-co">\s*<a[^>]*>([^<]+)</a>', page_html)
    assert m, "no detail company rendered"
    return m.group(1).strip()


def serp_count(page_text):
    m = re.search(r"(\d+) [A-Za-z ]* ?[Jj]obs", page_text)
    assert m, "no result count rendered"
    return int(m.group(1))


def read(page_text, needle, label):
    assert needle in page_text, f"premise missing: {label}: {needle!r} not on page"
    return needle



# -------------------------------------------------------------------- walks --
# r2 sync: every walk drives the DEEPENED task text (@ 4d57185b) along the
# reviewer's honest-minimal path (matching the r2 Playwright measurement:
# visible gestures only, hidden filter fields never counted, reads free,
# +1 compose, initial home load free, no unrequired gestures).

def walk_0(w):
    w.nav("/", count=False)
    t = w.search("software engineer", "San Francisco, CA")
    w.facts["base_count"] = serp_count(t)
    assert w.facts["base_count"] == 22
    t = w.filter(search="software engineer", location="San Francisco, CA",
                 remote="remote")
    w.facts["remote_count"] = serp_count(t)
    assert w.facts["remote_count"] == 1
    for needle, label in [("Software Engineer - Open Source Contributions - Remote", "title"),
                          ("YO AI Labs", "company"), ("$50 - $100/hr", "pay")]:
        read(t, needle, label)
    href = first_card_href(w.page_html)
    t = w.click(href)
    for needle, label in [("Full Time", "employment"), ("Posted 3 days ago", "posted")]:
        read(t, needle, label)
    m = re.search(r'href="(/co/YO-AI-Labs)"', w.page_html)
    t = w.click(m.group(1))
    for needle, label in [("Computing Infrastructure Providers, Data Processing, Web Hosting", "industry"),
                          ("201 - 500 employees", "size"),
                          ("Abu Dhabi, Abu Dhabi, AE", "hq")]:
        read(t, needle, label)
    # r3: the text now asks for the San Francisco JOBS-PAGE roles count, so
    # opening the company's SF jobs page is a required gesture (T7-style).
    m = re.search(r'href="(/co/YO-AI-Labs/Jobs/-in-San-Francisco,CA)"', w.page_html)
    assert m, "company page must link its San Francisco jobs page"
    t = w.click(m.group(1))
    read(t, "1 open roles from YO AI Labs in this snapshot", "sf jobs-page roles count")
    # return to the SERP (three browser backs: sf-jobs -> profile -> detail -> SERP)
    w.click("/co/YO-AI-Labs")
    w.click(href)
    w.click("/jobs-search?search=software+engineer&location=San+Francisco,+CA&apply=&remote=remote&days=&smin=&smax=&exp=")
    t = w.filter(search="software engineer", location="San Francisco, CA",
                 remote="", days="5")
    w.facts["days5_count"] = serp_count(t)
    assert w.facts["days5_count"] == 13
    read(t, "Forward Deployed Software Engineer", "days5 first title")
    read(t, "Posted 7 hours ago", "days5 first posted")
    assert "Quick apply" not in t.split("Forward Deployed Software Engineer")[1][:600], \
        "days5 first should not be a quick apply"
    hrefs = re.findall(r'class="job-title"><a href="([^"]+)"', w.page_html)
    t = w.click(hrefs[1])
    for needle, label in [("Veritus", "second company"), ("Alameda, CA", "second city")]:
        read(t, needle, label)
    w.compose()


def walk_1(w):
    w.nav("/", count=False)
    t = w.search("registered nurse", "New York, NY")
    w.facts["base"] = serp_count(t)
    assert w.facts["base"] == 24
    t = w.filter(search="registered nurse", location="New York, NY", apply="quick")
    w.facts["quick"] = serp_count(t)
    assert w.facts["quick"] == 9
    t = w.filter(search="registered nurse", location="New York, NY",
                 apply="quick", days="5")
    w.facts["quick5"] = serp_count(t)
    assert w.facts["quick5"] == 5
    for needle, label in [("Registered Nurse - Gastroenterology", "title"),
                          ("Park Ave Gastroenterology", "company"),
                          ("Huntington, NY", "city"), ("$40 - $50/hr", "pay")]:
        read(t, needle, label)
    href = first_card_href(w.page_html)
    t = w.click(href)
    for needle, label in [("Posted 23 hours ago", "posted"), ("Part Time", "employment")]:
        read(t, needle, label)
    # back to the filtered SERP, open the second listing
    w.click("/jobs-search?search=registered+nurse&location=New+York,+NY&apply=quick&remote=&days=5&smin=&smax=&exp=")
    hrefs = re.findall(r'class="job-title"><a href="([^"]+)"', w.page_html)
    t = w.click(hrefs[1])
    read(t, "Private Duty Registered Nurse (RN)", "second title")
    m = re.search(r'href="(/co/BAYADA-Home-Health-Care)"', w.page_html)
    t = w.click(m.group(1))
    for needle, label in [("Health Care and Social Assistance", "industry"),
                          ("10000+ employees", "size"), ("Moorestown, NJ", "hq")]:
        read(t, needle, label)
    # back, back, reset filters (one click on the reset link)
    w.click("/c/BAYADA-Home-Health-Care/Job/Private-Duty-Registered-Nurse-(RN)/-in-Hoboken,NJ?jid=26a8ee92a424ed2d")
    w.click("/jobs-search?search=registered+nurse&location=New+York,+NY&apply=quick&remote=&days=5&smin=&smax=&exp=")
    t = w.click("/jobs-search?search=registered+nurse&location=New+York,+NY")
    w.facts["first5"] = re.findall(
        r'class="job-location">[^<]*<a[^>]*>([^<]+)</a>', w.page_html)[:5]
    assert len(w.facts["first5"]) == 5, "first five listings premise"
    states = {loc.rsplit(", ", 1)[-1] for loc in w.facts["first5"]}
    assert states == {"NJ"}, f"first five states premise: {states}"
    read(t, "$85K - $89K/yr", "highest pay among first five")
    w.compose()


def walk_2(w):
    w.nav("/", count=False)
    t = w.search("accountant", "Denver, CO")
    w.facts["base"] = serp_count(t)
    assert w.facts["base"] == 12
    read(t, "$80K - $100K/yr", "highest pay in unfiltered results")
    t = w.filter(search="accountant", location="Denver, CO", smin="70000")
    w.facts["smin70"] = serp_count(t)
    assert w.facts["smin70"] == 4
    for needle, label in [("Senior Accountant", "title"),
                          ("Matter Family Office", "company"),
                          ("$80K - $100K/yr", "pay")]:
        read(t, needle, label)
    href = first_card_href(w.page_html)
    t = w.click(href)
    for needle, label in [("Full Time", "employment"), ("Posted yesterday", "posted")]:
        read(t, needle, label)
    m = re.search(r'href="(/co/Matter-Family-Office)"', w.page_html)
    t = w.click(m.group(1))
    read(t, "1 open roles from Matter Family Office in this snapshot", "open-job count")
    # back, back to the SERP
    w.click("/c/Matter-Family-Office/Job/Senior-Accountant/-in-Denver,CO?jid=3770eecfc82fcf30")
    w.click("/jobs-search?search=accountant&location=Denver,+CO&apply=&remote=&days=&smin=70000&smax=&exp=")
    hrefs = re.findall(r'class="job-title"><a href="([^"]+)"', w.page_html)
    t = w.click(hrefs[1])
    for needle, label in [("Staff Accountant", "second title"),
                          ("ELECTRO MAGNETIC APPLICATIONS INC", "second company"),
                          ("$70K - $90K/yr", "second pay")]:
        read(t, needle, label)
    # back + reset + within-10-days
    w.click("/jobs-search?search=accountant&location=Denver,+CO&apply=&remote=&days=&smin=70000&smax=&exp=")
    t = w.click("/jobs-search?search=accountant&location=Denver,+CO")
    t = w.filter(search="accountant", location="Denver, CO", days="10")
    w.facts["days10"] = serp_count(t)
    assert w.facts["days10"] == 10
    read(t, "Senior Accountant", "days10 first title")
    read(t, "Posted today", "days10 first posted")
    w.compose()


def walk_3(w):
    w.nav("/", count=False)
    t = w.search("nurse")
    w.facts["base"] = serp_count(t)
    assert w.facts["base"] == 124
    t = w.filter(search="nurse", et="part_time")
    w.facts["pt"] = serp_count(t)
    assert w.facts["pt"] == 27
    for needle, label in [("Part-Time Licensed Practical Nurse (LPN) - West Hartford", "title"),
                          ("GameDay Men's Health - West Hartford", "company"),
                          ("West Hartford, CT", "city")]:
        read(t, needle, label)
    href = first_card_href(w.page_html)
    t = w.click(href)
    for needle, label in [("Posted today", "posted"), ("Part Time", "employment")]:
        read(t, needle, label)
    assert "$" not in t.split("Job description")[0].split("Part Time")[-1], \
        "first PT listing should show no pay"
    w.click("/jobs-search?search=nurse&location=&apply=&remote=&days=&smin=&smax=&et=part_time&exp=")
    t = w.filter(search="nurse", et=["part_time", "per_diem"])
    w.facts["pt_pd"] = serp_count(t)
    assert w.facts["pt_pd"] == 29, "the real checkbox panel must combine PT+PD (29)"
    read(t, "Part-Time Licensed Practical Nurse (LPN) - West Hartford", "combined first title")
    t = w.click("/jobs-search?search=nurse&location=")
    t = w.filter(search="nurse", apply="quick")
    w.facts["quick"] = serp_count(t)
    assert w.facts["quick"] == 78
    for needle, label in [("Supplemental Health Care", "company"),
                          ("Oregon, WI", "location"), ("$1.3K - $1.4K/wk", "pay")]:
        read(t, needle, label)
    href = first_card_href(w.page_html)
    t = w.click(href)
    read(t, "Posted 11 hours ago", "quick first posted")
    w.click("/jobs-search?search=nurse&location=&apply=quick&remote=&days=&smin=&smax=&exp=")
    t = w.filter(search="nurse", apply="quick", exp="none")
    w.facts["quick_none"] = serp_count(t)
    assert w.facts["quick_none"] == 0
    w.compose()


def walk_4(w):
    w.nav("/", count=False)
    t = w.search("software engineer")
    w.facts["base"] = serp_count(t)
    assert w.facts["base"] == 76
    t = w.filter(search="software engineer", exp="senior")
    w.facts["senior"] = serp_count(t)
    assert w.facts["senior"] == 12
    for needle, label in [("Senior Software Engineer", "title"),
                          ("Burnt", "company"), ("$144K - $190K/yr", "pay")]:
        read(t, needle, label)
    href = first_card_href(w.page_html)
    t = w.click(href)
    for needle, label in [("San Francisco, CA", "location"),
                          ("Posted 2 days ago", "posted"), ("On-site", "location type")]:
        read(t, needle, label)
    assert "Quick apply" not in t.split("Job description")[0], "senior first is not a quick apply"
    m = re.search(r'href="(/co/Burnt)"', w.page_html)
    t = w.click(m.group(1))
    read(t, "1 open roles from Burnt in this snapshot", "company open jobs")
    w.click("/c/Burnt/Job/Senior-Software-Engineer/-in-San-Francisco,CA?jid=d3ee94d7831266fc")
    w.click("/jobs-search?search=software+engineer&location=&apply=&remote=&days=&smin=&smax=&exp=senior")
    t = w.filter(search="software engineer", exp="junior")
    w.facts["junior"] = serp_count(t)
    assert w.facts["junior"] == 1
    for needle, label in [("Software Engineer I & II", "title"),
                          ("Tek Fusion Global", "company"), ("$55K - $95K/yr", "pay")]:
        read(t, needle, label)
    href = first_card_href(w.page_html)
    t = w.click(href)
    for needle, label in [("Posted 11 days ago", "posted"), ("On-site", "location type")]:
        read(t, needle, label)
    w.click("/jobs-search?search=software+engineer&location=&apply=&remote=&days=&smin=&smax=&exp=junior")
    t = w.filter(search="software engineer", exp="none")
    w.facts["none"] = serp_count(t)
    assert w.facts["none"] == 2
    read(t, "RFA Engineering", "none first company")
    w.compose()


def walk_5(w):
    w.nav("/", count=False)
    t = w.search("truck driver", "Atlanta, GA")
    w.facts["base"] = serp_count(t)
    assert w.facts["base"] == 21
    pages = re.findall(r'href="[^"]*page=(\d+)"', w.page_html)
    w.facts["pages"] = max(int(p) for p in pages)
    assert w.facts["pages"] == 2
    for needle, label in [("CDL A Truck Driver", "p1 title"),
                          ("Dollar General Fleet", "p1 company"),
                          ("$100K/yr", "p1 pay")]:
        read(t, needle, label)
    t = w.click("/jobs-search?search=truck+driver&location=Atlanta,+GA&page=2")
    for needle, label in [("CDL A Truck Driver - Regional", "p2 title"),
                          ("Epes Transport Systems, Inc.", "p2 company"),
                          ("$66K - $96K/yr", "p2 pay")]:
        read(t, needle, label)
    w.click("/jobs-search?search=truck+driver&location=Atlanta,+GA&page=1")
    href = first_card_href(w.page_html)
    t = w.click(href)
    for needle, label in [("Posted 18 days ago", "posted"),
                          ("$100K/yr", "pay"), ("Full Time", "employment")]:
        read(t, needle, label)
    m = re.search(r'href="(/co/Dollar-General-Fleet)"', w.page_html)
    t = w.click(m.group(1))
    read(t, "1 open roles from Dollar General Fleet in this snapshot", "company open jobs")
    w.click("/c/Dollar-General-Fleet/Job/CDL-A-Truck-Driver/-in-Mcdonough,GA?jid=482a1c58fe133b8a")
    w.click("/jobs-search?search=truck+driver&location=Atlanta,+GA&page=1")
    t = w.filter(search="truck driver", location="Atlanta, GA", apply="quick")
    w.facts["quick"] = serp_count(t)
    assert w.facts["quick"] == 10
    read(t, "$26 - $28/hr", "quick first pay")
    href = first_card_href(w.page_html)
    t = w.click(href)
    read(t, "Full Time", "quick first employment")
    w.click("/jobs-search?search=truck+driver&location=Atlanta,+GA&apply=quick&remote=&days=&smin=&smax=&exp=")
    t = w.click("/jobs-search?search=truck+driver&location=Atlanta,+GA")
    cities = set(re.findall(r'class="job-location">[^<]*<a[^>]*>([^<]+)</a>', w.page_html))
    t = w.click("/jobs-search?search=truck+driver&location=Atlanta,+GA&page=2")
    cities |= set(re.findall(r'class="job-location">[^<]*<a[^>]*>([^<]+)</a>', w.page_html))
    w.facts["n_cities"] = len(cities)
    assert w.facts["n_cities"] == 7, f"distinct cities premise: {sorted(cities)}"
    w.compose()


def walk_6(w):
    w.nav("/", count=False)
    t = w.search("warehouse", "Dallas, TX")
    w.facts["base"] = serp_count(t)
    assert w.facts["base"] == 17
    t = w.filter(search="warehouse", location="Dallas, TX", apply="quick")
    w.facts["quick"] = serp_count(t)
    assert w.facts["quick"] == 8
    for needle, label in [("Forklift Operator", "title"), ("Proman Staffing", "company"),
                          ("Fort Worth, TX", "city"), ("$16.25 - $19.25/hr", "pay"),
                          ("Posted 8 hours ago", "posted")]:
        read(t, needle, label)
    href = first_card_href(w.page_html)
    t = w.click(href)
    read(t, "Full Time", "employment")
    m = re.search(r'href="(/co/Proman-Staffing)"', w.page_html)
    t = w.click(m.group(1))
    read(t, "1 open roles from Proman Staffing in this snapshot", "company open jobs")
    w.click("/c/Proman-Staffing/Job/Forklift-Operator/-in-Fort-Worth,TX?jid=024f93e335f888a9")
    t = w.click("/jobs-search?search=warehouse&location=Dallas,+TX&apply=quick&remote=&days=&smin=&smax=&exp=")
    hrefs = re.findall(r'class="job-title"><a href="([^"]+)"', w.page_html)
    for needle, label in [("Cold Environment Warehouse Packers", "second title"),
                          ("$13.50 - $14.50/hr", "second pay"),
                          ("Grand Prairie, TX", "second city")]:
        read(t, needle, label)
    t = w.click(hrefs[1])
    w.click("/jobs-search?search=warehouse&location=Dallas,+TX&apply=quick&remote=&days=&smin=&smax=&exp=")
    t = w.click("/jobs-search?search=warehouse&location=Dallas,+TX")
    t = w.filter(search="warehouse", location="Dallas, TX", days="5")
    w.facts["days5"] = serp_count(t)
    assert w.facts["days5"] == 10
    read(t, "Posted 8 hours ago", "days5 first posted")
    w.compose()


def walk_7(w):
    w.nav("/", count=False)
    t = w.search("software engineer", "San Francisco, CA")
    w.facts["base"] = serp_count(t)
    assert w.facts["base"] == 22
    href = first_card_href(w.page_html)
    t = w.click(href)
    for needle, label in [("Forward Deployed Software Engineer", "title"),
                          ("Veritus", "company"), ("San Francisco, CA", "location"),
                          ("On-site", "location type"), ("Full Time", "employment"),
                          ("Posted 7 hours ago", "posted"), ("New", "badge"),
                          ("Offices of Mental Health Practitioners", "industry"),
                          ("11 - 50 employees", "size"), ("OpenAI", "first platform")]:
        read(t, needle, label)
    m = re.search(r'href="(/co/Veritus)"', w.page_html)
    t = w.click(m.group(1))
    for needle, label in [("New York, NY", "hq"), ("veritussolutions.com", "website"),
                          ("11 open roles from Veritus in this snapshot", "open jobs")]:
        read(t, needle, label)
    m = re.search(r'href="(/co/Veritus/Jobs/-in-San-Francisco,CA)"', w.page_html)
    assert m, "company page must link its San Francisco jobs page"
    t = w.click(m.group(1))
    read(t, "1 open roles from Veritus in this snapshot", "sf jobs-page count")
    t = w.search("software engineer", "San Francisco, CA")
    t = w.filter(search="software engineer", location="San Francisco, CA", days="5")
    w.facts["days5"] = serp_count(t)
    assert w.facts["days5"] == 13
    href = first_card_href(w.page_html)
    t = w.click(href)
    read(t, "Posted 7 hours ago", "days5 first posted")
    assert "Quick apply" not in t.split("Job description")[0], "days5 first is not a quick apply"
    w.click("/jobs-search?search=software+engineer&location=San+Francisco,+CA&apply=&remote=&days=5&smin=&smax=&exp=")
    hrefs = re.findall(r'class="job-title"><a href="([^"]+)"', w.page_html)
    t = w.click(hrefs[1])
    for needle, label in [("Veritus", "second company"), ("Alameda, CA", "second city")]:
        read(t, needle, label)
    w.compose()


def walk_8(w):
    w.nav("/", count=False)
    t = w.search("registered nurse", "New York, NY")
    w.facts["base"] = serp_count(t)
    assert w.facts["base"] == 24
    href = first_card_href(w.page_html)
    t = w.click(href)
    for needle, label in [("Registered Nurse", "title"), ("CareOne", "company"),
                          ("East Brunswick, NJ", "city"), ("$39 - $57/hr", "pay"),
                          ("Full Time", "employment"), ("Posted 21 days ago", "posted")]:
        read(t, needle, label)
    m = re.search(r'href="(/co/CareOne)"', w.page_html)
    t = w.click(m.group(1))
    read(t, "1 open roles from CareOne in this snapshot", "company open jobs")
    m = re.search(r'href="(/co/CareOne/Jobs/-in-East-Brunswick,NJ)"', w.page_html)
    assert m, "company page must link its East Brunswick jobs page"
    t = w.click(m.group(1))
    read(t, "1 open roles from CareOne in this snapshot", "east brunswick jobs-page count")
    t = w.search("registered nurse", "New York, NY")
    t = w.filter(search="registered nurse", location="New York, NY", apply="quick")
    w.facts["quick"] = serp_count(t)
    assert w.facts["quick"] == 9
    for needle, label in [("Park Ave Gastroenterology", "quick first company"),
                          ("$40 - $50/hr", "quick first pay")]:
        read(t, needle, label)
    href = first_card_href(w.page_html)
    t = w.click(href)
    t = w.click("/jobs-search?search=registered+nurse&location=New+York,+NY&apply=quick&remote=&days=&smin=&smax=&exp=")
    t = w.click("/jobs-search?search=registered+nurse&location=New+York,+NY")
    hrefs = re.findall(r'class="job-title"><a href="([^"]+)"', w.page_html)
    t = w.click(hrefs[1])
    for needle, label in [("Private Duty Registered Nurse (RN)", "second title"),
                          ("Hoboken, NJ", "second city"), ("$35 - $45/hr", "second pay")]:
        read(t, needle, label)
    m = re.search(r'href="(/co/BAYADA-Home-Health-Care)"', w.page_html)
    t = w.click(m.group(1))
    for needle, label in [("6.87", "breakroom score"),
                          ("Based on 257 frontline", "breakroom response count")]:
        read(t, needle, label)
    w.compose()


def walk_9(w):
    w.nav("/", count=False)
    t = w.search("software engineer", "San Francisco, CA")
    w.facts["base"] = serp_count(t)
    assert w.facts["base"] == 22
    href = first_card_href(w.page_html)
    t = w.click(href)
    for needle, label in [("On-site", "location type"), ("Full Time", "employment"),
                          ("Posted 7 hours ago", "posted")]:
        read(t, needle, label)
    m = re.search(r'href="(/co/Veritus)"', w.page_html)
    t = w.click(m.group(1))
    for needle, label in [("Offices of Mental Health Practitioners", "industry"),
                          ("New York, NY", "hq")]:
        read(t, needle, label)
    t = w.search("software engineer", "San Francisco, CA")
    t = w.filter(search="software engineer", location="San Francisco, CA", remote="remote")
    w.facts["remote"] = serp_count(t)
    assert w.facts["remote"] == 1
    t = w.filter(search="software engineer", location="San Francisco, CA",
                 remote="remote", days="5")
    w.facts["days5"] = serp_count(t)
    assert w.facts["days5"] == 1
    t = w.click("/browse")
    t = w.click("/browse/titles/S")
    t = w.click("/Jobs/software-engineer")
    for needle, label in [("76 open Software Engineer roles in this snapshot", "roles"),
                          ("$147,524", "average pay")]:
        read(t, needle, label)
    t = w.click("/Salaries/software-engineer-Salary")
    for needle, label in [("$147,524 / year", "avg year"), ("$70.92 / hour", "avg hour"),
                          ("120,000", "25th percentile")]:
        read(t, needle, label)
    href = first_card_href(w.page_html)
    t = w.click(href)
    for needle, label in [("Full-Stack Software Engineer -- PRO Team", "nearby title"),
                          ("Viome Life Sciences", "nearby company")]:
        read(t, needle, label)
    w.compose()


def walk_10(w):
    w.nav("/", count=False)
    t = w.click("/browse")
    t = w.click("/browse/titles/R")
    t = w.click("/Jobs/registered-nurse")
    for needle, label in [("74 open Registered Nurse roles in this snapshot", "roles"),
                          ("$92,525", "average pay")]:
        read(t, needle, label)
    t = w.click("/Salaries/registered-nurse-Salary")
    for needle, label in [("$92,525 / year", "avg year"), ("$44.48 / hour", "avg hour"),
                          ("92,525", "median")]:
        read(t, needle, label)
    href = first_card_href(w.page_html)
    t = w.click(href)
    for needle, label in [("Registered Nurse Stepdown", "nearby title"),
                          ("Quick 2 Hire", "nearby company"),
                          ("On-site", "nearby location type"),
                          ("$47 - $50/hr", "nearby pay")]:
        read(t, needle, label)
    m = re.search(r'href="(/co/Quick-2-Hire)"', w.page_html)
    t = w.click(m.group(1))
    read(t, "1 open roles from Quick 2 Hire in this snapshot", "company open jobs")
    w.click("/c/Quick-2-Hire/Job/Registered-Nurse-Stepdown/-in-Seattle,WA?jid=74792a56887522ca")
    t = w.click("/Salaries/registered-nurse-Salary")
    for needle, label in [("San Mateo County, CA", "city1"), ("129,338", "city1 avg"),
                          ("Mineral, VA", "city2"), ("127,705", "city2 avg"),
                          ("Portola Valley, CA", "city3"), ("122,470", "city3 avg"),
                          ("Manager Interventional Radiology Rn", "related"),
                          ("147,291", "related avg")]:
        read(t, needle, label)
    t = w.search("registered nurse", "New York, NY")
    w.facts["ny"] = serp_count(t)
    assert w.facts["ny"] == 24
    t = w.filter(search="registered nurse", location="New York, NY", apply="quick")
    w.facts["ny_quick"] = serp_count(t)
    assert w.facts["ny_quick"] == 9
    for needle, label in [("Park Ave Gastroenterology", "quick first company"),
                          ("$40 - $50/hr", "quick first pay")]:
        read(t, needle, label)
    href = first_card_href(w.page_html)
    w.click(href)
    w.compose()


def walk_11(w):
    w.nav("/", count=False)
    t = w.click("/browse")
    t = w.click("/browse/titles/S")
    t = w.click("/Jobs/software-engineer")
    t = w.click("/Salaries/software-engineer-Salary")
    for needle, label in [("$147,524 / year", "avg year"), ("$70.92 / hour", "avg hour"),
                          ("147,524", "median"), ("95,500", "10th percentile"),
                          ("205,000", "90th percentile"),
                          ("Soledad, CA", "top city 1"), ("220,681", "top city 1 avg"),
                          ("Portola Valley, CA", "top city 2"), ("205,618", "top city 2 avg")]:
        read(t, needle, label)
    m = re.search(r'href="(/Salaries/software-engineer-Salary-in-San-Francisco,CA)"', w.page_html)
    assert m, "salary page must link its San Francisco version"
    t = w.click(m.group(1))
    for needle, label in [("$173,808 / year", "sf avg year"), ("$83.56 / hour", "sf avg hour"),
                          ("173,808", "sf median"), ("141,400", "sf 25th percentile")]:
        read(t, needle, label)
    href = first_card_href(w.page_html)
    t = w.click(href)
    for needle, label in [("Software Developer and SRE", "nearby title"),
                          ("Eitacies Inc", "nearby company")]:
        read(t, needle, label)
    # r3: the text now asks for the nearby job's COMPANY PROFILE open-roles
    # count, so the profile visit is a required gesture; the nationwide
    # search then runs from the company page's header search (no extra back).
    m = re.search(r'href="(/co/Eitacies-Inc)"', w.page_html)
    assert m, "nearby job detail must link its company profile"
    t = w.click(m.group(1))
    read(t, "1 open roles from Eitacies Inc in this snapshot", "nearby company open-roles count")
    t = w.search("software engineer")
    w.facts["national_jobs"] = serp_count(t)
    assert w.facts["national_jobs"] == 76
    t = w.filter(search="software engineer", exp="senior")
    w.facts["senior"] = serp_count(t)
    assert w.facts["senior"] == 12
    t = w.filter(search="software engineer", exp="senior", remote="remote")
    w.facts["senior_remote"] = serp_count(t)
    assert w.facts["senior_remote"] == 1
    for needle, label in [("Senior/Staff Software Engineer, Platform", "first title"),
                          ("AIDA Recruitment", "first company"),
                          ("$150K - $350K/yr", "first pay"),
                          ("Posted 6 days ago", "first posted")]:
        read(t, needle, label)
    href = first_card_href(w.page_html)
    t = w.click(href)
    read(t, "Senior/Staff Software Engineer, Platform", "opened first listing title")
    w.compose()


def walk_12(w):
    w.nav("/", count=False)
    t = w.click("/browse")
    m = re.search(r'href="(/browse/salaries)"', w.page_html)
    assert m, "browse page must link the salaries index"
    t = w.click(m.group(1))
    m = re.search(r'href="(/Salaries/accountant-Salary)"', w.page_html)
    assert m, "salaries index must link the Accountant salary page"
    t = w.click(m.group(1))
    for needle, label in [("$68,326 / year", "avg year"), ("$32.85 / hour", "avg hour"),
                          ("68,326", "median"), ("78,500", "75th percentile")]:
        read(t, needle, label)
    bands = re.findall(r'\$[\dK.]+K – \$[\dK.]+K\s*(\d+)% of jobs', w.page_text)
    w.facts["bands_ge15"] = sum(1 for b in bands if int(b) >= 15)
    assert w.facts["bands_ge15"] == 4
    t = w.search("accountant", "Denver, CO")
    w.facts["den"] = serp_count(t)
    assert w.facts["den"] == 12
    t = w.filter(search="accountant", location="Denver, CO", smin="70000")
    w.facts["den_70"] = serp_count(t)
    assert w.facts["den_70"] == 4
    for needle, label in [("Senior Accountant", "title"),
                          ("Matter Family Office", "company"),
                          ("$80K - $100K/yr", "pay")]:
        read(t, needle, label)
    href = first_card_href(w.page_html)
    t = w.click(href)
    for needle, label in [("Posted yesterday", "posted"), ("Full Time", "employment")]:
        read(t, needle, label)
    t = w.click("/jobs-search?search=accountant&location=Denver,+CO&apply=&remote=&days=&smin=70000&smax=&exp=")
    t = w.click("/jobs-search?search=accountant&location=Denver,+CO")
    t = w.filter(search="accountant", location="Denver, CO", days="10")
    w.facts["days10"] = serp_count(t)
    assert w.facts["days10"] == 10
    t = w.filter(search="accountant", location="Denver, CO", days="10", apply="quick")
    w.facts["quick"] = serp_count(t)
    assert w.facts["quick"] == 2
    t = w.click("/browse/salaries")
    m = re.search(r'href="(/Salaries/accountant-Salary-in-Denver,CO)"', w.page_html)
    assert m, "salaries index must link the Denver city page"
    t = w.click(m.group(1))
    for needle, label in [("$70,327 / year", "denver avg"), ("55,100", "denver 25th percentile")]:
        read(t, needle, label)
    w.compose()


def walk_13(w):
    w.nav("/", count=False)
    t = w.click("/blog/")
    cats_html = w.page_html.split('class="blog-cats"')[1].split('class="blog-list"')[0]
    w.facts["blog_cats"] = len(re.findall(r'href="/blog/category/', cats_html))
    assert w.facts["blog_cats"] == 7, "root + six data-driven subcategories"
    t = w.click("/blog/category/career-advice/trends/")
    m = re.search(r'(\d+) articles in this snapshot', t)
    w.facts["trends_count"] = m.group(1)
    assert w.facts["trends_count"] == "5"
    t = w.click("/blog/salary_exp/")
    for needle, label in [("4 Top Industry Insights to Fuel Your Job Search", "title"),
                          ("The ZipRecruiter Editors", "author"),
                          ("published 2023-03-07", "publish date"),
                          ("1. There Are More Jobs", "insight 1"),
                          ("2. Jobs Offer More Flexibility", "insight 2"),
                          ("3. Workplaces Want to Be More Diverse", "insight 3"),
                          ("4. Perks and Benefits Are a Priority", "insight 4"),
                          ("hottest job-market trends", "hottest trend line")]:
        read(t, needle, label)
    t = w.click("/blog/category/career-advice/trends/")
    m = re.search(r'href="(/blog/job-news-roundup-2022/)"', w.page_html)
    t = w.click(m.group(1))
    for needle, label in [("The ZipRecruiter Editors", "other author"),
                          ("published 2022-06-13", "other publish date")]:
        read(t, needle, label)
    t = w.click("/blog/")
    m = re.search(r'href="(/blog/category/career-advice/work-life/)"', w.page_html)
    assert m, "blog must list the Work Life category"
    t = w.click(m.group(1))
    m = re.search(r'(\d+) articles in this snapshot', t)
    w.facts["worklife_count"] = m.group(1)
    assert w.facts["worklife_count"] == "2"
    m = re.search(r'href="(/blog/rise-of-stay-at-home-dads/)"', w.page_html)
    t = w.click(m.group(1))
    read(t, "The Rise of Stay-at-Home Dads", "work life first article title")
    t = w.search("data analyst", "Seattle, WA")
    w.facts["da_sea"] = serp_count(t)
    assert w.facts["da_sea"] == 20
    t = w.filter(search="data analyst", location="Seattle, WA", days="5")
    w.facts["da_days5"] = serp_count(t)
    assert w.facts["da_days5"] == 4
    for needle, label in [("DKMRBH Inc", "first company"), ("$50 - $55/hr", "first pay")]:
        read(t, needle, label)
    href = first_card_href(w.page_html)
    t = w.click(href)
    read(t, "DKMRBH Inc", "opened first result company")
    w.compose()


def walk_14(w):
    w.nav("/", count=False)
    t = w.click("/blog/")
    t = w.click("/blog/category/career-advice/veterans/")
    w.facts["veterans_count"] = len(re.findall(r'<h2><a href="/blog/', w.page_html))
    assert w.facts["veterans_count"] == 2
    t = w.click("/blog/job-search-tips-for-veterans/")
    for needle, label in [("Job Search Tips Every Military Veteran Should Know", "title"),
                          ("Julia Pollak", "author"), ("published 2020-11-10", "publish date"),
                          ("updated 2022-06-16", "updated date"),
                          ("Where should I look for work", "tip 1"),
                          ("What kinds of industries should I explore", "tip 3")]:
        read(t, needle, label)
    t = w.click("/blog/category/career-advice/veterans/")
    t = w.click("/blog/the-12-best-job-industries-for-veterans/")
    for needle, label in [("The 12 Best Job Industries For Veterans", "title"),
                          ("Kat Boogaard", "author"), ("published 2017-10-20", "publish date")]:
        read(t, needle, label)
    t = w.click("/blog/")
    for needle, label in [("Dressing for Hot Weather Job Interviews", "hot title"),
                          ("Nicole Cavazos", "hot author"),
                          ("2018-08-24", "hot publish date"),
                          ("The Hiring Process", "hot category")]:
        read(t, needle, label)
    t = w.search("electrician", "Houston, TX")
    w.facts["ele_hou"] = serp_count(t)
    assert w.facts["ele_hou"] == 17
    t = w.filter(search="electrician", location="Houston, TX", days="5")
    w.facts["ele_days5"] = serp_count(t)
    assert w.facts["ele_days5"] == 4
    t = w.filter(search="electrician", location="Houston, TX", days="5", apply="quick")
    w.facts["ele_quick"] = serp_count(t)
    assert w.facts["ele_quick"] == 4
    for needle, label in [("FALCON CONTROL SYSTEMS", "first company"),
                          ("$20 - $40/hr", "first pay"),
                          ("Posted 19 hours ago", "first posted")]:
        read(t, needle, label)
    href = first_card_href(w.page_html)
    t = w.click(href)
    read(t, "FALCON CONTROL SYSTEMS", "opened first listing company")
    w.compose()


def walk_15(w):
    w.nav("/", count=False)
    t = w.click("/authn/register?realm=candidates")
    w.fill("name", "Contract Walker")
    w.fill("email", "rereview.t15@wh-review.test")
    w.fill("password", "RereviewPass123!")
    w.fill("location", "Dallas, TX")
    t = w.post("/authn/register", {"name": "Contract Walker",
                                   "email": "rereview.t15@wh-review.test",
                                   "password": "RereviewPass123!",
                                   "location": "Dallas, TX"})
    read(t, "My Profile", "profile landing after register")
    t = w.search("warehouse", "Dallas, TX")
    w.facts["base"] = serp_count(t)
    assert w.facts["base"] == 17
    t = w.filter(search="warehouse", location="Dallas, TX", apply="quick")
    w.facts["quick"] = serp_count(t)
    assert w.facts["quick"] == 8
    href = first_card_href(w.page_html)
    t = w.click(href)
    for needle, label in [("Forklift Operator", "title"), ("Proman Staffing", "company")]:
        read(t, needle, label)
    t = w.post("/apply/024f93e335f888a9", {})
    for needle, label in [("Application sent", "confirmation heading"),
                          ("Forklift Operator", "job title"),
                          ("Proman Staffing", "job company"),
                          ("Status: Applied", "application status")]:
        read(t, needle, label)
    t = w.click("/jobseeker/applications")
    for needle, label in [("Forklift Operator", "applications job"),
                          ("Proman Staffing", "applications company"),
                          ("Status: Applied", "applications status"),
                          ("1-Click Application submitted", "timeline note")]:
        read(t, needle, label)
    w.facts["saved_start"] = 0
    w.compose()


def walk_16(w):
    w.nav("/", count=False)
    t = w.click("/authn/login?realm=candidates")
    w.fill("email", "alice.j@test.com")
    w.fill("password", "TestPass123!")
    t = w.post("/authn/login?realm=candidates",
               {"email": "alice.j@test.com", "password": "TestPass123!"})
    t = w.click("/jobseeker/profile")
    for needle, label in [("Registered Nurse, BSN — 6 years ICU", "headline"),
                          ("Brooklyn, NY", "location")]:
        assert f'value="{needle}"' in w.page_html, f"premise missing: {label}"
    w.facts["years"] = 6
    t = w.click("/jobseeker/resume")
    read(t, "Registered Nurse — ICU", "resume title")
    w.facts["resume_skills"] = 6
    t = w.click("/jobseeker/saved-jobs")
    for needle, label in [("Registered Nurse (RN) - Bilingual Spanish/English (Urology)", "s1 title"),
                          ("New York Health", "s1 company"), ("Manhattan, NY", "s1 city"),
                          ("$52/hr", "s1 pay"),
                          ("Registered Nurse IV Drip - Park Slope", "s2 title"),
                          ("Brooklyn, NY", "s2 city"), ("$52 - $54/hr", "s2 pay"),
                          ("Registered Nurse (RN)", "s3 title"),
                          ("New York Cancer & Blood Specialists", "s3 company")]:
        read(t, needle, label)
    t = w.post("/save/06a2fa466a9d2928", {"next": "/jobseeker/saved-jobs"})
    assert "New York Health" not in t, "urology listing must be unsaved"
    read(t, "2 saved jobs", "remaining two jobs")
    for needle, label in [("Registered Nurse IV Drip - Park Slope", "remaining Brooklyn"),
                          ("Registered Nurse (RN)", "remaining Manhattan")]:
        read(t, needle, label)
    t = w.click("/c/Restore-Hyper-Wellness-RHWS037/Job/Registered-Nurse-IV-Drip-Park-Slope/-in-Brooklyn,NY?jid=1b13c75885354910")
    for needle, label in [("Posted 4 days ago", "brooklyn posted"),
                          ("Part Time", "brooklyn employment")]:
        read(t, needle, label)
    w.click("/jobseeker/saved-jobs")
    t = w.click("/jobseeker/alerts")
    w.fill("term", "licensed practical nurse")
    w.fill("location", "Brooklyn, NY")
    w.select("frequency", "weekly")
    t = w.post("/jobseeker/alerts", {"term": "licensed practical nurse",
                                     "location": "Brooklyn, NY",
                                     "frequency": "weekly"})
    for needle, label in [("registered nurse", "alert 1 term"),
                          ("New York, NY", "alert 1 location"),
                          ("Daily", "alert 1 frequency"),
                          ("licensed practical nurse", "alert 2 term"),
                          ("Brooklyn, NY", "alert 2 location"),
                          ("Weekly", "alert 2 frequency")]:
        read(t, needle, label)
    w.compose()


def walk_17(w):
    w.nav("/", count=False)
    t = w.click("/authn/login?realm=candidates")
    w.fill("email", "bob.c@test.com")
    w.fill("password", "TestPass123!")
    t = w.post("/authn/login?realm=candidates",
               {"email": "bob.c@test.com", "password": "TestPass123!"})
    t = w.click("/jobseeker/profile")
    t = w.click("/jobseeker/applications")
    for needle, label in [("Software Engineer", "app title"), ("JOLT", "app company"),
                          ("San Francisco, CA", "app city"), ("2026-09-21", "applied date"),
                          ("Interviewing", "current status"),
                          ("1-Click Application submitted", "tl1 note"),
                          ("The employer viewed your application", "tl2 note"),
                          ("The employer invited you to schedule a phone screen", "tl3 note")]:
        read(t, needle, label)
    href = re.search(r'href="(/c/JOLT/[^"]+)"', w.page_html).group(1)
    t = w.click(href)
    for needle, label in [("$125K - $135K/yr", "job pay"), ("On-site", "location type"),
                          ("Posted 17 days ago", "posted age")]:
        read(t, needle, label)
    t = w.click("/jobseeker/profile")
    t = w.click("/jobseeker/resume")
    for needle, label in [("Software Engineer — Full Stack", "resume title"),
                          ("complete", "completeness label"),
                          ("Backend-leaning full-stack engineer; Python, Go, Postgres.", "summary"),
                          ("JOLT", "experience employer"), ("2023-01", "experience start"),
                          ("Python", "skill 1"), ("Go", "skill 2"),
                          ("PostgreSQL", "skill 3"), ("React", "skill 4")]:
        read(t, needle, label)
    t = w.click("/jobseeker/saved-jobs")
    t = w.post("/save/032e0b0150231b0d", {"next": "/jobseeker/saved-jobs"})
    read(t, "1 saved jobs", "one saved job remains")
    read(t, "JOLT", "remaining saved employer")
    t = w.click("/jobseeker/alerts")
    w.fill("term", "data engineer")
    w.fill("location", "Seattle, WA")
    w.select("frequency", "weekly")
    t = w.post("/jobseeker/alerts", {"term": "data engineer",
                                     "location": "Seattle, WA",
                                     "frequency": "weekly"})
    for needle, label in [("software engineer", "alert 1 term"),
                          ("data engineer", "alert 2 term"),
                          ("Seattle, WA", "alert 2 location"),
                          ("Weekly", "alert 2 frequency")]:
        read(t, needle, label)
    w.compose()


def walk_18(w):
    w.nav("/", count=False)
    t = w.click("/authn/login?realm=candidates")
    w.fill("email", "dana.k@test.com")
    w.fill("password", "TestPass123!")
    t = w.post("/authn/login?realm=candidates",
               {"email": "dana.k@test.com", "password": "TestPass123!"})
    t = w.click("/jobseeker/profile")
    t = w.click("/jobseeker/resume")
    for needle, label in [("Senior Accountant (CPA)", "resume title"),
                          ("CPA with 8 years across public accounting and industry; month-end close, audit readiness, NetSuite.", "summary"),
                          ("Matter Family Office", "exp1 employer"), ("2022-04", "exp1 start"),
                          ("Caribou Financial", "exp2 employer"), ("2019-06", "exp2 start"),
                          ("BS, Accounting", "edu1"), ("Metro State Denver", "edu1 school"),
                          ("CPA license", "edu2"), ("Colorado BOA", "edu2 school"),
                          ("NetSuite (5y)", "skill 1"), ("Month-end close (8y)", "skill 2"),
                          ("GAAP (8y)", "skill 3"), ("Excel (8y)", "skill 4"),
                          ("Audit prep (6y)", "skill 5"), ("SQL (3y)", "skill 6")]:
        read(t, needle, label)
    w.fill("skill_7", "QuickBooks")
    w.fill("skill_yrs_7", "2")
    t = w.post("/jobseeker/resume", {"title": "Senior Accountant (CPA)",
                                     "summary": "CPA with 8 years across public accounting and industry; month-end close, audit readiness, NetSuite.",
                                     "exp_role_1": "Senior Accountant",
                                     "exp_employer_1": "Matter Family Office",
                                     "exp_start_1": "2022-04", "exp_end_1": "Present",
                                     "exp_text_1": "Own the monthly close for 4 entities; led the NetSuite migration.",
                                     "exp_role_2": "Staff Accountant II",
                                     "exp_employer_2": "Caribou Financial",
                                     "exp_start_2": "2019-06", "exp_end_2": "2022-03",
                                     "exp_text_2": "Audit prep, reconciliations, and AP/IC review.",
                                     "edu_degree_1": "BS, Accounting",
                                     "edu_school_1": "Metro State Denver", "edu_year_1": "2018",
                                     "edu_degree_2": "CPA license",
                                     "edu_school_2": "Colorado BOA", "edu_year_2": "2020",
                                     "skill_1": "NetSuite", "skill_yrs_1": "5",
                                     "skill_2": "Month-end close", "skill_yrs_2": "8",
                                     "skill_3": "GAAP", "skill_yrs_3": "8",
                                     "skill_4": "Excel", "skill_yrs_4": "8",
                                     "skill_5": "Audit prep", "skill_yrs_5": "6",
                                     "skill_6": "SQL", "skill_yrs_6": "3",
                                     "skill_7": "QuickBooks", "skill_yrs_7": "2"})
    for needle, label in [("QuickBooks (2y)", "new skill"), ("updated 2026-09-29", "updated at")]:
        read(t, needle, label)
    w.facts["skill_count"] = 7
    t = w.click("/jobseeker/applications")
    for needle, label in [("Senior Accountant", "app title"),
                          ("Matter Family Office", "app company"),
                          ("Denver, CO", "app city"), ("Withdrawn", "app status"),
                          ("2026-09-20", "tl1"), ("2026-09-22", "tl2"),
                          ("2026-09-25", "tl3")]:
        read(t, needle, label)
    href = re.search(r'href="(/c/Matter-Family-Office/[^"]+)"', w.page_html).group(1)
    t = w.click(href)
    for needle, label in [("$80K - $100K/yr", "job pay"), ("On-site", "location type"),
                          ("Posted yesterday", "posted age")]:
        read(t, needle, label)
    t = w.click("/jobseeker/profile")
    t = w.click("/jobseeker/alerts")
    w.fill("term", "staff accountant")
    w.fill("location", "Denver, CO")
    w.select("frequency", "weekly")
    t = w.post("/jobseeker/alerts", {"term": "staff accountant",
                                     "location": "Denver, CO",
                                     "frequency": "weekly"})
    for needle, label in [("accountant", "alert 1 term"), ("Denver, CO", "alert 1 location"),
                          ("Daily", "alert 1 frequency"),
                          ("remote bookkeeping", "alert 2 term"),
                          ("Anywhere", "alert 2 location"), ("Weekly", "alert 2 frequency"),
                          ("staff accountant", "alert 3 term"),
                          ("Denver, CO", "alert 3 location"), ("Weekly", "alert 3 frequency")]:
        read(t, needle, label)
    w.compose()


def walk_19(w):
    w.nav("/", count=False)
    t = w.search("teacher", "Chicago, IL")
    w.facts["teacher_chi"] = serp_count(t)
    assert w.facts["teacher_chi"] == 21
    href = first_card_href(w.page_html)
    t = w.click(href)
    for needle, label in [("Travel Special Education Teacher", "title"),
                          ("Aya Education", "company"), ("Posted 2 days ago", "posted"),
                          ("Other", "employment"), ("$2.3K - $2.5K/wk", "pay")]:
        read(t, needle, label)
    m = re.search(r'href="(/co/Aya-Education)"', w.page_html)
    t = w.click(m.group(1))
    for needle, label in [("Recruiting and Staffing Services", "industry"),
                          ("1 open roles from Aya Education in this snapshot", "open jobs")]:
        read(t, needle, label)
    t = w.search("receptionist", "Los Angeles, CA")
    w.facts["rec_la"] = serp_count(t)
    assert w.facts["rec_la"] == 19
    t = w.filter(search="receptionist", location="Los Angeles, CA", days="5")
    w.facts["rec_days5"] = serp_count(t)
    assert w.facts["rec_days5"] == 9
    for needle, label in [("EXPERIENCED Dental Office Treatment Coordinator / Receptionist", "first title"),
                          ("Restore Dental", "first company"), ("$20 - $35/hr", "first pay")]:
        read(t, needle, label)
    t = w.click("/browse")
    t = w.click("/browse/titles/R")
    titles = re.findall(r'<li><a href="/Jobs/([^"]+)">([^<]+)</a>', w.page_html)
    w.facts["r_first_two"] = [x[1] for x in titles[:2]]
    w.facts["r_count"] = len(titles)
    assert w.facts["r_first_two"] == ["Receptionist", "Registered Nurse"]
    assert w.facts["r_count"] == 2
    # r3: the text now routes through the first title's OWN page for its
    # open-roles count before its salary page (no direct salary shortcut).
    t = w.click("/Jobs/receptionist")
    read(t, "26 open Receptionist roles in this snapshot", "first title open-roles count")
    m = re.search(r'href="(/Salaries/receptionist-Salary)"', w.page_html)
    assert m, "title page must link its salary page"
    t = w.click(m.group(1))
    read(t, "$37,057 / year", "first title average yearly pay")
    w.compose()


WALKS = {
    "ZipRecruiter--0": walk_0, "ZipRecruiter--1": walk_1,
    "ZipRecruiter--2": walk_2, "ZipRecruiter--3": walk_3,
    "ZipRecruiter--4": walk_4, "ZipRecruiter--5": walk_5,
    "ZipRecruiter--6": walk_6, "ZipRecruiter--7": walk_7,
    "ZipRecruiter--8": walk_8, "ZipRecruiter--9": walk_9,
    "ZipRecruiter--10": walk_10, "ZipRecruiter--11": walk_11,
    "ZipRecruiter--12": walk_12, "ZipRecruiter--13": walk_13,
    "ZipRecruiter--14": walk_14, "ZipRecruiter--15": walk_15,
    "ZipRecruiter--16": walk_16, "ZipRecruiter--17": walk_17,
    "ZipRecruiter--18": walk_18, "ZipRecruiter--19": walk_19,
}


# --------------------------------------------------------------------- audit --

def audit():
    zr_mod.app.config.update(TESTING=True)
    failures = []
    measured = {}
    for task in TASKS:
        tid = task["id"]
        assert tid in WALKS, f"no walk for {tid}"
        # shape checks (7-key reviewer contract: the five contributor keys
        # plus verifier_path + judge_rubric; an answer key is never allowed)
        keys = set(task.keys())
        want = {"web_name", "id", "ques", "web", "upstream_url",
                "verifier_path", "judge_rubric"}
        if keys != want:
            failures.append(f"{tid}: expected 7 contract keys, got {sorted(keys)}")
        if "answer" in keys:
            failures.append(f"{tid}: answer key is forbidden in tasks.jsonl")
        words = len(task["ques"].split())
        if words > 100:
            failures.append(f"{tid}: {words} words (max 100)")
        if task["web"] != "http://localhost:40173/":
            failures.append(f"{tid}: web {task['web']!r} != slot 40173")
        # leak check: no ground-truth anchors may appear in the task text
        anchors = ANCHORS.get(tid, [])
        for anchor in anchors:
            if anchor.lower() in task["ques"].lower():
                failures.append(f"{tid}: answer anchor {anchor!r} leaks into the task text")
        # measured walk on a fresh client
        zr_mod.app.config.update(TESTING=True)
        client = zr_mod.app.test_client()
        w = Walk(client, tid)
        try:
            WALKS[tid](w)
        except AssertionError as e:
            failures.append(f"{tid}: walk failed: {e}")
            continue
        measured[tid] = w.atomic
        if w.atomic < 15:
            failures.append(f"{tid}: measured {w.atomic} atomic steps (< 15)")
        print(f"[walk] {tid}: {w.atomic} atomic steps, "
              f"{len(w.facts)} verified premises")
    print()
    for tid, n in sorted(measured.items()):
        print(f"  {tid}: {n}")
    if failures:
        print("\nFAILURES:")
        for f in failures:
            print(" -", f)
        sys.exit(1)
    print(f"\n[audit] all {len(TASKS)} tasks green: >=15 measured atomic steps, "
          f"premises verified, no leakage, shape OK")


# Ground-truth anchors that must NEVER appear in a task's text (they are the
# answers the task asks the agent to discover on the mirror).
ANCHORS = {
    "ZipRecruiter--0": ["YO AI Labs", "$50 - $100/hr", "Abu Dhabi", "Alameda"],
    "ZipRecruiter--1": ["Park Ave Gastroenterology", "$40 - $50/hr", "Moorestown"],
    "ZipRecruiter--2": ["Matter Family Office", "$80K - $100K", "ELECTRO MAGNETIC"],
    "ZipRecruiter--3": ["27", "part-time", "Supplemental Health Care"],
    "ZipRecruiter--4": ["Burnt", "$144K - $190K", "Tek Fusion", "RFA Engineering"],
    "ZipRecruiter--5": ["Epes Transport", "CompostNow"],
    "ZipRecruiter--6": ["Proman Staffing", "$16.25 - $19.25"],
    "ZipRecruiter--7": ["ElevenLabs", "Forward Deployed"],
    "ZipRecruiter--8": ["CareOne", "$39 - $57/hr", "6.87"],
    "ZipRecruiter--9": ["$147,524", "Soledad", "Senior Embedded Systems Engineer"],
    "ZipRecruiter--10": ["$92,525", "Quick 2 Hire", "$47 - $50/hr", "Manager Interventional"],
    "ZipRecruiter--11": ["$173,808", "$83.56", "Eitacies"],
    "ZipRecruiter--12": ["$68,326", "Matter Family Office", "$70,327"],
    "ZipRecruiter--13": ["The ZipRecruiter Editors", "2023-03-07", "Stay-at-Home"],
    "ZipRecruiter--14": ["Julia Pollak", "2020-11-10", "Nicole Cavazos"],
    "ZipRecruiter--15": ["Application sent"],
    "ZipRecruiter--16": ["New York Health", "Restore Hyper Wellness"],
    "ZipRecruiter--17": ["JOLT", "$125K - $135K"],
    "ZipRecruiter--18": ["Matter Family Office", "NetSuite"],
    "ZipRecruiter--19": ["26", "37,057"],
}


if __name__ == "__main__":
    audit()
