#!/usr/bin/env python3
"""Deterministic verifier for cars_com task Cars.com--18.

Hybrid cars for sale: result count; narrow to under $30,000 (new count);
cheapest hybrid's price/mileage/monthly estimate + APR/dealer; save it as
alice.j@test.com and report the garage; compare the Toyota RAV4 against the
Honda CR-V (which starts cheaper, which has more horsepower, each one's
city/highway MPG) and open the cheaper model's research page for its consumer
and safety ratings. Stateful (alice +1 saved car).

NOTE: the ground truth assumes the SERP filter-form fix (see the review
report)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_lib import (Judge, run_verifier, final_answer, navigated_to,
                        contains_int, contains_price, contains_all,
                        contains_any, check_trajectory_identity,
                        check_signed_in_as, check_saved_car,
                        check_only_tables_changed)

TASK_ID = "Cars.com--18"
FUSION_ID = "178f342a-84e9-447d-9f10-8d9f446bdd88"      # 2016 Ford Fusion Hybrid SE
COMPARE_PATH = "/research/compare/honda-cr_v-vs-toyota-rav4/"
CRV_PAGE = "/research/honda-cr_v-2025/"
ALICE = "alice.j@test.com"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_signed_in_as(judge, traj, ALICE)

    judge.check("nav_hybrid_srp", navigated_to(traj, "/shopping/results/"),
                "required: the hybrid SERP")
    judge.check("nav_cheapest", navigated_to(traj, f"/vehicledetail/{FUSION_ID}/"),
                f"required: /vehicledetail/{FUSION_ID[:8]}… (the cheapest hybrid)")
    judge.check("nav_garage", navigated_to(traj, "/profile/your-garage/"),
                "required: the garage page")
    judge.check("nav_compare", navigated_to(traj, COMPARE_PATH),
                f"required: {COMPARE_PATH}")
    judge.check("nav_cheaper_model_page", navigated_to(traj, CRV_PAGE),
                f"required: {CRV_PAGE} (the cheaper model's research page)")

    # counts: 49 hybrids; 10 under $30,000
    judge.check("answer_count_hybrid", contains_int(answer, 49),
                "expected 49 hybrid results")
    judge.check("answer_count_under30k", contains_int(answer, 10),
                "expected 10 results under $30,000")

    # cheapest hybrid: 2016 Ford Fusion Hybrid SE $9,171 / 151,095 mi /
    # Est. $173/mo at 7.0% APR / Kendall Ford of Marysville
    judge.check("answer_cheapest_price", contains_price(answer, 9171),
                "expected the cheapest hybrid at $9,171")
    judge.check("answer_cheapest_mileage", contains_int(answer, 151095),
                "expected 151,095 miles")
    judge.check("answer_monthly_apr",
                contains_int(answer, 173) and contains_any(answer, ["7.0%", "7%"]),
                "expected Est. $173/mo at 7.0% APR")
    judge.check("answer_dealer", contains_all(answer, ["Kendall Ford of Marysville"]),
                "expected the dealer Kendall Ford of Marysville")

    # garage: the saved Fusion Hybrid
    judge.check("answer_garage", contains_all(answer, ["Fusion Hybrid"]),
                "expected the saved Fusion Hybrid in the garage")

    # RAV4 vs CR-V: the CR-V starts cheaper ($31,520 vs $31,900); the RAV4 has
    # more horsepower (226 vs 190); MPG RAV4 47/40, CR-V 28/33
    judge.check("answer_msps",
                contains_price(answer, 31900) and contains_price(answer, 31520),
                "expected both starting MSRPs ($31,900 RAV4 / $31,520 CR-V)")
    judge.check("answer_cheaper_model", contains_all(answer, ["CR-V"]),
                "expected: the CR-V starts cheaper")
    judge.check("answer_horsepower",
                contains_int(answer, 226) and contains_int(answer, 190),
                "expected 226 hp (RAV4) and 190 hp (CR-V)")
    judge.check("answer_mpg",
                contains_all(answer, ["47"]) and contains_all(answer, ["40"])
                and contains_all(answer, ["28"]) and contains_all(answer, ["33"]),
                "expected MPG 47/40 (RAV4) and 28/33 (CR-V)")

    # cheaper model's research page (CR-V): consumer rating 5.0 (100%
    # recommend, 8 reviews); safety rating 5/5
    judge.check("answer_crv_consumer",
                contains_any(answer, ["5.0"]) and contains_any(answer, ["100"]),
                "expected the CR-V consumer rating 5.0 with 100% recommend")
    judge.check("answer_crv_safety", contains_any(answer, ["5/5", "5 / 5"]),
                "expected the CR-V safety rating 5/5")

    # DB: alice now has 4 saved cars (3 seed + the Fusion Hybrid)
    check_saved_car(judge, after_db, ALICE, FUSION_ID, exactly=4)
    check_only_tables_changed(judge, initial_db, after_db, ("saved_cars",))


if __name__ == "__main__":
    run_verifier(TASK_ID, run_checks)
