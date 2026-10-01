#!/usr/bin/env python3
"""Deterministic reviewer verifier for task Samsung--10 (samsung, r2 re-freeze).

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
 "task_id": "Samsung--10",
 "paths": [
  "/support/warranty/\\?category=phones-tablets-wearables",
  "model=sm-s948uzvexaa",
  "category=home-appliances&model=",
  "/support/contact/",
  "/support/contact/done/",
  "/account/login/"
 ],
 "claims": [
  [
   "category count",
   "\\b5\\b"
  ],
  [
   "s26 ultra coverage",
   "active"
  ],
  [
   "s26 ultra period",
   "12 months"
  ],
  [
   "home appliances coverage",
   "active"
  ],
  [
   "ticket number",
   "st-[0-9]{10,}"
  ],
  [
   "ticket status",
   "\\bopen\\b"
  ]
 ],
 "state": {
  "support_tickets": {
   "added": [
    {
     "id": {
      "regex": "[1-9][0-9]*"
     },
     "ticket_no": {
      "regex": "ST-[0-9]{10,}"
     },
     "user_id": 3,
     "category": "Phones, Tablets & Wearables",
     "topic": "Warranty",
     "status": "Open",
     "subject": {
      "regex": "(?i).{0,120}"
     }
    }
   ]
  }
 }
}

if __name__ == "__main__":
    raise SystemExit(verify_lib.main('Samsung--10', SPEC))
