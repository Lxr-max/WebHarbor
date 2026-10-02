# NOTICE — university_of_michigan

This directory contains a WebHarbor benchmark mirror of umich.edu built
for offline agent evaluation. It is not affiliated with, endorsed by, or
connected to the University of Michigan.

- The mirror reimplements the public look-and-feel of the Michigan gateway
  and its linked services (schools & colleges directory, majors & degrees
  browser, Fall 2026 class search, faculty roster, library catalog, Michigan
  News, the Happening @ Michigan events calendar, registrar academic
  calendars, undergraduate admissions costs/aid/apply pages and the campus
  building directory) with original code; the University of Michigan name
  and the Block M are trademarks of the Regents of the University of
  Michigan and are used here solely to describe what the mirror models.
- Degree program lists, tuition tables, aid and application deadlines,
  academic-calendar entries, class/section rosters with instructors,
  library catalog records, news articles, campus events and building data
  were captured from the public pages and public JSON APIs of umich.edu
  and its services on 2026-09-30 and remain the property of their
  respective right holders. See provenance.json for the exact source of
  every record, including the two endpoints that stayed Cloudflare-blocked
  for datacenter clients (the Library Search spectrum API and the
  Okta-walled LSA Course Guide) and the honest substitutes used instead.
- Photographic media under `static/images/` is real upstream imagery
  fetched from umich.edu, news.umich.edu, events.umich.edu and the
  schools' own asset hosts (per-file sha256 and source URL in
  asset_inventory.json); no placeholders, no duplicates, no stretched
  renders.
- Benchmark user accounts (alice.j/bob.c/carol.d/dana.k @test.com) are
  fictional fixtures created for evaluation; their password is
  TestPass123! and their backpacks/saved items reference real captured
  records.
