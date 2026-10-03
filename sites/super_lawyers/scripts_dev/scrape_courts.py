"""Re-capture the court-locations block for each city (fixes the first pass)."""
from __future__ import annotations
import json, pathlib, re, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from sl_browser import ATTORNEYS, goto_sl, launch

HERE = pathlib.Path(__file__).resolve().parent
SITE = HERE.parent
OUT = SITE / "source_data" / "listings"

CITY_FILES = {
    "washington": "seattle", "illinois": "chicago", "new-york": "new-york",
    "florida": "miami", "colorado": "denver", "massachusetts": "boston",
    "california": "los-angeles", "texas": "dallas", "georgia": "atlanta",
    "texas2": "houston", "arizona": "phoenix", "ohio": "columbus",
}
# one representative listing per city (state -> (pa, city))
PICKS = [
    ("personal-injury-plaintiff", "washington", "seattle"),
    ("personal-injury-plaintiff", "illinois", "chicago"),
    ("personal-injury-plaintiff", "new-york", "new-york"),
    ("personal-injury-plaintiff", "florida", "miami"),
    ("dui-dwi", "colorado", "denver"),
    ("employment-and-labor", "massachusetts", "boston"),
    ("personal-injury-plaintiff", "california", "los-angeles"),
    ("divorce", "texas", "houston"),
    ("criminal-defense", "georgia", "atlanta"),
    ("bankruptcy", "arizona", "phoenix"),
    ("workers-compensation", "ohio", "columbus"),
    ("elder-law", "california", "san-diego"),
    ("intellectual-property", "california", "san-francisco"),
    ("estate-planning-and-probate", "texas", "dallas"),
]

def parse_courts(html):
    courts = []
    ci = html.find("Court locations in ")
    if ci == -1:
        return courts
    chunk = html[ci:ci + 16000]
    for m in re.finditer(
            r"<strong>([^<]+)</strong>\s*<br>\s*([^<]+)\s*<br>\s*([^<]+)"
            r"\s*<br>\s*Phone:\s*<a[^>]*>([^<]+)</a>\s*<br>\s*"
            r"<a[^>]+href=\"([^\"]+)\"", chunk):
        courts.append({
            "name": m.group(1).strip(), "line1": m.group(2).strip(),
            "line2": m.group(3).strip(), "phone": m.group(4).strip(),
            "website": m.group(5).strip(),
        })
    return courts

def main():
    pw, browser, ctx = launch()
    page = ctx.new_page()
    for pa, state, city in PICKS:
        # patch every listing json of this city
        targets = sorted(OUT.glob(f"*__{state}__{city}.json"))
        if not targets:
            continue
        have = json.loads(targets[0].read_text())
        if have.get("courts"):
            continue
        url = f"{ATTORNEYS}/{pa}/{state}/{city}/"
        goto_sl(page, url)
        courts = parse_courts(page.content())
        for t in targets:
            d = json.loads(t.read_text())
            d["courts"] = courts
            t.write_text(json.dumps(d, indent=1, ensure_ascii=False))
        print(f"[ok] {state}/{city}: {len(courts)} courts over {len(targets)} listings")
    browser.close()
    pw.stop()

if __name__ == "__main__":
    main()
