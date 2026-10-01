#!/usr/bin/env python3
"""Deterministic reviewer verifier for task Samsung--19 (samsung, r2 re-freeze).

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
 "task_id": "Samsung--19",
 "paths": [
  "/smartphones/galaxy-s25-ultra/",
  "/compare/\\?models=sm-s938&models=sm-s948",
  "/smartphones/galaxy-z-flip8/",
  "/account/login/",
  "/account/"
 ],
 "claims": [
  [
   "model code",
   "sm-s938uzbavzw"
  ],
  [
   "price",
   "\\$?1,?299\\.99"
  ],
  [
   "rating",
   "4\\.8"
  ],
  [
   "reviews",
   "\\b30691\\b"
  ],
  [
   "display dimension",
   "6\\.9\""
  ],
  [
   "peak brightness",
   "2600\\s*nits"
  ],
  [
   "s25 ultra weight",
   "\\b218\\b"
  ],
  [
   "s26 ultra weight",
   "\\b214\\b"
  ],
  [
   "heavier model",
   "galaxy s25 ultra"
  ],
  [
   "flip8 price",
   "\\$?1,?049\\.99"
  ],
  [
   "wishlist count",
   "\\b4\\b"
  ]
 ],
 "forbidden": [
  [
   "heavier honesty",
   "heavier.{0,60}(not determinable|cannot be determined)"
  ],
  [
   "wrong heavier model",
   "galaxy s26 ultra is heavier"
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
     "product_slug": "galaxy-s25-ultra",
     "user_id": 1
    }
   ]
  }
 }
}

if __name__ == "__main__":
    raise SystemExit(verify_lib.main('Samsung--19', SPEC))
