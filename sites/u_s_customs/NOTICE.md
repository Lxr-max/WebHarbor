# u_s_customs mirror — notice

This directory contains a WebHarbor mirror of https://www.cbp.gov/
(U.S. Customs and Border Protection), built from data captured on
2026-09-28 for offline agent-benchmark use.

- All media under `static/images/` (homepage cards, news release photos,
  careers photography, site chrome) are real files served by the upstream
  sites, fetched at the resolved URLs the live pages render. The form PDFs
  under `static/external_cache/forms/` are the actual CBP form files served
  by www.cbp.gov. See `asset_inventory.json` for the per-file source URLs
  and `provenance.json` for the record-level provenance.
- Text content (travel pages, ESTA/I-94/Trusted Traveler Program reference
  copy, border wait times snapshots from bwt.cbp.gov, the port-of-entry
  directory, news releases, the forms catalog, trade guidance and USAJOBS
  postings surfaced by careers.cbp.gov) is a frozen snapshot of the public
  pages captured at the same date and stored in the tracked
  `source_data/*.json` files.
- Interactive traveler flows (the ESTA application wizard, I-94 retrieval,
  Trusted Traveler applications and interview scheduling, saved
  crossings/ports/forms/jobs, accounts) are original mirror code seeded
  with deterministic benchmark fixtures.
- The per-crossing hourly wait-time graphs on bwt.cbp.gov
  (/api/bwtwaittimegraph) served no data for the snapshot date, so the
  crossing detail pages here do not render an hourly chart; the current
  per-lane snapshot (delays, lanes open, update times) is complete.
- The Flask application, templates, stylesheet and scripts are original
  mirror code reproducing the site's structure and visual language for
  research purposes. This mirror is not affiliated with, endorsed by, or
  connected to U.S. Customs and Border Protection or the Department of
  Homeland Security. Works of the U.S. federal government are in the
  public domain; trademarks belong to their respective owners.
