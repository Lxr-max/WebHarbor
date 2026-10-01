#!/usr/bin/env python3
"""Deterministic verifier for Trader Joe's--19 (trader_joes).

Ground truth below is HARDCODED (frozen from the reviewer's two independent
honest Playwright r2 rounds on the review container tj-review-r2-container
built over the fix commit fb73dbfa, seed md5
34e1af0cc66a317223e889081c2381b4, with every hardcoded fact cross-checked
against the frozen seed database) — never read from tasks.jsonl.
Usage: python3 verify_19.py --run_dir DIR [--initial_db P] [--after_db P]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from verify_lib import (
    check_answer_absent, check_answer_any, check_answer_count_at_least,
    check_answer_number, check_answer_number_absent, check_answer_number_any,
    check_answer_ordered, check_answer_phrase, check_answer_price,
    check_answer_regex, check_answer_zero_or_phrase, check_read_only,
    check_rows_added, check_rows_removed, check_rows_changed,
    check_only_tables_changed, check_screenshots, check_seed_contract,
    check_trajectory_identity, check_visited_all, check_visited_any,
    check_visited_path, final_answer, run_verifier,
)

TASK_ID = "Trader Joe's--19"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    # Entertaining articles; guides listing; newest guide; stories listing; alice add + increase.
    check_visited_all(judge, traj, "nav_surfaces", [
        r"/home/discover/entertaining",
        r"/home/discover/guides",
        r"/home/discover/guides/one-seasoning-wonder",
        r"/home/discover/stories",
        r"/home/discover/stories/cider-to-crow-about",
        r"/login",
        r"/home/products/pdp/063804",
        r"/home/shopping-list",
    ])
    check_answer_number(judge, answer, "entertaining_count", 17)
    check_answer_phrase(judge, answer, "first_article", "Fall Forward With Spiced Chai Apple Crisp")
    check_answer_phrase(judge, answer, "first_category", "Common")
    check_answer_number(judge, answer, "guides_count", 56)
    check_answer_phrase(judge, answer, "newest_guide", "One Seasoning Wonder")
    check_answer_phrase(judge, answer, "guide_date", "2026-09-16")
    check_answer_phrase(judge, answer, "featured_product",
                        "Mushroom & Company Multipurpose Umami Seasoning Blend")
    check_answer_number(judge, answer, "stories_count", 67)
    check_answer_phrase(judge, answer, "newest_story", "A Cider to Crow About")
    check_answer_phrase(judge, answer, "newest_story_date", "2026-09-25")
    check_answer_number(judge, answer, "new_total", 9)
    check_answer_number(judge, answer, "final_total", 10)
    check_only_tables_changed(judge, initial, after, {"shopping_items"})
    check_rows_added(judge, initial, after, "shopping_items",
                     [[None, 1, "063804", 2, None]], "alice_adds_umami_seasoning_x2")

if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
