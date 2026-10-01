#!/usr/bin/env python3
"""Deterministic reviewer verifier for task Samsung--4 (samsung, r2 re-freeze).

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
 "task_id": "Samsung--4",
 "paths": [
  "/smartphones/galaxy-s26-ultra/",
  "/smartphones/galaxy-s26/",
  "/smartphones/galaxy-s26-fe/",
  "/account/login/",
  "/account/wishlist/"
 ],
 "claims": [
  [
   "model code",
   "sm-s948uzvexaa"
  ],
  [
   "price",
   "\\$?1,?499\\.99"
  ],
  [
   "rating",
   "4\\.8"
  ],
  [
   "reviews",
   "\\b17628\\b"
  ],
  [
   "display dimension",
   "6\\.9\""
  ],
  [
   "resolution",
   "3120 x 1440"
  ],
  [
   "peak brightness",
   "2600 nits"
  ],
  [
   "battery capacity",
   "5000\\s*mah"
  ],
  [
   "s26 price",
   "\\$?899\\.99"
  ],
  [
   "s26 spec table",
   "\\byes\\b"
  ],
  [
   "fe price",
   "\\$?699\\.99"
  ],
  [
   "wishlist count",
   "\\b3\\b"
  ]
 ],
 "forbidden": [
  [
   "battery honesty",
   "battery.{0,40}not (stated|shown|listed|rendered)"
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
     "product_slug": "galaxy-s26-ultra",
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
    raise SystemExit(verify_lib.main('Samsung--4', SPEC))
