#!/usr/bin/env python3
"""Live no-op against the running r2 container: every verifier must FAIL.

Builds a real agent_demo-shaped run directory (homepage only, empty answer,
clean DB fetched live from the container) and runs all 20 verifiers against
it. All must exit 1 / verdict FAIL (fail-closed).
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, "sites/the_weather_network/verify/tests")
sys.path.insert(0, "sites/the_weather_network/verify")
os.environ["WH_CONTAINER"] = "wh-twn-rereview"
os.environ["TWN_TEST_SEED_DB"] = "/tmp/twn_r2_seed.db"

from _support import RunBuilder, acquire_seed, copy_db  # noqa: E402

BASE = "http://localhost:46099"


def main():
    seed = acquire_seed()
    fails = []
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        for n in range(20):
            run_dir = root / f"noop{n}"
            run_dir.mkdir()
            copy_db(seed, run_dir / "initial.db")
            copy_db(seed, run_dir / "after.db")
            rb = RunBuilder(run_dir, f"The Weather Network--{n}")
            rb.add_step("observe", "/en")
            rb.finish("I looked at the homepage but did not complete the task.")
            r = subprocess.run(
                [sys.executable, f"sites/the_weather_network/verify/verify_{n}.py",
                 "--run_dir", str(run_dir)],
                capture_output=True, text=True)
            try:
                verdict = json.loads(r.stdout)
                ok = (verdict["pass"] is False and r.returncode == 1)
            except Exception:  # noqa: BLE001
                ok = False
                verdict = {"reason": r.stdout[:120] + r.stderr[:120]}
            print(f"T{n}: {'FAIL (correct)' if ok else 'UNEXPECTED'} — {verdict.get('reason', '')[:100]}")
            if not ok:
                fails.append(n)
    print()
    print("LIVE NO-OP: 20/20 FAIL (fail-closed)" if not fails else f"unexpected: {fails}")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
