"""Frozen Fandom facts. Answers stay in this module."""

import sqlite3

from checks import fold, has_num, has_phrase, near


LINKS = [
    "Avengers Compound", "Bruce Banner", "Infinity Gauntlet", "Iron Man Armor",
    "James Rhodes", "Pepper Potts", "Peter Parker", "Steve Rogers", "Thanos", "Vision",
]


def _open(path):
    if not path:
        return None
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _user(conn, username):
    return conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()


def _article(conn, wiki, title):
    return conn.execute(
        """
        SELECT a.id FROM articles a JOIN wikis w ON w.id=a.wiki_id
        WHERE w.slug=? AND a.title=?
        """,
        (wiki, title),
    ).fetchone()


def state_register(initial, after, answer, traj):
    conn = _open(after)
    if conn is None:
        return False, "missing after_state.db"
    try:
        user = _user(conn, "TestEditor99")
        if user is None or user["email"] != "testeditor99@example.com":
            return False, "TestEditor99 account missing"
        edits = conn.execute(
            "SELECT COUNT(*) FROM revisions WHERE user_id=?", (user["id"],)
        ).fetchone()[0]
        if edits != 0:
            return False, f"edit count is {edits}"
        text = fold(answer)
        if not has_num(answer, 0) or ("sign" not in text and "log" not in text):
            return False, "answer does not report 0 edits and sign-out"
        return True, "0 edits"
    finally:
        conn.close()


def state_watch(initial, after, answer, traj):
    conn = _open(after)
    if conn is None:
        return False, "missing after_state.db"
    try:
        user = _user(conn, "AliceJ")
        article = _article(conn, "mcu", "Thanos")
        if user is None or article is None:
            return False, "user or article missing"
        row = conn.execute(
            "SELECT 1 FROM watch_items WHERE user_id=? AND article_id=?",
            (user["id"], article["id"]),
        ).fetchone()
        if row is None:
            return False, "Thanos is not on AliceJ's watchlist"
        if not has_phrase(answer, "thanos"):
            return False, "answer omits Thanos"
        return True, "watching"
    finally:
        conn.close()


def state_apocrypha(initial, after, answer, traj):
    conn = _open(after)
    if conn is None:
        return False, "missing after_state.db"
    try:
        article = _article(conn, "starwars", "Luke Skywalker")
        user = _user(conn, "BobK")
        row = conn.execute(
            """
            SELECT summary, content FROM revisions
            WHERE article_id=? AND user_id=? AND summary=?
            ORDER BY id DESC LIMIT 1
            """,
            (article["id"], user["id"], "Add Apocrypha note"),
        ).fetchone()
        sentence = "Unverified rumors persist about Luke's role in the High Republic era."
        if row is None or sentence not in (row["content"] or "") or "Apocrypha" not in (row["content"] or ""):
            return False, "Apocrypha revision missing"
        if not has_phrase(answer, "Apocrypha") or not has_phrase(answer, "Unverified rumors"):
            return False, "answer does not confirm the section and sentence"
        return True, "revision stored"
    finally:
        conn.close()


def state_vote(initial, after, answer, traj):
    conn = _open(after)
    if conn is None:
        return False, "missing after_state.db"
    try:
        user = _user(conn, "CarolS")
        carol_votes = conn.execute(
            "SELECT COUNT(*) FROM poll_votes WHERE poll_id=3 AND user_id=? AND choice_idx=1",
            (user["id"],),
        ).fetchone()[0]
        total = conn.execute(
            "SELECT COUNT(*) FROM poll_votes WHERE poll_id=3 AND choice_idx=1"
        ).fetchone()[0]
        if carol_votes < 1:
            return False, "CarolS has no Liyue vote"
        if not has_num(answer, total) or not has_phrase(answer, "liyue"):
            return False, f"answer does not report the stored Liyue count {total}"
        return True, str(total)
    finally:
        conn.close()


def gotg_only(answer):
    text = fold(answer)
    needed = ["peter quill", "gamora", "rocket raccoon", "groot"]
    return all(name in text for name in needed) and not any(
        extra in text for extra in ("drax", "nebula", "mantis")
    )


def three_links(answer):
    return sum(1 for title in LINKS if has_phrase(answer, title)) >= 3


TASKS = {
    0: {
        "task_id": "Fandom--0",
        "nav": [r"/wiki/mcu/Tony_Stark"],
        "phrases": ["May 29, 1970"],
        "rubric": "FACT CHECKPOINTS: Open Tony Stark on the MCU wiki and report the full birth date in his infobox. A date from another character, or a date not shown in that infobox, fails.",
    },
    1: {
        "task_id": "Fandom--1",
        "nav": [r"/search\?[^#\s]*q=Thanos", r"/wiki/mcu/Thanos"],
        "phrases": ["Titan (Eternal-Deviant hybrid)", "Deceased"],
        "rubric": "FACT CHECKPOINTS: Search for Thanos, open the MCU article, and report his infobox species and status. Another wiki's Thanos article fails.",
    },
    2: {
        "task_id": "Fandom--2",
        "nav": [r"/wiki/genshin/Zhongli"],
        "phrases": ["Lapidus"],
        "bind": [("zhongli", 1.1)],
        "rubric": "FACT CHECKPOINTS: Open Zhongli on the Genshin Impact wiki and report the constellation and release version from his infobox. Do not substitute a different character's constellation.",
    },
    3: {
        "task_id": "Fandom--3",
        "nav": [r"/wiki/starwars/Mace_Windu"],
        "phrases": ["Purple", "Vaapad"],
        "rubric": "FACT CHECKPOINTS: Open Mace Windu on Wookieepedia and report the lightsaber color and form given in the article. A different Jedi's form or color fails.",
    },
    4: {
        "task_id": "Fandom--4",
        "nav": [r"/wiki/mcu/Category:Guardians_of_the_Galaxy"],
        "pred": gotg_only,
        "rubric": "FACT CHECKPOINTS: Open the MCU Guardians of the Galaxy category and list the character articles it actually contains. Adding characters who are not in that category fails.",
    },
    5: {
        "task_id": "Fandom--5",
        "nav": [r"/wiki/genshin/Category:Five-Star_Characters"],
        "phrases": ["Arlecchino", "Ignis Purgatorius"],
        "rubric": "FACT CHECKPOINTS: In Genshin Impact Five-Star Characters, identify the Pyro Polearm character from Snezhnaya and report that character's constellation. A different element's constellation fails.",
    },
    6: {
        "task_id": "Fandom--6",
        "nav": [r"/wiki/starwars/Special:RecentChanges\?[^#\s]*hide_bot=1"],
        "bind": [("revision", 200)],
        "rubric": "FACT CHECKPOINTS: On Wookieepedia Recent Changes, enable Hide bot edits and report how many revision rows are displayed. The page caps the list; report the displayed count, not an uncapped total from elsewhere.",
    },
    7: {
        "task_id": "Fandom--7",
        "nav": [r"/wiki/mcu/Tony_Stark/history"],
        "bind": [("revision", 3)],
        "rubric": "FACT CHECKPOINTS: Open Tony Stark's history on the MCU wiki and report how many revisions are listed. Another article's history fails.",
    },
    8: {
        "task_id": "Fandom--8",
        "nav": [r"/wiki/genshin/Hu_Tao/history"],
        "phrases": ["added"],
        "numbers": [60],
        "rubric": "FACT CHECKPOINTS: Compare the two newest Hu Tao revisions on the Genshin Impact wiki. Say whether the newest revision added or removed bytes and give the displayed byte delta. The other revision's delta, or the wrong sign, fails.",
    },
    9: {
        "task_id": "Fandom--9",
        "nav": [r"/wiki/starwars/Tatooine"],
        "bind": [("moon", 3)],
        "rubric": "FACT CHECKPOINTS: Open Tatooine on Wookieepedia and report the number of moons in its infobox. A moon count from a different planet fails.",
    },
    10: {
        "task_id": "Fandom--10",
        "nav": [r"/user/TestEditor99"],
        "phrases": ["TestEditor99"],
        "state": state_register,
        "rubric": "FACT CHECKPOINTS: Register TestEditor99 with testeditor99@example.com, report the edit count displayed on the account page, and sign out. A count that differs from the account page or a claim without the new account fails.",
    },
    11: {
        "task_id": "Fandom--11",
        "nav": [r"/wiki/mcu/Thanos", r"/wiki/mcu/Special:Watchlist"],
        "state": state_watch,
        "rubric": "FACT CHECKPOINTS: Sign in as AliceJ, add Thanos on the MCU wiki to the watchlist, and confirm it appears on the MCU watchlist. A self-report with no watch row fails.",
    },
    12: {
        "task_id": "Fandom--12",
        "nav": [r"/wiki/starwars/Luke_Skywalker", r"/wiki/starwars/Luke_Skywalker/history"],
        "state": state_apocrypha,
        "rubric": "FACT CHECKPOINTS: As BobK, append an Apocrypha section containing the requested sentence to Luke Skywalker, save it with the requested summary, and confirm both the section and the history summary. A missing revision fails.",
    },
    13: {
        "task_id": "Fandom--13",
        "nav": [r"/wiki/genshin/"],
        "state": state_vote,
        "rubric": "FACT CHECKPOINTS: As CarolS, vote for Liyue in the Genshin Impact community poll and report the Liyue vote count shown after that vote. The count must match the stored votes, including the new one.",
    },
    14: {
        "task_id": "Fandom--14",
        "nav": [r"/wiki/mcu/Special:WhatLinksHere/Tony_Stark"],
        "pred": three_links,
        "rubric": "FACT CHECKPOINTS: Open What links here for Tony Stark on the MCU wiki and report three source article titles that the page lists. Titles that do not link to Tony Stark fail.",
    },
    15: {
        "task_id": "Fandom--15",
        "nav": [r"/wiki/mcu/Forum/Thread/1"],
        "phrases": ["favorite MCU phase"],
        "bind": [("repl", 5)],
        "rubric": "FACT CHECKPOINTS: On MCU Discussions, open the pinned thread What is your favorite MCU phase? and report its reply count. Another pinned thread's count fails.",
    },
    16: {
        "task_id": "Fandom--16",
        "nav": [
            r"/wiki/mcu/Special:Polls",
            r"/wiki/starwars/Special:Polls",
            r"/wiki/genshin/Special:Polls",
        ],
        "phrases": [
            "Who is your favorite Avenger?",
            "Greatest Jedi of all time?",
            "Which region has the best music?",
        ],
        "rubric": "FACT CHECKPOINTS: Open the community poll list on each supported wiki and report the question text of every active poll. A retired or missing poll fails.",
    },
    17: {
        "task_id": "Fandom--17",
        "nav": [r"/wiki/genshin/Special:ListFiles\?[^#\s]*q=Mondstadt"],
        "phrases": ["Mondstadt Cathedral", "InfinityScribe"],
        "rubric": "FACT CHECKPOINTS: On the Genshin Impact Files page, search for Mondstadt and report the uploader of the file named Mondstadt Cathedral. A different file's uploader fails.",
    },
}
