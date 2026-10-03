# ups mirror — data & asset notice

Upstream: https://www.ups.com/ (United Parcel Service of America, Inc., US market)

Content captured from the public www.ups.com website on 2026-09-28 and stored
in the tracked `source_data/` snapshots (see `provenance.json` for the capture
scope and per-source URLs):

- Domestic service descriptions and commitments (UPS Next Day Air Early,
  Next Day Air, Next Day Air Saver, 2nd Day Air A.M., 2nd Day Air, 3 Day
  Select, Ground, Ground Saver) from the UPS Retail Rate and Service Guide
  (retail-rates-us-en.pdf, effective 2026-09-07) and the shipping services
  pages.
- Retail shipping quotes for eight origin/destination markets at weights
  1/5/15/40 lbs (plus a residential-destination variant), captured from the
  live Calculate Time and Cost wizard (wwwapps.ups.com/ctc) on 2026-09-28,
  including per-service transportation charge, Delivery Area Surcharge and
  Fuel Surcharge breakdowns, latest pickup times, schedule-by times, transit
  days, guaranteed flags and billable weights.
- 240 UPS locations (The UPS Store, UPS Access Points, Customer Centers,
  Drop Boxes, Authorized Shipping Outlets, retail chains) captured from the
  UPS Location Finder XML API (widgets.ups.com/api/ups.app/xml/Locator) as
  invoked by the ups.com header locator: names, street addresses, phones,
  coordinates, operating hours, latest air/ground drop-off times and service
  offerings for twelve ZIP searches (10001, 60601, 30301, 94105, 73301,
  98101, 02110, 33101, 90012, 80202, 19103, 45202).
- Tracking application UI strings and error copy from the ups.com tracking
  application lookup data (webapis.ups.com/track/api/WemsData/GetLookupData).
- Support articles (Understanding Tracking Status, UPS Delivery Notice, UPS
  Delivery Intercept, Where's My Package, How To Return a Package, Flat Rate
  Shipping, UPS Ground Saver, Freight Quote, Manage Your UPS Profile, File a
  Claim, Shipping Costs and Rates, Signature-Required Deliveries and more),
  pickup and business-solutions page content, The UPS Store pages, the
  service-alert notice and the guest claim wizard copy, captured as rendered.
- Value-added service fees (Smart Pickup $18.50/wk, Daily Pickup $39.00/wk,
  Day-Specific Pickup $8.00-$30.50/wk, On-Call Pickup $9.65/$15.75, Saturday
  stop charges, Signature Required $7.70/pkg, Adult Signature $9.35/pkg,
  Declared Value tiers, Delivery Intercept $18.00 web / $21.00 phone) from
  the UPS Retail Rate and Service Guide.

All images under `static/images/` are original ups.com media (UPS shield and
wordmark, site icons, AEM asset-library photography and banners) downloaded
from their upstream URLs on 2026-09-28; `asset_inventory.json` records bytes,
SHA-256 and the source URL for every file.

Mirror-authored elements, all derived from the captured upstream material and
documented in `provenance.json`:

- The benchmark personas (alice.j@test.com, bob.w@test.com, carol.d@test.com,
  dave.m@test.com / TestPass123!) and their shipment histories. Tracking
  numbers follow the real 18-character 1Z format (shipper + service code +
  serial + UPS mod-10 check digit). Activity scans use the real UPS scan
  vocabulary (Label Created, Origin Scan, Arrived at / Departed from Facility,
  Out for Delivery, Delivered, Delivered to a UPS Access Point, Transferred
  to Post Office, Exception) at real UPS network hub cities (Kent WA,
  Hodgkins IL, Louisville KY, Commerce City CO, Maspeth NY, San Bruno CA,
  Mesquite TX, Doraville GA, Wilmington MA, Tukwila WA, Ontario CA).
- The Create-a-Shipment and Schedule-a-Pickup wizards mirror the upstream
  flow (field sets, steps, service selection, On-Call Pickup fees) without
  contacting the real services; shipment and pickup confirmations are
  deterministic records in the mirror database.
- The Calculate Time and Cost estimator returns the captured quotes verbatim
  for captured lane/weight combinations and linearly interpolates per service
  between captured weights (labeled as an estimate on the results page).
  Residential-destination quotes reflect the captured +$12.08 air-service
  residential surcharge.
- Locator distances are the haversine miles between the captured search
  geocode and each captured location geocode, matching the distances the
  live locator displays.

The UPS name, logo and brand marks are used here only to keep the mirror
visually and behaviorally faithful to the upstream site for offline
benchmarking; this mirror is not affiliated with or endorsed by UPS.
