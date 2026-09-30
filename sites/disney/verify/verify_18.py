#!/usr/bin/env python3
"""Deterministic verifier for Disney--18 (disney).

Ground truth below is HARDCODED from the reviewer's independent Playwright
honest-path walk on the r2 review container (wh-disney-r2-review, seed md5
9f231a5a…) — never read from tasks.jsonl.

Usage: python3 verify_18.py --run_dir DIR [--initial_db P] [--after_db P]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from verify_lib import (
    check_answer_absent,
    check_answer_any,
    check_answer_count_at_least,
    check_answer_number,
    check_answer_number_absent,
    check_answer_ordered,
    check_answer_money,
    check_answer_phrase,
    check_answer_regex,
    check_only_tables_changed,
    check_read_only,
    check_row_matches,
    check_rows_added,
    check_screenshots,
    check_seed_contract,
    check_trajectory_identity,
    check_visited_all,
    check_visited_any,
    check_visited_path,
    run_verifier
)

TASK_ID = "Disney--18"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = (traj.get("final_answer") or "")

    # -- navigation gates (anti knowledge-shortcut) --
    check_visited_path(judge, traj, "frozen_search", r"""/search\?[^\" ]*q=frozen"""),
    check_visited_path(judge, traj, "fea_detail", r"""/parks/attractions/epcot/frozen-ever-after"""),
    check_visited_path(judge, traj, "frozen3_detail", r"""/movies/frozen-3"""),
    check_visited_path(judge, traj, "login", r"""/login"""),
    check_visited_path(judge, traj, "favorites", r"""/favorites"""),
    check_visited_path(judge, traj, "stitch_search", r"""/search\?[^\" ]*q=stitch"""),
    check_visited_path(judge, traj, "stitch_detail", r"""/shop/products/415161238870"""),
    check_visited_path(judge, traj, "bag", r"""/bag"""),
    # -- answer ground truth --
    check_answer_number(judge, answer, "frozen_movies", 1)
    check_answer_number(judge, answer, "frozen_parks_entertainment", 3)
    check_answer_phrase(judge, answer, "fea_park", "EPCOT")
    check_answer_phrase(judge, answer, "fea_height", "Any height")
    check_answer_phrase(judge, answer, "movie_title", "Frozen 3")
    check_answer_phrase(judge, answer, "movie_rating", "Not Yet Rated")
    check_answer_phrase(judge, answer, "movie_date", "November 24, 2027")
    check_answer_number(judge, answer, "dana_favorites_total", 4)
    check_answer_number(judge, answer, "stitch_products", 5)
    check_answer_phrase(judge, answer, "first_stitch", "Stitch Knit Plush")
    check_answer_money(judge, answer, "stitch_price", 24.99)
    check_answer_money(judge, answer, "bag_total", 24.99)

    check_only_tables_changed(judge, initial, after, {"favorites", "cart_items"})
    check_rows_added(judge, initial, after, "favorites", 1)
    check_row_matches(judge, after,
        "SELECT 1 FROM favorites WHERE user_id=4 AND item_type='movie' AND item_key='frozen-3'",
        (), "dana_faved_frozen3")
    check_rows_added(judge, initial, after, "cart_items", 1)
    check_row_matches(judge, after,
        "SELECT 1 FROM cart_items WHERE product_pid='415161238870' AND qty=1",
        (), "bag_row_stitch")

if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
