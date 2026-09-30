#!/usr/bin/env python3
"""Deepen the 17 FAIL tasks per the review's per-task redesign instructions
(wh-thumbtack-review-evidence/REPORT.md §三) to >=15 substantive steps.

Only the `ques` text changes on the 17 FAIL rows (ids --0,--2,--3,--4,--6,--7,
--8,--9,--10,--11,--12,--13,--14,--16,--17,--18,--19); rows --1, --5 and --15
stay byte-identical. Key set (5 keys), ids, web, upstream_url and web_name are
untouched on every row. No site data / images / structure changes.
"""
import json
import re
import sys
from pathlib import Path

TASKS = Path(__file__).resolve().parent.parent / "tasks.jsonl"

NEW_QUES = {
    # --0 (was 14 steps): save all three, then remove the two less popular from
    # the saved list (save+remove two-way state management) -> 16 honest steps.
    0: "Log in with the demo account (email: alice.j@test.com, password: TestPass123!). I'm choosing between the Seattle wedding photographers Jeshua Frees (Clearline Production), Tanner Schmidt, and Liz Ong. Compare how many Thumbtack hires each of them has, save all three to my saved pros, then open my saved list and remove the two less popular ones. Tell me how many years the remaining pro has been in business and how many employees they have.",
    # --1 unchanged (20 steps, PASS).
    # --2 (was 11, read-only): guides x2 -> Everett DJ profile -> message
    # (October availability) -> Request estimate wizard -> quotes -> 19+ steps.
    2: "Log in with the demo account (email: carol.d@test.com, password: TestPass123!). I'm planning a wedding on a tight budget. Using Thumbtack's cost guides, compare the national average cost of hiring a wedding DJ with a wedding photographer's, and tell me which service is more expensive and by roughly how much. Then find the highest-rated DJ based in Everett, message them to confirm they're available for an October wedding date, and request an estimate from them describing your four-hour wedding reception.",
    # --3 (was 12): review tags -> message Paty (supplies) -> second cleaner
    # same question -> follow up with Paty on Sunday availability -> 18+ steps.
    3: "Log in with the demo account (email: alice.j@test.com, password: TestPass123!). On Paty House Cleaning's profile, find the word customers mention most often in their reviews and check whether that theme also appears in the newest review. Message Paty asking whether they bring their own cleaning supplies. Then ask a second house cleaner the same question, and follow up with Paty asking whether they could come on a Sunday. Report all three replies.",
    # --4 (was 12): read lowest/count -> cancel -> replacement request with the
    # full questionnaire -> report the new cheapest quote -> 16+ steps.
    4: "Log in with the demo account (email: alice.j@test.com, password: TestPass123!). My TV mounting project is on hold — cancel it, but first tell me which pro had quoted the lowest price and how many quotes the project had received in total. Then start a replacement request in zip 98033 for a handyman to hang a heavy mirror, answer the questionnaire in full describing the job, and report the cheapest quote the new request received.",
    # --5 unchanged (16 steps, PASS).
    # --6 (was 13): verify bg+Venmo -> save -> message (urgent leak) -> wizard
    # -> lowest quote vs cost-guide range -> 17+ steps.
    6: "Log in with the demo account (email: david.k@test.com, password: TestPass123!). My kitchen faucet has been dripping for a week. Find a plumber who is background checked and accepts Venmo, save them to my saved pros, and message them to confirm they can handle the leak urgently. Then request a pipe-repair quote within a week describing the leaky faucet, and tell me the lowest quote and how it compares to the cost guide's typical range for plumbers.",
    # --7 (was 12): register -> wizard -> hire cheapest -> mark complete ->
    # 5-star review -> 17+ steps (the registered twin of --1).
    7: "Create a new Thumbtack account (name: Nina Patel, email: nina.p@test.com, password: NewHome2026!), then request quotes for assembling a large wardrobe and two bookcases in zip 98101, answering the questionnaire about the three items and the instructions you have and describing the job. Hire the cheapest pro who responded, mark the project complete, and leave them a 5-star review mentioning the smooth assembly. Tell me how many pros responded and what the cheapest quote was.",
    # --8 (was 14): find two Sunday handymen -> save both -> message the
    # more-reviewed -> follow-up on Sunday slots -> remove the other -> 20.
    8: "Log in with the demo account (email: alice.j@test.com, password: TestPass123!). I can only be home on Sundays. Find two handymen whose business hours include Sunday, save both to my saved pros, and message the one with more reviews to confirm they can do a Sunday visit. Follow up in the same thread asking which Sunday time slots they have open, then open my saved list and remove the other handyman. Report both replies.",
    # --9 (was 14): guide range -> wizard -> hire cheapest -> mark complete ->
    # review -> report inside/outside range -> 17+ steps.
    9: "Log in with the demo account (email: bob.c@test.com, password: TestPass123!). According to Thumbtack's cost guide, what do most people pay for a one-time house cleaning visit? Then request a one-time deep-cleaning quote for my 3-bedroom, 2-bathroom home in zip 98101, describing the job. Hire the pro with the cheapest quote, mark the project complete, and leave them a 5-star review. Tell me their name and whether their price falls inside the guide's typical range.",
    # --10 (was 10): saved-list removal x2 -> project lowest -> Strok profile
    # (rating/response) -> cancel -> smaller studio replacement -> 17+ steps.
    10: "Log in with the demo account (email: bob.c@test.com, password: TestPass123!). My moving plans changed. Remove the moving companies from my saved pros, open my pending moving project, and tell me which pro quoted the lowest price — check that pro's profile for their rating and how fast they respond. Then cancel the project and start a much smaller replacement request for a studio move in zip 98101, telling me how many pros respond this time.",
    # --11 (was 8, read-only): guides x2 -> Redmond Top Pro profile -> message
    # (October availability) -> Request estimate -> 18+ steps.
    11: "Log in with the demo account (email: carol.d@test.com, password: TestPass123!). I'm budgeting my daughter's quinceañera. Using the cost guides, compare what a makeup artist charges with what a DJ charges, and tell me which is more expensive. Then find the highest-rated Top Pro makeup artist based in Redmond, message them asking whether they're available for an October event, and request an estimate from them describing the quinceañera makeup for my daughter.",
    # --12 (was 10): read hired price + response note -> pre-review profile
    # check -> review ("spotless") -> reopen profile (newest) -> message +
    # follow-up (move-out clean) -> 16 steps.
    12: "Log in with the demo account (email: alice.j@test.com, password: TestPass123!). My house cleaning project is finished but I never left a review. Open the project, note the hired pro's price and their response note, and check their profile's current reviews. Then leave them a 5-star review saying they were thorough, including the word \"spotless\". Reopen their profile to confirm your review is the most recent one, and message them asking whether they could return for a move-out clean next month — follow up asking whether they'd bring their own supplies. Report both replies.",
    # --13 (was 11): existing thread -> second cleaner same question + Sunday
    # follow-up -> first cleaner Sunday question -> compare both -> 16+ steps.
    13: "Log in with the demo account (email: alice.j@test.com, password: TestPass123!). Read my existing message thread about cleaning supplies and tell me exactly what the pro said they bring. Then ask a different house cleaner the same question, follow up with them about Sunday availability, and ask the first cleaner the Sunday question too. Tell me how the two cleaners' answers compare.",
    # --14 (was 11): cost guide -> Top Pro exterminators -> wizard (within a
    # week) -> hire most-reviewed -> complete -> review ("ants") -> confirm on
    # profile -> 16+ steps.
    14: "Log in with the demo account (email: bob.c@test.com, password: TestPass123!). Ants have invaded my kitchen. Check the cost guide for what an exterminator typically runs, then find the exterminators who are Top Pros and request quotes for indoor ant treatment in zip 98101 within a week, describing the problem. Hire the responder with the most reviews, mark the project complete, and leave them a 5-star review mentioning the ants. Confirm on their profile that your review shows, and tell me their name, their quote, and the guide's typical range.",
    # --15 unchanged (15 steps, PASS).
    # --16 (was 14): cost guide -> Bellevue trainer profile -> message
    # (twice-a-week slots) -> Request estimate wizard -> 18+ steps.
    16: "Log in with the demo account (email: david.k@test.com, password: TestPass123!). I want to get in shape this fall. Using the cost guide, tell me the typical price range for personal training sessions. Then find the highest-rated personal trainer based in Bellevue, message them to confirm they have twice-a-week slots, and request a quote from them describing twice-a-week strength sessions.",
    # --17 (was 11): wizard (conceal cables, sound bar, above fireplace) ->
    # hire lowest -> mark complete -> review (cable work) -> 16+ steps.
    17: "Log in with the demo account (email: alice.j@test.com, password: TestPass123!). I want my 75-inch TV mounted above the fireplace with the cables hidden and my sound bar connected. Request TV mounting quotes in zip 98052, answering the questionnaire to match my setup and describing the job. Hire the pro with the lowest quote, mark the project complete, and leave them a 5-star review mentioning the tidy cable work. Tell me how many pros responded and which one you hired.",
    # --18 (was 12): near-me -> Events -> makeup -> Most hires -> profile Top
    # Pro/response check -> message (Oct 18) -> trial follow-up -> save -> 16+.
    18: "Log in with the demo account (email: carol.d@test.com, password: TestPass123!). Starting from the Services near me page, open the Events services group and go to the wedding and event makeup category. Sort the list by Most hires and tell me the top makeup artist's name, number of hires, and review count. Check their profile for Top Pro status and how fast they respond, message them about availability for an October 18 event, follow up asking about a pre-event trial, then save them to my saved pros. Report both replies.",
    # --19 (was 12): fastest-response sort -> Hotwire profile -> wizard
    # (refrigerator, GE) -> hire cheapest -> review ("refrigerator") -> 17+.
    19: "Log in with the demo account (email: bob.c@test.com, password: TestPass123!). My refrigerator stopped cooling overnight and my food is spoiling. Find the appliance repair specialist who responds fastest, request a quote describing the emergency repair for my GE refrigerator, hire the pro with the lowest quote, and leave them a 5-star review mentioning the refrigerator. Tell me the lowest quote you received.",
}

def main() -> None:
    lines = TASKS.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 20, f"expected 20 rows, got {len(lines)}"
    out, changed = [], []
    for i, line in enumerate(lines):
        row = json.loads(line)
        assert sorted(row) == ["id", "ques", "upstream_url", "web", "web_name"], row
        assert row["id"] == f"Thumbtack--{i}", row["id"]
        if i in NEW_QUES:
            row["ques"] = NEW_QUES[i]
            changed.append(i)
        words = len(row["ques"].split())
        assert words <= 100, f"task {i}: {words} words"
        assert not re.search(r"\$\d", row["ques"]), row["id"]
        out.append(json.dumps(row, ensure_ascii=False))
    assert sorted(changed) == [0, 2, 3, 4, 6, 7, 8, 9, 10, 11, 12, 13, 14, 16, 17, 18, 19]
    TASKS.write_text("\n".join(out) + "\n", encoding="utf-8")
    for i, line in enumerate(out):
        row = json.loads(line)
        print(f"--{i:2d}  {len(row['ques'].split()):3d} words  {'CHANGED' if i in changed else 'same   '}  {row['ques'][:60]}...")

if __name__ == "__main__":
    main()
