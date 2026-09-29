# ziprecruiter task verifier contract (reviewer track)

Deterministic, LLM-free grading contract for the 20 `ZipRecruiter--N` tasks,
added by the review round on top of the contributor's five-key `tasks.jsonl`.
Re-frozen at r2 for the deepened tasks of contribution 4d57185b (seed md5
`4f1cd6ce…`, rows sha256 `81377dd9…`, schema `50093efd…` unchanged); ground
truths move with the moved question points and `verify_6/9/11/14/15/17` —
whose tasks' truths did not move — stay byte-identical to r1 except
`verify_11` (adds the nearby-job checks the r1 contract missed).

## Layout

- `verify_lib.py` — shared fail-closed checks: package identity (task_id,
  `terminated`/`agent_done`, non-empty answer, same loopback origin+port,
  decodable PNG screenshots), the frozen seed identity gate (schema sha256
  `50093efd…`, rows sha256 `81377dd9…`, 16-table row counts, file md5
  `4f1cd6ce…` — a run graded against a pre-mutated database fails here),
  navigation gates, answer token/number/phrase/ordered checks, and the
  SQLite after-state contract (read-only tasks must leave the seed
  row-identical; stateful tasks must produce exactly the allowed row delta).
- `verify_0.py` … `verify_19.py` — one verifier per task. Ground truth is
  HARDCODED here (never in `tasks.jsonl`), frozen from the reviewer's two
  independent Playwright rounds on the re-review container
  `wh-ziprecruiter-rereview` (fresh control-plane reset + fresh browser
  context per task; the two rounds produced identical per-task facts).
- `gen_verifiers.py` — emits `verify_N.py` from the frozen spec table
  (regenerate only when a task text changes; the checked-in files are the
  contract).
- `append_rubrics.py` — appends `verifier_path` + `judge_rubric` to
  `../tasks.jsonl`. The five contributor keys stay byte-identical (each
  output row is the original line with the two keys appended); no `answer`
  key is ever written. Idempotent.
- `extract_fixtures.py` — rebuilds `tests/fixtures_data.py` from the
  reviewer's honest live runs (trajectories + initial/after DB snapshots).
  The checked-in fixtures are the contract; re-extraction requires the
  review evidence dir.
- `tests/` — `test_verifiers.py` + `_support.py` + `fixtures_data.py`:
  per task the honest run MUST PASS and the no-op / knowledge-shortcut /
  wrong-answer / read-only-tamper / stale-state / package-tamper /
  task-confusion runs MUST FAIL. `python3 -m pytest
  sites/ziprecruiter/verify/tests -q` (needs the review container or
  `WH_ZIP_SEED_DB` pointing at the frozen seed DB).

## Verification signature

```
python3 sites/ziprecruiter/verify/verify_N.py --run_dir <dir> [--initial_db …]
                                        [--after_db …] [--container wh-ziprecruiter-rereview]
```

`<dir>` holds `trajectory.json` (agent_demo shape), `screenshots/step_NNN.png`
and (optionally) `initial.db` / `after.db`; without the snapshots the verifier
fetches the seed / live instance DB from the container. Output is a JSON
verdict on stdout; exit 0 on PASS, 1 on FAIL.

## Frozen environment notes (review round 1)

- The verifier seed fingerprint is frozen from the reviewer's independently
  built image (`webharbor:ziprecruiter-review`, from contribution
  `24261f74`): the review Containerfile replicates the exact real-Dockerfile
  ziprecruiter site block (asset inventory gate 308/308 + `PYTHONHASHSEED=0`
  seed build). Fresh-boot, in-image rebuild, per-task reset and
  dirty-write+reset all reproduce md5 `6d683074…` byte-identically.
- Review port block: the requested 46115/47115/48115 was occupied
  (wh-zara-fix), so the block shifted +3000 to **49115 (site) / 50115
  (control) / 51115 (site secondary)**; all three verified free via
  `ss -ltn` before bind.
- Known premise/navigation defects pinned by this contract (full list and
  severity in the review report):
  - T2: the listing's company (Matter Family Office) carries no industry
    and no headquarters in the seed, so those two asks resolve to "not
    shown" — the verifier pins everything that does resolve.
  - T3: the employment-type filter panel cannot combine two types in a
    real browser (the app reads only the first `et` query param); the
    combined count is reachable via the `et=part_time,per_diem` URL, which
    verify_3 requires. The first PT/combined listing shows no pay anywhere
    — the honest answer reports that.
  - T7/T8: the location-scoped company jobs page
    (`/co/<slug>/Jobs/-in-<City>,ST`) has no inbound link on the mirror.
  - T11/T12: the city salary variants (`/Salaries/<slug>-Salary-in-<City>,ST`)
    have no inbound link on the mirror.
  - T13: the seeded blog subcategory set does not match the article data,
    so Tips & Advice shows 0 articles (frozen as the honest count).
  - T16: no saved listing has a gastroenterology employer; the intended
    listing is the Manhattan Urology job at New York Health — the verifier
    pins that target and the honest answer reports the mismatch.
  - T10: the nearby job's company (Quick 2 Hire) carries no industry in
    the seed; the honest answer reports the absence.
- Fix rounds that move any of these truths must re-freeze the affected
  verifiers from fresh honest walks (zara-r2 / wanderlog-r3 precedent).

## Regression (review round 1)

- 97 contract tests passed: 20 honest fixtures PASS; 20 no-op, 20
  pure-answer shortcuts, 20 wrong-answer runs, 4 read-only tampers, 2
  stale-state runs, 7 package tampers and 4 task-confusion runs all FAIL
  (zero false positives).
- Site pytest (independent container run, CSRF enabled): 36/36.
