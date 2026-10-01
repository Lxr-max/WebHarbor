#!/usr/bin/env python3
"""Deterministic reviewer verifier for task Samsung--9 (samsung, r2 re-freeze).

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
 "task_id": "Samsung--9",
 "paths": [
  "/compare/\\?models=sm-f971&models=sm-f976",
  "/compare/\\?models=sm-s938&models=sm-s948",
  "/smartphones/galaxy-z-fold8-ultra/",
  "/account/login/",
  "/account/"
 ],
 "claims": [
  [
   "fold8 unfolded",
   "123\\.9 x 161\\.4 x 4\\.5"
  ],
  [
   "fold8 ultra unfolded",
   "158\\.4 x 143\\.2 x 4\\.1"
  ],
  [
   "fold8 weight",
   "\\b201\\b"
  ],
  [
   "fold8 ultra weight",
   "\\b215\\b"
  ],
  [
   "heavier model",
   "galaxy z fold8 ultra"
  ],
  [
   "second compare column",
   "galaxy s25 ultra"
  ],
  [
   "second compare dimension",
   "6\\.9\""
  ],
  [
   "second compare brightness",
   "2600\\s*nits"
  ],
  [
   "wishlist count",
   "\\b2\\b"
  ]
 ],
 "forbidden": [
  [
   "heavier honesty",
   "heavier.{0,60}(not determinable|cannot be determined)"
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
     "user_id": 4
    }
   ]
  }
 }
}

if __name__ == "__main__":
    raise SystemExit(verify_lib.main('Samsung--9', SPEC))
