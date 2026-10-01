#!/usr/bin/env python3
"""Bind the downloaded image files into source_data/.

After download_images.py finishes, every entity's local file is recorded
as an image_path (the /static/... URL the mirror renders) in the tracked
source_data/*.json snapshots. Events that share an upstream image reuse
the shared file (exactly like the upstream site renders the same asset).
Shop products without a downloaded image are dropped from the snapshot so
the seed only ships products that render a real upstream photo.
"""
from __future__ import annotations

import json
from pathlib import Path

SITE = Path(__file__).resolve().parents[1]
SOURCE = SITE / "source_data"
IMAGE_MAP = json.loads((SITE / "scraped_data" / "image_map.json").read_text())


def load(path):
    return json.loads((SOURCE / path).read_text(encoding="utf-8"))


def save(path, obj):
    (SOURCE / path).write_text(
        json.dumps(obj, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def local(category: str, slug: str) -> str | None:
    return IMAGE_MAP.get(f"{category}/{slug}")


def main() -> None:
    # products
    data = load("products.json")
    for p in data["products"]:
        p["can_image_path"] = local("products/cans", p["slug"])
        p["scene_image_path"] = local("products/scenes", p["slug"])
    missing = [p["slug"] for p in data["products"] if not p["can_image_path"]]
    if missing:
        print("products missing can images:", missing)
    save("products.json", data)

    # events
    data = load("events.json")
    for e in data["events"]:
        e["image_path"] = local("events", e["slug"])
    dropped = [e["slug"] for e in data["events"] if not e["image_path"]]
    if dropped:
        print(f"events without images (dropped): {dropped}")
        data["events"] = [e for e in data["events"] if e["image_path"]]
    data["count"] = len(data["events"])
    save("events.json", data)

    # series
    data = load("event_series.json")
    for s in data["series"]:
        s["image_path"] = local("series", s["slug"])
    save("event_series.json", data)

    # athletes
    data = load("athletes.json")
    for a in data["athletes"]:
        a["image_path"] = local("athletes", a["slug"])
    dropped = [a["slug"] for a in data["athletes"] if not a["image_path"]]
    if dropped:
        print(f"athletes without images (dropped): {dropped}")
        data["athletes"] = [a for a in data["athletes"] if a["image_path"]]
    data["count"] = len(data["athletes"])
    save("athletes.json", data)

    # films / shows / stories
    for name, key, folder in (("films.json", "films", "films"),
                             ("shows.json", "shows", "shows"),
                             ("stories.json", "stories", "stories")):
        data = load(name)
        for it in data[key]:
            it["image_path"] = local(folder, it["slug"])
        dropped = [it["slug"] for it in data[key] if not it["image_path"]]
        if dropped:
            print(f"{key} without images (dropped {len(dropped)}): {dropped[:8]}")
            data[key] = [it for it in data[key] if it["image_path"]]
        data["count"] = len(data[key])
        save(name, data)

    # shop: keep only products with a downloaded image
    data = load("shop_products.json")
    kept = []
    for p in data["products"]:
        p["image_path"] = local("shop", p["handle"])
        if p["image_path"]:
            kept.append(p)
    print(f"shop: kept {len(kept)}/{len(data['products'])}")
    data["products"] = kept
    data["count"] = len(kept)
    save("shop_products.json", data)

    print("bind complete")


if __name__ == "__main__":
    main()
