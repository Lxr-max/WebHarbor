"""No-op, shortcut, wrong-answer, state-mismatch, and pass cases."""

import json
import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path

from verify_lib import TASKS, evaluate

SEED = Path(__file__).resolve().parents[1] / "instance_seed" / "eventbrite.db"
BASE = "http://localhost:40100"

PASS_URLS = {
    0: ["/search?city=ny--new-york&category=music&price=free&when=this-weekend"],
    1: ["/e/science-fiction-kim-stanley-robinson", "/checkout/science-fiction-kim-stanley-robinson/payment"],
    2: ["/e/ai-product-summit-online-2026", "/e/science-fiction-kim-stanley-robinson"],
    3: ["/search?category=business&format=Conference&venue=online&from=2026-06-01&to=2026-06-30", "/e/ai-product-summit-online-2026"],
    4: ["/search?city=tx--austin&category=music&venue=in-person&max_price=100&sort=price"],
    5: ["/e/science-fiction-kim-stanley-robinson"],
    6: ["/e/fillmore-sold-out-night-sf-2026"],
    7: ["/e/ai-product-summit-online-2026"],
    8: ["/e/science-fiction-kim-stanley-robinson/ics"],
    9: ["/help/search?q=refund"],
    10: ["/c/music"],
    11: ["/blog/p/how-to-promote-your-first-event"],
    12: ["/e/15th-annual-bushwick-collective-block-party", "/likes"],
    13: ["/e/rnb-rooftop-free-rsvp-brooklyn-2026", "/checkout/rnb-rooftop-free-rsvp-brooklyn-2026/payment"],
    14: ["/e/science-fiction-kim-stanley-robinson", "/checkout/science-fiction-kim-stanley-robinson/payment"],
    15: ["/account/edit", "/account"],
    16: ["/signup", "/"],
    17: ["/country/us", "/region/west"],
}

PASS_ANSWERS = {
    0: "R&B vs Slow Jams Rooftop — Free with RSVP at The DL Rooftop.",
    1: "Order EBTEST01 for Alice Johnson and Sam Chen, total $50.00.",
    2: "AI Product Summit is $0, which is cheaper than the Science + Fiction member price of $15. The difference is $15.",
    3: "The first speaker is Maya Sandoval, Head of AI, Stripe.",
    4: "Knox & Cell & Friends — Acoustic Showcase at Continental Club, lowest ticket $95.",
    5: "Science + Fiction: Kim Stanley Robinson starts on June 16, 2026.",
    6: "Venue The Fillmore. Sold-out tiers: General Admission (SOLD OUT) and VIP Balcony (SOLD OUT).",
    7: "Timezone America/Los_Angeles, 3 ticket tiers, most expensive is the Workshop Pass at $149.",
    8: "DTSTART:20260616T200000 and LOCATION:Pioneer Works, 159 Pioneer St, Brooklyn, NY 11231.",
    9: "4 matching articles: How do I get a refund?; The event was cancelled; How long do refunds take?; What if I miss the event?",
    10: "From Rock through Hip Hop the pills are Rock, EDM, and Hip Hop.",
    11: "Author Jules Park, published May 23, 2026.",
    12: "15th Annual Bushwick Collective Block Party appears on Likes.",
    13: "Maya Lee, dietary No nuts, total $0.00, order code EBFREE0001.",
    14: "Promo SUMMER25 takes $25 off. The persisted receipt total is $125.00.",
    15: "My Account now shows Chicago.",
    16: "The header showed Jordan, then I logged out and it stayed logged out.",
    17: "Listed cities: Los Angeles 31, San Francisco 32, Seattle 27, Denver 32, Portland 31, Phoenix 31, Las Vegas 32, San Diego 30. San Francisco, Denver, and Las Vegas tie.",
}


def traj(answer, paths):
    return {
        "start_url": BASE + "/",
        "final_answer": answer,
        "steps": [{"step": i, "url": BASE + path} for i, path in enumerate(paths)],
    }


def mutate(index, path):
    conn = sqlite3.connect(path)
    uid = conn.execute("SELECT id FROM users WHERE email='alice.j@test.com'").fetchone()[0]
    if index == 1:
        eid = conn.execute("SELECT id FROM events WHERE slug='science-fiction-kim-stanley-robinson'").fetchone()[0]
        tier = conn.execute("SELECT id FROM ticket_tiers WHERE event_id=? AND name='General Admission'", (eid,)).fetchone()[0]
        cur = conn.execute(
            "INSERT INTO orders (code, user_id, event_id, total, status, contact_email, contact_name, notes, created_at) VALUES ('EBTEST01', ?, ?, 50, 'confirmed', 'alice.j@test.com', 'Alice', '{}', '2026-09-01')",
            (uid, eid),
        )
        oid = cur.lastrowid
        conn.execute("INSERT INTO order_items (order_id, tier_id, qty, unit_price) VALUES (?, ?, 2, 25)", (oid, tier))
        conn.execute("INSERT INTO issued_tickets (order_id, tier_id, code, attendee_name, attendee_email) VALUES (?, ?, 'A', 'Alice Johnson', 'alice.j@test.com')", (oid, tier))
        conn.execute("INSERT INTO issued_tickets (order_id, tier_id, code, attendee_name, attendee_email) VALUES (?, ?, 'B', 'Sam Chen', 'sam.chen@test.com')", (oid, tier))
    elif index == 12:
        eid = conn.execute("SELECT id FROM events WHERE slug='15th-annual-bushwick-collective-block-party'").fetchone()[0]
        conn.execute("INSERT INTO saved_events (user_id, event_id, saved_at) VALUES (?, ?, '2026-09-01')", (uid, eid))
    elif index == 13:
        eid = conn.execute("SELECT id FROM events WHERE slug='rnb-rooftop-free-rsvp-brooklyn-2026'").fetchone()[0]
        tier = conn.execute("SELECT id FROM ticket_tiers WHERE event_id=? AND price=0", (eid,)).fetchone()[0]
        cur = conn.execute(
            "INSERT INTO orders (code, user_id, event_id, total, status, contact_email, contact_name, notes, created_at) VALUES ('EBFREE0001', ?, ?, 0, 'confirmed', 'alice.j@test.com', 'Alice', ?, '2026-09-01')",
            (uid, eid, json.dumps({"dietary": "No nuts"})),
        )
        oid = cur.lastrowid
        conn.execute("INSERT INTO order_items (order_id, tier_id, qty, unit_price) VALUES (?, ?, 1, 0)", (oid, tier))
        conn.execute("INSERT INTO issued_tickets (order_id, tier_id, code, attendee_name, attendee_email) VALUES (?, ?, 'C', 'Maya Lee', 'maya.lee@test.com')", (oid, tier))
    elif index == 14:
        eid = conn.execute("SELECT id FROM events WHERE slug='science-fiction-kim-stanley-robinson'").fetchone()[0]
        tier = conn.execute("SELECT id FROM ticket_tiers WHERE event_id=? AND name='VIP Reception'", (eid,)).fetchone()[0]
        cur = conn.execute(
            "INSERT INTO orders (code, user_id, event_id, total, status, contact_email, contact_name, notes, created_at) VALUES ('EBPROMO125', ?, ?, 125, 'confirmed', 'alice.j@test.com', 'Alice', ?, '2026-09-01')",
            (uid, eid, json.dumps({"promo_code": "SUMMER25", "discount": 25})),
        )
        conn.execute("INSERT INTO order_items (order_id, tier_id, qty, unit_price) VALUES (?, ?, 2, 75)", (cur.lastrowid, tier))
    elif index == 15:
        conn.execute("UPDATE users SET city='Chicago' WHERE email='alice.j@test.com'")
    elif index == 16:
        conn.execute(
            "INSERT INTO users (email, password_hash, name, city, created_at) VALUES ('jordan.lee@test.com', 'x', 'Jordan Lee', '', '2026-09-01')"
        )
    conn.commit()
    conn.close()


class EventbriteVerifierTests(unittest.TestCase):
    def test_matrix(self):
        for index in range(18):
            with self.subTest(task=index, case="noop"):
                self.assertFalse(evaluate(index, traj("", ["/"]))["pass"])
            with self.subTest(task=index, case="shortcut"):
                self.assertFalse(evaluate(index, traj(PASS_ANSWERS[index], ["/"]))["pass"])
            with self.subTest(task=index, case="wrong"):
                verdict = evaluate(index, traj("Nothing matched. The venue is Nowhere Hall.", PASS_URLS[index]))
                self.assertFalse(verdict["pass"], verdict)
            stateful = bool(TASKS[index].get("state"))
            with tempfile.TemporaryDirectory() as tmp:
                seed_copy = str(Path(tmp) / "seed.db")
                after = str(Path(tmp) / "after.db")
                shutil.copy(SEED, seed_copy)
                shutil.copy(SEED, after)
                if stateful:
                    with self.subTest(task=index, case="state-mismatch"):
                        verdict = evaluate(index, traj(PASS_ANSWERS[index], PASS_URLS[index]), seed_copy, after)
                        self.assertFalse(verdict["pass"], verdict)
                    mutate(index, after)
                with self.subTest(task=index, case="pass"):
                    verdict = evaluate(index, traj(PASS_ANSWERS[index], PASS_URLS[index]), seed_copy, after)
                    self.assertTrue(verdict["pass"], verdict)

    def test_right_price_wrong_event(self):
        verdict = evaluate(
            2,
            traj(
                "Science + Fiction is $0 and cheaper. AI Product Summit is $15. The difference is $15.",
                PASS_URLS[2],
            ),
        )
        self.assertFalse(verdict["pass"], verdict)


if __name__ == "__main__":
    unittest.main()
