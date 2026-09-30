#!/usr/bin/env python3
"""Deterministic verifier for Airbnb--18 (airbnb).

Ground truth below is HARDCODED (re-frozen for the r2/r3 fix rounds and
independently re-verified by the reviewer: real Playwright walks on the
reviewer's own image builds — r2: wh-airbnb-r2review @ 46116 from
d23640b0; r3: wh-airbnb-r3review @ 49116 from fed30bf9 — seed sha256
recorded in verify_lib.py) — never read from tasks.jsonl.

R2 RE-FREEZE NOTES (contribution fix round, review findings H3/M1 + depth):
(a) the book-it widget is now ONE shared form — the Request-to-book button
submits the current GUESTS select value via formaction, so booking for 3
guests no longer silently lands as 2 (the old hidden-input defect is gone);
(b) the mid-booking login bounce is fixed (relative `next`), so the
confirm round trip returns to the book page without browser-back
recovery; (c) the task was deepened with a post-booking save chain
(return to the listing, save it to the default wishlist, report the
default wishlist's saved-item count) — dana has no default wishlist in
the seed, so the save creates 'Saved' holding exactly one item.

Usage: python3 verify_18.py --run_dir DIR [--initial_db P] [--after_db P]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from verify_lib import (
    check_answer_absent, check_answer_any, check_answer_count_at_least,
    check_answer_money, check_answer_number, check_answer_number_absent,
    check_answer_ordered, check_answer_phrase, check_answer_regex,
    check_read_only, check_rows_added, check_rows_changed, check_rows_removed,
    check_only_tables_changed, check_screenshots, check_seed_contract,
    check_trajectory_identity, check_visited_all, check_visited_any,
    check_visited_path, final_answer, new_bookings,
    check_answer_has_new_booking_code, run_verifier, BOOKING_CODE_RX,
)

TASK_ID = "Airbnb--18"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)
    # navigation: Austin SERP with Instant Book + pets, the first PDP, the
    # book flow with 3 guests, login.
    check_visited_path(judge, traj, "nav_serp", r"/s/austin/homes\?[^ ]*instant_book=1")
    check_visited_path(judge, traj, "nav_serp_pets", r"/s/austin/homes\?[^ ]*pets=1")
    check_visited_path(judge, traj, "nav_pdp", r"/rooms/1747360047965466540")
    check_visited_path(judge, traj, "nav_book", r"/rooms/1747360047965466540/book")
    check_visited_path(judge, traj, "nav_login", r"/login")
    check_visited_path(judge, traj, "nav_wishlists", r"/wishlist")
    # answer ground truth
    check_answer_number(judge, answer, "ib_pets_count", 1)
    check_answer_any(judge, answer, "title",
        ["Townhouse in Austin", "UT Historic Scholar Home, Walk to Moody"])
    check_answer_money(judge, answer, "nightly", 150.60)
    check_answer_number(judge, answer, "capacity", 3)
    added = new_bookings(judge, initial, after)
    check_answer_has_new_booking_code(judge, answer, after, added, "booking_code")
    check_answer_money(judge, answer, "booking_total", 753.00)
    check_answer_number(judge, answer, "saved_count", 1)
    # stateful: dana books for 3 guests on the captured window, then saves
    # the listing to her (newly created) default wishlist
    check_rows_added(judge, initial, after, "bookings", [(
        None, "rx:^HM[A-Z0-9]{8}$", 4, "stay", "1747360047965466540", None, None,
        "2026-11-07", "2026-11-12", 3, 0, 0, 0, 3, 5, 150.6,
        753.0, 753.0, "confirmed", "2026-09-30")], "booking_row_shape")
    check_rows_added(judge, initial, after, "wishlists", [(
        None, 4, "Saved", 1, "2026-09-30")], "wishlist_row_shape")
    check_rows_added(judge, initial, after, "wishlist_items", [(
        None, None, "1747360047965466540", None, "2026-09-30")], "wishlist_item_row_shape")
    check_only_tables_changed(judge, initial, after,
                              {"bookings", "wishlists", "wishlist_items"})



if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
