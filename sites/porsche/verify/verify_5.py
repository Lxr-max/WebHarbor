"""Deterministic verifier for porsche task 5; see tasks.jsonl and verify/README.md."""
from verify_lib import (check_read_only, check_seed_contract, check_trajectory_identity,
                        contains_amount, contains_count, contains_phrase,
                        final_answer, navigated_configurator, run_verifier)

TASK_ID = "Porsche--5"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_seed_contract(judge, initial_db)
    judge.check("visited_cayenne_cfg", navigated_configurator(traj, "9YAAI1"),
                "required: configurator page for 9YAAI1")
    judge.check("visited_cayenne_s_electric_cfg", navigated_configurator(traj, "X1ABB1"),
                "required: configurator page for X1ABB1")
    judge.check("visited_macan_cfg", navigated_configurator(traj, "95BAU1"),
                "required: configurator page for 95BAU1")
    # answer gates
    judge.check("answer_cayenne_options", contains_count(answer, 47),
                "Cayenne catalog: 47 options")
    judge.check("answer_cayenne_base", contains_amount(answer, 89900),
                "Cayenne base price $89,900")
    judge.check("answer_cayenne_s_electric_options", contains_count(answer, 36),
                "Cayenne S Electric catalog: 36 options")
    judge.check("answer_cayenne_s_electric_base", contains_amount(answer, 126300),
                "Cayenne S Electric base price $126,300")
    judge.check("answer_macan_options", contains_count(answer, 44),
                "Macan catalog: 44 options")
    judge.check("answer_macan_base", contains_amount(answer, 65400),
                "Macan base price $65,400")
    judge.check("answer_largest_catalog",
                contains_phrase(answer, "cayenne") and contains_count(answer, 47),
                "the Cayenne catalog is the largest (47 options)")
    judge.check("answer_top_option_name",
                contains_phrase(answer, "Club Leather Interior in Black/Barrique with Cross-Stitching"),
                "most expensive option: Club Leather Interior in Black/Barrique with Cross-Stitching")
    judge.check("answer_top_option_model",
                contains_phrase(answer, "Cayenne"),
                "it belongs to the Cayenne catalog")
    judge.check("answer_top_option_price", contains_amount(answer, 6220),
                "it costs $6,220")
    check_read_only(judge, initial_db, after_db)


if __name__ == "__main__":
    run_verifier(TASK_ID, run_checks)
