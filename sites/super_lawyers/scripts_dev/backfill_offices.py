"""Backfill office lines for lawyer records that lack them (the office
block lives at id="firm_map_info"); also normalizes firm-name entities.
Re-fetches only the records that need it."""
from __future__ import annotations
import json, pathlib, re, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from sl_browser import goto_sl, launch

HERE = pathlib.Path(__file__).resolve().parent
SITE = HERE.parent
LAWYERS = SITE / "source_data" / "lawyers"
FIRMS = SITE / "source_data" / "firms"

def strip_tags(fragment):
    text = re.sub(r"<script.*?</script>", "", fragment, flags=re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    return (text.replace("&amp;", "&").replace("&#39;", "'")
                .replace("&quot;", '"').strip())

def main():
    pw, browser, ctx = launch()
    page = ctx.new_page()
    patched = 0
    for path in sorted(LAWYERS.glob("*.json")):
        rec = json.loads(path.read_text())
        if rec.get("office"):
            # still normalize firm entity encoding
            firm = rec.get("firm") or {}
            if firm.get("name") and "&amp;" in firm["name"]:
                firm["name"] = firm["name"].replace("&amp;", "&")
                path.write_text(json.dumps(rec, indent=1, ensure_ascii=False))
            continue
        goto_sl(page, rec["url"], tries=10)
        html = page.content()
        m = re.search(r'id="firm_map_info"[^>]*>(.*?)</p>', html, re.S)
        if m:
            lines = [strip_tags(x) for x in re.findall(r"([^<>]+)(?:<br\s*/?>|$)", m.group(1))]
            lines = [x for x in lines if x]
            rec["office"] = lines
            firm = rec.get("firm") or {}
            if firm.get("name") and "&amp;" in firm["name"]:
                firm["name"] = firm["name"].replace("&amp;", "&")
            path.write_text(json.dumps(rec, indent=1, ensure_ascii=False))
            patched += 1
            fu = firm.get("uuid")
            fp = FIRMS / f"{fu}.json"
            if fp.exists():
                fdata = json.loads(fp.read_text())
                if not fdata.get("office"):
                    fdata["office"] = lines
                    fp.write_text(json.dumps(fdata, indent=1, ensure_ascii=False))
    print(f"[backfill] patched {patched} lawyers")
    browser.close(); pw.stop()

if __name__ == "__main__":
    main()
