"""Flow tests: register, apply, save/unsave, alerts, resume editing and
the seeded benchmark fixtures — all through real CSRF-protected forms."""
import re

import app as zr
from conftest import with_csrf


# ------------------------------------------------------------------ authn --

def test_register_login_logout(client):
    r = client.post('/authn/register?realm=candidates',
                    data=with_csrf(client, '/authn/register?realm=candidates',
                                   {'name': 'Flow Tester',
                                    'email': 'flow.t@test.com',
                                    'password': 'FlowPass123!',
                                    'location': 'Austin, TX'}))
    assert r.status_code == 302
    r = client.get('/jobseeker/profile')
    assert r.status_code == 200
    assert 'Flow Tester' in r.get_data(as_text=True)
    # logout (CSRF form)
    r = client.post('/authn/logout',
                    data=with_csrf(client, '/jobseeker/profile', {}))
    assert r.status_code == 302
    r = client.get('/jobseeker/profile')
    assert r.status_code == 302


def test_register_rejects_bad_input(client):
    r = client.post('/authn/register?realm=candidates',
                    data=with_csrf(client, '/authn/register?realm=candidates',
                                   {'name': '', 'email': 'bad',
                                    'password': 'short'}))
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert 'valid email' in body or 'full name' in body


def test_login_rejects_wrong_password(client):
    r = client.post('/authn/login?realm=candidates',
                    data=with_csrf(client, '/authn/login?realm=candidates',
                                   {'email': 'alice.j@test.com',
                                    'password': 'WrongPass999!'}))
    assert r.status_code == 200
    assert "doesn’t match" in r.get_data(as_text=True)


# ------------------------------------------------------- register + apply --

def test_register_and_one_click_apply(client):
    client.post('/authn/register?realm=candidates',
                data=with_csrf(client, '/authn/register?realm=candidates',
                               {'name': 'Apply Tester',
                                'email': 'apply.t@test.com',
                                'password': 'ApplyPass123!',
                                'location': 'Dallas, TX'}))
    r = client.get('/jobs-search?search=warehouse&location=Dallas%2C+TX'
                   '&apply=quick')
    body = r.get_data(as_text=True)
    m = re.search(r'class="job-title"><a href="([^"]+)"', body)
    assert m, "no job card on the logged-in quick-apply SERP"
    detail = client.get(m.group(1))
    dbody = detail.get_data(as_text=True)
    mj = re.search(r'action="/apply/(\w+)"', dbody)
    assert mj, "no apply form on the job detail page"
    jid = mj.group(1)
    r = client.post(f'/apply/{jid}',
                    data=with_csrf(client, m.group(1), {}))
    assert r.status_code == 302
    r = client.get('/jobseeker/applications')
    body = r.get_data(as_text=True)
    assert 'Status: <strong>Applied</strong>' in body
    assert '1-Click Application submitted' in body
    # applying twice redirects to applications without a second row
    r = client.post(f'/apply/{jid}', data=with_csrf(
        client, m.group(1), {}))
    assert r.status_code == 302
    with zr.app.app_context():
        u = zr.User.query.filter_by(email='apply.t@test.com').first()
        assert zr.Application.query.filter_by(user_id=u.id).count() == 1


# ------------------------------------------------------------- saved jobs --

def test_save_and_unsave(alice):
    r = alice.get('/c/Veritus/Job/Forward-Deployed-Software-Engineer/'
                  '-in-San-Francisco,CA?jid=5f4b2c55241a752f')
    assert r.status_code == 200
    r = alice.post('/save/5f4b2c55241a752f',
                   data=with_csrf(alice,
                                  '/c/Veritus/Job/Forward-Deployed-Software-'
                                  'Engineer/-in-San-Francisco,CA'
                                  '?jid=5f4b2c55241a752f', {}),
                   follow_redirects=False)
    assert r.status_code == 302
    r = alice.get('/jobseeker/saved-jobs')
    body = r.get_data(as_text=True)
    assert 'Forward Deployed Software Engineer' in body
    # unsave restores the previous state
    r = alice.post('/save/5f4b2c55241a752f',
                   data=with_csrf(alice, '/jobseeker/saved-jobs', {}),
                   follow_redirects=False)
    assert r.status_code == 302
    assert 'Forward Deployed Software Engineer' not in \
        alice.get('/jobseeker/saved-jobs').get_data(as_text=True)


def test_alice_seed_fixture(alice):
    r = alice.get('/jobseeker/saved-jobs')
    body = r.get_data(as_text=True)
    assert body.count('class="job-card"') == 3
    assert 'Registered Nurse' in body
    r = alice.get('/jobseeker/applications')
    body = r.get_data(as_text=True)
    assert 'Viewed' in body
    assert '1-Click Application submitted' in body
    r = alice.get('/jobseeker/alerts')
    body = r.get_data(as_text=True)
    assert 'registered nurse' in body and 'daily' in body


def test_bob_application_timeline(bob):
    r = bob.get('/jobseeker/applications')
    body = r.get_data(as_text=True)
    assert 'Interviewing' in body
    assert 'The employer invited you to schedule a phone screen' in body
    assert '2026-09-21' in body and '2026-09-27' in body


def test_dana_withdrawn_application(dana):
    r = dana.get('/jobseeker/applications')
    body = r.get_data(as_text=True)
    assert 'Withdrawn' in body
    assert 'You withdrew this application' in body


# ----------------------------------------------------------------- alerts --

def test_alert_create_and_delete(alice):
    r = alice.post('/jobseeker/alerts',
                   data=with_csrf(alice, '/jobseeker/alerts',
                                  {'term': 'licensed practical nurse',
                                   'location': 'Brooklyn, NY',
                                   'frequency': 'daily'}))
    assert r.status_code == 302
    body = alice.get('/jobseeker/alerts').get_data(as_text=True)
    assert 'licensed practical nurse' in body
    m = re.search(r'licensed practical nurse.*?name="alert_id" value="(\d+)"',
                  body, re.S)
    assert m, "new alert id not rendered"
    r = alice.post('/jobseeker/alerts',
                   data=with_csrf(alice, '/jobseeker/alerts',
                                  {'action': 'delete',
                                   'alert_id': m.group(1)}))
    assert r.status_code == 302
    body = alice.get('/jobseeker/alerts').get_data(as_text=True)
    assert 'licensed practical nurse' not in body


def test_alert_requires_term(alice):
    r = alice.post('/jobseeker/alerts',
                   data=with_csrf(alice, '/jobseeker/alerts',
                                  {'term': '', 'location': 'Anywhere',
                                   'frequency': 'daily'}))
    assert r.status_code == 302
    # no new alert row was created
    with zr.app.app_context():
        u = zr.User.query.filter_by(email='alice.j@test.com').first()
        assert zr.JobAlert.query.filter_by(user_id=u.id).count() == 1


# ----------------------------------------------------------------- resume --

def test_dana_resume_fixture_and_edit(dana):
    r = dana.get('/jobseeker/resume')
    body = r.get_data(as_text=True)
    assert 'Senior Accountant (CPA)' in body
    assert 'complete' in body
    assert 'NetSuite (5y)' in body
    assert 'Matter Family Office' in body
    # edit: add QuickBooks with 2 years
    data = {'title': 'Senior Accountant (CPA)',
            'summary': 'CPA with 8 years across public accounting and '
                       'industry; month-end close, audit readiness, NetSuite.',
            'exp_role_1': 'Senior Accountant',
            'exp_employer_1': 'Matter Family Office',
            'exp_start_1': '2022-04', 'exp_end_1': 'Present',
            'exp_text_1': 'Own the monthly close for 4 entities.',
            'edu_degree_1': 'BS, Accounting', 'edu_school_1': 'Metro State',
            'edu_year_1': '2018'}
    for i, (sk, yr) in enumerate([('NetSuite', '5'), ('GAAP', '8'),
                                  ('QuickBooks', '2')]):
        data[f'skill_{i+1}'] = sk
        data[f'skill_yrs_{i+1}'] = yr
    r = dana.post('/jobseeker/resume', data=with_csrf(
        dana, '/jobseeker/resume', data))
    assert r.status_code == 302
    body = dana.get('/jobseeker/resume').get_data(as_text=True)
    assert 'QuickBooks (2y)' in body


def test_carol_has_no_resume(carol):
    r = carol.get('/jobseeker/resume')
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert 'haven’t created a resume' in body or \
        'resume-preview' not in body


# ---------------------------------------------------------------- profile --

def test_profile_edit(alice):
    r = alice.post('/jobseeker/profile',
                   data=with_csrf(alice, '/jobseeker/profile',
                                  {'name': 'Alice Johnson',
                                   'phone': '(718) 555-0142',
                                   'location': 'Brooklyn, NY',
                                   'headline': 'ICU RN — night shift lead',
                                   'about': 'Updated about.',
                                   'years': '7',
                                   'remote': 'on'}))
    assert r.status_code == 302
    r = alice.get('/jobseeker/profile')
    body = r.get_data(as_text=True)
    assert 'ICU RN — night shift lead' in body
    with zr.app.app_context():
        u = zr.User.query.filter_by(email='alice.j@test.com').first()
        prof = zr.Profile.query.filter_by(user_id=u.id).first()
        assert prof.years_experience == 7
        assert prof.willing_remote is True


# ------------------------------------------------------------ metro search --

def test_metro_search_spans_nearby_cities(client):
    """'New York, NY' must match the upstream metro behavior: NJ cities
    appear in the results, exactly as the captured SERP shows."""
    r = client.get('/jobs-search?search=registered+nurse'
                   '&location=New+York%2C+NY')
    body = r.get_data(as_text=True)
    assert 'Hoboken, NJ' in body or 'Hackensack, NJ' in body


def test_snapshot_note_shows_upstream_total(client):
    body = client.get('/jobs-search?search=registered+nurse'
                      '&location=New+York%2C+NY').get_data(as_text=True)
    assert 'upstream reported' in body
