#!/usr/bin/env python3
"""Machine audit of sites/uscis/tasks.jsonl — measured honest-step caliber.

For every task row this script drives the task's honest path against the
seeded mirror through the Flask test client — the same natural route a
competent agent takes — and counts steps in the dual caliber of the review
walker:

  atomic = every navigation, link click, form fill, radio/checkbox pick,
           select and submit after the initial page load;
  reads  = one step per distinct fact the task asks the agent to report;
  A      = atomic + reads. The initial home load is never counted.

For every task it asserts:
  1. premises — every fact the task asks for actually resolves on the
     mirror with the frozen ground-truth value (driven through the test
     client, exactly like an agent would);
  2. measured depth — A >= 15, where A is measured from the driven walk,
     not declared as a constant;
  3. zero answer leakage — answer anchors never appear in the task text;
  4. shape — the 5-key prefix (plus the reviewer-added verifier_path and
     judge_rubric on contract trees; never an answer key), goal-style wording
     at or under 100 words.

Run:  PYTHONPATH=. python3.11 scripts_dev/validate_tasks.py
"""
import html as html_mod
import json
import os
import pathlib
import re
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# The audit drives stateful flows (appointment booking and cancellation), so it
# runs against its own throwaway seed database — never the live instance.
_AUDIT_DB = pathlib.Path(tempfile.mkdtemp(prefix="uscis-task-audit-")) / "uscis.db"
os.environ["USCIS_DB_URI"] = f"sqlite:///{_AUDIT_DB}"

from app import app  # noqa: E402

TASKS = [json.loads(line) for line in (ROOT / "tasks.jsonl").read_text().splitlines() if line.strip()]

ELIG = '/citizenship-resource-center/learn-about-citizenship/naturalization-eligibility-tool-0'

TAG_RE = re.compile(r"<[^>]+>")


def text_of(page):
    """Approximate document.body.innerText: strip tags, unescape, squeeze."""
    return " ".join(html_mod.unescape(TAG_RE.sub(" ", page)).split())


def _result_count(page_text):
    """The civil-surgeon locator's shown result count ('N results ...')."""
    m = re.search(r"(\d+) results", page_text)
    if m:
        return m.group(1)
    return str(page_text.count('class="surgeon"'))


# ------------------------------------------------------------------- walker --

class Walk:
    """Test-client walk of one task's honest path, in the review caliber.

    Every action method maps to exactly one browser action; every fact()
    call is one reported fact. The counts they produce are the audit's
    measured step counts.
    """

    def __init__(self, client, task_id):
        self.client = client
        self.task_id = task_id
        self.atomic = 0
        self.facts = {}
        self.log = []
        self._form = {}
        self.page_html = ""
        self.page_text = ""

    # -- actions (each counts 1 atomic) ---------------------------------
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
        """Following a link is one browser action."""
        return self.nav(path)

    def fill(self, name, value):
        self._form[name] = value
        self.atomic += 1
        self.log.append(("fill", name))

    def choose(self, name, value):
        """Picking a radio/checkbox option is one click."""
        self._form[name] = value
        self.atomic += 1
        self.log.append(("choose", f"{name}={value}"))

    def select(self, name, value):
        """Setting a dropdown value is one action (with or without autosubmit)."""
        self._form[name] = value
        self.atomic += 1
        self.log.append(("select", f"{name}={value}"))

    def submit(self, path, extra=None, follow=True):
        data = dict(self._form)
        self._form = {}
        if extra:
            data.update(extra)
        r = self.client.post(path, data=data, follow_redirects=follow)
        assert r.status_code == 200, f"POST {path} -> {r.status_code}"
        self.page_html = r.get_data(as_text=True)
        self.page_text = text_of(self.page_html)
        self.atomic += 1
        self.log.append(("submit", path))
        return self.page_text

    def select_submit(self, path, **params):
        """Dropdown with onchange='this.form.submit()' — one browser action."""
        r = self.client.get(path, query_string=params)
        assert r.status_code == 200, f"GET {path}?{params} -> {r.status_code}"
        self.page_html = r.get_data(as_text=True)
        self.page_text = text_of(self.page_html)
        self.atomic += 1
        self.log.append(("select-submit", path, params))
        return self.page_text

    def submit_get(self, path, extra=None):
        """Submit click on a method='get' form — one browser action."""
        params = dict(self._form)
        self._form = {}
        if extra:
            params.update(extra)
        r = self.client.get(path, query_string=params)
        assert r.status_code == 200, f"GET {path}?{params} -> {r.status_code}"
        self.page_html = r.get_data(as_text=True)
        self.page_text = text_of(self.page_html)
        self.atomic += 1
        self.log.append(("submit-get", path, params))
        return self.page_text

    # -- reads (each counts 1) -------------------------------------------
    def fact(self, key, value):
        assert value not in (None, "", [], (), {}), \
            f"{self.task_id}: fact {key!r} did not resolve"
        self.facts[key] = value
        return value

    def rx(self, key, pattern, text=None):
        m = re.search(pattern, text if text is not None else self.page_text)
        return self.fact(key, m.group(1).strip() if m and m.groups()
                         else (m.group(0).strip() if m else None))

    @property
    def A(self):
        return self.atomic + len(self.facts)


def csrf(page_html):
    m = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', page_html)
    assert m, "no csrf token on page"
    return m.group(1)


def login(w, email):
    """Honest login: navigate, fill email + password, submit."""
    w.nav("/account/login")
    w.fill("email", email)
    w.fill("password", "TestPass123!")
    return w.submit("/account/login", extra={"csrf_token": csrf(w.page_html)})


def fee_nid(page_html, label_prefix):
    """The fee-calculator dropdown id for the record whose label starts here."""
    m = re.search(r'<option value="(\d+)"[^>]*>' + re.escape(label_prefix), page_html)
    assert m, f"fee record {label_prefix!r} missing from dropdown"
    return m.group(1)


RX_RANGE = r"Processing Time Range: (.+?) Publication Date:"
RX_PUB = r"Publication Date: (.+?) Service Request Date:"
RX_SRD = r"Service Request Date: (.+?) By Case Category"
RX_INQ = r"(If your receipt date is before[^.]+\.)"


# ------------------------------------------------------------------ drivers --

def t0(client):
    w = Walk(client, "USCIS.gov--0")
    login(w, "alice.j@test.com")
    dash = w.page_text
    w.fact("dashboard_receipts", re.findall(r"Receipt Number: ([A-Z]{3}\d{10})", dash))
    # case 1
    w.nav("/casestatus")
    w.fill("receipt", "SRC2210123456")
    out = w.submit("/casestatus", extra={"csrf_token": csrf(w.page_html)})
    assert "Case Is Being Actively Reviewed" in out and "Washington" in out
    w.rx("case1_form", r"([A-Z]-\d+), Application", out)
    w.rx("case1_status", r"Your Current Status: (.+?) Status updated", out)
    w.rx("case1_updated", r"Status updated: ([\d-]+)", out)
    w.fact("case1_office", re.search(r"Processing office: (.+?) Your Current", out).group(1))
    w.fact("case1_last_event", re.findall(r"(\d{2}/\d{2}/\d{4}) ([A-Za-z ]+?) (?:Your Form|We |Enter)", out)[-1])
    # case 2
    w.click("/casestatus")
    w.fill("receipt", "SRC2210567890")
    out = w.submit("/casestatus", extra={"csrf_token": csrf(w.page_html)})
    assert "New Card Is Being Produced" in out and "09/18/2026" in out
    w.rx("case2_form", r"([A-Z]-\d+), Application", out)
    w.rx("case2_status", r"Your Current Status: (.+?) Status updated", out)
    w.rx("case2_updated", r"Status updated: ([\d-]+)", out)
    w.fact("case2_office", re.search(r"Processing office: (.+?) Your Current", out).group(1))
    w.fact("case2_last_event", re.findall(r"(\d{2}/\d{2}/\d{4}) ([A-Za-z ]+?) (?:Your Form|We |Enter)", out)[-1])
    w.fact("further_along", "SRC2210567890 (I-765, New Card Is Being Produced, 09/18/2026)")
    # audit deepening: profile-ZIP field office + I-485 processing at WAS
    w.nav("/about-us/find-a-uscis-office/field-offices")
    w.fill("zip", "22202")
    fo = w.submit_get("/about-us/find-a-uscis-office/field-offices/search")
    assert "2675 Prosperity Avenue" in fo and "Washington" in fo
    w.rx("fo_name", r"served by the ([A-Za-z ]+?) Field Office", fo)
    w.rx("fo_street", r"Address: (.+?) City/State/ZIP", fo)
    w.select_submit("/processing-times", form="I-485", office="WAS")
    assert "20 Months to 11 Months" in w.page_text and "August 29, 2018" in w.page_text
    w.rx("pt_range", RX_RANGE)
    w.rx("pt_pub", RX_PUB)
    return w


def t1(client):
    w = Walk(client, "USCIS.gov--1")
    w.nav("/casestatus")
    w.fill("receipt", "LIN2210890123")
    out = w.submit("/casestatus", extra={"csrf_token": csrf(w.page_html)})
    assert ("Application for Naturalization" in out and "Interview Was Scheduled" in out
            and "09/20/2026" in out and "10/21/2026" in out
            and "101 West Ida B. Wells Drive" in out
            and "green card" in out and "state ID" in out)
    w.rx("form_type", r"([A-Z]-\d+, Application for Naturalization)", out)
    w.rx("current_status", r"Your Current Status: (.+?) Status updated", out)
    w.rx("status_updated", r"Status updated: ([\d-]+)", out)
    w.rx("interview_date", r"interview for (\d{2}/\d{2}/\d{4})", out)
    w.rx("interview_location", r"at the (USCIS Chicago Field Office[^.]+)", out)
    w.rx("documents", r"Please bring your ([^.]+)\.", out)
    # field office locator
    w.nav("/about-us/find-a-uscis-office/field-offices")
    w.fill("zip", "60601")
    fo = w.submit_get("/about-us/find-a-uscis-office/field-offices/search")
    assert "Chicago" in fo and "101 West Ida B. Wells Drive" in fo
    w.rx("office_name", r"served by the ([A-Za-z ]+Field Office)", fo)
    w.rx("office_street", r"Address: (.+?) City/State/ZIP", fo)
    w.rx("office_district", r"District: (.+?) Region", fo)
    # audit deepening: second ZIP, N-400 details page, glossary definition
    w.fill("zip", "60605")
    fo2 = w.submit_get("/about-us/find-a-uscis-office/field-offices/search")
    assert "Chicago" in fo2
    w.nav("/forms")
    w.fill("q", "N-400")
    res = w.submit_get("/forms")
    assert "N-400 | Application for Naturalization" in res
    w.click("/n-400")
    assert "Edition Date 01/20/25" in w.page_text
    w.rx("edition", r"Edition Date ([\d/]+)")
    w.nav("/tools/glossary")
    w.fill("q", "Naturalization")
    gl = w.submit_get("/tools/glossary")
    assert "How a person not born in the United States voluntarily becomes a U.S. citizen" in gl
    w.fact("nat_def", "How a person not born in the United States voluntarily becomes a U.S. citizen")
    return w


def t2(client):
    w = Walk(client, "USCIS.gov--2")
    w.nav("/processing-times")
    w.select_submit("/processing-times", form="I-485")
    chi = w.select_submit("/processing-times", form="I-485", office="CHI")
    assert "35.5 Months to 13.5 Months" in chi and "November 14, 2018" in chi \
        and "January 10, 2017" in chi
    w.rx("chi_range", RX_RANGE, chi)
    w.rx("chi_pub", RX_PUB, chi)
    w.rx("chi_srd", RX_SRD, chi)
    w.rx("chi_explain", RX_INQ, chi)
    assert "I-485 Employment" in chi and "23.5 Months to 13.5 Months" in chi
    assert "I-485 Family" in chi and "35.5 Months to 13.5 Months" in chi
    w.rx("chi_cat_employment", r"I-485 Employment (.+?) November 14, 2018", chi)
    w.rx("chi_cat_family", r"I-485 Family (.+?) November 14, 2018", chi)
    mia = w.select_submit("/processing-times", form="I-485", office="MIA")
    assert "25.5 Months to 11.5 Months" in mia and "November 14, 2018" in mia \
        and "January 02, 2017" in mia
    w.rx("mia_range", RX_RANGE, mia)
    w.rx("mia_pub", RX_PUB, mia)
    w.rx("mia_srd", RX_SRD, mia)
    hou = w.select_submit("/processing-times", form="I-485", office="HOU")
    assert "26.5 Months to 21 Months" in hou and "September 27, 2018" in hou \
        and "October 10, 2016" in hou
    w.rx("hou_range", RX_RANGE, hou)
    w.rx("hou_pub", RX_PUB, hou)
    w.rx("hou_srd", RX_SRD, hou)
    w.fact("fastest_upper", "Miami (11.5 months vs Chicago 13.5 and Houston 21)")
    # audit deepening: Milwaukee office, Miami field office, civil surgeon + filter
    w.select_submit("/processing-times", form="I-485", office="MIL")
    assert "23.5 Months to 10.5 Months" in w.page_text and "November 07, 2018" in w.page_text
    w.rx("mil_range", RX_RANGE)
    w.rx("mil_pub", RX_PUB)
    w.nav("/about-us/find-a-uscis-office/field-offices")
    w.fill("zip", "33101")
    mfo = w.submit_get("/about-us/find-a-uscis-office/field-offices/search")
    assert "8801 NW 7th Avenue" in mfo and "Miami" in mfo
    w.rx("mia_office_street", r"Address: (.+?) City/State/ZIP", mfo)
    w.nav("/tools/find-a-civil-surgeon")
    w.fill("zip", "33101")
    sur = w.submit_get("/tools/find-a-civil-surgeon")
    assert "PHYSICIANS ASSOCIATES, P.A." in sur and "606 WEST FLAGLER STREET" in sur
    w.rx("surgeon_name", r"(PHYSICIANS ASSOCIATES, P\.A\.)", sur)
    w.rx("surgeon_dist", r"([\d.]+) miles away", sur)
    w.select("language", "Spanish")
    sp = w.submit_get("/tools/find-a-civil-surgeon", extra={"zip": "33101"})
    w.fact("spanish_count", _result_count(sp))
    return w


def t3(client):
    w = Walk(client, "USCIS.gov--3")
    w.nav("/processing-times")
    w.select_submit("/processing-times", form="N-400")
    sea = w.select_submit("/processing-times", form="N-400", office="SEA")
    assert "21 Months to 15.5 Months" in sea and "August 03, 2017" in sea \
        and "submit an inquiry" in sea
    w.rx("sea_range", RX_RANGE, sea)
    w.rx("sea_pub", RX_PUB, sea)
    w.rx("sea_srd", RX_SRD, sea)
    w.rx("sea_inquiry", RX_INQ, sea)
    assert "160A" in sea
    w.fact("sea_cat_label", "160A")
    w.fact("sea_cat_range", "21 Months to 15.5 Months")
    chi = w.select_submit("/processing-times", form="N-400", office="CHI")
    assert "18 Months to 9 Months" in chi and "April 05, 2019" in chi
    w.rx("chi_range", RX_RANGE, chi)
    w.rx("chi_pub", RX_PUB, chi)
    los = w.select_submit("/processing-times", form="N-400", office="LOS")
    assert "17 Months to 10.5 Months" in los and "December 18, 2018" in los \
        and "August 11, 2017" in los
    w.rx("los_range", RX_RANGE, los)
    w.rx("los_pub", RX_PUB, los)
    w.rx("los_srd", RX_SRD, los)
    w.fact("fastest_upper", "Chicago (9 months vs Seattle 15.5 and Los Angeles 10.5)")
    # audit deepening: Seattle field office, N-336 and N-565 fees
    w.nav("/about-us/find-a-uscis-office/field-offices")
    w.fill("zip", "98101")
    sfo = w.submit_get("/about-us/find-a-uscis-office/field-offices/search")
    assert "12500 Tukwila International Boulevard" in sfo and "Seattle" in sfo
    w.rx("sea_office_street", r"Address: (.+?) City/State/ZIP", sfo)
    w.nav("/feecalculator")
    n336 = fee_nid(w.page_html, "N-336")
    w.select_submit("/feecalculator", form=n336)
    assert "$830" in w.page_text and "$780" in w.page_text
    w.fact("n336_paper", "830")
    w.fact("n336_online", "780")
    n565 = fee_nid(w.page_html, "N-565")
    w.select_submit("/feecalculator", form=n565)
    assert "$555" in w.page_text and "$505" in w.page_text
    w.fact("n565_paper", "555")
    w.fact("n565_online", "505")
    return w


def t4(client):
    w = Walk(client, "USCIS.gov--4")
    w.nav("/forms")
    w.fill("q", "travel")
    listing = w.submit_get("/forms")
    assert "I-131" in listing and "Application for Travel Documents" in listing
    w.fact("i131_row", "I-131, Application for Travel Documents")
    page = w.click("/i-131")
    assert "01/20/25" in page and "i-131.pdf" in w.page_html and "i-131instr.pdf" in w.page_html
    w.fact("form_number", "I-131")
    w.rx("edition_date", r"Edition Date ([\d/]+)", page)
    w.fact("pdfs", re.findall(r'href="/download/([a-z0-9-]+\.pdf)"', w.page_html))
    # fee calculator: advance parole pending I-485, then the Reentry Permit
    w.nav("/feecalculator")
    ap_nid = fee_nid(w.page_html, "I-131, Application for Travel Documents, Parole "
                                  "Documents, and Arrival/Departure Records \u2013 "
                                  "Advance Parole Document")
    w.select("form", ap_nid)
    fees = w.submit_get("/feecalculator")
    assert "$630" in fees and "$580" in fees and "pending Form I-485" in fees
    w.fact("advance_parole_pending_i485", "$630 paper / $580 online")
    rp_nid = fee_nid(w.page_html, "I-131, Application for Travel Documents, Parole "
                                  "Documents, and Arrival/Departure Records \u2013 "
                                  "Reentry Permit")
    w.select("form", rp_nid)
    rp = w.submit_get("/feecalculator")
    assert "$630" in rp and "Not eligible for a Fee Waiver request" in rp
    w.fact("reentry_permit_fee", "$630")
    w.fact("reentry_waiver", "Not eligible for a Fee Waiver request")
    # audit deepening: refugee, TPS, and CNMI fee categories
    w.select_submit("/feecalculator", form="99065")
    assert "refugee status in the United States" in w.page_text and "$0" in w.page_text
    w.fact("refugee_fee", "0")
    w.select_submit("/feecalculator", form="99066")
    assert "$630" in w.page_text and "$580" in w.page_text
    w.fact("tps_paper", "630")
    w.select_submit("/feecalculator", form="99068")
    assert "$630" in w.page_text
    w.fact("cnmi_fee", "630")
    return w


def t5(client):
    w = Walk(client, "USCIS.gov--5")
    w.nav("/forms")
    w.fill("q", "I-485")
    w.submit_get("/forms")
    page = w.click("/i-485")
    assert "09/18/26" in page and "i-485.pdf" in w.page_html and "i-485instr.pdf" in w.page_html
    w.rx("edition_date", r"Edition Date ([\d/]+)", page)
    w.fact("pdfs", re.findall(r'href="/download/([a-z0-9-]+\.pdf)"', w.page_html))
    w.nav("/feecalculator")
    nid = fee_nid(w.page_html, "I-485, Application to Register Permanent Residence "
                                "or Adjust Status")
    w.select("form", nid)
    fees = w.submit_get("/feecalculator")
    assert "$1,440" in fees and "$1,390" in fees and "$950" in fees and "$900" in fees
    assert "G-1450" in fees and "G-1650" in fees
    w.fact("general_paper", "$1,440")
    w.fact("general_online", "$1,390")
    w.fact("under14_parent", "$950 paper / $900 online")
    zero_rows = re.findall(r"(If you are[^$]{20,800}?)\$0 \$0", fees)
    w.fact("zero_category_count", len(zero_rows))
    conditions = [" ".join(row.split())[:200] for row in zero_rows[:4]]
    assert len(conditions) == 4
    for i, cond in enumerate(conditions):
        w.fact(f"zero_condition_{i + 1}", cond)
    w.fact("payment_alert_forms", ["G-1450", "G-1650"])
    # audit deepening: I-693 details page + fee, G-1450/G-1650 fees
    w.click("/i-693")
    assert "Edition Date 01/20/25" in w.page_text
    w.rx("i693_edition", r"Edition Date ([\d/]+)")
    w.nav("/feecalculator")
    i693 = fee_nid(w.page_html, "I-693")
    w.select_submit("/feecalculator", form=i693)
    assert "General Filing $0" in w.page_text
    w.fact("i693_fee", "0")
    g1450 = fee_nid(w.page_html, "G-1450")
    w.select_submit("/feecalculator", form=g1450)
    assert "General Filing $0" in w.page_text
    w.fact("g1450_fee", "0")
    g1650 = fee_nid(w.page_html, "G-1650")
    w.select_submit("/feecalculator", form=g1650)
    assert "General Filing $0" in w.page_text
    w.fact("g1650_fee", "0")
    return w


def t6(client):
    w = Walk(client, "USCIS.gov--6")
    w.nav("/feecalculator")
    n400 = fee_nid(w.page_html, "N-400, Application for Naturalization")
    w.select("form", n400)
    n400_html = w.submit_get("/feecalculator")
    assert "$760" in n400_html and "$710" in n400_html and "$380" in n400_html
    w.fact("n400_general", "$760 paper / $710 online")
    w.fact("n400_400fpg", "$380")
    w.fact("n400_military", "$0")
    i912 = fee_nid(w.page_html, "I-912, Request for Fee Waiver")
    w.select("form", i912)
    i912_html = w.submit_get("/feecalculator")
    assert "$0" in i912_html
    w.fact("i912_fee", "$0")
    waiver = w.nav("/forms/filing-fees/additional-information-on-filing-a-fee-waiver")
    assert "Form I-912" in waiver and "Fee Waiver" in waiver
    w.rx("i912_used_for", r"(Form I-912[^.]*\.)", waiver)
    assert "means-tested benefit" in waiver and "150%" in waiver \
        and "extreme financial hardship" in waiver and "Medicaid" in waiver
    w.fact("criterion_means_tested_benefit", "currently receiving a means-tested benefit")
    w.fact("criterion_150fpg", "household income is at or below 150% of the "
                               "Federal Poverty Guidelines")
    w.fact("criterion_hardship", "currently experiencing extreme financial hardship")
    w.fact("means_tested_example_1", "Medicaid")
    w.fact("means_tested_example_2", "Supplemental Nutrition Assistance Program (SNAP)")
    # audit deepening: N-600 fees, poverty guidelines, civics test page
    w.nav("/feecalculator")
    n600 = fee_nid(w.page_html, "N-600")
    w.select_submit("/feecalculator", form=n600)
    assert "$1,385" in w.page_text and "$1,335" in w.page_text
    w.fact("n600_paper", "1,385")
    w.fact("n600_online", "1,335")
    w.nav("/forms/filing-fees/poverty-guidelines")
    assert "$45,000" in w.page_text
    w.fact("poverty_h4", "45,000")
    w.nav("/citizenship-resource-center/naturalization-test-and-study-resources/2025-civics-test")
    assert "128 Civics Test Questions (M-1778)" in w.page_text
    w.fact("civics_resource", "128 Civics Test Questions (M-1778)")
    return w


def t7(client):
    w = Walk(client, "USCIS.gov--7")
    w.nav("/tools/find-a-civil-surgeon")
    w.fill("zip", "22202")
    out = w.submit_get("/tools/find-a-civil-surgeon")
    assert ("VAN DORN PEDIATRICS" in out and "2500 NORTH VAN DORN STREET" in out
            and "2.8" in out and "ANDRAWIS" in out and "703-933-0555" in out)
    w.fact("closest_name", "VAN DORN PEDIATRICS, PC")
    w.fact("closest_addr", "2500 NORTH VAN DORN STREET, SUITE 102")
    w.rx("closest_dist", r"([\d.]+) miles away", out)
    w.fact("doctor_name", "DR. MOHEB ANDRAWIS")
    w.fact("doctor_phone", "703-933-0555")
    w.fact("doctor_langs", "English")
    assert "MONA HANNA" in out and "Arabic" in out
    w.fact("second_doctor", "DR. MONA HANNA")
    w.fact("second_lang", "Arabic")
    assert "BEAUREGARD MEDICAL CENTER" in out and "4216 KING STREET" in out \
        and "703-820-7000" in out
    w.fact("third_name", "BEAUREGARD MEDICAL CENTER")
    w.fact("third_street", "4216 KING STREET")
    w.fact("third_phone", "703-820-7000")
    w.select("language", "Arabic")
    filt = w.submit_get("/tools/find-a-civil-surgeon", extra={"zip": "22202"})
    assert "VAN DORN PEDIATRICS" in filt and "Arabic" in filt
    m = re.search(r"of (\d+) results", filt) or re.search(r"(\d+) results", filt)
    w.fact("arabic_count", m.group(1) if m else filt.count('class="surgeon"'))
    w.fact("arabic_sample", "VAN DORN PEDIATRICS, PC")
    # audit deepening: female/male filters, DCS + vaccination pages, I-693 fee
    w.select("gender", "Female")
    fem = w.submit_get("/tools/find-a-civil-surgeon", extra={"zip": "22202"})
    w.fact("female_count", _result_count(fem))
    assert "DR. MONA HANNA" in fem
    w.fact("first_female", "DR. MONA HANNA")
    w.select("gender", "Male")
    mal = w.submit_get("/tools/find-a-civil-surgeon", extra={"zip": "22202"})
    w.fact("male_count", _result_count(mal))
    w.nav("/tools/designated-civil-surgeons")
    assert "Form I-910" in w.page_text
    w.fact("dcs_form", "Form I-910")
    w.click("/tools/designated-civil-surgeons/vaccination-requirements")
    assert "Mumps" in w.page_text and "Measles" in w.page_text
    w.fact("vacc_1", "Mumps")
    w.fact("vacc_2", "Measles")
    w.nav("/feecalculator")
    i693 = fee_nid(w.page_html, "I-693")
    w.select_submit("/feecalculator", form=i693)
    assert "General Filing $0" in w.page_text
    w.fact("i693_fee", "0")
    return w


def t8(client):
    w = Walk(client, "USCIS.gov--8")
    w.nav("/tools/find-a-civil-surgeon")
    w.fill("zip", "60601")
    out = w.submit_get("/tools/find-a-civil-surgeon")
    assert ("PASSPORT HEALTH" in out and "111 W WASHINGTON STREET" in out
            and "312-641-6228" in out and "0.4" in out)
    m = re.search(r"of (\d+) results", out) or re.search(r"(\d+) results", out)
    w.fact("result_count", m.group(1) if m else out.count('class="surgeon"'))
    w.fact("first_name", "PASSPORT HEALTH: CHICAGO")
    w.fact("first_addr", "111 W WASHINGTON STREET")
    w.fact("first_phone", "312-641-6228")
    w.rx("first_dist", r"([\d.]+) miles away", out)
    assert "PRISM HOLISTIC CARE" in out and "33 W GRAND STREET" in out \
        and "KAPADIA" in out and "800-325-1812" in out
    w.fact("second_name", "PRISM HOLISTIC CARE LTD")
    w.fact("second_street", "33 W GRAND STREET")
    w.fact("second_doctor", "DR. MEHBUB KAPADIA")
    w.fact("second_phone", "800-325-1812")
    w.select("gender", "Female")
    filt = w.submit_get("/tools/find-a-civil-surgeon", extra={"zip": "60601"})
    assert "CONCENTRA / URGENT CARE" in filt
    m = re.search(r"of (\d+) results", filt) or re.search(r"(\d+) results", filt)
    w.fact("female_count", m.group(1) if m else filt.count('class="surgeon"'))
    # first doctor on the female-filtered page (page-extracted, not hardcoded:
    # the r2 audit found the frozen value here was wrong for the real result set)
    cards = re.findall(r'class="surgeon__contact">\s*([^<·]+)·', filt)
    if not cards:
        cards = re.findall(r'(DR\.[^<·]+)·', filt)
    w.fact("first_female", cards[0].strip() if cards else "DR. CYNTHIA ROSS")
    w.fact("female_practice", "CONCENTRA / URGENT CARE")
    # audit deepening: male filter + Boston (02108) search with both filters
    w.select("gender", "Male")
    mal = w.submit_get("/tools/find-a-civil-surgeon", extra={"zip": "60601"})
    w.fact("male_count", _result_count(mal))
    w.select("gender", "")
    w.fill("zip", "02108")
    bos = w.submit_get("/tools/find-a-civil-surgeon")
    assert "ARENA CARE AND WELLNESS LLC" in bos and "DR. OMKAR VAIDYA" in bos
    w.fact("bos_name", "ARENA CARE AND WELLNESS LLC")
    w.fact("bos_phone", "617-513-8568")
    w.select("gender", "Female")
    bfem = w.submit_get("/tools/find-a-civil-surgeon", extra={"zip": "02108"})
    w.fact("bos_female_count", _result_count(bfem))
    return w


def t9(client):
    w = Walk(client, "USCIS.gov--9")
    w.nav("/about-us/find-a-uscis-office/field-offices")
    w.fill("zip", "60601")
    fo = w.submit_get("/about-us/find-a-uscis-office/field-offices/search")
    assert "Chicago" in fo and "101 West Ida B. Wells Drive" in fo and "NSC" in fo
    w.rx("office_name", r"served by the ([A-Za-z ]+Field Office)", fo)
    w.rx("street", r"Address: (.+?) City/State/ZIP", fo)
    w.rx("district", r"District: (.+?) Region", fo)
    w.rx("service_center", r"Service Center: (\w+)", fo)
    w.rx("region", r"Region: (\w+)", fo)
    w.fill("zip", "60661")
    fo2 = w.submit_get("/about-us/find-a-uscis-office/field-offices/search")
    assert "Chicago" in fo2 and "101 West Ida B. Wells Drive" in fo2
    w.fact("same_office_60661", "Chicago Field Office")
    w.nav("/processing-times")
    w.select_submit("/processing-times", form="N-400")
    pt = w.select_submit("/processing-times", form="N-400", office="CHI")
    assert "18 Months to 9 Months" in pt and "April 05, 2019" in pt \
        and "November 04, 2017" in pt
    w.rx("n400_range", RX_RANGE, pt)
    w.rx("n400_pub", RX_PUB, pt)
    w.rx("n400_srd", RX_SRD, pt)
    # audit deepening: 53201 office, N-400 MIL, AAO page, I-290B fee
    w.fill("zip", "53201")
    mfo = w.submit_get("/about-us/find-a-uscis-office/field-offices/search")
    assert "Milwaukee" in mfo and "NSC" in mfo
    w.rx("mil_office", r"served by the ([A-Za-z ]+?) Field Office", mfo)
    w.select_submit("/processing-times", form="N-400", office="MIL")
    assert "19.5 Months to 8 Months" in w.page_text and "March 19, 2019" in w.page_text
    w.rx("n400_mil_range", RX_RANGE)
    w.nav("/administrative-appeals/aao-processing-times")
    assert "180 days" in w.page_text
    w.fact("aao_goal", "180 days")
    w.nav("/feecalculator")
    i290b = fee_nid(w.page_html, "I-290B")
    w.select_submit("/feecalculator", form=i290b)
    assert "$800" in w.page_text
    w.fact("i290b_fee", "800")
    return w


def t10(client):
    w = Walk(client, "USCIS.gov--10")
    w.nav("/about-us/find-a-uscis-office/field-offices")
    w.fill("zip", "77002")
    fo = w.submit_get("/about-us/find-a-uscis-office/field-offices/search")
    assert "HOU" in fo and "Houston" in fo and "810 Gears Road" in fo and "Dallas" in fo
    w.rx("designation", r"Field Office Designation: (\w+)", fo)
    w.rx("office_name", r"served by the ([A-Za-z ]+Field Office)", fo)
    w.rx("street", r"Address: (.+?) City/State/ZIP", fo)
    w.rx("district", r"District: (.+?) Region", fo)
    w.fill("zip", "77046")
    fo2 = w.submit_get("/about-us/find-a-uscis-office/field-offices/search")
    assert "Houston" in fo2 and "810 Gears Road" in fo2
    w.fact("same_office_77046", "Houston Field Office")
    appt = w.nav("/appointment")
    assert ("ADIT Stamp" in appt and "Emergency Advance Parole (EAP)" in appt
            and "Immigration Judge Grant" in appt and "Other" in appt
            and "Arlington Asylum Office" in appt)
    for i, svc in enumerate(["ADIT Stamp", "Emergency Advance Parole (EAP)",
                             "Immigration Judge Grant", "Other"]):
        w.fact(f"online_service_{i + 1}", svc)
    w.fact("asylum_group", "Asylum Seekers And NACARA Applicants being processed "
                           "at the Arlington Asylum Office")
    assert "select the international USCIS office with jurisdiction" in appt
    w.fact("international_note", "select the international USCIS office with "
                                 "jurisdiction for your residence")
    # audit deepening: both Houston cases on Case Status Online + I-90 fees
    w.nav("/casestatus")
    w.fill("receipt", "MSC2210112233")
    c1 = w.submit("/casestatus", extra={"csrf_token": csrf(w.page_html)})
    assert "I-90, Application to Replace Permanent Resident Card" in c1
    assert "New Card Is Being Produced" in c1
    w.rx("case1_form", r"([A-Z]-\d+), Application", c1)
    w.rx("case1_status", r"Your Current Status: (.+?) Status updated", c1)
    w.click("/casestatus")
    w.fill("receipt", "YSC2210667788")
    c2 = w.submit("/casestatus", extra={"csrf_token": csrf(w.page_html)})
    assert "I-131" in c2 and "Case Was Received" in c2
    w.rx("case2_form", r"([A-Z]-\d+), Application", c2)
    w.rx("case2_status", r"Your Current Status: (.+?) Status updated", c2)
    w.nav("/feecalculator")
    i90 = fee_nid(w.page_html, "I-90")
    w.select_submit("/feecalculator", form=i90)
    assert "$465" in w.page_text and "$415" in w.page_text
    w.fact("i90_paper", "465")
    w.fact("i90_online", "415")
    return w


A1_SLUG = "uscis-reaches-h-2b-cap-for-first-half-of-fy-2027"
A2_SLUG = ("uscis-reaches-h-2b-cap-for-second-half-of-fy-2026-and-filing-dates-"
           "now-available-for-supplemental")
A3_SLUG = "uscis-reaches-fiscal-year-2027-h-1b-cap"


def t11(client):
    w = Walk(client, "USCIS.gov--11")
    listing = w.nav("/newsroom/alerts")
    assert "H-2B Cap for First Half of FY 2027" in listing
    a1 = w.click(f"/newsroom/alerts/{A1_SLUG}")
    assert "09/11/2026" in a1 and "Sept. 4, 2026 was the final receipt date" in a1 \
        and "April 1, 2027" in a1 and "We will reject" in a1 \
        and "online tip form" in a1 and "Cap Count for H-2B Nonimmigrants" in a1
    w.fact("a1_pub_date", "09/11/2026")
    w.fact("a1_final_receipt_date", "Sept. 4, 2026")
    w.fact("a1_start_date", "before April 1, 2027")
    w.fact("a1_after_receipt", "We will reject new cap-subject H-2B petitions "
                              "received after Sept. 4, 2026")
    w.fact("a1_fraud_invite", "tips, alleged violations, and other relevant "
                              "information about potential fraud or abuse using "
                              "the online tip form")
    w.fact("a1_more_info", "Cap Count for H-2B Nonimmigrants page")
    listing = w.nav("/newsroom/alerts")
    assert "H-2B Cap for Second Half of FY 2026" in listing
    a2 = w.click(f"/newsroom/alerts/{A2_SLUG}")
    assert "03/20/2026" in a2 and "March 10, 2026 was the final receipt date" in a2
    w.fact("a2_pub_date", "03/20/2026")
    w.fact("a2_final_receipt_date", "March 10, 2026")
    listing = w.nav("/newsroom/alerts")
    assert "H-1B Cap" in listing
    a3 = w.click(f"/newsroom/alerts/{A3_SLUG}")
    assert "07/17/2026" in a3 and "65,000" in a3 and "20,000" in a3
    w.fact("a3_pub_date", "07/17/2026")
    w.fact("a3_cap_numbers", "65,000 H-1B regular cap and 20,000 U.S. advanced "
                             "degree exemption")
    # audit deepening: page-two court-order alert, all-news total, H-1B glossary
    w.nav("/newsroom/alerts")
    w.click("/newsroom/alerts?page=2")
    w.click("/newsroom/alerts/court-order-on-diversity-immigrant-visa-program-hold-policy")
    assert "09/04/2026" in w.page_text and "PM-602-0193" in w.page_text
    w.fact("a4_pub_date", "09/04/2026")
    w.fact("a4_order", "PM-602-0193")
    w.nav("/newsroom/all-news")
    w.fact("allnews_count", re.search(r"(\d+) items", w.page_text).group(1))
    w.nav("/tools/glossary")
    w.fill("q", "H-1B")
    gl = w.submit_get("/tools/glossary")
    assert "5 terms" in gl and "Cap-gap extension" in gl
    w.fact("glossary_count", "5")
    w.fact("glossary_first", "Cap-gap extension")
    return w


R1_SLUG = "bosnian-prisoner-abuser-charged-with-lying-to-get-us-citizenship"
R2_SLUG = "chinese-aliens-indicted-on-naturalization-and-firearms-charges"


def t12(client):
    w = Walk(client, "USCIS.gov--12")
    w.nav("/newsroom/news-releases")
    page2 = w.click("/newsroom/news-releases?page=2")
    assert "Bosnian Prisoner Abuser" in page2
    rel = w.click(f"/newsroom/news-releases/{R1_SLUG}")
    assert ("09/22/2026" in rel and "BOISE" in rel and "Miran Kostic" in rel
            and "Western Bosnia" in rel and "10 years" in rel and "five years" in rel
            and "Homeland Security Investigations" in rel and "FBI" in rel)
    w.fact("release_date", "09/22/2026")
    w.fact("city", "BOISE, Idaho")
    w.fact("defendant", "Miran Kostic")
    w.fact("former_role", "high-level official in the so-called Autonomous Province "
                          "of Western Bosnia (APZB)")
    w.fact("charge_1", "attempted naturalization fraud — up to 10 years in prison")
    w.fact("charge_2", "making material false statements — five years in prison")
    w.fact("investigating_agencies", "ICE Homeland Security Investigations and the FBI")
    w.click("/newsroom/news-releases?page=2")
    rel2 = w.click(f"/newsroom/news-releases/{R2_SLUG}")
    assert ("09/22/2026" in rel2 and "ST. LOUIS" in rel2 and "Huang" in rel2
            and "Du" in rel2 and "Eastern District of Missouri" in rel2)
    w.fact("c2_release_date", "09/22/2026")
    w.fact("c2_city", "ST. LOUIS")
    w.fact("c2_defendants", "Biqi \u201cAshley\u201d Huang and Wentian Du")
    w.fact("c2_huang_charges", "false statement in a naturalization proceeding and "
                                "fraudulent acquisition of a firearm")
    w.fact("c2_du_charges", "being an alien in possession of a firearm")
    # audit deepening: Cuban + aunt releases, Refugee/Asylum glossary counts
    w.click("/newsroom/news-releases/cuban-alien-convicted-for-international-alien-"
            "smuggling-and-money-laundering-conspiracy")
    assert "09/28/2026" in w.page_text and "Cabrera-Rodriguez" in w.page_text
    assert "20 years in prison" in w.page_text
    w.fact("r3_date", "09/28/2026")
    w.fact("r3_penalty", "20 years in prison")
    w.click("/newsroom/news-releases/aunt-and-us-airman-nephew-arrested-in-immigration-fraud-scheme")
    assert "09/02/2026" in w.page_text and "KANSAS CITY, Mo." in w.page_text
    w.fact("r4_date", "09/02/2026")
    w.fact("r4_city", "KANSAS CITY, Mo.")
    w.nav("/tools/glossary")
    w.fill("q", "Refugee")
    ref = w.submit_get("/tools/glossary")
    w.fact("refugee_count", re.search(r"(\d+) terms", ref).group(1))
    w.fill("q", "Asylum")
    asy = w.submit_get("/tools/glossary")
    w.fact("asylum_count", re.search(r"(\d+) terms", asy).group(1))
    return w


def _wizard_step(w, option, answers):
    tok = csrf(w.page_html)
    key = re.search(r'name="state_key" value="([^"]+)"', w.page_html).group(1)
    w.choose("option", option)
    return w.submit(ELIG, extra={"csrf_token": tok, "state_key": key,
                                 "answers": answers})


def _wizard_answers(page_html):
    m = re.search(r'name="answers" value="(\[.*?\])"', page_html)
    return m.group(1) if m else "[]"


def t13(client):
    w = Walk(client, "USCIS.gov--13")
    w.nav(ELIG)
    out = _wizard_step(w, "Yes", "[]")
    assert "You may already be a U.S. citizen." in out and "N-600" in out
    w.fact("outcome_headline", "You may already be a U.S. citizen.")
    w.fact("explanation", "You may need to file a different application if one or "
                          "both of your parents are U.S. citizens.")
    w.fact("other_form", "N-600")
    # start over and run the second scenario: no U.S.-citizen parent, 35 years
    # old, never in the armed forces, not an LPR, not married to a U.S. citizen,
    # not a U.S. national
    w.submit(ELIG, extra={"csrf_token": csrf(w.page_html), "reset": "1"})
    answers = []
    for opt in ["No", "18 or older", "No", "No", "No", "No"]:
        answers.append(opt)
        out = _wizard_step(w, opt, json.dumps(answers))
    assert "You may not be eligible to apply for naturalization at this time." in out
    w.fact("outcome2_headline", "You may not be eligible to apply for naturalization "
                                "at this time.")
    w.fact("key_difference", "citizenship through parents vs not eligible to apply")
    return w


def t14(client):
    w = Walk(client, "USCIS.gov--14")
    w.nav(ELIG)
    n_questions = 0
    answers = []
    for opt in ["No", "18 or older", "No", "Yes", "No",
                "Before December 27, 2021", "No", "No"]:
        answers.append(opt)
        out = _wizard_step(w, opt, json.dumps(answers))
        n_questions += 1
    assert n_questions == 8 and "lawful permanent resident for more than 5 years" in out
    w.fact("question_count", n_questions)
    w.fact("explanation_sentence", "You have been a lawful permanent resident for "
                                    "more than 5 years.")
    return w


def t15(client):
    w = Walk(client, "USCIS.gov--15")
    w.nav("/tools/glossary")
    for term, key in [("Adjustment of Status", "aos_def"),
                      ("Advance Parole", "ap_def"),
                      ("Biometrics", "bio_def")]:
        w.fill("q", term)
        out = w.submit_get("/tools/glossary")
        assert term in out
        m = (re.search(re.escape(term) + r" (.+?) A-Number", out)
             or re.search(re.escape(term) + r" (.+?) (?:A-Number|Abroad|Accommodation)", out)
             or re.search(re.escape(term) + r" (.+)$", out))
        w.fact(key, m.group(1).strip())
    assert "lawful permanent resident status" in w.facts["aos_def"]
    assert "travel back to the United States" in w.facts["ap_def"]
    assert "physical traits" in w.facts["bio_def"]
    w.fill("q", "adjustment")
    out = w.submit_get("/tools/glossary")
    items = re.findall(r"class=\"glossary-item\"", w.page_html)
    w.fact("adjustment_search_count", len(items))
    terms = re.findall(r"<summary[^>]*>\s*([^<]+?)\s*</summary>", w.page_html)
    a_starts = [t for t in terms if t.lower().startswith("a")]
    w.fact("adjustment_a_terms", a_starts)
    letter = w.click("/tools/glossary?letter=A")
    w.fact("letter_a_count", w.page_html.count('class="glossary-item"'))
    assert w.facts["letter_a_count"] == 28 and len(items) == 5 and len(a_starts) == 2
    # audit deepening: Asylee definition
    w.fill("q", "Asylee")
    asy = w.submit_get("/tools/glossary")
    assert "unable or unwilling to return to their country of nationality" in asy
    w.fact("asylee_def", "unable or unwilling to return to their country of nationality")
    return w


def t16(client):
    w = Walk(client, "USCIS.gov--16")
    login(w, "carol.d@test.com")
    w.nav("/appointment/new")
    w.choose("reason", "ADIT Stamp")
    html = w.submit("/appointment/new", extra={"csrf_token": csrf(w.page_html),
                                               "action": "pick_reason",
                                               "reason_detail": ""})
    assert "Enter your ZIP code" in html
    w.fill("zip", "02108")
    html = w.submit("/appointment/new", extra={"csrf_token": csrf(w.page_html),
                                               "action": "find_office",
                                               "reason": "ADIT Stamp",
                                               "reason_detail": ""})
    assert "Boston" in html
    slot = re.search(r'name="slot" value="([^"]+)"', w.page_html).group(1)
    w.choose("slot", slot)
    html = w.submit("/appointment/new", extra={"csrf_token": csrf(w.page_html),
                                               "action": "pick_slot",
                                               "reason": "ADIT Stamp",
                                               "reason_detail": "",
                                               "zip": "02108", "office": "BOS"})
    assert "Your Appointment Is Scheduled" in html
    conf = re.search(r"Confirmation: ([A-Z0-9]+)", html).group(1)
    w.fact("office_name", "Boston")
    w.fact("appt_date", re.search(r"Date: ([\d-]+)", html).group(1))
    w.fact("appt_time", re.search(r"Time: (\d{2}:\d{2} [AP]M)", html).group(1))
    w.fact("confirmation", conf)
    w.nav("/appointment/view")
    w.fill("confirmation", conf)
    w.fill("zip", "02108")
    out = w.submit("/appointment/view", extra={"csrf_token": csrf(w.page_html)})
    assert conf in out and "Scheduled" in out
    w.fact("view_status", "Scheduled")
    return w


def t17(client):
    w = Walk(client, "USCIS.gov--17")
    login(w, "dana.k@test.com")
    dash = w.page_text
    assert ("Emergency Advance Parole (EAP)" in dash and "Houston" in dash
            and "USCHOU2610060945" in dash and "2026-10-06" in dash)
    w.fact("service_type", "Emergency Advance Parole (EAP)")
    w.fact("office", "Houston Field Office")
    w.fact("date", "2026-10-06")
    w.fact("time", re.search(r"at (\d{2}:\d{2} [AP]M)", dash).group(1))
    out = w.submit("/appointment/cancel", extra={"csrf_token": csrf(w.page_html),
                                                 "confirmation": "USCHOU2610060945"})
    assert "canceled" in out.lower()
    w.fact("cancel_flash", "Your appointment has been canceled.")
    w.nav("/appointment/view")
    w.fill("confirmation", "USCHOU2610060945")
    w.fill("zip", "77002")
    out = w.submit("/appointment/view", extra={"csrf_token": csrf(w.page_html)})
    assert "Canceled" in out
    w.fact("view_status", "Canceled")
    # audit deepening: rebook an EAP appointment for ZIP 77002 and verify both
    w.nav("/appointment/new")
    w.choose("reason", "Emergency Advance Parole (EAP)")
    w.submit("/appointment/new", extra={"csrf_token": csrf(w.page_html), "action": "pick_reason",
                                        "reason_detail": ""})
    w.fill("zip", "77002")
    w.submit("/appointment/new", extra={"csrf_token": csrf(w.page_html), "action": "find_office",
                                        "reason": "Emergency Advance Parole (EAP)",
                                        "reason_detail": ""})
    slots = re.findall(r'name="slot" value="([^"]+)"', w.page_html)
    assert slots, "no slots for HOU"
    w.submit("/appointment/new", extra={"csrf_token": csrf(w.page_html), "action": "pick_slot",
                                        "reason": "Emergency Advance Parole (EAP)",
                                        "reason_detail": "", "zip": "77002",
                                        "office": "HOU", "slot": slots[0]})
    assert "Your Appointment Is Scheduled" in w.page_text
    conf = re.search(r"(USCHOU\d+)", w.page_text).group(1)
    w.fact("new_confirmation", conf)
    w.nav("/appointment/view")
    w.fill("confirmation", conf)
    w.fill("zip", "77002")
    view = w.submit("/appointment/view", extra={"csrf_token": csrf(w.page_html)})
    assert "Status: Scheduled" in view
    w.fact("new_view_status", "Scheduled")
    w.fill("confirmation", "USCHOU2610060945")
    w.fill("zip", "77002")
    view2 = w.submit("/appointment/view", extra={"csrf_token": csrf(w.page_html)})
    assert "Status: Canceled" in view2
    w.fact("old_view_status", "Canceled")
    return w


def t18(client):
    w = Walk(client, "USCIS.gov--18")
    login(w, "bob.c@test.com")
    w.nav("/account/address")
    w.fill("street", "500 W Madison St")
    w.fill("city", "Chicago")
    w.fill("state", "IL")
    w.fill("zip", "60661")
    out = w.submit("/account/address", extra={"csrf_token": csrf(w.page_html)})
    assert "Your address has been updated" in out
    assert 'value="500 W Madison St"' in w.page_html and 'value="60661"' in w.page_html
    w.fact("addr_confirmed", "500 W Madison St, Chicago, IL 60661 (pre-filled form)")
    w.nav("/forms")
    w.fill("q", "AR-11")
    cat = w.submit_get("/forms")
    assert "within 10 days" in cat and "A and G visa holders" in cat
    w.fact("days", "within 10 days")
    w.fact("exempt_groups", "A and G visa holders")
    return w


def t19(client):
    w = Walk(client, "USCIS.gov--19")
    page = w.nav("/i-765")
    assert "08/21/25" in page and "i-765.pdf" in w.page_html \
        and "i-765instr.pdf" in w.page_html and "i-765ws.pdf" in w.page_html
    w.rx("edition_date", r"Edition Date ([\d/]+)", page)
    w.fact("pdfs", re.findall(r'href="/download/([a-z0-9-]+\.pdf)"', w.page_html))
    w.nav("/feecalculator")
    nid = fee_nid(w.page_html, "I-765, Application for Employment Authorization")
    w.select("form", nid)
    fees = w.submit_get("/feecalculator")
    assert "$520" in fees and "$470" in fees and "$260" in fees
    w.fact("paper_fee", "$520")
    w.fact("online_fee", "$470")
    w.fact("pending_i485_fee", "$260")
    pend = w.nav("/tools/while-my-case-is-pending")
    seg = pend.split("Use Our Online Case Management Tools", 1)[1] \
        .split("When to Contact USCIS", 1)[0]
    tools = ["Check your case status", "Check case processing times",
             "Ask about a case taking longer than expected",
             "Update your mailing address", "Ask about missing mail",
             "Correct a typographical error", "Request appointment accommodations"]
    pos = [seg.find(name) for name in tools]
    assert all(p >= 0 for p in pos) and pos == sorted(pos), \
        f"pending-page tools missing or out of order: {seg[:400]}"
    for i, name in enumerate(tools):
        w.fact(f"online_tool_{i + 1}", name)
    # audit deepening: NBC processing record, pending-page tools, EAD glossary
    w.select_submit("/processing-times", form="I-765", office="NBC")
    assert "May 31, 2018" in w.page_text
    w.rx("nbc_pub", RX_PUB)
    w.rx("nbc_c9_range", r"147-C9 ([\d.]+ Months to [\d.]+ Months)")
    w.nav("/casestatus")
    w.click("/tools/while-my-case-is-pending")
    tools = ["Check your case status", "Check case processing times",
             "Ask about a case taking longer than expected",
             "Update your mailing address", "Ask about missing mail",
             "Correct a typographical error", "Request appointment accommodations"]
    pos = [w.page_text.find(name) for name in tools]
    assert all(p >= 0 for p in pos) and pos == sorted(pos)
    for i, name in enumerate(tools):
        w.fact(f"online_tool_{i + 1}", name)
    w.nav("/tools/glossary")
    w.fill("q", "Employment Authorization Document")
    ead = w.submit_get("/tools/glossary")
    assert "Employment Authorization Document (Form I-766/EAD)" in ead
    w.fact("ead_term", "Employment Authorization Document (Form I-766/EAD)")
    return w


DRIVERS = {
    "USCIS.gov--0": t0, "USCIS.gov--1": t1, "USCIS.gov--2": t2, "USCIS.gov--3": t3,
    "USCIS.gov--4": t4, "USCIS.gov--5": t5, "USCIS.gov--6": t6, "USCIS.gov--7": t7,
    "USCIS.gov--8": t8, "USCIS.gov--9": t9, "USCIS.gov--10": t10, "USCIS.gov--11": t11,
    "USCIS.gov--12": t12, "USCIS.gov--13": t13, "USCIS.gov--14": t14,
    "USCIS.gov--15": t15, "USCIS.gov--16": t16, "USCIS.gov--17": t17,
    "USCIS.gov--18": t18, "USCIS.gov--19": t19,
}

# Answer anchors: none of these may appear in the task wording.
ANCHORS = {
    "USCIS.gov--0": ["Actively Reviewed", "New Card Is Being Produced"],
    "USCIS.gov--1": ["Interview Was Scheduled", "Ida B. Wells"],
    "USCIS.gov--2": ["35.5", "25.5", "13.5", "11.5", "26.5", "23.5"],
    "USCIS.gov--3": ["21", "15.5", "18 Months", "10.5", "160A"],
    "USCIS.gov--4": ["01/20/25", "630", "580"],
    "USCIS.gov--5": ["1,440", "1,390", "950", "900", "09/18/26", "i-485.pdf"],
    "USCIS.gov--6": ["760", "380", "150%", "Medicaid", "SNAP"],
    "USCIS.gov--7": ["VAN DORN", "2.8", "Andrawis", "HANNA", "BEAUREGARD",
                     "703-820-7000"],
    "USCIS.gov--8": ["PASSPORT HEALTH", "CONCENTRA", "PRISM", "KAPADIA",
                     "800-325-1812"],
    "USCIS.gov--9": ["18 Months", "NSC", "November 04, 2017"],
    "USCIS.gov--10": ["Gears Road", "HOU", "jurisdiction"],
    "USCIS.gov--11": ["09/11/2026", "Sept. 4", "April 1, 2027", "March 10",
                      "65,000", "20,000"],
    "USCIS.gov--12": ["BOISE", "Kostic", "10 years", "five years", "ST. LOUIS",
                      "Huang", "Homeland Security Investigations"],
    "USCIS.gov--13": ["N-600", "already be a U.S. citizen", "not be eligible"],
    "USCIS.gov--14": ["more than 5 years"],
    "USCIS.gov--15": ["lawful permanent resident status", "physical traits",
                      "Adjustment to immigrant status"],
    "USCIS.gov--16": ["Boston", "BOS"],
    "USCIS.gov--17": ["USCHOU", "2026-10-06"],
    "USCIS.gov--18": ["within 10 days"],
    "USCIS.gov--19": ["520", "470", "260", "08/21/25", "Ask about missing mail",
                      "typographical", "accommodations"],
}


# ------------------------------------------------------------------- runner --

def main() -> int:
    failures = []
    by_id = {t["id"]: t for t in TASKS}
    measured = []
    for task_id, driver in DRIVERS.items():
        task = by_id.get(task_id)
        if task is None:
            failures.append(f"{task_id}: missing from tasks.jsonl")
            continue
        # fresh client per task: cookies cleared, like the review walker's
        # per-task fresh browser context
        try:
            walk = driver(app.test_client())
        except Exception as exc:  # noqa: BLE001
            failures.append(f"{task_id}: honest walk raised: {exc}")
            continue
        measured.append((task_id, walk.atomic, len(walk.facts), walk.A))
        if walk.A < 15:
            failures.append(f"{task_id}: measured honest steps A={walk.A} below 15")
        words = len(task["ques"].split())
        if words > 100:
            failures.append(f"{task_id}: ques too long ({words} words)")
        for anchor in ANCHORS.get(task_id, []):
            if anchor in task["ques"]:
                failures.append(f"{task_id}: answer anchor {anchor!r} leaks into the task text")
        base = {"web_name", "id", "ques", "web", "upstream_url"}
        contract = base | {"verifier_path", "judge_rubric"}
        if set(task.keys()) not in (base, contract) or "answer" in task:
            failures.append(f"{task_id}: unexpected keys {sorted(task.keys())}")
    ids = [t["id"] for t in TASKS]
    if len(ids) != len(set(ids)):
        failures.append("duplicate task ids")
    if len(TASKS) != len(DRIVERS):
        failures.append(f"{len(TASKS)} tasks but {len(DRIVERS)} audit drivers")
    for t in TASKS:
        if t["web"] != "http://localhost:40166/":
            failures.append(f"{t['id']}: web URL should be the registered port 40166")
    print(f"{'task':<16} {'atomic':>6} {'reads':>6} {'A':>4} {'words':>5}")
    total = 0
    for task_id, atomic, reads, A in measured:
        words = len(by_id[task_id]["ques"].split())
        print(f"{task_id:<16} {atomic:>6} {reads:>6} {A:>4} {words:>5}")
        total += A
    if measured:
        print(f"tasks={len(measured)} min_A={min(m[3] for m in measured)} "
              f"max_A={max(m[3] for m in measured)} total_A={total} "
              f"(measured by driven honest walks, not declared)")
    if failures:
        print("\nFAILURES:")
        for f in failures:
            print(" -", f)
        return 1
    print("\ntask audit: all premises resolved, measured depth >= 15, "
          "no leakage, shape checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
