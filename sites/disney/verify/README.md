# disney — reviewer grading contract

Re-frozen by the r2 review round on top of the fixed contribution's
five-key `tasks.jsonl` (contribution `038c6d43`), independently
re-verified against the r2 reviewer's own container before freezing.
The r1 contract (commit e6dd2358) was frozen against contribution
b2155137; every truth the fix moved has been re-derived from the r2
reviewer's own Playwright walks (wh-disney-r2-review).

## Layout

- `verify_lib.py` — deterministic verifier utilities: fail-closed package
  identity (task_id / agent_done / non-empty answer / loopback
  origin+port / decodable PNGs), frozen seed identity gate (schema
  `f8bb11a8…` / rows `8571db9d…` / 13-table counts / md5 `9f231a5a…` /
  sha256 `344b6c2a…` from the r2 reviewer's independent image build
  `webharbor-disney-r2:dev`), navigation gates, answer
  token/number/phrase checks, and read-only vs exact stateful SQLite
  after-state checks.
- `verify_0.py` .. `verify_19.py` — one deterministic verifier per task,
  ground truth HARDCODED from the reviewer's independent Playwright honest
  walks (per-task control-plane reset + fresh context, identical facts
  across the walk set) — never read from `tasks.jsonl`.
- `gen_verifiers.py` — the spec that emitted the per-task verifiers
  (kept so a re-freeze after a contributor fix is a one-file edit).
- `append_rubrics.py` — idempotent appender for `verifier_path` +
  `judge_rubric`; the five contributor keys stay byte-identical, no
  `answer` key is ever written, rubrics are pure English rules.
- `tests/` — adversarial contract tests (94 cases): 20 honest fixtures
  PASS; 20 no-op, 20 pure-answer shortcuts, 20 wrong-answer runs,
  3 read-only tampers, 3 stale-state runs, 7 package tampers and 2
  task-confusion runs all FAIL (zero false positives).

## r2 re-freeze notes

All r1 known mirror defects are fixed on the site (contribution
038c6d43); the contract now pins the FIXED truths, re-derived from the
r2 reviewer's own walks:

- the attraction favorites form posts the full `park/slug` key and
  `/favorites` renders every favorited card — T7/T9/T19 pin count ==
  rendered cards and the DB rows carry the full key;
- the site-wide search lists full result sets — T4 pins Parks &
  Entertainment 13, T13 pins Shop 25 (count == listed rows);
- sale items still show no original price upstream, but T11 no longer
  asks for it; the first plush hit still has no reviews row, but T13 no
  longer asks for it;
- game titles are clean hub names and descriptions render real upstream
  rich text — T17 pins the on-page strings (search 'disney' now hits 3);
- two shows are still titled `DuckTales`, but T3 says "the newer
  DuckTales series" — pinned to the 2017 reboot (TV-Y7);
- two EPCOT fireworks still exist, but T7 names "the Heartbeat of
  Freedom fireworks show at EPCOT" — pinned to that one;
- T16 was redesigned into a real multi-city planning chain (18 honest
  atomic steps measured by the r2 reviewer's two-round walks; the Nov 22
  Buy Tickets link prefills 1:00 pm, so selecting the required 5:00 pm
  performance is a genuine step).

## Usage

```bash
# grade one run (initial/after DBs default to <run_dir>/initial.db and
# <run_dir>/after.db; when absent they are fetched from the container)
python3 verify_0.py --run_dir runs/0 [--container wh-disney-review]

# adversarial contract tests (needs the review container or WH_DISNEY_SEED_DB)
python3 -m pytest tests/test_verifiers.py -q
```
