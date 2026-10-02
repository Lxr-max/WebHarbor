# statista mirror — data & asset notice

Upstream: https://www.statista.com/ (Statista GmbH)

All statistic titles, chart data, metadata (last-update dates, regions,
survey periods, sources), summary and description text, topic pages with
their editor's picks / key insights / key figures, report details and
tables of contents, industry taxonomy, and Market Insights (outlook)
highlights / definitions / analyst opinions in this mirror were captured
from the public statista.com surfaces listed in `provenance.json` on
2026-09-26 with browser-profile fetchers (Playwright; see the harvest
scripts' normalization notes). They are Statista's public-page material,
mirrored for offline benchmarking. The Statista name and logo are used
here only to keep the mirror visually faithful to the upstream site.

The Market Insights "Market definition" and "Analyst Opinion" prose is
served from the tracked `source_data/outlook_market_content.json` capture
of the same live pages (the seeder's first pass had recorded the section
navigation labels instead of the opinion text, and no definitions); the
frozen seed database bytes are untouched by that content fix.

Design language: the mirror is pinned to the classic white Statista page
chrome (215x42 wordmark, single-row header with mega-menu navigation,
dark-blue footer) captured on 2026-09-26, applied uniformly to every page
— including the topic pages, which the live site also serves with the
white header. The live site has since started rolling out a darker
unified navigation bar on some surfaces (homepage, statistic and report
pages); that newer chrome is outside this frozen capture and is
intentionally not mirrored.

Statistics whose exact values are behind the upstream paywall for
anonymous visitors (premium statistics) keep their real titles and
metadata but reproduce the upstream masked-chart pattern; no paywalled
figure is redistributed.

The benchmark user accounts (alice/bob/carol/david @test.com), their
account tiers, favorites, and download history are fictional fixture
data created for this benchmark environment.

Imagery in `static/images/` (statistic chart thumbnails and hero
previews, report covers, Market Insights segment illustrations, favicon)
and the fonts in `static/fonts/` (Open Sans, Apache-2.0) are real
statista.com media captured from the CDN URLs recorded in
`asset_inventory.json`.
