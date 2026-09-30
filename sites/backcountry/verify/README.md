# Backcountry — deterministic task verifiers

One verifier per benchmark task: `verify_0.py` … `verify_19.py` (+ shared
`verify_lib.py`, cross-check suite `test_verifiers.py`).

## What they check

Each verifier runs five evidence families over a recorded honest walk
(`--run_dir <run>`):

1. **Trajectory identity** — the recorded task id matches, the run is
   terminated with `agent_done`, the final answer is non-empty, every URL
   stays on the mirror origin/port of `start_url`.
2. **Per-step screenshots** — every recorded action references a PNG that
   actually decodes.
3. **Frozen seed contract** — `initial.db` matches the published seed:
   20-table row counts, schema sha256, per-table row sha256 and file md5
   `44da2a3fc213b3ac5e76ba11453baee2` (UTC clock frozen at 2026-09-30).
4. **Navigation gates** — the visited URLs prove the required pages were
   reached (search, category, brand, PDP color, cart, checkout, order
   confirmation, account areas …) with the exact query parameters. Sign-in
   is accepted either via the header link (lands on `/account`) or via the
   PDP sign-in link (`/login?next=…` auto-return) — both are honest paths.
5. **Answer checks** — the final answer contains the hardcoded frozen facts:
   phrases, numbers, money amounts (accepts $X / $X.00 / X.00 forms).
   Answer text is quote-normalized (curly → straight) before phrase
   matching, because the upstream pages render U+2019 apostrophes.
6. **Database after-state** — the exact rows the task must add/remove/change
   (order + items, cart rows, reviews, questions, wishlist, addresses) and
   *only* those; read-only tasks assert zero row drift. Runtime-variant
   cells (ids, hashes, timestamps) match `rx:` wildcards.

## Ground truth policy

All expected values are **hardcoded in the verifier files**, re-verified
during the review round against the reviewer's own independent Playwright
walks of a freshly built review container (image built from this branch;
seed md5 `44da2a3fc213b3ac5e76ba11453baee2` reproduced in-image twice).
Verifiers never read `tasks.jsonl`, so a contributor cannot move the
goalposts by editing the task text. Review-round corrections applied to the
frozen constants:

- T3 review count is **49** — the Cosmo 350 PDP renders `(49)` and
  "based on 49 ratings" (the previous 21 was cross-task contamination).
- T2's wish-list item is **"Pro Team Training Jersey - Men's"** (the page
  title; "Pro Team Jersey" is not a substring of it).
- T5's order history lists **2** orders after checkout (dana has one seeded
  order), and the "new subtotal" right after the goggles qty-2 change is
  **$799.99** (the ski binding is still in the cart at that point).
- T0's title check accepts the PDP-rendered "Tungsten Tent: 2-Person
  3-Season" (the brand renders separately above the title).
- T7 accepts "0 reviews" or a "no reviews" phrasing (the PDP renders
  "No reviews yet" for the zero-count boot).

## Review-round deepening

Tasks 2, 3, 6, 7 and 13 measured 13–14 honest atomic steps on the
reviewer's minimal-path walkthroughs (below the 15-step floor) and were
deepened in place with page-anchored follow-up questions (remaining
wish-list item price, Cosmo 350-R price, Copper Spur price from the wish
list, rope color count, first related product + empty-cart message). The
deepened texts stay <= 100 words, keep the 7-key row shape, and re-measure
at 15–17 honest steps.

## Usage

```bash
python3 verify/verify_0.py --run_dir <evidence>/runs/minimal_r1/task_0
# -> {"task_id": "Backcountry--0", "pass": true, "reason": "all checks passed", ...}
```

Cross-check suite — honest fixtures are the reviewer's recorded walks
(absolute path in `test_verifiers.py`), plus a full negative battery:
no-op, answer-only, wrong-answer, stale-DB (except the documented net-zero
tasks 2/6/11), wrong task_id, off-site URL, not-terminated, bad PNG,
pre-mutated seed, foreign after.db:

```bash
python3 -m pytest verify/test_verifiers.py -q   # 239 passed
```
