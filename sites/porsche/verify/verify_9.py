"""Deterministic verifier for porsche task 9; see tasks.jsonl and verify/README.md."""
from verify_lib import (check_read_only, check_seed_contract, check_trajectory_identity,
                        contains_amount, contains_count, contains_phrase, contains_vin,
                        final_answer, navigated_finder, navigated_vehicle_detail,
                        run_verifier)

TASK_ID = "Porsche--9"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_seed_contract(judge, initial_db)
    judge.check("visited_finder_filtered",
                navigated_finder(traj, condition="preowned", range="Panamera",
                                 max_price="130000", max_mileage="30000"),
                "required: /finder/us/en-US/search?condition=preowned&range=Panamera"
                "&max_price=130000&max_mileage=30000")
    judge.check("visited_cheapest_match_detail",
                navigated_vehicle_detail(traj, "porsche-panamera-4-ehybrid-preowned-V3LZXR"),
                "required: detail page of the cheapest matching Panamera")
    # answer gates
    judge.check("answer_name", contains_phrase(answer, "Panamera 4 E-Hybrid"),
                "cheapest match: Panamera 4 E-Hybrid")
    judge.check("answer_price", contains_amount(answer, 123795),
                "$123,795")
    judge.check("answer_mileage", contains_count(answer, 7822),
                "7,822 miles")
    judge.check("answer_vin", contains_vin(answer, "WP0AE2YA3SL047104"),
                "VIN WP0AE2YA3SL047104")
    judge.check("answer_color", contains_phrase(answer, "Madeira Gold Metallic"),
                "exterior color Madeira Gold Metallic")
    judge.check("answer_transmission", contains_phrase(answer, "PDK"),
                "transmission PDK (Automatic)")
    judge.check("answer_dealer", contains_phrase(answer, "Porsche Bellevue"),
                "sold by Porsche Bellevue")
    judge.check("answer_preowned_total", contains_count(answer, 6),
                "6 pre-owned Panameras in stock")
    check_read_only(judge, initial_db, after_db)


if __name__ == "__main__":
    run_verifier(TASK_ID, run_checks)
