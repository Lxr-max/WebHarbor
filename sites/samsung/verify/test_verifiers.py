#!/usr/bin/env python3
"""Adversarial test suite for the samsung reviewer verifiers.

Every honest fixture (the reviewer's two-round Chromium runs) must PASS its
verifier; every adversarial mutation must FAIL (zero false positives):

  - no-op trajectories (no steps, no answer)            FAIL
  - answer-only shortcuts (claims without navigation)   FAIL
  - shortcut URLs (drop required surfaces)               FAIL
  - wrong / fabricated answers (per claim and DB-peek
    values for non-rendered question points)            FAIL
  - stale after-state (delta applied to the wrong task) FAIL
  - pre-mutated initial seed                            FAIL
  - tampered packages (wrong task_id, off-site URL,
    cross-port URL, unterminated, empty answer,
    corrupt screenshot)                                 FAIL
  - task confusion (right claims, wrong state)         FAIL

Run:  python3 test_verifiers.py
"""
import json
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import verify_lib as V  # noqa: E402

RUNS = Path("/data/zhaoyang-user-projects/websyn/wh-samsung-review-evidence/runs_r2")
RUNS_R1 = Path("/data/zhaoyang-user-projects/websyn/wh-samsung-review-evidence/runs")
CASES = []


def case(name):
    def deco(fn):
        CASES.append((name, fn))
        return fn
    return deco


def load_spec(task_id):
    idx = int(task_id.split("--")[1])
    ns = {"__file__": str(HERE / f"verify_{idx}.py"),
          "__name__": f"verify_{idx}"}
    exec((HERE / f"verify_{idx}.py").read_text(), ns)
    return ns["SPEC"]


def fresh_copy(task_idx, dest: Path):
    src = RUNS / "round1" / str(task_idx)
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest)
    return dest


_COUNT = [0]


def verdict(task_id, run_dir, expect_pass, label):
    _COUNT[0] += 1
    spec = load_spec(task_id)
    try:
        V.verify(run_dir, spec)
        ok = True
        why = ""
    except V.Fail as e:
        ok = False
        why = str(e)
    except Exception as e:  # corrupt db / missing files etc.
        ok = False
        why = f"hard failure: {e}"
    if ok == expect_pass:
        print(f"  ok   {label}")
        return True
    print(f"  FAIL {label}: expected {'PASS' if expect_pass else 'FAIL'}"
          f"{' — ' + why if why else ''}")
    return False


def run_all():
    tmp = Path(tempfile.mkdtemp(prefix="wh-samsung-verifiers-"))
    passed = 0

    print("== honest fixtures (r2 rounds 1 + 2) ==")
    for i in range(20):
        tid = f"Samsung--{i}"
        ok1 = verdict(tid, RUNS / "round1" / str(i), True, f"honest r1 T{i}")
        ok2 = verdict(tid, RUNS / "round2" / str(i), True, f"honest r2 T{i}")
        passed += (1 if ok1 else 0) + (1 if ok2 else 0)

    print("== no-op trajectories ==")
    for i in range(20):
        tid = f"Samsung--{i}"
        d = fresh_copy(i, tmp / f"noop{i}")
        traj = json.loads((d / "trajectory.json").read_text())
        traj["steps"] = []
        traj["final_answer"] = ""
        (d / "trajectory.json").write_text(json.dumps(traj))
        passed += verdict(tid, d, False, f"no-op T{i}")

    print("== answer-only shortcuts (navigation stripped) ==")
    for i in range(20):
        tid = f"Samsung--{i}"
        d = fresh_copy(i, tmp / f"short{i}")
        traj = json.loads((d / "trajectory.json").read_text())
        home = traj["start_url"] + "/"
        for s in traj["steps"]:
            s["url"] = home
            s["url_after"] = home
        (d / "trajectory.json").write_text(json.dumps(traj))
        passed += verdict(tid, d, False, f"shortcut T{i}")

    print("== wrong answers ==")
    for i in range(20):
        tid = f"Samsung--{i}"
        d = fresh_copy(i, tmp / f"wrong{i}")
        traj = json.loads((d / "trajectory.json").read_text())
        traj["final_answer"] = ("The answer is 999 and everything else is "
                                "completely different too.")
        (d / "trajectory.json").write_text(json.dumps(traj))
        passed += verdict(tid, d, False, f"wrong answer T{i}")

    print("== fabricated values (wrong data not shown on any page) ==")
    # r2: the battery value IS on the page now, so the fabrication guard pins
    # a WRONG value instead (4800 mAh appears neither on the page nor in the
    # DB; the honest 5000 mAh is a positive claim above)
    d = fresh_copy(4, tmp / "peek4")
    traj = json.loads((d / "trajectory.json").read_text())
    traj["final_answer"] = traj["final_answer"].replace("5000 mAh", "4800 mAh")
    if "4800" not in traj["final_answer"]:
        traj["final_answer"] += " Its battery capacity is 4800 mAh."
    (d / "trajectory.json").write_text(json.dumps(traj))
    passed += verdict("Samsung--4", d, False, "T4 fabricated 4800 mAh")

    # r2: the heavier-model fact correction — the old wrong claim (S26 Ultra)
    # must FAIL; the honest answer says the S25 Ultra is heavier
    d = fresh_copy(19, tmp / "peek19")
    traj = json.loads((d / "trajectory.json").read_text())
    traj["final_answer"] = traj["final_answer"].replace(
        "the Galaxy S25 Ultra is heavier", "the Galaxy S26 Ultra is heavier")
    (d / "trajectory.json").write_text(json.dumps(traj))
    passed += verdict("Samsung--19", d, False, "T19 wrong heavier model")

    print("== r2 render-fix regressions (stale r1 answers must FAIL) ==")
    # the battery value was unreachable in r1 and became page-visible with
    # the fix; an r1-era honest-absence trajectory must fail the r2 contract
    d = fresh_copy(4, tmp / "stale4")
    shutil.copytree(RUNS_R1 / "round1" / "4", d, dirs_exist_ok=True)
    (d / "initial.db").write_bytes(
        (RUNS_R1 / "round1" / "4" / "initial.db").read_bytes())
    passed += verdict("Samsung--4", d, False,
                      "T4 stale r1 absence answer (battery)")

    # the compare form renders only one column in r1 and every checked model
    # after the fix; an r1-era single-column trajectory must fail r2
    d = fresh_copy(8, tmp / "stale8")
    shutil.copytree(RUNS_R1 / "round1" / "8", d, dirs_exist_ok=True)
    passed += verdict("Samsung--8", d, False,
                      "T8 stale r1 single-column answer")

    print("== stale / wrong state ==")
    # T0's wishlist add applied to the wrong user (bob instead of alice)
    d = fresh_copy(0, tmp / "stale0")
    con = sqlite3.connect(d / "after.db")
    con.execute("UPDATE wishlist_items SET user_id = 2 WHERE user_id = 1 "
                "AND product_slug = 'galaxy-a17-5g'")
    con.commit()
    con.close()
    passed += verdict("Samsung--0", d, False, "T0 wrong-owner wishlist delta")

    # T5: cart left with the wrong quantity
    d = fresh_copy(5, tmp / "stale5")
    con = sqlite3.connect(d / "after.db")
    con.execute("UPDATE cart_items SET qty = 1")
    con.commit()
    con.close()
    passed += verdict("Samsung--5", d, False, "T5 wrong cart quantity")

    # T7: order placed with the wrong total
    d = fresh_copy(7, tmp / "stale7")
    con = sqlite3.connect(d / "after.db")
    con.execute("UPDATE orders SET total = 999.99 WHERE order_no LIKE 'SS-1%'")
    con.commit()
    con.close()
    passed += verdict("Samsung--7", d, False, "T7 wrong order total")

    # T11: read-only task with a polluted after-state
    d = fresh_copy(11, tmp / "stale11")
    con = sqlite3.connect(d / "after.db")
    con.execute("INSERT INTO wishlist_items (user_id, product_slug, added_ts) "
                "VALUES (2, 'galaxy-z-flip8', '2026-09-30T00:00:00Z')")
    con.commit()
    con.close()
    passed += verdict("Samsung--11", d, False, "T11 read-only pollution")

    # T16: read-only task with an extra support ticket
    d = fresh_copy(16, tmp / "stale16")
    con = sqlite3.connect(d / "after.db")
    con.execute("INSERT INTO support_tickets (ticket_no, user_id, email, "
                "category, topic, subject, message, status, created_ts) "
                "VALUES ('ST-999999', 1, 'x@y.z', 'c', 't', 's', 'm', 'Open', "
                "'2026-09-30T00:00:00Z')")
    con.commit()
    con.close()
    passed += verdict("Samsung--16", d, False, "T16 read-only pollution")

    # T6: the removed cart item left a row behind
    d = fresh_copy(6, tmp / "stale6")
    con = sqlite3.connect(d / "after.db")
    con.execute("INSERT INTO cart_items (cart_key, configurator, model_code, "
                "title, options, unit_price, qty, image) VALUES "
                "('user:2', 'smartphones_galaxy-z-fold8-ultra', "
                "'SM-F976UDGFXAA', 'x', '{}', 2399.99, 3, '')")
    con.commit()
    con.close()
    passed += verdict("Samsung--6", d, False, "T6 leftover cart row")

    print("== pre-mutated initial seed ==")
    for i in (0, 7, 12):
        tid = f"Samsung--{i}"
        d = fresh_copy(i, tmp / f"premut{i}")
        con = sqlite3.connect(d / "initial.db")
        con.execute("INSERT INTO wishlist_items (user_id, product_slug, "
                    "added_ts) VALUES (4, 'galaxy-s26', '2026-09-30T00:00:00Z')")
        con.commit()
        con.close()
        passed += verdict(tid, d, False, f"pre-mutated seed T{i}")

    print("== tampered packages ==")
    def tamper(idx, name, mutate):
        d = fresh_copy(idx, tmp / name)
        traj = json.loads((d / "trajectory.json").read_text())
        mutate(traj)
        (d / "trajectory.json").write_text(json.dumps(traj))
        return d

    d = tamper(0, "tid0", lambda t: t.update(task_id="Samsung--1"))
    passed += verdict("Samsung--0", d, False, "wrong task_id")
    d = tamper(0, "unterm0", lambda t: t.update(terminated=False))
    passed += verdict("Samsung--0", d, False, "unterminated trajectory")
    d = tamper(0, "nReason0", lambda t: t.update(termination_reason="max_steps"))
    passed += verdict("Samsung--0", d, False, "termination_reason max_steps")
    d = tamper(0, "offsite0", lambda t: t["steps"][3].update(
        url="https://example.com/leak", url_after="https://example.com/leak"))
    passed += verdict("Samsung--0", d, False, "off-site URL")
    d = tamper(0, "xport0", lambda t: t["steps"][3].update(
        url="http://localhost:9999/smartphones/",
        url_after="http://localhost:9999/smartphones/"))
    passed += verdict("Samsung--0", d, False, "cross-port URL")
    d = tamper(0, "empty0", lambda t: t.update(final_answer="   "))
    passed += verdict("Samsung--0", d, False, "empty final answer")
    d = fresh_copy(0, tmp / "png0")
    (tmp / "png0" / "screenshots" / "step_000.png").write_bytes(b"not a png")
    passed += verdict("Samsung--0", tmp / "png0", False, "corrupt screenshot")

    print("== task confusion ==")
    # T12: correct claims, but the wishlist edit hit the wrong products
    d = fresh_copy(12, tmp / "conf12")
    con = sqlite3.connect(d / "after.db")
    con.execute("UPDATE wishlist_items SET product_slug='galaxy-s25' "
                "WHERE user_id=1 AND product_slug='galaxy-watch9'")
    con.commit()
    con.close()
    passed += verdict("Samsung--12", d, False, "T12 wrong wishlist edit")
    # T15: signup with the wrong name
    d = fresh_copy(15, tmp / "conf15")
    con = sqlite3.connect(d / "after.db")
    con.execute("UPDATE users SET name='Frank NovaX' WHERE email='frank.n@test.com'")
    con.commit()
    con.close()
    passed += verdict("Samsung--15", d, False, "T15 wrong profile name")
    # T10: ticket filed under the wrong topic
    d = fresh_copy(10, tmp / "conf10")
    con = sqlite3.connect(d / "after.db")
    con.execute("UPDATE support_tickets SET topic='Repair' WHERE "
                "ticket_no LIKE 'ST-1%' AND user_id=3")
    con.commit()
    con.close()
    passed += verdict("Samsung--10", d, False, "T10 wrong ticket topic")

    shutil.rmtree(tmp, ignore_errors=True)
    total = _COUNT[0]
    print(f"\n{passed}/{total} cases behaved as expected")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(run_all())
