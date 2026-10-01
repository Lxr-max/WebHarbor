# nyse — reviewer grading contract (r2 re-freeze)

This directory holds the deterministic grading contract for the nyse mirror's
20 benchmark tasks. It was authored by the **reviewer** (review branch
`orch/review/nyse`); the contributor ships only the site and the five
task-definition keys per row (`web_name, id, ques, web, upstream_url`).
After the reviewer's pass, each `tasks.jsonl` row additionally carries
`verifier_path` (this directory) and `judge_rubric` (English fact-checkpoint
rules for the LLM judge). Ground truth is **never** written to
`tasks.jsonl` — it lives only inside the verifiers below, hardcoded from the
reviewer's two independent honest Playwright rounds and cross-checked against
the frozen seed database.

**r2 re-freeze**: the r1 review (contract @ `51585a73`, contributor base
`2afd7911`, seed md5 `02e14921456e139d621e002775b8d413`) returned
NEEDS-FIX; the contributor fixed all 8 items on
`orch/contribute/nyse` @ `ab719484`. This re-freeze syncs the contract to
that state:

- the seed contract is re-frozen to the r2 mirror seed (md5
  `b7c3bbfa3a7a64b8d09b4e7fb3323fd9`; the IBM gap-fill re-capture adds 13
  `board_members` rows — 6841 → 6854 — and fills IBM's company facts in
  `quotes`, the only changed quote row; schema unchanged);
- every `tasks.jsonl` 5-key prefix is byte-identical to the fix branch
  (`ab719484`), and the five re-anchored rows (T0/T8/T9/T14/T19) carry new
  rubrics; the other fifteen rows keep their r1 contract keys byte-identical;
- `verify_0/8/9/14/19.py` are re-anchored to the r2 honest walks (see
  below); the other fifteen verifiers keep their r1 gates (their ground
  truth is untouched by the fix);
- fixtures are re-captured on the r2 review container
  (`webharbor:nyse-r2`, built from `ab719484` through the real Dockerfile's
  nyse site block: 326-asset inventory gate → deterministic
  `PYTHONHASHSEED=0` seed → instance_seed freeze → seed-database check);
  every fixture `initial.db` is byte-identical to the frozen r2 seed.

## Layout

- `verify_lib.py` — shared deterministic utilities: fail-closed package
  identity (task_id / terminated / same-origin loopback URLs / decodable PNG
  screenshots; `about:blank` tolerated as the pre-navigation placeholder),
  frozen-seed identity gate (table counts + schema digest + rows digest), URL
  navigation gates (anti knowledge-shortcut), answer token/phrase/number/price
  checks, and the SQLite after-state diff engine.
- `verify_0.py` … `verify_19.py` — one deterministic verifier per task
  (`NYSE--0` … `NYSE--19`). Output: JSON `{task_id, pass, reason, evidence[]}`
  on stdout, exit 0 on PASS / 1 on FAIL.
- `test_verifiers.py` — adversarial contract tests (pytest): every honest
  fixture PASSES and every adversarial negative FAILs — no-op trajectories,
  answer-only shortcuts with the navigation stripped, fabricated wrong
  answers, stale-DB (delta undone), read-only violations, tampered packages
  (wrong task_id / off-site start URL / cross-port step URLs / not terminated
  / empty answer / pre-mutated seed) and task-specific confusions (T8 NIO
  toggled OFF instead of adding KO, T7 deleting the wrong alert, T12 deleting
  the wrong alert, wrong page titles / tickers, and the r2 alert-leg
  confusions on T0/T14/T19 — wrong symbol, wrong direction, wrong
  threshold).

## Usage

```bash
python3 sites/nyse/verify/verify_7.py --run_dir runs/7 \
        [--initial_db PATH] [--after_db PATH] [--container wh-nyse-r2]
```

`--run_dir` must contain `trajectory.json` (+ `screenshots/step_NNN.png`);
`initial.db` / `after.db` default to the run dir and fall back to a
`docker cp` from `--container` (instance / instance_seed) when absent.

## Verifier guarantees per task

- **Identity + seed**: every verifier fails closed unless the package names
  the right task, terminated with `agent_done`, stayed on one loopback origin,
  has decodable screenshots, and was graded against the byte-frozen seed
  (`b7c3bbfa3a7a64b8d09b4e7fb3323fd9`; counts/schema/rows digests inside
  `verify_lib.py`).
- **Navigation gates**: each verifier pins the on-site surfaces the task text
  names (directory tab + query URLs, quote pages with the required
  `zoom=`/`exp=` parameters, bell-calendar `type=`/`from=`/`to=`/`page=`
  filters, IPO-center `window=`/`status=`/`exchange=` filters, `/login`,
  `/watchlist`, `/alerts`). A correct answer with no matching navigation is a
  memory-recall shortcut and FAILs.
- **DB after-state**: stateful tasks must produce exactly the allowed row
  delta and nothing else (`users`/`watch_items`/`price_alerts` row templates
  inside each verifier); read-only tasks must leave every table
  row-identical to the seed. Task 7's honest end state is row-identical to
  the seed (the created alert is the deleted one — deleting the wrong alert
  leaves a delta and FAILs).
- **Answers**: token/phrase/number/price membership against hardcoded ground
  truth; several date and price legs accept the on-page rendering and common
  equivalents (e.g. `2026/09/29` / `2026-09-29`).

## Task-specific grading notes (r2)

- **NYSE--0 / NYSE--14 / NYSE--19** (deepened legs): each now ends with a
  real cross-page compound leg — back to the quote page from the watchlist,
  a price-alert creation with the task's direction/threshold/note, and a
  report of the new alert's status plus the account's alert total. The
  verifiers pin the exact `price_alerts` row template (symbol / direction /
  threshold / note) and the account totals (Alice 2 on T0/T14, Carol 1 on
  T19); wrong symbol / direction / threshold FAIL.
- **NYSE--8** (add Coca-Cola to Dana's watchlist): re-anchored from the r1
  "add NIO" instruction, which collided with Dana's seeded watchlist (the
  toggle showed Remove and two honest executions answered differently). KO
  is NOT in Dana's seeded watchlist (SPY/NIO/AMC), so the honest execution
  clicks Add and the final total is uniquely 4 (SPY/NIO/AMC/KO). The
  verifier requires exactly one added `watch_items` row (dana/KO) and the
  total 4; an agent that toggles a seeded symbol off instead leaves a
  removal delta and FAILs.
- **NYSE--9** (BABA 52-week low): re-anchored from the r1 "board member
  count" question (whose honest answer was 0 / missing-is-answer). The
  verifier now requires BABA's 52-week low as rendered on the quote page.
- **NYSE--14** (IBM company facts + board): the fix round gap-fills IBM's
  capture (CEO Arvind Krishna, sector Technology, 13 directors — matching
  the live upstream payload byte-for-byte), so the task reports them; the
  verifier pins all of them plus the r2 alert leg below 200.
- **NYSE--19** (AERO re-anchor): the r1 "CEO" question (honest answer N/A as
  the upstream API reports) is replaced by AERO's 52-week low and the lowest
  strike of the second options expiry tab, plus the r2 alert leg above 16.
- **NYSE--2 / NYSE--13** (bell titles): the upstream feed stores numeric
  HTML entities; the r1 mirror rendered them literally, the r2 fix decodes
  them at render time (`plain_title()` + `html.unescape`) exactly like the
  live pages (`… Rings The Closing Bell®`). Title checks match the
  human-readable part (`… Rings The Opening Bell`) so `®`, `&#0174;` and
  bare forms all pass.

## Honesty provenance

All hardcoded ground truth was transcribed from the reviewer's honest
anti-padding walks (reads don't count; only actions the task text requires;
two independent rounds, identical step counts and facts — r2: both rounds
362 total, min 15 / max 22, all twenty tasks ≥15 honest atomic steps), then
cross-checked against the frozen seed database query-by-query. The walk
scripts, the per-task trajectories, the fixture databases and the full
evidence trail live in the review evidence directory (outside the repo).
