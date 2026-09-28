# sourceforge — deterministic task verifiers

One verifier per task (`verify_0.py` … `verify_20.py`) plus the shared
`verify_lib.py`. Ground truth is HARDCODED in each verifier module (frozen from
the deterministic seed built at image time; rows digest `520501ac…`, schema
digest `aa61b172…`). The file-level SQLite bytes depend on the host SQLite
library; the contract is those two digests plus `SEED_COUNTS`, not a host md5.
Ground truth never lives in `tasks.jsonl`, which carries `verifier_path` and
`judge_rubric` (rules-only English, no answer key).

## Contract (fail-closed)

1. **Package identity** — task_id match, `terminated`/`agent_done`, non-empty
   answer, every URL on the same loopback origin:port, every referenced
   screenshot a decodable PNG.
2. **Navigation gates** — the agent must have actually opened the on-site
   surfaces the task names (search results, project/reviews/files/stats pages,
   trackers, forums, wiki, news, business directory, auth/account). A correct
   answer without the navigation is a knowledge shortcut = FAIL.
3. **Answer checks** — phrases and numbers must be standalone tokens owned by
   the named subject (project, ticket, file, thread, or label). A number that
   only occurs as a substring of a larger count, or that is attached to a
   different subject in the same answer, is a FAIL. `make_verifiers.py`
   refuses to emit an unbound number, K/M/B abbreviation, or ISO date.
4. **DB after-state** — read-only tasks require the after-DB row-identical to
   the frozen seed; stateful tasks (7, 13, 18) require the exact allowed delta
   (bookmark + 5-star review + counter bump / new user with country DE /
   bookmark swap + 4-star review + counter bump) and nothing else.

## Usage

```bash
# one task (run dir = trajectory.json + screenshots/ + initial.db + after.db)
python3 verify/verify_7.py --run_dir runs/SourceForge--7

# the whole contract test suite (needs the review container for the seed)
python3 -m pytest verify/tests -q
```

`make_verifiers.py` regenerates `verify_N.py` from the frozen spec table.
`append_rubrics.py` rewrites `judge_rubric` in place; it does not add keys.
