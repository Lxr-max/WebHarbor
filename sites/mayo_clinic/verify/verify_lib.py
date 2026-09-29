#!/usr/bin/env python3
"""Apartments.com deterministic graders.

Ground truth is hardcoded in this package. tasks.jsonl carries only the
task text, verifier path, and a rubric that states rules rather than answers.
"""

import argparse
import json
import os
import re
import sys
import tempfile
from pathlib import Path

from checks import fold, has_num, has_phrase, near
from contracts import TASKS

SITE = "mayo_clinic"


def observed_urls(traj):
    base = traj.get("start_url") or ""
    found = []
    for step in traj.get("steps") or []:
        for key in ("url", "url_after"):
            raw = step.get(key)
            if isinstance(raw, str) and raw.strip():
                found.append(raw.strip())
    final = traj.get("final_url")
    if isinstance(final, str) and final.strip():
        found.append(final.strip())
    if base:
        from urllib.parse import urljoin
        found = [urljoin(base, item) for item in found]
    return found


def navigation_ok(patterns, traj):
    urls = observed_urls(traj)
    blob = "\n".join(urls)
    missing = [pattern for pattern in patterns if not re.search(pattern, blob)]
    return not missing, urls


def answer_ok(spec, answer):
    if not (answer or "").strip():
        return False, "empty answer"
    for phrase in spec.get("phrases") or []:
        if not has_phrase(answer, phrase):
            return False, f"missing phrase {phrase!r}"
    for value in spec.get("numbers") or []:
        if not has_num(answer, value):
            return False, f"missing number {value}"
    window = spec.get("window", 240)
    for anchor, value in spec.get("bind") or []:
        if not near(answer, anchor, value, window):
            return False, f"{value!r} is not bound to {anchor!r}"
    atleast = spec.get("at_least")
    if atleast:
        needed, options = atleast
        hit = [phrase for phrase in options if has_phrase(answer, phrase)]
        if len(hit) < needed:
            return False, f"only {len(hit)} of {needed} options"
    predicate = spec.get("pred")
    if predicate is not None and not predicate(answer):
        return False, "subject or polarity check failed"
    return True, "answer matched the labelled facts"


def evaluate(task_index, traj, initial_db="", after_db=""):
    spec = TASKS[task_index]
    answer = str(traj.get("final_answer") or "")
    nav_pass, urls = navigation_ok(spec.get("nav") or [], traj)
    ans_pass, ans_detail = answer_ok(spec, answer)
    checks = [
        ("required_navigation", nav_pass, f"observed={urls!r}"),
        ("frozen_answer", ans_pass, ans_detail),
    ]
    if spec.get("state"):
        ok, detail = spec["state"](initial_db, after_db, answer, traj)
        checks.append(("after_state", ok, detail))
    return {
        "task_id": spec["task_id"],
        "pass": all(ok for _, ok, _ in checks),
        "reason": next((name for name, ok, _ in checks if not ok), ""),
        "evidence": [
            f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}"
            for name, ok, detail in checks
        ],
    }


def load_run(run_dir):
    return json.loads((Path(run_dir) / "trajectory.json").read_text())


def main(task_index):
    parser = argparse.ArgumentParser()
    parser.add_argument("--run_dir", required=True)
    parser.add_argument("--initial_db", default="")
    parser.add_argument("--after_db", default="")
    parser.add_argument("--container", default=os.environ.get("WH_CONTAINER", ""))
    parser.add_argument("--no_llm", nargs="?", const="True", default="True")
    args = parser.parse_args()
    traj = load_run(args.run_dir)
    initial, after = args.initial_db, args.after_db
    if TASKS[task_index].get("state") and not (initial or after):
        run_dir = Path(args.run_dir)
        snap_i = run_dir / "initial_state.db"
        snap_a = run_dir / "after_state.db"
        if snap_i.exists() or snap_a.exists():
            initial, after = str(snap_i), str(snap_a)
    with tempfile.TemporaryDirectory(prefix=f"{SITE}-grade-"):
        verdict = evaluate(task_index, traj, initial, after)
    print(json.dumps(verdict, indent=2))
    sys.exit(0 if verdict["pass"] else 1)
