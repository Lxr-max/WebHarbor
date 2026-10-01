# red_bull mirror — notice

This directory contains a WebHarbor mirror of https://www.redbull.com/
(us-en), built from data captured on 2026-09-30 for offline
agent-benchmark use.

- All media under `static/images/` (event, athlete, film, show and story
  imagery from img.redbull.com, product can and scene shots from the
  redbull.com storyblok assets, shop product photos from the Shopify CDN,
  the Red Bull wordmark and favicon) are real files served by the upstream
  and its CDNs, fetched at the resolved URLs the live pages render. See
  `asset_inventory.json` for the per-file source URLs and sha256 sums and
  `provenance.json` for the record-level provenance. Events that share one
  upstream image reuse the same file, exactly like the upstream renders
  the same asset for related stops.
- Text content (the 18-product energy-drink catalog with ingredient cards
  and can sizes, the 100-event calendar with per-event Info/Schedule/FAQs
  content and real registration fees captured from
  participate.redbull.com, the 5 event-series hubs, the 60 athlete
  profiles with facts panels and bios, the 100-film and 100-show Red Bull
  TV catalogs with episode tables, the 40 editorial stories with full
  bodies, and the 200-product Red Bull Shop US catalog with vendors,
  size variants, SKUs and prices) is a frozen snapshot of the public
  pages and public JSON content APIs captured at the same date, stored
  in the tracked `source_data/*.json` files.
- Benchmark accounts (Alice/Bob/Carol/Dana), their shop orders, event
  registration codes and favorites are deterministic fixtures declared in
  `provenance.json` — they are not presented as upstream data.
- The SQLite seed is materialized deterministically at image build time
  (PYTHONHASHSEED=0, frozen bcrypt benchmark password); the seed is
  idempotent and byte-reproducible.
