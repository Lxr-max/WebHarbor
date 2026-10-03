#!/usr/bin/env python3
"""Validate the source-backed logo additions without pruning legacy assets."""
import hashlib
import json
from pathlib import Path

from PIL import Image


def check(site: Path) -> int:
    manifest = json.loads((site / 'asset_additions.json').read_text())
    seen = set()
    for row in manifest['assets']:
        relative = Path(row['path'])
        if (relative.is_absolute() or '..' in relative.parts
                or relative.parts[:3] != ('static', 'images', 'espn')):
            raise ValueError(f"Invalid asset path: {row['path']}")
        if row['path'] in seen:
            raise ValueError(f"Duplicate asset: {row['path']}")
        seen.add(row['path'])
        path = site / relative
        data = path.read_bytes()
        if len(data) != row['bytes'] or hashlib.sha256(data).hexdigest() != row['sha256']:
            raise ValueError(f"Asset hash mismatch: {relative}")
        with Image.open(path) as image:
            image.load()
            if image.format != 'PNG' or image.size != (row['width'], row['height']):
                raise ValueError(f"Invalid image: {relative}")
    return len(seen)


if __name__ == '__main__':
    print(f'[espn] verified {check(Path(__file__).resolve().parent)} added logos')
