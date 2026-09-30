# U.S. DOJ offline research mirror

This site is an independent WebHarbor research environment. It is not an official
Department of Justice website and does not submit applications, reports, FOIA
requests, subscriptions, or messages to the U.S. government.

## Sources and snapshot

The collection was captured from rendered pages of <https://www.justice.gov/>
on September 27–28, 2026, with September 27 as the fixed benchmark reference date.
It contains 59 news releases, 50 legal vacancies, and 57 other public information
pages. This is a curated snapshot; result totals describe the local collection,
not the complete or current live website. Expired vacancies and dated statements
are preserved as source material, not presented as current advice.

`provenance.json` records source URLs, capture times, and hashes of original and
localized HTML. `asset_inventory.json` records the source URL, size, and SHA-256
of each bundled asset. `source_data.json` is bootstrap input; request handlers
read the SQLite database. Links to uncaptured pages and external services show
an explicit offline boundary. Public documents linked by captured pages are
bundled where available.

## Rights and attribution

The DOJ [Website Policies](https://www.justice.gov/legalpolicies) state that public
information may generally be copied and distributed unless otherwise indicated,
and that DOJ seals and logos require advance written authorization. DOJ seals
and logos used as standalone branding have therefore been excluded from the
redistributed assets and replaced by a text masthead. Source photographs may
retain incidental insignia on flags, buildings, or podiums. This mirror does
not imply DOJ endorsement.

Original credits and notices in captured content are retained. The public-domain
status of U.S. federal works does not automatically apply to credited third-party
materials; any original third-party rights and restrictions continue to apply.
Please report attribution or removal requests through this repository's issue
tracker, identifying the affected local asset and its recorded source URL.

## Source inconsistencies

The deregulation news release contains a correction referring to over 125
regulations, while its listing teaser still referred to over 170. The local
listing uses a neutral summary and the full corrected article is preserved.
Vacancy position and practice-area classifications follow the live site's
observed filters, even when they differ from ordinary interpretations of a job
title. No benchmark task depends on the inconsistent OIP office count.

The four test accounts in the database are synthetic WebHarbor fixtures; they
are not DOJ accounts and there is no government login or submission workflow.
