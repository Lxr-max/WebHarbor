#!/usr/bin/env python3
"""Honest step-count audit for the red_bull contribution.

Audit-rail rules (same contract as the us_appliance/tumblr audits):
- Per-task fresh browser context.
- ONLY visible-element interaction: links/buttons/inputs located by
  role/text/CSS. Direct URL navigation is allowed ONLY for the site
  homepage. Every other page is reached by clicking a visible link/button.
- Steps counted are ATOMIC ACTIONS the task genuinely requires:
  navigate (homepage), click, select, type, submit. Reads (extracting
  facts from the rendered page) are NOT counted. No padding actions.
- Answers are written ONLY from what the rendered pages actually show.
- Logins type the benchmark credentials into the visible login form.

Usage: audit_steps.py [--out runs/xxx] [--only N]
"""
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

SITE = "http://127.0.0.1:43127"
OUT_ROOT = Path("/data/zhaoyang-user-projects/websyn/wh-red-bull-contrib-evidence/runs")
SITE_DIR = Path(__file__).resolve().parents[1]

PASSWORD = "TestPass123!"
ALICE = "alice.j@test.com"
BOB = "bob.c@test.com"
CAROL = "carol.d@test.com"


def tasks():
    rows = {}
    for line in (SITE_DIR / "tasks.jsonl").read_text().splitlines():
        if line.strip():
            r = json.loads(line)
            rows[r["id"]] = r
    return rows


class Drive:
    """One audited task run: step log + extracted answers.

    step() records an ATOMIC ACTION (click/type/select/submit/navigate).
    note() records a READ (fact extraction) — logged but not counted.
    """

    def __init__(self, page, task_id: str, out_dir: Path):
        self.page = page
        self.task_id = task_id
        self.out = out_dir
        self.out.mkdir(parents=True, exist_ok=True)
        self.steps: list[dict] = []
        self.reads: list[dict] = []
        self.facts: dict = {}
        self.n = 0
        self.js_errors: list[str] = []
        page.on("pageerror", lambda e: self.js_errors.append(str(e)))

    # ---------------------------------------------------------------- actions

    def step(self, action: str, target: str, detail: str = "") -> None:
        self.n += 1
        self.steps.append({"n": self.n, "action": action, "target": target,
                           "detail": detail, "url": self.page.url})
        self.page.screenshot(path=str(self.out / f"step_{self.n:03d}.png"))

    def goto_home(self) -> None:
        self.page.goto(SITE, timeout=45000, wait_until="load")
        self.page.wait_for_timeout(500)
        self.step("navigate", "homepage (start_url)")

    def _visible_first(self, locator, label: str):
        deadline = time.time() + 15
        while time.time() < deadline:
            for i in range(min(locator.count(), 60)):
                el = locator.nth(i)
                if el.is_visible():
                    return el
            time.sleep(0.25)
        raise AssertionError(f"no visible element for: {label}")

    def click(self, selector: str, label: str = "") -> None:
        loc = self._visible_first(self.page.locator(selector), label or selector)
        loc.scroll_into_view_if_needed()
        loc.click()
        self.page.wait_for_timeout(450)
        self.step("click", label or selector)

    def click_link(self, href: str, label: str = "") -> None:
        loc = self._visible_first(self.page.locator(f'a[href="{href}"]'),
                                  label or href)
        loc.scroll_into_view_if_needed()
        loc.click()
        self.page.wait_for_timeout(450)
        self.step("click", f"link:{label or href}")

    def click_card(self, href_part: str, label: str = "") -> None:
        loc = self._visible_first(
            self.page.locator(f'.card[href*="{href_part}"]'), label or href_part)
        loc.scroll_into_view_if_needed()
        loc.click()
        self.page.wait_for_timeout(450)
        self.step("click", f"card:{label or href_part}")

    def nav(self, text: str) -> None:
        loc = self._visible_first(
            self.page.locator("header .main-nav a",
                              has_text=re.compile(f"^{re.escape(text)}$")),
            f"nav:{text}")
        loc.click()
        self.page.wait_for_timeout(500)
        self.step("click", f"nav:{text}")

    def select(self, selector: str, value, label: str = "") -> None:
        loc = self.page.locator(selector).first
        loc.wait_for(state="visible", timeout=15000)
        if value == "@first":
            # first enabled option with a real value (skips disabled and
            # placeholder "Choose..." options)
            idxs = [i for i, o in enumerate(loc.locator("option").all())
                    if o.get_attribute("disabled") is None
                    and (o.get_attribute("value") or "") != ""]
            loc.select_option(index=idxs[0] if idxs else 0)
        else:
            loc.select_option(value)
        self.page.wait_for_timeout(350)
        self.step("select", label or selector, str(value))

    def fill(self, selector: str, value: str, label: str = "") -> None:
        loc = self.page.locator(selector).first
        loc.wait_for(state="visible", timeout=15000)
        loc.click()
        loc.fill(value)
        self.page.wait_for_timeout(200)
        self.step("type", label or selector, value[:60])

    def submit(self, selector: str, label: str = "submit") -> None:
        before = self.page.url
        self.page.locator(selector).first.click()
        deadline = time.time() + 10
        while time.time() < deadline:
            self.page.wait_for_timeout(200)
            if self.page.url != before:
                break
        try:
            self.page.wait_for_load_state("load", timeout=8000)
        except Exception:                                        # noqa: BLE001
            pass
        self.step("click", label)

    def back(self, label: str = "back to list") -> None:
        self.page.go_back()
        self.page.wait_for_timeout(400)
        self.step("click", label)

    # ------------------------------------------------------------------ reads

    def note(self, label: str, value: str) -> str:
        self.reads.append({"label": label, "value": value[:400],
                           "url": self.page.url})
        self.facts[label] = value
        return value

    def body_text(self) -> str:
        return self.page.evaluate("() => document.body.innerText")

    def read_fact(self, label: str, pattern: str, flags: int = 0) -> str | None:
        m = re.search(pattern, self.body_text(), flags)
        return self.note(label, m.group(0).strip()) if m else None

    def finish(self, answer: dict) -> dict:
        row = {"task_id": self.task_id,
               "step_count": self.n,
               "steps": self.steps,
               "reads": self.reads,
               "facts": self.facts,
               "answer": answer,
               "js_errors": self.js_errors,
               "final_url": self.page.url}
        (self.out / "trace.json").write_text(
            json.dumps(row, indent=1, ensure_ascii=False), encoding="utf-8")
        return row


def login(d: Drive, email: str, password: str = PASSWORD) -> None:
    d.click_link("/account/login", "Log in")
    d.fill('input[name="email"]', email, "email field")
    d.fill('input[name="password"]', password, "password field")
    d.submit('.form-card button[type="submit"]', "Log in button")


def events_filter(d: Drive, *, country: str = "", discipline: str = "",
                  status: str = "") -> None:
    d.nav("Events")
    if discipline:
        d.select("#discipline", discipline, f"discipline={discipline}")
    if country:
        d.select("#country", country, f"country={country}")
    if status:
        d.select("#status", status, f"status={status}")
    d.submit(".filter-actions button", "Filter")


# --------------------------------------------------------------------- tasks --

def t0(d: Drive) -> dict:
    d.goto_home()
    events_filter(d, discipline="Surfing")
    d.click_card("/events/red-bull-foam-wreckers-virginia-beach", "Foam Wreckers VB card")
    d.click_link("/events/red-bull-foam-wreckers-virginia-beach/faqs", "FAQs tab")
    d.read_fact("faq_board", r"soft-top \(foamie\)[^\n]*")
    d.read_fact("faq_spectators", r"free to attend[^\n]*")
    d.click_link("/events/red-bull-foam-wreckers-virginia-beach/schedule", "Schedule tab")
    d.read_fact("checkin", r"Check In[^\n]*")
    d.click_link("/events/red-bull-foam-wreckers-virginia-beach", "Info tab")
    d.click_link("/events/red-bull-foam-wreckers-virginia-beach/register", "Register Now!")
    d.fill('input[name="first_name"]', "Casey", "first name")
    d.fill('input[name="last_name"]', "Rider", "last name")
    d.fill('input[name="email"]', "casey.rider@example.com", "email")
    d.select("#ticket_type", "@first", "ticket type")
    d.submit('.form-card button[type="submit"]', "Complete registration")
    m = re.search(r"Registration code\s*\n?\s*(RB[A-Z0-9]+)", d.body_text())
    code = m.group(1) if m else ""
    d.note("registration_code", code)
    d.read_fact("entry_fee", r"Entry fee\s*\n?\s*\$[0-9.]+ [A-Z]*")
    events_filter(d, discipline="Surfing")
    d.click_card("/events/red-bull-foam-wreckers-narragansett", "Narragansett card")
    d.read_fact("ri_venue", r"Narragansett Town Beach")
    return {"registration_code": code}


def t1(d: Drive) -> dict:
    d.goto_home()
    events_filter(d, country="US", status="upcoming")
    fees = {}
    for slug, name in [("red-bull-foam-wreckers-virginia-beach", "Foam Wreckers VB"),
                       ("red-bull-rapid-release", "Rapid Release"),
                       ("foam-wreckers-carolina-beach", "Foam Wreckers Carolina Beach")]:
        d.click_card(f"/events/{slug}", f"{name} card")
        text = d.body_text()
        m = re.search(r"per participant", text)
        fee = re.search(r"\$([0-9]+)", text)
        v = re.search(r"Venue\s*\n?\s*([^\n]+)", text)
        fees[slug] = {"fee": fee.group(1) if fee else "Free",
                      "venue": v.group(1).strip() if v else ""}
        d.note(f"fee_{slug}", str(fees[slug]))
        d.back(f"back from {name}")
    d.click_card("/events/foam-wreckers-carolina-beach", "Carolina Beach card")
    d.click_link("/events/foam-wreckers-carolina-beach/register", "Register Now!")
    d.fill('input[name="first_name"]', "Sam", "first name")
    d.fill('input[name="last_name"]', "Porter", "last name")
    d.fill('input[name="email"]', "sam.porter@example.com", "email")
    d.select("#ticket_type", "@first", "ticket type")
    d.submit('.form-card button[type="submit"]', "Complete registration")
    m = re.search(r"Registration code\s*\n?\s*(RB[A-Z0-9]+)", d.body_text())
    code = m.group(1) if m else ""
    d.note("registration_code", code)
    return {"fees": fees, "registration_code": code}


def t2(d: Drive) -> dict:
    d.goto_home()
    events_filter(d, discipline="Motocross")
    d.click_card("/events/red-bull-barn-find-open", "Barn Find Open card")
    d.read_fact("ia_venue", r"Oak Ridge MX Track[^\n]*")
    d.read_fact("era", r"race dirt bikes from the [^\n.]*")
    events_filter(d, discipline="DTM")
    d.click_card("/events/dtm-nuerburgring", "Nürburgring card")
    d.read_fact("nuerburgring_dates", r"August 15[^\n]*")
    d.back("back to DTM list")
    d.click_card("/events/dtm-hockenheimring", "Hockenheimring card")
    d.read_fact("hockenheimring_dates", r"October 10[^\n]*")
    events_filter(d, discipline="esports")
    d.click_card("/events/red-bull-wings-cup-united-states-2026", "Wings Cup card")
    d.read_fact("wings_dates", r"September 18[^\n]*")
    d.read_fact("badge", r"Registrations open")
    return {}


def t3(d: Drive) -> dict:
    d.goto_home()
    events_filter(d, country="IT")
    d.click_card("/events/red-bull-cliff-diving-world-series-polignano-a-mare-italy",
                 "Polignano a Mare card")
    d.click_link("/event-series/red-bull-cliff-diving", "series link")
    d.read_fact("series_desc", r"Divers execute[^\n]*")
    d.note("stops", str(re.findall(r"(Polignano a Mare|Mostar)", d.body_text())))
    d.nav("Events")
    d.select("#discipline", "Kitesurfing", "discipline=Kitesurfing")
    d.submit(".filter-actions button", "Filter")
    d.click_card("/events/red-bull-king-of-the-air", "King of the Air card")
    d.click_link("/event-series/red-bull-king-of-the-air", "KOTA series link")
    d.note("kota_stops", str(re.findall(r"(Taiwan qualifier|Cape Town)", d.body_text())))
    events_filter(d, discipline="Surfing")
    d.click_card("/events/red-bull-foam-wreckers-virginia-beach", "Foam Wreckers VB card")
    d.click_link("/event-series/red-bull-foam-wreckers", "Foam Wreckers series link")
    m = re.search(r"Stops\s*\n?\s*(\d+)", d.body_text())
    d.note("fw_stops", m.group(0) if m else "")
    return {}


def t4(d: Drive) -> dict:
    d.goto_home()
    events_filter(d, discipline="Basketball")
    d.click_card("/events/red-bull-rapid-release", "Rapid Release card")
    d.click_link("/events/red-bull-rapid-release/faqs", "FAQs tab")
    d.read_fact("teams", r"capped at \d+ teams[^\n]*")
    d.click_link("/events/red-bull-rapid-release/schedule", "Schedule tab")
    d.read_fact("checkin", r"check-in open[^\n]*", re.I)
    d.click_link("/events/red-bull-rapid-release", "Info tab")
    d.click_link("/events/red-bull-rapid-release/register", "Register Now!")
    d.fill('input[name="first_name"]', "", "empty first name")
    d.fill('input[name="last_name"]', "", "empty last name")
    d.fill('input[name="email"]', "not-an-email", "bad email")
    d.submit('.form-card button[type="submit"]', "Complete registration")
    d.note("errors", str(re.findall(r"(valid email address|first and last name)",
                                    d.body_text())))
    d.fill('input[name="first_name"]', "Dana", "first name")
    d.fill('input[name="last_name"]', "Kim", "last name")
    d.fill('input[name="email"]', "dana.k@example.com", "email")
    d.select("#ticket_type", "@first", "ticket type")
    d.submit('.form-card button[type="submit"]', "Complete registration")
    m = re.search(r"Registration code\s*\n?\s*(RB[A-Z0-9]+)", d.body_text())
    code = m.group(1) if m else ""
    d.note("registration_code", code)
    d.read_fact("fee", r"Entry fee\s*\n?\s*[^\n]+")
    return {"registration_code": code}


def t5(d: Drive) -> dict:
    d.goto_home()
    d.nav("Energy Drinks")
    d.click_card("/energydrink/red-bull-summer-edition", "Summer Edition card")
    d.note("summer_caf", str(re.findall(r"(\d+) mg", d.body_text())))
    d.note("summer_sug", str(re.findall(r"(\d+) g of sugars", d.body_text())))
    d.note("summer_sizes", str(re.findall(r"(\d+\.?\d* fl oz)", d.body_text())))
    d.nav("Energy Drinks")
    d.click_card("/energydrink/red-bull-energy-drink", "Original card")
    d.note("orig_caf", str(re.findall(r"(\d+) mg", d.body_text())))
    d.note("orig_sug", str(re.findall(r"(\d+) g of sugars", d.body_text())))
    d.note("orig_sizes", str(re.findall(r"(\d+\.?\d* fl oz)", d.body_text())))
    d.nav("Energy Drinks")
    d.click('.chip-row a.chip:has-text("Red Bull Editions")', "Editions chip")
    sugarfree = [l for l in d.body_text().split("\n") if "Sugarfree" in l]
    d.note("sugarfree_variants", str(sugarfree))
    d.click_card("/energydrink/red-bull-red-edition", "Red Edition card")
    d.note("red_sugarfree", "yes" if "Red Edition Sugarfree" in d.body_text() else "no")
    d.nav("Energy Drinks")
    d.click_card("/energydrink/red-bull-amber-edition", "Amber Edition card")
    d.note("amber_caf", str(re.findall(r"(\d+) mg", d.body_text())))
    d.note("amber_sug", str(re.findall(r"(\d+) g of sugars", d.body_text())))
    d.nav("Energy Drinks")
    d.click_card("/energydrink/red-bull-peach-edition", "Peach Edition card")
    d.note("peach_caf", str(re.findall(r"(\d+) mg", d.body_text())))
    d.note("peach_sug", str(re.findall(r"(\d+) g of sugars", d.body_text())))
    d.nav("Energy Drinks")
    d.click_card("/energydrink/red-bull-zero", "Zero card")
    d.read_fact("zero_monkfruit", r"monk fruit[^\n]*")
    d.nav("Energy Drinks")
    d.click_card("/energydrink/red-bull-sugarfree", "Sugarfree card")
    d.read_fact("sf_monkfruit", r"monk fruit[^\n]*")
    return {}


def t6(d: Drive) -> dict:
    d.goto_home()
    d.nav("Athletes")
    d.select("#country", "United Kingdom", "country=UK")
    d.submit(".filter-actions button", "Filter")
    d.note("uk_athletes", str([l for l in d.body_text().split("\n")
                                if l.strip()][:16]))
    careers = {}
    for slug in ("gee-atherton", "rachel-atherton", "sky-brown", "zoe-backstedt"):
        d.nav("Athletes")
        d.select("#country", "United Kingdom", "country=UK")
        d.submit(".filter-actions button", "Filter")
        d.click_card(f"/athletes/{slug}", f"{slug} card")
        m = re.search(r"Career start\s*\n\s*([^\n]+)", d.body_text())
        careers[slug] = m.group(1).strip() if m else ""
        d.note(f"career_{slug}", careers[slug])
    d.nav("Athletes")
    d.click('.chip-row a.chip:has-text("T")', "letter T chip")
    d.click_card("/athletes/terry-adams", "Terry Adams card")
    d.read_fact("terry_discipline", r"BMX Flatland")
    d.read_fact("terry_nationality", r"Nationality\s*\n?\s*([^\n]+)")
    return {"careers": careers}


def t7(d: Drive) -> dict:
    d.goto_home()
    d.nav("Films")
    d.click_card("/films/9191", "newest film card")
    d.read_fact("subheading", r"A season of snowboarding[^\n]*")
    d.read_fact("runtime", r"\d+ min")
    d.nav("Films")
    d.select("#discipline", "Snowboarding", "discipline=Snowboarding")
    d.submit(".filter-actions button", "Filter")
    d.read_fact("snowboarding_count", r"\d+ films")
    first = d.page.locator(".card").first
    first.click()
    d.step("click", "first snowboarding film")
    d.read_fact("first_snow_subheading", r"[^\n]*\n[^\n]*")
    d.nav("Films")
    d.select("#discipline", "Surfing", "discipline=Surfing")
    d.submit(".filter-actions button", "Filter")
    d.read_fact("surfing_count", r"\d+ films")
    d.nav("Films")
    d.select("#discipline", "esports", "discipline=esports")
    d.submit(".filter-actions button", "Filter")
    d.read_fact("esports_count", r"\d+ films")
    d.nav("Films")
    d.click('.pager a:has-text("Next")', "Next page 2")
    d.read_fact("page2_first", r"Red Bull Soapbox Race: 50 Crowd Favourites")
    return {}


def t8(d: Drive) -> dict:
    d.goto_home()
    d.nav("Shows")
    d.click_card("/shows/winter-heroes", "Winter Heroes card")
    d.read_fact("seasons", r"Seasons\s*\n?\s*\d+")
    d.read_fact("episodes", r"Episodes\s*\n?\s*\d+")
    d.note("first_episodes", str(re.findall(
        r"S1\s*\n?\s*E(\d+)\s*\n?\s*([^\n]+)", d.body_text())[:4]))
    d.nav("Shows")
    d.select("#discipline", "Snowboarding", "discipline=Snowboarding")
    d.submit(".filter-actions button", "Filter")
    d.read_fact("snow_shows_count", r"\d+ shows")
    first = d.page.locator(".card").first
    first.click()
    d.step("click", "first snowboarding show")
    d.note("first_snow_show", d.body_text().split("\n")[0][:100])
    d.read_fact("first_snow_eps", r"Episodes\s*\n?\s*\d+")
    d.nav("Shows")
    d.click('.pager a:has-text("Next")', "Shows page 2")
    d.click_card("/shows/no-contest", "No Contest card")
    d.read_fact("nocontest_discipline", r"Discipline\s*\n?\s*([^\n]+)")
    d.read_fact("nocontest_episodes", r"Episodes\s*\n?\s*\d+")
    d.nav("Shows")
    d.click_card("/shows/inside-pro-surfing", "Inside Pro Surfing card")
    d.read_fact("ips_seasons", r"Seasons\s*\n?\s*\d+")
    d.read_fact("ips_episodes", r"Episodes\s*\n?\s*\d+")
    d.nav("Shows")
    d.select("#discipline", "Snowboarding", "discipline=Snowboarding")
    d.submit(".filter-actions button", "Filter")
    second = d.page.locator(".card").nth(1)
    d.note("second_snow_show", second.inner_text().split("\n")[1] if second.count() else "")
    second.click()
    d.step("click", "second snowboarding show")
    d.read_fact("second_snow_eps", r"Episodes\s*\n?\s*\d+")
    return {}


def t9(d: Drive) -> dict:
    d.goto_home()
    d.nav("Stories")
    d.select("#discipline", "Dance", "topic=Dance")
    d.submit(".filter-actions button", "Filter")
    d.click_card("/stories/jreamz-wins-2026-red-bull-dance-your-style-national-final",
                 "JREAMZ story card")
    text = d.body_text()
    d.read_fact("final_city", r"national stage was set in ([^\n,]+)")
    d.read_fact("winner_age", r"\d+-year-old phenom [A-Z]+")
    d.read_fact("home_state", r"Arizona-based dancer")
    d.nav("Stories")
    d.select("#discipline", "Games", "topic=Games")
    d.submit(".filter-actions button", "Filter")
    d.read_fact("games_count", r"\d+ stories")
    d.click_card("/stories/gta-6-surprising-facts", "GTA 6 story card")
    d.note("gta_fact", str(re.findall(r"[^\n]*GTA[^\n]*", d.body_text())[:3]))
    d.nav("Stories")
    d.select("#discipline", "Cycling", "topic=Cycling")
    d.submit(".filter-actions button", "Filter")
    d.click_card("/stories/uci-world-championships-explained", "UCI explainer card")
    d.note("rainbow_fact", str(re.findall(r"[^\n]*rainbow jersey[^\n]*",
                                           d.body_text())[:2]))
    d.nav("Stories")
    d.click(".grid .card", "newest story card")
    d.note("newest_story", d.body_text().split("\n")[0][:120])
    return {}


def t10(d: Drive) -> dict:
    d.goto_home()
    login(d, ALICE)
    d.nav("Shop")
    d.select("#category", "headwear", "category=headwear")
    d.select("#vendor", "Oracle Red Bull Racing", "vendor=ORBR")
    d.select("#sort", "price_asc", "sort price asc")
    d.submit(".filter-actions button", "Filter")
    first = d.page.locator(".card").first
    title = first.inner_text().split("\n")[1] if first.count() else ""
    m = re.search(r"\$([0-9.]+)", first.inner_text())
    d.note("cheapest_headwear", f"{title} ${m.group(1) if m else ''}")
    first.click()
    d.step("click", "cheapest headwear product")
    d.select("#variant_id", "@first", "size option")
    d.fill("#quantity", "2", "quantity 2")
    d.submit('.form-card button[type="submit"]', "Add to cart")
    d.click_link("/shop/checkout", "Checkout")
    d.fill("#ship_name", "Alice Johnson", "ship name")
    d.fill("#ship_email", "alice.j@test.com", "ship email")
    d.fill("#address", "1 Main St", "address")
    d.fill("#city", "Seattle", "city")
    d.fill("#zip", "98101", "zip")
    d.submit('.form-card button[type="submit"]', "Place order")
    m = re.search(r"(RB-\d+)", d.body_text())
    order = m.group(1) if m else ""
    d.note("order_number", order)
    d.read_fact("total", r"Total\s*\n?\s*\$[0-9.]+")
    return {"order_number": order}


def t11(d: Drive) -> dict:
    d.goto_home()
    d.nav("Shop")
    d.click_card("/shop/oracle-red-bull-racing-classic-longsleeve-polo-copy",
                 "Classic Hoodie card")
    d.read_fact("material", r"\d+% Cotton[^\n]*")
    d.read_fact("xs_price", r"XS[^\n]*\$[0-9.]+")
    d.read_fact("category", r"(tops|Top|Tops|headwear)")
    d.nav("Shop")
    d.select("#sort", "price_asc", "sort price asc")
    d.submit(".filter-actions button", "Filter")
    first = d.page.locator(".card").first
    first.click()
    d.step("click", "cheapest item in shop")
    d.note("cheapest_overall", d.body_text().split("\n")[0][:100])
    d.read_fact("cheapest_price", r"\$[0-9.]+")
    d.read_fact("cheapest_category", r"(Accessories|Headwear|Tops|Bags)")
    d.nav("Shop")
    d.select("#category", "headwear", "category=headwear")
    d.submit(".filter-actions button", "Filter")
    d.read_fact("headwear_count", r"\d+ products")
    d.nav("Shop")
    d.select("#vendor", "Red Bull Rampage", "vendor=Rampage")
    d.submit(".filter-actions button", "Filter")
    d.read_fact("rampage_count", r"\d+ products")
    d.nav("Shop")
    d.select("#category", "bags", "category=bags")
    d.submit(".filter-actions button", "Filter")
    d.read_fact("bags_count", r"\d+ products")
    return {}


def t12(d: Drive) -> dict:
    d.goto_home()
    d.nav("Shop")
    d.select("#vendor", "FC Red Bull Salzburg", "vendor=FC Salzburg")
    d.submit(".filter-actions button", "Filter")
    d.read_fact("count", r"\d+ products")
    d.select("#sort", "price_asc", "sort price asc")
    d.submit(".filter-actions button", "Filter")
    first = d.page.locator(".card").first
    d.note("cheapest", first.inner_text()[:120] if first.count() else "")
    first.click()
    d.step("click", "cheapest Salzburg product")
    d.read_fact("category", r"(Sticker|Magnet|Bottle|Cap|Beanie|T-Shirt|Hoodie|Jacket|Polo|Jersey|Bottle|Keyring)")
    d.select("#variant_id", "@first", "size option")
    d.submit('.form-card button[type="submit"]', "Add to cart")
    d.read_fact("subtotal", r"Total\s*\n?\s*\$[0-9.]+")
    d.nav("Shop")
    d.select("#vendor", "FC Red Bull Salzburg", "vendor=FC Salzburg")
    d.select("#sort", "price_asc", "sort price asc")
    d.submit(".filter-actions button", "Filter")
    cards = d.page.locator(".card")
    cards.nth(1).click()
    d.step("click", "second-cheapest Salzburg product")
    d.select("#variant_id", "@first", "size option")
    d.submit('.form-card button[type="submit"]', "Add to cart")
    d.read_fact("subtotal2", r"Total\s*\n?\s*\$[0-9.]+")
    d.submit(".cart-table form[action*='remove'] button", "Remove first item")
    d.note("cart_after", "one item" if "Remove" in d.body_text() else "empty")
    return {}


def t13(d: Drive) -> dict:
    d.goto_home()
    login(d, BOB)
    d.click_link("/account", "Bob's account")
    text = d.body_text()
    m = re.search(r"(RB[A-Z0-9]+)", text)
    d.note("reg_code", m.group(1) if m else "")
    d.read_fact("event_date", r"October 17, 2026")
    d.read_fact("ticket_type", r"registration")
    # remove the favorited show
    d.click_link("/shows/inside-pro-surfing", "favorited show link")
    d.submit(".side-panel form button", "Remove from favorites")
    # add the Iowa motocross event
    events_filter(d, discipline="Motocross")
    d.click_card("/events/red-bull-barn-find-open", "Barn Find Open card")
    d.read_fact("venue", r"Oak Ridge MX Track[^\n]*")
    d.submit(".side-panel form button", "Save to favorites")
    d.click_link("/account", "Bob's account")
    d.note("favorites_now", str(re.findall(r"(Event|Film|Show|Story|Athlete)\n",
                                           d.body_text())))
    d.click_card("/stories/jreamz-wins-2026-red-bull-dance-your-style-national-final",
                 "Bob's favorited story")
    d.read_fact("story_topic", r"Dance")
    return {}


def t14(d: Drive) -> dict:
    d.goto_home()
    login(d, CAROL)
    d.click_link("/account", "Carol's account")
    d.note("existing_favs", str(re.findall(r"(Wings Cup|9191)", d.body_text())))
    events_filter(d, discipline="Motocross")
    d.click_card("/events/red-bull-barn-find-open", "Barn Find Open card")
    d.submit(".side-panel form button", "Save to favorites")
    d.click_link("/account", "Carol's account")
    d.note("barn_favorited", "yes" if "Barn Find Open" in d.body_text() else "no")
    d.nav("Films")
    d.click_card("/films/9191", "9191 film card")
    d.read_fact("runtime", r"\d+ min")
    d.submit(".side-panel form button", "Save to favorites")
    return {}


def t15(d: Drive) -> dict:
    d.goto_home()
    events_filter(d, country="DE", status="past")
    rows = re.findall(r"(Nürburgring|Sachsenring|Hockenheimring|Fürstlich Drehna|"
                      r"Stuttgart|Oschersleben|Gaildorf)[^\n]*", d.body_text())
    d.note("past_de", str(rows))
    d.click_card("/events/red-bull-stuttgart-cerro-abajo", "Stuttgart Cerro Abajo card")
    d.note("downhill_desc", str(re.findall(r"[^\n]*(?:stairs|streets|narrow)[^\n]*",
                                           d.body_text())[:2]))
    d.back("back to past list")
    d.click_card("/events/dtm-sachsenring", "Sachsenring card")
    d.read_fact("sachsenring_dates", r"September 12[^\n]*")
    d.back("back to past list")
    d.click_card("/events/adac-mx-masters-fuerstlich-drehna", "Fürstlich Drehna card")
    d.read_fact("drehna_dates", r"September 26[^\n]*")
    d.read_fact("drehna_discipline", r"Motocross")
    d.back("back to past list")
    d.click_card("/events/drift-masters-germany", "Drift Masters card")
    d.read_fact("drift_venue", r"DEKRA Lausitzring[^\n]*|Venue\s*\n?\s*([^\n]+)")
    events_filter(d, country="DE")
    d.read_fact("de_total", r"\d+ events")
    d.read_fact("de_upcoming", r"\d+ events")
    return {}


def t16(d: Drive) -> dict:
    d.goto_home()
    events_filter(d, country="US", status="upcoming")
    d.read_fact("us_upcoming_count", r"\d+ events")
    first = d.page.locator(".card").first
    d.note("earliest", first.inner_text().split("\n")[1] if first.count() else "")
    d.click_card("/events/red-bull-wings-cup-united-states-2026", "Wings Cup card")
    d.read_fact("standfirst", r"Play EA SPORTS FC[^\n]*")
    d.read_fact("fee", r"Registration\s*\n?\s*\$?(Free|\d+)")
    events_filter(d, country="US", status="upcoming")
    d.click_card("/events/red-bull-foam-wreckers-narragansett", "Narragansett card")
    d.note("badge", "yes" if "Registrations open" in d.body_text() else "no")
    d.read_fact("venue", r"Narragansett Town Beach")
    events_filter(d, country="US", status="upcoming")
    d.click_card("/events/red-bull-rapid-release", "Rapid Release card")
    d.read_fact("rapid_venue", r"Walk-On's[^\n]*")
    d.read_fact("rapid_fee", r"Free")
    return {}


def t17(d: Drive) -> dict:
    d.goto_home()
    d.nav("Energy Drinks")
    d.click_card("/energydrink/red-bull-amber-edition", "Amber card")
    d.read_fact("amber_flavor", r"Strawberry[^\n]*")
    d.nav("Energy Drinks")
    d.click_card("/energydrink/red-bull-yellow-edition", "Yellow card")
    d.read_fact("yellow_flavor", r"Tropical")
    d.nav("Energy Drinks")
    d.click_card("/energydrink/red-bull-red-edition", "Red card")
    d.read_fact("red_flavor", r"Watermelon")
    d.nav("Energy Drinks")
    d.click_card("/energydrink/red-bull-energy-drink", "Original card")
    d.note("original_sizes", str(re.findall(r"(\d+\.?\d* fl oz)", d.body_text())))
    d.nav("Energy Drinks")
    d.click_card("/energydrink/red-bull-peach-edition-sugarfree", "Peach Sugarfree card")
    d.read_fact("peach_sf_caffeine", r"\d+ mg of caffeine")
    d.nav("Energy Drinks")
    d.click_card("/energydrink/red-bull-sugarfree", "Sugarfree flagship card")
    d.note("sf_sizes", str(re.findall(r"(\d+\.?\d* fl oz)", d.body_text())))
    d.nav("Energy Drinks")
    d.click_card("/energydrink/red-bull-summer-edition", "Summer Edition card")
    d.read_fact("summer_flavor", r"Sudachi Lime")
    return {}


def t18(d: Drive) -> dict:
    d.goto_home()
    events_filter(d, country="US", status="past")
    d.click_card("/events/red-bull-dance-your-style-national-final-usa",
                 "Dance Your Style USA card")
    d.read_fact("venue", r"Tampa, FL")
    d.read_fact("date", r"September 19, 2026")
    d.click_card("/stories/jreamz-wins-2026-red-bull-dance-your-style-national-final",
                 "related story card")
    d.read_fact("final_city", r"national stage was set in ([^\n,]+)")
    d.read_fact("winner", r"\d+-year-old phenom [A-Z]+")
    events_filter(d, country="CH")
    d.click_card("/events/red-bull-dance-your-style-world-final-2026-zurich",
                 "World Final card")
    d.read_fact("world_final_venue", r"Hallenstadion[^\n]*")
    d.read_fact("world_final_date", r"October 24, 2026")
    events_filter(d, country="US", status="past")
    d.click_card("/events/red-bull-bc-one-cypher-usa-national-final", "BC One Cypher card")
    d.read_fact("bcone_venue", r"Port Pavilion[^\n]*")
    return {}


def t19(d: Drive) -> dict:
    d.goto_home()
    d.nav("Athletes")
    d.select("#discipline", "Supercross", "discipline=Supercross")
    d.submit(".filter-actions button", "Filter")
    d.click_card("/athletes/eli-tomac", "Eli Tomac card")
    d.read_fact("nationality", r"Nationality\s*\n?\s*([^\n]+)")
    d.read_fact("dob", r"Date of birth\s*\n?\s*([^\n]+)")
    d.note("grew_up", str(re.findall(r"[^\n]*Cortez, Colorado[^\n]*",
                                     d.body_text())[:1]))
    d.nav("Athletes")
    d.select("#discipline", "BMX Flatland", "discipline=BMX Flatland")
    d.submit(".filter-actions button", "Filter")
    d.click_card("/athletes/terry-adams", "Terry Adams card")
    d.read_fact("terry_birthplace", r"Birthplace\s*\n?\s*([^\n]+)")
    d.nav("Stories")
    d.select("#discipline", "Supercross", "topic=Supercross")
    d.submit(".filter-actions button", "Filter")
    d.click_card("/stories/supercross-vs-motocross", "supercross vs motocross card")
    d.note("difference_fact", str(re.findall(r"[^\n]*supercross[^\n]*",
                                             d.body_text(), re.I)[:3]))
    d.nav("Stories")
    d.select("#discipline", "Skateboarding", "topic=Skateboarding")
    d.submit(".filter-actions button", "Filter")
    d.read_fact("skate_story_count", r"\d+ stories")
    return {}


AUDITS = {i: f for i, f in [
    (0, t0), (1, t1), (2, t2), (3, t3), (4, t4), (5, t5), (6, t6),
    (7, t7), (8, t8), (9, t9), (10, t10), (11, t11), (12, t12),
    (13, t13), (14, t14), (15, t15), (16, t16), (17, t17), (18, t18),
    (19, t19)]}


def run(task_id: str, fn, out_root: Path) -> dict:
    print(f"\n=== {task_id} ===")
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1280, "height": 900})
        page = ctx.new_page()
        d = Drive(page, task_id, out_root / task_id)
        try:
            answer = fn(d)
            row = d.finish(answer)
        except Exception as e:                                  # noqa: BLE001
            row = d.finish({"error": str(e)})
            row["error"] = str(e)
        browser.close()
    print(f"  steps: {row['step_count']}  errors: {row['js_errors']}")
    return row


def main() -> None:
    only = None
    out_root = OUT_ROOT
    args = sys.argv[1:]
    if "--only" in args:
        only = int(args[args.index("--only") + 1])
    if "--out" in args:
        out_root = Path(args[args.index("--out") + 1])
    rows = {}
    for i, fn in sorted(AUDITS.items()):
        if only is not None and i != only:
            continue
        row = run(f"Red Bull--{i}", fn, out_root)
        rows[f"Red Bull--{i}"] = row
    summary = {k: {"steps": v["step_count"], "js_errors": v["js_errors"],
                   "answer": v.get("answer"), "error": v.get("error")}
               for k, v in rows.items()}
    (out_root / "audit_summary.json").parent.mkdir(parents=True, exist_ok=True)
    (out_root / "audit_summary.json").write_text(
        json.dumps(summary, indent=1, ensure_ascii=False), encoding="utf-8")
    print("\n== summary ==")
    for k, v in summary.items():
        print(f"  {k}: {v['steps']} steps" + (f"  ERROR: {v['error']}" if v.get("error") else ""))


if __name__ == "__main__":
    main()
