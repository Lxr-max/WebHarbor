"""Reviewer controls: copies of synthetic fixtures, not browser trajectories."""
import json
import sqlite3
from pathlib import Path
import pytest
from _support import *

def change_answer(run, fn):
    p=run/'trajectory.json';t=json.loads(p.read_text());t['final_answer']=fn(t['final_answer']);p.write_text(json.dumps(t))


def test_swapped_track_plays_rejected(tmp_path):
    run=honest_run(tmp_path,0)
    change_answer(run,lambda a:a.replace('969,416','SWAP').replace('280,716','969,416').replace('SWAP','280,716'))
    run_verifier(0,run,expect_pass=False)


def test_existing_track_metadata_preserved(tmp_path):
    run=honest_run(tmp_path,7)
    with sqlite3.connect(run/'after.db') as c:c.execute("UPDATE tracks SET title='Unrequested edit' WHERE id=(SELECT MIN(id) FROM tracks)")
    run_verifier(7,run,expect_pass=False)


def test_count_sentence_punctuation_and_plain_numbers(tmp_path):
    run=honest_run(tmp_path,2)
    change_answer(run,lambda a:a.replace('1,988,725','1988725'))
    run_verifier(2,run,expect_pass=True)


def test_negated_play_count_rejected(tmp_path):
    run=honest_run(tmp_path,0)
    change_answer(run,lambda a:a.replace('969,416 plays','not 969,416 plays'))
    run_verifier(0,run,expect_pass=False)
