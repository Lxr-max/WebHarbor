"""Frozen Apartments.com facts. Answers stay in this module."""

import json
import sqlite3

from checks import has_num, has_phrase, near


def _open(path):
    if not path:
        return None
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _building_id(conn, slug):
    row = conn.execute("SELECT id FROM buildings WHERE slug=?", (slug,)).fetchone()
    return row["id"] if row else None


def _user_id(conn, email):
    row = conn.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
    return row["id"] if row else None


def state_tour(initial, after, answer, traj):
    conn = _open(after)
    if conn is None:
        return False, "missing after_state.db"
    try:
        bid = _building_id(conn, "mosaic-apartments-miami-fl-000")
        rows = conn.execute(
            """
            SELECT id, tour_type, preferred_date, preferred_time, name, email
            FROM tour_requests
            WHERE building_id=? AND lower(email)=?
            """,
            (bid, "jane.doe@example.com"),
        ).fetchall()
        if len(rows) != 1:
            return False, f"expected one Jane Doe tour, found {len(rows)}"
        row = rows[0]
        if row["tour_type"] != "In-Person" or row["preferred_date"] != "2026-10-03":
            return False, "tour type or date mismatch"
        if row["preferred_time"] != "2:00 PM" or row["name"] != "Jane Doe":
            return False, "tour time or name mismatch"
        code = f"TR-{row['id']:06d}"
        if code.lower() not in (answer or "").lower():
            return False, "answer does not report the stored confirmation number"
        return True, code
    finally:
        conn.close()


def state_review(initial, after, answer, traj):
    conn = _open(after)
    if conn is None:
        return False, "missing after_state.db"
    try:
        bid = _building_id(conn, "the-symphony-chicago-il-000")
        uid = _user_id(conn, "alice.j@test.com")
        review = conn.execute(
            """
            SELECT title, rating, user_id FROM reviews
            WHERE building_id=? AND title=?
            """,
            (bid, "Great spot near the lake"),
        ).fetchone()
        if review is None or review["user_id"] != uid or review["rating"] != 5:
            return False, "review row missing or not Alice's 5-star review"
        building = conn.execute(
            "SELECT review_count FROM buildings WHERE id=?", (bid,)
        ).fetchone()
        if building["review_count"] != 21:
            return False, f"review_count is {building['review_count']}"
        if not has_num(answer, 21):
            return False, "answer does not report the updated count"
        return True, "review_count 21"
    finally:
        conn.close()


def state_saved(initial, after, answer, traj):
    conn = _open(after)
    if conn is None:
        return False, "missing after_state.db"
    try:
        uid = _user_id(conn, "alice.j@test.com")
        names = [
            row["name"]
            for row in conn.execute(
                "SELECT name FROM saved_searches WHERE user_id=?", (uid,)
            )
        ]
        if names.count("NYC 2BR under 4000") != 1:
            return False, f"saved names={names!r}"
        if "2BR Brooklyn under $4000" not in names or len(names) != 2:
            return False, f"expected the prior search plus one new row, got {names!r}"
        if not has_num(answer, 2):
            return False, "answer count is not the account total"
        return True, "2 saved searches"
    finally:
        conn.close()


def one_soma(answer):
    return (
        near(answer, "rental", 1, 40)
        or near(answer, "building", 1, 40)
        or near(answer, "result", 1, 40)
    )


def student_tie(answer):
    return near(answer, "new york", 5, 80) and near(answer, "san antonio", 5, 80)


TASKS = {
    0: {
        "task_id": "Apartments.com--0",
        "nav": [r"/search\?(?=[^#\s]*city=Miami)(?=[^#\s]*amenity=ev_charging)"],
        "bind": [("miami", 21)],
        "rubric": "FACT CHECKPOINTS: Open the Miami rental search filtered to EV charging and report how many buildings the results list. The count must be the Miami EV result, not another city or amenity. Empty or unbound answers fail.",
    },
    1: {
        "task_id": "Apartments.com--1",
        "nav": [
            r"/search\?(?=[^#\s]*neighborhood=Brickell)(?=[^#\s]*beds=2)(?=[^#\s]*price_max=3500)(?=[^#\s]*sort=price)",
            r"park-vista-tower-miami-fl-033",
        ],
        "phrases": ["Park Vista Tower", "8535 Washington Ave"],
        "bind": [("park vista", 3072)],
        "rubric": "FACT CHECKPOINTS: Search Brickell 2-bedroom rentals at or below $3,500 sorted by price and open the cheapest matching building. Report that building's name, address, and cheapest matching unit rent. A matching rent attached to a different building fails.",
    },
    2: {
        "task_id": "Apartments.com--2",
        "nav": [r"the-boulevard-austin-tx-000"],
        "bind": [("boulevard", 36), ("available", 9)],
        "rubric": "FACT CHECKPOINTS: Open The Boulevard at 6081 S 1st St in Austin and report its Walk Score and how many units are listed as available. Do not substitute another Boulevard or another city's scores.",
    },
    3: {
        "task_id": "Apartments.com--3",
        "nav": [r"mosaic-new-york-ny-000", r"beacon-seattle-wa-000"],
        "phrases": ["Mosaic"],
        "bind": [("mosaic", 78), ("mosaic", 3213), ("mosaic", 5751), ("beacon", 76), ("beacon", 2077), ("beacon", 3904)],
        "pred": lambda answer: has_phrase(answer, "mosaic") and not (
            has_phrase(answer, "beacon") and near(answer, "beacon", 78, 30) and not near(answer, "mosaic", 78, 40)
        ),
        "rubric": "FACT CHECKPOINTS: Open both Mosaic at 2392 5th Ave in New York and Beacon at 4690 Pike St in Seattle. Say which has the higher Walk Score and give each building's displayed rent range. Swapping the two buildings' scores or ranges fails.",
    },
    4: {
        "task_id": "Apartments.com--4",
        "nav": [r"vista-lofts-san-francisco-ca-024"],
        "phrases": ["Vista Lofts", "353 Minna St", "1308"],
        "bind": [("vista lofts", 2534)],
        "rubric": "FACT CHECKPOINTS: Find the cheapest available San Francisco 1-bedroom in a dog-friendly building with in-unit laundry. Report that building's name, address, unit number, and rent. The same rent on a different building or unit fails.",
    },
    5: {
        "task_id": "Apartments.com--5",
        "nav": [r"polygon=", r"37\.77", r"-122\.42"],
        "phrases": ["4548 Mission"],
        "numbers": [2593, 4401],
        "pred": one_soma,
        "rubric": "FACT CHECKPOINTS: Run the SoMa San Francisco draw-search preset and report how many buildings come back and the displayed rent range of that result. Use the range shown for matching available units on the result, and keep the count tied to that search.",
    },
    6: {
        "task_id": "Apartments.com--6",
        "nav": [r"mosaic-apartments-miami-fl-000", r"/tour"],
        "state": state_tour,
        "rubric": "FACT CHECKPOINTS: Submit an in-person tour for Mosaic Apartments at 8205 Collins Ave in Miami on October 3, 2026 at 2:00 PM for Jane Doe (jane.doe@example.com). Report the confirmation number stored for that request. A number with no matching tour row fails.",
    },
    7: {
        "task_id": "Apartments.com--7",
        "nav": [r"neighborhood=Streeterville"],
        "phrases": ["The Wynwood at Chicago", "3637 E Grand Ave"],
        "numbers": [4.8, 25],
        "bind": [("wynwood", 4.8)],
        "rubric": "FACT CHECKPOINTS: In Streeterville, Chicago, identify the highest-rated building and report its name, address, average rating, and review count. A high rating on a different Streeterville building fails.",
    },
    8: {
        "task_id": "Apartments.com--8",
        "nav": [r"1060-w-21st-st-new-york-ny-009"],
        "phrases": ["H-E-B"],
        "bind": [("h-e-b", 0.8)],
        "rubric": "FACT CHECKPOINTS: Open 1060 W 21st St in New York and report the nearest grocery store and its distance. A closer non-grocery place, or the same distance for a different store, fails.",
    },
    9: {
        "task_id": "Apartments.com--9",
        "nav": [r"/search\?(?=[^#\s]*city=Los\+Angeles|city=Los%20Angeles)(?=[^#\s]*mode=luxury)(?=[^#\s]*amenity=rooftop)(?=[^#\s]*amenity=pool)(?=[^#\s]*sort=price)"],
        "phrases": ["Pacific", "6613 Wilshire Blvd"],
        "numbers": [2143, 4797],
        "rubric": "FACT CHECKPOINTS: Filter Los Angeles luxury apartments that have both a rooftop and a pool, sort by price, and report the cheapest result's name, address, and displayed rent range. Do not report a cheaper building that misses one of those filters.",
    },
    10: {
        "task_id": "Apartments.com--10",
        "nav": [r"the-aspen-new-york-ny-054"],
        "phrases": ["Pacific High School"],
        "bind": [("pacific high", 10), ("pacific high", 0.2)],
        "rubric": "FACT CHECKPOINTS: Open The Aspen at 8650 Mission St in New York and report the nearby school rated 8 or higher, including its rating and distance. A lower-rated school, or the same rating on a different school, fails.",
    },
    11: {
        "task_id": "Apartments.com--11",
        "nav": [r"the-symphony-chicago-il-000"],
        "phrases": ["Great spot near the lake"],
        "state": state_review,
        "rubric": "FACT CHECKPOINTS: Sign in as alice.j@test.com and submit the requested 5-star review on The Symphony at 3430 N Clark St in Chicago. The review must be stored on that building and the answer must report the updated displayed review count. A self-report with no new review row fails.",
    },
    12: {
        "task_id": "Apartments.com--12",
        "nav": [
            r"/search\?(?=[^#\s]*city=New\+York|city=New%20York)(?=[^#\s]*beds=2)(?=[^#\s]*price_max=4000)",
            r"/saved-searches",
        ],
        "phrases": ["NYC 2BR under 4000"],
        "state": state_saved,
        "rubric": "FACT CHECKPOINTS: Sign in as alice.j@test.com, save the New York 2-bedroom search at no more than $4,000 under the requested name, and report the total number of saved searches on the account. Counting only the new row, or reporting success without saving it, fails.",
    },
    13: {
        "task_id": "Apartments.com--13",
        "nav": [r"the-camden-lofts-seattle-wa-003"],
        "phrases": ["The Camden Lofts", "1251 Westlake Ave N", "4015", "2026-06-26"],
        "bind": [("camden", 1814)],
        "rubric": "FACT CHECKPOINTS: Find the cheapest Seattle unit available on or before June 30, 2026 in a building with parking. Report the building, address, unit, rent, and available date. The same rent on another unit or building fails.",
    },
    14: {
        "task_id": "Apartments.com--14",
        "nav": [r"one-pacific-tower-san-francisco-ca-001"],
        "phrases": ["0904"],
        "numbers": [3711, 2565, 85, 169, 6530],
        "rubric": "FACT CHECKPOINTS: On One Pacific Tower at 3375 Geary Blvd, use the first available unit in the displayed unit order. Report that unit's rent plus the building security deposit, application fee, and administrative fee, and their total. A later unit, or the unit's own deposit in place of the building deposit, fails.",
    },
    15: {
        "task_id": "Apartments.com--15",
        "nav": [r"/student-housing"],
        "pred": student_tie,
        "rubric": "FACT CHECKPOINTS: Browse the full student-housing catalog and report every city tied for the most listings, with that count. Naming only one city when the catalog is tied, or using a truncated preview, fails.",
    },
}


RUBRICS = {index: spec["rubric"] for index, spec in TASKS.items()}
