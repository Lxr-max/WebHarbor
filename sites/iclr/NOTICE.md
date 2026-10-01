# iclr mirror — data notice

This directory contains a WebHarbor benchmark mirror of the International
Conference on Learning Representations site, built for offline agent
evaluation. It is not affiliated with, endorsed by, or connected to ICLR.

- The declared task upstream `iclr.com` is a GoDaddy parking lander with no
  content; the mirror targets the real ICLR service at https://iclr.cc/,
  following the same normalization precedent as the dblp mirror (declared
  parked `dblp.com` → real `dblp.org`). See `provenance.json` for the full
  record.
- All content was captured from the public pages of iclr.cc and blog.iclr.cc
  on 2026-09-30: the 5691 accepted ICLR 2026 papers (titles, authors with
  institutions, topics, decisions, sessions, rooms, poster positions,
  OpenReview links, abstracts) come verbatim from the upstream's own JSON
  data files; the six-day Rio schedule, 40 workshops, 7 invited talks, 21
  socials, sponsors, organizers, awards, news announcements, dates,
  registration structure, FAQ and venue facts are parsed from 277 HTTP-200
  captures stored in `scraped_data/captures/` (gitignored; sidecar metadata
  in the assets archive) and normalized into the tracked
  `source_data/*.json` snapshots.
- Images under `static/images/` are real upstream fetches (ICLR logos,
  speaker headshots, organizer portraits, blog artwork, the 2027 venue
  hero); every file's exact source URL, byte length and sha256 are recorded
  in `asset_inventory.json`. Where the upstream serves a generic avatar
  placeholder (e.g. for speakers without a photo), the mirror renders a
  styled-initial block instead of shipping a placeholder asset.
- The upstream's own data quirks are mirrored faithfully and declared in
  `provenance.json` (timezone labels on the papers JSON, CMS date-token
  breakage on the pricing pages, the rescheduled Percy Liang calendar
  entry). The mirror never invents prices: the only captured price is the
  $50 guest banquet ticket.
- Interactive flows (accounts, paper bookmarks, personal-schedule saves,
  the registration form with the captured affiliation types and item
  exclusivity rule, the HelpDesk contact form) are original mirror code
  seeded with deterministic benchmark fixtures; every paper, event,
  workshop, sponsor, organizer and news item they reference is a real
  captured upstream row.
- Benchmark accounts (alice.j@test.com, bob.c@test.com, carol.d@test.com,
  dana.k@test.com) and their bookmarks/saved events/registrations are
  authored fixtures modeling the authenticated flows.
