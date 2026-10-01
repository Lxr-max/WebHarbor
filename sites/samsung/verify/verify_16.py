#!/usr/bin/env python3
"""Deterministic reviewer verifier for task Samsung--16 (samsung, r2 re-freeze).

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
 "task_id": "Samsung--16",
 "paths": [
  "/shop/all/",
  "/tablets/",
  "/watches/",
  "/audio/",
  "/audio/galaxy-buds3-fe/",
  "/tvs/",
  "/orders/",
  "/orders/ss-100003/",
  "galaxy-watch9/buy/",
  "/account/login/"
 ],
 "claims": [
  [
   "shop all total",
   "\\b505\\b"
  ],
  [
   "tablets count",
   "\\b11\\b"
  ],
  [
   "watches count",
   "\\b14\\b"
  ],
  [
   "audio count",
   "\\b3\\b"
  ],
  [
   "audio product name",
   "galaxy buds3 fe, gray"
  ],
  [
   "audio product price",
   "\\$?149\\.99"
  ],
  [
   "tvs count",
   "\\b42\\b"
  ],
  [
   "order number",
   "ss-100003"
  ],
  [
   "order item",
   "galaxy z fold8 ultra 256gb \\(unlocked\\)"
  ],
  [
   "watch buy model",
   "sm-l340nzeaxaa"
  ]
 ],
 "state": {}
}

if __name__ == "__main__":
    raise SystemExit(verify_lib.main('Samsung--16', SPEC))
