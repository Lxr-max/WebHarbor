#!/usr/bin/env python3
"""Deterministic build-time seeder for the verizon mirror.

Thin wrapper: importing app.py materializes the seed inside
`with app.app_context():` via main() (db.create_all + the gated seed
functions); this entry point just runs the same gated path so the script
is idempotent. Run with PYTHONHASHSEED=0 during the image build so the
SQLite output is byte-reproducible: benchmark users use a frozen bcrypt
hash and every other row comes from the tracked source_data/*.json
snapshots plus the deterministic in-code fixtures, in a fixed order.
"""
from app import main

if __name__ == '__main__':
    main()
