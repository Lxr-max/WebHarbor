"""Contract tests: registry shape, task rows, asset inventory, seeded data."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

SITE_DIR = Path(__file__).resolve().parents[1]
# Reviewer pass (orch/review/verizon) appends the grading-contract keys to
# each task row: verifier_path + judge_rubric. The five original task
# definition keys stay byte-identical; the two appended keys are validated
# here as part of the post-review shape.
TASK_KEYS = {"web_name", "id", "ques", "web", "upstream_url"}
REVIEWER_KEYS = {"verifier_path", "judge_rubric"}
# Integrate rail (student_com/twn precedent): tasks.jsonl `web` is normalized
# to the wave-order registration slot (origin/main count 112 + 60, position
# 61) — port 40172 on this branch. The audit/contribute rails keep the
# branch-local registry slot 40099.
WEB_PORT = "http://localhost:40132/"


def load_tasks():
    rows = []
    for line in (SITE_DIR / "tasks.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def test_tasks_shape():
    rows = load_tasks()
    assert 15 <= len(rows) <= 25
    for row in rows:
        assert set(row) == TASK_KEYS | REVIEWER_KEYS
        assert row["web"] == WEB_PORT
        assert row["upstream_url"] == "https://www.verizon.com/"
        assert re.match(r"^Verizon--\d+$", row["id"])
        assert len(row["ques"].split()) <= 100
        # reviewer contract keys: verifier exists, rubric is non-empty rules
        assert "answer" not in row
        assert (SITE_DIR.parent.parent / row["verifier_path"]).is_file(), row["verifier_path"]
        assert row["verifier_path"].startswith("sites/verizon/verify/verify_")
        assert row["judge_rubric"].strip()


def test_asset_inventory_covers_files():
    manifest = json.loads((SITE_DIR / "asset_inventory.json").read_text())
    assert manifest["schema_version"] == 1
    assert manifest["site"] == "verizon"
    listed = {row["path"] for row in manifest["assets"]}
    assert len(listed) == len(manifest["assets"]) == manifest["asset_count"]
    actual = {
        str(p.relative_to(SITE_DIR))
        for root in ("static/images",)
        for p in (SITE_DIR / root).rglob("*")
        if p.is_file() and p.name != ".gitkeep"
    }
    assert actual == listed, (sorted(actual - listed)[:3], sorted(listed - actual)[:3])
    for row in manifest["assets"]:
        data = (SITE_DIR / row["path"]).read_bytes()
        assert len(data) == row["bytes"]
        assert hashlib.sha256(data).hexdigest() == row["sha256"]
        assert row["source_url"].startswith("https://")


def test_no_duplicate_images():
    """Every managed file must be a distinct upstream file (no repeated bytes)."""
    manifest = json.loads((SITE_DIR / "asset_inventory.json").read_text())
    hashes = [row["sha256"] for row in manifest["assets"]]
    assert len(hashes) == len(set(hashes)), "duplicate image content in inventory"


def test_source_data_present():
    for name in ("devices.json", "plans.json", "stores.json", "pages.json",
                 "store_city_index.json"):
        assert (SITE_DIR / "source_data" / name).is_file()
    devices = json.loads((SITE_DIR / "source_data" / "devices.json").read_text())
    assert len(devices) >= 20
    stores = json.loads((SITE_DIR / "source_data" / "stores.json").read_text())
    assert len(stores) >= 800


def test_health_counts():
    with __import__("app").app.test_client() as c:
        r = c.get("/_health")
        assert r.status_code == 200
        data = r.get_json()
        assert data["ok"] is True
        assert data["devices"] >= 20
        assert data["stores"] >= 800
        assert data["bills"] >= 12
        assert data["trade_in_quotes"] >= 20
        assert data["troubleshoot_flows"] >= 8
