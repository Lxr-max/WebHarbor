# Repository registry and asset audit

Run this read-only audit from a Git worktree of WebHarbor:

```bash
python3 scripts/audit_site_registry.py --strict
python3 scripts/audit_site_registry.py --site amazon --json
```

It checks registry consistency, TCP exposure, site entrypoints, task URLs,
HF-managed path declarations, effective ignore rules, and tracked runtime files.
It does not download assets, import website applications, reset state, or run
verifiers. Errors exit 1; warnings exit 0 normally and 1 with `--strict`.

## How the tools fit together

- `check_site_registry.py` is the compact registry/port check.
- `audit_site_registry.py` adds per-site JSON reports, asset-rule checks, and
  Git-index inspection for runtime artifacts. `--site` limits site-specific
  checks; global registry and Docker checks still run.
- `validate_tasks.py` checks the full task schema, IDs, grading metadata and
  wording heuristics. The audit reuses its local URL validator, but does not
  claim to validate the full grading contract.
- `check_reset_smoke.py` tests an explicitly selected deployment and resets state.
  It is separate from this read-only audit.

Registry parsers live in `scripts/site_registry.py`; none of the tools execute
startup or control-server code to discover sites. The two registry checkers share
Docker TCP parsing. UDP exposure cannot satisfy a web-service TCP requirement,
and invalid protocols or unregistered TCP ports fail. Local task URLs must use
HTTP and the correct port on localhost or 127.0.0.1.

Hidden directories such as ignored `sites/.cache` are excluded from site discovery.
An actual registry entry with a hidden/invalid name is still an error. Visible
unregistered directories remain findings.

## Assets and Git checks

The root `.gitignore` must cover each declared standard HF directory
(`instance_seed`, `static/images`, `static/external_cache`) with a wildcard or
site-specific directory rule. Git's effective ignore result must also remain
positive. A site-local rule may repeat root coverage; a global ignore or
`.git/info/exclude` alone cannot replace committed root configuration. The audit
probes hypothetical children and does not require downloaded assets.

Tracked files under those managed paths are errors, except empty `.gitkeep`
placeholders, matching `check_asset_inventory.py`'s inventory convention. Nonempty
placeholders still fail. Tracked runtime/scrape/cache/log files are warnings,
including indexed files missing from disk; local ignored runtime state is fine.
The original contribution removes two tracked CarMax runtime/scrape placeholders.

Git inspection failures, missing Git metadata, invalid registry input, and
unreadable required files are explicit errors. They cannot produce a clean audit.
Archive copies without a Git index cannot certify tracked-file cleanliness.

## Validation snapshot

See [the PR #110 revision report](../review-reports/PR-110-REGISTRY-AUDIT.md).
The 140-site registry audit is separate from known task-schema findings reported
by `validate_tasks.py`; passing this audit is not a clean-task-corpus claim.
