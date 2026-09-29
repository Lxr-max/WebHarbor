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

SEED = Path(__file__).resolve().parents[1] / "instance_seed" / "fandom.db"
BASE = "http://localhost:40101"

PASS_URLS = {
    0: ["/wiki/mcu/Tony_Stark"],
    1: ["/search?q=Thanos", "/wiki/mcu/Thanos"],
    2: ["/wiki/genshin/Zhongli"],
    3: ["/wiki/starwars/Mace_Windu"],
    4: ["/wiki/mcu/Category:Guardians_of_the_Galaxy"],
    5: ["/wiki/genshin/Category:Five-Star_Characters"],
    6: ["/wiki/starwars/Special:RecentChanges?hide_bot=1"],
    7: ["/wiki/mcu/Tony_Stark/history"],
    8: ["/wiki/genshin/Hu_Tao/history"],
    9: ["/wiki/starwars/Tatooine"],
    10: ["/register", "/user/TestEditor99"],
    11: ["/wiki/mcu/Thanos", "/wiki/mcu/Special:Watchlist"],
    12: ["/wiki/starwars/Luke_Skywalker", "/wiki/starwars/Luke_Skywalker/history"],
    13: ["/wiki/genshin/"],
    14: ["/wiki/mcu/Special:WhatLinksHere/Tony_Stark"],
    15: ["/wiki/mcu/Forum/Thread/1"],
    16: ["/wiki/mcu/Special:Polls", "/wiki/starwars/Special:Polls", "/wiki/genshin/Special:Polls"],
    17: ["/wiki/genshin/Special:ListFiles?q=Mondstadt"],
}

PASS_ANSWERS = {
    0: "Tony Stark's infobox birth date is May 29, 1970.",
    1: "Thanos is a Titan (Eternal-Deviant hybrid) and his status is Deceased.",
    2: "Zhongli's constellation is Lapidus and his release version is 1.1.",
    3: "Mace Windu's lightsaber is Purple and he uses Form VII (Vaapad).",
    4: "The category lists Peter Quill, Gamora, Rocket Raccoon, and Groot.",
    5: "Arlecchino, constellation Ignis Purgatorius.",
    6: "Hide bot edits shows 200 revision rows.",
    7: "Tony Stark's history lists 3 revisions.",
    8: "The newest Hu Tao revision added 60 bytes.",
    9: "Tatooine's infobox lists 3 moons.",
    10: "TestEditor99 shows an edit count of 0. I then signed out.",
    11: "Thanos is on the MCU watchlist.",
    12: "The Apocrypha section is present: Unverified rumors persist about Luke's role in the High Republic era. History summary is Add Apocrypha note.",
    13: "After voting, Liyue has 72 votes.",
    14: "Three sources are Pepper Potts, Steve Rogers, and Vision.",
    15: "What is your favorite MCU phase? has 5 replies.",
    16: "Active polls: Who is your favorite Avenger?; Greatest Jedi of all time?; Which region has the best music?",
    17: "Mondstadt Cathedral was uploaded by InfinityScribe.",
}


def traj(answer, paths):
    return {
        "start_url": BASE + "/",
        "final_answer": answer,
        "steps": [{"step": i, "url": BASE + path} for i, path in enumerate(paths)],
    }


def mutate(index, path):
    conn = sqlite3.connect(path)
    if index == 10:
        conn.execute(
            "INSERT INTO users (email, username, password_hash, joined) VALUES ('testeditor99@example.com', 'TestEditor99', 'x', '2026-09-01')"
        )
    elif index == 11:
        uid = conn.execute("SELECT id FROM users WHERE username='AliceJ'").fetchone()[0]
        aid = conn.execute(
            "SELECT a.id FROM articles a JOIN wikis w ON w.id=a.wiki_id WHERE w.slug='mcu' AND a.title='Thanos'"
        ).fetchone()[0]
        conn.execute("INSERT INTO watch_items (user_id, article_id, since) VALUES (?, ?, '2026-09-01')", (uid, aid))
    elif index == 12:
        uid = conn.execute("SELECT id FROM users WHERE username='BobK'").fetchone()[0]
        row = conn.execute(
            "SELECT a.id, a.content FROM articles a JOIN wikis w ON w.id=a.wiki_id WHERE w.slug='starwars' AND a.title='Luke Skywalker'"
        ).fetchone()
        content = row[1] + "\n\n== Apocrypha ==\nUnverified rumors persist about Luke's role in the High Republic era.\n"
        conn.execute("UPDATE articles SET content=? WHERE id=?", (content, row[0]))
        conn.execute(
            "INSERT INTO revisions (article_id, user_id, author_label, summary, content, minor, bot, bytes_size, bytes_delta, timestamp) VALUES (?, ?, 'BobK', 'Add Apocrypha note', ?, 0, 0, ?, 80, '2026-09-01')",
            (row[0], uid, content, len(content.encode())),
        )
    elif index == 13:
        uid = conn.execute("SELECT id FROM users WHERE username='CarolS'").fetchone()[0]
        conn.execute(
            "INSERT INTO poll_votes (poll_id, user_id, choice_idx, timestamp) VALUES (3, ?, 1, '2026-09-01')",
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


class FandomVerifierTests(unittest.TestCase):
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
                if index == 10:
                    self.assertNotIn(Decimal(0), numeric_tokens(rubric))

    def test_matrix(self):
        for index in range(18):
            with self.subTest(task=index, case="noop"):
                self.assertFalse(evaluate(index, traj("", ["/"]))["pass"])
            with self.subTest(task=index, case="shortcut"):
                self.assertFalse(evaluate(index, traj(PASS_ANSWERS[index], ["/"]))["pass"])
            with self.subTest(task=index, case="wrong"):
                verdict = evaluate(index, traj("No such page. The count is 0 for Nobody.", PASS_URLS[index]))
                self.assertFalse(verdict["pass"], verdict)
            stateful = bool(TASKS[index].get("state"))
            with tempfile.TemporaryDirectory() as tmp:
                seed_copy = str(Path(tmp) / "seed.db")
                after = str(Path(tmp) / "after.db")
                shutil.copy(SEED, seed_copy)
                shutil.copy(SEED, after)
                if stateful:
                    with self.subTest(task=index, case="state-mismatch"):
                        verdict = evaluate(index, traj(PASS_ANSWERS[index], PASS_URLS[index]), seed_copy, after)
                        self.assertFalse(verdict["pass"], verdict)
                    mutate(index, after)
                with self.subTest(task=index, case="pass"):
                    verdict = evaluate(index, traj(PASS_ANSWERS[index], PASS_URLS[index]), seed_copy, after)
                    self.assertTrue(verdict["pass"], verdict)

    def test_extra_guardian_fails(self):
        verdict = evaluate(
            4,
            traj("Peter Quill, Gamora, Rocket Raccoon, Groot, and Drax.", PASS_URLS[4]),
        )
        self.assertFalse(verdict["pass"], verdict)


if __name__ == "__main__":
    unittest.main()
