"""Deterministic verifier for porsche task 2; see tasks.jsonl and verify/README.md."""
from verify_lib import (check_read_only, check_seed_contract, check_trajectory_identity,
                        contains_amount, contains_count, contains_phrase,
                        final_answer, navigated_model_detail,
                        navigated_models_overview, run_verifier)

TASK_ID = "Porsche--2"

ELECTRIC_VARIANTS = [
    "Cayenne Turbo Electric", "Cayenne Turbo Coupe Electric",
    "Taycan Turbo GT with Weissach Package", "Taycan Turbo GT", "Taycan Turbo S",
    "Taycan Turbo", "Taycan GTS", "Cayenne S Electric", "Cayenne S Coupe Electric",
    "Macan Turbo Electric", "Macan GTS Electric", "Taycan 4S", "Macan 4S Electric",
    "Cayenne Electric", "Cayenne Coupe Electric", "Macan 4 Electric", "Taycan",
    "Taycan 4", "Macan Electric",
]


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_seed_contract(judge, initial_db)
    judge.check("visited_electric_filter", navigated_models_overview(traj, fuel="Electric"),
                "required: /usa/models/?fuel=Electric")
    # the task names the page: the Taycan Turbo GT with Weissach Package
    # (the r2 re-anchor resolves the site's $243,700 tie by naming the page)
    judge.check("visited_most_expensive_electric_page",
                navigated_model_detail(traj, "taycan-turbo-gt-wp"),
                "required: Taycan Turbo GT with Weissach Package model page")
    import json, re
    from pathlib import Path
    from verify_lib import entity_passages
    specs = json.loads(Path(__file__).with_name('electric_specs.json').read_text())
    passages = entity_passages(answer, specs)
    for name, expected in specs.items():
        judge.check(name+' price', contains_amount(passages[name], expected['price']))
        hp = f"{expected['hp']:,}".replace(',', ',?')
        judge.check(name+' power', bool(re.search(r'(?<![\d.])'+hp+r'\s*(?:hp|horsepower)\b', passages[name], re.I)))
    # answer gates: every electric variant must be listed
    missing = [v for v in ELECTRIC_VARIANTS if v.lower() not in answer.lower()]
    judge.check("answer_lists_all_19_electric_variants", not missing,
                f"missing from the list: {missing[:4]}")
    judge.check("answer_variant_count_19", contains_count(answer, 19),
                "19 purely electric variants")
    judge.check("answer_shared_power_pair",
                contains_phrase(answer, "Cayenne Turbo Electric")
                and contains_phrase(answer, "Cayenne Turbo Coupe Electric"),
                "the 1,139 hp pair: Cayenne Turbo Electric + Cayenne Turbo Coupe Electric")
    judge.check("answer_shared_output_1139", contains_count(answer, 1139),
                "shared output 1,139 hp")
    judge.check("answer_weissach_price", contains_amount(answer, 243700),
                "the most expensive electric variant(s) start at $243,700")
    judge.check("answer_flagship_0_60_and_top_speed",
                contains_phrase(answer, "2.1") and contains_phrase(answer, "190 mph"),
                "Weissach page: 0-60 2.1 s / top track speed 190 mph")
    check_read_only(judge, initial_db, after_db)


if __name__ == "__main__":
    run_verifier(TASK_ID, run_checks)
