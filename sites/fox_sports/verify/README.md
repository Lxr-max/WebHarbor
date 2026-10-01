# fox_sports — reviewer grading contract (r2 re-sync)

Reviewer-authored deterministic grading contract for the 20 `tasks.jsonl`
tasks of the `fox_sports` mirror. r1 review: contribution
`orch/contribute/fox_sports` @ `9e2c081d`, contract branch
`orch/review/fox_sports` @ `7a5b2fc9` (NEEDS-FIX). This r2 re-sync lands on
the fix commit `7249daad` (13 tasks deepened to >=15 honest atomic steps,
Team Leaders (label, side) alignment + both-side leaders data, provenance
source_hosts) and re-measures ALL ground truth from scratch against the
rebuilt container: new seed identity, new navigation gates, new claims for
every deepened question point, exact new state deltas, and the corrected
T14 ground truth (the r1 fixture had mis-picked Q3's "home" side —
chicago-bears is Q3's AWAY team; the honest home pick is tennessee-titans,
grading 3/6 with Q3/Q5/Q6 missed). The two appended `tasks.jsonl` keys are
the reviewer's work; the original 5-key prefix is byte-identical to the fix
branch's rows and no answer key exists (one exception:
`tests/test_contract.py::test_tasks_jsonl_contract` asserts the
post-review 7-key row per CONTRIBUTING.md "Reviewer role").

## Layout

- `verify_lib.py` — deterministic utilities: seed-identity gate, SQLite
  row-digest helpers, answer normalization, Super 6 helpers.
- `contract.json` — per-task ground truth, HARDCODED here and never in
  `tasks.jsonl`: navigation gates, scoped answer claims, exact DB deltas,
  dynamic answer-state bindings.
- `contract_engine.py` — the fail-closed verifier engine.
- `verify_<n>.py` (× 20) — one thin entry point per task; prints
  `{task_id, pass, reason, evidence[]}` and exits 0/1.
- `test_verifiers.py` — adversarial pytest suite (honest fixtures from two
  independent walkthrough rounds must PASS; no-op, answer-only shortcut,
  wrong-answer, stale-DB, rogue-write, Super 6 forgery and tamper packages
  must all FAIL).
- `append_rubrics.py` — attached `verifier_path` + `judge_rubric` to
  `tasks.jsonl` (original 5-key prefix byte-identical; rubrics are pure
  English rules with no ground-truth values).

## Ground-truth provenance

Every fact in `contract.json` was transcribed from the reviewer's two
independent honest Playwright walkthrough rounds of the r2 review container
(`wh-fox-review-r2`, image `webharbor:fox-review-r2`, built from the fix
commit `7249daad` + the re-staged tarball `fd7bb6a7…`, review port block
46123/47123/48123, site port 40130). The two rounds produced identical
per-task atomic step counts and identical facts (40 trajectories, 0 JS
errors, all 20 tasks >= 15 honest atomic steps: 15/16/16/16/19/19/19/17/
16/15/18/16/17 for the deepened set), and all 330 walk-fact comparisons
were cross-checked against the frozen r2 seed database
(`db_crosscheck_r2.py`, 0 mismatches) before hardcoding — the wanderlog-r2
anti-transcription-error precedent. The Team Leaders fix itself was
verified independently of the contributor's parser: an upstream-capture
cross-check (`r2_leaders_crosscheck.py`) re-parsed all 46 leader-bearing
boxscore captures from the raw HTML and found every (label, side, player,
value) pair exactly matching the committed data, with the away/home label
sets equal for every game.

## Frozen seed identity

The seed rebuilt inside the pinned r2 image (PYTHONHASHSEED=0, canonical
schema-order rebuild) is sha256
`4d157dd2b72bd729c15d57c7af4f9caf0324db688221f2152edca3155ae95baa`
(md5 `3c9809d0a3db203d45aa0f768c24d7ca`, rows digest `25499c92…`). The
reviewer reproduced it independently (three byte-identical in-image
rebuilds) and verified the contributor's host-toolchain seed
(sha256 `a1551ec2…`, SQLite 3.45.1 vs the image's 3.40.1; the tarball
member) is content-identical: same schema objects, all 20 tables
row-identical. Control-plane resets restore the instance byte-identically
(verified through a real UI dirty write with CSRF enabled).

## State contract

All 20 fox_sports tasks are stateful. Each allows exactly its measured
delta and nothing else: favorite writes for the named benchmark accounts,
the new account rows for the signup tasks (bcrypt hashes are matched by
pattern; every other column is pinned), and the Super 6 entry updates.
Every graded Super 6 entry must satisfy score == matches(picks, correct)
(the app computes this at submit time; a forged score fails). Task
FOX Sports--13 is pick-agnostic: the agent picks its own winners, and the
reported graded score must match the score saved in its own entry row.

## r1 premise defect — RESOLVED by the fix (r2 verified)

FOX Sports--1 asks for "the passing-yards leader for each side" of the
Chiefs-Raiders boxscore. The r1 page rendered the away PASS YARDS leader
(Patrick Mahomes 812) with no home-side passing leader (the home cell
showed the away rush leader, Kenneth Walker III 360). The `7249daad` fix
regenerated the leaders data for all 46 leader-bearing games from the
upstream captures and aligned the table by (label, side); the r2 container
renders `Patrick Mahomes 812 | PASS YARDS | Kirk Cousins 661`, and the
contract now requires BOTH side leaders (claims: away Mahomes 812, home
Cousins 661). The (label, side) invariant was independently re-verified
across all 46 games plus a 3-league rendered-vs-upstream sampling.
