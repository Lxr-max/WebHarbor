# usps mirror — notice

This directory contains a WebHarbor mirror of https://www.usps.com/ (the
United States Postal Service), built from data captured on 2026-09-28 for
offline agent-benchmark use.

- Media under `static/images/` (site chrome, quick-tool icons, page hero
  and feature art, Postal Store product imagery, newsroom photos) are
  real files served by the upstream sites, fetched at the resolved URLs
  the live pages render. See `asset_inventory.json` for the per-file
  source URLs and `provenance.json` for the record-level provenance.
- Reference data is a frozen snapshot of public upstream sources: retail
  prices, extra-service fees, PO Box fee schedules and the country price
  group directory from the official Notice 123 price list
  (pe.usps.com/text/dmm300/Notice123.htm); Individual Country Listings
  (prohibitions, restrictions, observations, customs forms) from Postal
  Explorer; the Post Office directory (names, ZIP Codes, states,
  establishment dates and postmaster rosters) from the official
  Postmaster Finder API (webpmt.usps.gov, as served by
  about.usps.com/who/profile/history/postmaster-finder/); Postal Store
  products from store.usps.com; newsroom releases and service alerts
  from about.usps.com; page copy from www.usps.com. All are stored in the
  tracked `source_data/*.json` files.
- Interactive flows (package tracking timelines, the Click-N-Ship label
  wizard, carrier pickup scheduling, Hold Mail and Change of Address
  requests, PO Box reservations, the store cart/checkout, insurance
  claims, accounts and Informed Delivery feeds) are original mirror code
  seeded with deterministic benchmark fixtures. Facility street
  addresses, phone numbers and hours in the location directory are
  deterministic mirror fixtures layered on the real Postmaster Finder
  roster (the live Find USPS Locations API is bot-protected and not
  capturable); every directory fact shown to agents that comes from
  Postmaster Finder — facility name, city, state, ZIP Code, county where
  available, establishment date and postmaster — is real upstream data.
- The Flask application, templates, stylesheet and scripts are original
  mirror code reproducing the site's structure and visual language for
  research purposes. This mirror is not affiliated with, endorsed by, or
  connected to the United States Postal Service. USPS, Priority Mail,
  Priority Mail Express, Click-N-Ship, Informed Delivery and Mr. ZIP are
  trademarks of the United States Postal Service; trademarks belong to
  their respective owners.
- Capture caveats, honestly declared: postmaster rosters are captured up
  to each city's first 12 named entries (see provenance.json), so facility
  pages show the earliest historical postmasters rather than the current
  one; a few scrape-extraction artifacts in the 2026-09-28 text snapshots
  (UTF-8 pages mis-decoded as latin-1 by the requests charset guess) are
  repaired at render time by app.py's `_fix_mojibake` — the frozen seed
  database is left byte-identical, and the scrapers now decode UTF-8
  explicitly so re-scrapes stay clean.
