import pytest
from conftest import csrf

@pytest.mark.parametrize('value', ['//example.org/x','https://example.org/','/\\example.org/','/%2fexample.org/','/%0aevil'])
def test_login_return_is_local(client, value):
    a,c=client
    token=csrf(c,'/account/login')
    r=c.post('/account/login',query_string={'next':value},data={'csrf_token':token,'email':'alice.chen@test.com','password':'TestPass123!'})
    assert r.headers['Location']=='/account/'

@pytest.mark.parametrize('field,value', [('quantity','-3'),('quantity','501'),('quantity','abc'),('hours','NaN'),('hours','731'),('currency','bogus')])
def test_invalid_saved_configuration_does_not_write(client,field,value):
    a,c=client;token=csrf(c,'/account/login')
    c.post('/account/login',data={'csrf_token':token,'email':'alice.chen@test.com','password':'TestPass123!'})
    data=dict(csrf_token=token,service='virtual-machines',size='linux-d4sv5-standard',quantity='3',hours='730',region='us-east',currency='usd',name='Invalid')
    data[field]=value
    with a.app.app_context(): before=a.Estimate.query.count()
    assert c.post('/pricing/calculator/save',data=data).status_code==400
    with a.app.app_context(): assert a.Estimate.query.count()==before

def test_storage_explains_actual_tiers(client):
    a,c=client;page=c.get('/pricing/calculator/?service=storage').get_data(as_text=True)
    assert '51,200 GB' in page and '460,800 GB' in page

def test_serverless_is_not_offered_as_a_free_throughput_estimate(client):
    a,c=client
    with a.app.app_context():
        assert a._compute_cosmos_estimate('us-east','serverless',400,25,'no','usd') is None
