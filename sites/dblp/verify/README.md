# dblp verifier suite (reviewer contract, r2-fix sync + r3 repairs)

Deterministic, LLM-free verifiers for the 20 `dblp--*` benchmark tasks.
Originally written by the dblp reviewer on `orch/review/dblp` @ `8348a8c2`
(from `orch/contribute/dblp` @ `8cdd14e1`); synced onto the contribution
branch by the r2 fix, which re-froze the verifiers for the 14 rewritten
tasks (1, 2, 3, 4, 5, 6, 7, 10, 13, 14, 15, 16, 17, 18) from the
contributor's two honest Playwright rounds on the fix container
`wh-dblp-fix` (image `webharbor:dblp-fix`, built from the fixed worktree;
seed identity unchanged — see below). The six untouched verifiers (0, 8, 9,
11, 12, 19) stay byte-identical to the reviewer's frozen contract. The
review branch itself is untouched for the re-reviewer to unify.

The r3 fix then repairs, per the r2 review's NEEDS-FIX list: (A) the
mirror's search-history dedup — a kind page reached from the combined
results page for the same query is the same search action and is not
recorded twice, while every other search action records (the r2 code's
consecutive-duplicate swallow broke t12 for honest agents); (B) verify_1 /
verify_3 / verify_4 / verify_17 are re-anchored to exactly the values the
task texts ask the agent to report (the honest-minimal answer set; the
reviewer's independent Round-A facts confirm every anchored value); (C)
verify_17's near-context check uses the natural venue phrase ("ACL"), not
its own fact key; (D) the two judge rubrics that contradicted their task
texts (t1 'jiawei$', t18 VLDB Endowment removal) are synced; (E) the
re-frozen verifier docstrings state the seed-identity convention below
instead of a stale file-level md5 claim; (F) the cross-port negative in
`test_verifiers.py` derives the port from the fixture's start_url (+1000)
instead of hardcoding 49121. The six frozen tasks' honest fixtures are
re-walked on the r3 fix container (their r1-code fixtures predated the
history-recording change and masked the t12 break).

Ground truth is **hardcoded** in each `verify_<n>.py` — for the re-frozen
tasks it is injected programmatically from the fix-walk facts
(`gen_verifiers_fix.py`), ruling out transcription errors.

Honest-walk facts live in
`/data/zhaoyang-user-projects/websyn/wh-dblp-fix-evidence/runs/<n>/`
(`trajectory.json` + `facts.json` + `screenshots/` + `initial.db` +
`after.db`) for the re-frozen tasks, and in
`/data/zhaoyang-user-projects/websyn/wh-dblp-fix-r3-evidence/runs/<n>/`
for the six frozen tasks (re-walked on the r3 fix container with the
repaired history recording; the r1-era fixtures under
`wh-dblp-review-evidence/runs/` predate the history change and are kept
only as archive). Both rounds of every re-frozen walk produced
identical step counts and identical facts.

## Seed identity

The frozen seed-identity gate (table counts + schema sha256 + rows sha256)
is unchanged and passes: the r2 fix touches no seed data or seed-builder
logic. Note the raw seed FILE md5 is informational only
(`SEED_FILE_MD5` in `verify_lib.py` is not enforced by
`check_seed_contract`, which pins counts/schema/rows digests): the seed
build is not file-level deterministic across rebuilds — the reviewer's own
image, rebuilt from its own untouched code, flips between several
byte-layouts (e42b5b29… / b087143a… / bc846c… / b06767b4…) that all carry
byte-identical schema and table rows. The r2 fix image reproduces the same
schema and all-tables-identical rows (verified against the review image's
seed), and control-plane resets keep instance == instance_seed
byte-identically.

## Mirror UI facts the contract encodes

The kind search pages (publication / author / venue) submit the header
search box back to their own kind, exactly like upstream dblp.org; every
other page submits to the combined search. A kind search reached from the
combined page costs the section's "all N matches" click; navigation gates
accept either surface (`/search?q=…` or `/search/<kind>?q=…`). Search
history records one entry per search action: a kind page reached from the
combined results page for the same query (the "all N matches" chain) is
the same search and is not recorded twice; every other search action
records its own row — including a fresh search whose text coincides with
an earlier history row (the r3 repair; the r2 code swallowed any
consecutive same-(query, kind) row, which broke t12 for honest agents
whose seed history ended on 'fuzzing'). Records show the DOI only inside
the electronic-edition
link for several task anchors (upstream shows no `doi` field for them), so
the affected task texts ask for "the DOI in its electronic edition link"
(t2/t5/t16/t17) or drop the DOI ask (t4/t10, whose records have no
doi.org link at all); the verifier anchors the parsed ee DOI.

## Layout

- `verify_lib.py` — shared contract: package identity (task_id / agent_done /
  non-empty answer / same-origin same-port / decodable PNGs), seed identity
  gate (table counts + schema sha256 + rows sha256 pinning the in-image seed),
  navigation gates, answer phrase/number/near-context/ordered checks, a
  step-action gate (download steps), and read-only / exact-delta DB
  after-state checks.
- `verify_0.py` … `verify_19.py` — one verifier per task: navigation gates +
  hardcoded ground truth + DB contract.
- `test_verifiers.py` — 115 pytest cases: 20 honest fixtures PASS (14 from
  the fix walks, 6 reviewer-frozen); no-op, answer-only shortcut,
  wrong-answer, stale-DB, read-only-violation, tampered-package (wrong task
  id / off-site URL / cross-port / not-terminated / empty answer / bad PNG /
  pre-mutated seed) and task-confusion negatives all FAIL (zero false
  positives). Together with the site's own suite (48 tests, CSRF enabled):
  163 passed.

## Usage

```bash
python3 sites/dblp/verify/verify_2.py --run_dir <trajectory_dir>
#   [--initial_db P] [--after_db P] [--container wh-dblp-fix]
# prints {"task_id": ..., "pass": true/false, "reason": ..., "evidence": [...]}
```

`<trajectory_dir>` holds `trajectory.json` + `screenshots/step_*.png` +
`initial.db` + `after.db` (the agent_demo run shape). If the DB files are
absent they are `docker cp`-ed from the running fix container
(`wh-dblp-fix`, mirror port 49121).

## Task / contract map

| task | kind | honest steps | DB contract |
|---|---|---|---|
| 0 | search semantics marathon | 15 | read-only (frozen) |
| 1 | author chain, homonyms, exact-word author search | 15 | read-only |
| 2 | combined + SIGMOD venue chain + year filter | 15 | read-only |
| 3 | conference browse + NeurIPS chain + facets | 15 | read-only |
| 4 | journal browse + PVLDB chain + VLDB Journal | 15 | read-only |
| 5 | venue search, explicit per-venue counts | 18 | read-only |
| 6 | oldest-year facet + record + bib + type facet | 15 | read-only |
| 7 | OR/exact/type/year search chain + pagination | 16 | read-only |
| 8 | register + collection + export | 26 | +1 user, +1 saved paper, history (frozen) |
| 9 | watchlist add/remove (alice) | 17 | ±watch rows, -1 venue, history (frozen) |
| 10 | venue watch (bob) | 18 | +1 venue watch, history |
| 11 | saved searches (dana) | 18 | ±saved search, +1 paper, history (frozen) |
| 12 | collections + export (carol) | 21 | +1 saved paper, history (frozen) |
| 13 | search history (dana, cleared-first redesign) | 21 | history cleared → 4 rows |
| 14 | profile edit (alice) | 16 | user row update only |
| 15 | Guoliang Li chain | 15 | read-only |
| 16 | stats + SIGMOD 2022/2021 chain | 15 | read-only |
| 17 | year-filtered search chains | 15 | read-only |
| 18 | learned index + NeurIPS watch (bob) | 18 | +1 paper, +1/-1 venue watch, history |
| 19 | Zhang author chains | 16 | read-only (frozen) |

The honest step counts for the re-frozen tasks are the contributor's
measurement of the minimal honest UI path each rewritten task text
requires (reads free; fill+submit = 2; combined → kind click-through = 3;
form submit = 1 + 1 per filled field; no unrequired actions), identical
across two independent Playwright rounds. Ten tasks were deepened from
below the 15-step bar (r1 measurements: t1 12, t2 13, t3 12, t4 12, t6 10,
t7 14, t14 14, t15 12, t16 11, t17 9); the full suite now measures
min 15 / max 26 / total 340 across all 20 tasks.
