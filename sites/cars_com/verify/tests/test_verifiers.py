"""Deterministic verifier contract tests for the 19 cars_com tasks.

Covers, per task: the honest trajectory (from the reviewer's live runs, frozen
in reviewed_fixtures.json) MUST PASS; a no-op run (homepage only, empty answer,
clean DB) MUST FAIL; a knowledge-shortcut (correct answer + delta, homepage-only
navigation) MUST FAIL; a wrong answer MUST FAIL; a state-mismatch (success
claim, no DB delta) MUST FAIL for stateful tasks. Read-only tasks MUST FAIL on
a mutated after-DB. Package tampering (task_id mismatch, off-site URL) MUST
fail closed.

No LLM: snapshots are seed copies mutated through sqlite, trajectories are
written in the agent_demo/agent.py shape.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _support import (ALL, READ_ONLY, STATEFUL, honest_run, noop_run,  # noqa: E402
                       offsite_run, readonly_mutation_run, run_verifier,
                       shortcut_run, state_mismatch_run, tampered_task_id_run,
                       wrong_answer_run)


# wrong answers per task: plausible but contradicting frozen ground truth
WRONG_ANSWERS = {
 0: "The used-SUV search found 250 results, narrowing to Good Deal left 21. The cheapest is a 2021 Toyota RAV4 LE at $25,000 with 43,000 miles, an estimated payment of $470/mo at 6.5% APR from Rairdon's of Kirkland rated 4.5. Monday hours 10:00am-9:00pm, phone (888) 555-1234. The reviews page shows 12 reviews and the inventory lists 8 cars.",
 1: "The used Civic search found 15 results. The lowest-mileage Good Deal Civic is a 2025 Honda Civic Sport at $27,500 with 11,000 miles, $530/mo at 6.5% APR, a Platinum White exterior, from Kia of Everett rated 4.5. My garage shows the Civic and a saved search 'Honda Civics' with weekly alerts.",
 2: "The new RAV4 search found 25 results with prices from $35,000 to $60,000 on page 1. The cheapest has 5 miles, $680/mo at 6.5% APR, from Marysville Toyota with Monday hours 10am-6pm. The calculator gives $690/mo and $6,000 total interest. The research page shows $30,000, 30 trims, the cheapest trim at $30,000 with 30/40 MPG, and a consumer rating of 4.6 with 80% recommending.",
 3: "The certified Toyota search found 9 results, narrowing left 6. The cheapest is a 2023 Toyota bZ4X Limited at $26,000 with 22,000 miles from Marysville Toyota with a Great Deal badge. The CPO basic warranty is 24 months/24,000 miles and the maximum is 8 years/100,000 miles. History: 2 owners, 1 accident, Salvage title. Monday hours 10am-6pm, phone (360) 555-1234, 12 reviews, 4 certified cars.",
 4: "The dealer filter finds 2 matches; the top dealer is Auburn Toyota rated 5.0 with 2,000 reviews, 25 miles away. Monday hours 10am-6pm, new-cars phone (253) 555-1234. The three most recent reviews are by John Smith (4.0, 2026-01-01), Jane Doe (5.0, 2026-01-02) and Bob Roe (3.0, 2026-01-03). I saved the search as 'Toyota watch' with monthly alerts.",
 5: "Porsche Bellevue is rated 4.8 with 1,200 reviews, shows 6 awards, and its weekly sales hours are 10am-7pm. The three most recent reviews are by Alice (5.0, 2026-09-01), Bob (4.0, 2026-09-02) and Carol (5.0, 2026-09-03). The inventory lists 10 cars; the most expensive is a 2021 Audi RS 6 Avant at $90,000 with 40,000 miles. My garage showed the Audi, and after removing it the F-150 and the Mustang remain.",
 6: "The Corolla has the lower starting MSRP ($24,000 vs $25,000); the Civic has more horsepower (200 vs 150); MPG is 30/40 for the Civic and 31/42 for the Corolla; both seat 4; passenger volume is 90 ft3 and 95 ft3. The Civic page shows a starting price of $25,000, 8 trims, the cheapest trim Sport CVT at $25,000, a safety rating of 4/5, a consumer rating of 4.5 with 80% recommending, and the Corolla's consumer rating is 3.5. I saved the cheapest Civic at $9,500.",
 7: "The 2018 Civic EX hatchback's initial estimate was $12,000 - $15,000 and its final offer was $11,500 - $14,500. The 2019 RAV4 XLE's final offer was $14,000 - $16,500. The Civic is worth more.",
 8: "The 72-month term costs $520/mo with $7,000 total interest; the 48-month term costs $700/mo with $5,000 total interest. The 48-month term is cheaper per month and the 72-month costs less overall. The 9% rerun gives $550/mo. The $40,000 case gives $750/mo at 6.0% APR.",
 9: "There are 25 cars for sale by owner. The cheapest is a 2013 Nissan Rogue at $3,000 with 190,000 miles in Tacoma, WA, and one listing carries a Great Deal badge. Narrowing to under $20,000 left 15 results. The cheapest has a Blue exterior and its seller area shows a dealership. The second-cheapest is at $3,500 with 195,000 miles. My garage shows the saved Rogue.",
 10: "There are 100 electric cars; narrowing to under $30,000 left 30. The cheapest EV is a 2018 Tesla Model 3 at $19,000 with 60,000 miles from Tesla Seattle. It shows $380/mo at 6.5% APR, a White exterior, and features including Leather Seats and a Sunroof. The most expensive on page 1 is at $30,500 with 20,000 miles from Bellevue Motors. My garage shows 3 saved cars.",
 11: "The budget search found 4 results. The three lowest-mileage listings are at $15,000/50,000 mi, $13,000/65,000 mi and $13,500/80,000 mi. The lowest-mileage one is from Bellevue Motors, has a Silver exterior, notes beginning 'Great value', an estimated payment of $300/mo at 6.5% APR, and a Great Deal badge. My garage shows 4 saved cars.",
 12: "The manual search found 13 results within 50 miles; narrowing to under $25,000 left 4. The cheapest is a VW Jetta at $14,000 and the most expensive is a Focus RS at $24,000. The cheapest shows 85,000 miles, a White exterior, AutoNation Ford Bellevue rated 4.5, and $260/mo at 6.5% APR. My garage shows the saved Jetta.",
 13: "I created a new account. The certified SUV search found 30 results. I saved the first two listings, a BMW X5 at $40,000 and a Chevrolet Blazer at $25,000, and saved the search with weekly alerts. After removing one, the BMW remains.",
 14: "Bob's garage shows the 2025 Ford F-150 XLT at $46,000, the 2026 Ford F-150 Lariat at $66,000 and the 2022 Tesla Model 3 Performance at $34,000, plus a saved search 'RAV4 watch' with daily alerts. The saved search finds 25 results. The Tesla valuation gave an initial range of $18,000 - $21,000 and a final offer of $17,900 - $20,500. After removing one car, three remain.",
 15: "The Shorewood Escape is priced at $25,000 with 51,000 miles and a Great Deal badge. Its good-deal range is $22,000 - $25,500, its price history has three rows, and the current price sits below the range. The Auburn Escape is more expensive at $23,000. The dealership's Monday hours are 10am-6pm. My garage shows the Escape at $25,000.",
 16: "Auburn Chevrolet lists 25 cars; filtering to used leaves 6. The cheapest used car is a 2017 Express 2500 at $12,000 and the most expensive is a 2025 Silverado at $38,000. The cheapest shows 185,000 miles, a Fair Deal badge, and a Summit Black exterior. The About line is 'Welcome to Auburn Chevrolet, your hometown dealer.' and Monday hours are 10am-7pm. My garage shows the saved Express.",
 17: "The 2025 Civic research page shows a starting price of $25,000 with 10 trims; the cheapest trim is at $22,000 with 30/40 MPG and 4 seats. The consumer rating is 4.5 with 90% recommending. Good points: Cheap and Roomy; bad points: Slow and Noisy. I saved the search as 'Civic research' with weekly alerts. The Accord comparison shows MSRP of $30,000 for the Accord and $28,000 for the Camry.",
 18: "There are 50 hybrids; narrowing to under $30,000 left 12. The cheapest is a 2016 Ford Fusion Hybrid at $9,500 with 160,000 miles, $180/mo at 6.5% APR, from Marysville Ford. The RAV4 starts cheaper ($31,000 vs $32,000); the CR-V has more horsepower (200 vs 180); MPG is 40/35 for the RAV4 and 30/28 for the CR-V. The RAV4's research page shows a consumer rating of 4.0 and a safety rating of 4/5. My garage shows the Fusion.",
}


# ---------------------------------------------------------------- honest PASS
@pytest.mark.parametrize("task_no", ALL)
def test_honest_pass(tmp_path, task_no):
    run = honest_run(tmp_path, task_no)
    run_verifier(task_no, run, expect_pass=True)


# ---------------------------------------------------------------- no-op FAIL
@pytest.mark.parametrize("task_no", ALL)
def test_noop_fails(tmp_path, task_no):
    run = noop_run(tmp_path, task_no)
    run_verifier(task_no, run, expect_pass=False)


# ---------------------------------------------------------------- shortcut FAIL
@pytest.mark.parametrize("task_no", ALL)
def test_shortcut_fails(tmp_path, task_no):
    run = shortcut_run(tmp_path, task_no)
    run_verifier(task_no, run, expect_pass=False)


# ---------------------------------------------------------------- wrong answer FAIL
@pytest.mark.parametrize("task_no", ALL)
def test_wrong_answer_fails(tmp_path, task_no):
    run = wrong_answer_run(tmp_path, task_no, WRONG_ANSWERS[task_no])
    run_verifier(task_no, run, expect_pass=False)


# ---------------------------------------------------------------- state-mismatch FAIL
@pytest.mark.parametrize("task_no", sorted(STATEFUL - {5}))
def test_state_mismatch_fails(tmp_path, task_no):
    run = state_mismatch_run(tmp_path, task_no)
    run_verifier(task_no, run, expect_pass=False)


# ---------------------------------------------------------------- read-only mutation FAIL
@pytest.mark.parametrize("task_no", sorted(READ_ONLY))
def test_readonly_mutation_fails(tmp_path, task_no):
    run = readonly_mutation_run(tmp_path, task_no)
    run_verifier(task_no, run, expect_pass=False)


# ---------------------------------------------------------------- tamper FAIL
@pytest.mark.parametrize("task_no", ALL)
def test_offsite_url_fails(tmp_path, task_no):
    run = offsite_run(tmp_path, task_no)
    run_verifier(task_no, run, expect_pass=False)


@pytest.mark.parametrize("task_no", ALL)
def test_tampered_task_id_fails(tmp_path, task_no):
    run = tampered_task_id_run(tmp_path, task_no)
    run_verifier(task_no, run, expect_pass=False)


# ---------------------------------------------------------------- T5 specifics
def test_t5_save_without_remove_fails(tmp_path):
    """T5's net-zero contract: saving the Audi but never removing it must FAIL
    (the after-DB would differ from the seed)."""
    from _support import SPECS, RunBuilder, copy_db, exec_sql, task_ques
    spec = SPECS["5"]
    root = tmp_path / "t5_no_remove"
    root.mkdir(parents=True)
    builder = RunBuilder(root, "Cars.com--5")
    for st in spec["steps"]:
        builder.step(st["path"], st["action"], st.get("params"),
                     url=st.get("url", st["path"]), thought=st.get("thought", ""))
    builder.build(spec["final_answer"], final_path=spec["final_path"])
    after = copy_db(root, "after.db")
    exec_sql(after, ["INSERT INTO saved_cars (user_id, listing_id, saved_at) "
                     "VALUES (2, '9d7e7c43-041e-4054-90a1-a0d03563d841', '2026-10-13')"])
    run_verifier(5, root, expect_pass=False)
