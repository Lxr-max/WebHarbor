#!/usr/bin/env python3
"""Second capture round: the deeper upstream pages most-linked from the
first-round pages (knowledge exam, road skills test, driver's manual,
emissions, highway use fee, learner's permit details, title subpages,
online-service subpages, records subpages), fetched by their real upstream
paths so the mirror can serve them at the same URLs. Also collects every
PDF (forms + manuals) referenced from the captured pages.
"""
import json
import pathlib
import re
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from scrape_pages import fetch  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "scraped_data" / "pages"
BASE = "https://www.dmv.virginia.gov"

# Most-linked upstream content paths from the first capture round.
EXTRA_PAGES = [
    "/licenses-ids/exams/know-exam",
    "/licenses-ids/exams/road-skills-test",
    "/licenses-ids/exams/manual",
    "/licenses-ids/learners/revised-learners-permit-holding-period-and-driver-education-requirements-faqs",
    "/licenses-ids/id-cards/legal-presence",
    "/vehicles/registration/emissions",
    "/vehicles/taxes-fees/highway-use",
    "/vehicles/registration/enotification-info",
    "/licenses-ids/cdl/hazmat",
    "/licenses-ids/learners/remote-test",
    "/licenses-ids/learners/apply",
    "/licenses-ids/learners/ed-reqs",
    "/online-services/record-request",
    "/online-services/reinstate-fee",
    "/vehicles/title/mail",
    "/vehicles/registration/state-owned-vehicles",
    "/vehicles/title/etitle",
    "/vehicles/buy-sell/buying-new",
    "/vehicles/buy-sell/buying-used",
    "/vehicles/buy-sell/selling",
    "/vehicles/general",
    "/vehicles/insurance-requirements",
    "/vehicles/insurance-coverage",
    "/records/emergency-contact",
    "/records/vital",
    "/records/ppi",
    "/moving/new-virginia",
    "/licenses-ids/improvement",
    "/licenses-ids/disability",
    "/licenses-ids/training",
    "/licenses-ids/military",
    "/licenses-ids/organ-donation",
    "/licenses-ids/payment-plan-program",
    "/licenses-ids/no-cost-credentials",
    "/licenses-ids/license-extension",
    "/licenses-ids/mobile-id",
    "/licenses-ids/id-apple-wallet",
    "/safety/resources",
    "/safety/programs",
    "/how-do-i",
    # round 3: the card-grid targets most-linked from the captured pages
    "/licenses-ids/cdl/applying",
    "/licenses-ids/cdl/locations",
    "/licenses-ids/id-cards/get-id",
    "/licenses-ids/id-cards/e-renew-online",
    "/licenses-ids/id-cards/replacement-id",
    "/licenses-ids/id-cards/adult-id",
    "/licenses-ids/id-cards/child-id",
    "/licenses-ids/id-cards/photo-id",
    "/licenses-ids/id-cards/vet-id",
    "/records/voluntary",
    "/records/personal-information-updates",
    "/moving/leaving-virginia",
    "/licenses-ids/motorcycle/skills-test",
    "/licenses-ids/license/applying/eligibility",
    "/licenses-ids/license/renewing",
    "/licenses-ids/license/driver-privilege-card",
    "/licenses-ids/license/driver-privilege-card/renewal",
    "/vehicles/registration/renew-online",
    "/vehicles/title/replacement",
]


ROUND2_PATHS = {p.strip("/").replace("/", "-"): p for p in EXTRA_PAGES}


def main() -> int:
    pages = json.loads((ROOT / "source_data" / "pages.json").read_text())
    captured = {p["name"] for p in pages}
    for path in EXTRA_PAGES:
        name = path.strip("/").replace("/", "-")
        out = RAW / f"{name}.html"
        if out.exists() or name in captured:
            continue
        try:
            data = fetch(BASE + path)
        except RuntimeError as exc:
            print(f"[pages2] SKIP {path}: {exc}")
            continue
        out.write_bytes(data)
        print(f"[pages2] {path} -> {len(data)} bytes")
        time.sleep(0.8)
    print("[pages2] done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
