"""Regression coverage for invalid renewal and appointment submissions."""
import pytest
from conftest import vadm_app as m, with_csrf

@pytest.mark.parametrize('years',['-1','0','99','oops'])
def test_invalid_license_term(carol,years):
    with m.app.app_context():
        before=m.Transaction.query.count();expires=m.User.query.filter_by(email='carol.d@test.com').one().license.expires
    response=carol.post('/account/license/renew',data=with_csrf(carol,'/account/license/renew',{'years':years}))
    assert response.status_code==400
    with m.app.app_context():
        assert m.Transaction.query.count()==before
        assert m.User.query.filter_by(email='carol.d@test.com').one().license.expires==expires

@pytest.mark.parametrize('day',['2026-10-04','2026-10-03','2026-01-01','bad'])
def test_invalid_appointment_day(client,day):
    response=client.post('/appointments/new',data=with_csrf(client,'/appointments/new',dict(step='2',office='alexandria',service='REAL ID',date=day)))
    assert response.status_code==400

@pytest.mark.parametrize('patch',[{'service':'fake'},{'time':'03:00 AM'},{'date':'bad'},{'email':'a@'},{'office':'fake'}])
def test_appointment_cannot_bypass_validation(client,patch):
    data=dict(step='3',office='alexandria',service='REAL ID',date='2026-10-06',time='8:00 AM',name='Test User',email='t@example.com');data.update(patch)
    with m.app.app_context():before=m.Appointment.query.count()
    response=client.post('/appointments/new',data=with_csrf(client,'/appointments/new',data))
    assert response.status_code==400
    with m.app.app_context():assert m.Appointment.query.count()==before

@pytest.mark.parametrize('data',[{'record_type':'bad'},{'delivery':'bad'}])
def test_invalid_record_options(alice,data):
    response=alice.post('/account/records',data=with_csrf(alice,'/account/records',data))
    assert response.status_code==400


def test_slots_have_exact_twenty_minute_intervals(client):
    response=client.post('/appointments/new',data=with_csrf(client,'/appointments/new',dict(step='2',office='alexandria',service='REAL ID',date='2026-10-06')))
    assert b'8:20 AM' in response.data
    assert b'8:19 AM' not in response.data


def test_every_correct_answer_is_selectable():
    with m.app.app_context():
        for q in m.QuizQuestion.query:
            answers=q.answers_list()
            assert all(a['text'].strip() for a in answers)
            assert q.correct in {str(a['value']) for a in answers}, q.qid
        traffic=m.QuizQuestion.query.filter_by(question='Traffic signals apply to:').one()
        assert traffic.correct == '4'
        radar=m.QuizQuestion.query.filter_by(question='It is illegal to use a radar detector in Virginia.').one()
        assert radar.correct == '1'


@pytest.mark.parametrize('path',['/news','/forms','/vehicles/license-plates/search'])
def test_invalid_page_number_does_not_crash(client,path):
    assert client.get(path+'?pg=invalid').status_code==200


def test_practice_attempt_preserves_answers_and_computed_score(client):
    import json
    with m.app.app_context():
        qs=m.QuizQuestion.query.filter_by(section='2').order_by(m.QuizQuestion.id).limit(10).all()
        payload={f'q_{q.id}':q.correct for q in qs}
        before=m.QuizAttempt.query.count()
    response=client.post('/licenses-ids/exams/practice-exam/2/grade', data=with_csrf(client,'/licenses-ids/exams/practice-exam/2',payload))
    assert response.status_code==200
    with m.app.app_context():
        assert m.QuizAttempt.query.count()==before+1
        attempt=m.QuizAttempt.query.order_by(m.QuizAttempt.id.desc()).first()
        assert (attempt.correct_count,attempt.total,attempt.percent,attempt.passed)==(10,10,100,True)
        assert len(json.loads(attempt.answers))==10


@pytest.mark.parametrize('path',['/account/license/renew','/account/license/replace'])
def test_expired_credential_requires_office_review(carol,path):
    with m.app.app_context():
        lic=m.UserLicense.query.filter_by(user_id=3).one();old=lic.expires;lic.expires='2025-08-02';m.db.session.commit()
    try:
        assert carol.get(path).status_code==400
    finally:
        with m.app.app_context():
            m.UserLicense.query.filter_by(user_id=3).one().expires=old;m.db.session.commit()
