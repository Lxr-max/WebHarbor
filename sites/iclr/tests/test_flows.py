"""Flow tests: real browser-shaped submissions with CSRF tokens enabled,
the registration exclusivity rule, account flows and the seeded
benchmark states."""
import re

from app import Bookmark, ContactMessage, Registration, ScheduleSave, db
from conftest import with_csrf


class TestAccountFlows:
    def test_login_bad_password(self, client):
        data = with_csrf(client, "/login", {"email": "alice.j@test.com",
                                            "password": "wrong"})
        r = client.post("/login", data=data)
        assert r.status_code == 200
        assert b"Invalid email or password" in r.data

    def test_signup_and_login(self, client):
        data = with_csrf(client, "/signup", {
            "name": "Turing Test", "email": "turing@test.com",
            "password": "Tape1950!"})
        r = client.post("/signup", data=data, follow_redirects=True)
        assert r.status_code == 200
        assert b"My Stuff" in r.data
        client.get("/logout")
        data = with_csrf(client, "/login", {"email": "turing@test.com",
                                            "password": "Tape1950!"})
        r = client.post("/login", data=data, follow_redirects=True)
        assert b"My Stuff" in r.data

    def test_signup_duplicate_email(self, client):
        data = with_csrf(client, "/signup", {
            "name": "Dup", "email": "alice.j@test.com",
            "password": "Passw0rd!"})
        r = client.post("/signup", data=data)
        assert b"already exists" in r.data

    def test_signup_short_password(self, client):
        data = with_csrf(client, "/signup", {
            "name": "Short", "email": "short@test.com", "password": "short"})
        r = client.post("/signup", data=data)
        assert b"at least 8 characters" in r.data

    def test_login_required_redirects(self, client):
        r = client.get("/mystuff")
        assert r.status_code == 302
        assert "/login" in r.headers["Location"]


class TestBookmarkFlows:
    def test_bookmark_toggle(self, alice_client):
        r = alice_client.get("/papers/10006395")
        assert b"Bookmark this paper" in r.data
        data = with_csrf(alice_client, "/papers/10006395", {
            "paper_id": "10006395", "back": "/papers/10006395"})
        r = alice_client.post("/bookmarks/toggle", data=data,
                             follow_redirects=True)
        assert b"Remove from My Bookmarks" in r.data
        db.session.commit()  # end the stale read transaction, then verify
        assert Bookmark.query.filter_by(user_id=1,
                                        paper_id=10006395).first() is not None
        r = alice_client.post("/bookmarks/toggle", data=data,
                              follow_redirects=True)
        assert b"Bookmark this paper" in r.data
        db.session.commit()
        assert Bookmark.query.filter_by(user_id=1,
                                        paper_id=10006395).first() is None

    def test_bookmark_invalid_paper_fails_closed(self, alice_client):
        data = with_csrf(alice_client, "/papers/10006831", {
            "paper_id": "99999999", "back": "/papers/10006831"})
        r = alice_client.post("/bookmarks/toggle", data=data)
        assert r.status_code == 400

    def test_alice_seed_bookmarks_render(self, alice_client):
        r = alice_client.get("/mystuff")
        assert r.status_code == 200
        cards = r.data.count(b'paper-row')
        bookmarks = Bookmark.query.filter_by(user_id=1).count()
        assert cards == bookmarks  # count == rendered cards (disney r1 #6)
        assert b"Transformers are Inherently Succinct" in r.data


class TestScheduleFlows:
    def test_save_and_unsave_event(self, bob_client):
        # 10000772 (ICBINB) is already in Bob's seed schedule, so the first
        # toggle removes it and the second re-adds it
        data = with_csrf(bob_client, "/events/10000772", {
            "event_id": "10000772", "back": "/events/10000772"})
        r = bob_client.post("/schedule/save", data=data,
                            follow_redirects=True)
        assert b"Add to My Schedule" in r.data
        assert ScheduleSave.query.filter_by(event_id=10000772).first() is None
        r = bob_client.post("/schedule/save", data=data,
                            follow_redirects=True)
        assert b"Remove from My Schedule" in r.data

    def test_save_invalid_event_fails_closed(self, bob_client):
        data = with_csrf(bob_client, "/events/10000772", {
            "event_id": "99999999", "back": "/events/10000772"})
        r = bob_client.post("/schedule/save", data=data)
        assert r.status_code == 400

    def test_carol_seed_schedule(self, carol_client):
        r = carol_client.get("/mystuff")
        assert b"Marin: Open Development of Frontier AI" in r.data
        assert b"VerifAI-2" in r.data


class TestRegistrationFlows:
    def test_register_success(self, client):
        data = with_csrf(client, "/register", {
            "name": "Grace Hopper", "email": "grace@test.com",
            "affiliation": "Academic",
            "items": ["Virtual Only Pass"], "banquet_tickets": "2",
            "dietary": "Vegan"})
        r = client.post("/register", data=data, follow_redirects=True)
        assert r.status_code == 200
        code = re.search(r"ICLR26-[0-9A-F]{8}", r.data.decode()).group(0)
        reg = Registration.query.filter_by(reg_code=code).one()
        assert reg.banquet_tickets == 2
        assert reg.total_usd == 100
        assert reg.dietary == "Vegan"
        assert code in r.data.decode()
        assert b"$100 USD" in r.data

    def test_exclusivity_rule(self, client):
        data = with_csrf(client, "/register", {
            "name": "X", "email": "x@test.com",
            "affiliation": "Industrial",
            "items": ["Conference Sessions and Workshops",
                      "Sunday Workshop 1 Day Pass"],
            "banquet_tickets": "0"})
        r = client.post("/register", data=data)
        assert b"do not check any other items" in r.data
        assert Registration.query.filter_by(email="x@test.com").first() is None

    def test_no_items_rejected(self, client):
        data = with_csrf(client, "/register", {
            "name": "X", "email": "x@test.com",
            "affiliation": "Industrial", "items": [],
            "banquet_tickets": "0"})
        r = client.post("/register", data=data)
        assert b"at least one registration item" in r.data

    def test_bad_affiliation_rejected(self, client):
        data = with_csrf(client, "/register", {
            "name": "X", "email": "x@test.com",
            "affiliation": "Corporate", "items": ["Virtual Only Pass"],
            "banquet_tickets": "0"})
        r = client.post("/register", data=data)
        assert b"affiliation type" in r.data

    def test_confirmation_requires_real_code(self, client):
        assert client.get("/register/confirmation/ICLR26-NOPE0000").status_code == 404

    def test_alice_seed_registration_in_mystuff(self, alice_client):
        r = alice_client.get("/mystuff")
        assert b"ICLR26-A1B2C3D4" in r.data
        assert b"$50 USD" in r.data

    def test_mystuff_registration_shows_registrant(self, alice_client):
        """r2 fix F-3: the registration history line must render the
        registrant name and affiliation so the on-page answer exists."""
        r = alice_client.get("/mystuff")
        assert b"Alice Johnson (Full time student)" in r.data


class TestHelpdeskFlows:
    def test_contact_success(self, client):
        data = with_csrf(client, "/helpdesk", {
            "name": "Ada Lovelace", "email": "ada@test.com",
            "topic": "program-chairs@iclr.cc", "subject": "Paper question",
            "body": "Where is my paper?"})
        r = client.post("/helpdesk", data=data, follow_redirects=True)
        assert b"has been sent" in r.data
        assert ContactMessage.query.filter_by(
            email="ada@test.com").count() == 1

    def test_contact_bad_topic(self, client):
        data = with_csrf(client, "/helpdesk", {
            "name": "A", "email": "a@test.com",
            "topic": "not-a-topic@iclr.cc", "subject": "s", "body": "b"})
        r = client.post("/helpdesk", data=data)
        assert b"Choose an email topic" in r.data


class TestCsrf:
    def test_unsigned_posts_rejected(self, client):
        for path, data in [
            ("/login", {"email": "alice.j@test.com",
                        "password": "TestPass123!"}),
            ("/signup", {"name": "n", "email": "n@t.com",
                          "password": "Passw0rd!"}),
            ("/register", {"name": "n", "email": "n@t.com",
                            "affiliation": "Academic",
                            "items": ["Virtual Only Pass"]}),
            ("/helpdesk", {"name": "n", "email": "n@t.com",
                           "topic": "press@iclr.cc", "subject": "s",
                           "body": "b"}),
            ("/bookmarks/toggle", {"paper_id": "10006831"}),
            ("/schedule/save", {"event_id": "10000772"}),
        ]:
            assert client.post(path, data=data).status_code == 400, path
