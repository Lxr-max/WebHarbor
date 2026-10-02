# steam mirror — content notice

This directory contains a WebHarbor mirror of https://store.steampowered.com/
built for offline agent benchmarks. It is not affiliated with, endorsed by,
or connected to Valve Corporation. "Steam", the Steam wordmark and other
marks are the property of Valve Corporation and appear here only because
the mirror reproduces the public store catalog, prices, system
requirements, review feeds and news posts that the live site serves to the
public.

All content records under `source_data/` were captured from the live store
and its public JSON endpoints on 2026-10-01 (see `provenance.json` for the
exact endpoints and record counts): the search/browse facets from
`/search/results/`, per-game details and system requirements from
`/api/appdetails`, user reviews from `/appreviews`, news from the public
`ISteamNews` API, and bundles from `/bundle/` pages. All images under
`static/images/` were downloaded from the Steam CDN hosts;
`asset_inventory.json` pins each file's sha256 and exact source URL. The
only authored rows are the four benchmark user accounts and their fixture
wishlists/orders, which are benchmark-account infrastructure, not upstream
content.

The mirror is a benchmark artifact: prices, discounts, review scores and
release dates are a frozen snapshot and are not an offer, a quote, or
authoritative product information.
