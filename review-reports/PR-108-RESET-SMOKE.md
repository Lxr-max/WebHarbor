# PR #108 reset/smoke revision

Reviewed original head `19238d9d71630ba636236842551f65da7cfe1a38` against main
`9f744ff2e3008a106c6d03f21942e740678e00a4` on 2026-09-30.
The original PR includes contributor commit `777fcdf236562e2bb9f079cfef088c7c0531c0b8`
from the PR #47 work. Integrate #108 before the reviewer continuation; retain
that contribution and history.

## Fixed findings

- Unrelated HTTP 200 HTML and false readiness formerly passed control checks.
  Health/reset/reset-all now validate bounded JSON bodies, exact site identity
  and inventory, readiness, ports, and non-partial reset outcomes. Control redirects
  are rejected with or without a token; failed resets cannot pass parity.
- One matching primary DB formerly hid differing or extra databases. Every direct
  `*.db` is now compared by name and hash, with per-file JSON evidence. Host and
  Docker modes use the same inventory implementation. Missing/unreadable inventories
  and nonempty SQLite WAL/journal files fail explicitly.
- `--site` formerly narrowed the report but not the effects of `--reset-all`.
  The combination now fails before requests. Conflicting DB sources and invalid
  timeout/port configurations are also rejected.
- Shell comments and commented assignments no longer become site entries or
  override active registry declarations; duplicates fail.
- Repeatable `--site-port SITE=PORT` mappings support host-published ports while
  preserving the container registry and control endpoint identity. Default request
  timeout increased from 10 to 120 seconds to accommodate real reset readiness.

## Executed validation

- `python3 -B scripts/test_check_reset_smoke.py`: **39 tests passed**, including
  wrong-service and false-ready HTTP responses; malformed/partial control payloads;
  multi-DB inventory, hash, and sidecar failures; mapped ports; authentication;
  redirect behavior; and configuration rejection before requests.
- `python -B scripts/test_reset_smoke_control_integration.py` in the repository
  Flask/Werkzeug environment: **one integration test passed with five real CLI
  subprocess scenarios** against current control routes and temporary SQLite DBs:
  conflicting reset scope, wrong credentials, one-site reset, reset-all, and a
  backend seed failure. One-site reset preserved the other site's dirty DBs;
  reset-all restored four DBs byte-for-byte and removed extra files. All homepage
  requests lacked Authorization; CLI output did not expose the fixture token.
- The integration fixture uses current authentication/routes/reset_db over loopback
  HTTP. Process lifecycle is stubbed, filesystem paths are redirected to temporary
  directories, and health port reporting is adapted to model published host ports.
  It does not validate supervisor startup/shutdown or a complete deployment.
- Docker's exact generated Python inventory payload executed locally and matched
  host inventories, including failure on active sidecars. The `docker exec`
  transport itself was not exercised against a daemon.
- Current registry check passed for **140 sites**. The smoke tool independently
  resolved all 140 ports, including Amazon 40001 and Disney 40139.
- Three Python sources compiled; documentation Bash examples parsed; whitespace
  checks passed. No site, task, verifier, runtime, registry, or asset changes.

## Scope and limitations

No live deployment was reset, no full image build or browser test ran, and no HF
asset change is required. No new independent LLM review was run. Historical
independent-review results in the PR #47 report refer only to its earlier candidate.

The operator must select DB files from the same deployment as the control URL and
run while other writers are stopped. A configured source label does not prove that
association. This tool does not dirty databases itself, establish task quality,
prove frontend functionality, or replace a visual review. With no DB source,
parity remains an explicit SKIP, including in strict mode.
