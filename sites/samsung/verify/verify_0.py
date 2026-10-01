#!/usr/bin/env python3
"""Deterministic reviewer verifier for task Samsung--0 (samsung, r2 re-freeze).

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
 "task_id": "Samsung--0",
 "paths": [
  "/smartphones/\\?",
  "/smartphones/galaxy-a17-5g/",
  "/smartphones/galaxy-z-fold8-ultra/",
  "/account/login/",
  "/account/"
 ],
 "claims": [
  [
   "catalog total",
   "\\b42\\b"
  ],
  [
   "galaxy z count",
   "\\b11\\b"
  ],
  [
   "cheapest name",
   "galaxy a17 5g 128gb \\(unlocked\\)"
  ],
  [
   "cheapest price",
   "\\$?249\\.99"
  ],
  [
   "cheapest rating",
   "4\\.3"
  ],
  [
   "cheapest reviews",
   "\\b3481\\b"
  ],
  [
   "fold8u price",
   "\\$?1,?799\\.99"
  ],
  [
   "wishlist count",
   "\\b4\\b"
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
     "product_slug": "galaxy-a17-5g",
     "user_id": 1
    }
   ]
  }
 }
}

if __name__ == "__main__":
    raise SystemExit(verify_lib.main('Samsung--0', SPEC))
