# stanford_university — reviewer grading contract

Review branch `orch/review/stanford_university`. This directory holds the
reviewer-authored grading contract.

- **r1 contract** (43eef816): reviewer grading contract for the contribution
  `orch/contribute/stanford_university` @ fc3db033.
- **r2 sync** (this commit): adopts the NEEDS-FIX round
  `orch/contribute/stanford_university` @ 77e3fa7e (all 9 blockers of the r1
  review fixed: exact career filter, bio-covering faculty search, Tanner
  library re-capture + duplicate merge, deepened tasks, de-leaked T16,
  upstream-verbatim hero, corrected provenance counts/seed hash) and
  re-freezes the contract from the reviewer's two independent honest
  Playwright rounds on the r2 review container
  (`wh-stanford-r2`, ports 46133/47133/48133, image built from 77e3fa7e via
  the real Dockerfile: 691-asset inventory gate → `PYTHONHASHSEED=0` seed
  build → instance_seed freeze → seed-database check).

## What lives here

- `verify_lib.py` — deterministic verifier utilities (package identity,
  frozen-seed gate, navigation gates, answer token/phrase/number/range/price
  checks, SQLite after-state diff engine). Seed contract re-frozen at r2:
  sha256 `65c57cd498ee5b4af55a81ee07dd15c131e5d2b94252cfb5ffdddab13aa71dd1`,
  md5 `c44be3f0be7aafde9e627bf408e6dc49`, libraries table 30 → 29 (the
  duplicate empty philosophy roster row is merged into the re-captured
  Tanner record), byte-identical across in-container rebuilds including
  `PYTHONHASHSEED=random`.
- `verify_0.py` … `verify_19.py` — one verifier per task. Ground truth is
  HARDCODED inside each verifier (never in `tasks.jsonl`), frozen from the
  reviewer's two identical r2 honest rounds (every hardcoded fact
  cross-checked against the frozen seed database). Re-frozen at r2 for the
  fix-affected tasks (0, 1, 2, 3, 5, 6, 7, 8, 11, 16, 17); the remaining
  verifiers keep their r1 ground truths (unchanged facts, re-verified on the
  r2 fixtures).
- `test_verifiers.py` — adversarial contract suite (232 tests, all green):
  40 honest fixtures (both r2 walk rounds) PASS; no-op / answer-only /
  wrong-answer / stale-DB / read-only-violation / tampered-package /
  task-confusion negatives all FAIL (zero false positives). Confusion
  guards updated for the fixes: the r1 substring-filter counts (77/12) and
  first row (EE101A) now FAIL their tasks; the r1 CHEM+FR=0 anchor is
  replaced by Mathematics+FR=28; a wrong Tanner location FAILs T11.

`tasks.jsonl` carries the 7-key contract: the original five keys plus
`verifier_path` (byte-identical to the r1 contract) and `judge_rubric`
(re-frozen by the fix against the deepened question points; the reviewer
verified every rubric against the task texts and the r2 ground truth — no
drift found). There is no `answer` key anywhere.

## Grading gates (per task)

1. **Package identity** — `task_id` match, `terminated`/`agent_done`,
   non-empty final answer, every URL on the same loopback origin+port,
   referenced screenshots decode as PNG.
2. **Seed identity** — initial DB must be the frozen r2 seed (12-table
   counts, schema digest, rows digest).
3. **Navigation gates** — the on-site surfaces the task names must appear in
   the trajectory (filters, detail pages, login, planner, saved events).
   T3 accepts either the bio-covering ADL search or the Aeronautics &
   Astronautics roster browse as the ADL-leader route.
4. **Answer checks** — hardcoded ground truth from the two honest rounds.
5. **DB after-state** — read-only tasks end row-identical to the seed;
   stateful tasks end with exactly the allowed delta. T17's honest end
   state is row-identical (CS103 added then removed); any leftover row
   FAILs. T18's third save is the first row of `/events?q=seminar`
   (eid 53870497268780).

## Honest step counts (two identical r2 rounds, reviewer's convention)

navigate(home)=1, click/select/fill/submit/back=1 each; reads don't count;
login = affordance click + 2 fills + submit; no action the task text does
not require.

| task | steps | task | steps |
|---|---|---|---|
| 0 | 18 | 10 | 15 |
| 1 | 15 | 11 | 15 |
| 2 | 15 | 12 | 17 |
| 3 | 16 | 13 | 21 |
| 4 | 15 | 14 | 17 |
| 5 | 16 | 15 | 19 |
| 6 | 16 | 16 | 18 |
| 7 | 17 | 17 | 19 |
| 8 | 17 | 18 | 19 |
| 9 | 18 | 19 | 16 |

min 15 / max 21 / mean 16.9 — **no task below the 15-step floor**. The fix
branch's claimed table matches 19/20 (T6: reviewer counts 16 vs the claim's
15; facts identical — recorded as a single ±1 calibration difference, both
readings clear the floor).

## r1 → r2 truth movement (what changed and why)

| task | r1 ground truth | r2 ground truth | fix |
|---|---|---|---|
| 0 | CS+Graduate 77 (substring leak) | 40 (exact career match) | app.py career `==` |
| 1 | 14 steps, no MS question | 15 steps, MSE MS program 2 requirement groups | task deepened |
| 2 | EE count 12, first EE101A, CHEM+FR 0 | EE count 6, first EE214B, MATH+FR 28 | career fix + re-anchor |
| 3 | ADL search dead-end, browse fallback (19 steps) | ADL search 1 hit Juan Alonso (16 steps) | faculty search covers bio |
| 5 | 13 steps | 16 steps, CS PhD 135 + CS MS 8 req groups | task deepened |
| 6 | 11 steps | 16 steps, 4-segment news chain | task deepened |
| 7 | 14 steps | 17 steps, On Campus topic + Student Experience count | task deepened |
| 8 | 12 steps, "first upcoming" ambiguous | 17 steps, upcoming+seminar 91 first 2026-10-01 + concert 36/address | task deepened, ambiguity gone |
| 11 | philosophy library: no location shown | Tanner location "Main Quad, first floor of Building 90, Room 91F" | Tanner re-captured, duplicate merged |
| 16 | 14 steps, title/date leak from homepage card | 18 steps, featured unit + main topic (detail-only facts) + classics search | de-leak + deepened |
| 17 | 14 steps | 19 steps, FR+CS+Winter cascade (8, CS103) | task deepened |

## Run

```bash
python3 sites/stanford_university/verify/verify_0.py \
    --run_dir <trajectory dir with trajectory.json + initial.db + after.db>
python3 -m pytest sites/stanford_university/verify/test_verifiers.py -q
```
