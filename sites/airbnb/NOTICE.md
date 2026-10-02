# NOTICE — airbnb

This directory contains a WebHarbor benchmark mirror of airbnb.com built for
offline agent evaluation. It is not affiliated with, endorsed by, or
connected to Airbnb, Inc.

- The mirror reimplements the public look-and-feel of the Airbnb stays and
  experiences flows (search, filters, listing pages, booking, wishlists,
  reviews) with original code; the Airbnb name and logo marks belong to
  Airbnb, Inc. and are used here solely to describe what the mirror models.
- Listing descriptions, reviews, amenity lists, house rules, prices and
  other textual records were captured from the public airbnb.com pages and
  API responses listed in `provenance.json` on 2026-09-30 and are the
  property of their respective hosts and guests.
- Photographic media under `static/images/upstream/` is real upstream
  imagery fetched from Airbnb's public CDN (a0.muscache.com) for benchmark
  research use; every file's exact source URL, byte length and sha256 are
  recorded in `asset_inventory.json`. If a rights holder wants media
  removed from the dataset, open an issue and it will be dropped from the
  next asset revision.
- Benchmark accounts (alice.j@test.com, bob.c@test.com, carol.d@test.com,
  dana.k@test.com) and their wishlists/bookings are authored fixtures
  modeling the authenticated flows; every listing or experience they
  reference is a real captured upstream row.
