# airbnb verifier contract (reviewer-authored, r3 contract-synced)

This directory holds the deterministic grading contract for the 20
`Airbnb--*` benchmark tasks. The r1 contract was written by the reviewer
on `orch/review/airbnb` @ `b2a83c23` from contribution `22e1808b`; the
contribution r2 fix round synced it into `orch/contribute/airbnb` and
re-froze every ground truth that the fixes changed; the r3 fix round
(fed30bf9: B4 residual repr family unpacked + T10 depth re-anchor)
re-froze verify_10 (booking 3/3 + rebook_guests=3) and lifted the
verify_8 KNOWN-GAP. This branch's r3 contract-sync re-freezes the
contract from the re-reviewer's own independent walks (container
`wh-airbnb-r3review` @ 49116/50116/51116, image built from the fixed
tree @ fed30bf9 through the real Dockerfile airbnb block).

## Layout

- `verify_lib.py` — shared deterministic contract:
  1. **Package identity** (fail-closed): `task_id` matches, `terminated`
     with `agent_done`, non-empty final answer, every recorded URL on the
     same loopback origin AND port as `start_url`, every referenced
     screenshot a decodable PNG.
  2. **Seed identity gate** (fail-closed): the initial DB snapshot must BE
     the frozen in-image seed — table counts
     `{destinations: 8, users: 4, listings: 96, experiences: 80,
     wishlists: 5, reviews: 1141, review_tags: 738, wishlist_items: 10,
     bookings: 4}`, schema sha256 `634ac0db…`, rows sha256 `e7c5d246…`,
     file md5 `03a6558e…` / sha256 `74d155d6…` (re-frozen in the r2 fix
     round; the schema digest is unchanged).
     The reviewer's independent r3 image build
     (`webharbor:airbnb-r3review`, built from a Containerfile that
     reproduces the real Dockerfile airbnb block verbatim: same base
     digest, `--require-hashes` dependency lock, the 1251-asset inventory
     gate, `PYTHONHASHSEED=0` seed build) reproduces the seed
     byte-identically (the r3 changes are render-layer only, so the seed
     equals the r2 freeze), and every per-task reset snapshot matched
     (3/3 rounds byte-identical).
  3. **Navigation gates** (anti knowledge-shortcut): the agent must have
     opened the on-site surfaces the task names — the Stays SERPs with the
     exact filter query strings (e.g. `guest_favorite=1`, `amenities=hot+tub`,
     `sort=price_asc`), the listing PDPs, the all-reviews pages, the
     Experiences SERPs/categories, the book/confirm flows, Trips,
     Wishlists, login/signup.
  4. **Answer checks**: token / phrase / number / money / set-coverage
     checks against ground truth HARDCODED in each `verify_<n>.py` (never
     in `tasks.jsonl`). Runtime booking codes are random (`HM` + 8
     `[A-Z0-9]`), so the answer's code is cross-checked against the
     booking row the after-state DB actually gained.
  5. **DB after-state**: read-only tasks require every table
     row-identical to the seed; stateful tasks require the exact allowed
     row delta (signup `users` row, `wishlists` / `wishlist_items` rows,
     `bookings` row with the frozen listing/experience id, window, guests
     and nights-x-nightly total, cancellation status) and nothing else.

- `verify_0.py` … `verify_19.py` — one verifier per task. Ground truth is
  re-frozen in the r2 fix round from the contributor's real Playwright
  rounds on the rebuilt fix container (fresh reset + fresh context per
  task) and from the rebuilt seed DB. Every r1 KNOWN-GAP was fixed in the
  r2 round (canonical amenity panel, experiences city selector, SERP card
  review counts, the Airbnb--6 quote-window fixture re-order, honest
  not-captured notes replacing the unanswerable Airbnb--15 / Airbnb--3 /
  Airbnb--14 asks, structured experience-page rendering); the affected
  verifiers document their R2 RE-FREEZE notes, and the remaining truth is
  fully gated.

- `test_verifiers.py` — 112 adversarial cases: 20 honest fixtures PASS
  (all 20 are real Playwright rounds on the r2 fix container — with every
  r1 UI blocker fixed, no intended-path substitutes are needed); no-op
  ×20, answer-only shortcut ×20, wrong-answer ×20, stale-DB ×11,
  stray-writes ×8, tampered-package ×7 and task-confusion ×4 negatives
  all FAIL — zero false positives.

## Usage

```bash
python3 verify_0.py --run_dir <trajectory dir>       # initial.db/after.db
python3 verify_0.py --run_dir DIR --initial_db P --after_db P
python3 -m pytest test_verifiers.py -q               # 112 adversarial cases
```

Each verifier prints a JSON verdict
`{task_id, pass, reason, evidence[]}` and exits 0 on PASS, 1 on FAIL.

## Contract coupling

`tasks.jsonl` carries `verifier_path` + `judge_rubric` appended after the
5 original contributor keys (the 5-key prefix stays byte-identical; there
is never an answer key; rubrics are English rules only).
`scripts_dev/validate_tasks.py` enforces the 7-key reviewer shape.
