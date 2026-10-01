#!/usr/bin/env python3
"""Deterministic reviewer verifier for task Samsung--6 (samsung, r2 re-freeze).

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
 "task_id": "Samsung--6",
 "paths": [
  "galaxy-z-fold8-ultra/buy/\\?storage=1tb",
  "color=violet",
  "/smartphones/galaxy-z-fold8-ultra/",
  "/account/login/",
  "/cart/",
  "/account/"
 ],
 "claims": [
  [
   "default model",
   "sm-f976udgaxaa"
  ],
  [
   "default price",
   "\\$?1,?799\\.99"
  ],
  [
   "terabyte price",
   "\\$?2,?399\\.99"
  ],
  [
   "terabyte model",
   "sm-f976udgfxaa"
  ],
  [
   "violet shadow model",
   "sm-f976uzvfxaa"
  ],
  [
   "one unit line total",
   "\\$?2,?399\\.99"
  ],
  [
   "three unit line total",
   "\\$?7,?199\\.97"
  ],
  [
   "cart after remove",
   "\\bempty\\b"
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
     "product_slug": "galaxy-z-fold8-ultra",
     "user_id": 2
    }
   ]
  }
 }
}

if __name__ == "__main__":
    raise SystemExit(verify_lib.main('Samsung--6', SPEC))
