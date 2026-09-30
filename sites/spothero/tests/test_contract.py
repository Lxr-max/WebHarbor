"""Contract tests: tasks.jsonl schema, page-200 smoke coverage, and the
seed/quote/search integrity invariants the reviewer relies on."""
import json
import pathlib
import re

from conftest import SITE

import pytest


# ------------------------------------------------------------------ tasks.jsonl

def test_tasks_contract():
    rows = [json.loads(line) for line
            in (SITE / 'tasks.jsonl').read_text().splitlines() if line.strip()]
    assert 15 <= len(rows) <= 25, 'task count outside the 15-25 band'
    contributor_keys = {'web_name', 'id', 'ques', 'web', 'upstream_url'}
    review_keys = {'verifier_path', 'judge_rubric'}  # appended by orch/review/spothero
    for row in rows:
        assert set(row) == contributor_keys | review_keys, \
            'five contributor keys (optionally + the two review-appended keys)'
        assert row['web_name'] == 'SpotHero'
        assert row['web'] == 'http://localhost:40106/'
        assert row['upstream_url'] == 'https://spothero.com/'
        assert re.fullmatch(r'SpotHero--\d+', row['id'])
        words = len(row['ques'].split())
        assert words <= 100, f"{row['id']} wording exceeds 100 words"
        assert 'answer' not in row
    ids = [r['id'] for r in rows]
    assert len(set(ids)) == len(ids), 'duplicate task ids'


def test_tasks_functional_breadth():
    rows = [json.loads(line) for line
            in (SITE / 'tasks.jsonl').read_text().splitlines() if line.strip()]
    text = ' '.join(r['ques'].lower() for r in rows)
    domains = {
        'hourly booking': 'book' in text and 'guest' in text,
        'monthly': 'monthly' in text,
        'airport': "o'hare" in text or 'airport' in text,
        'events': 'event parking' in text or 'game' in text,
        'account auth': 'testpass123!' in text,
        'payment methods': 'default' in text and 'payment' in text,
        'favorites': 'saved spots' in text,
        'profile': 'license plate' in text,
        'policy research': 'faq' in text or 'guarantee' in text,
        'comparison': 'compare' in text,
    }
    missing = [name for name, ok in domains.items() if not ok]
    assert not missing, f'tasks must cover: {missing}'


# ------------------------------------------------------------------ page smoke

PAGES = [
    '/',
    '/_health',
    '/cities',
    '/city/chicago-parking',
    '/city/monthly/chicago-parking',
    '/destination/chicago/wrigley-field-parking',
    '/destination/seattle/climate-pledge-arena-parking',
    '/destination/nyc-parking/times-square-parking',
    '/airport/chicago/ord-parking',
    '/airport/chicago-ord-parking',
    '/parking/airport-parking',
    '/parking/stadium-parking',
    '/parking/monthly-parking',
    '/faq',
    '/about',
    '/about/parking-guarantee',
    '/about/promo-code',
    '/legal/terms-of-use',
    '/sell-parking/operators',
    '/auth/login',
    '/auth/signup',
    '/search?kind=address&latitude=41.882552&longitude=-87.622551'
    '&search_string=Millennium+Park,+Chicago,+IL,+USA'
    '&starts=2026-10-03T12:00&ends=2026-10-03T18:00',
    '/search?kind=monthly&search_string=Chicago,+IL,+USA'
    '&monthly_start=2026-10-01&sort=price',
    '/search?kind=airport&airport=ORD&starts=2026-10-03T12:00'
    '&ends=2026-10-06T12:00',
    '/search?kind=event&id=1391016',
]


@pytest.mark.parametrize('path', PAGES)
def test_pages_render(client, path):
    response = client.get(path)
    assert response.status_code == 200, path
    body = response.get_data(as_text=True)
    if path == '/_health':
        import json
        assert json.loads(body)['ok'] is True
        return
    assert len(body) > 500, f'{path} rendered suspiciously little content'
    assert 'Whoops' not in body[:1000], f'{path} rendered the 404 page'


def test_destination_featured_cards_present(client):
    body = client.get('/destination/chicago/wrigley-field-parking'
                      ).get_data(as_text=True)
    assert body.count('class="spot-card"') >= 6, 'Wrigley must list its featured spots'
    for title in ['1075 W Addison St.', 'Hotel Zachary', 'Sheffield']:
        assert title in body, f'missing upstream featured spot: {title}'


def test_stadium_directory_counts(client):
    body = client.get('/parking/stadium-parking').get_data(as_text=True)
    assert 'NFL Stadiums' in body and 'NHL Arenas' in body
    # no count labels leak the answer to "how many" tasks
    assert not re.search(r'\b\d+\s+(?:NFL stadiums|NHL arenas|stadiums)\b',
                         body, re.I)


def test_unknown_route_404s(client):
    response = client.get('/no/such/page')
    assert response.status_code == 404


def test_airport_code_redirects(client):
    response = client.get('/airport-code/MDW')
    assert response.status_code == 302
    follow = client.get('/airport-code/MDW', follow_redirects=True)
    assert follow.status_code == 200
    assert 'Midway' in follow.get_data(as_text=True)


def test_suggest_api(client):
    body = client.get('/api/suggest?q=Seattle%20Kraken%20vs.%20Calgary%20Flames')
    results = body.get_json()['results']
    labels = [r['label'] for r in results]
    assert any('Oct 4' in lab for lab in labels), \
        'event suggestions must disambiguate by venue-local date'
    assert all(r['url'].startswith('/search?kind=event') for r in results)


# ------------------------------------------------------- search/radius integrity

def test_event_search_stays_local(client):
    """Event parking must only offer facilities within walking distance of
    the venue -- never cross-city inventory."""
    body = client.get('/search?kind=event&id=1391016').get_data(as_text=True)
    # the results list must only contain Seattle-inventory addresses
    listing = body.split('class="spot-list"', 1)[-1].split('</main>')[0]
    addresses = re.findall(r'([\d]+ [A-Z][^<]*)<', listing)
    assert addresses, 'event search must list venue-local options'
    assert not any('Chicago' in a for a in addresses), \
        'cross-city facility leaked into the Seattle event search'


def test_address_search_radius(client):
    """A search near Wrigley Field must return walkable options only."""
    body = client.get('/search?kind=address&latitude=41.947455'
                      '&longitude=-87.655593'
                      '&search_string=Wrigley+Field,+Chicago,+IL,+USA'
                      '&starts=2026-10-05T17:00&ends=2026-10-05T23:00'
                      ).get_data(as_text=True)
    assert 'Addison' in body or 'Sheffield' in body, \
        'Wrigley-area search should surface the nearby lots'
    assert 'Times Square' not in body and 'Fenway' not in body


def test_quotes_are_deterministic(client):
    quote1 = client.get('/api/facility/129876/quote?starts=2026-10-05T17:00'
                        '&ends=2026-10-05T23:00').get_json()
    quote2 = client.get('/api/facility/129876/quote?starts=2026-10-05T17:00'
                        '&ends=2026-10-05T23:00').get_json()
    assert quote1 == quote2
    assert quote1['total'] > 0


def test_promo_discount_math(client):
    """FIRSTSPOT10 must take exactly 10% off the subtotal at checkout."""
    body = client.get('/purchase/hourly?facility=2348&starts=2026-10-03T12:00'
                     '&ends=2026-10-03T18:00').get_data(as_text=True)
    m = re.search(r'Subtotal\s*\$([\d.]+)', re.sub(r'<[^>]+>', ' ', body))
    subtotal = float(m.group(1))

    # drive the promo through the real form path (FormClient scrapes the token)
    resp = client.post('/purchase/hourly?facility=2348&starts=2026-10-03T12:00'
                       '&ends=2026-10-03T18:00',
                       data={'action': 'promo', 'promo': 'FIRSTSPOT10'})
    body2 = resp.get_data(as_text=True)
    m = re.search(r'Promo FIRSTSPOT10\s*-?\$([\d.]+)',
                  re.sub(r'<[^>]+>', ' ', body2))
    assert m, 'promo line must appear in the price breakdown'
    assert abs(float(m.group(1)) - round(subtotal * 0.10, 2)) < 0.02
