"""Deterministic verifier for porsche task 19; see tasks.jsonl and verify/README.md."""
from verify_lib import (added_rows, check_only_tables_changed, check_seed_contract,
                        check_trajectory_identity, contains_amount, contains_count,
                        contains_phrase, contains_vin, entered_identity, final_answer,
                        navigated_finder, navigated_register, navigated_saved_vehicles,
                        navigated_vehicle_detail, rows_of, run_verifier)

TASK_ID = "Porsche--19"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_seed_contract(judge, initial_db)
    judge.check("visited_register", navigated_register(traj),
                "required: /my-porsche/register")
    judge.check("entered_new_email", entered_identity(traj, "alex.rivera@test.com"),
                "required: registration with alex.rivera@test.com")
    judge.check("visited_finder_preowned_911",
                navigated_finder(traj, range="911")
                or navigated_finder(traj, range="911", condition="preowned"),
                "required: finder filtered to the 911 range (pre-owned)")
    judge.check("visited_911_detail",
                navigated_vehicle_detail(traj, "porsche-911-carrera-4s-coupe-preowned-D4OZNP"),
                "required: 911 Carrera 4S Coupe detail page")
    judge.check("visited_saved_vehicles", navigated_saved_vehicles(traj),
                "required: /my-porsche/saved-vehicles showing the saved row")
    # DB delta: one users row + one saved_vehicles row under it
    check_only_tables_changed(judge, initial_db, after_db, {"users", "saved_vehicles"})
    users = added_rows(after_db, initial_db, "users", "id")
    judge.check("exactly_one_new_user", len(users) == 1, f"users delta = {len(users)}")
    user = users[0] if users else {}
    judge.check("new_user_email", (user.get("email") or "").lower() == "alex.rivera@test.com",
                f"new user email {user.get('email')!r}")
    judge.check("new_user_name",
                (user.get("first_name") or "") == "Alex" and (user.get("last_name") or "") == "Rivera",
                f"new user name {user.get('first_name')!r} {user.get('last_name')!r}")
    import bcrypt
    judge.check("new_user_password", bcrypt.checkpw(b"FastDriver9!", user.get("password_hash", "").encode()))
    saved = added_rows(after_db, initial_db, "saved_vehicles", "id")
    judge.check("exactly_one_saved_vehicle", len(saved) == 1,
                f"saved_vehicles delta = {len(saved)}")
    if saved:
        judge.check("saved_under_new_user", saved[0].get("user_id") == user.get("id"),
                   f"saved vehicle user_id={saved[0].get('user_id')}")
        vehicle = next((v for v in rows_of(initial_db, "vehicles")
                        if v["id"] == saved[0].get("vehicle_id")), None)
        judge.check("saved_cheapest_preowned_911",
                    vehicle is not None and vehicle["vin"] == "WP0AB2A99ES121144",
                    f"saved vehicle VIN {vehicle['vin'] if vehicle else None}")
    # answer gates
    judge.check("answer_name", contains_phrase(answer, "911 Carrera 4S Coupe"),
                "the least expensive pre-owned 911: 911 Carrera 4S Coupe")
    judge.check("answer_price", contains_amount(answer, 99999),
                "$99,999")
    judge.check("answer_vin", contains_vin(answer, "WP0AB2A99ES121144"),
                "VIN WP0AB2A99ES121144")
    judge.check("answer_color", contains_phrase(answer, "Black"),
                "exterior color Black")
    judge.check("answer_dealer", contains_phrase(answer, "Porsche Seattle North"),
                "selling Porsche Center: Porsche Seattle North")
    judge.check("answer_stock_total", contains_count(answer, 32),
                "32 pre-owned 911s in stock in total")


if __name__ == "__main__":
    run_verifier(TASK_ID, run_checks)
