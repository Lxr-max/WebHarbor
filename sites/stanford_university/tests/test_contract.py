"""Contract tests: every route renders, filters work, seed counts hold,
and CSRF-protected state changes behave like the real site."""
import json
import re

from conftest import _login, _logout, with_csrf


def test_health(client):
    r = client.get("/_health")
    assert r.status_code == 200
    data = r.get_json()
    assert data["ok"] is True
    assert data["site"] == "stanford_university"
    counts = data["counts"]
    assert counts["departments"] == 150
    assert counts["courses"] > 5000
    assert counts["programs"] == 355
    assert counts["faculty"] > 1200
    assert counts["news"] == 210
    assert counts["events"] > 500
    assert counts["calendar"] == 185
    assert counts["libraries"] == 29  # 30 -> 29: philosophy duplicate deduped (review fix #3)
    assert counts["users"] == 4


def test_home(client):
    r = client.get("/")
    assert r.status_code == 200
    assert b"Advancing the Frontier" in r.data
    assert b"Stanford News" in r.data
    assert b"The Seven Schools" in r.data
    # the full upstream hero renders, third sentence included (review fix #8)
    assert b"Alive with ideas and" in r.data
    assert b"this is Stanford." in r.data


def test_departments_list_and_filter(client):
    r = client.get("/departments")
    assert r.status_code == 200
    assert b"Aeronautics and Astronautics" in r.data
    r = client.get("/departments?school=engineering")
    assert b"Computer Science" in r.data
    r = client.get("/departments?q=chemistry")
    assert b"Chemistry" in r.data
    r = client.get("/departments?school=law")
    assert b"Chemistry" not in r.data


def test_department_detail_chain(client):
    r = client.get("/departments/COMPUTSCI")
    assert r.status_code == 200
    assert b"Computer Science" in r.data
    assert b"Computer Science (BS)" in r.data
    assert b"CS106A" in r.data
    r = client.get("/departments/NOPE")
    assert r.status_code == 404


def test_programs_search_and_compare(client):
    r = client.get("/programs?q=Economics")
    assert r.status_code == 200
    assert b"Economics (BA)" in r.data
    r = client.get("/programs/CS-BS")
    assert b"93" in r.data
    r = client.get("/programs/CS-BS?compare=CS-MS")
    assert b"45" in r.data
    assert b"CS-MS" in r.data
    r = client.get("/programs/CS-BS?compare=NOPE")
    assert r.status_code == 200


def test_courses_search_filters(client):
    r = client.get("/courses?q=machine learning")
    assert r.status_code == 200
    assert b"CS229" in r.data or b"machine learning" in r.data.lower()
    r = client.get("/courses?subject=EE&career=Graduate&term=Winter")
    # career filter matches exactly: the first graduate EE winter course is
    # EE214B, and the undergraduate circuits courses stay out of the list
    assert b"EE214B" in r.data
    assert b"EE101A" not in r.data
    r = client.get("/courses?ways=Formal Reasoning (FR)")
    assert b"CS106A" in r.data or b"CS103" in r.data
    r = client.get("/courses?q=zzzznotfound")
    assert b"No courses match" in r.data


def test_career_filter_is_exact(client):
    # "Graduate" must not match "Undergraduate" (review fix #1):
    # the CS subject under the graduate career lists exactly the true
    # graduate courses, none of the undergraduate ones.
    r = client.get("/courses?subject=CS&career=Graduate")
    assert r.status_code == 200
    assert b"40 courses" in r.data
    assert b"CS202" in r.data  # first graduate CS course by code
    assert b"CS106A" not in r.data  # undergraduate course, must be filtered out
    r = client.get("/courses?subject=CS&career=Undergraduate")
    assert b"CS106A" in r.data
    assert b"CS202" not in r.data


def test_course_detail(client):
    r = client.get("/courses/CS106A")
    assert r.status_code == 200
    assert b"Programming Methodology" in r.data
    assert b"Formal Reasoning (FR)" in r.data
    assert b"CS106B" in r.data  # related rows
    r = client.get("/courses/CS229")
    assert b"ROP - Letter or Credit/No Credit" in r.data
    r = client.get("/courses/NOPE123")
    assert r.status_code == 404


def test_faculty_search_and_detail(client):
    r = client.get("/faculty?q=Fei-Fei Li")
    assert r.status_code == 200
    assert b"Fei-Fei Li" in r.data
    r = client.get("/faculty?dept=Mathematics")
    assert b"Mathematics" in r.data
    r = client.get("/faculty/15052")
    assert r.status_code == 200
    assert b"Sequoia Capital Professor" in r.data
    r = client.get("/faculty/999999999")
    assert r.status_code == 404


def test_faculty_search_covers_bio(client):
    # review fix #2: the directory search also matches profile bios, like
    # profiles.stanford.edu does — searching for the laboratory its director
    # leads finds him instead of dead-ending
    r = client.get("/faculty?q=Aerospace Design Laboratory")
    assert r.status_code == 200
    assert b"Juan Alonso" in r.data
    r = client.get("/faculty?q=zzzznotfound")
    assert b"No faculty match" in r.data


def test_news_listing_search_detail(client):
    r = client.get("/news")
    assert r.status_code == 200
    assert b"Stanford Report" in r.data
    r = client.get("/news?category=Research+%26+Scholarship&topic=Health+%26+Medicine")
    assert r.status_code == 200
    r = client.get("/news?q=MacArthur")
    assert b"MacArthur" in r.data
    r = client.get("/news/song-lin-macarthur-fellowship")
    assert b"Song Lin" in r.data
    assert b"Adam Hadhazy" in r.data
    assert b"$800,000" in r.data
    r = client.get("/news/no-such-story")
    assert r.status_code == 404


def test_events_filters_and_detail(client):
    r = client.get("/events")
    assert r.status_code == 200
    r = client.get("/events?month=2026-11")
    assert b"2026-11" in r.data
    r = client.get("/events?when=upcoming")
    assert r.status_code == 200
    r = client.get("/events?q=lecture")
    assert b"lecture" in r.data.lower()
    r = client.get("/events/53922734404263")
    assert r.status_code == 200
    assert b"Big Earth Hackathon" in r.data
    r = client.get("/events/1")
    assert r.status_code == 404


def test_academic_calendar(client):
    r = client.get("/academic-calendar")
    assert r.status_code == 200
    assert b"September 22 (Tue)" in r.data
    assert b"Preliminary Study List deadline" in r.data
    assert b"$200" in r.data
    r = client.get("/academic-calendar?quarter=winter")
    assert b"January 4 (Mon)" in r.data
    r = client.get("/academic-calendar?quarter=bogus")
    assert r.status_code == 200  # falls back to autumn


def test_libraries(client):
    r = client.get("/libraries")
    assert r.status_code == 200
    assert b"Cecil H. Green Library" in r.data
    r = client.get("/libraries?q=east")
    assert b"East Asia Library" in r.data
    r = client.get("/libraries/cecil-h-green-library")
    assert b"12p-12a" in r.data
    assert b"(650) 723-1493" in r.data
    r = client.get("/libraries/robin-li-and-melissa-ma-science-library")
    assert b"(650) 723-1528" in r.data
    r = client.get("/libraries/nope")
    assert r.status_code == 404


def test_library_philosophy_record_complete(client):
    # review fix #3: the Tanner philosophy library is one complete record
    # (deduped from the hours roster) with the location re-captured from the
    # live redirect target on philosophy.stanford.edu — no empty anchors
    r = client.get("/libraries?q=philosophy")
    assert r.status_code == 200
    assert b"Tanner Memorial Library of Philosophy" in r.data
    assert b"Philosophy Library (Tanner)" not in r.data  # duplicate record gone
    r = client.get("/libraries/tanner-philosophy-library")
    assert r.status_code == 200
    assert b"Location:" in r.data
    assert b"Building 90" in r.data
    assert b"Room 91F" in r.data
    assert b"9:30a-5p" in r.data  # weekly hours from the SUL hours roster


def test_admission_and_aid(client):
    r = client.get("/admission")
    assert r.status_code == 200
    assert b"November 1" in r.data
    assert b"January 5" in r.data
    assert b"February 15" in r.data
    r = client.get("/admission/aid")
    assert b"$150,000" in r.data
    assert b"$70,000" in r.data
    r = client.get("/admission/aid?income=120000&family=2")
    assert b"No tuition responsibility" in r.data
    r = client.get("/admission/aid?income=80000&family=3")
    assert b"No tuition or room and board responsibility" in r.data
    r = client.get("/admission/aid?income=abc")
    assert r.status_code == 200


def test_404_page(client):
    r = client.get("/no/such/page")
    assert r.status_code == 404
    assert b"Page not found" in r.data


def test_faculty_photo_url_maps_to_packed_assets():
    """Audit regression: the seed mirrors the upstream CDN photo filename,
    which is not on disk; photo_url must map to the packed per-profile asset
    (faculty_<profile_id>.jpg) and never reference a missing file."""
    import os

    import app as su_app
    from app import BASE_DIR, Faculty

    with su_app.app.test_request_context():
        packed = Faculty.query.filter(Faculty.profile_id == 15052).first()  # Fei-Fei Li
        assert packed is not None and packed.photo is not None
        assert packed.photo_url == "/static/images/upstream/faculty/faculty_15052.jpg"
        unpacked = Faculty.query.filter(Faculty.profile_id == 19258).first()  # no packed photo
        assert unpacked is not None and unpacked.photo_url is None
        # every rendered photo URL must resolve to an existing file on disk
        rendered = 0
        for f in Faculty.query.filter(Faculty.photo.isnot(None)).all():
            url = f.photo_url
            if url:
                assert os.path.exists(os.path.join(BASE_DIR, url.lstrip("/"))), url
                rendered += 1
        assert rendered > 0


def test_responsive_css_rules_present():
    """Audit regression: the narrow-viewport rules (scrollable data tables,
    wrapping filter selects, clamped card grids, URL wrapping) must stay."""
    css = open("static/css/site.css").read()
    assert "@media (max-width: 860px)" in css
    assert "table.data { display: block; overflow-x: auto; }" in css
    assert ".filters select { max-width: 100%; }" in css
    assert "minmax(min(340px, 100%), 1fr)" in css
    assert "overflow-wrap: anywhere" in css
