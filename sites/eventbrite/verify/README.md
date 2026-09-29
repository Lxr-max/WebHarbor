# Eventbrite task verification

Run the primary deterministic grader from the repository root, with the
`agent_demo` dependencies and `uv` available:

```bash
python agent_demo/eval_judge.py --run_dir /absolute/path/to/task-run --verifier True
```

The runner reads `verifier_path` from `trajectory.json`, resolves it from the
repository root, and invokes that script with `--run_dir` under `agent_demo` via
`uv run python`. Use an absolute run path because the subprocess changes directory.

## Entry points and ground truth

`verify_0.py` through `verify_17.py` call `verify_lib.main(index)` for the
18 `Eventbrite--N` tasks. `contracts.py` holds `TASKS`: frozen expected facts,
navigation patterns, task-specific predicates, state callbacks, and rules-only
rubrics. `checks.py` supplies case/punctuation folding, phrase and numeric matching,
and proximity helpers. These are deterministic text checks, not a semantic judge.
Ground truth belongs in the verifier package and its test fixtures, not in
`tasks.jsonl` or this document.

## Run signature

For direct invocation, select the task's matching entry point:

```bash
python sites/eventbrite/verify/verify_0.py --run_dir /absolute/path/to/task-run
```

- `--run_dir` is required and must contain `trajectory.json`.
- The answer is `trajectory.final_answer`. Navigation comes from each step's `url`
  and `url_after`, plus `final_url`. Relative URLs are resolved against `start_url`;
  `start_url` alone is not a visited-page record.
- Stateful tasks (1 and 12 through 16) accept `--initial_db` and `--after_db` paths.
  If neither option is supplied and either `initial_state.db` or `after_state.db`
  exists in the run directory, both run-directory paths are passed to the state
  callback. Supplying either explicit path disables this fallback entirely; a
  missing counterpart is not filled automatically. No seed or live-container
  snapshot is substituted. Provide valid SQLite snapshots for stateful runs.
- `--container` (defaulting to `WH_CONTAINER`) and `--no_llm` are accepted but do
  not affect evaluation. No secondary judgment or network call is made.

The state callbacks in this package inspect the after-state; they do not compare every row with the initial snapshot.

The current shared harness checks URL patterns, the non-empty final answer, and
any task-specific state callback. It does not validate screenshots, completion
flags, trajectory task identity, or URL origin, and does not enforce unchanged
read-only databases. State checks are task-specific, not a complete database diff.

## Verdict and tests

A completed evaluation prints JSON with `task_id`, boolean `pass`, `reason`, and
an `evidence` list of check results. Exit status is `0` for PASS and `1` for FAIL;
`reason` names the first failed check and is empty on PASS. Invalid arguments,
unreadable input, malformed JSON, or SQLite errors can terminate without verdict
JSON; they are not successful evaluations.

```bash
python -m pytest -q -p no:cacheprovider sites/eventbrite/verify
```

Extract the reviewed `eventbrite.tar.gz` seed into the site before running tests.
`test_verifiers.py` copies `instance_seed/eventbrite.db` into temporary databases.
For every task its synthetic matrix checks a no-op failure, a correct-answer
shortcut without navigation, a wrong-answer failure on the required URLs, and a
passing case; stateful tasks also reject an unchanged-state self-report.
Additional regressions cover correct prices assigned to the wrong events.
The schema/no-leak test requires exactly the seven task keys, matching task ids
and existing indexed verifier paths, synchronized rubrics, and no answer key.
It checks expected numeric tokens and answer literals, allowing task inputs
already stated in the question, with targeted guards for audited outcome leaks.
These fixtures are not browser trajectories; the literal checks supplement,
rather than replace, review of rubric meaning.
