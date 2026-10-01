"""Contract tests: every route renders, seeded data is coherent, and no
answer-destroying shortcuts exist (no answer keys in the agent-facing
task file, upstream-shaped URLs resolve)."""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

import app as fs_app
from app import (Episode, Favorite, Game, HomeTile, Personality, Player,
                 PlayerNews, PlayerStat, Show, Story, Super6Contest,
                 Super6Entry, Super6Question, Team, User)

SITE = Path(__file__).resolve().parents[1]


# ------------------------------------------------------------- core surfaces --

def test_home_renders(client):
    r = client.get('/')
    assert r.status_code == 200
    body = r.data.decode()
    assert 'Top Games' in body
    assert 'FOX SPORTS' in body.upper()


def test_scores_hub_lists_leagues(client):
    r = client.get('/scores')
    assert r.status_code == 200
    body = r.data.decode()
    for name in ('NFL', 'MLB', 'College Football'):
        assert name in body


def test_nfl_standings_eight_divisions(client):
    r = client.get('/nfl/standings')
    assert r.status_code == 200
    body = r.data.decode()
    for division in ('AFC EAST', 'AFC NORTH', 'AFC SOUTH', 'AFC WEST',
                     'NFC EAST', 'NFC NORTH', 'NFC SOUTH', 'NFC WEST'):
        assert division in body
    assert 'Buffalo Bills' in body


def test_mlb_standings_six_divisions(client):
    r = client.get('/mlb/standings')
    assert r.status_code == 200
    body = r.data.decode()
    for division in ('AL EAST', 'AL CENTRAL', 'AL WEST',
                      'NL EAST', 'NL CENTRAL', 'NL WEST'):
        assert division in body
    # playoff clinch markers are rendered
    assert 'Z' in body and 'X' in body


def test_cfb_poll_top_25(client):
    r = client.get('/college-football/standings')
    assert r.status_code == 200
    body = r.data.decode()
    assert 'Texas' in body
    assert 'first-place votes' in body


def test_scoreboard_lists_finals_and_upcoming(client):
    r = client.get('/scores/nfl')
    assert r.status_code == 200
    body = r.data.decode()
    assert 'FINAL' in body
    assert 'game-boxscore' in body


def test_boxscore_final_has_score_and_facts(client):
    from app import db
    game = (Game.query.filter_by(league='nfl', status='final')
            .order_by(Game.date_iso.desc()).first())
    r = client.get(f'/nfl/{game.slug}')
    assert r.status_code == 200
    body = r.data.decode()
    assert 'FINAL' in body
    assert str(game.away_score) in body and str(game.home_score) in body


def test_boxscore_upcoming_has_odds_and_leaders(client):
    from app import db
    game = (Game.query.filter_by(league='nfl', status='scheduled')
            .filter(Game.spread.isnot(None))
            .order_by(Game.date_iso).first())
    r = client.get(f'/nfl/{game.slug}')
    assert r.status_code == 200
    body = r.data.decode()
    assert 'Matchup Odds' in body
    assert 'Team Leaders' in body


def test_mlb_final_boxscore_innings(client):
    game = (Game.query.filter_by(league='mlb', status='final')
            .order_by(Game.date_iso.desc()).first())
    r = client.get(f'/mlb/{game.slug}')
    assert r.status_code == 200
    body = r.data.decode()
    assert 'Box Score' in body
    assert 'Key Players' in body
    assert 'Key Plays' in body


def test_team_page_news_and_next_game(client):
    r = client.get('/nfl/kansas-city-chiefs-team')
    assert r.status_code == 200
    body = r.data.decode()
    assert 'Next Game' in body
    assert 'Player News' in body


def test_roster_lists_groups(client):
    r = client.get('/nfl/kansas-city-chiefs-team-roster')
    assert r.status_code == 200
    body = r.data.decode()
    assert 'OFFENSE' in body
    assert 'DEFENSE' in body
    assert '-player' in body


def test_player_page_bio(client):
    r = client.get('/nfl/patrick-mahomes-ii-player')
    assert r.status_code == 200
    body = r.data.decode()
    assert 'Patrick Mahomes' in body
    assert 'College' in body


def test_stat_leaders_page(client):
    r = client.get('/nfl/players')
    assert r.status_code == 200
    body = r.data.decode()
    assert 'Passing Yards' in body
    assert 'Rushing Yards' in body


def test_story_page_body(client):
    story = Story.query.filter_by(
        slug='2026-nfl-power-rankings-week-4').first()
    r = client.get(f'/stories/{story.league}/{story.slug}')
    assert r.status_code == 200
    body = r.data.decode()
    assert 'Miami Dolphins' in body
    assert 'Stat To Know' in body or 'Stat to Know' in body


def test_shows_and_episodes(client):
    r = client.get('/shows')
    assert r.status_code == 200
    r2 = client.get('/shows/the-herd-with-colin-cowherd')
    assert r2.status_code == 200
    assert 'Episodes' in r2.data.decode()


def test_personality_page(client):
    r = client.get('/personalities/colin-cowherd')
    assert r.status_code == 200
    assert 'Videos' in r.data.decode()


def test_betting_hub_has_odds(client):
    r = client.get('/betting')
    assert r.status_code == 200
    body = r.data.decode()
    assert 'O/U' in body


def test_nascar_and_ufc_pages(client):
    assert client.get('/nascar/cup-series/standings').status_code == 200
    assert client.get('/ufc').status_code == 200
    body = client.get('/nascar/cup-series/standings').data.decode()
    assert 'Kyle Larson' in body


def test_watch_page(client):
    r = client.get('/watch')
    assert r.status_code == 200
    assert 'Live Now' in r.data.decode()


def test_search_teams_and_players(client):
    r = client.get('/search?q=chiefs')
    assert r.status_code == 200
    body = r.data.decode()
    assert 'Kansas City Chiefs' in body
    r2 = client.get('/search?q=wild card')
    assert 'GAME' in r2.data.decode() or 'game-boxscore' in r2.data.decode()


def test_unknown_league_404(client):
    assert client.get('/nhl').status_code == 404
    assert client.get('/nfl/not-a-real-page').status_code == 404


# ------------------------------------------------------------ data contract --

def test_seed_counts():
    assert Team.query.count() == 214
    assert Team.query.filter_by(league='nfl').count() == 32
    assert Team.query.filter_by(league='mlb').count() == 30
    assert Game.query.count() >= 300
    assert Game.query.filter(Game.status == 'final').count() >= 200
    assert Player.query.count() >= 3000
    assert Story.query.count() == 120
    assert Show.query.count() >= 10
    assert User.query.count() == 4
    assert Favorite.query.count() == 23


def test_every_game_has_two_known_teams():
    teams = {t.slug for t in Team.query.all()}
    for game in Game.query.all():
        assert game.away_team in teams, game.slug
        assert game.home_team in teams, game.slug


def test_super6_contest_fixture():
    contest = Super6Contest.query.filter_by(slug='nfl-week-3-pick-6').first()
    assert contest is not None
    questions = Super6Question.query.filter_by(contest_id=contest.id) \
        .order_by(Super6Question.order).all()
    assert len(questions) == 6
    entries = Super6Entry.query.filter_by(contest_id=contest.id).all()
    assert len(entries) == 4
    # Carol's perfect entry leads the fixture leaderboard
    scores = sorted((e.score for e in entries), reverse=True)
    assert scores[0] == 6
    for q in questions:
        game = Game.query.filter_by(slug=q.game_slug).first()
        assert game is not None
        winner = game.away_team if game.away_score > game.home_score \
            else game.home_team
        assert q.correct_pick == winner


def test_benchmark_password_hash():
    user = User.query.filter_by(email='alice.j@test.com').first()
    assert user.password_hash == (
        '$2b$12$qSds4Mr9Wo7VwPWLhompEer88SuxxXFDp31P9etY6v7nfRctNO7B.')
    from flask_bcrypt import check_password_hash
    assert check_password_hash(user.password_hash, 'TestPass123!')


def test_tasks_jsonl_contract():
    rows = [json.loads(line) for line
            in (SITE / 'tasks.jsonl').read_text().splitlines() if line.strip()]
    assert 15 <= len(rows) <= 25
    base = {'web_name', 'id', 'ques', 'web', 'upstream_url'}
    for row in rows:
        # contributor keys plus the reviewer grading contract
        # (CONTRIBUTING.md "Reviewer role": verifier_path + judge_rubric
        # are appended by the reviewer; an answer key never ships)
        assert base <= set(row)
        assert set(row) <= base | {'verifier_path', 'judge_rubric'}
        assert 'verifier_path' in row and 'judge_rubric' in row
        assert not any(k.startswith('answer') for k in row)
        assert row['verifier_path'].startswith(
            'sites/fox_sports/verify/verify_')
        assert row['web'] == 'http://localhost:40209/'
        assert row['upstream_url'] == 'https://www.foxsports.com/'
        assert len(row['ques'].split()) <= 100
        # no URL shortcuts or direct-DB hints leak inside the task text
        assert 'http://localhost' not in row['ques']
        assert 'SELECT' not in row['ques']


def test_inventory_matches_images():
    inv = json.loads((SITE / 'asset_inventory.json').read_text())
    assert inv['asset_count'] == len(inv['assets'])
    for row in inv['assets']:
        path = SITE / row['path']
        assert path.exists(), row['path']
        assert path.stat().st_size == row['bytes']
    images = list((SITE / 'static/images/upstream').glob('*'))
    images = [p for p in images if p.name != '.gitkeep']
    assert len(images) == inv['asset_count']
