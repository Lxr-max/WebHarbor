#!/usr/bin/env python3
"""Deterministic reviewer verifier for task Samsung--14 (samsung, r2 re-freeze).

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
 "task_id": "Samsung--14",
 "paths": [
  "/search/\\?q=family",
  "rf29db9900qdaa",
  "/search/\\?q=buds",
  "/search/\\?q=case",
  "/audio/galaxy-buds4-pro/",
  "/account/login/",
  "/account/"
 ],
 "claims": [
  [
   "family hub results",
   "\\b9\\b"
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
   "buds first result",
   "clip case with carabiner"
  ],
  [
   "buds first price",
   "\\$?15\\.00"
  ],
  [
   "case results",
   "\\b219\\b"
  ],
  [
   "wishlist count",
   "\\b3\\b"
  ]
 ],
 "forbidden": [
  [
   "buds first result confusion",
   "first result.{0,40}galaxy buds3 fe"
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
     "product_slug": "galaxy-buds4-pro",
     "user_id": 2
    }
   ]
  }
 }
}

if __name__ == "__main__":
    raise SystemExit(verify_lib.main('Samsung--14', SPEC))
