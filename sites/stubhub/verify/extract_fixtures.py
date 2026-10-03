#!/usr/bin/env python3
"""Extract fixtures_data.py SPECS from the reviewer's honest live runs.

For each task: the visited URL sequence, the final answer, and (stateful
tasks) the exact SQL that reproduces the observed DB delta on a seed copy.
Output: verify/tests/fixtures_data.py (frozen, LLM-free).
"""
import json
import sqlite3
import sys
from pathlib import Path

EVID = Path("/data/zhaoyang-user-projects/websyn/wh-stubhub-review-evidence")
OUT = Path(__file__).resolve().parent / "tests" / "fixtures_data.py"

READ_ONLY = {0, 1, 2, 7, 8, 9, 10, 13, 14, 15, 16, 17, 18, 20}
STATEFUL = {3, 4, 5, 6, 11, 12, 19}


def run_dir(n):
    return (EVID / "runs-ref" / f"StubHub--{n}" if n in (6, 19)
            else EVID / "runs" / f"StubHub--{n}")


def urls(traj):
    out = []
    for step in traj["steps"]:
        u = step.get("url_after") or ""
        # strip the run's origin (46096/46097) -> path only; the tests rebase to BASE
        for port in ("46096", "46097"):
            u = u.replace(f"http://localhost:{port}", "")
        if u and (not out or out[-1] != u):
            out.append(u)
    return out


def sql_literal(v):
    if v is None:
        return "NULL"
    if isinstance(v, (int, float)):
        return repr(v)
    s = str(v).replace("'", "''")
    return f"'{s}'"


def delta_sql(n, initial, after):
    """Exact SQL statements reproducing the after-state on a seed copy."""
    tables = {3: ("orders", "listings", "notifications"),
              4: ("listings", "events"),
              5: ("gift_card_orders",),
              6: ("favorites", "performers"),
              11: ("payment_cards",),
              12: ("users", "orders", "listings", "payment_cards", "notifications"),
              19: ("users", "gift_card_orders", "favorites", "performers")}[n]
    stmts = []

    def snap(db, t):
        cols = [c[1] for c in db.execute(f"PRAGMA table_info({t})")]
        pk = [c[1] for c in db.execute(f"PRAGMA table_info({t})") if c[5]] or cols[:1]
        return cols, pk, {tuple(r[k] for k in pk): dict(r)
                          for r in db.execute(f'SELECT * FROM "{t}"')}

    a = sqlite3.connect(f"file:{initial}?mode=ro", uri=True); a.row_factory = sqlite3.Row
    b = sqlite3.connect(f"file:{after}?mode=ro", uri=True); b.row_factory = sqlite3.Row
    for t in tables:
        cols, pk, ra = snap(a, t)
        _, _, rb = snap(b, t)
        for key, row in rb.items():
            if key not in ra:
                stmts.append(
                    f'INSERT INTO "{t}" ({", ".join(cols)}) VALUES '
                    f'({", ".join(sql_literal(row[c]) for c in cols)})')
        for key in ra:
            if key not in rb:
                stmts.append(f'DELETE FROM "{t}" WHERE '
                             + " AND ".join(f'"{k}" = {sql_literal(v)}' for k, v in zip(pk, key)))
        for key in set(ra) & set(rb):
            if ra[key] != rb[key]:
                sets = ", ".join(f'"{c}" = {sql_literal(rb[key][c])}'
                                 for c in cols if ra[key][c] != rb[key][c])
                stmts.append(f'UPDATE "{t}" SET {sets} WHERE '
                             + " AND ".join(f'"{k}" = {sql_literal(v)}' for k, v in zip(pk, key)))
    a.close(); b.close()
    return stmts


def main():
    specs = {}
    for n in sorted(READ_ONLY | STATEFUL):
        d = run_dir(n)
        traj = json.loads((d / "trajectory.json").read_text())
        spec = {"urls": urls(traj), "answer": traj["final_answer"]}
        if n in STATEFUL:
            spec["sql"] = delta_sql(n, d / "initial.db", d / "after.db")
        specs[n] = spec
        print(f"T{n}: {len(spec['urls'])} urls, answer {len(spec['answer'])} chars, "
              f"{len(spec.get('sql', []))} sql stmts")

    body = ['"""Frozen fixtures for the stubhub verifier tests.',
            '',
            'Extracted programmatically from the reviewer\'s 21 honest live runs',
            '(real Chromium trajectories + initial/after SQLite snapshots). The stateful SQL',
            'reproduces the exact observed row deltas on a copy of the deterministic seed.',
            'No LLM, no live browser needed: the tests rebuild agent_demo-shaped runs from',
            'these SPECS. Honest runs for T6/T19 come from the with-images reference build',
            '(the canonical build blocks the performer Follow button — see the review report;',
            'the DB deltas are identical because the seeds differ only in performers.image_file',
            'and performers.node_id).',
            '"""',
            'BASE = "http://localhost:40105"',
            'SPECS = ' + json.dumps(specs, indent=1, ensure_ascii=False)]
    OUT.write_text("\n".join(body) + "\n")
    print(f"\nwrote {OUT} ({OUT.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
