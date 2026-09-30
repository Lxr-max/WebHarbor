"""Self-checks for the super_lawyers mirror.

Run from sites/super_lawyers/: python3 -m pytest tests/ -q
"""
import json
import os
import pathlib
import re
import sqlite3
import sys
import tempfile

_SCRATCH = tempfile.TemporaryDirectory(prefix="sl-site-tests-")
os.environ["SUPER_LAWYERS_DB_PATH"] = "sqlite:///" + str(
    pathlib.Path(_SCRATCH.name) / "test.db")

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import app as sl_app  # noqa: E402
from app import (Answer, Court, Favorite, FeatureArticle, Firm, Inquiry,  # noqa: E402
                 Lawyer, ListingEntry, ListingMeta, PracticeArea, ResourceArticle,
                 ResourceTopic, SavedSearch, State, TopList, TopListEntry, User,
                 db)

app = sl_app.app
app.config["TESTING"] = True


def client():
    return app.test_client()


def test_health():
    with client() as c:
        r = c.get("/_health")
        assert r.status_code == 200
        data = r.get_json()
        assert data["ok"] is True
        assert data["counts"]["lawyers"] >= 1700
        assert data["counts"]["listings"] >= 890
        assert data["counts"]["top_lists"] >= 50
        assert data["counts"]["answers"] >= 30


def test_home_and_directory():
    with client() as c:
        for url in ["/", "/attorneys/", "/attorneys/washington/",
                    "/attorneys/personal-injury-plaintiff/",
                    "/attorneys/washington/seattle/",
                    "/attorneys/personal-injury-plaintiff/washington/seattle/"]:
            r = c.get(url)
            assert r.status_code == 200, url
        r = c.get("/attorneys/not-a-real-thing/")
        assert r.status_code == 404


def test_serp_cards_and_profiles():
    with client() as c:
        r = c.get("/attorneys/personal-injury-plaintiff/washington/seattle/")
        body = r.get_data(as_text=True)
        assert "Lara Herrmann" in body
        # every card lawyer has a resolvable profile page
        with app.app_context():
            entries = ListingEntry.query.filter_by(
                practice_slug="personal-injury-plaintiff",
                state_slug="washington", city_slug="seattle").all()
            assert len(entries) >= 25
            lawyer = Lawyer.query.filter_by(
                uuid=entries[0].lawyer_uuid).first()
        assert lawyer is not None
        r = c.get(f"/profiles/{lawyer.state_slug}/{lawyer.city_slug}/"
                  f"lawyer/{lawyer.slug}/{lawyer.uuid}.html")
        assert r.status_code == 200
        assert lawyer.name in r.get_data(as_text=True)


def test_top_lists():
    with client() as c:
        r = c.get("/top-lists/washington/top-10-2026-washington-super-lawyers/1/")
        assert r.status_code == 200
        body = r.get_data(as_text=True)
        assert "Sherri M. Anderson" in body
        with app.app_context():
            count = TopListEntry.query.filter(
                TopListEntry.list_id == TopList.query.filter_by(
                    slug="top-10-2026-washington-super-lawyers").first().id
            ).count()
        assert count == 10


def test_resources_and_answers():
    with client() as c:
        r = c.get("/resources/elder-law/what-is-elderly-financial-abuse/")
        assert r.status_code == 200
        r = c.get("/answers/search/?q=severance")
        assert r.status_code == 200
        assert "Severance" in r.get_data(as_text=True)
        with app.app_context():
            ans = Answer.query.filter(
                Answer.question.like("%severance%")).first()
        r = c.get(f"/answers/{ans.topic_slug}/{ans.state_slug}/"
                  f"{ans.slug}/{ans.uuid}.html")
        assert r.status_code == 200
        assert ans.answerer_name in r.get_data(as_text=True)


def test_scored_search_not_strict_and():
    with client() as c:
        # a recognized practice + city query redirects to the canonical SERP
        r = c.get("/attorneys/search/?q=personal+injury&where=seattle")
        assert r.status_code == 302
        assert "/attorneys/personal-injury-plaintiff/washington/seattle/" \
            in r.headers["Location"]
        # unrecognized multi-word queries fall back to scored lawyer search
        r = c.get("/attorneys/search/?q=trial+advocate+classmate")
        assert r.status_code == 200
        r = c.get("/answers/search/?q=elder+financial+abuse+florida")
        assert r.status_code == 200
        assert "elder" in r.get_data(as_text=True).lower()


def test_auth_flow_and_favorites():
    with client() as c:
        r = c.post("/login", data={"email": "alice.j@test.com",
                                   "password": "TestPass123!"},
                   follow_redirects=True)
        assert r.status_code == 200
        with app.app_context():
            user = User.query.filter_by(email="alice.j@test.com").first()
            n_favs = Favorite.query.filter_by(user_id=user.id).count()
        assert n_favs >= 4
        r = c.get("/account/favorites")
        assert r.status_code == 200


def test_contact_inquiry_persists():
    with client() as c:
        c.post("/login", data={"email": "alice.j@test.com",
                               "password": "TestPass123!"})
        with app.app_context():
            before = Inquiry.query.count()
            lawyer = Lawyer.query.filter_by(
                name="Lara Herrmann").first()
        r = c.post(f"/profiles/contact/lawyer/{lawyer.uuid}.html", data={
            "first_name": "Test", "last_name": "User",
            "email": "alice.j@test.com", "phone": "206-555-0100",
            "city": "Seattle", "state": "WA",
            "message": "pytest inquiry"},
            follow_redirects=True)
        assert r.status_code == 200
        with app.app_context():
            after = Inquiry.query.count()
        assert after == before + 1


def test_registration_validation():
    with client() as c:
        r = c.post("/register", data={
            "email": "not-an-email", "username": "x",
            "display_name": "X", "password": "short"})
        assert r.status_code == 400


def test_benchmark_users_seeded():
    with app.app_context():
        for email in ["alice.j@test.com", "bob.c@test.com",
                      "carol.d@test.com", "david.k@test.com"]:
            user = User.query.filter_by(email=email).first()
            assert user is not None, email
            assert user.check_password("TestPass123!")


def test_seed_idempotence_gate():
    """Re-running the seeders on the populated test DB must be a no-op."""
    with app.app_context():
        before = Lawyer.query.count()
    with app.app_context():
        import seed_data  # noqa: PLC0415
        seed_data.db = db
        seed_data.seed_database()
        seed_data.seed_benchmark_users()
        after = Lawyer.query.count()
    assert before == after


def test_court_dedup():
    """Each (state, city) has each court name at most once."""
    with app.app_context():
        rows = db.session.execute(db.text(
            "SELECT state_slug, city_slug, name, COUNT(*) c FROM courts "
            "GROUP BY state_slug, city_slug, name HAVING c > 1")).fetchall()
    assert rows == []


def test_lawyer_photo_paths_resolve():
    """Every stored photo path must exist under static/."""
    with app.app_context():
        paths = [r[0] for r in db.session.query(Lawyer.photo_path)]
        paths += [r[0] for r in db.session.query(Firm.map_path)]
        paths += [r[0] for r in db.session.query(Answer.answerer_photo_path)]
    root = pathlib.Path(sl_app.BASE_DIR) / "static"
    for rel in paths:
        if rel:
            assert (root / rel).is_file(), rel


def test_answerer_photos_present():
    with app.app_context():
        missing = Answer.query.filter(
            Answer.answerer_photo_path.is_(None)).count()
    assert missing == 0


def test_all_lawyer_profiles_render():
    """Every lawyer profile page in the directory must return 200 —
    including the 28 lawyers with no real headshot (upstream serves a
    circled-headshot placeholder icon in their photo slot, and so do we).
    Guards the photo() -> url_for(filename=None) BuildError crash found in
    review (28 pages 500, both Westchester Top 25 lists fully dead)."""
    with app.app_context():
        lawyers = Lawyer.query.all()
        photoless = [l for l in lawyers if not l.photo_path]
    assert len(lawyers) >= 1700
    assert len(photoless) == 28  # the known photo-less cohort must stay covered
    with client() as c:
        for lawyer in lawyers:
            r = c.get(f"/profiles/{lawyer.state_slug}/{lawyer.city_slug}/"
                      f"lawyer/{lawyer.slug}/{lawyer.uuid}.html")
            assert r.status_code == 200, (lawyer.uuid, lawyer.name)
        # the photo-less cohort renders the upstream placeholder headshot
        for lawyer in photoless:
            r = c.get(f"/profiles/{lawyer.state_slug}/{lawyer.city_slug}/"
                      f"lawyer/{lawyer.slug}/{lawyer.uuid}.html")
            body = r.get_data(as_text=True)
            assert lawyer.name in body
            assert "icon-headshot-circled.png" in body, lawyer.name


def test_westchester_top25_links_resolve():
    """The two Top 25 Westchester County list pages were 50 dead links in
    review: every card on them must now open a 200 profile page."""
    slugs = ["top-25-2024-westchester-county-super-lawyers",
             "top-25-2025-westchester-county-super-lawyers"]
    with client() as c:
        for slug in slugs:
            r = c.get(f"/top-lists/new-york/{slug}/1/")
            assert r.status_code == 200, slug
            body = r.get_data(as_text=True)
            hrefs = re.findall(r'href="(/profiles/[^" ]+)"', body)
            assert len(hrefs) == 25, (slug, len(hrefs))
            for href in hrefs:
                assert c.get(href).status_code == 200, (slug, href)


def test_article_featured_lawyers_resolve():
    """Every feature-article page must render, every featured-lawyer link
    on it must resolve (lawyers missing from the mirror render with photo +
    name + office city and no dead profile link), and the April Jones
    article must show the featured lawyer's photo and office city."""
    with app.app_context():
        articles = FeatureArticle.query.all()
    assert len(articles) >= 39
    with client() as c:
        for art in articles:
            r = c.get(f"/articles/{art.state_slug}/{art.slug}/")
            assert r.status_code == 200, (art.state_slug, art.slug)
            body = r.get_data(as_text=True)
            hrefs = re.findall(r'href="(/profiles/[^" ]+)"', body)
            for href in hrefs:
                assert c.get(href).status_code == 200, (art.slug, href)
        r = c.get("/articles/colorado/finding-the-after/")
        assert r.status_code == 200
        body = r.get_data(as_text=True)
        assert "April D. Jones" in body
        assert "Greenwood Village, CO" in body  # featured office city line
        assert re.search(r"images/lawyers/8919223c", body)  # her real photo


def test_asset_inventory_source_urls_clean():
    """No HTML-entity corruption in registered source URLs (review found all
    401 map source_urls had '&center=' mangled to '¢er=')."""
    manifest = json.loads((pathlib.Path(sl_app.BASE_DIR)
                           / "asset_inventory.json").read_text(encoding="utf-8"))
    assert manifest["asset_count"] == len(manifest["assets"])
    for row in manifest["assets"]:
        assert "¢" not in row["source_url"], row["path"]
        assert "&center=" in row["source_url"] if "/staticmap?" in \
            row["source_url"] else True, row["path"]
