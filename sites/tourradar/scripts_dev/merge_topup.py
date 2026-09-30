#!/usr/bin/env python3
"""Merge the 3 top-up tours (46923/251939/252256) into serp_cards.json and
tour_dests.json.

The SERP first-load batches don't reach these tours (they sit deep in the
upstream lists), so cards are built from each tour's own upstream detail-page
record (tour_progress.jsonl) — same fields the SERP card parser produces.
Destination slugs come from the tours' own pages: Europe Taster is linked to
/d/europe (breadcrumbs: Europe Tours > Western Europe Tours); both Egypt tours
are linked to /d/egypt (breadcrumbs: Africa Tours > Egypt Tours > Nile Valley).
"""
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "scraped_data"

DEST_FOR = {"46923": ["europe"], "251939": ["egypt"], "252256": ["egypt"]}


def main():
    cards = json.loads((OUT / "serp_cards.json").read_text())
    dests = json.loads((OUT / "tour_dests.json").read_text())
    have = {c["tour_id"] for c in cards}
    recs = {}
    for line in (OUT / "tour_progress.jsonl").read_text().splitlines():
        r = json.loads(line)
        if str(r["tour_id"]) in DEST_FOR:
            recs[r["tour_id"]] = r

    added = 0
    for tid, rec in sorted(recs.items()):
        if tid in have:
            print(f"{tid}: card already present, skipping")
            continue
        card = {
            "tour_id": tid,
            "image": next((i["src"] for i in (rec.get("images") or [])
                           if "/s3/tour/" in (i.get("src") or "")), None),
            "image_alt": (rec.get("title") or "")[:120],
            "rating": rec.get("rating"),
            "name": rec.get("title"),
            "review_count": rec.get("review_count"),
            "duration": f"{rec.get('duration_days')} days",
            "age_range": None,
            "operator": rec.get("operator"),
            "destinations": None,
            "operated_in": rec.get("guided_language"),
            "islands": None,
            "region": None,
            "style": (rec.get("attributes") or [{}])[0].get("name"),
            "price_basis": None,
            "discount_pct": None,
            "price_from": rec.get("price_from"),
            "price_current": rec.get("price_current"),
        }
        cards.append(card)
        added += 1
        print(f"card built for {tid}: {card['name'][:56]} "
              f"rating={card['rating']} reviews={card['review_count']} "
              f"price={card['price_current']}")
    for tid, slugs in DEST_FOR.items():
        cur = dests.setdefault(tid, [])
        for s in slugs:
            if s not in cur:
                cur.append(s)
        print(f"tour_dests[{tid}] = {cur}")
    (OUT / "serp_cards.json").write_text(json.dumps(cards, indent=1))
    (OUT / "tour_dests.json").write_text(json.dumps(dests, indent=1))
    print(f"done: cards+={added} total={len(cards)} dests={len(dests)}")


if __name__ == "__main__":
    main()
