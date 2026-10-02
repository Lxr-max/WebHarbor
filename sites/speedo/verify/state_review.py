"""Preserve existing rows outside the task's reviewed mutations.

Contract values describe seeded records, not browser instructions or answers.
New records remain subject to the task-specific ownership/content checks.
"""
import json
import sqlite3
from pathlib import Path


def check_existing_state(judge, initial_db, after_db, task_id):
    number = task_id.rsplit("--", 1)[-1]
    rules = json.loads(Path(__file__).with_name("existing_state.json").read_text())[number]
    owned = []
    def connect(value):
        if isinstance(value, sqlite3.Connection): return value
        c = sqlite3.connect(f"file:{Path(value).resolve()}?mode=ro", uri=True)
        owned.append(c)
        return c
    before, after = connect(initial_db), connect(after_db)
    try:
        for table, rule in rules.items():
            if task_id == "Speedo--19" and table == "payment_cards": continue
            def snap(c):
                cur = c.execute(f'SELECT * FROM "{table}"')
                cols = [d[0] for d in cur.description]
                rows = [dict(zip(cols, r)) for r in cur]
                return {json.dumps([r[k] for k in rule["key"]]):r for r in rows}
            old, new = snap(before), snap(after)
            errors = []
            for key, row in old.items():
                if key not in new:
                    if key not in rule["deleted"]: errors.append(f"unexpected deletion {key}")
                    continue
                for col, val in row.items():
                    if new[key][col] != val and rule["changed"].get(key, {}).get(col, val) != new[key][col]:
                        errors.append(f"unexpected change {key}.{col}")
            judge.check("preserve_" + table, not errors, "; ".join(errors[:5]))
    finally:
        for c in owned: c.close()
