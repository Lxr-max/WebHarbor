# trader_joes mirror — notice

This directory contains a WebHarbor mirror of https://www.traderjoes.com/,
built from data captured on 2026-09-30/10-01 for offline
agent-benchmark use.

- All media under `static/images/` (product photos, recipe and context
  imagery, guide/story art, announcement photos, category tiles, site
  chrome) are real files served by the upstream site, fetched at the
  resolved URLs the live pages render. Each file is stored as the
  upstream webp-640 rendition — the exact bytes the site serves on
  narrow screens — except three assets that upstream only publishes in
  their original format (two PNG, one animated GIF). See
  `asset_inventory.json` for the per-file source URLs and SHA-256
  checksums and `provenance.json` for the record-level provenance.
  Three additional images referenced by upstream data 404 on the live
  site; the mirror renders them as broken, exactly as the live pages do,
  and no placeholder is substituted.
- The Kalam webfonts under `static/fonts/` are the woff2 files the live
  site loads from fonts.gstatic.com.
- Text content (the product catalog with prices, descriptions, nutrition
  panels, ingredients and allergens; the recipe library; the store
  directory with addresses, phone numbers and hours; the Discover guides
  and stories; the announcements board; the entertaining articles; the
  podcast episode list; the CMS pages) is a frozen snapshot of the public
  pages and public JSON APIs captured at the same date and stored in the
  tracked `source_data/*.json` files. The upstream site fronts its APIs
  with an Akamai WAF; every capture was made through a real desktop
  Chromium session, documented in `provenance.json`.
- Interactive flows (accounts, the shopping list, the My Store
  preference, newsletter subscribe/unsubscribe, and the gift card
  balance inquiry — the upstream page delegates balance checks to an
  external partner platform) are original mirror code seeded with
  deterministic benchmark fixtures.
- The Flask application, templates, stylesheet and scripts are original
  mirror code reproducing the site's structure and visual language for
  research purposes. This mirror is not affiliated with, endorsed by, or
  connected to Trader Joe's Company. Trademarks belong to their
  respective owners.
