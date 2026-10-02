# Deterministic review grading

Run a task with the normal browser agent, then use the repository entrypoint:

```sh
python agent_demo/eval_judge.py --run_dir /absolute/path/to/run --verifier True
```

Each task has a reviewer-authored rubric and verifier. `contract.json` records
reviewed source facts, relevant page evidence and exact requested database
changes. `contract_engine.py` checks task identity, decoded screenshots,
consistent local origin, saved initial/final SQLite snapshots, required factual
claims and preservation of unrelated rows. It never falls back to a live DB.
Passwords, generated identifiers and creation timestamps are treated separately
from account ownership, quantities, symbols, course codes and order relationships.

Answers may use prose, bullets or tables; tasks do not require a fixed output
schema. Recognition uses finite deterministic patterns, numeric/unit
normalization and domain aliases. It is not general semantic understanding:
unrecognized valid paraphrases can require reviewer attention. The LLM judge is
a separate secondary assessment and was not configured for this review.

The review recordings are scripted UI regressions. Portable controls are run with:

```sh
WEBHARBOR_REVIEW_RUNS=/path/to/task-directories python -m pytest sites/stanford_university/verify/test_verifiers.py -q
```

Controls use copies of the evidence and saved databases. They check positive
answer variants, missing facts, changed ownership/quantities/resources, unrelated
state preservation, task identity, incomplete attempts and seed tampering.
