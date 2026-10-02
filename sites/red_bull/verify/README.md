# red_bull deterministic task verifiers

Run from the repository root:

```sh
python agent_demo/eval_judge.py --run_dir /path/to/task-run --verifier True
```

Each task wrapper loads its reviewed contract. Required evidence consists of
`trajectory.json`, actual local-browser PNG screenshots, and saved `initial.db`
and `after.db` snapshots. Bibliography export tasks also require the downloaded
`.bib` files in `downloads/`. No live database or LLM fallback is used.

Checks cover the task identity, visited detail pages, scoped answer facts,
reviewed initial-state digest, exact requested account changes and preservation
of unrelated state. Valid generated codes, timestamps and explicitly permitted
size choices are accepted. Search-history side effects are scoped to the acting
account. Answer recognition is finite and deterministic; it does not provide
general semantic equivalence for arbitrary prose.

`python -m pytest sites/red_bull/verify` runs portable contract regressions.
Set `WEBHARBOR_REVIEW_RUNS` to a directory containing `task-00` through `task-19`
to include the external browser fixtures. Fixtures and GIFs are review artifacts,
not repository runtime dependencies. No contributor-specific paths are required.
