# NOTICE — nyse

This directory contains a WebHarbor benchmark mirror of nyse.com built for
offline agent evaluation. It is not affiliated with, endorsed by, or
connected to Intercontinental Exchange, Inc. or the New York Stock
Exchange.

- The mirror reimplements the public look-and-feel of the NYSE portal
  (listings directory, quote pages, IPO Center, the Bell calendar, markets
  and the exchange history) with original code; the NYSE name and logo
  marks belong to Intercontinental Exchange, Inc. and are used here solely
  to describe what the mirror models.
- Quote payloads, company facts, board rosters, options chains, price
  histories, IPO tables, bell-calendar events and the CMS copy were
  captured from the public pages and public JSON APIs of www.nyse.com on
  2026-09-29/30 and remain the property of their respective right
  holders. See provenance.json for the exact source of every record.
- Photographic media under `static/images/upstream/` is real upstream
  imagery fetched from www.nyse.com's public asset hosts (bell-ceremony
  artwork, homepage collage and feature images, the listings hero, and the
  history-of-NYSE photo collection), for benchmark research use; every
  file's exact source URL, byte length and sha256 are recorded in
  asset_inventory.json. If a rights holder wants media removed from the
  dataset, open an issue and it will be dropped from the next asset
  revision.
- Benchmark accounts (alice.j@test.com, bob.c@test.com, carol.d@test.com,
  dana.k@test.com) and their watchlists / price alerts are authored
  fixtures modeling the authenticated flows; every symbol they reference
  is a real captured upstream quote.
- Market data on this mirror is a delayed snapshot captured on
  2026-09-29/30 and is not live data; it must not be used for any
  investment decision.
