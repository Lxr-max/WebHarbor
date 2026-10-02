# carvana mirror — notice

This directory contains a WebHarbor mirror of https://www.carvana.com/
(used-car e-commerce: car search with the upstream filter taxonomy — make,
model, body style, price, year, mileage, fuel, transmission, drivetrain,
single-owner, accident-free — plus pagination and sorting; vehicle detail
pages with photo galleries, key specs, features, installed options,
vehicle history, inspection highlights and owner reviews; the per-vehicle
financing monthly-payment estimator; the checkout purchase flow with
delivery scheduling; the sell-your-car instant-offer flow; the account
area with saved cars, orders with status timelines and profile; and the
upstream content pages), built from data captured on 2026-09-29 for
offline agent-benchmark use.

- All media under `static/images/` is served by the real upstream hosts
  (Carvana's cdnblob card CDN, the vexgateway photo pipeline that serves
  each vehicle's stabilized 360-spin frames and hero shots, and the
  site's brand assets) and was fetched from the exact upstream URLs. See
  `asset_inventory.json` for the per-file source URLs, byte lengths and
  sha256s and `provenance.json` for the record-level provenance.
- Text content (the 1,500+-vehicle inventory corpus with prices, mileage,
  trims, VINs, locations, badges and monthly-payment terms; the full
  vehicle-detail records with specs, features, options, narratives,
  inspection data and history flags for the 54 deep-captured vehicles;
  the owner reviews; the upstream search-page totals; and the content
  pages) is a frozen snapshot of the public carvana.com pages captured
  with a headful Chromium that rendered the real site, stored in the
  tracked `source_data/*.json` files. The untrimmed upstream snapshots
  live in the gitignored `scraped_data/`. Nothing pretends to be live;
  the pages state the snapshot date.
- The upstream search reports its live inventory total (53,866 cars when
  captured); the mirror serves the captured subset and states both
  numbers on the search page rather than faking the upstream total.
- The financing estimator implements the standard amortization formula
  (M = P·r/(1−(1+r)^−n)) over the APR the upstream captured per vehicle
  (6.99% default; credit-tier APRs as the upstream soft-pull modal
  presents them) and the captured estimated taxes & fees, so every
  displayed payment is recomputable by hand.
- The four benchmark accounts (alice.j/bob.c/carol.d/dana.k @test.com)
  and their saved cars, orders with delivery schedules and status
  timelines, profile data and trade-in offer are authored fixtures on
  top of real captured upstream vehicle rows (see provenance.json),
  modeled after the u_s_customs/zara/ziprecruiter precedent. The
  sell-your-car instant offer is computed deterministically from a
  stable VIN hash anchored on the captured KBB valuation data.
- Carvana is a registered trademark of Carvana Co. This offline mirror
  is for benchmark purposes and is not affiliated with or endorsed by
  Carvana Co.
