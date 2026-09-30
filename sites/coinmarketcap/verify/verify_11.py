#!/usr/bin/env python3
"""Deterministic verifier for CoinMarketCap--11 (coinmarketcap).

Ground truth below is HARDCODED (re-frozen from the contributor's two honest
Playwright rounds on the r2-fix container wh-coinmarketcap-fix2, image seed
sha256 f0d2d46b01bab8896f026929be4ae1ded19b8eb1ea2d969583857ac562eb427c,
md5 990af4a551228a1877ae0118ad3ae3b0) — never read from tasks.jsonl.
All values are the frozen 2026-09-29/30 UTC capture snapshot.

r2-fix notes (B3 depth + M1 scope + a truth correction):
  1. The task was deepened (T11 honest depth 13→16 atomic steps) with two
     more text-required exchange pages: the #1 DEX (GaiaEx) for its market
     share and launch date, and OKX for its derivatives volume.
  2. TRUTH CORRECTION vs the r1 contract: the r1 gate froze Bybit's taker
     fee as "0.05%", but the page renders (and the r1 walk fact recorded)
     "Maker / Taker Fee 0.02% / 0.06%" (captured taker_fee 0.055 → 2dp).
     The re-frozen gate uses the on-page truth 0.06%.
  3. Known gap (still open, M1): the derivatives rankings table shows the
     SPOT filtered volume / market share for cross-listed exchanges; the
     task only asks for the top-3 NAMES and detail-page values, which the
     detail pages render correctly.
Usage: python3 verify_11.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "CoinMarketCap--11"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    check_visited_path(judge, traj, "nav_dex_tab", r"tab=dex")
    check_visited_path(judge, traj, "nav_dex1", r"/exchanges/gaiaex/")
    check_visited_path(judge, traj, "nav_dex2", r"/exchanges/hyperliquid/")
    check_visited_path(judge, traj, "nav_deriv_tab", r"tab=derivatives")
    check_visited_path(judge, traj, "nav_deriv8", r"/exchanges/deribit/")
    check_visited_path(judge, traj, "nav_bybit", r"/exchanges/bybit/")
    check_visited_path(judge, traj, "nav_okx", r"/exchanges/okx/")
    check_visited_path(judge, traj, "nav_spot_tab", r"tab=spot")
    check_answer_ordered(judge, answer, "dex_top3", ["GaiaEx", "Hyperliquid", "PumpSwap"])
    check_answer_phrase(judge, answer, "dex1_share", "49.55%")
    check_answer_phrase(judge, answer, "dex1_launch", "Feb 21, 2025")
    check_answer_phrase(judge, answer, "dex2_pair", "HYPE/USDC")
    check_answer_phrase(judge, answer, "dex2_price", "$86.30")
    check_answer_phrase(judge, answer, "dex2_volume", "$85.11M")
    check_answer_count_at_least(judge, answer, "deriv_top3", ["Binance", "OKX", "Bybit"], 3)
    check_answer_phrase(judge, answer, "deriv8_volume", "$1.40B")
    check_answer_phrase(judge, answer, "deriv8_oi", "$1.87B")
    check_answer_phrase(judge, answer, "bybit_maker", "0.02%")
    check_answer_phrase(judge, answer, "bybit_taker", "0.06%")
    check_answer_phrase(judge, answer, "okx_deriv_volume", "$24.96B")
    check_answer_any(judge, answer, "more_exchanges", ["DEX"])
    check_read_only(judge, initial, after)


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
