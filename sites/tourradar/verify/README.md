# tourradar — reviewer grading contract

Deterministic per-task verifiers for the 22 TourRadar tasks, authored by the
reviewer (grading contract). Ground truth is **hardcoded inside the
verifiers**; `tasks.jsonl` carries only `verifier_path` + `judge_rubric`
(no answer key).

## Layout
- `verify_lib.py` — shared utilities: trajectory loading/identity checks,
  navigation gates, answer token/amount matching, SQLite snapshot plumbing,
  the frozen seed contract (schema sha + table counts + rows sha), booking /
  wishlist / Q&A / review delta checks, the Judge harness and CLI plumbing.
- `verify_0.py` … `verify_21.py` — one verifier per task. Pure deterministic
  (no LLM calls): navigation gates + answer checks + DB after-state checks.
- `tests/` — pytest suite (`reviewed_fixtures.json` freezes the reviewer's
  honest live runs; `_support.py` builds agent_demo-shaped trajectories and
  seed-copy snapshots; `test_verifiers.py` asserts honest PASS + no-op /
  shortcut / wrong-answer / state-mismatch / read-only-mutation / off-site /
  tampered-task-id / no-op-with-pasted-answer all FAIL).

## Run
```bash
python3 -m pytest sites/tourradar/verify/tests -q          # 176 tests
python3 sites/tourradar/verify/verify_0.py --run_dir runs/0 # single verdict
```
The seed DB resolves from `$TOURRADAR_TEST_SEED_DB`, else
`sites/tourradar/instance_seed/tourradar.db`, else `docker cp` from
`$WH_CONTAINER` (default `wh-tourradar-review`).

## Frozen seed fingerprint
- schema sha256 `31fc91ccf2d7f37932a381db2f74f77b4437cb0fc24ac3ce23686b49d6d397fe`
- rows sha256 `5283855cd4341416a349fa31c51bf9eae1fbea94d1b4537047091605e637d90e`
- file md5 `12ac4632db0334d1bd50b4c8352bae1f` (byte-identical on every
  `PYTHONHASHSEED=0` build; verified twice in-image by the reviewer).
