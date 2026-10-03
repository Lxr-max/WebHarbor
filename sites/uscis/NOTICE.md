# uscis mirror — notice

This directory contains a WebHarbor mirror of https://www.uscis.gov/
(U.S. Citizenship and Immigration Services), built from data captured on
2026-09-28 for offline agent-benchmark use.

- All media under `static/images/` (homepage cards, citizenship and green
  card topic photography, news photos, site chrome) are real files served
  by www.uscis.gov and my.uscis.gov, fetched at the resolved URLs the live
  pages render. The form PDFs under `static/external_cache/forms/` are the
  actual USCIS form files served by www.uscis.gov. See
  `asset_inventory.json` for the per-file source URLs and `provenance.json`
  for the record-level provenance.
- Text content (topic pages, green card and citizenship guidance, form
  pages, filing-fee guidance, humanitarian and working-in-the-U.S. content,
  the newsroom, the glossary, the field-office directory and the ZIP-to-field
  office dataset, the civil surgeon locator results, the naturalization
  eligibility wizard, and the myUSCIS appointment landing page) is a frozen
  snapshot of the public pages captured at the same date and stored in the
  tracked `source_data/*.json` files.
- The fee-calculator records are the real per-form fee tables served by the
  upstream `/views/ajax` fee listing (the public data behind
  www.uscis.gov/feecalculator), and the processing-times records are the
  real `/processing-times/api/processingtime/{form}/{office}` responses,
  captured from the upstream archive because the live egov.uscis.gov host
  blocks this build network (see provenance.json for the exact capture
  notes).
- Interactive flows (Case Status Online, account sign-in with myProgress,
  the online appointment request flow, and the AR-11-style change of
  address) are reconstructed for offline benchmark use: the receipt numbers,
  case histories, benchmark accounts, appointment slots and confirmation
  numbers are mirror-native fixtures seeded from
  `source_data/benchmark_users.json`; the tool chrome (status layout,
  validation wording, related tools) follows the real USCIS tools as
  captured at the referenced URLs.
- USCIS content is a work of the United States Government and is not
  subject to copyright protection in the United States (17 U.S.C. § 105).
  Trademarks, agency seals and logos belong to their owners and are used
  here solely to keep the benchmark mirror faithful to the upstream site.
