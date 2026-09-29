#!/usr/bin/env python3
"""extract_fixtures.py — rebuild tests/fixtures_data.py from the reviewer's
honest live runs (trajectories + DB snapshots). The checked-in fixtures are
the contract; re-extraction requires the review evidence dir.
"""
import json
import sqlite3
import sys
from pathlib import Path

EVID = Path("/data/zhaoyang-user-projects/websyn/wh-ziprecruiter-review-evidence")
OUT = Path(__file__).resolve().parent / "tests" / "fixtures_data.py"

# stateful tasks: SQL that reproduces the observed DB delta on a seed copy
STATEFUL_SQL = {
    15: [
        "INSERT INTO users (id, email, display_name, password_hash, is_benchmark, created_at) "
        "VALUES (5, 'fixture.t15@contract.test', 'Contract Fixture', "
        "'$2b$12$2Ru8s5Tbn3OBUjRrdXf3SuuUzsNhc8mk9gkS.jTEgQjwqoMMDbngi', 0, '2026-09-29')",
        "INSERT INTO profiles (id, user_id, phone, location, headline, about, years_experience, willing_remote) "
        "VALUES (5, 5, NULL, 'Dallas, TX', NULL, NULL, NULL, 0)",
        "INSERT INTO applications (id, user_id, job_id, applied_at, status, cover_note) "
        "VALUES (5, 5, 11, '2026-09-29', 'Applied', NULL)",
        "INSERT INTO application_events (id, application_id, status, note, occurred_at) "
        "VALUES (10, 5, 'Applied', '1-Click Application submitted', '2026-09-29')",
    ],
    16: [
        "DELETE FROM saved_jobs WHERE id = 1",
        "INSERT INTO job_alerts (id, user_id, term, location, frequency, created_at) "
        "VALUES (6, 1, 'licensed practical nurse', 'Brooklyn, NY', 'daily', '2026-09-29')",
    ],
    17: [
        "DELETE FROM saved_jobs WHERE id = 4",
        "INSERT INTO job_alerts (id, user_id, term, location, frequency, created_at) "
        "VALUES (6, 2, 'data engineer', 'Seattle, WA', 'weekly', '2026-09-29')",
    ],
    18: [
        "UPDATE resumes SET updated_at = '2026-09-29', skills = "
        "'[[\"NetSuite\", \"5\"], [\"Month-end close\", \"8\"], [\"GAAP\", \"8\"], [\"Excel\", \"8\"], "
        "[\"Audit prep\", \"6\"], [\"SQL\", \"3\"], [\"QuickBooks\", \"2\"]]' WHERE user_id = 4",
    ],
}


def urls_of(traj):
    out = []
    if traj.get("start_url"):
        out.append(str(traj["start_url"]))
    for step in traj.get("steps", []):
        for key in ("url", "url_after"):
            if step.get(key):
                out.append(str(step[key]))
        if step.get("action") == "goto" and str(step.get("locator", "")).startswith("http"):
            out.append(str(step["locator"]))
    dedup = []
    for u in out:
        if not dedup or u != dedup[-1]:
            dedup.append(u)
    return dedup


def main():
    specs = {}
    for n in range(20):
        rd = EVID / "runs_round1" / str(n)
        traj = json.loads((rd / "trajectory.json").read_text())
        spec = {
            "answer": traj["final_answer"],
            "urls": urls_of(traj),
        }
        if n in STATEFUL_SQL:
            spec["sql"] = STATEFUL_SQL[n]
        specs[str(n)] = spec
    body = ['"""Honest fixtures frozen from the reviewer\'s two independent',
            'Playwright rounds (identical per-task facts across both rounds) on',
            'wh-ziprecruiter-review, seed md5 6d6830746bd74d5b19b91c983dec0c3c.',
            'Stateful tasks carry the exact SQL that reproduces their observed',
            'DB delta on a seed copy."""',
            'BASE = "http://localhost:49115"',
            f"SPECS = {specs!r}", ""]
    OUT.write_text("\n".join(body).replace("'", "'") , encoding="utf-8")
    print(f"wrote {OUT} with {len(specs)} specs")


if __name__ == "__main__":
    main()
