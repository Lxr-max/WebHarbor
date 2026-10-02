#!/usr/bin/env python3
"""Capture the raw HTML surfaces of www.dmv.virginia.gov used by the mirror.

Polite fetcher: browser User-Agent, ~1s delay, retry-on-5xx, raw HTML stored
under scraped_data/pages/ so the parse step is re-runnable offline. The parse
step (build_source_data.py) turns these into the tracked source_data/*.json
snapshots; provenance.json records the capture window.
"""
import pathlib
import time
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "scraped_data" / "pages"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

PAGES = [
    # core chrome + section landings
    ("home", "/"),
    ("about", "/about"),
    ("contact-us", "/contact-us"),
    ("how-do-i", "/how-do-i"),
    ("news", "/news"),
    ("moving", "/moving"),
    ("moving-new-virginia", "/moving/new-virginia"),
    ("online-services", "/online-services"),
    ("online-services-all", "/online-services-all"),
    ("online-services-address-change", "/online-services/address-change"),
    ("online-services-insurance", "/online-services/insurance"),
    ("appointments", "/appointments"),
    ("records", "/records"),
    ("records-request-dvr", "/records/request-driver-vehicle-record"),
    ("licenses-ids", "/licenses-ids"),
    ("licenses-ids-license", "/licenses-ids/license"),
    ("licenses-ids-license-applying", "/licenses-ids/license/applying"),
    ("licenses-ids-license-replace", "/licenses-ids/license/replace"),
    ("licenses-ids-learners", "/licenses-ids/learners"),
    ("licenses-ids-real-id", "/licenses-ids/real-id"),
    ("licenses-ids-cdl", "/licenses-ids/cdl"),
    ("licenses-ids-id-cards", "/licenses-ids/id-cards"),
    ("licenses-ids-motorcycle", "/licenses-ids/motorcycle"),
    ("licenses-ids-exams", "/licenses-ids/exams"),
    ("licenses-ids-exams-know", "/licenses-ids/exams/know-exam"),
    ("licenses-ids-exams-manual", "/licenses-ids/exams/manual"),
    ("licenses-ids-exams-practice", "/licenses-ids/exams/practice-exam"),
    ("licenses-ids-organ-donation", "/licenses-ids/organ-donation"),
    ("licenses-ids-military", "/licenses-ids/military"),
    ("vehicles", "/vehicles"),
    ("vehicles-registration", "/vehicles/registration"),
    ("vehicles-title", "/vehicles/title"),
    ("vehicles-license-plates", "/vehicles/license-plates"),
    ("vehicles-taxes-fees", "/vehicles/taxes-fees"),
    ("vehicles-buy-sell", "/vehicles/buy-sell"),
    ("vehicles-insurance-requirements", "/vehicles/insurance-requirements"),
    ("vehicles-general", "/vehicles/general"),
    ("all-locations", "/all-locations"),
    ("locations", "/locations"),
]


# name -> real upstream path (the mirror serves pages at these paths).
PAGE_PATHS = {name: path for name, path in PAGES}


def fetch(url: str, tries: int = 3) -> bytes:
    last = None
    for attempt in range(tries):
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(3 * (attempt + 1))
    raise RuntimeError(f"fetch failed {url}: {last}")


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    base = "https://www.dmv.virginia.gov"
    for name, path in PAGES:
        out = RAW / f"{name}.html"
        if out.exists():
            print(f"[pages] cached {name}")
            continue
        data = fetch(base + path)
        out.write_bytes(data)
        print(f"[pages] {path} -> {len(data)} bytes")
        time.sleep(1.0)


if __name__ == "__main__":
    main()
