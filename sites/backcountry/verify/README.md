# Reviewed task grading

`verify_0.py` through `verify_19.py` use the self-contained `contract_engine.py`
and `contract.json`. Run through `agent_demo/eval_judge.py --run_dir RUN --verifier True`.
Each RUN must include trajectory.json, referenced PNGs, initial.db and after.db.
There is no fallback to live containers or mutable preview state.

The contract validates task identity, same-origin page evidence, decoded screenshots,
logical initial seed identity, and exact requested state deltas. Unrelated rows must
remain unchanged. New passwords are checked using bcrypt, with fresh salts allowed.
Order codes are checked against the actual saved order. Answers accept tested prose,
bullets, tables and currency equivalents; deterministic language coverage is finite.
Navigation gates identify relevant detail/outcome pages without prescribing click order
or requiring a minimum action count. Reviewer evidence is scripted Playwright, not an
independent LLM agent run. No secondary LLM judge was configured.

Run `python -m pytest tests verify/tests -q` from the site directory.
Answer controls are declared positive/negative fixtures, separate from real browser evidence.
The external review report retains the actual browser runs and independent state-mutation controls.
