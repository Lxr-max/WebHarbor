"""Reviewer regressions; no external evidence directory required."""
import re
from urllib.parse import urlsplit, parse_qs
import pytest
import app as site

@pytest.mark.parametrize('target', ['http://[invalid', '//[invalid', 'https://example.org/', '//example.org/', '/\\example.org/', '/%2fexample.org/', '/%5cexample.org/', '/%0d%0aLocation:https://example.org/'])
def test_external_continuations_stay_local(target):
    with site.app.test_request_context('/'):
        assert site.local_redirect(target, '/').location == '/'

@pytest.mark.parametrize('target', ['/papers?q=hello', '/account', '/search/publ?year=2026&type=article'])
def test_internal_continuations_survive(target):
    with site.app.test_request_context('/'):
        assert site.local_redirect(target, '/').location == target

def test_pagination_preserves_both_facets(client):
    response = client.get('/search/publ?q=graph&h=1&year=2026&type=article')
    html = response.get_data(as_text=True)
    href = re.search(r'href="([^"]+)">\[next', html).group(1)
    from html import unescape
    query = parse_qs(urlsplit(unescape(href)).query)
    assert query['year'] == ['2026'] and query['type'] == ['article']
    page = client.get(unescape(href)).get_data(as_text=True)
    assert 'year=2026' in page and 'type=article' in page


def test_cross_filtered_facets_are_attainable(client):
    html = client.get('/search/publ?q=query+optimization&type=article').get_data(as_text=True)
    from html import unescape
    links = re.findall(r'href="([^"]+year=\d+[^"]*)">(\d+) \((\d+)\)</a>', html)
    assert links
    for href, year, count in links:
        page = client.get(unescape(href)).get_data(as_text=True)
        actual = re.search(r'found (\d+) matches', page).group(1)
        assert actual == count and int(actual) > 0
