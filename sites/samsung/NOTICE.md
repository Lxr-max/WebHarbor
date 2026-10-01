# samsung mirror — content notice

This directory contains a WebHarbor mirror of https://www.samsung.com/us/
built for offline agent benchmarks. It is not affiliated with, endorsed by,
or connected to Samsung Electronics America, Inc. or Samsung Electronics
Co., Ltd. "Samsung", "Galaxy", "Bespoke" and other marks are the property of
their respective owners and appear here only because the mirror reproduces
the public product catalog, prices, specification tables, warranty
information and support copy that the live site serves to the public.

All content records under `source_data/` were captured from the live site
and its public JSON endpoints on 2026-09-30 (see `provenance.json` for the
exact endpoints and record counts). All images under `static/images/` were
downloaded from the upstream CDNs; `asset_inventory.json` pins each file's
sha256 and exact source URL. The only authored rows are the four benchmark
user accounts and their fixture orders / wishlist entries / support tickets,
which are benchmark-account infrastructure, not upstream content.

The mirror is a benchmark artifact: prices, stock, ratings and warranty
text are a frozen snapshot and are not an offer, a quote, or authoritative
product information.
