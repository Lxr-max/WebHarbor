#!/usr/bin/env python3
"""Deterministic reviewer verifier for task Samsung--18 (samsung, r2 re-freeze).

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
 "task_id": "Samsung--18",
 "paths": [
  "galaxy-z-flip8/buy/\\?storage=512gb",
  "/account/login/",
  "/cart/",
  "/smartphones/galaxy-z-flip8/",
  "galaxy-z-flip8/buy/"
 ],
 "claims": [
  [
   "default model",
   "sm-f776ulgaxaa"
  ],
  [
   "default price",
   "\\$?1,?049\\.99"
  ],
  [
   "512gb model",
   "sm-f776ulgexaa"
  ],
  [
   "512gb price",
   "\\$?1,?249\\.99"
  ],
  [
   "cart subtotal",
   "\\$?2,?499\\.98"
  ],
  [
   "cart item count",
   "\\b2\\b"
  ],
  [
   "new subtotal",
   "\\$?1,?049\\.99"
  ],
  [
   "new options",
   "storage: 256gb"
  ]
 ],
 "state": {
  "cart_items": {
   "added": [
    {
     "id": {
      "regex": "[1-9][0-9]*"
     },
     "cart_key": "user:2",
     "configurator": "smartphones_galaxy-z-flip8",
     "model_code": "SM-F776ULGAXAA",
     "qty": 1,
     "unit_price": 1049.99
    }
   ]
  }
 }
}

if __name__ == "__main__":
    raise SystemExit(verify_lib.main('Samsung--18', SPEC))
