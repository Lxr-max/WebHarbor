# cars_com mirror — notice

This directory contains a WebHarbor mirror of https://www.cars.com/
(car shopping: new/used/certified search with the upstream filter
taxonomy, listing detail pages, the dealer directory and dealer pages,
research model pages, the side-by-side compare tool, the Instant Cash
Offer valuation wizard and the car payment calculator), built from data
captured on 2026-10-13 for offline agent-benchmark use.

- All media under `static/images/` (vehicle listing photos, research
  model photos, comparison photos) is served by the real upstream image
  CDN (platform.cstatic-images.com) and was fetched from the exact
  upstream URLs the captured pages rendered. See `asset_inventory.json`
  for the per-file source URLs, byte lengths and sha256s, and
  `provenance.json` for the record-level provenance.
- Vehicle listing data (prices, mileage, trim, VIN, stock type, deal
  badges, dealer names and locations, price history rows, feature
  lists, spec summaries), dealer facts, research-page trims/specs and
  the valuation wizard's question/estimate data are frozen snapshots of
  the public cars.com pages captured with a headful Chromium that
  rendered the real site behind its Cloudflare interstitial, stored in
  the tracked `source_data/*.json` files. The untrimmed upstream
  snapshots live in the gitignored `scraped_data/`. Nothing pretends to
  be live; the pages state the snapshot date.
- Vehicle descriptions ("seller's notes") and consumer/dealer reviews
  are the captured content of the individual public listing and review
  pages served by the upstream site, kept as the functional content of
  those records for benchmark fidelity; editorial reviews are carried
  only as the short attributed "Our Expert's Take" summary excerpt.
- The four benchmark accounts (alice.j/bob.c/carol.d/dana.k @test.com)
  and their saved cars, saved searches and alerts are authored fixtures
  on top of real captured upstream listing rows (see provenance.json),
  modeled after the u_s_customs/ziprecruiter precedent.
- Cars.com is a trademark of Cars.com, LLC. This offline mirror is for
  benchmark purposes and is not affiliated with or endorsed by
  Cars.com, LLC.
