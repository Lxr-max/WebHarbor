#!/usr/bin/env python3
"""Deterministic reviewer verifier for task Samsung--12 (samsung, r2 re-freeze).

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
 "task_id": "Samsung--12",
 "paths": [
  "/orders/ss-100002/",
  "/orders/ss-100001/",
  "/account/wishlist/",
  "galaxy-watch9/buy/",
  "/account/login/"
 ],
 "claims": [
  [
   "order count",
   "\\b2\\b"
  ],
  [
   "recent order number",
   "ss-100002"
  ],
  [
   "older order number",
   "ss-100001"
  ],
  [
   "recent item",
   "galaxy watch9, 40 mm, bluetooth, graphite"
  ],
  [
   "recent quantity",
   "\\b2\\b"
  ],
  [
   "delivery city",
   "ridgefield park"
  ],
  [
   "older item",
   "galaxy s26 ultra 512gb \\(unlocked\\)"
  ],
  [
   "older total",
   "\\$?1,?599\\.36"
  ],
  [
   "watch buy model",
   "sm-l340nzeaxaa"
  ],
  [
   "wishlist count",
   "\\b3\\b"
  ],
  [
   "ticket count",
   "\\b1\\b"
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
     "product_slug": "galaxy-watch9",
     "user_id": 1
    }
   ],
   "removed": [
    {
     "added_ts": {
      "regex": "[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9:]+Z"
     },
     "id": {
      "regex": "[1-9][0-9]*"
     },
     "product_slug": "galaxy-tab-s11",
     "user_id": 1
    }
   ]
  }
 }
}

if __name__ == "__main__":
    raise SystemExit(verify_lib.main('Samsung--12', SPEC))
