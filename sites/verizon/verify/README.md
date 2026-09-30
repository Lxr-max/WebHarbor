# Deterministic task grading

Run `agent_demo/eval_judge.py --run_dir PATH --verifier True` from the repository root.
Each task entry selects its self-contained verifier. Supply `trajectory.json`, decoded browser PNGs under `screenshots/`, and saved `initial.db` / `after.db` snapshots. No live database or LLM fallback is used.

`contract.json` contains reviewer-only expected facts, required relevant pages and exact state changes. Task prompts contain no ground truth. Unrelated rows must stay unchanged. Random confirmation IDs and permitted unspecified variants are accepted, while account ownership, quantities, selections, totals and relationships are checked.

Natural prose, bullets and tables are supported within finite deterministic paraphrase coverage; this is not a general semantic judge. Recommendations may vary when supported by the requested compared facts. There is no minimum-action grading gate. The evidence checks reject missing/blank/corrupt screenshots, invalid origins and incomplete attempts; screenshots are not OCR-graded.

The final GIF dashboard discloses that walkthroughs were reviewer-scripted and answers were authored from captured UI. Independent synthetic controls are separate from browser evidence. The secondary LLM judge was not run.
