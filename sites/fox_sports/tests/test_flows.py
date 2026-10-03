"""Flow tests: the interactive surfaces a browser agent must drive —
auth, favorites, the Super 6 contest, search and CSRF enforcement."""
from __future__ import annotations

import re

from app import (Favorite, Super6Entry, Super6Question, Team, User)
from conftest import with_csrf


# --------------------------------------------------------------------- auth --

def test_login_flow(alice_client):
    r = alice_client.get('/favorites')
    assert r.status_code == 200
    body = r.data.decode()
    assert 'Alice' in body


def test_login_requires_valid_credentials(client):
    data = with_csrf(client, '/login', {'email': 'alice.j@test.com',
                                        'password': 'wrong'})
    r = client.post('/login', data=data)
    assert r.status_code == 200
    assert 'Invalid email or password' in r.data.decode()


def test_signup_creates_account(client):
    data = with_csrf(client, '/signup', {
        'name': 'Sam Fan', 'email': 'sam.fan@test.com',
        'password': 'Season2026!'})
    r = client.post('/signup', data=data)
    assert r.status_code in (302, 303)
    user = User.query.filter_by(email='sam.fan@test.com').first()
    assert user is not None and user.name == 'Sam Fan'


def test_signup_validation(client):
    data = with_csrf(client, '/signup', {
        'name': 'Sam Fan', 'email': 'not-an-email', 'password': 'short'})
    r = client.post('/signup', data=data)
    assert r.status_code == 200
    body = r.data.decode()
    assert 'valid email' in body or 'at least 8 characters' in body


def test_favorites_requires_login(client):
    r = client.get('/favorites')
    assert r.status_code == 302


def test_logout(bob_client):
    r = bob_client.get('/logout', follow_redirects=False)
    assert r.status_code == 302
    r2 = bob_client.get('/favorites')
    assert r2.status_code == 302


# ---------------------------------------------------------------- favorites --

def test_follow_team_from_team_page(client):
    # a fresh account keeps the benchmark fixtures untouched
    data = with_csrf(client, '/signup', {
        'name': 'Pat Fan', 'email': 'pat.fan@test.com',
        'password': 'Season2026!'})
    r = client.post('/signup', data=data)
    assert r.status_code in (302, 303)
    user = User.query.filter_by(email='pat.fan@test.com').first()
    assert Favorite.query.filter_by(user_id=user.id).count() == 0
    r = client.get('/nfl/kansas-city-chiefs-team')
    assert r.status_code == 200
    data = with_csrf(client, '/nfl/kansas-city-chiefs-team', {
        'item_type': 'team', 'item_key': 'buffalo-bills',
        'next': '/nfl/kansas-city-chiefs-team'})
    r = client.post('/favorites/toggle', data=data)
    assert r.status_code in (302, 303)
    assert Favorite.query.filter_by(user_id=user.id).count() == 1
    body = client.get('/favorites').data.decode()
    assert 'Buffalo Bills' in body


def test_unfollow_toggles_back(client):
    data = with_csrf(client, '/signup', {
        'name': 'Rae Fan', 'email': 'rae.fan@test.com',
        'password': 'Season2026!'})
    client.post('/signup', data=data)
    user = User.query.filter_by(email='rae.fan@test.com').first()
    data = with_csrf(client, '/nfl/kansas-city-chiefs-team', {
        'item_type': 'team', 'item_key': 'kansas-city-chiefs',
        'next': '/nfl/kansas-city-chiefs-team'})
    r = client.post('/favorites/toggle', data=data)
    assert r.status_code in (302, 303)
    assert Favorite.query.filter_by(user_id=user.id).count() == 1
    data2 = with_csrf(client, '/nfl/kansas-city-chiefs-team', {
        'item_type': 'team', 'item_key': 'kansas-city-chiefs',
        'next': '/nfl/kansas-city-chiefs-team'})
    client.post('/favorites/toggle', data=data2)
    assert Favorite.query.filter_by(user_id=user.id).count() == 0


def test_favorite_unknown_key_rejected(carol_client):
    data = with_csrf(carol_client, '/nfl/kansas-city-chiefs-team', {
        'item_type': 'team', 'item_key': 'no-such-team', 'next': '/'})
    r = carol_client.post('/favorites/toggle', data=data)
    assert r.status_code == 400


def test_fixture_favorite_counts():
    alice = User.query.filter_by(email='alice.j@test.com').first()
    dana = User.query.filter_by(email='dana.k@test.com').first()
    assert Favorite.query.filter_by(user_id=alice.id).count() == 6
    assert Favorite.query.filter_by(user_id=dana.id).count() == 5


# ------------------------------------------------------------------ super 6 --

def test_super6_enter_requires_login(client):
    r = client.get('/fox-super-6/nfl-week-3-pick-6/enter')
    assert r.status_code == 302


def test_super6_full_entry_flow(dana_client):
    questions = Super6Question.query.order_by(Super6Question.order).all()
    data = {}
    r = dana_client.get('/fox-super-6/nfl-week-3-pick-6/enter')
    assert r.status_code == 200
    token = re.search(rb'name="csrf_token"[^>]*value="([^"]+)"', r.data)
    data['csrf_token'] = token.group(1).decode()
    for q in questions:
        data[f'pick-{q.order}'] = q.correct_pick
    r = dana_client.post('/fox-super-6/nfl-week-3-pick-6/submit', data=data)
    assert r.status_code in (302, 303)
    dana = User.query.filter_by(email='dana.k@test.com').first()
    entry = Super6Entry.query.filter_by(user_id=dana.id).order_by(
        Super6Entry.id.desc()).first()
    assert entry.score == 6
    entry_page = dana_client.get(
        f'/fox-super-6/nfl-week-3-pick-6/entries/{entry.id}')
    assert entry_page.status_code == 200
    assert '6 of 6' in entry_page.data.decode()


def test_super6_rejects_invalid_pick(dana_client):
    questions = Super6Question.query.order_by(Super6Question.order).all()
    data = {}
    r = dana_client.get('/fox-super-6/nfl-week-3-pick-6/enter')
    token = re.search(rb'name="csrf_token"[^>]*value="([^"]+)"', r.data)
    data['csrf_token'] = token.group(1).decode()
    for q in questions:
        data[f'pick-{q.order}'] = q.correct_pick
    data['pick-3'] = 'not-a-team'
    r = dana_client.post('/fox-super-6/nfl-week-3-pick-6/submit', data=data)
    assert r.status_code == 400


def test_super6_leaderboard_orders_scores(client):
    r = client.get('/fox-super-6/nfl-week-3-pick-6/leaderboard')
    assert r.status_code == 200
    body = r.data.decode()
    assert '6 / 6' in body
    # Carol Davis (perfect fixture entry) is the leader
    assert 'Carol Davis' in body


def test_super6_entry_requires_login(client):
    r = client.get('/fox-super-6/nfl-week-3-pick-6/entries/1')
    assert r.status_code == 302
    assert '/login' in r.headers.get('Location', '')


def test_super6_entry_private_to_owner(client):
    carol = User.query.filter_by(email='carol.d@test.com').first()
    entry = Super6Entry.query.filter_by(user_id=carol.id).first()
    # another signed-in user is forbidden
    data = with_csrf(client, '/login', {'email': 'alice.j@test.com',
                                        'password': 'TestPass123!'})
    client.post('/login', data=data)
    r = client.get(f'/fox-super-6/nfl-week-3-pick-6/entries/{entry.id}')
    assert r.status_code == 403
    # the owner can view it
    data = with_csrf(client, '/login', {'email': 'carol.d@test.com',
                                        'password': 'TestPass123!'})
    client.post('/login', data=data)
    r2 = client.get(f'/fox-super-6/nfl-week-3-pick-6/entries/{entry.id}')
    assert r2.status_code == 200


# -------------------------------------------------------------------- csrf --

def test_unsigned_post_rejected(client):
    r = client.post('/login', data={'email': 'alice.j@test.com',
                                    'password': 'TestPass123!'})
    assert r.status_code == 400


def test_unsigned_favorites_toggle_rejected(alice_client):
    r = alice_client.post('/favorites/toggle', data={
        'item_type': 'team', 'item_key': 'buffalo-bills'})
    assert r.status_code == 400


# ------------------------------------------------------------------- search --

def test_search_player_hits(client):
    body = client.get('/search?q=Aaron Rodgers').data.decode()
    assert 'Aaron Rodgers' in body


def test_search_story_hits(client):
    body = client.get('/search?q=power rankings').data.decode()
    assert 'Power Rankings' in body


def test_search_partial_query(client):
    body = client.get('/search?q=yankee').data.decode()
    assert 'New York Yankees' in body
