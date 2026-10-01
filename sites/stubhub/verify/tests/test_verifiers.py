"""Deterministic verifier contract tests for the 21 stubhub tasks.

Covers, per task: the honest trajectory (from the reviewer's live runs, frozen
in fixtures_data.SPECS) MUST PASS; a no-op run (homepage only, empty answer,
clean DB) MUST FAIL; a knowledge-shortcut (correct answer + delta, homepage-only
navigation) MUST FAIL; a wrong answer MUST FAIL; a state-mismatch (success
claim, no DB delta) MUST FAIL for stateful tasks. Read-only tasks MUST FAIL on
a mutated after-DB. Package tampering (task_id mismatch, off-site URL, missing
screenshot, non-done trajectory, undecodable screenshot, wrong initial DB)
MUST fail closed.

No LLM: snapshots are seed copies mutated through sqlite, trajectories are
written in the agent_demo/agent.py shape.
"""
from __future__ import annotations

import json
import shutil
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _support import (BASE, PNG, RunBuilder, copy_db, exec_sql, honest_run,  # noqa: E402
                       noop_run, run_verifier, shortcut_run, state_mismatch_run,
                       tampered_read_only_run, task_ques, wrong_answer_run, acquire_seed)
from fixtures_data import SPECS  # noqa: E402

STATEFUL = {3, 4, 5, 6, 11, 12, 19}
READ_ONLY = {0, 1, 2, 7, 8, 9, 10, 13, 14, 15, 16, 17, 18, 20}
ALL = sorted(STATEFUL | READ_ONLY)

# plausible but wrong answers per task (each contradicts frozen ground truth)
WRONG_ANSWERS = {
    0: "The eight Seahawks home games run from $237 (Chargers) to $368 (49ers); the cheapest "
       "is the Cowboys game at $195 with get-in 320, Row AA; highest get-in $368.",
    1: "6 listings match all three conditions; the cheapest match is 305, Row QQ, $270. The "
       "cheapest 4-ticket 300 Level listing is 319, Row RR, $330. The zone option is cheaper.",
    2: "The two-day pass has 30 listings and a get-in of $1,140; Oct 1 has 25 listings at "
       "$750; Oct 3 has 11 listings at $1,130. The two single nights together are cheaper.",
    3: "Bought 2 tickets with UPS delivery. Order reference 41801304; delivery fee $12.95; "
       "processing fee $3.95; final total $406.90.",
    4: "Listed section 220 row 14 at $195 each, then updated to $175. Alice has 3 listings "
       "for sale with a combined asking value of $300.",
    5: "The site offers amounts $20/$50/$100/$200/$500 and three designs. Bought a $100 "
       "holiday gift card for Danny, code SHFIXTURE01. Carol's history shows 3 gift cards; "
       "the earliest is the $150 one from Sep 1, 2026.",
    6: "Favorites now shows two entries: metallica and the Giants game. Metallica has 21 "
       "upcoming events.",
    7: "For 'metal' the suggestion service proposes metallica. For 'seattle' it proposes "
       "seattle kraken, seattle mariners, seattle opera, seattle seahawks, seattle sounders "
       "fc, seattle symphony. Seattle Sounders FC: 56,600 followers, 5 upcoming events; next "
       "event \"Minnesota United FC at Seattle Sounders FC\" at Lumen Field. Seattle Mariners: "
       "75,200 followers, 2 upcoming events; next event \"Los Angeles Angels at Seattle "
       "Mariners\" at T-Mobile Park. The Mariners have more upcoming events.",
    8: "The Theater category contains Opera, Circus and Magic. The three soonest Comedy events "
       "are all on Sep 27; the one with the most listings has 25 listings.",
    9: "Salome has four performances: get-ins $125, $121, $154 and $118. The first has more "
       "listings (26 vs 23). The venue is Benaroya Hall, Bellevue. Cheapest sections: ST 40 "
       "and ST 43.",
    10: "Alice has three purchases: the Metallica pass ($2,500.95), Rush ($1,100.95) and a "
        "Kraken game. Her largest total is the Rush order. She has 3 payment cards on file.",
    11: "Cards on file before: Visa 4242 and Amex 1005. Added Mastercard 5555, removed the "
        "Visa, and the Amex is now the default.",
    12: "Created an account and bought the cheapest single ticket with mobile delivery. "
        "Order reference 41801399, final total $370.95. The order does not appear in history.",
    13: "The Kraken list 40 home games at Climate Pledge Arena. First: Vegas Golden Knights "
        "10-5 ($70). Last: Edmonton Oilers 3-13-2027 ($95).",
    14: "100 Level: 145, Row Y, $470; 200 Level: 230, Row R, $640; 300 Level: 305, Row DD, "
        "$360. The 100 Level is cheapest; the gap is $250; 27 total listings.",
    15: "The cheapest 4-ticket listing is 305, Row QQ at $270 per ticket. At quantity 2 the "
        "total is $542.95; at quantity 4 it is $1,082.95. The processing fee doubles with "
        "quantity.",
    16: "The three biggest discounts: 144 (now $431, was $583, saving $152), 239 ($449, was "
        "$659, saving $210) and CLB212 ($485, was $687, saving $202). The biggest is 144. "
        "The event has 31 listings.",
    17: "The nearby events have get-ins $1,140, $1,120, $1,090 and $720. The cheapest nearby "
        "get-in is the October 3 single night. The two-day pass get-in is $1,000.",
    18: "The catalog's first three events are Gnash, Kamelot and Beth Stelling. Page 2 starts "
        "with Serenade. There are 1,268 events with tickets. The earliest event's get-in is "
        "$110 and it has 2 listings.",
    19: "Bought a $75 concert-design gift card, code SHFIXTURE99. The Kraken have 40 upcoming "
        "home games; the next one is Vegas Golden Knights.",
    20: "Kraken: 45,000 followers, 42 events, next game Vegas Golden Knights at $70. "
        "Seahawks: 60,000 followers, 9 events, next game at $240. Sounders: 50,000 followers, "
        "6 events, next game at $20. The Seahawks have the most home events.",
}


# ---------------------------------------------------------------- honest passes
@pytest.mark.parametrize("n", ALL)
def test_honest_run_passes(tmp_path, n):
    run = honest_run(tmp_path, n)
    run_verifier(n, run, expect_pass=True)


# ---------------------------------------------------------------- no-op fails
@pytest.mark.parametrize("n", ALL)
def test_noop_run_fails(tmp_path, n):
    run = noop_run(tmp_path, n)
    run_verifier(n, run, expect_pass=False)


# ---------------------------------------------------------------- shortcut fails
@pytest.mark.parametrize("n", ALL)
def test_shortcut_run_fails(tmp_path, n):
    run = shortcut_run(tmp_path, n)
    run_verifier(n, run, expect_pass=False)


# ---------------------------------------------------------------- wrong answers
@pytest.mark.parametrize("n", ALL)
def test_wrong_answer_fails(tmp_path, n):
    run = wrong_answer_run(tmp_path, n, WRONG_ANSWERS[n])
    run_verifier(n, run, expect_pass=False)


# ---------------------------------------------------------------- state mismatch
@pytest.mark.parametrize("n", sorted(STATEFUL))
def test_state_mismatch_fails(tmp_path, n):
    run = state_mismatch_run(tmp_path, n)
    run_verifier(n, run, expect_pass=False)


# ---------------------------------------------------------------- read-only tamper
@pytest.mark.parametrize("n", sorted(READ_ONLY))
def test_read_only_tamper_fails(tmp_path, n):
    run = tampered_read_only_run(tmp_path, n)
    run_verifier(n, run, expect_pass=False)


# ---------------------------------------------------------------- package tampering
def _honest_steps(n):
    return SPECS[str(n)]["urls"]


def test_task_id_mismatch_fails(tmp_path):
    run = tmp_path / "wrongid"
    run.mkdir()
    b = RunBuilder(run, "StubHub--0")
    for i, u in enumerate(_honest_steps(0)):
        b.add_step("navigate" if i == 0 else "click", u)
    b.finish(SPECS["0"]["answer"])
    (run / "initial.db").write_bytes(acquire_seed().read_bytes())
    (run / "after.db").write_bytes(acquire_seed().read_bytes())
    run_verifier(1, run, expect_pass=False)  # verifier 1 sees a foreign task_id


def test_offsite_url_fails(tmp_path):
    run = tmp_path / "offsite"
    run.mkdir()
    b = RunBuilder(run, "StubHub--0")
    b.add_step("navigate", "https://example.com/seahawks")
    for i, u in enumerate(_honest_steps(0)[:2]):
        b.add_step("click", u)
    b.finish(SPECS["0"]["answer"])
    (run / "initial.db").write_bytes(acquire_seed().read_bytes())
    (run / "after.db").write_bytes(acquire_seed().read_bytes())
    run_verifier(0, run, expect_pass=False)


def test_missing_screenshot_fails(tmp_path):
    run = honest_run(tmp_path, 13)
    for shot in (run / "screenshots").glob("step_*.png"):
        shot.unlink()
        break
    run_verifier(13, run, expect_pass=False)


def test_undecodable_screenshot_fails(tmp_path):
    run = honest_run(tmp_path, 13)
    shot = sorted((run / "screenshots").glob("step_*.png"))[0]
    shot.write_bytes(b"\x89PNG\r\n\x1a\n" + b"garbage" * 40)
    run_verifier(13, run, expect_pass=False)


def test_not_done_trajectory_fails(tmp_path):
    n = 13
    s = SPECS[str(n)]
    run = tmp_path / "notdone"
    run.mkdir()
    b = RunBuilder(run, f"StubHub--{n}")
    for i, u in enumerate(s["urls"]):
        b.add_step("navigate" if i == 0 else "click", u)
    b.finish(s["answer"], terminated=False, reason="max_steps")
    (run / "initial.db").write_bytes(acquire_seed().read_bytes())
    (run / "after.db").write_bytes(acquire_seed().read_bytes())
    run_verifier(n, run, expect_pass=False)


def test_tampered_initial_db_fails(tmp_path):
    """A doctored 'initial' DB (not the frozen seed) must fail closed."""
    n = 3
    run = honest_run(tmp_path, n)
    tampered = copy_db(tmp_path, "initial.db")
    exec_sql(tampered, ["UPDATE performers SET followers = followers + 5 WHERE id = 1"])
    shutil.copyfile(tampered, run / "initial.db")
    run_verifier(n, run, expect_pass=False)


def test_extra_state_fails(tmp_path):
    """Stateful tasks must fail when an extra, unallowed row appears."""
    n = 3
    run = honest_run(tmp_path, n)
    after = run / "after.db"
    exec_sql(after, ["INSERT INTO favorites (user_id, performer_id, created_at) "
                     "VALUES (2, 527, '2026-09-26 12:00:00.000000')"])
    run_verifier(n, run, expect_pass=False)


# ---------------------------------------------------------------- tasks.jsonl contract
def test_tasks_jsonl_contract():
    lines = (Path(__file__).resolve().parents[2] / "tasks.jsonl").read_text().splitlines()
    assert len(lines) == 21
    for line in lines:
        row = json.loads(line)
        assert "answer" not in row, "no answer key may ever ship in tasks.jsonl"
        for key in ("web_name", "id", "ques", "web", "upstream_url"):
            assert key in row, f"missing contributor key {key}"
        assert "verifier_path" in row and row["verifier_path"] == f"sites/stubhub/verify/verify_{int(row["id"].rsplit("--")[1])}.py"
        assert "judge_rubric" in row and len(row["judge_rubric"]) > 80
        words = len(row["ques"].split())
        assert words <= 100, f"task {row['id']} has {words} words (>100 FAIL)"
        assert row["web"] == "http://localhost:40105/"


def test_task_definitions_have_stable_identity():
    rows = [json.loads(line) for line in (Path(__file__).resolve().parents[2] / "tasks.jsonl").read_text().splitlines()]
    assert [r["id"] for r in rows] == [f"StubHub--{i}" for i in range(21)]
    assert all(r["web_name"] == "StubHub" and r["upstream_url"] == "https://www.stubhub.com/" for r in rows)
