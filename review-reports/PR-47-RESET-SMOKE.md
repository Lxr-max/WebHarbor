# Review of PR #47: reset and smoke verification

Historical snapshot: see [the PR #108 revision report](PR-108-RESET-SMOKE.md)
for subsequent fixes and current validation. The attached JSON records the earlier
frozen executions.

Reviewer-owned continuation of [PR #47](https://github.com/aiming-lab/WebHarbor/pull/47)
by @Lxr-max / XuanRui LI. Contributor and reviewer history is preserved.

## Current candidate — 2026-09-28

- Upstream main: `1c1dc23f5fabdaaef67c6d3bbf87bcd6915b9518`.
- Frozen executable candidate: `661a7642d39abb66f7acc8efefa502da756362a5`.
- Registry: 99 sites, ports 40000–40098.
- Checker and unit-test sources are unchanged from `eb27154` (the authentication repair).

The checker reads `WEBSYN_CONTROL_TOKEN` from the environment for `/health`,
`/reset/<site>` and `/reset-all`. Site homepage requests receive no bearer header.
Authenticated control redirects fail. Invalid token values fail as structured JSON
before network requests; missing/wrong credentials cannot produce reset or parity success.

`--docker-container` selects deployed container DBs; `--db-root` selects an explicit
host deployment tree. With neither flag parity is `SKIP`, even if the checkout contains
DBs. Reset failures also skip parity. [Usage](../docs/reset-smoke.md).

## Current engineering checks

```bash
python3.12 -B -m unittest discover -s scripts -p 'test_check_reset_smoke.py' -v
pyright scripts/check_reset_smoke.py scripts/test_check_reset_smoke.py
ruff check scripts/check_reset_smoke.py scripts/test_check_reset_smoke.py
python3.12 -B scripts/check_site_registry.py
```

**30/30 tests PASS**; syntax, Pyright and Ruff PASS; all **99 registry entries** consistent.
Reviewer-delta whitespace checks pass. The root README remains identical to upstream.

## Executed authentication matrix

The following 13 guided CLI executions use fresh subprocesses, real loopback HTTP,
and actual temporary SQLite databases. The upstream token loader, authentication guard,
health/reset routes and `reset_db` execute unchanged. The registry has one fixture site;
process identity, reaping and restart are substituted so the fixture cannot manage real
site processes. Reset calls restore the actual temporary dirty DB from its seed.
Control redirects and backend reset failures are explicit fixtures.

The [public observations](PR-47-AUTH-RESULTS.json) include CLI output, HTTP records,
reset events, before/after DB hashes and rows, the checkout DB precondition, and a
separate redirect-destination log. Temporary paths and synthetic authorization values
are normalized as documented in that file. Nonzero CLI exits are required for negative
scenarios; they are not test-runner failures.

| Scenario | Contract | CLI exit |
|---|---|---:|
| A01 | Authenticated per-site reset restores the dirty database; homepage receives no bearer header. | 0 |
| A02 | Authenticated reset-all restores the database without issuing per-site reset requests. | 0 |
| A03 | Without a DB-source flag, reset succeeds but parity is SKIP even if checkout DBs exist. | 0 |
| A04 | An absent token must fail authenticated control requests and leave DB state unchanged. | 1 |
| A05 | An incorrect token must fail per-site reset and skip parity without mutating the DB. | 1 |
| A06 | An incorrect token must fail reset-all, skip parity, and leave the DB unchanged. | 1 |
| A07 | A short token must fail as structured JSON before any HTTP request or reset. | 1 |
| A08 | A token containing a newline must fail as structured JSON before any HTTP request. | 1 |
| A09 | A non-ASCII token must fail as structured JSON before any HTTP request. | 1 |
| A10 | Authenticated control redirects must be rejected; the redirect destination receives no request. | 1 |
| A11 | A homepage redirect to a successful page is allowed, with no bearer token on either hop. | 0 |
| A12 | A token of exactly 32 printable ASCII characters is supported for control requests. | 0 |
| A13 | An authenticated backend reset failure returns failure, skips parity, and preserves the dirty DB. | 1 |

## Independent authentication review

A fresh isolated **Claude Opus 5.5** session returned **13 PASS / 0 FAIL** for A01–A13
at the frozen executable candidate above. The session received only the allowlisted
packet, with no source, previous review, or reviewer conclusions. It reported no
contamination and a valid packet.

The reviewer executed the supplied packet checker, which validated **174 file hashes**
and compared raw SQLite snapshots with their recorded rows and hashes. It relied on
that helper's successful output rather than separately auditing the helper source.
The CLI's own PASS/FAIL fields were assessed as product output, not accepted as a grading oracle.

- Packet manifest SHA256: `404ca2340cf42280d0324a9c1fc557edc833ae4d89ee453ba030e7d04fff98f7`.
- Frozen independent response SHA256: `b4fc9be2dd6976a789fae6dd9520b8bc19bd36cf5112efdd7c61423277274f8b`.
- Per-scenario verdicts and limitations are included with the public observations.

Local reconciliation agrees with all 13 verdicts. The subsequent report/evidence commit
changes documentation only; checker, tests, control source and frozen executions remain
unchanged. **The requested authentication follow-up is complete and ready for maintainer review.**

The historical 14/14 independent review at `d660caf` remains evidence for its original
scope. It is not used to certify this authentication delta.

## Applicability and limits

This is repository tooling: no mirror, task, verifier, Dockerfile or asset delta is
introduced relative to current main. Tooling scripts and reports are not copied into
the runtime image by its explicit COPY instructions. No new HF contribution is needed.

No full 99-site live smoke, Docker build or container launch was performed this round.
The current matrix validates the authentication/CLI/DB-reset boundaries described above;
it does not certify production process supervision, browser behavior, or site content.
Earlier live-container evidence covers its historical two-site scope only. Podman and
remote Docker daemons remain untested. A `--db-root` verdict concerns the supplied root;
homepage smoke checks status rather than page content.

Final approval and merge remain with the maintainer.
