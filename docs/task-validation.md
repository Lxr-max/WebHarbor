# Validate Tasks

Use the read-only task validator to check task JSONL files, site registration,
localhost ports, and optional reviewer grading metadata before opening a review
or PR. It reports findings without rewriting tasks or executing verifiers.

```bash
python3 scripts/validate_tasks.py
python3 scripts/validate_tasks.py --site amazon
python3 scripts/validate_tasks.py --tasks sites/amazon/tasks.jsonl
python3 scripts/validate_tasks.py --strict
python3 scripts/validate_tasks.py --json
```

Errors exit 1. Warnings exit 0 normally and 1 with `--strict`. JSON output includes
`exit_code`, counts, and per-file findings with line numbers.

## Contract

- Required non-empty strings: `id`, `web_name`, `web`, `upstream_url`, `ques`.
- IDs must be exactly `<web_name>--<number>` and unique across task files. The
  display name must be consistent within a file; it need not match the directory
  slug (for example, `UC Berkeley` in `sites/berkeley/`). The directory and local
  URL port identify the registered site.
- Reviewer fields `verifier_path` and `judge_rubric` must be present together or
  both absent. Each verifier must be a distinct existing Python file under that
  site's `verify/` directory. Rubrics must be non-empty strings. These checks
  follow [the contributor/reviewer contract](../CONTRIBUTING.md).
- Agent-facing answer/ground-truth fields are errors. Unknown fields and
  suspicious question wording are warnings. Generic credit-card vocabulary and
  demo login credentials are allowed; explicit real-payment, secret-credential,
  answer-leak and placeholder patterns still warn. Heuristics are review hints,
  not a guarantee of task quality or absence of secrets.

## Current corpus findings

At upstream `1c1dc23f5fabdaaef67c6d3bbf87bcd6915b9518`, the 99-site / 2,417-task
scan reports **173 errors, 0 warnings**, and exits 1 in both normal and strict
modes: 68 ID/display-name mismatches, 54 object-valued rubrics, and 51 reused
verifier references. This is an expected diagnostic result for the unchanged
upstream corpus, not a clean-corpus claim. Object-valued rubrics also raise
`TypeError` in the current LLM judge.

The repair removes 88 undocumented display-name/slug errors and 10 ordinary
payment-topic warnings. It retains checks for the remaining documented contract
violations. See [the review report](../review-reports/PR-45-TASK-VALIDATOR.md) for
the per-site findings, tests, and independent review scope.
