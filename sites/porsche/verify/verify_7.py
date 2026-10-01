"""Deterministic verifier for porsche task 7; see tasks.jsonl and verify/README.md."""
from verify_lib import (check_read_only, check_seed_contract, check_trajectory_identity,
                        contains_amount, contains_count, contains_phrase, contains_vin,
                        final_answer, navigated_finder, navigated_vehicle_detail,
                        run_verifier)

TASK_ID = "Porsche--7"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_seed_contract(judge, initial_db)
    judge.check("visited_finder_manual_911",
                navigated_finder(traj, transmission="Manual", range="911"),
                "required: /finder/us/en-US/search?transmission=Manual&range=911")
    judge.check("visited_st_detail", navigated_vehicle_detail(traj, "porsche-911-st-preowned-9P2V7O"),
                "required: 911 S/T detail page")
    # answer gates
    judge.check("answer_manual_911_count", contains_count(answer, 6),
                "6 manual-transmission 911s")
    judge.check("answer_most_name", contains_phrase(answer, "911 S/T"),
                "most expensive manual 911: 911 S/T")
    judge.check("answer_most_price", contains_amount(answer, 610099),
                "$610,099")
    judge.check("answer_most_vin", contains_vin(answer, "WP0AF2A9XRS274223"),
                "VIN WP0AF2A9XRS274223")
    judge.check("answer_most_color", contains_phrase(answer, "White"),
                "exterior color White")
    judge.check("answer_most_mileage", contains_count(answer, 4052),
                "4,052 miles")
    judge.check("answer_most_dealer", contains_phrase(answer, "Porsche Tacoma"),
                "sold by Porsche Tacoma")
    judge.check("answer_least_name", contains_phrase(answer, "911 Carrera T"),
                "least expensive manual 911: 911 Carrera T")
    judge.check("answer_least_price", contains_amount(answer, 194155),
                "$194,155")
    judge.check("least_detail", navigated_vehicle_detail(traj, "porsche-911-carrera-t-preowned-RNR59L"))
    judge.check("least_vin", contains_vin(answer, "WP0AA2A9XSS209182"))
    judge.check("least_mileage", contains_count(answer, 2448))
    judge.check("least_color", contains_phrase(answer, "Gentian Blue Metallic"))
    judge.check("least_dealer", contains_phrase(answer, "Porsche Bellevue"))
    check_read_only(judge, initial_db, after_db)


if __name__ == "__main__":
    run_verifier(TASK_ID, run_checks)
