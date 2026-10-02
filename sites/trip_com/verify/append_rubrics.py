"""Validate reviewer-maintained task/rubric alignment without rewriting tasks."""
import json
from pathlib import Path
root = Path(__file__).resolve().parents[1]
for line in (root / "tasks.jsonl").read_text().splitlines():
    task = json.loads(line)
    assert "answer" not in task
    assert task["judge_rubric"] and task["ques"]
    assert (root.parents[1] / task["verifier_path"]).is_file()
print("Task contracts validated")
