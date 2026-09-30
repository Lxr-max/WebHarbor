"""_support.py — build synthetic verifier run dirs for contract tests."""
import json
import struct
import zlib
from pathlib import Path

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def fake_png(width=4, height=4) -> bytes:
    """Minimal decodable PNG (IHDR + IDAT + IEND)."""

    def chunk(tag, data):
        c = tag + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c))

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    raw = b"".join(b"\x00" + b"\x30\x60\x90" * width for _ in range(height))
    return PNG_MAGIC + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")


def build_run(run_dir: Path, task_id: str, urls, answer: str,
              initial_db: Path, after_db: Path,
              *, start_url=None, no_steps=False, shots=3,
              agent_done=True, terminated=True, task_id_override=None):
    run_dir.mkdir(parents=True, exist_ok=True)
    start = start_url or (urls[0] if urls else "http://localhost:50122/")
    steps = []
    if not no_steps:
        for u in urls:
            steps.append({"action": "goto", "url": str(u),
                          "url_after": str(u), "locator": ""})
    traj = {
        "task_id": task_id_override or task_id,
        "start_url": str(start),
        "terminated": terminated,
        "agent_done": agent_done,
        "final_answer": answer,
        "steps": steps,
    }
    (run_dir / "trajectory.json").write_text(json.dumps(traj), encoding="utf-8")
    shots_dir = run_dir / "screenshots"
    shots_dir.mkdir(exist_ok=True)
    for i in range(shots):
        (shots_dir / f"step_{i:03d}.png").write_bytes(fake_png())
    if initial_db is not None:
        (run_dir / "initial.db").write_bytes(initial_db.read_bytes())
    if after_db is not None:
        (run_dir / "after.db").write_bytes(after_db.read_bytes())
    return run_dir


def seed_db(dest_dir: Path, seed: Path) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    out = dest_dir / "initial.db"
    out.write_bytes(seed.read_bytes())
    return out


def apply_sql(db_path: Path, sql: str):
    import sqlite3
    con = sqlite3.connect(str(db_path))
    try:
        con.executescript(sql)
        con.commit()
    finally:
        con.close()
