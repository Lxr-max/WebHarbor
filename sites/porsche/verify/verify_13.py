from verify_lib import (check_read_only, check_seed_contract, check_trajectory_identity,
                        contains_amount, contains_count, contains_phrase, final_answer,
                        navigated_dealer_search, navigated_finder, run_verifier)

TASK_ID = "Porsche--13"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_seed_contract(judge, initial_db)
    judge.check("visited_dealersearch_wa", navigated_dealer_search(traj, state="WA"),
                "required: /usa/dealersearch/?state=WA")
    judge.check("visited_stock_leader_inventory",
                navigated_finder(traj, dealer="Porsche Bellevue"),
                "required: finder filtered to the WA stock leader's inventory")
    # answer gates — earliest weekday opening (unchanged anchor)
    judge.check("answer_center_name", contains_phrase(answer, "Porsche Bellevue"),
                "earliest weekday opening: Porsche Bellevue")
    judge.check("answer_opening_time", contains_phrase(answer, "09:00") or contains_phrase(answer, "9 am"),
                "opens at 09:00")
    judge.check("answer_street", contains_phrase(answer, "11910 N.E. 8th Street"),
                "street address 11910 N.E. 8th Street")
    judge.check("answer_phone", contains_phrase(answer, "+1 425-633-1583") or contains_phrase(answer, "425-633-1583"),
                "phone +1 425-633-1583")
    # answer gates — WA stock leader (r2 re-anchored sub-question)
    judge.check("answer_leader_name", contains_phrase(answer, "Porsche Bellevue"),
                "the WA center listing the most vehicles: Porsche Bellevue")
    judge.check("answer_leader_inventory_count", contains_count(answer, 236),
                "Porsche Bellevue lists 236 in-stock vehicles")
    judge.check("answer_cheapest_1",
                contains_phrase(answer, "2014 Porsche Cayenne") and contains_amount(answer, 7795),
                "cheapest: 2014 Porsche Cayenne at $7,795")
    judge.check("answer_cheapest_2",
                contains_phrase(answer, "2017 Porsche Macan") and contains_amount(answer, 18000),
                "second cheapest: 2017 Porsche Macan at $18,000")
    check_read_only(judge, initial_db, after_db)


if __name__ == "__main__":
    run_verifier(TASK_ID, run_checks)
