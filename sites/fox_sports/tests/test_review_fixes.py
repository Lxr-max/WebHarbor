import pytest
from conftest import with_csrf

@pytest.mark.parametrize('value',['//example.org/x','https://example.org/','/\\example.org/','/%2fexample.org/','/%0aevil'])
def test_login_return_is_local(client,value):
    data=with_csrf(client,'/login',{'email':'bob.c@test.com','password':'TestPass123!'})
    r=client.post('/login',query_string={'next':value},data=data)
    assert r.headers['Location']=='/'

def test_driver_follow_and_unfollow(bob_client):
    c=bob_client
    assert c.get('/nascar/drivers/2').status_code==200
    data=with_csrf(c,'/nascar/drivers/2',{'item_type':'driver','item_key':'2','next':'//example.org/'})
    r=c.post('/favorites/toggle',data=data)
    assert r.headers['Location']=='/favorites'
    assert b'Denny Hamlin' in c.get('/favorites').data
    c.post('/favorites/toggle',data=data)
    assert b'Denny Hamlin' not in c.get('/favorites').data

def test_unknown_driver_cannot_be_followed(bob_client):
    c=bob_client;data=with_csrf(c,'/nascar/drivers/2',{'item_type':'driver','item_key':'99999'})
    assert c.post('/favorites/toggle',data=data).status_code==400

def test_my_entry_links_to_owned_contest(alice_client):
    html=alice_client.get('/fox-super-6').get_data(as_text=True)
    from bs4 import BeautifulSoup
    soup=BeautifulSoup(html,'html.parser')
    link=next(a for a in soup.select('a') if a.get_text(strip=True)=='View entry')
    assert link['href'] != '#'
    assert alice_client.get(link['href']).status_code==200
    assert 'NFL Week 3 Pick 6' in link.find_parent('tr').get_text()
