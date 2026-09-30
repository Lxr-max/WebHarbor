"""Deterministic verifier for porsche task 16; see tasks.jsonl and verify/README.md."""
from verify_lib import (contains_ref, check_read_only, check_seed_contract, check_trajectory_identity,
                        contains_amount, contains_phrase, contains_ref, final_answer,
                        navigated_shop_category, run_verifier)

TASK_ID = "Porsche--16"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_seed_contract(judge, initial_db)
    judge.check("visited_accessories", navigated_shop_category(traj, "vehicle-accessories"),
                "required: Vehicle Accessories category")
    judge.check("visited_clothing", navigated_shop_category(traj, "clothing"),
                "required: Clothing category")
    judge.check("visited_home", navigated_shop_category(traj, "home-lifestyle"),
                "required: Home & Lifestyle category")
    # answer gates
    judge.check("answer_top_name", contains_phrase(answer, "911 Soundbar 2.0"),
                "most expensive product: 911 Soundbar 2.0")
    judge.check("answer_top_category", contains_phrase(answer, "Home & Lifestyle")
                or contains_phrase(answer, "home & lifestyle"),
                "category Home & Lifestyle")
    judge.check("answer_top_price", contains_amount(answer, 4070),
                "$4,070")
    judge.check("answer_top_sku", contains_ref(answer, "WAP0509110PSDB"),
                "SKU WAP0509110PSDB")
    judge.check("answer_accessories_top",
                contains_phrase(answer, "Rear Bicycle Carrier") and contains_amount(answer, 3372),
                "Vehicle Accessories top: Rear Bicycle Carrier $3,372")
    judge.check("answer_clothing_top",
                contains_phrase(answer, "Classic Leather Jacket") and contains_amount(answer, 1990),
                "Clothing top: Classic Leather Jacket $1,990")
    judge.check("accessories_sku", contains_ref(answer, "9J0813601A"))
    judge.check("clothing_sku", contains_ref(answer, "4056487100289"))
    check_read_only(judge, initial_db, after_db)


if __name__ == "__main__":
    run_verifier(TASK_ID, run_checks)
