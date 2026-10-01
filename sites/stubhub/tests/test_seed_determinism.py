"""Seed reproducibility and byte-identity checks for the stubhub mirror.

Two fresh seeds built from the tracked source snapshot (PYTHONHASHSEED=0)
must produce byte-identical SQLite files, and a second boot over an already
populated database must not touch it — the two halves of the
`/reset/stubhub` byte-identity invariant.

The full stubhub seed takes ~15 seconds per build (20885 listing rows), so
the fresh-seed reproducibility check is marked slow and skipped unless
STUBHUB_SLOW_TESTS is set; the no-op boot check runs against the
already-built instance_seed and is always executed.
"""
import hashlib
import os
import pathlib
import shutil
import subprocess
import sys

import pytest

SITE = pathlib.Path(__file__).resolve().parent.parent
SEED = SITE / "instance_seed" / "stubhub.db"


def _md5(path: pathlib.Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def _boot(db_path: pathlib.Path) -> None:
    env = dict(os.environ)
    env["STUBHUB_DB_PATH"] = f"sqlite:///{db_path}"
    env["PYTHONHASHSEED"] = "0"
    subprocess.run(
        [sys.executable, "-c", "from app import app"],
        cwd=SITE, env=env, check=True,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def test_seed_exists_and_is_populated():
    if not SEED.exists():
        pytest.skip("instance_seed/stubhub.db not built yet")
    import sqlite3
    con = sqlite3.connect(f"file:{SEED}?mode=ro", uri=True)
    try:
        counts = dict(con.execute(
            "SELECT 'events', COUNT(*) FROM events "
            "UNION ALL SELECT 'performers', COUNT(*) FROM performers "
            "UNION ALL SELECT 'venues', COUNT(*) FROM venues "
            "UNION ALL SELECT 'listings', COUNT(*) FROM listings "
            "UNION ALL SELECT 'users', COUNT(*) FROM users "
            "UNION ALL SELECT 'category_nodes', COUNT(*) FROM category_nodes").fetchall())
        assert counts["events"] >= 1000
        assert counts["performers"] >= 500
        assert counts["venues"] >= 250
        assert counts["listings"] >= 15000
        assert counts["users"] == 4
        assert counts["category_nodes"] >= 30
        # every event with listings exposes a price window
        bad = con.execute(
            "SELECT COUNT(*) FROM events WHERE listing_count > 0 "
            "AND (min_price IS NULL OR max_price IS NULL)").fetchone()[0]
        assert bad == 0
    finally:
        con.close()


def test_second_boot_is_a_noop(tmp_path):
    if not SEED.exists():
        pytest.skip("instance_seed/stubhub.db not built yet")
    db = tmp_path / "stubhub.db"
    shutil.copyfile(SEED, db)
    _boot(db)                       # boot over a populated DB
    first = _md5(db)
    _boot(db)                       # boot again
    assert _md5(db) == first, "second boot mutated the database"


@pytest.mark.skipif(not os.environ.get("STUBHUB_SLOW_TESTS"),
                    reason="full seed build takes ~15s; set STUBHUB_SLOW_TESTS=1")
def test_fresh_seed_is_byte_reproducible(tmp_path):
    a, b = tmp_path / "a.db", tmp_path / "b.db"
    _boot(a)
    _boot(b)
    assert _md5(a) == _md5(b), "two fresh seeds differ"
    if SEED.exists():
        assert _md5(a) == _md5(SEED), \
            "freshly built seed differs from the shipped instance_seed"
