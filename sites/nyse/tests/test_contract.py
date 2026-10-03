"""Contract tests: every route renders, filters are deterministic, the seed
matches the captured upstream facts, and every DB-referenced image is a real
downloaded upstream asset."""
import json
import re
from pathlib import Path

import pytest

import app as nyse_app
from app import db

SITE = Path(__file__).resolve().parents[1]


def count_label(html, noun):
    m = re.search(rf"><strong>(\d+)</strong> {noun}s?\b", html)
    return int(m.group(1)) if m else None


class TestPagesRender:
    def test_home(self, client):
        r = client.get("/")
        assert r.status_code == 200
        assert b"market-defining IPOs" in r.data
        assert b"NU" in r.data and b"12.35" in r.data

    def test_market_update_article(self, client):
        r = client.get("/market-update")
        assert r.status_code == 200
        assert b"Michael P. Reinking" in r.data
        assert b"conflicting Iran related news" in r.data

    def test_listings_hub(self, client):
        r = client.get("/listings")
        assert r.status_code == 200
        assert b"Why list on the NYSE?" in r.data

    def test_markets(self, client):
        r = client.get("/markets")
        assert r.status_code == 200
        assert b"NU HOLDINGS LTD" in r.data
        assert b"STABLECOIN DEVELOPMENT CORPORATION" in r.data

    def test_history(self, client):
        r = client.get("/history-of-nyse")
        assert r.status_code == 200
        assert b"Buttonwood Agreement" in r.data
        assert b"1792" in r.data

    def test_bell_hub(self, client):
        r = client.get("/bell")
        assert r.status_code == 200

    def test_404(self, client):
        assert client.get("/no-such-page").status_code == 404


class TestDirectory:
    def test_stock_tab_count(self, client):
        r = client.get("/listings_directory/stock")
        assert r.status_code == 200
        assert count_label(r.data.decode(), "listing") == 6830

    def test_etf_tab_count(self, client):
        r = client.get("/listings_directory/etf")
        assert count_label(r.data.decode(), "listing") == 5765

    def test_index_tab_count(self, client):
        r = client.get("/listings_directory/index")
        assert count_label(r.data.decode(), "listing") == 1329

    def test_reit_tab_count(self, client):
        r = client.get("/listings_directory/reit")
        assert count_label(r.data.decode(), "listing") == 144

    def test_unknown_tab_404(self, client):
        assert client.get("/listings_directory/bonds").status_code == 404

    def test_search_filter(self, client):
        r = client.get("/listings_directory/stock?q=AGILENT")
        html = r.data.decode()
        assert count_label(html, "listing") == 1
        assert "AGILENT TECHNOLOGIES INC" in html

    def test_search_by_symbol_fragment(self, client):
        r = client.get("/listings_directory/stock?q=BABA")
        html = r.data.decode()
        assert "BABA" in html
        assert "ALIBABA" in html

    def test_sort_by_name_desc(self, client):
        r = client.get("/listings_directory/stock?sort=name&order=desc")
        html = r.data.decode()
        names = re.findall(r"<tr>\s*<td>.*?</td>\s*<td>([^<]+)</td>", html, re.S)
        assert len(names) >= 2
        assert names[0] >= names[1]  # descending by name

    def test_pagination_walks(self, client):
        r1 = client.get("/listings_directory/stock")
        r2 = client.get("/listings_directory/stock?page=2")
        assert r1.status_code == r2.status_code == 200
        assert 'page=2"' in r1.data.decode()

    def test_front_page_rows_all_linked_when_captured(self, client):
        # The first page of the stock tab is fully covered by the quote walk:
        # every row links to its captured quote page (across all MICs).
        r = client.get("/listings_directory/stock")
        html = r.data.decode()
        linked = len(re.findall(r'href="/quote/[A-Z]+:', html))
        plain = len(re.findall(r'<td>\s*<span>[A-Z.]', html))
        assert linked == 20 and plain == 0


class TestQuotePages:
    def test_ko_quote(self, client):
        r = client.get("/quote/XNYS:KO")
        assert r.status_code == 200
        html = r.data.decode()
        assert "COCA-COLA CO" in html
        assert "Consumer Staples" in html
        assert "James Quincey" in html or "James R. Quincey" in html

    def test_ko_key_data(self, client):
        r = client.get("/quote/XNYS:KO")
        html = r.data.decode()
        assert "Key Data" in html
        assert "Board of Directors" in html

    def test_quote_404_unknown_symbol(self, client):
        assert client.get("/quote/XNYS:NOPE99").status_code == 404

    def test_quote_404_bad_mic(self, client):
        assert client.get("/quote/XNAS:KO").status_code == 404

    def test_quote_requires_colon(self, client):
        assert client.get("/quote/KO").status_code == 404

    def test_chart_renders_for_rich_symbol(self, client):
        r = client.get("/quote/XNYS:KO")
        html = r.data.decode()
        assert 'stroke="#0096d6"' in html
        assert "1W" in html and "5Y" in html

    def test_zoom_windows(self, client):
        for zoom, present in (("1W", True), ("1M", True), ("1Y", True)):
            r = client.get(f"/quote/XNYS:KO?zoom={zoom}")
            assert r.status_code == 200
            assert 'class="cur"' in r.data.decode()

    def test_options_table(self, client):
        r = client.get("/quote/XNYS:KO")
        html = r.data.decode()
        assert "Put/Call Ratio" in html
        assert "Strikes" in html
        assert "Openint" in html

    def test_options_expiry_tabs(self, client):
        r = client.get("/quote/XNYS:KO?exp=2")
        assert r.status_code == 200
        assert 'class="cur"' in r.data.decode()

    def test_index_quote(self, client):
        r = client.get("/quote/index/ABCERI")
        assert r.status_code == 200
        assert "AUSPICE BROAD COMMODITY EXCESS RETURN INDEX" in r.data.decode()

    def test_returns_panel(self, client):
        r = client.get("/quote/XNYS:KO")
        assert b"Total Return" in r.data


class TestIpoCenter:
    def test_recent_ipo_priced_deals(self, client):
        r = client.get("/ipo-center/recent-ipo")
        assert r.status_code == 200
        html = r.data.decode()
        assert "Accelevation Holdings Corp." in html
        assert "Priced Deals" in html
        assert "S&amp;P Global" in html

    def test_largest_window_toggle(self, client):
        r = client.get("/ipo-center/recent-ipo?window=180")
        assert r.status_code == 200
        assert "Largest 10 IPOs" in r.data.decode()

    def test_pricing_stats(self, client):
        r = client.get("/ipo-center/ipo-pricing-stats")
        assert r.status_code == 200
        assert "Basic Materials" in r.data.decode()
        assert "Priced Within" in r.data.decode()

    def test_filings_filters(self, client):
        r = client.get("/ipo-center/filings?status=Priced")
        html = r.data.decode()
        assert count_label(html, "deal") >= 1
        r2 = client.get("/ipo-center/filings?exchange=New+York+Stock+Exchange")
        assert r2.status_code == 200

    def test_backlog_totals(self, client):
        r = client.get("/ipo-center/backlog")
        assert r.status_code == 200
        assert "Consumer Services" in r.data.decode()


class TestBellCalendar:
    def test_calendar(self, client):
        r = client.get("/bell/calendar")
        assert r.status_code == 200
        assert count_label(r.data.decode(), "bell event") == 300

    def test_type_filter(self, client):
        r = client.get("/bell/calendar?type=Closing+Bell")
        html = r.data.decode()
        assert "Opening Bell" not in re.sub(r"<option[^>]*>.*?</option>", "", html, flags=re.S)

    def test_search(self, client):
        r = client.get("/bell/calendar?q=Vanguard")
        html = r.data.decode()
        assert "Vanguard" in html
        assert count_label(html, "bell event") >= 1

    def test_date_window(self, client):
        r = client.get("/bell/calendar?from=2026-09-01&to=2026-09-30")
        assert r.status_code == 200
        assert count_label(r.data.decode(), "bell event") >= 1

    def test_event_image_resolves(self, client):
        r = client.get("/bell/calendar")
        imgs = re.findall(r'src="(/static/images/upstream/[^"]+)"',
                          r.data.decode())
        assert len(imgs) >= 10


class TestSiteSearch:
    def test_search_gold(self, client):
        r = client.get("/search?q=gold")
        assert r.status_code == 200
        assert "Listings" in r.data.decode()

    def test_search_bell(self, client):
        r = client.get("/search?q=Vanguard")
        assert r.status_code == 200
        assert "Bell Events" in r.data.decode()

    def test_empty_search(self, client):
        r = client.get("/search")
        assert r.status_code == 200


class TestSeedMatchesCapture:
    def test_market_mover_prices(self, client):
        r = client.get("/markets")
        html = r.data.decode()
        assert "NU HOLDINGS LTD" in html

    def test_benchmark_users(self, client):
        from app import User
        with nyse_app.app.app_context():
            for email in ("alice.j@test.com", "bob.c@test.com",
                          "carol.d@test.com", "dana.k@test.com"):
                assert User.query.filter_by(email=email).first()

    def test_home_hero_text(self, client):
        r = client.get("/")
        html = r.data.decode()
        assert "The New York Stock Exchange is where icons and disruptors" in html


class TestReviewFixes:
    """Regression tests for the r1 review fix round."""

    def test_bell_titles_decode_entities(self, client):
        # The upstream feed stores numeric HTML entities in the raw titles;
        # the rendered pages must show the decoded characters exactly like
        # the live site, never the literal entity text.
        r = client.get("/bell/calendar")
        assert r.status_code == 200
        html = r.data.decode()
        assert "&#0174;" not in html
        assert re.search(r"Rings The (Closing|Opening) Bell\u00ae", html)

    def test_bell_hub_recent_titles_decode(self, client):
        r = client.get("/bell")
        html = r.data.decode()
        assert "&#0174;" not in html

    def test_site_search_bell_titles_decode(self, client):
        r = client.get("/search?q=Vanguard")
        html = r.data.decode()
        assert "&#0174;" not in html
        assert "The Vanguard Group, Inc. Rings The Closing Bell\u00ae" in html

    def test_bell_descriptions_decode_entities(self, client):
        # Numeric entities beyond &#0174; (\u00ed \u00e9 \u2019 \u2122 ...) must
        # decode in the flattened descriptions too.
        r = client.get("/bell/calendar")
        html = r.data.decode()
        assert "&#0237;" not in html and "&#0233;" not in html
        assert "&#8217;" not in html and "&#8482;" not in html

    def test_recent_ipo_priced_table_only_lists_priced(self, client):
        # The upstream "Priced Deals" table lists only deals that actually
        # priced; filed / expected / withdrawn / postponed rows live on the
        # Filings page.
        r = client.get("/ipo-center/recent-ipo")
        assert r.status_code == 200
        html = r.data.decode()
        assert "Accelevation Holdings Corp." in html
        assert "ADARx Pharmaceuticals, Inc." in html
        for filed_only in ("Ives Ultra AI Opportunities", "Fitness Fanatics",
                           "Hacker Interstellar", "Web3Labs Global",
                           "Holtec Nuclear Corp", "Bamboo Insurance Services",
                           "Oura Inc."):
            assert filed_only not in html, filed_only

    def test_filings_still_lists_every_status(self, client):
        r = client.get("/ipo-center/filings")
        html = r.data.decode()
        assert "Ives Ultra AI Opportunities" in html
        assert "Oura Inc." in html
        assert "Accelevation Holdings Corp." in html

    def test_ibm_company_facts_and_board(self, client):
        # The r1 capture came back with an empty boardMember block for IBM
        # (the only rich symbol affected); the gap-filled capture restores
        # the company facts and the board of directors.
        r = client.get("/quote/XNYS:IBM")
        assert r.status_code == 200
        html = r.data.decode()
        assert "Arvind Krishna" in html
        assert "Technology" in html
        assert "Board of Directors" in html
        assert "Andrew N. Liveris" in html
        assert "Ramon L. Laguarta" in html


class TestAssetInventory:
    def test_every_referenced_image_is_inventoried(self, client):
        inventory = json.load(open(SITE / 'asset_inventory.json'))
        known = {row['path'].split('/')[-1] for row in inventory['assets']}
        for url in ('/', '/bell/calendar', '/history-of-nyse', '/listings'):
            html = client.get(url).data.decode()
            for name in re.findall(
                    r'/static/images/upstream/([A-Za-z0-9._%()+-]+)', html):
                assert name in known, f"referenced image not inventoried: {name}"

    def test_inventory_rows_carry_sha_and_source(self):
        inventory = json.load(open(SITE / 'asset_inventory.json'))
        for row in inventory['assets']:
            assert row['source_url'].startswith('https://')
            assert len(row['sha256']) == 64
            assert row['bytes'] > 0
            path = SITE / row['path']
            assert path.exists() and path.stat().st_size == row['bytes']

    def test_no_duplicate_image_bytes(self):
        inventory = json.load(open(SITE / 'asset_inventory.json'))
        hashes = [row['sha256'] for row in inventory['assets']]
        assert len(hashes) == len(set(hashes))
