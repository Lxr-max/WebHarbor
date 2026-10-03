"""Derive each firm's office lines from its scraped lawyers.

Upstream renders the same office block (id="firm_map_info") on the firm
page and on each member lawyer's profile, so the firm office is the most
common office among its scraped attorneys. Pure post-processing: no
network. Run after scrape_firms + backfill_offices.
"""
from __future__ import annotations
import json, pathlib
from collections import Counter

HERE = pathlib.Path(__file__).resolve().parent
SITE = HERE.parent
LAWYERS = SITE / "source_data" / "lawyers"
FIRMS = SITE / "source_data" / "firms"

def main():
    offices: dict[str, Counter] = {}
    for path in sorted(LAWYERS.glob("*.json")):
        rec = json.loads(path.read_text())
        fu = (rec.get("firm") or {}).get("uuid")
        if fu and rec.get("office"):
            offices.setdefault(fu, Counter())[tuple(rec["office"])] += 1
    patched = 0
    for fp in sorted(FIRMS.glob("*.json")):
        fdata = json.loads(fp.read_text())
        if fdata.get("office"):
            continue
        best = offices.get(fp.stem)
        if best:
            fdata["office"] = list(best.most_common(1)[0][0])
            fp.write_text(json.dumps(fdata, indent=1, ensure_ascii=False))
            patched += 1
    print(f"[derive-firm-offices] patched {patched} firms")

if __name__ == "__main__":
    main()
