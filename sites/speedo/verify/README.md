# speedo verify/ — reviewer grading contract

Deterministic per-task verifiers for the 21 benchmark tasks in
`sites/speedo/tasks.jsonl`, authored by the reviewer (not the contributor).
Ground truth (order numbers, totals, product picks, wishlist/card deltas) is
HARDCODED in each `verify_N.py`; `tasks.jsonl` carries only
`verifier_path` + `judge_rubric` on top of the five contributor keys — there
is no answer key in the task file.

## Contract

Each verifier reads the run signature `(trajectory.json, screenshots/,
initial.db, after.db)` and emits a binary PASS/FAIL (exit 0/1, JSON verdict on
stdout):

1. **Package identity (fail-closed)** — task_id match, `terminated` +
   `agent_done`, non-empty final answer, every URL on the same loopback
   origin/port, every referenced screenshot a decodable PNG.
2. **Navigation gates** — the on-site surfaces the task names (quiz pages,
   facet-filtered collections, product pages, account pages, size guides,
   blog/FAQ, contact) MUST appear in the trajectory. A correct answer without
   the navigation is a memory-recall shortcut = FAIL.
3. **Answer checks** — phrase/number matching against frozen ground truth.
4. **DB after-state** — `initial.db` must be the frozen seed (schema + row
   digests); read-only tasks require the after-DB row-identical to the seed;
   stateful tasks require the exact allowed delta (one order + its items and
   the cart clear-down, a wishlist row swap, a contact case, a newsletter
   signup, a registered user, address/card/profile mutations) and every other
   table untouched.

## Frozen seed contract

`verify_lib.py` pins the seed built at image time (`PYTHONHASHSEED=0`, no
secondary indexes — byte-identical on every rebuild, md5 `5561ace9…`):
22 tables, `SEED_COUNTS`, `SCHEMA_SHA256`, `SEED_ROWS_SHA256`.

## Usage

```bash
# against a live run dir (initial/after DBs default to the run dir copies,
# falling back to the container seed / live instance):
python3 sites/speedo/verify/verify_0.py --run_dir runs/Speedo--0

# contract tests (no LLM, seed copy + sqlite mutations + synthetic trajectories):
python3 -m pytest sites/speedo/verify/tests -q
```

`append_rubrics.py` is the one-shot script that appended `verifier_path` +
`judge_rubric` to `tasks.jsonl` while keeping the five contributor keys
byte-identical; it is idempotent and kept for audit.
