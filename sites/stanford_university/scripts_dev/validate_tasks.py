#!/usr/bin/env python3
"""Honest-path task auditor for the stanford_university mirror.

For every task in tasks.jsonl this walker drives the exact honest path a
solving agent must take through the mirror UI (Flask test client, real CSRF
tokens, forms submitted the way a browser submits them), verifies each
premise the task relies on, collects the answers the task asks for, and
counts the atomic UI actions the task genuinely requires (reads are free;
actions the task text does not require are not taken).

Runs two fully independent rounds (fresh seeded database each time) and
reports both step-count sequences; they must agree and every task must
require at least 15 honest atomic steps.

Step conventions (same caliber as the review/fix browser walk):
  navigate(home)          1  opening the site homepage (the walk's start)
  click(link/button)      1  on-page element click (nav link, card, row link,
                             in-page "Log in ..." affordance, clear-filters)
  back()                  1  browser back
  fill(field)             1  per form field the task requires filling
  select(dropdown)        1  per dropdown change
  submit                 1  pressing the form's submit button (incl. login)
Reads (parsing a rendered page for an answer) are free. The login flow is
click-the-log-in-affordance + fill email + fill password + submit (4 steps),
the same count a browser walk takes via the in-page "Log in ..." links.

Run from sites/stanford_university:  python3 scripts_dev/validate_tasks.py
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
PASSWORD = 'TestPass123!'


def fresh_app(tag):
    """Boot the app against a fresh seeded SQLite database (per round).

    No persistent app context is pushed: a pushed app context would make
    flask.g (where flask_wtf caches the CSRF token and flask_login caches
    the current user) stick across requests and break per-task login/CSRF
    isolation. Every request manages its own contexts instead."""
    root = Path(tempfile.mkdtemp(prefix=f'stanford-audit-{tag}-'))
    os.environ['STANFORD_UNIVERSITY_DB_URI'] = f'sqlite:///{root / "stanford_university.db"}'
    os.environ['STANFORD_UNIVERSITY_AUTO_SEED'] = '1'
    for mod in list(sys.modules):
        if mod in ('app', 'seed_lib'):
            del sys.modules[mod]
    import app as A
    A.app.config.update(TESTING=True)
    return A, root


def csrf(client, url):
    r = client.get(url)
    assert r.status_code == 200, f'{url} -> {r.status_code}'
    m = re.search(rb'name="csrf_token"[^>]*value="([^"]+)"', r.data)
    assert m, f'no csrf token on {url}'
    return m.group(1).decode()


def text(resp):
    return resp.data.decode()


def strip(raw):
    """Tag-stripped, unescaped page text (what a browser renders)."""
    return html.unescape(html.unescape(re.sub(r'<[^>]+>', ' ', raw)))


class Walker:
    """Counts atomic UI actions under the honest caliber."""

    def __init__(self, client):
        self.client = client
        self.steps = 0
        self.log = []
        self.last = None  # (url, text) of the current page

    # ---------------------------------------------------------- actions --
    def go(self, url, desc, count=True):
        r = self.client.get(url)
        assert r.status_code == 200, f'{url} -> {r.status_code}'
        self.last = (url, text(r))
        if count:
            self.steps += 1
            self.log.append(f'{self.steps:02d} navigate {desc}')
        return self.last[1]

    def click(self, url, desc):
        return self.go(url, desc, count=True)

    def back(self, desc='browser back'):
        # the test client has no history; the honest flows here only use
        # back to return to the page they came from, so replay that page
        self.steps += 1
        self.log.append(f'{self.steps:02d} back {desc}')
        return self.last[1]

    def fill(self, desc):
        self.steps += 1
        self.log.append(f'{self.steps:02d} fill {desc}')

    def select(self, desc):
        self.steps += 1
        self.log.append(f'{self.steps:02d} select {desc}')

    def submit(self, url, data, desc, token_src=None, method='post'):
        if method == 'get':
            r = self.client.get(url, query_string=data)
            assert r.status_code == 200, f'GET {url} -> {r.status_code}'
        else:
            payload = dict(data)
            if token_src:
                payload['csrf_token'] = csrf(self.client, token_src)
            r = self.client.post(url, data=payload, follow_redirects=True)
            assert r.status_code == 200, f'POST {url} -> {r.status_code}'
        self.last = (r.request.url if hasattr(r, 'request') else url, text(r))
        self.steps += 1
        self.log.append(f'{self.steps:02d} submit {desc}')
        return self.last[1]

    def search(self, url, params, desc):
        """GET form submission (the catalog/directory search forms)."""
        return self.submit(url, params, desc, method='get')

    def login_via(self, login_url, email, desc='log in'):
        self.click(login_url, f'{desc}: open login page')
        self.fill(f'{desc}: email')
        self.fill(f'{desc}: password')
        return self.submit('/login', {'email': email, 'password': PASSWORD,
                                      'next': login_url.split('next=')[-1]},
                           f'{desc}: submit', token_src='/login')

    # ----------------------------------------------------------- reads --
    def page_text(self):
        return strip(self.last[1])

    def expect(self, needle, where=None):
        body = where if where is not None else self.page_text()
        assert needle in body, f'EXPECTED NOT FOUND: {needle!r}'
        return body


def count_label(body):
    m = re.search(r'([\d,]+) (?:courses|stories|events|departments|programs|'
                  r'faculty|libraries|locations|planned courses|academic departments|'
                  r'Stanford faculty)', body)
    return int(m.group(1).replace(',', '')) if m else None


def fact(body, label):
    m = re.search(re.escape(label) + r'\s*\n?\s*([^<\n]+)', body)
    return m.group(1).strip() if m else None


def first_row_code(body):
    m = re.search(r'\b([A-Z]{2,4}[&A-Z]*\d+[A-Z]?)\b', body.split('Terms offered')[-1])
    return m.group(1) if m else None


def planner_total(body):
    m = re.search(r'Total planned units:\s*\n?\s*(\d+(?:\.\d+)?\s*[\u2013\u2212-]\s*\d+(?:\.\d+)?|\d+(?:\.\d+)?)',
                  body)
    return m.group(1).replace(' ', '') if m else None


def table_first_cells(body, needle):
    m = re.search(re.escape(needle), body)
    seg = body[m.end():m.end() + 400] if m else ''
    cells = [c.strip() for c in re.split(r'\||\n{2,}', seg) if c.strip()]
    return cells


# ══════════════════════════════════════════════════════════════════ flows ══

def task_00(w):
    w.go('/', 'open site homepage')
    w.click('/courses', 'nav Courses')
    w.fill('search machine learning')
    w.search('/courses', {'q': 'machine learning'}, 'search')
    w.click('/courses?q=machine+learning&page=2', 'paginate to page 2')
    w.click('/courses/CS229', 'open CS229 course detail')
    body = w.expect('Machine Learning')
    w.expect('ROP - Letter or Credit/No Credit')
    w.click('/courses', 'nav Courses')
    w.select('subject CS')
    w.select('career Graduate')
    w.search('/courses', {'subject': 'CS', 'career': 'Graduate'}, 'search')
    body = w.last[1]
    assert count_label(body) == 40, count_label(body)
    w.click('/courses?subject=CS&career=Graduate&page=2', 'paginate to page 2')
    w.click('/courses/CS229', 'reopen CS229 to add to planner')
    w.login_via('/login?next=%2Fcourses%2FCS229', 'alice.j@test.com')
    w.submit('/planner/add', {'code': 'CS229', 'next': '/planner'},
             'add CS229 to planner', token_src='/courses/CS229')
    w.click('/planner', 'open planner')
    body = w.expect('CS106A')
    w.expect('MATH51')
    assert 'CS229' in body
    assert planner_total(body)


def task_01(w):
    w.go('/', 'open site homepage')
    w.click('/departments', 'nav Departments')
    w.select('school engineering')
    w.search('/departments', {'school': 'engineering'}, 'search')
    assert count_label(strip(w.last[1])) == 14
    w.click('/departments/AEROASTRO', 'open Aeronautics dept')
    w.expect('Aeronautics and Astronautics')
    w.click('/programs/AA-BS', 'open AA Bachelor of Science program')
    w.expect('Minimum units')
    w.fill('compare with AA-MS')
    w.search('/programs/AA-BS', {'compare': 'AA-MS'}, 'run compare')
    w.expect('AA-MS')
    w.click('/departments', 'nav Departments')
    w.select('school engineering')
    w.search('/departments', {'school': 'engineering'}, 'search')
    w.click('/departments/MGMTSCI', 'open MSE dept')
    w.expect('MS&E')
    w.click('/courses?dept=MGMTSCI', 'open MSE course catalog link')
    body = w.page_text()
    assert 'MS&E103' in body and 'Fundamentals of Agentic Systems' in body, body[:200]
    w.back('back to MSE dept page')
    w.expect('Degree Programs')
    w.click('/programs/MGTSC-MS', 'open MSE Master of Science program')
    w.expect('Requirements')


def task_02(w):
    w.go('/', 'open site homepage')
    w.click('/courses', 'nav Courses')
    w.select('subject EE')
    w.select('career Graduate')
    w.select('term Winter')
    w.search('/courses', {'subject': 'EE', 'career': 'Graduate', 'term': 'Winter'}, 'search')
    assert count_label(strip(w.last[1])) == 6, count_label(w.last[1])
    assert 'EE214B' in strip(w.last[1]) and 'EE101A' not in strip(w.last[1])
    w.click('/courses/EE214B', 'open first course by code (EE214B)')
    w.expect('Advanced Integrated Circuit Design')
    w.click('/courses', 'nav Courses')
    w.fill('search Programming Methodology')
    w.search('/courses', {'q': 'Programming Methodology'}, 'search')
    w.click('/courses/CS106A', 'open CS106A')
    w.expect('Formal Reasoning (FR)')
    w.click('/courses', 'nav Courses')
    w.select('subject MATH')
    w.select('WAYS Formal Reasoning')
    w.search('/courses', {'subject': 'MATH', 'ways': 'Formal Reasoning (FR)'}, 'search')
    assert count_label(strip(w.last[1])) == 28, count_label(w.last[1])


def task_03(w):
    w.go('/', 'open site homepage')
    w.click('/faculty', 'nav Faculty')
    w.fill('search Fei-Fei Li')
    w.search('/faculty', {'q': 'Fei-Fei Li'}, 'search')
    w.expect('Sequoia Capital Professor')
    w.click('/faculty/15052', 'open Fei-Fei Li profile')
    w.expect('Computer Science')
    w.click('/faculty', 'nav Faculty')
    w.select('dept Mathematics')
    w.search('/faculty', {'dept': 'Mathematics'}, 'search')
    w.expect('Mohammed Abouzaid')
    w.click('/faculty/' + w.last[1].split('href="/faculty/')[1].split('"')[0],
             'open first Math profile')
    w.expect('Professor of Mathematics')
    w.click('/faculty', 'nav Faculty')
    w.fill('search Aerospace Design Laboratory (bio covered after fix)')
    w.search('/faculty', {'q': 'Aerospace Design Laboratory'}, 'search')
    w.expect('Juan Alonso')
    w.click('/faculty/19258', 'open the ADL leader profile')
    w.expect('Coffman Professor')
    w.click('/faculty', 'nav Faculty')
    w.select('dept Psychology')
    w.search('/faculty', {'dept': 'Psychology'}, 'search')
    assert count_label(strip(w.last[1])) == 54


def task_04(w):
    w.go('/', 'open site homepage')
    w.click('/programs', 'nav Programs')
    w.fill('search programs Economics')
    w.search('/programs', {'q': 'Economics'}, 'search')
    w.click('/programs/ECON-BA', 'open Economics BA program')
    w.expect('Minimum units')
    w.click('/departments/ECONOMICS', 'open offering department page')
    w.expect('ECON')
    w.click('/programs/ECON-MA', 'open Economics MA program')
    w.expect('Minimum units')
    w.click('/programs', 'nav Programs')
    w.fill('search programs Computer Science')
    w.search('/programs', {'q': 'Computer Science'}, 'search')
    w.click('/programs/CS-MIN', 'open CS Minor program')
    w.expect('Minimum units')
    w.click('/programs', 'nav Programs')
    w.select('kind PhD (PhD Minor type)')
    w.search('/programs', {'kind': 'PhD'}, 'search')
    body = w.last[1]
    w.click('/programs/' + body.split('href="/programs/')[1].split('"')[0],
            'open first PhD Minor program')


def task_05(w):
    w.go('/', 'open site homepage')
    w.click('/programs', 'nav Programs')
    w.fill('search programs Computer Science')
    w.search('/programs', {'q': 'Computer Science'}, 'search')
    w.click('/programs/CS-BS', 'open CS BS program')
    w.expect('Minimum units')
    w.fill('compare with CS-MS')
    w.search('/programs/CS-BS', {'compare': 'CS-MS'}, 'run compare')
    w.expect('CS-MS')
    w.back('back to CS BS page')
    w.back('back to CS program listing')
    w.click('/programs/CS-MIN', 'open CS Minor program')
    w.fill('compare with CS-PHD')
    w.search('/programs/CS-MIN', {'compare': 'CS-PHD'}, 'run compare')
    w.expect('CS-PHD')
    w.click('/departments/COMPUTSCI', 'open CS department page')
    w.expect('Degree Programs')
    w.click('/programs/CS-PHD', 'open CS PhD program')
    w.expect('Minimum units')
    w.back('back to CS dept page')
    w.click('/programs/CS-MS', 'open CS MS program')
    w.expect('Requirements')


def task_06(w):
    w.go('/', 'open site homepage')
    w.click('/news', 'nav News')
    w.select('category University News')
    w.search('/news', {'category': 'University News'}, 'search')
    assert count_label(strip(w.last[1])) == 43
    w.fill('search MacArthur')
    w.search('/news', {'q': 'MacArthur', 'category': 'University News'}, 'search')
    w.click('/news/song-lin-macarthur-fellowship', 'open the Song Lin MacArthur story')
    w.expect('MacArthur Fellowship')
    w.click('/news', 'back to Stanford Report listing')
    w.select('topic Health & Medicine')
    w.search('/news', {'topic': 'Health & Medicine'}, 'search')
    assert count_label(strip(w.last[1])) == 22
    body = w.last[1]
    w.click('/news/' + body.split('href="/news/')[1].split('"')[0],
            'open the newest H&M story for its writer')
    w.expect('Erin Digitale')
    w.click('/news', 'clear back to all stories')
    w.fill('search Siebel Scholars')
    w.search('/news', {'q': 'Siebel Scholars'}, 'search')
    w.click('/news/students-siebel-scholars', 'open the Siebel Scholars story')
    w.expect('Alex Kekauoha')


def task_07(w):
    w.go('/', 'open site homepage')
    w.click('/news', 'nav News')
    w.select('category Research & Scholarship')
    w.select('topic Health & Medicine')
    w.search('/news', {'category': 'Research & Scholarship', 'topic': 'Health & Medicine'}, 'search')
    assert count_label(strip(w.last[1])) == 20
    body = w.last[1]
    w.click('/news/' + body.split('href="/news/')[1].split('"')[0],
            'open newest R&S + H&M story for writer')
    w.expect('Erin Digitale')
    w.click('/news', 'clear the filters')
    w.expect('Stanford chemist Song Lin receives MacArthur Fellowship')
    w.fill('search democracy')
    w.search('/news', {'q': 'democracy'}, 'search')
    assert count_label(strip(w.last[1])) == 10
    body = w.last[1]
    w.click('/news/' + body.split('href="/news/')[1].split('"')[0],
            'open newest democracy story')
    w.expect('Lara Tiedens')
    w.click('/news', 'nav News')
    w.select('category On Campus')
    w.search('/news', {'category': 'On Campus'}, 'search')
    assert count_label(strip(w.last[1])) == 42
    body = w.last[1]
    w.click('/news/' + body.split('href="/news/')[1].split('"')[0],
            'open newest On Campus story')
    w.expect('President Levin')
    w.click('/news', 'nav News')
    w.select('category Student Experience')
    w.search('/news', {'category': 'Student Experience'}, 'search')
    assert count_label(strip(w.last[1])) == 32


def task_08(w):
    w.go('/', 'open site homepage')
    w.click('/events', 'nav Events')
    w.fill('search events lecture')
    w.search('/events', {'q': 'lecture'}, 'search')
    assert count_label(strip(w.last[1])) == 29
    w.click('/events/54101567783190', 'open Hoover memorial lecture event')
    w.expect('Hoover Institution')
    w.click('/events', 'nav Events')
    w.select('month November 2026')
    w.search('/events', {'month': '2026-11'}, 'search')
    assert count_label(strip(w.last[1])) == 60
    body = w.last[1]
    w.click('/events/' + body.split('href="/events/')[1].split('"')[0],
            'open first November event')
    w.expect('Stanford Energy Seminar')
    w.click('/events', 'nav Events')
    w.select('when upcoming')
    w.fill('search seminar within upcoming')
    w.search('/events', {'when': 'upcoming', 'q': 'seminar'}, 'search')
    assert count_label(strip(w.last[1])) == 91
    assert '2026-10-01' in strip(w.last[1])
    w.click('/events', 'clear the filters')
    w.fill('search events concert')
    w.search('/events', {'q': 'concert'}, 'search')
    assert count_label(strip(w.last[1])) == 36
    body = w.last[1]
    w.click('/events/' + body.split('href="/events/')[1].split('"')[0],
            'open first concert event')
    w.expect('471 Lagunita Drive')


def task_09(w):
    w.go('/', 'open site homepage')
    w.login_via('/login?next=%2Fsaved-events', 'bob.c@test.com')
    w.click('/saved-events', 'open saved events')
    w.expect('Trust and Safety Research Conference')
    w.click('/events', 'nav Events')
    w.select('month December 2026')
    w.search('/events', {'month': '2026-12'}, 'search')
    assert count_label(strip(w.last[1])) >= 1
    body = w.last[1]
    first_eid = body.split('href="/events/')[1].split('"')[0]
    w.click(f'/events/{first_eid}', 'open first December event')
    w.submit('/events/save', {'eid': first_eid, 'next': '/saved-events'},
             'save the event', token_src=f'/events/{first_eid}')
    w.click('/saved-events', 'view saved events')
    w.click('/events', 'nav Events')
    w.fill('search events conference')
    w.search('/events', {'q': 'conference'}, 'search')
    w.click('/events/53074254797631', 'open the research conference already in the list')
    w.submit('/events/unsave', {'eid': '53074254797631', 'next': '/saved-events'},
             'remove it', token_src='/events/53074254797631')
    w.click('/saved-events', 'view saved events')
    w.expect('1 saved')


def task_10(w):
    w.go('/', 'open site homepage')
    w.click('/academic-calendar', 'open 2026-27 academic calendar')
    w.expect('September 22 (Tue)')
    w.click('/academic-calendar?quarter=winter', 'switch to Winter Quarter')
    w.expect('January 4 (Mon)')
    w.login_via('/login?next=%2Fplanner', 'dana.k@test.com')
    w.click('/planner', 'open course planner')
    w.expect('BIO102')
    w.submit('/planner/remove', {'code': 'BIO102', 'next': '/planner'},
             'remove the neuroscience course', token_src='/planner')
    w.click('/courses', 'open course catalog')
    w.fill('search Linear Algebra, Multivariable Calculus')
    w.search('/courses', {'q': 'Linear Algebra, Multivariable Calculus'}, 'search')
    w.click('/courses/MATH51', 'open MATH51')
    w.submit('/planner/add', {'code': 'MATH51', 'next': '/planner'},
             'add MATH51 to planner', token_src='/courses/MATH51')
    w.click('/planner', 'view planner')
    w.expect('MATH51')


def task_11(w):
    w.go('/', 'open site homepage')
    w.click('/libraries', 'nav Libraries')
    w.click('/libraries/robin-li-and-melissa-ma-science-library', 'open Robin Li library')
    w.expect('(650) 723-1528')
    w.click('/libraries', 'nav Libraries')
    w.click('/libraries/cecil-h-green-library', 'open Green Library')
    w.expect('(650) 723-1493')
    w.click('/libraries', 'nav Libraries')
    w.click('/libraries/music-library', 'open Music Library')
    w.click('/libraries', 'nav Libraries')
    w.fill('search libraries east')
    w.search('/libraries', {'q': 'east'}, 'search')
    w.click('/libraries/east-asia-library', 'open East Asia Library')
    w.expect('Lathrop Library')
    w.click('/libraries', 'nav Libraries')
    w.fill('search libraries philosophy')
    w.search('/libraries', {'q': 'philosophy'}, 'search')
    w.expect('Tanner Memorial Library of Philosophy')
    w.click('/libraries/tanner-philosophy-library', 'open the philosophy library')
    w.expect('Main Quad, first floor of Building 90, Room 91F')


def task_12(w):
    w.go('/', 'open site homepage')
    w.click('/admission', 'nav Admission & Aid')
    w.expect('November 1')
    w.expect('January 5')
    w.click('/admission/aid', 'open financial aid page')
    w.fill('estimator income 120000')
    w.fill('estimator family 2')
    w.search('/admission/aid', {'income': '120000', 'family': '2'},
             'run estimator')
    w.expect('No tuition responsibility')
    w.click('/signup', 'open signup page')
    w.fill('signup name Sam Rivera')
    w.fill('signup email sam.rivera@test.com')
    w.fill('signup password')
    w.submit('/signup', {'name': 'Sam Rivera', 'email': 'sam.rivera@test.com',
                         'password': 'TestPass123!'}, 'submit signup', token_src='/signup')
    w.expect('Sam Rivera')
    w.click('/courses', 'open course catalog')
    w.fill('search Introduction to Psychology')
    w.search('/courses', {'q': 'Introduction to Psychology'}, 'search')
    w.click('/courses/PSYCH1', 'open PSYCH1')
    w.submit('/planner/add', {'code': 'PSYCH1', 'next': '/planner'},
             'add to planner', token_src='/courses/PSYCH1')
    w.click('/planner', 'view planner')
    w.expect('PSYCH1')


def task_13(w):
    w.go('/', 'open site homepage')
    w.login_via('/login?next=%2Fplanner', 'bob.c@test.com')
    w.click('/planner', 'open course planner')
    w.expect('ECON1')
    w.submit('/planner/remove', {'code': 'PSYCH1', 'next': '/planner'},
             'remove the psychology course', token_src='/planner')
    w.click('/courses', 'open catalog')
    w.fill('search Introduction to Neuroscience')
    w.search('/courses', {'q': 'Introduction to Neuroscience'}, 'search')
    w.click('/courses/BIO102', 'open BIO102')
    w.submit('/planner/add', {'code': 'BIO102', 'next': '/planner'},
             'add BIO102', token_src='/courses/BIO102')
    w.click('/planner', 'view planner')
    w.submit('/planner/remove', {'code': 'ECON1', 'next': '/planner'},
             'remove the economics course', token_src='/planner')
    w.click('/courses', 'open catalog')
    w.fill('search Mechanics physics course')
    w.search('/courses', {'q': 'Mechanics'}, 'search')
    w.click('/courses?q=Mechanics&page=5', 'paginate to page 5')
    w.click('/courses/PHYSICS41', 'open PHYSICS41')
    w.submit('/planner/add', {'code': 'PHYSICS41', 'next': '/planner'},
             'add PHYSICS41', token_src='/courses/PHYSICS41')
    w.click('/planner', 'view planner')
    w.expect('PHYSICS41')


def task_14(w):
    w.go('/', 'open site homepage')
    w.click('/signup', 'open signup page')
    w.fill('signup name Jordan Vale')
    w.fill('signup email jordan.vale@test.com')
    w.fill('signup password')
    w.submit('/signup', {'name': 'Jordan Vale', 'email': 'jordan.vale@test.com',
                         'password': 'TestPass123!'}, 'submit signup', token_src='/signup')
    w.expect('Jordan Vale')
    w.click('/courses', 'open catalog')
    w.fill('search introduction to neuroscience')
    w.search('/courses', {'q': 'introduction to neuroscience'}, 'search')
    w.click('/courses/BIO102', 'open the Biology neuroscience course')
    w.expect('Grading basis')
    w.submit('/planner/add', {'code': 'BIO102', 'next': '/planner'},
             'add BIO102', token_src='/courses/BIO102')
    w.click('/courses', 'nav Courses')
    w.fill('search Principles of Economics')
    w.search('/courses', {'q': 'Principles of Economics'}, 'search')
    w.click('/courses/ECON1', 'open ECON1')
    w.submit('/planner/add', {'code': 'ECON1', 'next': '/planner'},
             'add ECON1', token_src='/courses/ECON1')
    w.click('/planner', 'view planner')
    w.expect('Total planned units')


def task_15(w):
    w.go('/', 'open site homepage')
    w.click('/departments', 'nav Departments')
    w.fill('search dept Chemistry')
    w.search('/departments', {'q': 'Chemistry'}, 'search')
    w.click('/departments/CHEMISTRY', 'open Chemistry department')
    w.expect('CHEM')
    w.click('/courses?dept=CHEMISTRY', 'open Chemistry catalog link')
    w.click('/courses', 'nav Courses')
    w.fill('search machine learning for chemical')
    w.search('/courses', {'q': 'machine learning for chemical'}, 'search')
    w.click('/courses/CHEM263', 'open CHEM263')
    w.expect('Units')
    w.click('/faculty', 'nav Faculty')
    w.select('dept Chemistry')
    w.search('/faculty', {'dept': 'Chemistry'}, 'search')
    body = w.last[1]
    w.click('/faculty/' + body.split('href="/faculty/')[1].split('"')[0],
            'open first Chemistry faculty alphabetically')
    w.click('/departments', 'nav Departments')
    w.fill('search dept Chemistry')
    w.search('/departments', {'q': 'Chemistry'}, 'search')
    w.click('/departments/CHEMISTRY', 'open Chemistry department')
    w.click('/programs/CHEM-PHD', 'open Chemistry PhD program')
    w.expect('Minimum units')


def task_16(w):
    w.go('/', 'open site homepage')
    body = w.last[1]
    slug = body.split('href="/news/')[1].split('"')[0]
    w.click(f'/news/{slug}', 'open newest homepage story')
    w.expect('Adam Hadhazy')
    w.click('/events', 'nav Events')
    w.select('when upcoming')
    w.search('/events', {'when': 'upcoming'}, 'search')
    body = w.last[1]
    first_eid = body.split('href="/events/')[1].split('"')[0]
    w.click(f'/events/{first_eid}', 'open first upcoming event')
    w.expect('Climber Coffee')
    w.login_via(f'/login?next=%2Fevents%2F{first_eid}', 'dana.k@test.com')
    w.submit('/events/save', {'eid': first_eid, 'next': '/saved-events'},
             'save the event', token_src=f'/events/{first_eid}')
    w.click('/saved-events', 'view saved events')
    w.expect('2 saved')
    w.click('/academic-calendar', 'open 2026-27 academic calendar')
    w.expect('September 22 (Tue)')
    w.click('/academic-calendar?quarter=summer', 'switch to Summer Quarter')
    w.click('/libraries', 'nav Libraries')
    w.fill('search libraries classics')
    w.search('/libraries', {'q': 'classics'}, 'search')
    w.expect('Classics Library')
    w.click('/libraries/classics-library', 'open the first classics match')
    w.expect('(650) 723-0479')


def task_17(w):
    w.go('/', 'open site homepage')
    w.click('/courses', 'nav Courses')
    w.select('WAYS Formal Reasoning')
    w.search('/courses', {'ways': 'Formal Reasoning (FR)'}, 'search')
    assert count_label(strip(w.last[1])) == 90
    w.select('subject CS')
    w.search('/courses', {'ways': 'Formal Reasoning (FR)', 'subject': 'CS'}, 'search')
    assert count_label(strip(w.last[1])) == 11
    w.click('/courses/CS103', 'open lowest course number (CS103)')
    w.expect('Mathematical Foundations of Computing')
    w.login_via('/login?next=%2Fcourses%2FCS103', 'carol.d@test.com')
    w.submit('/planner/add', {'code': 'CS103', 'next': '/planner'},
             'add CS103 to planner', token_src='/courses/CS103')
    w.click('/planner', 'view planner')
    w.expect('CS103')
    w.submit('/planner/remove', {'code': 'CS103', 'next': '/planner'},
             'remove CS103', token_src='/planner')
    w.expect('Your course planner is empty')
    w.click('/courses', 'return to the catalog')
    w.select('WAYS Formal Reasoning')
    w.select('subject CS')
    w.select('term Winter')
    w.search('/courses', {'ways': 'Formal Reasoning (FR)', 'subject': 'CS',
                          'term': 'Winter'}, 'search')
    assert count_label(strip(w.last[1])) == 8
    assert 'CS103' in strip(w.last[1])


def task_18(w):
    w.go('/', 'open site homepage')
    w.login_via('/login?next=%2Fsaved-events', 'carol.d@test.com')
    w.click('/saved-events', 'open saved events')
    w.expect('Lunchtime Curator Talk')
    w.click('/events', 'nav Events')
    w.fill('search events multifaith')
    w.search('/events', {'q': 'multifaith'}, 'search')
    w.click('/events/53969575639155', 'open Multifaith Dinner')
    w.submit('/events/save', {'eid': '53969575639155', 'next': '/saved-events'},
             'save it', token_src='/events/53969575639155')
    w.click('/saved-events', 'view saved events')
    w.submit('/events/unsave', {'eid': '53685756293663', 'next': '/saved-events'},
             'remove the curator talk event', token_src='/saved-events')
    w.click('/events', 'nav Events')
    w.fill('search events seminar')
    w.search('/events', {'q': 'seminar'}, 'search')
    w.click('/events/53870497268780', 'open the first seminar event')
    w.submit('/events/save', {'eid': '53870497268780', 'next': '/saved-events'},
             'save it', token_src='/events/53870497268780')
    w.click('/saved-events', 'view saved events')
    w.expect('2 saved')


def task_19(w):
    w.go('/', 'open site homepage')
    w.click('/faculty', 'nav Faculty')
    w.select('dept Computer Science')
    w.search('/faculty', {'dept': 'Computer Science'}, 'search')
    body = w.last[1]
    w.click('/faculty/' + body.split('href="/faculty/')[1].split('"')[0],
            'open first CS faculty alphabetically')
    w.login_via('/login?next=%2Fplanner', 'alice.j@test.com')
    w.click('/planner', 'open course planner')
    w.expect('CS106A')
    w.click('/courses', 'open catalog')
    w.fill('search Design and Analysis of Algorithms')
    w.search('/courses', {'q': 'Design and Analysis of Algorithms'}, 'search')
    w.click('/courses/CS161', 'open CS161')
    w.submit('/planner/add', {'code': 'CS161', 'next': '/planner'},
             'add CS161', token_src='/courses/CS161')
    w.click('/planner', 'view planner')
    w.expect('CS161')


FLOWS = [task_00, task_01, task_02, task_03, task_04, task_05, task_06,
         task_07, task_08, task_09, task_10, task_11, task_12, task_13,
         task_14, task_15, task_16, task_17, task_18, task_19]

TASKS = [json.loads(l) for l in (SITE / 'tasks.jsonl').read_text().strip().splitlines()]


def run_round(tag):
    A, root = fresh_app(tag)
    counts = []
    for i, flow in enumerate(FLOWS):
        # a fresh test client per task = a fresh browser context (cookies
        # and session start clean, exactly like the browser walk's per-task
        # reset + new context)
        w = Walker(A.app.test_client())
        flow(w)
        counts.append(w.steps)
        status = 'ok' if w.steps >= MIN_STEPS else 'FAIL(<15)'
        print(f'  {TASKS[i]["id"]}: {w.steps} steps {status}', flush=True)
        assert w.steps >= MIN_STEPS, f'{TASKS[i]["id"]} finished in {w.steps} < 15 honest steps'
    shutil.rmtree(root, ignore_errors=True)
    return counts


def main():
    print('round 1 (fresh seeded database):', flush=True)
    r1 = run_round('r1')
    print('round 2 (fresh seeded database):', flush=True)
    r2 = run_round('r2')
    print('round1:', r1)
    print('round2:', r2)
    print('rounds agree:', r1 == r2)
    print('min:', min(r1), 'mean:', round(sum(r1) / len(r1), 1),
          'all >= 15:', all(x >= MIN_STEPS for x in r1))
    assert r1 == r2, 'the two honest rounds disagree'


if __name__ == '__main__':
    main()
