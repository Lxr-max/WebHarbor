"""No-op, shortcut, wrong-answer, state-mismatch, and pass cases."""

import json
import re
import shutil
import sqlite3
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from verify_lib import TASKS, evaluate

SEED = Path(__file__).resolve().parents[1] / "instance_seed" / "apartments_com.db"
BASE = "http://localhost:40099"

PASS_URLS = {
    0: ["/search?city=Miami&amenity=ev_charging"],
    1: [
        "/search?neighborhood=Brickell&beds=2&price_max=3500&sort=price",
        "/fl/miami/park-vista-tower-miami-fl-033/",
    ],
    2: ["/tx/austin/the-boulevard-austin-tx-000/"],
    3: [
        "/ny/new-york/mosaic-new-york-ny-000/",
        "/wa/seattle/beacon-seattle-wa-000/",
    ],
    4: ["/ca/san-francisco/vista-lofts-san-francisco-ca-024/"],
    5: ["/search?polygon=37.77,-122.42;37.79,-122.42;37.79,-122.39;37.77,-122.39"],
    6: ["/fl/miami/mosaic-apartments-miami-fl-000/tour"],
    7: ["/search?neighborhood=Streeterville&sort=rating"],
    8: ["/ny/new-york/1060-w-21st-st-new-york-ny-009/"],
    9: ["/search?city=Los+Angeles&mode=luxury&amenity=rooftop&amenity=pool&sort=price"],
    10: ["/ny/new-york/the-aspen-new-york-ny-054/"],
    11: ["/il/chicago/the-symphony-chicago-il-000/reviews"],
    12: [
        "/search?city=New+York&beds=2&price_max=4000",
        "/saved-searches",
    ],
    13: ["/wa/seattle/the-camden-lofts-seattle-wa-003/"],
    14: ["/ca/san-francisco/one-pacific-tower-san-francisco-ca-001/"],
    15: ["/student-housing"],
}

PASS_ANSWERS = {
    0: "Miami has 21 rentals with EV charging.",
    1: "Park Vista Tower, 8535 Washington Ave, Miami, FL. Cheapest matching unit rent is $3,072.",
    2: "The Boulevard has Walk Score 36 and 9 units currently available.",
    3: "Mosaic has the higher Walk Score, 78 versus Beacon's 76. Mosaic rent is $3,213–$5,751. Beacon rent is $2,077–$3,904.",
    4: "Vista Lofts, 353 Minna St, unit 1308, rent $2,534.",
    5: "The SoMa preset returns 1 rental, 4548 Mission St, displayed range $2,593–$4,401.",
    6: "Tour confirmed. Confirmation number TR-000001.",
    7: "The Wynwood at Chicago, 3637 E Grand Ave, rating 4.8, 25 reviews.",
    8: "The nearest grocery is H-E-B at 0.8 miles.",
    9: "Pacific, 6613 Wilshire Blvd, displayed rent $2,143–$4,797.",
    10: "Pacific High School is rated 10 and is 0.2 miles away.",
    11: "The review Great spot near the lake is on the page. Updated review count is 21.",
    12: "Saved NYC 2BR under 4000. The account now has 2 saved searches.",
    13: "The Camden Lofts, 1251 Westlake Ave N, unit 4015, rent $1,814, available 2026-06-26.",
    14: "Unit 0904 rent $3,711, building deposit $2,565, application fee $85, admin fee $169, total $6,530.",
    15: "New York and San Antonio are tied with 5 student-housing listings each.",
}


def traj(answer, paths):
    return {
        "start_url": BASE + "/",
        "final_answer": answer,
        "steps": [{"step": i, "url": BASE + path} for i, path in enumerate(paths)],
    }


def mutate(index, path):
    conn = sqlite3.connect(path)
    if index == 6:
        bid = conn.execute(
            "SELECT id FROM buildings WHERE slug='mosaic-apartments-miami-fl-000'"
        ).fetchone()[0]
        conn.execute(
            """
            INSERT INTO tour_requests
            (building_id, name, email, preferred_date, preferred_time, tour_type, created_at)
            VALUES (?, 'Jane Doe', 'jane.doe@example.com', '2026-10-03', '2:00 PM', 'In-Person', '2026-09-01')
            """,
            (bid,),
        )
    elif index == 11:
        bid = conn.execute(
            "SELECT id FROM buildings WHERE slug='the-symphony-chicago-il-000'"
        ).fetchone()[0]
        uid = conn.execute(
            "SELECT id FROM users WHERE email='alice.j@test.com'"
        ).fetchone()[0]
        conn.execute(
            """
            INSERT INTO reviews
            (building_id, author_name, rating, title, body, user_id, created_at)
            VALUES (?, 'Alice Johnson', 5, 'Great spot near the lake', 'Bright and quiet.', ?, '2026-09-01')
            """,
            (bid, uid),
        )
        conn.execute(
            "UPDATE buildings SET review_count=21 WHERE id=?", (bid,)
        )
    elif index == 12:
        uid = conn.execute(
            "SELECT id FROM users WHERE email='alice.j@test.com'"
        ).fetchone()[0]
        conn.execute(
            """
            INSERT INTO saved_searches (user_id, name, query_string, created_at)
            VALUES (?, 'NYC 2BR under 4000', 'city=New York&beds=2&price_max=4000', '2026-09-01')
            """,
            (uid,),
        )
    conn.commit()
    conn.close()


def contract_literals(value):
    if isinstance(value, (str, int, float)) and not isinstance(value, bool):
        yield str(value)
    elif isinstance(value, (tuple, list, set, frozenset)):
        for item in value:
            yield from contract_literals(item)
    elif callable(value):
        yield from contract_literals(value.__code__.co_consts)


def literal_words(text):
    return " " + " ".join(re.findall(r"\w+", text.casefold().replace("_", " "))) + " "


def numeric_tokens(text):
    return {
        Decimal(token.replace(",", ""))
        for token in re.findall(r"(?<!\w)\d+(?:,\d{3})*(?:\.\d+)?(?!\w)", text)
    }


class ApartmentsVerifierTests(unittest.TestCase):
    def test_task_schema_and_rules_only_rubrics(self):
        site_dir = SEED.parents[1]
        repo_root = site_dir.parents[1]
        rows = [
            json.loads(line)
            for line in (site_dir / "tasks.jsonl").read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual([row["id"] for row in rows], [spec["task_id"] for spec in TASKS.values()])
        for index, row in enumerate(rows):
            with self.subTest(task=index, case="schema-no-leak"):
                spec = TASKS[index]
                self.assertEqual(set(row), {
                    "web_name", "id", "ques", "web", "upstream_url",
                    "verifier_path", "judge_rubric",
                })
                self.assertEqual(row["web_name"], row["id"].rsplit("--", 1)[0])
                self.assertEqual(row["verifier_path"], f"sites/{site_dir.name}/verify/verify_{index}.py")
                self.assertTrue((repo_root / row["verifier_path"]).is_file())
                rubric = row["judge_rubric"]
                self.assertTrue(rubric.startswith("FACT CHECKPOINTS:"))
                self.assertEqual(rubric, spec["rubric"])
                expected = list(contract_literals([
                    spec.get("phrases", []), spec.get("numbers", []),
                    [value for _, value in spec.get("bind", [])],
                    spec.get("at_least", (0, []))[1],
                ]))
                callback_values = list(contract_literals([spec.get("pred"), spec.get("state")]))
                answer_numbers = numeric_tokens(" ".join(expected + callback_values + [PASS_ANSWERS[index]]))
                input_numbers = numeric_tokens(row["ques"])
                self.assertFalse(numeric_tokens(rubric) & (answer_numbers - input_numbers))
                for literal in expected:
                    if literal_words(literal) not in literal_words(row["ques"]):
                        self.assertNotIn(literal_words(literal), literal_words(rubric))
                for literal in callback_values:
                    if literal and literal.casefold() not in row["ques"].casefold():
                        for quote, closing in (("\"", "\""), ("'", "'"), ("`", "`"), ("\u201c", "\u201d")):
                            self.assertNotIn(f"{quote}{literal}{closing}".casefold(), rubric.casefold())

    def test_matrix(self):
        for index in range(16):
            with self.subTest(task=index, case="noop"):
                verdict = evaluate(index, traj("", ["/"]))
                self.assertFalse(verdict["pass"], verdict)
            with self.subTest(task=index, case="shortcut"):
                verdict = evaluate(index, traj(PASS_ANSWERS[index], ["/"]))
                self.assertFalse(verdict["pass"], verdict)
            with self.subTest(task=index, case="wrong"):
                verdict = evaluate(
                    index,
                    traj("No matching listing. Count is 0 at Nowhere Tower.", PASS_URLS[index]),
                )
                self.assertFalse(verdict["pass"], verdict)
            stateful = bool(TASKS[index].get("state"))
            with tempfile.TemporaryDirectory() as tmp:
                seed_copy = str(Path(tmp) / "seed.db")
                after = str(Path(tmp) / "after.db")
                shutil.copy(SEED, seed_copy)
                shutil.copy(SEED, after)
                if stateful:
                    with self.subTest(task=index, case="state-mismatch"):
                        verdict = evaluate(
                            index,
                            traj(PASS_ANSWERS[index], PASS_URLS[index]),
                            seed_copy,
                            after,
                        )
                        self.assertFalse(verdict["pass"], verdict)
                    mutate(index, after)
                with self.subTest(task=index, case="pass"):
                    verdict = evaluate(
                        index,
                        traj(PASS_ANSWERS[index], PASS_URLS[index]),
                        seed_copy,
                        after,
                    )
                    self.assertTrue(verdict["pass"], verdict)

    def test_wrong_building_same_rent(self):
        verdict = evaluate(
            1,
            traj(
                "Harbor House, 1 Other St, cheapest matching unit rent is $3,072.",
                PASS_URLS[1],
            ),
        )
        self.assertFalse(verdict["pass"], verdict)


if __name__ == "__main__":
    unittest.main()
