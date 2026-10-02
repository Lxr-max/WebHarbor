# verizon mirror — notice

This directory contains a WebHarbor mirror of https://www.verizon.com/,
built from data captured on 2026-09-29 for offline agent-benchmark use.

- All media under `static/images/` (device gallery shots, store
  interior/exterior photos, homepage hero shots, the Verizon wordmark) are
  real files served by www.verizon.com and its CDNs (ss7.vzw.com,
  assets.verizon.com), fetched at the resolved URLs the live pages render.
  See `asset_inventory.json` for the per-file source URLs and
  `provenance.json` for the record-level provenance. Authorized-retailer
  store photos that the CDN serves with 403 were not fetchable; those
  stores render no photo block instead of a placeholder.
- Text content (the Simplicity Plan and Verizon Prepaid plan pricing and
  rules, the 24-device catalog with colors, storage, financing terms and
  spec-compare rows, the store directory with per-day hours and services,
  the return policy, the contact-us numbers and hours, the network support
  and trade-in program pages) is a frozen snapshot of the public pages
  captured at the same date and stored in the tracked `source_data/*.json`
  files.
- Benchmark accounts (users, lines, bills, usage, orders), the protection
  plans, the trade-in estimate matrix and the troubleshoot wizard flows
  are deterministic fixtures declared in `provenance.json` — they are not
  presented as upstream data.
- The SQLite seed is materialized deterministically at image build time
  (PYTHONHASHSEED=0, frozen bcrypt benchmark password).
- The Samsung Galaxy A17 5G device record carries its real upstream
  single-capacity config block ("Storage: 128 GB", "Free shipping by
  Thursday with new line") from the frozen 2026-09-29 capture of the live
  PDP, re-verified against the live page on the fix date; the depth-fix
  seed digest changed only through that devices-row completion.
