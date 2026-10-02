"""Deterministic verifier for porsche task 3; see tasks.jsonl and verify/README.md."""
from verify_lib import (check_read_only, check_seed_contract, check_trajectory_identity,
                        contains_amount, contains_count, contains_phrase, contains_vin,
                        final_answer, navigated_finder, navigated_model_detail,
                        navigated_models_overview, navigated_to_path, navigated_vehicle_detail,
                        run_verifier)

TASK_ID = "Porsche--3"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_seed_contract(judge, initial_db)
    judge.check("visited_cayenne_lineup",
                navigated_models_overview(traj, range="Cayenne")
                or navigated_to_path(traj, "/usa/models/cayenne")
                or navigated_model_detail(traj, "cayenne-turbo-gt"),
                "required: Cayenne lineup (filtered overview, range page or Turbo GT page)")
    judge.check("visited_finder_cayenne", navigated_finder(traj, range="Cayenne"),
                "required: /finder/us/en-US/search?range=Cayenne")
    judge.check("visited_cheapest_cayenne_detail",
                navigated_vehicle_detail(traj, "porsche-cayenne-preowned-L6LRPX"),
                "required: detail page of the least expensive Cayenne")
    # answer gates
    judge.check("answer_top_cayenne_msrp", contains_amount(answer, 214800),
                "most expensive Cayenne variant MSRP $214,800")
    judge.check("answer_top_cayenne_name", contains_phrase(answer, "Cayenne Turbo GT"),
                "the most expensive Cayenne variant is the Cayenne Turbo GT")
    judge.check("answer_cheapest_price", contains_amount(answer, 7795),
                "least expensive Cayenne in stock costs $7,795")
    judge.check("answer_cheapest_vin", contains_vin(answer, "WP1AA2A25ELA00643"),
                "VIN WP1AA2A25ELA00643")
    judge.check("answer_cheapest_mileage", contains_count(answer, 200500),
                "200,500 miles")
    judge.check("answer_cheapest_body", contains_phrase(answer, "SUV"),
                "body style SUV")
    judge.check("answer_cheapest_color", contains_phrase(answer, "Dark Blue Metallic"),
                "exterior color Dark Blue Metallic")
    judge.check("answer_cheapest_dealer", contains_phrase(answer, "Porsche Bellevue"),
                "sold by Porsche Bellevue")
    judge.check("answer_cheaper_by", contains_amount(answer, 207005),
                "$207,005 cheaper than the lineup MSRP")
    check_read_only(judge, initial_db, after_db)


if __name__ == "__main__":
    run_verifier(TASK_ID, run_checks)
