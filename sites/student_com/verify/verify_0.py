#!/usr/bin/env python3
"""Verify Student.com--0 against the reviewed task and saved browser state."""
from verify_lib import (check_answer_absent, check_answer_any,
                        check_answer_count_at_least, check_answer_number,
                        check_answer_phrase, check_bookmark_delta, check_enquiry_created,
                        check_only_tables_changed, check_read_only,
                        check_trajectory_identity, check_user_created,
                        check_views_added, check_views_only, check_visited_path,
                        final_answer, run_verifier)

TASK_ID = "Student.com--0"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_visited_path(judge, traj, "visited_gt_srp_filtered", r"/us/ga/atlanta/u/georgia-institute-of-technology\?.*max_price=1200.*type=Student")
    check_visited_path(judge, traj, "visited_rive_property", r"/us/ga/atlanta/p/the-rive-atlanta-vbqacu")
    check_answer_phrase(judge, answer, "answer_name", 'The Rive Atlanta')
    check_answer_any(judge, answer, "answer_distance", ['0.7', '0.69'])
    check_answer_count_at_least(judge, answer, "answer_amenities", ['Games Room', 'Gas', 'Co-working Spaces', 'Dishwasher', 'Microwave', 'Oven', 'Shared Refrigerator', 'Furnishing Option', 'BBQ Area', 'Cinema Room', 'Gym', 'Rooftop Terrace', 'Swimming Pool', 'Wifi', 'Pet Friendly', 'Controlled Access Gate', 'Maintenance Team', 'Library / Study Area', 'Post / Parcel Collection', 'Entertainment Area / Lounge', 'Smart Home Technology', 'Private Balcony / Patio', 'Walk-in Closet', 'Washer / Dryer'], 2)

    check_only_tables_changed(judge, initial_db, after_db,
                               {"bookmarks", "property_views"})
    check_bookmark_delta(judge, initial_db, after_db, "alice.j@test.com", "the-rive-atlanta-vbqacu", None)
    check_views_added(judge, initial_db, after_db, ["the-rive-atlanta-vbqacu"])


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
