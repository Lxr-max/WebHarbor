from conftest import su_app

def test_library_aliases_carry_hours_without_duplicates(client):
    with su_app.app.app_context():
        for name, alias in [('Robin Li and Melissa Ma Science Library', 'Science Library (Li and Ma)'), ('Branner Earth Sciences Library & Map Collections', 'Earth Sciences Library & Map Collections (Branner)')]:
            lib = su_app.Library.query.filter_by(name=name).one()
            assert lib.hours_rows and lib.location
            assert not su_app.Library.query.filter_by(name=alias).count()
            page = client.get('/libraries/' + lib.slug).get_data(as_text=True)
            assert 'Library &amp; circulation' in page

def test_aid_thresholds_do_not_claim_individual_awards(client):
    text = client.get('/admission/aid?income=120000&family=2').get_data(as_text=True)
    assert 'No tuition responsibility' in text
    assert 'no-room-and-board threshold is below $100,000' in text
    assert 'assets typical' in text
    assert 'does not calculate an individual award' in text
    bad = client.get('/admission/aid?income=120000&family=0').get_data(as_text=True)
    assert 'class="facts"' not in bad

def test_program_compare_uses_named_options(client):
    text = client.get('/programs/CS-BS?compare=CS-MS').get_data(as_text=True)
    assert 'Compare with program' in text
    assert 'Computer Science (MS)' in text
    assert 'Open CS-MS' in text


def test_missing_event_times_and_prices_are_not_invented(client):
    with su_app.app.app_context():
        event = su_app.CampusEvent.query.filter_by(title='Climber Coffee').one()
        text = client.get('/events/' + str(event.eid)).get_data(as_text=True)
    assert 'Time not listed' in text
    assert 'Admission cost not listed' in text
    assert '<td>None</td>' not in text
