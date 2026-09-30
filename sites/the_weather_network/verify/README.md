# verify/ — deterministic grading contract for the_weather_network

Authored by the reviewer (branch `orch/review/the_weather_network`, on top of
the contribution `orch/contribute/the_weather_network` @ `51662c07`).

## Layout

- `verify_lib.py` — shared deterministic utilities: package identity (task_id,
  `agent_done`, same-origin URLs, decodable screenshots), navigation gates,
  answer token/phrase/number checks, and the frozen seed contract (schema +
  row digests + table counts). No LLM call is load-bearing.
- `verify_0.py … verify_19.py` — one verifier per task. Ground truth is
  HARDCODED inside these files (never in `tasks.jsonl`). Two free-choice tasks
  (1: Alberta ski first-snow, 10: Alberta golf best-day) resolve the location
  the agent actually opened from the trajectory and validate the reported
  (date, high) pair against that location's frozen `daily_forecasts` rows.
- `append_contract.py` — the script that appended `verifier_path` +
  `judge_rubric` to `tasks.jsonl` with byte-identical preservation of the five
  contributor keys.
- `tests/` — the contract test suite (`test_verifiers.py` + `_support.py` +
  `fixtures_data.py` + `gen_fixtures.py`). Fixtures are the reviewer's honest
  live Playwright walks frozen as agent_demo-shaped trajectories; after-state
  DBs are seed copies mutated through sqlite. No LLM.

## Frozen seed contract

The seed is a build output (`.build-generated-seed`): `PYTHONHASHSEED=0
python3 seed_data.py` inside the image. The raw SQLite file md5 is NOT
environment-stable (the build-time SQLite library version changes the physical
page layout — host sqlite 3.45.1 vs in-container 3.40.1 produce different
bytes), but the LOGICAL content is stable: the schema digest and the row
digest reproduce exactly across both environments. The contract freezes:

    SCHEMA_SHA256     = ed0420308c8724ee26bdb502407963fa6173754311cd15a884fbe0eab6e08748
    SEED_ROWS_SHA256  = 35cbe02ea07012b9199667bc16c69b5565f7bc5a69c5d27af78b05d73106b9b1
    SEED_COUNTS       = {alerts 51, articles 638, authors 42, daily_forecasts 8700,
                         hourly_forecasts 41760, locations 580, monthly_averages 23744,
                         observations 580, saved_locations 15, users 4, videos 782,
                         wellbeing 525}

## Running

```bash
# container must be running (default name wh-twn-review, override with WH_CONTAINER)
python3 verify_N.py --run_dir <agent run dir>          # uses <run_dir>/initial.db + after.db
python3 verify_N.py --run_dir <dir> --container NAME   # or fetches seed/instance from the container

# full contract suite (225 tests; needs pytest + a running review container)
python3 -m pytest tests -q
```

A run directory follows the `agent_demo/agent.py` shape: `trajectory.json`
plus `screenshots/step_NNN.png`. Output: JSON verdict on stdout, exit 0 on
PASS / 1 on FAIL.

## Contract semantics

- Read-only tasks (0–4, 6–13, 15–19): every table must be row-identical to the
  frozen seed after the run. The unit toggle (4) is session-only when signed
  out, so it stays read-only.
- Stateful tasks: 5 (bob: remove the odd saved location, add Whistler
  Blackcomb → exactly that delta, final count 4) and 14 (exactly one new user
  `weather_fan2026` + exactly three saved locations for it: Toronto, a ski
  resort, one more destination).
- Anti-shortcut: every task has navigation gates naming the pages the task
  requires; a correct answer without the navigation is a FAIL. No-op runs
  fail on every task. Package tampering (task_id mismatch, off-site URL,
  missing/undecodable screenshot, non-done trajectory, empty answer) fails
  closed.
- Known review finding: the °F toggle is a redirect-through URL
  (`/en/account/preferences?unit=imperial` bounces back to the referrer), so
  task 4's toggle is enforced via the imperial answer values (63°F / 16 mph)
  rather than a URL gate.

## Review verdict context

Delivered alongside a **NEEDS-FIX** review verdict: 15/20 tasks measure under
15 honest steps under the established step-counting standard
(NAV/FILL/SELECT/SMIT/SCAN/READ; scrolls are not steps), which the reviewer
measured by driving all 20 tasks through the live site. This contract grades
the CURRENT task set; when the contributor redesigns the shallow tasks, the
contract should be re-synced on the new 5-key prefix (see student_com r2
precedent).

## r2 re-sync (contribution @ 8af51be4)

Re-synced onto the deepened task set of the r2 fix commit `8af51be4`
(app.py link-rewrite + 15 deepened task texts, seed data byte-identical):

- `tasks.jsonl`: 5-key prefix byte-identical to `8af51be4`; new FACT
  CHECKPOINTS rubrics for the 15 deepened tasks (r1 rubrics kept verbatim for
  0/4/6/14/17); no answer key.
- `verify_1/2/3/5/7/8/9/10/11/12/13/15/16/18/19.py`: new answer gates per
  the frozen seed. verify_0/4/6/14/17 are byte-identical to the r1 contract.
- `verify_lib.py`: additive `check_answer_signed_number` (negative-value
  gates: -6/-3/-1) and `daily_rows` now also selects the page-visible
  combined `pop` column (the 7-day page renders `pop`, not `day_pop`).
- `tests/test_verifiers.py`: the 5-key-prefix baseline moved from `51662c07`
  to `8af51be4`. Fixtures regenerated from the reviewer's r2 honest live
  walks (container `wh-twn-rereview`, port block 46099/47099/48099).
- `adv_negatives_r2.py`: r2 adversarial negatives, including the case that
  the fix receipt's own recorded T7 7-day answer ("Sep 30, 60%") FAILS the
  correctly-gated verifier (frozen rows: Thursday, October 1 at 70% is the
  unique maximum) and that both Tue/Wed tie days PASS T19's
  highest-rain-day gate.
- Known tie handled by design: T19's "highest rain chance" day is a 60%/60%
  tie between Tue Sep 29 and Wed Sep 30 in the frozen rows — either day is
  accepted.

## r3 incremental re-sync (contribution @ 2d15effd)

The r3 fix commit `2d15effd` deepened only T3/T7 (`tasks.jsonl` 2 lines; all
other site files byte-identical). Incremental re-sync on top of `7572bdcf`:

- `tasks.jsonl`: 5-key prefix byte-identical to `2d15effd` (T3/T7 `ques`
  updated); T3/T7 FACT CHECKPOINTS rubrics extended to the new asked facts.
- `verify_3.py`: +4 gates — Patricia's top winds (345 km/h), Polo's 24-hour
  central pressure drop (88 mb), eye-footage author (Nathan Howes), publish
  date (Sep. 26, 2026). All r2 gates kept.
- `verify_7.py`: +3 gates — overnight low during the rain (14°C), Monday
  afternoon high after the rain (20°C), expected rain on the 7-day peak day
  (5-10 mm). All r2 gates kept (incl. the frozen truth Thursday, Oct. 1 at
  70% as the unique maximum).
- `tests/test_verifiers.py`: the 5-key-prefix baseline moved from
  `8af51be4` to `2d15effd` (the only by-design drift when overlaying the
  new tasks onto the r2 contract).
- `tests/fixtures_data.py`: SPECS[3]/[7] honest answers re-frozen from the
  reviewer's r3 honest live walks (container `wh-twn-rereview`, port block
  46099/47099/48099, reset + fresh context per task); WRONG_ANSWERS[3]/[7]
  rewritten for the new task shape.
- `adv_negatives_r3.py`: r3 adversarial negatives — one mutated fact per
  case against the new gates (B1–B7), the r2 receipt's wrong 7-day answer
  regression (B8), and honest controls (B9/B10) proving zero false
  positives.
- `live_noop_r3.py`: r3 live no-op twin (fresh seed cache `/tmp/twn_r3_seed.db`).
