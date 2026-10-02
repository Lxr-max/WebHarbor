"""Flow tests with CSRF enabled: accounts, backpack toggles, saved programs,
saved events and the request-info form, exactly the way a browser drives them."""
import re

import app as umich_app
from conftest import with_csrf, app_ctx

from app import (BackpackItem, EventItem, InfoRequest, Program, SavedEvent,
                 SavedProgram, Section, User, db)


class TestSignupLogin:
    def test_signup_creates_and_logs_in(self, client):
        data = with_csrf(client, "/signup", {
            "name": "Test Wolverine", "email": "wolverine.t@test.com",
            "password": "TestPass456!"})
        r = client.post("/signup", data=data, follow_redirects=True)
        assert r.status_code == 200
        assert b"wolverine.t@test.com" not in r.data  # never echo the email
        assert b"My U-M" in r.data

    def test_signup_rejects_short_password(self, client):
        data = with_csrf(client, "/signup", {
            "name": "Short Pw", "email": "short.pw@test.com",
            "password": "short"})
        r = client.post("/signup", data=data)
        assert r.status_code == 200
        assert b"at least 8 characters" in r.data

    def test_signup_rejects_duplicate_email(self, client):
        data = with_csrf(client, "/signup", {
            "name": "Alice Again", "email": "alice.j@test.com",
            "password": "TestPass123!"})
        r = client.post("/signup", data=data)
        assert b"already exists" in r.data

    def test_login_rejects_bad_password(self, client):
        data = with_csrf(client, "/login", {
            "email": "alice.j@test.com", "password": "wrong"})
        r = client.post("/login", data=data)
        assert r.status_code == 200
        assert b"Invalid email or password" in r.data

    def test_unsigned_login_post_rejected(self, client):
        r = client.post("/login", data={"email": "alice.j@test.com",
                                        "password": "TestPass123!"})
        assert r.status_code == 400  # CSRF fails closed


class TestBackpack:
    def test_myumich_requires_login(self, client):
        r = client.get("/myumich")
        assert r.status_code in (302, 303)

    def test_alice_backpack_seeded(self, alice_client):
        r = alice_client.get("/myumich")
        assert r.status_code == 200
        assert b"CHEM 125" in r.data
        assert b"MATH 115" in r.data

    def test_backpack_toggle_add_and_remove(self, alice_client):
        with app_ctx():
            sec = Section.query.filter_by(class_nbr="32104").first()
        data = with_csrf(alice_client, f"/courses/class/{sec.class_nbr}", {})
        r = alice_client.post(f"/backpack/toggle/{sec.id}", data=data,
                              follow_redirects=True)
        assert r.status_code == 200
        assert b"Backpack" in r.data
        with app_ctx():
            rows = BackpackItem.query.filter_by(user_id=1).count()
        assert rows == 3  # alice had 2 seeded
        # toggle again removes it
        r2 = alice_client.post(f"/backpack/toggle/{sec.id}", data=data,
                               follow_redirects=True)
        with app_ctx():
            assert BackpackItem.query.filter_by(user_id=1).count() == 2

    def test_backpack_toggle_requires_csrf(self, alice_client):
        with app_ctx():
            sec = Section.query.first()
        r = alice_client.post(f"/backpack/toggle/{sec.id}", data={})
        assert r.status_code == 400

    def test_backpack_is_per_user(self, bob_client):
        r = bob_client.get("/myumich")
        assert r.status_code == 200
        assert b"CHEM 125" not in r.data  # that's alice's backpack
        assert b"ECON 101" in r.data


class TestSavedPrograms:
    def test_save_program(self, alice_client):
        with app_ctx():
            p = Program.query.filter_by(name="Nursing").first()
        data = with_csrf(alice_client, f"/programs/{p.id}", {})
        r = alice_client.post(f"/programs/save/{p.id}", data=data,
                              follow_redirects=True)
        assert r.status_code == 200
        with app_ctx():
            saved = SavedProgram.query.filter_by(user_id=1).count()
        assert saved == 2  # alice had 1 seeded
        r2 = alice_client.get("/myumich")
        assert b"Nursing" in r2.data

    def test_save_program_idempotent(self, alice_client):
        with app_ctx():
            p = Program.query.filter_by(name="Biology").first()
        data = with_csrf(alice_client, f"/programs/{p.id}", {})
        alice_client.post(f"/programs/save/{p.id}", data=data)
        alice_client.post(f"/programs/save/{p.id}", data=data)
        with app_ctx():
            assert SavedProgram.query.filter_by(
                user_id=1, program_id=p.id).count() == 1


class TestSavedEvents:
    def test_save_event(self, carol_client):
        with app_ctx():
            e = EventItem.query.filter_by(name="T.REX").first()
        data = with_csrf(carol_client, f"/events/{e.eid}", {})
        r = carol_client.post(f"/events/save/{e.eid}", data=data,
                              follow_redirects=True)
        assert r.status_code == 200
        r2 = carol_client.get("/myumich")
        assert b"T.REX" in r2.data

    def test_saved_events_seeded(self, dana_client):
        r = dana_client.get("/myumich")
        assert b"Susan Werner" in r.data


class TestRequestInfo:
    def test_request_info_flow(self, client):
        data = with_csrf(client, "/admissions/request-info", {
            "name": "Prospective Parent", "email": "parent.p@test.com",
            "audience": "Parent or Guardian",
            "message": "When is the next campus tour?"})
        r = client.post("/admissions/request-info", data=data)
        assert r.status_code in (302, 303)
        follow = client.get("/admissions/request-info/thanks?name=Prospective+Parent")
        assert b"Prospective Parent" in follow.data
        with app_ctx():
            row = InfoRequest.query.filter_by(email="parent.p@test.com").first()
        assert row is not None
        assert row.audience == "Parent or Guardian"

    def test_request_info_validation(self, client):
        data = with_csrf(client, "/admissions/request-info", {
            "name": "", "email": "not-an-email", "audience": ""})
        r = client.post("/admissions/request-info", data=data)
        assert r.status_code == 200
        assert b"Enter your full name" in r.data

    def test_request_info_requires_csrf(self, client):
        r = client.post("/admissions/request-info", data={
            "name": "X", "email": "x@y.com", "audience": "Counselor"})
        assert r.status_code == 400


class TestMyUmirchAggregates:
    def test_carol_view(self, carol_client):
        r = carol_client.get("/myumich")
        assert r.status_code == 200
        assert b"Psychology" in r.data
        assert b"Nursing" in r.data
        assert b"EEB 313" in r.data

    def test_dana_view(self, dana_client):
        r = dana_client.get("/myumich")
        assert r.status_code == 200
        assert b"SI 110" in r.data
        assert b"English" in r.data
