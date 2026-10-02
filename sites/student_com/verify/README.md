# Student.com task verification

Run the primary deterministic grader from the repository root:

```bash
python agent_demo/eval_judge.py --run_dir /path/to/task-run --verifier True
```

Each run supplies trajectory.json, referenced screenshots, initial.db and after.db.
The verifier checks task identity, completed execution, local origin, decoded image
evidence, relevant page visits, requested answer facts and saved-state deltas.
The initial schema and rows are pinned to the reviewed build-generated seed.
Account actions preserve unrelated records. Natural wording and common numeric/date
formats are supported; matching remains deterministic and is not a general semantic judge.
Ground truth belongs in the verifiers and test fixtures, never in tasks.jsonl.

Tests:

```bash
python -m pytest sites/student_com/tests sites/student_com/verify/tests -q
```

Build the seed with the site's Dockerfile procedure before running tests. The test
fixtures reconstruct browser-checked outcomes synthetically; they are separate from
real trajectories. No secondary LLM judgment is needed for these checks.
