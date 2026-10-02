# Parkers deterministic grading

The 20 task verifiers are the primary graders. Ground truth lives in
`verify_N.py`; task instructions and rubrics in `../tasks.jsonl` contain no
answer field. Each task pursues a complete user goal.

Run through the official entrypoint:

```bash
python agent_demo/eval_judge.py --run_dir PATH_TO_RUN --verifier True
```

Or invoke an individual verifier with `--run_dir DIR`, optionally supplying
`--initial_db PATH` and `--after_db PATH`. By default snapshots resolve to
`initial.db` and `after.db` in the run directory. The verifier emits JSON
`{task_id, pass, reason, evidence}` and exits 0 for pass, 1 for failure.

The shared contract checks task identity, strict completion, same-origin
navigation, all referenced PNGs through full decoding, the frozen initial seed,
final schema, and precise permitted state changes. Read-only tasks preserve every
row; stateful tasks preserve all unrelated records. Task-specific checks bind
answers to requested entities and require monetary assertions to include currency.

`tests/reviewed_fixtures.json` contains portable synthetic fixtures distilled
from reviewed browser outcomes. Its tiny images exercise the evidence contract;
these tests are not browser-completion evidence. The actual browser recordings
are retained separately in the review dashboard.

Fetch the pinned assets and generate the seed where the site requires it, then
run site and verifier tests separately:

```bash
python -m pytest sites/parkers/tests -q
python -m pytest sites/parkers/verify/tests -q
```

Controls cover correct completion, no-op/knowledge shortcuts, wrong answers,
state mismatches, changed unrelated rows, and malformed or tampered evidence.
Keep tasks, rubrics, verifiers, and fixtures in sync when changing behavior.
