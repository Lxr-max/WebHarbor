"""_support.py — build synthetic verifier runs from fixture specs.

Trajectory shape matches the honest walks: start_url + steps[] (each step
carries its landing URL) + final_answer + terminated/agent_done + at least
one decodable PNG screenshot. DBs are materialized from the frozen seed
(copy) plus the stateful SQL delta when the spec carries one.
"""
import json
import shutil
import sqlite3
import struct
import zlib
from pathlib import Path

BASE = "http://localhost:49115"


def make_png(path: Path):
    """A minimal 1x1 gray PNG (valid header for the screenshot gate)."""
    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 0, 0, 0, 0)
    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    raw = b"\x00\x80"
    path.write_bytes(sig + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def seed_db(tmp: Path, seed_source: Path) -> Path:
    tmp.mkdir(parents=True, exist_ok=True)
    dest = tmp / "initial.db"
    shutil.copyfile(seed_source, dest)
    return dest


def apply_sql(db_path: Path, statements):
    con = sqlite3.connect(db_path)
    try:
        for s in statements:
            con.execute(s)
        con.commit()
    finally:
        con.close()


def build_run(tmp: Path, task_id: str, urls, answer, initial: Path, after: Path,
              *, shots=2, terminate=True, agent_done=True, port=None,
              offsite_url=None, start_url=None, no_steps=False, bad_png=False):
    tmp.mkdir(parents=True, exist_ok=True)
    (tmp / "screenshots").mkdir(exist_ok=True)
    for i in range(max(shots, 1)):
        p = tmp / "screenshots" / f"step_{i:03d}_x.png"
        if bad_png and i == 0:
            p.write_bytes(b"not-a-png")
        else:
            make_png(p)
    start = start_url or (urls[0] if urls else f"{BASE}/")
    steps = []
    if not no_steps:
        for u in urls[1:]:
            steps.append({"n": len(steps) + 1, "action": "goto", "locator": u, "url": u})
    if offsite_url:
        steps.append({"n": len(steps) + 1, "action": "goto", "locator": offsite_url, "url": offsite_url})
    traj = {
        "task_id": task_id,
        "start_url": start,
        "terminated": terminate,
        "agent_done": agent_done,
        "steps": steps,
        "final_answer": answer,
    }
    (tmp / "trajectory.json").write_text(json.dumps(traj, indent=1))
    shutil.copyfile(initial, tmp / "initial.db")
    shutil.copyfile(after, tmp / "after.db")
    return tmp
