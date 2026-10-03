# fox_sports mirror — notice

This directory contains a WebHarbor mirror of FOX Sports
(https://www.foxsports.com/), built from data captured on 2026-09-28
for offline agent-benchmark use.

- The declared upstream `fox_sports.com` does not resolve (underscores
  are not valid in DNS hostnames); the mirror targets the real service
  at https://www.foxsports.com/, following the same normalization
  precedent as the dblp mirror. See `provenance.json` for the full
  record.
- All media under `static/images/` (team logos, league marks, story/
  show/personality artwork, headshots) are real files served by the
  upstream CDN, fetched at the resolved URLs the live pages render. See
  `asset_inventory.json` for the per-file source URLs and sha256 digests.
- Text content (league hubs, standings, schedules, boxscores, rosters,
  stat leaders, player news, stories, shows, personalities, NASCAR and
  UFC pages, the Super 6 contest and betting hubs) is a frozen snapshot
  of the public pages captured at the same date and stored in the
  tracked `source_data/*.json` files; the raw HTML captures live in
  `scraped_data/captures/` with per-page sidecars (not tracked in git;
  they live in the assets archive).
- Interactive flows (accounts, favoriting teams/players/shows/
  personalities, story search, the Super 6 pick-6 contest with grading
  and a leaderboard, login/session management) are original mirror code
  seeded with deterministic benchmark fixtures.
- The FOX Super 6 contest on the upstream site is a live, periodically
  reskeduled free-to-play game; the mirror freezes a Week 3 NFL Pick 6
  card with the six real final scores captured in the snapshot, plus
  deterministic fixture entries for the four benchmark users.
- The Flask application, templates, stylesheet and scripts are original
  mirror code reproducing the site's structure and visual language for
  research purposes. This mirror is not affiliated with, endorsed by,
  or connected to FOX Sports Media Group or Fox Corporation. Editorial
  content belongs to its authors; team and league marks belong to their
  respective owners.
