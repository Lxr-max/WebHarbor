# Thumbtack mirror — third-party content notice

This directory contains a non-commercial, offline research mirror of
https://www.thumbtack.com/ built for the WebHarbor deterministic web-agent
benchmark. It redistributes or renders third-party material captured from
the public site on 2026-09-26:

- **Photographs and imagery** (`static/images/`): pro avatars, project
  portfolio photos, category icons and homepage hero imagery served by
  `production-next-images-cdn.thumbtack.com`, fetched via the captured
  upstream URLs recorded in `asset_inventory.json` / `provenance.json`.
- **Typography**: the Rise variable font (`static/fonts/ThumbtackRiseVF.woff2`)
  served by fonts.thumbtack.com.
- **Business listings and reviews** (`source_data_pros.json`): pro names,
  cities, ratings, review text and service details as rendered on the public
  pro-profile pages, used to populate the mirror's database.
- **Cost-guide copy** (`source_data_content.json`): titles, price tables and
  FAQ text from the public /p/ cost-guide articles.

All trademarks and copyrights in this material belong to Thumbtack, Inc. and
the respective pro businesses and reviewers. The material is reproduced here
for research and evaluation only, is not affiliated with or endorsed by
Thumbtack, and must be removed from any distribution that lacks permission
for its use.
