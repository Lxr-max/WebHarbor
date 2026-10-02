#!/usr/bin/env python3
"""Verify Speedo--12: My goggles and swimsuit get regular use in a chlorinated pool. Put together a care routine from Speedo's goggles-care article and swimsuit-care FAQ, covering how to clean and dry both and what to avoid. Ask customer support to clarify whether that routine is suitable for daily chlorinated-pool use, under Product Enquiry / Goggles. Report the advice and the case reference."""
from verify_lib import (Judge, check_answer_phrase,
                        check_only_tables_changed, check_trajectory_identity,
                        check_visited_path, final_answer, run_verifier,
                        table_diff)

TASK_ID = "Speedo--12"

CASE = "CAS100001"
BLOG_SLUG = "4-easy-ways-to-care-for-your-swimming-goggles"


def run_checks(judge, traj, initial_db, after_db):
    from state_review import check_existing_state
    check_existing_state(judge, initial_db, after_db, TASK_ID)
    answer = final_answer(traj)
    import re
    for name, pattern in {
        "goggles_lukewarm":r"lukewarm", "swimsuit_cold":r"cold water",
        "air_dry":r"air[ -]?dry|dry naturally", "protective_storage":r"protective (?:pouch|case)",
        "no_soap":r"(?:no|without|avoid|not use)[^.;]{0,20}(?:soap|detergent)",
        "no_rubbing":r"(?:not|never|avoid)[^.;]{0,16}(?:rub|scratch|touch)",
        "no_towel_wrap":r"(?:not|never|avoid)[^.;]{0,20}wrap[^.;]{0,20}towel",
    }.items(): judge.check(name, bool(re.search(pattern, answer, re.I)))
    judge.check("no_soap_endorsement", not re.search(r"(?:wash|clean)[^.;]{0,25}with (?:soap|detergent)", answer, re.I))
    check_trajectory_identity(judge, traj, TASK_ID)
    check_visited_path(judge, traj, "visited_blog_index", r"/blogs/news/?")
    check_visited_path(judge, traj, "visited_goggle_care_article",
                       rf"/blogs/news/{BLOG_SLUG}")
    check_visited_path(judge, traj, "visited_faqs", r"/pages/faqs")
    check_visited_path(judge, traj, "visited_contact", r"/pages/contact")
    check_answer_phrase(judge, answer, "mentions_rinse", "rinse")
    check_answer_phrase(judge, answer, "mentions_case", CASE)

    check_only_tables_changed(judge, initial_db, after_db,
                              allowed={"contact_messages"})
    added, removed, _ = table_diff(initial_db, after_db, "contact_messages")
    judge.check("one_case_added", len(added) == 1 and len(removed) == 0,
                f"added={list(added.values())!r}")
    if added:
        row = list(added.values())[0]
        judge.check("care_question", all(re.search(pattern, row["message"], re.I) for pattern in [r"chlorin", r"goggles", r"rinse|rinsing|care|routine"]))
        judge.check("open_case", row["status"] == "Open")
        judge.check("case_ref", row["case_ref"] == CASE, f"case_ref={row['case_ref']!r}")
        judge.check("case_category", row["category"] == "Product Enquiry",
                    f"category={row['category']!r}")
        judge.check("case_subcategory", row["subcategory"] == "Goggles",
                    f"subcategory={row['subcategory']!r}")


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
