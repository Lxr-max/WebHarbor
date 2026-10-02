#!/usr/bin/env python3
"""Deterministic seed builder for the fox_sports mirror.

Everything materialized here comes from the tracked source_data/*.json
snapshots (captured 2026-09-30 from https://www.foxsports.com/, see
provenance.json) in a fixed, sorted order; the four benchmark accounts,
their favorites, and the FOX Super 6 contest entries are authored
fixtures following the u_s_customs / disney precedent: every team,
player, game, show and story they reference is a real captured upstream
row, and every timestamp is a frozen constant so the SQLite output is
byte-reproducible (PYTHONHASHSEED=0).
"""
import hashlib
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
SOURCE = os.path.join(HERE, 'source_data')

BENCHMARK_HASH = (
    '$2b$12$qSds4Mr9Wo7VwPWLhompEer88SuxxXFDp31P9etY6v7nfRctNO7B.')
MIRROR_TS = '2026-09-30'

LEAGUES = [
    ('nfl', 'NFL', 'Football'),
    ('college-football', 'College Football', 'Football'),
    ('mlb', 'MLB', 'Baseball'),
    ('nascar', 'NASCAR', 'Racing'),
    ('ufc', 'UFC', 'Fighting'),
]

BENCHMARK_USERS = [
    {'email': 'alice.j@test.com', 'name': 'Alice Johnson'},
    {'email': 'bob.c@test.com', 'name': 'Bob Chen'},
    {'email': 'carol.d@test.com', 'name': 'Carol Davis'},
    {'email': 'dana.k@test.com', 'name': 'Dana Kim'},
]


def _load(name):
    with open(os.path.join(SOURCE, name), encoding='utf-8') as f:
        return json.load(f)


_ASSET_MAP = None


def _asset_map():
    """url -> local filename, resolved from the tracked inventory so the
    saved extension always describes the real bytes."""
    global _ASSET_MAP
    if _ASSET_MAP is None:
        _ASSET_MAP = {}
        path = os.path.join(HERE, 'asset_inventory.json')
        if os.path.exists(path):
            with open(path, encoding='utf-8') as f:
                for row in json.load(f).get('assets', []):
                    _ASSET_MAP[row.get('source_url')] = \
                        row['path'].split('/')[-1]
    return _ASSET_MAP


def asset_name(url):
    """Deterministic local filename for an upstream image URL."""
    if not url:
        return None
    mapped = _asset_map().get(url)
    if mapped:
        return mapped
    digest = hashlib.sha256(url.encode('utf-8')).hexdigest()[:20]
    path = url.split('?')[0]
    ext = os.path.splitext(path)[1].lower() or '.jpg'
    if ext not in ('.jpg', '.jpeg', '.png', '.webp', '.gif'):
        ext = '.jpg'
    return digest + ext


def _js(obj):
    """Compact deterministic JSON for DB text columns."""
    if obj is None:
        return None
    return json.dumps(obj, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'))


def _pipe(values):
    if values is None:
        return None
    if isinstance(values, str):
        values = [v.strip() for v in values.split('|') if v.strip()]
    return '|'.join(v for v in (values or []) if v)


def seed_all(db):
    from app import (Episode, Favorite, Game, HomeTile, League, NascarDriver,
                     NascarRace, Personality, PersonalityVideo, Player,
                     PlayerNews, PlayerStat, Show, Story, Super6Contest,
                     Super6Entry, Super6Question, Team, UfcEvent, User)

    teams_raw = _load('teams.json')
    standings = _load('standings.json')
    team_info = _load('team_info.json')
    games = _load('games.json')
    details = _load('game_details.json')
    players = _load('players.json')
    stats = _load('player_stats.json')
    news = _load('player_news.json')
    stories = _load('stories.json')
    shows = _load('shows.json')
    people = _load('personalities.json')
    home = _load('home.json')
    nascar = _load('nascar.json')
    ufc = _load('ufc.json')
    super6 = _load('super6.json')

    # ---------------------------------------------------------------- leagues
    for slug, name, sport in LEAGUES:
        db.session.add(League(slug=slug, name=name, sport=sport))

    db.session.commit()

    # ------------------------------------------------------------------ teams
    standings_by_slug = {r['slug']: r for r in standings['nfl']}
    standings_by_slug.update({r['slug']: r for r in standings['mlb']})
    poll_by_slug = {r['slug']: r for r in standings['cfb_poll']}
    info_by_slug = team_info

    for row in sorted(teams_raw, key=lambda r: (r['league'], r['slug'])):
        st = standings_by_slug.get(row['slug'])
        poll = poll_by_slug.get(row['slug'])
        info = info_by_slug.get(row['slug'], {})
        division = st.get('division') if st else None
        db.session.add(Team(
            league=row['league'], slug=row['slug'],
            full_name=row['full_name'], city=row.get('city'),
            short=row.get('short'), logo=asset_name(row.get('logo')),
            division=division,
            conference=division.split(' ')[0] if division else None,
            rank=st.get('rank') if st else (info.get('rank') or None),
            record=(st.get('record') if st else None) or info.get('record'),
            note=info.get('note'),
            pct=st.get('pct') if st else None,
            pf=st.get('pf') if st else None,
            pa=st.get('pa') if st else None,
            home_rec=st.get('home') if st else None,
            away_rec=st.get('away') if st else None,
            conf_rec=st.get('conf') if st else None,
            div_rec=st.get('div') if st else None,
            streak=st.get('strk') if st else None,
            gb=st.get('gb') if st else None,
            l10=st.get('l10') if st else None,
            runs_for=st.get('rs') if st else None,
            runs_against=st.get('ra') if st else None,
            run_diff=st.get('diff') if st else None,
            clinch=st.get('clinch') if st else None,
            poll_rank=poll.get('rank') if poll else None,
            poll_votes=poll.get('first_place_votes') if poll else None,
            poll_points=poll.get('points') if poll else None,
            poll_record=poll.get('record') if poll else None,
            poll_movement=poll.get('movement') if poll else None,
            next_homeaway=info.get('next_homeaway'),
            next_opponent=info.get('next_opponent'),
            next_day=info.get('next_day'),
            next_time=info.get('next_time'),
            next_spread=info.get('next_spread'),
            next_total=info.get('next_total'),
        ))

    db.session.commit()

    # ----------------------------------------------------------------- games
    for row in sorted(games, key=lambda r: (r['league'], r['slug'])):
        det = details.get(row['slug'], {})
        db.session.add(Game(
            league=row['league'], slug=row['slug'],
            game_id=row.get('game_id'), date=row.get('date'),
            date_iso=row.get('date_iso'), week=row.get('week'),
            phase=row.get('phase'), series=row.get('series'),
            series_game=row.get('series_game'),
            series_note=row.get('series_note'),
            away_team=row.get('away_team'), home_team=row.get('home_team'),
            away_record=row.get('away_record'),
            home_record=row.get('home_record'),
            status=row.get('status'),
            away_score=row.get('away_score'), home_score=row.get('home_score'),
            away_abbr=row.get('away_abbr'), home_abbr=row.get('home_abbr'),
            away_hits=row.get('away_hits'), home_hits=row.get('home_hits'),
            away_errors=row.get('away_errors'),
            home_errors=row.get('home_errors'),
            time=row.get('time'), broadcaster=row.get('broadcaster'),
            spread=row.get('spread'), total=row.get('total'),
            away_ml=row.get('away_ml'), home_ml=row.get('home_ml'),
            venue=row.get('venue'), venue_city=row.get('venue_city'),
            attendance=row.get('attendance'), recap=row.get('recap'),
            odds_line=row.get('odds_line'),
            innings=_js(det.get('innings')),
            facts=_js(det.get('facts')),
            team_stats=_js(det.get('team_stats')),
            leaders=_js(det.get('leaders')),
            starting_qbs=_js(det.get('starting_qbs')),
            recent_games=_js(det.get('recent_games')),
            player_news=_js(det.get('player_news')),
            key_players=_js(det.get('key_players')),
            odds_notes=_js(det.get('odds_notes')),
            key_plays=_js(det.get('key_plays')),
            probable_pitchers=_js(det.get('probable_pitchers')),
            mlb_leaders=_js(det.get('mlb_leaders')),
        ))

    db.session.commit()

    # ---------------------------------------------------------------- players
    news_by_player = {}
    for item in news:
        news_by_player.setdefault((item['league'], item['player']), []).append(item)
    for row in sorted(players, key=lambda r: (r['league'], r['team'], r['slug'])):
        db.session.add(Player(
            league=row['league'], team=row['team'], slug=row['slug'],
            name=row['name'], number=row.get('number'),
            group_name=row.get('group'), pos=row.get('pos'),
            age=row.get('age'), height=row.get('height'),
            weight=row.get('weight'), college=row.get('college'),
        ))
    for item in sorted(news, key=lambda r: (r['league'], r['team'],
                                            r['player'], r['headline'])):
        db.session.add(PlayerNews(
            league=item['league'], team=item['team'],
            player=item['player'], headline=item['headline'],
            story=item.get('story'), impact=item.get('impact'),
            time_ago=item.get('time_ago'), source=item.get('source'),
        ))

    db.session.commit()

    # ------------------------------------------------------------- stat leaders
    rank_counter = {}
    for league in ('nfl', 'mlb', 'college-football'):
        for row in stats.get(league, []):
            key = (league, row['stat'])
            rank_counter[key] = rank_counter.get(key, 0) + 1
            db.session.add(PlayerStat(
                league=league, label=row['label'], stat=row['stat'],
                player=row['player'], team_abbr=row['team_abbr'],
                value=row['value'], rank=rank_counter[key],
            ))
        for row in stats.get(league + '_teams', []):
            db.session.add(PlayerStat(
                league=league, label=row['label'], stat=row['stat'],
                player=row['team'], team_abbr='', value=row['value'],
                rank=1, is_team=True,
            ))

    db.session.commit()

    # ---------------------------------------------------------------- stories
    for row in stories:
        db.session.add(Story(
            league=row['league'], slug=row['slug'], title=row['title'],
            dek=row.get('dek'), image=asset_name(row.get('image')),
            published=row.get('published'), author=row.get('author'),
            time_ago=row.get('time_ago'), source=row.get('source'),
            body=_pipe(row.get('body')),
        ))

    db.session.commit()

    # ------------------------------------------------------------------ shows
    for row in shows:
        db.session.add(Show(slug=row['slug'], title=row['title'],
                            art=asset_name(row.get('art'))))
        for ep in row.get('episodes', []):
            db.session.add(Episode(
                show_slug=row['slug'], title=ep['title'],
                time_ago=ep.get('time_ago'), source=ep.get('source'),
                thumb=asset_name(ep.get('thumb')),
            ))

    db.session.commit()

    # ----------------------------------------------------------- personalities
    for row in people:
        db.session.add(Personality(slug=row['slug'], name=row['name'],
                                   role=row.get('role'),
                                   art=asset_name(row.get('art'))))
        for vid in row.get('videos', []):
            db.session.add(PersonalityVideo(
                person_slug=row['slug'], title=vid['title'],
                time_ago=vid.get('time_ago'), source=vid.get('source'),
                thumb=asset_name(vid.get('thumb')),
            ))

    db.session.commit()

    # ------------------------------------------------------------------- home
    featured = home.get('featured', [])
    for tile in featured:
        story = next((s for s in stories if s['slug'] == tile['slug']), None)
        db.session.add(HomeTile(
            kind='story', title=story['title'] if story else tile['slug'],
            description=story.get('dek') if story else None,
            image=asset_name(story.get('image')) if story else None,
            link=f"/stories/{tile['league']}/{tile['slug']}",
            league=tile['league'],
        ))
    for text in home.get('moments', [])[:12]:
        db.session.add(HomeTile(kind='moment', title=text, description=None,
                                image=None, link=None, league=None))
    for text in home.get('live_tiles', [])[:12]:
        db.session.add(HomeTile(kind='live', title=text, description=None,
                                image=None, link='/watch', league=None))

    db.session.commit()

    # ----------------------------------------------------------------- nascar
    for row in nascar['standings']:
        db.session.add(NascarDriver(
            rank=int(row['rank']), driver=row['driver'],
            points=int(row['points']), back=row['back'],
            starts=int(row['starts']), wins=int(row['wins']),
            top5=int(row['top5']), top10=int(row['top10']),
            dnf=int(row['dnf']), stage_wins=int(row['stage_wins']),
            laps_led=int(row['laps_led'].replace(',', '')),
        ))
    for row in nascar['races']:
        db.session.add(NascarRace(
            when=row['when'], name=row['name'], track=row['track'],
            city=row['city'], time=row['time'], network=row['network'],
        ))

    db.session.commit()

    # -------------------------------------------------------------------- ufc
    for row in ufc:
        db.session.add(UfcEvent(
            when=row['when'], name=row['name'], venue=row['venue'],
            city=row['city'], fighter1=row['fighter1'],
            result1=row['result1'], fighter2=row['fighter2'],
            result2=row['result2'],
        ))

    db.session.commit()

    # --------------------------------------------------------------- super six
    contest = Super6Contest(
        slug='nfl-week-3-pick-6',
        title='NFL Week 3 Pick 6',
        description=('Practice picking six captured regular-season Week 3 results. '
                     'This offline benchmark contest offers no prizes.'),
        prize=super6.get('prize_tiers'),
        how_to_play=_pipe(super6.get('how_to_play')),
        deadline='2026-09-24 12:00PM', status='graded',
    )
    db.session.add(contest)
    db.session.flush()
    week3 = sorted(
        [g for g in games
         if g['league'] == 'nfl' and g.get('week') == 3
         and g['status'] == 'final' and g.get('phase') == 'regular'],
        key=lambda r: r['slug'])
    picked = week3[:6]
    for order, game in enumerate(picked, 1):
        correct = game['away_team'] if game['away_score'] > game['home_score'] \
            else game['home_team']
        db.session.add(Super6Question(
            contest_id=contest.id, order=order,
            label=f'Pick the winner: {order} of 6',
            away_team=game['away_team'], home_team=game['home_team'],
            game_slug=game['slug'], correct_pick=correct,
        ))
    db.session.flush()


# --------------------------------------------------------------------------
# Benchmark fixtures: the four accounts, their favorites and their Super 6
# entries (deterministic, referencing only real captured rows).
# --------------------------------------------------------------------------

def seed_benchmark_users(db):
    from app import Favorite, Super6Entry, Super6Question, User
    from flask_bcrypt import check_password_hash  # noqa: F401

    users = {}
    for row in BENCHMARK_USERS:
        user = User(email=row['email'], name=row['name'],
                    password_hash=BENCHMARK_HASH, joined=MIRROR_TS)
        db.session.add(user)
        users[row['email']] = user
    db.session.flush()

    # ---- favorites ---------------------------------------------------------
    def fav(email, item_type, key):
        db.session.add(Favorite(user_id=users[email].id, item_type=item_type,
                                item_key=key, added_at=MIRROR_TS))

    # Alice: NFL-centric
    fav('alice.j@test.com', 'team', 'kansas-city-chiefs')
    fav('alice.j@test.com', 'team', 'new-york-yankees')
    fav('alice.j@test.com', 'player', 'patrick-mahomes-ii')
    fav('alice.j@test.com', 'player', 'aaron-rodgers')
    fav('alice.j@test.com', 'show', 'the-herd-with-colin-cowherd')
    fav('alice.j@test.com', 'personality', 'colin-cowherd')
    # Bob: AFC East + FS1 mornings
    fav('bob.c@test.com', 'team', 'buffalo-bills')
    fav('bob.c@test.com', 'team', 'baltimore-ravens')
    fav('bob.c@test.com', 'player', 'josh-allen-2')
    fav('bob.c@test.com', 'player', 'derrick-henry')
    fav('bob.c@test.com', 'show', 'first-things-first')
    fav('bob.c@test.com', 'personality', 'nick-wright')
    # Carol: October baseball
    fav('carol.d@test.com', 'team', 'atlanta-braves')
    fav('carol.d@test.com', 'team', 'houston-astros')
    fav('carol.d@test.com', 'player', 'hunter-brown')
    fav('carol.d@test.com', 'player', 'kyle-tucker')
    fav('carol.d@test.com', 'show', 'fox-nfl-sunday')
    fav('carol.d@test.com', 'personality', 'tom-brady')
    # Dana: college football Saturdays
    fav('dana.k@test.com', 'team', 'texas-longhorns')
    fav('dana.k@test.com', 'team', 'notre-dame-fighting-irish')
    fav('dana.k@test.com', 'player', 'jayden-daniels')
    fav('dana.k@test.com', 'show', 'big-noon-kickoff')
    fav('dana.k@test.com', 'personality', 'joel-klatt')

    # ---- Super 6 fixture entries -------------------------------------------
    questions = list(db.session.query(Super6Question).order_by(
        Super6Question.contest_id, Super6Question.order))
    contest_id = questions[0].contest_id if questions else None
    if not contest_id:
        return
    picks_by_user = {
        'alice.j@test.com': 5,   # misses question 3
        'bob.c@test.com': 4,      # misses questions 2 and 5
        'carol.d@test.com': 6,    # perfect entry, the leader
        'dana.k@test.com': 3,     # misses questions 1, 4 and 6
    }
    for email, score in picks_by_user.items():
        picks = []
        for q in questions:
            if q.order <= score:
                picks.append(q.correct_pick)
            else:
                picks.append(q.away_team if q.correct_pick == q.home_team
                             else q.home_team)
        db.session.add(Super6Entry(
            contest_id=contest_id, user_id=users[email].id,
            created_at=MIRROR_TS, picks='|'.join(picks),
            score=score, is_fixture=True,
        ))
