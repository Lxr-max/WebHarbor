# university_of_michigan — grading contract (reviewer-authored, r2 re-freeze)

Reviewer branch `orch/review/university_of_michigan` (r2 re-freeze on top of
the contributor's fix commit `orch/contribute/university_of_michigan @
8fed65a6`; r1 contract was `fd6adbe1` over `06f64a79`). This directory holds
the deterministic verifier suite the reviewer re-froze after independently
re-verifying the fix round and walking every task twice on the r2 review
container `wh-umich-review-r2` (image `webharbor:umich-review-r2`, seed md5
`0492574f8c28ddc5b923294839d99cc0` — the r2 seed differs from the r1 seed by
exactly one `deadlines` row, the Financial-Aid first-row sentence restored
verbatim from upstream).

## Shape

* `verify_lib.py` — shared utilities:
  * **package identity** (fail-closed): task_id, `terminated` with
    `agent_done`, non-empty final answer, all URLs on the same loopback
    origin/port as `start_url` (`about:blank` tolerated), decodable PNG
    screenshots;
  * **seed identity** (fail-closed): the initial DB must be the frozen r2
    seed (19-table counts + schema digest + rows digest, md5 above);
  * **navigation gates** (anti knowledge-shortcut): each task's required
    on-site surfaces (search/filter URLs, detail pages, login, My U-M);
  * **answer gates**: phrase / number / price / regex / any-of checks with
    ground truth HARDCODED in the verifiers (never in tasks.jsonl);
  * **DB after-state**: read-only tasks must be row-identical to the seed;
    stateful tasks must show exactly the allowed row delta and **no row
    removals** in the touched table (the removal gate catches agents that
    toggle a seeded entry off while claiming the required add).
* `verify_0.py` … `verify_19.py` — one deterministic verifier per task;
  the r2 re-freeze re-transcribed the ground truth of the ten re-anchored
  tasks (T3/T4/T5/T7/T9/T10/T13/T14/T16/T17) from the reviewer's r2 honest
  rounds.
* `test_verifiers.py` — adversarial contract tests (pytest): honest
  fixtures PASS; no-op, answer-only shortcuts, wrong answers, stale DB,
  read-only violations, tampered packages and task-specific confusions all
  FAIL.

Ground truth was transcribed from the reviewer's two independent r2 honest
Playwright rounds (`walk_umich.py` r1/r2 — identical facts and step counts)
and cross-checked against the frozen r2 seed database.

## Grading rules worth knowing

* **Re-anchored seed-state conflicts** (r2): every "add" target is now
  outside all seeded Backpacks, so the expected end states are unique:
  * **T3** adds Alexander Stark's SECOND section (CHEM 125-200, class
    10712): honest delta +1 row for Alice, total **3**. Adding the first
    (seeded) section or toggling a seeded row off FAILs.
  * **T10** adds the ECON 102 first section (class 10942): honest delta +1
    row for Bob, total **3**.
  * **T16** adds-then-removes the STATS 250 first section (class 13492):
    the honest end state is row-identical to the seed, remainder **1
    class**; an un-removed add, a wrong-section flow or a removed seeded
    entry all leave a delta and FAIL.
  * **T17** stays the idempotent re-save (row-identical, total **2**).
* **T2 FAFSA** — the Aid page now carries the full upstream sentence
  ("Complete the Free Application for Federal Student Aid (FAFSA), as soon
  as available, …"), so the canonical answer **Oct. 1** is anchored on the
  named page; answering "March 1" (the FAFSA receipt deadline) still FAILs.
* **T9 bio count** — the task now says to clear the a-f tab back to a-z
  first, so the answer is uniquely **15** (the a-f-retained 10 FAILs).
* **T14 El Niño** — the task now uses the real spelling; the verifier's
  navigation gate accepts either URL encoding of "El Niño" and the answer
  must carry the ~40% figure.
* **T4 histotripsy** — re-anchored to the funding foundation named in the
  story body (a body fact, NOT visible in the search-result title).
* **T7/T13 deepening** — new cross-page question points: the LSA school
  page's course-subject count (**16**) and the MATH subject's course count
  (**87**).
* **T14/T19** — "open the first Backpack class" is graded on the class
  detail page being opened from My U-M (navigation gate), with the
  instructor/course-code facts read off that page.

## Honest step counts (reviewer's two identical r2 rounds)

```
T0  19   T1  22   T2  17   T3  19   T4  15
T5  24   T6  17   T7  16   T8  16   T9  22
T10 20   T11 18   T12 16   T13 16   T14 15
T15 22   T16 19   T17 19   T18 19   T19 16
```
(min 15 / max 24 / mean 18.4; identical to the contributor's declared
table; atomic actions only, reads free, login = open-login-page + fill +
fill + submit, in-page login links used where the action context provides
them — the same convention as the r1 walk and the nyse review rail.)

## Usage

```bash
python3 verify_<n>.py --run_dir <dir>            # dir with trajectory.json,
                                                 # screenshots/, initial.db, after.db
pytest test_verifiers.py                        # adversarial contract suite
```
