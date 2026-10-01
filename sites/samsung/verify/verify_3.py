#!/usr/bin/env python3
"""Deterministic reviewer verifier for task Samsung--3 (samsung, r2 re-freeze).

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
 "task_id": "Samsung--3",
 "paths": [
  "/refrigerators/\\?q=family",
  "rf29db9900qdaa",
  "/laundry/\\?sort=price-low",
  "/account/login/",
  "/account/"
 ],
 "claims": [
  [
   "family hub count",
   "\\b6\\b"
  ],
  [
   "fridge name",
   "bespoke ai 4-door flex.{0,3} family hub"
  ],
  [
   "fridge price",
   "\\$?3,?799\\.00"
  ],
  [
   "fridge model",
   "rf29db9900qdaa"
  ],
  [
   "laundry name",
   "top load electric dryer sensor dry"
  ],
  [
   "laundry price",
   "\\$?599\\.00"
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
     "product_slug": "bespoke-4-door-flex-refrigerator-29-cu-ft-with-family-hub-32-and-ai-vision-in-stainless-steel-sku-rf29db9900qdaa",
     "user_id": 4
    }
   ]
  }
 }
}

if __name__ == "__main__":
    raise SystemExit(verify_lib.main('Samsung--3', SPEC))
