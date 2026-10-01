#!/usr/bin/env python3
"""Deterministic verifier for NYSE--8 (nyse).

Ground truth below is HARDCODED (frozen from the reviewer's two independent
honest Playwright rounds on the r2 review container wh-nyse-r2, seed md5
b7c3bbfa3a7a64b8d09b4e7fb3323fd9, with every hardcoded fact cross-checked
against the frozen seed database) — never read from tasks.jsonl.

r2 re-anchor: the r1 task asked Dana to "add NIO" while her seeded watchlist
already contained NIO (toggle showed Remove; two honest executions answered
differently). The fix re-anchors the leg to Coca-Cola (KO) — NOT in Dana's
seeded watchlist — so the honest execution adds exactly one watch_items row
(dana/KO) and the final total is uniquely 4 (SPY/NIO/AMC/KO). The history
question now quotes the page's own wording ("moved into a new building with a
much larger Trading Floor"); the answer year is unchanged (1903).
Usage: python3 verify_8.py --run_dir DIR [--initial_db P] [--after_db P]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from verify_lib import (
    check_answer_absent, check_answer_any, check_answer_count_at_least,
    check_answer_number, check_answer_number_absent, check_answer_ordered,
    check_answer_phrase, check_answer_price, check_answer_regex,
    check_answer_zero_or_phrase, check_read_only, check_rows_added,
    check_rows_removed, check_only_tables_changed, check_screenshots,
    check_seed_contract, check_trajectory_identity, check_visited_all,
    check_visited_any, check_visited_path, final_answer, run_verifier,
)

TASK_ID = "NYSE--8"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    # History (Buttonwood year, 1903 building), Closing Bell Sept count +
    # first title, Markets first NYSE mover + American rows, dana login,
    # Coca-Cola search, add KO to the watchlist, watchlist total (4).
    check_visited_all(judge, traj, "nav_surfaces", [
        r"/history-of-nyse",
        r"/bell/calendar\?[^ ]*type=Closing\+Bell[^ ]*from=2026-09-01[^ ]*to=2026-09-30",
        r"/markets",
        r"/login",
        r"/listings_directory/stock\?q=Coca",
        r"/quote/XNYS:KO",
        r"/watchlist",
    ])
    check_answer_number(judge, answer, "buttonwood_year", 1792)
    check_answer_number(judge, answer, "broad_year", 1903)
    check_answer_number(judge, answer, "sep_closing_count", 21)
    check_answer_regex(judge, answer, "sep_first_title", r"arcos dorados[^\n]*rings the closing bell")
    check_answer_phrase(judge, answer, "first_nyse_mover", "NU Holdings")
    check_answer_price(judge, answer, "first_nyse_last", 12.35)
    check_answer_number(judge, answer, "american_rows", 10)
    check_answer_number(judge, answer, "dana_watch_total", 4)
    check_answer_count_at_least(judge, answer, "dana_watch_symbols",
        ["SPY", "NIO", "AMC", "KO"], 4)
    check_only_tables_changed(judge, initial, after, {"watch_items"})
    check_rows_added(judge, initial, after, "watch_items", [
        [None, 4, "KO", "2026-09-29"],
    ], "watch_row_added")



if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
