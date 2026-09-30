# cars_com — reviewer grading contract

Deterministic per-task verifiers for the 19 cars_com tasks, authored by the
reviewer (grading contract). Ground truth is **hardcoded inside the
verifiers**; `tasks.jsonl` carries only `verifier_path` + `judge_rubric`
(no answer key).

## Layout
- `verify_lib.py` — shared utilities: trajectory loading/identity checks,
  navigation gates, answer token/price/count matching, SQLite snapshot
  plumbing, the frozen seed contract (schema sha + table counts + rows sha),
  saved-car / saved-search / offer-request / new-user checks, the Judge
  harness and CLI plumbing.
- `verify_0.py` … `verify_18.py` — one verifier per task. Pure deterministic
  (no LLM calls): navigation gates + answer checks + DB after-state checks.
- `tests/` — pytest suite (`reviewed_fixtures.json` freezes the reviewer's
  honest live runs; `_support.py` builds agent_demo-shaped trajectories and
  seed-copy snapshots; `test_verifiers.py` asserts honest PASS + no-op /
  shortcut / wrong-answer / state-mismatch / read-only-mutation / off-site /
  tampered-task-id all FAIL).

## Run
```bash
python3 -m pytest sites/cars_com/verify/tests -q        # contract tests
python3 sites/cars_com/verify/verify_0.py --run_dir runs/0  # single verdict
```
The seed DB resolves from `$CARS_COM_TEST_SEED_DB`, else
`sites/cars_com/instance_seed/cars_com.db`, else `docker cp` from
`$WH_CONTAINER` (default `wh-cars-com-review-r1`).

## Frozen seed fingerprint
- schema sha256 `29d2fcfc17ebe231321b203507e3939d8e67f655ba40fee59060c9e2a2ddec76`
- table counts: users 4, dealers 190, model_pages 23, compare_pairs 9,
  valuation_vehicles 8, listings 736, saved_cars 10, saved_searches 5,
  offer_requests 0
- rows sha256 `f04bba1affb80ec0bdc07c8fa7bd7cea0bd5e2b34473b9fc5e185c27afca4454`
- seed file md5 `140ef39cbf144d035e593016ea0d5e87` (byte-identical across two
  independent no-cache image builds; PYTHONHASHSEED=0 build-time seeding)

## Ground-truth caveat (filter-form fix)
The frozen SERP counts/prices assume the two review-track blocker fixes:
1. `_listing_filters` must skip empty values for `exterior_color_slugs`,
   `fuel_slugs`, `transmission_slugs`, `drivetrain_slugs` (the shipped form
   submission always ANDed `slug == ''` and returned 0 results).
2. The model/compare pages' "See all listings" links must emit `models[]`
   (the SERP sort/filter round-trip silently dropped the `models` filter).
The frozen values equal what the sort-form URL (which carries only non-empty
params) renders on the shipped build, i.e. the post-fix semantics.
