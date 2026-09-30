#!/usr/bin/env python3
"""Phase 2b: extract the spec-compare blocks from the saved PDP pages.

The PDP compare accordion (battery life / screen / camera / storage /
reviews) is fully present in the rendered HTML captured by scrape_pdp.py.
The compare list alternates <device name> <section name> <value> per
compared model; this pass restructures it into {device: {section: value}}.

Run: python3.11 scrape_specs.py
Output: scraped_data/device_specs.json
"""
import html as htmllib
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "scraped_data"

SECTIONS = ["Battery life", "Screen", "Camera", "Storage", "Reviews"]


def strip_lines(html):
    text = re.sub(r"<script[^>]*>.*?</script>", " ", html, flags=re.S)
    text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.S)
    text = re.sub(r"<[^>]+>", "\n", text)
    text = htmllib.unescape(text)
    text = re.sub(r"[ \t ]+", " ", text)
    return [l.strip() for l in text.split("\n") if l.strip()]


def main():
    devices = json.loads((OUT / "devices.json").read_text())
    names = [d["name"] for d in devices]
    name_set = set(names)
    specs_out = {}
    for dev in devices:
        slug = dev.get("slug")
        page = OUT / "pages" / "pdp" / f"{slug}.html"
        if not page.exists():
            continue
        lines = strip_lines(page.read_text(encoding="utf-8", errors="replace"))
        sections = {}
        i = 0
        while i < len(lines):
            if lines[i] not in SECTIONS:
                i += 1
                continue
            section = lines[i]
            j = i + 1
            block = []
            while j < len(lines) and lines[j] not in SECTIONS:
                block.append(lines[j])
                j += 1
            # block alternates: device, section, value, device, section, value...
            entries = {}
            k = 0
            while k < len(block):
                if k + 2 < len(block) and block[k] in name_set and block[k + 1] == section:
                    entries[block[k]] = block[k + 2]
                    k += 3
                elif block[k] in name_set and k + 2 == len(block):
                    entries[block[k]] = block[k + 2]
                    k += 3
                else:
                    k += 1
            if entries:
                sections[section] = entries
            i = j
        specs_out[slug] = sections
        heads = {s: len(v) for s, v in sections.items()}
        print(f"[specs] {slug}: {heads}")
    (OUT / "device_specs.json").write_text(
        json.dumps(specs_out, indent=1), encoding="utf-8")
    print(f"[specs] captured {len(specs_out)} devices")


if __name__ == "__main__":
    main()
