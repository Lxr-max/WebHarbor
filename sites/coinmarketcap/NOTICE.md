# coinmarketcap — NOTICE

This directory mirrors https://coinmarketcap.com/ for the WebHarbor
deterministic offline benchmark. It is a frozen snapshot of the upstream
site taken 2026-09-29/30 UTC:

- All coin, exchange, market, category, leaderboard and glossary data in
  `source_data/*.json` was captured from coinmarketcap.com and
  api.coinmarketcap.com (the site's own public data plane) with plain HTTP
  plus a headless Chromium for the client-rendered islands. See
  `provenance.json` for the full source map and trim policy.
- All images under `static/images/` (coin logos, exchange logos, 7-day
  sparkline SVGs, menu icons, brand assets) were fetched from their exact
  upstream URLs (s2/s3.coinmarketcap.com); every file's sha256 and source
  URL is recorded in `asset_inventory.json`.
- The four benchmark accounts (alice.j / bob.c / carol.d / dana.l
  @test.com, password `TestPass123!`) are authored fixtures following the
  u_s_customs precedent: their watchlists reference real captured coins.
- Deviation from upstream, declared: upstream signup is captcha-gated
  (captured upstream response: error 1017 "Need Captcha Verification
  again"); the mirror's signup accepts email + password without the
  captcha so account flows are drivable offline. Login error text, field
  labels and the guest watchlist prompt are the exact captured upstream
  strings.
- Deviation from upstream, declared: the homepage "Sentiment" column is
  omitted because the homepage data plane returns no sentiment data for its
  rows — every row of the captured aggr/v3/web/homepage response (the data
  plane the live homepage table renders from) has socialMetrics null and
  carries no sentiment/vote field, so upstream renders the column's default
  neutral state. Captured verbatim, archived tracked at
  `source_data/captures/aggr_web_homepage.json` (with a .meta.json sidecar:
  url, status, timestamp).
- Prices do not tick: this is a snapshot, not a live market feed.
