"""Deterministic verifier for porsche task 11; see tasks.jsonl and verify/README.md."""
from verify_lib import (check_read_only, check_seed_contract, check_trajectory_identity,
                        contains_amount, contains_count, contains_phrase, contains_ref,
                        contains_vin, final_answer, navigated_dealer_search,
                        navigated_vehicle_detail, run_verifier)

TASK_ID = "Porsche--11"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_seed_contract(judge, initial_db)
    judge.check("visited_most_expensive_detail",
                navigated_vehicle_detail(traj, "porsche-911-st-preowned-9P2V7O"),
                "required: detail page of the most expensive listing (911 S/T)")
    judge.check("visited_dealer_for_partner_no",
                navigated_dealer_search(traj, query="Porsche Tacoma")
                or navigated_dealer_search(traj, state="WA"),
                "required: dealer directory for Porsche Tacoma's partner number")
    # answer gates
    judge.check("answer_full_name", contains_phrase(answer, "911 S/T"),
                "most expensive listing: 2024 Porsche 911 S/T")
    judge.check("answer_vin", contains_vin(answer, "WP0AF2A9XRS274223"),
                "VIN WP0AF2A9XRS274223")
    judge.check("answer_color", contains_phrase(answer, "White"),
                "exterior color White")
    judge.check("answer_mileage", contains_count(answer, 4052),
                "4,052 miles")
    judge.check("answer_price_before_fees", contains_amount(answer, 609899),
                "vehicle price before fees $609,899.00")
    judge.check("answer_doc_fee", contains_amount(answer, 200),
                "documentation fee $200.00")
    judge.check("answer_total_price", contains_amount(answer, 610099),
                "total price $610,099.00")
    judge.check("answer_second_name", contains_phrase(answer, "911 GT3"),
                "second most expensive: 2026 Porsche 911 GT3")
    judge.check("answer_second_price", contains_amount(answer, 359992),
                "$359,992")
    judge.check("answer_partner_number", contains_ref(answer, "4501962"),
                "Porsche Tacoma partner number 4501962")
    check_read_only(judge, initial_db, after_db)


if __name__ == "__main__":
    run_verifier(TASK_ID, run_checks)
