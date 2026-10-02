"""Contract tests: every route renders, filters are deterministic, the seed
matches the captured upstream facts, and every DB-referenced image is a real
downloaded upstream asset."""
import json
import re
from pathlib import Path

import pytest

from app import (Award, DateItem, Event, NewsPost, Organizer, Paper,
                 Registration, ScheduleSave, SessionEvent, Sponsor, User,
                 Bookmark, db)

SITE = Path(__file__).resolve().parents[1]


def count_label(html, pattern):
    m = re.search(pattern, html)
    return m.group(1) if m else None


class TestPagesRender:
    def test_home(self, client):
        r = client.get("/")
        assert r.status_code == 200
        assert b"Rio de Janeiro" in r.data and b"accepted papers" in r.data
        assert b"5691" in r.data

    def test_papers_grid(self, client):
        r = client.get("/papers")
        assert r.status_code == 200

    def test_paper_detail(self, client):
        r = client.get("/papers/10006831")
        assert r.status_code == 200
        assert b"Escaping Policy Contraction" in r.data
        assert b"Dun Yuan" in r.data and b"McGill University" in r.data
        assert b"P4-#4602" in r.data

    def test_paper_detail_404(self, client):
        assert client.get("/papers/99999999").status_code == 404

    def test_paper_detail_without_session_renders(self, client):
        """(audit fix) Accepted papers with no session assignment (58 in the
        frozen seed, e.g. MADFormer 10011069) are linked from the papers
        browser; their detail page must render instead of 500-ing on the
        missing day/session window row."""
        r = client.get("/papers/10011069")
        assert r.status_code == 200
        assert b"MADFormer" in r.data
        assert b"Session window" not in r.data
        assert b"Accept (Poster)" in r.data
        # papers with a session keep their session window row
        r2 = client.get("/papers/10006553")
        assert r2.status_code == 200
        assert b"Session window" in r2.data

    def test_all_no_session_papers_render(self, client):
        """(audit fix) Every paper linked from the papers browser must render
        its detail page: all 58 no-session papers in the frozen seed (all
        eventtype Poster; two carry Accept (Oral) decisions via the upstream
        double-row quirk) previously 500-ed on the missing day."""
        from app import Paper
        papers = Paper.query.filter(Paper.session.is_(None)).all()
        assert len(papers) == 58
        for p in papers:
            r = client.get(f"/papers/{p.id}")
            assert r.status_code == 200, p.id
            assert b"Session window" not in r.data

    def test_schedule_all_days(self, client):
        for date in ("2026-04-22", "2026-04-23", "2026-04-24",
                     "2026-04-25", "2026-04-26", "2026-04-27"):
            r = client.get(f"/schedule?date={date}")
            assert r.status_code == 200, date

    def test_schedule_default_day(self, client):
        r = client.get("/schedule")
        assert b"WED 22 APR" in r.data

    def test_event_detail_workshop(self, client):
        r = client.get("/events/10000772")
        assert r.status_code == 200
        assert b"I Can&#39;t Believe It&#39;s Not Better" in r.data or \
            b"I Can't Believe It's Not Better" in r.data
        assert b"Arno Blaas" in r.data
        assert b"Opening Remarks - Welcome &amp; Introduction to ICBINB" in r.data

    def test_event_detail_invited_talk(self, client):
        r = client.get("/events/10020588")
        assert r.status_code == 200
        assert b"Maja Matari" in r.data
        assert b"Overflow Room: 201 A/B" in r.data
        assert b"University of Southern California" in r.data

    def test_event_detail_404(self, client):
        assert client.get("/events/99999999").status_code == 404

    def test_workshops_hub(self, client):
        r = client.get("/workshops")
        assert r.status_code == 200
        assert r.data.count(b'sched-event sched-workshop') == 40

    def test_invited_talks_hub(self, client):
        r = client.get("/invited-talks")
        assert r.status_code == 200
        assert r.data.count(b'sched-invited-talk') == 7

    def test_sponsors(self, client):
        r = client.get("/sponsors")
        assert r.status_code == 200
        assert b"Double Diamond" in r.data and b"Amazon" in r.data

    def test_organizers(self, client):
        r = client.get("/organizers")
        assert r.status_code == 200
        assert b"General Chair" in r.data and b"Carl Vondrick" in r.data

    def test_awards(self, client):
        r = client.get("/awards")
        assert r.status_code == 200
        assert b"Transformers are Inherently Succinct" in r.data
        assert b"Unsupervised Representation Learning with Deep Convolutional" in r.data

    def test_news(self, client):
        r = client.get("/news")
        assert r.status_code == 200
        assert b"Announcing the ICLR 2026 Outstanding Papers" in r.data

    def test_news_detail(self, client):
        r = client.get("/news/awards")
        assert r.status_code == 200
        assert b"Philippe Laban" in r.data

    def test_dates(self, client):
        r = client.get("/dates")
        assert r.status_code == 200
        assert b"Sep 18 &#39;26" in r.data or b"Sep 18 '26" in r.data

    def test_venue(self, client):
        r = client.get("/venue")
        assert r.status_code == 200
        assert b"Riocentro" in r.data and b"USD $100" in r.data

    def test_about(self, client):
        r = client.get("/about")
        assert r.status_code == 200
        assert b"representation learning" in r.data

    def test_faq(self, client):
        r = client.get("/faq")
        assert r.status_code == 200
        assert b"Badge Replacement Policy" in r.data

    def test_search(self, client):
        r = client.get("/search?q=Marin")
        assert r.status_code == 200
        assert b"Marin: Open Development of Frontier AI" in r.data

    def test_search_venue_section(self, client):
        """The site-wide search also covers the Conference Site page text
        (r2 fix F-2): Riocentro and the venue notes must be searchable."""
        r = client.get("/search?q=Riocentro")
        assert r.status_code == 200
        assert b">Conference site" in r.data
        assert b'<a href="/venue">Riocentro</a>' in r.data
        # no other content section claims a Riocentro hit
        assert b"No papers match" in r.data
        assert b"No events match" in r.data
        assert b"No sponsors match" in r.data
        assert b"No announcements match" in r.data

    def test_search_venue_luggage_note(self, client):
        r = client.get("/search?q=luggage")
        assert r.status_code == 200
        assert b">Conference site" in r.data
        assert b"Luggage Check" in r.data

    def test_search_venue_no_false_hits(self, client):
        """Queries absent from the venue text must not fabricate hits."""
        r = client.get("/search?q=Susquehanna")
        assert b"No conference-site notes match" in r.data
        r = client.get("/search?q=zzqqxx")
        assert b"No conference-site notes match" in r.data
        assert b"No papers match" in r.data

    def test_register_get(self, client):
        r = client.get("/register")
        assert r.status_code == 200
        assert b"$50" in r.data and b"Full time student" in r.data

    def test_helpdesk_get(self, client):
        r = client.get("/helpdesk")
        assert r.status_code == 200
        assert b"Visa Support" in r.data

    def test_404_page(self, client):
        r = client.get("/no-such-page")
        assert r.status_code == 404
        assert b"does not exist" in r.data


class TestSeedFacts:
    """The seed must match the captured upstream facts exactly."""

    def test_paper_counts(self, app_context):
        assert Paper.query.count() == 5691
        assert (Paper.query.filter_by(decision="Accept (Oral)").count()
                == 447)
        assert (Paper.query.filter_by(decision="Accept (Poster)").count()
                == 5244)

    def test_oral_talk_slot_conversion(self, app_context):
        # the upstream JSON labels the instant -07:00; Rio local is +4h
        p = db.session.get(Paper, 10007744)
        assert p.title == "Latent Speech-Text Transformer"
        assert p.talk_start == "11:42" and p.talk_end == "11:52"

    def test_poster_session_window(self, app_context):
        p = db.session.get(Paper, 10006831)
        assert p.session == "Poster Session 4 Pavilion 4"
        assert p.session_start == "15:15" and p.session_end == "17:45"
        assert p.poster_position == "P4-#4602"

    def test_event_counts(self, app_context):
        assert Event.query.count() == 112
        assert Event.query.filter_by(kind="workshop").count() == 40
        assert Event.query.filter_by(kind="invited-talk").count() == 7
        assert Event.query.filter_by(kind="social").count() == 21

    def test_session_events(self, app_context):
        assert SessionEvent.query.count() == 47
        oral = SessionEvent.query.filter_by(kind="oral-session").count()
        poster = SessionEvent.query.filter_by(kind="poster-session").count()
        assert oral + poster == 47

    def test_sponsors(self, app_context):
        assert Sponsor.query.count() == 60
        dd = Sponsor.query.filter_by(tier="Double Diamond").all()
        assert [s.name for s in dd] == ["Amazon", "Tencent"]

    def test_organizers(self, app_context):
        assert Organizer.query.count() == 29
        assert Organizer.query.filter_by(role="General Chair").count() == 1
        assert Organizer.query.filter_by(role="Program Chair").count() == 4

    def test_awards(self, app_context):
        assert Award.query.count() == 5
        outstanding = Award.query.filter_by(kind="Outstanding Paper").count()
        assert outstanding == 2
        assert Award.query.filter_by(kind="Honorable Mention").count() == 1
        assert Award.query.filter_by(kind="Test of Time").count() == 2

    def test_news(self, app_context):
        assert NewsPost.query.count() == 8
        latest = (NewsPost.query.order_by(NewsPost.date.desc()).first())
        assert latest.slug == "iclr-2027-submission-policies"

    def test_dates(self, app_context):
        assert DateItem.query.count() == 35
        d27 = DateItem.query.filter_by(year="2027").all()
        names = {d.name for d in d27}
        assert "Abstract Deadline" in names
        assert "Paper Deadline" in names

    def test_benchmark_users(self, app_context):
        users = User.query.order_by(User.id).all()
        assert [u.email for u in users] == [
            "alice.j@test.com", "bob.c@test.com", "carol.d@test.com",
            "dana.k@test.com"]
        assert all(u.name for u in users)

    def test_fixture_rows_are_real(self, app_context):
        """Every bookmark / save / registration references a real captured
        upstream row (the disney r1 lesson: fixtures must resolve)."""
        for b in Bookmark.query.all():
            assert db.session.get(Paper, b.paper_id) is not None
        for s in ScheduleSave.query.all():
            assert db.session.get(Event, s.event_id) is not None
        reg = Registration.query.first()
        assert reg is not None
        assert json.loads(reg.items) == ["Conference Sessions and Workshops"]
        assert reg.total_usd == 50
        assert reg.banquet_tickets == 1


class TestFilters:
    def test_title_search(self, client):
        r = client.get("/papers?q=diffusion")
        assert r.status_code == 200
        total = int(count_label(r.data.decode(),
                               r"(\d+) papers match the current filters"))
        expected = Paper.query.filter(
            Paper.title.ilike("%diffusion%")).count()
        assert total == expected

    def test_topic_filter(self, client):
        topic = "Reinforcement Learning->Deep RL"
        r = client.get("/papers",
                       query_string={"topic": topic})
        total = int(count_label(r.data.decode(),
                                r"(\d+) papers match the current filters"))
        assert total == Paper.query.filter_by(topic=topic).count()

    def test_decision_filter(self, client):
        r = client.get("/papers", query_string={"decision": "Accept (Oral)"})
        total = int(count_label(r.data.decode(),
                                r"(\d+) papers match the current filters"))
        assert total == 447

    def test_combined_filters(self, client):
        topic = "Applications->Language, Speech and Dialog"
        r = client.get("/papers", query_string={"q": "language",
                                                "topic": topic})
        total = int(count_label(r.data.decode(),
                                r"(\d+) papers match the current filters"))
        expected = Paper.query.filter(
            Paper.topic == topic,
            Paper.title.ilike("%language%")).count()
        assert total == expected

    def test_pagination(self, client):
        r1 = client.get("/papers?page=1")
        r2 = client.get("/papers?page=2")
        ids1 = set(re.findall(rb'href="/papers/(\d+)"', r1.data))
        ids2 = set(re.findall(rb'href="/papers/(\d+)"', r2.data))
        assert len(ids1) == 50 and len(ids2) == 50
        assert not (ids1 & ids2)

    def test_sort_by_id(self, client):
        r = client.get("/papers?sort=id")
        ids = [int(x) for x in re.findall(rb'href="/papers/(\d+)"', r.data)]
        assert ids == sorted(ids)


class TestImages:
    def test_every_rendered_image_exists(self, client):
        """No broken images: every /static/ reference on key pages exists."""
        from pathlib import Path
        pages = ["/", "/papers", "/papers/10006831", "/schedule",
                 "/events/10020588", "/workshops", "/invited-talks",
                 "/sponsors", "/organizers", "/awards", "/news",
                 "/news/keynotes", "/venue", "/about", "/faq", "/register",
                 "/helpdesk", "/login", "/signup"]
        for page in pages:
            r = client.get(page)
            assert r.status_code == 200
            for src in re.findall(rb'(?:src|href)="(/static/[^"]+)"',
                                  r.data):
                rel = src.decode().replace("/static/", "", 1)
                assert (SITE / "static" / rel).exists(), (page, src)

    def test_inventory_covers_tree(self):
        inventory = json.loads((SITE / "asset_inventory.json").read_text())
        files = {str(p.relative_to(SITE))
                 for p in (SITE / "static" / "images").rglob("*")
                 if p.is_file()}
        listed = {row["path"] for row in inventory["assets"]}
        assert files == listed
        assert inventory["asset_count"] == len(listed)

    def test_headshots_are_real_assets(self, app_context):
        """Speakers the upstream photographs render a downloaded file;
        speakers without an upstream photo (Bouman, the rescheduled
        placeholder) render initials, never a placeholder image."""
        bouman = Event.query.filter(Event.title ==
                                    "Images of the Hidden Universe").one()
        assert bouman.headshot_url is None
        maja = db.session.get(Event, 10020588)
        assert maja.headshot_url == "maja_mataric.jpg"
        assert (SITE / "static" / "images" / "speakers" /
                maja.headshot_url).exists()
