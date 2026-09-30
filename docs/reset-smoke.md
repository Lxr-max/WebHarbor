# Reset and smoke checks

This CLI **resets website state** and checks control health, homepage reachability,
and optional runtime/seed database parity. Run it against an owned test deployment
from a checkout with the same site registry. It does not perform browser or task
verification.

Set `WEBSYN_CONTROL_TOKEN` to the token configured on the control server. The CLI
reads it from the environment and sends it only to control endpoints. It rejects
control redirects and never sends the token to homepage requests. Do not put the
token in a URL or command-line argument.

```bash
# Reset and check one site; its usual container port is used for the homepage.
python3 scripts/check_reset_smoke.py --site amazon --docker-container wh-test

# Example: the container publishes control on 8201 and Amazon's 40001 on 41001.
python3 scripts/check_reset_smoke.py --site amazon \
  --control-url http://127.0.0.1:8201 --base-host 127.0.0.1 \
  --site-port amazon=41001 --docker-container wh-test --json
```

`--site-port SITE=PORT` overrides the homepage's **host** port; repeat it for
multiple mapped sites. It does not change the registered container port or reset
endpoint. Unknown sites, invalid ports, duplicate mapping entries, and overlapping
homepage ports fail. The control health response must still match the checkout's
complete registry, including container ports.

With no `--site`, the tool resets and checks every registered site sequentially.
`--reset-all` instead calls the global reset endpoint once and then checks all
sites. **`--site` and `--reset-all` cannot be combined.** Invalid configuration
fails before requests. The HTTP timeout defaults to 120 seconds because control
resets may take more than 60 seconds; use `--timeout` for slower deployments.

## What counts as passing

- Health must return HTTP 200 and JSON with `ok: true`, the exact registered site
  inventory, and matching ports with every site alive and ready.
- A per-site reset must return HTTP 200 and identify the requested site with
  `ready: true` and a positive process ID. A reset-all must report `ok: true`,
  `partial: false`, and a successful result for every registered site.
- An HTML fallback page, malformed JSON, or false/partial readiness is a failure
  even with HTTP 200. Failed resets never produce database-parity passes.
- Homepages must be reachable; ordinary redirects may lead to the final page.
  This is an HTTP smoke check, not a visual or functional review.

## Database source and coverage

The checker must read the deployment's actual files. Choose exactly one source:

```bash
# Files inside the selected running Docker container, under /opt/WebSyn.
python3 scripts/check_reset_smoke.py --site amazon --docker-container wh-test

# An explicitly selected host deployment: <root>/<site>/instance[_seed].
python3 scripts/check_reset_smoke.py --site amazon --db-root /opt/WebSyn
```

Ensure the source belongs to the same deployment as `--control-url`; naming a
source cannot establish that relationship automatically. The Docker path requires
`docker exec` access and Python 3 in the container. Host and Docker modes run the
same inventory/hash implementation.

Every direct `*.db` file in `instance/` must have a same-named counterpart in
`instance_seed/`, with identical bytes. Missing, extra, renamed, unreadable, or
mismatched databases fail. A matching primary database cannot hide other files.
Run with other writers stopped. Nonempty SQLite WAL or rollback-journal files
fail because hashing the main file alone cannot establish parity; the checker
does not checkpoint, delete, or repair those files.

Without a source flag, parity is explicitly `SKIP` with source `none`, even in
`--strict` mode. A passing exit code with skipped parity is not a reset-byte-identity
certificate. Multiple sources are rejected. Errors exit 1; warnings also exit 1
with `--strict`.

`--json` includes the source, reset and homepage outcomes, and per-database names,
hashes and statuses in `sites[].md5_files`. Legacy single-DB path/hash fields are
retained; for multiple databases the paths identify directories and the scalar
hashes are null. On failure, use the recorded errors and per-file outcomes.

Validation and limitations are recorded in the
[PR #108 revision report](../review-reports/PR-108-RESET-SMOKE.md). Earlier
[PR #47 evidence](../review-reports/PR-47-RESET-SMOKE.md) describes its historical
candidate rather than the current implementation.
