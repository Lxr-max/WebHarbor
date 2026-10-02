# The Weather Network mirror — data & asset notice

Upstream: https://www.theweathernetwork.com/ (The Weather Network / Pelmorex Media Inc.)

All forecast data (current conditions, hourly, 14-day long-term, monthly
climate averages, air quality, UV, pollen, health and bug indices) in this
mirror was captured from the public Pelmorex weather APIs for 581 real
locations on 2026-09-26/27. News articles (638), video metadata (782 jwplayer
videos), active Environment Canada alerts (51) and site chrome were captured
from the corresponding public theweathernetwork.com surfaces on the same
dates; see `provenance.json` for the per-file scope. The Weather Network name
and logo are used here only to keep the mirror visually faithful to the
upstream site.

Imagery in `static/images/` (article thumbnails, author avatars, video
posters, weather condition icons, radar basemaps and overlays from the
Pelmorex map services, brand assets, and the full inline article body image
corpus) is real upstream media, byte- and hash-verified against
`asset_inventory.json` with the exact source URLs recorded per file. The
fonts in `static/fonts/` are the webfont subsets the upstream site serves.

The benchmark user accounts (alice/bob/carol/david @test.com) and their
saved locations are fictional fixture data created for this benchmark
environment. The site clock is pinned to the capture moment so every relative
display ("Updated 2 minutes ago", "It's Sunday, September 27th") matches the
frozen snapshot.
