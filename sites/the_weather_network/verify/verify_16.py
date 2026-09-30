#!/usr/bin/env python3
"""Verify The Weather Network--16 (El Niño hub -> first-frost article ->
frost-zones explainer).

r2 re-sync: deepened to the full two-article chain. Frozen ground truth:
the first-frost article is filed under weather/forecasts; Prairie
communities typically see their average first frost around the middle of
September; October brings the average first frost to southern Ontario,
southern Quebec, the Atlantic provinces and B.C.'s Interior; a hard freeze
is -2°C or colder for several hours; frost advisories have already been
issued in portions of New Brunswick, Newfoundland, Quebec and Ontario. The
linked frost-zones explainer: zones rated 0 through 9, Zone 0 the coldest
(northern Canada), Zone 9 the mildest (parts of Vancouver Island); based
on a 30-year average; meteorologist Kevin MacKay is quoted.
"""
from verify_lib import (check_answer_any, check_answer_number, check_read_only,
                        check_trajectory_identity, check_visited_path,
                        final_answer, run_verifier)

TASK_ID = "The Weather Network--16"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    from reviewed_checks import check_answer
    check_answer(judge, traj, 16)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_visited_path(judge, traj, "visited_el_nino_hub",
                       r"/en/explore/el-nino-la-nina")
    check_visited_path(judge, traj, "visited_first_frost_article",
                       r"/en/news/weather/forecasts/el-nino-could-delay")
    check_visited_path(judge, traj, "visited_frost_zones_article",
                       r"/en/news/science/explainers/understanding-canadas-frost-zones")
    # which news section the article is filed under
    check_answer_any(judge, answer, "answer_article_section",
                     ["weather", "forecasts"],
                     label="news section the article is filed under")
    # Prairie average first frost
    check_answer_any(judge, answer, "answer_prairie_first_frost",
                     ["middle of september", "mid-september", "mid september"],
                     label="Prairie average first frost")
    # October first-frost regions (at least one of the four named areas)
    hay = answer.casefold()
    judge.check("answer_october_regions",
                any(r in hay for r in ["southern ontario", "southern quebec", "atlantic",
                                      "b.c.'s interior", "british columbia's interior",
                                      "bc's interior", "b.c. interior", "interior"]),
                "answer must name at least one October first-frost region "
                "(southern Ontario / southern Quebec / Atlantic / B.C. Interior); "
                f"answer={answer[:200]!r}")
    # hard freeze definition
    check_answer_any(judge, answer, "answer_hard_freeze",
                     ["-2", "minus 2", "–2"], label="hard freeze threshold")
    check_answer_any(judge, answer, "answer_hard_freeze_duration",
                     ["several hours", "a few hours"], label="hard freeze duration")
    # regions already under frost advisories
    judge.check("answer_frost_advisory_regions",
                any(r in hay for r in ["new brunswick", "newfoundland", "quebec", "ontario"]),
                "answer must name regions that already had frost advisories "
                "(New Brunswick, Newfoundland, Quebec, Ontario)")
    # frost zones explainer facts
    check_answer_any(judge, answer, "answer_coldest_zone",
                     ["zone 0"], label="coldest frost zone")
    check_answer_any(judge, answer, "answer_mildest_zone",
                     ["zone 9"], label="mildest frost zone")
    check_answer_any(judge, answer, "answer_zone_basis",
                     ["30-year average", "30 year average", "thirty-year"],
                     label="what the frost zones are based on")
    check_answer_any(judge, answer, "answer_meteorologist",
                     ["kevin mackay", "mackay"], label="quoted meteorologist")
    check_read_only(judge, initial_db, after_db)


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
