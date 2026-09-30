# PR #45 task-validator review

This reviewer-owned continuation of [PR #45](https://github.com/aiming-lab/WebHarbor/pull/45)
preserves Xuanrui Li's original contribution and history. It adds a read-only task
validator and repairs schema, registry, grading-metadata, and diagnostic handling.

## Current repair — 2026-09-28

The validator incorrectly required a display name to match its directory slug.
For example, `UC Berkeley--1` / `UC Berkeley` is valid under CONTRIBUTING.md even
though its directory is `berkeley`. Removing that undocumented restriction fixes
88 false errors across Berkeley, CA.gov, IRS Refund Tracker, and PhET. ID prefixes
must still exactly match `web_name`; numeric suffixes, consistent names, unique
IDs, registered directories, and correct localhost ports are still checked.

Generic `credit card` wording also produced 10 false warnings for offline task
topics and demo workflows. That generic pattern is removed. Explicit real-payment,
secret-credential, answer-leak, and placeholder patterns still warn; normal and
strict exit behavior is unchanged.

- Upstream main: `1c1dc23f5fabdaaef67c6d3bbf87bcd6915b9518`.
- Main merge: `1fffcc22a8b336853da04cb3e4eb17ad99541083`.
- Frozen executable/test/usage-doc commit: `6fb08f64373314e0d31214f53f673276d16f0610`.
- Subsequent delivery changes only this report and its JSON evidence attachments.
- No task, verifier, site runtime, registry, root README, agent/judge, Dockerfile,
  or asset differs from upstream. No Hugging Face action is required.

## Current corpus: expected nonzero diagnostics

The full normal and strict scans both cover **99 sites / 2,417 tasks** and return
**exit 1, 173 errors, 0 warnings**. Before this repair the same corpus returned
261 errors and 10 warnings. A validator that correctly rejects existing invalid
metadata can be ready for review while the corpus itself remains noncompliant.
This report does not claim a clean repository-wide scan.

The remaining findings match the documented contract; they are not unresolved
alias heuristics:

| Sites | Finding | Count | Why retained |
|---|---|---:|---|
| Adopt a Pet (20), Best Buy (12), Macy's Wine Shop (16), Recreation.gov (20) | `bad-task-identity` | 68 | IDs use compact names such as `AdoptAPet--0` instead of the exact `web_name` prefix required by CONTRIBUTING.md. This is a naming-contract violation, not proof of a runtime failure. |
| Healthgrades, Kelley Blue Book, Uniqlo (18 each) | `bad-judge-rubric` | 54 | Rubrics are objects; CONTRIBUTING.md requires an English text block, and the actual current judge raises `TypeError` when joining them into its prompt. |
| Healthgrades, Kelley Blue Book, Uniqlo (17 additional references each) | `duplicate-verifier` | 51 | All 18 tasks in each site reference the same dispatcher. This violates the documented one-script-per-task convention; reuse alone does not prove an incorrect grading result. |

The 173 findings affect 122 rows across seven sites. The other 92 sites have no
findings. See [all current findings with paths and line numbers](PR-45-CORPUS-FINDINGS.json).
The data follow-up is to reconcile ID/display-name metadata, render the rubric
criteria as text, and provide the required per-task verifier entry points (or
have maintainers explicitly revise that repository convention). Those site-data
changes are outside this validator PR and have not been performed here.

## Verification

**36 unit tests pass** on Python 3.12. New regressions cover four unrelated
slug/display-name pairs, wrong ports despite legal aliases, benign payment topics
and demo credentials, real-payment/secret warnings, and non-text/empty rubrics.
Existing negative tests retain malformed JSON/UTF-8, missing/empty files,
registry drift, wrong ID prefixes/suffixes, duplicate IDs, forbidden answer
fields, half grading pairs, missing/escaped/reused verifiers, and warning exits.
The new alias/payment regressions failed before the implementation repair.

Fresh checks also pass: Pyright (0 errors), Ruff lint and format, scoped
`git diff --check`, and upstream registry validation for ports **40000–40098**.

The real CLI was executed in 22 synthetic scenarios, capturing stdout, stderr,
OS process exit codes, and file hashes before/after. All match their declared
contracts and preserve input bytes. These are guided CLI fixtures, not web-agent
benchmark trajectories. They exercise legal aliases/reviewer metadata, wrong
IDs/ports/names, shared/missing/escaping verifier paths, malformed rubric types,
answer fields, normal/strict warnings, cross-site duplicate IDs, and empty files.
[Execution inputs and observations](PR-45-CLI-RESULTS.json) are public.

A separate probe extracted and executed the **actual `trajectory_text` function**
from `agent_demo/eval_judge.py` without importing external SDKs or calling an LLM.
All 54 current object-valued rubrics raise `TypeError`. Full-corpus scans were
also rerun in normal and strict modes with input hashes checked before/after;
all 3,198 task, registry and verifier input files remained byte-identical. The public CLI attachment records the counts and results.

## Independent review

A fresh isolated Claude Code session (actual model `claude-opus-5-5`) returned
**22 PASS / 0 FAIL**, with `packet_valid=true` and `contaminated=false`.
Validator source, unit tests, expected-result oracles, prior reviews and project
memory were excluded. The session executed the allowed hash helper, which
verified 68 packet files and input/state correspondence for all 22 cases.

- Manifest SHA-256: `834d10f0552cc416e35c171ba42a2d0cfec315854a13e3df11fdc22ceb091837`.
- Raw verdict transport SHA-256 (frozen before parsing/reconciliation):
  `ed67057db79bc683dfac4bdff4fdb4c4e0c0b56bf1fcc5299f176426ea09bac7`.
- [Per-case independent verdicts and observations](PR-45-CLI-RESULTS.json).

The reviewer relied on the helper's reported hash checks; it did not independently
inspect that helper or rerun the validator. It reviewed only these frozen CLI
executions, not the full corpus or production grading behavior. Reconciliation
against the predeclared fixture contracts found no discrepancies. The minor
`secret credential` diagnostic label denotes the matched `client secret` category.

The first session's result was not accepted as final because its extra manifest-hash
command was denied and manifest identity was unconfirmed. The helper was extended
to check that identity and input/state correspondence; a new isolated session
reviewed the same frozen executions. No validator change or rerun was required.

## Reproduce

```bash
python3.12 -B -m unittest discover -s scripts -p 'test_validate_tasks.py' -v
python3.12 -B scripts/check_site_registry.py
pyright scripts/validate_tasks.py scripts/test_validate_tasks.py
ruff check scripts/validate_tasks.py scripts/test_validate_tasks.py
ruff format --check scripts/validate_tasks.py scripts/test_validate_tasks.py
python3.12 -B scripts/validate_tasks.py --site berkeley --strict  # exit 0
python3.12 -B scripts/validate_tasks.py --site phet_simulations --strict  # exit 0
python3.12 -B scripts/validate_tasks.py --json  # exit 1: 173 errors, no warnings
python3.12 -B scripts/validate_tasks.py --strict --json  # same findings and exit 1
```

To replay an individual published CLI fixture, create its `inputs.text_files`,
create empty files at the paths listed in `inputs.verifier_inventory`, and copy
`scripts/validate_tasks.py` from the frozen commit into that fixture root's
`scripts/` directory. Run the recorded command with Python 3.12 from the fixture
root. Verifier stubs are only existence fixtures and are never executed. Compare
JSON findings and the OS exit code, allowing the absolute `root` field to differ.

The consumer probe can be reproduced without installing or calling the judge SDK:

```python
import ast, json
from pathlib import Path

source = Path('agent_demo/eval_judge.py')
fn = next(n for n in ast.parse(source.read_text()).body
          if isinstance(n, ast.FunctionDef) and n.name == 'trajectory_text')
scope = {}
exec(compile(ast.Module(body=[fn], type_ignores=[]), str(source), 'exec'), scope)
for site in ('healthgrades', 'kelley_blue_book', 'uniqlo'):
    rows = Path(f'sites/{site}/tasks.jsonl').read_text().splitlines()
    for raw in rows:
        task = json.loads(raw)
        try:
            scope['trajectory_text']({'judge_rubric': task['judge_rubric'], 'steps': []})
        except TypeError as error:
            print(site, task['id'], type(error).__name__, str(error))
        else:
            raise AssertionError('Expected an incompatible object rubric')
```

## Delivery limits and historical evidence

This is repository tooling. No full Docker build, live site/UI task execution,
asset validation, source-fidelity certification, or grading-accuracy claim is
made. Static schema checks cannot prove task feasibility or verifier correctness.

The historical 18-scenario review of executable `142bae2` covered 24 sites and
805 tasks. Its [frozen report](https://github.com/jackjin1997/WebHarbor/blob/c4813222453acda5f0f80ab7397154f08c44faa2/review-reports/PR-45-TASK-VALIDATOR.md)
and [independent result](https://github.com/aiming-lab/WebHarbor/pull/91#issuecomment-5614696822)
remain historical evidence; their PASS does not certify today's enlarged corpus.

Non-blocking diagnostic conventions remain: registry-set drift uses the broad
message “site order differs”; task counts include nonblank malformed JSONL rows;
and full scans list expected missing registered-site files among their targets.
These do not alter severity or exit semantics.

## Maintainer handoff

The validator repair is ready for maintainer review. The branch contains the
latest checked upstream main and preserves the original contributor ancestry.
The current published head and GitHub mergeability are recorded in PR #91's
description at delivery. Final approval and merge remain with the maintainer;
no PR was merged by this review. The seven-site corpus findings above remain
explicit data follow-up work and must not be mistaken for a green corpus.
