# NOTICE — yahoo_finance

This directory contains a WebHarbor benchmark mirror of finance.yahoo.com
built for offline agent evaluation. It is not affiliated with, endorsed by,
or connected to Yahoo Inc. or Yahoo Finance.

- The mirror reimplements the public look-and-feel of Yahoo Finance (market
  summary and trending tickers, symbol lookup, quote pages with the
  Summary / Statistics / Financials / Profile / History / News tabs, the
  stock screener with its predefined screens and custom filters, the
  earnings calendar, the news hub with topics and keyword search, article
  pages, and the sector & industry comparison pages) with original code;
  the Yahoo Finance name and logo marks belong to Yahoo Inc. and are used
  here solely to describe what the mirror models.
- Market data — quotes, key statistics, income statements, chart series,
  screener results, trending tickers, earnings-calendar events, news
  streams and article bodies — was captured from the public endpoints of
  finance.yahoo.com on 2026-10-01 UTC using Yahoo's documented anonymous
  crumb flow, and remains the property of its respective right holders.
  See provenance.json for the exact source of every record; raw captures
  with per-request metadata are archived under scraped_data/captures/
  (gitignored, never shipped).
- Photographic media under `static/images/upstream/` is real upstream
  imagery fetched from Yahoo's image pipelines (s.yimg.com resizes and
  provider originals on media.zenfs.com) for benchmark research use; every
  file's exact source URL, byte length and sha256 are recorded in
  asset_inventory.json. If a rights holder wants media removed from the
  dataset, open an issue and it will be dropped from the next asset
  revision.
- Benchmark accounts (alice.j@test.com, bob.c@test.com, carol.d@test.com,
  dana.k@test.com) and their watchlists / price alerts are authored
  fixtures modeling the authenticated flows; every symbol they reference
  is a real captured upstream quote.
- Market data on this mirror is a delayed snapshot captured after the
  September 30, 2026 close. It is not live data and must not be used for
  any investment decision.
