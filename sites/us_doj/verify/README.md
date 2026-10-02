# Reviewer grading

Run from the repository root:

```sh
uv run --project agent_demo python agent_demo/eval_judge.py --run_dir /path/to/run --verifier True
```

The offline verifier requires `trajectory.json`, its referenced `screenshots/`,
and SQLite `initial.db` and `after.db` snapshots. CVS also needs Playwright
`browser-state.json` storage state for cart ownership and selected-store evidence.
It never substitutes a live database for saved evidence or calls an external model.

`contract.json` contains reviewer-only expectations, separate from task prompts.
Read tasks must preserve the initial database; state tasks require the exact requested
rows, account ownership, item quantities and totals, preserving unrelated records.
Equivalent item insertion order and generated row IDs are accepted. Browser paths
accept captured and local product aliases. There is no minimum action-count gate.

Answers may use natural paragraphs, bullets or tables. Entity-scoped regular
expressions check facts, units and selected policy distinctions. Language coverage
is finite, not general semantic equivalence: novel correct paraphrases may need
review. Evidence checks establish relevant recorded paths and readable screenshots,
not independent proof against a forged trajectory. Signed offline demo sessions
bind guest state and selected stores to the recorded browser.

Validation uses real scripted browser actions plus separately labelled synthetic
answer/state/evidence controls. Reviewer-authored answers summarize captured UI;
no independent LLM browser agent or secondary LLM judge was run. Final per-task
recordings and controls live in the PR dashboard under `/data/webharbor-prs/final/`.
