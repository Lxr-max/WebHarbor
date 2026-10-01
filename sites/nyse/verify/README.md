# Deterministic task verification

Each `verify_N.py` delegates to this site's `contract_engine.py`. The frozen
`contract.json` stores ground truth separately from agent-facing tasks.

Run from the repository root through the official evaluator:

```sh
python agent_demo/eval_judge.py --run_dir /absolute/task-run --verifier True
```

Evidence must include `trajectory.json`, referenced PNGs in `screenshots/`, and
saved `initial.db` and `after.db`. The verifier checks task identity, termination,
local origin, decoded screenshots, task-relevant visited pages, scoped factual
claims, initial seed identity, and exact changes to every database table.
There is no live-database fallback and no minimum action-count gate.

Natural sentences, lists and tables are accepted where their facts match the
contract alternatives. Recognition is finite and deterministic, not unrestricted
semantic interpretation. The optional LLM judge is a separate secondary check.

Browser controls can run against externally stored final evidence:

```sh
WEBHARBOR_REVIEW_RUNS=/absolute/site-review python -m pytest verify/test_verifiers.py
```

Controls declare expected failures for wrong facts, no browser evidence, wrong
identity, unfinished attempts, false disclaimers, altered initial fixtures and
unrequested saved-state changes. Controls mutate copies, never the original run.
