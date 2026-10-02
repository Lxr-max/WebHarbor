#!/usr/bin/env python3
"""Verify The Weather Network--10 (Alberta golf: best day + chain).

r2 re-sync: deepened to current conditions, warmest day, >20% PoP count and
the weekend outlook. Free-choice task: the agent may open any Alberta golf
course. The verifier resolves the course actually opened from the trajectory
and recomputes every asked fact from that course's frozen daily_forecasts
rows: the lowest-P.O.P. day(s) with that day's high, the warmest day, the
number of days above 20% PoP, and the weekend (Sat Sep 26 / Sun Sep 27)
outlook.
"""
from verify_lib import (check_answer_number, check_read_only, check_trajectory_identity,
                        check_visited_path, daily_rows, final_answer, run_verifier,
                        visited_location_slug)

TASK_ID = "The Weather Network--10"

DAY_TOKENS = {
    "2026-09-26": ["saturday", "sep 26", "september 26", "26th", "today"],
    "2026-09-27": ["sunday", "sep 27", "september 27", "27th", "tomorrow"],
    "2026-09-28": ["monday", "sep 28", "september 28", "28th"],
    "2026-09-29": ["tuesday", "sep 29", "september 29", "29th"],
    "2026-09-30": ["wednesday", "sep 30", "september 30", "30th"],
    "2026-10-01": ["thursday", "oct 1", "october 1", "1st"],
    "2026-10-02": ["friday", "oct 2", "october 2", "2nd"],
}


def _day_high_pairs(rows, target_rows):
    """(day_token, high) pairs for the given target daily rows."""
    pairs = []
    for r in target_rows:
        date = r["date_local"][:10]
        for tok in DAY_TOKENS.get(date, []):
            pairs.append((tok, int(r["day_temp"])))
    return pairs


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_visited_path(judge, traj, "visited_ab_golf_current",
                       r"/en/golf/ca/alberta/[a-z0-9-]+/current")
    check_visited_path(judge, traj, "visited_ab_golf_7days",
                       r"/en/golf/ca/alberta/[a-z0-9-]+/7-days")
    check_visited_path(judge, traj, "visited_ab_golf_weekend",
                       r"/en/golf/ca/alberta/[a-z0-9-]+/weekend")
    slug = visited_location_slug(traj, "golf")
    judge.check("resolved_golf_course", slug is not None,
                "trajectory did not open an Alberta golf course forecast page")
    if slug is None:
        return
    rows = daily_rows(initial_db, slug, "golf", start="2026-09-26", end="2026-10-02")
    judge.check("course_has_forecast", bool(rows), f"no daily_forecasts rows for {slug}")
    if not rows:
        return
    hay = answer.casefold()

    # The 7-day page renders the combined P.O.P. column (`pop`, day+night), not
    # the daytime-only `day_pop` — the agent answers from what the page shows.
    # best day: lowest PoP day(s) with that day's high
    min_pop = min(r["pop"] for r in rows)
    best = [r for r in rows if r["pop"] == min_pop]
    pairs = _day_high_pairs(rows, best)
    hit = [p for p in pairs if p[0] in hay]
    judge.check("answer_best_day_and_high", bool(hit),
                f"answer must pair a lowest-P.O.P. day with that day's high for {slug}: "
                f"lowest pop {min_pop}% on {[(r['date_local'][:10], int(r['day_temp'])) for r in best]}; "
                f"answer={answer[:220]!r}")
    # warmest day of the seven
    max_temp = max(r["day_temp"] for r in rows)
    warm = [r for r in rows if r["day_temp"] == max_temp]
    wpairs = _day_high_pairs(rows, warm)
    whit = [p for p in wpairs if p[0] in hay]
    judge.check("answer_warmest_day", bool(whit),
                f"answer must name the warmest day for {slug}: "
                f"{[(r['date_local'][:10], int(r['day_temp'])) for r in warm]}; answer={answer[:200]!r}")
    # days with PoP above 20 percent (page-visible combined PoP)
    above = sum(1 for r in rows if r["pop"] > 20)
    check_answer_number(judge, answer, "answer_days_above_20", str(above),
                        label=f"days with PoP above 20% for {slug}")
    # weekend outlook: Saturday and Sunday values from the frozen rows
    sat = next((r for r in rows if r["date_local"].startswith("2026-09-26")), None)
    sun = next((r for r in rows if r["date_local"].startswith("2026-09-27")), None)
    sat_ok = sat is not None and (
        ("saturday" in hay or "sat" in hay or "26th" in hay or "today" in hay))
    judge.check("answer_weekend_saturday", sat_ok,
                f"answer must describe the coming Saturday at {slug} "
                f"(frozen: {int(sat['day_temp']) if sat else '?'}°, PoP {sat['pop'] if sat else '?'}%)")
    sun_ok = sun is not None and (
        ("sunday" in hay or "sun " in hay or "27th" in hay or "tomorrow" in hay))
    judge.check("answer_weekend_sunday", sun_ok,
                f"answer must describe the coming Sunday at {slug} "
                f"(frozen: {int(sun['day_temp']) if sun else '?'}°, PoP {sun['pop'] if sun else '?'}%)")
    check_read_only(judge, initial_db, after_db)


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
