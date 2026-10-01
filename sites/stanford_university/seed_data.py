#!/usr/bin/env python3
"""Build the stanford_university seed database from the tracked source_data
snapshots.

Run with PYTHONHASHSEED=0 for a byte-reproducible artifact (the Dockerfile
does exactly that at image build time; see .build-generated-seed).
"""
import os

if __name__ == '__main__':
    from app import create_all_and_seed
    create_all_and_seed()
