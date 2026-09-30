import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest


SITE = Path(__file__).resolve().parents[1]
TMP = tempfile.TemporaryDirectory()
DB_PATH = Path(TMP.name) / "eventbrite.db"
os.environ["EVENTBRITE_DB_PATH"] = str(DB_PATH)
spec = importlib.util.spec_from_file_location("eventbrite_app", SITE / "app.py")
site = importlib.util.module_from_spec(spec)
spec.loader.exec_module(site)
site.app.template_folder = str(SITE / "templates")
site.app.static_folder = str(SITE / "static")


class EventbriteRegressionTests(unittest.TestCase):
    def setUp(self):
        self.client = site.app.test_client()

    def login(self):
        response = self.client.post(
            "/login",
            data={"email": "alice.j@test.com", "password": "alice12345"},
        )
        self.assertEqual(response.status_code, 302)

    def select(self, slug, tier_id, qty):
        return self.client.post(
            f"/checkout/{slug}", data={f"qty_{tier_id}": str(qty)}
        )

    def attendees(self, slug, count, tier_id):
        data = {"qa_dietary": "No nuts"}
        for index in range(count):
            data[f"name_{index}"] = f"Attendee {index + 1}"
            data[f"email_{index}"] = f"attendee{index + 1}@test.com"
        return self.client.post(f"/checkout/{slug}/attendees", data=data)

    def test_auth_registration_and_logout_stays_logged_out(self):
        self.assertEqual(self.client.get("/dev/login/alice_j").status_code, 404)
        response = self.client.get("/")
        self.assertNotIn(b"</text></svg>", response.data)
        self.assertNotIn(b'<rect width=', response.data)
        self.assertIn(b"Log In", response.data)
        self.assertNotIn(b"Alice</a>", response.data)

        response = self.client.post(
            "/register",
            data={
                "name": "Jordan Lee",
                "email": "jordan.unique@test.com",
                "password": "JordanPass123",
            },
            follow_redirects=True,
        )
        self.assertIn(b"Jordan</a>", response.data)
        response = self.client.post("/logout", follow_redirects=True)
        self.assertIn(b"Log In", response.data)
        self.assertNotIn(b"Jordan</a>", response.data)

    def test_search_form_and_links_preserve_combined_constraints(self):
        url = (
            "/search?city=tx--austin&category=music&venue=in-person"
            "&language=English&when=this-month&sort=price"
        )
        response = self.client.get(url)
        body = response.get_data(as_text=True)
        for field, value in (
            ("city", "tx--austin"),
            ("category", "music"),
            ("venue", "in-person"),
            ("language", "English"),
            ("when", "this-month"),
            ("sort", "price"),
        ):
            self.assertIn(f'name="{field}" value="{value}"', body)
        self.assertIn("category=music", body)
        self.assertIn("venue=in-person", body)
        self.assertIn("city=tx--austin", body)

        response = self.client.get(
            "/search?city=tx--austin&category=music&venue=in-person"
            "&max_price=100&sort=price"
        )
        self.assertIn(b"Knox &amp; Cell &amp; Friends", response.data)
        self.assertNotIn(b"AI Product Summit", response.data)

    def test_custom_dates_replace_relative_date_filter(self):
        response = self.client.get(
            "/search?when=today&from=2026-06-01&to=2026-06-30"
            "&venue=online&category=business&format=Conference"
        )
        self.assertIn(b"AI Product Summit 2026", response.data)

    def test_search_ignores_invalid_filter_values(self):
        response = self.client.get(
            "/search?city=unknown&category=unknown&format=Unknown"
            "&price=unknown&venue=unknown&language=Unknown&when=unknown"
            "&max_price=nan&sort=unknown"
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(b"unknown", response.data.lower())
        self.assertIn(b'<option value="date"        selected>', response.data)
        self.assertIn(b"/search?sort=SORT_VALUE", response.data)

        for invalid_price in ("-1", "inf"):
            with self.subTest(max_price=invalid_price):
                response = self.client.get(f"/search?max_price={invalid_price}")
                self.assertEqual(response.status_code, 200)
                self.assertNotIn(
                    f'name="max_price" value="{invalid_price}"'.encode(),
                    response.data,
                )

    def test_shared_breadcrumb_parents_link_to_existing_hubs(self):
        cases = {
            "/d/ny--new-york/all-events/": 'href="/country/us">Cities</a>',
            "/events/today": 'href="/search">Events</a>',
            "/c/music": 'href="/sitemap">Categories</a>',
        }
        for path, expected_link in cases.items():
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                body = response.get_data(as_text=True)
                self.assertIn(expected_link, body)
                self.assertNotIn('href="/d">', body)
                self.assertNotIn('href="/events">', body)
                self.assertNotIn('href="/c">', body)

    def test_text_search_includes_events_after_first_500_rows(self):
        with site.app.app_context():
            event = site.db.session.get(site.Event, 862)
            self.assertEqual(event.title, "Women in AI: 2027 Annual (Online)")
        response = self.client.get("/search?q=Women+in+AI+2027+Annual")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Women in AI: 2027 Annual (Online)", response.data)

    def test_login_next_only_allows_local_paths(self):
        credentials = {"email": "alice.j@test.com", "password": "alice12345"}
        for target in ("https://example.com/steal", "//example.com/steal"):
            with self.subTest(target=target):
                client = site.app.test_client()
                response = client.post(f"/login?next={target}", data=credentials)
                self.assertEqual(response.status_code, 302)
                self.assertEqual(response.location, "/")

        client = site.app.test_client()
        response = client.post(
            "/login?next=/account/saved",
            data=credentials,
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.location, "/account/saved")

    def test_mixed_free_event_has_zero_minimum_price(self):
        with site.app.app_context():
            event = site.Event.query.filter_by(
                slug="ai-product-summit-online-2026"
            ).one()
            self.assertEqual(event.min_price(), 0.0)
            self.assertFalse(event.is_free())

    def test_quantity_is_clamped_and_attendee_count_must_match(self):
        self.login()
        slug = "science-fiction-kim-stanley-robinson"
        response = self.select(slug, 5, 999)
        self.assertEqual(response.location, f"/checkout/{slug}/attendees")
        with self.client.session_transaction() as session:
            self.assertEqual(session["eb_cart"]["items"][0][1], 10)
            session["eb_attendees"] = [{"tier_id": 5, "name": "Only", "email": "one@test.com"}]
        response = self.client.get(f"/checkout/{slug}/payment")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.location, f"/checkout/{slug}")

    def test_stale_price_is_rejected_before_payment(self):
        self.login()
        slug = "science-fiction-kim-stanley-robinson"
        self.select(slug, 5, 2)
        self.attendees(slug, 2, 5)
        with site.app.app_context():
            tier = site.db.session.get(site.TicketTier, 5)
            original = tier.price
            tier.price = original + 1
            site.db.session.commit()
        try:
            response = self.client.get(f"/checkout/{slug}/payment")
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.location, f"/checkout/{slug}")
        finally:
            with site.app.app_context():
                tier = site.db.session.get(site.TicketTier, 5)
                tier.price = original
                site.db.session.commit()

    def test_checkout_state_is_bound_to_user_and_cleared_on_logout(self):
        self.login()
        slug = "science-fiction-kim-stanley-robinson"
        self.select(slug, 5, 1)
        with self.client.session_transaction() as session:
            self.assertEqual(session["eb_cart"]["user_id"], 1)
        self.client.post("/logout")
        with self.client.session_transaction() as session:
            self.assertNotIn("eb_cart", session)
            self.assertNotIn("eb_attendees", session)
            self.assertNotIn("eb_qa", session)
        self.client.post(
            "/login",
            data={"email": "bob.s@test.com", "password": "bobpassword"},
        )
        response = self.client.get(f"/checkout/{slug}/attendees")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.location, f"/checkout/{slug}")

    def test_ticket_outside_sale_window_cannot_enter_checkout_or_cart(self):
        self.login()
        slug = "science-fiction-kim-stanley-robinson"
        with site.app.app_context():
            tier = site.db.session.get(site.TicketTier, 5)
            original_end = tier.sale_end
            tier.sale_end = site.benchmark_now() - site.timedelta(seconds=1)
            site.db.session.commit()
        try:
            response = self.select(slug, 5, 1)
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.location, f"/checkout/{slug}")
            with self.client.session_transaction() as session:
                self.assertNotIn("eb_cart", session)
            response = self.client.post(
                "/cart/add",
                data={"tier_id": "5", "qty": "1"},
                headers={"Referer": f"/e/{slug}"},
            )
            self.assertEqual(response.status_code, 302)
            with site.app.app_context():
                self.assertEqual(
                    site.CartItem.query.filter_by(user_id=1, tier_id=5).count(),
                    0,
                )
        finally:
            with site.app.app_context():
                tier = site.db.session.get(site.TicketTier, 5)
                tier.sale_end = original_end
                site.db.session.commit()

    def test_cart_rejects_cumulative_quantity_over_remaining_inventory(self):
        self.login()
        with site.app.app_context():
            tier = site.db.session.get(site.TicketTier, 5)
            original_sold = tier.sold
            tier.sold = tier.capacity - 3
            site.db.session.add(
                site.CartItem(user_id=1, event_id=tier.event_id, tier_id=tier.id, qty=2)
            )
            site.db.session.commit()
        try:
            response = self.client.post(
                "/cart/add",
                data={"tier_id": "5", "qty": "2"},
            )
            self.assertEqual(response.status_code, 302)
            with site.app.app_context():
                item = site.CartItem.query.filter_by(user_id=1, tier_id=5).one()
                self.assertEqual(item.qty, 2)
        finally:
            with site.app.app_context():
                site.CartItem.query.filter_by(user_id=1, tier_id=5).delete()
                tier = site.db.session.get(site.TicketTier, 5)
                tier.sold = original_sold
                site.db.session.commit()

    def test_free_order_persists_ticket_attendee_and_zero_total(self):
        self.login()
        slug = "rnb-rooftop-free-rsvp-brooklyn-2026"
        self.select(slug, 1, 1)
        self.attendees(slug, 1, 1)
        response = self.client.post(
            f"/checkout/{slug}/payment",
            data={"billing_name": "Alice Johnson", "billing_email": "alice.j@test.com"},
        )
        self.assertEqual(response.status_code, 302)
        with site.app.app_context():
            order = site.Order.query.order_by(site.Order.id.desc()).first()
            self.assertEqual(order.total, 0.0)
            self.assertEqual(order.items[0].qty, 1)
            self.assertEqual(len(order.tickets), 1)
            self.assertEqual(order.tickets[0].attendee_email, "attendee1@test.com")

    def test_promo_discount_is_visible_and_persisted(self):
        self.login()
        slug = "science-fiction-kim-stanley-robinson"
        self.select(slug, 7, 2)
        self.attendees(slug, 2, 7)
        response = self.client.post(
            f"/checkout/{slug}/promo",
            data={"code": "SUMMER25"},
            follow_redirects=True,
        )
        self.assertIn(b"Discount (SUMMER25)", response.data)
        self.assertIn(b"$125.00", response.data)
        response = self.client.post(
            f"/checkout/{slug}/payment",
            data={"billing_name": "Alice Johnson", "billing_email": "alice.j@test.com"},
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Total paid $125.00", response.data)
        with site.app.app_context():
            order = site.Order.query.order_by(site.Order.id.desc()).first()
            self.assertEqual(order.total, 125.0)
            self.assertEqual(json.loads(order.notes)["promo_code"], "SUMMER25")
            self.assertEqual(sum(item.qty for item in order.items), 2)
            self.assertEqual(len(order.tickets), 2)
            order_code = order.code
        response = self.client.get(f"/order/{order_code}")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Total paid $125.00", response.data)

    def test_every_submitted_task_has_a_candidate_or_working_flow(self):
        tasks = [json.loads(line) for line in (SITE / "tasks.jsonl").read_text().splitlines()]
        self.assertEqual(len(tasks), 18)
        self.assertEqual([task["id"] for task in tasks], [f"Eventbrite--{i}" for i in range(18)])
        self.assertTrue(all(set(task) == {"web_name", "id", "ques", "web", "upstream_url", "verifier_path", "judge_rubric"} for task in tasks))
        self.assertTrue(all(task["web"] == "http://localhost:40116/" for task in tasks))

        with site.app.app_context():
            titles = {event.title for event in site.Event.query.all()}
            required = {
                "Science + Fiction: Kim Stanley Robinson",
                "AI Product Summit 2026 — Online",
                "Knox & Cell & Friends — Acoustic Showcase",
                "15th Annual Bushwick Collective Block Party",
                "R&B vs Slow Jams Rooftop — Free with RSVP",
            }
            self.assertTrue(required <= titles)
            self.assertEqual(site.Event.query.count(), 933)
            self.assertEqual(site.Organizer.query.count(), 215)
            self.assertEqual(site.TicketTier.query.count(), 1865)
            austin = (
                site.Event.query.filter_by(
                    city_slug="tx--austin", category_slug="music", is_online=False
                ).one()
            )
            self.assertLessEqual(austin.min_price(), 100)
            june_ai = (
                site.Event.query.filter_by(
                    slug="ai-product-summit-online-2026",
                    is_online=True,
                    category_slug="business",
                    format="Conference",
                ).one()
            )
            self.assertEqual(june_ai.start_dt.strftime("%Y-%m"), "2026-06")
            self.assertTrue(june_ai.get_speakers())
            weekend_free_music = [
                event for event in site.Event.query.filter_by(
                    city_slug="ny--new-york", category_slug="music", is_online=False
                ).all()
                if event.start_dt.date().isoformat() in {"2026-05-30", "2026-05-31"}
                and event.min_price() == 0
            ]
            self.assertTrue(weekend_free_music)
            self.assertEqual(
                site.Event.query.filter_by(
                    city_slug="ca--san-francisco", category_slug="music"
                ).filter(site.Event.slug == "fillmore-sold-out-night-sf-2026").count(),
                1,
            )
            self.assertTrue(
                site.HelpArticle.query.filter(
                    site.HelpArticle.title.ilike("%refund%")
                ).count()
            )
            self.assertTrue(
                site.BlogPost.query.filter_by(
                    slug="how-to-promote-your-first-event"
                ).first()
            )

        task_paths = {
            0: "/search?city=ny--new-york&category=music&price=free&when=this-weekend",
            1: "/e/science-fiction-kim-stanley-robinson",
            2: "/search?q=AI+Product+Summit",
            3: "/search?category=business&venue=online&format=Conference&from=2026-06-01&to=2026-06-30",
            4: "/search?city=tx--austin&category=music&venue=in-person&max_price=100&sort=price",
            5: "/search?city=ny--new-york&category=arts",
            6: "/e/fillmore-sold-out-night-sf-2026",
            7: "/e/ai-product-summit-online-2026",
            8: "/e/science-fiction-kim-stanley-robinson/ics",
            9: "/help/search?q=refund",
            10: "/c/music",
            11: "/blog",
            12: "/e/15th-annual-bushwick-collective-block-party",
            13: "/e/rnb-rooftop-free-rsvp-brooklyn-2026",
            14: "/e/science-fiction-kim-stanley-robinson",
            15: "/login",
            16: "/register",
            17: "/region/west",
        }
        self.assertEqual(set(task_paths), set(range(len(tasks))))
        for task_id, path in task_paths.items():
            with self.subTest(task_id=task_id, path=path):
                self.assertEqual(self.client.get(path).status_code, 200)

    def test_review_calendar_preserves_timezone(self):
        response = self.client.get('/e/science-fiction-kim-stanley-robinson/ics')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'DTSTART:20260617T000000Z', response.data)
        self.assertIn(b'DTEND:20260617T020000Z', response.data)
        self.assertIn(b'Pioneer Works\\, 159 Pioneer St', response.data)

    def test_review_questions_are_visible_after_submission(self):
        marker = 'Does the recording include questions from remote attendees?'
        response = self.client.post('/e/ai-product-summit-online-2026/qa',
            data={'name': 'Review Reader', 'question': marker}, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(marker.encode(), response.data)
        self.assertIn(b'Review Reader', response.data)


if __name__ == "__main__":
    unittest.main()
