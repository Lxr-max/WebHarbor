#!/usr/bin/env python3
"""Deterministically pack the nyse asset bundle (nyse.tar.gz).

The HF dataset ships one tarball per site: sites/nyse.tar.gz extracting to
sites/nyse/{instance_seed,static/images,static/external_cache}. nyse carries
the .build-generated-seed marker, so per the repo packing convention
(scripts/extract_assets.sh + scripts/validate_asset_archive.py
--allow-missing-seed) the shipped bundle contains only static/images: the
SQLite seed is deterministically rebuilt at image build time from the tracked
source_data snapshots (PYTHONHASHSEED=0 python3 seed_data.py) and is never
shipped.

This packer reproduces the shipped bundle from the working tree: every file
under static/images/ walked in sorted order, gzip mtime pinned to 0 and every
member mtime normalized to 0 — two runs over the same tree produce
byte-identical output regardless of staging file timestamps, so the shipped
sha256 is reproducible from the branch content alone.
"""
from __future__ import annotations

import argparse
import gzip
import sys
import tarfile
from pathlib import Path

SITE = "nyse"
ALLOWED_ROOTS = ("static/images",)


def collect(site_dir: Path) -> list[tuple[str, Path | None]]:
    """Return sorted (archive_name, filesystem_path) pairs; None marks a dir."""
    members: list[tuple[str, Path | None]] = []
    for root in ALLOWED_ROOTS:
        base = site_dir / root
        members.append((f"{SITE}/{root}", None))
        paths = sorted(
            (p for p in base.rglob("*") if p.is_file() or p.is_dir()),
            key=lambda p: p.relative_to(site_dir).as_posix(),
        )
        for p in paths:
            arc = f"{SITE}/{p.relative_to(site_dir).as_posix()}"
            members.append((arc, None if p.is_dir() else p))
    return members


def pack(site_dir: Path, output: Path) -> None:
    members = collect(site_dir)
    with open(output, "wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as gz:
            with tarfile.open(fileobj=gz, mode="w") as tar:
                for arc, path in members:
                    if path is None:
                        info = tarfile.TarInfo(arc)
                        info.type = tarfile.DIRTYPE
                        info.mode = 0o700
                        info.mtime = 0
                        tar.addfile(info)
                    else:
                        st = path.stat()
                        info = tar.gettarinfo(str(path), arcname=arc)
                        info.uid, info.gid = st.st_uid, st.st_gid
                        info.uname = ""
                        info.gname = ""
                        info.mtime = 0
                        with open(path, "rb") as f:
                            tar.addfile(info, f)
    print(f"[pack] {output} ({output.stat().st_size} bytes, "
          f"{len(members)} members)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--site-dir", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    pack(args.site_dir, args.output)


if __name__ == "__main__":
    main()
