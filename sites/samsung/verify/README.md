# samsung verify/ — reviewer grading contract (r2 re-freeze)

Reviewer-track deterministic contract for `orch/contribute/samsung` @
`fac9a96e` (the fix commit), re-frozen by the samsung reviewer on the
`orch/review/samsung` branch per the wanderlog / red_bull r2 precedent.
Every grading decision is offline regex / token / SQLite after-state; no LLM
call is load-bearing.

## Layout

- `verify_lib.py` — shared gates:
  1. **package identity** (fail-closed): task_id match, `terminated` +
     `agent_done`, non-empty final answer, every recorded URL on the same
     loopback origin and port as `start_url` (`about:blank` from the fresh
     tab is ignored), every referenced screenshot a decodable PNG;
  2. **seed identity gate** (fail-closed): the initial DB snapshot must BE
     the frozen in-image seed — file md5 `cc018b53658bfb13f07637892409287a`
     plus per-table counts, schema digest `e2b5780f…` and rows digest
     `8569b3b6…`. A run graded against a pre-mutated database fails here;
  3. **navigation gates**: the on-site surfaces the task names (catalogs
     with their filter/sort query strings, product and buy pages with the
     option selections in the URL, compare submissions, support/warranty,
     orders, account) must appear in the trajectory — a memory-recall
     shortcut with a correct answer fails;
  4. **answer claims**: per-task `(label, regex)` patterns against the
     normalized final answer, ground truth HARDCODED here (never in
     tasks.jsonl; no `answer` key exists anywhere);
  5. **forbidden patterns**: fabricated values for question points the
     rendered site does not carry (see honest-absence policy) fail the run;
  6. **DB after-state**: read-only tasks require every table row-identical
     to the seed; stateful tasks require the exact allowed row delta
     (wishlist add/remove, cart rows with model/qty/price, placed orders
     with subtotal/tax/total/payment, filed tickets with category/topic)
     and nothing else.
- `verify_0.py` … `verify_19.py` — one deterministic verifier per task
  (`SPEC` = paths + claims + forbidden + state). CLI:
  `python3 verify_<n>.py --run_dir <dir>` → JSON verdict, exit 0/1.
- `test_verifiers.py` — adversarial suite (123 cases): honest fixtures
  (the reviewer's r2 round-1 and round-2 Chromium runs, 40/40) must PASS;
  no-op, navigation-stripped, wrong-answer, fabricated-value, wrong-state,
  pre-mutated-seed, tampered-package and task-confusion mutations must
  FAIL, and two r2 render-fix regressions (stale r1 honest-absence
  trajectories for T4/T8) must FAIL (zero false positives).
- `contract_engine.py` + `contract.json` — the contributor's own offline
  contract, kept untouched (their pytest suite references it). The
  reviewer's independent findings about it are in the review report.

## Render-fix re-anchor policy (r2)

The two r1 grounding defects were fixed at the render layer by `fac9a96e`,
independently re-proven by the reviewer's r2 container and walks, so the r1
honest-absence gradings became POSITIVE anchors re-frozen from the r2 walks:

- **battery capacity on product pages** — the product-page template now
  renders the unlabeled Battery-group value row under its group heading;
  T4's `5000 mAh` is a page-visible positive claim. A stale r1-style
  "not stated" answer FAILS (pinned by the test suite's regression case).
- **Galaxy Compare multi-model selection** — the route now reads the full
  `models` parameter list (`getlist`), so a real form submission
  (`models=A&models=B`) renders every checked model as its own column;
  T8/T9/T19's per-model values are positive claims read from the rendered
  columns. Stale r1-style single-column answers FAIL (pinned by the T8
  regression case), and fabricated wrong values (e.g. a wrong battery
  number, the wrong heavier model) FAIL.

T19's heavier-model fact is corrected with the re-anchor: the rendered
two-column comparison shows the Galaxy S25 Ultra at 218 g outweighing the
Galaxy S26 Ultra at 214 g, so the claim is `galaxy s25 ultra`; the r1-era
contributor contract's `Galaxy S26 Ultra` expectation contradicted the data
(it was synthesized by the old test-client walker with the same broken
logic) and the wrong claim is now a forbidden pattern.

## Ground-truth provenance

Every hardcoded value was transcribed from the reviewer's two independent
honest r2 Chromium rounds against the fix container (audit rail: per-task
control-plane reset + fresh context; atomic click/fill/select/submit/back
actions only; reads recorded from the rendered DOM; screenshots +
initial/after DB snapshots archived per task in the review evidence tree),
and every walked fact was independently cross-checked against the frozen
seed database (45-fact DB cross-check, zero drift). The two r2 rounds'
per-task step counts are identical: `[19, 16, 19, 17, 18, 15, 19, 17, 16,
17, 16, 16, 17, 15, 18, 18, 16, 16, 18, 18]` (total 341, min 15 / max 19,
all tasks within the 15–20 depth band; the r1 depth blockers T6/T17/T18
are resolved by the deepened task texts).

The seed the contract pins is byte-identical to the in-image
`instance_seed/samsung.db` (md5 `cc018b53658bfb13f07637892409287a`),
reproduced independently by the reviewer's r2 review container build
(40-reset byte-identity re-proven, restart persistence included).
