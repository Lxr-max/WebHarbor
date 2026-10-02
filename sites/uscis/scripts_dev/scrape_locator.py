#!/usr/bin/env python3
"""Phase 3: harvest the Find a Civil Surgeon locator results.

The real tool (www.uscis.gov/tools/find-a-civil-surgeon) geocodes the query
through the public ArcGIS World GeocodeServer with USCIS's own runtime token,
then queries the USCIS locator REST API. We drive the actual page once per
frozen ZIP query and capture every JSON response verbatim:

  geocode:  geocode.arcgis.com/.../findAddressCandidates?SingleLine=<zip>
  id list:  /rest/locator/proximity/id/{lat},{lng}<=10000mi/41091/all/all/all
  details:  /rest/locator/proximity/{lat},{lng}<=10000mi/41091/{ids}/all/all
  count:    /rest/locator/proximity/pagination/41091/all/all/all

Run:  python3.11 scrape_locator.py
"""
import json
import pathlib
import time

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "scraped_data" / "locator"
OUT.mkdir(parents=True, exist_ok=True)

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
PAGE_URL = "https://www.uscis.gov/tools/find-a-civil-surgeon"

# Frozen search set: representative ZIPs an agent would type, one per region.
ZIPS = [
    ("22202", "Arlington, VA"),
    ("10001", "New York, NY"),
    ("90210", "Beverly Hills, CA"),
    ("60601", "Chicago, IL"),
    ("77002", "Houston, TX"),
    ("33101", "Miami, FL"),
    ("94105", "San Francisco, CA"),
    ("02108", "Boston, MA"),
    ("98101", "Seattle, WA"),
    ("85004", "Phoenix, AZ"),
    ("80202", "Denver, CO"),
    ("19106", "Philadelphia, PA"),
    ("30301", "Atlanta, GA"),
    ("55401", "Minneapolis, MN"),
    ("89101", "Las Vegas, NV"),
    ("78701", "Austin, TX"),
    ("50309", "Des Moines, IA"),
    ("29401", "Charleston, SC"),
]


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
        ctx = browser.new_context(user_agent=UA, viewport={"width": 1366, "height": 1000})
        page = ctx.new_page()

        def captures_for(zip_code: str) -> dict:
            caught = {}

            def on_resp(resp):
                url = resp.url
                try:
                    if "findAddressCandidates" in url:
                        caught["geocode"] = {"url": url, "body": resp.text()}
                    elif "/rest/locator/proximity/id/" in url:
                        caught["id_list"] = {"url": url, "body": resp.text()}
                    elif "/rest/locator/proximity/" in url and "+/" not in url and "/id/" not in url:
                        caught.setdefault("details", []).append({"url": url, "body": resp.text()})
                    elif "/rest/locator/proximity/pagination/" in url:
                        caught["pagination"] = {"url": url, "body": resp.text()}
                except Exception:
                    pass

            page.on("response", on_resp)
            page.goto(PAGE_URL, timeout=60000, wait_until="domcontentloaded")
            page.wait_for_timeout(1200)
            page.fill("#search-entry", zip_code)
            page.click("input.locator-search__submit")
            page.wait_for_timeout(6000)
            page.remove_listener("response", on_resp)
            return caught

        index = {"zips": {}, "languages": [], "genders": [], "doctor_count": None}
        for zip_code, label in ZIPS:
            out_path = OUT / f"{zip_code}.json"
            if out_path.exists():
                continue
            caught = captures_for(zip_code)
            time.sleep(0.2)
            if "geocode" not in caught or "id_list" not in caught:
                print(f"  {zip_code}: incomplete capture keys={list(caught)}")
                continue
            try:
                geo = json.loads(caught["geocode"]["body"])
                cand = (geo.get("candidates") or [{}])[0]
                rec = {
                    "zip": zip_code, "label": label,
                    "geocode_url": caught["geocode"]["url"],
                    "geocode": {"lat": cand.get("location", {}).get("y"),
                                "lng": cand.get("location", {}).get("x"),
                                "match": cand.get("attributes", {}).get("Match_addr", "")},
                    "id_list_url": caught["id_list"]["url"],
                    "id_list": json.loads(caught["id_list"]["body"]),
                    "detail_urls": [d["url"] for d in caught.get("details", [])],
                    "details": [json.loads(d["body"]) for d in caught.get("details", [])],
                    "results_text": page.inner_text("main")[:12000],
                }
                out_path.write_text(json.dumps(rec, indent=1))
                n = sum(len(d) for d in rec["details"])
                print(f"  {zip_code} ({label}): {n} surgeon rows, match={rec['geocode']['match'][:44]}")
            except Exception as exc:
                print(f"  ERR {zip_code}: {str(exc)[:110]}")
        # taxonomy + filter options + global doctor count
        page.goto(PAGE_URL, timeout=60000, wait_until="domcontentloaded")
        page.wait_for_timeout(1500)
        index["languages"] = page.eval_on_selector_all(
            "select#edit-language-spoken option",
            "els => els.map(o => o.textContent.trim()).filter(t => t && t !== 'Any')")
        index["genders"] = page.eval_on_selector_all(
            "select#edit-gender option",
            "els => els.map(o => o.textContent.trim()).filter(t => t && t !== 'Any')")
        taxonomy = page.request.get("https://www.uscis.gov/rest/taxonomy/locator_types/terms/en").json()
        pagination = page.request.get("https://www.uscis.gov/rest/locator/proximity/pagination/41091/all/all/all").json()
        index["taxonomy"] = taxonomy
        index["doctor_count"] = pagination
        index["zips"] = {z: l for z, l in ZIPS}
        (OUT / "_index.json").write_text(json.dumps(index, indent=1))
        browser.close()
        print("done; doctor_count =", pagination)


if __name__ == "__main__":
    main()
