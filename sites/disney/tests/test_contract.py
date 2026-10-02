"""Contract tests: every route renders, filters are deterministic, the seed
matches the captured upstream facts, and every DB-referenced image is a real
downloaded upstream asset."""
import json
import re
from pathlib import Path

import pytest

from app import db

SITE = Path(__file__).resolve().parents[1]


def count_label(html, noun):
    m = re.search(rf">(\d+) {noun}s?\b", html)
    return int(m.group(1)) if m else None


class TestPagesRender:
    def test_home(self, client):
        r = client.get("/")
        assert r.status_code == 200
        assert b"Movies" in r.data and b"Parks" in r.data

    def test_movies_grid(self, client):
        r = client.get("/movies")
        assert r.status_code == 200
        assert count_label(r.data.decode(), "movie") == 40

    def test_movie_detail(self, client):
        r = client.get("/movies/moana-2")
        assert r.status_code == 200
        assert b"PG" in r.data and b"1h 40min" in r.data

    def test_movie_detail_404(self, client):
        assert client.get("/movies/no-such-movie").status_code == 404

    def test_shows_grid(self, client):
        r = client.get("/shows")
        assert r.status_code == 200
        assert count_label(r.data.decode(), "show") == 54

    def test_show_detail(self, client):
        r = client.get("/shows/ducktales")
        assert r.status_code == 200
        assert b"TV-Y7" in r.data

    def test_games(self, client):
        r = client.get("/games")
        assert r.status_code == 200
        assert count_label(r.data.decode(), "game") == 4

    def test_parks_hub(self, client):
        r = client.get("/parks")
        assert r.status_code == 200
        assert b"EPCOT" in r.data

    def test_attractions_list(self, client):
        r = client.get("/parks/attractions")
        assert r.status_code == 200
        assert count_label(r.data.decode(), "result") == 267

    def test_attraction_detail(self, client):
        r = client.get(
            "/parks/attractions/magic-kingdom/seven-dwarfs-mine-train")
        assert r.status_code == 200
        assert b'38"' in r.data

    def test_shop_pages(self, client):
        for path in ("/shop", "/shop/toys", "/shop/clothing",
                     "/shop/accessories", "/shop/sale"):
            r = client.get(path)
            assert r.status_code == 200, path

    def test_product_detail(self, client):
        r = client.get("/shop/products/416120537041")
        assert r.status_code == 200
        assert b"Blaze Doll Set" in r.data

    def test_live_shows(self, client):
        r = client.get("/live-shows")
        assert r.status_code == 200
        assert b"Lion King" in r.data

    def test_doi_schedule(self, client):
        r = client.get("/live-shows/disney-on-ice")
        assert r.status_code == 200
        assert count_label(r.data.decode(), "event") == 89

    def test_doi_event(self, client):
        r = client.get("/live-shows/disney-on-ice/120960")
        assert r.status_code == 200
        assert b"Kent, WA" in r.data

    def test_search(self, client):
        r = client.get("/search?q=moana")
        assert r.status_code == 200
        assert b"Moana 2" in r.data

    def test_auth_pages(self, client):
        assert client.get("/login").status_code == 200
        assert client.get("/signup").status_code == 200

    def test_health_probe(self):
        from _health import health
        result = health()
        assert result["ok"] is True


class TestFilters:
    def test_movie_status_taxonomy(self, client):
        for status, expected in (("streaming", 6), ("coming_soon", 9),
                                 ("now_playing", 1)):
            r = client.get(f"/movies?status={status}")
            assert count_label(r.data.decode(), "movie") == expected, status

    def test_movie_genre_filter(self, client):
        r = client.get("/movies?genre=Animation")
        assert count_label(r.data.decode(), "movie") == 16

    def test_movie_search(self, client):
        r = client.get("/movies?q=star")
        assert count_label(r.data.decode(), "movie") == 2

    def test_movie_release_sort_newest_first(self, client):
        r = client.get("/movies?sort=release")
        slugs = re.findall(r'href="/movies/([a-z0-9-]+)"', r.data.decode())
        assert slugs[0] == "incredibles-3"

    def test_show_genre_filters(self, client):
        for genre, expected in (("Animation", 25), ("Comedy", 25),
                                ("Science Fiction", 10), ("Fantasy", 9),
                                ("Variety", 3)):
            r = client.get(f"/shows?genre={genre.replace(' ', '+')}")
            assert count_label(r.data.decode(), "show") == expected, genre

    def test_park_facets(self, client):
        for park, expected in (("magic-kingdom", 62), ("epcot", 72),
                               ("hollywood-studios", 40),
                               ("animal-kingdom", 59)):
            r = client.get(f"/parks/attractions?park={park}")
            assert count_label(r.data.decode(), "result") == expected, park

    def test_park_type_interest_height(self, client):
        r = client.get("/parks/attractions?park=magic-kingdom&"
                       "interest=Thrill+Rides&height=40")
        assert count_label(r.data.decode(), "result") >= 2

    def test_shop_collection_filters(self, client):
        r = client.get("/shop/toys?category=Action+Figures")
        assert count_label(r.data.decode(), "product") == 15
        r = client.get("/shop/clothing?target_age=Adults")
        assert count_label(r.data.decode(), "product") == 25

    def test_doi_show_and_city(self, client):
        r = client.get("/live-shows/disney-on-ice?show=Jump+In%21")
        assert count_label(r.data.decode(), "event") == 16
        r = client.get("/live-shows/disney-on-ice?q=Kent")
        assert count_label(r.data.decode(), "event") == 1

    def test_doi_search_matches_whole_words(self, client):
        # 'CA' must match California stops, not 'Medical' inside venue names
        r = client.get("/live-shows/disney-on-ice?q=CA")
        assert count_label(r.data.decode(), "event") == 8

    def test_empty_filter_results(self, client):
        r = client.get("/movies?q=zzzznope")
        assert b"No movies match" in r.data


class TestSeedContract:
    def test_benchmark_users(self, client):
        from app import User
        for email in ("alice.j@test.com", "bob.c@test.com",
                      "carol.d@test.com", "dana.k@test.com"):
            assert User.query.filter_by(email=email).first(), email

    def test_benchmark_password(self, client):
        from app import User, bcrypt
        alice = User.query.filter_by(email="alice.j@test.com").first()
        assert bcrypt.check_password_hash(alice.password_hash, "TestPass123!")

    def test_fixture_favorites(self, client):
        from app import Favorite
        assert Favorite.query.count() == 11

    def test_row_counts(self, client):
        from app import (IceEvent, LiveShow, Movie, ParkEntity, Product,
                        Show, HomeTile)
        assert Movie.query.count() == 40
        assert Show.query.count() == 54
        assert ParkEntity.query.count() == 267
        assert Product.query.count() == 150
        assert IceEvent.query.count() == 89
        assert LiveShow.query.count() == 4
        assert HomeTile.query.count() == 23

    def test_captured_facts(self, client):
        from app import Movie, ParkEntity, Product
        moana = Movie.query.filter_by(slug="moana-2").first()
        assert moana.rating == "PG"
        assert moana.runtime == "1h 40min"
        assert moana.release_date == "November 27, 2024"
        assert "Auli'i Cravalho" in (moana.cast or "")
        tron = ParkEntity.query.filter_by(
            key="magic-kingdom/tron-lightcycle-run").first()
        assert tron.height == 48
        blaze = Product.query.filter_by(pid="416120537041").first()
        assert blaze.price == 64.99
        assert blaze.reviews == 4

    def test_ice_event_performances(self, client):
        from app import IceEvent
        kent = IceEvent.query.filter_by(city="Kent, WA").first()
        perfs = kent.performance_list()
        assert perfs[0]["day"] == "Oct 22, 2026"
        assert "7:00 pm" in perfs[0]["times"]


class TestReviewRegressions:
    """Regressions for the r1 review difference list: home page must
    reference only real images, park display names must never be bare
    slugs, game titles must be free of upstream CMS artifacts, game
    descriptions must render as text, and the booking form must not
    auto-submit on the day dropdown."""

    def test_home_images_resolve(self, client):
        r = client.get("/")
        srcs = re.findall(r'src="(/static/[^"]+)"', r.data.decode())
        assert srcs, "home page renders no images"
        for src in srcs:
            assert client.get(src).status_code == 200, src

    def test_parks_hub_display_names(self, client):
        r = client.get("/parks")
        html = r.data.decode()
        for name in ("Disney&#39;s BoardWalk",
                     "Disney&#39;s Grand Floridian Resort &amp; Spa",
                     "Disney&#39;s Port Orleans Resort - Riverside"):
            assert name in html, name
        for slug in (">boardwalk<", ">grand-floridian-resort-and-spa<",
                     ">port-orleans-resort-riverside<"):
            assert slug not in html, slug

    def test_resort_entity_names_and_parks(self, client):
        """The three resort entertainment venues carry their real upstream
        names and park display names (r1 flagged the bare slugs; the chip
        text standing in for names was the same parse failure)."""
        from app import ParkEntity
        expected = {
            "boardwalk/atlantic-dance-hall":
                ("Atlantic Dance Hall", "Disney's BoardWalk"),
            "grand-floridian-resort-and-spa/grand-floridian-lobby-pianist":
                ("Grand Floridian Lobby Pianist",
                 "Disney's Grand Floridian Resort & Spa"),
            "port-orleans-resort-riverside/"
            "yehaa-bob-jackson-at-river-roost":
                ("Yehaa Bob Jackson at River Roost Lounge",
                 "Disney's Port Orleans Resort - Riverside"),
        }
        for key, (name, park) in expected.items():
            e = db.session.get(ParkEntity, key)
            assert e is not None, key
            assert e.name == name, (key, e.name)
            assert e.park == park, (key, e.park)
        r = client.get("/parks/attractions/boardwalk/atlantic-dance-hall")
        assert b"Atlantic Dance Hall" in r.data
        assert b"Disney&#39;s BoardWalk" in r.data

    def test_games_clean(self, client):
        r = client.get("/games")
        html = r.data.decode()
        assert "Hero banner" not in html
        assert "Featured Content Banner" not in html
        assert "Gargoyles Remastered" in html
        assert "Disney Illusion Island" in html

    def test_game_detail_real_copy(self, client):
        r = client.get("/games/disney-illusion-island")
        html = r.data.decode()
        assert "&lt;p&gt;" not in html, "literal HTML rendered"
        assert "AVAILABLE NOW" in html
        assert "Description" in html
        assert ("Join Mickey &amp; Friends on a quest to explore the "
                "mysterious island of Monoth") in html
        r = client.get("/games/disney-gargoyles-remastered")
        assert b"Story Overview" in r.data
        assert b"Key Features" in r.data

    def test_booking_page_no_autosubmit(self, client):
        r = client.get("/live-shows/disney-on-ice/120960/book")
        assert r.status_code == 200
        assert b"onchange" not in r.data


class TestAssetInventory:
    def test_inventory_covers_all_referenced_images(self, client):
        """Every image the DB references must be a real downloaded upstream
        asset listed in asset_inventory.json, and the file must exist."""
        from app import (Game, HomeTile, IceEvent, LiveShow, Movie,
                         ParkEntity, Product, Show)
        inventory = json.loads((SITE / "asset_inventory.json").read_text())
        by_name = {a["path"].split("/")[-1]: a for a in inventory["assets"]}
        referenced = set()
        for m in Movie.query.all():
            referenced.add(m.poster)
            referenced.update(g for g in (m.gallery or "").split("|") if g)
        for s in Show.query.all():
            referenced.add(s.thumb)
        for g in Game.query.all():
            referenced.add(g.image)
        for t in HomeTile.query.all():
            referenced.add(t.image)
        for e in ParkEntity.query.all():
            referenced.add(e.image)
            referenced.update(json.loads(e.images or "[]"))
        for p in Product.query.all():
            referenced.update(json.loads(p.images or "[]"))
        for ls in LiveShow.query.all():
            referenced.add(ls.image)
        referenced.discard(None)
        missing = [r for r in sorted(referenced) if r not in by_name]
        assert not missing, f"{len(missing)} DB images missing from inventory"
        on_disk_missing = [
            r for r in sorted(referenced)
            if not (SITE / "static" / "images" / "upstream" / r).exists()
        ]
        assert not on_disk_missing, on_disk_missing[:5]

    def test_inventory_hashes_valid(self):
        import hashlib
        inventory = json.loads((SITE / "asset_inventory.json").read_text())
        assert inventory["asset_count"] == len(inventory["assets"])
        for a in inventory["assets"][:25]:
            data = (SITE / a["path"]).read_bytes()
            assert len(data) == a["bytes"], a["path"]
            assert hashlib.sha256(data).hexdigest() == a["sha256"], a["path"]
            assert a["source_url"].startswith("http"), a["path"]
