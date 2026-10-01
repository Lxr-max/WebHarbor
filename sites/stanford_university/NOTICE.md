# NOTICE — stanford_university

This directory contains a WebHarbor benchmark mirror of www.stanford.edu
built for offline agent evaluation. It is not affiliated with, endorsed by,
or connected to Stanford University or Leland Stanford Junior University.

- The mirror reimplements the public look-and-feel of the Stanford
  University domain (department directory, degree programs, course
  catalog, faculty directory, Stanford Report news, campus events, the
  2026-27 academic calendar, libraries with weekly hours, undergraduate
  admission and financial aid) with original code; the Stanford name and
  Block S mark belong to Stanford University and are used here solely to
  describe what the mirror models.
- Course data, program descriptions, department copy, faculty profiles,
  news stories, campus events, academic-calendar entries, library
  information and admission copy were captured from the public pages and
  public JSON APIs of www.stanford.edu, bulletin.stanford.edu,
  profiles.stanford.edu, news.stanford.edu, events.stanford.edu,
  studentservices.stanford.edu, library.stanford.edu,
  library-hours.stanford.edu, admission.stanford.edu and
  financialaid.stanford.edu on 2026-09-30 and remain the property of
  their respective right holders. See provenance.json for the exact
  source of every record.
- Photographic media under `static/images/upstream/` is real upstream
  imagery fetched from Stanford's public asset hosts (the homepage
  storyblok CDN, news.stanford.edu story images, CAP profile photos,
  Localist event photos, library sites-pro media and admission site
  banners), for benchmark research use; every file's exact source URL,
  byte length and sha256 are recorded in asset_inventory.json. If a
  rights holder wants media removed from the dataset, open an issue and
  it will be dropped from the next asset revision.
- Benchmark accounts (alice.j@test.com, bob.c@test.com, carol.d@test.com,
  dana.k@test.com) and their course planner rows / saved events are
  authored fixtures modeling the authenticated flows; every course and
  event they reference is a real captured upstream record.
- The net price estimator applies the financial-aid thresholds exactly
  as published on admission.stanford.edu and financialaid.stanford.edu;
  it is a benchmark fixture, not the official Stanford net price
  calculator.
