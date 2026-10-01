#!/usr/bin/env python3
"""Download every upstream image the iclr mirror renders.

Real upstream media only. Sources:
  - iclr.cc core logos (ICLR-logo.svg, iclr-navbar-logo.svg)
  - blog.iclr.cc wordmark + favicon + keynote/announcement artwork
  - invited-talk speaker headshots (media.iclr.cc and the speaker pages
    the upstream bios list references)
  - organizer portraits (the exact personal-site URLs the upstream
    organizers page renders; the two http:// references are fetched over
    https, which both hosts serve, and the https URL is recorded)
  - the ICLR 2027 venue hero (media.iclr.cc)

Each file is recorded in scraped_data/image_manifest.json with sha256,
byte size, source URL and the captured pages that reference it.

Run from sites/iclr:  python3 scripts_dev/download_images.py
"""
import hashlib
import json
import pathlib
import time
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
IMG = ROOT / "static" / "images"
MANIFEST = ROOT / "scraped_data" / "image_manifest.json"

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

# (relative path under static/images, source URL, used_by)
IMAGES = [
    # core site logos
    ("logos/iclr-logo.svg",
     "https://iclr.cc/static/core/img/ICLR-logo.svg",
     ["site chrome: every page navbar/footer"]),
    ("logos/iclr-navbar-logo.svg",
     "https://iclr.cc/static/core/img/iclr-navbar-logo.svg",
     ["site chrome: every page navbar"]),
    ("logos/blog-logo.svg",
     "https://blog.iclr.cc/wp-content/uploads/ICLR-Logo.svg",
     ["blog_home", "blog_awards", "blog_tot", "blog_keynotes"]),
    ("logos/blog-favicon.png",
     "https://blog.iclr.cc/wp-content/uploads/ICLR-favicon.png",
     ["blog_home"]),
    # invited talk headshots (virtual/2026 bios + talk pages)
    ("speakers/maja_mataric.jpg",
     "https://media.iclr.cc/Conferences/ICLR2026/img/headshots/maria_m.jpg",
     ["event_invited-talk_10020588", "v_invited_bios"]),
    ("speakers/max_welling.jpg",
     "https://media.iclr.cc/Conferences/ICLR2026/img/headshots/Max_Welling.jpg",
     ["event_invited-talk_10020866", "v_invited_bios"]),
    ("speakers/karen_adolph.jpg",
     "https://media.iclr.cc/Conferences/ICLR2026/img/headshots/Karen_Adolph.jpg",
     ["event_invited-talk_10020869", "v_invited_bios"]),
    ("speakers/percy_liang.jpg",
     "https://cs.stanford.edu/~pliang/resources/percy3.jpeg",
     ["event_invited-talk_10020867", "v_invited_bios"]),
    ("speakers/paa.jpg",
     "https://media.iclr.cc/Conferences/ICLR2026/img/headshots/paa.jpg",
     ["event_invited-talk_10021684", "v_invited_bios"]),
    # blog keynote/announcement artwork
    ("blog/bouman_headshot.jpg",
     "https://blog.iclr.cc/wp-content/uploads/bouman_headshot-scaled.jpg",
     ["blog_keynotes"]),
    ("blog/keynote-image-11.png",
     "https://blog.iclr.cc/wp-content/uploads/image-11.png",
     ["blog_keynotes"]),
    ("blog/keynote-image-12.png",
     "https://blog.iclr.cc/wp-content/uploads/image-12.png",
     ["blog_keynotes"]),
    ("blog/keynote-image-13.png",
     "https://blog.iclr.cc/wp-content/uploads/image-13.png",
     ["blog_keynotes"]),
    ("blog/karen_blog.jpg",
     "https://blog.iclr.cc/wp-content/uploads/karen.jpg",
     ["blog_keynotes"]),
    ("blog/paa2025.jpg",
     "https://blog.iclr.cc/wp-content/uploads/paa2025-scaled.jpg",
     ["blog_keynotes"]),
    ("blog/policy-image-14.png",
     "https://blog.iclr.cc/wp-content/uploads/image-14.png",
     ["blog_2027_policies"]),
    # organizer portraits (upstream organizers page)
    ("organizers/portrait-atomium.jpg",
     "https://imaginarynumber.net/img/portrait-atomium.jpg",
     ["v_organizers"]),
    ("organizers/photo-me2.webp",
     "https://www.cs.columbia.edu/~vondrick/img/photo-me2.webp",
     ["v_organizers"]),
    ("organizers/amith-ananthram.jpg",
     "https://amith-ananthram.github.io/images/profile.jpg",
     ["v_organizers"]),
    ("organizers/andre-araujo.jpg",
     "https://andrefaraujo.github.io/images/Andre_Araujo.jpg",
     ["v_organizers"]),
    ("organizers/colin-raffel.jpg",
     "https://colinraffel.com/images/me_small.jpg",
     ["v_organizers"]),
    ("organizers/diyi-yang.jpg",
     "https://cs.stanford.edu/~diyiy/img/Diyi_Yang.jpg",
     ["v_organizers"]),
    ("organizers/yuntian-deng.jpg",
     "https://cs.uwaterloo.ca/computer-science/sites/default/files/styles/uw_is_portrait/public/uploads/images/professor-yuntian-deng.jpg",
     ["v_organizers"]),
    ("organizers/imgur-RKnNyxL.jpeg",
     "https://i.imgur.com/RKnNyxL.jpeg",
     ["v_organizers"]),
    ("organizers/merve.jpg",
     "https://klr-icml2023.github.io/assets/images/merve.jpg",
     ["v_organizers"]),
    ("organizers/liuziyi.jpg",
     "https://liuziyi219.github.io/portrait.jpg",
     ["v_organizers"]),
    ("organizers/david-dobre.jpg",
     "https://media.iclr.cc/Conferences/ICLR2022/headshots/david_dobre.jpg",
     ["v_organizers"]),
    ("organizers/sherry.jpg",
     "https://media.iclr.cc/Conferences/ICLR2022/headshots/sherry_headshot.jpg",
     ["v_organizers"]),
    ("organizers/talha.png",
     "https://media.iclr.cc/Conferences/ICLR2023/img/talha-headshot.png",
     ["v_organizers"]),
    ("organizers/aleksandra-faust.jpg",
     "https://media.iclr.cc/Conferences/ICLR2026/img/headshots/sandra11.jpeg",
     ["v_organizers"]),
    ("organizers/carlo-lucibello.jpg",
     "https://media.iclr.cc/Conferences/ICLR2024/img/headshots/carlo.jpg",
     ["v_organizers"]),
    ("organizers/niklas-gao.jpg",
     "https://n-gao.de/assets/images/profile.jpg",
     ["v_organizers"]),
    ("organizers/nicholas-bergan.jpg",
     "https://njbergam.github.io/images/pic1_zoomed.jpg",
     ["v_organizers"]),
    ("organizers/psc-gradient.png",
     "https://psc-g.github.io/assets/images/psc_gradient.png",
     ["v_organizers"]),
    ("organizers/schwinn.jpg",
     "https://schwinnl.github.io//images/picture.jpg",
     ["v_organizers"]),
    ("organizers/yanan-sui.jpg",
     "https://yanansui.com/src/pi.jpg",
     ["v_organizers"]),
    # ICLR 2027 venue hero (home + 2027 conference page)
    ("venue/venue-hero-2027.jpg",
     "https://media.iclr.cc/Conferences/ICLR2027/venue-hero.jpg",
     ["home", "conf2027"]),
]


def fetch(url, tries=3):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=40) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(2 * (i + 1))
    print(f"[img] FAIL {url}: {str(last)[:100]}")
    return None


def main():
    manifest = []
    for rel, url, used_by in IMAGES:
        out = IMG / rel
        if out.exists():
            data = out.read_bytes()
            print(f"[img] exists {rel} ({len(data)}B)")
        else:
            data = fetch(url)
            if data is None:
                raise SystemExit(f"image fetch failed: {url}")
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(data)
            print(f"[img] fetched {rel} <- {url} ({len(data)}B)")
            time.sleep(0.4)
        manifest.append({
            "file": f"static/images/{rel}",
            "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
            "source_url": url,
            "used_by": used_by,
        })
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    print(f"[img] manifest: {len(manifest)} images")


if __name__ == "__main__":
    main()
