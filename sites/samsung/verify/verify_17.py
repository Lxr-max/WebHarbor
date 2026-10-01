#!/usr/bin/env python3
"""Deterministic reviewer verifier for task Samsung--17 (samsung, r2 re-freeze).

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
 "task_id": "Samsung--17",
 "paths": [
  "galaxy-watch9/buy/\\?size=44mm",
  "connectivity=lte",
  "color=graphite",
  "/account/login/",
  "/cart/",
  "/checkout/"
 ],
 "claims": [
  [
   "default model",
   "sm-l340nzeaxaa"
  ],
  [
   "default price",
   "\\$?379\\.99"
  ],
  [
   "lte model",
   "sm-l355uzsaxaa"
  ],
  [
   "lte price",
   "\\$?459\\.99"
  ],
  [
   "graphite model",
   "sm-l355uzkaxaa"
  ],
  [
   "cart subtotal",
   "\\$?919\\.98"
  ],
  [
   "cart options",
   "size: 44mm"
  ],
  [
   "cart options 2",
   "connectivity: lte"
  ],
  [
   "estimated tax",
   "\\$?60\\.95"
  ]
 ],
 "state": {
  "cart_items": {
   "added": [
    {
     "id": {
      "regex": "[1-9][0-9]*"
     },
     "cart_key": "user:3",
     "configurator": "watches_galaxy-watch9",
     "model_code": "SM-L355UZKAXAA",
     "qty": 2,
     "unit_price": 459.99
    }
   ]
  }
 }
}

if __name__ == "__main__":
    raise SystemExit(verify_lib.main('Samsung--17', SPEC))
