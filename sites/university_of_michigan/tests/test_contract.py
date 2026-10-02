"""Contract tests: every route renders, filters are deterministic, and the
seed matches the captured upstream facts."""
import json
import re
from pathlib import Path

import pytest

import app as umich_app
from conftest import app_ctx
from app import (AcademicTerm, Building, CalendarEntry, Course, EventItem,
                 Instructor, LibraryItem, NewsArticle, Program, School,
                 Section, TuitionRow, db)

SITE = Path(__file__).resolve().parents[1]


class TestSeed:
    def test_row_counts(self):
        with app_ctx():
            assert School.query.count() == 21
            assert Program.query.count() == 156
            assert Course.query.count() > 400
            assert Section.query.count() > 2000
            assert Instructor.query.count() > 500
            assert LibraryItem.query.count() == 624
            assert NewsArticle.query.count() == 28
            assert EventItem.query.count() == 42
            assert Building.query.count() == 265
            assert CalendarEntry.query.count() > 60
            assert TuitionRow.query.count() == 4

    def test_benchmark_password(self, client):
        with app_ctx():
            data = {"email": "alice.j@test.com", "password": "TestPass123!"}
            from conftest import with_csrf
            r = client.post("/login", data=with_csrf(client, "/login", data))
            assert r.status_code in (302, 303)

    def test_schools_are_the_upstream_roster(self):
        with app_ctx():
            names = {s.short_name for s in School.query.all()}
            for expected in ("Architecture & Urban Planning", "Art & Design",
                             "Business", "Engineering", "Information", "Law",
                             "Literature, Science, and the Arts",
                             "Music, Theatre & Dance", "Nursing", "Pharmacy",
                             "Public Health", "Public Policy",
                             "Rackham School of Graduate Studies", "Social Work"):
                assert expected in names

    def test_majors_match_upstream(self):
        with app_ctx():
            names = {p.name for p in Program.query.all()}
            for expected in ("Actuarial Mathematics", "Aerospace Engineering",
                             "Biomedical Engineering", "Computer Science (BS)",
                             "Nursing", "Voice & Opera", "Women’s and Gender Studies"):
                assert expected in names

    def test_calendar_facts(self):
        with app_ctx():
            f26 = CalendarEntry.query.filter_by(
                term="Fall 2026", ctype="Academic Calendar").all()
            events = {e.event for e in f26}
            assert "Classes begin fall term" in events
            assert "Labor Day (holiday)" in events
            assert "Commencement" in events
            w26 = CalendarEntry.query.filter_by(
                term="Winter 2026", ctype="Academic Calendar").all()
            wevents = {e.event for e in w26}
            assert any("Martin Luther King" in e for e in wevents)
            reg = CalendarEntry.query.filter_by(
                term="Fall 2026", ctype="Registration Deadlines").all()
            assert any("Backpack opens" in e.event for e in reg)

    def test_tuition_facts(self):
        with app_ctx():
            row = TuitionRow.query.filter_by(
                residency="Michigan Residents (In-State)",
                level="Lower Division Tuition").first()
            assert row.tuition_fees == 18896
            assert row.total == 40194
            oos = TuitionRow.query.filter_by(
                residency="Nonresidents (Out-of-State)",
                level="Lower Division LSA").first()
            assert oos.tuition_fees == 67096
            assert oos.total == 88394

    def test_course_facts(self):
        with app_ctx():
            c = Course.query.filter_by(subject="CHEM", number="125").first()
            assert c is not None
            assert c.title == "Gen Chem Lab I"
            assert len(c.sections) > 50
            sec = Section.query.filter_by(class_nbr="32104").first()
            assert sec.course.subject == "AAS"
            assert sec.instructor == "Brian Klein"
            assert sec.topic == "Reconsider Afr Environments"
            assert sec.status == "Closed"

    def test_library_facts(self):
        with app_ctx():
            item = LibraryItem.query.filter(
                LibraryItem.title.ilike("%Climate Risk Management%")).first()
            assert item is not None
            assert "Bosn, Keely" in item.authors
            assert item.date_issued == "2020"

    def test_news_facts(self):
        with app_ctx():
            a = NewsArticle.query.filter_by(
                slug="arts-taking-center-stage-at-u-m-throughout-october").first()
            assert a is not None
            assert "arts-culture" in a.category_list()

    def test_event_facts(self):
        with app_ctx():
            e = EventItem.query.filter_by(name="T.REX").first()
            assert e is not None
            assert e.type == "Film Screening"
            assert e.location_name == "Museum of Natural History"

    def test_building_facts(self):
        with app_ctx():
            b = Building.query.filter_by(name="Michigan League").first()
            assert b is not None
            assert b.address == "911 N. UNIVERSITY AVE"
            assert b.category == "Student Life"


class TestPagesRender:
    def test_home(self, client):
        r = client.get("/")
        assert r.status_code == 200
        assert b"University of Michigan" in r.data
        assert b"schools and colleges" in r.data

    def test_all_top_routes(self, client):
        for p in ["/schools-colleges", "/programs", "/courses", "/faculty",
                  "/library", "/news", "/events", "/calendars", "/admissions",
                  "/admissions/costs", "/admissions/aid", "/admissions/apply",
                  "/admissions/request-info", "/map", "/login", "/signup",
                  "/search?q=michigan"]:
            r = client.get(p)
            assert r.status_code == 200, p

    def test_404(self, client):
        assert client.get("/no-such-page").status_code == 404

    def test_health(self, client):
        r = client.get("/_health")
        assert r.status_code == 200
        assert b"university_of_michigan" in r.data


class TestProgramBrowser:
    def test_search_and_school_filter(self, client):
        r = client.get("/programs?q=engineering")
        assert r.status_code == 200
        assert b"Engineering" in r.data
        r2 = client.get("/programs",
                        query_string={"school": "College of Engineering"})
        assert r2.status_code == 200
        assert b"Aerospace Engineering" in r2.data

    def test_letter_tabs(self, client):
        r = client.get("/programs?letter=a-f")
        assert r.status_code == 200
        assert b"Actuarial Mathematics" in r.data
        assert b"Women" not in r.data

    def test_program_detail(self, client):
        with app_ctx():
            p = Program.query.filter_by(name="Biology").first()
        r = client.get(f"/programs/{p.id}")
        assert r.status_code == 200
        assert b"Biology" in r.data


class TestCourseCatalog:
    def test_subject_browse(self, client):
        r = client.get("/courses/subject/CHEM")
        assert r.status_code == 200
        assert b"Gen Chem Lab I" in r.data

    def test_keyword_search(self, client):
        r = client.get("/courses?q=chemistry")
        assert r.status_code == 200
        assert b"CHEM" in r.data

    def test_class_detail(self, client):
        r = client.get("/courses/class/32104")
        assert r.status_code == 200
        assert b"Reconsider Afr Environments" in r.data
        assert b"Brian Klein" in r.data

    def test_unknown_subject_404(self, client):
        assert client.get("/courses/subject/ZZZZZ").status_code == 404


class TestFaculty:
    def test_directory(self, client):
        r = client.get("/faculty")
        assert r.status_code == 200

    def test_name_search(self, client):
        r = client.get("/faculty?q=Keane")
        assert r.status_code == 200
        assert b"Sarah Keane" in r.data

    def test_faculty_detail_sections(self, client):
        with app_ctx():
            person = Instructor.query.filter_by(name="Brian Klein").first()
        r = client.get(f"/faculty/{person.id}")
        assert r.status_code == 200
        assert b"32104" in r.data


class TestLibrary:
    def test_search(self, client):
        r = client.get("/library?q=climate")
        assert r.status_code == 200
        assert b"Climate" in r.data

    def test_type_filter(self, client):
        r = client.get("/library?type=Article")
        assert r.status_code == 200
        assert b"Article" in r.data

    def test_item_detail(self, client):
        with app_ctx():
            item = LibraryItem.query.first()
        r = client.get(f"/library/item/{item.uuid}")
        assert r.status_code == 200
        assert item.title.encode() in r.data


class TestNewsEvents:
    def test_news_category(self, client):
        r = client.get("/news?category=health")
        assert r.status_code == 200

    def test_article(self, client):
        r = client.get("/news/arts-taking-center-stage-at-u-m-throughout-october")
        assert r.status_code == 200
        assert b"Michigan Arts Festival" in r.data

    def test_events_type_filter(self, client):
        r = client.get("/events?type=Performance")
        assert r.status_code == 200
        assert b"Performance" in r.data

    def test_event_detail(self, client):
        with app_ctx():
            e = EventItem.query.filter_by(name="T.REX").first()
        r = client.get(f"/events/{e.eid}")
        assert r.status_code == 200
        assert b"Sam Neill" in r.data


class TestCalendars:
    def test_term_filter(self, client):
        r = client.get("/calendars?term=Fall+2026&type=Academic+Calendar")
        assert r.status_code == 200
        assert b"Classes begin fall term" in r.data

    def test_registration(self, client):
        r = client.get("/calendars?term=Fall+2026&type=Registration+Deadlines")
        assert r.status_code == 200
        assert b"Backpack opens" in r.data


class TestCampusMap:
    def test_building_search(self, client):
        r = client.get("/map?q=league")
        assert r.status_code == 200
        assert b"Michigan League" in r.data

    def test_category_filter(self, client):
        r = client.get("/map?category=Library%2FMuseum")
        assert r.status_code == 200
        assert b"Museum of Natural History" in r.data
        assert b"Hatcher Graduate Library" in r.data

    def test_building_detail(self, client):
        with app_ctx():
            b = Building.query.filter_by(name="Michigan League").first()
        r = client.get(f"/map/building/{b.slug}")
        assert r.status_code == 200
        assert b"911 N. UNIVERSITY AVE" in r.data


class TestImages:
    """Every DB-referenced image must exist on disk and be a real asset."""

    def test_school_images_exist(self):
        with app_ctx():
            import os
            for s in School.query.all():
                if s.image:
                    assert (SITE / s.image.lstrip("/")).exists(), s.image

    def test_news_images_exist(self):
        with app_ctx():
            import os
            for a in NewsArticle.query.all():
                if a.image:
                    assert (SITE / a.image.lstrip("/")).exists(), a.image

    def test_event_images_exist(self):
        with app_ctx():
            import os
            for e in EventItem.query.all():
                if e.image:
                    assert (SITE / e.image.lstrip("/")).exists(), e.image


class TestReviewFixes:
    """Regressions for the review NEEDS-FIX round (REPORT.md section 6)."""

    def test_financial_aid_fafsa_row_upstream_verbatim(self, client):
        # fix 3: the Oct. 1 row was truncated to 'Complete the'; upstream
        # carries the full sentence (live capture 2026-09-30).
        r = client.get("/admissions/aid")
        assert r.status_code == 200
        assert (b"Complete the Free Application for Federal Student Aid "
                b"(FAFSA), as soon as available") in r.data
        assert b"directed to the Office of Financial Aid." in r.data

    def test_costs_footnote_upstream_verbatim(self, client):
        # fix 10: the footnote 'corrected' the year to 2026-2027 and dropped
        # the trailing sentence; upstream says 2025-2026 with the full text.
        r = client.get("/admissions/costs")
        assert r.status_code == 200
        assert (b"based on approved rates for the 2025-2026 academic year. "
                b"Rates are approved each June by the U-M Board of Regents "
                b"and estimated budgets are updated at that time. Tuition and "
                b"fees may be higher or lower depending on a student's "
                b"program of study; these estimated budgets use information "
                b"from the College of Literature, Science, and the Arts. "
                b"Current tuition information is available through the "
                b"Office of the Registrar.") in r.data
        assert b"2026-2027 academic year" not in r.data

    def test_lsa_program_page_links_school(self, client):
        # fix 7: program_detail must resolve '(LSA)'/'(SMTD)' suffixed
        # program.school values to the real school page.
        with app_ctx():
            bcn = Program.query.filter_by(
                name="Biopsychology, Cognition, and Neuroscience").first()
            lsa = School.query.filter_by(slug="lsa").first()
        r = client.get(f"/programs/{bcn.id}")
        assert r.status_code == 200
        assert f'href="/schools-colleges/{lsa.slug}"'.encode() in r.data
        assert lsa.full_name.encode() in r.data
        # the 'All Programs From This Unit' table is populated (100 LSA rows)
        assert r.data.count(b'<td><a href="/programs/') >= 90

    def test_smtd_program_page_links_school(self, client):
        with app_ctx():
            smtd_prog = (Program.query.filter(Program.school.like('%(SMTD)%'))
                         .order_by(Program.name).first())
            smtd = School.query.filter_by(slug="smtd").first()
        r = client.get(f"/programs/{smtd_prog.id}")
        assert r.status_code == 200
        assert f'href="/schools-colleges/{smtd.slug}"'.encode() in r.data

    def test_nonsuffix_program_still_resolves_school(self, client):
        # the slug-first lookup must not regress plain full-name programs
        with app_ctx():
            nursing_prog = Program.query.filter_by(name="Nursing").first()
            nursing = School.query.filter_by(slug="nursing").first()
        r = client.get(f"/programs/{nursing_prog.id}")
        assert r.status_code == 200
        assert f'href="/schools-colleges/{nursing.slug}"'.encode() in r.data


class TestAuditFixes:
    """Regressions for the audit round (in-place render-layer fixes)."""

    def test_home_hero_image_exists_and_inventoried(self, client):
        # audit fix: the hero <img> referenced burton-tower-rainbow.jpg which
        # was never captured (404 on every homepage load); it now renders a
        # real upstream umich.edu gallery asset registered in the inventory.
        import json as _json
        r = client.get("/")
        assert r.status_code == 200
        assert b'src="/static/images/core/burton-tower-fall.jpg"' in r.data
        hero = SITE / "static/images/core/burton-tower-fall.jpg"
        assert hero.is_file() and hero.stat().st_size > 0
        inv = _json.loads((SITE / "asset_inventory.json").read_text())
        entry = [a for a in inv["assets"]
                 if a["path"] == "static/images/core/burton-tower-fall.jpg"]
        assert len(entry) == 1
        import hashlib
        digest = hashlib.sha256(hero.read_bytes()).hexdigest()
        assert entry[0]["sha256"] == digest
        assert entry[0]["bytes"] == hero.stat().st_size
        assert entry[0]["source_url"].startswith("https://umich.edu/")
        # the dead reference is gone
        assert b"burton-tower-rainbow.jpg" not in r.data

    def test_home_featured_story_links_resolve(self, client):
        # audit fix: featured-story links used the upstream slug verbatim,
        # producing /news/<upstream-slug> routes that 404 (mirror slugs are
        # truncated). Mirrored stories now link to the real article; stories
        # without a mirrored article keep their upstream (external) URL.
        r = client.get("/")
        assert r.status_code == 200
        data = r.data.decode()
        # the El Niño story resolves to the mirrored article slug
        assert 'href="/news/el-ninos-more-intense-over-last-40-years-than' in data
        assert "el-ninos-more-intense-over-last-40-years-than-previous-1000-according-to-u-m-study" \
            not in data
        # stories without a mirrored article keep the upstream link (external,
        # same honest shape as the school-website links)
        assert 'href="https://news.umich.edu/' in data
        # every internal story link resolves to a real article
        with app_ctx():
            from app import NewsArticle
            slugs = {a.slug for a in NewsArticle.query.all()}
        import re as _re
        for slug in _re.findall(r'href="/news/([^"]+)"', data):
            assert slug in slugs, slug

    def test_responsive_table_css_present(self, client):
        # audit fix: data tables overflowed phone viewports (up to +426px at
        # 320 on /admissions/costs); the stylesheet now scrolls them inside
        # the page below 860px.
        css = (SITE / "static/css/main.css").read_text()
        assert "table.list, table.plain { display: block; overflow-x: auto; }" in css
        assert "@media (max-width: 860px)" in css
