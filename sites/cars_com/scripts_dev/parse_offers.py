#!/usr/bin/env python3
"""Parse the captured Instant Cash Offer wizard runs into scraped_data/offers_raw.json.

Each wizard run (scraped_data/captures/offer-steps/<tag>-sN.html) drove the
real accu-trade frame inside cars.com's sell page: after picking the vehicle
the frame shows the initial estimated value; after answering the details
(mileage, ZIP, color, keys, ownership) it shows the adjusted offer. This
extracts, per run: the vehicle line (year/make/model/trim as the wizard
rendered it), the initial range, the adjusted range, the value-impacting
options and the standard-features text.

Run:  python3 scripts_dev/parse_offers.py
"""
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
STEPS = os.path.join(ROOT, "scraped_data", "captures", "offer-steps")
OUT = os.path.join(HERE, "..", "scraped_data")

# The flows the wizard was driven for: (tag, mileage, zip, color)
# (tag, make, model, mileage, zip, color) - the wizard was driven with these
# exact selections; the trim is read from the wizard's own vehicle line.
FLOWS = [
    ("2018-honda-civic-ex", "HONDA", "CIVIC", 60000, "98101", "Blue"),
    ("2019-toyota-rav4-xle", "TOYOTA", "RAV4", 55000, "98101", "White"),
    ("2021-tesla-model_3-long_range", "TESLA", "MODEL 3", 38000, "98101", "White"),
    ("2016-ford-f150-xlt", "FORD", "F150", 85000, "98101", "Black"),
    ("2020-bmw-3_series-330i", "BMW", "3 SERIES", 48000, "98101", "Gray"),
    ("2017-chevrolet-equinox-lt", "CHEVROLET", "EQUINOX", 72000, "98101", "Silver"),
    ("2015-toyota-camry-se_4_door", "TOYOTA", "CAMRY", 95000, "98101", "Red"),
    ("2014-subaru-outback-2.5i_premium", "SUBARU", "OUTBACK", 98000, "98101", "Green"),
]


def text_of(path):
    html = open(path, encoding="utf-8", errors="ignore").read()
    t = re.sub(r"<script.*?</script>", " ", html, flags=re.S)
    t = re.sub(r"<style.*?</style>", " ", t, flags=re.S)
    t = re.sub(r"<[^>]+>", " ", t)
    return " ".join(t.split())


def vehicle_line(t):
    m = re.search(r"(\d{4} [A-Z][A-Z0-9 .&/-]+?) Edit", t)
    return m.group(1).strip() if m else None


def step_num(fn):
    m = re.search(r"-s(\d+)", fn)
    return int(m.group(1)) if m else 0


def first_range(t):
    m = re.search(r"Estimated car value\s+\$([\d,]+)\s*-\s*\$([\d,]+)", t)
    if not m:
        m = re.search(r"\$([\d,]+)\s*-\s*\$([\d,]+)", t)
    return [int(m.group(1).replace(",", "")), int(m.group(2).replace(",", ""))] if m else None


def main():
    vehicles = []
    for tag, make, model, mileage, zipc, color in FLOWS:
        files = sorted((f for f in os.listdir(STEPS) if f.startswith(tag) and f.endswith(".html")),
                       key=step_num)
        if not files:
            print(f"[warn] no steps for {tag}")
            continue
        initial = adjusted = None
        vline = None
        options = []
        std = None
        for fn in files:
            t = text_of(os.path.join(STEPS, fn))
            if vline is None:
                vline = vehicle_line(t)
            r = first_range(t)
            if r and initial is None:
                # the first estimated-car-value range the frame shows (right
                # after the vehicle pick) is the initial estimate
                m = re.search(r"Estimated car value\s+\$([\d,]+)\s*-\s*\$([\d,]+)", t)
                if m:
                    initial = [int(m.group(1).replace(",", "")), int(m.group(2).replace(",", ""))]
            if r and initial and r != initial and adjusted is None:
                # the details step moves the estimate; the first distinct
                # range after the details is the adjusted offer
                adjusted = r
            if not options:
                m = re.search(r"Select your value impacting options (.*?)(?:Standard Features|How many miles)", t)
                if m:
                    options = [x.strip() for x in re.split(r"\s{2,}| · |, (?=[a-z])", m.group(1))
                               if 2 < len(x.strip()) < 60][:10]
            if std is None:
                m = re.search(r"Standard Features: ([^|]{3,140}?) (?:How many miles|What is)", t)
                if m:
                    std = m.group(1).strip()
        if initial and adjusted is None:
            adjusted = initial
        if not vline:
            print(f"[warn] no vehicle line for {tag}")
            continue
        m = re.match(r"(\d{4}) (.+)$", vline)
        year = int(m.group(1)) if m else 0
        rest = m.group(2).strip() if m else vline
        # make/model come from the driven flow; the trim is the wizard's own
        # text after the make+model prefix
        prefix = f"{make} {model}"
        trim = rest[len(prefix):].strip() if rest.upper().startswith(prefix.upper()) else rest
        vehicles.append({
            "year": year, "make": make, "model": model, "trim": trim,
            "mileage": mileage, "zip": zipc, "color": color,
            "options": options, "standard_features": std,
            "initial_estimate": initial, "adjusted_estimate": adjusted,
        })
        print(f"[offer] {vline[:58]}: initial={initial} adjusted={adjusted} opts={len(options)}")
    with open(os.path.join(OUT, "offers_raw.json"), "w") as f:
        json.dump({"vehicles": vehicles, "wizard": {}}, f, indent=1)
    print(f"[parse_offers] {len(vehicles)} flows")


if __name__ == "__main__":
    main()
