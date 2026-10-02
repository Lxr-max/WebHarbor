# TourRadar mirror — notice

This directory contains a WebHarbor mirror of https://www.tourradar.com/,
built from data captured on 2026-09-27 for offline agent-benchmark use.

- All media under `static/images/` (tour photography, traveler avatars,
  review photos, moments, operator logos, destination heroes, site chrome)
  are real files served by the upstream CDN, fetched at the resolved URLs the
  live pages render. See `asset_inventory.json` for the per-file source URLs
  and `provenance.json` for the record-level provenance.
- Text content (tour names, itineraries, departure dates, prices, reviews,
  Q&A, destination copy) is a frozen snapshot of the public pages captured at
  the same date and stored in the tracked `source_data_*.json` files.
- The Flask application, templates, stylesheet and scripts are original
  mirror code reproducing the site's structure and visual language for
  research purposes. This mirror is not affiliated with, endorsed by, or
  connected to TourRadar Inc.
- Trademarks and copyrighted materials belong to their respective owners.
