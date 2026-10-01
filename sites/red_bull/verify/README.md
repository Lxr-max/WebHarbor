# red_bull verifier contract

One deterministic verifier per task (`verify_0.py` … `verify_19.py`), shared
utilities in `verify_lib.py`, adversarial contract tests in
`test_verifiers.py`. Invoked through `agent_demo/eval_judge.py --verifier
True` or directly:

```bash
python3 sites/red_bull/verify/verify_<n>.py --run_dir RUNS/TASK_N \
        [--initial_db PATH] [--after_db PATH]
```

`RUNS/TASK_N` holds `trajectory.json` + `screenshots/step_NNN.png`; the two
SQLite snapshots default to `initial.db` / `after.db` inside the run dir
(fetched from the pinned container when absent). Output is
`{task_id, pass, reason, evidence[]}`; exit 0 on PASS, 1 on FAIL.

## Grading layers (all deterministic; no LLM call is load-bearing)

1. **Package identity** — task_id match, `terminated`/`agent_done`, non-empty
   final answer, every URL loopback on the mirror port, PNG screenshots.
2. **Seed identity** — the initial snapshot must BE the frozen in-image seed
   (counts + schema digest + rows digest; r2 re-freeze seed md5
   `652c2f0fade475e6905194c6700b9923`, image caliber, built from
   `orch/contribute/red_bull` @ 4f33f649).
3. **Navigation gates** — the on-site surfaces the task names (filters, tabs,
   product pages, shop/account flow) must appear in the trajectory; a correct
   answer from memory alone FAILs.
4. **Answer gates** — hardcoded ground truth per task (never in
   `tasks.jsonl`). The r1 honest-absence family (unrendered standfirst, A–Z
   letter, native-validation outcomes) is resolved by the fix round: event
   pages render the standfirst, the task names the first-name letter, and the
   registration form's server-side errors are reachable — the on-page values
   are now the graded truth; fabricated values FAIL.
5. **DB after-state** — read-only tasks must be row-identical to the seed;
   stateful tasks must show exactly the allowed delta (registrations, orders,
   cart, favorites) and nothing else.

## Honest fixtures

`fixtures/<n>/` (r2 review evidence tree) holds the reviewer's two-round
Playwright walks against the r2 review container (independent build from the
fix commit); per-task step counts were identical across rounds (20/20 at
least 15 honest atomic steps). The frozen constants in `verify_lib.py` were
cross-checked against the independently built r2 review image and the fix
container's measured image-caliber seed.

## Adversarial guarantees (`test_verifiers.py`)

Honest fixtures PASS; every negative FAILs: no-op trajectories, answer-only
shortcuts (navigation stripped), wrong answers per question point, stale-DB
runs (the claimed write undone), read-only violations, tampered packages
(wrong task id / off-site URL / cross-port URL / not terminated / empty
answer / pre-mutated seed / corrupt screenshot), and task-specific
confusions (wrong-event registration, wrong badge claim, swapped flavor
attribution, letter-A claim, wrong save-target outcome, era fabrication).
r2 sync: `tasks.jsonl` rows are byte-identical to the fix branch's five-key
rows plus the two contract keys (`verifier_path`, `judge_rubric`); no
`answer` key is ever added.
