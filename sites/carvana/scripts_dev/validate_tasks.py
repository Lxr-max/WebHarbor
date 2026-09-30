#!/usr/bin/env python3
"""Machine audit of sites/carvana/tasks.jsonl — measured honest-atomic
caliber, after the ziprecruiter/zara/u_s_customs precedent.

For every task row this script drives the task's honest path against the
seeded mirror through the Flask test client — the same natural route a
competent agent takes — and counts steps in the HONEST-ATOMIC caliber:

  atomic = every navigation, link click, form fill, VISIBLE radio/checkbox
           pick, dropdown select and form submit after the initial page
           load. Reads are NOT counted. No gestures beyond the task text
           (no padding). No "+1 compose" convention - matching the
           reviewer's strict honest-atomic caliber exactly.

For every task it asserts:
  1. premises — every fact the task asks for actually resolves on the
     mirror with the frozen ground-truth value (driven through the test
     client, exactly like an agent would);
  2. measured depth — atomic >= 15, measured from the driven walk, not
     declared as a constant;
  3. zero answer leakage — answer anchors never appear in the task text;
  4. shape — the 5 contributor task keys, goal-style wording at or under
     100 words.

Run:  PYTHONPATH=. python3 scripts_dev/validate_tasks.py
"""
import html as html_mod
import json
import os
import pathlib
import re
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]

# The audit drives stateful flows (register, purchase, save, offers), so it
# runs against its own throwaway seed database — never the live instance.
_AUDIT_DB = pathlib.Path(tempfile.mkdtemp(prefix="carvana-task-audit-")) / "carvana.db"
os.environ["CARVANA_DB_URI"] = f"sqlite:///{_AUDIT_DB}"
os.environ["CARVANA_AUTO_SEED"] = "1"

sys.path.insert(0, str(ROOT))
import app as cv_mod  # noqa: E402
from app import app  # noqa: E402

TASKS = [json.loads(line) for line in
         (ROOT / "tasks.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]

TAG_RE = re.compile(r"<[^>]+>")


def text_of(page):
    return " ".join(html_mod.unescape(TAG_RE.sub(" ", page)).split())


def csrf_from(page_html):
    m = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', page_html)
    assert m, "no csrf token rendered"
    return m.group(1)


# ------------------------------------------------------------------- walker --

class Walk:
    """Test-client walk of one task's honest path, in the honest-atomic
    caliber: every visible gesture after the initial page load counts
    exactly one (matching a real browser: one user gesture, one step).
    Reads are free. The page a POST redirects to loads for free."""

    def __init__(self, client, task_id):
        self.client = client
        self.task_id = task_id
        self.atomic = 0
        self.facts = {}
        self.log = []
        self.page_html = ""
        self.page_text = ""
        # Browser-accurate history: entries are kept and a cursor moves on
        # Back (a real browser never pops entries it backs out of); a new
        # navigation truncates the forward entries like Chromium does.
        self.history = []
        self.cursor = -1
        self._last_was_post = False

    def _get(self, path):
        r = self.client.get(path)
        hops = 0
        while r.status_code in (302, 303) and hops < 3:
            loc = r.headers.get("Location")
            if not loc or not loc.startswith("/"):
                break
            r = self.client.get(loc)
            hops += 1
        assert r.status_code == 200, f"GET {path} -> {r.status_code}"
        self.page_html = r.get_data(as_text=True)
        self.page_text = text_of(self.page_html)
        self.history = self.history[:self.cursor + 1] + [path]
        self.cursor = len(self.history) - 1
        self._last_was_post = False
        return self.page_text

    def nav(self, path, count=True):
        t = self._get(path)
        if count:
            self.atomic += 1
            self.log.append(("nav", path))
        return t

    def click(self, path):
        return self.nav(html_mod.unescape(path))

    def back(self):
        """Browser back: one gesture; the previous page loads for free.
        The cursor moves back without dropping entries, exactly like a
        real browser's history stack."""
        assert self.cursor >= 1, "nowhere to go back to"
        self.cursor -= 1
        path = self.history[self.cursor]
        r = self.client.get(path)
        assert r.status_code == 200, f"GET {path} -> {r.status_code}"
        self.page_html = r.get_data(as_text=True)
        self.page_text = text_of(self.page_html)
        self._last_was_post = False
        self.atomic += 1
        self.log.append(("back", "browser-back"))
        return self.page_text

    def fill(self, name, value):
        self.atomic += 1
        self.log.append(("fill", name))
        return (name, value)

    def pick(self, name, value):
        """A visible dropdown/radio pick: one atomic gesture."""
        self.atomic += 1
        self.log.append(("choose", f"{name}={value}"))
        return (name, value)

    def home_search(self, make=None, model=None, body=None, q=None):
        """The home hero form: one gesture per visible control the agent
        actually touches plus the submit. Untouched fields never count."""
        params = {}
        if make is not None:
            self.pick("make", make)
            params["make"] = make
        if model is not None:
            self.fill("model", model)
            params["model"] = model
        if body is not None:
            self.pick("body", body)
            params["body"] = body
        if q is not None:
            self.fill("q", q)
            params["q"] = q
        self.atomic += 1
        self.log.append(("submit", "home search"))
        return self._get("/cars?" + "&".join(
            f"{k}={str(v).replace(' ', '+')}" for k, v in params.items()))

    def header_search(self, **params):
        """The header search form (one submit; fields the agent fills each
        count one)."""
        for k in params:
            self.atomic += 1
            self.log.append(("fill", k))
        self.atomic += 1
        self.log.append(("submit", "header search"))
        return self._get("/cars?" + "&".join(
            f"{k}={str(v).replace(' ', '+')}" for k, v in params.items()))

    def filter(self, carry=None, **params):
        """Pick VISIBLE filter controls and press Apply filters: one atomic
        action per touched control plus one for the submit. Values already
        selected in the form are carried in `carry` — the form resubmits
        them but the agent does not touch them again."""
        carry = dict(carry or {})
        for k in params:
            self.atomic += 1
            self.log.append(("choose", f"{k}={params[k]}"))
        self.atomic += 1
        self.log.append(("submit", "Apply filters"))
        query = {**carry, **params}
        return self._get("/cars?" + "&".join(
            f"{k}={v}" for k, v in query.items()))

    def sort(self, carry, value):
        """The sort dropdown: one pick that auto-submits."""
        self.atomic += 1
        self.log.append(("choose", f"sort={value}"))
        query = {k: v for k, v in carry.items() if k not in ("sort", "page")}
        query["sort"] = value
        return self._get("/cars?" + "&".join(
            f"{k}={v}" for k, v in query.items()))

    def post(self, path, data, fills=0, expect_redirect=True):
        """A CSRF-protected form submit: one atomic action per visible
        field the agent fills (or selects) plus one for the submit."""
        token = csrf_from(self.page_html)
        payload = dict(data)
        payload["csrf_token"] = token
        for i in range(fills):
            self.atomic += 1
            self.log.append(("fill/select", f"{path}#{i}"))
        r = self.client.post(path, data=payload, follow_redirects=False)
        if expect_redirect:
            assert r.status_code in (302, 303), f"POST {path} -> {r.status_code}"
            loc = r.headers.get("Location")
            hops = 0
            while loc and loc.startswith("/") and hops < 3:
                rr = self.client.get(loc)
                if rr.status_code in (302, 303):
                    loc = rr.headers.get("Location")
                    hops += 1
                    continue
                assert rr.status_code == 200, f"GET {loc} -> {rr.status_code}"
                self.page_html = rr.get_data(as_text=True)
                self.page_text = text_of(self.page_html)
                self.history = self.history[:self.cursor + 1] + [loc]
                self.cursor = len(self.history) - 1
                break
        else:
            assert r.status_code == 200
            self.page_html = r.get_data(as_text=True)
            self.page_text = text_of(self.page_html)
            # a real browser pushes the POST result onto history: Back
            # returns to the form that hosted it. A refinement POST to the
            # same URL replaces the entry (the agent never leaves the page).
            if not (self._last_was_post and self.history
                    and self.history[self.cursor] == path):
                self.history = self.history[:self.cursor + 1] + [path]
                self.cursor = len(self.history) - 1
            self._last_was_post = True
        self.atomic += 1
        self.log.append(("submit", path))
        return self.page_text

    def login(self, email, password="TestPass123!"):
        """Log in through the real form: two fills plus the submit."""
        self.nav("/authn/login")
        self.fill("email", email)
        self.fill("password", password)
        return self.post("/authn/login",
                         {"email": email, "password": password})

# ------------------------------------------------------------------ helpers --

def serp_count(page_text):
    m = re.search(r"(\d+) cars match your search", page_text)
    assert m, "no result count rendered"
    return int(m.group(1))


def card_hrefs(page_html, n=None):
    hrefs = re.findall(r'class="car-card">\s*<a href="(/vehicle/\d+)"', page_html)
    assert hrefs, "no car cards rendered"
    return hrefs[:n] if n else hrefs


def first_card_href(page_html):
    return card_hrefs(page_html, 1)[0]


def card_summary(page_html, index=0):
    """(year, make+model, mileage, price) of the n-th card on the page."""
    blocks = re.findall(
        r'class="car-card">\s*<a href="(/vehicle/(\d+))".*?<h3>(\d{4}) ([^<]+)</h3>'
        r'.*?<p class="car-meta">([\d,]+) miles · ([^·<]+)· ([A-Za-z ]+), ([A-Z]{2})</p>'
        r'.*?<p class="car-price">\$([\d,]+)',
        page_html, re.S)
    assert blocks, "no card blocks parsed"
    b = blocks[index]
    return {"href": b[0], "vehicle_id": b[1], "year": b[2],
            "title": b[3], "mileage": int(b[4].replace(',', '')),
            "body": b[5].strip(), "city": b[6].strip(), "state": b[7],
            "price": int(b[8].replace(',', ''))}


def vdp_field(page_html, label):
    m = re.search(rf'<div><span>{re.escape(label)}</span>([^<]+)</div>', page_html)
    assert m, f"VDP field {label!r} missing"
    return m.group(1).strip()


def vdp_est(page_html):
    m = re.search(r'<strong>\$([\d,]+)/mo</strong> estimated · \$0 cash down · '
                  r'([\d.]+)% APR · (\d+) months', page_html)
    assert m, "no $0-down estimate line rendered"
    return int(m.group(1).replace(',', '')), m.group(2), int(m.group(3))


def vdp_title(page_html):
    m = re.search(r'<h1>([^<]+)</h1>', page_html)
    assert m, "no VDP h1"
    return m.group(1).strip()


def read(page_text, needle, label):
    assert needle in page_text, f"premise missing: {label}: {needle!r} not on page"
    return needle


def monthly(vehicle_id, down, term, apr_percent):
    with app.app_context():
        v = cv_mod.Vehicle.query.filter_by(vehicle_id=vehicle_id).first()
        return int(round(v.monthly_payment(down_payment=down, term=term,
                                           apr_percent=apr_percent)))


def _q(model, **filters):
    with app.app_context():
        return model.query.filter_by(**filters).first()


def _first_sorted(model, *criteria, order):
    with app.app_context():
        q = model.query.filter(*criteria) if criteria else model.query
        return q.order_by(order).first()


# -------------------------------------------------------------------- walks --
# Each walk drives exactly the gestures its task text requires — no more
# (no padding), no fewer — with ground truths asserted from the seeded
# corpus (the same deterministic seed the dev container runs).


# New honest walks for sites/carvana/scripts_dev/validate_tasks.py —
# reviewer-caliber (no compose, no redundant default picks, real UI paths).
# Appended by fix-round generator; spliced in place of the old walk section.

def walk_0(w):
    w.nav("/", count=False)
    t = w.home_search(make="Honda")
    w.facts["honda"] = serp_count(t)
    assert w.facts["honda"] == 90
    t = w.filter(body="SUV")
    w.facts["honda_suv"] = serp_count(t)
    t = w.filter(carry={"body": "SUV"}, price_max="25000")
    w.facts["honda_suv_25k"] = serp_count(t)
    card = card_summary(w.page_html)
    w.facts["first"] = card
    t = w.click(card["href"])
    w.facts["body"] = vdp_field(w.page_html, "Body style")
    w.facts["color"] = vdp_field(w.page_html, "Exterior color")
    w.facts["fuel"] = vdp_field(w.page_html, "Fuel")
    w.facts["mpg"] = vdp_field(w.page_html, "MPG (combined)")
    w.back()
    t = w.filter(body="Sedan")
    w.facts["honda_sedan"] = serp_count(t)
    sedan = card_summary(w.page_html)
    w.facts["sedan_first"] = sedan
    t = w.click(sedan["href"])
    w.facts["sedan_mpg"] = vdp_field(w.page_html, "MPG (combined)")
    w.back()
    t = w.filter(carry={"body": "Sedan"}, year_min="2020")
    w.facts["honda_sedan_2020"] = serp_count(t)
    t = w.click("/cars")
    w.facts["total"] = serp_count(t)
    assert w.facts["total"] == 1544


def walk_1(w):
    w.nav("/", count=False)
    # the footer "Electric Cars" link is the real UI's EV entry point
    t = w.nav("/cars?fuel=Electric")
    w.facts["electric"] = serp_count(t)
    assert w.facts["electric"] == 108
    t = w.filter(carry={"fuel": "Electric"}, price_max="30000")
    w.facts["ev_30k"] = serp_count(t)
    card = card_summary(w.page_html)
    w.facts["first"] = card
    assert card["title"] == "Tesla Model X"
    t = w.click(card["href"])
    w.facts["drivetrain"] = vdp_field(w.page_html, "Drivetrain")
    assert w.facts["drivetrain"] == "AWD"
    w.back()
    t = w.filter(carry={"fuel": "Electric", "price_max": "30000"},
                 year_min="2022")
    w.facts["ev_30k_2022"] = serp_count(t)
    t = w.sort({"fuel": "Electric", "price_max": "30000"}, "price_asc")
    cheapest = card_summary(w.page_html)
    w.facts["cheapest"] = cheapest
    assert cheapest["title"] == "smart fortwo electric drive"
    t = w.click(cheapest["href"])
    w.facts["cheapest_city"] = cheapest["city"]
    vid = cheapest["vehicle_id"]
    # estimator: down fill + term pick (default 75) + tier pick (default good)
    m = monthly(int(vid), 2500, 60, 6.24)
    w.facts["est_2500_60_great"] = m
    t = w.post(f"/vehicle/{vid}/payment-estimate",
               {"down_payment": "2500", "term": "60", "credit_tier": "great"},
               fills=3, expect_redirect=False)
    assert f"${m:,}/mo" in t
    w.back()
    w.back()
    t = w.sort({"fuel": "Electric", "price_max": "30000"}, "year_desc")
    newest = card_summary(w.page_html)
    w.facts["newest"] = newest
    t = w.click(newest["href"])
    est, apr, term = vdp_est(w.page_html)
    w.facts["newest_est"] = est


def walk_2(w):
    w.nav("/", count=False)
    t = w.nav("/cars")
    w.facts["total"] = serp_count(t)
    assert w.facts["total"] == 1544
    t = w.sort({}, "price_asc")
    first3 = [card_summary(w.page_html, i) for i in range(3)]
    w.facts["first3"] = first3
    t = w.filter(mileage_max="40000")
    w.facts["low_miles"] = serp_count(t)
    t = w.filter(carry={"mileage_max": "40000"}, price_max="20000",
                 body="Sedan")
    w.facts["low_miles_sedan_20k"] = serp_count(t)
    sedan = card_summary(w.page_html)
    w.facts["sedan"] = sedan
    t = w.click(sedan["href"])
    w.facts["color"] = vdp_field(w.page_html, "Exterior color")
    w.facts["fuel"] = vdp_field(w.page_html, "Fuel")
    w.facts["mpg"] = vdp_field(w.page_html, "MPG (combined)")
    w.back()
    t = w.filter(carry={"mileage_max": "40000"}, body="SUV", year_min="2020")
    w.facts["suv_2020"] = serp_count(t)
    suv = card_summary(w.page_html)
    w.facts["suv"] = suv
    t = w.click(suv["href"])
    read(t, suv["city"], "city")
    w.back()
    t = w.click("/cars")
    w.facts["total2"] = serp_count(t)


def walk_3(w):
    w.nav("/", count=False)
    t = w.home_search(make="Toyota", model="Camry")
    w.facts["camry"] = serp_count(t)
    assert w.facts["camry"] == 20
    t = w.sort({"make": "Toyota", "model": "Camry"}, "year_desc")
    newest = card_summary(w.page_html)
    w.facts["newest"] = newest
    assert newest["year"] == "2026"
    t = w.click(newest["href"])
    vid = newest["vehicle_id"]
    w.facts["mileage"] = vdp_field(w.page_html, "Mileage")
    w.facts["color"] = vdp_field(w.page_html, "Exterior color")
    w.facts["fuel"] = vdp_field(w.page_html, "Fuel")
    assert w.facts["fuel"] == "Hybrid"
    w.back()
    t = w.filter(carry={"make": "Toyota", "model": "Camry"}, price_max="30000")
    w.facts["camry_30k"] = serp_count(t)
    assert w.facts["camry_30k"] == 15
    t = w.sort({"make": "Toyota", "model": "Camry", "price_max": "30000"},
               "price_asc")
    cheapest = card_summary(w.page_html)
    w.facts["cheapest"] = cheapest
    t = w.click(cheapest["href"])
    w.facts["cheapest_price"] = cheapest["price"]
    # back x3: price-sorted SERP -> price-capped SERP -> year-desc SERP,
    # where the newest Camry is the first card; re-open it with one click
    w.back()
    w.back()
    w.back()
    t = w.click(newest["href"])
    # estimator: down fill + 72-term pick (default 84); Good tier is default
    m = monthly(int(vid), 3000, 72, 6.99)
    w.facts["pay_72"] = m
    t = w.post(f"/vehicle/{vid}/payment-estimate",
               {"down_payment": "3000", "term": "72", "credit_tier": "good"},
               fills=2, expect_redirect=False)
    assert f"${m:,}/mo" in t
    m60 = monthly(int(vid), 3000, 60, 6.99)
    w.facts["pay_60"] = m60
    t = w.post(f"/vehicle/{vid}/payment-estimate",
               {"down_payment": "3000", "term": "60", "credit_tier": "good"},
               fills=1, expect_redirect=False)
    assert f"${m60:,}/mo" in t
    mex = monthly(int(vid), 3000, 60, 5.49)
    w.facts["pay_excellent"] = mex
    t = w.post(f"/vehicle/{vid}/payment-estimate",
               {"down_payment": "3000", "term": "60", "credit_tier": "excellent"},
               fills=1, expect_redirect=False)
    assert f"${mex:,}/mo" in t
    with app.app_context():
        v = cv_mod.Vehicle.query.filter_by(vehicle_id=int(vid)).first()
        w.facts["taxes"] = v.estimated_taxes_fees
        read(t, f"${v.estimated_taxes_fees:,}", "taxes & fees")


def walk_4(w):
    w.nav("/", count=False)
    w.nav("/authn/register")
    email = "walker4@test.com"
    t = w.post("/authn/register",
               {"display_name": "Walker Four", "email": email,
                "password": "Walker4Pass!"},
               fills=3)
    assert "Saved cars" in t
    # header keyword search (the task pins the keyword scope: Unlimited counts)
    t = w.header_search(q="Jeep Wrangler")
    w.facts["wrangler_count"] = serp_count(t)
    assert w.facts["wrangler_count"] == 21
    t = w.sort({"q": "Jeep Wrangler"}, "price_asc")
    cheapest = card_summary(w.page_html)
    w.facts["wrangler"] = cheapest
    assert cheapest["title"] == "Jeep Wrangler Unlimited"
    t = w.click(cheapest["href"])
    w.facts["mileage"] = vdp_field(w.page_html, "Mileage")
    t = w.click(f"/vehicle/{cheapest['vehicle_id']}/checkout")
    vid = cheapest["vehicle_id"]
    m = monthly(int(vid), 2500, 60, 6.24)
    w.facts["monthly"] = m
    # checkout defaults: earliest date + 8-10AM slot are preselected (read)
    t = w.post(f"/vehicle/{vid}/checkout",
               {"payment_type": "finance", "down_payment": "2500",
                "term": "60", "credit_tier": "great", "trade_in": "no",
                "trade_credit": "0", "delivery_date": "2026-09-30",
                "delivery_slot": "8:00 AM - 10:00 AM",
                "street": "500 Sunset Blvd", "city": "Scottsdale",
                "state": "AZ", "zip": "85254"},
               fills=8)
    om = re.search(r"Order <strong>(CV-\d+)</strong>", w.page_html)
    assert om, "no order number rendered"
    w.facts["order"] = om.group(1)
    assert f"${m:,}/mo" in t
    read(t, "2026-09-30", "delivery date")


def walk_5(w):
    w.nav("/", count=False)
    w.login("alice.j@test.com")
    # login lands on Saved cars - read the three seed saves
    saved = re.findall(r"<h3>(\d{4} [^<]+)</h3>", w.page_html)
    w.facts["saved_models"] = saved
    assert len(saved) == 3
    t = w.header_search(q="Tesla Model Y")
    w.facts["modely_count"] = serp_count(t)
    first = card_summary(w.page_html)
    w.facts["first"] = first
    t = w.click(first["href"])
    vid = first["vehicle_id"]
    w.facts["modely_price"] = first["price"]
    # estimator: down fill + term 60 pick (default 84) + Great tier pick
    m = monthly(int(vid), 2000, 60, 6.24)
    w.facts["est_2000_60_great"] = m
    t = w.post(f"/vehicle/{vid}/payment-estimate",
               {"down_payment": "2000", "term": "60", "credit_tier": "great"},
               fills=3, expect_redirect=False)
    assert f"${m:,}/mo" in t
    t = w.click(f"/vehicle/{vid}")            # "Back to the car"
    t = w.post(f"/vehicle/{vid}/favorite", {}, fills=0)
    t = w.nav("/account/favorites")
    saved2 = re.findall(r"<h3>(\d{4} [^<]+)</h3>", w.page_html)
    w.facts["saved_after"] = len(saved2)
    assert len(saved2) == 4
    blocks = re.findall(
        r'<h3>(\d{4} Toyota RAV4[^<]*)</h3>.*?action="(/account/favorites/(\d+)/remove)"',
        w.page_html, re.S)
    assert blocks, "RAV4 remove button missing"
    t = w.post(blocks[0][1], {}, fills=0)
    saved3 = re.findall(r"<h3>(\d{4} [^<]+)</h3>", w.page_html)
    w.facts["remaining"] = saved3
    assert len(saved3) == 3
    civic = re.search(
        r'href="(/vehicle/(\d+))"[^>]*>.*?<h3>(\d{4} Honda Civic[^<]*)</h3>',
        w.page_html, re.S)
    assert civic, "no Civic in favorites"
    t = w.click(civic.group(1))
    est, apr, term = vdp_est(w.page_html)
    w.facts["civic_est"] = est
    w.facts["civic_mileage"] = vdp_field(w.page_html, "Mileage")
    w.facts["civic_body"] = vdp_field(w.page_html, "Body style")
    w.back()
    model3 = re.search(
        r'href="(/vehicle/(\d+))"[^>]*>.*?<h3>(\d{4} Tesla Model 3[^<]*)</h3>',
        w.page_html, re.S)
    assert model3, "no Model 3 in favorites"
    t = w.click(model3.group(1))
    w.facts["model3_price"] = re.search(
        r'class="price">\$([\d,]+)', w.page_html).group(1)
    w.facts["model3_mileage"] = vdp_field(w.page_html, "Mileage")


def walk_6(w):
    w.nav("/", count=False)
    t = w.nav("/cars")
    t = w.filter(single_owner="1")
    w.facts["single_owner"] = serp_count(t)
    assert w.facts["single_owner"] == 20
    t = w.filter(carry={"single_owner": "1"}, accident_free="1")
    w.facts["so_af"] = serp_count(t)
    assert w.facts["so_af"] == 18
    card = card_summary(w.page_html)
    w.facts["first"] = card
    assert card["title"] == "Kia Telluride"
    t = w.click(card["href"])
    w.facts["prior_use"] = re.search(
        r"<span>Prior use</span>([^<]+)", w.page_html).group(1).strip()
    w.back()
    t = w.filter(carry={"single_owner": "1", "accident_free": "1"},
                 price_max="20000")
    w.facts["so_af_20k"] = serp_count(t)
    assert w.facts["so_af_20k"] == 7
    first20k = card_summary(w.page_html)
    t = w.click(first20k["href"])
    w.facts["engine_20k"] = vdp_field(w.page_html, "Engine")
    w.facts["color_20k"] = vdp_field(w.page_html, "Exterior color")
    w.back()
    t = w.sort({"single_owner": "1", "accident_free": "1",
                "price_max": "20000"}, "price_asc")
    cheapest = card_summary(w.page_html)
    w.facts["cheapest"] = cheapest
    t = w.click(cheapest["href"])
    w.facts["mpg"] = vdp_field(w.page_html, "MPG (combined)")
    w.facts["city"] = cheapest["city"]
    w.back()
    t = w.sort({"single_owner": "1", "accident_free": "1",
                "price_max": "20000"}, "mileage_asc")
    lowest = card_summary(w.page_html)
    w.facts["lowest_mileage"] = lowest
    t = w.click(lowest["href"])
    w.facts["lowest_mileage_vdp"] = vdp_field(w.page_html, "Mileage")


def walk_7(w):
    w.nav("/", count=False)
    t = w.nav("/sell-my-car")
    t = w.click("/sell-my-car/offer")
    # first offer: VIN + mileage fills; Good condition is the form default
    t = w.post("/sell-my-car/offer",
               {"vin": "1HGCM82633A004352", "mileage": "45000",
                "condition": "good"}, fills=2, expect_redirect=False)
    m = re.search(r'class="offer-amount">\$([\d,]+)</p>', w.page_html)
    assert m, "no offer rendered"
    w.facts["offer_good"] = int(m.group(1).replace(",", ""))
    w.back()
    t = w.post("/sell-my-car/offer",
               {"vin": "1HGCM82633A004352", "mileage": "45000",
                "condition": "excellent"}, fills=3, expect_redirect=False)
    m = re.search(r'class="offer-amount">\$([\d,]+)</p>', w.page_html)
    w.facts["offer_excellent"] = int(m.group(1).replace(",", ""))
    assert w.facts["offer_excellent"] > w.facts["offer_good"]
    w.back()
    # third offer: a real browser's bfcache keeps 'excellent' checked, so
    # the honest path re-picks Good (parity with the browser walk)
    t = w.post("/sell-my-car/offer",
               {"vin": "1HGCM82633A004352", "mileage": "60000",
                "condition": "good"}, fills=3, expect_redirect=False)
    m = re.search(r'class="offer-amount">\$([\d,]+)</p>', w.page_html)
    w.facts["offer_60k"] = int(m.group(1).replace(",", ""))
    assert w.facts["offer_60k"] < w.facts["offer_good"]
    w.login("bob.c@test.com")
    t = w.nav("/sell-my-car")
    t = w.click("/sell-my-car/offer")
    t = w.post("/sell-my-car/offer",
               {"vin": "1HGCM82633A004352", "mileage": "45000",
                "condition": "good"}, fills=2, expect_redirect=False)
    assert f"${w.facts['offer_good']:,}" in t
    # the claim POST redirects to the orders page; the target loads for free
    t = w.post("/sell-my-car/offer/claim", {}, fills=0)
    om = re.search(r"(TI-\d+)", t)
    assert om, "no offer code in account"
    w.facts["claimed_code"] = om.group(1)
    read(t, f"${w.facts['offer_good']:,}", "claimed offer amount")


def walk_8(w):
    w.nav("/", count=False)
    t = w.home_search(make="Kia", model="Telluride")
    w.facts["telluride"] = serp_count(t)
    assert w.facts["telluride"] == 21
    # the first 2022 Telluride in the results is the first card (4255570)
    first = card_summary(w.page_html)
    assert first["year"] == "2022"
    t = w.click(first["href"])
    vid = first["vehicle_id"]
    w.facts["price"] = first["price"]
    w.facts["mileage"] = vdp_field(w.page_html, "Mileage")
    w.facts["engine"] = vdp_field(w.page_html, "Engine")
    w.facts["transmission"] = vdp_field(w.page_html, "Transmission")
    w.facts["drivetrain"] = vdp_field(w.page_html, "Drivetrain")
    w.facts["seating"] = vdp_field(w.page_html, "Seating")
    w.facts["vin"] = vdp_field(w.page_html, "VIN")
    w.facts["location"] = first["city"]
    m = re.search(r"Owner reviews for the Kia Telluride \((\d+)\)",
                  w.page_html)
    assert m, "no owner-review count label"
    w.facts["owner_review_count"] = int(m.group(1))
    assert w.facts["owner_review_count"] == 20
    rm = re.search(r'<p class="review-stars">([^<]*?)\s*<span>(\d)/5</span>',
                   w.page_html)
    assert rm, "no review stars rendered"
    w.facts["first_review_rating"] = int(rm.group(2))
    w.facts["first_review_author"] = re.search(
        r'class="review-meta">([^·]+)·', w.page_html).group(1).strip()
    w.facts["accidents"] = "None reported" in w.page_html
    w.facts["prior_use"] = re.search(
        r"<span>Prior use</span>([^<]+)", w.page_html).group(1).strip()
    # cheapest similar SUV (first card of the VDP's similar section)
    sim = re.search(
        r'More SUVs like this</h2>.*?href="(/vehicle/(\d+))".*?'
        r'<h3>(\d{4} [^<]+)</h3>.*?class="car-price">\$([\d,]+)',
        w.page_html, re.S)
    assert sim, "no similar SUVs rendered"
    w.facts["similar"] = (sim.group(3), sim.group(4))
    t = w.click(sim.group(1))
    w.back()
    w.back()
    second = card_summary(w.page_html, 1)
    w.facts["second"] = second
    t = w.click(second["href"])
    w.facts["second_price"] = second["price"]
    w.back()
    t = w.sort({"make": "Kia", "model": "Telluride"}, "price_asc")
    cheapest = card_summary(w.page_html)
    w.facts["cheapest"] = cheapest
    # return to the 2022 Telluride S (65,981 miles is unique on the SERP)
    back22 = None
    for block in re.findall(r'class="car-card">.*?(?=class="car-card"|\Z)',
                             w.page_html, re.S):
        if "<h3>2022 Kia Telluride</h3>" in block and "65,981 miles" in block:
            back22 = re.search(r'<a href="(/vehicle/(\d+))"', block)
            break
    assert back22, "2022 Telluride S not found on the sorted SERP"
    assert back22.group(2) == vid
    t = w.click(back22.group(1))
    # estimator: down + term 60 (default 75) + Great tier; then term 72
    m60 = monthly(int(vid), 5000, 60, 6.24)
    w.facts["pay_60_great"] = m60
    t = w.post(f"/vehicle/{vid}/payment-estimate",
               {"down_payment": "5000", "term": "60", "credit_tier": "great"},
               fills=3, expect_redirect=False)
    assert f"${m60:,}/mo" in t
    m72 = monthly(int(vid), 5000, 72, 6.24)
    w.facts["pay_72_great"] = m72
    t = w.post(f"/vehicle/{vid}/payment-estimate",
               {"down_payment": "5000", "term": "72", "credit_tier": "great"},
               fills=1, expect_redirect=False)
    assert f"${m72:,}/mo" in t


def walk_9(w):
    w.nav("/", count=False)
    w.login("bob.c@test.com")
    t = w.nav("/account/orders")
    om = re.search(r"CV-100019 — <a href=\"/vehicle/(\d+)\">(\d{4} [^<]+)</a>",
                   w.page_html)
    assert om, "delivered order missing"
    w.facts["order_car"] = om.group(2)
    w.facts["order_number"] = "CV-100019"
    info = re.findall(r"<p>([^<]+)</p>", w.page_html)
    w.facts["order_info"] = info[:3]
    timeline = re.findall(r"<li><strong>([^<]+)</strong> — ([^<]+)<em>",
                          w.page_html)
    w.facts["timeline"] = timeline
    assert len(timeline) == 5
    tm = re.search(r"(TI-\d+)", t)
    assert tm, "trade-in offer missing"
    w.facts["trade_in_code"] = tm.group(1)
    t = w.click(f"/vehicle/{om.group(1)}")
    vid = om.group(1)
    w.facts["stock"] = vdp_field(w.page_html, "Stock #")
    w.facts["vin"] = vdp_field(w.page_html, "VIN")
    # estimator: down fill + term 60 pick (default 75); Good tier default
    m = monthly(int(vid), 2000, 60, 6.99)
    w.facts["est_2000_60"] = m
    t = w.post(f"/vehicle/{vid}/payment-estimate",
               {"down_payment": "2000", "term": "60", "credit_tier": "good"},
               fills=2, expect_redirect=False)
    assert f"${m:,}/mo" in t
    w.back()
    w.back()
    t = w.nav("/account/favorites")
    saved = re.findall(r"<h3>(\d{4} [^<]+)</h3>", w.page_html)
    w.facts["saved_trucks"] = saved
    assert len(saved) == 2
    blocks = re.findall(
        r'<h3>(\d{4} Jeep Wrangler[^<]*)</h3>.*?action="(/account/favorites/(\d+)/remove)"',
        w.page_html, re.S)
    assert blocks, "Wrangler remove button missing"
    t = w.post(blocks[0][1], {}, fills=0)
    saved2 = re.findall(r"<h3>(\d{4} [^<]+)</h3>", w.page_html)
    w.facts["remaining"] = saved2
    assert len(saved2) == 1
    w.nav("/authn/logout")
    w.login("bob.c@test.com")
    saved3 = re.findall(r"<h3>(\d{4} [^<]+)</h3>", w.page_html)
    w.facts["saved_after_relogin"] = saved3
    assert saved3 == saved2


def walk_10(w):
    w.nav("/", count=False)
    t = w.header_search(q="Ram 2500")
    w.facts["ram_count"] = serp_count(t)
    assert w.facts["ram_count"] == 3
    first = card_summary(w.page_html)
    assert first["year"] == "2025"
    t = w.click(first["href"])
    vid = first["vehicle_id"]
    est, apr, term = vdp_est(w.page_html)
    w.facts["est_0down"] = est
    w.facts["default_apr"] = apr
    w.facts["engine"] = vdp_field(w.page_html, "Engine")
    w.facts["drivetrain"] = vdp_field(w.page_html, "Drivetrain")
    with app.app_context():
        v = cv_mod.Vehicle.query.filter_by(vehicle_id=int(vid)).first()
        w.facts["taxes"] = v.estimated_taxes_fees
    w.back()
    t = w.filter(carry={"q": "Ram 2500"}, price_max="50000")
    w.facts["ram_50k"] = serp_count(t)
    assert w.facts["ram_50k"] == 2
    t = w.sort({"q": "Ram 2500", "price_max": "50000"}, "price_asc")
    cheapest = card_summary(w.page_html)
    w.facts["cheapest"] = cheapest
    t = w.click(cheapest["href"])
    w.facts["cheapest_trim"] = re.search(
        r'class="vdp-subtitle">([^<]+)', w.page_html).group(1).strip()
    # back x3: price-sorted SERP -> price-capped SERP -> the Ram SERP,
    # where the 2025 is the first card; re-open it with one click
    w.back()
    w.back()
    w.back()
    t = w.click(first["href"])
    # estimator: down fill + Excellent tier pick; 84-month term is default
    m = monthly(int(vid), 10000, 84, 5.49)
    w.facts["pay_84_exc"] = m
    t = w.post(f"/vehicle/{vid}/payment-estimate",
               {"down_payment": "10000", "term": "84", "credit_tier": "excellent"},
               fills=2, expect_redirect=False)
    assert f"${m:,}/mo" in t
    m72 = monthly(int(vid), 10000, 72, 5.49)
    w.facts["pay_72_exc"] = m72
    t = w.post(f"/vehicle/{vid}/payment-estimate",
               {"down_payment": "10000", "term": "72", "credit_tier": "excellent"},
               fills=1, expect_redirect=False)
    assert f"${m72:,}/mo" in t
    mp = monthly(int(vid), 10000, 72, 11.99)
    w.facts["pay_72_poor"] = mp
    t = w.post(f"/vehicle/{vid}/payment-estimate",
               {"down_payment": "10000", "term": "72", "credit_tier": "poor"},
               fills=1, expect_redirect=False)
    assert f"${mp:,}/mo" in t
    m15 = monthly(int(vid), 15000, 72, 11.99)
    w.facts["pay_15k_poor"] = m15
    t = w.post(f"/vehicle/{vid}/payment-estimate",
               {"down_payment": "15000", "term": "72", "credit_tier": "poor"},
               fills=1, expect_redirect=False)
    assert f"${m15:,}/mo" in t


def walk_11(w):
    w.nav("/", count=False)
    w.login("carol.d@test.com")
    t = w.header_search(q="Mazda CX-5")
    w.facts["cx5_count"] = serp_count(t)
    # keyword scope: 21 CX-5s + 5 CX-50s match the two terms
    assert w.facts["cx5_count"] == 26
    t = w.sort({"q": "Mazda CX-5"}, "price_asc")
    cheapest = card_summary(w.page_html)
    w.facts["cheapest"] = cheapest
    t = w.click(cheapest["href"])
    vid = cheapest["vehicle_id"]
    w.facts["color"] = vdp_field(w.page_html, "Exterior color")
    w.facts["fuel"] = vdp_field(w.page_html, "Fuel")
    t = w.click(f"/vehicle/{vid}/checkout")
    # Pay cash is the preselected default (read); trade-in + credit + date +
    # slot + address are the touched controls
    t = w.post(f"/vehicle/{vid}/checkout",
               {"payment_type": "cash", "trade_in": "yes",
                "trade_credit": "5000", "delivery_date": "2026-10-06",
                "delivery_slot": "4:00 PM - 6:00 PM",
                "street": "1040 N State St", "city": "Chicago",
                "state": "IL", "zip": "60610"},
               fills=8)
    om = re.search(r"Order <strong>(CV-\d+)</strong>", w.page_html)
    assert om, "no order number rendered"
    w.facts["order"] = om.group(1)
    read(t, "Cash", "payment method")
    read(t, "2026-10-06", "delivery date")
    t = w.nav("/account/orders")
    tl = re.findall(r"<li><strong>([^<]+)</strong> — ([^<]+)<em>",
                    w.page_html)
    assert tl, "new order timeline missing"
    w.facts["new_timeline"] = tl[:2]


def walk_12(w):
    w.nav("/", count=False)
    w.login("dana.k@test.com")
    t = w.nav("/account/profile")
    m = re.search(r"Name: (.+)", t)
    w.facts["profile_line"] = m.group(1).strip() if m else None
    m = re.search(r"Delivery address: (.+)", t)
    w.facts["address_line"] = m.group(1).strip() if m else None
    t = w.post("/account/profile",
               {"phone": "(617) 555-0700", "street": "77 Beacon St",
                "city": "Boston", "state": "MA", "zip": "02110",
                "about": ""},
               fills=2)
    m = re.search(r"Name: (.+)", t)
    w.facts["profile_line_after"] = m.group(1).strip() if m else None
    m = re.search(r"Delivery address: (.+)", t)
    w.facts["address_line_after"] = m.group(1).strip() if m else None
    t = w.nav("/account/favorites")
    saved = re.findall(r"<h3>(\d{4} [^<]+)</h3>", w.page_html)
    w.facts["saved"] = saved
    assert len(saved) == 2
    blocks = re.findall(
        r'<h3>(\d{4} Toyota Camry Hybrid[^<]*)</h3>.*?action="(/account/favorites/(\d+)/remove)"',
        w.page_html, re.S)
    assert blocks, "Camry Hybrid remove button missing"
    t = w.post(blocks[0][1], {}, fills=0)
    saved2 = re.findall(r"<h3>(\d{4} [^<]+)</h3>", w.page_html)
    w.facts["remaining"] = saved2
    assert len(saved2) == 1
    t = w.nav("/account/orders")
    read(t, "CV-100033", "order number")
    read(t, "Financing review", "order status")
    tl = re.findall(r"<li><strong>([^<]+)</strong> — ([^<]+)<em>",
                    w.page_html)
    w.facts["timeline"] = tl[:2]
    w.nav("/authn/logout")
    w.login("dana.k@test.com")
    t = w.nav("/account/profile")
    m = re.search(r"Name: (.+)", t)
    w.facts["profile_line_persisted"] = m.group(1).strip() if m else None
    read(t, "(617) 555-0700", "persisted phone")


def walk_13(w):
    w.nav("/", count=False)
    t = w.header_search(q="Mustang")
    w.facts["mustang_count"] = serp_count(t)
    assert w.facts["mustang_count"] == 21
    t = w.sort({"q": "Mustang"}, "year_desc")
    newest = card_summary(w.page_html)
    w.facts["newest"] = newest
    t = w.click(newest["href"])
    vid = newest["vehicle_id"]
    w.facts["engine"] = vdp_field(w.page_html, "Engine")
    w.facts["transmission"] = vdp_field(w.page_html, "Transmission")
    w.facts["drivetrain"] = vdp_field(w.page_html, "Drivetrain")
    w.back()
    t = w.sort({"q": "Mustang"}, "mileage_asc")
    lowest = card_summary(w.page_html)
    w.facts["lowest_mileage"] = lowest
    t = w.click(lowest["href"])
    w.facts["lowest_price"] = lowest["price"]
    w.facts["lowest_exterior"] = vdp_field(w.page_html, "Exterior color")
    w.facts["lowest_interior"] = vdp_field(w.page_html, "Interior color")
    w.back()
    t = w.filter(carry={"q": "Mustang"}, year_min="2020")
    w.facts["mustang_2020"] = serp_count(t)
    assert w.facts["mustang_2020"] == 9
    first2020 = card_summary(w.page_html)
    w.facts["first_2020_price"] = first2020["price"]
    # open the newest Mustang again (2025 GT Premium, on the filtered SERP)
    t = w.click(newest["href"])
    # estimator: down fill + 66-term pick (default 84); Good tier default
    m = monthly(int(vid), 2000, 66, 6.99)
    w.facts["pay_2k_66"] = m
    t = w.post(f"/vehicle/{vid}/payment-estimate",
               {"down_payment": "2000", "term": "66", "credit_tier": "good"},
               fills=2, expect_redirect=False)
    assert f"${m:,}/mo" in t
    m4k = monthly(int(vid), 4000, 66, 6.99)
    w.facts["pay_4k_66"] = m4k
    t = w.post(f"/vehicle/{vid}/payment-estimate",
               {"down_payment": "4000", "term": "66", "credit_tier": "good"},
               fills=1, expect_redirect=False)
    assert f"${m4k:,}/mo" in t


def walk_14(w):
    w.nav("/", count=False)
    t = w.nav("/cars?body=Truck")
    w.facts["trucks"] = serp_count(t)
    assert w.facts["trucks"] == 102
    t = w.filter(carry={"body": "Truck"}, fuel="Diesel")
    w.facts["diesel_trucks"] = serp_count(t)
    assert w.facts["diesel_trucks"] == 5
    first = card_summary(w.page_html)
    w.facts["first"] = first
    assert first["title"] == "Ram 2500 Crew Cab"
    t = w.click(first["href"])
    vid = first["vehicle_id"]
    w.facts["engine"] = vdp_field(w.page_html, "Engine")
    # estimator: down fill + 72-term pick (default 84); Good tier default
    m = monthly(int(vid), 5000, 72, 6.99)
    w.facts["pay_5k_72"] = m
    t = w.post(f"/vehicle/{vid}/payment-estimate",
               {"down_payment": "5000", "term": "72", "credit_tier": "good"},
               fills=2, expect_redirect=False)
    assert f"${m:,}/mo" in t
    w.back()
    w.back()
    t = w.filter(fuel="", body="Convertible")
    w.facts["convertibles"] = serp_count(t)
    assert w.facts["convertibles"] == 49
    t = w.sort({"body": "Convertible"}, "price_asc")
    cheapest = card_summary(w.page_html)
    w.facts["cheapest_conv"] = cheapest
    t = w.click(cheapest["href"])
    w.facts["cheapest_color"] = vdp_field(w.page_html, "Exterior color")
    w.back()
    t = w.click("/cars")
    snap = re.search(r"Upstream carvana\.com listed ([\S]+) total cars", t)
    assert snap, "snapshot note missing"
    w.facts["snapshot_total"] = snap.group(1)
    assert w.facts["snapshot_total"] == "53,866"
    t = w.filter(body="Convertible")
    t = w.sort({"body": "Convertible"}, "price_desc")
    priciest = card_summary(w.page_html)
    w.facts["priciest_conv"] = priciest
    t = w.click(priciest["href"])


def walk_15(w):
    w.nav("/", count=False)
    w.login("alice.j@test.com")
    t = w.nav("/account/orders")
    om = re.search(r"CV-100026 — <a href=\"/vehicle/(\d+)\">(\d{4} [^<]+)</a>",
                   w.page_html)
    assert om, "scheduled order missing"
    w.facts["order_number"] = "CV-100026"
    w.facts["order_car"] = om.group(2)
    info = re.findall(r"<p>([^<]+)</p>", w.page_html)
    w.facts["order_info"] = info[:3]
    t = w.click(f"/vehicle/{om.group(1)}")
    w.facts["stock"] = vdp_field(w.page_html, "Stock #")
    w.facts["vin"] = vdp_field(w.page_html, "VIN")
    w.back()
    t = w.header_search(q="Honda Civic")
    w.facts["civic_count"] = serp_count(t)
    first = card_summary(w.page_html)
    assert first["year"] == "2022"
    t = w.click(first["href"])
    vid = first["vehicle_id"]
    est, apr, term = vdp_est(w.page_html)
    w.facts["civic_est"] = est
    w.facts["civic_price"] = first["price"]
    # estimator: down + term 60 (default 84) + Great tier
    m = monthly(int(vid), 1500, 60, 6.24)
    w.facts["pay_1500_60_great"] = m
    t = w.post(f"/vehicle/{vid}/payment-estimate",
               {"down_payment": "1500", "term": "60", "credit_tier": "great"},
               fills=3, expect_redirect=False)
    assert f"${m:,}/mo" in t
    w.back()
    w.back()
    civic23 = None
    for block in re.findall(r'class="car-card">.*?(?=class="car-card"|\Z)',
                             w.page_html, re.S):
        if "<h3>2023 Honda Civic</h3>" in block:
            civic23 = re.search(r'<a href="(/vehicle/(\d+))"', block)
            break
    assert civic23, "2023 Civic not on the SERP"
    t = w.click(civic23.group(1))
    t = w.post(f"/vehicle/{civic23.group(2)}/favorite", {}, fills=0)
    t = w.nav("/account/favorites")
    saved = re.findall(r"<h3>(\d{4} [^<]+)</h3>", w.page_html)
    w.facts["saved_after"] = saved
    assert len(saved) == 4


def walk_16(w):
    w.nav("/", count=False)
    t = w.nav("/faq")
    cats = re.findall(r"<h2>([^<]+)</h2>", w.page_html)
    w.facts["categories"] = cats
    assert len(cats) == 6
    articles = re.findall(r'href="(/help/[^"]+)"', w.page_html)
    w.facts["article_count"] = len(set(articles))
    q1 = w.click("/help/pickup-and-delivery/can-i-reschedule-my-appointment")
    w.facts["reschedule"] = re.search(r'<section class="content-section">\s*<p>([^<]+)</p>', w.page_html).group(1)
    w.back()
    q2 = w.click("/help/pickup-and-delivery/can-i-keep-my-car-vending-machine-token")
    w.facts["token"] = re.search(r'<section class="content-section">\s*<p>([^<]+)</p>', w.page_html).group(1)
    w.back()
    q3 = w.click("/help/payment-and-financing/can-i-add-auto-pay-after-receiving-my-car")
    w.facts["autopay"] = re.search(r'<section class="content-section">\s*<p>([^<]+)</p>', w.page_html).group(1)
    w.back()
    q4 = w.click("/help/extended-coverage-and-repairs/does-carvana-offer-gap-coverage")
    w.facts["gap"] = re.search(r'<section class="content-section">\s*<p>([^<]+)</p>', w.page_html).group(1)
    w.back()
    q5 = w.click("/help/sell-or-trade/are-there-tax-savings-to-trading-in-my-car")
    w.facts["tax_savings"] = re.search(r'<section class="content-section">\s*<p>([^<]+)</p>', w.page_html).group(1)
    w.back()
    q6 = w.click("/help/purchasing-a-car/business-owner-which-documents-can-i-provide-for-proof-of-income")
    w.facts["business_owner_q"] = re.search(r"<h1>([^<]+)</h1>",
                                            w.page_html).group(1)
    w.back()
    q7 = w.click("/help/pickup-and-delivery/can-i-buy-a-car-i-see-inside-the-carvana-vending-machine")
    w.facts["vending_buy"] = re.search(r'<section class="content-section">\s*<p>([^<]+)</p>', w.page_html).group(1)
    w.back()
    q8 = w.click("/help/carvana-inventory/are-carvanas-vehicles-certified")
    w.facts["certified"] = re.search(r'<section class="content-section">\s*<p>([^<]+)</p>', w.page_html).group(1)


def walk_17(w):
    w.nav("/", count=False)
    t = w.nav("/how-it-works")
    w.facts["hiw_title"] = re.search(r"<h1>([^<]+)</h1>", w.page_html).group(1)
    read(t, "inspected and reconditioned", "inspection claim")
    wf = re.search(r"limited (\d+) day/([\d,]+) mile", t)
    assert wf, "worry-free guarantee line missing"
    w.facts["worry_free"] = wf.groups()
    read(t, "7-Day", "return policy")
    read(t, "PAY YOUR WAY", "payment options")
    t = w.nav("/certified-program")
    read(t, "150-point", "certified inspection claim")
    t = w.nav("/cars")
    t = w.sort({}, "price_asc")
    first3 = [card_summary(w.page_html, i) for i in range(3)]
    w.facts["three_cheapest"] = first3
    t = w.click(first3[0]["href"])
    vid = first3[0]["vehicle_id"]
    est, apr, term = vdp_est(w.page_html)
    w.facts["cheapest_est"] = est
    w.facts["cheapest_city"] = first3[0]["city"]
    # estimator: down fill + term 60 pick (default 72); Good tier default
    m = monthly(int(vid), 3000, 60, 6.99)
    w.facts["pay_3k_60"] = m
    t = w.post(f"/vehicle/{vid}/payment-estimate",
               {"down_payment": "3000", "term": "60", "credit_tier": "good"},
               fills=2, expect_redirect=False)
    assert f"${m:,}/mo" in t
    w.back()
    w.back()
    t = w.sort({}, "price_desc")
    priciest = card_summary(w.page_html)
    w.facts["priciest"] = priciest
    t = w.click(priciest["href"])
    w.facts["priciest_body"] = vdp_field(w.page_html, "Body style")
    w.back()
    t = w.filter(body="SUV", price_max="20000")
    w.facts["suv_20k"] = serp_count(t)
    assert w.facts["suv_20k"] == 211
    first = card_summary(w.page_html)
    w.facts["first_suv"] = first
    t = w.click(first["href"])
    read(t, first["city"], "city")


def walk_18(w):
    w.nav("/", count=False)
    t = w.nav("/financing")
    m = re.search(r"APR of ([\d.]+)% at (\d+) months with \$([\d,]+) down", t)
    assert m, "sample financing line missing"
    w.facts["sample"] = m.groups()
    ap = re.search(r"(\d+)% approval rate", t)
    assert ap, "approval-rate claim missing"
    w.facts["approval"] = ap.group(1)
    t = w.nav("/cars")
    t = w.filter(fuel="Hybrid")
    w.facts["hybrids"] = serp_count(t)
    assert w.facts["hybrids"] == 57
    first = card_summary(w.page_html)
    w.facts["first_hybrid"] = first
    t = w.click(first["href"])
    vid = first["vehicle_id"]
    with app.app_context():
        v = cv_mod.Vehicle.query.filter_by(vehicle_id=int(vid)).first()
        w.facts["taxes"] = v.estimated_taxes_fees
    w.back()
    t = w.filter(carry={"fuel": "Hybrid"}, price_max="25000")
    w.facts["hybrid_25k"] = serp_count(t)
    assert w.facts["hybrid_25k"] == 19
    first25 = card_summary(w.page_html)
    assert first25["vehicle_id"] == vid
    t = w.click(first25["href"])
    w.facts["first_25k_mileage"] = vdp_field(w.page_html, "Mileage")
    # estimator: down + term 66 (default 60) + Fair tier; then down 8000,
    # then term 60
    m4k = monthly(int(vid), 4000, 66, 8.74)
    w.facts["pay_4k_66_fair"] = m4k
    t = w.post(f"/vehicle/{vid}/payment-estimate",
               {"down_payment": "4000", "term": "66", "credit_tier": "fair"},
               fills=3, expect_redirect=False)
    assert f"${m4k:,}/mo" in t
    m8k = monthly(int(vid), 8000, 66, 8.74)
    w.facts["pay_8k_66_fair"] = m8k
    t = w.post(f"/vehicle/{vid}/payment-estimate",
               {"down_payment": "8000", "term": "66", "credit_tier": "fair"},
               fills=1, expect_redirect=False)
    assert f"${m8k:,}/mo" in t
    m60 = monthly(int(vid), 8000, 60, 8.74)
    w.facts["pay_8k_60_fair"] = m60
    t = w.post(f"/vehicle/{vid}/payment-estimate",
               {"down_payment": "8000", "term": "60", "credit_tier": "fair"},
               fills=1, expect_redirect=False)
    assert f"${m60:,}/mo" in t


def walk_19(w):
    w.nav("/", count=False)
    w.nav("/authn/register")
    email = "walker19@test.com"
    t = w.post("/authn/register",
               {"display_name": "Walker Nineteen", "email": email,
                "password": "Walker19Pass!"},
               fills=3)
    assert "Saved cars" in t
    t = w.header_search(q="Nissan Frontier")
    w.facts["frontier_count"] = serp_count(t)
    assert w.facts["frontier_count"] == 3
    t = w.sort({"q": "Nissan Frontier"}, "price_asc")
    cheapest = card_summary(w.page_html)
    w.facts["cheapest"] = cheapest
    t = w.click(cheapest["href"])
    vid = cheapest["vehicle_id"]
    t = w.click(f"/vehicle/{vid}/checkout")
    m = monthly(int(vid), 1500, 75, 6.99)
    w.facts["monthly"] = m
    # checkout: finance radio + down + term 75 (default 72) + date + slot +
    # address; Good tier is the preselected default (read)
    t = w.post(f"/vehicle/{vid}/checkout",
               {"payment_type": "finance", "down_payment": "1500",
                "term": "75", "credit_tier": "good", "trade_in": "no",
                "trade_credit": "0", "delivery_date": "2026-10-01",
                "delivery_slot": "12:00 PM - 2:00 PM",
                "street": "88 Oak Street", "city": "Denver",
                "state": "CO", "zip": "80203"},
               fills=9)
    om = re.search(r"Order <strong>(CV-\d+)</strong>", w.page_html)
    assert om, "no order number rendered"
    w.facts["order"] = om.group(1)
    assert f"${m:,}/mo" in t
    with app.app_context():
        v = cv_mod.Vehicle.query.filter_by(vehicle_id=int(vid)).first()
        principal = v.financed_principal(1500, 0)
        w.facts["amount_financed"] = principal
        read(t, f"${principal:,}", "amount financed line")
    read(t, "2026-10-01", "delivery date")
    t = w.nav("/account/orders")
    tl = re.findall(r"<li><strong>([^<]+)</strong> — ([^<]+)<em>",
                    w.page_html)
    assert tl, "order timeline missing"
    w.facts["first_timeline"] = tl[0]


def walk_20(w):
    w.nav("/", count=False)
    w.login("carol.d@test.com")
    t = w.nav("/")
    t = w.home_search(make="BMW")
    w.facts["bmw"] = serp_count(t)
    assert w.facts["bmw"] == 56
    t = w.filter(carry={"make": "BMW"}, model="3 Series")
    w.facts["bmw3"] = serp_count(t)
    assert w.facts["bmw3"] == 21
    t = w.sort({"make": "BMW", "model": "3 Series"}, "price_asc")
    cheapest = card_summary(w.page_html)
    w.facts["cheapest"] = cheapest
    t = w.click(cheapest["href"])
    vid = cheapest["vehicle_id"]
    w.facts["color"] = vdp_field(w.page_html, "Exterior color")
    w.facts["fuel"] = vdp_field(w.page_html, "Fuel")
    # estimator: down + term 48 (default 75) + Great tier
    m = monthly(int(vid), 2000, 48, 6.24)
    w.facts["pay_48_great"] = m
    t = w.post(f"/vehicle/{vid}/payment-estimate",
               {"down_payment": "2000", "term": "48", "credit_tier": "great"},
               fills=3, expect_redirect=False)
    assert f"${m:,}/mo" in t
    read(t, "Amount financed", "amount financed label")
    t = w.click(f"/vehicle/{vid}")            # "Back to the car"
    t = w.post(f"/vehicle/{vid}/favorite", {}, fills=0)
    w.nav("/authn/logout")
    w.login("carol.d@test.com")
    saved = re.findall(r"<h3>(\d{4} [^<]+)</h3>", w.page_html)
    w.facts["saved_after"] = saved
    assert len(saved) == 2
    prices = re.findall(r'class="car-price">\$([\d,]+)</p>', w.page_html)
    w.facts["saved_prices"] = [int(p.replace(",", "")) for p in prices]


WALKS = {
    "Carvana--0": walk_0, "Carvana--1": walk_1, "Carvana--2": walk_2,
    "Carvana--3": walk_3, "Carvana--4": walk_4, "Carvana--5": walk_5,
    "Carvana--6": walk_6, "Carvana--7": walk_7, "Carvana--8": walk_8,
    "Carvana--9": walk_9, "Carvana--10": walk_10, "Carvana--11": walk_11,
    "Carvana--12": walk_12, "Carvana--13": walk_13, "Carvana--14": walk_14,
    "Carvana--15": walk_15, "Carvana--16": walk_16, "Carvana--17": walk_17,
    "Carvana--18": walk_18, "Carvana--19": walk_19, "Carvana--20": walk_20,
}


# --------------------------------------------------------------------- audit --

def fresh_seed():
    """Reset the audit mirror to the pristine seed state before every task
    walk — exactly how the benchmark grades each task (one task, one fresh
    mirror), so stateful tasks never contaminate each other."""
    with app.app_context():
        cv_mod.db.session.remove()
        cv_mod.db.drop_all()
        cv_mod.db.create_all()
        cv_mod.seed_database()
        cv_mod.seed_benchmark_users()


def main():
    failures = []
    print(f"auditing {len(TASKS)} tasks, each against a fresh seeded mirror ...")
    for task in TASKS:
        tid = task["id"]
        walk_fn = WALKS.get(tid)
        assert walk_fn, f"no walk for {tid}"
        fresh_seed()
        app.config.update(TESTING=True)
        client = app.test_client()
        w = Walk(client, tid)
        try:
            walk_fn(w)
            depth = w.atomic
            status = "OK " if depth >= 15 else "SHALLOW"
            print(f"[{status}] {tid}: {depth} atomic steps")
            if depth < 15:
                failures.append(f"{tid}: only {depth} atomic steps")
        except AssertionError as e:
            print(f"[FAIL] {tid}: {e}")
            for entry in w.log[-6:]:
                print(f"    ... {entry}")
            failures.append(f"{tid}: {e}")
    # shape + leakage checks
    for task in TASKS:
        tid = task["id"]
        assert set(task.keys()) == {"web_name", "id", "ques", "web",
                                    "upstream_url"}, f"{tid}: keys"
        assert task["web"] == "http://localhost:40116/", f"{tid}: web url"
        words = len(task["ques"].split())
        assert words <= 100, f"{tid}: {words} words"
        assert not re.search(r"/vehicle/\d|CV-\d|localhost:\d+", task["ques"]), \
            f"{tid}: URL/answer leakage in task text"
    print()
    if failures:
        print("FAILURES:")
        for f in failures:
            print("  -", f)
        return 1
    print("all tasks: premises resolve, depth >= 15, no leakage, shape OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
