import re
import pytest
import app as zr
from conftest import with_csrf


def test_pagination_has_no_duplicates_or_omissions(client):
    url = '/jobs-search?search=software+engineer&location=San+Francisco%2C+CA&page='
    ids = []
    for page in [1, 2]:
        ids += re.findall(r'id="job-card-([^"]+)"', client.get(url+str(page)).text)
    assert len(ids) == len(set(ids)) == 22


@pytest.mark.parametrize('query', ['days=bad', 'days=-1', 'smin=abc',
                                  'smin=90000&smax=70000', 'remote=invalid'])
def test_invalid_filters_fail_cleanly(client, query):
    assert client.get('/jobs-search?search=nurse&'+query).status_code == 400


def test_metros_are_available_without_source_json(client, monkeypatch):
    monkeypatch.setattr(zr, '_load', lambda _: pytest.fail('Runtime JSON read'))
    body = client.get('/jobs-search?search=software+engineer&location=San+Francisco%2C+CA').text
    assert '<h1>22 ' in body


def test_unsubmitted_application_has_no_confirmation(alice):
    assert alice.get('/apply/done/5f4b2c55241a752f').status_code == 404


def test_regular_job_cannot_quick_apply(alice):
    path = '/c/Veritus/Job/Forward-Deployed-Software-Engineer/-in-San-Francisco,CA?jid=5f4b2c55241a752f'
    with zr.app.app_context():
        before = zr.Application.query.count()
    r = alice.post('/apply/5f4b2c55241a752f', data=with_csrf(alice, path, {}))
    assert r.status_code == 400
    with zr.app.app_context():
        assert zr.Application.query.count() == before


def test_alert_rejects_invalid_frequency(alice):
    r = alice.post('/jobseeker/alerts', data=with_csrf(alice, '/jobseeker/alerts',
        {'term': 'nurse', 'location': 'Brooklyn, NY', 'frequency': 'hourly'}))
    assert r.status_code == 400


@pytest.mark.parametrize('target', ['https://example.org', '//example.org', '/\\example.org'])
def test_safe_redirects(target):
    assert zr.safe_next(target) == '/'


def test_mismatched_company_profile_not_attributed_to_voice_ai_employer(client):
    body = client.get('/co/Veritus').text
    assert 'could not be reliably matched' in body
    assert 'Mental Health Practitioners' not in body
    assert 'veritussolutions.com' not in body
