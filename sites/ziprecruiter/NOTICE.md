# ziprecruiter mirror — notice

This directory contains a WebHarbor mirror of https://www.ziprecruiter.com/
(job search: SERP with filters, job details, company profiles, title
landing pages, salary pages, career-advice blog and the job-seeker
account area), built from data captured on 2026-09-29 for offline
agent-benchmark use.

- All media under `static/images/` is served by the real upstream host
  (ziprecruiter.com's fotomat logo CDN, its wp-content blog uploads and
  the article bodies' own image hosts, and the site's brand assets) and
  was fetched from the exact upstream URLs. See `asset_inventory.json`
  for the per-file source URLs, byte lengths and sha256s and
  `provenance.json` for the record-level provenance. One upstream hero
  image (the 2022 grad-report article) no longer serves upstream (it
  302-redirects to the site's own 404); the mirror renders that article
  without a hero and documents the dead URL in the inventory's
  `missing_upstream` list rather than substituting a placeholder.
- Text content (the job corpus with descriptions, employment types,
  remote/location types, pay, posted ages, badges and career Q&A; the
  company facts and Breakroom ratings; the salary percentiles,
  histograms, top-cities and related-title tables; the browse indexes;
  and the blog articles) is a frozen snapshot of the public
  ziprecruiter.com pages captured with a headful Chromium that rendered
  the real site, stored in the tracked `source_data/*.json` files. The
  untrimmed upstream snapshots live in the gitignored `scraped_data/`.
  Nothing pretends to be live; the pages state the snapshot date.
- Two render-layer fidelity transforms are applied to captured text at
  display time (the stored captures stay verbatim): job descriptions
  have their inline formatting unescaped once (`rich_text` filter) so
  the browser renders the upstream bold/italics instead of literal
  `<b>` tag text, and company-size ranges render the upstream's
  lowercased "employees" suffix.
- The four benchmark accounts (alice.j/bob.c/carol.d/dana.k @test.com)
  and their profiles, resumes, saved jobs, applications with status
  timelines and job alerts are authored fixtures on top of real
  captured upstream job rows (see provenance.json), modeled after the
  u_s_customs/zara precedent.
- ZipRecruiter is a trademark of ZipRecruiter, Inc. This offline mirror
  is for benchmark purposes and is not affiliated with or endorsed by
  ZipRecruiter, Inc.
