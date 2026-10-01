#!/usr/bin/env python3
"""Deterministic reviewer verifier for task Samsung--7 (samsung, r2 re-freeze).

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
 "task_id": "Samsung--7",
 "paths": [
  "/account/login/",
  "galaxy-tab-s11/buy/",
  "/checkout/",
  "/orders/ss-"
 ],
 "claims": [
  [
   "default model",
   "sm-x930nzaaxar"
  ],
  [
   "default price",
   "\\$?1,?299\\.99"
  ],
  [
   "order number",
   "ss-[0-9]{10,}"
  ],
  [
   "order total",
   "\\$?1,?386\\.11"
  ],
  [
   "order tax",
   "\\$?86\\.12"
  ],
  [
   "order count",
   "\\b3\\b"
  ]
 ],
 "state": {
  "orders": {
   "added": [
    {
     "id": {
      "regex": "[1-9][0-9]*"
     },
     "order_no": {
      "regex": "SS-[0-9]{10,}"
     },
     "user_id": 1,
     "payment_method": "Samsung Pay",
     "subtotal": 1299.99,
     "tax": 86.12,
     "total": 1386.11,
     "status": "Processing"
    }
   ]
  },
  "order_items": {
   "added": [
    {
     "id": {
      "regex": "[1-9][0-9]*"
     },
     "order_id": {
      "regex": "[1-9][0-9]*"
     },
     "model_code": "SM-X930NZAAXAR",
     "qty": 1,
     "unit_price": 1299.99
    }
   ]
  }
 }
}

if __name__ == "__main__":
    raise SystemExit(verify_lib.main('Samsung--7', SPEC))
