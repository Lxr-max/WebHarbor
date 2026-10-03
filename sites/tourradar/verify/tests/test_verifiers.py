"""Deterministic verifier contract tests for the 22 tourradar tasks.

Covers, per task: the honest trajectory (from the reviewer's live runs, frozen
in reviewed_fixtures.json) MUST PASS; a no-op run (homepage only, empty
answer, clean DB) MUST FAIL; a knowledge-shortcut (correct answer + delta,
homepage-only navigation) MUST FAIL; a wrong answer MUST FAIL; a state-mismatch
(success claim, no DB delta) MUST FAIL for stateful tasks. Read-only tasks
MUST FAIL on a mutated after-DB. Package tampering (task_id mismatch,
off-site URL) MUST fail closed.

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
WRONG_ANSWERS = {0: 'Booked Japan Classic 10 Day for 2 travelers. Reference TR-99999999999, US$449.80 charged today.', 1: 'Booked the Big Five Classic Safari in Tanzania, departing January 1, 2027, single room without insurance. Reference TR-199790019999, total US$1,900.00.', 2: 'Cancelled TR-000010102; the remaining trip departs October 1, 2026; her wishlist lists 3 adventures.', 3: 'Removed the Thai Intro tour and saved Best Of Vietnam In 14 Days at US$677 per person.', 4: 'Nepal Social Treks is rated 4.9 and responds 9 hours; Nepal Hiking Team is 4.8 and responds 5 hours; their cheapest Nepal tours cost US$1,475 and US$890; the first guaranteed October 2026 departure is October 3, 2026 at US$890 and the 2-traveler deposit is US$178.00.', 5: 'The most-reviewed Machu Picchu tour is Classic Inca Trail Trek 4D/3N with 239 reviews; 50% of its 2026 departures are sold out; the 2-traveler deposit is US$300.00; the cheapest result is the 5 Day Cusco Travel Package at US$559 with 25 available 2026 departures.', 6: 'Booked Iceland Northern Lights 6 days. Reference TR-98112039999, departure October 8, 2026.', 7: "Premium Protection US$400.00 vs Trip Cancellation Only US$300.00; premium is cheaper; the deposit would charge US$500.00 today; the Single Room is US$2,000; Premium for 2 travelers is US$300.00; the second-cheapest guaranteed departure is US$1,635; Europe Jewel's cheapest guaranteed departure is May 27, 2027 at US$2,500.", 8: "The Dimos review posted in September 2026 is Christene's: rating 4.8, traveled in July 2026, and the operator posted a reply; the top-rated Dimos review is ARUNA's 4.5; the tour has 390 reviews and its cheapest guaranteed departure is US$1,735; Europe Jewel's most recent review is by Susan and Classic Europe's by Paul.", 9: 'The highest-rated Kenya tour is the 6 Days Masai Mara - L. Nakuru - Amboseli Classic Budget Safari (5.0, 16 reviews); its cheapest departure is September 30, 2026 at US$1,438; the Single Room is US$2,000; the Amboseli tour lists no Typhoid; the most-reviewed Kenya tour is Kenya Wildlife Safari at US$1,444.', 10: "Day 5 is the Sacred Valley day: included are the Pisac ruins; there are no optional activities; 2 days list optionals; the reviews page lists 12 entries; the cheapest available departure is October 24, 2026 at US$1,512; the Classic Inca Trail's Day 1 is 'Cusco' and Day 4 'Machu Picchu', rated 4.8 with 10 reviews listed.", 11: 'October 2026 has the most tours departing (520 tours); the guide lists 28 budget tours for Japan; the top-reviewed tour is the 8D Splendid Japan at 4.9, first departing October 16, 2026; the wishlist lists 2 adventures.', 12: 'The question was not sent to the operator; the submission failed.', 13: "Published David's review; the tour's reviews page now lists 194 entries; 5 are rated 5.0; his saved adventures are the Philippines Island Hopper and Philippines West, the cheapest at US$1,240; the booking reference is TR-000040501 and the next departure is October 16, 2026.", 14: 'Applied TRAVEL50 to the Genuine Europe (20 destinations) tour. Reference TR-290646019999, total after the discount US$2,439.00.', 15: "Timeless Morocco has the smallest maximum group size (2-15), US$1,268 per person, 216 reviews; the runner-up is the 5 day trip: Sahara Fun Outdoor Experience (1-10, US$1,153); the Casablanca form's deposit is US$250.00 and the Sahara Fun form's US$200.00; Morocco lists 8 tours, 4 with more than 110 reviews.", 16: 'The longest Medium-intensity Peru tour is the 7 Day Cusco Travel Package: 7 days, starting in Lima and ending in Cusco; its cheapest available departure is October 30, 2026 at US$669; there are 5 Medium-intensity Peru tours; the cheaper tour is the Cusco & Salkantay Trekking.', 17: 'Booked Fantastic Thailand - 9 Days for 2 travelers. Reference TR-147055029999, US$200.40 charged today.', 18: "The best-reviewed Greek island tour is Best of Greece (15 days): 4.5 stars, US$1,360, next guaranteed departure October 15, 2026, based on a Shared Room; the first reviewer is Susan; the form shows US$1,360 per person, US$1,800 Single Room and a US$300.00 deposit; the Cultural Athens & Island Hopping tour's deposit is US$250.00.", 19: "Searching 'Nile cruise' finds 12 tours. The cheapest is Pharaohs Nile Cruise Adventure at US$975, run by Beyond The Nile Tours with a 96% response rate, and it has plenty of upcoming departures; the most-reviewed is the Ultimate Egyptian Experience (1,652 reviews, 4.7), first available October 1, 2026 with a US$200.00 deposit and a 100% response rate; the 'Egypt' search finds 15 tours.", 20: "Trafalgar responds fastest (9 hours); response rates are Expat 72%, Intrepid 84%, Trafalgar 80%; Expat lists the most tours (4); Expat's most-reviewed tour is Classic Europe (311 reviews), Intrepid's is Europe Jewel (406 reviews) and Trafalgar's is Mexico Unplugged (126 reviews).", 21: 'Ancient Wonders Egypt (rating 4.5, US$1,391) was booked for 2 travelers; reference TR-251939029999.'}


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
@pytest.mark.parametrize("task_no", sorted(STATEFUL))
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


# ---------------------------------------------------------------- no-op with pasted answer FAIL
# (an agent that only opens the homepage and pastes the correct answer text
# must still fail — navigation gates + DB checks both bite)
@pytest.mark.parametrize("task_no", ALL)
def test_noop_with_answer_fails(tmp_path, task_no):
    from _support import SPECS
    run = noop_run(tmp_path, task_no, answer=SPECS[str(task_no)]["final_answer"])
    run_verifier(task_no, run, expect_pass=False)
