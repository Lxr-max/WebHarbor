#!/usr/bin/env python3
"""Honest-path task auditor for the iclr mirror.

For every task in tasks.jsonl this walker drives the exact honest path a
solving agent must take through the mirror UI (Flask test client, real CSRF
tokens, forms submitted the way a browser submits them), verifies each
premise the task relies on, collects the answers the task asks for, counts
the atomic UI actions the task requires, and fails when a task leaks its
own answers or can be finished in fewer than 15 honest atomic steps.

Runs two fully independent rounds (fresh database each time) and reports
both step counts; they must agree.

Step conventions (frozen reviewer-rail caliber; reads are free):
  go(url)                1  page navigation (nav link / direct URL)
  click(url)             1  on-page element click (day tab, result link,
                            session paper-list link, bookmark button)
  back()                 1  browser back
  fill(field)            1  per form field the task requires filling
  select(dropdown)       1  per dropdown change
  check/unchecked(box)   1  per checkbox toggle
  submit                 1  pressing the form's submit button — and only
                            that; the field fills above are the steps, the
                            same form is never counted twice (the r1 review
                            dinged the old walker for adding `fills` again
                            inside submit())
  done                   1  composing the final answer
The initial homepage load does not count. Every action is followed by a
page the walker actually reads (visible element + page feedback).

Run from sites/iclr:  python3 scripts_dev/validate_tasks.py
"""
from __future__ import annotations

import html
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SITE))

MIN_STEPS = 15


def fresh_client(tag):
    root = Path(tempfile.mkdtemp(prefix=f'iclr-audit-{tag}-'))
    os.environ['ICLR_DB_URI'] = f'sqlite:///{root / "iclr.db"}'
    os.environ['ICLR_AUTO_SEED'] = '1'
    for mod in list(sys.modules):
        if mod in ('app', 'seed_lib'):
            del sys.modules[mod]
    import app as A
    A.app.config.update(TESTING=True)
    return A, A.app.test_client(), root


def csrf(client, url):
    r = client.get(url)
    assert r.status_code == 200, f'{url} -> {r.status_code}'
    m = re.search(rb'name="csrf_token"[^>]*value="([^"]+)"', r.data)
    assert m, f'no csrf token on {url}'
    return m.group(1).decode()


def text(resp):
    return resp.data.decode()


def unescape(t):
    return html.unescape(html.unescape(t))


class Walker:
    """Counts atomic UI actions under the frozen honest caliber."""

    def __init__(self, client):
        self.client = client
        self.steps = 0
        self.log = []
        self.answers = {}
        self._stack = []      # visited URLs, for browser back()
        self._current = None

    # ------------------------------------------------------------- actions --
    def _get(self, url):
        r = self.client.get(url, follow_redirects=True)
        assert r.status_code == 200, f'{url} -> {r.status_code}'
        return text(r)

    def go(self, url, note=''):
        """Navigate (nav bar / direct URL)."""
        page = self._get(url)
        self.steps += 1
        self.log.append(f'{self.steps:3d} GO    {url} {note}')
        if self._current is not None:
            self._stack.append(self._current)
        self._current = url
        return page

    def click(self, url, note=''):
        """Click an on-page element whose target is `url` (day tab, result
        link, session paper-list link, log-out link, ...)."""
        page = self._get(url)
        self.steps += 1
        self.log.append(f'{self.steps:3d} CLICK {url} {note}')
        if self._current is not None:
            self._stack.append(self._current)
        self._current = url
        return page

    def back(self, note=''):
        """Browser back to the previous page."""
        assert self._stack, 'back() with empty history'
        url = self._stack.pop()
        page = self._get(url)
        self.steps += 1
        self.log.append(f'{self.steps:3d} BACK  {url} {note}')
        self._current = url
        return page

    def fill(self, note):
        self.steps += 1
        self.log.append(f'{self.steps:3d} FILL  {note}')

    def select(self, note):
        self.steps += 1
        self.log.append(f'{self.steps:3d} SEL   {note}')

    def check(self, note):
        self.steps += 1
        self.log.append(f'{self.steps:3d} CHECK {note}')

    def uncheck(self, note):
        self.steps += 1
        self.log.append(f'{self.steps:3d} UNCHK {note}')

    POST_ROUTES = ('/login', '/signup', '/register', '/helpdesk',
                   '/bookmarks/toggle', '/schedule/save')

    def submit(self, source, action, fields, note=''):
        """Press a form's submit button: exactly ONE atomic step.

        `fields` must NOT include the token. GET forms (paper search /
        filters / site search) carry no token; POST forms (login, signup,
        registration, toggles, helpdesk) submit a real token. The fills
        are counted where they happen (fill/select/check above) — the
        same form is never counted twice."""
        data = dict(fields)
        method = 'POST' if action in self.POST_ROUTES else 'GET'
        if method == 'POST':
            data['csrf_token'] = csrf(self.client, source)
        self.steps += 1
        self.log.append(f'{self.steps:3d} {method}  {action} {note}')
        if method == 'GET':
            r = self.client.get(action, query_string=data,
                                follow_redirects=True)
        else:
            r = self.client.post(action, data=data, follow_redirects=True)
        assert r.status_code == 200, f'{method} {action} -> {r.status_code}'
        if self._current is not None:
            self._stack.append(self._current)
        self._current = r.request.url if hasattr(r, 'request') else action
        return text(r)

    def done(self, note='compose final answer'):
        self.steps += 1
        self.log.append(f'{self.steps:3d} DONE  {note}')

    # -------------------------------------------------------------- records --
    def answer(self, key, value):
        self.answers[key] = str(value)

    def must(self, cond, msg):
        assert cond, msg


# ------------------------------------------------------------------ helpers --

def paper_count(page):
    m = re.search(r'(\d+) papers match the current filters', page)
    return int(m.group(1)) if m else None


def first_paper_link(page):
    m = re.search(r'href="/papers/(\d+)">', page)
    return int(m.group(1)) if m else None


def paper_detail_facts(page):
    title = re.search(r'<h1 style="font-size:1\.35rem">([^<]+)</h1>', page)
    session = re.search(r'<th[^>]*>Session</th><td>([^<]+)</td>', page)
    pos = re.search(r'<th[^>]*>Poster position</th><td>([^<]+)</td>', page)
    slot = re.search(r'<th[^>]*>Talk slot</th><td>([^<]+)</td>', page)
    window = re.search(r'<th[^>]*>Session window</th><td>([^<]+)</td>', page)
    room = re.search(r'<th[^>]*>Room</th><td>([^<]+)</td>', page)
    authors = re.findall(r'<b>([^<]+)</b>\s*(?:<span class="muted">\(([^)]*)\)</span>)?', page)
    return {
        'title': title.group(1) if title else None,
        'session': session.group(1) if session else None,
        'position': pos.group(1) if pos else None,
        'talk_slot': unescape(slot.group(1)).strip() if slot else None,
        'window': unescape(window.group(1)).strip() if window else None,
        'room': room.group(1) if room else None,
        'authors': authors,
    }


def card_position(page, pid):
    """Poster position as shown on a papers-browser card (no detail open)."""
    m = re.search(rf'href="/papers/{pid}">.*?poster (P\d+-#\d+)', page, re.S)
    return m.group(1) if m else None


def search_sections(page):
    """Section headings that carry at least one hit on /search results."""
    sections = []
    parts = re.split(r'<h2 class="muted"[^>]*>', page)
    for part in parts[1:]:
        name = re.match(r'([^<(]+?)(?: \(\d+\))?</h2>', part)
        body = part.split('</h2>', 1)[-1]
        if name and '<a href' in body:
            sections.append(name.group(1).strip())
    return sections


def session_window_on_schedule(page, session_name):
    # the time div precedes the session title inside the block
    m = re.search(rf'<div class="time">([^<]+)\u2013([^<]+)</div>\s*'
                  rf'<div class="body">\s*<h3>{re.escape(session_name)}</h3>',
                  page)
    return (m.group(1).strip(), m.group(2).strip()) if m else None


def venue_hits_on_search(page):
    """(heading, snippet) pairs rendered in the Conference site section."""
    m = re.search(r'>Conference site(?: \((\d+)\))?</h2>(.*?)(?=<h2|\Z)',
                  page, re.S)
    if not m or 'No conference-site notes match' in m.group(2):
        return []
    return re.findall(r'<a href="/venue">([^<]+)</a>\s*'
                      r'<span class="muted small">\u2014 ([^<]+)</span>',
                      m.group(2))


def mystuff_reg_line(page, code):
    m = re.search(rf'{code}</b> \u2014 ([^<]+)</p>', page)
    return m.group(1).strip() if m else None


from urllib.parse import quote  # noqa: E402


# --------------------------------------------------------------- task walks --

def walk_0(w, A, client):
    """diffusion search -> topic -> first -> oral filter -> session window."""
    page = w.go('/papers', 'papers browser')
    w.fill('search q=diffusion')
    page = w.submit('/papers', '/papers', {'q': 'diffusion'}, 'search diffusion')
    total = paper_count(page)
    w.answer('diffusion_count', total)
    w.must(total == 406, f'premise: diffusion count is 406 not {total}')
    w.select('topic select')
    page = w.submit('/papers', '/papers',
                    {'q': 'diffusion', 'topic': 'Reinforcement Learning->Deep RL'},
                    'apply topic filter')
    narrow = paper_count(page)
    w.answer('rl_topic_count', narrow)
    w.must(narrow == 4, f'premise: RL->Deep RL subset is 4 not {narrow}')
    pid = first_paper_link(page)
    detail = w.click(f'/papers/{pid}', 'open first result')
    facts = paper_detail_facts(detail)
    w.answer('first_position', facts['position'])
    w.answer('first_session', facts['session'])
    w.must(facts['position'] == 'P4-#4618', f'premise: position {facts["position"]}')
    w.must(facts['session'] == 'Poster Session 2 Pavilion 4',
           f'premise: session {facts["session"]}')
    page = w.back('back to the diffusion search')
    w.select('reset topic to All')
    w.select('oral decisions only')
    page = w.submit('/papers', '/papers',
                    {'q': 'diffusion', 'decision': 'Accept (Oral)'},
                    'apply oral filter')
    orals = paper_count(page)
    w.answer('diffusion_oral_count', orals)
    w.must(orals == 34, f'premise: diffusion orals 34 not {orals}')
    pid2 = first_paper_link(page)
    detail2 = w.click(f'/papers/{pid2}', 'open first oral match')
    facts2 = paper_detail_facts(detail2)
    w.answer('first_oral_session', facts2['session'])
    w.answer('first_oral_has_position', bool(facts2['position']))
    w.must(facts2['position'] == 'P3-#1309',
           f'premise: first diffusion oral position {facts2["position"]}')
    day = A.Paper.query.get(pid2).day
    page = w.go('/schedule', 'schedule')
    page = w.click(f'/schedule?date={day}', "the session's day tab")
    window = session_window_on_schedule(page, facts2['session'])
    w.answer('session_window', f'{window[0]}-{window[1]}')
    page = w.click(f'/papers?session={quote(facts2["session"])}',
                   "the session's paper list")
    w.answer('session_paper_count', paper_count(page))
    w.go('/login', 'login page')
    w.fill('email')
    w.fill('password')
    w.submit('/login', '/login',
             {'email': 'alice.j@test.com', 'password': 'TestPass123!'},
             'login alice')
    w.go(f'/papers/{pid}', 'back to first result')
    w.submit(f'/papers/{pid}', '/bookmarks/toggle',
             {'paper_id': str(pid), 'back': f'/papers/{pid}'}, 'bookmark')
    mystuff = w.go('/mystuff', 'my stuff')
    w.answer('alice_bookmarks', mystuff.count('paper-row'))
    w.must(mystuff.count('paper-row') == 4, 'premise: alice 4 bookmarks')
    w.done()


def walk_1(w, A, client):
    """language model search -> oral -> first -> schedule -> bob bookmark."""
    page = w.go('/papers', 'papers browser')
    w.fill('search q=language model')
    page = w.submit('/papers', '/papers', {'q': 'language model'}, 'search')
    total = paper_count(page)
    w.answer('lm_count', total)
    w.must(total == 495, f'premise: language model 495 not {total}')
    w.select('oral only')
    page = w.submit('/papers', '/papers',
                    {'q': 'language model', 'decision': 'Accept (Oral)'},
                    'apply oral filter')
    orals = paper_count(page)
    w.answer('lm_oral_count', orals)
    w.must(orals == 38, f'premise: lm orals 38 not {orals}')
    pid = first_paper_link(page)
    detail = w.click(f'/papers/{pid}', 'open first result')
    facts = paper_detail_facts(detail)
    w.answer('first_session', facts['session'])
    w.answer('first_page_shows', 'talk slot' if facts['talk_slot'] else 'poster position')
    w.must(facts['talk_slot'] is None and facts['window'],
           'premise: poster-only oral shows a session window')
    p = A.Paper.query.get(pid)
    page = w.go('/schedule', 'schedule')
    page = w.click(f'/schedule?date={p.day}', "the session's day tab")
    window = session_window_on_schedule(page, facts['session'])
    w.answer('session_day', p.day)
    w.answer('session_window', f'{window[0]}-{window[1]}')
    w.go('/login', 'login page')
    w.fill('email')
    w.fill('password')
    w.submit('/login', '/login',
             {'email': 'bob.c@test.com', 'password': 'TestPass123!'}, 'login bob')
    detail = w.go(f'/papers/{pid}', 'back to the paper')
    w.submit(f'/papers/{pid}', '/bookmarks/toggle',
             {'paper_id': str(pid), 'back': f'/papers/{pid}'}, 'bookmark')
    mystuff = w.go('/mystuff', 'my stuff')
    n = mystuff.count('paper-row')
    w.answer('bob_bookmarks', n)
    w.must(n == 2, f'premise: bob ends with 2 bookmarks, got {n}')
    w.done()


def walk_2(w, A, client):
    """poster session 4 P4 -> first -> schedule -> PS1P4 -> carol bookmark."""
    page = w.go('/papers', 'papers browser')
    w.select('PS4P4 session select')
    page = w.submit('/papers', '/papers',
                    {'session': 'Poster Session 4 Pavilion 4', 'sort': 'title'},
                    'session filter (title is the default sort)')
    total = paper_count(page)
    w.answer('ps4p4_count', total)
    w.must(total == 432, f'premise: PS4P4 432 not {total}')
    pid = first_paper_link(page)
    detail = w.click(f'/papers/{pid}', 'open first result')
    facts = paper_detail_facts(detail)
    w.answer('first_position', facts['position'])
    w.answer('first_author_institution', facts['authors'][0][1])
    p = A.Paper.query.get(pid)
    page = w.go('/schedule', 'schedule')
    page = w.click(f'/schedule?date={p.day}', 'the PS4P4 day tab')
    window = session_window_on_schedule(page, 'Poster Session 4 Pavilion 4')
    w.answer('ps4p4_window', f'{window[0]}-{window[1]}')
    page = w.go('/papers', 'papers browser again')
    w.select('PS1P4 session select')
    page = w.submit('/papers', '/papers',
                    {'session': 'Poster Session 1 Pavilion 4', 'sort': 'title'},
                    'PS1P4 filter')
    pid2 = first_paper_link(page)
    w.answer('ps1p4_count', paper_count(page))
    pos2 = card_position(page, pid2)
    w.answer('ps1p4_first_position', pos2)
    w.must(pos2 == 'P4-#3316', f'premise: P4-#3316 not {pos2}')
    w.go('/login', 'login page')
    w.fill('email')
    w.fill('password')
    w.submit('/login', '/login',
             {'email': 'carol.d@test.com', 'password': 'TestPass123!'},
             'login carol')
    w.go(f'/papers/{pid2}', 'back to the paper')
    w.submit(f'/papers/{pid2}', '/bookmarks/toggle',
             {'paper_id': str(pid2), 'back': f'/papers/{pid2}'}, 'bookmark')
    mystuff = w.go('/mystuff', 'my stuff')
    w.answer('carol_bookmarks', mystuff.count('paper-row'))
    w.must(mystuff.count('paper-row') == 2, 'premise: carol 2 bookmarks')
    w.done()


def walk_3(w, A, client):
    """Thursday schedule: OS1A talks, PS1P4 window, Friday socials."""
    page = w.go('/schedule', 'schedule (defaults Wed)')
    page = w.click('/schedule?date=2026-04-23', 'day tab THU 23 APR')
    m = re.search(r'Oral Session 1A LLMs and Reasoning.*?<table class="data"[^>]*>(.*?)</table>',
                  page, re.S)
    w.must(m, 'premise: OS1A inline talk table renders')
    rows = re.findall(r'<td class="mono">([^<]+)\u2013([^<]+)</td>'
                      r'\s*<td><a href="/papers/(\d+)">([^<]+)</a></td>', m.group(1))
    w.answer('os1a_talk_count', len(rows))
    w.must(len(rows) == 6, f'premise: OS1A has 6 talks, got {len(rows)}')
    w.answer('os1a_first_title', unescape(rows[0][3]))
    w.answer('os1a_last_title', unescape(rows[-1][3]))
    first_id, last_id = int(rows[0][2]), int(rows[-1][2])
    d1 = w.click(f'/papers/{first_id}', "open first talk's paper")
    f1 = paper_detail_facts(d1)
    w.answer('first_talk_decision', f1['session'] and 'Accept (Oral)')
    w.answer('first_talk_room', f1['room'])
    w.must(f1['room'] == 'Amphitheater', f'premise: room {f1["room"]}')
    w.back('back to Thursday')
    d2 = w.click(f'/papers/{last_id}', "open last talk's paper")
    f2 = paper_detail_facts(d2)
    w.answer('last_talk_slot', f2['talk_slot'])
    w.must(f2['talk_slot'] and '11:30 AM' in f2['talk_slot'],
           f'premise: slot {f2["talk_slot"]}')
    page = w.back('back to Thursday')
    window = session_window_on_schedule(page, 'Poster Session 1 Pavilion 4')
    w.answer('ps1p4_window', f'{window[0]}-{window[1]}')
    page = w.click('/papers?session=Poster%20Session%201%20Pavilion%204',
                   'PS1P4 paper list')
    w.answer('ps1p4_count', paper_count(page))
    pid = first_paper_link(page)
    w.answer('ps1p4_first_position', card_position(page, pid))
    w.go('/login', 'login page')
    w.fill('email')
    w.fill('password')
    w.submit('/login', '/login',
             {'email': 'bob.c@test.com', 'password': 'TestPass123!'}, 'login bob')
    w.go(f'/papers/{last_id}', 'back to last talk paper')
    w.submit(f'/papers/{last_id}', '/bookmarks/toggle',
             {'paper_id': str(last_id), 'back': f'/papers/{last_id}'},
             'bookmark')
    mystuff = w.go('/mystuff', 'my stuff')
    w.answer('bob_bookmarks', mystuff.count('paper-row'))
    w.must(mystuff.count('paper-row') == 2, 'premise: bob 2 bookmarks')
    saved = re.search(r'<h3><a href="/events/\d+">([^<]+)</a></h3>', mystuff)
    w.answer('bob_saved_event', unescape(saved.group(1)))
    page = w.go('/schedule', 'schedule')
    page = w.click('/schedule?date=2026-04-24', 'day tab FRI 24 APR')
    socials = re.findall(r'sched-social', page)
    w.answer('friday_socials', len(socials))
    w.must(len(socials) == 12, f'premise: 12 Friday socials, got {len(socials)}')
    first_social = re.search(r'sched-social.*?<div class="time">(\d\d:\d\d)', page, re.S)
    w.answer('earliest_social_time', first_social.group(1))
    w.done()


def walk_4(w, A, client):
    """workshops hub: Sunday count, VerifAI-2, AI for Peace, ICBINB, dana."""
    page = w.go('/workshops', 'workshops hub')
    rows = re.findall(r'<div class="time">([^<]+)<br>([^<]+)</div>\s*'
                      r'<div class="body">\s*<h3><a href="/events/(\d+)">([^<]+)</a>',
                      page)
    sun = [r for r in rows if 'Apr 26' in r[0]]
    w.answer('sunday_workshops', len(sun))
    w.must(len(sun) == 20, f'premise: 20 Sunday workshops, got {len(sun)}')
    verif = [r for r in rows if r[3].startswith('VerifAI-2')][0]
    page = w.click(f'/events/{verif[2]}', 'open VerifAI-2')
    people = re.findall(r'<p>([^<]+(?:⋅[^<]+)*)</p>', page)
    organizers = [p for p in people if '⋅' in p]
    w.answer('verifai_organizers', unescape(organizers[0]) if organizers else '')
    items = re.findall(r'<td class="mono">([^<]+)</td>\s*<td>([^<]+)</td>', page)
    w.answer('verifai_schedule_items', len(items))
    w.must(len(items) == 18, f'premise: 18 items, got {len(items)}')
    page = w.back('back to the hub')
    peace = [r for r in rows if r[3] == 'AI for Peace'][0]
    page = w.click(f'/events/{peace[2]}', 'open AI for Peace')
    first_item = re.search(r'<td class="mono">([^<]+)</td>\s*<td>([^<]+)</td>', page)
    w.answer('peace_first_time', first_item.group(1))
    w.answer('peace_first_title', unescape(first_item.group(2)))
    aims = [r for r in rows if 'AI for Mechanism Design' in r[3]][0]
    w.go('/login', 'login page')
    w.fill('email')
    w.fill('password')
    w.submit('/login', '/login',
             {'email': 'dana.k@test.com', 'password': 'TestPass123!'}, 'login dana')
    page = w.go('/workshops', 'workshops hub')
    page = w.click(f'/events/{aims[2]}', 'open AIMS')
    w.submit(f'/events/{aims[2]}', '/schedule/save',
             {'event_id': str(aims[2]), 'back': f'/events/{aims[2]}'},
             'save AIMS')
    mystuff = w.go('/mystuff', 'my stuff')
    n = mystuff.count('sched-event')
    w.answer('dana_saved_events', n)
    w.must(n == 2, f'premise: dana ends with 2 saved events, got {n}')
    page = w.go('/schedule', 'schedule')
    page = w.click('/schedule?date=2026-04-27', 'Monday schedule tab')
    monday = len(re.findall(r'sched-workshop', page))
    w.answer('monday_workshops', monday)
    w.must(monday == 20, f'premise: 20 Monday workshops, got {monday}')
    icb = re.search(r'<h3><a href="/events/(\d+)">(I Can[^<]+)</a>', page)
    page = w.click(f'/events/{icb.group(1)}', 'open ICBINB')
    dom = re.search(r'href="(https?://[^/"]+)', page)
    w.answer('icbinb_domain', dom.group(1))
    w.done()


def walk_5(w, A, client):
    """invited talks hub: Bouman bio, Marin, Maja overflow, Karen, alice."""
    page = w.go('/invited-talks', 'invited talks hub')
    talks = re.findall(r'href="/events/(\d+)">([^<]+)</a>', page)
    w.answer('talk_count', len(set(t for _, t in talks)))
    w.must(len(set(t for _, t in talks)) == 7, 'premise: 7 talks')
    bouman = [t for t in talks if t[1] == 'Images of the Hidden Universe'][0]
    page = w.click(f'/events/{bouman[0]}', 'Bouman talk')
    w.answer('bouman_speaker', 'Katherine Bouman')
    w.answer('bouman_bio_university', 'California Institute of Technology')
    w.must('California Institute of Technology' in page, 'premise: bio university')
    page = w.back('back to the talks hub')
    marin = [t for t in talks if t[1].startswith('Marin')][0]
    page = w.click(f'/events/{marin[0]}', 'Marin talk')
    w.answer('marin_speaker', 'Percy Liang')
    w.answer('marin_day', 'Sat, Apr 25, 2026')
    w.answer('marin_start', '5:45 PM')
    w.must('5:45 PM' in page, 'premise: Marin 5:45 PM')
    page = w.back('back to the talks hub')
    maja = [t for t in talks if t[1].startswith('The Challenges')][0]
    page = w.click(f'/events/{maja[0]}', 'open the Thursday 9:00 AM talk')
    w.answer('maja_overflow', '201 A/B')
    w.must('Overflow Room: 201 A/B' in page, 'premise: overflow room')
    page = w.back('back to the talks hub')
    karen = [t for t in talks if t[1].startswith('Learning while developing')][0]
    page = w.click(f'/events/{karen[0]}', 'Karen talk')
    w.answer('karen_speaker', 'Karen E. Adolph')
    w.go('/login', 'login page')
    w.fill('email')
    w.fill('password')
    w.submit('/login', '/login',
             {'email': 'alice.j@test.com', 'password': 'TestPass123!'},
             'login alice')
    page = w.go(f'/events/{marin[0]}', 'back to Marin')
    w.submit(f'/events/{marin[0]}', '/schedule/save',
             {'event_id': str(marin[0]), 'back': f'/events/{marin[0]}'},
             'save Marin')
    mystuff = w.go('/mystuff', 'my stuff')
    n = mystuff.count('sched-event')
    w.answer('alice_saved_events', n)
    w.must(n == 1, f'premise: alice saved 1 event, got {n}')
    w.done()


def walk_6(w, A, client):
    """site search: Susquehanna, Marin event, sponsors, Amazon, blog, ToT."""
    w.fill('search q=Susquehanna')
    page = w.submit('/search', '/search', {'q': 'Susquehanna'}, 'search')
    tier = re.search(r'Susquehanna</a> <span class="muted small">\u2014 ([^<]+)</span>', page)
    w.answer('susquehanna_tier', tier.group(1))
    w.must(tier and 'Diamond' in tier.group(1), f'premise: tier {tier}')
    w.fill('search q=Marin')
    page = w.submit('/search', '/search', {'q': 'Marin'}, 'search')
    event = re.search(r'href="/events/(\d+)">(Marin[^<]+)</a>', page)
    w.answer('marin_event', unescape(event.group(2)))
    page = w.click(f'/events/{event.group(1)}', 'open the Marin event')
    w.answer('marin_speaker', 'Percy Liang')
    w.must('<p>Percy Liang</p>' in page, 'premise: Marin speaker renders')
    w.answer('marin_start', '5:45 PM')
    w.must('5:45 PM' in page, 'premise: Marin 5:45 PM')
    page = w.go('/schedule', 'schedule')
    page = w.click('/schedule?date=2026-04-25', "the talk's day tab")
    window = session_window_on_schedule(page, 'Poster Session 6 Pavilion 3')
    w.answer('ps6p3_window', f'{window[0]}-{window[1]}')
    page = w.go('/sponsors', 'sponsors page')
    names = re.findall(r'<a class="chip" href="[^"]+"[^>]*>([^<]+)</a>', page)
    dd_names = []
    diamond_count = None
    for m in re.finditer(r'<h2>([^<]+)</h2>\s*<div class="chips">(.*?)</div>', page, re.S):
        if m.group(1) == 'Double Diamond':
            dd_names = re.findall(r'<a class="chip"[^>]*>([^<]+)</a>', m.group(2))
        if m.group(1) == 'Diamond':
            diamond_count = len(re.findall(r'<a class="chip"', m.group(2)))
    w.answer('double_diamond_names', ', '.join(dd_names))
    w.answer('diamond_count', diamond_count)
    w.must(dd_names == ['Amazon', 'Tencent'], f'premise: DD {dd_names}')
    w.must(diamond_count == 13, f'premise: Diamond 13, got {diamond_count}')
    w.fill("search q=Amazon")
    page = w.submit('/search', '/search', {'q': 'Amazon'}, "look up Amazon's tier")
    tier = re.search(r'Amazon</a> <span class="muted small">\u2014 ([^<]+)</span>', page)
    w.answer('amazon_tier', tier.group(1))
    page = w.go('/news', 'blog')
    newest = re.search(r'<h2><a href="/news/([^"]+)">([^<]+)</a></h2>\s*'
                       r'<p class="muted small">(\d{4}-\d{2}-\d{2})', page)
    w.answer('newest_post', unescape(newest.group(2)))
    w.answer('newest_date', newest.group(3))
    w.must(newest.group(3) == '2026-09-02', 'premise: newest post date')
    page = w.click(f'/news/{newest.group(1)}', 'open the newest post')
    author = re.search(r'<p class="muted">[^<]+(?:&middot;|\u00b7) ([^<]+)</p>', page)
    w.answer('newest_author', author.group(1).strip() if author else '')
    page = w.back('return to the blog')
    tot_post = re.search(r'<h2><a href="/news/([^"]+)">(Announcing the Test of Time[^<]+)</a></h2>\s*'
                         r'<p class="muted small">(\d{4}-\d{2}-\d{2})', page)
    w.answer('tot_post_title', unescape(tot_post.group(2)))
    w.answer('tot_post_date', tot_post.group(3))
    w.must(tot_post.group(3) == '2026-04-22', 'premise: ToT post date')
    page = w.click(f'/news/{tot_post.group(1)}', 'open the ToT announcement')
    page = w.go('/awards', 'awards page')
    tots = re.findall(r'<span class="badge tier">Test of Time</span>.*?'
                      r'<h3 style="margin:8px 0 4px">([^<]+)</h3>', page, re.S)
    w.answer('tot_titles', ' | '.join(tots))
    w.must(len(tots) == 2, f'premise: 2 ToT titles, got {len(tots)}')
    w.done()


def walk_7(w, A, client):
    """organizers, awards, blog post, Polar Express, Transformers bookmark."""
    page = w.go('/organizers', 'organizers page')
    m = re.search(r'General Chair \(1\)\s*\n(.+?)\n(.+)', page)
    w.answer('gc_name', m.group(1).strip() if m else None)
    w.answer('gc_institution', m.group(2).strip() if m else None)
    m = re.search(r'Program Chairs \((\d+)\)', page)
    w.answer('program_chairs', m.group(1) if m else None)
    m = re.search(r'Ethics Review Chairs \((\d+)\)', page)
    w.answer('ethics_review_chairs', m.group(1) if m else None)
    spc = re.search(r'Senior Program Chair[^<]*</h2>(.*?)</div>', page, re.S)
    w.answer('spc_first_area', ' '.join(spc.group(1).split())[:120] if spc else None)
    page = w.go('/awards', 'awards page')
    outs = re.findall(r'<span class="badge tier">Outstanding Paper</span>.*?'
                      r'<h3 style="margin:8px 0 4px">([^<]+)</h3>', page, re.S)
    w.answer('outstanding_titles', ' | '.join(outs))
    hm = re.search(r'Honorable Mention</span>.*?<h3 style="margin:8px 0 4px">([^<]+)</h3>.*?'
                   r'<p class="muted small">([^<]+)</p>', page, re.S)
    w.answer('hm_title', unescape(hm.group(1)) if hm else None)
    w.answer('hm_first_author', unescape(hm.group(2)) if hm else None)
    page = w.go('/news', 'blog')
    outstanding_post = re.search(
        r'<h2><a href="/news/([^"]+)">(Announcing the ICLR 2026 Outstanding Papers)</a></h2>',
        page)
    page = w.click(f'/news/{outstanding_post.group(1)}', 'outstanding papers post')
    author = re.search(r'<p class="muted">[^<]+(?:&middot;|\u00b7) ([^<]+)</p>', page)
    w.answer('outstanding_post_author', author.group(1).strip() if author else '')
    page = w.go('/papers', 'papers browser')
    w.fill('search q=Polar Express')
    page = w.submit('/papers', '/papers', {'q': 'Polar Express', 'sort': 'title'},
                    'search Polar Express')
    pid = first_paper_link(page)
    w.must(pid == 10006553, f'premise: first match is the poster row, got {pid}')
    detail = w.click(f'/papers/{pid}', 'open the first match')
    facts = paper_detail_facts(detail)
    w.answer('polar_session', facts['session'])
    w.answer('polar_decision', facts['session'] and 'Accept (Oral)')
    w.answer('polar_position', facts['position'])
    w.must(facts['position'] == 'P3-#407',
           f'premise: poster row position {facts["position"]}')
    w.go('/login', 'login page')
    w.fill('email')
    w.fill('password')
    w.submit('/login', '/login',
             {'email': 'carol.d@test.com', 'password': 'TestPass123!'},
             'login carol')
    page = w.go('/papers', 'papers browser')
    w.fill('search q=Transformers are Inherently Succinct')
    page = w.submit('/papers', '/papers',
                    {'q': 'Transformers are Inherently Succinct', 'sort': 'title'},
                    'search Transformers')
    tid = first_paper_link(page)
    w.must(tid == 10008853, f'premise: first match is the poster row, got {tid}')
    detail = w.click(f'/papers/{tid}', 'open the first match')
    w.submit(f'/papers/{tid}', '/bookmarks/toggle',
             {'paper_id': str(tid), 'back': f'/papers/{tid}'}, 'bookmark')
    mystuff = w.go('/mystuff', 'my stuff')
    w.answer('carol_bookmarks', mystuff.count('paper-row'))
    w.must(mystuff.count('paper-row') == 2, 'premise: carol 2 bookmarks')
    w.done()


def walk_8(w, A, client):
    """awards, outstanding post, keynotes, newest post, Transformers paper."""
    page = w.go('/awards', 'awards page')
    outs = re.findall(r'<span class="badge tier">Outstanding Paper</span>.*?'
                      r'<h3 style="margin:8px 0 4px">([^<]+)</h3>.*?'
                      r'<p class="muted small">([^<]+)</p>', page, re.S)
    w.answer('outstanding_firsts', ' | '.join(f'{t}~{a}' for t, a in outs))
    tots = re.findall(r'<span class="badge tier">Test of Time</span>.*?'
                      r'<h3 style="margin:8px 0 4px">([^<]+)</h3>.*?'
                      r'<p class="muted small">([^<]+)</p>', page, re.S)
    w.answer('tot_firsts', ' | '.join(f'{t}~{a}' for t, a in tots))
    page = w.go('/news', 'blog')
    outstanding_post = re.search(
        r'<h2><a href="/news/([^"]+)">(Announcing the ICLR 2026 Outstanding Papers)</a></h2>', page)
    page = w.click(f'/news/{outstanding_post.group(1)}', 'open the Outstanding Papers post')
    chair = re.search(r'Outstanding Paper Committee[^:]*:\s*<[^>]*>?([^,<]+)', page)
    m = re.search(r'Selected by the Outstanding Paper Committee:\s*(.*?)\.', page)
    w.answer('committee_chair', m.group(1).split(',')[0] if m else None)
    page = w.back('back to the blog')
    keynotes = re.search(r'<h2><a href="/news/([^"]+)">(Announcing the ICLR 2026 keynotes)</a></h2>', page)
    page = w.click(f'/news/{keynotes.group(1)}', 'open the keynotes announcement')
    talks = re.findall(r'<h3[^>]*>([^<]+)</h3>', page)
    w.answer('keynote_talks', len(talks))
    w.answer('first_keynote_day', 'Thu' if 'Thursday' in page or 'Thu,' in page else None)
    page = w.back('back to the blog')
    newest = re.search(r'<h2><a href="/news/([^"]+)">([^<]+)</a></h2>\s*'
                       r'<p class="muted small">(\d{4}-\d{2}-\d{2})', page)
    w.answer('newest_title', unescape(newest.group(2)))
    page = w.click(f'/news/{newest.group(1)}', 'open the newest post')
    m = re.search(r'(\d+)\s+page', page) or re.search(r'(\d+)\s+submission', page) \
        or re.search(r'limit of\s+(\d+)', page)
    w.answer('submission_limit', m.group(1) if m else None)
    w.go('/login', 'login page')
    w.fill('email')
    w.fill('password')
    w.submit('/login', '/login',
             {'email': 'alice.j@test.com', 'password': 'TestPass123!'},
             'login alice')
    page = w.go('/papers', 'papers browser')
    w.fill('search q=Transformers are Inherently Succinct')
    page = w.submit('/papers', '/papers',
                    {'q': 'Transformers are Inherently Succinct', 'sort': 'title'},
                    'search Transformers')
    tid = first_paper_link(page)
    w.must(tid == 10008853, f'premise: first match is the poster row, got {tid}')
    detail = w.click(f'/papers/{tid}', 'open the first match')
    facts = paper_detail_facts(detail)
    w.answer('transformers_session', facts['session'])
    w.answer('transformers_bookmarked', 'Bookmarked' if 'Bookmarked' in detail else 'not bookmarked')
    page = w.click(f'/papers?session={quote(facts["session"])}',
                   "the session's paper list")
    w.answer('session_count', paper_count(page))
    w.done()


def walk_9(w, A, client):
    """registration: banquet price, invalid combo, valid, alice's code."""
    page = w.go('/register', 'registration page')
    w.answer('banquet_price', re.search(r'\$(\d+) USD each', page).group(1))
    w.answer('affiliation_types', ' | '.join(re.findall(
        r'<option value="([^"]+)">', page)))
    w.fill('name')
    w.fill('email')
    w.select('affiliation')
    w.check('item Conference Sessions and Workshops')
    w.check('second item')
    page = w.submit('/register', '/register', {
        'name': 'Reg Tester', 'email': 'reg@test.com',
        'affiliation': 'Full time student',
        'items': ['Conference Sessions and Workshops', 'Sunday Workshop 1 Day Pass'],
        'banquet_tickets': '0'}, 'invalid combination')
    w.must('do not' in page.lower(), 'premise: exclusivity error renders')
    w.answer('exclusivity_error', 'shown')
    w.uncheck('uncheck second item')
    w.fill('two banquet tickets')
    page = w.submit('/register', '/register', {
        'name': 'Reg Tester', 'email': 'reg@test.com',
        'affiliation': 'Full time student',
        'items': ['Conference Sessions and Workshops'],
        'banquet_tickets': '2'}, 'valid registration')
    code = re.search(r'ICLR26-[0-9A-F]{8}', page)
    w.answer('reg_code', code.group(0))
    w.answer('reg_total', '100')
    w.must(code and '$100' in page, 'premise: code and $100 total render')
    w.go('/login', 'login page')
    w.fill('email')
    w.fill('password')
    w.submit('/login', '/login',
             {'email': 'alice.j@test.com', 'password': 'TestPass123!'}, 'login alice')
    mystuff = w.go('/mystuff', 'my stuff')
    line = mystuff_reg_line(mystuff, 'ICLR26-A1B2C3D4')
    w.answer('alice_reg_line', line)
    w.must('ICLR26-A1B2C3D4' in mystuff and '$50 USD' in mystuff,
           'premise: alice seed registration renders')
    w.done()


def walk_10(w, A, client):
    """signup, Escaping Policy Contraction, bookmark persistence."""
    w.go('/signup', 'signup page')
    w.fill('name')
    w.fill('email')
    w.fill('password')
    w.submit('/signup', '/signup',
             {'name': 'Rosa Parks', 'email': 'rosa.p@test.com',
              'password': 'RosaPass123!'}, 'create profile')
    page = w.go('/papers', 'papers browser')
    w.fill('search q=Escaping Policy Contraction')
    page = w.submit('/papers', '/papers',
                    {'q': 'Escaping Policy Contraction', 'sort': 'title'},
                    'search')
    pid = first_paper_link(page)
    detail = w.click(f'/papers/{pid}', 'open the match')
    facts = paper_detail_facts(detail)
    w.answer('epc_session', facts['session'])
    w.answer('epc_position', facts['position'])
    w.submit(f'/papers/{pid}', '/bookmarks/toggle',
             {'paper_id': str(pid), 'back': f'/papers/{pid}'}, 'bookmark')
    mystuff = w.go('/mystuff', 'my stuff')
    w.answer('rosa_bookmarks', mystuff.count('paper-row'))
    w.must(mystuff.count('paper-row') == 1, 'premise: 1 bookmark')
    w.click('/logout', 'log out')
    w.go('/login', 'login page')
    w.fill('email')
    w.fill('password')
    w.submit('/login', '/login',
             {'email': 'rosa.p@test.com', 'password': 'RosaPass123!'},
             'log back in')
    mystuff = w.go('/mystuff', 'my stuff')
    n = mystuff.count('paper-row')
    s = mystuff.count('sched-event')
    w.answer('rosa_after_relogin', f'{n} bookmarks, {s} saved events')
    w.must(n == 1 and s == 0, f'premise: persisted 1 bookmark, 0 events, got {n}/{s}')
    badge = re.search(r'badge oral">([^<]+)<', mystuff)
    w.answer('bookmarked_decision', badge.group(1) if badge else None)
    w.done()


def walk_11(w, A, client):
    """FAQ badge fee, luggage search -> venue, dates, policies post, helpdesk."""
    page = w.go('/faq', 'faq')
    fee = re.search(r'Badge Replacement Policy.*?1st Time: Badge Replacement Fee \$?(\d+)', page, re.S)
    w.answer('badge_replacement_fee', fee.group(1) if fee else None)
    w.must(fee and fee.group(1) == '100', 'premise: $100 badge fee')
    w.fill('search q=luggage')
    page = w.submit('/search', '/search', {'q': 'luggage'}, 'search luggage')
    hits = venue_hits_on_search(page)
    w.answer('luggage_result_types', ', '.join(search_sections(page)))
    w.must(hits, 'premise: luggage hits the Conference site section (F-2 fix)')
    page = w.click('/venue', 'open the conference site result')
    lost = re.search(r'Lost Badge Fee - USD \$(\d+)', page)
    w.answer('lost_badge_fee', lost.group(1))
    w.must(lost and lost.group(1) == '100', 'premise: lost badge fee $100')
    luggage = re.search(r'April 24 through 27 ([^<]+)', page)
    w.answer('luggage_hours', luggage.group(1).strip())
    w.must(luggage and '7am-5:30pm' in luggage.group(1),
           f'premise: luggage hours {luggage and luggage.group(1)}')
    page = w.go('/dates', 'dates page')

    def date_of(name):
        m = re.search(rf'{re.escape(name)}</td><td class="mono">([^<]+)</td>', page)
        return unescape(m.group(1)).strip() if m else None

    w.answer('dietary_deadline', date_of('Dietary Preference Deadline'))
    w.answer('cancellation_deadline', date_of('Registration Cancellation Deadline'))
    w.must(date_of('Dietary Preference Deadline'),
           'premise: dietary preference deadline renders')
    w.must(date_of('Registration Cancellation Deadline'),
           'premise: cancellation deadline renders')
    w.fill('search q=policies')
    page = w.submit('/search', '/search', {'q': 'policies'}, 'search policies')
    posts = re.findall(r'<a href="/news/([^"]+)">([^<]+)</a>\s*'
                       r'<span class="muted small">\u2014 (\d{4}-\d{2}-\d{2})', page)
    w.answer('policies_hits', len(posts))
    oldest = min(posts, key=lambda p: p[2])
    w.answer('oldest_policies_post', unescape(oldest[1]))
    w.must(oldest[1] == 'Policies on Large Language Model Usage at ICLR 2026',
           f'premise: oldest policies post {oldest[1]}')
    page = w.click(f'/news/{oldest[0]}', 'open the oldest matching announcement')
    w.answer('oldest_post_title', unescape(re.search(r'<h1[^>]*>([^<]+)</h1>', page).group(1)))
    w.go('/helpdesk', 'helpdesk')
    w.fill('name')
    w.fill('email')
    w.check('topic radio')
    w.fill('subject')
    w.fill('body')
    page = w.submit('/helpdesk', '/helpdesk',
                    {'name': 'Help Tester', 'email': 'help@test.com',
                     'topic': 'workshop-chairs@iclr.cc',
                     'subject': 'Workshop question',
                     'body': 'Do Sunday passes include virtual access?'},
                    'send message')
    w.answer('helpdesk_confirmation', 'sent' if 'has been sent' in page else None)
    w.must('has been sent' in page, 'premise: helpdesk confirmation')
    page = w.go('/helpdesk', 'back to the helpdesk form for the topic list')
    visa = re.search(r'value="([^"]+)"[^>]*>\s*([^<]*Visa Support[^<]*)', page)
    press = re.search(r'value="([^"]+)"[^>]*>\s*([^<]*Press)', page)
    w.answer('visa_topic', visa.group(2).strip() if visa else None)
    w.answer('press_topic', press.group(2).strip() if press else None)
    w.done()


def walk_12(w, A, client):
    """dates 2027/2026, Riocentro search, sponsors, venue, faq, alice reg."""
    page = w.go('/dates', 'dates page')

    def date_of(name):
        m = re.search(rf'{re.escape(name)}</td><td class="mono">([^<]+)</td>', page)
        return unescape(m.group(1)).strip() if m else None

    w.answer('abstract_deadline', date_of('Abstract Deadline'))
    w.answer('paper_deadline', date_of('Paper Deadline'))
    w.answer('final_decisions', date_of('Final Decisions'))
    w.answer('reg_open', date_of('Registration Open'))
    w.answer('early_reg', date_of('Early Registration Deadline'))
    w.must(date_of('Abstract Deadline') and date_of('Final Decisions'),
           'premise: 2027 deadlines render')
    w.must(date_of('Registration Open'), 'premise: 2026 registration dates render')
    w.fill('search q=Riocentro')
    page = w.submit('/search', '/search', {'q': 'Riocentro'}, 'search Riocentro')
    hits = venue_hits_on_search(page)
    w.answer('riocentro_result_types', ', '.join(search_sections(page)))
    w.must(hits, 'premise: Riocentro now hits the Conference site section (F-2 fix)')
    w.fill('search q=Amazon')
    page = w.submit('/search', '/search', {'q': 'Amazon'}, 'search Amazon')
    tier = re.search(r'Amazon</a> <span class="muted small">\u2014 ([^<]+)</span>', page)
    w.answer('amazon_tier_search', tier.group(1))
    page = w.go('/sponsors', 'sponsors page')
    tier = re.search(r'Amazon</a>', page)
    dd = re.findall(r'Double Diamond.*?<a class="chip"[^>]*>Amazon</a>', page, re.S)
    w.answer('amazon_tier', 'Double Diamond' if dd else None)
    w.must(dd, 'premise: Amazon is Double Diamond')
    page = w.go('/venue', 'conference site page')
    lost = re.search(r'Lost Badge Fee - USD \$(\d+)', page)
    w.answer('lost_badge_fee', lost.group(1))
    luggage = re.search(r'April 24 through 27 ([^<]+)', page)
    w.answer('luggage_hours', luggage.group(1).strip())
    page = w.go('/faq', 'faq')
    fee = re.search(r'Badge Replacement Policy.*?1st Time: Badge Replacement Fee \$?(\d+)', page, re.S)
    w.answer('badge_replacement_fee', fee.group(1) if fee else None)
    page = w.go('/papers', 'papers browser')
    w.fill('search q=Polar Express')
    page = w.submit('/papers', '/papers', {'q': 'Polar Express', 'sort': 'title'},
                    'search Polar Express')
    pid = first_paper_link(page)
    w.must(pid == 10006553, f'premise: first match is the poster row, got {pid}')
    w.answer('polar_decision', 'Accept (Oral)')
    w.go('/login', 'login page')
    w.fill('email')
    w.fill('password')
    w.submit('/login', '/login',
             {'email': 'alice.j@test.com', 'password': 'TestPass123!'},
             'login alice')
    mystuff = w.go('/mystuff', 'my stuff')
    line = mystuff_reg_line(mystuff, 'ICLR26-A1B2C3D4')
    w.answer('alice_reg_line', line)
    w.answer('alice_bookmarks', mystuff.count('paper-row'))
    w.must(mystuff.count('paper-row') == 3, 'premise: alice 3 bookmarks')
    w.done()


def walk_13(w, A, client):
    """site search tour: Riocentro->venue, Outstanding, Amazon, Jane Street,
    VerifAI workshop, Polar Express first match."""
    w.fill('search q=Riocentro')
    page = w.submit('/search', '/search', {'q': 'Riocentro'}, 'search Riocentro')
    hits = venue_hits_on_search(page)
    w.answer('riocentro_result_types', ', '.join(search_sections(page)))
    w.must(hits, 'premise: Riocentro now hits the Conference site section (F-2 fix)')
    page = w.click('/venue', 'open the conference site page result')
    nxt = re.search(r'Looking ahead \u2014 ICLR 2027</h2>\s*<p><b>([^<]+)</b>'
                    r'\s*\u2014 ([^,]+), ([^<]+)</p>', page)
    w.answer('iclr2027_location', nxt.group(2).strip() if nxt else None)
    w.answer('iclr2027_dates', nxt.group(3).strip() if nxt else None)
    w.must(nxt and 'California' in nxt.group(2),
           f'premise: 2027 location renders ({nxt and nxt.group(2)})')
    w.fill('search q=Outstanding')
    page = w.submit('/search', '/search', {'q': 'Outstanding'}, 'search Outstanding')
    posts = re.findall(r'<a href="/news/([^"]+)">([^<]+)</a>\s*'
                       r'<span class="muted small">\u2014 (\d{4}-\d{2}-\d{2})', page)
    newest = max(posts, key=lambda p: p[2])
    w.answer('outstanding_post', unescape(newest[1]))
    w.must(newest[1] == 'Announcing the ICLR 2026 Outstanding Papers',
           f'premise: newest outstanding post {newest[1]}')
    page = w.click(f'/news/{newest[0]}', 'open the newest matching announcement')
    m = re.search(r'<p class="muted">([^<]+)(?:&middot;|\u00b7)\s*([^<]+)</p>', page) or \
        re.search(r'<p class="muted">([^<]+)&middot; ([^<]+)</p>', page)
    date_m = re.search(r'(\w{3}, \w{3} \d{1,2}, \d{4})', page)
    w.answer('outstanding_date', date_m.group(1) if date_m else newest[2])
    w.answer('outstanding_author', m.group(2).strip() if m else None)
    w.fill('search q=Amazon')
    page = w.submit('/search', '/search', {'q': 'Amazon'}, 'search Amazon')
    tier = re.search(r'Amazon</a> <span class="muted small">\u2014 ([^<]+)</span>', page)
    w.answer('amazon_tier', tier.group(1))
    w.fill('search q=Jane Street')
    page = w.submit('/search', '/search', {'q': 'Jane Street'}, 'search Jane Street')
    tier = re.search(r'Jane Street</a> <span class="muted small">\u2014 ([^<]+)</span>', page)
    w.answer('jane_street_tier', tier.group(1))
    w.must(tier and tier.group(1) == 'Diamond',
           f'premise: Jane Street is Diamond, got {tier and tier.group(1)}')
    w.fill('search q=VerifAI')
    page = w.submit('/search', '/search', {'q': 'VerifAI'}, 'search VerifAI')
    ev = re.search(r'href="/events/(\d+)">([^<]*VerifAI[^<]*)</a>', page)
    w.answer('verifai_event', unescape(ev.group(2)))
    page = w.click(f'/events/{ev.group(1)}', 'open the matching workshop')
    day = re.search(r'<p class="muted">([^<]*Sun[^<]*)</p>', page) or \
        re.search(r'(Sun, Apr 26, 2026)', page)
    w.answer('verifai_day', day.group(1) if day else None)
    start = re.search(r'(\d{1,2}:\d{2} [AP]M)\s*\u2013', page)
    w.answer('verifai_start', start.group(1) if start else None)
    items = re.findall(r'<td class="mono">([^<]+)</td>\s*<td>([^<]+)</td>', page)
    w.answer('verifai_items', len(items))
    w.must(len(items) == 18, f'premise: 18 schedule items, got {len(items)}')
    w.fill('search q=Polar Express')
    page = w.submit('/papers', '/papers', {'q': 'Polar Express', 'sort': 'title'},
                    'papers search Polar Express')
    pid = first_paper_link(page)
    w.must(pid == 10006553, f'premise: first match is the poster row, got {pid}')
    detail = w.click(f'/papers/{pid}', 'open the first match')
    facts = paper_detail_facts(detail)
    w.answer('polar_decision', facts['session'] and 'Accept (Oral)')
    w.done()


def walk_14(w, A, client):
    """schedule tour: Wednesday, Sunday workshops, Monday, Saturday town hall."""
    page = w.go('/schedule', 'schedule (defaults Wed Apr 22)')
    kinds = set(re.findall(r'sched-(\w+)"', page))
    w.answer('wednesday_kind', 'workshops only' if 'workshop' in kinds else ', '.join(kinds))
    page = w.go('/schedule?date=2026-04-26', 'Sunday')
    ws = re.findall(r'sched-workshop', page)
    w.answer('sunday_workshops', len(ws))
    w.must(len(ws) == 20, f'premise: 20 Sunday workshops, got {len(ws)}')
    first = re.search(r'sched-workshop.*?<h3><a href="/events/(\d+)">([^<]+)</a>', page, re.S)
    page = w.click(f'/events/{first.group(1)}', 'open the first workshop')
    people = re.findall(r'<p>([^<]+(?:⋅[^<]+)*)</p>', page)
    organizers = [p for p in people if '⋅' in p]
    w.answer('first_workshop_organizers', unescape(organizers[0]) if organizers else '')
    page = w.go('/schedule?date=2026-04-27', 'Monday')
    ws = re.findall(r'sched-workshop', page)
    w.answer('monday_workshops', len(ws))
    w.must(len(ws) == 20, f'premise: 20 Monday workshops, got {len(ws)}')
    icb = re.search(r'<h3><a href="/events/(\d+)">(I Can[^<]+)</a>', page)
    page = w.click(f'/events/{icb.group(1)}', 'open ICBINB')
    start = re.search(r'(\d{1,2}:\d{2} [AP]M)\s*\u2013', page)
    w.answer('icbinb_start', start.group(1) if start else None)
    first_item = re.search(r'<td class="mono">([^<]+)</td>\s*<td>([^<]+)</td>', page)
    w.answer('icbinb_first_item', unescape(first_item.group(2)))
    page = w.go('/schedule?date=2026-04-25', 'Saturday')
    town = re.search(r'<h3><a href="/events/(\d+)">(.*?Town Hall[^<]*)</a>', page)
    page = w.click(f'/events/{town.group(1)}', 'open the Town Hall event')
    start = re.search(r'(\d{1,2}:\d{2} [AP]M)\s*\u2013', page)
    w.answer('townhall_start', start.group(1) if start else None)
    abstract = re.search(r'<p class="small">([^<]+)</p>', page)
    w.answer('townhall_abstract', abstract.group(1)[:120] if abstract else None)
    w.go('/login', 'login page')
    w.fill('email')
    w.fill('password')
    w.submit('/login', '/login',
             {'email': 'bob.c@test.com', 'password': 'TestPass123!'}, 'login bob')
    page = w.go(f'/events/{town.group(1)}', 'back to the Town Hall')
    w.submit(f'/events/{town.group(1)}', '/schedule/save',
             {'event_id': str(town.group(1)), 'back': f'/events/{town.group(1)}'},
             'save the Town Hall')
    mystuff = w.go('/mystuff', 'my stuff')
    titles = re.findall(r'<h3><a href="/events/\d+">([^<]+)</a></h3>', mystuff)
    w.answer('bob_saved_events', len(titles))
    w.answer('bob_saved_titles', ' | '.join(unescape(t) for t in titles))
    w.must(len(titles) == 2, f'premise: bob 2 saved events, got {len(titles)}')
    w.done()


def walk_15(w, A, client):
    """papers totals, oral count, PS3P3, dana bookmarks."""
    page = w.go('/papers', 'papers browser')
    total = paper_count(page)
    w.answer('total_papers', total)
    w.must(total == 5691, f'premise: 5691 papers, got {total}')
    w.select('oral decisions')
    page = w.submit('/papers', '/papers', {'decision': 'Accept (Oral)'},
                    'apply oral filter')
    orals = paper_count(page)
    w.answer('oral_count', orals)
    w.must(orals == 447, f'premise: 447 orals, got {orals}')
    w.select('reset decision')
    w.select('PS3P3 session')
    page = w.submit('/papers', '/papers',
                    {'session': 'Poster Session 3 Pavilion 3', 'sort': 'title'},
                    'PS3P3 filter')
    n = paper_count(page)
    w.answer('ps3p3_count', n)
    pid = first_paper_link(page)
    detail = w.click(f'/papers/{pid}', 'open the first result')
    facts = paper_detail_facts(detail)
    w.answer('first_position', facts['position'])
    w.answer('first_author_institution', facts['authors'][0][1])
    w.go('/login', 'login page')
    w.fill('email')
    w.fill('password')
    w.submit('/login', '/login',
             {'email': 'dana.k@test.com', 'password': 'TestPass123!'}, 'login dana')
    mystuff = w.go('/mystuff', 'my stuff')
    w.answer('dana_bookmarks', mystuff.count('paper-row'))
    w.answer('dana_saved', mystuff.count('sched-event'))
    w.must(mystuff.count('paper-row') == 2 and mystuff.count('sched-event') == 1,
           'premise: dana 2 bookmarks 1 event')
    w.go(f'/papers/{pid}', 'back to the first result')
    w.submit(f'/papers/{pid}', '/bookmarks/toggle',
             {'paper_id': str(pid), 'back': f'/papers/{pid}'}, 'bookmark')
    mystuff = w.go('/mystuff', 'my stuff')
    w.answer('dana_bookmarks_after', mystuff.count('paper-row'))
    w.must(mystuff.count('paper-row') == 3, 'premise: dana 3 bookmarks after')
    w.done()


def walk_16(w, A, client):
    """awards -> LLMs Get Lost -> papers browser -> session -> alice."""
    page = w.go('/awards', 'awards page')
    llm = re.search(r'<span class="badge tier">Outstanding Paper</span>.*?'
                    r'<h3 style="margin:8px 0 4px">(LLMs Get Lost[^<]+)</h3>', page, re.S)
    w.answer('llm_award_title', unescape(llm.group(1)))
    other = re.findall(r'<span class="badge tier">Outstanding Paper</span>.*?'
                       r'<h3 style="margin:8px 0 4px">([^<]+)</h3>.*?'
                       r'<p class="muted small">([^<]+)</p>', page, re.S)
    w.answer('outstanding_firsts', ' | '.join(f'{t}~{a}' for t, a in other))
    tots = re.findall(r'<span class="badge tier">Test of Time</span>.*?'
                      r'<h3 style="margin:8px 0 4px">([^<]+)</h3>', page, re.S)
    w.answer('tot_titles', ' | '.join(tots))
    page = w.go('/papers', 'papers browser')
    w.fill('search q=LLMs Get Lost')
    page = w.submit('/papers', '/papers',
                    {'q': 'LLMs Get Lost In Multi-Turn Conversation', 'sort': 'title'},
                    'search its title')
    pid = first_paper_link(page)
    w.must(pid == 10009146, f'premise: first match is the poster row, got {pid}')
    detail = w.click(f'/papers/{pid}', 'open the first match')
    facts = paper_detail_facts(detail)
    w.answer('llm_session', facts['session'])
    w.answer('llm_decision', facts['session'] and 'Accept (Oral)')
    w.answer('llm_position', facts['position'])
    w.must(facts['position'] == 'P3-#1505',
           f'premise: poster row position {facts["position"]}')
    page = w.go('/schedule', 'schedule')
    page = w.click(f'/schedule?date={A.Paper.query.get(pid).day}', "the session's day tab")
    window = session_window_on_schedule(page, facts['session'])
    w.answer('llm_session_window', f'{window[0]}-{window[1]}')
    page = w.click(f'/papers?session={quote(facts["session"])}',
                   "the session's paper list")
    w.answer('session_count', paper_count(page))
    first_id = first_paper_link(page)
    w.answer('session_first_position', card_position(page, first_id))
    page = w.go('/awards', 'back to the awards page')
    w.go('/login', 'login page')
    w.fill('email')
    w.fill('password')
    w.submit('/login', '/login',
             {'email': 'alice.j@test.com', 'password': 'TestPass123!'}, 'login alice')
    mystuff = w.go('/mystuff', 'my stuff')
    w.answer('alice_saved_events', mystuff.count('sched-event'))
    w.must(mystuff.count('sched-event') == 0, 'premise: alice 0 saved events')
    w.done()


def walk_17(w, A, client):
    """carol: mystuff counts, add AI for Peace, remove Marin, bookmark."""
    w.go('/login', 'login page')
    w.fill('email')
    w.fill('password')
    w.submit('/login', '/login',
             {'email': 'carol.d@test.com', 'password': 'TestPass123!'}, 'login carol')
    mystuff = w.go('/mystuff', 'my stuff')
    n = mystuff.count('paper-row')
    s = mystuff.count('sched-event')
    titles = re.findall(r'<h3><a href="/events/\d+">([^<]+)</a></h3>', mystuff)
    w.answer('carol_bookmarks', n)
    w.answer('carol_saved', s)
    w.answer('carol_saved_titles', ' | '.join(unescape(t) for t in titles))
    w.must(n == 1 and s == 2, f'premise: carol 1 bookmark 2 events, got {n}/{s}')
    page = w.go('/workshops', 'workshops hub')
    peace = re.search(r'<h3><a href="/events/(\d+)">(AI for Peace)</a>', page)
    page = w.click(f'/events/{peace.group(1)}', 'open AI for Peace')
    w.submit(f'/events/{peace.group(1)}', '/schedule/save',
             {'event_id': str(peace.group(1)), 'back': f'/events/{peace.group(1)}'},
             'add AI for Peace')
    mystuff = w.go('/mystuff', 'my stuff')
    w.answer('carol_saved_after_add', mystuff.count('sched-event'))
    w.must(mystuff.count('sched-event') == 3, 'premise: 3 events after add')
    marin = re.search(r'<h3><a href="/events/(\d+)">(Marin[^<]+)</a>', mystuff)
    page = w.click(f'/events/{marin.group(1)}', 'open the saved Marin talk')
    w.submit(f'/events/{marin.group(1)}', '/schedule/save',
             {'event_id': str(marin.group(1)), 'back': f'/events/{marin.group(1)}'},
             'remove Marin')
    mystuff = w.go('/mystuff', 'my stuff')
    w.answer('carol_saved_after_remove', mystuff.count('sched-event'))
    w.must(mystuff.count('sched-event') == 2, 'premise: 2 events after remove')
    page = w.go('/papers', 'papers browser')
    w.fill('search q=LLMs Get Lost')
    page = w.submit('/papers', '/papers',
                    {'q': 'LLMs Get Lost In Multi-Turn Conversation', 'sort': 'title'},
                    'search LLMs Get Lost')
    pid = first_paper_link(page)
    w.must(pid == 10009146, f'premise: first match is the poster row, got {pid}')
    detail = w.click(f'/papers/{pid}', 'open the first match')
    w.submit(f'/papers/{pid}', '/bookmarks/toggle',
             {'paper_id': str(pid), 'back': f'/papers/{pid}'}, 'bookmark')
    mystuff = w.go('/mystuff', 'my stuff')
    w.answer('carol_bookmarks_final', mystuff.count('paper-row'))
    w.must(mystuff.count('paper-row') == 2, 'premise: carol 2 bookmarks final')
    w.done()


def walk_18(w, A, client):
    """bob registers; exclusivity rule; alice's registration name/affiliation."""
    w.go('/login', 'login page')
    w.fill('email')
    w.fill('password')
    w.submit('/login', '/login',
             {'email': 'bob.c@test.com', 'password': 'TestPass123!'}, 'login bob')
    page = w.go('/register', 'registration page')
    w.fill('name')
    w.fill('email')
    w.select('affiliation Academic')
    w.check('Sunday Workshop 1 Day Pass')
    w.fill('one banquet ticket')
    w.fill('dietary Halal')
    page = w.submit('/register', '/register', {
        'name': 'Bob Chen', 'email': 'bob.c@test.com', 'affiliation': 'Academic',
        'items': ['Sunday Workshop 1 Day Pass'], 'banquet_tickets': '1',
        'dietary': 'Halal'}, 'submit registration')
    code = re.search(r'ICLR26-[0-9A-F]{8}', page)
    w.answer('bob_reg_code', code.group(0))
    w.answer('bob_reg_total', '50')
    w.must(code and '$50' in page, 'premise: bob code + $50 total')
    mystuff = w.go('/mystuff', 'my stuff')
    regs = re.findall(r'ICLR26-[0-9A-F]{8}', mystuff)
    w.answer('bob_registrations', len(regs))
    line = mystuff_reg_line(mystuff, code.group(0))
    w.answer('bob_reg_items', line)
    w.must(len(regs) == 1, f'premise: bob has 1 registration, got {len(regs)}')
    page = w.go('/register', 'registration page for the exclusivity rule')
    m = re.search(r'If you choose Conference Sessions and Workshops[^<]*', page)
    w.answer('exclusivity_rule', m.group(0) if m else None)
    w.must(m, 'premise: exclusivity rule prints on the registration page')
    w.click('/logout', 'log out')
    w.go('/login', 'login page')
    w.fill('email')
    w.fill('password')
    w.submit('/login', '/login',
             {'email': 'alice.j@test.com', 'password': 'TestPass123!'}, 'login alice')
    mystuff = w.go('/mystuff', 'my stuff')
    line = mystuff_reg_line(mystuff, 'ICLR26-A1B2C3D4')
    w.answer('alice_reg_line', line)
    m = re.search(r'ICLR26-A1B2C3D4</b> \u2014 ([^(]+)\(([^)]+)\)', mystuff)
    w.answer('alice_registrant_name', m.group(1).strip() if m else None)
    w.answer('alice_registrant_affiliation', m.group(2).strip() if m else None)
    w.must(m and m.group(1).strip() == 'Alice Johnson' and
           m.group(2).strip() == 'Full time student',
           f'premise: registrant name + affiliation render in My Stuff (F-3 fix), '
           f'got {m and (m.group(1), m.group(2))}')
    w.done()


def walk_19(w, A, client):
    """home banner, Personality Subnetworks, dana bookmark toggle, schedule."""
    # the conference home is the free initial load; the banner is read there
    r = client.get('/')
    assert r.status_code == 200
    page = text(r)
    city = re.search(r'Rio de Janeiro', page)
    banner = re.search(r'Sunday April 26 through Monday April 27', page) or \
        re.search(r'(Sunday[^<]*Monday[^<]*)', page)
    w.answer('conference_city', 'Rio de Janeiro' if city else None)
    w.answer('workshop_days', banner.group(1) if banner else None)
    w.must(city, 'premise: home banner city')
    page = w.go('/papers', 'papers browser')
    w.fill('search q=Personality Subnetworks')
    page = w.submit('/papers', '/papers',
                    {'q': 'Personality Subnetworks', 'sort': 'title'}, 'search')
    pid = first_paper_link(page)
    detail = w.click(f'/papers/{pid}', 'open the match')
    facts = paper_detail_facts(detail)
    w.answer('psn_session', facts['session'])
    w.answer('psn_position', facts['position'])
    w.go('/login', 'login page')
    w.fill('email')
    w.fill('password')
    w.submit('/login', '/login',
             {'email': 'dana.k@test.com', 'password': 'TestPass123!'}, 'login dana')
    mystuff = w.go('/mystuff', 'my stuff')
    w.answer('psn_in_bookmarks', str(pid in [int(x) for x in
               re.findall(r'href="/papers/(\d+)"', mystuff)]))
    page = w.click(f'/papers/{pid}', 'open the bookmarked paper')
    w.submit(f'/papers/{pid}', '/bookmarks/toggle',
             {'paper_id': str(pid), 'back': f'/papers/{pid}'}, 'remove it')
    mystuff = w.go('/mystuff', 'my stuff')
    w.answer('dana_bookmarks_after', mystuff.count('paper-row'))
    w.must(mystuff.count('paper-row') == 1, 'premise: dana 1 bookmark after remove')
    page = w.go('/schedule', 'schedule')
    page = w.click(f'/schedule?date={A.Paper.query.get(pid).day}',
                   "the session's day tab")
    window = session_window_on_schedule(page, facts['session'])
    w.answer('session_window', f'{window[0]}-{window[1]}')
    page = w.click(f'/papers?session={quote(facts["session"])}',
                   "the session's paper list")
    w.answer('session_count', paper_count(page))
    page = w.back('back to the schedule')
    first_oral = re.search(r'Oral Session.*?<td><a href="/papers/(\d+)">([^<]+)</a>', page, re.S)
    detail = w.click(f'/papers/{first_oral.group(1)}', "open the first oral talk's paper")
    facts = paper_detail_facts(detail)
    w.answer('first_oral_decision', facts['session'] and 'Accept (Oral)')
    w.done()


WALKS = [walk_0, walk_1, walk_2, walk_3, walk_4, walk_5, walk_6, walk_7,
         walk_8, walk_9, walk_10, walk_11, walk_12, walk_13, walk_14,
         walk_15, walk_16, walk_17, walk_18, walk_19]


def check_leakage(tasks):
    """No task text may contain one of its own walker answers verbatim."""
    leaks = []
    for i, task in enumerate(tasks):
        ques = task['ques']
        for phrase in ('P4-#', 'P3-#', 'ICLR26-', '406', '432', '5691',
                       '7am-5:30pm', '$100', 'California,', 'A1B2C3D4',
                       'Amphitheater', '201 A/B', 'Test of Time Awards from'):
            if phrase in ques:
                leaks.append((i, phrase))
    return leaks


def main():
    tasks = [json.loads(line) for line in
             (SITE / 'tasks.jsonl').read_text().splitlines() if line.strip()]
    assert len(tasks) == len(WALKS), f'{len(tasks)} tasks vs {len(WALKS)} walks'
    leaks = check_leakage(tasks)
    if leaks:
        print(f'[audit] ANSWER LEAKAGE in task texts: {leaks}')
        return 1
    report = {'rounds': [], 'leaks': leaks}
    # Each task walks against its own freshly seeded database and its own
    # client (clean cookies) — the reviewer convention of per-task reset,
    # so state mutations from one task never leak into the next.
    for tag in (1, 2):
        counts = []
        for i, (task, walk) in enumerate(zip(tasks, WALKS)):
            A, client, root = fresh_client(f'r{tag}t{i}')
            with A.app.app_context():
                w = Walker(client)
                walk(w, A, client)
            counts.append(w.steps)
            print(f'[round {tag}] iclr--{i}: {w.steps} steps, '
                  f'{len(w.answers)} answers')
            if w.steps < MIN_STEPS:
                print(f'  !! BELOW {MIN_STEPS}: task iclr--{i} needs more depth')
            shutil.rmtree(root, ignore_errors=True)
        report['rounds'].append(counts)
    r1, r2 = report['rounds']
    agree = r1 == r2
    print(f'\n[audit] round1: {r1}')
    print(f'[audit] round2: {r2}')
    print(f'[audit] agree: {agree}; min {min(r1 + r2)}; '
          f'max {max(r1 + r2)}; mean {sum(r1) / len(r1):.1f}')
    ok = agree and min(r1) >= MIN_STEPS
    (SITE / 'scripts_dev' / 'walk_report.json').write_text(
        json.dumps(report, indent=1))
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
