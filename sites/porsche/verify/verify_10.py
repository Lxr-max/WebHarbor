"""Deterministic verifier for porsche task 10; see tasks.jsonl and verify/README.md."""
from verify_lib import (check_read_only, check_seed_contract, check_trajectory_identity,
                        contains_amount, contains_count, contains_phrase, contains_vin,
                        final_answer, navigated_finder, navigated_vehicle_detail,
                        run_verifier)

TASK_ID = "Porsche--10"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_seed_contract(judge, initial_db)
    judge.check("visited_finder_new_macan",
                navigated_finder(traj, condition="new", range="Macan"),
                "required: /finder/us/en-US/search?condition=new&range=Macan")
    judge.check("visited_cheapest_macan_detail",
                navigated_vehicle_detail(traj, "porsche-macan-new-W32Q6Q"),
                "required: detail page of the least expensive new Macan")
    # answer gates
    judge.check("answer_price", contains_amount(answer, 77100),
                "least expensive new Macan: $77,100")
    judge.check("answer_vin", contains_vin(answer, "WP1AA2A54TLB20053"),
                "VIN WP1AA2A54TLB20053")
    judge.check("answer_color", contains_phrase(answer, "Carrara White Metallic"),
                "exterior color Carrara White Metallic")
    judge.check("answer_transmission", contains_phrase(answer, "PDK"),
                "transmission PDK (Automatic)")
    import re
    judge.check("monthly_payment", bool(re.search(r"1,?114\.44\s*(?:per|a|/)\s*month", answer, re.I)))
    judge.check("lease_term", bool(re.search(r"39[- ]months?", answer, re.I)))
    judge.check("down_payment", bool(re.search(r"(?:\$?7,?710(?:\.00)?\s*(?:down|deposit)|down.{0,20}\$?7,?710)", answer, re.I)))
    judge.check("no_security_deposit", bool(re.search(r"(?:no|without) (?:a )?security deposit|security deposit (?:is )?(?:not required|not needed|waived)", answer, re.I)))
    judge.check("delivery_fee", contains_amount(answer, 2350))
    judge.check("answer_new_macan_total", contains_count(answer, 116),
                "116 brand-new Macans in stock")
    check_read_only(judge, initial_db, after_db)


if __name__ == "__main__":
    run_verifier(TASK_ID, run_checks)
