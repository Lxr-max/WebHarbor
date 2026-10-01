#!/usr/bin/env python3
"""Deterministic reviewer verifier for task Samsung--8 (samsung, r2 re-freeze).

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
 "task_id": "Samsung--8",
 "paths": [
  "/compare/\\?models=sm-s942&models=sm-s948",
  "/compare/\\?models=sm-f776&models=sm-s942&models=sm-s948",
  "/smartphones/galaxy-s26-ultra/buy/",
  "/account/login/",
  "/account/"
 ],
 "claims": [
  [
   "s26 dimension",
   "6\\.3\""
  ],
  [
   "s26 ultra dimension",
   "6\\.9\""
  ],
  [
   "s26 weight",
   "\\b167\\b"
  ],
  [
   "s26 ultra weight",
   "\\b214\\b"
  ],
  [
   "s26 wide camera",
   "50\\.0\\s*mp"
  ],
  [
   "s26 ultra wide camera",
   "200\\.0\\s*mp"
  ],
  [
   "s26 battery",
   "4300\\s*mah"
  ],
  [
   "s26 ultra battery",
   "5000\\s*mah"
  ],
  [
   "larger battery",
   "galaxy s26 ultra"
  ],
  [
   "flip8 dimension",
   "6\\.9\""
  ],
  [
   "buy model",
   "sm-s948uzsaxaa"
  ],
  [
   "wishlist count",
   "\\b2\\b"
  ]
 ],
 "forbidden": [
  [
   "larger battery honesty",
   "larger battery.{0,60}(not determinable|cannot be determined)"
  ],
  [
   "camera honesty",
   "(no wide camera|camera resolution.{0,40}not (listed|stated))"
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
     "user_id": 4
    }
   ]
  }
 }
}

if __name__ == "__main__":
    raise SystemExit(verify_lib.main('Samsung--8', SPEC))
