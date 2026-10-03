# NOTICE — disney

This directory contains a WebHarbor benchmark mirror of disney.com built for
offline agent evaluation. It is not affiliated with, endorsed by, or
connected to The Walt Disney Company.

- The mirror reimplements the public look-and-feel of the Disney.com portal
  (movies, shows, games, parks finder, store, and live-shows ticketing)
  with original code; the Disney name and logo marks belong to The Walt
  Disney Company and are used here solely to describe what the mirror
  models.
- Movie synopses, credits, show descriptions, attraction descriptions,
  product descriptions and prices, tour schedules and other textual records
  were captured from the public pages of disney.com, movies.disney.com,
  shows.disney.com, games.disney.com, disneyworld.disney.go.com,
  disneystore.com, liveshows.disney.com and disneyonice.com on 2026-09-29
  and are the property of their respective right holders. See
  provenance.json for the exact source of every record.
- Photographic media under `static/images/upstream/` is real upstream
  imagery fetched from Disney's public CDNs (lumiere-a.akamaihd.net,
  cdn1.parksmedia.wdprapps.disney.com, cdn-ssl.s7.shopdisney.com) and the
  Disney wordmark under `static/icons/` comes from
  static-mh.content.disney.io, for benchmark research use; every file's
  exact source URL, byte length and sha256 are recorded in
  asset_inventory.json. If a rights holder wants media removed from the
  dataset, open an issue and it will be dropped from the next asset
  revision.
- Benchmark accounts (alice.j@test.com, bob.c@test.com, carol.d@test.com,
  dana.k@test.com) and their favorites/orders are authored fixtures
  modeling the authenticated flows; every movie, show, park entity,
  product and ice event they reference is a real captured upstream row.
