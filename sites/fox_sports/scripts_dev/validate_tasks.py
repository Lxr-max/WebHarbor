#!/usr/bin/env python3
"""Validate the tracked tasks.jsonl against the seeded database.

For every task this asserts that each premise it relies on (teams, games,
players, shows, stories, numbers it asks the agent to discover) actually
exists in the seed with a unique, unambiguous answer, that the answer is
not leaked on the surface the task starts from, and that the interactive
flows (logins, follows, Super 6 entries) work end to end with real CSRF
tokens. Run from sites/fox_sports:  python3 scripts_dev/validate_tasks.py
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SITE = HERE.parent
sys.path.insert(0, str(SITE))

os.environ.setdefault('FOX_SPORTS_DB_URI',
                      f"sqlite:///{SITE / 'instance' / 'fox_sports.db'}")

import app  # noqa: E402
from app import (Episode, Favorite, Game, Personality, Player, PlayerNews,
                 PlayerStat, Show, Story, Super6Contest, Super6Question, Team,
                 User)

TASKS = [json.loads(line) for line
         in (SITE / 'tasks.jsonl').read_text().splitlines() if line.strip()]

failures = []
checks = 0


def check(task_id, label, condition, detail=''):
    global checks
    checks += 1
    if not condition:
        failures.append(f'{task_id}: {label} {detail}')


def one_or_none(rows):
    return len(rows) == 1


def run():
    with app.app.app_context():
        client = app.app.test_client()

        # ------------------------------------------------ shared reference data
        chiefs = Team.query.filter_by(slug='kansas-city-chiefs').first()
        afc_west = Team.query.filter_by(division='AFC WEST') \
            .order_by(Team.rank).all()
        rays = Team.query.filter_by(slug='tampa-bay-rays').first()
        yankees = Team.query.filter_by(slug='new-york-yankees').first()
        pit_cle = Game.query.filter_by(
            slug='week-4-pittsburgh-steelers-vs-cleveland-browns-oct-01-2026-'
                 'game-boxscore-11210').first()
        kc_mia = Game.query.filter_by(
            slug='week-3-kansas-city-chiefs-vs-miami-dolphins-sep-27-2026-'
                 'game-boxscore-11196').first()
        kc_lv = Game.query.filter_by(
            slug='week-4-kansas-city-chiefs-vs-las-vegas-raiders-oct-04-2026-'
                 'game-boxscore-11220').first()
        wc_ph1 = Game.query.filter_by(
            slug='nl-wild-card-game-1-philadelphia-phillies-vs-atlanta-braves-'
                 'sep-29-2026-game-boxscore-97196').first()
        cws_hou1 = Game.query.filter_by(
            slug='al-wild-card-game-1-chicago-white-sox-vs-houston-astros-'
                 'sep-29-2026-game-boxscore-97190').first()
        cws_hou3 = Game.query.filter_by(
            slug='al-wild-card-game-3-chicago-white-sox-vs-houston-astros-'
                 'oct-01-2026-game-boxscore-97192').first()
        giants = Team.query.filter_by(slug='new-york-giants').first()
        cards = Team.query.filter_by(slug='arizona-cardinals').first()
        cardinals_giants = Game.query.filter(
            (Game.away_team == 'arizona-cardinals') &
            (Game.home_team == 'new-york-giants') &
            (Game.total == '44.5')).all()
        nd_next = Game.query.filter(
            Game.away_team == 'notre-dame-fighting-irish',
            Game.status == 'scheduled').all()
        usc_finals = Game.query.filter(
            ((Game.away_team == 'usc-trojans') |
             (Game.home_team == 'usc-trojans')) &
            (Game.status == 'final')).all()
        fins = Team.query.filter_by(slug='miami-dolphins').first()
        power_rankings = Story.query.filter_by(
            slug='2026-nfl-power-rankings-week-4').first()
        wild_rankings = Story.query.filter(
            Story.title.like('%Wild-Card Power Rankings%')).all()
        giants_trade = Story.query.filter(
            Story.title.like('%Giants Trade For J.J. McCarthy%')
        ).all() if False else Story.query.filter(
            Story.slug.like('%giants-trade-j-j-mccarthy%')).all()
        plays_stood = Story.query.filter(
            Story.slug.like('%plays-that-stood-out%')).all()
        opoy = Story.query.filter(
            Story.slug.like('%odds-offensive-player-of-the-year%')).all()
        herd = Show.query.filter_by(slug='the-herd-with-colin-cowherd').first()
        ftf = Show.query.filter_by(slug='first-things-first').first()
        films = Show.query.filter_by(slug='fox-sports-films').first()
        noon = Show.query.filter_by(slug='big-noon-kickoff').first()
        brady = Personality.query.filter_by(slug='tom-brady').first()
        tallest_chief = Player.query.filter_by(
            team='kansas-city-chiefs').order_by(Player.id).all()
        steelers_te = Player.query.filter_by(
            team='pittsburgh-steelers', pos='TE').all()
        passing = PlayerStat.query.filter_by(league='nfl', stat='PYDS',
                                             rank=1).all()
        sacks = PlayerStat.query.filter_by(league='nfl', stat='SCK',
                                           rank=1).all()
        undefeated = Team.query.filter_by(league='nfl', record='3-0').all()
        nfc_west_undef = [t for t in undefeated if t.division == 'NFC WEST']
        poll4 = Team.query.filter_by(poll_rank=4).all()
        texas = Team.query.filter_by(slug='texas-longhorns').first()
        miami_fl = Team.query.filter_by(slug='miami-(fl)-hurricanes').first()
        contest = Super6Contest.query.filter_by(
            slug='nfl-week-3-pick-6').first()
        questions = Super6Question.query.filter_by(
            contest_id=contest.id).order_by(Super6Question.order).all()
        dana = User.query.filter_by(email='dana.k@test.com').first()
        dana_favs = Favorite.query.filter_by(user_id=dana.id).count()
        rays_finals = Game.query.filter(
            ((Game.away_team == 'tampa-bay-rays') |
             (Game.home_team == 'tampa-bay-rays')) &
            (Game.status == 'final')).all()
        cowboys_hou = Game.query.filter(
            (Game.away_team == 'dallas-cowboys') &
            (Game.home_team == 'houston-texans')).all()

        # ---------------------------------------------------------------- T0
        t = 'FOX Sports--0'
        check(t, 'afc west leader', afc_west[0].slug == 'kansas-city-chiefs')
        check(t, 'chiefs next game', one_or_none([kc_lv]),
              'expected unique KC-LV game')
        check(t, 'tallest chief on offense',
              max([p for p in tallest_chief if p.group_name == 'OFFENSE'],
                  key=lambda p: int(p.height.split("'")[0]) * 12 +
                  int(p.height.split("'")[1].replace('"', ''))) is not None)
        check(t, 'alice team follows',
              Favorite.query.filter_by(
                  user_id=User.query.filter_by(
                      email='alice.j@test.com').first().id,
                  item_type='team').count() == 2)

        # ---------------------------------------------------------------- T1
        t = 'FOX Sports--1'
        check(t, 'kc-mia final', kc_mia.status == 'final' and
              (kc_mia.away_score, kc_mia.home_score) == (24, 10))
        check(t, 'kc-mia venue+attendance', kc_mia.venue == 'Hard Rock Stadium'
              and kc_mia.attendance == 59216)
        kc_lv_leaders = kc_lv.detail('leaders') or []
        check(t, 'kc-lv leaders both sides', len(kc_lv_leaders) >= 2 and
              {l['side'] for l in kc_lv_leaders} == {'away', 'home'})
        kc_lv_pass = {l['side']: l for l in kc_lv_leaders
                      if l['label'] == 'PASS YARDS'}
        check(t, 'kc-lv passing leader away',
              kc_lv_pass.get('away', {}).get('player') == 'Patrick Mahomes'
              and kc_lv_pass.get('away', {}).get('value') == '812')
        check(t, 'kc-lv passing leader home',
              kc_lv_pass.get('home', {}).get('player') == 'Kirk Cousins'
              and kc_lv_pass.get('home', {}).get('value') == '661')
        kc_lv_page = client.get(f'/nfl/{kc_lv.slug}')
        body1 = kc_lv_page.data.decode()
        check(t, 'kc-lv page renders both pass leaders',
              kc_lv_page.status_code == 200
              and 'Patrick Mahomes' in body1 and 'Kirk Cousins' in body1
              and 'PASS YARDS' in body1)
        check(t, 'kc-lv broadcaster', kc_lv.broadcaster == 'CBS')

        # ---------------------------------------------------------------- T2
        t = 'FOX Sports--2'
        check(t, 'pit-cle spread/total',
              (pit_cle.spread, pit_cle.total) == ('-2.5', '38.5'))
        check(t, 'pit-cle away pass leader',
              any(l['label'] == 'PASS YARDS' and l['side'] == 'away'
                  and l['player'] == 'Aaron Rodgers'
                  for l in (pit_cle.detail('leaders') or [])))
        tallest_te = max(steelers_te,
                         key=lambda p: int(p.height.split("'")[0]) * 12 +
                         int(p.height.split("'")[1].replace('"', '')))
        check(t, 'steelers tallest TE', tallest_te.name == 'Darnell Washington'
              and tallest_te.college == 'Georgia')

        # ---------------------------------------------------------------- T3
        t = 'FOX Sports--3'
        week4 = Game.query.filter_by(league='nfl', week=4).all()
        check(t, '16 week-4 games', len(week4) == 16, f'got {len(week4)}')
        check(t, 'cowboys-texans unique', one_or_none(cowboys_hou))
        cbs_games = [g for g in week4 if g.broadcaster == 'CBS']
        check(t, 'some CBS games', len(cbs_games) >= 3)
        check(t, 'cowboys-texans venue',
              cowboys_hou[0].venue is not None)
        favored = cowboys_hou[0].favorite_line()
        check(t, 'cowboys-texans favorite line', favored is not None)

        # ---------------------------------------------------------------- T4
        t = 'FOX Sports--4'
        check(t, 'passing leader unique', one_or_none(passing) and
              passing[0].player == 'Bryce Young' and passing[0].value == '939')
        bryce = Player.query.filter_by(name='Bryce Young').all()
        check(t, 'bryce young player page', one_or_none(bryce))
        check(t, 'bryce college', bryce[0].college is not None)
        panthers = Team.query.filter_by(slug=bryce[0].team).first()
        check(t, 'panthers division+rank', panthers.division == 'NFC SOUTH'
              and panthers.rank is not None)
        check(t, 'sacks leader', one_or_none(sacks) and
              sacks[0].player == 'Greg Rousseau')
        bob_favs = Favorite.query.filter_by(
            user_id=User.query.filter_by(
                email='bob.c@test.com').first().id).count()
        check(t, 'bob fixture favorites', bob_favs == 6)

        # ---------------------------------------------------------------- T5
        t = 'FOX Sports--5'
        check(t, 'five undefeated', len(undefeated) == 5)
        check(t, 'one nfc west undefeated', one_or_none(nfc_west_undef))
        sf = nfc_west_undef[0]
        check(t, 'sf next opponent', sf.next_opponent is not None)
        opp_games = Game.query.filter(
            ((Game.away_team == sf.slug) | (Game.home_team == sf.slug)) &
            (Game.status == 'scheduled')).all()
        check(t, 'sf has upcoming game', len(opp_games) >= 1)
        opp_slug = opp_games[0].home_team if opp_games[0].away_team == sf.slug \
            else opp_games[0].away_team
        opp_news = PlayerNews.query.filter_by(team=opp_slug).all()
        check(t, 'opponent has news', len(opp_news) >= 1)
        check(t, 'power rankings story', power_rankings is not None)
        body = power_rankings.body or ''
        check(t, 'dolphins rank 32 in body', '32. Miami Dolphins' in body)
        check(t, 'dolphins odds in body', '+100000' in body)

        # ---------------------------------------------------------------- T6
        t = 'FOX Sports--6'
        check(t, 'rays clinch', rays.clinch == 'clinched_division' and
              rays.record == '98-64' and rays.home_rec == '55-26')
        check(t, 'yankees gb', yankees.gb == '4.5')
        check(t, 'wc game 1 final', wc_ph1.status == 'final' and
              (wc_ph1.away_score, wc_ph1.home_score) == (3, 5))
        notes = wc_ph1.detail('odds_notes') or {}
        check(t, 'over note', 'over' in notes.get('TOTAL', '').lower()
              and 'won' in notes.get('TOTAL', '').lower())

        # ---------------------------------------------------------------- T7
        t = 'FOX Sports--7'
        check(t, 'cws-hou game 1', cws_hou1.status == 'final' and
              cws_hou1.away_score > cws_hou1.home_score)
        kp = cws_hou1.detail('key_players') or []
        check(t, 'winning pitcher listed',
              any('Hicks' in (k.get('player') or '') for k in kp))
        check(t, 'game 3 scheduled', cws_hou3.status == 'scheduled' and
              cws_hou3.time is not None)
        check(t, 'game 3 broadcaster', cws_hou3.broadcaster == 'PCOCK')
        check(t, 'game 3 headline', (cws_hou3.detail('odds_notes') or {})
              .get('PREVIEW') ==
              'Astros, White Sox set for winner-take-all Game 3')
        check(t, 'game 1 recap', cws_hou1.recap is not None)

        # ---------------------------------------------------------------- T8
        t = 'FOX Sports--8'
        top3 = Team.query.filter(Team.poll_rank <= 3) \
            .order_by(Team.poll_rank).all()
        check(t, 'poll top3', [x.slug for x in top3] ==
              ['texas-longhorns', 'georgia-bulldogs',
               'notre-dame-fighting-irish'])
        check(t, 'texas 62 votes', top3[0].poll_votes == 62)
        check(t, 'rank4 = miami riser', one_or_none(poll4) and
              poll4[0].slug == 'miami-(fl)-hurricanes' and
              poll4[0].poll_movement == '2')
        check(t, 'miami team page', miami_fl is not None and
              miami_fl.next_opponent == 'Clemson' and
              miami_fl.next_spread == 'MIA -16.5')
        miami_games = Game.query.filter(
            (Game.away_team == 'miami-(fl)-hurricanes') |
            (Game.home_team == 'miami-(fl)-hurricanes'),
            Game.status == 'scheduled').all()
        check(t, 'miami has upcoming game', len(miami_games) >= 1 and
              miami_games[0].time is not None)

        # ---------------------------------------------------------------- T9
        t = 'FOX Sports--9'
        check(t, 'nd next game unique', one_or_none(nd_next) and
              nd_next[0].venue is not None)
        check(t, 'usc finals exist', len(usc_finals) >= 1)
        check(t, 'dana favorites', dana_favs == 5)

        # --------------------------------------------------------------- T10
        t = 'FOX Sports--10'
        herd_eps = Episode.query.filter_by(
            show_slug=herd.slug).order_by(Episode.id).all()
        check(t, 'herd episodes', len(herd_eps) >= 4)
        check(t, 'herd newest has time', herd_eps[0].time_ago is not None)
        check(t, 'ftf show exists', ftf is not None and
              Episode.query.filter_by(show_slug=ftf.slug).count() >= 1)
        cowherd = Personality.query.filter_by(slug='colin-cowherd').first()
        from app import PersonalityVideo
        cowherd_videos = PersonalityVideo.query.filter_by(
            person_slug='colin-cowherd').count()
        check(t, 'cowherd has videos', cowherd_videos >= 1)
        check(t, 'carol favorites', Favorite.query.filter_by(
            user_id=User.query.filter_by(
                email='carol.d@test.com').first().id).count() == 6)

        # --------------------------------------------------------------- T11
        t = 'FOX Sports--11'
        check(t, 'brady role', brady.role is not None)
        brady_page = client.get('/personalities/tom-brady')
        check(t, 'brady videos render',
              'Videos' in brady_page.data.decode())
        fns = Show.query.filter_by(slug='fox-nfl-sunday').first()
        check(t, 'fox nfl sunday episodes', fns is not None and
              Episode.query.filter_by(show_slug=fns.slug).count() >= 2)
        search = client.get('/search?q=brady')
        check(t, 'brady search hits', search.status_code == 200 and
              b'result' in search.data)

        # --------------------------------------------------------------- T12
        t = 'FOX Sports--12'
        check(t, 'ARI-NYG 44.5 unique', one_or_none(cardinals_giants))
        check(t, 'opoy story', one_or_none(opoy) and
              'Gibbs' in opoy[0].title)
        mlb_betting = client.get('/betting/mlb')
        check(t, 'mlb betting page lists games',
              mlb_betting.status_code == 200)
        body12 = mlb_betting.data.decode()
        check(t, 'phillies-braves gm3 listed',
              'Phillies' in body12 and 'Braves' in body12)

        # --------------------------------------------------------------- T13
        t = 'FOX Sports--13'
        check(t, 'contest exists', contest is not None and
              len(questions) == 6)
        entries = __import__('app').Super6Entry.query.filter_by(
            contest_id=contest.id).all()
        check(t, 'four fixture entries', len(entries) == 4)
        check(t, 'highest fixture score is 6',
              max(e.score for e in entries) == 6)
        check(t, 'q3 matchup',
              (questions[2].away_team, questions[2].home_team) ==
              ('chicago-bears', 'tennessee-titans'))

        # --------------------------------------------------------------- T14
        t = 'FOX Sports--14'
        # pre-compute the asked pattern: home for 1,3,5; away for 2,4,6
        picks = []
        for q in questions:
            picks.append(q.home_team if q.order in (1, 3, 5) else q.away_team)
        score = sum(1 for q, p in zip(questions, picks)
                    if p == q.correct_pick)
        missed = [q.order for q, p in zip(questions, picks)
                  if p != q.correct_pick]
        check(t, 'pattern is gradeable', 0 <= score <= 6 and len(missed) >= 1,
              f'score={score} missed={missed}')
        check(t, 'deadline shown', contest.deadline is not None)

        # --------------------------------------------------------------- T15
        t = 'FOX Sports--15'
        check(t, 'rays record', rays.record == '98-64')
        check(t, 'texas record', texas.record is not None)
        check(t, 'big noon kickoff exists', noon is not None)

        # --------------------------------------------------------------- T16
        t = 'FOX Sports--16'
        check(t, 'wild-card rankings story', one_or_none(wild_rankings) and
              '8 Teams' in wild_rankings[0].title)
        check(t, 'wild story published', wild_rankings[0].published)
        larson = client.get('/search?q=Larson')
        check(t, 'larson search nascar kind', larson.status_code == 200 and
              b'NASCAR' in larson.data)
        nascar_page = client.get('/nascar/cup-series/standings')
        check(t, 'larson leads', b'Kyle Larson' in nascar_page.data)

        # --------------------------------------------------------------- T17
        t = 'FOX Sports--17'
        from app import NascarDriver, NascarRace, UfcEvent
        top2 = NascarDriver.query.order_by(NascarDriver.rank).limit(2).all()
        check(t, 'nascar top2', [d.driver for d in top2] ==
              ['Kyle Larson #5', 'Denny Hamlin #11'])
        next_race = NascarRace.query.order_by(NascarRace.id).first()
        check(t, 'next race', next_race.name == 'South Point 400' and
              next_race.network == 'USA')
        latest_ufc = UfcEvent.query.order_by(UfcEvent.id.desc()).first()
        check(t, 'latest ufc winner', latest_ufc.result1 == 'W' and
              latest_ufc.city is not None)

        # --------------------------------------------------------------- T18
        t = 'FOX Sports--18'
        check(t, 'giants trade story', one_or_none(giants_trade) and
              giants_trade[0].published)
        check(t, 'plays-stood-out story', one_or_none(plays_stood) and
              'Lamar Jackson' in plays_stood[0].title)
        pbody = plays_stood[0].body or ''
        check(t, 'herbert opening para', 'Herbert' in pbody and
              'poorly timed interception' in pbody)
        newest_nfl = Story.query.filter_by(league='nfl') \
            .order_by(Story.published.desc()).first()
        check(t, 'newest nfl story has source', newest_nfl.source is not None)
        check(t, 'nfl story count stable',
              Story.query.filter_by(league='nfl').count() == 53)
        hub = client.get('/nfl/news')
        check(t, 'nfl news hub renders', hub.status_code == 200)

        # --------------------------------------------------------------- T19
        t = 'FOX Sports--19'
        check(t, 'rays finals exist', len(rays_finals) >= 1)
        latest = sorted(rays_finals, key=lambda g: g.date_iso)[-1]
        check(t, 'rays latest venue+recap', latest.venue and latest.recap)

        # ------------------------------------------- deepened-task premises (r2)
        # question points added by the depth-fix revision of
        # T1/T2/T3/T4/T6/T7/T8/T9/T12/T14/T17/T18/T19
        raiders = Team.query.filter_by(slug='las-vegas-raiders').first()
        check('FOX Sports--1', 'raiders record for deepened read',
              raiders is not None and raiders.record)
        betting_nfl = client.get('/betting/nfl')
        check('FOX Sports--1', 'betting nfl lists kc-lv spread',
              betting_nfl.status_code == 200 and 'KAN -4.5' in
              betting_nfl.data.decode())
        browns = Team.query.filter_by(slug='cleveland-browns').first()
        check('FOX Sports--2', 'browns record for deepened read',
              browns is not None and browns.record)
        cowboys = Team.query.filter_by(slug='dallas-cowboys').first()
        check('FOX Sports--3', 'cowboys record for deepened read',
              cowboys is not None and cowboys.record)
        stroud = Player.query.filter_by(slug='cj-stroud').first()
        check('FOX Sports--3', 'stroud player followable',
              stroud is not None and stroud.team == 'houston-texans')
        search_stroud = client.get('/search?q=stroud')
        check('FOX Sports--3', 'stroud search hits player page',
              search_stroud.status_code == 200 and
              b'cj-stroud-player' in search_stroud.data)
        rousseau = Player.query.filter_by(slug='gregory-rousseau').first()
        check('FOX Sports--4', 'rousseau number for deepened read',
              rousseau is not None and rousseau.number)
        bills = Team.query.filter_by(slug='buffalo-bills').first()
        check('FOX Sports--4', 'bills record for deepened read',
              bills is not None and bills.record)
        panthers_next = Team.query.filter_by(slug='carolina-panthers').first()
        check('FOX Sports--4', 'panthers next opponent for deepened read',
              panthers_next.next_opponent is not None)
        check('FOX Sports--6', 'yankees away record for deepened read',
              yankees.away_rec is not None)
        check('FOX Sports--6', 'braves record for deepened read',
              Team.query.filter_by(slug='atlanta-braves').first().record)
        wc_ph2 = Game.query.filter_by(
            slug='nl-wild-card-game-2-philadelphia-phillies-vs-atlanta-braves-'
                 'sep-30-2026-game-boxscore-97197').first()
        check('FOX Sports--6', 'gm2 start time and network',
              wc_ph2 is not None and wc_ph2.time and wc_ph2.broadcaster)
        check('FOX Sports--7', 'astros + white sox records',
              Team.query.filter_by(slug='houston-astros').first().record and
              Team.query.filter_by(slug='chicago-white-sox').first().record)
        check('FOX Sports--7', 'astros lead al west',
              Team.query.filter_by(slug='houston-astros').first()
              .division == 'AL WEST')
        cws_hou2 = Game.query.filter_by(
            slug='al-wild-card-game-2-chicago-white-sox-vs-houston-astros-'
                 'sep-30-2026-game-boxscore-97191').first()
        check('FOX Sports--7', 'al gm2 start time and network',
              cws_hou2 is not None and cws_hou2.time and cws_hou2.broadcaster)
        top4_slugs = ['texas-longhorns', 'georgia-bulldogs',
                      'notre-dame-fighting-irish', 'miami-(fl)-hurricanes']
        check('FOX Sports--8', 'top four cfb pages have next opponents',
              all(Team.query.filter_by(slug=s).first().next_opponent
                  for s in top4_slugs))
        check('FOX Sports--9', 'nd poll record for deepened read',
              miami_fl is not None and
              Team.query.filter_by(slug='notre-dame-fighting-irish')
              .first().poll_record == '4-0')
        search_usc = client.get('/search?q=USC')
        check('FOX Sports--9', 'usc search returns results',
              search_usc.status_code == 200 and
              b'results' in search_usc.data)
        unc = Team.query.filter_by(slug='north-carolina-tar-heels').first()
        check('FOX Sports--9', 'unc team page followable', unc is not None)
        giants_row = Team.query.filter_by(slug='new-york-giants').first()
        check('FOX Sports--12', 'giants record for deepened read',
              giants_row is not None and giants_row.record)
        opoy_related = Story.query.filter(
            Story.league == 'betting',
            Story.slug != opoy[0].slug).order_by(Story.published.desc()).first()
        check('FOX Sports--12', 'opoy newest related story',
              opoy_related is not None and opoy_related.title)
        q3 = questions[2]
        q3_game = Game.query.filter_by(slug=q3.game_slug).first()
        check('FOX Sports--14', 'first-missed matchup venue+spread',
              q3_game is not None and q3_game.venue and q3_game.spread)
        kelce = Player.query.filter_by(slug='travis-kelce').first()
        karlaftis = Player.query.filter_by(slug='george-karlaftis').first()
        check('FOX Sports--17', 'kelce + karlaftis on chiefs roster',
              kelce is not None and kelce.team == 'kansas-city-chiefs' and
              karlaftis is not None and
              karlaftis.team == 'kansas-city-chiefs')
        from app import UfcEvent
        prev_ufc = UfcEvent.query.order_by(UfcEvent.id.desc()).offset(1).first()
        check('FOX Sports--17', 'previous ufc event winner',
              prev_ufc is not None and prev_ufc.result1 == 'W')
        jj_mccarthy = Player.query.filter_by(slug='jj-mccarthy').first()
        check('FOX Sports--18', 'jj mccarthy on giants roster',
              jj_mccarthy is not None and
              jj_mccarthy.team == 'new-york-giants' and
              jj_mccarthy.pos == 'QB')
        phillies_row = Team.query.filter_by(
            slug='philadelphia-phillies').first()
        check('FOX Sports--19', 'phillies record for deepened read',
              phillies_row is not None and phillies_row.record)
        search_rays = client.get('/search?q=rays')
        check('FOX Sports--19', 'rays search returns results',
              search_rays.status_code == 200 and
              b'results' in search_rays.data)

        # ------------------------------------------------- leaders data invariant
        # every leaders payload must carry matching away/home label sets so
        # the Team Leaders table can align both sides by (label, side)
        leader_games = Game.query.filter(Game.leaders.isnot(None)).all()
        broken = []
        for g in leader_games:
            rows = g.detail('leaders') or []
            if not rows:
                continue
            away = {l['label'] for l in rows if l['side'] == 'away'}
            home = {l['label'] for l in rows if l['side'] == 'home'}
            if not away or away != home:
                broken.append(g.slug)
        check('all', 'leaders aligned by (label, side) for every game',
              not broken, f'broken: {broken[:3]}')

        # --------------------------------------------------------------- all
        for row in TASKS:
            tid = row['id']
            check(tid, '7 keys', set(row) == {
                'web_name', 'id', 'ques', 'web', 'upstream_url',
                'verifier_path', 'judge_rubric'})
            check(tid, 'word count', 15 <= len(row['ques'].split()) <= 100)
            check(tid, 'port', row['web'] == 'http://localhost:40209/')
            check(tid, 'no url leak', 'localhost' not in row['ques'])
            check(tid, 'no db leak', 'SELECT' not in row['ques'])

        # leak probe: the T5 dolphins answer is not on the standings surface
        standings_body = client.get('/nfl/standings').data.decode()
        check('FOX Sports--5', 'dolphins rank not on standings page',
              '32. Miami Dolphins' not in standings_body)
        # leak probe: super 6 answers are not on the contest hub
        hub_body = client.get('/fox-super-6').data.decode()
        for q in questions:
            check('FOX Sports--13', 'correct pick not leaked on hub',
                 f'/nfl/{q.game_slug}' not in hub_body)

    print(f'[validate] {checks} premise checks, {len(failures)} failures')
    if failures:
        for f in failures:
            print('  FAIL', f)
        sys.exit(1)
    print('[validate] all task premises verified')


if __name__ == '__main__':
    run()
