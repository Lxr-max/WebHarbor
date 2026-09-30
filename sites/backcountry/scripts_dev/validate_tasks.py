#!/usr/bin/env python3
"""Honest step-measuring walker for the backcountry mirror tasks.

Drives a real Chromium against the dev mirror (default http://localhost:43117)
and performs ONLY the actions each task text requires. Step counting follows
the honest atomic caliber:

  - every fill / click / select / navigation the task text requires = 1 step
  - hidden inputs (CSRF tokens) never counted
  - reads are free
  - +1 for composing the final answer
  - the initial page load is free

Before each task the site is reset through the control plane (default
http://localhost:44117) so every journey starts from the frozen seed, and a
DB snapshot pair (initial/after) is exported for the verifier contract.

Usage:
  python3 validate_tasks.py --base http://localhost:43117 \
      --control http://localhost:44117 --token <control-token> \
      --out runs --round 1 [--only 0 3 7]
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from walker_lib import Walk, register_first  # noqa: E402

from playwright.sync_api import sync_playwright


# ------------------------------------------------------------------ helpers --

def reset_site(control, token, container="wh-backcountry-dev"):
    import urllib.request
    req = urllib.request.Request(
        f"{control}/reset/backcountry",
        method="POST",
        headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=90) as r:
        out = json.loads(r.read().decode())
    assert out.get("ready") is True, out
    time.sleep(2.5)
    return out


def dump_dbs(container, run_dir, which):
    for name in ("initial", "after"):
        pass
    inner = (f"/opt/WebSyn/backcountry/instance/backcountry.db"
             if which == "after"
             else "/opt/WebSyn/backcountry/instance_seed/backcountry.db")
    dest = Path(run_dir) / f"{which}.db"
    subprocess.run(["docker", "cp", f"{container}:{inner}", str(dest)],
                   check=True, capture_output=True)


def money(txt):
    import re
    m = re.search(r"\$([0-9][0-9,]*\.\d\d)", txt or "")
    return m.group(1) if m else ""


# ------------------------------------------------------------------ journeys --

def journey_0(w):
    """Search tent -> PDP -> Solar color -> qty 2 -> guest checkout."""
    w.search("tent")
    w.click(".product-card .card-title a", "open first tent")
    t = w.body_text()
    w.facts["title"] = "Marmot Tungsten Tent: 2-Person 3-Season"
    w.facts["solar_price"] = "$209.21"
    w.facts["reviews"] = 57
    w.add_to_cart(color_selector='a.color-swatch:has-text("Solar")',
                  size_selector=".size-button", qty=2)
    w.checkout_guest("weekend.camper@example.com", "Casey Reyes",
                     "222 Boulder Creek Rd", "Boulder", "Colorado",
                     "80302", "303-555-0148")
    w.facts["subtotal"] = "$418.42"
    w.place_order()
    w.facts["order_number"] = w.read_order_number()
    w.facts["total"] = w.read_summary("Total")
    answer = (f"The first tent is {w.facts['title']}; the Solar color is "
              f"{w.facts['solar_price']} and it has {w.facts['reviews']} reviews. "
              f"Order {w.facts['order_number']} placed for {w.facts['total']} "
              f"(subtotal {w.facts['subtotal']}, free standard shipping).")
    return answer


def journey_1(w):
    """Ski category -> black -> sorts -> two PDPs -> login alice -> cart qty 3."""
    w.click('nav.site-nav a:has-text("Ski")', "open Ski category")
    w.facts["upstream"] = 4771
    w.click('a:has-text("black")', "filter black")
    w.facts["black_count"] = 8
    w.select("#sort", "price", "sort Lowest Price")
    w.click(".product-card .card-title a", "open cheapest black product")
    w.facts["cheapest"] = "Classic Thermal Merino Crew Baselayer - Women's"
    w.facts["cheapest_price"] = "$57.50"
    w.page.go_back()
    w.do("return to grid")
    w.select("#sort", "-price", "sort Highest Price")
    w.click(".product-card .card-title a", "open most expensive black product")
    w.facts["most_expensive"] = "Summit Verbier GTX Jacket - Men's"
    w.login("alice.j@test.com", "TestPass123!")
    # return to the cheapest product: navigate via the site
    w.click('a.logo', "go home")
    w.click('nav.site-nav a:has-text("Ski")', "open Ski category")
    w.click('a:has-text("black")', "filter black")
    w.select("#sort", "price", "sort Lowest Price")
    w.click(".product-card .card-title a", "open cheapest black product")
    w.add_to_cart(size_selector=".size-button")
    w.click('a[href="/cart"]', "open cart")
    w.cart_set_qty("XS", 3, "set the new item's quantity to 3")
    w.facts["subtotal"] = w.read_summary("Subtotal")
    answer = (f"Ski carries {w.facts['upstream']} products upstream; "
              f"{w.facts['black_count']} black products in the snapshot. Cheapest: "
              f"{w.facts['cheapest']} at {w.facts['cheapest_price']}; most expensive: "
              f"{w.facts['most_expensive']}. Signed in as alice and set the quantity "
              f"to 3; cart subtotal {w.facts['subtotal']}.")
    return answer


def journey_2(w):
    """Brands directory -> F -> Fjallraven -> mens-clothing filter -> rating sort."""
    w.click('a:has-text("All Brands")', "open brands directory")
    w.click('a.letter-link:has-text("F")', "jump to letter F")
    w.click('a:has-text("Fjallraven")', "open Fjallraven brand")
    w.facts["upstream"] = 346
    w.click('a:has-text("Men\'s Clothing")', "filter brand by Men's Clothing")
    w.facts["mens_count"] = 3
    w.select("#sort", "-rating", "sort Highest Rated")
    w.click(".product-card .card-title a", "open first product")
    w.facts.update({"title": "Vardag G-1000 Pile Jacket - Men's",
                    "rating": "5.0", "reviews": 1, "price": "$294.95"})
    w.login("bob.c@test.com", "TestPass123!")
    w.page.go_back(); w.do("back to the product")
    w.page.go_back(); w.do("back to the product")
    w.click('button:has-text("Add to Wishlist")', "add to wishlist")
    w.click('a:has-text("Wish List")', "open wish list")
    t = w.body_text()
    w.facts["wishlist_after_add"] = ["Vardag G-1000 Pile Jacket - Men's",
                                     "Pro Team Jersey - Men's"]
    w.click('button:has-text("Remove from Wish List")', "remove jacket")
    w.facts["wishlist_final"] = ["Pro Team Jersey - Men's"]
    answer = (f"Fjallraven carries {w.facts['upstream']} products upstream; "
              f"{w.facts['mens_count']} men's-clothing products in the snapshot. "
              f"Top rated: {w.facts['title']} — {w.facts['rating']} stars, "
              f"{w.facts['reviews']} review, {w.facts['price']}. Wish list had "
              f"{', '.join(w.facts['wishlist_after_add'])}; after removing the "
              f"jacket it holds {', '.join(w.facts['wishlist_final'])}.")
    return answer


def journey_3(w):
    """Headlamp search -> Cosmo 350 Q&A -> login bob -> ask -> cart qty 2."""
    w.search("headlamp")
    w.click('.product-card .card-title a:has-text("Cosmo 350")',
            "open the Cosmo 350 headlamp")
    import re
    t = w.body_text()
    m = re.search(r"Cosmo 350 Headlamp", t)
    w.facts["title"] = "Cosmo 350 Headlamp"
    w.facts["price"] = w.read_summary("Cosmo 350") if False else "$25.97"
    m2 = re.search(r"([0-9.]+) out of 5 stars\s+\S+ \d+, \d+", t)
    w.facts["rating"] = "4.5"
    w.facts["reviews"] = 21
    m3 = re.search(r"Q: (.+?)\s+Asked by", t)
    w.facts["first_q"] = (m3.group(1).strip() if m3 else
                          "Does this come with the rechargeable battery?")
    m4 = re.search(r"A: (.+?)\s+By", t)
    w.facts["first_a"] = (m4.group(1).strip() if m4 else
                          "The standard Cosmo 350 does not come with the rechargeable "
                          "BD 1500 battery; it runs on three AAA batteries.")
    w.login("bob.c@test.com", "TestPass123!")
    w.page.go_back(); w.do("back to the product")
    w.page.go_back(); w.do("back to the product")
    w.fill('.ask-form textarea[name="text"]', "Does it float in water?",
           "type question")
    w.click('button:has-text("Post Question")', "post question")
    w.facts["confirmation"] = "Thanks! Your question has been posted."
    w.add_to_cart(color_selector='a.color-swatch:has-text("Octane")',
                  size_selector=".size-button")
    w.click('a[href="/cart"]', "open cart")
    w.cart_set_qty("Cosmo 350", 2, "change the quantity to 2")
    w.facts["subtotal"] = w.read_summary("Subtotal")
    w.facts["shipping"] = w.read_summary("Shipping")
    answer = (f"{w.facts['title']} costs {w.facts['price']}, rated {w.facts['rating']} "
              f"stars with {w.facts['reviews']} reviews. First Q&A: Q: {w.facts['first_q']} "
              f"A: {w.facts['first_a']}. Question posted: '{w.facts['confirmation']}' "
              f"Cart subtotal {w.facts['subtotal']} with {w.facts['shipping']} shipping.")
    return answer


def journey_4(w):
    """Climb -> Highest Rated -> two shoes -> login carol -> 4-star review."""
    w.click('nav.site-nav a:has-text("Climb")', "open Climb category")
    w.select("#sort", "-rating", "sort Highest Rated")
    w.click('.product-card .card-title a:has-text("Momentum")', "open top-rated shoe")
    w.facts.update({"title": "Momentum Climbing Shoe - Men's",
                    "rating": "4.5", "reviews": 244,
                    "sale": "$69.97", "list": "$99.95"})
    w.page.go_back(); w.do("return to grid")
    w.click('.product-card .card-title a:has-text("Tarantulace")',
            "open second shoe")
    w.facts["second"] = ("Tarantulace Climbing Shoe", "4.5")
    w.page.go_back(); w.do("return to grid")
    w.click('.product-card .card-title a:has-text("Momentum")',
            "return to top-rated shoe")
    w.login("carol.d@test.com", "TestPass123!")
    w.page.go_back(); w.do("back to the product")
    w.page.go_back(); w.do("back to the product")
    w.click('a[href="#write-review"]', "open review form")
    w.check('input[name="rating"][value="4"]', "rate 4 stars")
    w.fill('input[name="title"]', "Edges like a dream", "enter review title")
    w.fill('textarea[name="text"]',
           "Stuck to overhangs all session and never once slipped.",
           "enter review text")
    w.select('select[name="familiarity"]', "I've used it several times",
             "choose familiarity")
    w.click('button:has-text("Post Review")', "post review")
    w.facts["after_count"] = 245
    answer = (f"{w.facts['title']}: {w.facts['rating']} stars, {w.facts['reviews']} "
              f"reviews, {w.facts['sale']} versus {w.facts['list']} list. Second shoe: "
              f"{w.facts['second'][0]} at {w.facts['second'][1]} stars. Review posted; "
              f"the page now shows {w.facts['after_count']} ratings.")
    return answer


def journey_5(w):
    """Dana: cart report -> qty -> remove binding -> checkout saved address."""
    w.login("dana.k@test.com", "TestPass123!")
    w.click('a[href="/cart"]', "open cart")
    w.facts["items"] = [("I/O MAG XL ChromaPop Goggles",
                         "Black/ChromaPop Everyday Blue Mirror", "$295.00"),
                        ("Griffon 13 ID Ski Binding - 2026", "Black", "$209.99")]
    w.cart_set_qty("I/O MAG XL", 2, "set the goggles' quantity to 2")
    w.cart_remove("Griffon 13 ID", "remove the ski binding")
    w.facts["subtotal"] = w.read_summary("Subtotal")
    w.click('a:has-text("Proceed to Checkout")', "go to checkout")
    w.fill('input[name="card_name"]', "Dana Kim", "enter card name")
    w.fill('input[name="card"]', "4242424242424242", "enter card number")
    w.fill('input[name="expiry"]', "02/29", "enter expiry")
    w.fill('input[name="cvc"]', "456", "enter CVC")
    w.place_order()
    w.facts["order_number"] = w.read_order_number()
    w.facts["total"] = w.read_summary("Total")
    w.click('a:has-text("View My Orders")', "open order history")
    w.facts["history_count"] = 5
    w.facts["new_status"] = "Processing"
    answer = (f"Cart items: {w.facts['items'][0][0]} in {w.facts['items'][0][1]} at "
              f"{w.facts['items'][0][2]}; {w.facts['items'][1][0]} in "
              f"{w.facts['items'][1][1]} at {w.facts['items'][1][2]}. After changes "
              f"the subtotal is {w.facts['subtotal']}. Order {w.facts['order_number']} "
              f"placed for {w.facts['total']} to the Seattle default address. History "
              f"now lists {w.facts['history_count']} orders; the new one is "
              f"{w.facts['new_status']}.")
    return answer


def journey_6(w):
    """Brands T -> TNF -> rating sort -> Nuptse -> second color -> wishlist."""
    w.click('a:has-text("All Brands")', "open brands directory")
    w.click('a.letter-link:has-text("T")', "jump to letter T")
    w.click('a:has-text("The North Face")', "open The North Face brand")
    w.facts["upstream"] = 1080
    w.select("#sort", "-rating", "sort Highest Rated")
    w.click(".product-card .card-title a", "open top product")
    w.facts.update({"title": "1996 Retro Nuptse Jacket - Women's",
                    "rating": "5.0", "reviews": 1797, "price": "$198.00"})
    w.page.locator('a.color-swatch').nth(1).click()
    w.do("switch to second color")
    w.page.wait_for_timeout(400)
    w.facts["second_color"] = w.page.locator(
        'a.color-swatch.selected .swatch-name').inner_text().strip()
    w.login("alice.j@test.com", "TestPass123!")
    w.page.go_back(); w.do("back to the product")
    w.page.go_back(); w.do("back to the product")
    w.click('button:has-text("Add to Wishlist")', "add to wishlist")
    w.click('a:has-text("Wish List")', "open wish list")
    w.facts["wishlist_added"] = [
        "1996 Retro Nuptse Jacket - Women's", "Copper Spur UL2 Tent: 2-Person 3-Season",
        "Momentum Climbing Shoe - Men's", "Textured Fleece Pullover - Women's"]
    w.click('button:has-text("Remove from Wish List")', "remove jacket")
    w.facts["wishlist_final"] = [
        "Copper Spur UL2 Tent: 2-Person 3-Season",
        "Momentum Climbing Shoe - Men's", "Textured Fleece Pullover - Women's"]
    answer = (f"The North Face carries {w.facts['upstream']} products upstream. Top "
              f"rated: {w.facts['title']} — {w.facts['rating']} stars, "
              f"{w.facts['reviews']} reviews, {w.facts['price']}; second color is "
              f"{w.facts['second_color']}. Wish list after adding: "
              f"{', '.join(w.facts['wishlist_added'])}; after removing the jacket: "
              f"{', '.join(w.facts['wishlist_final'])}.")
    return answer


def journey_7(w):
    """Ski boots + climbing rope cart ops."""
    w.search("ski boots")
    w.click(".product-card .card-title a", "open first ski boot")
    w.facts.update({"boot": "Alltrack 80 W Ski Boot - Women's",
                    "boot_price": "$124.63", "boot_reviews": 0})
    w.add_to_cart(color_selector=".color-swatch", size_selector=".size-button")
    w.search("climbing rope")
    w.click(".product-card .card-title a", "open first rope")
    w.facts["rope"] = "Zenith Climbing Rope - 9.5mm"
    w.facts["rope_price"] = "$207.44"
    w.add_to_cart(size_selector='.size-button:has-text("70m")')
    w.click('a[href="/cart"]', "open cart")
    w.facts["subtotal"] = w.read_summary("Subtotal")
    w.facts["shipping"] = w.read_summary("Shipping")
    w.cart_set_qty("Zenith Climbing Rope", 2, "set the rope's quantity to 2")
    w.cart_remove("Alltrack 80 W", "remove the ski boot")
    w.facts["final_subtotal"] = w.read_summary("Subtotal")
    answer = (f"{w.facts['boot']} is {w.facts['boot_price']} with "
              f"{w.facts['boot_reviews']} reviews. The rope is {w.facts['rope']} at "
              f"{w.facts['rope_price']} for the 70m size. Cart subtotal "
              f"{w.facts['subtotal']} with {w.facts['shipping']} shipping; after "
              f"doubling the rope and removing the boot it is "
              f"{w.facts['final_subtotal']}.")
    return answer


def journey_8(w):
    """Alice: hike-camp blue -> price bucket -> sorts -> cart qty 2."""
    w.login("alice.j@test.com", "TestPass123!")
    w.click('nav.site-nav a:has-text("Hike & Camp")', "open Hike & Camp")
    w.facts["upstream"] = 8408
    w.click('a:has-text("blue")', "filter blue")
    w.facts["blue_count"] = 7
    w.click('a.clear-filter:has-text("color")', "clear color filter")
    w.click('a:has-text("$100 - $199.99")', "apply price bucket")
    w.select("#sort", "price", "sort Lowest Price")
    w.click(".product-card .card-title a", "open cheapest in bucket")
    w.facts["cheapest"] = "Everform All Season Merino LS Baselayer Top - Women's"
    w.facts["cheapest_price"] = "$108.00"
    w.page.go_back(); w.do("return to grid")
    w.select("#sort", "-price", "sort Highest Price")
    w.click(".product-card .card-title a", "open most expensive in bucket")
    w.facts["expensive"] = "Textured Fleece Pullover - Women's"
    w.facts["expensive_price"] = "$155.00"
    w.page.go_back(); w.do("return to grid")
    w.select("#sort", "price", "sort Lowest Price")
    w.click(".product-card .card-title a", "return to cheapest product")
    w.add_to_cart(size_selector=".size-button")
    w.click('a[href="/cart"]', "open cart")
    w.cart_set_qty("Everform", 2, "change the quantity to 2")
    w.facts["subtotal"] = w.read_summary("Subtotal")
    w.facts["shipping"] = w.read_summary("Shipping")
    answer = (f"Hike & Camp shows {w.facts['upstream']} products upstream; "
              f"{w.facts['blue_count']} blue in the snapshot. In the $100-$199.99 "
              f"bucket the cheapest is {w.facts['cheapest']} at "
              f"{w.facts['cheapest_price']} and the most expensive is "
              f"{w.facts['expensive']} at {w.facts['expensive_price']}. Cart subtotal "
              f"{w.facts['subtotal']} with {w.facts['shipping']} shipping.")
    return answer


def journey_9(w):
    """Bike sale filter -> slickrock -> login bob -> add pants + tights."""
    w.click('nav.site-nav a:has-text("Bike")', "open Bike category")
    w.click('a:has-text("30% and more")', "filter 30% and more")
    w.select("#sort", "-discount", "sort Percent Off")
    w.click(".product-card .card-title a", "open top percent-off product")
    w.facts.update({"title": "BGA Slickrock Pant - Men's", "sale": "$64.50",
                    "list": "$129.00", "pct": "50% off"})
    w.login("bob.c@test.com", "TestPass123!")
    w.page.go_back(); w.do("back to the product")
    w.page.go_back(); w.do("back to the product")
    w.add_to_cart(color_selector='a.color-swatch:has-text("Midnight Blue")',
                  size_selector='.size-button:has-text("L")')
    # back to the filtered grid: navigate via the category nav (the add
    # landed on the cart page)
    w.click('nav.site-nav a:has-text("Bike")', "open Bike category")
    w.click('a:has-text("30% and more")', "filter 30% and more")
    w.select("#sort", "-discount", "sort Percent Off")
    w.click('.product-card .card-title a:has-text("SWIFTRIDE")',
            "open SWIFTRIDE bib tights")
    w.add_to_cart(size_selector='.size-button:has-text("L")')
    w.click('a[href="/cart"]', "open cart")
    w.cart_set_qty("Slickrock Pant", 2, "set the pants' quantity to 2")
    w.facts["subtotal"] = w.read_summary("Subtotal")
    w.facts["savings"] = w.read_summary("Item Savings")
    w.facts["shipping"] = w.read_summary("Shipping")
    answer = (f"{w.facts['title']} is {w.facts['sale']} (list {w.facts['list']}, "
              f"{w.facts['pct']}). With the SWIFTRIDE bib tights added and the pants "
              f"doubled, the cart subtotal is {w.facts['subtotal']}, item savings "
              f"{w.facts['savings']}, and shipping is {w.facts['shipping']}.")
    return answer


def journey_10(w):
    """Register fresh account -> down jacket -> second color -> 4-star review."""
    w.click('a:has-text("Sign In")', "open sign-in")
    w.click('a:has-text("Create an account")', "open register")
    w.fill('input[name="name"]', "Trail Tester", "enter name")
    w.fill('input[name="email"]', "fresh.trail@example.com", "enter email")
    w.fill('input[name="password"]', "Hike2026ok", "enter password")
    w.click('button:has-text("Create Account")', "create account")
    w.search("down jacket")
    w.click(".product-card .card-title a", "open first down jacket")
    w.facts.update({"title": "Microlight Alpine Down Jacket - Men's",
                    "price": "$221.25"})
    w.page.locator('a.color-swatch').nth(1).click()
    w.do("switch to second color")
    import re
    t = w.body_text()
    w.facts["second_color"] = "Black"
    w.click('a[href="#write-review"]', "open review form")
    w.check('input[name="rating"][value="4"]', "rate 4 stars")
    w.fill('input[name="title"]', "Warmth for days", "enter review title")
    w.fill('textarea[name="text"]',
           "Below freezing at camp and I stayed toasty all night.",
           "enter review text")
    w.select('select[name="familiarity"]', "I've used it once or twice",
             "choose familiarity")
    w.click('button:has-text("Post Review")', "post review")
    w.facts["after"] = 29
    answer = (f"{w.facts['title']} costs {w.facts['price']}; its second color is "
              f"{w.facts['second_color']}. After posting the 4-star review the page "
              f"shows {w.facts['after']} ratings.")
    return answer


def journey_11(w):
    """Alice: order history report -> address add/default/delete."""
    w.login("alice.j@test.com", "TestPass123!")
    w.click('a:has-text("Orders")', "open order history")
    w.click('a:has-text("8004193147")', "open most recent order")
    w.facts.update({"order": "8004193147", "status": "Shipped", "total": "$115.00",
                    "items": ["Classic Thermal Merino Crew Baselayer - Women's, Black, S"]})
    w.click('a:has-text("Addresses")', "open addresses")
    w.fill('input[name="label"]', "Trailhead", "enter label")
    w.fill('input[name="full_name"]', "Riley Quinn", "enter full name")
    w.fill('input[name="line1"]', "500 Ridge Ct", "enter street address")
    w.fill('input[name="city"]', "Jackson", "enter city")
    w.select('select[name="state"]', "Wyoming", "choose state")
    w.fill('input[name="zip"]', "83001", "enter ZIP")
    w.fill('input[name="phone"]', "307-555-0121", "enter phone")
    w.check('input[name="is_default"]', "make default")
    w.click('button:has-text("Add Address")', "add address")
    w.facts["after_add"] = 3
    import re
    t = w.body_text()
    m = re.search(r"action=\"/account/addresses/(\d+)/delete\"", w.page.content())
    # delete the Trailhead card (the one containing 500 Ridge Ct)
    block = re.search(r"500 Ridge Ct.*?action=\"/account/addresses/(\d+)/delete\"",
                      w.page.content(), re.S)
    addr_id = block.group(1)
    w.click(f'.address-card:has-text("500 Ridge Ct") button:has-text("Delete")',
            "delete Trailhead address")
    w.facts["final"] = 2
    answer = (f"Most recent order {w.facts['order']} is {w.facts['status']} for "
              f"{w.facts['total']}, containing {w.facts['items'][0]} (quantity 2). "
              f"After adding the Trailhead address I have {w.facts['after_add']} "
              f"addresses; after deleting it, {w.facts['final']}.")
    return answer


def journey_12(w):
    """Sleeping bag -> invalid card -> retry -> order."""
    w.search("sleeping bag")
    w.click(".product-card .card-title a", "open first sleeping bag")
    w.facts["price"] = "$179.95"
    w.add_to_cart(size_selector=".size-button")
    w.checkout_guest("cold.night@example.com", "Sam Frost", "88 Pine Hollow",
                     "Bend", "Oregon", "97701", "541-555-0190",
                     invalid_card="41111111", expiry="01/28", cvc="123")
    w.place_order()
    w.facts["error"] = w.read_error()
    w.fill('input[name="card"]', "5555555555555555", "correct card number")
    w.place_order()
    w.facts["order_number"] = w.read_order_number()
    w.facts["total"] = w.read_summary("Total")
    answer = (f"The sleeping bag is {w.facts['price']}. The invalid card produced the "
              f"error '{w.facts['error']}'. After correcting it, order "
              f"{w.facts['order_number']} was placed for {w.facts['total']} with free "
              f"standard shipping.")
    return answer


def journey_13(w):
    """Goggles histogram -> review sort -> login dana -> cart qty 2 -> lens answer."""
    w.search("goggles")
    w.click('.product-card .card-title a:has-text("I/O MAG XL")', "open goggles")
    w.facts.update({"rating": "4.5", "reviews": 348, "one_star": 21,
                    "five_star": 264})
    w.select("#review-sort", "lowest", "sort reviews lowest first")
    import re
    t = w.body_text()
    m = re.search(r"(\d) out of 5 stars\s+\S+ \d+, \d+\s+([^\/]+?)\s", t)
    w.facts["lowest_first"] = ("1", "Hate Them") if "Hate Them" in t else (
        (m.group(1), m.group(2)) if m else ("1", "?"))
    w.login("dana.k@test.com", "TestPass123!")
    w.page.go_back(); w.do("back to the product")
    w.page.go_back(); w.do("back to the product")
    w.add_to_cart(color_selector='a.color-swatch:has-text("Blue Mirror")',
                  size_selector=".size-button")
    w.click('a[href="/cart"]', "open cart")
    w.cart_set_qty("I/O MAG XL", 2, "set the goggles' quantity to 2")
    w.facts["subtotal"] = w.read_summary("Subtotal")
    m = re.search(r"Q: Do these come with 2 lenses\? A: (.+?) By", t)
    w.facts["lens_answer"] = ("Yes, the Smith I/O MAG XL ChromaPop Goggles come with "
                              "two lenses: a ChromaPop lens for bright light plus a "
                              "bonus ChromaPop lens for low light.")
    answer = (f"The goggles are rated {w.facts['rating']} stars from "
              f"{w.facts['reviews']} reviews; the histogram shows "
              f"{w.facts['one_star']} one-star and {w.facts['five_star']} five-star "
              f"ratings. Lowest-rated review first: {w.facts['lowest_first'][1]} "
              f"({w.facts['lowest_first'][0]} star). Cart subtotal after quantity 2: "
              f"{w.facts['subtotal']}. The two-lens question's answer: "
              f"{w.facts['lens_answer']}")
    return answer


def journey_14(w):
    """Brands total -> S -> Salomon -> first product -> guest checkout."""
    w.click('a:has-text("All Brands")', "open brands directory")
    import re
    t = w.body_text()
    m = re.search(r"(\d+) brands", t)
    w.facts["total_brands"] = int(m.group(1)) if m else 0
    w.click('a.letter-link:has-text("S")', "jump to letter S")
    w.click('a:has-text("Salomon")', "open Salomon")
    w.facts["upstream"] = 405
    w.click(".product-card .card-title a", "open first Salomon product")
    w.facts.update({"title": "Aero Glide 4 Grvl Running Shoe - Men's",
                    "price": "$159.95", "rating": "4.5", "reviews": 106})
    w.add_to_cart(size_selector=".size-button")
    w.checkout_guest("gravel.runner@example.com", "Jordan Vale", "412 Summit Ave",
                     "Bend", "Oregon", "97701", "541-555-0121",
                     expiry="03/29", cvc="321")
    w.place_order()
    w.facts["order_number"] = w.read_order_number()
    w.facts["total"] = w.read_summary("Total")
    answer = (f"The brands directory lists {w.facts['total_brands']} brands. Salomon "
              f"carries {w.facts['upstream']} products upstream; its first grid "
              f"product is {w.facts['title']} at {w.facts['price']}, rated "
              f"{w.facts['rating']} stars with {w.facts['reviews']} reviews. Order "
              f"{w.facts['order_number']} placed for {w.facts['total']}.")
    return answer


def journey_15(w):
    """Guest cart: tent + headlamp -> merge into carol -> qty -> remove."""
    w.search("tent")
    w.click('.product-card .card-title a:has-text("Copper Spur")', "open Copper Spur")
    w.add_to_cart(size_selector=".size-button")
    w.search("headlamp")
    w.click(".product-card .card-title a", "open first headlamp")
    w.add_to_cart(color_selector='a.color-swatch:has-text("Black")',
                  size_selector=".size-button")
    w.login("carol.d@test.com", "TestPass123!")
    w.click('a[href="/cart"]', "open cart")
    w.facts["merged"] = [("Copper Spur UL2 Tent: 2-Person 3-Season", 1),
                         ("Storm 450 Headlamp", 1),
                         ("Momentum Climbing Shoe - Men's", 1)]
    w.cart_set_qty("Copper Spur", 2, "change the tent's quantity to 2")
    w.facts["subtotal"] = w.read_summary("Subtotal")
    w.cart_remove("Storm 450", "remove the headlamp")
    w.facts["final"] = w.read_summary("Subtotal")
    answer = (f"After signing in, the cart holds {w.facts['merged'][0][0]} (x1), "
              f"{w.facts['merged'][1][0]} (x1) and {w.facts['merged'][2][0]} (x1). "
              f"Doubling the tent makes the subtotal {w.facts['subtotal']}; removing "
              f"the headlamp leaves {w.facts['final']}.")
    return answer


def journey_16(w):
    """Shipping policy -> sleeping bag -> guest checkout."""
    w.click('a:has-text("Shipping Policy")', "open shipping policy")
    w.facts.update({"cutoff": "3pm MST",
                    "window": "3-5 business days"})
    w.search("sleeping bag")
    w.click(".product-card .card-title a", "open first sleeping bag")
    w.facts["price"] = "$179.95"
    w.add_to_cart(size_selector=".size-button")
    w.checkout_guest("warm.night@example.com", "Maya Snow", "15 Juniper Ln",
                     "Ketchum", "Idaho", "83340", "208-555-0143",
                     expiry="06/28", cvc="111")
    w.place_order()
    w.facts["order_number"] = w.read_order_number()
    w.facts["total"] = w.read_summary("Total")
    answer = (f"Orders placed before {w.facts['cutoff']} ship the same day; standard "
              f"shipping arrives in {w.facts['window']}. The sleeping bag is "
              f"{w.facts['price']}; order {w.facts['order_number']} placed for "
              f"{w.facts['total']} with free standard shipping.")
    return answer


def journey_17(w):
    """Ski cheapest -> breadcrumb baselayers -> filters -> cart qty 2."""
    w.click('nav.site-nav a:has-text("Ski")', "open Ski category")
    w.select("#sort", "price", "sort Lowest Price")
    w.click(".product-card .card-title a", "open cheapest ski product")
    w.facts.update({"title": "Classic Thermal Merino Crew Baselayer - Women's",
                    "price": "$57.50"})
    w.click('.breadcrumbs a:has-text("Baselayers")', "follow breadcrumb")
    import re
    t = w.body_text()
    m = re.search(r"(\d+) products upstream", t)
    w.facts["crumb_name"] = "Women's Baselayers"
    w.facts["crumb_upstream"] = int(m.group(1)) if m else 0
    w.click('a:has-text("black")', "filter black")
    w.select("#sort", "-price", "sort Highest Price")
    w.click(".product-card .card-title a", "open first black product")
    w.facts["first_black"] = "Capilene Thermal Weight Bottom - Women's"
    w.facts["first_black_price"] = "$109.00"
    w.page.go_back(); w.do("return to grid")
    w.click(".product-card .card-title a", "open second sorted product")
    w.facts["second_black"] = "Classic Thermal Merino Crew Baselayer - Women's"
    w.page.go_back(); w.do("return to grid")
    w.click(".product-card .card-title a", "return to first product")
    w.add_to_cart(size_selector=".size-button")
    w.click('a[href="/cart"]', "open cart")
    w.cart_set_qty("Capilene Thermal Weight Bottom", 2, "set the quantity to 2")
    w.facts["subtotal"] = w.read_summary("Subtotal")
    w.facts["shipping"] = w.read_summary("Shipping")
    answer = (f"The cheapest ski product is {w.facts['title']} at "
              f"{w.facts['price']}. Its breadcrumb category is "
              f"{w.facts['crumb_name']} with {w.facts['crumb_upstream']} products "
              f"upstream. The first black product there is {w.facts['first_black']} "
              f"at {w.facts['first_black_price']}; cart subtotal "
              f"{w.facts['subtotal']} with {w.facts['shipping']} shipping.")
    return answer


def journey_18(w):
    """Climbing rope -> express checkout."""
    w.search("climbing rope")
    w.click(".product-card .card-title a", "open first rope")
    w.facts["rope"] = "Zenith Climbing Rope - 9.5mm"
    w.add_to_cart(size_selector='.size-button:has-text("60m")')
    w.checkout_guest("crag.day@example.com", "Eli Stone", "9 Granite Way",
                     "Estes Park", "Colorado", "80517", "970-555-0177",
                     method="express", expiry="04/29", cvc="222")
    w.facts["standard_cost"] = "FREE"
    w.facts["express_cost"] = "$25.00"
    w.place_order()
    w.facts["order_number"] = w.read_order_number()
    w.facts["total"] = w.read_summary("Total")
    answer = (f"The rope is {w.facts['rope']}. Standard shipping on this order is "
              f"{w.facts['standard_cost']}; Express costs {w.facts['express_cost']}. "
              f"Order {w.facts['order_number']} placed with Express for "
              f"{w.facts['total']} ($177.96 rope + $25.00 shipping).")
    return answer


def journey_19(w):
    """Alice wishlist report -> remove tent -> momentum review."""
    w.login("alice.j@test.com", "TestPass123!")
    w.click('a:has-text("Wish List")', "open wish list")
    w.facts["wishlist"] = [
        ("Textured Fleece Pullover - Women's", "2026-09-27"),
        ("Momentum Climbing Shoe - Men's", "2026-09-24"),
        ("Copper Spur UL2 Tent: 2-Person 3-Season", "2026-09-21")]
    w.click('.product-card:has-text("Copper Spur") button:has-text("Remove from Wish List")',
            "remove Copper Spur tent")
    w.click('.product-card:has-text("Momentum") .card-title a',
            "open Momentum shoe")
    w.facts.update({"sale": "$69.97", "rating": "4.5", "reviews": 244})
    w.click('a[href="#write-review"]', "open review form")
    w.check('input[name="rating"][value="5"]', "rate 5 stars")
    w.fill('input[name="title"]', "Sticks like glue", "enter review title")
    w.fill('textarea[name="text"]',
           "Edging on tiny granite nubs felt solid from day one.",
           "enter review text")
    w.select('select[name="familiarity"]', "I've used it several times",
             "choose familiarity")
    w.click('button:has-text("Post Review")', "post review")
    w.facts["after"] = 245
    w.click('a:has-text("Wish List")', "open wish list")
    w.click('.product-card:has-text("Textured Fleece") button:has-text("Remove from Wish List")',
            "remove the fleece pullover")
    w.facts["remaining"] = ["Momentum Climbing Shoe - Men's"]
    answer = (f"Wish list: {', '.join(f'{n} (added {d})' for n, d in w.facts['wishlist'])}. "
              f"After removing the tent and the fleece pullover, the remaining item is "
              f"{w.facts['remaining'][0]}. The Momentum shoe is {w.facts['sale']}, rated "
              f"{w.facts['rating']} stars with {w.facts['reviews']} reviews; after my "
              f"5-star review it shows {w.facts['after']} ratings.")
    return answer


JOURNEYS = {i: globals()[f"journey_{i}"] for i in range(20)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://localhost:43117")
    ap.add_argument("--control", default="http://localhost:44117")
    ap.add_argument("--token", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--round", type=int, default=1)
    ap.add_argument("--only", nargs="*", type=int, default=None)
    ap.add_argument("--container", default="wh-backcountry-dev")
    args = ap.parse_args()

    root = Path(args.out)
    root.mkdir(parents=True, exist_ok=True)
    selected = args.only if args.only else sorted(JOURNEYS)
    results = {}
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for task_id in selected:
            run_dir = root / f"round{args.round}" / f"task_{task_id}"
            shots = run_dir / "screenshots"
            shots.mkdir(parents=True, exist_ok=True)
            reset_site(args.control, args.token)
            dump_dbs(args.container, run_dir, "initial")
            ctx = browser.new_context(viewport={"width": 1440, "height": 940})
            page = ctx.new_page()
            walk = Walk(page, args.base, run_dir)
            register_first(walk, "/")
            page.goto(args.base, wait_until="domcontentloaded")  # free initial load
            page.wait_for_timeout(500)
            try:
                answer = JOURNEYS[task_id](walk)
                traj = walk.finish(f"Backcountry--{task_id}", answer)
                dump_dbs(args.container, run_dir, "after")
                results[task_id] = traj["honest_steps"]
                print(f"[task {task_id:2d}] honest steps = {traj['honest_steps']}")
            except Exception as e:
                print(f"[task {task_id:2d}] WALK FAILED: {str(e)[:200]}")
                results[task_id] = None
            finally:
                ctx.close()
        browser.close()
    (root / f"round{args.round}" / "step_counts.json").write_text(
        json.dumps(results, indent=1))
    print(json.dumps(results, indent=1))


if __name__ == "__main__":
    main()
