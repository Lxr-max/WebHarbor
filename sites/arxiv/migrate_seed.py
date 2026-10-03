#!/usr/bin/env python3
"""Apply source-checked metadata repairs before the arXiv reset seed ships.

Used by fetch_assets.sh in staging and by Docker at build time. Never run on
startup: the packaged seed is already clean, so resetting requires no DB writes.
Only exact captured titles are replaced; user state and scientific abstracts
are untouched. A missing DB fails instead of creating an empty SQLite file.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sqlite3

from metadata_cleaning import clean_paper_metadata_fields


def migrate(path: Path, *, check: bool = False) -> int:
    uri = path.resolve().as_uri() + "?mode=" + ("ro" if check else "rw")
    with sqlite3.connect(uri, uri=True) as connection:
        connection.row_factory = sqlite3.Row
        updates = []
        for paper in connection.execute("SELECT arxiv_id, title FROM papers"):
            fields = clean_paper_metadata_fields(dict(paper))
            if "title" in fields:
                updates.append((fields["title"], paper["arxiv_id"], paper["title"]))
        if updates and not check:
            connection.executemany(
                "UPDATE papers SET title=? WHERE arxiv_id=? AND title=?", updates
            )
    return len(updates)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("db", nargs="?", type=Path,
                        default=Path(__file__).parent / "instance_seed/arxiv.db")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    count = migrate(args.db, check=args.check)
    print(f"[arxiv metadata] {count} {'pending' if args.check else 'corrected'} titles")
    return int(args.check and count > 0)


if __name__ == "__main__":
    raise SystemExit(main())
