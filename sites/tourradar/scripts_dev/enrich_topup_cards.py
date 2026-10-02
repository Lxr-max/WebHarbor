#!/usr/bin/env python3
"""Enrich the 3 constructed SERP cards (46923/251939/252256) with structured
facts from the same upstream API the live SERP cards derive from:
destinations, price basis, discount %, age range. Idempotent."""
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRAPE = ROOT / "scraped_data"
IDS = (46923, 251939, 252256)


def main():
    cards = json.loads((SCRAPE / "serp_cards.json").read_text())
    by_id = {c["tour_id"]: c for c in cards}
    for tid in IDS:
        a = json.loads((SCRAPE / "api" / f"{tid}.json").read_text())
        t = ((a.get("comparison") or {}).get("tour") or {})
        c = by_id[tid]
        cities = [x["name"] for x in (t.get("destinations") or {}).get("cities", [])
                  if x.get("name")]
        if cities:
            c["destinations"] = ", ".join(cities[:6])
        pf = t.get("price_from") or {}
        if pf.get("based_on"):
            c["price_basis"] = pf["based_on"]
        if pf.get("price_base") and pf.get("price_total"):
            c["discount_pct"] = round((1 - pf["price_total"] / pf["price_base"]) * 100)
        ar = ((t.get("age_range") or {}).get("strict") or {})
        if ar.get("min_age") is not None and ar.get("max_age"):
            c["age_range"] = f"Ages {ar['min_age']}-{ar['max_age']}"
        elif ar.get("min_age") is not None:
            c["age_range"] = f"Ages {ar['min_age']}+"
        print(tid, "→", {k: c.get(k) for k in
                          ("destinations", "price_basis", "discount_pct", "age_range")})
    (SCRAPE / "serp_cards.json").write_text(json.dumps(cards, indent=1))


if __name__ == "__main__":
    main()
