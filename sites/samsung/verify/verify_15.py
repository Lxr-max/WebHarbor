#!/usr/bin/env python3
"""Deterministic reviewer verifier for task Samsung--15 (samsung, r2 re-freeze).

Ground truth frozen from the reviewer's honest two-round r2 Chromium walks of
orch/contribute/samsung @ fac9a96e (review container webharbor:samsung-r2,
per-task control-plane reset, screenshots + initial/after DB snapshots in the
review evidence tree; every walked fact independently cross-checked against
the frozen seed database). The fix commit renders the previously-unreachable
question points (the battery capacity value on product pages; the compare
form's multi-model columns), so the r1 honest-absence gradings are now
POSITIVE anchors; stale r1-style absence answers fail via the ``forbidden``
patterns.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import verify_lib  # noqa: E402

SPEC = {
 "task_id": "Samsung--15",
 "paths": [
  "/account/signup/",
  "/watches/galaxy-watch9/",
  "/smartphones/galaxy-z-flip8/"
 ],
 "claims": [
  [
   "account name",
   "frank nova"
  ],
  [
   "account email",
   "frank\\.n@test\\.com"
  ],
  [
   "account orders",
   "\\b0\\b"
  ],
  [
   "account saved",
   "\\b0\\b"
  ],
  [
   "no tickets",
   "no tickets"
  ],
  [
   "profile name",
   "frank nova"
  ],
  [
   "flip8 price",
   "\\$?1,?049\\.99"
  ],
  [
   "wishlist count",
   "\\b1\\b"
  ]
 ],
 "state": {
  "users": {
   "added": [
    {
     "id": {
      "regex": "[1-9][0-9]*"
     },
     "name": "Frank Nova",
     "email": "frank.n@test.com"
    }
   ]
  },
  "wishlist_items": {
   "added": [
    {
     "added_ts": {
      "regex": "[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9:]+Z"
     },
     "id": {
      "regex": "[1-9][0-9]*"
     },
     "product_slug": "galaxy-watch9",
     "user_id": {
      "regex": "[1-9][0-9]*"
     }
    }
   ]
  }
 }
}

if __name__ == "__main__":
    raise SystemExit(verify_lib.main('Samsung--15', SPEC))
