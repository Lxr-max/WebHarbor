# virginia_dmv mirror — notice

This directory contains a WebHarbor mirror of https://www.dmv.virginia.gov/
(Virginia Department of Motor Vehicles), built from data captured on
2026-09-29 for offline agent-benchmark use.

- All media under `static/images/` (342 specialized license plate designs at
  the upstream max_650x650 style URL that both the live search grid and the
  plate detail pages render, homepage and section card art, news photos,
  theme pin assets — 398 files, plus the 121 manual/exam images declared
  separately) are real files served by
  www.dmv.virginia.gov at the exact style URLs the live pages render. The
  form PDFs under `static/external_cache/forms/` (322 files, every English
  Driver/Vehicle/Other/Dealer/Transportation Safety form in the catalog plus
  the DMV 201 fee chart) are the actual DMV form files served by
  www.dmv.virginia.gov. See `asset_inventory.json` for the per-file sha256 +
  source URLs and `provenance.json` for the record-level provenance.
- Text content (87 content pages across Licenses & IDs, Vehicles, Moving,
  Records, Online Services, About and Safety; the 134-office location
  directory with hours/phones/services; the 342-plate catalog with fees and
  requirements; the 419-row forms catalog; the 70-item newsroom; the site
  chrome and the scam alert) is a frozen snapshot of the public pages
  captured on the same date and stored in the tracked
  `source_data/*.json` files.
- The driver's manual study guide (7 sections, 21 subsections) and the
  sample knowledge-exam bank (266 questions with answers and feedback) are
  the real records served by the upstream dmv-manuals API
  (transactions.dmv.virginia.gov/dmvapimanuals) that the live study-guide
  SPA calls. The manual's inline figures and the exam bank's picture
  questions (including the 38 road-sign questions) are the real image files
  served by the upstream dmv-manuals backend
  (transactions.dmv.virginia.gov/dmv-manuals/manuals/images/1/); the 121
  unique captured files live under `static/images/manual/` with per-file
  sha256 + source URL in `asset_inventory.json`, and the two upstream
  filename case variants that serve byte-identical art are mapped through
  `source_data/manual_image_map.json`.
- The fee schedule (`source_data/fees.json`) is transcribed 1:1 from the
  DMV 201 fee chart (08/10/2026 edition) and programmatically verified
  against its pdftotext extraction at build time.
- The DMV online-account surface (login, dashboard, address change,
  registration renewal with the real fee math, license renewal/replacement,
  plate purchase with personalization checks, record requests, receipts)
  and the Reserve-Your-Spot appointment flow are mirror-native
  reconstructions: the real account app sits behind an Okta-fed login and
  the OABS wizard behind a recaptcha-gated flow, so they cannot be mirrored
  from live sessions. The four benchmark accounts (Alice Johnson, Bob Chen,
  Carol Diaz, Dana King — password TestPass123!) and their vehicles,
  licenses, receipts and appointments are fixtures declared in
  `source_data/benchmark_users.json`; every fee, rule and receipt wording
  inside those flows is the real upstream data from the DMV 201 chart, the
  registration-renewal intro and the captured service pages. See
  `provenance.json` for the full access notes.
- DMV content is a work of the Commonwealth of Virginia. Trademarks,
  agency seals and logos belong to their owners and are used here solely
  to keep the benchmark mirror faithful to the upstream site.
- Upstream drift recorded on 2026-09-29 (fix pass; snapshot semantics,
  no action taken): the live forms catalog now lists 422 forms against the
  frozen 419-row capture, and the live home page now labels the ID card
  link "Get an ID Card" where the frozen capture reads "Get an
  Identification Card". See `provenance.json` → `upstream_drift`.
