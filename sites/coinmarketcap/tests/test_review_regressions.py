import re
import pytest
import app as cmc
from conftest import with_csrf


@pytest.mark.parametrize('query', ['page=abc', 'page=-1', 'price=bad~3', 'price=nan~5', 'price=10~2'])
def test_invalid_filters_fail_cleanly(client, query):
    assert client.get('/?'+query).status_code == 400


@pytest.mark.parametrize('amount', ['-1', 'nan', 'inf', 'bad', '1e309'])
def test_converter_rejects_invalid_amount(client, amount):
    r = client.post('/converter/', data=with_csrf(client, '/converter/',
        {'amount': amount, 'from': 'bitcoin', 'to': 'usd'}))
    assert r.status_code == 400


def test_crypto_conversion_has_no_dollar_unit(client):
    r = client.post('/converter/', data=with_csrf(client, '/converter/',
        {'amount': '1', 'from': 'bitcoin', 'to': 'ethereum'}))
    result = re.search(r'<div class="result-box">(.*?)</div>', r.text, re.S).group(1)
    assert '$' not in result
    assert 'Ethereum' in result


def test_newsletter_choice_is_saved(client):
    client.post('/signup', data=with_csrf(client, '/signup',
        {'email': 'newsletter@test.com', 'password': 'NewsPass123!', 'newsletter': 'on'}))
    with cmc.app.app_context():
        assert cmc.User.query.filter_by(email='newsletter@test.com').one().newsletter is True


def test_glossary_article_is_linked_and_complete(client):
    assert 'href="/academy/glossary/51-attack"' in client.get('/academy/glossary').text
    assert 'What Is a' in client.get('/academy/glossary/51-attack').text


def test_snapshot_links_to_current_coin_pages(client):
    assert 'href="/currencies/bitcoin/"' in client.get('/historical/20260927/').text or 'href="/currencies/bitcoin/"' in client.get('/historical/2026-09-27/').text


@pytest.mark.parametrize('target', ['https://example.org', '//example.org', '/\\example.org'])
def test_watchlist_redirect_stays_local(client, target):
    r = client.post('/watchlist/toggle/bitcoin', data=with_csrf(client, '/currencies/bitcoin/', {'next': target}))
    assert r.headers['Location'] == '/'


def test_glossary_search_keeps_matching_terms(client):
    body = client.get('/academy/glossary?q=51%25+Attack').text
    assert 'href="/academy/glossary/51-attack"' in body
    assert 'href="/academy/glossary/blockchain"' not in body
