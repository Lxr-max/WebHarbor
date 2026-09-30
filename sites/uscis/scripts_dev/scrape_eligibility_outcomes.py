#!/usr/bin/env python3
"""Phase 5b: capture the outcome-page text for each distinct wizard branch.

The BFS in scrape_eligibility.py replays answers from the start, and terminal
outcome pages share their headline ("You may be eligible...") while carrying
branch-specific explanation text. This pass walks one representative path per
distinct terminal branch and records the verbatim outcome text.

Run:  python3.11 scrape_eligibility_outcomes.py
"""
import json
import pathlib
import time

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "scraped_data" / "eligibility"
OUT.mkdir(parents=True, exist_ok=True)

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
URL = ("https://www.uscis.gov/citizenship-resource-center/learn-about-citizenship/"
       "naturalization-eligibility-tool-0")

# One representative answer path per distinct terminal branch.
PATHS = [
    ("parents_citizen", ["Yes"]),
    ("under18", ["No", "Under 18"]),
    ("armed_forces_hostilities", ["No", "18 or older", "Yes", "Yes, during a designated period of hostilities"]),
    ("armed_forces_oneyear", ["No", "18 or older", "Yes", "Yes, for a year or more"]),
    ("armed_forces_neither", ["No", "18 or older", "Yes", "Neither of these apply to me"]),
    ("lpr_5yr_noleave", ["No", "18 or older", "No", "Yes", "No",
                         "Before December 27, 2021", "No", "No"]),
    ("lpr_5yr_left6mo", ["No", "18 or older", "No", "Yes", "No",
                         "Before December 27, 2021", "Yes", "Yes"]),
    ("lpr_3yr_married", ["No", "18 or older", "No", "Yes", "No",
                         "Between December 27, 2021 and December 27, 2023",
                         "Yes"]),
    ("lpr_not_married", ["No", "18 or older", "No", "Yes", "No",
                         "Between December 27, 2021 and December 27, 2023",
                         "No", "Yes"]),
    ("lpr_3yr_married_yes", ["No", "18 or older", "No", "Yes", "No",
                              "Between December 27, 2021 and December 27, 2023",
                              "Yes", "Yes"]),
    ("lpr_3yr_married_no", ["No", "18 or older", "No", "Yes", "No",
                             "Between December 27, 2021 and December 27, 2023",
                             "Yes", "No"]),
    ("not_us_national", ["No", "18 or older", "No", "Yes", "No",
                          "Between December 27, 2021 and December 27, 2023",
                          "No", "No"]),
    ("not_lpr", ["No", "18 or older", "No", "No"]),
]


def main() -> None:
    out_path = OUT / "outcomes.json"
    outcomes = {}
    if out_path.exists():
        outcomes = json.loads(out_path.read_text())
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
        ctx = browser.new_context(user_agent=UA, viewport={"width": 1366, "height": 1000})
        ctx.set_default_timeout(15000)
        page = ctx.new_page()
        for name, path in PATHS:
            if name in outcomes:
                continue
            try:
                page.goto(URL, timeout=60000, wait_until="domcontentloaded")
                page.wait_for_timeout(1400)
                page.get_by_text("Determine my eligibility").first.click()
                page.wait_for_timeout(1400)
                ok = True
                for opt in path:
                    loc = page.locator("main label", has_text=opt).first
                    loc.click(timeout=8000)
                    page.wait_for_timeout(450)
                    page.get_by_role("button", name="Next").first.click(timeout=8000)
                    page.wait_for_timeout(1400)
                text = page.inner_text("main")
                outcomes[name] = {"path": path, "text": text[:3000]}
                print(f"  {name}: {'OK' if text else 'EMPTY'} :: {text[:90].replace(chr(10), ' | ')}")
            except Exception as exc:
                print(f"  ERR {name}: {str(exc)[:90]}")
            time.sleep(0.3)
        browser.close()
    out_path.write_text(json.dumps(outcomes, indent=1))
    print(f"captured {len(outcomes)} branch outcomes")


if __name__ == "__main__":
    main()
