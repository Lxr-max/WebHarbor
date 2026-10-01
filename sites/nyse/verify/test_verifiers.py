#!/usr/bin/env python3
"""test_verifiers.py — adversarial contract tests for the nyse verifier suite
(review branch orch/review/nyse, r2 re-freeze synced to the fix branch
orch/contribute/nyse @ ab719484).

Guarantees (run with pytest):
  * each honest fixture (from the reviewer's two independent Playwright rounds
    on the r2 review container wh-nyse-r2, seed md5
    b7c3bbfa3a7a64b8d09b4e7fb3323fd9) PASSES its verify_<n>.py;
  * every adversarial negative FAILS (zero false positives):
      - no-op trajectories (20),
      - answer-only shortcuts with no navigation (20),
      - wrong-answer trajectories (20, fabricated per question point),
      - stale-DB trajectories (all 12 stateful tasks: the DB delta is undone
        while the answer claims success),
      - read-only violations (all 8 read-only tasks get an injected write),
      - tampered packages (wrong task_id / off-site URL / cross-port URL /
        not-terminated / empty answer / pre-mutated seed),
      - task-specific confusions (T8 NIO toggled OFF instead of adding KO,
        T7 wrong alert deleted, T12 wrong alert deleted, T2 wrong page-title,
        T19 wrong ticker, T0/T14/T19 alert-leg confusions).
"""
from __future__ import annotations

import json
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

VERIFY = Path(__file__).resolve().parent
EV = Path("/data/zhaoyang-user-projects/websyn/wh-nyse-r2-rereview-evidence")
FIXTURES = EV / "fixtures"
TMP = EV / "verify_runs" / "_pytest_tmp"
PY = sys.executable

TASK_IDS = [f"NYSE--{n}" for n in range(20)]
# r2: T8 is stateful again (its leg adds KO to Dana's watchlist).
STATEFUL = [0, 1, 3, 5, 8, 10, 12, 14, 16, 17, 18, 19]
READ_ONLY = [n for n in range(20) if n not in STATEFUL]


def run_verifier(n: int, run_dir: Path):
    proc = subprocess.run(
        [PY, str(VERIFY / f"verify_{n}.py"), "--run_dir", str(run_dir)],
        capture_output=True, text=True, timeout=180)
    try:
        verdict = json.loads(proc.stdout)
    except json.JSONDecodeError:
        verdict = {"pass": False, "reason": proc.stdout[-300:] or proc.stderr[-300:]}
    return verdict


def clone(n: int, tag: str) -> Path:
    dst = TMP / f"{n}_{tag}"
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(FIXTURES / str(n), dst)
    return dst


def set_traj(run_dir: Path, **changes):
    p = run_dir / "trajectory.json"
    traj = json.loads(p.read_text())
    traj.update(changes)
    p.write_text(json.dumps(traj, indent=2))


def mutate_answer(run_dir: Path, new_answer: str):
    set_traj(run_dir, final_answer=new_answer)


def mutate_db(run_dir: Path, which: str, sql: str):
    db = sqlite3.connect(run_dir / which)
    db.execute(sql)
    db.commit()
    db.close()


def drop_nav(run_dir: Path):
    """Replace the whole trajectory with a homepage-only no-op walk."""
    p = run_dir / "trajectory.json"
    traj = json.loads(p.read_text())
    base = traj.get("start_url", "http://localhost:46128/")
    step = {"step": 0, "url": base, "url_after": base, "action": "navigate",
            "thought": "look around", "screenshot_before": None,
            "screenshot_after": None}
    for s in traj.get("steps", []):
        for key in ("screenshot_before", "screenshot_after"):
            s.pop(key, None)
    traj["steps"] = [step]
    p.write_text(json.dumps(traj, indent=2))


def keep_answer_drop_nav(run_dir: Path):
    drop_nav(run_dir)


# ---------------------------------------------------------------- honest PASS --

@pytest.mark.parametrize("n", range(20))
def test_honest_fixture_passes(n):
    verdict = run_verifier(n, FIXTURES / str(n))
    assert verdict["pass"], f"NYSE--{n} honest fixture must PASS: {verdict['reason']}"


# ---------------------------------------------------------------- no-op FAIL --

NOOP_ANSWER = {
    0: "The Agilent quote page shows sector Healthcare and CEO Padraig McDonnell. "
       "Third expiry tab lowest strike 60.00, put/call ratio 0.75. Alice's watchlist "
       "shows 4 symbols with last prices KO 86.84, DIS 105.41, NKE 35.84, A 175.03. "
       "The new A alert below 170 with the note Lab spinout is Pending; Alice has "
       "2 alerts in total.",
    1: "NOK has sector Technology, CEO Justin Hotard, 52-week high on Wednesday, June 03, 2026. "
       "Watchlist shows 1 symbol. First Priced deal is Accelevation Holdings Corp. at 18.00. "
       "Largest 10 in 90 days top issuer is Csquare, Inc. with proceeds 1.21B. "
       "Backlog industry with most current deals is Technology.",
    2: "September Opening Bells: 21 events. Last page top event: Oracle (NYSE: ORCL) Rings The "
       "Opening Bell. Vanguard ceremony date: September 29th, 2026. IPO matches: 1. "
       "Closing Bell page 2 first: Labcorp Holdings Inc. (NYSE: LH) Rings The Closing Bell.",
    3: "KO last 86.84, 52-week high Monday, August 24, 2026; 5Y chart first date 2021/09/30. "
       "Alcoa 52-week low 32.85. Bob has 3 alerts in total.",
    4: "SPY: 21 listings match, last 764.20, 52-week high 779.37, second expiry highest strike "
       "950.00, put/call ratio 1.97. Auspice index: AUSPICE BROAD COMMODITY EXCESS RETURN INDEX, "
       "last 4,955.41. NIO: sector Consumer Discretionary, volume 706,930, 1Y last 2026/09/29.",
    5: "REITs tab has 144 listings. ABR: sector Financials, last 3.97, first board member Caryn "
       "Effron (term 5). Carol's final watchlist shows 1 symbol: ABR.",
    6: "First Priced deal: Accelevation Holdings Corp. at 18.00. Largest 10 in 90 days: Csquare, "
       "Inc., proceeds 1.21B. 180-day window shows 10 rows. Pricing stats top sector Healthcare "
       "with 84% within range. Ives Ultra AI exchange: New York Stock Exchange. NASDAQ deals: 5. "
       "Backlog: Technology.",
    7: "SDEV last 3.27, 52-week low 0.78. Alert status Pending; Dana has 2 alerts, 1 after "
       "deleting. Carnival 52-week high date: Friday, February 06, 2026.",
    8: "Buttonwood Agreement 1792; the NYSE moved into a new building with a much "
       "larger Trading Floor in 1903. September Closing Bells: 21, first: Arcos "
       "Dorados Rings The Closing Bell. First NYSE mover NU HOLDINGS LTD last 12.35; "
       "American rows 10. Dana watchlist total 4 (SPY, NIO, AMC, KO).",
    9: "ABCERI: AUSPICE BROAD COMMODITY EXCESS RETURN INDEX, last 4,955.41, 1Y last "
       "2026/09/29. BABA: CEO N/A, market cap 1.82T, beta 0.79, EPS 4.50, 52-week low "
       "91.99, first expiry lowest strike 80.00. NIO: 19 matches, sector Consumer "
       "Discretionary, 1Y last 2026/09/29.",
    10: "gold matches 13 listings. AAAU last 41.16, exchange heading Cboe BZX. After removing the "
        "gold stock 1 symbol remains: NIO.",
    11: "TECHNOLOGIES matches 132. First name descending: ZYMEWORKS INC (US). First REIT: sector "
        "Real Estate & REITs, 52-week high Thursday, July 16, 2026, 1Y last 2026/09/29. Realty "
        "matches 24, first result volume 843. Backlog: Technology. Stats: Healthcare. American "
        "rows 10.",
    12: "Bob's symbols: AAPL, TSLA. TSLA beta 1.84, RSI 44.80. AAPL 52-week high 345.34. 3 alerts "
        "before, 2 after deleting AAPL; the new TSLA alert is Pending.",
    13: "Vanguard: The Vanguard Group Rings The Closing Bell on September 29th, 2026. September "
        "Opening Bells: 21; last page top: Oracle Rings The Opening Bell. Bell intro: One of the "
        "most familiar images of the NYSE on the evening news is the loud ringing of a bell. "
        "Bob's watchlist: AAPL, TSLA; second symbol last price 352.84.",
    14: "IBM last 219.99, average volume 5,653,953, sector Technology, CEO Arvind "
        "Krishna, 13 board members. 1M last 2026/09/29; 5Y first 2021/09/30. Second "
        "expiry highest strike 310.00. Alice watchlist 4 symbols. The IBM alert below "
        "200 is Pending; Alice has 2 alerts in total.",
    15: "Filings total 9 deals. Postponed first: Bamboo Insurance Services, Inc. New York Stock "
        "Exchange deals: 2, first Ives Ultra AI Opportunities Inc. Filed: 3. First Priced: "
        "Accelevation. Latest month Sep'26: 1.72B proceeds, 5 deals. Backlog: Technology.",
    16: "DIS sector Media & Communications, 52-week low 92.19, dividend yield 1.42. Alice "
        "watchlist 3 symbols. Bob sees 2 alerts: AAPL, TSLA.",
    17: "Header search Vanguard: 5 listings, 2 bell events. Description: The New York Stock "
        "Exchange welcomes Vanguard in celebration of 25 years of Vanguard ETFs. KO dividend "
        "yield 2.44, beta 0.34. Alert status Pending; Alice has 2 alerts. First NYSE American "
        "mover last 3.27.",
    18: "Page 3 first linked row ABT: last 100.95, volume 1,462. UNITED matches 22. Dana "
        "watchlist 4, then 3 after removing NIO. NU sector Financials.",
    19: "First Priced deal: ACCV, Technology. 180-day window shows 10 rows. AERO sector "
        "Industrials, 52-week low 12.26, 1Y first date 2025/11/06, second expiry lowest "
        "strike 5.00. Carol watchlist 2 symbols. The AERO alert above 16 is Pending; "
        "Carol has 1 alert in total.",
}


@pytest.mark.parametrize("n", range(20))
def test_noop_fails(n):
    run_dir = clone(n, "noop")
    drop_nav(run_dir)
    mutate_answer(run_dir, "")
    verdict = run_verifier(n, run_dir)
    assert not verdict["pass"], f"NYSE--{n} no-op must FAIL"


@pytest.mark.parametrize("n", range(20))
def test_answer_only_shortcut_fails(n):
    """Correct answer, but the agent never navigated anywhere (memory recall)."""
    run_dir = clone(n, "shortcut")
    keep_answer_drop_nav(run_dir)
    mutate_answer(run_dir, NOOP_ANSWER[n])
    verdict = run_verifier(n, run_dir)
    assert not verdict["pass"], f"NYSE--{n} answer-only shortcut must FAIL"


WRONG_ANSWERS = {
    0: "A sector is Information Technology and CEO is Mike McMullen; third expiry lowest strike "
       "55.00 with put/call ratio 1.10. Alice's watchlist shows 5 symbols. The A alert is "
       "Triggered and Alice has 3 alerts.",
    1: "The highest-volume NYSE mover is NU; sector Financials, CEO David Velez Osorno, 52-week "
       "high January 29, 2026. Watchlist 2 symbols. First Priced Ives Ultra at 10.00; Largest-90 "
       "top is Accelevation with 540.00M; backlog industry Financials.",
    2: "September Opening Bells: 18. Last page top event: Cognizant Rings The Opening Bell. "
       "Vanguard date October 1st, 2026. IPO matches: 3. Closing Bell page 2 first: GE Rings "
       "The Closing Bell.",
    3: "KO last 92.10, 52-week high Monday, December 01, 2025; 5Y first date 2021/06/01. Alcoa "
       "52-week low 28.40. Bob has 4 alerts.",
    4: "SPY: 18 matches, last 771.02, 52-week high 801.20, exp2 highest 900.00, ratio 1.41. "
       "Auspice: CANE INDEX last 25.10. NIO: Technology sector, volume 2,100,000, 1Y last "
       "2026/09/25.",
    5: "REITs tab has 142 listings. Second REIT is ACRES COMMERCIAL REALTY CORP: sector "
       "Healthcare, last 7.15, board chair James Sullivan (term 7). Carol's watchlist: 2 symbols.",
    6: "First Priced deal: ADARx at 17.00. Largest-90 top: Jersey Mike's Subs Inc. 1,059.17M. "
       "180-day window shows 8 rows. Stats top sector Financials with 77%. IVAI exchange: NASDAQ. "
       "NASDAQ deals: 6. Backlog: Healthcare.",
    7: "Highest American volume is BTG; last 5.34, 52-week low 2.10. Alert status Triggered; "
       "Dana 3 alerts then 2. Carnival 52-week high: Monday, March 02, 2026.",
    8: "Buttonwood Agreement signed 1791; the exchange moved into its new larger building "
       "in 1865. September Closing Bells: 19; first: Vanguard Rings The Closing Bell. First NYSE "
       "mover NOK last 10.36; American rows 8. Dana watchlist 2.",
    9: "ABCERI: AUSPICE index last 5,000.00, 1Y last 2026/09/25. BABA CEO Eddie Wu, market cap "
       "2.10T, beta 0.95, EPS 6.10, 52-week low 85.50, first expiry lowest strike 70.00. NIO: "
       "12 matches, sector Technology.",
    10: "gold search returned 9 listings. First gold listing GLD last 245.12 on NYSE Arca. After "
        "removing the gold stock 2 symbols remain.",
    11: "TECHNOLOGIES: 105 matches. First name descending: ZYNERBA BIO. First REIT sector "
        "Healthcare, 52-week high June 30, 2026, 1Y last 2026/09/28. Realty: 21 matches, volume "
        "2,415. Backlog: Consumer Services. Stats: Financials. American rows 8.",
    12: "Bob's symbols: TSLA, AAPL. TSLA beta 2.01, RSI 61.35. AAPL 52-week high 320.15. Alerts "
        "2 before, 3 after. New alert Triggered.",
    13: "Vanguard ceremony October 2nd, 2026. September Opening Bells: 24; last page top: "
        "Snoopy Rings The Opening Bell. Bell intro: The NYSE bell is one of the most familiar. "
        "Bob's watchlist: KO, DIS; second last 86.84.",
    14: "IBM last 224.50, average volume 4,982,110, sector Financials, CEO Dario Gil, 9 board "
        "members. 1M last 2026/09/28; 5Y first 2022/01/05. Second expiry highest 300.00. Alice "
        "watchlist 5. The IBM alert is Triggered and Alice has 3 alerts.",
    15: "Filings total 11 deals. Postponed first: Oura Inc. NYSE deals: 4, first Accelevation. "
        "Filed: 2. First Priced: ADARx. Latest month Aug'26: 2.04B. Backlog: Consumer Services.",
    16: "DIS sector Consumer Discretionary, 52-week low 88.10, dividend yield 1.85. Alice "
        "watchlist 4 symbols. Bob sees 3 alerts: AAPL, TSLA, DIS.",
    17: "Vanguard search: 8 listings, 4 bell events. Description: Vanguard celebrates ETFs. KO "
        "dividend yield 1.90, beta 0.55. Alert status Triggered; Alice has 3 alerts. First "
        "American mover last 2.95.",
    18: "Page 3 first row AA: last 39.85, volume 5,000,000. UNITED matches 19. Dana watchlist 3 "
        "then 4 after. NU sector Technology.",
    19: "First Priced deal: ADRX, Healthcare. 180-day window shows 8 rows. AERO sector "
        "Consumer Discretionary, 52-week low 9.75, 1Y first 2025/09/10, second expiry lowest "
        "7.50. Carol watchlist 3. The AERO alert is Triggered and Carol has 2 alerts.",
}


@pytest.mark.parametrize("n", range(20))
def test_wrong_answer_fails(n):
    run_dir = clone(n, "wrong")
    mutate_answer(run_dir, WRONG_ANSWERS[n])
    verdict = run_verifier(n, run_dir)
    assert not verdict["pass"], f"NYSE--{n} wrong answer must FAIL"


@pytest.mark.parametrize("n", STATEFUL)
def test_stale_db_fails(n):
    """The state change in after.db is undone while the answer claims success."""
    run_dir = clone(n, "stale")
    shutil.copyfile(run_dir / "initial.db", run_dir / "after.db")
    verdict = run_verifier(n, run_dir)
    assert not verdict["pass"], f"NYSE--{n} stale DB must FAIL"


@pytest.mark.parametrize("n", READ_ONLY)
def test_readonly_violation_fails(n):
    """An unexpected write on a read-only task must FAIL."""
    run_dir = clone(n, "dirty")
    mutate_db(run_dir, "after.db",
              "INSERT INTO watch_items (user_id, symbol, added_at) VALUES (1, 'AAPL', '2026-09-29')")
    verdict = run_verifier(n, run_dir)
    assert not verdict["pass"], f"NYSE--{n} read-only violation must FAIL"


# ---------------------------------------------------------------- tamper cases --

@pytest.mark.parametrize("n", range(20))
def test_wrong_task_id_fails(n):
    run_dir = clone(n, "wrongid")
    set_traj(run_dir, task_id=f"NYSE--{(n + 1) % 20}")
    verdict = run_verifier(n, run_dir)
    assert not verdict["pass"]


@pytest.mark.parametrize("n", range(20))
def test_offsite_url_fails(n):
    run_dir = clone(n, "offsite")
    set_traj(run_dir, start_url="https://www.nyse.com/")
    verdict = run_verifier(n, run_dir)
    assert not verdict["pass"]


@pytest.mark.parametrize("n", range(20))
def test_cross_port_url_fails(n):
    run_dir = clone(n, "crossport")
    p = run_dir / "trajectory.json"
    traj = json.loads(p.read_text())
    for s in traj["steps"]:
        for key in ("url", "url_after"):
            if s.get(key) and "localhost" in str(s[key]):
                s[key] = str(s[key]).replace("46128", "99999")
    p.write_text(json.dumps(traj, indent=2))
    verdict = run_verifier(n, run_dir)
    assert not verdict["pass"]


@pytest.mark.parametrize("n", range(20))
def test_not_terminated_fails(n):
    run_dir = clone(n, "openend")
    set_traj(run_dir, terminated=False, termination_reason="max_steps")
    verdict = run_verifier(n, run_dir)
    assert not verdict["pass"]


@pytest.mark.parametrize("n", range(20))
def test_empty_answer_fails(n):
    run_dir = clone(n, "empty")
    mutate_answer(run_dir, "   ")
    verdict = run_verifier(n, run_dir)
    assert not verdict["pass"]


@pytest.mark.parametrize("n", range(20))
def test_premutated_seed_fails(n):
    """initial.db no longer equals the frozen seed (seed identity gate)."""
    run_dir = clone(n, "badseed")
    mutate_db(run_dir, "initial.db", "DELETE FROM watch_items WHERE id = 1")
    mutate_db(run_dir, "after.db", "DELETE FROM watch_items WHERE id = 1")
    verdict = run_verifier(n, run_dir)
    assert not verdict["pass"], f"NYSE--{n} pre-mutated seed must FAIL"


# ------------------------------------------------------- task-specific cases --

def test_t8_nio_toggled_off_fails():
    """r2 T8: the task adds Coca-Cola (KO) — NOT in Dana's seeded watchlist.
    An agent that instead toggles a seeded symbol off (removing NIO) must
    FAIL: the DB shows a removal instead of the required dana/KO add, and
    the reported total is wrong."""
    run_dir = clone(8, "niooff")
    mutate_db(run_dir, "after.db", "DELETE FROM watch_items WHERE user_id = 4 AND symbol = 'NIO'")
    mutate_answer(run_dir, NOOP_ANSWER[8].replace("Dana watchlist total 4", "Dana watchlist total 3"))
    verdict = run_verifier(8, run_dir)
    assert not verdict["pass"]


def test_t8_ko_missing_but_answer_claims_fours():
    """r2 T8: no KO row added, yet the answer claims a total of 4."""
    run_dir = clone(8, "nokO")
    shutil.copyfile(run_dir / "initial.db", run_dir / "after.db")
    verdict = run_verifier(8, run_dir)
    assert not verdict["pass"]


def test_t0_wrong_alert_symbol_fails():
    """r2 T0 alert leg: the created alert is on the wrong symbol (DIS instead
    of A) — row template mismatch must FAIL even with a perfect answer."""
    run_dir = clone(0, "wrongalertsym")
    mutate_db(run_dir, "after.db",
              "UPDATE price_alerts SET symbol = 'DIS' WHERE user_id = 1 AND symbol = 'A'")
    verdict = run_verifier(0, run_dir)
    assert not verdict["pass"]


def test_t14_wrong_alert_direction_fails():
    """r2 T14 alert leg: the IBM alert is 'above' 200 instead of 'below'."""
    run_dir = clone(14, "wrongalertdir")
    mutate_db(run_dir, "after.db",
              "UPDATE price_alerts SET direction = 'above' WHERE user_id = 1 AND symbol = 'IBM'")
    verdict = run_verifier(14, run_dir)
    assert not verdict["pass"]


def test_t19_wrong_alert_threshold_fails():
    """r2 T19 alert leg: the AERO alert threshold is 160 instead of 16."""
    run_dir = clone(19, "wrongalertthr")
    mutate_db(run_dir, "after.db",
              "UPDATE price_alerts SET threshold = 160.0 WHERE user_id = 3 AND symbol = 'AERO'")
    verdict = run_verifier(19, run_dir)
    assert not verdict["pass"]


def test_t7_wrong_alert_deleted_fails():
    """T7 must delete the SDEV alert it just created. Deleting Dana's seeded
    NIO alert instead leaves the SDEV alert behind: a price_alerts delta on a
    read-only-graded task."""
    run_dir = clone(7, "wrongdel")
    db = sqlite3.connect(run_dir / "after.db")
    db.execute("DELETE FROM price_alerts WHERE user_id = 4 AND symbol = 'NIO'")
    db.commit()
    db.close()
    verdict = run_verifier(7, run_dir)
    assert not verdict["pass"]


def test_t12_wrong_alert_deleted_fails():
    """T12 must delete the AAPL alert. Deleting the seeded TSLA alert instead
    must FAIL (row template mismatch)."""
    run_dir = clone(12, "wrongdel")
    db = sqlite3.connect(run_dir / "after.db")
    # restore AAPL, remove the seeded TSLA-above-200 instead
    db.execute("INSERT INTO price_alerts (id, user_id, symbol, direction, threshold, note, created_at) "
               "VALUES (2, 2, 'AAPL', 'below', 300.0, NULL, '2026-09-29')")
    db.execute("DELETE FROM price_alerts WHERE id = 3")
    db.commit()
    db.close()
    verdict = run_verifier(12, run_dir)
    assert not verdict["pass"]


def test_t2_wrong_page_title_fails():
    run_dir = clone(2, "wrongtitle")
    mutate_answer(run_dir, NOOP_ANSWER[2].replace("Oracle (NYSE: ORCL)", "Cognizant (NYSE: CTSH)"))
    verdict = run_verifier(2, run_dir)
    assert not verdict["pass"]


def test_t19_wrong_ticker_fails():
    run_dir = clone(19, "wrongticker")
    mutate_answer(run_dir, NOOP_ANSWER[19].replace("ACCV", "ADR X").replace("Technology", "Healthcare"))
    verdict = run_verifier(19, run_dir)
    assert not verdict["pass"]
