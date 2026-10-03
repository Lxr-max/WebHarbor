# Mirror notice — ticketmaster (www.ticketmaster.com)

This directory contains a functional mirror of https://www.ticketmaster.com/
built for the WebHarbor offline benchmark environment. It is a benchmark
fixture, not an official Ticketmaster product.

## What is mirrored

- The homepage: Highlights carousel, Trending Searches chips, Happening This
  Weekend, Popular Near You with genre tabs, and the city tiles, over the real
  621-event US catalog captured from the upstream search, discover and event
  pages on 2026-09-27.
- Discovery browsing for Concerts / Sports / Arts & Theater / Family with
  date, city, max-price and subcategory filters, plus date and lowest-price
  sorts, and the Cities directory.
- Scored site search across events, artists and venues with relevance and
  date sorts.
- Event pages: sale info / presale timelines using the captured upstream
  presale copy, related dates for the same artist, important info, the seat
  map section panel, and real-pattern ticket listings with quantity, price,
  ticket-type (Standard Admission / VIP Package / Accessible) and accessible
  filters and Lowest Price / Best Seats / Highest Price sorts.
- The ticket selection panel: quantity stepper bounded by availability and
  the event ticket limit, the face value + service fee breakdown, and
  Reserve Tickets.
- Checkout: delivery method (Mobile Transfer / Mobile Entry), payment with
  saved cards for signed-in buyers or a new card for guests and cardless
  accounts, order review, and the confirmation page with the order number.
- Artist pages with the captured ratings and favorites; venue pages with
  addresses and upcoming events grouped by category.
- Member area: orders and order detail, profile editing, payment methods
  (add/remove with validation), and favorites.
- Gift cards page ($25-$1000 denominations, e-gift/physical types, balance
  check), the help centre with topic articles, the sell landing page, VIP
  page, travel page and legal pages.

## Media and data provenance

The original 778 images under `static/images/` were downloaded from
Ticketmaster's CDNs (s1.ticketm.net, prismic-images.tmol.io) on 2026-09-27;
their source URLs, byte sizes and SHA-256 digests are recorded in
`asset_inventory.json`, and the data provenance for every tracked file is
recorded in `provenance.json`. The incomplete captured wordmark SVG was replaced with a readable typographic
wordmark in the header and footer. Event, artist, venue and content data come from
the tracked `source_data_*.json` snapshots captured from the rendered pages.

The catalog includes the real near-name events captured from the rendered
search results for "power to the people" on 2026-09-27 (The High Kings'
"Power of the People" 2027 US tour dates, The Casualties' "People Over Power"
tour and Hiss Golden Messenger's "I'm People" tour, alongside the Power to
the People Festival itself) so the search leg of the fee-breakdown task
returns real competitors to disambiguate by venue and city. Those events and
their artists / venues were captured from the rendered search, artist and
venue pages; the rendered search cards do not embed card image URLs, so those
rows carry no image rather than substituting media, keeping the pinned asset
bundle byte-identical (no new files under `static/images/`).

## Trademarks

"Ticketmaster", the Ticketmaster wordmark and the covered event, artist,
team and venue names are trademarks or trade names of their respective
owners (Ticketmaster/Live Nation and the event promoters, teams, artists and
venues). They are reproduced here only to describe the benchmark fixture.
This mirror is not affiliated with, endorsed by, or connected to Ticketmaster
or Live Nation.

## Homepage visual refinement (2026-09-29)

The homepage now uses a featured-event panel, distinct performer selections across
Highlights and the weekend shelf, category rotation, and thumbnails in the popular
event lists. Each shelf selects events deterministically from the existing SQLite
catalog. Weekend dates mean Saturday/Sunday relative to the frozen mirror date;
event research, ticketing tasks, rubrics and verifiers are unchanged. This is an
editorial adaptation of the captured mirror, not a fresh reproduction of today's
Ticketmaster homepage: live Ticketmaster US and Canada pages returned HTTP 403.

A visual check found two incorrectly associated images in the original bundle.
The Columbus Crew's official crest (columbuscrew.com, MLS CDN) replaces FC
Cincinnati's crest in its event and artist images. Official Mystère artwork from
cirquedusoleil.com replaces a generic concert photo in that show's 20 event images
and artist image. The 23 replacements keep their existing paths; source pages,
URLs, retrieval date, transformations and hashes are in `asset_inventory.json`.
No video, audio or unrelated attachments were added. The total remains 778 images.
