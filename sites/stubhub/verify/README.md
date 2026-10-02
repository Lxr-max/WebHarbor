# stubhub task verifier contract (reviewer track)

Deterministic, LLM-free grading contract for the 21 `StubHub--N` tasks, added by
the review round on top of the contributor's five-key `tasks.jsonl`.

## Layout

- `verify_lib.py` — shared fail-closed checks: package identity (task_id,
  `terminated`/`agent_done`, non-empty answer, same loopback origin+port,
  decodable PNG screenshots), navigation gates, answer token/number/phrase
  matching, and the SQLite after-state contract (frozen seed schema + row
  digests; read-only tasks must leave the seed byte-identical row-wise,
  stateful tasks must produce exactly the allowed row delta).
- `verify_0.py` … `verify_20.py` — one verifier per task. Ground truth is
  HARDCODED here (never in `tasks.jsonl`), frozen from the deterministic seed
  (`instance_seed/stubhub.db`, build-time `PYTHONHASHSEED=0`, md5 `c71165b3…`)
  and cross-checked against the reviewer's honest live runs.
- `append_rubrics.py` — appends `verifier_path` + `judge_rubric` to
  `../tasks.jsonl`. The five contributor keys stay byte-identical (each output
  row is the original line with the two keys appended); no `answer` key is ever
  written. Idempotent.
- `generate_verifiers.py` — emits `verify_N.py` from the frozen spec table
  (regenerate only when a task text changes; the checked-in files are the
  contract).
- `extract_fixtures.py` — rebuilds `tests/fixtures_data.py` from the reviewer's
  honest live runs (trajectories + initial/after DB snapshots). Checked-in
  fixtures are the contract; re-extraction requires the review evidence dir.
- `tests/` — `test_verifiers.py` + `_support.py` + `fixtures_data.py`:
  per task the honest run MUST PASS and the no-op / knowledge-shortcut /
  wrong-answer / state-mismatch / read-only-tamper / package-tamper runs MUST
  FAIL. `python3 -m pytest sites/stubhub/verify/tests -q` (needs the review
  container or `STUBHUB_TEST_SEED_DB` pointing at the seed DB).

## Verification signature

```
python3 sites/stubhub/verify/verify_N.py --run_dir <dir> [--initial_db …]
                                        [--after_db …] [--container wh-stubhub-review]
```

`<dir>` holds `trajectory.json` (agent_demo shape), `screenshots/step_NNN.png`
and (optionally) `initial.db` / `after.db`; without the snapshots the verifier
fetches the seed / live instance DB from the container. Output is a JSON
verdict on stdout; exit 0 on PASS, 1 on FAIL.

## Known environment notes (r2, post-fix contract)

- The r1 canonical-build caveats are resolved by the F1–F12 fix commit
  (`8c06a7b0`): the seeder no longer reads the untracked `scraped_data/`
  scratch (performer imagery resolves from the tracked asset tree —
  602/699 with images, 699/699 with a taxonomy node — and the clean-context
  seed is byte-identical to the with-scratch build, row digest `4cd4a215…`),
  the Follow button is clickable on media-less performer heroes, the
  similar-artists rail populates, event pages render the 42 venue seat maps
  inline, and displayed dates are venue-local (matching the URL slug).
  T6/T19 fixtures may now come from the canonical build itself.
- Gift-card codes are runtime-random (`os.urandom`): the contract matches the
  `SH[A-Z0-9]{10}` shape and the row delta instead of a frozen code.
- Checkout honors a filled "Use a new card" form over the saved-card radios
  (F6): for card-holding buyers the new card is used for the order only and
  `orders.card_last4` reflects it; the wallet is left untouched. The T3
  contract still freezes the order row (reference, fees, total) and not the
  agent-chosen card number.
- `verify_4`'s event delta is `listing_count 10 -> 11` (the F9 fix removed the
  +1 double-count), and `verify_5`'s earliest-purchase date is Jul 24, 2026
  (the F8 fix made the pages show the true seeded `created_at`).
- `verify_7` accepts both suggestion-service uses: the raw endpoint URL in
  the trajectory, or the term typed into the search box (the F7 autocomplete
  dropdown is fed by that endpoint).
