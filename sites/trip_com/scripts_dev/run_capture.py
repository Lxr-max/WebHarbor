#!/usr/bin/env python3
"""Sequential capture runner (background): enriched details, attractions, OW, SEO."""
import subprocess
import sys

HERE = "/data/zhaoyang-user-projects/websyn/WebHarbor/_wh_review_tools/orch/contribute/build/trip_com/sites/trip_com/scripts_dev"


def run(script, *args):
    print(f"=== {script} {' '.join(args)}", flush=True)
    r = subprocess.run([sys.executable, "-u", f"{HERE}/{script}", *args])
    if r.returncode != 0:
        print(f"!!! {script} {' '.join(args)} failed rc={r.returncode}", flush=True)


if __name__ == "__main__":
    for city in ["las_vegas", "new_york", "los_angeles", "orlando",
                 "san_francisco", "chicago", "miami", "new_orleans"]:
        run("harvest_hotel_detail_async.py", city, "12", "4")
    for city in ["orlando", "las_vegas", "new_york"]:
        run("harvest_attractions.py", city)
        run("harvest_attraction_detail.py", city, "8")
    for route in ["sfo_nyc", "lax_nyc", "ord_mia", "las_lax", "mia_nyc", "sfo_las"]:
        run("harvest_flights_oneway.py", route)
    for city in ["las_vegas", "new_york", "los_angeles", "orlando",
                 "san_francisco", "chicago", "miami", "new_orleans"]:
        run("harvest_city_seo.py", city)
    print("ALL_CAPTURE_DONE", flush=True)
