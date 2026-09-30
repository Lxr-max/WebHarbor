"""Flow tests: auth, watchlist, converter — all with CSRF enabled."""
from conftest import with_csrf


def test_register_login_logout(client):
    r = client.post('/signup', data=with_csrf(client, '/signup', {
        'email': 'flow.user@example.com', 'password': 'TestPass123!',
        'newsletter': 'on'}))
    assert r.status_code == 302
    body = client.get('/').get_data(as_text=True)
    assert 'Hi, flow' in body
    r = client.post('/logout', data=with_csrf(client, '/', {}))
    assert r.status_code == 302
    body = client.get('/').get_data(as_text=True)
    assert 'Log In' in body


def test_register_rejects_bad_email(client):
    r = client.post('/signup', data=with_csrf(client, '/signup', {
        'email': 'not-an-email', 'password': 'TestPass123!'}))
    body = r.get_data(as_text=True)
    assert 'not in the correct format' in body


def test_register_rejects_short_password(client):
    r = client.post('/signup', data=with_csrf(client, '/signup', {
        'email': 'short.pw@example.com', 'password': 'short'}))
    body = r.get_data(as_text=True)
    assert 'at least 8 characters' in body


def test_login_rejects_wrong_password(client):
    r = client.post('/login', data=with_csrf(client, '/login', {
        'email': 'alice.j@test.com', 'password': 'WrongPass999'}))
    body = r.get_data(as_text=True)
    # exact upstream error string
    assert 'Your email and password does not match. Please try again.' in body


def test_guest_watchlist_session_flow(client):
    # star two coins as a guest
    for slug in ('dogecoin', 'xrp'):
        r = client.post('/watchlist/toggle/' + slug,
                        data=with_csrf(client, f'/currencies/{slug}/',
                                      {'next': '/watchlist/'}))
        assert r.status_code == 302
    body = client.get('/watchlist/').get_data(as_text=True)
    assert 'Dogecoin' in body and 'XRP' in body
    assert 'Wanna keep this Watchlist?' in body
    # remove one
    r = client.post('/watchlist/', data=with_csrf(client, '/watchlist/',
                                                  {'remove': 'xrp'}))
    body = client.get('/watchlist/').get_data(as_text=True)
    assert 'XRP' not in body and 'Dogecoin' in body


def test_guest_watchlist_carries_into_signup(client):
    client.post('/watchlist/toggle/bitcoin',
                data=with_csrf(client, '/currencies/bitcoin/',
                              {'next': '/watchlist/'}))
    r = client.post('/signup', data=with_csrf(client, '/signup', {
        'email': 'carry.over@example.com', 'password': 'TestPass123!'}))
    assert r.status_code == 302
    body = client.get('/watchlist/').get_data(as_text=True)
    assert 'Bitcoin' in body
    assert 'Wanna keep this Watchlist?' not in body


def test_alice_seed_fixture(alice):
    body = alice.get('/watchlist/').get_data(as_text=True)
    for name in ('Bitcoin', 'Ethereum', 'Solana'):
        assert name in body
    # alice's watchlist is account-saved: no guest prompt
    assert 'Wanna keep this Watchlist?' not in body


def test_watchlist_add_remove_logged_in(alice):
    r = alice.post('/watchlist/toggle/chainlink',
                   data=with_csrf(alice, '/currencies/chainlink/',
                                 {'next': '/watchlist/'}))
    assert r.status_code == 302
    body = alice.get('/watchlist/').get_data(as_text=True)
    assert 'Chainlink' in body
    r = alice.post('/watchlist/', data=with_csrf(alice, '/watchlist/',
                                                 {'remove': 'chainlink'}))
    body = alice.get('/watchlist/').get_data(as_text=True)
    assert 'Chainlink' not in body


def test_watchlists_are_per_user(alice):
    # a second, anonymous client must not see alice's saved watchlist
    import app as cmc
    anon = cmc.app.test_client()
    anon.post('/watchlist/toggle/dogecoin',
              data=with_csrf(anon, '/currencies/dogecoin/',
                             {'next': '/watchlist/'}))
    body = anon.get('/watchlist/').get_data(as_text=True)
    assert 'Dogecoin' in body
    assert 'Ethereum' not in body  # alice's ETH is not in the guest list


def test_converter_computes_from_captured_prices(client):
    # 2.5 BTC -> USD must equal 2.5 x captured BTC price
    import json
    from pathlib import Path
    coins = json.loads((Path(__file__).resolve().parents[1]
                       / 'source_data' / 'coins.json').read_text())
    btc = next(c for c in coins if c['slug'] == 'bitcoin')
    eth = next(c for c in coins if c['slug'] == 'ethereum')
    r = client.post('/converter/', data=with_csrf(client, '/converter/', {
        'amount': '2.5', 'from': 'bitcoin', 'to': 'usd'}))
    body = r.get_data(as_text=True)
    expected = f"${2.5 * btc['price']:,.2f}"
    assert expected in body
    # 1 BTC -> ETH uses the captured ETH price
    r = client.post('/converter/', data=with_csrf(client, '/converter/', {
        'amount': '1', 'from': 'bitcoin', 'to': 'ethereum'}))
    body = r.get_data(as_text=True)
    expected_eth = btc['price'] / eth['price']
    assert f"${expected_eth:,.2f}" in body


def test_converter_rejects_bad_amount(client):
    r = client.post('/converter/', data=with_csrf(client, '/converter/', {
        'amount': 'not-a-number', 'from': 'bitcoin', 'to': 'usd'}))
    assert r.status_code == 200  # re-renders without a result box
    assert 'result-box' not in r.get_data(as_text=True)
