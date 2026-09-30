# Reviewed deterministic grading

Run through `agent_demo/eval_judge.py --run_dir PATH --verifier True` from the repository root. Each `verify_N.py` emits JSON and exits 0/1. `contract.json` holds reviewer-only ground truth; tasks.jsonl holds no answers.

Evidence must contain the correct task, completed local browser trajectory and decoded screenshots, plus saved initial.db and after.db snapshots. Grading checks relevant page evidence, entity-bound facts and exact account/state deltas, preserving unrelated rows. The initial database must match the reviewed logical seed. There is no action-count gate and no live-database or external-LLM fallback.

Natural prose and tables are supported through finite deterministic normalization and patterns; this is not unrestricted semantic understanding. Review controls cover correct equivalents, missing/wrong facts, navigation shortcuts, corrupt evidence and saved-state errors. The browser evidence and control outcomes are retained in the final review dashboard under /data; they are not bundled into the site image. A secondary LLM judge is separate and was not configured for this review.
