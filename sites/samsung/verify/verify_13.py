#!/usr/bin/env python3
"""Deterministic reviewer verifier for task Samsung--13 (samsung, r2 re-freeze).

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
 "task_id": "Samsung--13",
 "paths": [
  "/support/warranty/\\?category=phones-tablets-wearables",
  "model=sm-f776ulgaxaa",
  "/support/contact/",
  "/support/contact/done/",
  "/account/login/",
  "/account/"
 ],
 "claims": [
  [
   "flip8 coverage",
   "active"
  ],
  [
   "flip8 period",
   "12 months"
  ],
  [
   "ticket number",
   "st-[0-9]{10,}"
  ],
  [
   "ticket status",
   "\\bopen\\b"
  ],
  [
   "ticket on account",
   "(account|listed)"
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
     "user_id": 4,
     "category": "Phones, Tablets & Wearables",
     "topic": "Repair",
     "status": "Open"
    }
   ]
  }
 }
}

if __name__ == "__main__":
    raise SystemExit(verify_lib.main('Samsung--13', SPEC))
