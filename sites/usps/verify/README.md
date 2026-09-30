# Reviewed offline verifier

Run from the repository root: `python agent_demo/eval_judge.py --run_dir RUN --verifier True`. Each task wrapper selects its contract. The run must contain a completed trajectory, decoded screenshots, and saved `initial.db` / `after.db` snapshots. There is no live-database fallback.

The verifier checks task identity, local browser evidence, required content pages, factual claims, and exact permitted state changes while preserving unrelated rows. It does not enforce an action count. Answer recognition uses finite deterministic expressions, accepting supported numeric/case/format variants; it is not unrestricted semantic grading. A secondary LLM judge is separate. Ground truth is stored here, never in the task prompt.
