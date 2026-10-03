# thumbtack — deterministic verifier contract (review track)

Branch: `orch/review/thumbtack` (reviewer: raibows). Review container:
`wh-tt-review` (image `webharbor:tt-review`, built from the contributor tree
at `371b81fa`), site `127.0.0.1:46100 -> 40099`, control `127.0.0.1:47100 ->
8101`, secondary site port `48100`. Deterministic seed md5
`0c1320fd…` (instance == instance_seed, byte-identical on rebuild).

## Layout

- `verify_lib.py` — shared fail-closed checks: trajectory identity (task_id,
  `agent_done`, non-empty answer, same loopback origin+port, decodable
  step-referenced PNGs), navigation gates, answer token/phrase/number checks
  against ground truth hardcoded in each verifier, key-aware SQLite
  add/remove/update delta checks, frozen seed-count contract.
- `verify_0.py` … `verify_19.py` — one deterministic verifier per task.
  Ground truth is frozen from the reviewer's independent honest Chromium
  walks (2026-09-27); quote amounts are the app's det_hash(project_id=6,
  service_pk) values, cross-checked against the live container.
- `append_rubrics.py` — the one-shot writer that appended `verifier_path` +
  `judge_rubric` to `tasks.jsonl` (original five keys byte-identical, no
  answer key; judge rubrics are English rule-style).
- `tests/` — pytest contract suite (242 tests): honest runs PASS; no-op,
  knowledge-shortcut, wrong-answer, state-mismatch, wrong-delta,
  read-only-mutation, and package-tampering runs all FAIL; seed contract and
  tasks.jsonl key contract asserted. No LLM.

## Usage

```bash
# against a run dir (agent_demo trajectory + screenshots + initial/after DBs)
python3 sites/thumbtack/verify/verify_7.py --run_dir runs/07

# against the live review container (DBs fetched via docker cp)
python3 sites/thumbtack/verify/verify_7.py --run_dir runs/07 --container wh-tt-review

# contract suite
python3 -m pytest sites/thumbtack/verify/tests -q
```

Output: JSON `{task_id, pass, reason, evidence[]}`; exit 0 on PASS, 1 on FAIL.

## State contract per task

Read-only (after-DB must equal the seed): tasks 2, 11.
Stateful (exact allowed delta): all other tasks — new project id 6 + 5
deterministic matches (quote amounts frozen per category), saved_pros
add/remove, review row (rating 5, body tokens), thread + user/pro message
pair with the deterministic keyword reply, registered user with bcrypt hash,
project status transitions (matched -> hired -> completed / cancelled),
profile zip/address update.

## Notes

- The mid-walk quote amounts are deterministic per project id: after a reset
  the identical wizard input reproduces the identical quotes; project ids
  advance within a live DB (verified live: same input after reset -> same
  quotes; without reset -> next project id).
- The Kirkland city page (`/wa/kirkland`) is reachable only by URL inference
  (footer city pattern); recorded as a discoverability note in the review
  report, task 15 still verifiable via the navigation gate on `/wa/kirkland`.


Reviewer continuation (PRs 252–254): tasks and verifiers are maintained together.
The former generation scripts must not be used to overwrite the reviewed contract.
The current tests reconstruct synthetic states from final browser regression deltas;
they are unit tests, not additional browser runs. Numeric checks accept equivalent
decimal forms and selected comparisons bind values to subjects. These deterministic
checks cover finite language patterns, not arbitrary semantic equivalence.
