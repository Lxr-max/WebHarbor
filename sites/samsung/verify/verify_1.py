#!/usr/bin/env python3
"""Deterministic reviewer verifier for task Samsung--1 (samsung, r2 re-freeze).

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
 "task_id": "Samsung--1",
 "paths": [
  "/mobile-accessories/\\?",
  "ef-cs947ctegus",
  "/account/login/",
  "/account/"
 ],
 "claims": [
  [
   "case search count",
   "\\b181\\b"
  ],
  [
   "cases and covers count",
   "\\b85\\b"
  ],
  [
   "top case name",
   "galaxy s26\\+ clear magnet case, transparent"
  ],
  [
   "top case price",
   "\\$?49\\.99"
  ],
  [
   "wishlist count",
   "\\b3\\b"
  ]
 ],
 "state": {
  "wishlist_items": {
   "added": [
    {
     "added_ts": {
      "regex": "[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9:]+Z"
     },
     "id": {
      "regex": "[1-9][0-9]*"
     },
     "product_slug": "galaxy-s26-plus-clear-magnet-case-transparent-sku-ef-cs947ctegus",
     "user_id": 2
    }
   ]
  }
 }
}

if __name__ == "__main__":
    raise SystemExit(verify_lib.main('Samsung--1', SPEC))
