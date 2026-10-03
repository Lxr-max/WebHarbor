#!/usr/bin/env python3
"""Verify SourceForge--19: Evaluate SourceForge as a place to promote our business software. Establish its founding year and the size of its software directory, explain what the vendor listing page offers, and examine the featured case-study vendors. Check NinjaOne and Google Cloud Platform's product pages for their ratings counts to illustrate the scale of customer feedback."""
from verify_lib import (check_answer_number, check_answer_phrase, check_read_only,
                        check_only_tables_changed, check_trajectory_identity,
                        check_visited_path, final_answer, run_verifier,
                        table_diff, check_answer_any)

import re

TASK_ID = "SourceForge--19"



def _pid(db, shortname):
    return db.execute("SELECT id FROM projects WHERE shortname = ?", (shortname,)).fetchone()[0]


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_visited_path(judge, traj, "visited_about", r"/about")
    check_visited_path(judge, traj, "visited_case_studies", r"/software/case-studies/")
    check_visited_path(judge, traj, "visited_ninjaone", r"/software/product/NinjaOne/")
    check_visited_path(judge, traj, "visited_gcp", r"/software/product/Google-Cloud-Platform/")
    check_visited_path(judge, traj, "visited_vendors", r"/software/vendors/")
    check_answer_phrase(judge, answer, "founded_1999", '1999')
    check_answer_phrase(judge, answer, "software_titles", '123,200')
    check_answer_phrase(judge, answer, "vendor_1", 'Gemini Enterprise Agent Platform')
    check_answer_phrase(judge, answer, "vendor_2", 'Google Cloud Platform')
    check_answer_phrase(judge, answer, "vendor_3", 'NinjaOne')
    check_answer_number(judge, answer, "ninjaone_ratings", '6,035', 'NinjaOne ratings count')
    check_answer_number(judge, answer, "gcp_ratings", '61,049', 'Google Cloud Platform ratings count')
    judge.check("vendors_offer", bool(re.search(r"\blist(?:ing)?\b[^.\n]{0,100}business software directory", answer, re.I)), "explain the offer to list business software in the directory")
    check_read_only(judge, initial_db, after_db)


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
