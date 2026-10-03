#!/usr/bin/env python3
"""r3 adversarial negatives: wrong values on the NEW T3/T7 gates must FAIL.

Cases (beyond adv_negatives_r2.py and the suite's built-in wrong-answer
negatives) — each mutates exactly one or two of the newly gated facts while
keeping the honest navigation, so a FAIL proves the new gate bites:
 B1. T3 right everything, wrong Patricia top winds (400 km/h)
 B2. T3 right everything, wrong 24-hour pressure drop (50 mb)
 B3. T3 right everything, wrong eye-footage author (Matt Howes)
 B4. T3 right everything, wrong publish date (Sep. 27, 2026)
 B5. T7 right everything, wrong overnight low during rain (10°C)
 B6. T7 right everything, wrong Monday-afternoon high (25°C)
 B7. T7 right everything, wrong expected rain on the peak day (1-3 mm)
 B8. T7 the r2 receipt's own wrong 7-day answer (Sep 30 / 60%) — regression
 B9. control: T3 honest answer must PASS (zero false positives)
 B10. control: T7 honest answer must PASS (zero false positives)
"""
import pathlib
import sys
import tempfile

sys.path.insert(0, "sites/the_weather_network/verify/tests")
sys.path.insert(0, "sites/the_weather_network/verify")
os = __import__("os")
os.environ["WH_CONTAINER"] = "wh-twn-rereview"
os.environ["TWN_TEST_SEED_DB"] = "/tmp/twn_r3_seed.db"

from _support import build_run, run_verifier  # noqa: E402

T3_HONEST = ("Hurricane Patricia is the only hurricane on record in the eastern Pacific with a "
             "lower central pressure — 872 mb (October 2015), with maximum winds of about "
             "345 km/h. Polo reached peak intensity on Tuesday, Sept. 22 with maximum sustained "
             "winds of 285 km/h. According to NOAA, Polo's minimum central pressure dropped by "
             "88 mb in 24 hours. The video embedded at the top of the 'Polo cements' article is "
             "'Hurricane Polo, one of the Eastern Pacific's most intense hurricanes', and the "
             "video at the top of the 'Inside the eye' article is 'See the view inside Hurricane "
             "Polo as it became a monster storm'. The eye-footage piece was written by Nathan "
             "Howes and published on Sep. 26, 2026.")

T7_HONEST = ("Toronto right now: 18°C and Clear. The hourly forecast shows rain starting at "
             "11 PM Sunday, with the last of the showers clearing by 5 AM Monday — 7 hours of "
             "rain in total, with the highest precipitation chance during them at 60%. "
             "Overnight during the rain it gets as cold as 14°C. The dry stretch before the "
             "rain arrives spans 12-23°C, and Monday afternoon warms back up to 20°C after the "
             "rain clears. In the 7-day outlook the day later in the week with the highest rain "
             "chance is Thursday, October 1 at 70% (5-10 mm expected) — that is when you would "
             "need to stop painting.")


def swap(text, old, new):
    assert old in text, f"swap anchor missing: {old!r}"
    return text.replace(old, new)


CASES = [
    ("B1", 3, swap(T3_HONEST, "about 345 km/h", "about 400 km/h"), False,
     "wrong Patricia top winds must FAIL the r3 gate"),
    ("B2", 3, swap(T3_HONEST, "dropped by 88 mb in 24 hours", "dropped by 50 mb in 24 hours"),
     False, "wrong 24-hour pressure drop must FAIL the r3 gate"),
    ("B3", 3, swap(T3_HONEST, "Nathan Howes", "Matt Howes"), False,
     "wrong eye-footage author must FAIL the r3 gate"),
    ("B4", 3, swap(T3_HONEST, "Sep. 26, 2026", "Sep. 27, 2026"), False,
     "wrong publish date must FAIL the r3 gate"),
    ("B5", 7, swap(T7_HONEST, "as cold as 14°C", "as cold as 10°C"), False,
     "wrong overnight low during the rain must FAIL the r3 gate"),
    ("B6", 7, swap(T7_HONEST, "warms back up to 20°C", "warms back up to 25°C"), False,
     "wrong Monday-afternoon high must FAIL the r3 gate"),
    ("B7", 7, swap(T7_HONEST, "70% (5-10 mm expected)", "70% (1-3 mm expected)"), False,
     "wrong expected rain on the peak day must FAIL the r3 gate"),
    ("B8", 7, ("Toronto right now: 18°C and Clear. Rain starts at 11 PM Sunday and the last "
               "showers clear by 5 AM Monday — 7 hours of rain with the highest precipitation "
               "chance at 60%. Overnight during the rain it gets as cold as 14°C. The dry "
               "stretch before the rain spans 12-23°C, and Monday afternoon warms back up to "
               "20°C. The day later in the week with the highest rain chance is Tuesday, "
               "September 30 at 60% (1-3 mm expected)."),
     False, "the r2 receipt's own wrong 7-day answer (Sep 30 / 60%) must still FAIL"),
    ("B9", 3, T3_HONEST, True, "control: honest T3 answer must PASS (no false positive)"),
    ("B10", 7, T7_HONEST, True, "control: honest T7 answer must PASS (no false positive)"),
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
    print("ALL R3 ADVERSARIAL NEGATIVES BEHAVED" if not bad else f"{len(bad)} UNEXPECTED RESULTS")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
