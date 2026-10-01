#!/usr/bin/env python3
"""Deterministic reviewer verifier for task Samsung--5 (samsung, r2 re-freeze).

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
 "task_id": "Samsung--5",
 "paths": [
  "galaxy-s26-ultra/buy/\\?storage=1tb",
  "carrier=unlocked",
  "/account/login/",
  "/cart/"
 ],
 "claims": [
  [
   "default model",
   "sm-s948uzsaxaa"
  ],
  [
   "default price",
   "\\$?1,?299\\.99"
  ],
  [
   "terabyte price",
   "\\$?1,?799\\.99"
  ],
  [
   "terabyte model",
   "sm-s948uzsfxaa"
  ],
  [
   "violet model",
   "sm-s948uzvfxaa"
  ],
  [
   "cart subtotal",
   "\\$?3,?599\\.98"
  ]
 ],
 "state": {
  "cart_items": {
   "added": [
    {
     "id": {
      "regex": "[1-9][0-9]*"
     },
     "cart_key": "user:1",
     "configurator": "smartphones_galaxy-s26-ultra",
     "model_code": "SM-S948UZVFXAA",
     "qty": 2,
     "unit_price": 1799.99
    }
   ]
  }
 }
}

if __name__ == "__main__":
    raise SystemExit(verify_lib.main('Samsung--5', SPEC))
