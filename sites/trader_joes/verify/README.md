# trader_joes — reviewer verifier contract (r2 re-freeze)

Review branch `orch/review/trader_joes` (reviewer contract only), on top of
the contributor's NEEDS-FIX fix `orch/contribute/trader_joes` @ `fb73dbfa`
(r1 review was `668a5ad7` over `bda7f0a7`), author raibows, not pushed.

## What is here

- `verify_lib.py` — deterministic verifier utilities: package identity gate
  (task_id / terminated=agent_done / non-empty answer / same-origin loopback
  URLs / decodable PNG screenshots), frozen-seed identity gate (14-table
  counts + schema sha256 + rows sha256; seed md5
  `34e1af0cc66a317223e889081c2381b4`, r2 caliber: two upstream-404 story
  artifacts removed — editorials 125→123 — and the recipes
  hours/minutesToCook2 time columns restored; local PYTHONHASHSEED=0
  rebuilds reproduce md5 `7f95c9e5ff2b7a3089e37b35b076d2f2`), navigation
  gates, answer gates (phrase / number / price / regex / any-of / ordered /
  zero-or-phrase), and the SQLite initial-vs-after diff engine (row added /
  removed / changed with template matching).
- `verify_0.py … verify_19.py` — one deterministic verifier per task. Ground
  truth is HARDCODED in each file, transcribed from the reviewer's two
  independent honest Playwright rounds on the independent r2 review container
  (`webharbor:tj-review-r2`, built from the real Dockerfile's trader_joes
  site block over the fix commit; port block 46137/47137/48137) and
  cross-checked against the frozen seed database. `tasks.jsonl` carries only
  `verifier_path` + `judge_rubric` (English pure-rule text; the seven
  re-anchored tasks' rubrics re-frozen reviewer-authored); the original five
  keys are byte-identical to `fb73dbfa` (13 untouched tasks' five keys are the
  byte prefix of the 7-key line as inherited from the fix) and no answer key
  exists anywhere in the task file.
- `test_verifiers.py` — 246 adversarial contract tests (pytest): every
  honest fixture PASSES (20), and every negative FAILs with zero false
  positives: no-op trajectories (20), answer-only shortcuts with correct
  answers but no navigation (20), fabricated wrong answers (20), stale-DB
  runs where the claimed delta was never written (18 stateful tasks),
  injected writes on read-only tasks (2), tampered packages (wrong task_id /
  off-site start_url / cross-port URL / unterminated / empty answer /
  pre-mutated seed — 120), and task-specific confusions (26): wrong list row
  removed, wrong signup email, wrong product set, wrong My Store, wrong
  subscriber, subscribe-without-unsubscribe, wrong added sku, wrong quantity
  change, wrong final rows, wrong description-product added (T9), un-removed
  spice (T12), wrong bisque quantity (T12), crispbread not removed (T13),
  missing quantity increase (T19), the artifact-story answer against the r2
  ground truth (T15), and the no-confirmation claim against the now-rendering
  unsubscribe confirmation (T5).

## Honest step-count table (reviewer's two r2 rounds, identical)

| Task | R1 | R2 | | Task | R1 | R2 |
|------|----|----|--|------|----|----|
| T0 | 18 | 18 | | T10 | 17 | 17 |
| T1 | 20 | 20 | | T11 | 15 | 15 |
| T2 | 18 | 18 | | T12 | 16 | 16 |
| T3 | 18 | 18 | | T13 | 17 | 17 |
| T4 | 15 | 15 | | T14 | 18 | 18 |
| T5 | 20 | 20 | | T15 | 16 | 16 |
| T6 | 17 | 17 | | T16 | 17 | 17 |
| T7 | 17 | 17 | | T17 | 18 | 18 |
| T8 | 16 | 16 | | T18 | 16 | 16 |
| T9 | 18 | 18 | | T19 | 16 | 16 |

min 15 / max 20 / total 343, per-task
`[18,20,18,18,15,20,17,17,16,18,17,15,16,17,18,16,17,18,16,16]`; the two
rounds agree exactly task-by-task with zero fact mismatches (program
comparison). All 20 tasks meet the 15-step depth standard.

Counting convention (pipeline precedent, same as umich/nyse/wanderlog):
atomic actions the task text genuinely requires — navigate(home), click,
fill, select, submit, browser back; reads never count; actions the task does
not require are never taken (anti-padding); hover-to-reveal a CSS dropdown
then clicking the revealed link counts as one click; login = click Log In +
2 fills + submit (4); signup = click Log In + click Create an account +
3 fills + submit (6); site search = fill + submit (2). Where a task says
"report the new list total" the honest walk opens the shopping list (the
header badge is a proxy); the contributor's walker read the badge, which is
the single 1-step T9 difference (17 vs 18 here) — both rounds of each
measurement agree internally and both clear the 15-step standard.

The 13 untouched tasks reproduce the reviewer's r1 counts exactly
(T0=18, T2=18, T3=18, T4=15, T5=20, T6=17, T7=17, T8=16, T10=17, T11=15,
T14=18, T15=16, T18=16). The seven re-anchored tasks: T9 14→18, T12 14→16,
T13 14→17, T16 14→17, T17 22→18 (registered-mark title now searches
directly), T19 13→16, T1 20→20 with the text now explicitly anchoring the
home What's-New rail.

## r1 blockers resolved by the fix (re-verified live by the reviewer)

- **Five sub-15 tasks deepened** with real cross-page question points (T9
  description-linked product + search + add; T12 bisque increase + spice
  removal with running totals; T13 Norwegian crispbread price/size; T16
  10-mile re-search; T19 Stories listing + newest story + quantity
  increase) — all measured ≥16 under the honest convention above.
- **T5 unsubscribe confirmation renders** — `subscribe.html` gained the
  `{% if removed %}` block; the confirmation text was verified live and the
  contract now requires it (claiming no confirmation FAILs).
- **T15 capture artifacts gone** — the two upstream-404 story slugs
  (`fall-products-2025`, `talkin-with-`) were removed from `stories.json`
  (-12 lines) and a capture-side `_is_404_capture` guard in `seed_lib.py`
  rejects any 404 capture; the newest story is the real "A Cider to Crow
  About" (2026-09-25). An answer still reporting "Oops!" FAILs.
- **What's New heading matches upstream** — the category template renders
  "What's New" (h1/title/breadcrumb tail) in the areNewProducts filter
  state; verified character-identical against the live upstream URL; normal
  categories unchanged.
- **T17 registered-mark title searches directly** — the task text now uses
  the real display name ("American Heritage® Cream Cheese with Chives &
  Onions") and the exact-phrase search returns the product as the single
  hit (22→18 steps, no retry).
- **T1 home-rail anchoring** — the task text explicitly says "Back on the
  home page, add … from its What's New rail".
- **Recipe time ranges restored** — `minutesToCook2/hoursToCook/hoursToCook2`
  recovered from the 544 original upstream captures (+1632/-0) and the
  rendered Time text verified character-identical against the live upstream
  for multi-hour ("55 mins - 1 h 10 mins", "7 h 35 mins - 11 h 45 mins"),
  short ("15 mins - 25 mins"), and all-zero (renders no value) cases; the
  T2/T11 ground truths re-transcribed accordingly.
- **provenance typos fixed** — Bob's My Store Boston - Back Bay (510), Dana's
  Charlotte - Piper Glen (742); the T5 ground truth follows the seed state.
- **Guides/Stories breadcrumbs** — the editorial listing pages render the
  "Home › Discover › Guides/Stories" breadcrumb (upstream caliber).

## Running

```bash
pytest verify/test_verifiers.py          # 246 tests, all green
python3 verify/verify_<n>.py --run_dir <dir>   # single run verdict (JSON)
```

Each honest fixture directory (`initial.db`, `after.db`,
`trajectory.json`, `screenshots/`) comes from the reviewer's independent
r2 container; a verifier run needs no network and no LLM.
