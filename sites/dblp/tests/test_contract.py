"""Contract tests for the dblp mirror (CSRF enabled throughout)."""
import json
import re

from conftest import with_csrf


# ------------------------------------------------------------------ health --

def test_health(client):
    r = client.get('/_health')
    assert r.status_code == 200
    data = r.get_json()
    assert data['ok'] is True
    assert data['publications'] > 5000
    assert data['authors'] > 1000
    assert data["venues"] == 21
    assert data['users'] == 4


# -------------------------------------------------------------------- home --

def test_home_renders(client):
    r = client.get('/')
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert 'Welcome to dblp' in body
    assert 'dblp blog' in body
    assert '8,779,805' in body          # upstream publications counter
    assert '2026-09-21' in body         # latest captured news item
    assert 'captured from' in body      # mirror declaration


# ------------------------------------------------------------------ search --

def test_publ_search_attention(client):
    r = client.get('/search/publ?q=attention+is+all+you+need')
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert 'found ' in body
    assert 'Attention' in body


def test_publ_search_prefix_semantics(client):
    r = client.get('/search/publ?q=sig')
    body = r.get_data(as_text=True)
    assert 'found ' in body
    # prefix search: 'sig' matches titles starting with 'sig' and words
    # starting with 'sig' inside titles
    assert re.search(r'class="title">[^<]*[Ss]ig', body)


def test_publ_search_exact_word(client):
    loose = client.get('/search/publ?q=graph')
    exact = client.get('/search/publ?q=graph$')
    assert 'found ' in loose.get_data(as_text=True)
    assert 'found ' in exact.get_data(as_text=True)
    n_loose = _count(loose.get_data(as_text=True))
    n_exact = _count(exact.get_data(as_text=True))
    # exact-word matches are a strict subset of prefix matches
    assert n_exact <= n_loose
    body = exact.get_data(as_text=True)
    for title in re.findall(r'class="title">([^<]+)<', body):
        assert re.search(r'(^|\s)[Gg]raph(\s|$|[,.;:])', title), title


def _count(body):
    m = re.search(r'found ([\d,]+) matches', body)
    assert m, body[:500]
    return int(m.group(1).replace(',', ''))


def test_publ_search_or_and_year_filter(client):
    r = client.get('/search/publ?q=graph|network&year=2024')
    body = r.get_data(as_text=True)
    assert 'found ' in body
    for y in re.findall(r'\((\d{4})\)</cite>', body):
        assert y == '2024'


def test_publ_search_pagination(client):
    r1 = client.get('/search/publ?q=learning&h=30&f=0')
    b1 = r1.get_data(as_text=True)
    total = _count(b1)
    assert total > 30
    assert '[next &gt;&gt;]' in b1
    r2 = client.get('/search/publ?q=learning&h=30&f=30')
    b2 = r2.get_data(as_text=True)
    keys1 = set(re.findall(r'id="((?:conf|journals)/[^"]+)"', b1))
    keys2 = set(re.findall(r'id="((?:conf|journals)/[^"]+)"', b2))
    assert keys1 and keys2
    assert not (keys1 & keys2)


def test_combined_search_sections(client):
    r = client.get('/search?q=sigmod')
    body = r.get_data(as_text=True)
    assert 'Author search results' in body
    assert 'Venue search results' in body
    assert 'Publication search results' in body
    assert 'ACM SIGMOD Conference' in body


def test_author_search(client):
    r = client.get('/search/author?q=jiawei+han')
    body = r.get_data(as_text=True)
    assert 'Jiawei Han' in body
    assert '/pid/h/JiaweiHan.html' in body


def test_author_search_exact_word(client):
    # dblp search is case-insensitive across the board, including the
    # exact-word operator: 'han$' must match mixed-case stored names
    # ('Jiawei Han'), not only already-lowercase ones
    r = client.get('/search/author?q=han$')
    body = r.get_data(as_text=True)
    m = re.search(r'All (\d+) matches', body)
    assert m and int(m.group(1)) > 500
    assert '[next &gt;&gt;]' in body   # results span several pages
    # the exact-word operator excludes prefix-only names like 'Handel'
    r2 = client.get('/search/author?q=handel$')
    body2 = r2.get_data(as_text=True)
    m2 = re.search(r'All (\d+) matches', body2)
    assert not m2 or int(m2.group(1)) < int(m.group(1))


def test_author_search_no_leak(client):
    r = client.get('/search/author?q=zzzznotaperson')
    body = r.get_data(as_text=True)
    assert 'no matches' in body


def test_venue_search(client):
    r = client.get('/search/venue?q=sigmod')
    body = r.get_data(as_text=True)
    assert 'All ' in body
    assert 'SIGMOD' in body


def test_search_requires_query(client):
    r = client.get('/search/publ')
    assert 'Please enter a search query' in r.get_data(as_text=True)


# ------------------------------------------------------------ author pages --

def test_author_profile(client):
    r = client.get('/pid/h/JiaweiHan.html')
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert 'Jiawei Han' in body
    assert 'Person information' in body
    assert 'Coauthor Index' in body
    assert 'University of Illinois' in body


def test_author_profile_stats_and_decades(client):
    r = client.get('/pid/h/JiaweiHan.html')
    body = r.get_data(as_text=True)
    assert 'records by year' in body
    assert re.search(r'\d{4} \u2013 \d{4}', body) or '– today' in body


def test_author_404(client):
    r = client.get('/pid/xx/NobodyHere.html')
    assert r.status_code == 404


# ------------------------------------------------------------- venue pages --

def test_browse_conferences(client):
    r = client.get('/db/conf/')
    body = r.get_data(as_text=True)
    assert 'ACM SIGMOD Conference' in body
    assert 'Conference on Neural Information Processing Systems' in body


def test_browse_journals(client):
    r = client.get('/db/journals/')
    body = r.get_data(as_text=True)
    assert 'ACM Transactions on Database Systems' in body
    assert 'Proceedings of the VLDB Endowment' in body


def test_venue_page_sigmod(client):
    r = client.get('/db/conf/sigmod/index.html')
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert 'ACM SIGMOD Conference' in body
    assert 'Venue statistics' in body
    assert 'records by year' in body
    assert 'frequent authors' in body
    assert 'Editions' in body


def test_venue_headline_shows_abbr_once(client):
    # the venue name already embeds the abbreviation; the headline must not
    # append it a second time (upstream shows it exactly once)
    r = client.get('/db/conf/sigmod/index.html')
    body = r.get_data(as_text=True)
    assert '<h1>ACM SIGMOD Conference (SIGMOD)</h1>' in body
    assert '(SIGMOD) (SIGMOD)' not in body


def test_search_venue_hits_show_abbr_once(client):
    for path in ('/search?q=sigmod', '/search/venue?q=sigmod'):
        body = client.get(path).get_data(as_text=True)
        assert 'ACM SIGMOD Conference (SIGMOD)' in body
        assert '(SIGMOD) (SIGMOD)' not in body


def test_edition_headline_uses_upstream_short_display(client):
    # conference toc pages show the upstream short display name, not the
    # full proceedings title
    r = client.get('/db/conf/sigmod/sigmod2022.html')
    body = r.get_data(as_text=True)
    assert '<h1>ACM SIGMOD Conference 2022: Philadelphia, PA, USA</h1>' in body
    assert "SIGMOD '22: International Conference" not in body
    # journal volume pages keep the full volume title (upstream does too)
    r = client.get('/db/journals/pvldb/pvldb19.html')
    body = r.get_data(as_text=True)
    assert '<h1>Proceedings of the VLDB Endowment, Volume 19</h1>' in body


def test_search_form_submits_to_current_kind(client):
    # upstream kind search pages submit the search box back to their own
    # kind; every other page submits to the combined search
    for path, action in (
            ('/search/publ?q=gnn', '/search/publ'),
            ('/search/author?q=han', '/search/author'),
            ('/search/venue?q=sigmod', '/search/venue'),
            ('/', '/search'),
            ('/db/conf/sigmod/index.html', '/search')):
        body = client.get(path).get_data(as_text=True)
        m = re.search(r'id="completesearch-form" action="([^"]+)"', body)
        assert m, path
        assert m.group(1) == action, (path, m.group(1))


def test_search_history_dedupes_combined_to_kind_chain(dana):
    # one search action = one history row: the kind page reached from the
    # combined results page for the same query (the "all N matches"
    # click-through) must not record a second row
    dana.get('/search?q=oblivious+chase')
    dana.get('/search/publ?q=oblivious+chase',
             headers={'Referer': 'http://localhost/search?q=oblivious+chase'})
    body = dana.get('/account/history').get_data(as_text=True)
    assert body.count('>oblivious chase<') == 1
    # a fresh search action with the same text as an earlier row still
    # records — a new action is a new search, not a duplicate
    dana.get('/search?q=oblivious+chase')
    body = dana.get('/account/history').get_data(as_text=True)
    assert body.count('>oblivious chase<') == 2
    # a different query still records normally
    dana.get('/search?q=graph')
    body = dana.get('/account/history').get_data(as_text=True)
    assert body.count('>graph<') >= 1


def test_venue_page_journal(client):
    r = client.get('/db/journals/pvldb/index.html')
    body = r.get_data(as_text=True)
    assert 'Proceedings of the VLDB Endowment' in body
    assert 'Volumes' in body
    assert 'Volume 19' in body


def test_edition_page(client):
    r = client.get('/db/conf/sigmod/sigmod2022.html')
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert 'Table of contents' in body
    assert 'records' in body


def test_venue_404(client):
    r = client.get('/db/conf/doesnotexist/index.html')
    assert r.status_code == 404


# ------------------------------------------------------------ record pages --

def test_record_page_and_bibtex(client):
    r = client.get('/rec/journals/pacmmod/0001LW24.html')
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert 'Relational Algorithms for Top-k Query Evaluation' in body
    assert '@article{DBLP:journals/pacmmod/0001LW24,' in body
    assert 'biburl' in body
    assert 'bibsource' in body


def test_record_bib_download(client):
    r = client.get('/rec/journals/pacmmod/0001LW24.bib')
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert body.startswith('@article{DBLP:journals/pacmmod/0001LW24,')
    assert 'attachment' in r.headers['Content-Disposition']


def test_record_404(client):
    r = client.get('/rec/conf/nowhere/Nothing.html')
    assert r.status_code == 404


# --------------------------------------------------------------- account ---

def test_login_logout_flow(client):
    r = client.post('/authn/login',
                    data=with_csrf(client, '/authn/login',
                                   {'email': 'alice.j@test.com',
                                    'password': 'TestPass123!'}))
    assert r.status_code == 302
    r = client.get('/account')
    assert r.status_code == 200
    assert 'Alice Johnson' in r.get_data(as_text=True)
    r = client.post('/authn/logout',
                    data=with_csrf(client, '/account',
                                   {'csrf_token': _token(client, '/account')}))
    assert r.status_code == 302
    r = client.get('/account')
    assert r.status_code == 302  # back to login


def _token(client, source):
    r = client.get(source)
    m = re.search(rb'name="csrf_token"[^>]*value="([^"]+)"', r.data)
    assert m
    return m.group(1).decode()


def test_login_bad_credentials(client):
    r = client.post('/authn/login',
                    data=with_csrf(client, '/authn/login',
                                   {'email': 'alice.j@test.com',
                                    'password': 'wrong'}))
    assert r.status_code == 200
    assert 'Invalid credentials' in r.get_data(as_text=True)


def test_register_flow(client):
    r = client.post('/authn/register',
                    data=with_csrf(client, '/authn/register',
                                   {'email': 'eve.n@test.com',
                                    'display_name': 'Eve Nguyen',
                                    'password': 'Sup3rSecret!'}))
    assert r.status_code == 302
    r = client.get('/account')
    assert 'Eve Nguyen' in r.get_data(as_text=True)


def test_register_duplicate_email(client):
    r = client.post('/authn/register',
                    data=with_csrf(client, '/authn/register',
                                   {'email': 'alice.j@test.com',
                                    'display_name': 'Fake Alice',
                                    'password': 'Sup3rSecret!'}))
    assert 'already registered' in r.get_data(as_text=True)


def test_csrf_required(client):
    # POST without a token must fail (CSRF stays enabled in the suite)
    r = client.post('/authn/login', data={'email': 'x', 'password': 'y'})
    assert r.status_code == 400


def test_watchlist_flow(alice):
    # Alice's seeded watchlist: 3 nips authors + nips/icml venues
    r = alice.get('/account/watchlist')
    body = r.get_data(as_text=True)
    assert 'Watched authors' in body
    assert 'Watched venues' in body
    assert 'records in this mirror' in body
    # add a new author from a profile page
    r = alice.get('/pid/h/JiaweiHan.html')
    pid = re.search(r'name="pid" value="([^"]+)"', r.get_data(as_text=True))
    assert pid
    r = alice.post('/account/watchlist/author/add',
                   data=with_csrf(alice, '/pid/h/JiaweiHan.html',
                                  {'pid': pid.group(1),
                                   'next': '/pid/h/JiaweiHan.html'}))
    assert r.status_code == 302
    body = alice.get('/account/watchlist').get_data(as_text=True)
    assert body.count('remove') >= 4
    # remove it again
    r = alice.post('/account/watchlist/author/remove',
                   data=with_csrf(alice, '/account/watchlist',
                                  {'pid': pid.group(1)}))
    assert r.status_code == 302


def test_watchlist_venue_flow(bob):
    r = bob.get('/account/watchlist')
    body = r.get_data(as_text=True)
    assert 'ACM SIGMOD Conference' in body
    assert 'Proceedings of the VLDB Endowment' in body
    # remove one venue
    vid = re.search(r'name="venue_id" value="(\d+)"', body)
    r = bob.post('/account/watchlist/venue/remove',
                 data=with_csrf(bob, '/account/watchlist',
                                 {'venue_id': vid.group(1)}))
    assert r.status_code == 302
    body2 = bob.get('/account/watchlist').get_data(as_text=True)
    assert body2.count('added 2026-09-02') < body.count('added 2026-09-02')


def test_saved_searches_flow(alice):
    r = alice.get('/account/saved-searches')
    body = r.get_data(as_text=True)
    assert 'graph neural network' in body
    assert 'save this search' not in body  # only on search pages
    # add one from a search page
    r = alice.post('/account/saved-searches/add',
                   data=with_csrf(alice, '/search/publ?q=graph',
                                  {'query': 'graph', 'search_type': 'publ',
                                   'next': '/search/publ?q=graph'}))
    assert r.status_code == 302
    body = alice.get('/account/saved-searches').get_data(as_text=True)
    assert 'run' in body
    # delete it
    sid = re.findall(r'/account/saved-searches/(\d+)/delete', body)[-1]
    r = alice.post(f'/account/saved-searches/{sid}/delete',
                   data=with_csrf(alice, '/account/saved-searches', {}))
    assert r.status_code == 302


def test_saved_papers_flow(carol):
    r = carol.get('/account/papers')
    body = r.get_data(as_text=True)
    assert 'My Library' in body
    # save a record from its page
    r = carol.get('/rec/journals/pacmmod/0001LW24.html')
    assert r.status_code == 200
    r = carol.post('/account/papers/add',
                   data=with_csrf(carol, '/rec/journals/pacmmod/0001LW24.html',
                                  {'key': 'journals/pacmmod/0001LW24',
                                   'collection': 'Reading pile',
                                   'next': '/rec/journals/pacmmod/0001LW24.html'}))
    assert r.status_code == 302
    body = carol.get('/account/papers').get_data(as_text=True)
    assert 'Reading pile' in body
    # export as BibTeX
    r = carol.get('/account/papers/export.bib?collection=Reading%20pile')
    assert r.status_code == 200
    bib = r.get_data(as_text=True)
    assert 'Relational Algorithms for Top-k Query Evaluation' in bib
    assert bib.count('@') >= 1


def test_search_history_flow(dana):
    # seeded history rows exist
    r = dana.get('/account/history')
    body = r.get_data(as_text=True)
    assert 'question answering' in body
    assert 'retrieval' in body
    # running a search records a new history row
    dana.get('/search/publ?q=summarization')
    body = dana.get('/account/history').get_data(as_text=True)
    assert body.count('summarization') >= 2
    # clear history
    r = dana.post('/account/history/clear',
                  data=with_csrf(dana, '/account/history', {}))
    assert r.status_code == 302
    body = dana.get('/account/history').get_data(as_text=True)
    assert 'search history is empty' in body


def test_profile_edit(alice):
    r = alice.post('/account/profile',
                   data=with_csrf(alice, '/account/profile',
                                  {'display_name': 'Alice J. Johnson',
                                   'affiliation': 'Stanford University',
                                   'research_interests': 'GNNs, transformers'}))
    assert r.status_code == 302
    body = alice.get('/account/profile').get_data(as_text=True)
    assert 'Alice J. Johnson' in body
    assert 'GNNs, transformers' in body


def test_account_requires_login(client):
    r = client.get('/account')
    assert r.status_code == 302
    r = client.get('/account/papers')
    assert r.status_code == 302
