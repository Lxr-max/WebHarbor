#!/usr/bin/env python3
"""Browser honest-walk measurement for the verizon mirror (scripts_dev/walk_tasks.py).

Second, independent measured round: drives every task's honest path with a
real headless Chromium against the LIVE dev container (default
http://127.0.0.1:43111), with a per-task control-plane reset + fresh
browser context. Caliber identical to the test-client audit:

- atomic  = navigation actions after the home load: link clicks, form
            fills/selects, submits (each fill/select = 1, each submit = 1);
- reads   = one per reported fact, asserted present in the rendered page;
- A       = atomic + reads.

Writes walk_results.json + per-task screenshots to evidence_out/.

Run: python3.11 walk_tasks.py [--base http://127.0.0.1:43111] [--control http://127.0.0.1:44111]
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
import time
import urllib.request

from playwright.sync_api import sync_playwright

OUT = pathlib.Path(__file__).resolve().parents[1] / "walkthrough"
OUT.mkdir(exist_ok=True)


def reset_site(control: str, token: str):
    req = urllib.request.Request(f"{control}/reset/verizon", method="POST",
                                 headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=90) as r:
        r.read()


class BrowserWalk:
    def __init__(self, page):
        self.page = page
        self.atomic = 0
        self.reads = 0
        self.fails = []

    def goto(self, path, count=1):
        self.page.goto(path, wait_until="domcontentloaded", timeout=30000)
        self.page.wait_for_timeout(400)
        self.atomic += count

    def click(self, selector):
        self.page.click(selector, timeout=15000)
        self.page.wait_for_timeout(400)
        self.atomic += 1

    def select(self, selector, value):
        self.page.select_option(selector, value, timeout=15000)
        self.atomic += 1

    def fill(self, selector, value):
        self.page.fill(selector, value, timeout=15000)
        self.atomic += 1

    def submit(self, selector="button[type=submit]"):
        self.page.click(selector, timeout=15000)
        self.page.wait_for_timeout(900)
        self.atomic += 1

    def body(self):
        return self.page.inner_text("body")

    def read(self, needle, what=None):
        if needle not in self.body():
            self.fails.append(f"read miss: {needle!r} ({what or 'fact'} not on page)")
        self.reads += 1

    def read_count(self, pattern, expected, what):
        found = len(re.findall(pattern, self.body()))
        if found != expected:
            self.fails.append(f"count miss: {what} = {found}, expected {expected}")
        self.reads += 1

    def score(self):
        return self.atomic + self.reads


def walk(w: BrowserWalk, base: str):
    """Drive the 20 honest paths; mirrors validate_tasks.py's walks."""
    idx = int(w.task_id.split("--")[1])
    home = base
    if idx == 0:
        w.goto(f"{home}/plans/")
        w.read("$30", "per-line price")
        w.select("#lines", "4"); w.submit()
        w.read("$120", "4-line total")
        w.read("/month for 4 lines", "line-count confirmation")
        w.read("After AutoPay and $15/mo switch discount", "price note")
        w.read("5G Ultra Wideband", "feature 1")
        w.read("Satellite texting", "feature 2")
        w.read("10 GB mobile hotspot data", "feature 3")
        w.read("Up to 12 lines per account", "max lines")
        w.read("ACH bank draft or the Verizon Visa Card", "autopay methods")
        w.read("Bring", "phone option 1")
        w.read("Upgrade to the latest phone every year", "phone option 2")
        w.read("$80/mo when you switch to Verizon with Simplicity Plan", "hero price")
    elif idx == 1:
        w.goto(f"{home}/prepaid/")
        for needle, what in [("$30", "T&T autopay"), ("$35", "T&T base"),
                            ("$45", "15GB base"), ("$50", "Unlimited autopay"),
                            ("$60", "Unlimited base / UP autopay"),
                            ("$70", "UP base"), ("$65.00", "UP after 3 months"),
                            ("$60.00", "UP after 9 months"), ("25 GB", "UP hotspot"),
                            ("$10/mo", "autopay discount $45+"),
                            ("$5/mo", "T&T autopay discount"),
                            ("iPhone 16e for $349.99", "promo device"),
                            ("Offer ends 9/30/26", "promo end date"),
                            ("3-year price lock guarantee", "price lock length")]:
            w.read(needle, what)
    elif idx == 2:
        w.goto(f"{home}/prepaid/")
        w.read("$30", "T&T autopay price")
        w.read("Talk & Text", "T&T name")
        w.read("$35", "15GB autopay price")
        w.read("15 GB", "15GB name")
        w.read("Includes 5G Ultra Wideband", "Unlimited 5G UW feature")
        w.read("Unlimited", "cheapest 5G UW plan name")
        w.read("Starting at $60.00/mo", "base price")
        w.read("$50", "autopay price")
        w.read("5 GB", "hotspot allowance")
        w.read("Unlimited talk, text and data", "other feature")
        w.read("3-year price lock guarantee", "price lock")
        w.goto(f"{home}/plans/")
        w.read("$30", "postpaid per-line price")
        w.read("After AutoPay and $15/mo switch discount", "postpaid discounts")
        w.read("Satellite texting", "postpaid feature")
    elif idx == 3:
        w.goto(f"{home}/smartphones/")
        w.select("#brand", "Samsung"); w.select("#sort", "price-asc"); w.submit()
        w.read("Samsung Galaxy A17 5G", "cheapest Samsung name")
        w.click("text=Samsung Galaxy A17 5G")
        w.read("Full retail price: $249.99", "cheapest retail")
        w.read("$6.94/mo", "36-month price")
        w.read("128 GB", "storage from compare table")
        w.read("4.2 out of 5 rating", "rating")
        w.read("3.5K", "review count")
        w.read("Up to 29 hours", "battery life")
        w.goto(f"{home}/smartphones/?brand=Samsung&sort=price-desc")
        w.read("Samsung Galaxy Z Fold8 Ultra", "most expensive name")
        w.read("Retail price: $2,099.99", "most expensive retail")
    elif idx == 4:
        w.goto(f"{home}/smartphones/apple-iphone-18-pro/")
        for needle, what in [("$99.99/mo", "12-month price"),
                             ("$49.99/mo", "24-month price"),
                             ("$24.99/mo", "48-month price"),
                             ("Full retail price: $1,199.99", "full retail"),
                             ("Burgundy", "color 1"), ("Glacier", "color 2"),
                             ("256 GB", "storage 1"), ("2 TB", "storage 2"),
                             ("Tue, Sep 29 - Fri, Oct 9", "ship window"),
                             ("4.2 out of 5 rating", "rating"), ("93", "review count"),
                             ("Typical use: Up to 24 hours", "battery life line"),
                             ("Up to 30 hours", "18 Pro Max battery"),
                             ("$210.00", "cracked trade-in value")]:
            w.read(needle, what)
    elif idx == 5:
        w.goto(f"{home}/smartphones/motorola-moto-g-2026/")
        w.click("text=Configure this device")
        w.page.check('input[name=protection][value="Verizon Mobile Protect"]')
        w.atomic += 1
        w.submit()
        w.read("Verizon Mobile Protect", "protection in cart")
        w.goto(f"{home}/checkout/")
        w.fill("input[name=name]", "Jordan Pratt")
        w.fill("input[name=email]", "jordan.pratt@example.com")
        w.fill("input[name=street]", "88 Pine Street")
        w.fill("input[name=city]", "Seattle")
        w.fill("input[name=state]", "WA")
        w.fill("input[name=zip]", "98101")
        w.submit()
        if not re.search(r"Order VZW\d+", w.body()):
            w.fails.append("order confirmation number not found")
        w.reads += 1
        w.read("$54.77/mo", "monthly total")
        w.read("Ships between", "delivery window")
        w.read("($17.00/mo)", "protection monthly")
        w.read("($30.00/mo)", "plan monthly")
    elif idx == 6:
        w.goto(f"{home}/trade-in/")
        w.read("Mail your old device to us within 30 days", "mail-by")
        w.read("instant credit", "credit option 1")
        w.read("account credit", "credit option 2")
        w.read("gift card", "credit option 3")
        w.goto(f"{home}/trade-in/estimate/")
        w.select("select[name=device]", "Google Pixel 11")
        w.select("select[name=condition]", "Good")
        w.submit()
        w.read("$300.00", "Pixel 11 good value")
        w.read("minor wear, fully functional", "good definition")
        w.goto(f"{home}/trade-in/estimate/")
        w.select("select[name=device]", "Motorola moto g - 2026")
        w.select("select[name=condition]", "Good")
        w.submit()
        w.read("$70.00", "moto g good value")
    elif idx == 7:
        w.goto(f"{home}/stores/washington/")
        w.click("text=Seattle")
        w.read_count(r"Verizon Company Store|Big 6 - Business", 6, "Seattle store count")
        w.read("Big 6 - Business", "non-company store type")
        w.read("Verizon Company Store — Seattle Northgate", "company store name")
        w.read("401 NE Northgate Way", "street address")
        w.read("Hours today-style (Mon): 10:00 AM 08:00 PM", "Monday hours")
        w.read("206-367-0687", "phone")
        w.click("text=View store details")
        w.read("10:00 AM 06:00 PM", "Sunday hours")
        w.read("Appointments accepted", "accepts appointments")
        w.read("Seattle-Everett, WA", "market name")
        w.goto(f"{home}/stores/washington/bellevue/")
        w.read_count(r"Verizon Company Store|Big 6 - Business", 2, "Bellevue store count")
        w.goto(f"{home}/store/r00000328070/")
        w.read("Express Pickup Locker", "Bellevue locker store service")
    elif idx == 8:
        w.goto(f"{home}/stores/washington/seattle/")
        w.read("Verizon Company Store — Seattle Northgate", "store name")
        w.click("text=View store details")
        w.read("401 NE Northgate Way", "address")
        w.read("10:00 AM 06:00 PM", "Sunday hours")
        w.read("206-367-0687", "phone")
        w.click("text=Schedule an appointment")
        w.fill("input[name=name]", "Sam Rivera")
        w.fill("input[name=email]", "sam.rivera@example.com")
        w.fill("input[name=phone]", "206-555-0139")
        w.select("select[name=topic]", "Device trade-in")
        w.fill("input[name=date]", "2026-10-06")
        w.select("select[name=time]", "02:00 PM")
        w.submit()
        if not re.search(r"Confirmation APT\d+", w.body()):
            w.fails.append("appointment confirmation number not found")
        w.reads += 1
        w.read("2026-10-06", "appointment date")
        w.read("02:00 PM", "appointment time")
        w.read("Device trade-in", "topic")
    elif idx in (9, 10, 11, 12, 13, 14, 17):
        # account tasks: log in first
        emails = {9: "alice.j@test.com", 10: "bob.c@test.com", 11: "carol.d@test.com",
                 12: "alice.j@test.com", 13: "dana.k@test.com", 14: "alice.j@test.com",
                 17: "bob.c@test.com"}
        w.goto(f"{home}/account/login")
        w.fill("input[name=email]", emails[idx])
        w.fill("input[name=password]", "TestPass123!")
        w.submit()
        if "Account overview" not in w.body():
            w.fails.append("login failed")
        if idx == 9:
            w.read("8472-0913", "account number")
            w.read("postpaid", "account type")
            w.click("text=View bill detail")
            w.read("Sep 2026", "bill period")
            w.read("$160.62", "bill total")
            w.read("2026-10-13", "due date")
            w.read("due", "status")
            w.read("Simplicity Plan — Alice", "charge 1")
            w.read("Device payment — Alice", "charge 2")
            w.read("Verizon Mobile Protect — Alice", "protection charge line")
            w.read("Simplicity Plan — Mike (partner line)", "charge 4")
            w.read("Device payment — Mike (partner line)", "charge 5")
            w.read("Taxes, surcharges and fees", "taxes line")
            w.goto(f"{home}/account/")
            w.read("Lines on this account (2)", "line count")
        elif idx == 10:
            w.goto(f"{home}/account/pay/")
            w.read("Sep 2026", "bill period")
            w.read("2026-10-13", "due date")
            w.read("$118.17", "bill total")
            w.read("Bank account (ACH ending 8891)", "other method 1")
            w.read("Verizon Visa Card ending 0057", "other method 2")
            w.submit()
            if not re.search(r"Confirmation PMT\d+", w.body()):
                w.fails.append("payment confirmation number not found")
            w.reads += 1
            w.read("$118.17", "paid amount")
            w.read("Card ending 4242", "method")
            w.goto(f"{home}/account/bills/")
            w.read("Aug 2026", "last paid bill period")
        elif idx == 11:
            w.read("Auto Pay: Off", "autopay status before")
            w.read("Paper-free billing: Off", "paper status before")
            w.click("text=Manage Auto Pay & paper-free billing")
            w.read("$10/mo per-line discount", "autopay discount")
            w.read("bank draft or the Verizon Visa Card", "eligible methods")
            w.read("Receive bills and notifications by email", "paper-free description")
            w.page.check("input[name=autopay]")
            w.page.check("input[name=paper_free]")
            w.atomic += 2
            w.submit()
            w.read("Auto Pay and billing preferences updated.", "confirmation message")
            w.read("Auto Pay: Enrolled", "new autopay status")
            w.read("Paper-free billing: On", "new paper status")
        elif idx == 12:
            w.goto(f"{home}/account/usage/")
            w.read("31.4", "Alice data used")
            w.read("9.6", "Alice hotspot used")
            w.read("10 GB", "hotspot cap")
            w.read("12.2", "Mike data used")
            w.read("1.1", "Mike hotspot used")
            w.read("Simplicity Plan", "plan name")
            w.read("$30.00/mo", "plan monthly cost")
            w.read("10 GB mobile hotspot allowance", "plan hotspot allowance")
            w.read("Prepaid Unlimited includes 5 GB", "prepaid Unlimited allowance")
            w.read("Unlimited Plus 25 GB", "prepaid UP allowance")
            w.read("Sep 2026", "cycle label")
        elif idx == 13:
            w.read("Unlimited Plus ($70.00/mo)", "current plan")
            w.click("text=Change plan")
            w.read("Simplicity Plan — $30.00/mo", "option 1")
            w.read("Talk & Text — $35.00/mo", "option 2")
            w.read("15 GB — $45.00/mo", "option 3")
            w.read("Unlimited — $60.00/mo", "option 4")
            w.read("Unlimited Plus — $70.00/mo", "option 5")
            w.page.check("input[name=plan][value='4']")
            w.atomic += 1
            w.submit()
            w.read("Plan for Dana changed to Unlimited.", "confirmation message")
            w.read("Unlimited ($60.00/mo)", "new plan on overview")
            w.goto(f"{home}/account/usage/")
            w.read("5 GB", "new plan hotspot allowance")
        elif idx == 14:
            w.goto(f"{home}/smartphones/")
            w.select("#brand", "Samsung"); w.select("#sort", "price-asc"); w.submit()
            w.read("Samsung Galaxy A17 5G", "cheapest Samsung")
            w.goto(f"{home}/smartphones/samsung-galaxy-a17-5g/")
            w.read("Full retail price: $249.99", "retail price")
            w.goto(f"{home}/account/add-line/")
            w.fill("input[name=nickname]", "Mom")
            w.select("select[name=device]", "18")
            w.select("select[name=plan]", "1")
            w.submit()
            w.read("Lines on this account (3)", "line count after")
            w.read("New line added for Mom with Simplicity Plan.", "flash confirmation")
            w.read("$30.00/mo", "plan monthly")
        elif idx == 17:
            w.click("text=All orders")
            w.click("a:has-text('VZW')")
            body = w.body()
            m = re.search(r"(VZW\d+)", body)
            w.read(m.group(1) if m else "VZWMISSING", "order number")
            w.read("Samsung Galaxy A17 5G", "device")
            w.read("Navy Blue", "color")
            w.read("128 GB", "storage")
            w.read("In transit", "status")
            w.read("Arriving by Thu, Oct 1", "delivery estimate")
            w.read("2026-09-25", "placed date")
            w.read("$36.94/mo", "monthly total")
            w.goto(f"{home}/account/bills/")
            w.read("Aug 2026", "last paid bill period")
    elif idx == 15:
        w.goto(f"{home}/support/return-policy/")
        for needle, what in [("$50", "restocking fee"),
                             ("excluding Hawaii", "Hawaii exception"),
                             ("within 30 days of purchase", "return window"),
                             ("one exchange", "exchange count"),
                             ("like-new condition", "condition requirement"),
                             ("you will not receive a refund", "after-window rule"),
                             ("may have its own return/exchange policy", "retailer rule"),
                             ("Gift card returns", "gift card section"),
                             ("Standard monthly account service termination", "service termination")]:
            w.read(needle, what)
        w.goto(f"{home}/support/contact-us/")
        w.read("800-225-5499", "Sales number")
        w.read("8 AM - 10 PM ET (Mon - Sat)", "Sales hours")
        w.read("8 AM - 7 PM PDT (Mon - Sat)", "Account & billing hours")
        w.read("8 AM - 12 AM PDT (Sun - Sat)", "Technical support hours")
    elif idx == 16:
        w.goto(f"{home}/support/troubleshoot/")
        w.select("select[name=family]", "Google")
        w.select("select[name=issue]", "No service or cannot connect to the network")
        w.submit()
        w.read("Check the coverage map for your address.", "step 1")
        w.read("Toggle Airplane mode", "step 2")
        w.read("Reset network settings", "step 3")
        w.read("then restart the phone", "step 4")
        w.read("Still no service", "recommendation")
        w.read("delete and re-add it in My Verizon", "eSIM fix")
        w.select("select[name=family]", "Apple")
        w.select("select[name=issue]", "Battery drains too fast")
        w.submit()
        w.read("Open Settings and check Battery health", "Apple battery step 1")
        w.read("the battery needs service", "Apple battery resolution")
    elif idx == 18:
        w.goto(f"{home}/smartphones/apple-iphone-18-pro/")
        for needle, what in [("$33.33/mo", "18 Pro 36-month price"),
                             ("Full retail price: $1,199.99", "18 Pro retail"),
                             ("2 TB", "18 Pro max storage"),
                             ("Typical use: Up to 24 hours", "18 Pro battery"),
                             ("Super Retina XDR display", "18 Pro screen"),
                             ("4.2 out of 5 rating", "18 Pro rating"), ("93", "18 Pro reviews")]:
            w.read(needle, what)
        w.goto(f"{home}/smartphones/samsung-galaxy-s26-ultra/")
        for needle, what in [("$36.11/mo", "S26U 36-month price"),
                             ("Full retail price: $1,299.99", "S26U retail"),
                             ("512 GB", "S26U storage option"),
                             ("Up to 30.62 hrs", "S26U battery"),
                             ("4.8 out of 5 rating", "S26U rating"), ("18K", "S26U reviews")]:
            w.read(needle, what)
    elif idx == 19:
        w.goto(f"{home}/prepaid/")
        for needle, what in [("Starting at $60.00/mo", "Unlimited base"),
                             ("$55.00", "after 3 months"),
                             ("$50.00", "after 9 months"),
                             ("Auto Pay and loyalty discounts cannot be combined", "combine rule"),
                             ("$35", "15 GB autopay price"),
                             ("$20/mo when you add any Verizon Prepaid Unlimited phone plan", "multiline discount"),
                             ("5 GB", "Unlimited hotspot allowance"),
                             ("Unlimited talk, text and data", "feature Talk & Text lacks"),
                             ("void if lines are canceled or moved to an ineligible plan", "price lock void"),
                             ("3-year price lock guarantee", "price lock length"),
                             ("First month for $60.00/mo", "Unlimited first-month price"),
                             ("Unlimited Plus", "Unlimited Plus name"),
                             ("$60", "Unlimited Plus Auto Pay price")]:
            w.read(needle, what)
        w.goto(f"{home}/plans/")
        w.read("$30", "single postpaid line price")
        w.read("After AutoPay and $15/mo switch discount", "postpaid discounts")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:43111")
    parser.add_argument("--control", default="http://127.0.0.1:44111")
    parser.add_argument("--token-file", default="/tmp/wh_vz/token")
    args = parser.parse_args()
    token = pathlib.Path(args.token_file).read_text().strip()

    tasks = [json.loads(l) for l in
             (pathlib.Path(__file__).resolve().parents[1] / "tasks.jsonl")
             .read_text(encoding="utf-8").splitlines() if l.strip()]
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        for task in tasks:
            reset_site(args.control, token)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                           "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
                viewport={"width": 1440, "height": 2400})
            page = context.new_page()
            page.goto(args.base, wait_until="domcontentloaded", timeout=30000)
            w = BrowserWalk(page)
            w.task_id = task["id"]
            walk(w, args.base)
            a = w.score()
            shot = OUT / f"{task['id'].replace('.', '_')}.png"
            try:
                page.screenshot(path=str(shot), full_page=False)
            except Exception:
                pass
            results.append({"id": task["id"], "atomic": w.atomic, "reads": w.reads,
                            "A": a, "fails": w.fails})
            print(f"{task['id']:<16} atomic={w.atomic:>3} reads={w.reads:>3} A={a:>3}"
                  f"{' FAILS' if w.fails else ''}")
            context.close()
            time.sleep(0.4)
        browser.close()
    (OUT / "walk_results.json").write_text(json.dumps(results, indent=1),
                                           encoding="utf-8")
    total = sum(r["A"] for r in results)
    min_a = min(r["A"] for r in results)
    max_a = max(r["A"] for r in results)
    bad = [r for r in results if r["fails"] or r["A"] < 15]
    print(f"\ntasks={len(results)} min_A={min_a} max_A={max_a} total_A={total}")
    if bad:
        for r in bad:
            print("FAIL", r["id"], r["fails"][:4])
        return 1
    print("browser honest-walk audit: all 20 tasks >= 15, all premises resolved")
    return 0


if __name__ == "__main__":
    sys.exit(main())
