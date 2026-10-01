"""Robustness checks for the student_com mirror: every key route renders
non-empty content, auth works, forms validate and persist, search handles
partial queries, sort/filter math is exact, and bad input fails gracefully.

All tests run against the conftest scratch database (a copy of
instance_seed/student_com.db), never the live worktree instance.
"""
import html
import pathlib
import re

from conftest import csrf_token, login

SITE = pathlib.Path(__file__).resolve().parent.parent


def text_of(response):
    return html.unescape(response.get_data(as_text=True))


def get(client, path, min_len=500):
    response = client.get(path)
    assert response.status_code == 200, f"{path} -> {response.status_code}"
    body = response.get_data(as_text=True)
    assert len(body) > min_len, f"{path} rendered suspiciously little content"
    return body


# ---------------- health ----------------

def test_health_endpoint(client):
    data = client.get("/_health").get_json()
    assert data["ok"] is True
    assert data["counts"]["properties"] == 414
    assert data["counts"]["universities"] == 269
    assert data["counts"]["cities"] >= 15
    assert data["counts"]["users"] >= 4
    assert data["counts"]["jobs"] >= 100


# ---------------- core pages ----------------

def test_homepage_renders(client):
    body = get(client, "/", 20000)
    assert "student.com" in body
    assert "Search Texas Now" in body
    assert "Popular Cities" in body
    assert "Popular Colleges" in body


def test_state_finder_all_four_states(client):
    for state, name in [("tx", "Texas"), ("fl", "Florida"), ("ga", "Georgia"), ("oh", "Ohio")]:
        body = get(client, f"/us/{state}/u", 8000)
        assert f"Popular Colleges in {name}" in body
        assert "colleges" in body


def test_state_finder_search(client):
    body = get(client, "/us/tx/u?q=longhorn", 1000)
    assert "The University of Texas at Austin" in body


def test_city_page(client):
    body = get(client, "/us/tx/austin", 20000)
    assert "Student living in Austin" in body
    assert "Popular properties in Austin" in body
    assert "Curious about Austin" in body


def test_university_srp(client):
    body = get(client, "/us/tx/austin/u/the-university-of-texas-at-austin", 20000)
    assert "Homes near The University of Texas at Austin" in body
    assert "out of" in body and "results" in body
    assert "Sort by Distance" in body


def test_university_srp_sort_price(client):
    body = get(client, "/us/ga/atlanta/u/georgia-institute-of-technology?sort=price_asc", 8000)
    prices = [int(p.replace(",", "")) for p in re.findall(r"From \$([\d,]+)/mo", body)]
    assert prices == sorted(prices), f"price_asc not sorted: {prices}"


def test_university_srp_price_filter(client):
    body = get(client, "/us/tx/austin/u/the-university-of-texas-at-austin?min_price=1000&max_price=2000", 8000)
    prices = [int(p.replace(",", "")) for p in re.findall(r"From \$([\d,]+)/mo", body)]
    assert prices and all(1000 <= p <= 2000 for p in prices), prices


def test_university_srp_pagination_json(client):
    data = client.get("/us/tx/austin/u/the-university-of-texas-at-austin?offset=20&format=json").get_json()
    assert data["count"] > 20
    assert len(data["properties"]) <= 20
    assert all("url" in p and "min_price" in p for p in data["properties"])


def test_property_page(client):
    body = get(client, "/us/tx/austin/p/moontower-69d81c", 15000)
    assert "Moontower" in body
    assert "From $" in body and "/month" in body
    assert "AI Property Summary" in body
    assert "Email property" in body
    assert "Reviews" in body


def test_all_property_pages_render(client):
    """Traversal gate: every one of the 414 property detail pages must render.

    Upstream room_details comes in two shapes — dicts with ensuite/kitchen
    details, or plain per-room-type prices (int/float; a few carry a
    placeholder string). The old template assumed dicts and crashed with
    HTTP 500 on the 18 price-shaped records (all city_slug=miami, including
    The Retreat at Tampa), which the route-level tests never caught because
    they only opened one hand-picked property page.
    """
    import sqlite3

    seed = SITE / "instance_seed" / "student_com.db"
    db = sqlite3.connect(f"file:{seed}?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    rows = db.execute(
        "SELECT state_slug, city_slug, slug, name FROM properties").fetchall()
    db.close()
    assert len(rows) == 414, f"expected 414 properties, found {len(rows)}"
    for row in rows:
        path = f"/us/{row['state_slug']}/{row['city_slug']}/p/{row['slug']}"
        response = client.get(path)
        assert response.status_code == 200, f"{path} -> {response.status_code}"
        body = html.unescape(response.get_data(as_text=True))
        assert row["name"] in body, f"{path} missing its own name"
        assert "Rooms available" in body or "About this property" in body, path
        assert "Contact" in body, path


def test_property_room_details_scalar_fallback(client):
    """The 18 price-shaped room_details records render a per-room price line.

    The Retreat at Tampa (upstream {"4 Bed": 850, ...}) must show each room
    type with its own price; float-valued prices render too; and the string
    placeholder record renders the room names without a price line instead
    of crashing.
    """
    body = get(client, "/us/fl/miami/p/the-retreat-at-tampa", 15000)
    assert "The Retreat at Tampa" in body
    assert "4 Bed" in body and "1 Bed" in body
    assert "from $850/mo" in body and "from $900/mo" in body
    rooms = body.split("Rooms available", 1)[1].split("Reviews", 1)[0]
    assert "Ensuite" not in rooms and "Shared bathroom" not in rooms
    # float-valued room price renders without crashing, string placeholder
    # record renders the room names with no price line instead of crashing
    body = get(client, "/us/fl/miami/p/university-of-south-florida-housing-residential-education", 1000)
    assert "from $812/mo" in body
    body = get(client, "/us/fl/miami/p/celine-gardens", 1000)
    assert "Celine Gardens" in body
    assert "Studio" in body and "1 Bed" in body


def test_property_contact_email_rendered(client):
    """The contact email stored per property is rendered in the Contact card
    (upstream pages carry it; it was previously stored but never shown)."""
    body = get(client, "/us/ga/atlanta/p/catalyst-s7m7fb", 15000)
    assert "catalystmidtown@crm-living.com" in body
    assert 'href="mailto:catalystmidtown@crm-living.com"' in body
    body = get(client, "/us/fl/miami/p/the-retreat-at-tampa", 15000)
    assert "info@RetreatAtUSF.com" in body


def test_srp_map_pin_price_format(client):
    """Map pin labels use the compact $/k form for four-figure prices
    ($1,539 -> \"$1.5k\") instead of the truncating \"$1\"."""
    body = get(client, "/us/tx/college-station/u/texas-am-university", 8000)
    assert ">$1.5k<" in body, "100 Park ($1,539) pin should read $1.5k"
    assert ">$1.1k<" in body, "Rise at Northgate ($1,085) pin should read $1.1k"
    assert "Price: $1,539" in body, "pin title/aria-label should carry the full price"
    body = get(client, "/us/fl/tampa/u/university-of-south-florida", 8000)
    assert ">$940<" in body, "sub-$1000 pins keep the plain dollar form"


def test_srp_map_toggle_css_rule():
    """The map/list view toggle relies on a .hidden rule in the stylesheet;
    without it the map stays visible and the toggle is cosmetic only."""
    css = (SITE / "static" / "css" / "site.css").read_text(encoding="utf-8")
    assert re.search(r"^\.hidden\s*\{[^}]*display:\s*none", css, re.MULTILINE), \
        "site.css must define .hidden { display: none; }"


def test_property_404_for_wrong_city(client):
    assert client.get("/us/tx/houston/p/moontower-69d81c").status_code == 404


def test_legacy_city_redirect(client):
    response = client.get("/us/austin")
    assert response.status_code == 308
    assert response.headers["Location"].endswith("/us/tx/austin")


def test_404_page(client):
    response = client.get("/us/zz/nowhere")
    assert response.status_code == 404
    assert "404 - Not Found" in text_of(response)
    assert "Took a Study Break" in text_of(response)


# ---------------- search ----------------

def test_search_suggest_cities_unis_props(client):
    data = client.get("/search/suggest?q=aust").get_json()
    types = {r["type"] for r in data["results"]}
    assert "city" in types
    data = client.get("/search/suggest?q=georgia tech").get_json()
    assert any(r["type"] == "university" for r in data["results"])
    data = client.get("/search/suggest?q=moontower").get_json()
    assert any(r["type"] == "property" for r in data["results"])


def test_search_results_page(client):
    body = get(client, "/search?q=houston", 3000)
    assert "Houston" in body


# ---------------- auth ----------------

def test_login_logout(client):
    login(client)
    body = get(client, "/us/tx/austin/p/moontower-69d81c", 5000)
    assert "Hi, Alice" in body
    response = client.post("/auth/logout", headers={"X-CSRFToken": csrf_token(client)})
    assert response.get_json()["ok"] is True


def test_login_bad_password(client):
    response = client.post("/auth/login", data={"email": "alice.j@test.com", "password": "wrong"},
                           headers={"X-CSRFToken": csrf_token(client)})
    assert response.status_code == 401


def test_register_validation(client):
    token = csrf_token(client)
    response = client.post("/auth/register", data={"email": "not-an-email", "password": "x"},
                            headers={"X-CSRFToken": token})
    assert response.status_code == 400
    response = client.post("/auth/register", data={"email": "new.student@test.com", "password": "TestPass123!",
                                                    "first_name": "New", "last_name": "Student"},
                            headers={"X-CSRFToken": token})
    assert response.get_json()["ok"] is True


# ---------------- profile ----------------

def test_profile_requires_login(client):
    assert client.get("/profile/bookmarks").status_code == 200
    assert "Sign up or log in" in text_of(client.get("/profile/bookmarks"))


def test_bookmarks_flow(client):
    login(client)
    body = get(client, "/profile/bookmarks", 3000)
    assert "Moontower" in body  # alice has moontower saved
    # add a new one
    response = client.post("/property/linea-midtown-zb0foh/bookmark",
                           headers={"X-CSRFToken": csrf_token(client)})
    assert response.get_json()["bookmarked"] is True
    body = get(client, "/profile/bookmarks", 3000)
    assert "Linea Midtown" in body
    # remove it again
    response = client.post("/property/linea-midtown-zb0foh/bookmark",
                           headers={"X-CSRFToken": csrf_token(client)})
    assert response.get_json()["bookmarked"] is False


def test_recently_viewed(client):
    login(client)
    get(client, "/us/tx/austin/p/villas-on-rio-8639e0", 5000)
    body = get(client, "/profile/history", 2000)
    assert "Villas on Rio" in body


def test_inquiries_flow(client):
    login(client)
    body = get(client, "/profile/inquiries", 2000)
    assert "INQ-" in body  # alice has seeded inquiries
    # submit a new enquiry
    response = client.post("/property/moontower-69d81c/enquiry",
                           data={"first_name": "Alice", "last_name": "Johnson",
                                 "phone": "(512) 555-0142", "email": "alice.j@test.com",
                                 "message": "Is a studio available for fall?"},
                           headers={"X-CSRFToken": csrf_token(client)})
    assert response.status_code == 200
    reference = response.get_json()["reference"]
    assert reference.startswith("INQ-")
    body = get(client, "/profile/inquiries", 2000)
    assert "Is a studio available for fall?" in body


def test_enquiry_validation(client):
    login(client)
    response = client.post("/property/moontower-69d81c/enquiry",
                           data={"first_name": "", "last_name": "Johnson",
                                 "phone": "123", "email": "bad"},
                           headers={"X-CSRFToken": csrf_token(client)})
    assert response.status_code == 400
    errors = response.get_json()["errors"]
    assert "first_name" in errors and "phone" in errors and "email" in errors


# ---------------- jobs + calculator + content ----------------

def test_city_jobs_page(client):
    body = get(client, "/us/tx/austin/internships", 5000)
    assert "Land your dream Austin Internship" in body
    assert "View Job" in body


def test_jobs_type_filter(client):
    body = get(client, "/us/tx/austin/internships?type=part-time", 3000)
    assert "Part-Time" in body


def test_budget_calculator_page(client):
    body = get(client, "/budget-calculator", 8000)
    assert "Student budget calculator" in body
    assert "Comfortable rent target" in body
    assert "Financial Aid / Scholarships" in body


def test_content_pages(client):
    for path, marker in [
        ("/about", "world's leading marketplace"),
        ("/how-it-works", "How to book on Student.com"),
        ("/contact", "Connect with our team"),
        ("/help", "How can we help you today"),
        ("/guides/avoid-scams-and-fraud", "Red Flag"),
        ("/scholarships", "Scholarships"),
        ("/list-your-property", "List your property on Student.com"),
        ("/terms", "Terms, Conditions and Policies"),
        ("/terms/privacy", "Privacy Policy"),
    ]:
        body = get(client, path, 2000)
        assert marker in body, f"{path} missing {marker!r}"


def test_contact_form_persists(client):
    response = client.post("/contact", data={"name": "Carol", "email": "carol.d@test.com",
                                             "topic": "Booking with Student.com",
                                             "message": "A question."},
                            headers={"X-CSRFToken": csrf_token(client)})
    assert response.get_json()["ok"] is True
    response = client.post("/contact", data={"name": "", "email": "bad", "message": ""},
                            headers={"X-CSRFToken": csrf_token(client)})
    assert response.status_code == 400


# ---------------- data integrity ----------------

def test_images_are_real_files(client):
    for rel in ["properties/moontower-69d81c/01.jpg", "home/hero-banner-new.png"]:
        response = client.get(f"/static/images/{rel}")
        assert response.status_code == 200
        data = response.get_data()
        assert len(data) > 10_000, f"{rel} suspiciously small"
        assert data[:3] == b"\xff\xd8\xff" or data[:8] == b"\x89PNG\r\n\x1a\n" or data[:4] == b"RIFF"


def test_filtered_count_matches_browsable_catalogue(client):
    html = client.get('/us/fl/orlando/u/university-of-central-florida?max_price=800&type=Apartment').get_data(as_text=True)
    assert 'Showing 5 out of 5 results' in html
    assert 'out of 177' not in html


def test_job_dates_visible_for_tied_newest_openings(client):
    html = client.get('/us/tx/austin/internships?type=part-time').get_data(as_text=True)
    assert html.count('Posted 2026-08-18') == 2
    assert 'Operations Associate (Part-Time)' in html
    assert 'Sales Associate (Part-Time)' in html
