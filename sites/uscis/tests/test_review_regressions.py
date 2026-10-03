import app as m


def test_appointment_pages_do_not_read_scrape_json(client, monkeypatch):
    def unavailable(*args):
        raise AssertionError('runtime attempted to read build input')
    monkeypatch.setattr(m, '_load', unavailable)
    assert client.get('/appointment').status_code == 200


def test_invalid_booking_leaves_state_unchanged(auth_alice):
    with m.app.app_context():
        before = m.Appointment.query.count()
    for fields in [dict(reason='Invented',office='WAS',zip='22202',slot='2026-10-05|09:00 AM'), dict(reason='ADIT Stamp',office='WAS',zip='60601',slot='2026-10-05|09:00 AM'),dict(reason='ADIT Stamp',office='WAS',zip='22202',slot='1900-01-01|00:00 AM')]:
        response=auth_alice.post('/appointment/new',data=dict(action='pick_slot',**fields))
        assert response.status_code in (400,302)
    with m.app.app_context():
        assert m.Appointment.query.count()==before


def test_booking_keeps_lookup_zip_and_reserves_slot(auth_alice):
    with m.app.app_context():
        slot=m._slots_for('BOS')[0]
        before=m.Appointment.query.count()
    data=dict(action='pick_slot',reason='ADIT Stamp',office='BOS',zip='02108',slot=slot['date']+'|'+slot['time'])
    assert auth_alice.post('/appointment/new',data=data).status_code==302
    with m.app.app_context():
        booked=m.Appointment.query.order_by(m.Appointment.id.desc()).first()
        confirmation=booked.confirmation
        assert booked.booking_zip=='02108'
        assert slot not in m._slots_for('BOS')
    # Alice's profile ZIP is Arlington; lookup must use the ZIP used to book.
    assert 'Scheduled' in auth_alice.post('/appointment/view',data={'confirmation':confirmation,'zip':'02108'}).text
    auth_alice.post('/appointment/new',data=data)
    with m.app.app_context():
        assert m.Appointment.query.count()==before+1
        m.db.session.delete(m.Appointment.query.filter_by(confirmation=confirmation).one());m.db.session.commit()


def test_processing_bounds_are_numeric_and_ascending(client):
    html = client.get('/processing-times?form=I-485&office=CHI').text
    assert '13.5 Months to 35.5 Months' in html
    assert '35.5 Months to 13.5 Months' not in html
    assert m._duration_days({'value':2,'unit_en':'Years'}) > m._duration_days({'value':20,'unit_en':'Months'})


def test_female_filter_keeps_eligible_doctor_in_mixed_clinic(client):
    html = client.get('/tools/find-a-civil-surgeon?zip=60601&gender=Female').text
    assert html.count('class="surgeon"') == 5
    assert 'arti chawla' in html.lower()


def test_poverty_tables_have_regions_without_orphan_legacy_table(client):
    from bs4 import BeautifulSoup
    page = BeautifulSoup(client.get('/forms/filing-fees/poverty-guidelines').text, 'html.parser')
    tables = page.select('table')
    assert len(tables) == 3
    assert '49,500' in tables[0].text
    assert 'Alaska' in tables[1].text or 'Alaska' in str(tables[1].parent)
    assert 'Hawaii' in tables[2].text or 'Hawaii' in str(tables[2].parent)


def test_populated_initializer_does_not_commit(monkeypatch):
    def unexpected_commit():
        raise AssertionError('populated initialization attempted a commit')
    with m.app.app_context():
        monkeypatch.setattr(m.db.session, 'commit', unexpected_commit)
        m.main()
