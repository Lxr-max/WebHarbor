#!/usr/bin/env python3
"""Deterministic reviewer verifier for task Samsung--2 (samsung, r2 re-freeze).

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
 "task_id": "Samsung--2",
 "paths": [
  "/tvs/\\?",
  "mrn75r85hafxza",
  "sort=price-high",
  "mna89ms1bacxza",
  "/account/login/",
  "/account/"
 ],
 "claims": [
  [
   "tv total",
   "\\b42\\b"
  ],
  [
   "size filter count",
   "\\b17\\b"
  ],
  [
   "both filter count",
   "\\b2\\b"
  ],
  [
   "first tv name",
   "75 inch class micro rgb r85h"
  ],
  [
   "first tv price",
   "\\$?1,?899\\.99"
  ],
  [
   "expensive tv name",
   "89\" class micro led \\(ms1b\\)"
  ],
  [
   "expensive tv price",
   "\\$?109,?999\\.00"
  ],
  [
   "wishlist count",
   "\\b2\\b"
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
     "product_slug": "89-class-micro-led-sku-mna89ms1bacxza",
     "user_id": 3
    }
   ]
  }
 }
}

if __name__ == "__main__":
    raise SystemExit(verify_lib.main('Samsung--2', SPEC))
