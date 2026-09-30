# Reviewed task grading

Run the primary grader through `agent_demo/eval_judge.py --run_dir <run> --verifier True`.
Each task uses a wrapper, the local contract engine and `contract.json`. Ground truth stays outside tasks.jsonl.

Evidence requires the supplied task, complete local-browser trajectory, decoded PNG screenshots, relevant pages, and saved initial.db/after.db snapshots. The initial fixture must match the reviewed logical seed. State changes are checked row by row and field by field, preserving unrelated data. No mutable live-database fallback or minimum-action gate is used.

Natural prose, bullets and equivalent formatting are accepted by finite deterministic patterns. These are bounded recognizers, not unrestricted semantic grading. Facts are scoped to entities, properties and units; unsupported formulations can require rubric review. The secondary LLM judge is separate.

Regression controls and final browser evidence are linked from the PR report/dashboard. Source-backed unavailable fields must remain unavailable; do not invent values to make a task pass.
