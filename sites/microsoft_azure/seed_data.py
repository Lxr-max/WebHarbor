#!/usr/bin/env python3
"""Deterministic build-time seeder for the microsoft_azure mirror.

Importing app.py materializes the seed inside the app context
(db.create_all + the gated seed functions); main() re-runs the same gated
path as a no-op so this entry point is idempotent. Run with
PYTHONHASHSEED=0 during the image build so the SQLite output is
byte-reproducible.

    PYTHONHASHSEED=0 python seed_data.py    # build the seed
"""
from app import main

if __name__ == '__main__':
    main()
