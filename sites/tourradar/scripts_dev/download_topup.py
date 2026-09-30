#!/usr/bin/env python3
"""Top-up downloader: fetch ONLY the managed-image refs that are actually
used by source_data (+ template site chrome) and missing on disk.

Unlike download_images.py this never re-pulls the ~2.5k orphan URLs that the
cleanup pass removed, and it MERGES its extension fixes into the existing
image_ext_fixes.json instead of overwriting the log.
"""
import json
import pathlib
import sys
import time

import httpx

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from download_images import MAGIC, UA, IMG, SCRAPE, verify, sniff_fix, SITE_IMAGES  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]

TOPUP_TIDS = (46923, 251939, 252256)


def topup_picked_refs():
    """Every image ref the build would pick for the 3 top-up tours:
    replicate pick_images + the hero-card fallback + operator logo pick.
    Registers the upstream URLs into build_source_data.URL_MAP so we can
    download exactly what a post-download build will keep."""
    import build_source_data as B
    refs = set()
    cards = {c["tour_id"]: c for c in
             json.loads((SCRAPE / "serp_cards.json").read_text())}
    for line in (SCRAPE / "tour_progress.jsonl").read_text().splitlines():
        rec = json.loads(line)
        if rec.get("tour_id") not in TOPUP_TIDS:
            continue
        picked = B.pick_images(rec)
        tid = rec["tour_id"]
        if not picked["hero"]:
            card_img = cards[tid].get("image") or ""
            if "/s3/tour/" in card_img:
                ext = pathlib.Path(card_img.split("/")[-1]).suffix
                picked["hero"] = B.map_image(f"tours/{tid}_card{ext}", card_img)
        if picked["hero"]:
            refs.add(picked["hero"])
        refs.update(picked["gallery"])
        for key in ("avatars", "review_photos"):
            refs.update(p for p, _ in picked[key])
        refs.update(p for p, _ in picked["moments"])
        for img in rec.get("images") or []:
            src = img.get("src") or ""
            if "/s3/op/" in src:
                refs.add(B.map_image(f"operators/{src.split('/')[-1]}", src))
                break
    refs = {r for r in refs if r}
    return refs, B.URL_MAP


def keep_refs():
    """Every image ref used by source_data files."""
    refs = set()

    def walk(o):
        if isinstance(o, str):
            if o and '/' in o and o.split('.', 1)[-1] in (
                    'jpg', 'jpeg', 'png', 'webp', 'gif'):
                refs.add(o)
        elif isinstance(o, list):
            for x in o:
                walk(x)
        elif isinstance(o, dict):
            for v in o.values():
                walk(v)

    for f in ('source_data_tours.json', 'source_data_catalog.json',
              'source_data_content.json'):
        walk(json.loads((ROOT / f).read_text()))
    refs = {r for r in refs
            if not r.startswith('static/') and not r.startswith('http')}
    refs.update(SITE_IMAGES)
    return refs


def main():
    urls = json.loads((SCRAPE / 'image_urls.json').read_text())
    refs = keep_refs()
    picked, url_map = topup_picked_refs()
    urls.update(url_map)
    refs.update(picked)
    missing = sorted(r for r in refs
                     if not (IMG / r).is_file() and r in urls)
    print(f"keep-refs={len(refs)} missing-with-url={len(missing)}")
    no_url = sorted(r for r in refs
                    if not (IMG / r).is_file() and r not in urls)
    if no_url:
        print("missing WITHOUT upstream url:", no_url[:10])
    ok = skip = 0
    fail = []
    ext_fixes = json.loads((SCRAPE / 'image_ext_fixes.json').read_text())
    with httpx.Client(follow_redirects=True, timeout=40,
                      headers={'User-Agent': UA,
                               'Referer': 'https://www.tourradar.com/'}) as cx:
        for n, local in enumerate(missing):
            url = urls[local]
            try:
                r = cx.get(url)
                if r.status_code != 200:
                    fail.append((local, url, r.status_code))
                    continue
                data = r.content
                fixed = sniff_fix(local, data)
                if fixed:
                    ext_fixes[local] = fixed
                    local = fixed
                if not verify(local, data):
                    fail.append((local, url, 'bad-bytes'))
                    continue
                out = IMG / local
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_bytes(data)
                ok += 1
            except Exception as e:
                fail.append((local, url, str(e)[:60]))
            time.sleep(0.05)
    (SCRAPE / 'image_ext_fixes.json').write_text(
        json.dumps(ext_fixes, indent=1, sort_keys=True))
    print(f"downloaded={ok} failed={len(fail)} ext_fixes_total={len(ext_fixes)}")
    for row in fail[:20]:
        print("FAIL:", row)


if __name__ == '__main__':
    main()
