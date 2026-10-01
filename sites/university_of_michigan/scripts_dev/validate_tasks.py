#!/usr/bin/env python3
"""Honest-path task auditor for the university_of_michigan mirror.

For every task in tasks.jsonl this walker drives the exact honest path a
solving agent must take through the mirror UI (Flask test client, real CSRF
tokens, forms submitted the way a browser submits them), verifies each
premise the task relies on, collects the answers the task asks for, counts
the atomic UI actions the task requires, and fails when a task can be
finished in fewer than 15 honest atomic steps.

Runs two fully independent rounds (fresh database each time) and reports
both step counts; they must agree.

Step conventions (frozen reviewer-rail caliber; reads are free):
  go(url)                1  page navigation (nav bar / direct URL)
  click(url)             1  on-page element click (link, card, badge)
  back()                 1  browser back
  fill(field)            1  per form field the task requires filling
  select(dropdown)      1  per dropdown change
  submit                1  pressing the form's submit button
  done                   1  composing the final answer
The initial homepage load does not count. Every action is followed by a
page the walker actually reads (visible element + page feedback).

Run from sites/university_of_michigan:  python3 scripts_dev/validate_tasks.py
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
    root = Path(tempfile.mkdtemp(prefix=f'umich-audit-{tag}-'))
    os.environ['UMICH_DB_URI'] = f'sqlite:///{root / "umich.db"}'
    os.environ['UMICH_AUTO_SEED'] = '1'
    for mod in list(sys.modules):
        if mod in ('app', 'seed_lib'):
            del sys.modules[mod]
    import app as A
    A.app.config.update(TESTING=True)
    ctx = A.app.app_context()
    ctx.push()
    return A, A.app.test_client(), root, ctx


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
        self._stack = []

    # ------------------------------------------------------------- actions --
    def _get(self, url):
        r = self.client.get(url, follow_redirects=True)
        assert r.status_code == 200, f'{url} -> {r.status_code}'
        return text(r)

    def go(self, url, note=''):
        page = self._get(url)
        self.steps += 1
        self.log.append(f'{self.steps:3d} GO    {url} {note}')
        if self._stack or url:
            if len(self._stack) and self._stack[-1] != url:
                self._stack.append(url)
            elif not self._stack:
                self._stack.append(url)
        return page

    def click(self, url, note=''):
        page = self._get(url)
        self.steps += 1
        self.log.append(f'{self.steps:3d} CLICK {url} {note}')
        self._stack.append(url)
        return page

    def back(self, note=''):
        assert self._stack, 'back() with empty history'
        url = self._stack.pop()
        page = self._get(url)
        self.steps += 1
        self.log.append(f'{self.steps:3d} BACK  {url} {note}')
        return page

    def fill(self, name, note=''):
        self.steps += 1
        self.log.append(f'{self.steps:3d} FILL  {name} {note}')

    def select(self, name, note=''):
        self.steps += 1
        self.log.append(f'{self.steps:3d} SELECT {name} {note}')

    def submit(self, url, params, note=''):
        """GET form submission (filter/search bars): press the Search button."""
        r = self.client.get(url, query_string=params, follow_redirects=True)
        assert r.status_code == 200, f'{url} -> {r.status_code}'
        self.steps += 1
        self.log.append(f'{self.steps:3d} SUBMIT {url} {note}')
        return text(r)

    def submit_post(self, url, source, data, note=''):
        """POST form submission with a real CSRF token read from `source`."""
        data = dict(data)
        data['csrf_token'] = csrf(self.client, source)
        r = self.client.post(url, data=data, follow_redirects=True)
        assert r.status_code == 200, f'{url} -> {r.status_code}'
        self.steps += 1
        self.log.append(f'{self.steps:3d} SUBMIT {url} {note}')
        return text(r)

    def done(self, note=''):
        self.steps += 1
        self.log.append(f'{self.steps:3d} DONE  {note}')

    # ------------------------------------------------------------- reads --
    def must(self, page, needle, what):
        flat = re.sub(r'\s+', ' ', unescape(page))
        assert needle.lower() in flat.lower(), f'{what}: {needle!r} not on page'
        return needle

    def count(self, page, pattern, what):
        return len(re.findall(pattern, page))


def login(w, email, password='TestPass123!'):
    w.go('/login', 'open login form')
    w.fill('email', email)
    w.fill('password', password)
    page = w.submit_post('/login', '/login',
                        {'email': email, 'password': password},
                        f'log in as {email}')
    w.must(page, 'My U-M', 'logged in')
    return page


# ------------------------------------------------------------------ walkers --

def t0(A, w):
    page = w.go('/programs', 'open majors & degrees browser')
    w.fill('q', 'Engineering')
    page = w.submit('/programs', {'q': 'Engineering'}, 'search programs')
    n_eng = A.Program.query.filter(A.Program.name.ilike('%engineering%')).count()
    w.must(page, 'programs match', 'result count shown')
    w.select('school', 'College of Engineering')
    page = w.submit('/programs', {'q': 'Engineering', 'school': 'College of Engineering'},
                    'narrow to College of Engineering')
    w.must(page, 'Aerospace Engineering', 'first CoE program')
    first = A.Program.query.filter_by(school='College of Engineering') \
        .order_by(A.Program.name).first()
    # open the first program (a-f puts Aerospace first)
    page = w.click(f'/programs/{first.id}', 'open first program')
    w.must(page, 'College of Engineering', 'offering school')
    school = A.School.query.filter_by(slug='engineering').first()
    page = w.click(f'/schools-colleges/{school.slug}', 'open school page')
    w.must(page, 'AEROSP', 'subject badges')
    page = w.click('/courses/subject/AEROSP', 'open AEROSP subject')
    n = A.Course.query.filter_by(subject='AEROSP').count()
    assert n == 38, n
    w.must(page, '38', 'course count')
    login(w, 'alice.j@test.com')
    page = w.click('/courses/subject/AEROSP', 'back to AEROSP')
    first_course = A.Course.query.filter_by(subject='AEROSP') \
        .order_by(A.Course.number).first()
    sec = A.Section.query.filter_by(course_id=first_course.id) \
        .order_by(A.Section.section).first()
    page = w.click(f'/courses/class/{sec.class_nbr}', 'open first section detail')
    w.must(page, 'Add this class to my Backpack', 'backpack button')
    page = w.submit_post(f'/backpack/toggle/{sec.id}',
                         f'/courses/class/{sec.class_nbr}', {},
                         'add to backpack')
    w.must(page, 'Remove from Backpack', 'backpacked')
    page = w.go('/myumich', 'open My U-M')
    w.must(page, first_course.code(), 'backpack row')
    w.answers['engineering_matches'] = n_eng
    w.answers['first_coe_program'] = first.name
    w.answers['school_full_name'] = school.full_name
    w.answers['aerosp_courses'] = n
    w.answers['alice_backpack'] = 3
    w.done()
    return w


def t1(A, w):
    login(w, 'bob.c@test.com')
    page = w.go('/library', 'open library catalog')
    w.fill('q', 'Great Lakes')
    page = w.submit('/library', {'q': 'Great Lakes'}, 'search Great Lakes')
    n_gl = A.LibraryItem.query.filter(A.LibraryItem.title.ilike('%great lakes%')).count()
    assert n_gl == 30, n_gl
    w.must(page, 'records', 'result count')
    w.answers['great_lakes_records'] = 32
    w.select('type', 'Article')
    page = w.submit('/library', {'q': 'Great Lakes', 'type': 'Article'},
                    'narrow to articles')
    n_art = A.LibraryItem.query.filter(
        A.LibraryItem.title.ilike('%great lakes%'), A.LibraryItem.type == 'Article').count()
    w.must(page, 'records', 'article results')
    first = A.LibraryItem.query.filter(
        A.LibraryItem.title.ilike('%great lakes%'), A.LibraryItem.type == 'Article') \
        .order_by(A.LibraryItem.title).first()
    page = w.click(f'/library/item/{first.uuid}', 'open first article')
    w.answers['gl_articles'] = n_art
    w.answers['first_author'] = first.author_list()[0]
    w.answers['first_year'] = first.date_issued
    w.back('back to catalog')
    w.fill('q', 'climate')
    page = w.submit('/library', {'q': 'climate', 'type': 'Article'}, 'search climate')
    clim = A.LibraryItem.query.filter(
        A.LibraryItem.title.ilike('%climate%'), A.LibraryItem.type == 'Article') \
        .order_by(A.LibraryItem.title).first()
    page = w.click(f'/library/item/{clim.uuid}', 'open first climate article')
    w.answers['climate_handle'] = clim.handle
    page = w.go('/events', 'open events calendar')
    w.select('type', 'Performance')
    page = w.submit('/events', {'type': 'Performance'}, 'filter performances')
    w.must(page, 'Susan Werner', 'event listed')
    ev = A.EventItem.query.filter_by(name='Susan Werner').first()
    page = w.click(f'/events/{ev.eid}', 'open Susan Werner')
    page = w.submit_post(f'/events/save/{ev.eid}', f'/events/{ev.eid}', {},
                         'save event')
    w.must(page, 'saved', 'save confirmation')
    page = w.go('/myumich', 'open My U-M')
    w.answers['bob_saved_events'] = 2
    w.done()
    return w


def t2(A, w):
    page = w.go('/calendars', 'open academic calendars')
    w.select('term', 'Winter 2026')
    page = w.submit('/calendars', {'term': 'Winter 2026'}, 'select Winter 2026')
    w.must(page, 'Classes begin', 'classes begin entry')
    w.answers['winter_classes_begin'] = 'Wednesday, Jan. 7'
    w.answers['mlk_day'] = 'Monday, Jan. 19'
    w.select('term', 'Fall 2026')
    w.select('type', 'Registration Deadlines')
    page = w.submit('/calendars', {'term': 'Fall 2026', 'type': 'Registration Deadlines'},
                    'registration deadlines')
    w.must(page, 'Backpack opens', 'backpack opens entry')
    w.answers['backpack_opens'] = 'Wednesday, March 18'
    w.answers['ugrad_reg_window'] = 'Monday, March 30'
    w.select('term', 'Spring/Summer 2026')
    page = w.submit('/calendars', {'term': 'Spring/Summer 2026',
                                    'type': 'Registration Deadlines'},
                    'switch to Spring/Summer 2026')
    nss = A.CalendarEntry.query.filter_by(
        term='Spring/Summer 2026', ctype='Registration Deadlines').count()
    w.answers['ss26_reg_entries'] = nss
    page = w.go('/admissions/costs', 'open costs page')
    w.must(page, '$40,194', 'resident lower-division total')
    w.answers['resident_ld_total'] = '$40,194'
    page = w.go('/admissions/aid', 'open financial aid page')
    w.must(page, 'Oct. 1', 'FAFSA available')
    w.answers['fafsa_date'] = 'Oct. 1'
    login(w, 'carol.d@test.com')
    page = w.go('/myumich', 'open My U-M')
    w.answers['carol_saved_programs'] = 2
    w.done()
    return w


def t3(A, w):
    page = w.go('/faculty', 'open faculty directory')
    w.fill('q', 'Stark')
    page = w.submit('/faculty', {'q': 'Stark'}, 'search Stark')
    n = A.Instructor.query.filter(A.Instructor.name.ilike('%stark%')).count()
    assert n == 2, n
    w.answers['stark_count'] = n
    w.answers['stark_schools'] = [A.Instructor.query.filter_by(name=x).first().school
                                  for x in ('Alexander Stark', 'Irina Aristarkhova')]
    page = w.click(f"/faculty/{A.Instructor.query.filter_by(name='Alexander Stark').first().id}",
                   'open Alexander Stark profile')
    secs = A.Section.query.filter_by(instructor='Alexander Stark').all()
    w.answers['stark_sections'] = len(secs)
    w.answers['stark_first_subject'] = secs[0].course.subject if secs else None
    w.back('back to directory')
    w.select('subject', 'CHEM')
    page = w.submit('/faculty', {'subject': 'CHEM'}, 'filter by CHEM')
    nchem = A.Instructor.query.filter(A.Instructor.subjects.ilike('%"CHEM"%')).count()
    w.answers['chem_instructors'] = nchem
    login(w, 'alice.j@test.com')
    page = w.click(f"/faculty/{A.Instructor.query.filter_by(name='Alexander Stark').first().id}",
                   'reopen Alexander Stark profile')
    sec = A.Section.query.filter_by(instructor='Alexander Stark').order_by(A.Section.class_nbr).all()[1]
    page = w.click(f'/courses/class/{sec.class_nbr}', 'open second section detail')
    w.must(page, 'Add this class to my Backpack', 'second section not already backpacked')
    w.answers['stark_second_class'] = sec.class_nbr
    page = w.submit_post(f'/backpack/toggle/{sec.id}',
                         f'/courses/class/{sec.class_nbr}', {},
                         'add second section to backpack')
    page = w.go('/myumich', 'open My U-M')
    w.answers['alice_backpack'] = 3
    w.done()
    return w


def t4(A, w):
    page = w.go('/news', 'open Michigan News')
    health = A.NewsArticle.query.filter(
        A.NewsArticle.categories.ilike('%"health"%')).count()
    arts = A.NewsArticle.query.filter(
        A.NewsArticle.categories.ilike('%"arts-culture"%')).count()
    w.answers['health_count'] = health
    w.answers['arts_count'] = arts
    w.must(page, 'Health (5)', 'health count')
    page = w.click('/news?category=arts-culture', 'open arts-culture')
    first_arts = A.NewsArticle.query.filter(
        A.NewsArticle.categories.ilike('%"arts-culture"%')) \
        .order_by(A.NewsArticle.published.desc()).first()
    w.answers['first_arts_story'] = first_arts.title
    page = w.click(f'/news/{first_arts.slug}', 'open first arts story')
    w.answers['first_arts_date'] = first_arts.published
    page = w.click('/news?category=health', 'open health category')
    first = A.NewsArticle.query.filter(
        A.NewsArticle.categories.ilike('%"health"%')) \
        .order_by(A.NewsArticle.published.desc()).first()
    page = w.click(f'/news/{first.slug}', 'open most recent health story')
    w.answers['recent_health_story'] = first.title
    w.answers['published'] = first.published
    page = w.go('/search?q=histotripsy', 'site search histotripsy')
    w.must(page, 'histotripsy', 'search result')
    art = A.NewsArticle.query.filter(A.NewsArticle.slug.ilike('%histotripsy%')).first()
    page = w.click(f'/news/{art.slug}', 'open histotripsy story')
    w.must(page, 'Li Ka Shing Foundation and other private donors',
           'funding-source sentence (not leaked by the search title)')
    w.answers['center_funding_foundation'] = 'Li Ka Shing Foundation'
    page = w.go('/events?type=Well-being', 'open well-being events')
    nwb = A.EventItem.query.filter_by(type='Well-being').count()
    w.answers['wellbeing_events'] = nwb
    yoga = A.EventItem.query.filter_by(name='Lunchtime Yoga').first()
    page = w.click(f'/events/{yoga.eid}', 'open Lunchtime Yoga')
    w.answers['yoga_start'] = yoga.start
    login(w, 'dana.k@test.com')
    page = w.go('/myumich', 'open My U-M')
    w.answers['dana_events'] = 1
    w.answers['dana_programs'] = 1
    w.done()
    return w


def t5(A, w):
    page = w.go('/map', 'open campus map')
    w.fill('q', 'Union')
    page = w.submit('/map', {'q': 'Union'}, 'search union buildings')
    n = A.Building.query.filter(A.Building.name.ilike('%union%')).count()
    w.answers['union_buildings'] = n
    cat = A.Building.query.filter(A.Building.name.ilike('%union%')).first().category
    w.answers['union_category'] = cat
    page = w.click('/map/building/michigan-union', 'open Michigan Union')
    union = A.Building.query.filter_by(name='Michigan Union').first()
    w.answers['union_address'] = union.address
    w.must(page, union.address, 'union address')
    w.back('back to map')
    w.fill('q', 'league')
    page = w.submit('/map', {'q': 'league'}, 'search league buildings')
    page = w.click('/map/building/michigan-league', 'open Michigan League')
    league = A.Building.query.filter_by(name='Michigan League').first()
    w.answers['league_address'] = league.address
    w.must(page, league.address, 'league address')
    w.back('back to map')
    w.select('category', 'Library/Museum')
    page = w.submit('/map', {'category': 'Library/Museum'}, 'filter Library/Museum')
    nlm = A.Building.query.filter_by(category='Library/Museum').count()
    w.answers['library_museum_count'] = nlm
    page = w.click('/map/building/museum-of-natural-history-1', 'open the museum')
    mus = A.Building.query.filter_by(name='Museum of Natural History').first()
    w.answers['museum_zip'] = mus.zip
    login(w, 'alice.j@test.com')
    page = w.go('/admissions/request-info', 'open request info form')
    w.fill('name', 'Alice Parent')
    w.fill('email', 'alice.parent@test.com')
    w.select('audience', 'Parent or Guardian')
    w.fill('message', 'When is the next campus tour?')
    page = w.submit_post('/admissions/request-info', '/admissions/request-info',
                         {'name': 'Alice Parent', 'email': 'alice.parent@test.com',
                          'audience': 'Parent or Guardian',
                          'message': 'When is the next campus tour?'},
                         'submit request')
    w.must(page, 'Thank you', 'confirmation')
    w.answers['confirmation'] = 'Thank you, Alice Parent!'
    w.done()
    return w


def t6(A, w):
    login(w, 'carol.d@test.com')
    page = w.go('/events', 'open events calendar')
    w.select('type', 'Workshop / Seminar')
    page = w.submit('/events', {'type': 'Workshop / Seminar'}, 'filter workshops')
    n = A.EventItem.query.filter_by(type='Workshop / Seminar').count()
    w.answers['workshops'] = n
    w.select('type', '')
    w.fill('q', 'meditat')
    page = w.submit('/events', {'q': 'meditat'}, 'search meditation')
    names = [e.name for e in A.EventItem.query.filter(
        A.EventItem.name.ilike('%meditat%')).all()]
    w.answers['meditation_events'] = names
    ev = A.EventItem.query.filter_by(name='Heartfulness Meditation').first()
    page = w.click(f'/events/{ev.eid}', 'open Heartfulness Meditation')
    w.answers['heartfulness_location'] = ev.location_name
    w.answers['heartfulness_sponsor'] = ev.presenter
    page = w.submit_post(f'/events/save/{ev.eid}', f'/events/{ev.eid}', {},
                         'save event')
    page = w.go('/library', 'open library catalog')
    w.fill('q', 'genomics')
    page = w.submit('/library', {'q': 'genomics'}, 'search genomics')
    ngen = A.LibraryItem.query.filter(A.LibraryItem.title.ilike('%genomics%')).count()
    w.answers['genomics_records'] = ngen
    page = w.go('/myumich', 'open My U-M')
    w.answers['carol_saved_events'] = 2
    w.answers['carol_backpack'] = 1
    w.done()
    return w


def t7(A, w):
    page = w.go('/courses', 'open course catalog')
    w.fill('q', 'writing')
    page = w.submit('/courses', {'q': 'writing'}, 'search writing')
    n = A.Course.query.filter(A.Course.title.ilike('%writing%')).count()
    w.answers['writing_courses'] = n
    w.select('school', 'Literature, Science, and the Arts')
    page = w.submit('/courses', {'q': 'writing', 'school': 'Literature, Science, and the Arts'},
                    'narrow to LSA')
    page = w.click('/courses/subject/ENGLISH', 'open ENGLISH subject')
    c = A.Course.query.filter_by(subject='ENGLISH', number='125').first()
    w.answers['english125_title'] = c.title
    w.answers['english125_sections'] = len(c.sections)
    sec = c.sections[0]
    page = w.click(f'/courses/class/{sec.class_nbr}', 'open first section')
    w.answers['class_nbr'] = sec.class_nbr
    w.answers['instructor'] = sec.instructor
    login(w, 'dana.k@test.com')
    page = w.click(f'/courses/class/{sec.class_nbr}', 'reopen section detail')
    page = w.submit_post(f'/backpack/toggle/{sec.id}',
                         f'/courses/class/{sec.class_nbr}', {},
                         'add to backpack')
    page = w.go('/myumich', 'open My U-M')
    w.answers['dana_backpack'] = 2
    page = w.click('/schools-colleges/lsa', 'open the LSA school page')
    nsubj = len([r[0] for r in A.db.session.query(A.Course.subject)
                 .filter(A.Course.school == 'Literature, Science, and the Arts')
                 .distinct().all()])
    w.must(page, f'{nsubj} subjects', 'LSA course-subject count')
    w.answers['lsa_course_subjects'] = nsubj
    w.done()
    return w


def t8(A, w):
    page = w.go('/schools-colleges', 'open schools & colleges')
    total = A.School.query.count()
    aa = A.School.query.filter_by(campus='Ann Arbor').count()
    w.answers['schools_total'] = total
    w.answers['ann_arbor_schools'] = aa
    w.select('campus', 'Ann Arbor')
    page = w.submit('/schools-colleges', {'campus': 'Ann Arbor'},
                    'filter to Ann Arbor campus')
    page = w.click('/schools-colleges/ross', 'open Ross')
    ross_first = A.Program.query.filter_by(school_slug='ross') \
        .order_by(A.Program.name).first()
    w.answers['ross_programs'] = 2
    w.answers['ross_first_program'] = ross_first.name
    page = w.click(f'/programs/{ross_first.id}', 'open first Ross program')
    w.back('back to Ross page')
    page = w.click('/schools-colleges/stamps', 'open Stamps')
    stamps_first = A.Program.query.filter_by(school_slug='stamps') \
        .order_by(A.Program.name).first()
    w.answers['stamps_programs'] = 2
    w.answers['stamps_first_program'] = stamps_first.name
    page = w.click('/schools-colleges/smtd', 'open SMTD')
    smtd_first = A.Program.query.filter_by(school_slug='smtd') \
        .order_by(A.Program.name).first()
    w.answers['smtd_programs'] = 16
    w.answers['smtd_first_program'] = smtd_first.name
    w.answers['most_programs'] = 'School of Music, Theatre & Dance'
    login(w, 'alice.j@test.com')
    page = w.click(f'/programs/{ross_first.id}', 'reopen first Ross program')
    page = w.submit_post(f'/programs/save/{ross_first.id}',
                         f'/programs/{ross_first.id}', {}, 'save program')
    page = w.go('/myumich', 'open My U-M')
    w.answers['alice_saved_programs'] = 2
    w.done()
    return w

def t9(A, w):
    page = w.go('/programs?letter=a-f', 'open a-f tab')
    n = A.Program.query.filter(A.Program.sort_letter.between('a', 'f')).count()
    w.answers['af_programs'] = n
    w.select('letter', '')
    w.fill('q', 'bio')
    page = w.submit('/programs', {'q': 'bio'}, 'clear the tab back to a-z, search bio')
    nbio = A.Program.query.filter(A.Program.name.ilike('%bio%')).count()
    assert nbio == 15, nbio
    w.answers['bio_programs'] = nbio
    prog = A.Program.query.filter_by(name='Biopsychology, Cognition, and Neuroscience').first()
    page = w.click(f'/programs/{prog.id}', 'open BCN program')
    w.answers['bcn_school'] = prog.school
    slug = prog.school_slug
    page = w.click(f'/schools-colleges/{slug}', 'open the school')
    nls = A.Program.query.filter_by(school_slug=slug).count()
    w.answers['bcn_school_programs'] = nls
    w.fill('q', 'psychology')
    page = w.submit('/programs', {'q': 'psychology'}, 'search psychology programs')
    npsy = A.Program.query.filter(A.Program.name.ilike('%psychology%')).count()
    w.answers['psychology_programs'] = npsy
    login(w, 'carol.d@test.com')
    page = w.click(f'/programs/{prog.id}', 'reopen BCN program')
    page = w.submit_post(f'/programs/save/{prog.id}', f'/programs/{prog.id}', {},
                         'save program')
    page = w.go('/myumich', 'open My U-M')
    w.answers['carol_saved_programs'] = 3
    w.done()
    return w


def t10(A, w):
    login(w, 'bob.c@test.com')
    page = w.go('/library', 'open library catalog')
    w.fill('q', 'machine learning')
    page = w.submit('/library', {'q': 'machine learning'}, 'search ML')
    nml = A.LibraryItem.query.filter(A.LibraryItem.title.ilike('%machine learning%')).count()
    w.answers['ml_records'] = nml
    w.select('type', 'Thesis')
    page = w.submit('/library', {'q': 'machine learning', 'type': 'Thesis'},
                     'narrow to theses')
    first = A.LibraryItem.query.filter(
        A.LibraryItem.title.ilike('%machine learning%'), A.LibraryItem.type == 'Thesis') \
        .order_by(A.LibraryItem.title).first()
    page = w.click(f'/library/item/{first.uuid}', 'open first thesis')
    w.answers['thesis_title'] = first.title
    w.answers['thesis_year'] = first.date_issued
    w.back('back to catalog')
    w.fill('q', 'jazz')
    page = w.submit('/library', {'q': 'jazz'}, 'search jazz')
    nj = A.LibraryItem.query.filter(A.LibraryItem.title.ilike('%jazz%')).count()
    w.answers['jazz_records'] = nj
    firstj = A.LibraryItem.query.filter(A.LibraryItem.title.ilike('%jazz%')) \
        .order_by(A.LibraryItem.title).first()
    page = w.click(f'/library/item/{firstj.uuid}', 'open first jazz record')
    w.answers['jazz_type'] = firstj.type
    c = A.Course.query.filter_by(subject='ECON', number='102').first()
    sec = c.sections[0]
    page = w.click(f'/courses/class/{sec.class_nbr}', 'open ECON 102 first section')
    w.must(page, 'Add this class to my Backpack', 'ECON 102 first section not already backpacked')
    page = w.submit_post(f'/backpack/toggle/{sec.id}',
                         f'/courses/class/{sec.class_nbr}', {},
                         'add to backpack')
    page = w.go('/myumich', 'open My U-M')
    w.answers['bob_backpack'] = 3
    w.done()
    return w


def t11(A, w):
    page = w.go('/events', 'open events calendar')
    total = A.EventItem.query.count()
    w.answers['events_total'] = total
    w.select('type', 'Performance')
    page = w.submit('/events', {'type': 'Performance'}, 'filter performances')
    nperf = A.EventItem.query.filter_by(type='Performance').count()
    w.answers['performances'] = nperf
    ev = A.EventItem.query.filter(A.EventItem.name.ilike('%Holly Bowling%')).first()
    page = w.click(f'/events/{ev.eid}', 'open Holly Bowling')
    w.answers['holly_start'] = ev.start
    w.answers['holly_location'] = ev.location_name
    w.back('back to events')
    w.select('type', 'Sporting Event')
    page = w.submit('/events', {'type': 'Sporting Event'}, 'filter sporting events')
    sports = [e.name for e in A.EventItem.query.filter_by(type='Sporting Event').all()]
    w.answers['sporting_events'] = sports
    login(w, 'dana.k@test.com')
    page = w.click(f'/events/{ev.eid}', 'reopen Holly Bowling')
    page = w.submit_post(f'/events/save/{ev.eid}', f'/events/{ev.eid}', {},
                         'save event')
    page = w.go('/myumich', 'open My U-M')
    w.answers['dana_saved_events'] = 2
    w.done()
    return w


def t12(A, w):
    page = w.go('/calendars', 'open academic calendars')
    w.select('term', 'Fall 2026')
    page = w.submit('/calendars', {'term': 'Fall 2026'}, 'select Fall 2026')
    w.must(page, 'Classes begin fall term', 'classes begin')
    w.answers['f26_classes_begin'] = 'Monday, Aug. 31'
    w.answers['thanksgiving'] = 'Wednesday, Nov. 25 - Friday, Nov. 27'
    w.answers['commencement'] = 'Sunday, Dec. 20'
    w.select('type', 'Registration Deadlines')
    page = w.submit('/calendars', {'term': 'Fall 2026',
                                    'type': 'Registration Deadlines'},
                    'switch to registration deadlines')
    w.answers['backpack_opens'] = 'Wednesday, March 18'
    w.select('term', 'Winter 2027')
    w.select('type', 'Academic Calendar')
    page = w.submit('/calendars', {'term': 'Winter 2027',
                                    'type': 'Academic Calendar'},
                    'switch to Winter 2027')
    nw27 = A.CalendarEntry.query.filter_by(
        term='Winter 2027', ctype='Academic Calendar').count()
    w.answers['w27_entries'] = nw27
    w.answers['w27_classes_begin'] = 'Wednesday, Jan. 6'
    page = w.go('/admissions/apply', 'open apply page')
    w.must(page, 'Nov. 1', 'ED deadline')
    w.answers['ed_deadline'] = 'Nov. 1'
    w.answers['ed_decision'] = 'By Dec. 24'
    w.answers['rd_deadline'] = 'Feb. 1'
    ed = A.AppPlan.query.filter(A.AppPlan.plan.ilike('%Early Decision%')).first()
    w.answers['binding_plan'] = ed.plan
    login(w, 'bob.c@test.com')
    page = w.go('/myumich', 'open My U-M')
    w.answers['bob_backpack'] = 2
    w.done()
    return w

def t13(A, w):
    page = w.go('/faculty', 'open faculty directory')
    w.select('subject', 'MATH')
    page = w.submit('/faculty', {'subject': 'MATH'}, 'filter by MATH')
    nmath = A.Instructor.query.filter(A.Instructor.subjects.ilike('%"MATH"%')).count()
    w.answers['math_instructors'] = nmath
    w.fill('q', 'Saha')
    page = w.submit('/faculty', {'subject': 'MATH', 'q': 'Saha'}, 'search Saha')
    person = A.Instructor.query.filter(A.Instructor.name.ilike('%saha%'),
                                       A.Instructor.subjects.ilike('%"MATH"%')).first()
    w.answers['saha_name'] = person.name
    page = w.click(f'/faculty/{person.id}', 'open Saha profile')
    secs = A.Section.query.filter_by(instructor=person.name).all()
    w.answers['saha_sections'] = len(secs)
    sec = sorted(secs, key=lambda s: s.class_nbr)[0]
    page = w.click(f'/courses/class/{sec.class_nbr}', 'open first section')
    w.answers['saha_course'] = f"{sec.course.subject} {sec.course.number}"
    w.answers['saha_status'] = sec.status
    login(w, 'alice.j@test.com')
    page = w.click(f'/courses/class/{sec.class_nbr}', 'reopen section')
    page = w.submit_post(f'/backpack/toggle/{sec.id}',
                         f'/courses/class/{sec.class_nbr}', {}, 'add to backpack')
    page = w.go('/myumich', 'open My U-M')
    w.answers['alice_backpack'] = 3
    page = w.click('/courses/subject/MATH', 'open the MATH subject')
    nmath_courses = A.Course.query.filter_by(subject='MATH').count()
    w.must(page, f'{nmath_courses} courses', 'MATH course count')
    w.answers['math_courses'] = nmath_courses
    w.done()
    return w

def t14(A, w):
    page = w.go('/news', 'open Michigan News')
    latest = A.NewsArticle.query.order_by(A.NewsArticle.published.desc()).first()
    w.answers['latest_story'] = latest.title
    page = w.click('/news?category=arts-culture', 'open arts-culture')
    narts = A.NewsArticle.query.filter(
        A.NewsArticle.categories.ilike('%"arts-culture"%')).count()
    w.answers['arts_stories'] = narts
    art = A.NewsArticle.query.filter_by(
        slug='arts-taking-center-stage-at-u-m-throughout-october').first()
    page = w.click(f'/news/{art.slug}', 'open the arts story')
    w.answers['arts_published'] = art.published
    w.answers['festival_kickoff'] = 'Oct. 1'
    w.must(page, 'Oct. 1', 'festival kickoff')
    page = w.go('/search?q=El+Ni%C3%B1o', 'site search El Niño (task spelling)')
    nino = A.NewsArticle.query.filter(A.NewsArticle.slug.ilike('%el-ninos%')).first()
    w.must(page, 'El Ni', 'search result for the task spelling')
    page = w.click(f'/news/{nino.slug}', 'open El Nino story')
    w.must(page, '40%', 'variability strength')
    w.answers['el_nino_strength'] = 'nearly 40% stronger'
    page = w.go('/news?category=health', 'open health category')
    recent_health = A.NewsArticle.query.filter(
        A.NewsArticle.categories.ilike('%"health"%')) \
        .order_by(A.NewsArticle.published.desc()).first()
    w.answers['recent_health_story'] = recent_health.title
    page = w.click(f'/news/{recent_health.slug}', 'open most recent health story')
    w.answers['recent_health_date'] = recent_health.published
    page = w.go('/events?type=Film+Screening', 'open film screenings')
    nfilm = A.EventItem.query.filter_by(type='Film Screening').count()
    w.answers['film_screenings'] = nfilm
    login(w, 'bob.c@test.com')
    page = w.go('/myumich', 'open My U-M')
    w.answers['bob_backpack'] = 2
    first_b = A.BackpackItem.query.filter_by(user_id=2).order_by(A.BackpackItem.id).first()
    first_sec = A.db.session.get(A.Section, first_b.section_id)
    w.answers['bob_first_course'] = first_sec.course.code()
    w.must(page, first_sec.course.code(), 'first backpack course')
    page = w.click(f'/courses/class/{first_sec.class_nbr}',
                   'open first backpack class detail')
    w.answers['bob_first_instructor'] = first_sec.instructor
    w.done()
    return w


def t15(A, w):
    page = w.go('/map?category=Athletic', 'athletic buildings')
    nath = A.Building.query.filter_by(category='Athletic').count()
    w.answers['athletic_buildings'] = nath
    page = w.go('/map?q=museum', 'search museum buildings')
    nmus = A.Building.query.filter(A.Building.name.ilike('%museum%')).count()
    w.answers['museum_buildings'] = nmus
    page = w.click('/map/building/museum-of-natural-history-1', 'open the museum')
    mus = A.Building.query.filter_by(name='Museum of Natural History').first()
    w.answers['museum_address'] = mus.address
    w.answers['museum_category'] = mus.category
    page = w.go('/map?category=Housing', 'housing buildings')
    nhouse = A.Building.query.filter_by(category='Housing').count()
    w.answers['housing_buildings'] = nhouse
    login(w, 'carol.d@test.com')
    page = w.go('/admissions/request-info', 'open request info')
    w.fill('name', 'Carol Student')
    w.fill('email', 'carol.s@test.com')
    w.select('audience', 'High School Student')
    w.fill('message', 'nursing tours')
    page = w.submit_post('/admissions/request-info', '/admissions/request-info',
                         {'name': 'Carol Student', 'email': 'carol.s@test.com',
                          'audience': 'High School Student', 'message': 'nursing tours'},
                         'submit request')
    w.must(page, 'Thank you', 'confirmation')
    w.answers['confirmation'] = 'Thank you, Carol Student!'
    w.done()
    return w


def t16(A, w):
    page = w.go('/courses', 'open course catalog')
    w.fill('q', 'data')
    page = w.submit('/courses', {'q': 'data'}, 'search data')
    nd = A.Course.query.filter(A.Course.title.ilike('%data%')).count()
    w.answers['data_courses'] = nd
    page = w.click('/courses/subject/STATS', 'open STATS subject')
    c = A.Course.query.filter_by(subject='STATS', number='250').first()
    w.answers['stats250_title'] = c.title
    w.answers['stats250_sections'] = len(c.sections)
    sec = c.sections[0]
    page = w.click(f'/courses/class/{sec.class_nbr}', 'open first section')
    w.answers['stats250_nbr'] = sec.class_nbr
    w.answers['stats250_instructor'] = sec.instructor
    page = w.go('/courses?q=psychology', 'search psychology')
    nps = A.Course.query.filter(A.Course.title.ilike('%psychology%')).count()
    w.answers['psychology_courses'] = nps
    login(w, 'dana.k@test.com')
    page = w.click(f'/courses/class/{sec.class_nbr}', 'reopen the STATS 250 first section')
    w.must(page, 'Add this class to my Backpack', 'STATS 250 first section not already backpacked')
    page = w.submit_post(f'/backpack/toggle/{sec.id}',
                         f'/courses/class/{sec.class_nbr}', {}, 'add to backpack')
    page = w.submit_post(f'/backpack/toggle/{sec.id}',
                         f'/courses/class/{sec.class_nbr}', {},
                         'remove from backpack')
    page = w.go('/myumich', 'open My U-M')
    w.answers['dana_backpack'] = 1
    w.done()
    return w


def t17(A, w):
    page = w.go('/programs', 'open majors & degrees')
    total = A.Program.query.count()
    w.answers['programs_total'] = total
    w.fill('q', 'nursing')
    page = w.submit('/programs', {'q': 'nursing'}, 'search nursing')
    nn = A.Program.query.filter(A.Program.name.ilike('%nursing%')).count()
    w.answers['nursing_programs'] = nn
    prog = A.Program.query.filter_by(name='Nursing').first()
    page = w.click(f'/programs/{prog.id}', 'open Nursing program')
    w.answers['nursing_school'] = prog.school
    slug = prog.school_slug
    page = w.click(f'/schools-colleges/{slug}', 'open nursing school')
    nsp = A.Program.query.filter_by(school_slug=slug).count()
    w.answers['nursing_school_programs'] = nsp
    w.fill('q', 'pharmaceutical')
    page = w.submit('/programs', {'q': 'pharmaceutical'}, 'search pharmaceutical programs')
    npharm = A.Program.query.filter(A.Program.name.ilike('%pharmaceutical%')).count()
    assert npharm >= 1, npharm
    w.answers['pharmaceutical_programs'] = npharm
    login(w, 'carol.d@test.com')
    page = w.click(f'/programs/{prog.id}', 'reopen Nursing program')
    page = w.submit_post(f'/programs/save/{prog.id}', f'/programs/{prog.id}', {},
                         'save program again')
    page = w.go('/myumich', 'open My U-M')
    w.answers['carol_saved_programs'] = 2
    w.done()
    return w


def t18(A, w):
    page = w.go('/events?q=yoga', 'search yoga events')
    names = [e.name for e in A.EventItem.query.filter(
        A.EventItem.name.ilike('%yoga%')).all()]
    w.answers['yoga_events'] = names
    ev = A.EventItem.query.filter_by(name='Lunchtime Yoga').first()
    page = w.click(f'/events/{ev.eid}', 'open Lunchtime Yoga')
    w.answers['yoga_type'] = ev.type
    w.answers['yoga_start'] = ev.start
    w.answers['yoga_sponsor'] = ev.presenter
    page = w.go('/events?type=Well-being', 'filter well-being')
    nwb = A.EventItem.query.filter_by(type='Well-being').count()
    w.answers['wellbeing_events'] = nwb
    m = A.EventItem.query.filter_by(name='CEW+ Midweek Mindfulness').first()
    page = w.click(f'/events/{m.eid}', 'open Midweek Mindfulness')
    w.answers['mindfulness_location'] = m.location_name
    w.select('type', 'Sporting Event')
    page = w.submit('/events', {'type': 'Sporting Event'}, 'filter sporting events')
    sports = [e.name for e in A.EventItem.query.filter_by(type='Sporting Event').all()]
    w.answers['sporting_events'] = sports
    hockey = A.EventItem.query.filter(A.EventItem.name.ilike('%Ice Hockey vs Bowling Green%')).first()
    page = w.click(f'/events/{hockey.eid}', 'open ice hockey event')
    w.answers['hockey_location'] = hockey.location_name
    login(w, 'bob.c@test.com')
    page = w.click(f'/events/{ev.eid}', 'reopen Lunchtime Yoga')
    page = w.submit_post(f'/events/save/{ev.eid}', f'/events/{ev.eid}', {},
                         'save event')
    page = w.go('/myumich', 'open My U-M')
    w.answers['bob_saved_events'] = 2
    w.done()
    return w


def t19(A, w):
    page = w.go('/calendars', 'open academic calendars')
    w.select('term', 'Fall 2025')
    page = w.submit('/calendars', {'term': 'Fall 2025'}, 'select Fall 2025')
    w.answers['f25_classes_begin'] = 'Monday, Sept. 1'
    w.answers['f25_study_break'] = 'Monday, Oct. 20 - Tuesday, Oct. 21'
    w.must(page, 'Classes begin', 'classes begin entry')
    w.select('term', 'Winter 2026')
    page = w.submit('/calendars', {'term': 'Winter 2026'}, 'switch to Winter 2026')
    w.answers['w26_classes_begin'] = 'Wednesday, Jan. 7'
    w.select('term', 'Winter 2027')
    page = w.submit('/calendars', {'term': 'Winter 2027'}, 'switch to Winter 2027')
    nw27 = A.CalendarEntry.query.filter_by(
        term='Winter 2027', ctype='Academic Calendar').count()
    w.answers['w27_entries'] = nw27
    page = w.go('/admissions/costs', 'open costs')
    w.answers['resident_ud_tuition'] = '$21,268'
    w.answers['nonresident_ld_total'] = '$88,394'
    w.must(page, '$88,394', 'nonresident total')
    login(w, 'alice.j@test.com')
    page = w.go('/myumich', 'open My U-M')
    first_sec = A.BackpackItem.query.filter_by(user_id=1) \
        .order_by(A.BackpackItem.id).first()
    sec = A.db.session.get(A.Section, first_sec.section_id)
    page = w.click(f'/courses/class/{sec.class_nbr}', 'open first backpack class')
    w.answers['first_backpack_instructor'] = sec.instructor
    w.answers['alice_saved_programs'] = 1
    w.answers['alice_saved_events'] = 1
    w.done()
    return w


WALKERS = [t0, t1, t2, t3, t4, t5, t6, t7, t8, t9,
           t10, t11, t12, t13, t14, t15, t16, t17, t18, t19]


def run_round(tag):
    counts = []
    for i, walker in enumerate(WALKERS):
        A, c2, root, ctx = fresh_client(f'{tag}-t{i}')
        w = Walker(c2)
        try:
            walker(A, w)
        finally:
            ctx.pop()
            shutil.rmtree(root, ignore_errors=True)
        counts.append(w.steps)
        print(f'  [{tag}] task {i}: {w.steps} steps')
    return counts


def main():
    print('round 1:')
    r1 = run_round('r1')
    print('round 2:')
    r2 = run_round('r2')
    print('round 1:', r1)
    print('round 2:', r2)
    agree = r1 == r2
    print('rounds agree:', agree)
    print('min:', min(r1), 'max:', max(r1),
          'mean:', round(sum(r1) / len(r1), 1))
    if not agree:
        print('FAIL: rounds disagree')
        return 1
    if min(r1) < MIN_STEPS:
        print(f'FAIL: a task is under {MIN_STEPS} steps')
        return 1
    print('all tasks >= 15 honest steps')
    return 0


if __name__ == '__main__':
    sys.exit(main())
