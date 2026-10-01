"""End-to-end flows for the dblp mirror (CSRF enabled throughout)."""
import re

from conftest import with_csrf


def test_flow_search_to_author_to_venue(client):
    # publication search -> open first author -> open their venue
    r = client.get('/search/publ?q=attention+is+all+you+need')
    body = r.get_data(as_text=True)
    pid = re.search(r'href="(/pid/[^"]+\.html)"', body)
    assert pid
    r = client.get(pid.group(1))
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    stream = re.search(r'href="(/db/(?:conf|journals)/[^"]+/index\.html)"',
                       body)
    assert stream
    r = client.get(stream.group(1))
    assert r.status_code == 200


def test_flow_watch_and_export(alice):
    # watch an author, watch a venue, then view the watchlist
    r = alice.get('/pid/h/JiaweiHan.html')
    assert r.status_code == 200
    r = alice.post('/account/watchlist/author/add',
                   data=with_csrf(alice, '/pid/h/JiaweiHan.html',
                                  {'pid': 'h/JiaweiHan',
                                   'next': '/pid/h/JiaweiHan.html'}))
    assert r.status_code == 302
    r = alice.get('/db/conf/sigmod/index.html')
    r = alice.post('/account/watchlist/venue/add',
                   data=with_csrf(alice, '/db/conf/sigmod/index.html',
                                  {'stream': 'conf/sigmod',
                                   'next': '/db/conf/sigmod/index.html'}))
    assert r.status_code == 302
    body = alice.get('/account/watchlist').get_data(as_text=True)
    assert 'Jiawei Han' in body
    assert 'ACM SIGMOD Conference' in body


def test_flow_save_search_rerun(bob):
    r = bob.post('/account/saved-searches/add',
                 data=with_csrf(bob, '/search/publ?q=query+optimization',
                                {'query': 'query optimization',
                                 'search_type': 'publ',
                                 'next': '/search/publ?q=query+optimization'}))
    assert r.status_code == 302
    body = bob.get('/account/saved-searches').get_data(as_text=True)
    run = re.search(r'href="(/search/publ\?q=[^"]+)"', body)
    assert run
    r = bob.get(run.group(1))
    assert r.status_code == 200
    assert 'found ' in r.get_data(as_text=True)


def test_flow_record_to_library_to_bib(dana):
    r = dana.get('/search/publ?q=question+answering')
    body = r.get_data(as_text=True)
    key = re.search(r'id="((?:conf|journals)/[^"]+)"', body)
    assert key
    r = dana.get(f'/rec/{key.group(1)}.html')
    assert r.status_code == 200
    r = dana.post('/account/papers/add',
                  data=with_csrf(dana, f'/rec/{key.group(1)}.html',
                                 {'key': key.group(1),
                                  'collection': 'QA papers',
                                  'next': f'/rec/{key.group(1)}.html'}))
    assert r.status_code == 302
    r = dana.get('/account/papers/export.bib?collection=QA%20papers')
    bib = r.get_data(as_text=True)
    assert 'DBLP:' in bib


def test_flow_edition_toc_to_record(client):
    r = client.get('/db/conf/sigmod/index.html')
    body = r.get_data(as_text=True)
    toc = re.search(r'href="(/db/conf/sigmod/[^"]+\.html)"', body)
    assert toc and 'index' not in toc.group(1)
    r = client.get(toc.group(1))
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    rec = re.search(r'href="(/rec/[^"]+\.html)"', body)
    assert rec
    r = client.get(rec.group(1))
    assert r.status_code == 200


def test_flow_register_watch_export(client):
    # a brand-new user can register, watch, save and export
    r = client.post('/authn/register',
                    data=with_csrf(client, '/authn/register',
                                   {'email': 'frank.m@test.com',
                                    'display_name': 'Frank Miller',
                                    'password': 'Sup3rSecret!'}))
    assert r.status_code == 302
    r = client.get('/pid/h/JiaweiHan.html')
    client.post('/account/watchlist/author/add',
                data=with_csrf(client, '/pid/h/JiaweiHan.html',
                               {'pid': 'h/JiaweiHan',
                                'next': '/pid/h/JiaweiHan.html'}))
    body = client.get('/account/watchlist').get_data(as_text=True)
    assert 'Jiawei Han' in body
    # empty library export is a valid empty file
    r = client.get('/account/papers/export.bib')
    assert r.status_code == 200
