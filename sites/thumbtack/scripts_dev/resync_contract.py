#!/usr/bin/env python3
"""resync_contract.py — audit-rail contract re-sync for the 17 deepened
thumbtack tasks (one-shot writer; provenance artifact).

Context: review round 2 (CONVERGED) recorded re-review observation R1 — the
deepened tasks.jsonl (orch/contribute/thumbtack @ a50f9d4f) drifted from the
r1-frozen verifier contract by design (new state legs / answer gates), and
the re-sync was assigned to the integration stage per the student_com
precedent. This audit performs that re-sync from ITS OWN fresh honest walks
(audit container wh-tt-audit @ 127.0.0.1:49100, per-task reset + fresh
context, visible-element interaction only, seed md5 0c1320fd…):

- verify/make_verifiers.py TASKS entries re-frozen for the 15 drifted tasks
  (2,3,6,7,8,9,10,11,12,13,14,16,17,18,19): navigation gates mirror the audit
  walk URLs; answer anchors mirror the audit answers; DB deltas mirror the
  deterministic application writes. verify_0/1/4/5/15 stay byte-frozen (the
  audit walks pass them unchanged).
- verify/verify_N.py regenerated from the updated spec table.
- verify/tests/fixtures_data.py SPECS/MUTATIONS/WRONG_ANSWERS re-frozen for
  the same 15 tasks (SPECS urls/answers and MUTATIONS SQL are derived
  mechanically from the audit run dirs: trajectory.json + initial.db/after.db).
- verify/append_rubrics.py RUBRICS re-synced for the 17 changed rows
  (0,2,3,4,6,7,8,9,10,11,12,13,14,16,17,18,19) and tasks.jsonl rewritten as
  contributor 5-key prefix + the two contract keys.

No answer key is ever written into tasks.jsonl. Pure stdlib; no network.
"""
import json
import re
import sqlite3
import sys
from pathlib import Path

SITE_DIR = Path(__file__).resolve().parents[1]
VERIFY = SITE_DIR / 'verify'
RUNS = Path(sys.argv[1] if len(sys.argv) > 1 else
            '/data/zhaoyang-user-projects/websyn/wh-thumbtack-audit-evidence/runs')
BASE = 'http://localhost:49100'          # audit-rail origin (host-mapped slot)

DRIFTED = [2, 3, 6, 7, 8, 9, 10, 11, 12, 13, 14, 16, 17, 18, 19]
RUBRIC_TASKS = [0, 2, 3, 4, 6, 7, 8, 9, 10, 11, 12, 13, 14, 16, 17, 18, 19]

TS = "2026-09-26 12:00:00.000000"
TSU = "2026-09-26 12:30:00.000000"
TSP = "2026-09-26 12:32:00.000000"


# ===================================================================== helpers
def walk_urls(task_no):
    traj = json.loads((RUNS / f'task{task_no}' / 'trajectory.json').read_text())
    urls = []
    for s in traj['steps']:
        u = (s.get('url_after') or s.get('url', ''))
        u = u.replace('http://127.0.0.1:49100', '')   # emit bare paths
        if u and (not urls or urls[-1] != u):
            urls.append(u)
    if traj.get('final_url') and urls[-1] != traj['final_url']:
        urls.append(traj['final_url'].replace('http://127.0.0.1:49100', ''))
    return urls


def walk_answer(task_no):
    return json.loads((RUNS / f'task{task_no}' / 'trajectory.json').read_text())['final_answer']


def py_str(s):
    return json.dumps(s)  # JSON string escaping is valid Python for str literals


def sql_lit(v):
    """Single-quoted SQL string literal (SQLite convention: '' escapes ')."""
    return "'" + v.replace("'", "''") + "'"


def delta_sql(task_no):
    """Exact row-level SQL delta (INSERT/DELETE/UPDATE) between the audit
    run's initial.db and after.db — application-order, deterministic."""
    conI = sqlite3.connect(RUNS / f'task{task_no}' / 'initial.db')
    conA = sqlite3.connect(RUNS / f'task{task_no}' / 'after.db')
    stmts = []
    order = ['users', 'projects', 'project_matches', 'reviews',
             'saved_pros', 'threads', 'messages']
    for t in order:
        rowsI = conI.execute(f'SELECT * FROM {t}').fetchall()
        rowsA = conA.execute(f'SELECT * FROM {t}').fetchall()
        if rowsI == rowsA:
            continue
        cols = [r[1] for r in conI.execute(f'PRAGMA table_info({t})')]
        setI = {tuple(r) for r in rowsI}
        setA = {tuple(r) for r in rowsA}
        added = [r for r in rowsA if tuple(r) not in setI]
        removed = [r for r in rowsI if tuple(r) not in setA]
        keyI = {r[0]: r for r in rowsI}
        keyA = {r[0]: r for r in rowsA}
        for k in sorted(keyI):
            if k in keyA and tuple(keyI[k]) != tuple(keyA[k]):
                changed = [(c, keyA[k][i]) for i, c in enumerate(cols)
                           if keyI[k][i] != keyA[k][i]]
                sets = ', '.join(f'{c} = {sql_lit(v) if isinstance(v, str) else ("NULL" if v is None else repr(v))}'
                                 for c, v in changed)
                stmts.append(f'UPDATE {t} SET {sets} WHERE id = {k}')
        for r in removed:
            stmts.append(f'DELETE FROM {t} WHERE id = {r[0]}')
        for r in added:
            vals = ', '.join(sql_lit(v) if isinstance(v, str)
                             else ('NULL' if v is None else repr(v)) for v in r)
            stmts.append(f'INSERT INTO {t} VALUES ({vals})')
    conI.close()
    conA.close()
    return stmts


TS_MAP = [(TS, 'TS'), (TSU, 'TSU'), (TSP, 'TSP')]


def sql_pyexpr(stmt):
    """Emit the statement as a Python expression with the frozen mirror
    timestamps factored through the TS/TSU/TSP constants ('...' + TS + '...')."""
    out = []
    rest = stmt
    while True:
        best = None
        for ts, name in TS_MAP:
            lit = "'" + ts + "'"
            i = rest.find(lit)
            if i >= 0 and (best is None or i < best[0]):
                best = (i, lit, name)
        if best is None:
            out.append(py_str(rest))
            break
        i, lit, name = best
        out.append(py_str(rest[:i] + "'"))
        out.append(name)
        rest = "'" + rest[i + len(lit):]
    return ' + '.join(out)


# ============================================================ per-task verifier specs
# Hand-frozen gates/anchors/db-shapes per drifted task; the mechanical
# constants (urls, answers, exact SQL) come from the audit runs above.
Q = {}
for _line in (SITE_DIR / 'tasks.jsonl').read_text().splitlines():
    _r = json.loads(_line)
    Q[_r['id'].split('--')[1]] = _r['ques']

VM = 'check_visited_path(judge, traj, "{}", r"{}")'
DB_ONLY = '    check_only_tables_changed(judge, initial_db, after_db, {})'


def nav(*gates):
    return '    ' + '\n    '.join(VM.format(l, p) for l, p in gates)


def ans(*checks):
    return '    ' + '\n    '.join(checks)


def db(code):
    return '    ' + code


SPECS_V = {}

# ---------------------------------------------------------------- task 2
SPECS_V[2] = dict(
    ques=Q['2'],
    constants="""DJ_AVG = 550
PHOTO_AVG = 150
EVERETT_DJ = "Cessionnation"
EVERETT_DJ_PK = 376863969460043777
DJ_REPLY = "love to be part of it\"""",
    nav=nav(('login page', r'/login'),
            ('wedding DJ cost guide', r'/p/wedding-djs-cost'),
            ('photographer cost guide', r'/p/wedding-photographer-prices'),
            ('DJs category sorted', r'/k/djs/near-me\?sort=highest_rated'),
            ('Everett DJ profile',
             r'/wa/everett/djs/cessionnation/service/376863969460043777'),
            ('DJ message flow', r'/message/376863969460043777|/account/messages/2'),
            ('quote wizard', r'/projects/new\?category=djs'),
            ('project page', r'/projects/6')),
    answ=ans('check_answer_number(judge, answer, "DJ national average", DJ_AVG, "dj")',
             'check_answer_number(judge, answer, "photographer national average", PHOTO_AVG,\n'
             '                        "photographer")',
             'check_answer_phrase(judge, answer, "DJ more expensive", "dj")',
             'check_answer_phrase(judge, answer, "Everett DJ", EVERETT_DJ)',
             'check_answer_phrase(judge, answer, "DJ reply", DJ_REPLY)',
             'check_answer_phrase(judge, answer, "four-hour reception", "four-hour")',
             'check_answer_any(judge, answer, "estimate requested",\n'
             '                     ["estimate", "quote", "request"])'),
    db=db('''check_only_tables_changed(judge, initial_db, after_db,
                              {"threads", "messages", "projects", "project_matches"})
    check_table_added(judge, initial_db, after_db, "threads",
                      [(2, 3, 19, None, None)])
    check_table_added(judge, initial_db, after_db, "messages",
                      [(3, 2, "user", None, None),
                       (4, 2, "pro", None, None)])
    check_table_added(judge, initial_db, after_db, "projects",
                      [(6, 3, 16, "98004", None, None, None, "matched", None)])
    check_table_added(judge, initial_db, after_db, "project_matches",
                      [(26, 6, 23, 1, 527, None, None, 0),
                       (27, 6, 19, 1, 567, None, None, 0),
                       (28, 6, 20, 0, None, None, None, 0),
                       (29, 6, 26, 1, 586, None, None, 0),
                       (30, 6, 22, 1, 520, None, None, 0)])'''),
)

# ---------------------------------------------------------------- task 3
SPECS_V[3] = dict(
    ques=Q['3'],
    constants="""MOST_MENTIONED = "clean"
PATY_PRO_ID = 71
SECOND_CLEANER = "Empire Cleaning Services"
SECOND_PRO_ID = 65
SUPPLIES_REPLY = "we bring all of our own supplies and equipment"
SUNDAY_REPLY = "happy to work around your schedule\"""",
    nav=nav(('login page', r'/login'),
            ('Paty profile',
             r'/wa/lynnwood/house-cleaning/paty-house-cleaning/service/491085485275881476'),
            ('Paty message flow', r'/message/491085485275881476|/account/messages/2'),
            ('house cleaning category sorted', r'/k/house-cleaning/near-me\?sort=highest_rated'),
            ('second cleaner profile',
             r'/wa/kirkland/house-cleaning/empire-cleaning-services/service/476683242989297681'),
            ('second cleaner thread', r'/account/messages/3'),
            ('Paty Sunday follow-up', r'/account/messages/2')),
    answ=ans('check_answer_phrase(judge, answer, "most-mentioned word", MOST_MENTIONED)',
             'check_answer_phrase(judge, answer, "second cleaner", SECOND_CLEANER)',
             'check_answer_phrase(judge, answer, "supplies reply", SUPPLIES_REPLY)',
             'check_answer_phrase(judge, answer, "Sunday reply", SUNDAY_REPLY)'),
    db=db('''check_only_tables_changed(judge, initial_db, after_db, {"threads", "messages"})
    check_table_added(judge, initial_db, after_db, "threads",
                      [(2, 1, PATY_PRO_ID, None, None),
                       (3, 1, SECOND_PRO_ID, None, None)])
    check_table_added(judge, initial_db, after_db, "messages",
                      [(3, 2, "user", None, None),
                       (4, 2, "pro", None, None),
                       (5, 3, "user", None, None),
                       (6, 3, "pro", None, None),
                       (7, 2, "user", None, None),
                       (8, 2, "pro", None, None)])'''),
)

# ---------------------------------------------------------------- task 6
SPECS_V[6] = dict(
    ques=Q['6'],
    constants="""PLUMBER = "Velichkoremodels"
PLUMBER_PRO_ID = 6
URGENT_REPLY = "same-day or next-day"
LOWEST_QUOTE = 51
GUIDE_RANGE = "$50 - $200\"""",
    nav=nav(('login page', r'/login'),
            ('plumbers category sorted',
             r'/k/affordable-plumbing-services/near-me\?sort=highest_rated'),
            ('plumber profile',
             r'/wa/everett/affordable-plumbing-services/velichkoremodels-llc-emergency-restoration-247/service/550902459815264257'),
            ('urgent message flow', r'/message/550902459815264257|/account/messages/2'),
            ('pipe-repair wizard', r'/projects/new\?category=affordable-plumbing-services'),
            ('project page', r'/projects/6'),
            ('plumbers cost guide', r'/p/plumbers-cost')),
    answ=ans('check_answer_phrase(judge, answer, "plumber name", PLUMBER)',
             'check_answer_any(judge, answer, "background checked", ["background checked"])',
             'check_answer_any(judge, answer, "venmo", ["venmo"])',
             'check_answer_phrase(judge, answer, "urgent reply", URGENT_REPLY)',
             'check_answer_number(judge, answer, "lowest quote", LOWEST_QUOTE,\n'
             '                        ["quote", "lowest", "cheapest"])',
             'check_answer_phrase(judge, answer, "guide range", GUIDE_RANGE)'),
    db=db('''check_only_tables_changed(judge, initial_db, after_db,
                              {"saved_pros", "threads", "messages",
                               "projects", "project_matches"})
    check_table_added(judge, initial_db, after_db, "saved_pros",
                      [(14, 4, PLUMBER_PRO_ID, None)])
    check_table_added(judge, initial_db, after_db, "threads",
                      [(2, 4, PLUMBER_PRO_ID, None, None)])
    check_table_added(judge, initial_db, after_db, "messages",
                      [(3, 2, "user", None, None),
                       (4, 2, "pro", None, None)])
    check_table_added(judge, initial_db, after_db, "projects",
                      [(6, 4, 2, "98033", None, "Within a week", None, "matched", None)])
    check_table_added(judge, initial_db, after_db, "project_matches",
                      [(26, 6, 6, 1, 189, None, None, 0),
                       (27, 6, 3, 1, 135, None, None, 0),
                       (28, 6, 1, 1, 51, None, None, 0),
                       (29, 6, 5, 1, 184, None, None, 0),
                       (30, 6, 2, 1, 169, None, None, 0)])'''),
)

# ---------------------------------------------------------------- task 7
SPECS_V[7] = dict(
    ques=Q['7'],
    constants="""NEW_USER = "Nina Patel"
NEW_EMAIL = "nina.p@test.com"
NEW_USERNAME = "nina.p"
N_RESPONDERS = 4
CHEAPEST_QUOTE = 107
HIRED_PRO_ID = 52
WIZARD_ANSWERS = ('[["Number of items", "3 items"], '
                  '["Instructions or make/model provided by client?", '
                  '"Yes, I have assembly instructions or make and model information"]]')""",
    nav=nav(('registration page', r'/register'),
            ('furniture assembly category', r'/k/furniture-assembly/near-me'),
            ('quote wizard', r'/projects/new\?category=furniture-assembly'),
            ('project page', r'/projects/6'),
            ('review form', r'/projects/6/review')),
    answ=ans('check_answer_number(judge, answer, "responders", N_RESPONDERS,\n'
             '                        ["respond", "pros"])',
             'check_answer_number(judge, answer, "cheapest quote", CHEAPEST_QUOTE,\n'
             '                        ["quote", "cheapest"])',
             'check_answer_any(judge, answer, "smooth assembly review",\n'
             '                     ["smooth assembly", "smooth"])'),
    db=db('''check_only_tables_changed(judge, initial_db, after_db,
                              {"users", "projects", "project_matches", "reviews"})
    check_new_user(judge, initial_db, after_db, NEW_EMAIL,
                    "nina.p", NEW_USER)
    check_table_added(judge, initial_db, after_db, "projects",
                      [(6, 5, 9, "98101", None, None, WIZARD_ANSWERS,
                        "completed", None)])
    check_table_added(judge, initial_db, after_db, "project_matches",
                      [(26, 6, 49, 1, 180, None, None, 0),
                       (27, 6, 44, 0, None, None, None, 0),
                       (28, 6, 46, 1, 131, None, None, 0),
                       (29, 6, HIRED_PRO_ID, 1, 107, None, None, 1),
                       (30, 6, 50, 1, 144, None, None, 0)])
    check_table_added(judge, initial_db, after_db, "reviews",
                      [(857, HIRED_PRO_ID, NEW_USER, "Sep 26, 2026", 5,
                        None, "project:6", 1, "user")])'''),
)

# ---------------------------------------------------------------- task 8
SPECS_V[8] = dict(
    ques=Q['8'],
    constants="""SUNDAY_ONE = "Evergreen Home Assist"
SUNDAY_ONE_ID = 54
SUNDAY_TWO = "I.d. Handyman"
SUNDAY_TWO_ID = 55
SUNDAY_TWO_REVIEWS = 56
SLOTS_REPLY = "We do have openings\"""",
    nav=nav(('login page', r'/login'),
            ('handyman category', r'/k/handyman/near-me'),
            ('first Sunday handyman profile',
             r'/wa/mountlake-terrace/handyman/evergreen-home-assist-llc/service/559530045965762575'),
            ('second Sunday handyman profile',
             r'/wa/lynnwood/handyman/id-handyman/service/557383931483373571'),
            ('Sunday message flow', r'/message/557383931483373571|/account/messages/2'),
            ('saved list', r'/account/saved')),
    answ=ans('check_answer_phrase(judge, answer, "Sunday handyman one", SUNDAY_ONE)',
             'check_answer_phrase(judge, answer, "Sunday handyman two", SUNDAY_TWO)',
             'check_answer_number(judge, answer, "more-reviewed handyman reviews",\n'
             '                        SUNDAY_TWO_REVIEWS, "review")',
             'check_answer_phrase(judge, answer, "Sunday slots replies", SLOTS_REPLY)',
             'check_answer_any(judge, answer, "removal from saved",\n'
             '                     ["removed", "remove"])'),
    db=db('''check_only_tables_changed(judge, initial_db, after_db,
                              {"saved_pros", "threads", "messages"})
    check_table_added(judge, initial_db, after_db, "saved_pros",
                      [(15, 1, SUNDAY_TWO_ID, None)])
    check_table_added(judge, initial_db, after_db, "threads",
                      [(2, 1, SUNDAY_TWO_ID, None, None)])
    check_table_added(judge, initial_db, after_db, "messages",
                      [(3, 2, "user", None, None),
                       (4, 2, "pro", None, None),
                       (5, 2, "user", None, None),
                       (6, 2, "pro", None, None)])'''),
)

# ---------------------------------------------------------------- task 9
SPECS_V[9] = dict(
    ques=Q['9'],
    constants="""GUIDE_RANGE = "$174 - $256"
HIRED_PRO = "Ipanema Cleaning Service"
HIRED_PRO_ID = 66
CHEAPEST_QUOTE = 184""",
    nav=nav(('login page', r'/login'),
            ('house cleaning cost guide', r'/p/house-cleaning-prices'),
            ('house cleaning category', r'/k/house-cleaning/near-me'),
            ('quote wizard', r'/projects/new\?category=house-cleaning'),
            ('project page', r'/projects/6'),
            ('review form', r'/projects/6/review')),
    answ=ans('check_answer_phrase(judge, answer, "guide typical range", GUIDE_RANGE)',
             'check_answer_phrase(judge, answer, "hired pro name", HIRED_PRO)',
             'check_answer_number(judge, answer, "cheapest quote", CHEAPEST_QUOTE,\n'
             '                        ["quote", "cheapest", "lowest"])',
             'check_answer_any(judge, answer, "inside/outside verdict",\n'
             '                     ["inside", "outside"])',
             'check_answer_any(judge, answer, "5-star review",\n'
             '                     ["5-star", "five-star", "5 star"])'),
    db=db('''check_only_tables_changed(judge, initial_db, after_db,
                              {"projects", "project_matches", "reviews"})
    check_table_added(judge, initial_db, after_db, "projects",
                      [(6, 2, 1, "98101", None, None, None, "completed", None)])
    check_table_added(judge, initial_db, after_db, "project_matches",
                      [(26, 6, 73, 1, 191, None, None, 0),
                       (27, 6, HIRED_PRO_ID, 1, 184, None, None, 1),
                       (28, 6, 76, 1, 244, None, None, 0),
                       (29, 6, 67, 1, 245, None, None, 0),
                       (30, 6, 65, 1, 227, None, None, 0)])
    check_table_added(judge, initial_db, after_db, "reviews",
                      [(857, HIRED_PRO_ID, "Bob Chen", "Sep 26, 2026", 5,
                        None, "project:6", 1, "user")])'''),
)

# ---------------------------------------------------------------- task 10
SPECS_V[10] = dict(
    ques=Q['10'],
    constants="""MOVER_ONE = "At Moving"
MOVER_TWO = "John Frank Moving"
LOWEST_QUOTE = 199
LOWEST_PRO = "Strok Industries Moving Company"
STROK_RATING = "4.9"
STROK_RESPONSE = "within a day"
N_NEW_QUOTES = 5""",
    nav=nav(('login page', r'/login'),
            ('saved list', r'/account/saved'),
            ('moving project', r'/projects/3'),
            ('lowest-quote pro profile',
             r'/wa/kent/local-movers/strok-industries-moving-company/service/537096908478578695'),
            ('local movers category', r'/k/local-movers/near-me'),
            ('replacement wizard', r'/projects/new\?category=local-movers'),
            ('replacement project page', r'/projects/6')),
    answ=ans('check_answer_phrase(judge, answer, "removed mover one", MOVER_ONE)',
             'check_answer_phrase(judge, answer, "removed mover two", MOVER_TWO)',
             'check_answer_phrase(judge, answer, "lowest-quote pro", LOWEST_PRO)',
             'check_answer_number(judge, answer, "lowest quote", LOWEST_QUOTE,\n'
             '                        ["quote", "lowest"])',
             'check_answer_phrase(judge, answer, "Strok rating", STROK_RATING)',
             'check_answer_phrase(judge, answer, "Strok response speed", STROK_RESPONSE)',
             'check_answer_any(judge, answer, "cancelled", ["cancel"])',
             'check_answer_number(judge, answer, "replacement quotes", N_NEW_QUOTES,\n'
             '                        ["quotes", "respond", "received"])'),
    db=db('''check_only_tables_changed(judge, initial_db, after_db,
                              {"saved_pros", "projects", "project_matches"})
    check_table_removed(judge, initial_db, after_db, "saved_pros", 2,
                        "user_id = 2 AND pro_id IN (117, 119)")
    check_row_updated(judge, initial_db, after_db, "projects", "id = 3",
                      "status", "cancelled")
    check_table_added(judge, initial_db, after_db, "projects",
                      [(6, 2, 15, "98101", None, None, None, "matched", None)])
    check_table_added(judge, initial_db, after_db, "project_matches",
                      [(26, 6, 119, 1, 274, None, None, 0),
                       (27, 6, 117, 1, 174, None, None, 0),
                       (28, 6, 115, 1, 224, None, None, 0),
                       (29, 6, 124, 1, 233, None, None, 0),
                       (30, 6, 118, 1, 261, None, None, 0)])'''),
)

# ---------------------------------------------------------------- task 11
SPECS_V[11] = dict(
    ques=Q['11'],
    constants="""DJ_AVG = 550
MAKEUP_AVG = 167
MAKEUP_RANGE = "$156 - $178"
TARGET_PRO = "Mel Mua"
TARGET_PRO_PK = 549098172844007430
MEL_REPLY = "love to do your makeup\"""",
    nav=nav(('login page', r'/login'),
            ('makeup artist cost guide', r'/p/makeup-artist-prices'),
            ('wedding DJ cost guide', r'/p/wedding-djs-cost'),
            ('makeup artists category sorted',
             r'/k/makeup-artists/near-me\?sort=highest_rated'),
            ('target pro profile',
             r'/wa/redmond/makeup-artists/mel-mua/service/549098172844007430'),
            ('October message flow', r'/message/549098172844007430|/account/messages/2'),
            ('quote wizard', r'/projects/new\?category=makeup-artists'),
            ('project page', r'/projects/6')),
    answ=ans('check_answer_number(judge, answer, "DJ average", DJ_AVG, "dj")',
             'check_answer_number(judge, answer, "makeup artist average", MAKEUP_AVG,\n'
             '                        "makeup")',
             'check_answer_phrase(judge, answer, "makeup guide range", MAKEUP_RANGE)',
             'check_answer_phrase(judge, answer, "target pro", TARGET_PRO)',
             'check_answer_any(judge, answer, "Top Pro status", ["top pro"])',
             'check_answer_phrase(judge, answer, "Mel reply", MEL_REPLY)',
             'check_answer_phrase(judge, answer, "quinceanera", "quincea")'),
    db=db('''check_only_tables_changed(judge, initial_db, after_db,
                              {"threads", "messages", "projects", "project_matches"})
    check_table_added(judge, initial_db, after_db, "threads",
                      [(2, 3, 130, None, None)])
    check_table_added(judge, initial_db, after_db, "messages",
                      [(3, 2, "user", None, None),
                       (4, 2, "pro", None, None)])
    check_table_added(judge, initial_db, after_db, "projects",
                      [(6, 3, 12, "98004", None, None, None, "matched", None)])
    check_table_added(judge, initial_db, after_db, "project_matches",
                      [(26, 6, 129, 1, 159, None, None, 0),
                       (27, 6, 130, 1, 162, None, None, 0),
                       (28, 6, 128, 1, 156, None, None, 0),
                       (29, 6, 131, 1, 158, None, None, 0),
                       (30, 6, 127, 1, 177, None, None, 0)])'''),
)

# ---------------------------------------------------------------- task 12
SPECS_V[12] = dict(
    ques=Q['12'],
    constants="""HIRED_PRO = "Empire Cleaning Services"
HIRED_PRO_ID = 65
HIRED_PRICE = 244
RESPONSE_NOTE = "adjust after an on-site visit"
MOVEOUT_REPLY = "3-4 hours"
SUPPLIES_REPLY = "we bring all of our own supplies\"""",
    nav=nav(('login page', r'/login'),
            ('finished project', r'/projects/1'),
            ('hired pro profile',
             r'/wa/kirkland/house-cleaning/empire-cleaning-services/service/476683242989297681'),
            ('review form', r'/projects/1/review'),
            ('move-out message flow', r'/message/476683242989297681|/account/messages/2')),
    answ=ans('check_answer_phrase(judge, answer, "hired pro name", HIRED_PRO)',
             'check_answer_number(judge, answer, "hired price", HIRED_PRICE,\n'
             '                        ["price", "hired", "quoted"])',
             'check_answer_phrase(judge, answer, "response note", RESPONSE_NOTE)',
             'check_answer_any(judge, answer, "spotless review", ["spotless"])',
             'check_answer_phrase(judge, answer, "move-out reply", MOVEOUT_REPLY)',
             'check_answer_phrase(judge, answer, "supplies reply", SUPPLIES_REPLY)'),
    db=db('''check_only_tables_changed(judge, initial_db, after_db,
                              {"reviews", "threads", "messages"})
    check_table_added(judge, initial_db, after_db, "reviews",
                      [(857, HIRED_PRO_ID, "Alice Johnson", "Sep 26, 2026", 5,
                        None, "project:1", 1, "user")])
    check_table_added(judge, initial_db, after_db, "threads",
                      [(2, 1, HIRED_PRO_ID, None, None)])
    check_table_added(judge, initial_db, after_db, "messages",
                      [(3, 2, "user", None, None),
                       (4, 2, "pro", None, None),
                       (5, 2, "user", None, None),
                       (6, 2, "pro", None, None)])'''),
)

# ---------------------------------------------------------------- task 13
SPECS_V[13] = dict(
    ques=Q['13'],
    constants="""FIRST_CLEANER = "Ipanema Cleaning Service"
SECOND_CLEANER = "Empire Cleaning Services"
SECOND_PRO_ID = 65
SUPPLIES_REPLY = "we bring all of our own supplies and equipment"
SUNDAY_REPLY = "happy to work around your schedule\"""",
    nav=nav(('login page', r'/login'),
            ('existing supplies thread', r'/account/messages/1'),
            ('house cleaning category sorted', r'/k/house-cleaning/near-me\?sort=highest_rated'),
            ('second cleaner profile',
             r'/wa/kirkland/house-cleaning/empire-cleaning-services/service/476683242989297681'),
            ('second cleaner thread', r'/account/messages/2'),
            ('first cleaner Sunday question', r'/account/messages/1')),
    answ=ans('check_answer_phrase(judge, answer, "first cleaner", FIRST_CLEANER)',
             'check_answer_phrase(judge, answer, "second cleaner", SECOND_CLEANER)',
             'check_answer_phrase(judge, answer, "supplies replies", SUPPLIES_REPLY)',
             'check_answer_phrase(judge, answer, "Sunday replies", SUNDAY_REPLY)'),
    db=db('''check_only_tables_changed(judge, initial_db, after_db, {"threads", "messages"})
    check_row_updated(judge, initial_db, after_db, "threads", "id = 1",
                      "updated_at", "2026-09-26 12:32:00.000000")
    check_table_added(judge, initial_db, after_db, "threads",
                      [(2, 1, SECOND_PRO_ID, None, None)])
    check_table_added(judge, initial_db, after_db, "messages",
                      [(3, 2, "user", None, None),
                       (4, 2, "pro", None, None),
                       (5, 2, "user", None, None),
                       (6, 2, "pro", None, None),
                       (7, 1, "user", None, None),
                       (8, 1, "pro", None, None)])'''),
)

# ---------------------------------------------------------------- task 14
SPECS_V[14] = dict(
    ques=Q['14'],
    constants="""GUIDE_RANGE = "$131 - $341"
HIRED_PRO = "Super Attic Solutions"
HIRED_PRO_ID = 38
HIRED_REVIEWS = 123
HIRED_QUOTE = 315""",
    nav=nav(('login page', r'/login'),
            ('exterminator cost guide', r'/p/exterminators-prices'),
            ('exterminators category', r'/k/exterminators/near-me'),
            ('quote wizard', r'/projects/new\?category=exterminators'),
            ('project page', r'/projects/6'),
            ('review form', r'/projects/6/review'),
            ('hired pro profile',
             r'/wa/kirkland/exterminators/super-attic-solutions/service/472430256251617281')),
    answ=ans('check_answer_phrase(judge, answer, "guide typical range", GUIDE_RANGE)',
             'check_answer_phrase(judge, answer, "hired pro name", HIRED_PRO)',
             'check_answer_number(judge, answer, "hired pro reviews", HIRED_REVIEWS,\n'
             '                        "review")',
             'check_answer_number(judge, answer, "hired quote", HIRED_QUOTE,\n'
             '                        ["quote", "quoted"])',
             'check_answer_any(judge, answer, "ants review", ["ants", "ant"])'),
    db=db('''check_only_tables_changed(judge, initial_db, after_db,
                              {"projects", "project_matches", "reviews"})
    check_table_added(judge, initial_db, after_db, "projects",
                      [(6, 2, 11, "98101", None, "Within a week", None,
                        "completed", None)])
    check_table_added(judge, initial_db, after_db, "project_matches",
                      [(26, 6, 36, 1, 250, None, None, 0),
                       (27, 6, 40, 1, 170, None, None, 0),
                       (28, 6, 32, 1, 207, None, None, 0),
                       (29, 6, 41, 1, 137, None, None, 0),
                       (30, 6, HIRED_PRO_ID, 1, 315, None, None, 1)])
    check_table_added(judge, initial_db, after_db, "reviews",
                      [(857, HIRED_PRO_ID, "Bob Chen", "Sep 26, 2026", 5,
                        None, "project:6", 1, "user")])'''),
)

# ---------------------------------------------------------------- task 16
SPECS_V[16] = dict(
    ques=Q['16'],
    constants="""GUIDE_RANGE = "$40 - $100"
GUIDE_AVG = 55
TARGET_PRO = "Gaskill Personal Training"
TARGET_PRO_PK = 285389944820876322
GASKILL_REPLY = "morning and evening slots\"""",
    nav=nav(('login page', r'/login'),
            ('personal trainer cost guide', r'/p/personal-trainer-cost'),
            ('trainers category sorted', r'/k/personal-trainers/near-me\?sort=highest_rated'),
            ('target pro profile',
             r'/wa/bellevue/personal-trainers/gaskill-personal-training/service/285389944820876322'),
            ('twice-a-week message flow',
             r'/message/285389944820876322|/account/messages/2'),
            ('quote wizard', r'/projects/new\?category=personal-trainers'),
            ('project page', r'/projects/6')),
    answ=ans('check_answer_phrase(judge, answer, "guide typical range", GUIDE_RANGE)',
             'check_answer_number(judge, answer, "guide average", GUIDE_AVG, "average")',
             'check_answer_phrase(judge, answer, "target pro", TARGET_PRO)',
             'check_answer_phrase(judge, answer, "Gaskill reply", GASKILL_REPLY)',
             'check_answer_any(judge, answer, "twice-a-week quote",\n'
             '                     ["twice-a-week", "twice a week"])'),
    db=db('''check_only_tables_changed(judge, initial_db, after_db,
                              {"threads", "messages", "projects", "project_matches"})
    check_table_added(judge, initial_db, after_db, "threads",
                      [(2, 4, 136, None, None)])
    check_table_added(judge, initial_db, after_db, "messages",
                      [(3, 2, "user", None, None),
                       (4, 2, "pro", None, None)])
    check_table_added(judge, initial_db, after_db, "projects",
                      [(6, 4, 14, "98033", None, None, None, "matched", None)])
    check_table_added(judge, initial_db, after_db, "project_matches",
                      [(26, 6, 136, 1, 67, None, None, 0),
                       (27, 6, 138, 1, 90, None, None, 0),
                       (28, 6, 135, 1, 98, None, None, 0),
                       (29, 6, 133, 1, 60, None, None, 0),
                       (30, 6, 137, 1, 68, None, None, 0)])'''),
)

# ---------------------------------------------------------------- task 17
SPECS_V[17] = dict(
    ques=Q['17'],
    constants="""N_RESPONDERS = 4
LOWEST_QUOTE = 127
HIRED_PRO = "Mmy"
HIRED_PRO_ID = 160
WIZARD_ANSWERS = ('[["Conceal cables/wires?", "Yes, I need to conceal cables and wires"], '
                  '["Sound system", "Sound bar"], '
                  '["TV installation location", "Wall mount above fireplace"]]')""",
    nav=nav(('login page', r'/login'),
            ('TV mounting category', r'/k/tv-wall-mount-install/near-me'),
            ('quote wizard', r'/projects/new\?category=tv-wall-mount-install'),
            ('project page', r'/projects/6'),
            ('review form', r'/projects/6/review')),
    answ=ans('check_answer_number(judge, answer, "responders", N_RESPONDERS,\n'
             '                        ["respond", "pros"])',
             'check_answer_number(judge, answer, "lowest quote", LOWEST_QUOTE,\n'
             '                        ["quote", "lowest"])',
             'check_answer_phrase(judge, answer, "hired pro", HIRED_PRO)',
             'check_answer_any(judge, answer, "tidy cable review",\n'
             '                     ["tidy cable", "tidy"])'),
    db=db('''check_only_tables_changed(judge, initial_db, after_db,
                              {"projects", "project_matches", "reviews"})
    check_table_added(judge, initial_db, after_db, "projects",
                      [(6, 1, 8, "98052", None, None, WIZARD_ANSWERS,
                        "completed", None)])
    check_table_added(judge, initial_db, after_db, "project_matches",
                      [(26, 6, 162, 1, 220, None, None, 0),
                       (27, 6, 163, 0, None, None, None, 0),
                       (28, 6, HIRED_PRO_ID, 1, 127, None, None, 1),
                       (29, 6, 161, 1, 173, None, None, 0),
                       (30, 6, 159, 1, 187, None, None, 0)])
    check_table_added(judge, initial_db, after_db, "reviews",
                      [(857, HIRED_PRO_ID, "Alice Johnson", "Sep 26, 2026", 5,
                        None, "project:6", 1, "user")])'''),
)

# ---------------------------------------------------------------- task 18
SPECS_V[18] = dict(
    ques=Q['18'],
    constants="""TOP_PRO_NAME = "Mel Mua"
TOP_PRO_PK = 549098172844007430
TOP_HIRES = 121
TOP_REVIEWS = 71
TOP_RESPONSE = "28 min"
TRIAL_REPLY = "love to do your makeup\"""",
    nav=nav(('login page', r'/login'),
            ('services near me', r'/near-me'),
            ('makeup category sorted by hires',
             r'/k/makeup-artists/near-me\?sort=most_hires'),
            ('top pro profile',
             r'/wa/redmond/makeup-artists/mel-mua/service/549098172844007430'),
            ('October 18 message flow',
             r'/message/549098172844007430|/account/messages/2')),
    answ=ans('check_answer_phrase(judge, answer, "top pro name", TOP_PRO_NAME)',
             'check_answer_number(judge, answer, "top hires", TOP_HIRES, "hire")',
             'check_answer_number(judge, answer, "top reviews", TOP_REVIEWS, "review")',
             'check_answer_any(judge, answer, "top pro status", ["top pro"])',
             'check_answer_phrase(judge, answer, "response speed", TOP_RESPONSE)',
             'check_answer_phrase(judge, answer, "trial replies", TRIAL_REPLY)',
             'check_answer_any(judge, answer, "saved", ["saved", "save"])'),
    db=db('''check_only_tables_changed(judge, initial_db, after_db,
                              {"saved_pros", "threads", "messages"})
    check_table_added(judge, initial_db, after_db, "saved_pros",
                      [(14, 3, 130, None)])
    check_table_added(judge, initial_db, after_db, "threads",
                      [(2, 3, 130, None, None)])
    check_table_added(judge, initial_db, after_db, "messages",
                      [(3, 2, "user", None, None),
                       (4, 2, "pro", None, None),
                       (5, 2, "user", None, None),
                       (6, 2, "pro", None, None)])'''),
)

# ---------------------------------------------------------------- task 19
SPECS_V[19] = dict(
    ques=Q['19'],
    constants="""FASTEST_PRO = "Hotwire Hvac Refrigeration & Appliance Repair"
FASTEST_RESPONSE = "1 min"
LOWEST_QUOTE = 130
HIRED_PRO_ID = 18
WIZARD_ANSWERS = ('[["Appliance type", "Refrigerator"], '
                  '["Appliance brand", "GE"]]')""",
    nav=nav(('login page', r'/login'),
            ('appliance category sorted by fastest response',
             r'/k/appliance-repair/near-me\?sort=fastest_response'),
            ('fastest pro profile',
             r'/wa/woodinville/appliance-repair/hotwire-hvac-refrigeration-appliance-repair/service/500453696558571522'),
            ('quote wizard', r'/projects/new\?category=appliance-repair'),
            ('project page', r'/projects/6'),
            ('review form', r'/projects/6/review')),
    answ=ans('check_answer_phrase(judge, answer, "fastest pro", "Hotwire")',
             'check_answer_phrase(judge, answer, "fastest response", FASTEST_RESPONSE)',
             'check_answer_phrase(judge, answer, "GE refrigerator", "GE")',
             'check_answer_number(judge, answer, "lowest quote", LOWEST_QUOTE,\n'
             '                        ["quote", "lowest"])',
             'check_answer_any(judge, answer, "refrigerator review", ["refrigerator"])'),
    db=db('''check_only_tables_changed(judge, initial_db, after_db,
                              {"projects", "project_matches", "reviews"})
    check_table_added(judge, initial_db, after_db, "projects",
                      [(6, 2, 6, "98101", None, None, WIZARD_ANSWERS,
                        "completed", None)])
    check_table_added(judge, initial_db, after_db, "project_matches",
                      [(26, 6, 11, 1, 275, None, None, 0),
                       (27, 6, 9, 1, 328, None, None, 0),
                       (28, 6, HIRED_PRO_ID, 1, 130, None, None, 1),
                       (29, 6, 17, 1, 319, None, None, 0),
                       (30, 6, 14, 1, 232, None, None, 0)])
    check_table_added(judge, initial_db, after_db, "reviews",
                      [(857, HIRED_PRO_ID, "Bob Chen", "Sep 26, 2026", 5,
                        None, "project:6", 1, "user")])'''),
)


# ============================================================ rubrics (17 changed rows)
RUBRICS = {
 0: ("Verify the agent logged in as alice.j@test.com, compared the Thumbtack hires of the "
     "Seattle wedding photographers Jeshua Frees (Clearline Production), Tanner Schmidt and "
     "Liz Ong, saved all three to the saved pros, and then removed the two less popular ones "
     "from the saved list. The answer must state Jeshua Frees has the most hires (69, versus "
     "Tanner Schmidt's 30 and Liz Ong's 26), that only Jeshua Frees remains saved, and that he "
     "has been in business 7 years with 19 employees. Fail answers that pick a different "
     "remaining pro or invent the years or employee count."),
 2: ("Verify the agent logged in as carol.d@test.com, opened the wedding DJ and wedding "
     "photographer cost guides, compared the national averages, then found the highest-rated "
     "DJ based in Everett, messaged them about an October wedding date, and requested an "
     "estimate describing the four-hour wedding reception. The answer must state the wedding "
     "DJ national average ($500-$600, national average cost $550) is more expensive than the "
     "photographer's ($122-$450, national average cost $150) by roughly $400, that the "
     "Everett DJ is Cessionnation, and quote their reply about the October date. Fail answers "
     "that swap the two services, skip the message or the estimate request."),
 3: ("Verify the agent logged in as alice.j@test.com, opened Paty House Cleaning's profile, "
     "identified the most-mentioned review word, checked the newest review for that theme, "
     "messaged Paty about cleaning supplies, asked a second house cleaner the same question, "
     "and followed up with Paty about a Sunday visit. The answer must state customers mention "
     "'clean' most often, that the theme also appears in the newest review, name the second "
     "cleaner (Empire Cleaning Services), and report all three replies: both cleaners bring "
     "all their own supplies and equipment, and Paty works around the customer's schedule "
     "including weekends. Fail answers that claim the customer must provide supplies or omit "
     "any of the three replies."),
 4: ("Verify the agent logged in as alice.j@test.com, opened the pending TV mounting project, "
     "reported its lowest quote and total quote count, cancelled it, and started a replacement "
     "handyman request in zip 98033 for hanging a heavy mirror, answering the questionnaire in "
     "full. The answer must state the lowest quote was $121 from Wa Pro Builders with 5 quotes "
     "in total, that the project was cancelled, and report the replacement request's cheapest "
     "quote ($62). Fail answers that report a different lowest pro, amount, count or "
     "replacement cheapest quote, or that skip the replacement request."),
 6: ("Verify the agent logged in as david.k@test.com, found a plumber who is background checked "
     "and accepts Venmo (Velichkoremodels Llc Emergency Restoration 24/7), saved them, messaged "
     "them to confirm they can handle the urgent leak, requested a pipe-repair quote within a "
     "week describing the leaky kitchen faucet, and compared the lowest quote with the plumbers "
     "cost guide. The answer must name Velichkoremodels, confirm background check and Venmo, "
     "quote their same-day/next-day reply, state the lowest quote ($51), and place it against "
     "the guide's $50-$200 typical range. Fail answers that name a plumber without both "
     "credentials or invent the quote or range."),
 7: ("Verify the agent created a new account (Nina Patel, nina.p@test.com, NewHome2026!), "
     "requested quotes for assembling a large wardrobe and two bookcases in zip 98101 answering "
     "the questionnaire about the three items and the instructions, hired the cheapest pro who "
     "responded, marked the project complete, and left a 5-star review mentioning the smooth "
     "assembly. The answer must state 4 pros responded and the cheapest quote was $107. Fail "
     "answers that report a different responder count or cheapest quote."),
 8: ("Verify the agent logged in as alice.j@test.com, found two handymen whose business hours "
     "include Sunday (Evergreen Home Assist Llc and I.d. Handyman), saved both, messaged the "
     "more-reviewed one (I.d. Handyman, 56 reviews) to confirm a Sunday visit, followed up in "
     "the same thread asking which Sunday time slots they have open, and removed the other "
     "handyman from the saved list. The answer must name both handymen with their Sunday hours "
     "and review counts and report both replies (they have openings and asked for dates). Fail "
     "answers that message the less-reviewed handyman or omit the removal."),
 9: ("Verify the agent logged in as bob.c@test.com, read the house cleaning cost guide, "
     "requested a one-time deep-cleaning quote for a 3-bedroom, 2-bathroom home in zip 98101, "
     "hired the pro with the cheapest quote, marked the project complete, and left a 5-star "
     "review. The answer must state most people pay $174-$256 for a one-time visit, name "
     "Ipanema Cleaning Service as the hired pro with the $184 cheapest quote, and say whether "
     "the price falls inside the guide's typical range (it does). Fail answers that report a "
     "different range, pro or quote, or skip the inside/outside verdict."),
 10: ("Verify the agent logged in as bob.c@test.com, removed the moving companies (At Moving "
      "and John Frank Moving Company) from the saved pros, opened the pending moving project, "
      "reported its lowest quote, checked that pro's profile for rating and response speed, "
      "cancelled the project, and started a smaller studio-move replacement request in zip "
      "98101. The answer must state the lowest quote was $199 from Strok Industries Moving "
      "Company (Excellent 4.9, responds within a day), that the project was cancelled, and "
      "that the studio replacement received 5 quotes. Fail answers that mix up the removed "
      "pros, the lowest quote, or the replacement responder count."),
 11: ("Verify the agent logged in as carol.d@test.com, compared the makeup artist and wedding "
      "DJ cost guides, found the highest-rated Top Pro makeup artist based in Redmond (Mel "
      "Mua), messaged her about an October event, and requested an estimate describing the "
      "quinceanera makeup. The answer must state a DJ is more expensive (averages $550 vs "
      "$167, ranges $500-$600 vs $156-$178), name Mel Mua with Top Pro status, and quote her "
      "reply about the October event. Fail answers that swap the services or skip the message "
      "or estimate request."),
 12: ("Verify the agent logged in as alice.j@test.com, opened the finished house cleaning "
      "project, noted the hired pro's price and response note, checked the pro's profile "
      "reviews, left a 5-star review saying they were thorough including the word 'spotless', "
      "reopened the profile to confirm the review is the most recent one, and messaged the pro "
      "about a move-out clean next month with a supplies follow-up. The answer must state "
      "Empire Cleaning Services was hired at $244, quote the response note, confirm the "
      "spotless review shows as the most recent, and report both message replies. Fail answers "
      "that report a different hired price or omit either reply."),
 13: ("Verify the agent logged in as alice.j@test.com, read the existing message thread about "
      "cleaning supplies, asked a different house cleaner (Empire Cleaning Services) the same "
      "question, followed up with them about Sunday availability, and asked the first cleaner "
      "(Ipanema Cleaning Service) the Sunday question too. The answer must quote what Ipanema "
      "brings (all their own supplies and equipment), state the second cleaner answered the "
      "same way, and report both Sunday replies (both work around the schedule including "
      "weekends) with the comparison. Fail answers that claim either cleaner requires the "
      "customer to provide supplies or omit the comparison."),
 14: ("Verify the agent logged in as bob.c@test.com, read the exterminator cost guide, "
      "requested quotes for indoor ant treatment in zip 98101 within a week from the Top Pro "
      "exterminators, hired the responder with the most reviews, marked the project complete, "
      "left a 5-star review mentioning the ants, and confirmed on the pro's profile that the "
      "review shows. The answer must state exterminators typically run $131-$341, name Super "
      "Attic Solutions (123 reviews) with a $315 quote, and confirm the review appears as the "
      "most recent on the profile. Fail answers that report a different guide range, pro, "
      "review count or quote."),
 16: ("Verify the agent logged in as david.k@test.com, read the personal trainer cost guide, "
      "found the highest-rated personal trainer based in Bellevue (Gaskill Personal Training), "
      "messaged them to confirm twice-a-week slots, and requested a quote describing "
      "twice-a-week strength sessions. The answer must state sessions typically cost $40-$100 "
      "(national average $55), name Gaskill Personal Training, and quote their reply about "
      "morning and evening slots. Fail answers that report a different range or trainer or "
      "skip the message or quote request."),
 17: ("Verify the agent logged in as alice.j@test.com, requested TV mounting quotes in zip "
      "98052 answering the questionnaire to match a 75-inch TV above the fireplace with "
      "concealed cables and a connected sound bar, hired the pro with the lowest quote, marked "
      "the project complete, and left a 5-star review mentioning the tidy cable work. The "
      "answer must state 4 pros responded, that the lowest quote was $127, and name the hired "
      "pro (Mmy). Fail answers that report a different responder count, lowest quote or hired "
      "pro."),
 18: ("Verify the agent logged in as carol.d@test.com, started from the Services near me page, "
      "opened the Events services group's wedding and event makeup category, sorted by Most "
      "hires, checked the top makeup artist's profile for Top Pro status and response speed, "
      "messaged her about an October 18 event, followed up about a pre-event trial, and saved "
      "her to the saved pros. The answer must name Mel Mua with 121 hires and 71 reviews, "
      "state her Top Pro status and 28-minute response time, and report both replies. Fail "
      "answers that name a different artist or invent the hires, reviews or replies."),
 19: ("Verify the agent logged in as bob.c@test.com, found the appliance repair specialist who "
      "responds fastest (Hotwire Hvac Refrigeration & Appliance Repair, about 1 min), "
      "requested a quote describing the emergency repair for the GE refrigerator, hired the "
      "pro with the lowest quote, and left a 5-star review mentioning the refrigerator. The "
      "answer must name Hotwire, state the lowest quote received ($130), and confirm the "
      "GE refrigerator description and the review. Fail answers that name a different "
      "specialist or invent the quote."),
}

# ============================================================ wrong answers (15 drifted)
WRONG = {
 2: ("The wedding photographer is more expensive at $550; DJs average $150. The Everett DJ "
     "Cessionnation responds in about 4 hours; no message or estimate was sent."),
 3: ("Customers mention 'thorough' most often. Paty said I must provide all cleaning supplies "
     "myself; the second cleaner never replied and Paty is closed on Sundays."),
 6: ("Saved George Gas Piping (no background check) and requested a quote about the dripping "
     "faucet; the lowest quote was $200, right at the top of the guide's range."),
 7: ("5 pros responded and the cheapest quote was $180; I hired the most expensive one and "
     "left a 3-star review."),
 8: ("Messaged Evergreen Home Assist Llc (12 reviews); they said they have no Sunday "
     "openings. I.d. Handyman was kept in the saved list."),
 9: ("A one-time visit typically costs $40-$55 per hour; the cheapest quote $184 is outside "
     "that range. I hired Sirlene's Cleaning and left a 4-star review."),
 10: ("Removed I.d. Handyman from saved pros; the lowest quote was $241 from At Moving; I "
      "cancelled and the studio replacement got 2 quotes."),
 11: ("The makeup artist is more expensive at $550; Mel Mua has a 4.8 rating and accepts only "
      "cash; no estimate was requested."),
 12: ("Left a 4-star review saying the job was fine; it appears at the bottom of the reviews. "
      "Empire quoted $184 and never replied to the move-out message."),
 13: ("Ipanema said they bring their own supplies; the second cleaner said I must provide "
      "everything; only the first cleaner answered the Sunday question."),
 14: ("Hired Attic Crawl Inc (110 reviews) with a quote of $207; the guide range is $50-$200; "
      "my review does not show on the profile."),
 16: ("Sessions typically cost $55-$100; requested a quote from Jason Joyce Fitness instead "
      "of the Bellevue trainer; no message was sent."),
 17: ("5 pros responded and the lowest quote was $220 from Wa Pro Builders; I hired them and "
      "left a 4-star review about the price."),
 18: ("The top makeup artist is Cessionnation with 121 hires and 71 reviews; she said she is "
      "booked and does not do trials; she was not saved."),
 19: ("The fastest responder is Fresh Start Pro Llc (15 min); the lowest quote was $232; I "
      "hired them and left a 3-star review about the delay."),
}


# ============================================================ writers
def write_make_verifiers():
    path = VERIFY / 'make_verifiers.py'
    src = path.read_text()
    for n in DRIFTED:
        spec = SPECS_V[n]
        entry = (f'TASKS[{n}] = V({n},\n'
                 f'"""{spec["ques"]}""",\n'
                 f'"""{spec["constants"]}\n""",\n'
                 f"'''{spec['nav']}''',\n"
                 f"'''{spec['answ']}''',\n"
                 f"'''{spec['db']}''')\n")
        # replace from the task marker to the next task marker (or EOF section)
        pat = re.compile(
            rf'# -+ task {n}\n'
            rf'TASKS\[{n}\] = V\(.*?\'\'\'\)\n', re.S)
        if not pat.search(src):
            raise SystemExit(f'make_verifiers: task {n} block not found')
        src = pat.sub(lambda _m: f'# ---------------------------------------------------------------- task {n}\n' + entry, src, count=1)
    # header provenance note
    src = src.replace(
        "deltas mirror the deterministic application writes (PYTHONHASHSEED=0 seed +\n"
        "det_hash quotes for project id 6).\n\"\"\"",
        "deltas mirror the deterministic application writes (PYTHONHASHSEED=0 seed +\n"
        "det_hash quotes for project id 6).\n\n"
        "Audit-rail re-freeze (2026-09-28, re-sync of re-review observation R1):\n"
        "tasks 2,3,6,7,8,9,10,11,12,13,14,16,17,18,19 re-frozen from the AUDIT\n"
        "walks on the audit container wh-tt-audit @ 127.0.0.1:49100 (same\n"
        "deterministic seed md5 0c1320fd…, per-task reset + fresh context,\n"
        "visible-element interaction only); tasks 0/1/4/5/15 keep the reviewer's\n"
        "r2-frozen ground truth (the audit walks pass them unchanged).\n\"\"\"")
    path.write_text(src)
    print('make_verifiers.py: 15 TASKS entries re-frozen + header updated')


def write_fixtures():
    path = VERIFY / 'tests' / 'fixtures_data.py'
    src = path.read_text()
    # SPECS entries for the drifted tasks
    for n in DRIFTED:
        urls = walk_urls(n)
        answer = walk_answer(n)
        url_lines = ',\n              '.join(f'BASE + {py_str(u)}' for u in urls)
        entry = (f'    {n}: dict(\n'
                 f'        urls=[{url_lines}],\n'
                 f'        answer={py_str(answer)},\n'
                 f'    ),')
        pat = re.compile(rf'    {n}: dict\((?:.|\n)*?\n    \),', re.S)
        if not pat.search(src):
            raise SystemExit(f'fixtures SPECS: task {n} block not found')
        src = pat.sub(lambda _m: entry, src, count=1)
    # MUTATIONS entries for the drifted tasks (replace existing, insert new)
    for n in DRIFTED:
        stmts = delta_sql(n)
        body = ',\n        '.join(sql_pyexpr(s) for s in stmts)
        entry = f'    {n}: [\n        {body},\n    ],'
        pat = re.compile(rf'    {n}: \[\n(?:.|\n)*?\n    \],', re.S)
        if pat.search(src):
            src = pat.sub(lambda _m: entry, src, count=1)
        else:
            # new stateful task: insert after the numerically preceding entry
            prev = max(int(k) for k in
                       re.findall(r'^    (\d+): \[', src, re.M) if int(k) < n)
            prev_pat = re.compile(rf'    {prev}: \[\n(?:.|\n)*?\n    \],', re.S)
            m = prev_pat.search(src)
            if not m:
                raise SystemExit(f'fixtures MUTATIONS: cannot locate entry {prev} '
                                 f'to insert {n} after')
            src = src[:m.end()] + '\n' + entry + src[m.end():]
    # WRONG_ANSWERS for the drifted tasks
    for n in DRIFTED:
        entry = f'    {n}: {py_str(WRONG[n])},'
        pat = re.compile(rf'    {n}: "(?:.|\n)*?",\n')
        if not pat.search(src):
            raise SystemExit(f'fixtures WRONG_ANSWERS: task {n} not found')
        src = pat.sub(entry + '\n', src, count=1)
    # header provenance
    src = src.replace(
        "both verified against fresh honest walks on the round-2 review container\n"
        "(wh-tt-rereview, same deterministic seed).\"\"\"",
        "both verified against fresh honest walks on the round-2 review container\n"
        "(wh-tt-rereview, same deterministic seed).\n\n"
        "Audit-rail re-freeze (2026-09-28, re-sync of re-review observation R1):\n"
        "the 15 deepened tasks (2,3,6,7,8,9,10,11,12,13,14,16,17,18,19) re-frozen\n"
        "from the audit walks on the audit container wh-tt-audit @\n"
        "127.0.0.1:49100 (same deterministic seed md5 0c1320fd…, per-task reset +\n"
        "fresh context, visible-element interaction only). SPECS urls/answers and\n"
        "MUTATIONS statements are derived mechanically from those runs'\n"
        "trajectory.json and initial.db/after.db pairs by\n"
        "scripts_dev/resync_contract.py. Tasks 0/1/4/5/15 keep the r2-frozen\n"
        "values (the audit walks pass them unchanged).\"\"\"")
    src = src.replace('BASE = "http://localhost:46100"',
                      'BASE = "http://localhost:49100"')
    path.write_text(src)
    print('fixtures_data.py: SPECS/MUTATIONS/WRONG_ANSWERS re-frozen for 15 tasks + header')


def write_rubrics_and_tasks():
    path = VERIFY / 'append_rubrics.py'
    src = path.read_text()
    for n in RUBRIC_TASKS:
        body = '\n     '.join(re.findall(r'"[^"]*"|"[^"]*"\s*"[^"]*"', RUBRICS[n])[0:200]) \
            if False else None
        # compose the python literal: split into 90-char chunks like the file style
        text = RUBRICS[n]
        chunks = []
        cur = ''
        for w in text.split(' '):
            if len(cur) + len(w) + 1 > 88 and cur:
                chunks.append(cur)
                cur = w
            else:
                cur = (cur + ' ' + w).strip()
        chunks.append(cur)
        lit = '("' + '"\n     "'.join(chunks) + '")'
        pat = re.compile(rf' {n}: \("(?:.|\n)*?"\),', re.S)
        if not pat.search(src):
            raise SystemExit(f'append_rubrics: task {n} not found')
        src = pat.sub(f' {n}: {lit},', src, count=1)
    src = src.replace(
        '"""append_rubrics.py — append verifier_path + judge_rubric to tasks.jsonl.',
        '"""append_rubrics.py — append verifier_path + judge_rubric to tasks.jsonl.\n\n'
        'Audit-rail re-sync (2026-09-28): rubrics for the 17 deepened rows\n'
        '(0,2,3,4,6,7,8,9,10,11,12,13,14,16,17,18,19) rewritten to match the\n'
        'deepened task texts; rows 1/5/15 keep the reviewer\'s r2 rubrics.')
    path.write_text(src)
    # regenerate tasks.jsonl: contributor 5-key prefix + the two contract keys
    rows = []
    rubric_map = {}
    for m in re.finditer(r' (\d+): \("(?:.|\n)*?"\),', src, re.S):
        n = int(m.group(1))
        rubric_map[n] = re.sub(r'\s+', ' ', eval(m.group(0).split(':', 1)[1].strip().rstrip(',')))
    for line in (SITE_DIR / 'tasks.jsonl').read_text().splitlines():
        r = json.loads(line)
        n = int(r['id'].split('--')[1])
        out = {k: r[k] for k in ('web_name', 'id', 'ques', 'web', 'upstream_url')}
        out['verifier_path'] = r['verifier_path']
        out['judge_rubric'] = rubric_map.get(n, r['judge_rubric'])
        assert out['judge_rubric'].strip()
        rows.append(json.dumps(out, ensure_ascii=False))
    (SITE_DIR / 'tasks.jsonl').write_text('\n'.join(rows) + '\n')
    print('append_rubrics.py + tasks.jsonl: 17 rubrics re-synced')


if __name__ == '__main__':
    write_make_verifiers()
    write_fixtures()
    write_rubrics_and_tasks()
    # regenerate the verifier modules from the updated spec table, then restore
    # the two byte-frozen hand-fixed modules that the table intentionally does
    # not model (verify_5/verify_15 carry the reviewer's r2 hand re-freeze
    # comments; make_verifiers TASKS[5]/[15] still hold the r1 values).
    import subprocess
    subprocess.run([sys.executable, str(VERIFY / 'make_verifiers.py')], check=True)
    subprocess.run(['git', 'checkout', '--',
                    str(VERIFY / 'verify_5.py'), str(VERIFY / 'verify_15.py')],
                   check=True, cwd=str(SITE_DIR.parents[1]))
    print('re-sync complete (verify_0/1/4/5/15 byte-frozen; 15 drifted re-frozen)')
