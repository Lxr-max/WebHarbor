#!/usr/bin/env python3
"""Build the trader_joes seed database from the tracked source_data snapshots.

Run with PYTHONHASHSEED=0 for a byte-reproducible artifact (the boot path
in the image does this automatically; see .build-generated-seed).
"""
import os

if __name__ == '__main__':
    from app import main
    main()
