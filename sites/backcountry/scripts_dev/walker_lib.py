#!/usr/bin/env python3
"""Honest step-measuring walker for the backcountry mirror tasks.

Drives a real Chromium against the dev mirror and performs ONLY the actions
each task text requires (no shortcuts, no extra gestures). Step counting
follows the honest atomic caliber:

  - every fill/click/select/navigation the task text requires = 1 step
  - hidden inputs (CSRF tokens) never counted
  - reads are free
  - +1 for composing the final answer
  - the initial page load is free

Per task it writes runs/<task_id>/ with trajectory.json (steps, urls,
screenshots), the collected facts (ground truth for the verifiers) and the
measured honest step count. Two independent rounds are run; the task texts
must measure >= 15 in BOTH rounds.

Usage:  python3 validate_tasks.py --base http://localhost:43117 \
            --out runs --round 1 [--only 0 3 7]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
STEP_PAD = 3  # "000"


class Walk:
    def __init__(self, page, base, out_dir):
        self.page = page
        self.base = base
        self.out = Path(out_dir)
        self.steps = []
        self.facts = {}
        self.shot_no = 0

    # ---------------------------------------------------------- utilities --
    def url(self, path):
        return self.base + path

    def shot(self, label):
        self.shot_no += 1
        name = f"step_{self.shot_no:03d}.png"
        try:
            self.page.screenshot(path=str(self.out / "screenshots" / name))
        except Exception:
            pass
        return name

    def do(self, action, url="", note=""):
        """Record one honest atomic action with its evidence screenshot."""
        shot = self.shot(action)
        self.steps.append({"action": action, "url": url or self.page.url,
                           "note": note, "screenshot": shot})
        return shot

    # ---------------------------------------------------------- primitives --
    def goto(self, path, note="navigate"):
        self.page.goto(self.url(path), wait_until="domcontentloaded")
        self.page.wait_for_timeout(400)
        return self.do(note, note=f"open {path}")

    def click(self, selector, note, timeout=8000):
        self.page.click(selector, timeout=timeout)
        self.page.wait_for_timeout(300)
        return self.do(note)

    def click_role(self, name, note):
        self.page.get_by_role("link", name=name).first.click(timeout=8000)
        self.page.wait_for_timeout(300)
        return self.do(note)

    def fill(self, selector, value, note):
        self.page.fill(selector, value)
        return self.do(note)

    def select(self, selector, value, note):
        self.page.select_option(selector, value)
        self.page.wait_for_timeout(400)
        return self.do(note)

    def press(self, selector, key, note):
        self.page.press(selector, key)
        self.page.wait_for_timeout(400)
        return self.do(note)

    def read_text(self, selector):
        try:
            return self.page.inner_text(selector).strip()
        except Exception:
            return ""

    def body_text(self):
        return re.sub(r"\s+", " ", self.page.inner_text("body"))

    # ---------------------------------------------------------- composites --
    def search(self, term):
        self.fill('input[name="q"]', term, f"type search '{term}'")
        self.press('input[name="q"]', "Enter", "run search")

    def login(self, email, password):
        self.click_role("Sign In", "open sign-in")
        self.fill('input[name="email"]', email, "enter email")
        self.fill('input[name="password"]', password, "enter password")
        self.click('button:has-text("Sign In")', "submit login")

    def add_to_cart(self, size_selector=None, color_selector=None,
                    qty=None, note_prefix=""):
        if color_selector:
            self.click(color_selector, f"{note_prefix}select color")
        if size_selector:
            self.click(size_selector, f"{note_prefix}select size")
        if qty:
            self.fill('input[name="quantity"]', str(qty), "set quantity")
        self.click('button:has-text("Add to Cart")', "add to cart")
        self.page.wait_for_timeout(500)

    def checkout_guest(self, email, name, line1, city, state, zipc, phone,
                       card="4111111111111111", expiry="01/28", cvc="123",
                       method="standard", invalid_card=None):
        self.click_role("Proceed to Checkout", "go to checkout")
        self.fill('input[name="email"]', email, "enter email")
        self.fill('input[name="full_name"]', name, "enter full name")
        self.fill('input[name="line1"]', line1, "enter street address")
        self.fill('input[name="city"]', city, "enter city")
        self.select('select[name="state"]', state, "choose state")
        self.fill('input[name="zip"]', zipc, "enter ZIP")
        self.fill('input[name="phone"]', phone, "enter phone")
        if method == "express":
            self.check('input[name="shipping_method"][value="express"]',
                       "choose express shipping")
        self.fill('input[name="card_name"]', name, "enter card name")
        if invalid_card:
            self.fill('input[name="card"]', invalid_card, "enter invalid card")
        else:
            self.fill('input[name="card"]', card, "enter card number")
        self.fill('input[name="expiry"]', expiry, "enter expiry")
        self.fill('input[name="cvc"]', cvc, "enter CVC")

    def check(self, selector, note):
        self.page.check(selector)
        return self.do(note)

    # -------------------------------------------------- cart row helpers --
    def cart_set_qty(self, row_text, qty, note):
        line = self.page.locator(f'.cart-line:has-text("{row_text}")')
        line.locator('input[name="quantity"]').fill(str(qty))
        self.do(note)
        line.locator('button:has-text("Update")').click()
        self.page.wait_for_timeout(700)
        self.do("update quantity")

    def cart_remove(self, row_text, note):
        self.page.locator(f'.cart-line:has-text("{row_text}")') \
            .locator('button:has-text("Remove")').click()
        self.page.wait_for_timeout(700)
        self.do(note)

    def read_summary(self, label):
        import re as _re
        t = self.body_text()
        m = _re.search(_re.escape(label) + r"\s*(-?\$?[0-9][0-9,]*\.?\d\d?)", t)
        if m:
            v = m.group(1).lstrip("-")
            return ("$" + v) if not v.startswith("$") else v
        if _re.search(_re.escape(label) + r"\s*FREE", t):
            return "FREE"
        return "?"

    def read_order_number(self):
        import re as _re
        m = _re.search(r"order number is (\d+)", self.body_text())
        return m.group(1) if m else "?"

    def read_count(self, pattern):
        import re as _re
        m = _re.search(pattern, self.body_text())
        return m.group(1) if m else "?"

    def read_error(self):
        t = self.body_text()
        for known in ("Enter a valid 16-digit card number.",
                      "Fill in every shipping address field.",
                      "Enter a valid email address for your order.",
                      "Enter the card expiry as MM/YY.",
                      "Enter the 3- or 4-digit card security code.",
                      "Enter a valid ZIP code"):
            if known in t:
                return known
        return "?" 

    def place_order(self):
        self.click('button:has-text("Place Order")', "place order")
        self.page.wait_for_timeout(700)

    # ------------------------------------------------------------- output --
    def finish(self, task_id, answer):
        self.do("compose final answer", note="compose")
        traj = {
            "task_id": task_id,
            "start_url": self.first_url,
            "terminated": True,
            "termination_reason": "agent_done",
            "final_answer": answer,
            "steps": self.steps,
            "facts": self.facts,
            "honest_steps": len(self.steps),
        }
        (self.out / "trajectory.json").write_text(
            json.dumps(traj, indent=1), encoding="utf-8")
        return traj

    first_url = None


def register_first(walk, path="/"):
    walk.first_url = walk.url(path)
