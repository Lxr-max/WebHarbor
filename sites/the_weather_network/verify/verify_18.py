#!/usr/bin/env python3
"""Verify The Weather Network--18 ('road-trip ruiner' plant article)."""
from verify_lib import (check_answer_phrase, check_read_only,
                        check_trajectory_identity, check_visited_path,
                        final_answer, run_verifier)

TASK_ID = "The Weather Network--18"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    from reviewed_checks import check_answer
    check_answer(judge, traj, 18)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_visited_path(judge, traj, "visited_plant_article",
                       r"/en/news/nature/habitats/once-you-see-it-you-cant-unsee-it-ontarios-worst-invasive-plant-is-back-phragmites")
    # exact headline: "'Once you see it, you can't unsee it': The 'road-trip ruiner' plant is back"
    check_answer_phrase(judge, answer, "answer_headline_1", "once you see it")
    check_answer_phrase(judge, answer, "answer_headline_2", "road-trip ruiner")
    # filed under Nature > Habitats
    check_answer_phrase(judge, answer, "answer_category", "nature")
    check_answer_phrase(judge, answer, "answer_subcategory", "habitats")
    # written by Cheryl Santa Maria
    check_answer_phrase(judge, answer, "answer_author", "cheryl santa maria")
    check_read_only(judge, initial_db, after_db)


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
