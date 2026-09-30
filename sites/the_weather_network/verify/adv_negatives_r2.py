#!/usr/bin/env python3
"""r2 adversarial negatives: wrong-path / wrong-fact answers must FAIL.

Cases (beyond the suite's built-in wrong-answer negatives):
 A1. T1 answered for Nakiska (wrong resort — task names Banff Sunshine)
 A2. T1 Banff Sunshine trajectory but wrong values (first snow Oct 5, 12° ...)
 A3. T12 'Alberta Beach is warmest Saturday' (wrong beach — Aspen is)
 A4. T13 the OLD r1 answer shape (coldest-high Oct 4/10 tie focus, no
     warmest/wettest/monthly/alert chain) — must FAIL the re-anchored gates
 A5. T7 the fix receipt's own recorded 7-day answer (Wed Sep 30, 60%) —
     wrong against the frozen rows (Thu Oct 1, 70% is the unique max)
 A6. T10 answer inconsistent with the visited course (Friday best day,
     60% PoP, high 25°)
 A7. T19 'Tuesday' only vs 'Wednesday' only — BOTH tie days must PASS the
     highest-rain-day gate (tie accepted by design)
"""
import json
import os
import pathlib
import sys
import tempfile

sys.path.insert(0, "sites/the_weather_network/verify/tests")
sys.path.insert(0, "sites/the_weather_network/verify")
os.environ["WH_CONTAINER"] = "wh-twn-rereview"
os.environ["TWN_TEST_SEED_DB"] = "/tmp/twn_r2_seed.db"

from _support import build_run, run_verifier  # noqa: E402
from fixtures_data import SPECS  # noqa: E402

CASES = [
    ("A1", 1, ("Nakiska Ski Area: the first date fresh snow is expected is September 29, with under 1 cm "
               "falling and a daytime high of 8°C. The coldest overnight low is -6°C and the warmest day "
               "is October 5 at 12°C. Saturday light snow 4°C 60%, Sunday 6°C 10%."),
     False, "wrong resort (Nakiska) must FAIL the Banff-Sunshine-anchored task"),
    ("A2", 1, ("Banff Sunshine right now: 3°C and Clear. The first fresh snow is expected on October 5 "
               "with about 12 cm and a high of 12°C. The coldest overnight low is -2°C and the warmest "
               "day is September 26 at 4°C. Saturday sunny 10°C 10%, Sunday 12°C 20%."),
     False, "right resort, wrong values must FAIL"),
    ("A3", 12, ("Alberta Beach at Lac Ste. Anne is the warmest on Saturday at 9°C. Aspen Beach is the "
                "one expecting rain that day with about 5 mm. The other two beaches stay dry. The three "
                "Sunday outlooks all differ."),
     False, "wrong warmest beach + wrong rain beach must FAIL"),
    ("A4", 13, ("Baker Lake's 14-day forecast: the coldest daytime high is 3°C on October 4 and also "
                "3°C on October 10; the warmest daytime high is 7°C on Monday, September 28. Snow is "
                "expected on September 27."),
     False, "the old r1 answer shape (no wettest/monthly/alert chain) must FAIL the re-anchored gates"),
    ("A5", 7, ("Toronto right now: 18°C and Clear. Rain starts at 11 PM Sunday and the last showers "
               "clear by 5 AM Monday — 7 hours of rain with the highest precipitation chance at 60%. "
               "The dry stretch before the rain spans 12-23°C. The day later in the week with the "
               "highest rain chance is Tuesday, September 30 at 60%."),
     False, "the fix receipt's own wrong 7-day answer (Sep 30 / 60%) must FAIL — frozen rows say "
            "Thursday, October 1 at 70%"),
    ("A6", 10, ("Acme Golf Club: the best day is Friday, October 2 with a 60% chance of precipitation "
                "and a high of 25°C. The warmest day is Monday at 25°C. 2 days show a chance above 20 "
                "percent. The weekend is rainy both days."),
     False, "values inconsistent with the visited course must FAIL"),
    ("A7a", 19, ("At Banff Community High School right now it is 3°C and Clear. Tomorrow during school "
                 "hours is mainly sunny with no precipitation (10% PoP) — drop-off at 9 AM is -1°C, "
                 "daytime high 11°C. The rest of the week does not stay dry: Tuesday, September 29 "
                 "shows the highest rain chance at 60%."),
     True, "tie day Tuesday alone must PASS (frozen rows tie Tue/Wed at 60%)"),
    ("A7b", 19, ("At Banff Community High School right now it is 3°C and Clear. Tomorrow during school "
                 "hours is mainly sunny with no precipitation (10% PoP) — drop-off at 9 AM is -1°C, "
                 "daytime high 11°C. The rest of the week does not stay dry: Wednesday, September 30 "
                 "shows the highest rain chance at 60%."),
     True, "tie day Wednesday alone must PASS (frozen rows tie Tue/Wed at 60%)"),
]


def main():
    results = []
    for tag, task_no, answer, expect_pass, why in CASES:
        with tempfile.TemporaryDirectory() as td:
            run = build_run(pathlib.Path(td), task_no, apply_sql=True, answer_override=answer)
            try:
                run_verifier(task_no, run, expect_pass=expect_pass)
                results.append((tag, task_no, "OK", why))
            except AssertionError as e:
                results.append((tag, task_no, "UNEXPECTED", f"{why} — {str(e)[:140]}"))
    print()
    for tag, task_no, status, why in results:
        print(f"{tag} (T{task_no}): {status} — {why[:110]}")
    bad = [r for r in results if r[2] != "OK"]
    print()
    print("ALL ADVERSARIAL NEGATIVES BEHAVED" if not bad else f"{len(bad)} UNEXPECTED RESULTS")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
