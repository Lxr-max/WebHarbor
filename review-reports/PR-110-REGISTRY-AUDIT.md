# PR #110 registry audit revision

Reviewed original head `1b012e856f66ac65c5e6a8d5942f515472d8152b` against main
`2be36945470bb22dcd47e4401adfecd745236b39` on 2026-09-30. The PR retains contributor
commit `32299f6c2c2371a16e8db87903f3e18783f2c13c` from the PR #46 work. Integrate
#110 first, then the reviewer continuation, preserving that history.

## Revised behavior

- The audit remains read-only and adds per-site reporting, asset configuration
  coverage and tracked-artifact inspection. It does not replace full task grading.
- `site_registry.py` provides shared static registry parsing for the compact
  checker, audit, task validator and reset/smoke tool. Both registry checkers use
  the same Docker TCP parser. The static checkers reuse `validate_local_web`
  from the task validator rather than maintaining divergent URL rules.
- Hidden local cache directories are excluded from site discovery. UDP-only web
  exposure, invalid protocols, extra TCP ports, HTTPS mirror URLs and wrong task
  ports fail. Comments and function-local Python assignments do not alter ports.
- Git index/ignore inspection errors fail explicitly. Root ignore coverage and
  effective Git ignore behavior are both required. Site-local positive rules may
  repeat root coverage. Global or info/exclude-only rules cannot replace it.
- Real tracked HF assets fail. Empty `.gitkeep` files follow the existing asset
  inventory convention and are allowed; nonempty placeholders fail. Runtime-like
  tracked files still warn even if missing on disk. The original PR's deletion
  of two CarMax runtime/scrape placeholders is retained.
- AGENTS.md derives Docker port ranges from the current registry instead of
  embedding an obsolete 99-site range. The public README is untouched.

## Executed validation

- **32 audit tests passed**, including real Git repositories, ignore negations,
  nested ignore rules, failed Git execution, tracked assets/runtime artifacts,
  protocol checks and shared URL outcomes. Two real CLI runs confirmed JSON,
  exit codes and byte-for-byte unchanged fixture files including Git metadata.
- **41 task-validator tests passed**, including four real CLI fixtures.
- **39 reset/smoke tests passed**, plus **one current-control integration test**
  with five real CLI/HTTP/SQLite scenarios; process lifecycle remains stubbed and
  all state belongs to temporary fixtures. No live preview was reset.
- Normal and strict audit CLI scans each covered **140 sites / 3,258 tasks**,
  with **0 errors, 0 warnings, exit 0**. SHA-256 checks confirmed 144 task/registry/
  asset-configuration inputs unchanged across these scans.
- The compact registry check passed across 140 sites. Package imports used by
  documentation resolved end ports 40139 and 41139 correctly. Changed Python
  sources compiled, Bash examples parsed, and whitespace checks passed.
- The full task validator retained exactly its existing **406 errors, 0 warnings**:
  88 ID/name mismatches, 144 non-text rubrics, 174 reused verifier paths. Passing
  the registry audit does not certify a clean task corpus.

## Scope

Only repository tooling, its tests/docs, and the original empty CarMax work
placeholders change. No website application, task, verifier, registry assignment,
HF archive, asset pin, or public README changes. No full Docker build, live reset,
new browser trajectory, or fresh independent LLM review was run. Earlier isolated
review claims belong to the historical PR #46 report.

Reproduce the static audit with `python3 scripts/audit_site_registry.py --strict`.
Run test files in `scripts/` directly; the control integration test requires the
repository Flask/Werkzeug Python environment. The shared parser is shipped beside
the tools, including in their standalone CLI test fixtures.
