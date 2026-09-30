#!/usr/bin/env python3
"""Deterministic seed builder for the ziprecruiter mirror.

Everything materialized here comes from the tracked source_data/*.json
snapshots (captured 2026-09-29) in a fixed order; the four benchmark
accounts and their saved jobs, applications, alerts, profiles and
resumes are authored fixtures following the u_s_customs/zara precedent:
every job they reference is a real captured upstream row (real jid,
company, salary, city), and every timestamp is a frozen constant so the
SQLite output is byte-reproducible (PYTHONHASHSEED=0).
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))

BENCHMARK_HASH = (
    '$2b$12$qSds4Mr9Wo7VwPWLhompEer88SuxxXFDp31P9etY6v7nfRctNO7B.')

CATEGORIES = [
    ('healthcare', 'Healthcare'),
    ('technology', 'Technology'),
    ('business-finance', 'Business & Finance'),
    ('logistics-warehouse', 'Logistics & Warehouse'),
    ('customer-service', 'Customer Service'),
    ('education', 'Education'),
    ('sales', 'Sales'),
    ('skilled-trades', 'Skilled Trades'),
    ('marketing', 'Marketing'),
]

FAMILY_CATEGORY = {
    'registered-nurse': 'healthcare',
    'licensed-practical-nurse': 'healthcare',
    'software-engineer': 'technology',
    'data-analyst': 'technology',
    'accountant': 'business-finance',
    'project-manager': 'business-finance',
    'warehouse-worker': 'logistics-warehouse',
    'truck-driver': 'logistics-warehouse',
    'customer-service-representative': 'customer-service',
    'receptionist': 'customer-service',
    'teacher': 'education',
    'sales-representative': 'sales',
    'electrician': 'skilled-trades',
    'marketing-manager': 'marketing',
}

KEYWORD_CATEGORY = [
    (('nurse', 'medical', 'health', 'caregiver', 'hospice'), 'healthcare'),
    (('software', 'developer', 'engineer', 'data', 'it ', 'cloud'), 'technology'),
    (('account', 'finance', 'payroll', 'audit'), 'business-finance'),
    (('warehouse', 'forklift', 'driver', 'logistics', 'delivery'), 'logistics-warehouse'),
    (('customer service', 'receptionist', 'front desk', 'call center'), 'customer-service'),
    (('teacher', 'school', 'education', 'tutor'), 'education'),
    (('sales', 'account executive'), 'sales'),
    (('electrician', 'plumber', 'hvac', 'technician', 'maintenance'), 'skilled-trades'),
    (('marketing', 'seo', 'content'), 'marketing'),
]


def _load(name):
    with open(os.path.join(HERE, 'source_data', name), encoding='utf-8') as f:
        return json.load(f)


def category_for(job):
    fam = job.get('family')
    if fam and fam in FAMILY_CATEGORY:
        return FAMILY_CATEGORY[fam]
    t = (job.get('title') or '').lower()
    for kws, cat in KEYWORD_CATEGORY:
        if any(k in t for k in kws):
            return cat
    return 'business-finance'


def seed_all(db, bcrypt, app):
    """Materialize the seed DB from the tracked snapshots. Idempotent."""
    from app import (Application, ApplicationEvent, Article, BlogCategory,
                     Company, Job, JobAlert, JobCategory, JobTitle, Profile,
                     Resume, SalaryStat, SavedJob, SearchSnapshot, TitleFaq,
                     User)

    cat_by_slug = {}
    for slug, name in CATEGORIES:
        cat = JobCategory(name=name, slug=slug)
        db.session.add(cat)
        cat_by_slug[slug] = cat
    db.session.flush()

    # companies (fixed order by slug)
    companies = _load('companies.json')
    co_by_slug = {}
    for co in sorted(companies, key=lambda c: c['slug']):
        row = Company(
            name=co['name'], slug=co['slug'], industry=co.get('industry'),
            size=co.get('size'), hq_city=co.get('hq_city'),
            hq_state=co.get('hq_state'), founded=co.get('founded'),
            website=co.get('website'), logo=co.get('logo'),
            rating_value=co.get('rating_value'),
            rating_count=co.get('rating_count'),
            rating_highlights=json.dumps(co.get('rating_highlights') or []),
            findings=json.dumps(co.get('findings') or []),
            perks=json.dumps([]),
            about=co.get('br_about'),
            sourced_about=co.get('sourced_about'))
        db.session.add(row)
        co_by_slug[co['slug']] = row
    db.session.flush()

    # jobs (fixed order by jid)
    jobs = _load('jobs.json')
    job_by_jid = {}
    for j in sorted(jobs, key=lambda x: x['jid']):
        cat_slug = category_for(j)
        co = co_by_slug.get(j['company_slug'])
        if co is None:
            co = Company(name=j['company_slug'].replace('-', ' '),
                         slug=j['company_slug'])
            db.session.add(co)
            db.session.flush()
            co_by_slug[j['company_slug']] = co
        badges = list(j.get('benefits') or [])
        row = Job(
            jid=j['jid'], title=j['title'], title_slug=j['title_slug'],
            company_id=co.id, city=j['city'], state=j['state'],
            category_id=cat_by_slug[cat_slug].id,
            employment_types=','.join(j['employment_types']),
            remote=j['remote'], experience=j['experience'],
            salary_min=j['salary_min'], salary_max=j['salary_max'],
            salary_period=j['salary_period'], salary_text=j['salary_text'],
            posted_days=j['posted_days'], posted_text=j.get('posted_text'),
            quick_apply=j['quick_apply'], is_new=j['is_new'],
            description_html=j['description_html'],
            badges=json.dumps(badges), soc_code=j.get('soc_code'))
        db.session.add(row)
        job_by_jid[j['jid']] = row
    db.session.flush()

    # title landing pages
    titles = _load('titles.json')
    for t in sorted(titles, key=lambda x: x['slug']):
        db.session.add(JobTitle(name=t['name'], slug=t['slug'],
                                family=t['slug'],
                                category_id=cat_by_slug.get(
                                    FAMILY_CATEGORY.get(t['slug'],
                                                        'business-finance')).id))
    db.session.flush()

    # FAQs per family
    for f in _load('faqs.json'):
        for q in f['items']:
            db.session.add(TitleFaq(title_slug=f['family'],
                                    question=q['question'],
                                    answer_html=q['answer_html']))

    # salary pages
    for s in sorted(_load('salaries.json'),
                    key=lambda x: (x['title_slug'], x['scope'],
                                   x.get('city') or '')):
        nearby = [job_by_jid[jid].id for jid in s['nearby']
                  if jid in job_by_jid]
        db.session.add(SalaryStat(
            title_slug=s['title_slug'], scope=s['scope'], city=s['city'],
            state=s['state'], avg_year=s['avg_year'], avg_hour=s['avg_hour'],
            p10=s['p10'], p25=s['p25'], median=s['median'],
            p75=s['p75'], p90=s['p90'],
            histogram=json.dumps(s['histogram']),
            top_cities=json.dumps(s['top_cities']),
            related=json.dumps([[n, n.lower().replace(' ', '-'), a]
                                for n, a in s['related']]),
            by_state=json.dumps([]),
            nearby_jobs=json.dumps(nearby)))

    # SERP snapshots
    for snap in _load('serp_snapshots.json'):
        order = [job_by_jid[jid].id for jid in snap['page1_order']
                 if jid in job_by_jid]
        db.session.add(SearchSnapshot(
            term=snap['term'], location=snap['location'],
            upstream_total=snap['upstream_total'],
            page1_order=json.dumps(order)))

    # blog
    cats = {}
    def blog_cat(slug, name, parent=None):
        if slug not in cats:
            cats[slug] = BlogCategory(name=name, slug=slug, parent=parent)
            db.session.add(cats[slug])
            db.session.flush()
        return cats[slug]

    root = blog_cat('career-advice', 'Career Advice')
    # Subcategories exactly as the captured articles declare them: the
    # upstream blog nav also lists Tips & Advice / Professional
    # Development, but no captured article lives under them, and the
    # captured articles under Students / Work Life were silently rolled
    # up to the root. Align the category tree with the article data so
    # every listed category holds its articles.
    articles_src = sorted(_load('blog.json'), key=lambda a: a['slug'])
    for sub_slug in sorted({a['category_slug'] for a in articles_src
                            if a.get('category_slug')
                            and a['category_slug'] != 'career-advice'}):
        name = next(a['category_name'] for a in articles_src
                    if a['category_slug'] == sub_slug)
        blog_cat(sub_slug, name, root)
    for art in articles_src:
        cat = cats.get(art['category_slug']) or root
        db.session.add(Article(
            slug=art['slug'], title=art['title'], author=art['author'],
            published=art['published'], modified=art['modified'],
            category_id=cat.id,
            hero=f"blog-{art['slug']}",
            excerpt=None, body_html=art['body_html']))
    db.session.commit()
    seed_benchmark(db, bcrypt, app)


def seed_benchmark(db, bcrypt, app):
    """The four benchmark accounts + their fixtures (idempotent)."""
    from app import (Application, ApplicationEvent, JobAlert, Profile,
                     Resume, SavedJob, User)
    from app import Job

    if User.query.filter_by(is_benchmark=True).count() >= 4:
        return

    def add_user(email, name):
        u = User(email=email, display_name=name,
                 password_hash=BENCHMARK_HASH, is_benchmark=True,
                 created_at='2026-09-01')
        db.session.add(u)
        return u

    def jid_of(jid):
        return Job.query.filter_by(jid=jid).first()

    alice = add_user('alice.j@test.com', 'Alice Johnson')
    bob = add_user('bob.c@test.com', 'Bob Chen')
    carol = add_user('carol.d@test.com', 'Carol Davis')
    dana = add_user('dana.k@test.com', 'Dana Kim')
    db.session.flush()

    # ---------------- profiles -----------------------------------------
    db.session.add(Profile(user_id=alice.id, phone='(718) 555-0134',
                           location='Brooklyn, NY',
                           headline='Registered Nurse, BSN — 6 years ICU',
                           about='ICU nurse looking for a full-time role '
                                 'in the New York metro area.',
                           years_experience=6, willing_remote=False))
    db.session.add(Profile(user_id=bob.id, phone='(415) 555-0198',
                           location='San Francisco, CA',
                           headline='Full-stack software engineer (Python/Go)',
                           about='Backend engineer, 5 years across startups.',
                           years_experience=5, willing_remote=True))
    db.session.add(Profile(user_id=carol.id, phone='(214) 555-0177',
                           location='Dallas, TX',
                           headline='Warehouse lead — forklift certified',
                           about='Warehouse operations lead open to 2nd shift.',
                           years_experience=4, willing_remote=False))
    db.session.add(Profile(user_id=dana.id, phone='(303) 555-0162',
                           location='Denver, CO',
                           headline='Senior Accountant (CPA)',
                           about='Public-accounting trained staff and senior '
                                 'accountant, Denver metro.',
                           years_experience=8, willing_remote=True))

    # ---------------- resumes ------------------------------------------
    db.session.add(Resume(
        user_id=alice.id, title='Registered Nurse — ICU',
        summary='BSN-prepared ICU registered nurse with 6 years of '
                'critical-care experience across Level 1 trauma centers.',
        updated_at='2026-09-24',
        experience=json.dumps([
            ['ICU Registered Nurse', 'New York Health', '2021-03', 'Present',
             'Level 1 trauma ICU; charge nurse for the night shift since 2024.'],
            ['Staff Nurse, Med-Surg', 'Brooklyn Regional Hospital', '2020-06',
             '2021-02', 'Medical-surgical unit, 6:1 ratio, EPIC charting.']]),
        education=json.dumps([
            ['BS, Nursing (BSN)', 'Hunter College', '2020']]),
        skills=json.dumps([['ICU', '6'], ['Ventilator management', '5'],
                          ['EPIC', '6'], ['ACLS', '6'], ['BLS', '6'],
                          ['Charge nurse', '2']])))

    db.session.add(Resume(
        user_id=bob.id, title='Software Engineer — Full Stack',
        summary='Backend-leaning full-stack engineer; Python, Go, Postgres.',
        updated_at='2026-09-19',
        experience=json.dumps([
            ['Software Engineer', 'JOLT', '2023-01', 'Present',
             'Payments API in Go; cut p99 latency 38%.']]),
        education=json.dumps([['BA, Computer Science', 'UW Seattle', '2022']]),
        skills=json.dumps([['Python', '5'], ['Go', '4'], ['PostgreSQL', '5'],
                          ['React', '3']])))

    db.session.add(Resume(
        user_id=dana.id, title='Senior Accountant (CPA)',
        summary='CPA with 8 years across public accounting and industry; '
                'month-end close, audit readiness, NetSuite.',
        updated_at='2026-09-26',
        experience=json.dumps([
            ['Senior Accountant', 'Matter Family Office', '2022-04', 'Present',
             'Own the monthly close for 4 entities; led the NetSuite migration.'],
            ['Staff Accountant II', 'Caribou Financial', '2019-06', '2022-03',
             'Audit prep, reconciliations, and AP/IC review.']]),
        education=json.dumps([
            ['BS, Accounting', 'Metro State Denver', '2018'],
            ['CPA license', 'Colorado BOA', '2020']]),
        skills=json.dumps([['NetSuite', '5'], ['Month-end close', '8'],
                          ['GAAP', '8'], ['Excel', '8'], ['Audit prep', '6'],
                          ['SQL', '3']])))

    # ---------------- saved jobs ---------------------------------------
    def save(user, jid, when):
        j = jid_of(jid)
        if j:
            db.session.add(SavedJob(user_id=user.id, job_id=j.id, saved_at=when))

    save(alice, '06a2fa466a9d2928', '2026-09-26')   # RN Bilingual — Manhattan
    save(alice, '1b13c75885354910', '2026-09-25')   # RN IV Drip — Park Slope
    save(alice, '1d3f1c0f8feb32ef', '2026-09-22')   # RN — Manhattan
    save(bob, '032e0b0150231b0d', '2026-09-27')     # SWE Open Source — SF
    save(bob, '19d6f9232eedc0f5', '2026-09-21')     # SWE — JOLT SF
    save(carol, '09e24b6b221cc39d', '2026-09-24')   # Warehouse Worker — Dallas
    save(dana, '3770eecfc82fcf30', '2026-09-27')    # Senior Accountant — Denver
    save(dana, '0e437270a22657fa', '2026-09-23')    # Staff Accountant — Bellevue

    # ---------------- applications with status timelines ------------------
    def apply(user, jid, applied_at, events, note=None):
        j = jid_of(jid)
        if not j:
            return None
        a = Application(user_id=user.id, job_id=j.id, applied_at=applied_at,
                        status=events[-1][1], cover_note=note)
        db.session.add(a)
        db.session.flush()
        for when, status, ev_note in events:
            db.session.add(ApplicationEvent(application_id=a.id, status=status,
                                            note=ev_note, occurred_at=when))
        return a

    apply(alice, '1d3f1c0f8feb32ef', '2026-09-22',
          [('2026-09-22', 'Applied', '1-Click Application submitted'),
           ('2026-09-24', 'Viewed', 'The employer viewed your application')])
    apply(alice, '06a2fa466a9d2928', '2026-09-26',
          [('2026-09-26', 'Applied', '1-Click Application submitted')])
    apply(bob, '19d6f9232eedc0f5', '2026-09-21',
          [('2026-09-21', 'Applied', '1-Click Application submitted'),
           ('2026-09-23', 'Viewed', 'The employer viewed your application'),
           ('2026-09-27', 'Interviewing',
            'The employer invited you to schedule a phone screen')])
    apply(dana, '3770eecfc82fcf30', '2026-09-20',
          [('2026-09-20', 'Applied', '1-Click Application submitted'),
           ('2026-09-22', 'Viewed', 'The employer viewed your application'),
           ('2026-09-25', 'Withdrawn', 'You withdrew this application')])

    # ---------------- job alerts ----------------------------------------
    db.session.add(JobAlert(user_id=alice.id, term='registered nurse',
                           location='New York, NY', frequency='daily',
                           created_at='2026-09-15'))
    db.session.add(JobAlert(user_id=bob.id, term='software engineer',
                           location='San Francisco, CA', frequency='weekly',
                           created_at='2026-09-18'))
    db.session.add(JobAlert(user_id=carol.id, term='warehouse',
                           location='Dallas, TX', frequency='daily',
                           created_at='2026-09-20'))
    db.session.add(JobAlert(user_id=dana.id, term='accountant',
                           location='Denver, CO', frequency='daily',
                           created_at='2026-09-12'))
    db.session.add(JobAlert(user_id=dana.id, term='remote bookkeeping',
                           location='Anywhere', frequency='weekly',
                           created_at='2026-09-14'))
    db.session.commit()
