#!/usr/bin/env python3
"""Capture ONE-WAY flight results from us.trip.com (real one-way prices).

Usage: python3 harvest_flights_oneway.py [route|all]
Outputs sites/trip_com/scraped_data/flights_ow_<route>.json
"""
import json
import pathlib
import sys

sys.path.insert(0, "/tmp")
from recon_lib import Recon  # noqa: E402
from harvest_flights import EXTRACT, extract_cards, ROUTES  # noqa: E402

BASE = pathlib.Path(__file__).resolve().parent.parent / "scraped_data"

OW_DATES = {
    "sfo_nyc": ("2026-10-20",),
    "lax_nyc": ("2026-10-21",),
    "ord_mia": ("2026-10-22",),
    "las_lax": ("2026-10-23",),
    "mia_nyc": ("2026-10-24",),
    "sfo_las": ("2026-10-25",),
}


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    r = Recon()
    try:
        for route, (dcity, acity, _dd, _rd) in ROUTES.items():
            if which != "all" and which != route:
                continue
            ddate = OW_DATES[route][0]
            url = (f"https://us.trip.com/flights/showfarefirst?dcity={dcity}&acity={acity}"
                   f"&ddate={ddate}&triptype=ow&class=y&quantity=1&locale=en-US&curr=USD")
            page = r.goto(url, wait=14)
            r.scroll_load(max_px=12000, pause=0.8)
            data = page.evaluate(EXTRACT)
            data["cards"] = extract_cards(page)
            data["route"] = route
            data["url"] = url
            data["ddate"] = ddate
            (BASE / f"flights_ow_{route}.json").write_text(
                json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")
            print(f"[{route} OW] {len(data['cards'])} cards, {len(data['strip'])} strip, "
                  f"{len(data['airlines'])} airline facets", flush=True)
    finally:
        r.close()


if __name__ == "__main__":
    main()
