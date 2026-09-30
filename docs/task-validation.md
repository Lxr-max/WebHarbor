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
- Local `web` URLs must use HTTP and the registered port on `localhost` or
  `127.0.0.1`; the mirror runtime does not serve HTTPS. Upstream URLs may use
  HTTP or HTTPS. Run `python3 scripts/check_site_registry.py` alongside this
  validator for the full registry/Docker EXPOSE and canonical task-URL checks.
- Reviewer fields `verifier_path` and `judge_rubric` must be present together or
  both absent. Each verifier must be a distinct existing Python file under that
  site's `verify/` directory, without leading or trailing whitespace. Rubrics
  must be non-empty strings. These checks
  follow [the contributor/reviewer contract](../CONTRIBUTING.md).
- Agent-facing answer/ground-truth fields are errors. Unknown fields and
  suspicious question wording are warnings. Generic credit-card vocabulary and
  demo login credentials are allowed; explicit real-payment, secret-credential,
  answer-leak and placeholder patterns still warn. Heuristics are review hints,
  not a guarantee of task quality or absence of secrets.
- A supplied booking reference, product code, or shipping ZIP code is not
  inherently an answer leak. Those tokens alone do not warn, even when a task
  asks for a confirmation code. Explicit answer-revealing phrases still warn.

This tool checks static contracts. It does not establish that a task is natural,
coherent, feasible, or requires more than five meaningful browser actions; nor
does it execute a verifier or prove grading accuracy. Those require browser
review and grading controls. Use it as a diagnostic tool; the current corpus
has known errors, so a repository-wide run is not yet a passing CI gate.

## Corpus snapshot — 2026-09-30

Against tasks from main `e506aca87598c2cf51f65f8c71b672ea656a153b`, the revised
validator scans **140 sites / 3,258 tasks** and reports **406 errors, 0 warnings**.
Normal and strict modes both exit 1:

- 144 non-text rubrics: confirmed `TypeError` in the LLM judge's trajectory formatter.
- 88 ID/display-name mismatches: naming-contract violations; inspect consumers before renaming IDs.
- 174 reused verifier references: violations of the documented one-script-per-task structure; reuse alone does not establish incorrect grading.

No task files were rewritten to make the scan pass. See the
[PR #91 revision report](../review-reports/PR-91-TASK-VALIDATOR.md) for validation
and per-site counts. The [earlier PR #45 report](../review-reports/PR-45-TASK-VALIDATOR.md)
and its JSON attachments retain the historical 99-site review evidence.
