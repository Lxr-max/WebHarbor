"""Backfill the 46 top-list lawyers whose profiles were never captured
(they appear on top lists but not on any scraped listing). Uses the
scrape_profiles.parse_profile machinery; profile URL city comes from the
toplists entry when present, otherwise the state's first captured city.
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from scrape_profiles import parse_profile  # noqa: E402
from sl_browser import PROFILES, launch  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
SITE = HERE.parent
OUT = SITE / "source_data" / "lawyers"


def main() -> None:
    have = {p.stem for p in OUT.glob("*.json")}
    tops = json.loads((SITE / "source_data" / "toplists.json").read_text())
    # city fallback: first city captured per state from the directory
    directory = json.loads((SITE / "source_data" / "directory.json").read_text())
    state_city = {}
    for row in directory["cities"]:
        state_city.setdefault(row["state"], row["slug"])

    todo = {}
    for st, entry in tops.get("states", {}).items():
        for lst in entry.get("lists", []):
            for lw in lst.get("lawyers", []):
                u = lw.get("uuid")
                if u and u not in have and u not in todo:
                    city = lw.get("city") or entry.get("city") or state_city.get(st)
                    if city:
                        todo[u] = {"slug": lw["slug"], "state": st, "city": city}
    print(f"[toplist-backfill] {len(todo)} missing profiles")
    if not todo:
        return
    pw, browser, ctx = launch()
    page = ctx.new_page()
    from sl_browser import goto_sl  # noqa: PLC0415
    saved = 0
    for u, meta in todo.items():
        url = (f"{PROFILES}/{meta['state']}/{meta['city']}/lawyer/"
               f"{meta['slug']}/{u}.html")
        try:
            ok = goto_sl(page, url, tries=10)
            html = page.content()
            if not ok or "404" in page.title():
                print(f"  [fail] {meta['slug']}")
                continue
            rec = parse_profile(html, url)
        except Exception as exc:  # noqa: BLE001
            print(f"  [err] {meta['slug']}: {exc}")
            continue
        (OUT / f"{u}.json").write_text(json.dumps(rec, indent=1,
                                                  ensure_ascii=False))
        saved += 1
    browser.close()
    pw.stop()
    print(f"[toplist-backfill] saved {saved}/{len(todo)}")


if __name__ == "__main__":
    main()
