"""Scrape full lawyer profiles for attorneys on the harvested top lists
that are not covered by the listing-derived profile set, using the real
profile hrefs recorded by scrape_toplists."""
from __future__ import annotations
import json, pathlib, sys, time
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from sl_browser import goto_sl, launch
import scrape_profiles as sp

HERE = pathlib.Path(__file__).resolve().parent
SITE = HERE.parent
OUT = SITE / "source_data" / "lawyers"

def main() -> None:
    toplists = json.loads((SITE / "source_data" / "toplists.json").read_text())
    have = {p.stem for p in OUT.glob("*.json")}
    targets = {}
    for st, entry in toplists.get("states", {}).items():
        for lst in entry.get("lists", []):
            if ": 2026" not in lst["title"] and ": 2027" not in lst["title"]:
                continue
            for lw in lst.get("lawyers", []):
                uuid, href = lw.get("uuid"), lw.get("profile_href")
                if uuid and href and uuid not in have and uuid not in targets:
                    targets[uuid] = href
    print(f"[tl-profiles] {len(targets)} missing")
    pw, browser, ctx = launch()
    page = ctx.new_page()
    done = fails = 0
    t0 = time.time()
    for uuid, href in targets.items():
        ok = goto_sl(page, href, tries=10)
        html = page.content()
        if not ok or "404" in page.title():
            fails += 1
            if fails <= 5:
                print(f"[fail] {href[:100]}")
            continue
        try:
            rec = sp.parse_profile(html, page.url)
        except Exception as exc:  # noqa: BLE001
            print(f"[parse-error] {uuid}: {exc}")
            continue
        if not rec.get("name"):
            fails += 1
            continue
        (OUT / f"{uuid}.json").write_text(json.dumps(rec, indent=1, ensure_ascii=False))
        done += 1
        if done % 100 == 0:
            rate = done / (time.time() - t0)
            print(f"  {done}/{len(targets)} ({rate:.2f}/s eta {(len(targets)-done)/rate/60:.0f}m)")
    browser.close()
    pw.stop()
    print(f"[tl-profiles] done: {done} scraped, {fails} failed")

if __name__ == "__main__":
    main()
