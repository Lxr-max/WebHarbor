#!/usr/bin/env python3
"""Deterministic reviewer verifier for task Samsung--11 (samsung, r2 re-freeze).

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
 "task_id": "Samsung--11",
 "paths": [
  "/support/warranty/\\?category=tv-display-home-theater",
  "category=phones-tablets-wearables&model=sm-l340nzeaxaa",
  "galaxy-s26-ultra/buy/\\?storage=512gb",
  "/watches/galaxy-watch9/buy/"
 ],
 "claims": [
  [
   "faq count",
   "\\b7\\b"
  ],
  [
   "validate answer",
   "error in your warranty expiration"
  ],
  [
   "tv coverage",
   "active"
  ],
  [
   "tv period",
   "12 months"
  ],
  [
   "watch coverage",
   "active"
  ],
  [
   "512gb model",
   "sm-s948uzsexaa"
  ],
  [
   "512gb price",
   "\\$?1,?499\\.99"
  ],
  [
   "watch price",
   "\\$?379\\.99"
  ],
  [
   "watch buy model",
   "sm-l340nzeaxaa"
  ]
 ],
 "state": {}
}

if __name__ == "__main__":
    raise SystemExit(verify_lib.main('Samsung--11', SPEC))
