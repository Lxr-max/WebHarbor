#!/usr/bin/env python3
"""Machine audit of sites/cars_com/tasks.jsonl — measured honest-atomic
caliber, after the ziprecruiter/u_s_customs precedent, updated to the
reviewers' depth standard (hidden form fields never count as gestures).

For every task row this script drives the task's honest path against the
seeded mirror through the Flask test client — the same natural route a
competent agent takes — and counts steps in the HONEST-ATOMIC caliber:

  atomic = every navigation, link click, form fill, VISIBLE radio/checkbox
           pick, dropdown select and form submit after the initial page
           load, plus one final step for composing the answer. Reads are
           NOT counted. Hidden form inputs (the filter form's carried
           query fields, the sort form's carried filters) are NEVER
           counted. No gestures beyond the task text (no padding).

For every task it asserts:
  1. premises — every fact the task asks for actually resolves on the
     mirror with the frozen ground-truth value (driven through the test
     client, exactly like an agent would);
  2. measured depth — atomic >= 15, measured from the driven walk, not
     declared as a constant;
  3. zero answer leakage — answer anchors never appear in the task text;
  4. shape — the 7-key contract (5 contributor keys + the reviewer's
     verifier_path + judge_rubric; never an answer key), goal-style wording
     at or under 100 words.

Run:  PYTHONPATH=. venv/bin/python scripts_dev/validate_tasks.py
"""
import html as html_mod
import json
import os
import pathlib
import re
import sys
import tempfile
from urllib.parse import parse_qsl

ROOT = pathlib.Path(__file__).resolve().parents[1]

# The audit drives stateful flows (register, save, garage, offers), so it
# runs against its own throwaway seed database — never the live instance.
_AUDIT_DB = pathlib.Path(tempfile.mkdtemp(prefix="cars-com-task-audit-")) / "cars_com.db"
os.environ["CARS_COM_DB_URI"] = f"sqlite:///{_AUDIT_DB}"

sys.path.insert(0, str(ROOT))
import app as cars_mod  # noqa: E402
from app import app  # noqa: E402

TASKS = [json.loads(line) for line in
         (ROOT / "tasks.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]

TAG_RE = re.compile(r"<[^>]+>")


def text_of(page):
    return " ".join(html_mod.unescape(TAG_RE.sub(" ", page)).split())


def csrf_from(page_html, form_action=None):
    m = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', page_html)
    assert m, "no csrf token rendered"
    return m.group(1)


# ------------------------------------------------------------------- walker --

class Walk:
    """Test-client walk of one task's honest path, in the honest-atomic
    caliber: every visible gesture after the initial page load counts
    exactly one (matching a real browser: one user gesture, one step).
    Reads are free. Hidden form inputs never count. The page a POST
    redirects to loads for free. A dropdown whose change auto-submits its
    form (the SERP sort) is one gesture, like a real browser."""

    def __init__(self, client, task_id):
        self.client = client
        self.task_id = task_id
        self.atomic = 0
        self.facts = {}
        self.log = []
        self.page_html = ""
        self.page_text = ""
        self.history = []

    def _get(self, path):
        r = self.client.get(path)
        assert r.status_code == 200, f"GET {path} -> {r.status_code}"
        self.page_html = r.get_data(as_text=True)
        self.page_text = text_of(self.page_html)
        self.history.append(path)
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
        """Browser back: one gesture; the previous page loads for free."""
        if len(self.history) < 2:
            raise AssertionError("nowhere to go back to")
        self.history.pop()
        path = self.history[-1]
        r = self.client.get(path)
        assert r.status_code == 200, f"GET {path} -> {r.status_code}"
        self.page_html = r.get_data(as_text=True)
        self.page_text = text_of(self.page_html)
        self.atomic += 1
        self.log.append(("back", "browser-back"))
        return self.page_text

    def fill(self, name, value):
        self.atomic += 1
        self.log.append(("fill", name))
        return (name, value)

    def search(self, stock=None, make=None, model=None, distance=None):
        """The home search widget: one fill per field the agent actually
        touches plus the submit. Untouched fields never count."""
        data = {}
        if stock is not None:
            self.fill("stock_type", stock)
            data["stock_type"] = stock
        if make is not None:
            self.fill("makes[]", make)
            data["makes[]"] = make
        if model is not None:
            self.fill("models[]", model)
            data["models[]"] = model
        if distance is not None:
            self.fill("maximum_distance", distance)
            data["maximum_distance"] = distance
        self.atomic += 1
        self.log.append(("submit", "search"))
        qs = "&".join(f"{k}={v}" for k, v in data.items())
        return self._get("/shopping/results/?" + qs)

    def filter(self, carry=None, **params):
        """Pick VISIBLE filter controls and press Update results: one
        atomic action per touched control (select, fill, checkbox) plus
        one for the submit. Hidden/carried fields never count.

        A real browser submits EVERY form control on Update - including
        the untouched selects' empty "All ..." values - so the audit must
        too (the review found a real submission zeroing the SERP when the
        backend missed the empty-value guards on four slug params)."""
        carry = dict(carry or {})
        for k in params:
            self.atomic += 1
            self.log.append(("choose", f"{k}={params[k]}"))
        self.atomic += 1
        self.log.append(("submit", "Update results"))
        # the full control set of the real filter form, browser-faithful
        query = {"stock_type": "all", "list_price_min": "", "list_price_max": "",
                 "mileage_max": "", "deal_ratings": "", "seller_type": "",
                 "year_min": "", "year_max": "", "makes[]": "", "models[]": "",
                 "keyword": "", "body_style_slugs": "", "exterior_color_slugs": "",
                 "fuel_slugs": "", "transmission_slugs": "", "drivetrain_slugs": "",
                 "cylinder_counts": "", "maximum_distance": "", "zip": "98101"}
        query.update(carry)
        query.update(params)
        return self._get("/shopping/results/?" + "&".join(
            f"{k}={v}" for k, v in query.items()))

    def sort(self, value, carry=None):
        """The SERP sort dropdown auto-submits on change: one gesture."""
        self.atomic += 1
        self.log.append(("sort", value))
        query = dict(carry or {})
        query["sort"] = value
        return self._get("/shopping/results/?" + "&".join(
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
            if loc and loc.startswith("/"):
                rr = self.client.get(loc)
                assert rr.status_code == 200
                self.page_html = rr.get_data(as_text=True)
                self.page_text = text_of(self.page_html)
                self.history.append(loc)
        else:
            assert r.status_code == 200, f"POST {path} -> {r.status_code}"
            self.page_html = r.get_data(as_text=True)
            self.page_text = text_of(self.page_html)
        self.atomic += 1
        self.log.append(("submit", path))
        return self.page_text

    def compose(self):
        self.atomic += 1
        self.log.append(("compose", "the final answer"))

    def login(self, email, password):
        """Submit the login form rendered on the current page to its own
        action URL (the action carries the next_url a real browser keeps)."""
        m = re.search(r'<form class="auth-form" method="post" action="([^"]+)"',
                      self.page_html)
        assert m, "no login form on the current page"
        action = html_mod.unescape(m.group(1))
        self.post(action, {"email": email, "password": password}, fills=2)


# ------------------------------------------------------------------ helpers --

def serp_count(page_text):
    m = re.search(r"(\d+) results", page_text)
    assert m, "no result count rendered"
    return int(m.group(1))


def first_card(page_html):
    m = re.search(r'class="vehicle-card"[^>]*id="vehicle-card-([0-9a-f-]{36})"', page_html)
    assert m, "no vehicle card rendered"
    return m.group(1)


def card_field(page_html, lid, cls, pattern):
    i = page_html.find(f'id="vehicle-card-{lid}"')
    assert i > 0, f"card {lid} not on page"
    seg = page_html[i:i + 3500]
    m = re.search(pattern, seg)
    assert m, f"no {cls} on card {lid}"
    return html_mod.unescape(m.group(1)).strip()


def read(page_text, needle, label):
    assert needle in page_text, f"premise missing: {label}: {needle!r} not on page"
    return needle


def detail_for(client, lid):
    r = client.get(f"/vehicledetail/{lid}/")
    assert r.status_code == 200
    return r.get_data(as_text=True)



def card_segment(page_html, cards, idx, span=3500):
    """One card's own HTML: from its id to the next card's id (no leakage)."""
    start = page_html.find(f'id="vehicle-card-{cards[idx]}"')
    end = page_html.find(f'id="vehicle-card-{cards[idx + 1]}"') if idx + 1 < len(cards) else -1
    if end <= start:
        end = start + span
    return page_html[start:end]

# -------------------------------------------------------------------- walks --

def walk_0(w):
    """T0 — used SUV $25-35k, <70k mi, <=50 mi; Good Deal; dealer chain."""
    w.nav("/", count=False)
    t = w.search(stock="used", distance="50")
    w.facts["base_count"] = serp_count(t)
    assert w.facts["base_count"] == 249, "expected 249 used cars within 50 miles"
    t = w.filter(carry={"stock_type": "used", "maximum_distance": "50"},
                 body_style_slugs="suv", list_price_min="25000",
                 list_price_max="35000", mileage_max="70000")
    w.facts["suv_count"] = serp_count(t)
    assert w.facts["suv_count"] == 37, "expected 37 after the SUV + price + mileage filters"
    t = w.filter(carry={"stock_type": "used", "maximum_distance": "50",
                        "body_style_slugs": "suv", "list_price_min": "25000",
                        "list_price_max": "35000", "mileage_max": "70000"},
                 deal_ratings="good")
    w.facts["good_count"] = serp_count(t)
    assert w.facts["good_count"] == 22, "expected 22 after narrowing to Good Deal"
    t = w.sort("list_price_asc", carry={"stock_type": "used", "maximum_distance": "50",
                                        "body_style_slugs": "suv", "list_price_min": "25000",
                                        "list_price_max": "35000", "mileage_max": "70000",
                                        "deal_ratings": "good"})
    lid = first_card(w.page_html)
    w.facts["cheapest_price"] = card_field(w.page_html, lid, "price", r'class="price">(\$[\d,]+)')
    w.facts["cheapest_mileage"] = card_field(w.page_html, lid, "mileage", r'class="mileage">([\d,]+) mi')
    badge = card_field(w.page_html, lid, "badge", r'badge badge-[a-z-]+">([^<]+)')
    read(badge, "Good Deal", "deal badge")
    w.facts["cheapest_badge"] = badge
    t = w.click(f"/vehicledetail/{lid}/")
    m = re.search(r"Est\. payment \$(\d+)/mo", t)
    assert m, "no monthly payment on detail"
    w.facts["monthly"] = int(m.group(1))
    m = re.search(r"based on ([\d.]+)% APR, (\d+) months", t)
    assert m, "no APR on detail"
    w.facts["apr"] = m.group(1)
    m = re.search(r'href="(/dealers/\d+/[a-z0-9_-]+)/"', w.page_html)
    assert m, "no dealer link on detail"
    dealer_path = m.group(1)
    m = re.search(r"Seller's info ([A-Za-z0-9&'. -]+?) \d[\d,]* reviews", t)
    assert m, "no dealer name on detail"
    w.facts["dealer"] = m.group(1).strip()
    m = re.search(r"★ ([\d.]+)", t)
    assert m, "no dealer rating on detail"
    w.facts["dealer_rating"] = m.group(1)
    t = w.click(dealer_path.rstrip("/") + "/")
    m = re.search(r"<tr><th>Monday</th><td>([^<]+)</td>", w.page_html)
    assert m, "no Monday hours on dealer page"
    w.facts["monday_hours"] = m.group(1)
    m = re.search(r"New: (\(?\d{3}\)?[ -]?\d{3}[ -]?\d{4})", t)
    assert m, "no phone on dealer page"
    w.facts["dealer_phone"] = m.group(1)
    t = w.click(dealer_path.rstrip("/") + "/reviews/")
    m = re.search(r"\((\d[\d,]*) reviews\)", w.page_html) or \
        re.search(r"★ [\d.]+ · ([\d,]+) reviews", t)
    assert m, "no review count on reviews page"
    w.facts["review_count"] = m.group(1)
    t = w.click(dealer_path.rstrip("/") + "/inventory/")
    m = re.search(r"(\d+) cars listed at this dealership", t)
    assert m, "no inventory count"
    w.facts["inventory_count"] = int(m.group(1))
    w.compose()


def walk_1(w):
    """T1 — used Civics <=50 mi, Good Deal, lowest mileage; save as alice."""
    w.nav("/", count=False)
    t = w.search(stock="used", model="honda-civic", distance="50")
    w.facts["base_count"] = serp_count(t)
    assert w.facts["base_count"] > 0
    t = w.filter(carry={"stock_type": "used", "models[]": "honda-civic",
                        "maximum_distance": "50"}, deal_ratings="good")
    w.facts["good_count"] = serp_count(t)
    assert w.facts["good_count"] > 0
    t = w.sort("mileage_low", carry={"stock_type": "used", "models[]": "honda-civic",
                                     "maximum_distance": "50", "deal_ratings": "good"})
    lid = first_card(w.page_html)
    w.facts["price"] = card_field(w.page_html, lid, "price", r'class="price">(\$[\d,]+)')
    w.facts["mileage"] = card_field(w.page_html, lid, "mileage", r'class="mileage">([\d,]+) mi')
    t = w.click(f"/vehicledetail/{lid}/")
    m = re.search(r"Est\. payment \$(\d+)/mo", t)
    assert m, "no monthly payment"
    w.facts["monthly"] = int(m.group(1))
    m = re.search(r"based on ([\d.]+)% APR", t)
    assert m, "no APR"
    w.facts["apr"] = m.group(1)
    m = re.search(r"<li>([A-Za-z ]+) exterior color</li>", w.page_html)
    assert m, "no exterior color"
    w.facts["color"] = m.group(1).strip()
    m = re.search(r"Seller's info ([A-Za-z0-9&'. -]+?) \d[\d,]* reviews", t)
    assert m, "no dealer name"
    w.facts["dealer"] = m.group(1).strip()
    m = re.search(r"★ ([\d.]+)", t)
    assert m, "no dealer rating"
    w.facts["dealer_rating"] = m.group(1)
    # save while logged out -> login page -> back here -> save again
    w.post(f"/save/{lid}/", {"next": f"/vehicledetail/{lid}/"})
    read(w.page_text, "Password", "login page shown after save")
    w.login("alice.j@test.com", "TestPass123!")
    read(w.page_text, "\u2665 Save", "back on the listing after login")
    w.post(f"/save/{lid}/", {"next": f"/vehicledetail/{lid}/"})
    t = w.nav("/profile/your-garage/")
    i = w.page_html.find(f"saved-{lid}")
    assert i > 0, "saved car not in garage"
    w.facts["garage_saved"] = True
    read(t, "Saved searches", "saved-searches area")
    m = re.search(r"Used Honda Civics under \$25k", t)
    assert m, "alice's saved search missing"
    w.facts["saved_search"] = "Used Honda Civics under $25k"
    m = re.search(r"Used Honda Civics under \$25k .*?alert frequency: (\w+)", t)
    assert m, "no alert frequency for saved search"
    w.facts["saved_search_freq"] = m.group(1)
    w.compose()


def walk_2(w):
    """T2 — new RAV4 search, cheapest + dealer, calculator, research page."""
    w.nav("/", count=False)
    t = w.search(stock="new", model="toyota-rav4")
    w.facts["count"] = serp_count(t)
    assert w.facts["count"] == 24, "expected 24 new RAV4s"
    prices = [int(p.replace(",", "")) for p in re.findall(r'class="price">\$([\d,]+)', w.page_html)]
    assert prices, "no prices on SERP"
    w.facts["min_price"], w.facts["max_price"] = min(prices), max(prices)
    t = w.sort("list_price_asc", carry={"stock_type": "new", "models[]": "toyota-rav4"})
    lid = first_card(w.page_html)
    w.facts["cheapest_price"] = card_field(w.page_html, lid, "price", r'class="price">(\$[\d,]+)')
    t = w.click(f"/vehicledetail/{lid}/")
    m = re.search(r"Est\. payment \$(\d+)/mo", t)
    assert m, "no monthly payment"
    w.facts["monthly"] = int(m.group(1))
    m = re.search(r"based on ([\d.]+)% APR", t)
    assert m, "no APR"
    w.facts["apr"] = m.group(1)
    m = re.search(r"Seller's info ([A-Za-z0-9&'. -]+?) \d[\d,]* reviews", t)
    assert m, "no dealer name"
    w.facts["dealer"] = m.group(1).strip()
    m = re.search(r'href="(/dealers/\d+/[a-z0-9_-]+)/"', w.page_html)
    assert m, "no dealer link"
    t = w.click(m.group(1) + "/")
    m = re.search(r"<tr><th>Monday</th><td>([^<]+)</td>", w.page_html)
    assert m, "no Monday hours on dealer page"
    w.facts["monday_hours"] = m.group(1)
    # calculator for the cheapest price, good credit, $4,000 down, 60 months
    price = int(w.facts["cheapest_price"].replace("$", "").replace(",", ""))
    t = w.nav("/car-loan-calculator/")
    t = w.post("/car-loan-calculator/",
               {"vehicle_price": str(price), "credit_rating": "good",
                "down_payment": "4000", "term": "60"}, fills=4, expect_redirect=False)
    m = re.search(r"Estimated monthly payment: \$([\d,]+)/mo", t)
    assert m, "no calculator monthly payment"
    w.facts["calc_monthly"] = int(m.group(1))
    m = re.search(r"<tr><th>Total interest paid</th><td>\$([\d,]+)</td>", w.page_html)
    assert m, "no total interest"
    w.facts["calc_interest"] = int(m.group(1).replace(",", ""))
    # research page for the RAV4 model year
    t = w.nav("/research/")
    m = re.search(r'href="(/research/toyota-rav4-\d+/)"', w.page_html)
    assert m, "no RAV4 research page listed"
    t = w.click(m.group(1))
    m = re.search(r"Shop options from \$([\d,]+)", t)
    assert m, "no starting price on research page"
    w.facts["research_start"] = int(m.group(1).replace(",", ""))
    trims = re.findall(r'<tr>\s*<td>([^<]+)</td>\s*<td>(\$[\d,]+)</td>', w.page_html)
    assert trims, "no trims on research page"
    w.facts["trim_count"] = len(trims)
    w.facts["cheapest_trim"] = trims[0]
    m = re.search(r"(\d+)% of drivers recommend", t)
    assert m, "no recommend pct"
    w.facts["recommend"] = m.group(1)
    m = re.search(r"([\d.]+) / 5 Based on (\d+) reviews", t)
    assert m, "no consumer rating"
    w.facts["consumer_rating"] = m.group(1)
    w.compose()


def walk_3(w):
    """T3 — certified Toyotas, <=40k mi, >=2020; CPO terms; dealer chain."""
    w.nav("/", count=False)
    t = w.search(stock="cpo", make="toyota")
    w.facts["base_count"] = serp_count(t)
    assert w.facts["base_count"] == 8, "expected 8 certified Toyotas"
    t = w.filter(carry={"stock_type": "cpo", "makes[]": "toyota"}, mileage_max="40000")
    w.facts["mileage_count"] = serp_count(t)
    assert w.facts["mileage_count"] == 7, "expected 7 after the mileage cap"
    t = w.filter(carry={"stock_type": "cpo", "makes[]": "toyota", "mileage_max": "40000"},
                 year_min="2020")
    w.facts["year_count"] = serp_count(t)
    assert w.facts["year_count"] == 7, "expected 7 after the year floor"
    t = w.sort("list_price_asc", carry={"stock_type": "cpo", "makes[]": "toyota",
                                        "mileage_max": "40000", "year_min": "2020"})
    lid = first_card(w.page_html)
    w.facts["price"] = card_field(w.page_html, lid, "price", r'class="price">(\$[\d,]+)')
    w.facts["mileage"] = card_field(w.page_html, lid, "mileage", r'class="mileage">([\d,]+) mi')
    t = w.click(f"/vehicledetail/{lid}/")
    m = re.search(r"Seller's info ([A-Za-z0-9&'. -]+?) \d[\d,]* reviews", t)
    assert m, "no dealer name"
    w.facts["dealer"] = m.group(1).strip()
    read(t, "Manufacturer Certified Pre-Owned", "CPO program section")
    w.facts["cpo_text"] = True
    m = re.search(r"History report summary: Owner (\d+), Accidents (\d+), Title ([A-Za-z]+)", t)
    assert m, "no history summary"
    w.facts["history"] = (m.group(1), m.group(2), m.group(3))
    m = re.search(r'badge badge-[a-z-]+">(Great Deal|Good Deal|Fair Deal)<', w.page_html)
    w.facts["badge"] = m.group(1) if m else None
    m = re.search(r'href="(/dealers/\d+/[a-z0-9_-]+)/"', w.page_html)
    assert m, "no dealer link"
    dealer_path = m.group(1)
    t = w.click(dealer_path.rstrip("/") + "/")
    m = re.search(r"<tr><th>Monday</th><td>([^<]+)</td>", w.page_html)
    assert m, "no Monday hours"
    w.facts["monday_hours"] = m.group(1)
    m = re.search(r"New: (\(?\d{3}\)?[ -]?\d{3}[ -]?\d{4})", t)
    assert m, "no phone"
    w.facts["phone"] = m.group(1)
    t = w.click(dealer_path.rstrip("/") + "/reviews/")
    m = re.search(r"([\d,]+) reviews", t)
    assert m, "no review count"
    w.facts["review_count"] = m.group(1)
    t = w.click(dealer_path.rstrip("/") + "/inventory/")
    m = re.search(r"(\d+) cars listed at this dealership", t)
    w.facts["inventory_count"] = int(m.group(1)) if m else 0
    # filter the inventory to certified cars
    w.fill("stock_type", "cpo")
    t = w.nav(dealer_path.rstrip("/") + "/inventory/?stock_type=cpo")
    m = re.search(r"(\d+) cars listed at this dealership", t)
    assert m, "no certified inventory count"
    w.facts["cpo_inventory"] = int(m.group(1))
    w.compose()


def walk_4(w):
    """T4 — Toyota dealer directory, top dealer chain; dana saves a search."""
    t = w.nav("/dealers/")
    w.fill("make", "Toyota")
    w.fill("rating", "4")
    w.fill("maximum_distance", "100")
    t = w.nav("/dealers/?make=Toyota&rating=4&maximum_distance=100")
    m = re.search(r"(\d+) matches", t)
    assert m, "no dealer match count"
    w.facts["matches"] = int(m.group(1))
    assert w.facts["matches"] > 0
    m = re.search(r'class="dealer-list".*?<a href="(/dealers/\d+/[a-z0-9_-]+)/">([^<]+)</a>', w.page_html, re.S)
    assert m, "no top dealer row"
    dealer_path, dealer_name = m.group(1), m.group(2)
    w.facts["dealer"] = dealer_name
    m = re.search(r"★ ([\d.]+) \(([\d,]+) reviews\)", t)
    assert m, "no rating/review count for top dealer"
    w.facts["rating"], w.facts["review_count"] = m.group(1), m.group(2)
    m = re.search(r"(\d+) miles away", t)
    w.facts["distance"] = m.group(1) if m else None
    t = w.click(dealer_path.rstrip("/") + "/")
    m = re.search(r"<tr><th>Monday</th><td>([^<]+)</td>", w.page_html)
    assert m, "no Monday hours"
    w.facts["monday_hours"] = m.group(1)
    m = re.search(r"New: (\(?\d{3}\)?[ -]?\d{3}[ -]?\d{4})", t)
    assert m, "no new-cars phone"
    w.facts["phone_new"] = m.group(1)
    t = w.click(dealer_path.rstrip("/") + "/reviews/")
    revs = re.findall(r"By ([A-Za-z0-9_.-]+).*?· ★ ([\d.]+) · (\d{4}-\d\d-\d\d)", w.page_text)
    assert len(revs) >= 3, "fewer than 3 dated reviews"
    w.facts["recent"] = revs[:3]
    # log in as dana, search used RAV4s within 50 miles, save the search
    t = w.nav("/authn/login")
    w.login("dana.k@test.com", "TestPass123!")
    read(w.page_text, "Your Garage", "garage after login")
    w.nav("/")
    t = w.search(stock="used", model="toyota-rav4", distance="50")
    w.facts["rav4_count"] = serp_count(t)
    assert w.facts["rav4_count"] > 0
    read(w.page_html, "Name this search", "save-search form shown")
    w.post("/searches/save/", {"query_string": w.page_html and re.search(r'name="query_string" value="([^"]*)"', w.page_html).group(1),
                               "name": "RAV4 watch", "alert_frequency": "weekly"}, fills=2)
    read(w.page_text, "Saved searches", "garage saved-searches area")
    read(w.page_text, "RAV4 watch", "saved search name")
    m = re.search(r"RAV4 watch .*?alert frequency: (\w+)", w.page_text)
    assert m, "no saved-search frequency"
    w.facts["saved_freq"] = m.group(1)
    w.compose()


def walk_5(w):
    """T5 — Porsche Bellevue via make filter; reviews; inventory; save+remove as bob."""
    t = w.nav("/dealers/")
    w.fill("make", "Porsche")
    t = w.nav("/dealers/?make=Porsche")
    m = re.search(r'href="(/dealers/\d+/[a-z0-9_-]+)/"[^>]*>Porsche Bellevue<', w.page_html) or \
        re.search(r"dealer-row-main.*?Porsche Bellevue.*?href=\"(/dealers/\d+/[a-z0-9_-]+)/\"", w.page_html, re.S)
    assert m, "Porsche Bellevue not in filtered directory"
    dealer_path = m.group(1)
    t = w.click(dealer_path.rstrip("/") + "/")
    m = re.search(r"★ ([\d.]+) · ([\d,]+) reviews", t)
    assert m, "no rating/review count"
    w.facts["rating"], w.facts["review_count"] = m.group(1), m.group(2)
    hours = re.findall(r"<(th|td)>(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)</\1><td>([^<]+)</td>", w.page_html)
    days = re.findall(r"<th>(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)</th><td>([^<]+)</td>", w.page_html)
    assert len(days) == 7, "no weekly hours table"
    w.facts["hours"] = dict(days)
    m = re.search(r"(\d+) awards", t)
    assert m, "no awards count"
    w.facts["awards"] = int(m.group(1))
    t = w.click(dealer_path.rstrip("/") + "/reviews/")
    revs = re.findall(r"By ([A-Za-z0-9_.-]+).*?· ★ ([\d.]+) · (\d{4}-\d\d-\d\d)", w.page_text)
    assert len(revs) >= 3, "fewer than 3 reviews with star+date"
    w.facts["recent"] = revs[:3]
    t = w.click(dealer_path.rstrip("/") + "/inventory/")
    m = re.search(r"(\d+) cars listed at this dealership", t)
    assert m, "no inventory count"
    w.facts["inventory_count"] = int(m.group(1))
    assert w.facts["inventory_count"] > 0
    # most expensive car on the inventory page (sorted by price asc)
    cards = re.findall(r'id="vehicle-card-([0-9a-f-]{36})"', w.page_html)
    assert cards, "no inventory cards"
    lid = cards[-1]
    i = w.page_html.find(f'id="vehicle-card-{lid}"')
    seg = w.page_html[i:i + 3500]
    m = re.search(r'card-title">\s*<a href="[^"]*">([^<]+)</a>', seg)
    assert m, "no title for most expensive"
    w.facts["most_expensive"] = (m.group(1), re.search(r'class="price">(\$[\d,]+)', seg).group(1))
    t = w.click(f"/vehicledetail/{lid}/")
    read(w.page_text, "♥ Save", "save button on listing")
    w.post(f"/save/{lid}/", {"next": f"/vehicledetail/{lid}/"})
    w.login("bob.c@test.com", "TestPass123!")
    w.post(f"/save/{lid}/", {"next": f"/vehicledetail/{lid}/"})
    t = w.nav("/profile/your-garage/")
    i = w.page_html.find(f"saved-{lid}")
    assert i > 0, "saved car missing from garage"
    w.facts["garage_shows"] = True
    # remove it
    w.post(f"/save/{lid}/", {"next": "/profile/your-garage/"})
    t = w.nav("/profile/your-garage/")
    assert f"saved-{lid}" not in w.page_html, "car still in garage after remove"
    w.facts["removed"] = True
    w.compose()


def walk_6(w):
    """T6 — Civic vs Corolla compare, both model pages, Civic listings, save as carol."""
    t = w.nav("/research/compare/")
    m = re.search(r'href="(/research/compare/honda-civic-vs-toyota-corolla/)"', w.page_html)
    assert m, "civic-corolla compare not listed"
    t = w.click(m.group(1))
    m = re.search(r"Starting MSRP</th>\s*<td>\$([\d,]+)</td>\s*<td>\$([\d,]+)</td>", w.page_html)
    assert m, "no starting MSRPs in compare table"
    a_msrp, b_msrp = int(m.group(1).replace(",", "")), int(m.group(2).replace(",", ""))
    w.facts["cheaper"] = "Civic" if a_msrp <= b_msrp else "Corolla"
    w.facts["msrp_delta"] = abs(a_msrp - b_msrp)
    m = re.search(r"Horsepower</th>\s*<td>(\d+) hp</td>\s*<td>(\d+) hp</td>", w.page_html)
    assert m, "no horsepower row"
    w.facts["hp"] = (m.group(1), m.group(2))
    m = re.search(r"MPG</th>\s*<td>([^<]+)</td>\s*<td>([^<]+)</td>", w.page_html)
    assert m, "no MPG row"
    w.facts["mpg"] = (m.group(1), m.group(2))
    m = re.search(r"Seating Capacity</th>\s*<td>(\d+)</td>\s*<td>(\d+)</td>", w.page_html)
    assert m, "no seating row"
    w.facts["seats"] = (m.group(1), m.group(2))
    m = re.search(r"Passenger Volume</th>\s*<td>([^<]+)</td>\s*<td>([^<]+)</td>", w.page_html)
    assert m, "no passenger volume row"
    w.facts["pass_vol"] = (m.group(1), m.group(2))
    # both model pages from the comparison
    m = re.search(r'href="(/research/honda-civic-\d+/)"', w.page_html)
    assert m, "no Civic model page link"
    civic_path = m.group(1)
    t = w.click(civic_path)
    m = re.search(r"Shop options from \$([\d,]+)", t)
    assert m, "no Civic starting price"
    w.facts["civic_start"] = int(m.group(1).replace(",", ""))
    trims = re.findall(r'<tr>\s*<td>([^<]+)</td>\s*<td>(\$[\d,]+)</td>', w.page_html)
    assert trims, "no Civic trims"
    w.facts["civic_trims"] = len(trims)
    w.facts["civic_cheapest_trim"] = trims[0]
    m = re.search(r"Safety rating (\d)/5", t)
    assert m, "no Civic safety rating"
    w.facts["civic_safety"] = m.group(1)
    m = re.search(r"(\d+)% of drivers recommend", t)
    assert m, "no Civic recommend pct"
    w.facts["civic_recommend"] = m.group(1)
    m = re.search(r"([\d.]+) / 5 Based on (\d+) reviews", t)
    assert m, "no Civic consumer rating"
    w.facts["civic_rating"] = m.group(1)
    w.back()
    m = re.search(r'href="(/research/toyota-corolla-\d+/)"', w.page_html)
    assert m, "no Corolla model page link"
    t = w.click(m.group(1))
    m = re.search(r"([\d.]+) / 5 Based on (\d+) reviews", t)
    w.facts["corolla_rating"] = m.group(1) if m else None
    w.back()
    t = w.click(civic_path)
    m = re.search(r'href="(/shopping/results/\?[^"]*)"', w.page_html)
    assert m, "no listings link on Civic page"
    qs = html_mod.unescape(m.group(1))
    t = w.click(qs)
    read(t, "results", "civic listings SERP")
    assert 'models%5B%5D=honda-civic' in qs or 'models[]=honda-civic' in qs, \
        "the listings link must emit models[] (sort/filter round-trip)"
    t = w.sort("list_price_asc", carry=dict(parse_qsl(qs.split("?", 1)[1])))
    w.facts["civic_serp_count"] = serp_count(t)
    assert w.facts["civic_serp_count"] == 68, "expected 68 Civic listings"
    titles = re.findall(r'card-title">\s*<a href="[^"]*">([^<]+)</a>', w.page_html)
    assert titles and all('Civic' in x for x in titles), \
        "the model filter must survive the sort (was silently dropped before)"
    lid = first_card(w.page_html)
    w.facts["cheapest"] = card_field(w.page_html, lid, "price", r'class="price">(\$[\d,]+)')
    # save the cheapest from its card
    w.post(f"/save/{lid}/", {"next": qs})
    w.login("carol.d@test.com", "TestPass123!")
    w.post(f"/save/{lid}/", {"next": qs})
    t = w.nav("/profile/your-garage/")
    i = w.page_html.find(f"saved-{lid}")
    assert i > 0, "saved car missing from garage"
    w.facts["garage"] = True
    w.compose()


def walk_7(w):
    """T7 — Instant Cash Offer: 2018 Civic EX, then 2019 RAV4 XLE."""
    t = w.nav("/sell/instant-offer/")
    read(t, "Get your Instant Offer", "offer start page")
    t = w.post("/sell/instant-offer/vehicle/",
               {"year": "2018", "make": "HONDA", "model": "CIVIC",
                "trim": "EX 4 DOOR HATCHBACK 1.5L 4 CYL TURBO"}, fills=4)
    m = re.search(r"Estimated car value</h2>\s*<p class=\"value-range\">\$([\d,]+) - \$([\d,]+)", w.page_html)
    assert m, "no initial estimate on details page"
    w.facts["civic_initial"] = (int(m.group(1).replace(",", "")), int(m.group(2).replace(",", "")))
    t = w.post("/sell/instant-offer/details/",
               {"mileage": "60000", "zip": "98101", "exterior_color": "Blue",
                "keys": "1", "original_owner": "Yes", "payments": "No"}, fills=5)
    m = re.search(r"Your Instant Offer estimate</h2>\s*<p class=\"value-range\">\$([\d,]+) - \$([\d,]+)", w.page_html)
    assert m, "no final offer for Civic"
    w.facts["civic_offer"] = (int(m.group(1).replace(",", "")), int(m.group(2).replace(",", "")))
    # second vehicle: 2019 RAV4 XLE
    t = w.click("/sell/instant-offer/")
    t = w.post("/sell/instant-offer/vehicle/",
               {"year": "2019", "make": "TOYOTA", "model": "RAV4",
                "trim": "XLE 4 DOOR SUV 2.5L 4 CYL"}, fills=4)
    t = w.post("/sell/instant-offer/details/",
               {"mileage": "55000", "zip": "98101", "exterior_color": "White",
                "keys": "1", "original_owner": "Yes", "payments": "No"}, fills=5)
    m = re.search(r"Your Instant Offer estimate</h2>\s*<p class=\"value-range\">\$([\d,]+) - \$([\d,]+)", w.page_html)
    assert m, "no final offer for RAV4"
    w.facts["rav4_offer"] = (int(m.group(1).replace(",", "")), int(m.group(2).replace(",", "")))
    w.facts["worth_more"] = "Civic" if w.facts["civic_offer"][0] > w.facts["rav4_offer"][0] else "RAV4"
    w.compose()


def walk_8(w):
    """T8 — payment calculator: 72 vs 48 months, custom 9%, $40k excellent."""
    t = w.nav("/car-loan-calculator/")
    read(t, "Estimate your monthly car loan payment", "calculator page")
    t = w.post("/car-loan-calculator/",
               {"vehicle_price": "30000", "credit_rating": "good",
                "down_payment": "3000", "term": "72"}, fills=4, expect_redirect=False)
    m = re.search(r"Estimated monthly payment: \$([\d,]+)/mo", t)
    assert m, "no 72-month payment"
    w.facts["m72"] = int(m.group(1).replace(",", ""))
    m = re.search(r"<tr><th>Total interest paid</th><td>\$([\d,]+)</td>", w.page_html)
    assert m, "no 72-month interest"
    w.facts["i72"] = int(m.group(1).replace(",", ""))
    t = w.post("/car-loan-calculator/", {"term": "48"}, fills=1, expect_redirect=False)
    m = re.search(r"Estimated monthly payment: \$([\d,]+)/mo", t)
    assert m, "no 48-month payment"
    w.facts["m48"] = int(m.group(1).replace(",", ""))
    m = re.search(r"<tr><th>Total interest paid</th><td>\$([\d,]+)</td>", w.page_html)
    assert m, "no 48-month interest"
    w.facts["i48"] = int(m.group(1).replace(",", ""))
    t = w.post("/car-loan-calculator/", {"custom_apr": "9", "term": "72"}, fills=2, expect_redirect=False)
    m = re.search(r"Estimated monthly payment: \$([\d,]+)/mo", t)
    assert m, "no 9%-APR payment"
    w.facts["m9"] = int(m.group(1).replace(",", ""))
    t = w.post("/car-loan-calculator/",
               {"vehicle_price": "40000", "credit_rating": "excellent",
                "down_payment": "5000", "term": "60"}, fills=4, expect_redirect=False)
    m = re.search(r"Estimated monthly payment: \$([\d,]+)/mo", t)
    assert m, "no $40k payment"
    w.facts["m40k"] = int(m.group(1).replace(",", ""))
    m = re.search(r"<tr><th>APR used</th><td>([\d.]+)%</td>", w.page_html)
    assert m, "no APR used row"
    w.facts["apr40k"] = m.group(1)
    w.compose()


def walk_9(w):
    """T9 — for sale by owner, under $20k, two listings, save as dana."""
    t = w.nav("/shopping/for-sale-by-owner/")
    read(t, "Cars for Sale by Owner", "FSO browse page")
    m = re.search(r'href="(/shopping/results/\?[^"]*seller_type=private_seller[^"]*)"', w.page_html)
    assert m, "no private-seller listings link"
    fso_qs = m.group(1)
    t = w.click(fso_qs)
    w.facts["count"] = serp_count(t)
    assert w.facts["count"] == 24, "expected 24 for-sale-by-owner results"
    t = w.filter(carry={"stock_type": "used", "seller_type": "private_seller"},
                 list_price_max="20000")
    w.facts["under20k"] = serp_count(t)
    assert w.facts["under20k"] == 16, "expected 16 FSBO listings under $20,000"
    t = w.sort("list_price_asc", carry={"stock_type": "used", "seller_type": "private_seller",
                                        "list_price_max": "20000"})
    cards = re.findall(r'id="vehicle-card-([0-9a-f-]{36})"', w.page_html)
    assert len(cards) >= 2, "fewer than 2 FSO listings"
    cheapest, second = cards[0], cards[1]
    w.facts["cheapest"] = (card_field(w.page_html, cheapest, "price", r'class="price">(\$[\d,]+)'),
                           card_field(w.page_html, cheapest, "mileage", r'class="mileage">([\d,]+) mi'))
    w.facts["second"] = (card_field(w.page_html, second, "price", r'class="price">(\$[\d,]+)'),
                          card_field(w.page_html, second, "mileage", r'class="mileage">([\d,]+) mi'))
    w.facts["badges"] = bool(re.search(r'badge badge-[a-z-]+">(Great|Good|Fair) Deal', w.page_html))
    t = w.click(f"/vehicledetail/{cheapest}/")
    m = re.search(r"<li>([A-Za-z ]+) exterior color</li>", w.page_html)
    assert m, "no exterior color on FSO listing"
    w.facts["color"] = m.group(1).strip()
    w.facts["seller_area"] = "Seller's info" in t or "Confirm Availability" in t
    w.back()
    t = w.click(f"/vehicledetail/{second}/")
    read(w.page_text, "Features", "second-cheapest listing opens")
    w.back()
    # save the cheaper one from its card
    w.post(f"/save/{cheapest}/", {"next": fso_qs})
    w.login("dana.k@test.com", "TestPass123!")
    w.post(f"/save/{cheapest}/", {"next": fso_qs})
    t = w.nav("/profile/your-garage/")
    i = w.page_html.find(f"saved-{cheapest}")
    assert i > 0, "saved FSO car missing from garage"
    w.facts["garage"] = True
    w.compose()


def walk_10(w):
    """T10 — electric cars under $30k, cheapest + most expensive, save as alice."""
    t = w.nav("/shopping/electric/")
    read(t, "Electric Cars for Sale", "electric browse page")
    m = re.search(r'href="(/shopping/results/\?fuel_slugs=electric)"', w.page_html)
    assert m, "no electric listings link"
    ev_qs = m.group(1)
    t = w.click(ev_qs)
    w.facts["count"] = serp_count(t)
    assert w.facts["count"] == 101, "expected 101 electric results"
    t = w.filter(carry={"fuel_slugs": "electric"}, list_price_max="30000")
    w.facts["under30k"] = serp_count(t)
    assert w.facts["under30k"] == 31, "expected 31 EVs under $30,000"
    t = w.sort("list_price_asc", carry={"fuel_slugs": "electric", "list_price_max": "30000"})
    cards = re.findall(r'id="vehicle-card-([0-9a-f-]{36})"', w.page_html)
    assert cards, "no EV cards"
    cheapest, most_exp = cards[0], cards[-1]
    w.facts["cheapest"] = (card_field(w.page_html, cheapest, "price", r'class="price">(\$[\d,]+)'),
                           card_field(w.page_html, cheapest, "mileage", r'class="mileage">([\d,]+) mi'),
                           card_field(w.page_html, cheapest, "seller", r'seller-name">([^<]+)'))
    t = w.click(f"/vehicledetail/{cheapest}/")
    m = re.search(r"Est\. payment \$(\d+)/mo", t)
    assert m, "no monthly payment"
    w.facts["monthly"] = int(m.group(1))
    m = re.search(r"based on ([\d.]+)% APR", t)
    assert m, "no APR"
    w.facts["apr"] = m.group(1)
    m = re.search(r"<li>([A-Za-z ]+) exterior color</li>", w.page_html)
    assert m, "no exterior color"
    w.facts["color"] = m.group(1).strip()
    feats = re.findall(r'<div class="feature-group">\s*<h3>(\w+)</h3>\s*<ul>(.*?)</ul>', w.page_html, re.S)
    items = [x.strip() for _, body in feats for x in re.findall(r'<li[^>]*>([^<]+)</li>', body)]
    assert len(items) >= 2, "fewer than 2 features on EV listing"
    w.facts["features"] = items[:2]
    w.back()
    t = w.click(f"/vehicledetail/{most_exp}/")
    m = re.search(r'class="mileage">([\d,]+) mi', w.page_html)
    assert m, "no mileage on most expensive EV"
    w.facts["most_exp_mileage"] = m.group(1)
    w.facts["most_exp_seller"] = card_field(w.page_html, most_exp, "seller", r'seller-name">([^<]+)') \
        if f"vehicle-card-{most_exp}" in w.page_html else None
    w.back()
    w.post(f"/save/{cheapest}/", {"next": ev_qs})
    w.login("alice.j@test.com", "TestPass123!")
    w.post(f"/save/{cheapest}/", {"next": ev_qs})
    t = w.nav("/profile/your-garage/")
    n = len(re.findall(r'class="vehicle-card" id="saved-', w.page_html))
    assert n > 0, "no saved cars in garage"
    w.facts["saved_count"] = n
    w.compose()


def walk_11(w):
    """T11 — budget used cars <$15k, <=80k mi, <=20 mi; save as carol."""
    w.nav("/", count=False)
    t = w.search(stock="used", distance="20")
    w.facts["base_count"] = serp_count(t)
    t = w.filter(carry={"stock_type": "used", "maximum_distance": "20"},
                 list_price_max="15000", mileage_max="80000")
    w.facts["count"] = serp_count(t)
    assert w.facts["count"] == 3, "expected 3 budget listings"
    t = w.sort("mileage_low", carry={"stock_type": "used", "maximum_distance": "20",
                                     "list_price_max": "15000", "mileage_max": "80000"})
    cards = re.findall(r'id="vehicle-card-([0-9a-f-]{36})"', w.page_html)
    assert len(cards) >= 3, "fewer than 3 budget listings"
    for i, lid in enumerate(cards[:3]):
        w.facts[f"low{i}_price"] = card_field(w.page_html, lid, "price", r'class="price">(\$[\d,]+)')
        w.facts[f"low{i}_mileage"] = card_field(w.page_html, lid, "mileage", r'class="mileage">([\d,]+) mi')
    lid = cards[0]
    t = w.click(f"/vehicledetail/{lid}/")
    m = re.search(r"Seller's info ([A-Za-z0-9&'. -]+?) \d[\d,]* reviews", t)
    assert m, "no dealer name"
    w.facts["dealer"] = m.group(1).strip()
    m = re.search(r"<li>([A-Za-z ]+) exterior color</li>", w.page_html)
    assert m, "no exterior color"
    w.facts["color"] = m.group(1).strip()
    m = re.search(r"Seller's notes</h2>\s*<p class=\"seller-notes\">([^<]{10,}?)\.", w.page_html, re.S)
    assert m, "no seller's notes"
    w.facts["notes"] = " ".join(m.group(1).split())[:160]
    m = re.search(r"Est\. payment \$(\d+)/mo", t)
    assert m, "no monthly payment"
    w.facts["monthly"] = int(m.group(1))
    m = re.search(r"based on ([\d.]+)% APR", t)
    assert m, "no APR"
    w.facts["apr"] = m.group(1)
    w.post(f"/save/{lid}/", {"next": f"/vehicledetail/{lid}/"})
    w.login("carol.d@test.com", "TestPass123!")
    w.post(f"/save/{lid}/", {"next": f"/vehicledetail/{lid}/"})
    t = w.nav("/profile/your-garage/")
    n = len(re.findall(r'class="vehicle-card" id="saved-', w.page_html))
    assert n > 0
    i = w.page_html.find(f"saved-{lid}")
    assert i > 0, "saved budget car missing from garage"
    w.facts["saved_count"] = n
    w.compose()


def walk_12(w):
    """T12 — manual transmission under $25k; save as bob."""
    w.nav("/", count=False)
    t = w.search(stock="used", distance="50")
    w.facts["base_count"] = serp_count(t)
    t = w.filter(carry={"stock_type": "used", "maximum_distance": "50"},
                 transmission_slugs="manual")
    w.facts["manual_count"] = serp_count(t)
    assert w.facts["manual_count"] == 12, "expected 12 manual cars within 50 miles"
    t = w.filter(carry={"stock_type": "used", "maximum_distance": "50",
                        "transmission_slugs": "manual"},
                 list_price_max="25000")
    w.facts["count"] = serp_count(t)
    assert w.facts["count"] == 3, "expected 3 manual cars under $25,000"
    t = w.sort("list_price_asc", carry={"stock_type": "used", "maximum_distance": "50",
                                        "transmission_slugs": "manual", "list_price_max": "25000"})
    cards = re.findall(r'id="vehicle-card-([0-9a-f-]{36})"', w.page_html)
    assert cards, "no manual cards"
    cheapest, most_exp = cards[0], cards[-1]
    w.facts["cheapest"] = (card_field(w.page_html, cheapest, "title", r'card-title">\s*<a href="[^"]*">([^<]+)</a>'),
                           card_field(w.page_html, cheapest, "price", r'class="price">(\$[\d,]+)'))
    w.facts["most_exp"] = (card_field(w.page_html, most_exp, "title", r'card-title">\s*<a href="[^"]*">([^<]+)</a>'),
                           card_field(w.page_html, most_exp, "price", r'class="price">(\$[\d,]+)'))
    t = w.click(f"/vehicledetail/{cheapest}/")
    m = re.search(r'class="mileage">([\d,]+) mi', w.page_html)
    assert m, "no mileage"
    w.facts["mileage"] = m.group(1)
    m = re.search(r"<li>([A-Za-z ]+) exterior color</li>", w.page_html)
    assert m, "no exterior color"
    w.facts["color"] = m.group(1).strip()
    m = re.search(r"Seller's info ([A-Za-z0-9&'. -]+?) \d[\d,]* reviews", t)
    assert m, "no dealer name"
    w.facts["dealer"] = m.group(1).strip()
    m = re.search(r"★ ([\d.]+)", t)
    assert m, "no dealer rating"
    w.facts["rating"] = m.group(1)
    m = re.search(r"Est\. payment \$(\d+)/mo", t)
    assert m, "no monthly payment"
    w.facts["monthly"] = int(m.group(1))
    m = re.search(r"based on ([\d.]+)% APR", t)
    assert m, "no APR"
    w.facts["apr"] = m.group(1)
    w.post(f"/save/{cheapest}/", {"next": f"/vehicledetail/{cheapest}/"})
    w.login("bob.c@test.com", "TestPass123!")
    w.post(f"/save/{cheapest}/", {"next": f"/vehicledetail/{cheapest}/"})
    t = w.nav("/profile/your-garage/")
    i = w.page_html.find(f"saved-{cheapest}")
    assert i > 0, "saved manual car missing from garage"
    w.facts["garage"] = True
    w.compose()


def walk_13(w):
    """T13 — register, CPO SUV search <=100 mi, save two cars + the search, remove one."""
    t = w.nav("/authn/register")
    read(t, "Create", "register page")
    email, name, pw = "walk13@test.com", "Walk Thirteen", "TestPass123!"
    w.post("/authn/register", {"email": email, "name": name, "password": pw}, fills=3)
    read(w.page_text, "Your Garage", "garage after register")
    w.nav("/")
    t = w.search(stock="cpo", distance="100")
    t = w.filter(carry={"stock_type": "cpo", "maximum_distance": "100"},
                 body_style_slugs="suv")
    w.facts["count"] = serp_count(t)
    assert w.facts["count"] == 32, "expected 32 certified SUVs within 100 miles"
    cards = re.findall(r'id="vehicle-card-([0-9a-f-]{36})"', w.page_html)
    assert len(cards) >= 2
    first, second = cards[0], cards[1]
    serp_path = w.history[-1]
    w.post(f"/save/{first}/", {"next": serp_path})
    w.post(f"/save/{second}/", {"next": serp_path})
    read(w.page_text, "Name this search", "save-search form")
    w.post("/searches/save/", {"query_string": serp_path,
                               "name": "CPO SUVs near me", "alert_frequency": "daily"}, fills=2)
    read(w.page_text, "Saved cars", "garage after saving search")
    i = w.page_html.find(f"saved-{first}")
    titles = re.findall(r'id="saved-([0-9a-f-]{36})"[^>]*>.*?class="price">(\$[\d,]+).*?card-title">\s*<a href="[^"]*">([^<]+)</a>', w.page_html, re.S)
    assert len(titles) >= 2, "two saved cars missing from garage"
    w.facts["saved"] = titles[:2]
    m = re.search(r"CPO SUVs near me .*?alert frequency: (\w+)", w.page_text)
    assert m, "saved search missing"
    w.facts["search_freq"] = m.group(1)
    # remove one saved car
    w.post(f"/save/{first}/", {"next": "/profile/your-garage/"})
    t = w.nav("/profile/your-garage/")
    assert f"saved-{first}" not in w.page_html and f"saved-{second}" in w.page_html, "remove failed"
    w.facts["remaining"] = second
    w.compose()


def walk_14(w):
    """T14 — bob's garage report, saved-search link, Tesla offer, remove."""
    t = w.nav("/authn/login")
    w.login("bob.c@test.com", "TestPass123!")
    read(w.page_text, "Your Garage", "bob's garage")
    saved = re.findall(r'id="saved-([0-9a-f-]{36})"[^>]*>.*?card-title">\s*<a href="[^"]*">([^<]+)</a></h3>.*?class="price">(\$[\d,]+)', w.page_html, re.S)
    assert saved, "bob has no saved cars"
    w.facts["saved"] = saved
    searches = re.findall(r'<li><a href="(/shopping/results/\?[^"]*)">([^<]+)</a>\s*<span class="muted"> &middot; alert frequency: (\w+)</span>', w.page_html)
    assert searches, "bob has no saved searches"
    w.facts["searches"] = searches
    t = w.click(searches[0][0])
    w.facts["search_results"] = serp_count(t)
    # value bob's Tesla through the wizard
    t = w.nav("/sell/instant-offer/")
    t = w.post("/sell/instant-offer/vehicle/",
               {"year": "2021", "make": "TESLA", "model": "MODEL 3",
                "trim": "LONG RANGE AWD SEDAN ELECTRIC"}, fills=4)
    m = re.search(r"Estimated car value</h2>\s*<p class=\"value-range\">\$([\d,]+) - \$([\d,]+)", w.page_html)
    assert m, "no initial estimate for Tesla"
    w.facts["initial"] = (int(m.group(1).replace(",", "")), int(m.group(2).replace(",", "")))
    t = w.post("/sell/instant-offer/details/",
               {"mileage": "38000", "zip": "98101", "exterior_color": "White",
                "keys": "1", "original_owner": "Yes"}, fills=4)
    m = re.search(r"Your Instant Offer estimate</h2>\s*<p class=\"value-range\">\$([\d,]+) - \$([\d,]+)", w.page_html)
    assert m, "no final offer for Tesla"
    w.facts["offer"] = (int(m.group(1).replace(",", "")), int(m.group(2).replace(",", "")))
    read(w.page_text, "Offer request saved", "offer saved for logged-in bob")
    t = w.nav("/profile/your-garage/")
    m = re.search(r"Instant Offer requests</h2>(.*?)</section>", w.page_html, re.S)
    assert m and "Tesla" in m.group(1), "Tesla offer missing from garage"
    w.facts["offers_area"] = True
    # remove one saved car
    victim = saved[0][0]
    w.post(f"/save/{victim}/", {"next": "/profile/your-garage/"})
    t = w.nav("/profile/your-garage/")
    assert f"saved-{victim}" not in w.page_html, "remove failed"
    remaining = re.findall(r'id="saved-([0-9a-f-]{36})"', w.page_html)
    assert remaining, "no saved cars remain"
    w.facts["remaining"] = remaining
    w.compose()


def walk_15(w):
    """T15 — certified Ford Escapes; Shorewood listing price history; save as dana."""
    w.nav("/", count=False)
    t = w.search(stock="cpo", make="ford", model="ford-escape")
    w.facts["count"] = serp_count(t)
    assert w.facts["count"] >= 2, "fewer than 2 certified Escapes"
    # find the Shorewood listing card
    shorewood = None
    all_cards = re.findall(r'id="vehicle-card-([0-9a-f-]{36})"', w.page_html)
    for pos, lid in enumerate(all_cards):
        seg = card_segment(w.page_html, all_cards, pos)
        if "Shorewood, IL" in seg:
            shorewood = lid
            w.facts["shorewood_title"] = re.search(r'card-title">\s*<a href="[^"]*">([^<]+)</a>', seg).group(1)
            w.facts["shorewood_price"] = re.search(r'class="price">(\$[\d,]+)', seg).group(1)
            break
    assert shorewood, "no Shorewood Escape on the SERP"
    t = w.click(f"/vehicledetail/{shorewood}/")
    m = re.search(r'class="mileage">([\d,]+) mi', w.page_html)
    assert m, "no mileage on Shorewood listing"
    w.facts["mileage"] = m.group(1)
    m = re.search(r'badge badge-[a-z-]+">(Great Deal|Good Deal|Fair Deal)<', w.page_html)
    w.facts["badge"] = m.group(1) if m else None
    m = re.search(r"The good deal range for this vehicle is between \$([\d,]+) and \$([\d,]+)", t)
    assert m, "no good-deal range"
    w.facts["good_deal"] = (m.group(1), m.group(2))
    rows = re.findall(r"<tr><td>(\d\d/\d\d/\d\d)</td>\s*<td>([^<]*)</td>\s*<td>(\$[\d,]+)</td></tr>", w.page_html)
    assert rows, "no price history rows"
    w.facts["history"] = rows
    m = re.search(r"VIN: ([A-Z0-9]+) / Stock #: ([A-Z0-9]+)", t)
    assert m, "no VIN/stock"
    w.facts["vin"] = (m.group(1), m.group(2))
    # open the other Escape listing too
    w.back()
    other = None
    for pos, lid in enumerate(all_cards):
        if lid != shorewood:
            seg = card_segment(w.page_html, all_cards, pos)
            if "Auburn, WA" in seg:
                other = lid
                w.facts["other_price"] = re.search(r'class="price">(\$[\d,]+)', seg).group(1)
                break
    assert other, "no other Escape listing"
    t = w.click(f"/vehicledetail/{other}/")
    read(w.page_text, "Features", "other Escape opens")
    w.facts["cheaper"] = "Shorewood" if int(w.facts["shorewood_price"].replace("$", "").replace(",", "")) < int(w.facts["other_price"].replace("$", "").replace(",", "")) else "Auburn"
    # back to the Shorewood listing, its dealer page, then save
    w.back()
    t = w.click(f"/vehicledetail/{shorewood}/")
    m = re.search(r'href="(/dealers/\d+/[a-z0-9_-]+)/"', w.page_html)
    assert m, "no dealer link on Shorewood listing"
    t = w.click(m.group(1) + "/")
    m = re.search(r"<tr><th>Monday</th><td>([^<]+)</td>", w.page_html)
    assert m, "no Monday hours on Shorewood dealer page"
    w.facts["monday_hours"] = m.group(1)
    w.back()
    w.post(f"/save/{shorewood}/", {"next": f"/vehicledetail/{shorewood}/"})
    w.login("dana.k@test.com", "TestPass123!")
    w.post(f"/save/{shorewood}/", {"next": f"/vehicledetail/{shorewood}/"})
    t = w.nav("/profile/your-garage/")
    i = w.page_html.find(f"saved-{shorewood}")
    assert i > 0, "Shorewood Escape missing from garage"
    m = re.search(rf'id="saved-{shorewood}".*?card-title">\s*<a href="[^"]*">([^<]+)</a>.*?class="price">(\$[\d,]+)', w.page_html, re.S)
    assert m, "saved car title/price missing"
    w.facts["garage"] = (m.group(1), m.group(2))
    w.compose()


def walk_16(w):
    """T16 — Auburn Chevrolet inventory via directory make filter; save as carol."""
    t = w.nav("/dealers/")
    w.fill("make", "Chevrolet")
    t = w.nav("/dealers/?make=Chevrolet")
    m = re.search(r'href="(/dealers/\d+/auburn-chevrolet/?)?"', w.page_html) or \
        re.search(r"Auburn Chevrolet.*?href=\"(/dealers/\d+/[a-z0-9-]+)/inventory/\"", w.page_html, re.S)
    assert m, "Auburn Chevrolet not found"
    dealer_path = m.group(1).rstrip("/")
    t = w.click(dealer_path.rstrip("/") + "/inventory/")
    m = re.search(r"(\d+) cars listed at this dealership", t)
    assert m, "no inventory count"
    w.facts["count"] = int(m.group(1))
    assert w.facts["count"] > 0
    w.fill("stock_type", "used")
    t = w.nav(dealer_path.rstrip("/") + "/inventory/?stock_type=used")
    m = re.search(r"(\d+) cars listed at this dealership", t)
    assert m, "no used count"
    w.facts["used_count"] = int(m.group(1))
    assert w.facts["used_count"] > 0
    cards = re.findall(r'id="vehicle-card-([0-9a-f-]{36})"', w.page_html)
    assert cards, "no used cards"
    cheapest, most_exp = cards[0], cards[-1]
    w.facts["cheapest"] = (card_field(w.page_html, cheapest, "title", r'card-title">\s*<a href="[^"]*">([^<]+)</a>'),
                           card_field(w.page_html, cheapest, "price", r'class="price">(\$[\d,]+)'))
    w.facts["most_exp"] = (card_field(w.page_html, most_exp, "title", r'card-title">\s*<a href="[^"]*">([^<]+)</a>'),
                           card_field(w.page_html, most_exp, "price", r'class="price">(\$[\d,]+)'))
    t = w.click(f"/vehicledetail/{cheapest}/")
    m = re.search(r'class="mileage">([\d,]+) mi', w.page_html)
    assert m, "no mileage on cheapest"
    w.facts["mileage"] = m.group(1)
    m = re.search(r'badge badge-[a-z-]+">(Great Deal|Good Deal|Fair Deal)<', w.page_html)
    w.facts["badge"] = m.group(1) if m else None
    m = re.search(r"<li>([A-Za-z ]+) exterior color</li>", w.page_html)
    assert m, "no exterior color"
    w.facts["color"] = m.group(1).strip()
    m = re.search(r'href="(/dealers/\d+/[a-z0-9_-]+)/"', w.page_html)
    assert m, "no dealer link"
    t = w.click(m.group(1) + "/")
    m = re.search(r"<h2>About [^<]*</h2>\s*<p>([^<]{20,})", w.page_html)
    assert m, "no About text on dealer page"
    w.facts["about"] = " ".join(m.group(1).split())[:120]
    m = re.search(r"<tr><th>Monday</th><td>([^<]+)</td>", w.page_html)
    assert m, "no Monday hours"
    w.facts["monday_hours"] = m.group(1)
    w.back()
    w.post(f"/save/{cheapest}/", {"next": f"/vehicledetail/{cheapest}/"})
    w.login("carol.d@test.com", "TestPass123!")
    w.post(f"/save/{cheapest}/", {"next": f"/vehicledetail/{cheapest}/"})
    t = w.nav("/profile/your-garage/")
    i = w.page_html.find(f"saved-{cheapest}")
    assert i > 0, "saved car missing from garage"
    w.facts["garage"] = True
    w.compose()


def walk_17(w):
    """T17 — 2025 Civic research page; save search as alice; Accord compare."""
    t = w.nav("/authn/login")
    w.login("alice.j@test.com", "TestPass123!")
    read(w.page_text, "Your Garage", "alice garage")
    w.nav("/")
    t = w.nav("/research/")
    m = re.search(r'href="(/research/honda-civic-2025/)"', w.page_html)
    assert m, "2025 Civic research page not listed"
    t = w.click(m.group(1))
    m = re.search(r"Shop options from \$([\d,]+)", t)
    assert m, "no starting price"
    w.facts["start"] = int(m.group(1).replace(",", ""))
    trims = re.findall(r'<tr>\s*<td>([^<]+)</td>\s*<td>(\$[\d,]+)</td>\s*<td>([^<]*)</td>\s*<td>([^<]*)</td>', w.page_html)
    assert trims, "no trims"
    w.facts["trim_count"] = len(trims)
    w.facts["cheapest_trim"] = trims[0]
    m = re.search(r"(\d+)% of drivers recommend", t)
    assert m, "no recommend pct"
    w.facts["recommend"] = m.group(1)
    m = re.search(r"The good</h3><ul>(.*?)</ul>", w.page_html, re.S)
    assert m, "no good points"
    good = [x.strip() for x in re.findall(r"<li>([^<]+)</li>", m.group(1))]
    assert len(good) >= 2, "fewer than 2 good points"
    m = re.search(r"The bad</h3><ul>(.*?)</ul>", w.page_html, re.S)
    assert m, "no bad points"
    bad = [x.strip() for x in re.findall(r"<li>([^<]+)</li>", m.group(1))]
    assert len(bad) >= 2, "fewer than 2 bad points"
    w.facts["good"], w.facts["bad"] = good[:2], bad[:2]
    m = re.search(r'href="(/shopping/results/\?[^"]*)"', w.page_html)
    assert m, "no listings link"
    qs = html_mod.unescape(m.group(1))
    assert 'models%5B%5D=honda-civic' in qs or 'models[]=honda-civic' in qs, \
        "the listings link must emit models[] (filter round-trip)"
    t = w.click(qs)
    read(t, "results", "civic listings")
    t = w.filter(carry=dict(parse_qsl(qs.split("?", 1)[1])), list_price_max="30000")
    w.facts["count"] = serp_count(t)
    assert w.facts["count"] == 65, "expected 65 Civics under $30,000"
    titles = re.findall(r'card-title">\s*<a href="[^"]*">([^<]+)</a>', w.page_html)
    assert titles and all('Civic' in x for x in titles), \
        "the model filter must survive the price narrowing"
    read(w.page_html, "Name this search", "save-search form")
    w.post("/searches/save/", {"query_string": w.history[-1],
                               "name": "Civic research", "alert_frequency": "daily"}, fills=2)
    read(w.page_text, "Saved searches", "garage saved-searches")
    read(w.page_text, "Civic research", "saved search name")
    t = w.nav("/research/compare/")
    m = re.search(r'href="(/research/compare/[^"]*accord[^"]*/)"', w.page_html)
    assert m, "no Accord comparison listed"
    t = w.click(m.group(1))
    m = re.search(r"Starting MSRP</th>\s*<td>\$([\d,]+)</td>\s*<td>\$([\d,]+)</td>", w.page_html)
    assert m, "no starting MSRPs in Accord compare"
    w.facts["msrps"] = (m.group(1), m.group(2))
    w.compose()


def walk_18(w):
    """T18 — hybrids under $30k, cheapest; RAV4 vs CR-V compare; save as alice."""
    t = w.nav("/shopping/hybrid/")
    read(t, "Hybrid Cars for Sale", "hybrid browse page")
    m = re.search(r'href="(/shopping/results/\?fuel_slugs=hybrid)"', w.page_html)
    assert m, "no hybrid listings link"
    hyb_qs = m.group(1)
    t = w.click(hyb_qs)
    w.facts["count"] = serp_count(t)
    assert w.facts["count"] == 49, "expected 49 hybrid results"
    t = w.filter(carry={"fuel_slugs": "hybrid"}, list_price_max="30000")
    w.facts["under30k"] = serp_count(t)
    assert w.facts["under30k"] == 10, "expected 10 hybrids under $30,000"
    t = w.sort("list_price_asc", carry={"fuel_slugs": "hybrid", "list_price_max": "30000"})
    lid = first_card(w.page_html)
    w.facts["cheapest"] = (card_field(w.page_html, lid, "price", r'class="price">(\$[\d,]+)'),
                           card_field(w.page_html, lid, "mileage", r'class="mileage">([\d,]+) mi'),
                           card_field(w.page_html, lid, "seller", r'seller-name">([^<]+)'))
    t = w.click(f"/vehicledetail/{lid}/")
    m = re.search(r"Est\. payment \$(\d+)/mo", t)
    assert m, "no monthly payment"
    w.facts["monthly"] = int(m.group(1))
    m = re.search(r"based on ([\d.]+)% APR", t)
    assert m, "no APR"
    w.facts["apr"] = m.group(1)
    m = re.search(r"Seller's info ([A-Za-z0-9&'. -]+?) \d[\d,]* reviews", t)
    assert m, "no dealer name"
    w.facts["dealer"] = m.group(1).strip()
    # save, log in as alice, finish saving, report the garage
    w.post(f"/save/{lid}/", {"next": f"/vehicledetail/{lid}/"})
    read(w.page_text, "Password", "login page after save")
    w.login("alice.j@test.com", "TestPass123!")
    read(w.page_text, "♥ Save", "back on the hybrid listing")
    w.post(f"/save/{lid}/", {"next": f"/vehicledetail/{lid}/"})
    t = w.nav("/profile/your-garage/")
    i = w.page_html.find(f"saved-{lid}")
    assert i > 0, "saved hybrid missing from garage"
    w.facts["garage"] = True
    # compare RAV4 vs CR-V
    t = w.nav("/research/compare/")
    m = re.search(r'href="(/research/compare/honda-cr_v-vs-toyota-rav4/)"', w.page_html)
    assert m, "RAV4/CR-V compare not listed"
    t = w.click(m.group(1))
    m = re.search(r"Starting MSRP</th>\s*<td>\$([\d,]+)</td>\s*<td>\$([\d,]+)</td>", w.page_html)
    assert m, "no starting MSRPs"
    a_msrp, b_msrp = int(m.group(1).replace(",", "")), int(m.group(2).replace(",", ""))
    w.facts["msrps"] = (m.group(1), m.group(2))
    m = re.search(r"<h2>[^<]*Toyota RAV4[^<]*</h2>", w.page_html)
    first_is_rav4 = bool(m)
    w.facts["cheaper"] = ("RAV4" if first_is_rav4 else "CR-V") if a_msrp < b_msrp else ("CR-V" if first_is_rav4 else "RAV4")
    m = re.search(r"Horsepower</th>\s*<td>(\d+) hp</td>\s*<td>(\d+) hp</td>", w.page_html)
    assert m, "no horsepower row"
    w.facts["hp"] = (m.group(1), m.group(2))
    m = re.search(r"MPG</th>\s*<td>([^<]+)</td>\s*<td>([^<]+)</td>", w.page_html)
    assert m, "no MPG row"
    w.facts["mpg"] = (m.group(1), m.group(2))
    cheaper_slug = "toyota-rav4" if w.facts["cheaper"] == "RAV4" else "honda-cr_v"
    m = re.search(rf'href="(/research/{cheaper_slug}-\d+/)"', w.page_html)
    assert m, "no research link for the cheaper model"
    t = w.click(m.group(1))
    m = re.search(r"([\d.]+) / 5 Based on (\d+) reviews", t)
    assert m, "no consumer rating on research page"
    w.facts["consumer_rating"] = m.group(1)
    m = re.search(r"Safety rating (\d)/5", t)
    assert m, "no safety rating"
    w.facts["safety"] = m.group(1)
    w.compose()


WALKS = {0: walk_0, 1: walk_1, 2: walk_2, 3: walk_3, 4: walk_4, 5: walk_5, 6: walk_6, 7: walk_7, 8: walk_8, 9: walk_9, 10: walk_10, 11: walk_11, 12: walk_12, 13: walk_13, 14: walk_14, 15: walk_15, 16: walk_16, 17: walk_17, 18: walk_18}


LEAK_RE = re.compile(r"\$[\d,]+|\d+\.\d+|\d{4}-\d\d-\d\d|\d\d/\d\d/\d\d|\d{4,}")


def fact_strings(value):
    """Every answer-ish string inside a walk's recorded facts."""
    if isinstance(value, dict):
        for v in value.values():
            yield from fact_strings(v)
    elif isinstance(value, (list, tuple)):
        for v in value:
            yield from fact_strings(v)
    else:
        s = str(value)
        if len(s) >= 3:
            yield s


def check_shape(row, failures):
    keys = set(row.keys())
    # reviewer contract: the 5 contributor keys + the reviewer's grading keys
    # (verifier_path + judge_rubric). An answer key is never allowed.
    if keys != {"web_name", "id", "ques", "web", "upstream_url",
                "verifier_path", "judge_rubric"}:
        failures.append(f"{row['id']}: task keys {sorted(keys)} != the 7-key contract "
                        "(5 contributor keys + verifier_path + judge_rubric; no answer key)")
    if "answer" in keys:
        failures.append(f"{row['id']}: answer key must never exist")
    words = len(row["ques"].split())
    if words > 100:
        failures.append(f"{row['id']}: {words} words (max 100)")
    if re.search(r"\b(step|click) (one|1|two|2|three|3)\b", row["ques"], re.I):
        failures.append(f"{row['id']}: mechanical step-by-step phrasing")
    if "http" in row["ques"] or "/vehicledetail/" in row["ques"] or "/dealers/" in row["ques"]:
        failures.append(f"{row['id']}: direct URL in task text")


def check_leakage(row, facts, failures):
    """No answer value (price/range/rating/date/4+ digit number) from the
    driven walk may appear in the task text. Subject names (the dealer or
    account a task is about) are anchors, not leaks."""
    text = " ".join(row["ques"].split())
    for v in fact_strings(facts):
        if LEAK_RE.search(v) and v in text:
            failures.append(f"{row['id']}: answer value {v!r} leaked into the task text")


def run_audit():
    failures = []
    results = []
    for row in TASKS:
        check_shape(row, failures)
        tid = int(row["id"].split("--")[1])
        walk_fn = WALKS.get(tid)
        if not walk_fn:
            failures.append(f"{row['id']}: NO WALK — every task needs a measured walk")
            continue
        cars_mod.app.config.update(TESTING=True)
        client = cars_mod.app.test_client()
        w = Walk(client, row["id"])
        try:
            walk_fn(w)
            check_leakage(row, w.facts, failures)
            results.append((row["id"], w.atomic, len(w.log)))
            status = "OK " if w.atomic >= 15 else "THIN"
            print(f"[{status}] {row['id']}: atomic={w.atomic}")
            if w.atomic < 15:
                failures.append(f"{row['id']}: measured only {w.atomic} atomic steps (need >= 15)")
        except AssertionError as e:
            failures.append(f"{row['id']}: {e}")
            print(f"[FAIL] {row['id']}: {e}")
    print(f"== audited {len(results)} tasks, {len(failures)} failures")
    if failures:
        for f in failures:
            print("  -", f)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(run_audit())
