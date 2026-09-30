#!/usr/bin/env python3
"""Capture ONE-WAY flight results for the REVERSE of each route (return legs).

Usage: python3 harvest_flights_oneway_rev.py [route|all]
Outputs sites/trip_com/scraped_data/flights_ow_rev_<route>.json
"""
import json
import pathlib
import sys

sys.path.insert(0, "/tmp")
from recon_lib import Recon  # noqa: E402
from harvest_flights import EXTRACT, extract_cards, ROUTES  # noqa: E402

BASE = pathlib.Path(__file__).resolve().parent.parent / "scraped_data"

OW_DATES = {
    "sfo_nyc": "2026-10-27",
    "lax_nyc": "2026-10-28",
    "ord_mia": "2026-10-29",
    "las_lax": "2026-10-30",
    "mia_nyc": "2026-10-31",
    "sfo_las": "2026-11-01",
}


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    r = Recon()
    try:
        for route, (dcity, acity, _dd, _rd) in ROUTES.items():
            if which != "all" and which != route:
                continue
            ddate = OW_DATES[route]
            url = (f"https://us.trip.com/flights/showfarefirst?dcity={acity}&acity={dcity}"
                   f"&ddate={ddate}&triptype=ow&class=y&quantity=1&locale=en-US&curr=USD")
            page = r.goto(url, wait=14)
            r.scroll_load(max_px=12000, pause=0.8)
            data = page.evaluate(EXTRACT)
            data["cards"] = extract_cards(page)
            data["route"] = route
            data["url"] = url
            data["ddate"] = ddate
            (BASE / f"flights_ow_rev_{route}.json").write_text(
                json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")
            print(f"[{route} OW-REV] {len(data['cards'])} cards", flush=True)
    finally:
        r.close()


if __name__ == "__main__":
    main()
