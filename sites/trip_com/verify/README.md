# trip_com — reviewer grading contract

Authored by the reviewer (branch `orch/review/trip_com`) after the independent
review of the contribution `orch/contribute/trip_com` @ `60038e71` (round 1)
and re-synced onto the fixed contribution `a375a671` (round 2, 2026-09-28).
The contributor ships only the 5-key task rows; this directory adds the
**grading contract**: one deterministic verifier per task plus the LLM-judge
rubrics recorded in `tasks.jsonl`.

## Layout

| File | Role |
|---|---|
| `verify_lib.py` | Deterministic utilities: trajectory identity, navigation gates, answer token/phrase/number/money checks, SQLite after-state diffing, frozen seed contract. No LLM call is load-bearing. |
| `verify_0.py` … `verify_19.py` | One verifier per task (`Trip.com--N`). Ground truth is HARDCODED here — never in `tasks.jsonl`. |
| `make_verifiers.py` | Deterministic generator for the verifiers (byte-stable regeneration is asserted in the tests). |
| `append_rubrics.py` | Merges `verifier_path` + `judge_rubric` into `tasks.jsonl`, asserting the contributor's 5-key prefix stays byte-identical and that no `answer` key ever appears. |
| `tests/` | 260-test pytest suite: honest runs PASS, no-op / shortcut / wrong-answer / state-mismatch / tampering runs FAIL, read-only purity, seed contract, tasks.jsonl contract. |

## Contract rules

1. **Identity (fail-closed).** task_id match, `terminated=agent_done`, non-empty
   answer, every URL on the same loopback origin:port, every referenced
   screenshot a decodable PNG.
2. **Navigation gates.** The agent must have opened the on-site surfaces the
   task names (list/detail/book/confirmation/account pages). A correct answer
   without the navigation is a knowledge shortcut = FAIL.
3. **Answer checks.** Frozen phrases / numbers / money amounts, with documented
   tie sets: T2 accepts any of the three $213 Delta nonstop outbounds
   (07:00/16:15/22:15) + the unique $228 return; T11 accepts any of the three
   $93 cheapest Miami rooms; T18's rating tie resolves to the only 5.0-rated
   activity with a highlights section.
4. **DB after-state.** Read-only tasks (9, 11, 12, 13, 15, 16, 19) must leave
   every table row-identical to the seed. Stateful tasks must leave exactly the
   allowed delta (one booking row with the frozen price math, one status flip,
   one wishlist set-delta) and nothing else.
5. **Seed contract.** Frozen table counts, sqlite_master digest, all-rows
   digest `56fa75a6…` and file md5 `99cb4050…` — the value produced by the
   r2 reviewer's independent image build from `a375a671` (two fresh
   `PYTHONHASHSEED=0` seed builds inside the image reproduce it byte-
   identically; the r1 value `4d3cfe87…` changed only through the
   contributor's tracked attraction-image path manifest).

## r2 re-freeze notes (2026-09-28)

- **T18 unblocked.** The attraction booking form fix (contribution
  `1e2ca971`: the POST branch reads `request.form` first) records the
  submitted date and guests, so the 3-guest/12-October booking is reachable:
  the frozen row is now `2026-10-12 / 3 guests / $48.27` and `check_blocked`
  is gone. T17's row collapsed to the submitted `2026-10-12`.
- **Deepened tasks.** The 10 deepened rows' new asked facts were added as
  purely additive answer checks and navigation gates (sourceforge-r3
  precedent); the other 10 verifiers are byte-untouched.
- **Real-trajectory gate reality.** `agent_demo` records `url_after` as the
  page after each action, so form POSTs appear as their redirect targets and
  form GETs encode spaces as `+`. T6 (cancel) and T7 (wishlist toggle) gates
  now accept both the action URL and the redirect target, and T12's list
  gates accept both `%20` and `+` encodings.
- **tasks.jsonl** was re-appended onto the `a375a671` 5-key prefixes (7 keys,
  no `answer` key, prefixes byte-identical; 10 rubrics updated to cover the
  deepened asks).
- **T2** still requires the qualifying round trip (Delta out + Delta nonstop
  return, $441.00); the Select link now carries the outbound filters, so the
  naive non-Delta return ($370) remains the rejected trap.

## Running

```bash
# verifier (from repo root): exit 0 = PASS, 1 = FAIL; JSON verdict on stdout
python3 sites/trip_com/verify/verify_0.py --run_dir runs/0

# contract tests (seed DB is docker-cp'd from the review container by default)
python3 -m pytest sites/trip_com/verify/tests -q        # 260 passed
```

Environment: `WH_CONTAINER` (default `wh-trip-com-review`) and
`TRIP_COM_TEST_SEED_DB` override the seed DB location for tests.

Reviewer continuation for PRs 252–254: maintain task prompts, rubrics and verifiers together. The former generation scripts must not overwrite this reviewed contract. Tests reconstruct synthetic states from final browser regression deltas; they are not additional browser runs. Numeric checks accept equivalent decimal forms and selected comparisons bind values to subjects. Coverage uses finite language patterns, not arbitrary semantic equivalence.
