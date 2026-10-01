"""Contract tests: every route family renders real upstream-sourced content."""
import json
import re


def _get(client, path):
    resp = client.get(path)
    assert resp.status_code == 200, f"{path} -> {resp.status_code}"
    return resp.get_data(as_text=True)


def test_health(client):
    data = json.loads(client.get('/_health').get_data())
    assert data['ok'] is True
    assert data['site'] == 'uscis'
    assert data['pages'] >= 60
    assert data['forms'] >= 100
    assert data['fees'] >= 120
    assert data['news'] >= 50
    assert data['glossary'] >= 250
    assert data['offices'] >= 90
    assert data['zips'] >= 40000
    assert data['surgeons'] >= 15
    assert data['processing_times'] >= 60
    assert data['wizard_states'] >= 25
    assert data['users'] == 4


def test_homepage(client):
    html = _get(client, '/')
    for marker in ['Manage Your Case', 'File Online', 'Explore by Topic',
                   'Case Status Online', 'Processing Times', 'Fee Calculator',
                   'Find a Civil Surgeon', 'Newsroom']:
        assert marker in html, f"homepage missing {marker!r}"


def test_content_pages(client):
    probes = [
        ('/green-card', 'Green Card'),
        ('/citizenship', 'Citizenship'),
        ('/working-in-the-united-states', 'Working in the United States'),
        ('/humanitarian/temporary-protected-status', 'Temporary Protected Status'),
        ('/green-card/green-card-eligibility-categories', 'Green Card Eligibility Categories'),
        ('/tools/while-my-case-is-pending', 'While My Case is Pending'),
        ('/avoid-scams', 'Avoid Scams'),
        ('/contactcenter', 'USCIS Contact Center'),
        ('/file-online/forms-available-to-file-online', 'Forms Available to File Online'),
        ('/i-9-central', 'I-9 Central'),
    ]
    for path, marker in probes:
        html = _get(client, path)
        assert marker in html, f"{path} missing {marker!r}"


def test_forms_catalog(client):
    html = _get(client, '/forms')
    assert 'All Forms' in html
    assert 'Form Details' in html
    html = _get(client, '/forms?q=I-485')
    assert 'I-485' in html and 'Application to Register Permanent Residence' in html
    html = _get(client, '/forms?q=N-400')
    assert 'Application for Naturalization' in html
    html = _get(client, '/forms?online=1')
    assert 'File Online' in html


def test_form_detail_pages(client):
    html = _get(client, '/i-485')
    assert 'Application to Register Permanent Residence' in html
    assert 'i-485.pdf' in html and 'Edition Date' in html
    html = _get(client, '/n-400')
    assert 'Application for Naturalization' in html
    assert 'n-400.pdf' in html
    html = _get(client, '/i-765')
    assert 'i-765ws.pdf' in html  # the real worksheet PDF ships


def test_pdf_download(client):
    resp = client.get('/download/i-485.pdf')
    assert resp.status_code == 200
    assert resp.data[:4] == b'%PDF'
    resp = client.get('/download/n-400.pdf')
    assert resp.status_code == 200
    assert resp.data[:4] == b'%PDF'


def test_fee_calculator(client):
    html = _get(client, '/feecalculator')
    assert 'Select a Form for Fee Information' in html
    assert 'What is the Fee Calculator?' in html
    m = re.search(r'<option value="(\d+)"[^>]*>I-485, Application to Register', html)
    assert m, "I-485 missing from the fee dropdown"
    html = _get(client, f'/feecalculator?form={m.group(1)}')
    assert 'Filing Category' in html
    assert '$1,440' in html and '$1,390' in html


def test_processing_times(client):
    html = _get(client, '/processing-times')
    assert 'Processing Times' in html
    assert 'I-485' in html and 'N-400' in html
    html = _get(client, '/processing-times?form=N-400&office=SEA')
    assert 'Application for Naturalization' in html
    assert '15.5 Months to 21 Months' in html
    assert 'August 03, 2017' in html


def test_case_status(client):
    html = _get(client, '/casestatus')
    assert 'Case Status Online' in html
    assert 'receipt number' in html
    resp = client.post('/casestatus', data={'receipt': 'BOGUS123'})
    assert resp.status_code == 200
    assert b'does not recognize the receipt number' in resp.data


def test_civil_surgeon(client):
    html = _get(client, '/tools/find-a-civil-surgeon')
    assert 'Find a Civil Surgeon' in html
    html = _get(client, '/tools/find-a-civil-surgeon?zip=22202')
    assert 'VAN DORN PEDIATRICS' in html
    assert 'of 6815' not in html  # only the ZIP-matched fixture is displayed


def test_glossary(client):
    html = _get(client, '/tools/glossary')
    assert 'Glossary' in html
    html = _get(client, '/tools/glossary?q=adjustment')
    assert 'Adjustment of Status' in html
    html = _get(client, '/tools/glossary?letter=B')
    assert 'Biometrics' in html


def test_field_office(client):
    html = _get(client, '/about-us/find-a-uscis-office/field-offices')
    assert 'Field Offices' in html
    html = _get(client, '/about-us/find-a-uscis-office/field-offices/search?zip=60601')
    assert 'Chicago' in html
    assert '101 West Ida B. Wells Drive' in html


def test_newsroom(client):
    html = _get(client, '/newsroom')
    assert 'Newsroom' in html
    html = _get(client, '/newsroom/alerts')
    assert 'Alert' in html
    html = _get(client, '/newsroom/news-releases')
    assert 'News Release' in html
    detail = _get(client, '/newsroom/alerts/uscis-reaches-h-2b-cap-for-first-half-of-fy-2027')
    assert 'H-2B Cap' in detail
    assert '09/11/2026' in detail


def test_eligibility_tool(client):
    html = _get(client, '/citizenship-resource-center/learn-about-citizenship/'
                        'naturalization-eligibility-tool-0')
    assert 'Naturalization Eligibility Tool' in html
    assert 'Were one or both of your parents a U.S. citizen when you were born?' in html


def test_appointment_landing(client):
    html = _get(client, '/appointment')
    assert 'My Appointment' in html
    assert 'ADIT Stamp' in html
    assert 'Emergency Advance Parole (EAP)' in html
    assert 'Immigration Judge Grant' in html
    assert 'Other' in html


def test_account_routes_guarded(client):
    resp = client.get('/account')
    assert resp.status_code == 302  # login required
    html = _get(client, '/account/login')
    assert 'Sign in to your USCIS online account' in html


def test_404(client):
    resp = client.get('/this-page-does-not-exist')
    assert resp.status_code == 404
    assert b'Page Not Found' in resp.data
