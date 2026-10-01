# steam verifier suite (reviewer contract, r2 re-freeze)

Deterministic, LLM-free verifiers for the 20 `Steam--*` benchmark tasks.
Written by the steam reviewer on `orch/review/steam` from contribution
`baaf57f9` (r1, `9289dc61`) and re-frozen at r2 against the fix tree
`orch/contribute/steam` @ `e2ea4cb0`: the r1 findings (T7 depth, T5/T11
wording, release-date sort, playtime units, T15's discount premise,
Portal-Bundle ambiguity, tokenized search) were all fixed upstream and the
affected verifiers re-frozen from the reviewer's two independent honest
Playwright rounds on the r2 review container `wh-steam-r2` (image
`webharbor:steam-r2`, built independently by the reviewer from the fix tree
with the pinned, sha256-verified HF asset archives at revision
`c1009c3b…`; seed md5 `b9a24e716aa09b3702ab3a0b38d8c4de`, sha256
`e6d0805e…`, byte-identical to r1 — the fixes touch no seed data). Both r2
rounds produced identical per-task step counts and answers (audit-trail
caliber: one navigation / one fill / one select / one checkbox / one submit,
reads never counted, initial home load not counted; **min 15 / max 24 /
total 366, all 20 tasks ≥ 15**); zero JS errors; every per-task reset
snapshot byte-identical to the frozen seed. Every hardcoded fact was
cross-checked against the frozen seed database.

## Layout

- `verify_lib.py` — shared contract: package identity (task_id / agent_done /
  non-empty answer / same-origin same-port / decodable PNGs), seed identity
  gate (table counts + schema sha256 + rows sha256 + file md5 pinning the
  in-image seed — unchanged at r2, re-verified against the independent r2
  image build), navigation gates, answer token/phrase/number/money/ordered
  checks, and read-only / exact-delta DB after-state checks.
- `verify_0.py` … `verify_19.py` — one verifier per task; navigation gates +
  hardcoded ground truth + DB contract. Re-frozen at r2: `verify_6.py`
  (playtime is now displayed as hours — "28.3 hrs on record"),
  `verify_7.py` (the deepened task: every free-to-play Valve game's page
  must be opened and its release date + review summary reported; developer
  17 / publisher 19 games), `verify_11.py` (the fixed release-date sort
  makes WARDOGS the newest Indie game — $39.99, not discounted; the r1
  PEAK anchors are superseded). All other verifiers keep their r1 anchors
  (the site's observable facts for those tasks did not change).
- `test_verifiers.py` — 153 pytest cases: 40 honest fixtures PASS (both
  reviewer r2 rounds); no-op, answer-only shortcut, wrong-answer, stale-DB,
  read-only-violation, tampered-package and task-confusion negatives all
  FAIL (zero false positives). With the site's own suite: 177 passed.

## Usage

```bash
python3 sites/steam/verify/verify_7.py --run_dir <trajectory_dir>
#   [--initial_db P] [--after_db P] [--container wh-steam-r2]
```

## Ground-truth notes (r2 findings baked into the contract)

- Steam--15: Dead Cells itself carries **no discount** in the frozen seed
  (`discount_pct = 0`; the store page shows a plain `$24.99`) and the task
  now asks "whether it is discounted" — the honest answer states this. The
  r1 contribution contract pinned a `-20%` its own seed contradicts (fixed
  upstream). **The r2 fix tree's own `contract.json` still pins a wrong
  fact for this task**: `second bundle price = $24.99` — that is the first
  bundle ITEM's individual price (Dead Cells/Windblown $24.99 each), not
  the Windblown + Dead Cells bundle's price ($44.98, seed
  `final_price_cents = 4498`). This contract pins $44.98, matching the
  seed and the page's buy box.
- Steam--7: the deepened task measures **16 honest atomic steps** (the r1
  wording measured 14); the contributor's r2 claim of 16 agrees with the
  reviewer's independent two-round measurement.
- Steam--11: the release-date sort now orders by the real parsed date
  ("Mon D, YYYY" in SQL), so the Indie page's newest is WARDOGS
  (Sep 10, 2026) — matching the site's own displayed data and upstream
  semantics.
- Steam--6: the reviews page now displays playtime as hours ("28.3 hrs on
  record"), matching upstream.
- Steam--4 / Steam--9: the tasks now name the Portal Bundle explicitly
  (two bundles include Portal 2); the DB row still records the bundle's
  internal row id.

## Freezing / re-sync

`python3 verify_lib.py --freeze <seed.db>` prints the frozen seed constants
from a given seed database, for re-syncing the contract after accepted fixes
(the wanderlog r2/r3 precedent).
