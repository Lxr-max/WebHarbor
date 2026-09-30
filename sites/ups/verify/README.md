# Deterministic reviewer grading

Run each task through `agent_demo/eval_judge.py --run_dir RUN --verifier True`.
The trajectory must include the current task wording, same-origin browser URLs,
decodable PNG screenshots, and saved `initial.db` and `after.db` snapshots.

The grader checks the reviewed seed, required content surfaces, scoped factual
claims and exact requested database changes while preserving unrelated rows.
Generated booking confirmations must match saved state. No live database or
external model fallback is used. The task action count is descriptive, never a
grading gate. Answer recognition is finite regex-based language coverage;
ordinary prose, bullets and equivalent tested formulations are supported, not
unrestricted semantic understanding. Browser replay evidence and synthetic
controls are reported separately in the external review dashboard.
