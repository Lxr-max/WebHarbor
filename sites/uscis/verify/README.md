# Offline deterministic task grading

Run the official entrypoint from the repository root:

```sh
python agent_demo/eval_judge.py --run_dir /path/to/run --verifier True
```

Each `verify_N.py` uses this site's `contract_engine.py` and private `contract.json`.
Task files contain prompts and grading rules, never expected answers. Save `initial.db`
and `after.db` alongside `trajectory.json` and its PNG `screenshots/`; the verifier
never reads a mutable live database or copies state from a container.

Checks cover task identity and completion, one loopback browser origin, fully decoded
screenshots, relevant pages including filters where requested, reviewed initial seed,
entity-bound factual claims, and precise state deltas preserving unrelated records.
Generated post identifiers, valid appointment slots, optional contact fields, and
freeform message content are handled separately from fixed requested outcomes.
No minimum action count is imposed. Rubrics accept natural language; deterministic
pattern recognition has finite paraphrase coverage and is not semantic equivalence.
The synthetic controls are regression evidence, not independent browser attempts.

Run `python -m pytest sites/uscis/verify/tests -q` for focused verifier regressions.
Review dashboard receipts contain the real scripted walkthroughs, official grades,
and separately labelled positive, negative, and state-mutation controls.
