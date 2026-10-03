# PR #91 task-validator revision

Reviewed original head `291bc267b2d4014a653db2be850ccd7d1564913b` against main
`e506aca87598c2cf51f65f8c71b672ea656a153b` on 2026-09-30.
PR #91 includes the original PR #45 commit; #45 is closed without a merge.
Integrate #91 before this reviewer continuation to retain that ancestry.

## Revisions

- Removed the context-free confirmation-code token heuristic: ZIP codes and
  supplied lookup identifiers are legitimate task inputs. Explicit answer-revealing
  phrase warnings remain. This does not certify that all answer leakage is detected.
- Reject padded verifier paths, matching the evaluator's untrimmed path resolution.
- Require HTTP for local mirror URLs; allow HTTPS for upstream URLs.
- Document runtime failures separately from naming/structure violations, and
  retain older review artifacts as explicitly historical evidence.

## Executed validation

- 41 unit/integration tests passed, including four real CLI fixture executions
  checking JSON output, normal/strict exit codes, and unchanged fixture files.
- Normal and strict full-corpus CLI scans each covered 140 sites / 3,258 tasks:
  406 errors, zero warnings, exit 1. The three original Disney warnings disappeared.
- SHA-256 comparisons confirmed 3,613 task/verifier/registry input files unchanged
  across both scans.
- All 140 sites passed the existing registry/Docker EXPOSE/task-port checker.
- The actual `trajectory_text` function extracted from `agent_demo/eval_judge.py`
  raised `TypeError` for all 144 current non-text rubric values. This was an
  isolated formatter check, not a secondary LLM judge execution.
- Python source compilation and whitespace checks passed.

No website, task, verifier, judge, runtime, Docker configuration, or HF asset was
changed. No Docker build or browser replay was run for this static-tool change.
No fresh independent LLM review was run; earlier such claims belong only to the
historical report. Corpus defects remain separate follow-up work; this diagnostic
tool is not installed as a repository-wide CI gate.

## Current findings by site

Identity and shared-verifier findings enforce documented structure; they do not
alone establish execution or grading failure. Non-text rubrics break the current
secondary judge formatter. Counts are findings and may overlap within a task.

| Site | ID/name mismatch | Non-text rubric | Reused verifier |
|---|---:|---:|---:|
| adopt_a_pet | 20 | 0 | 0 |
| apartments_com | 0 | 16 | 15 |
| bestbuy | 12 | 0 | 0 |
| cvs | 0 | 0 | 19 |
| eventbrite | 0 | 18 | 17 |
| fandom | 0 | 18 | 17 |
| healthgrades | 0 | 18 | 17 |
| kelley_blue_book | 0 | 18 | 17 |
| macys_wine_shop | 16 | 0 | 0 |
| mayo_clinic | 0 | 20 | 19 |
| recreation_gov | 20 | 0 | 0 |
| smartasset | 0 | 18 | 17 |
| uniqlo | 0 | 18 | 17 |
| us_appliance | 20 | 0 | 0 |
| us_doj | 0 | 0 | 19 |

Reproduce with `python3 scripts/validate_tasks.py --json` (optionally `--strict`).
The original detailed evidence remains in the PR #45 report and attachments.
