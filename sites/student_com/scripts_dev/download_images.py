"""Download all real images for the student_com mirror.

Sources:
- property images: dbswqyg6sdujh.cloudfront.net (from properties_full.json)
- city heroes: image.student.com/<heroImage.source> (from city_graphql.json), fallback first property image
- austin city page: framerusercontent.com base images
- homepage: cdn.student.com heroes + channel logos + university SVGs (icons dir)
- hot-city rail cards: image.student.com/<smallHeroImage.source>

Everything is resized to <=1280px wide, re-encoded JPEG q82 (photos) or kept as-is
(small PNG/SVG/WebP). Writes static/images/** and scraped_data/image_manifest.json
with {path, source_url, sha256, bytes} for asset_inventory.json.
"""
import hashlib, json, pathlib, re, sys, time, urllib.request, urllib.error
from io import BytesIO

from PIL import Image, ImageOps

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRAP = ROOT / "scraped_data"
IMG = ROOT / "static" / "images"
HDRS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36",
    "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
    "Referer": "https://www.student.com/",
    "Accept-Language": "en-US,en;q=0.9",
}
MAX_W = 1280
JPEG_Q = 82

def fetch_bytes(url, retries=4):
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=HDRS)
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code in (404, 403) and attempt >= 1:
                return None
            time.sleep(1 + attempt)
        except Exception:
            time.sleep(1 + attempt)
    return None

def save_image(data, dest: pathlib.Path, resize=True):
    dest.parent.mkdir(parents=True, exist_ok=True)
    suffix = dest.suffix.lower()
    if suffix in (".svg",) or (not resize and suffix in (".png", ".webp")):
        dest.write_bytes(data)
        return
    try:
        img = Image.open(BytesIO(data))
        img = ImageOps.exif_transpose(img)
        if suffix in (".jpg", ".jpeg"):
            img = img.convert("RGB")
            if resize and img.width > MAX_W:
                h = round(img.height * MAX_W / img.width)
                img = img.resize((MAX_W, h), Image.LANCZOS)
            img.save(dest, "JPEG", quality=JPEG_Q, optimize=True, progressive=True)
        else:
            if resize and img.width > MAX_W:
                h = round(img.height * MAX_W / img.width)
                img = img.resize((MAX_W, h), Image.LANCZOS)
            img.save(dest)
    except Exception as e:
        # not a raster image; write raw
        dest.write_bytes(data)

def record(manifest, rel_path, source_url):
    p = IMG / rel_path
    data = p.read_bytes()
    manifest[rel_path] = {
        "source_url": source_url,
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }

def main():
    manifest_path = SCRAP / "image_manifest.json"
    manifest = json.load(open(manifest_path)) if manifest_path.exists() else {}
    props = json.load(open(SCRAP / "properties_full.json"))
    city_gql = json.load(open(SCRAP / "city_graphql.json"))

    # 1. property images
    n_new = 0
    for slug, rec in props.items():
        images = rec.get("images") or []
        for i, im in enumerate(images):
            url = im["url"]
            ext = ".jpg"
            rel = f"properties/{slug}/{i+1:02d}{ext}"
            if rel in manifest:
                continue
            data = fetch_bytes(url)
            if not data:
                print(f"  [miss] {url[:90]}", file=sys.stderr)
                continue
            save_image(data, IMG / rel)
            record(manifest, rel, url)
            n_new += 1
            if n_new % 100 == 0:
                manifest_path.write_text(json.dumps(manifest, indent=1))
                print(f"[props] {n_new} new images (last: {rel})", flush=True)
            time.sleep(0.15)
    manifest_path.write_text(json.dumps(manifest, indent=1))
    print(f"property images done: +{n_new}, total manifest {len(manifest)}")

    # 2. city heroes
    for slug, c in city_gql.items():
        if c is None:
            continue
        rel = f"cities/{slug}-hero.jpg"
        if rel in manifest:
            continue
        src = (c.get("heroImage") or {}).get("source")
        url = f"https://image.student.com/{src}" if src else None
        data = fetch_bytes(url) if url else None
        if not data:
            # fallback: first property image of this city
            for pslug, prec in props.items():
                if prec.get("city_slug") == slug and prec.get("images"):
                    data = fetch_bytes(prec["images"][0]["url"])
                    url = prec["images"][0]["url"]
                    break
        if data:
            save_image(data, IMG / rel)
            record(manifest, rel, url)
            print(f"hero {slug}: {len(data)} bytes from {url[:60] if url else ''}")
        else:
            print(f"hero {slug}: MISSING", file=sys.stderr)
    manifest_path.write_text(json.dumps(manifest, indent=1))

    # 3. homepage + brand assets
    home_assets = {
        "home/hero-banner-new.png": "https://cdn.student.com/student-website/images/hero-banner-new.png",
        "home/hero-banner-mobile.png": "https://cdn.student.com/student-website/images/hero-banner-mobile-new.png",
        "home/woman-with-computer.webp": "https://cdn.student.com/student-website/images/woman-with-computer.webp",
        "home/woman-with-tablet.webp": "https://cdn.student.com/student-website/images/woman-with-tablet.webp",
        "home/trustpilot.webp": "https://cdn.student.com/student-website/images/trustpilot-image.webp",
        "home/hp-hero-default.jpg": "https://cdn.student.com/bundles/microapp-home-page/images/public/hero-banner/hp-hero-default@1x.jpg",
        "brand/bloomberg.png": "https://cdn.student.com/student-website/images/channels/BloombergLogo.png",
        "brand/financial-times.png": "https://cdn.student.com/student-website/images/channels/FinancialTimesLogo.png",
        "brand/forbes.png": "https://cdn.student.com/student-website/images/channels/ForbesLogo.png",
        "brand/techcrunch.png": "https://cdn.student.com/student-website/images/channels/TechCrunchLogo.png",
        "brand/venturebeat.png": "https://cdn.student.com/student-website/images/channels/VentureBeatLogo.png",
    }
    for rel, url in home_assets.items():
        if rel in manifest:
            continue
        data = fetch_bytes(url)
        if not data:
            print(f"  [miss] {url}", file=sys.stderr)
            continue
        save_image(data, IMG / rel, resize=False)
        record(manifest, rel, url)
        print(f"home asset {rel}: {len(data)}")
    manifest_path.write_text(json.dumps(manifest, indent=1))
    print("manifest size:", len(manifest))

if __name__ == "__main__":
    main()
