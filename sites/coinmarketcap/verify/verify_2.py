#!/usr/bin/env python3
"""Deterministic verifier for CoinMarketCap--2 (coinmarketcap).

Ground truth below is HARDCODED (frozen from the reviewer's independent
Playwright round on the review container wh-coinmarketcap-review, container
seed sha256 f0d2d46b01bab8896f026929be4ae1ded19b8eb1ea2d969583857ac562eb427c,
md5 990af4a551228a1877ae0118ad3ae3b0) — never read from tasks.jsonl.
All values are the frozen 2026-09-29/30 UTC capture snapshot.

r2-fix note: the type tabs are LIVE UI now (real links preserving the
active filters), so the Coins/Tokens switches are real clicks and the URL
gates match the tab links exactly. Remaining known gap: the task text calls
the category "Collectibles & NFTs" while the site names it "NFTs &
Collectibles" (upstream-verbatim name; findable, no data change needed).
Usage: python3 verify_2.py --run_dir DIR [--initial_db P] [--after_db P]
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
    check_visited_path, final_answer, run_verifier,
)

TASK_ID = "CoinMarketCap--2"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    check_visited_path(judge, traj, "nav_type_coins", r"type=coins")
    check_visited_path(judge, traj, "nav_type_tokens", r"type=tokens")
    check_visited_path(judge, traj, "nav_memes", r"/view/memes/")
    check_visited_path(judge, traj, "nav_stablecoin", r"/view/stablecoin/")
    check_visited_path(judge, traj, "nav_top_stable", r"/currencies/tether/")
    check_visited_path(judge, traj, "nav_layer1", r"/view/layer-1/")
    check_visited_path(judge, traj, "nav_lending", r"/view/lending-borowing/")
    check_visited_path(judge, traj, "nav_lend_top", r"/currencies/aave/")
    check_visited_path(judge, traj, "nav_nft", r"/view/collectibles-nfts/")
    check_answer_phrase(judge, answer, "stablecoin_gone", "Tether")
    check_answer_any(judge, answer, "first_token", ["USDT", "Tether"])
    check_answer_number(judge, answer, "first_token_rank", 3)
    check_answer_number(judge, answer, "memes_shown", 9)
    check_answer_any(judge, answer, "memes_upstream_total", ["5,363", "5363", "5,434", "5434"])
    check_answer_any(judge, answer, "top_meme", ["Dogecoin", "DOGE"])
    check_answer_phrase(judge, answer, "top_meme_24h", "+0.01%")
    check_answer_phrase(judge, answer, "top_stable", "Tether")
    check_answer_number(judge, answer, "top_stable_rank", 3)
    check_answer_ordered(judge, answer, "layer1_top3", ["Bitcoin", "Ethereum", "BNB"])
    check_answer_phrase(judge, answer, "lending_top", "Aave")
    check_answer_number(judge, answer, "lending_top_rank", 37)
    check_answer_phrase(judge, answer, "lending_top_24h", "+10.77%")
    check_answer_any(judge, answer, "nft_top", ["Render", "RENDER"])
    check_read_only(judge, initial, after)


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
