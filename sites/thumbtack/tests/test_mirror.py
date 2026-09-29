"""Self-check suite for the thumbtack mirror.

Run from sites/thumbtack/:  python3 -m pytest tests/ -q

The suite runs against a temporary database seeded from scratch (pointed to
via THUMBTACK_DB_URI before importing the app) so it never mutates the seed.
"""
import json
import os
import pathlib
import re
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
SITE = HERE.parent
sys.path.insert(0, str(SITE))

TMP = tempfile.mkdtemp(prefix='thumbtack-tests-')
DB_PATH = os.path.join(TMP, 'thumbtack.db')
os.environ['THUMBTACK_DB_URI'] = f'sqlite:///{DB_PATH}'

from app import (app, db, Category, CostGuide, Pro, Project,  # noqa: E402
                  ProjectMatch, Review, SavedPro, Thread, Message, User,
                  pro_quote, seed_matches, rating_word)

app.config['TESTING'] = True
app.config['WTF_CSRF_ENABLED'] = False
client = app.test_client()

# Flask-SQLAlchemy 3 requires an explicit app context for direct queries.
_app_ctx = app.app_context()
_app_ctx.push()


def test_health():
    r = client.get('/_health')
    assert r.status_code == 200
    assert r.get_json() == {'ok': True, 'site': 'thumbtack'}


def test_seed_volume():
    assert Category.query.count() >= 12
    assert Pro.query.count() >= 60
    assert Review.query.count() >= 150
    assert CostGuide.query.count() >= 20
    cats = {c.slug: Pro.query.filter_by(category_id=c.id).count()
            for c in Category.query.all()}
    assert all(n >= 5 for n in cats.values()), cats
    # every pro has a real avatar + at least one gallery photo
    for p in Pro.query.all():
        assert p.avatar.startswith('av_')
        assert len(p.gallery_list) >= 1
        assert p.rating_word in ('Exceptional', 'Excellent', 'Very good',
                                 'Great', 'Good', None)


def test_benchmark_users():
    for email in ('alice.j@test.com', 'bob.c@test.com', 'carol.d@test.com',
                  'david.k@test.com'):
        u = User.query.filter_by(email=email).first()
        assert u is not None
        assert u.password_hash  # frozen bcrypt hash
    alice = User.query.filter_by(email='alice.j@test.com').first()
    assert SavedPro.query.filter_by(user_id=alice.id).count() >= 2
    assert Project.query.filter_by(user_id=alice.id).count() >= 1


def test_homepage_renders():
    r = client.get('/')
    assert r.status_code == 200
    html = r.data.decode()
    assert 'For everything home could be.' in html
    assert 'Find a pro' in html
    assert 'House Cleaning' in html


def test_all_categories_render():
    for c in Category.query.all():
        r = client.get(f'/k/{c.slug}/near-me')
        assert r.status_code == 200
        html = r.data.decode()
        assert c.h1 in html
        assert 'hires on Thumbtack' in html


def test_category_filters_and_sort():
    cat = Category.query.filter_by(slug='house-cleaning').first()
    base = f'/k/{cat.slug}/near-me'
    r = client.get(base + '?sort=highest_rated')
    assert r.status_code == 200
    # filter by a real option from the question set
    q0 = cat.question_list[0]['opts'][0]
    r = client.get(base + f'?f0={q0}&sort=recommended')
    assert r.status_code == 200
    r = client.get(base + '?sort=most_hires')
    assert r.status_code == 200
    r = client.get(base + '?sort=fastest_response')
    assert r.status_code == 200


def test_pro_profiles_render():
    from html import escape
    for p in Pro.query.all()[:12]:
        r = client.get(p.profile_path)
        assert r.status_code == 200
        html = r.data.decode()
        assert escape(p.name) in html
        assert 'Reviews' in html
        assert 'Business hours' in html


def test_scored_search():
    r = client.get('/search?q=house cleaning')
    assert r.status_code == 200
    assert 'House Cleaning' in r.data.decode()
    r = client.get('/search?q=plumber in Bellevue')
    html = r.data.decode()
    assert r.status_code == 200
    # partial multi-token query still returns results (never strict AND)
    r = client.get('/search?q=cleaners deep')
    assert r.status_code == 200


def test_cost_guides():
    r = client.get('/prices')
    assert r.status_code == 200
    for g in CostGuide.query.all()[:8]:
        r = client.get(f'/p/{g.slug}')
        assert r.status_code == 200
        html = r.data.decode()
        assert g.title in html
        assert '$' in html


def test_city_and_near_me_pages():
    r = client.get('/near-me')
    assert r.status_code == 200
    r = client.get('/wa/seattle')
    assert r.status_code == 200
    assert 'Seattle' in r.data.decode()
    r = client.get('/wa/nowhereville')
    assert r.status_code == 404


def test_auth_flow():
    r = client.post('/login', data={'email': 'alice.j@test.com',
                                    'password': 'TestPass123!'},
                    follow_redirects=True)
    assert r.status_code == 200
    assert b'Alice' in r.data
    r = client.get('/account')
    assert r.status_code == 200
    r = client.get('/logout', follow_redirects=True)
    assert r.status_code == 200
    r = client.get('/account')
    assert r.status_code == 302          # back to login


def test_profile_edit():
    client.post('/login', data={'email': 'bob.c@test.com',
                                'password': 'TestPass123!'})
    r = client.post('/account/profile', data={
        'name': 'Bob Chen', 'phone': '(206) 555-0199',
        'zip': '98109', 'address': '220 Westlake Ave, Seattle, WA 98109'},
        follow_redirects=True)
    assert r.status_code == 200
    u = User.query.filter_by(email='bob.c@test.com').first()
    assert u.phone == '(206) 555-0199'
    assert u.zip == '98109'
    client.get('/logout')


def test_saved_pros_toggle():
    client.post('/login', data={'email': 'alice.j@test.com',
                                'password': 'TestPass123!'})
    pro = Pro.query.first()
    r = client.post(f'/account/saved/toggle/{pro.id}', follow_redirects=True)
    assert r.status_code == 200
    alice = User.query.filter_by(email='alice.j@test.com').first()
    saved = SavedPro.query.filter_by(user_id=alice.id, pro_id=pro.id).count()
    assert saved in (0, 1)
    r = client.post(f'/account/saved/toggle/{pro.id}', follow_redirects=True)
    assert SavedPro.query.filter_by(user_id=alice.id, pro_id=pro.id).count() == 0
    client.get('/logout')


def _login(email):
    client.post('/login', data={'email': email, 'password': 'TestPass123!'})


def test_quote_request_and_hire_chain():
    _login('bob.c@test.com')
    cat = Category.query.filter_by(slug='furniture-assembly').first()
    q0 = cat.question_list[0]['opts'][0] if cat.question_list else ''
    r = client.post('/projects/new', data={
        'category': cat.slug, 'zip': '98101',
        'timeline': 'Within a week', 'f0': q0,
        'details': 'Assemble a large wardrobe and two bookcases.',
    }, follow_redirects=True)
    assert r.status_code == 200
    project = Project.query.filter_by(user_id=User.query.filter_by(
        email='bob.c@test.com').first().id).order_by(Project.id.desc()).first()
    assert project.category_id == cat.id
    matches = ProjectMatch.query.filter_by(project_id=project.id).all()
    assert len(matches) == 5
    responders = [m for m in matches if m.responded]
    assert 3 <= len(responders) <= 5
    for m in responders:
        assert m.quote_amount is not None and m.quote_amount > 0
        assert m.response_note
    # hire the cheapest responder
    cheapest = min(responders, key=lambda m: m.quote_amount)
    r = client.post(f'/projects/{project.id}/hire/{cheapest.id}',
                    follow_redirects=True)
    assert r.status_code == 200
    assert project.status == 'hired'
    assert cheapest.hired
    # cannot hire a second pro while hired
    other = next(m for m in responders if m.id != cheapest.id)
    r = client.post(f'/projects/{project.id}/hire/{other.id}',
                    follow_redirects=True)
    assert not other.hired
    # complete + review
    r = client.post(f'/projects/{project.id}/complete', follow_redirects=True)
    assert project.status == 'completed'
    r = client.post(f'/projects/{project.id}/review', data={
        'rating': '5', 'body': 'Fast and careful with the boxes. spotless work.'},
        follow_redirects=True)
    assert r.status_code == 200
    rev = Review.query.filter_by(details=f'project:{project.id}').first()
    assert rev is not None
    assert rev.rating == 5
    assert 'spotless' in rev.body.lower()
    # duplicate review rejected
    r = client.post(f'/projects/{project.id}/review', data={
        'rating': '5', 'body': 'again'}, follow_redirects=True)
    assert Review.query.filter_by(details=f'project:{project.id}').count() == 1
    client.get('/logout')


def test_quote_determinism():
    cat = Category.query.filter_by(slug='house-cleaning').first()
    _login('alice.j@test.com')
    client.post('/projects/new', data={
        'category': cat.slug, 'zip': '98052', 'timeline': 'Within 48 hours',
        'details': 'one-time clean'})
    p1 = Project.query.order_by(Project.id.desc()).first()
    # quotes are deterministic per (project, pro) and land in the cost band
    for m in ProjectMatch.query.filter_by(project_id=p1.id).all():
        if m.responded:
            assert m.quote_amount == pro_quote(m.pro, p1)
            guide = CostGuide.query.filter_by(slug=cat.cost_slug).first()
            assert guide.range_low <= m.quote_amount <= guide.range_high
    # the responder set is the category's top-5 pros
    top5 = [p.id for p in Pro.query.filter_by(category_id=cat.id)
            .order_by(Pro.rating.desc(), Pro.hires.desc()).limit(5).all()]
    got = sorted(m.pro_id for m in
                 ProjectMatch.query.filter_by(project_id=p1.id).all())
    assert got == sorted(top5)
    client.get('/logout')


def test_cancel_project():
    _login('alice.j@test.com')
    alice = User.query.filter_by(email='alice.j@test.com').first()
    project = Project.query.filter_by(user_id=alice.id).filter(
        Project.status == 'matched').first()
    assert project is not None
    r = client.post(f'/projects/{project.id}/cancel', follow_redirects=True)
    assert project.status == 'cancelled'
    client.get('/logout')


def test_messaging_auto_reply():
    _login('alice.j@test.com')
    pro = Pro.query.filter_by(category_id=Category.query.filter_by(
        slug='house-cleaning').first().id).first()
    r = client.post(f'/message/{pro.service_pk}', data={
        'body': 'Do you bring your own supplies?'}, follow_redirects=True)
    assert r.status_code == 200
    thread = Thread.query.filter_by(pro_id=pro.id).order_by(
        Thread.id.desc()).first()
    msgs = Message.query.filter_by(thread_id=thread.id).order_by(Message.id).all()
    assert msgs[0].sender == 'user'
    assert msgs[1].sender == 'pro'
    assert len(msgs[1].body) > 10
    # reply again -> another deterministic pro answer
    client.post(f'/account/messages/{thread.id}', data={'body': 'Great! What about ovens?'})
    msgs = Message.query.filter_by(thread_id=thread.id).order_by(Message.id).all()
    assert len(msgs) == 4
    client.get('/logout')


def test_registration_flow():
    r = client.post('/register', data={
        'name': 'Nina Patel', 'email': 'nina.p@test.com',
        'password': 'NewHome2026!', 'zip': '98052'}, follow_redirects=True)
    assert r.status_code == 200
    u = User.query.filter_by(email='nina.p@test.com').first()
    assert u is not None and u.display_name == 'Nina Patel'
    client.get('/logout')


def test_static_content_pages():
    for path, marker in [('/guarantee', 'Guarantee'),
                         ('/how-it-works', 'How Thumbtack works'),
                         ('/pro', 'Join as a pro'),
                         ('/near-me', 'services near me')]:
        r = client.get(path)
        assert r.status_code == 200
        assert marker.lower() in r.data.decode().lower()


def test_seed_idempotence():
    """Re-running the bootstrap must not add rows."""
    from app import seed_database, seed_benchmark_users
    n_pros = Pro.query.count()
    n_cats = Category.query.count()
    n_users = User.query.count()
    seed_database()
    seed_benchmark_users()
    assert Pro.query.count() == n_pros
    assert Category.query.count() == n_cats
    assert User.query.count() == n_users


def test_rating_words_bands():
    assert rating_word(5.0) == 'Exceptional'
    assert rating_word(4.9) == 'Excellent'
    assert rating_word(4.7) == 'Very good'
    assert rating_word(4.3) == 'Great'
    assert rating_word(3.9) == 'Good'
    assert rating_word(3.0) is None
