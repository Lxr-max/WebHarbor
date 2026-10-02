"""Harvest the directory taxonomy from the saved attorneys.superlawyers.com
landing render: practice areas, states, and top cities with their real
slugs. Output: source_data/directory.json
"""
from __future__ import annotations

import json
import pathlib
import re

HERE = pathlib.Path(__file__).resolve().parent
SITE = HERE.parent
HTML = SITE / "scraped_data" / "attorneys_home.html"
OUT = SITE / "source_data" / "directory.json"

STATE_SLUGS = [
    "alabama", "alaska", "arizona", "arkansas", "california", "colorado",
    "connecticut", "delaware", "florida", "georgia", "hawaii", "idaho",
    "illinois", "indiana", "iowa", "kansas", "kentucky", "louisiana",
    "maine", "maryland", "massachusetts", "michigan", "minnesota",
    "mississippi", "missouri", "montana", "nebraska", "nevada",
    "new-hampshire", "new-jersey", "new-mexico", "new-york",
    "north-carolina", "north-dakota", "ohio", "oklahoma", "oregon",
    "pennsylvania", "rhode-island", "south-carolina", "south-dakota",
    "tennessee", "texas", "utah", "vermont", "virginia", "washington",
    "washington-dc", "west-virginia", "wisconsin", "wyoming",
]


def unesc(text: str) -> str:
    return (text.replace("&amp;", "&").replace("&#39;", "'")
                .replace("&quot;", '"').strip())


def main() -> None:
    html = HTML.read_text()

    states, cities, practices = [], [], []
    seen = set()
    for m in re.finditer(
            r'<a[^>]+href="(?:https://attorneys\.superlawyers\.com)?/([a-z0-9-]+)/?"[^>]*>(.*?)</a>',
            html, re.S):
        slug = m.group(1)
        name = unesc(re.sub(r"<[^>]+>", " ", m.group(2)))
        name = re.sub(r"\s+", " ", name).strip()
        if not name or slug in seen:
            continue
        seen.add(slug)
        if slug in STATE_SLUGS:
            states.append({"slug": slug, "name": name})
        elif "/" not in slug:
            practices.append({"slug": slug, "name": name})

    # cities: two-segment links state/city
    seen_c = set()
    for m in re.finditer(
            r'<a[^>]+href="(?:https://attorneys\.superlawyers\.com)?/([a-z0-9-]+)/([a-z0-9-]+)/?"[^>]*>(.*?)</a>',
            html, re.S):
        state, city = m.group(1), m.group(2)
        name = unesc(re.sub(r"<[^>]+>", " ", m.group(3)))
        name = re.sub(r"\s+", " ", name).strip()
        key = (state, city)
        if not name or key in seen_c or state not in STATE_SLUGS:
            continue
        seen_c(key) if False else seen_c.add(key)
        cities.append({"slug": city, "name": name, "state": state})

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "states": states, "cities": cities, "practice_areas": practices,
    }, indent=1, ensure_ascii=False))
    print(f"states={len(states)} cities={len(cities)} practice_areas={len(practices)}")


if __name__ == "__main__":
    main()
