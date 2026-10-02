# us_appliance — upstream content notice

This directory contains a WebHarbor mirror of https://www.us-appliance.com/
(BigCommerce storefront, appliance e-commerce). Product names, prices,
specifications, descriptions, images, brand lists, rebate offers, financing
copy, delivery rules, FAQ text and customer reviews were captured from the
public storefront (anonymous requests) on 2026-09-28/29.

- `source_data_*.json` are frozen snapshots of that capture (see
  `provenance.json` for scope and method).
- `static/images/` contains media downloaded from the upstream CDN
  (cdn11.bigcommerce.com) and ShopperApproved; every file's source URL, byte
  size and sha256 is pinned in `asset_inventory.json`.
- The mirror is a benchmark environment: accounts, carts, orders and
  order-tracking events are mirror-native fixtures built deterministically by
  `seed_data.py`; no real customer data is included. Benchmark users use the
  shared WebHarbor test password.
- Two small behaviors are mirror-added on top of the frozen capture: every
  state-changing POST form carries a CSRF token (WebHarbor-wide convention;
  the read-only ZIP-availability JSON endpoint stays open for the product-page
  AJAX check), and `static/js/site.js` translates the upstream
  `#filter_on-sale.filter=...` hash URLs (e.g. the deals-page "on sale today"
  links) into the equivalent server-side `?on_sale=1` filtered grid, matching
  how BigCommerce resolves the same links client-side.
- Captured content belongs to US Appliance / its manufacturers and is used
  here for research/benchmark purposes only.
