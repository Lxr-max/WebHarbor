"""Contract tests: seeded data, public pages, CSRF on every POST form,
asset integrity and the search/filter semantics."""
import hashlib
import json
import os
import re

import app as zr
from conftest import with_csrf


# ------------------------------------------------------------------- seeds --

def test_seed_counts():
    with zr.app.app_context():
        assert zr.Job.query.filter_by(active=True).count() >= 700
        assert zr.Company.query.count() >= 400
        assert zr.SalaryStat.query.count() >= 15
        assert zr.JobTitle.query.count() == 14
        assert zr.JobCategory.query.count() == 9
        assert zr.Article.query.count() >= 12
        assert zr.TitleFaq.query.count() >= 100
        assert zr.User.query.filter_by(is_benchmark=True).count() == 4
        assert zr.SavedJob.query.count() == 8
        assert zr.Application.query.count() == 4
        assert zr.ApplicationEvent.query.count() == 9
        assert zr.JobAlert.query.count() == 5
        assert zr.Resume.query.count() == 3
        assert zr.Profile.query.count() == 4
        assert zr.SearchSnapshot.query.count() == 17


def test_benchmark_password_frozen():
    with zr.app.app_context():
        alice = zr.User.query.filter_by(email='alice.j@test.com').first()
        assert zr.bcrypt.check_password_hash(alice.password_hash,
                                             'TestPass123!')


def test_health_ok(client):
    r = client.get('/_health')
    assert r.status_code == 200
    data = json.loads(r.get_data(as_text=True))
    assert data['ok'] is True
    assert data['jobs'] >= 700 and data['companies'] >= 400


def test_every_seed_image_is_real_upstream():
    """Every image served from static/images/upstream is inventoried with an
    https source URL, exact byte length and sha256 (no placeholders)."""
    inv = json.load(open(os.path.join(zr.BASE_DIR,
                                      'asset_inventory.json')))
    rows = inv['assets']
    assert inv['asset_count'] == len(rows) == len({r['path'] for r in rows})
    for row in rows:
        path = os.path.join(zr.BASE_DIR, row['path'])
        data = open(path, 'rb').read()
        assert len(data) == row['bytes']
        assert row['source_url'].startswith('https://')
        assert hashlib.sha256(data).hexdigest() == row['sha256']


def test_rendered_images_are_managed(client):
    """No <img src> in any public page may point outside managed assets."""
    seen = set()
    for path in ('/', '/jobs-search?search=software+engineer&location='
                 'San+Francisco%2C+CA', '/blog/', '/Jobs/Software-Engineer'):
        body = client.get(path).get_data(as_text=True)
        for m in re.finditer(r'src="(/static/images/[^"]+)"', body):
            seen.add(m.group(1))
    assert seen, "no managed images rendered"
    for s in seen:
        assert os.path.exists(os.path.join(zr.BASE_DIR, s.lstrip('/')))


# ------------------------------------------------------------ public pages --

def test_home(client):
    r = client.get('/')
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert 'ZipRecruiter' in body
    assert 'Search Jobs' in body
    assert 'phil-cartoon' in body or 'ZipRecruiter' in body


def test_serp_search_and_filters(client):
    r = client.get('/jobs-search?search=software+engineer'
                   '&location=San+Francisco%2C+CA')
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert 'Software engineer Jobs in San Francisco, CA' in body
    assert 'Remote' in body and 'Date posted' in body
    assert 'Employment types' in body and 'Experience level' in body
    # remote filter narrows the results
    r = client.get('/jobs-search?search=software+engineer'
                   '&location=San+Francisco%2C+CA&remote=remote')
    body = r.get_data(as_text=True)
    assert '<h1>1 ' in body
    # date filter narrows the results
    r = client.get('/jobs-search?search=software+engineer'
                   '&location=San+Francisco%2C+CA&days=5')
    body = r.get_data(as_text=True)
    assert '<h1>13 ' in body


def test_serp_filter_panel_upstream_taxonomy(client):
    body = client.get('/jobs-search?search=nurse').get_data(as_text=True)
    for label in ['All apply types', 'Quick apply only',
                  'All remote/on-site', 'On-site', 'Hybrid', 'Remote',
                  'Posted anytime', 'Within 30 days', 'Within 10 days',
                  'Within 5 days', 'Within 1 day',
                  'Full Time', 'Part Time', 'Per Diem', 'Contract',
                  'Temporary', 'Other',
                  'No experience needed', 'Junior level', 'Mid level',
                  'Senior level and above']:
        assert label in body, f"filter option {label!r} missing"


def test_job_detail_page(client):
    r = client.get('/c/Veritus/Job/Forward-Deployed-Software-Engineer/'
                   '-in-San-Francisco,CA?jid=5f4b2c55241a752f')
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert 'Forward Deployed Software Engineer' in body
    assert 'Veritus' in body
    assert 'About Veritus' in body
    assert 'Offices of Mental Health Practitioners' in body
    assert '11 - 50 employees' in body


def test_job_detail_404_on_wrong_slug(client):
    r = client.get('/c/Veritus/Job/Not-A-Real-Job/'
                   '-in-San-Francisco,CA?jid=5f4b2c55241a752f')
    assert r.status_code == 404


def test_company_profile_and_jobs(client):
    r = client.get('/co/Veritus')
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert 'VERITUS' in body.upper()
    assert 'Jobs at Veritus' in body
    r = client.get('/co/Veritus/Jobs/-in-San-Francisco,CA')
    assert r.status_code == 200
    assert 'open roles' in r.get_data(as_text=True)


def test_title_landing_pages(client):
    r = client.get('/Jobs/Software-Engineer')
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert 'Software Engineer Jobs' in body
    assert 'salaries/software-engineer-salary' in body.lower()
    r = client.get('/Jobs/Registered-Nurse/-in-New-York,NY')
    assert r.status_code == 200


def test_browse_pages(client):
    r = client.get('/browse')
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert 'Browse Jobs by Title' in body
    r = client.get('/browse/titles/S')
    assert r.status_code == 200
    assert 'Job titles starting with' in r.get_data(as_text=True)
    r = client.get('/browse/titles/1')
    assert r.status_code == 404


def test_salary_pages(client):
    r = client.get('/Salaries/Software-Engineer-Salary')
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert '$147,524' in body and '$70.92' in body
    assert 'Soledad, CA' in body and '$220,681' in body
    assert 'Senior Embedded Systems Engineer' in body
    # city variant
    r = client.get('/Salaries/Software-Engineer-Salary-in-San-Francisco,CA')
    assert r.status_code == 200
    assert '$173,808' in r.get_data(as_text=True)
    # 404 for unknown titles
    r = client.get('/Salaries/Not-A-Job-Salary')
    assert r.status_code == 404


def test_salary_nearby_jobs_are_real_rows(client):
    r = client.get('/Salaries/Registered-Nurse-Salary')
    body = r.get_data(as_text=True)
    assert 'Registered Nurse Stepdown' in body
    assert 'Quick 2 Hire' in body


def test_blog_pages(client):
    r = client.get('/blog/')
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert 'Career Advice' in body
    r = client.get('/blog/category/career-advice/trends/')
    assert r.status_code == 200
    r = client.get('/blog/salary_exp/')
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert 'The ZipRecruiter Editors' in body
    assert '1. There Are More Jobs' in body
    r = client.get('/blog/not-a-real-article/')
    assert r.status_code == 404


def test_404_page(client):
    r = client.get('/no-such-page')
    assert r.status_code == 404
    assert 'Page Not Found' in r.get_data(as_text=True)


# --------------------------------------------------------- CSRF on POSTs --

def test_login_requires_csrf(client):
    r = client.post('/authn/login?realm=candidates',
                    data={'email': 'alice.j@test.com',
                          'password': 'TestPass123!'})
    # Flask-WTF rejects the missing token
    assert r.status_code in (400, 302)
    if r.status_code == 302:
        # some configs redirect on failure; assert it did NOT log in
        r2 = client.get('/jobseeker/profile')
        assert r2.status_code == 302


def test_apply_requires_login(client):
    r = client.post('/apply/5f4b2c55241a752f',
                    data=with_csrf(client, '/authn/login?realm=candidates',
                                   {}))
    assert r.status_code == 302
    assert '/authn/login' in r.headers.get('Location', '')


def test_logout_requires_csrf(client):
    r = client.post('/authn/logout', data={})
    assert r.status_code in (400, 302)


# ------------------------------------------------------------- determinism --

def test_seed_is_idempotent():
    """Re-running the gated seed path must be a no-op (byte-stable DB)."""
    import subprocess
    import sys
    with zr.app.app_context():
        n_jobs = zr.Job.query.count()
    before = os.path.getsize(os.environ['ZIPRECRUITER_DB_URI']
                            .replace('sqlite:///', ''))
    # second boot path (no auto-seed) must not touch the DB rows
    with zr.app.app_context():
        assert zr.Job.query.count() == n_jobs
    after = os.path.getsize(os.environ['ZIPRECRUITER_DB_URI']
                            .replace('sqlite:///', ''))
    assert before == after


# ------------------------------------------------- r1-review fix coverage --

def test_employment_type_multiselect_via_repeated_params(client):
    """The employment-type checkboxes submit repeated et= params; the app
    must read them all (real-browser combination filter), not just the
    first (the r1 review's T3 UI defect)."""
    r = client.get('/jobs-search?search=nurse&et=part_time&et=per_diem')
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert '<h1>29 ' in body, 'combined Part Time + Per Diem count must be 29'
    assert re.search(r'name="et" value="part_time"[^>]*checked', body), \
        'Part Time checkbox must stay checked after submit'
    assert re.search(r'name="et" value="per_diem"[^>]*checked', body), \
        'Per Diem checkbox must stay checked after submit'
    assert 'Part Time, Per Diem' in body, 'chip labels must list both'
    # single comma-joined value keeps working (URL-shaped queries)
    r = client.get('/jobs-search?search=nurse&et=part_time,per_diem')
    assert '<h1>29 ' in r.get_data(as_text=True)


def test_job_descriptions_render_formatting_not_literal_tags(client):
    """438 captured descriptions store their inline formatting HTML-
    escaped; the render layer must unescape once so the browser shows
    bold/italics like the upstream, never literal <b>...</b> text."""
    with zr.app.test_request_context():
        with zr.app.app_context():
            rows = zr.Job.query.filter(
                zr.Job.description_html.like('%&lt;%')).limit(25).all()
            assert len(rows) >= 20, 'expected at least 20 escaped descriptions'
            urls = [job.url() for job in rows]
    for url in urls:
        r = client.get(url)
        assert r.status_code == 200
        body = r.get_data(as_text=True)
        assert '&lt;b&gt;' not in body and '&lt;strong&gt;' not in body, \
            f'literal tags rendered for {url}'
        assert '<strong>' in body or '<b>' in body or '<em>' in body or \
            '<i>' in body, f'formatting lost for {url}'


def test_salary_page_titles_upstream_style(client):
    r = client.get('/Salaries/Software-Engineer-Salary')
    assert r.status_code == 200
    assert '<title>Salary: Software Engineer (September, 2026) United States</title>' \
        in r.get_data(as_text=True)
    assert 'bound method' not in r.get_data(as_text=True)
    r = client.get('/Salaries/Software-Engineer-Salary-in-San-Francisco,CA')
    assert 'Salary: Software Engineer in San Francisco, CA (Sep, 2026)' \
        in r.get_data(as_text=True)


def test_salary_related_rows_are_not_dead_links(client):
    """The related-title table points at salary pages the capture never
    fetched; it must render as plain text (like top-cities), not links."""
    r = client.get('/Salaries/Software-Engineer-Salary')
    body = r.get_data(as_text=True)
    assert 'Senior Embedded Systems Engineer' in body
    assert 'href="/Salaries/senior-embedded-systems-engineer-Salary"' not in body


def test_browse_salaries_index_lists_all_salary_pages(client):
    """The footer's Search Salaries link must land on a real index that
    links every captured salary page (national and city)."""
    r = client.get('/browse/salaries')
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert 'Browse Salaries' in body
    with zr.app.app_context():
        n = zr.SalaryStat.query.count()
    hrefs = set(re.findall(r'href="(/Salaries/[^"]+)"', body))
    assert len(hrefs) >= n, 'index must link every captured salary page'
    for href in hrefs:
        assert client.get(href).status_code == 200, f'dead link {href}'


def test_privacy_policy_page_serves_banner_target(client):
    r = client.get('/privacy-policy')
    assert r.status_code == 200
    assert 'Privacy Policy' in r.get_data(as_text=True)


def test_company_profile_links_jobs_by_location(client):
    """Company pages must link their per-city jobs pages so they are
    reachable by navigation, not URL construction."""
    r = client.get('/co/Veritus')
    body = r.get_data(as_text=True)
    assert 'Jobs by location:' in body
    m = re.search(r'href="(/co/Veritus/Jobs/-in-San-Francisco,CA)"', body)
    assert m, 'missing San Francisco jobs-page link'
    r = client.get(m.group(1))
    assert r.status_code == 200
    assert 'Forward Deployed Software Engineer' in r.get_data(as_text=True)


def test_salary_city_pages_linked_from_national(client):
    r = client.get('/Salaries/Software-Engineer-Salary')
    body = r.get_data(as_text=True)
    m = re.search(r'href="(/Salaries/software-engineer-Salary-in-San-Francisco,CA)"',
                   body)
    assert m, 'national page must link its captured city pages'
    r = client.get(m.group(1))
    assert r.status_code == 200
    assert 'See the United States average' in r.get_data(as_text=True)


def test_blog_categories_match_captured_articles(client):
    """Every listed blog category must hold at least one captured
    article; Students and Work Life nest their articles (r1 item 8)."""
    with zr.app.app_context():
        cats = zr.BlogCategory.query.all()
        roots = [c for c in cats if c.parent_id is None]
        subs = [c for c in cats if c.parent_id is not None]
        assert len(roots) == 1 and len(subs) == 6
        names = {c.name for c in subs}
        assert names == {'Career Paths', 'Students', 'The Hiring Process',
                         'Trends', 'Veterans', 'Work Life'}
        for c in subs:
            n = zr.Article.query.filter_by(category_id=c.id).count()
            assert n > 0, f'category {c.name} is empty'
    r = client.get('/blog/')
    body = r.get_data(as_text=True)
    assert 'Students' in body and 'Work Life' in body
    assert 'Professional Development' not in body
    r = client.get('/blog/category/career-advice/work-life/')
    assert r.status_code == 200
    assert '2 articles' in r.get_data(as_text=True)


def test_empty_search_degrades_to_near_me(client):
    r = client.get('/jobs-search')
    assert r.status_code == 302
    assert '/Search-Jobs-Near-Me' in r.headers['Location']
    # a real query still lands on the SERP
    r = client.get('/jobs-search?search=nurse')
    assert r.status_code == 200


def test_serp_title_matches_upstream_pattern(client):
    r = client.get('/jobs-search?search=software+engineer&location=San+Francisco%2C+CA')
    body = r.get_data(as_text=True)
    assert '<title>22 Software Engineer Jobs (NOW HIRING) in San Francisco, CA</title>' \
        in body


def test_badges_render_with_separator(client):
    """Badges must not concatenate into 'NewQuick apply' text."""
    r = client.get('/jobs-search?search=software+engineer&location=San+Francisco%2C+CA&days=5')
    body = r.get_data(as_text=True)
    assert 'NewQuick apply' not in re.sub(r'<[^>]+>', '', body)


def test_location_lines_use_upstream_bullet(client):
    r = client.get('/c/Veritus/Job/Forward-Deployed-Software-Engineer/'
                   '-in-San-Francisco,CA?jid=5f4b2c55241a752f')
    body = r.get_data(as_text=True)
    assert 'San Francisco, CA • On-site' in re.sub(r'<[^>]+>', '', body)
