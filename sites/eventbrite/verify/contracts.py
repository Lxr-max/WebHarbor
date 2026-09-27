"""Frozen Eventbrite facts. Answers stay in this module."""

import json
import sqlite3

from checks import after_near, fold, has_num, has_phrase, near


def _open(path):
    if not path:
        return None
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _event_id(conn, slug):
    row = conn.execute("SELECT id FROM events WHERE slug=?", (slug,)).fetchone()
    return row["id"] if row else None


def _user_id(conn, email):
    row = conn.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
    return row["id"] if row else None


def _orders(conn, slug, email):
    eid = _event_id(conn, slug)
    uid = _user_id(conn, email)
    if eid is None or uid is None:
        return []
    return conn.execute(
        "SELECT * FROM orders WHERE event_id=? AND user_id=? AND status='confirmed'",
        (eid, uid),
    ).fetchall()


def state_ga_order(initial, after, answer, traj):
    conn = _open(after)
    if conn is None:
        return False, "missing after_state.db"
    try:
        rows = _orders(conn, "science-fiction-kim-stanley-robinson", "alice.j@test.com")
        matched = []
        for order in rows:
            items = conn.execute(
                """
                SELECT ti.name, oi.qty, oi.unit_price
                FROM order_items oi JOIN ticket_tiers ti ON ti.id=oi.tier_id
                WHERE oi.order_id=?
                """,
                (order["id"],),
            ).fetchall()
            people = conn.execute(
                "SELECT attendee_name, attendee_email FROM issued_tickets WHERE order_id=?",
                (order["id"],),
            ).fetchall()
            ga = [item for item in items if item["name"] == "General Admission" and item["qty"] == 2 and item["unit_price"] == 25]
            names = {(p["attendee_name"], p["attendee_email"].lower()) for p in people}
            if (
                ga
                and abs(order["total"] - 50) < 0.01
                and ("Alice Johnson", "alice.j@test.com") in names
                and ("Sam Chen", "sam.chen@test.com") in names
            ):
                matched.append(order)
        if len(matched) != 1:
            return False, f"expected one 2x GA order, found {len(matched)}"
        code = matched[0]["code"]
        if code.lower() not in (answer or "").lower():
            return False, "answer omits the stored order code"
        if not has_num(answer, 50):
            return False, "answer omits the $50 total"
        return True, code
    finally:
        conn.close()


def state_free_order(initial, after, answer, traj):
    conn = _open(after)
    if conn is None:
        return False, "missing after_state.db"
    try:
        rows = _orders(conn, "rnb-rooftop-free-rsvp-brooklyn-2026", "alice.j@test.com")
        matched = []
        for order in rows:
            notes = json.loads(order["notes"] or "{}")
            people = conn.execute(
                "SELECT attendee_name, attendee_email FROM issued_tickets WHERE order_id=?",
                (order["id"],),
            ).fetchall()
            names = {(p["attendee_name"], p["attendee_email"].lower()) for p in people}
            if (
                abs(order["total"]) < 0.01
                and notes.get("dietary") == "No nuts"
                and ("Maya Lee", "maya.lee@test.com") in names
            ):
                matched.append(order)
        if len(matched) != 1:
            return False, f"expected one free RSVP, found {len(matched)}"
        code = matched[0]["code"]
        if code.lower() not in (answer or "").lower() or not has_num(answer, 0):
            return False, "answer omits the $0 total or stored order code"
        return True, code
    finally:
        conn.close()


def state_promo(initial, after, answer, traj):
    conn = _open(after)
    if conn is None:
        return False, "missing after_state.db"
    try:
        rows = _orders(conn, "science-fiction-kim-stanley-robinson", "alice.j@test.com")
        matched = []
        for order in rows:
            notes = json.loads(order["notes"] or "{}")
            items = conn.execute(
                "SELECT qty, unit_price FROM order_items WHERE order_id=?",
                (order["id"],),
            ).fetchall()
            subtotal = sum(item["qty"] * item["unit_price"] for item in items)
            if (
                notes.get("promo_code") == "SUMMER25"
                and float(notes.get("discount") or 0) == 25
                and subtotal >= 100
                and abs(order["total"] - (subtotal - 25)) < 0.01
            ):
                matched.append((order, subtotal))
        if len(matched) != 1:
            return False, f"expected one SUMMER25 order, found {len(matched)}"
        order, _sub = matched[0]
        if not has_num(answer, 25) or not has_num(answer, float(order["total"])):
            return False, "answer does not report the $25 discount and persisted total"
        return True, f"total {order['total']}"
    finally:
        conn.close()


def state_saved(initial, after, answer, traj):
    conn = _open(after)
    if conn is None:
        return False, "missing after_state.db"
    try:
        uid = _user_id(conn, "alice.j@test.com")
        eid = _event_id(conn, "15th-annual-bushwick-collective-block-party")
        row = conn.execute(
            "SELECT id FROM saved_events WHERE user_id=? AND event_id=?",
            (uid, eid),
        ).fetchone()
        if row is None:
            return False, "event is not saved"
        if not has_phrase(answer, "15th Annual Bushwick Collective Block Party"):
            return False, "answer omits the saved title"
        return True, "saved"
    finally:
        conn.close()


def state_city(initial, after, answer, traj):
    conn = _open(after)
    if conn is None:
        return False, "missing after_state.db"
    try:
        row = conn.execute(
            "SELECT city FROM users WHERE email='alice.j@test.com'"
        ).fetchone()
        if row is None or (row["city"] or "").strip().lower() != "chicago":
            return False, f"city is {row['city'] if row else None!r}"
        if not has_phrase(answer, "chicago"):
            return False, "answer does not say Chicago"
        return True, "Chicago"
    finally:
        conn.close()


def state_signup(initial, after, answer, traj):
    conn = _open(after)
    if conn is None:
        return False, "missing after_state.db"
    try:
        row = conn.execute(
            "SELECT name FROM users WHERE email='jordan.lee@test.com'"
        ).fetchone()
        if row is None or "jordan" not in (row["name"] or "").lower():
            return False, "Jordan Lee account missing"
        text = fold(answer)
        if "jordan" not in text or "log" not in text:
            return False, "answer does not confirm Jordan and logout"
        return True, row["name"]
    finally:
        conn.close()


def price_gap(answer):
    ai_free = after_near(answer, "ai product", 0, 40)
    sci_member = after_near(answer, "science", 15, 48) or after_near(answer, "member", 15, 24)
    return ai_free and sci_member and (has_phrase(answer, "cheaper") or has_phrase(answer, "less"))


def pill_order(answer):
    text = fold(answer)
    start = 0
    while True:
        rock = text.find("rock", start)
        if rock < 0:
            return False
        edm = text.find("edm", rock + 4)
        hip = text.find("hip hop", edm + 3) if edm >= 0 else -1
        if edm > rock and hip > edm:
            return True
        start = rock + 4


def sci_date(answer):
    text = fold(answer)
    return "2026-06-16" in text or "june 16 2026" in text


def west_tie(answer):
    return (
        near(answer, "san francisco", 32, 40)
        and near(answer, "denver", 32, 40)
        and near(answer, "las vegas", 32, 40)
    )


TASKS = {
    0: {
        "task_id": "Eventbrite--0",
        "nav": [r"/search\?(?=[^#\s]*city=ny--new-york)(?=[^#\s]*category=music)(?=[^#\s]*price=free)(?=[^#\s]*when=this-weekend)"],
        "phrases": ["R&B vs Slow Jams Rooftop", "The DL Rooftop"],
        "rubric": "FACT CHECKPOINTS: With the catalog frozen on May 27, 2026, find the free Music event this weekend in New York and report its title and venue. A paid event or another city's free show fails.",
    },
    1: {
        "task_id": "Eventbrite--1",
        "nav": [r"science-fiction-kim-stanley-robinson", r"/checkout/"],
        "phrases": ["Alice Johnson", "Sam Chen"],
        "state": state_ga_order,
        "rubric": "FACT CHECKPOINTS: As alice.j@test.com, buy 2 General Admission tickets for Science + Fiction: Kim Stanley Robinson for Alice Johnson and Sam Chen. Report the stored order code and the receipt total. A self-reported code with no matching order fails.",
    },
    2: {
        "task_id": "Eventbrite--2",
        "nav": [r"ai-product-summit-online-2026", r"science-fiction-kim-stanley-robinson"],
        "numbers": [15],
        "pred": price_gap,
        "rubric": "FACT CHECKPOINTS: Compare the lowest ticket price of AI Product Summit 2026 — Online with Science + Fiction: Kim Stanley Robinson. Say which is cheaper and the difference. Ignoring a free tier, or swapping the two events, fails.",
    },
    3: {
        "task_id": "Eventbrite--3",
        "nav": [
            r"/search\?(?=[^#\s]*category=business)(?=[^#\s]*format=Conference)(?=[^#\s]*venue=online)",
            r"ai-product-summit-online-2026",
        ],
        "phrases": ["Maya Sandoval", "Head of AI, Stripe"],
        "rubric": "FACT CHECKPOINTS: Filter online Business conferences in June 2026, open the AI conference, and report the first speaker's name and title. A speaker from the other June conference fails.",
    },
    4: {
        "task_id": "Eventbrite--4",
        "nav": [r"/search\?(?=[^#\s]*city=tx--austin)(?=[^#\s]*category=music)(?=[^#\s]*venue=in-person)(?=[^#\s]*max_price=100)(?=[^#\s]*sort=price)"],
        "phrases": ["Knox & Cell & Friends", "Continental Club"],
        "bind": [("continental", 95)],
        "rubric": "FACT CHECKPOINTS: Filter in-person Music in Austin with a maximum price of $100, sort by price, and report the first result's title, venue, and lowest ticket price. A later or over-max result fails.",
    },
    5: {
        "task_id": "Eventbrite--5",
        "nav": [r"science-fiction-kim-stanley-robinson"],
        "phrases": ["Science + Fiction"],
        "pred": sci_date,
        "rubric": "FACT CHECKPOINTS: Find the New York Performing & Visual Arts event whose refund policy is refunds up to 1 day before the event. Report its title and start date. A different refund policy or city fails.",
    },
    6: {
        "task_id": "Eventbrite--6",
        "nav": [r"fillmore-sold-out-night-sf-2026"],
        "phrases": ["The Fillmore", "General Admission (SOLD OUT)", "VIP Balcony (SOLD OUT)"],
        "rubric": "FACT CHECKPOINTS: Identify the sold-out Music event in San Francisco and report its venue and every ticket tier shown as sold out. A different venue, or only one tier when both are sold out, fails.",
    },
    7: {
        "task_id": "Eventbrite--7",
        "nav": [r"ai-product-summit-online-2026"],
        "phrases": ["America/Los_Angeles"],
        "bind": [("tier", 3), ("workshop", 149)],
        "rubric": "FACT CHECKPOINTS: Open AI Product Summit 2026 — Online and report its timezone, how many ticket tiers it has, and the most expensive ticket price. The top price must belong to that event.",
    },
    8: {
        "task_id": "Eventbrite--8",
        "nav": [r"science-fiction-kim-stanley-robinson/ics"],
        "phrases": ["DTSTART:20260616T200000", "Pioneer Works, 159 Pioneer St"],
        "rubric": "FACT CHECKPOINTS: Open the calendar file for Science + Fiction: Kim Stanley Robinson and report its DTSTART and LOCATION lines. A different event's calendar fails.",
    },
    9: {
        "task_id": "Eventbrite--9",
        "nav": [r"/help/search\?[^#\s]*q=refund"],
        "phrases": [
            "How do I get a refund?",
            "The event was cancelled",
            "How long do refunds take?",
            "What if I miss the event?",
        ],
        "bind": [("article", 4)],
        "rubric": "FACT CHECKPOINTS: Search Help Center for refund and report how many articles match and each result title. Do not count navigation chrome, and do not omit a result.",
    },
    10: {
        "task_id": "Eventbrite--10",
        "nav": [r"/c/music"],
        "pred": pill_order,
        "rubric": "FACT CHECKPOINTS: Open the Music category page and report the subcategory pills from Rock through Hip Hop in the order they are displayed. A different span or order fails.",
    },
    11: {
        "task_id": "Eventbrite--11",
        "nav": [r"/blog/p/how-to-promote-your-first-event"],
        "phrases": ["Jules Park", "May 23, 2026"],
        "rubric": "FACT CHECKPOINTS: Open the blog post How to promote your first event on Eventbrite and report its author and publication date. Another post's byline fails.",
    },
    12: {
        "task_id": "Eventbrite--12",
        "nav": [r"15th-annual-bushwick-collective-block-party", r"/likes"],
        "state": state_saved,
        "rubric": "FACT CHECKPOINTS: As alice.j@test.com, save 15th Annual Bushwick Collective Block Party and confirm that title on Likes. A claim that it is saved, with no saved-event row, fails.",
    },
    13: {
        "task_id": "Eventbrite--13",
        "nav": [r"rnb-rooftop-free-rsvp-brooklyn-2026", r"/checkout/"],
        "phrases": ["Maya Lee", "No nuts"],
        "state": state_free_order,
        "rubric": "FACT CHECKPOINTS: As alice.j@test.com, buy 1 Free RSVP for R&B vs Slow Jams Rooftop for Maya Lee with dietary note No nuts. Report the $0.00 total and the stored order code. A paid tier or a missing order row fails.",
    },
    14: {
        "task_id": "Eventbrite--14",
        "nav": [r"science-fiction-kim-stanley-robinson", r"/checkout/"],
        "phrases": ["SUMMER25"],
        "state": state_promo,
        "rubric": "FACT CHECKPOINTS: As alice.j@test.com, complete an order over $100 for Science + Fiction: Kim Stanley Robinson with promo SUMMER25. Report the discount and the persisted receipt total for that order. A discount that was not stored, or a total that does not match the saved order, fails.",
    },
    15: {
        "task_id": "Eventbrite--15",
        "nav": [r"/account"],
        "state": state_city,
        "rubric": "FACT CHECKPOINTS: As alice.j@test.com, change the profile city to Chicago and confirm the city shown on the account. The stored profile must be Chicago, not only the answer text.",
    },
    16: {
        "task_id": "Eventbrite--16",
        "nav": [r"/signup"],
        "state": state_signup,
        "rubric": "FACT CHECKPOINTS: Create the Jordan Lee account with jordan.lee@test.com, confirm the header shows Jordan, log out, and confirm the header stays logged out. An account that was not created fails.",
    },
    17: {
        "task_id": "Eventbrite--17",
        "nav": [r"/country/us", r"/region/west"],
        "phrases": [
            "Los Angeles", "San Francisco", "Seattle", "Denver",
            "Portland", "Phoenix", "Las Vegas", "San Diego",
        ],
        "pred": west_tie,
        "rubric": "FACT CHECKPOINTS: Open the United States page, then the West region, and report every listed city plus which listed cities have the most upcoming events in the displayed counts. A unique winner when the counts are tied fails.",
    },
}
