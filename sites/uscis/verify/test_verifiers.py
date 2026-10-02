#!/usr/bin/env python3
"""test_verifiers.py — adversarial contract tests for the uscis verifier suite.

Guarantees (run with pytest):
  * each honest fixture (transcribed from the auditor's real Playwright
    walkthroughs of the audit container wh-uscis-audit) PASSES its verify_<n>.py;
  * every adversarial negative FAILS (no false positives):
      - no-op trajectories (20),
      - answer-only shortcuts with no navigation (per read-only task),
      - wrong-answer trajectories (per task),
      - stale-DB trajectories (stateful tasks missing their writes),
      - read-only violations (unexpected DB writes on read-only tasks),
      - tampered packages (wrong task_id / off-site URL / cross-port /
        not-terminated / empty answer / bad PNG / pre-mutated seed),
      - task-specific confusions and audit-deepening negatives (per task).
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
EV = Path("/data/zhaoyang-user-projects/websyn/wh-uscis-audit-evidence")
FIXTURES = EV / "runs"
TMP = EV / "verify_runs" / "_pytest_tmp"
PY = sys.executable

TASK_IDS = [f"USCIS.gov--{n}" for n in range(20)]
READ_ONLY = [n for n in range(20) if n not in (16, 17, 18)]
STATEFUL = {17: "appointments"}


def run_verifier(n: int, run_dir: Path):
    proc = subprocess.run(
        [PY, str(VERIFY / f"verify_{n}.py"), "--run_dir", str(run_dir)],
        capture_output=True, text=True, timeout=120)
    try:
        verdict = json.loads(proc.stdout)
    except json.JSONDecodeError:
        verdict = {"pass": False, "reason": proc.stdout[-300:] or proc.stderr[-300:]}
    return verdict


def clone(n: int, tag: str) -> Path:
    dst = TMP / f"{n}_{tag}"
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(FIXTURES / f"task{n}", dst)
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
    """Strip all step URLs down to the bare start page (no tool navigation)."""
    p = run_dir / "trajectory.json"
    traj = json.loads(p.read_text())
    start = traj["start_url"]
    for step in traj.get("steps", []):
        step["url"] = start
        step["url_after"] = start
    p.write_text(json.dumps(traj, indent=2))


# ---------------------------------------------------------------- happy path
@pytest.mark.parametrize("n", range(20))
def test_honest_fixture_passes(n):
    verdict = run_verifier(n, FIXTURES / f"task{n}")
    assert verdict["pass"], verdict["reason"]


# ---------------------------------------------------------------- no-op
@pytest.mark.parametrize("n", range(20))
def test_noop_fails(n):
    run_dir = clone(n, "noop")
    set_traj(run_dir, steps=[], final_answer="", terminated=False,
             termination_reason="max_steps")
    verdict = run_verifier(n, run_dir)
    assert not verdict["pass"]


# ---------------------------------------------------------------- shortcuts
@pytest.mark.parametrize("n", READ_ONLY)
def test_answer_only_shortcut_fails(n):
    run_dir = clone(n, "shortcut")
    drop_nav(run_dir)
    verdict = run_verifier(n, run_dir)
    assert not verdict["pass"]
    assert any("nav_" in e for e in verdict["evidence"] if e.startswith("FAIL"))


@pytest.mark.parametrize("n", [16, 17, 18])
def test_stateful_shortcut_fails(n):
    run_dir = clone(n, "shortcut")
    drop_nav(run_dir)
    verdict = run_verifier(n, run_dir)
    assert not verdict["pass"]


# ---------------------------------------------------------------- wrong answers
WRONG = {
    0: "Case SRC2210123456 is Form N-400 in Interview status; case SRC2210567890 is Form I-130; the I-130 is further along. The profile ZIP maps to the Arlington Field Office at 1 Main Street, and I-485 there takes 30 Months to 12 Months published May 5, 2020.",
    1: "The form is I-485; status Card Was Produced updated 2025-01-01; interview 11/11/2026 at the Dallas office; bring passport. ZIPs 60601 and 60605 map to the Dallas Field Office, 1100 Commerce Street, district DAL. The N-400 edition is 04/01/24 with one PDF, and Naturalization means serving in the military.",
    2: "I-485 Chicago: 30 Months to 12 Months published May 5, 2020; Miami: 20 to 10 published June 6, 2020; Houston: 40 Months to 30 Months published January 1, 2021; Milwaukee: 15 Months to 5 Months published June 6, 2020. Houston shows the fastest upper bound. Chicago's case categories are I-485 Employment 10 Months to 5 Months and I-485 Family 12 Months to 6 Months. The Miami office is at 100 Biscayne Blvd, and the closest surgeon is DAHLIA CLINIC, 1 OAK STREET, 9 miles away; the Spanish filter leaves 12 results.",
    3: "N-400 Seattle: 5 Months to 2 Months published June 6, 2020; Chicago: 30 to 25 published July 7, 2020; Los Angeles: 25 Months to 20 Months published August 8, 2020. Seattle is fastest. The tool says to call the office. Seattle's case category 485B shows 8 Months to 4 Months. The Seattle office is at 1 Pine Street. Form N-336 costs $500 paper / $450 online and N-565 costs $100.",
    4: "The travel form is I-131A, edition 03/03/25, with only i-131a.pdf. The advance parole fee for a pending I-485 is $755 paper / $700 online; the Reentry Permit category costs $1,000 and is eligible for a fee waiver; a refugee pays $180; the TPS document costs $75; and CNMI residents pay $25.",
    5: "I-485 edition date 04/01/24, PDFs i-485.pdf only. The I-693 page shows edition 03/03/25 and a $50 fee. General fee $1,140 paper / $1,290 online; under 14 filing with a parent $850; 6 filing categories cost $0, including being over 65 and living in a rural area. The payment alert names G-1050 and G-1040, each with a $25 fee.",
    6: "N-400 general fee $640; 400% FPG fee $405; military fee $185; I-912 fee $465; N-600 fees $900 paper / $850 online. Form I-912 is used for appeals. The criteria are income below 50% of the poverty line and owning no car; the benefits named are Medicare and WIC. The household-of-four 150% threshold is $30,000. The civics test page lists 100 Civics Test Questions (M-1778).",
    7: "Closest practice is ALEXANDRIA FAMILY MEDICINE at 1 MAIN STREET, 5.0 miles away; Dr. John Smith, 555-0100, speaks French. The second doctor is DR. JANE DOE who speaks Spanish; the third practice is CAPITAL CLINIC, 100 PENN AVENUE, phone 555-9999. The Arabic filter leaves 9 results, the female filter 2, and the male filter 1. The vaccination page lists Chickenpox first. Form I-693 costs $75 with edition 02/02/26.",
    8: "The 60601 search shows 6 results; the first practice is CHICAGO QUICK CARE, 10 W ADAMS, phone 312-555-0100, 2.1 miles; the second is WESTSIDE FAMILY MEDICINE, 500 OAK STREET, DR. ALAN TUDOR, phone 312-777-1000. The female filter leaves 7 results with first female doctor DR. JANE DOE at WESTSIDE CLINIC; the male filter leaves 9. In Boston the closest practice is BEACON HEALTH at 1 TREMONT, and its filters leave 8 female and 3 male results.",
    9: "ZIP 60601 is served by the New York Field Office at 26 Federal Plaza, district NYC, region E, service center ESC. ZIP 60661 maps to the Milwaukee Field Office. ZIP 53201 maps to the Chicago office, which shares the ESC service center. N-400 at Chicago is 10 Months to 5 Months published June 6, 2020; at Milwaukee 12 to 6 published July 7, 2020. The AAO goal is 90 days and the I-290B fee is $650.",
    10: "ZIP 77002 is served by the Dallas Field Office, designation DAL, 1100 Commerce Street, district HOU. ZIP 77046 maps to the Austin Field Office. The online services are ADIT Stamp and Immigration Judge Grant only. Asylum seekers in Los Angeles may schedule online. Case MSC2210112233 is Form I-130 in Received status; case YSC2210667788 is Form I-90 in Approved status. Form I-90 costs $300 paper / $250 online.",
    11: "The FY2027 first-half H-2B alert was published 10/01/2026; the final receipt date was Oct. 10, 2026 for start dates before May 1, 2027; USCIS will process petitions in received order. The FY2026 second-half alert was published 01/15/2026 with final receipt date Jan. 5, 2026; the FY2027 H-1B alert was published 08/08/2026 with an 85,000 cap. The court-order alert is dated 07/07/2026 and vacates PM-602-0050. The all-news list shows 45 items. The glossary H-1B search returns 12 terms, first Being Human.",
    12: "Release date 08/12/2026 in DALLAS, Texas. Defendant Marko Milic, former police chief, faces one charge of fraud with up to 25 years, investigated by the SEC and IRS. The same-day release about two Chinese aliens was announced in KANSAS CITY: defendants Li Wei and Zhang San, charged with shoplifting. The Cuban release is dated 07/07/2026 and Cabrera faces 5 years; the aunt release is dated 06/06/2026 in Denver. The Refugee search returns 12 terms and Asylum returns 9.",
    13: "Scenario 1: the tool says you must file the N-336 within 90 days and are already registered. Scenario 2 (start over, no citizen parent, 35, never in the armed forces, not an LPR, no citizen spouse, not a U.S. national): the tool says you are eligible immediately and should file the N-400 at any office; the key difference is the filing fee.",
    14: "The tool asks 5 questions; the outcome explains you have been a permanent resident for more than 3 years and need only 2 years of residence.",
    15: "Adjustment of Status means changing employers; Advance Parole is a work permit; Biometrics are blood tests. Searching 'adjustment' returns 12 terms, and the two A-terms are Abroad and Accommodation. The letter-A index lists 40 terms. Asylee means an alien waiting for a visa interview abroad.",
    16: "I booked at the Miami office (MIA) for 2026-12-25 at 08:00 AM, confirmation USCMIA12250800; the view shows Scheduled.",
    17: "My appointment is an ADIT Stamp at Boston (BOS), 2026-10-01 at 10:00 AM; after canceling, I booked a replacement ADIT Stamp in Boston and the view shows both as Confirmed.",
    18: "The address is now 100 Main St, Dallas, TX 75201; aliens have 30 days to report a change of address, with no exemptions.",
    19: "Edition date 09/17/21; PDFs i-765.pdf only. Fees $410 paper / $365 online; pending I-485 fee $180. The NBC record was published June 6, 2020 with 147-C9 showing 3 Months to 1 Month. The pending page tools are: Change your address, Request appointment accommodations, Correct a typographical error, Ask about missing mail, Update your mailing address, Ask about a case taking longer than expected, Check your case status, Check case processing times. The glossary term is Electronic Work Permit (EAD).",
}


@pytest.mark.parametrize("n", range(20))
def test_wrong_answer_fails(n):
    run_dir = clone(n, "wrong")
    mutate_answer(run_dir, WRONG[n])
    verdict = run_verifier(n, run_dir)
    assert not verdict["pass"]


# ---------------------------------------------------------------- stale DB / read-only violations
@pytest.mark.parametrize("n", [16, 17])
def test_stale_db_fails(n):
    """Stateful task with NO DB change (agent forgot to book/cancel)."""
    run_dir = clone(n, "stale")
    shutil.copyfile(run_dir / "initial.db", run_dir / "after.db")
    verdict = run_verifier(n, run_dir)
    assert not verdict["pass"]
    assert any("db_" in e for e in verdict["evidence"] if e.startswith("FAIL"))


def test_stale_db_address_fails():
    run_dir = clone(18, "stale")
    shutil.copyfile(run_dir / "initial.db", run_dir / "after.db")
    verdict = run_verifier(18, run_dir)
    assert not verdict["pass"]


@pytest.mark.parametrize("n", [2, 5, 11])
def test_read_only_violation_fails(n):
    """Read-only task whose DB acquired an unexpected write."""
    run_dir = clone(n, "dirty")
    mutate_db(run_dir, "after.db",
              "INSERT INTO users (email, password_hash, display_name, account_number, "
              "created_at) VALUES ('sneaky@test.com','x','Sneaky','USC999999','2026-09-28')")
    verdict = run_verifier(n, run_dir)
    assert not verdict["pass"]
    assert any("db_read_only" in e for e in verdict["evidence"] if e.startswith("FAIL"))


def test_t16_wrong_office_booking_fails():
    """Booking recorded at the wrong office (HOU instead of BOS)."""
    run_dir = clone(16, "wrongoffice")
    mutate_db(run_dir, "after.db",
              "UPDATE appointments SET office_designation='HOU', office_name='Houston', "
              "confirmation='USCHOU2610050900' WHERE confirmation='USCBOS2610050900'")
    verdict = run_verifier(16, run_dir)
    assert not verdict["pass"]


def test_t17_uncanceled_fails():
    """Cancel flow whose DB still shows the appointment Scheduled."""
    run_dir = clone(17, "uncanceled")
    mutate_db(run_dir, "after.db",
              "UPDATE appointments SET status='Scheduled' "
              "WHERE confirmation='USCHOU2610060945'")
    verdict = run_verifier(17, run_dir)
    assert not verdict["pass"]


def test_t17_rebook_missing_fails():
    """Rebooking forgotten: the DB shows the cancel but no new appointment row."""
    run_dir = clone(17, "norebook")
    conn = sqlite3.connect(run_dir / "after.db")
    conn.execute("DELETE FROM appointments WHERE confirmation != 'USCHOU2610060945'")
    conn.commit()
    conn.close()
    verdict = run_verifier(17, run_dir)
    assert not verdict["pass"]
    assert any("db_appointment_booked" in e for e in verdict["evidence"] if e.startswith("FAIL"))


def test_t18_wrong_address_fails():
    run_dir = clone(18, "wrongaddr")
    mutate_db(run_dir, "after.db",
              "UPDATE users SET street='1 Wrong Way', city='Nowhere', state='XX', "
              "zip='00000' WHERE email='bob.c@test.com'")
    verdict = run_verifier(18, run_dir)
    assert not verdict["pass"]


# ---------------------------------------------------------------- tampered packages
def test_tampered_task_id_fails():
    run_dir = clone(5, "tampered_id")
    set_traj(run_dir, task_id="USCIS.gov--4")
    verdict = run_verifier(5, run_dir)
    assert not verdict["pass"]


def test_tampered_offsite_url_fails():
    run_dir = clone(2, "offsite")
    set_traj(run_dir, start_url="https://www.uscis.gov/")
    verdict = run_verifier(2, run_dir)
    assert not verdict["pass"]


def test_tampered_cross_port_fails():
    run_dir = clone(3, "crossport")
    p = run_dir / "trajectory.json"
    traj = json.loads(p.read_text())
    for step in traj["steps"]:
        if step.get("url"):
            step["url"] = step["url"].replace(":50109", ":51109")
        if step.get("url_after"):
            step["url_after"] = step["url_after"].replace(":50109", ":51109")
    p.write_text(json.dumps(traj, indent=2))
    verdict = run_verifier(3, run_dir)
    assert not verdict["pass"]


def test_tampered_not_terminated_fails():
    run_dir = clone(7, "notterm")
    set_traj(run_dir, terminated=False, termination_reason="max_steps")
    verdict = run_verifier(7, run_dir)
    assert not verdict["pass"]


def test_tampered_empty_answer_fails():
    run_dir = clone(11, "emptyans")
    mutate_answer(run_dir, "")
    verdict = run_verifier(11, run_dir)
    assert not verdict["pass"]


def test_tampered_bad_png_fails():
    run_dir = clone(15, "badpng")
    victim = run_dir / "screenshots" / "step_001.png"
    if victim.exists():
        victim.write_bytes(b"not a png at all")
    verdict = run_verifier(15, run_dir)
    assert not verdict["pass"]


def test_tampered_seed_fails():
    """A pre-mutated initial DB must fail the seed identity gate."""
    run_dir = clone(9, "premutated")
    mutate_db(run_dir, "initial.db",
              "INSERT INTO users (email, password_hash, display_name, account_number, "
              "created_at) VALUES ('pre@test.com','x','Pre','USC888888','2026-09-28')")
    verdict = run_verifier(9, run_dir)
    assert not verdict["pass"]
    assert any("seed_" in e for e in verdict["evidence"] if e.startswith("FAIL"))


# ---------------------------------------------------------------- task-specific confusions
def test_t2_office_swap_fails():
    """Chicago/Miami values swapped between offices."""
    run_dir = clone(2, "swap")
    mutate_answer(run_dir,
                  "I-485 Chicago: 25.5 Months to 11.5 Months, published November 14, "
                  "2018. I-485 Miami: 35.5 Months to 13.5 Months, published November "
                  "14, 2018. Chicago shows the faster upper bound (11.5 vs 13.5 "
                  "months). Chicago's service request date is January 10, 2017: if "
                  "your receipt date is before the service request date shown, your "
                  "case is outside of our normal processing times and you may submit "
                  "an inquiry about your case online. Houston: 26.5 Months to 21 "
                  "Months published September 27, 2018; Milwaukee: 23.5 Months to "
                  "10.5 Months published November 07, 2018. Chicago case categories: "
                  "I-485 Employment 23.5 Months to 13.5 Months; I-485 Family 35.5 "
                  "Months to 13.5 Months. The Miami office is at 8801 NW 7th Avenue; "
                  "the closest surgeon is PHYSICIANS ASSOCIATES, P.A. and the Spanish "
                  "filter leaves 5 results.")
    verdict = run_verifier(2, run_dir)
    assert not verdict["pass"]


def test_t7_wrong_filter_count_fails():
    run_dir = clone(7, "badcount")
    mutate_answer(run_dir,
                  "Closest practice: VAN DORN PEDIATRICS, PC, 2500 NORTH VAN DORN "
                  "STREET, SUITE 102, 2.8 miles away. Doctor: DR. MOHEB ANDRAWIS, "
                  "phone 703-933-0555, spoken language English. Second listing's "
                  "doctor: DR. MONA HANNA who speaks Arabic. Third practice: "
                  "BEAUREGARD MEDICAL CENTER, 4216 KING STREET, phone 703-820-7000. "
                  "Filtering to Arabic-speaking doctors leaves 9 results; the female "
                  "filter leaves 6 and the male filter 3. The vaccination page lists "
                  "Shingles first. Form I-693's filing fee is $0 and its edition is "
                  "01/20/25.")
    verdict = run_verifier(7, run_dir)
    assert not verdict["pass"]


# ------------------------------------------------ audit-deepening negatives
def test_t0_wrong_field_office_and_pt_fails():
    """Audit additions fabricated: profile office + I-485 WAS record."""
    run_dir = clone(0, "badfo")
    mutate_answer(run_dir,
                  "Case SRC2210123456 is Form I-485 (Case Is Being Actively Reviewed), "
                  "most recent history event 2026-08-30; case SRC2210567890 is Form "
                  "I-765 (New Card Is Being Produced), most recent history event "
                  "2026-09-18. USCIS lists the processing office as Washington for "
                  "both. The case that is further along is SRC2210123456. The account "
                  "profile ZIP 22202 is served by the Arlington Field Office, 1 Main "
                  "Street. Form I-485 at that office (WAS): 35.5 Months to 13.5 "
                  "Months, publication date November 14, 2018.")
    verdict = run_verifier(0, run_dir)
    assert not verdict["pass"]
    assert any(k in e for e in verdict["evidence"] if e.startswith("FAIL")
               for k in ("further_along", "field_office", "pt_range"))


def test_t1_wrong_zip2_and_n400_page_fails():
    run_dir = clone(1, "bad60605")
    mutate_answer(run_dir,
                  "Receipt LIN2210890123 is Form N-400, Application for Naturalization. "
                  "Current status: Interview Was Scheduled, updated 2026-09-20. The "
                  "interview is 10/21/2026 at the USCIS Chicago Field Office, 101 West "
                  "Ida B. Wells Drive; the history says to bring green card, state ID, "
                  "and re-entry permits. ZIP 60601 is served by the Chicago Field "
                  "Office but ZIP 60605 maps to the Milwaukee Field Office, 517 E "
                  "Wisconsin Ave, district MIL. The N-400 details page shows edition "
                  "date 03/03/25 with downloadable PDFs n-400.pdf. Glossary, "
                  "Naturalization: How a person not born in the United States "
                  "voluntarily becomes a U.S. citizen.")
    verdict = run_verifier(1, run_dir)
    assert not verdict["pass"]


def test_t2_milwaukee_and_surgeon_fabricated_fails():
    run_dir = clone(2, "badmil")
    mutate_answer(run_dir,
                  "I-485 Chicago: 35.5 Months to 13.5 Months published November 14, "
                  "2018 (service request date January 10, 2017); Miami: 25.5 Months to "
                  "11.5 Months published November 14, 2018 (service request date "
                  "January 02, 2017); Houston: 26.5 Months to 21 Months published "
                  "September 27, 2018 (service request date October 10, 2016); "
                  "Milwaukee: 15 Months to 5 Months published June 6, 2020. Miami "
                  "shows the fastest upper bound. If your receipt date is before the "
                  "service request date shown, your case is outside of our normal "
                  "processing times and you may submit an inquiry about your case "
                  "online. Chicago case categories: I-485 Employment 23.5 Months to "
                  "13.5 Months; I-485 Family 35.5 Months to 13.5 Months. The Miami "
                  "Field Office for ZIP 33101 is at 8801 NW 7th Avenue. The closest "
                  "civil surgeon practice is MIAMI QUICK CARE, 100 BISCAYNE BLVD, 9.9 "
                  "miles away; the Spanish-language filter leaves 2 results.")
    verdict = run_verifier(2, run_dir)
    assert not verdict["pass"]
    assert any(k in e for e in verdict["evidence"] if e.startswith("FAIL")
               for k in ("mil_range", "surgeon_name", "spanish_count"))


def test_t3_n336_n565_fabricated_fails():
    run_dir = clone(3, "badn336")
    mutate_answer(run_dir,
                  "N-400 Seattle: 21 Months to 15.5 Months published April 05, 2019; "
                  "Chicago: 18 Months to 9 Months published April 05, 2019; Los "
                  "Angeles: 17 Months to 10.5 Months published December 18, 2018. "
                  "Chicago shows the fastest upper bound. Seattle's service request "
                  "date is August 03, 2017: if your receipt date is before the "
                  "service request date shown, you may submit an inquiry about your "
                  "case online. Seattle's case category 160A shows 21 Months to 15.5 "
                  "Months. The Seattle Field Office for ZIP 98101 is at 12500 Tukwila "
                  "International Boulevard. Form N-336: $500 paper / $450 online. "
                  "Form N-565: $100 paper / $90 online.")
    verdict = run_verifier(3, run_dir)
    assert not verdict["pass"]
    assert any("n336" in e or "n565" in e for e in verdict["evidence"] if e.startswith("FAIL"))


def test_t4_extra_fee_categories_fabricated_fails():
    run_dir = clone(4, "badfees")
    mutate_answer(run_dir,
                  "The travel document form is I-131, Application for Travel Documents, "
                  "Parole Documents, and Arrival/Departure Records, edition 01/20/25, "
                  "with downloadable PDFs Form I-131 and Instructions for Form I-131. "
                  "Advance parole for someone with a pending Form I-485 costs $630 "
                  "paper / $580 online; the Reentry Permit costs $630 and is not "
                  "eligible for a Fee Waiver request; a refugee holding refugee status "
                  "pays $135; the TPS travel authorization document costs $100 paper / "
                  "$90 online; CNMI long-term residents' advance permission to travel "
                  "costs $250.")
    verdict = run_verifier(4, run_dir)
    assert not verdict["pass"]
    assert any(k in e for e in verdict["evidence"] if e.startswith("FAIL")
               for k in ("refugee_fee", "tps_", "cnmi_fee"))


def test_t5_i693_and_payment_fees_fabricated_fails():
    run_dir = clone(5, "badi693")
    mutate_answer(run_dir,
                  "Form I-485 details page: current edition date 09/18/26, downloadable "
                  "PDFs Form I-485 and Instructions for Form I-485. The immigration "
                  "medical examination form I-693: edition date 03/03/25, downloadable "
                  "PDFs Form I-693, filing fee $50. Fee calculator for Form I-485: "
                  "general filing fee $1,440 paper / $1,390 online; an applicant under "
                  "14 filing with a parent $950 paper; 11 filing categories cost $0. "
                  "The payment alert names Forms G-1450 and G-1650; each one's filing "
                  "fee is $30.")
    verdict = run_verifier(5, run_dir)
    assert not verdict["pass"]
    assert any(k in e for e in verdict["evidence"] if e.startswith("FAIL")
               for k in ("i693_fee", "i693_edition", "g1450_fee", "g1650_fee"))


def test_t6_poverty_and_civics_fabricated_fails():
    run_dir = clone(6, "badpoverty")
    mutate_answer(run_dir,
                  "Fee calculator: N-400 general filing fee $760 paper / $710 online; "
                  "household income at or below 400% of the Federal Poverty Guidelines "
                  "$380; qualifying military service $0; Form I-912 fee $0; N-600 "
                  "general fees $1,385 paper / $1,335 online. Complete the most "
                  "current version of Form I-912, Request for Fee Waiver, or write a "
                  "letter asking for a fee waiver. You can demonstrate you cannot pay "
                  "if you are currently receiving a means-tested benefit, your "
                  "household income is at or below 150% of the Federal Poverty "
                  "Guidelines, or you are currently experiencing extreme financial "
                  "hardship. Means-tested benefits include Medicaid and SNAP. The "
                  "poverty guidelines page shows a 150% threshold of $25,000 for a "
                  "household of four. The civics test page lists the study resource "
                  "100 Civics Test Questions (M-1778).")
    verdict = run_verifier(6, run_dir)
    assert not verdict["pass"]
    assert any(k in e for e in verdict["evidence"] if e.startswith("FAIL")
               for k in ("poverty_h4", "civics_resource"))


def test_t7_dcs_and_vaccination_fabricated_fails():
    run_dir = clone(7, "baddcs")
    mutate_answer(run_dir,
                  "Closest practice for ZIP 22202: VAN DORN PEDIATRICS, PC, 2500 NORTH "
                  "VAN DORN STREET, SUITE 102, 2.8 miles away. Doctor DR. MOHEB "
                  "ANDRAWIS, phone 703-933-0555, spoken language English. Second "
                  "listing's doctor DR. MONA HANNA, spoken language Arabic. Third "
                  "practice BEAUREGARD MEDICAL CENTER, 4216 KING STREET, phone "
                  "703-820-7000. The Arabic filter leaves 5 results including VAN "
                  "DORN PEDIATRICS, PC; the female filter leaves 4 with first female "
                  "doctor DR. MONA HANNA; the male filter leaves 6 with first male "
                  "doctor DR. MOHEB ANDRAWIS. Becoming a civil surgeon requires "
                  "applying using Form I-920. The vaccination requirements page lists "
                  "Shingles, Hepatitis C, and Influenza among the diseases to "
                  "prevent. Form I-693's filing fee is $0 and its current edition "
                  "date is 01/20/25.")
    verdict = run_verifier(7, run_dir)
    assert not verdict["pass"]
    assert any(k in e for e in verdict["evidence"] if e.startswith("FAIL")
               for k in ("vaccines", "i693"))


def test_t8_boston_fabricated_fails():
    run_dir = clone(8, "badboston")
    mutate_answer(run_dir,
                  "ZIP 60601 shows 10 results. First practice: PASSPORT HEALTH: "
                  "CHICAGO, 111 W WASHINGTON STREET, SUITE 1440, phone 312-641-6228, "
                  "0.4 miles away. Second practice: PRISM HOLISTIC CARE LTD, 33 W "
                  "GRAND STREET, doctor DR. MEHBUB KAPADIA, phone 800-325-1812. The "
                  "female-doctor filter leaves 4 results; the first female doctor is "
                  "DR. CYNTHIA ROSS of CONCENTRA / URGENT CARE. The male-doctor filter "
                  "leaves 5 results. For Boston (ZIP 02108) the closest practice is "
                  "BEACON MEDICAL, 1 TREMONT STREET, with doctor DR. JAMES TAYLOR, "
                  "phone 617-555-0100; its female filter leaves 9 results and its male "
                  "filter leaves 2.")
    verdict = run_verifier(8, run_dir)
    assert not verdict["pass"]
    assert any(k in e for e in verdict["evidence"] if e.startswith("FAIL")
               for k in ("boston_name", "boston_doctor", "boston_female_count"))


def test_t9_aao_and_i290b_fabricated_fails():
    run_dir = clone(9, "badaao")
    mutate_answer(run_dir,
                  "ZIP 60601 is served by the Chicago Field Office (designation CHI), "
                  "101 West Ida B. Wells Drive, district CHI Chicago, region C, "
                  "service center NSC. ZIP 60661 maps to the same Chicago Field "
                  "Office. ZIP 53201 is served by the Milwaukee Field Office, which "
                  "shares Chicago's NSC service center. N-400 at Chicago: 18 Months to "
                  "9 Months published April 05, 2019; at Milwaukee: 19.5 Months to 8 "
                  "Months published March 19, 2019. The AAO strives to complete its "
                  "appellate review within 90 days. Form I-290B: General Filing fee "
                  "$650.")
    verdict = run_verifier(9, run_dir)
    assert not verdict["pass"]
    assert any(k in e for e in verdict["evidence"] if e.startswith("FAIL")
               for k in ("aao_goal", "i290b_fee"))


def test_t10_cases_and_i90_fees_fabricated_fails():
    run_dir = clone(10, "badcases")
    mutate_answer(run_dir,
                  "ZIP 77002 is served by the Houston Field Office (designation HOU), "
                  "810 Gears Road, Suite 100, district DAL Dallas. ZIP 77046 maps to "
                  "the same Houston Field Office. The four online appointment services "
                  "are ADIT Stamp, Emergency Advance Parole (EAP), Immigration Judge "
                  "Grant, and Other. Asylum Seekers And NACARA Applicants being "
                  "processed at the Arlington Asylum Office may schedule asylum "
                  "appointments online. Case MSC2210112233 is Form I-131 with status "
                  "Case Was Received; case YSC2210667788 is Form I-90 with status New "
                  "Card Is Being Produced. Form I-90 replacement-card fees: $300 paper "
                  "/ $250 online.")
    verdict = run_verifier(10, run_dir)
    assert not verdict["pass"]
    assert any(k in e for e in verdict["evidence"] if e.startswith("FAIL")
               for k in ("case1_form", "case2_form", "i90_paper"))


def test_t11_div_order_and_allnews_fabricated_fails():
    run_dir = clone(11, "baddiv")
    mutate_answer(run_dir,
                  "The FY 2027 first-half H-2B cap alert was published 09/11/2026; the "
                  "final receipt date was Sept. 4, 2026 for petitions requesting an "
                  "employment start date before April 1, 2027. We will reject new "
                  "cap-subject H-2B petitions received after Sept. 4, 2026, that "
                  "request an employment start date before April 1, 2027. Anyone can "
                  "send us tips, alleged violations, and other relevant information "
                  "about potential fraud or abuse using our online tip form. The FY "
                  "2026 second-half H-2B alert was published 03/20/2026 with final "
                  "receipt date March 10, 2026. The FY 2027 H-1B cap alert was "
                  "published 07/17/2026 with a 65,000 H-1B regular cap and 20,000 "
                  "U.S. advanced degree exemption. The page-two court-order alert on "
                  "the Diversity Immigrant Visa hold policy is dated 09/04/2026 and "
                  "temporarily vacates PM-602-0050. The all-news list shows 45 items "
                  "in total. The glossary search for 'H-1B' returns 5 terms, the first "
                  "being Cap-gap extension.")
    verdict = run_verifier(11, run_dir)
    assert not verdict["pass"]
    assert any(k in e for e in verdict["evidence"] if e.startswith("FAIL")
               for k in ("a4_order", "allnews_count"))


def test_t12_cuban_aunt_glossary_fabricated_fails():
    run_dir = clone(12, "badcuban")
    mutate_answer(run_dir,
                  "The Bosnian release: 09/22/2026, announced in BOISE, Idaho. "
                  "Defendant Miran Kostic, a high-level official in the so-called "
                  "Autonomous Province of Western Bosnia (APZB), faces up to 10 years "
                  "in prison for each charge of attempted naturalization fraud and "
                  "five years in prison for the false statements charge; investigated "
                  "by U.S. Immigration and Customs Enforcement Homeland Security "
                  "Investigations and the FBI. The same-day Chinese aliens release was "
                  "announced in ST. LOUIS: Huang faces one count of a false statement "
                  "in a naturalization proceeding and one count of fraudulent "
                  "acquisition of a firearm; Du faces one count of being an alien in "
                  "possession of a firearm. The Cuban alien smuggling conviction "
                  "release is dated 07/07/2026; Cabrera-Rodriguez faces a maximum "
                  "penalty of 5 years in prison. The aunt and U.S. airman nephew "
                  "release is dated 09/02/2026, announced in DENVER. The glossary "
                  "search for 'Refugee' returns 12 terms and 'Asylum' returns 9 terms.")
    verdict = run_verifier(12, run_dir)
    assert not verdict["pass"]
    assert any(k in e for e in verdict["evidence"] if e.startswith("FAIL")
               for k in ("r3_date", "r4_city", "refugee_count"))


def test_t15_asylee_fabricated_fails():
    run_dir = clone(15, "badasylee")
    mutate_answer(run_dir,
                  "Adjustment of Status: The process that you can use to apply for "
                  "lawful permanent resident status (also known as applying for a "
                  "Green Card) when you are present in the United States. Advance "
                  "Parole: Advance parole allows you to travel back to the United "
                  "States without applying for a visa. Biometrics: USCIS offices "
                  "where applicants usually have their biometrics (such as "
                  "fingerprints, photograph. and signature) taken. Searching "
                  "'adjustment' returns 5 terms; the two starting with A are "
                  "Adjustment of Status and Adjustment to immigrant status. The "
                  "letter-A index lists 28 glossary terms. Asylee: an alien living "
                  "abroad who is waiting for an immigrant visa interview.")
    verdict = run_verifier(15, run_dir)
    assert not verdict["pass"]
    assert any("asylee_def" in e for e in verdict["evidence"] if e.startswith("FAIL"))


def test_t17_rebook_swapped_status_fails():
    """Both view-flow statuses swapped in the answer."""
    run_dir = clone(17, "swapped")
    mutate_answer(run_dir,
                  "The existing appointment is an Emergency Advance Parole (EAP) at "
                  "the Houston office on 2026-10-06 at 09:45 AM. After canceling it "
                  "from the dashboard, I requested a replacement Emergency Advance "
                  "Parole (EAP) appointment using ZIP 77002: new appointment at the "
                  "Houston office, confirmation number USCHOU2610121000. Looking up "
                  "both through the appointment tool's view flow: the old appointment "
                  "USCHOU2610060945 shows Status: Scheduled, and the new appointment "
                  "shows Status: Canceled.")
    verdict = run_verifier(17, run_dir)
    assert not verdict["pass"]
    assert any(k in e for e in verdict["evidence"] if e.startswith("FAIL")
               for k in ("old_status", "new_status", "status_order"))


def test_t19_nbc_and_ead_fabricated_fails():
    run_dir = clone(19, "badnbc")
    mutate_answer(run_dir,
                  "Form I-765: current edition date 08/21/25; downloadable PDFs Form "
                  "I-765, Instructions for Form I-765, and Form I-765 Worksheet. Fee "
                  "calculator: general filing fee $520 paper / $470 online; an "
                  "applicant with a pending Form I-485 filed on or after April 1, "
                  "2024 pays $260. Form I-765 at the National Benefits Center: "
                  "publication date June 6, 2020, 147-C9 category 3 Months to 1 "
                  "Month. The While My Case Is Pending page lists every online "
                  "case-management tool, in order: Check your case status; Check case "
                  "processing times; Ask about a case taking longer than expected; "
                  "Update your mailing address; Ask about missing mail; Correct a "
                  "typographical error; Request appointment accommodations. The "
                  "glossary search for 'Employment Authorization Document' returns the "
                  "term Work Permit Card (EAD).")
    verdict = run_verifier(19, run_dir)
    assert not verdict["pass"]
    assert any(k in e for e in verdict["evidence"] if e.startswith("FAIL")
               for k in ("nbc_pub", "ead_term"))
