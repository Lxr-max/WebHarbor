#!/usr/bin/env python3
"""Phase 8: harvest the processing-times API records from the upstream archive.

egov.uscis.gov (the live Case Status Online and Processing Times tools) sits
behind a Cloudflare WAF that hard-blocks this build network (verified: HTTP
403 "Attention Required!" from headless Chromium, headed Chromium and curl,
across repeated attempts on 2026-09-28). The processing-times REST API that
the tool's Vue frontend calls — /processing-times/api/processingtime/{form}/
{office} — is archived verbatim in the Internet Archive, so we pull the real
JSON records from there and freeze them with their snapshot dates.

Run:  python3.11 scrape_pt_archive.py
"""
import json
import pathlib
import time
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "scraped_data" / "processing_times"
OUT.mkdir(parents=True, exist_ok=True)

CDX = "http://web.archive.org/cdx/search/cdx"
BASE = "https://egov.uscis.gov/processing-times/api/processingtime/"


def fetch(url: str, retries: int = 3) -> bytes:
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "webharbor-harvest/1.0"})
            with urllib.request.urlopen(req, timeout=90) as r:
                return r.read()
        except Exception:
            time.sleep(4 * (attempt + 1))
    raise RuntimeError(f"failed: {url}")


def main() -> None:
    out_path = OUT / "records.json"
    # 1) the archived URL index for the processingtime API (collapse=urlkey: one
    # entry per unique URL, otherwise the first 2000 lines are all revisits)
    q = urllib.parse.quote("egov.uscis.gov/processing-times/api/processingtime/*")
    text = fetch(f"{CDX}?url={q}&output=text&limit=2000&collapse=urlkey").decode("utf-8", "replace")
    rows = []
    for line in text.strip().split("\n"):
        parts = line.split()
        if len(parts) >= 7 and parts[4] == "200" and parts[3] == "application/json":
            rows.append({"timestamp": parts[1], "original": parts[2]})
    out_path = OUT / "records.json"
    records = []
    have = set()
    if out_path.exists():
        records = json.loads(out_path.read_text())
        have = {(r.get("_original_url"), r.get("_snapshot")) for r in records}
    print(f"archived JSON snapshots: {len(rows)}")
    for i, row in enumerate(rows):
        if (row["original"], row["timestamp"]) in have:
            continue
        url = f"http://web.archive.org/web/{row['timestamp']}id_/{row['original']}"
        try:
            body = fetch(url)
            data = json.loads(body.decode("utf-8"))
            rec = data.get("data", {}).get("processing_time", data)
            rec["_snapshot"] = row["timestamp"]
            rec["_snapshot_date"] = f"{row['timestamp'][:4]}-{row['timestamp'][4:6]}-{row['timestamp'][6:8]}"
            rec["_original_url"] = row["original"]
            records.append(rec)
            if i % 10 == 0:
                print(f"  {i}: {rec.get('form_name')}/{rec.get('office_code')} @ {rec['_snapshot_date']}")
        except Exception as exc:
            print(f"  ERR {row['original']}: {str(exc)[:80]}")
        time.sleep(1.0)
    out_path.write_text(json.dumps(records, indent=1))
    forms = sorted({r.get("form_name") for r in records})
    print(f"records={len(records)} forms={len(forms)}: {forms[:14]}")


if __name__ == "__main__":
    main()
