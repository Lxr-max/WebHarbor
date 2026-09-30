"""Shared fixtures for the tumblr verifier tests.

Snapshots are copies of the real deterministic seed (instance_seed/tumblr.db,
rebuilt in-container with PYTHONHASHSEED=0 and TZ=UTC, exactly like the
production Dockerfile) with the per-task stateful mutations applied through
sqlite; trajectories are written in the agent_demo/agent.py shape from the
reviewer's honest live walks. No LLM.

The seed DB resolves from the review container (wh-tumblr-review-1) or the
site's instance_seed; the TUMBLR_TEST_SEED_DB env var overrides. Run:

    python3 -m pytest sites/tumblr/verify/tests -q
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import zlib
from pathlib import Path

VERIFY_DIR = Path(__file__).resolve().parents[1]
SITE_DIR = VERIFY_DIR.parent
CONTAINER = os.environ.get("WH_CONTAINER", "wh-tumblr-review-1")
CACHE = Path(os.environ.get("TUMBLR_TEST_SEED_DB")
             or (SITE_DIR / "instance_seed" / "tumblr.db"))
TASKS_FILE = SITE_DIR / "tasks.jsonl"
PASSWORD = "TestPass123!"
BASE = "http://localhost:40099"
RUN_TS = 1790596800            # frozen 'now' for stateful mutations


def acquire_seed() -> Path:
    if CACHE.is_file():
        return CACHE
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(["docker", "cp",
                        f"{CONTAINER}:/opt/WebSyn/tumblr/instance_seed/tumblr.db",
                        str(CACHE)], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"cannot acquire the seed DB: {r.stderr[:200]}")
    return CACHE


def task_ques(task_id: str) -> str:
    for line in TASKS_FILE.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        if row["id"] == task_id:
            return row["ques"]
    raise KeyError(task_id)


# ------------------------------------------------------------------ tiny valid PNG
def tiny_png(width: int = 4, height: int = 4) -> bytes:
    raw = b"".join(b"\x00" + b"\x40\x90\xd0" * width for _ in range(height))

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (len(data).to_bytes(4, "big") + tag + data
                + zlib.crc32(tag + data).to_bytes(4, "big"))

    ihdr = width.to_bytes(4, "big") + height.to_bytes(4, "big") + \
        b"\x08\x02\x00\x00\x00"
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


PNG = tiny_png()


# ------------------------------------------------------------------ run-dir builder
class RunBuilder:
    """Writes an agent_demo-shaped run directory: trajectory.json + screenshots/."""

    def __init__(self, root: Path, task_id: str, start_path: str = "/"):
        self.root = root
        self.task_id = task_id
        self.shots_dir = root / "screenshots"
        self.shots_dir.mkdir(parents=True, exist_ok=True)
        self.steps: list[dict] = []
        self.start_url = BASE + start_path

    def step(self, action, target, url, text=None, detail=""):
        params = {"text": text} if text is not None else {}
        entry = {"n": len(self.steps) + 1, "action": action, "target": target,
                 "url": url, "params": params, "detail": detail}
        self.steps.append(entry)
        (self.shots_dir / f"step_{len(self.steps):03d}.png").write_bytes(PNG)
        return entry

    def finish(self, final_url, final_answer, terminated="agent_done"):
        traj = {"task_id": self.task_id, "start_url": self.start_url,
                "steps": self.steps, "final_url": final_url,
                "final_answer": final_answer, "terminated": terminated}
        (self.root / "trajectory.json").write_text(
            json.dumps(traj, ensure_ascii=False, indent=1), encoding="utf-8")
        return self.root


def copy_db(src: Path, dst: Path) -> Path:
    shutil.copyfile(src, dst)
    return dst


def exec_sql(db: Path, statements):
    con = sqlite3.connect(str(db))
    try:
        for sql, params in statements:
            con.execute(sql, params)
        con.commit()
    finally:
        con.close()


def blog_id(seed: Path, name: str) -> int:
    con = sqlite3.connect(str(seed))
    try:
        return con.execute("SELECT id FROM blogs WHERE name = ?", (name,)).fetchone()[0]
    finally:
        con.close()


def user_id(seed: Path, username: str) -> int:
    con = sqlite3.connect(str(seed))
    try:
        return con.execute("SELECT id FROM users WHERE username = ?",
                           (username,)).fetchone()[0]
    finally:
        con.close()


# ------------------------------------------------------------------ state mutators
def apply_state(task_no: int, seed: Path, out: Path) -> Path:
    """Apply the exact DB delta an honest run of the task produces."""
    copy_db(seed, out)
    if task_no == 10:      # unfollow + refollow cabinporn: row re-dated
        alice = user_id(seed, "alice-j")
        cabin = blog_id(seed, "cabinporn")
        exec_sql(out, [
            ("DELETE FROM follows WHERE user_id = ? AND blog_id = ?", (alice, cabin)),
            ("INSERT INTO follows (user_id, blog_id, created_at) VALUES (?, ?, ?)",
             (alice, cabin, RUN_TS)),
        ])
    elif task_no == 11:    # bob likes the first trending post
        bob = user_id(seed, "bob-c")
        exec_sql(out, [
            ("INSERT INTO likes (user_id, post_id, created_at) VALUES (?, ?, ?)",
             (bob, "817505727903137792", RUN_TS)),
        ])
    elif task_no == 12:    # carol reblogs waneella's Shimmer with 'someday.'
        carol = blog_id(seed, "carol-d")
        exec_sql(out, [
            ("INSERT INTO posts (id, blog_id, type, original_type, is_blocks_post_format,"
             " content, layout, trail, tags, timestamp, date_str, post_url, slug, summary,"
             " note_count, like_count, reblog_count, reply_count, state, reblog_of_id,"
             " user_created, created_at)"
             " VALUES ('1790596800000', ?, 'text', 'regular', 1, ?, '[]',"
             " (SELECT trail FROM posts WHERE id='827616468115079168'), '[]',"
             " ?, '2026-09-28 12:00:00 GMT', 'https://carol-d.tumblr.com/', '',"
             " 'someday.', 0, 0, 0, 0, 'published', '827616468115079168', 1, ?)",
             (carol, json.dumps([{"type": "text", "text": "someday."}]),
              RUN_TS, RUN_TS)),
            ("INSERT INTO reblogs (user_id, source_post_id, new_post_id, comment,"
             " created_at) VALUES (?, '827616468115079168', '1790596800000',"
             " 'someday.', ?)", (user_id(seed, "carol-d"), RUN_TS)),
            ("UPDATE posts SET reblog_count = reblog_count + 1 "
             "WHERE id = '827616468115079168'", ()),
            ("UPDATE blogs SET posts_count = posts_count + 1 WHERE name = 'carol-d'", ()),
        ])
    elif task_no == 13:    # david follows scipunk (the last suggestion)
        exec_sql(out, [
            ("INSERT INTO follows (user_id, blog_id, created_at) VALUES (?, ?, ?)",
             (user_id(seed, "david-k"), blog_id(seed, "scipunk"), RUN_TS)),
        ])
    elif task_no == 14:    # alice replies in the staff thread
        exec_sql(out, [
            ("INSERT INTO messages (conversation_id, from_user, sender_name, body,"
             " created_at, read) VALUES (1, 1, 'alice-j',"
             " 'One more question: what is next for Tumblr?', ?, 0)", (RUN_TS,)),
            ("UPDATE conversations SET updated_at = ? WHERE id = 1", (RUN_TS,)),
        ])
    elif task_no == 15:    # bob asks alice; alice opens the (existing) thread
        alice = user_id(seed, "alice-j")
        conv = None
        con = sqlite3.connect(str(seed))
        try:
            conv = con.execute(
                "SELECT id FROM conversations WHERE user_id = ? AND blog_name = 'bob-c'",
                (alice,)).fetchone()[0]
        finally:
            con.close()
        exec_sql(out, [
            ("INSERT INTO messages (conversation_id, from_user, sender_name, body,"
             " created_at, read) VALUES (?, 0, 'bob-c',"
             " 'Which museum do you visit most often?', ?, 1)",
             (conv, RUN_TS)),
            ("UPDATE messages SET read = 1 WHERE conversation_id = ?"
             " AND from_user = 0 AND read = 0", (conv,)),
        ])
    elif task_no == 16:    # alice opens activity: notifications read
        exec_sql(out, [
            ("UPDATE notifications SET is_new = 0 WHERE user_id = ?",
             (user_id(seed, "alice-j"),)),
        ])
    elif task_no == 17:    # carol publishes the cabin-wishlist text post
        content = json.dumps([
            {"type": "text", "text": "Cabin Wishlist, Part Two", "subtype": "heading"},
            {"type": "text",
             "text": "A cast-iron wood stove with a glass door is at the top of my "
                     "cabin wishlist."},
        ])
        exec_sql(out, [
            ("INSERT INTO posts (id, blog_id, type, original_type, is_blocks_post_format,"
             " content, layout, trail, tags, timestamp, date_str, post_url, slug, summary,"
             " note_count, like_count, reblog_count, reply_count, state, user_created,"
             " created_at) VALUES ('1790596800001', ?, 'text', 'regular', 1, ?, '[]',"
             " '[]', ?, ?, '2026-09-28 12:00:00 GMT', 'https://carol-d.tumblr.com/',"
             " '', 'Cabin Wishlist, Part Two', 0, 0, 0, 0, 'published', 1, ?)",
             (blog_id(seed, "carol-d"), content,
              json.dumps(["cottagecore", "wishlist"]), RUN_TS, RUN_TS)),
            ("UPDATE blogs SET posts_count = posts_count + 1 WHERE name = 'carol-d'", ()),
        ])
    elif task_no == 18:    # alice publishes the Twyla Tharp quote post
        content = json.dumps([
            {"type": "quote",
             "text": "\u201cArt is the only way to run away without leaving home.\u201d",
             "source": "Twyla Tharp"},
        ])
        exec_sql(out, [
            ("INSERT INTO posts (id, blog_id, type, original_type, is_blocks_post_format,"
             " content, layout, trail, tags, timestamp, date_str, post_url, slug, summary,"
             " note_count, like_count, reblog_count, reply_count, state, user_created,"
             " created_at) VALUES ('1790596800002', ?, 'quote', 'quote', 1, ?, '[]',"
             " '[]', ?, ?, '2026-09-28 12:00:00 GMT', 'https://alice-j.tumblr.com/',"
             " '', 'New post', 0, 0, 0, 0, 'published', 1, ?)",
             (blog_id(seed, "alice-j"), content, json.dumps(["quotes"]),
              RUN_TS, RUN_TS)),
            ("UPDATE blogs SET posts_count = posts_count + 1 WHERE name = 'alice-j'", ()),
        ])
    elif task_no == 19:    # bob renames his blog
        exec_sql(out, [
            ("UPDATE blogs SET title = 'bob''s art lab' WHERE name = 'bob-c'", ()),
        ])
    elif task_no == 20:    # register harbor-tester + follow nasa
        con = sqlite3.connect(str(out))
        try:
            pw_hash = hashlib.sha256(
                f"webharbor-tumblr:{PASSWORD}".encode()).hexdigest()
            con.execute(
                "INSERT INTO blogs (name, title, description, url, uuid, updated,"
                " \"primary\", posts_count, avatar, can_message, ask, ask_anon,"
                " ask_page_title, background_color, owner_user_id)"
                " VALUES ('harbor-tester', 'harbor-tester', '', '', '', 0, 0, 0,"
                " '', 1, 1, 1, 'Ask me anything', '#001935', NULL)")
            blog_row = con.execute(
                "SELECT id FROM blogs WHERE name = 'harbor-tester'").fetchone()[0]
            con.execute(
                "INSERT INTO users (email, password_hash, username, display_name,"
                " blog_id) VALUES ('harbor.tester@example.com', ?, 'harbor-tester',"
                " 'harbor-tester', ?)", (pw_hash, blog_row))
            uid = con.execute(
                "SELECT id FROM users WHERE username = 'harbor-tester'").fetchone()[0]
            con.execute("UPDATE blogs SET owner_user_id = ? WHERE id = ?", (uid, blog_row))
            con.execute(
                "INSERT INTO follows (user_id, blog_id, created_at)"
                " VALUES (?, ?, ?)",
                (uid, blog_id(seed, "nasa"), RUN_TS))
            con.commit()
        finally:
            con.close()
    return out


# ------------------------------------------------------------------ honest trajectories
def honest_steps(task_no: int, rb: RunBuilder) -> str:
    """Play the honest trajectory recorded in the reviewer's live walk; return
    the final answer composed from the frozen ground truth."""
    home, login = BASE + "/", BASE + "/login"
    if task_no == 0:
        rb.step("navigate", "homepage", home)
        rb.step("click", "popular tags #photography", BASE + "/tagged/photography")
        rb.step("read", "hub stats + editorial", BASE + "/tagged/photography")
        rb.step("click", "first related tag", BASE + "/tagged/photographer")
        rb.step("read", "related tag page", BASE + "/tagged/photographer")
        rb.step("navigate", "browser back", BASE + "/tagged/photography")
        rb.step("click", "open newest post",
                BASE + "/blog/arainthepara/829013305812205568")
        rb.step("read", "post blog/notes/first tag",
                BASE + "/blog/arainthepara/829013305812205568")
        rb.step("click", "open the posting blog", BASE + "/blog/arainthepara")
        return ("The most-followed Popular tag is #photography with 43M followers "
                "and 2.4K new posts today; its editorial reads 'For those who "
                "prefer to show rather than tell, photography takes precedence "
                "over words'. The first related tag is #photographer with 61 "
                "new posts. The newest post in the #photography feed is by "
                "arainthepara with 0 notes and its first tag is #photography. "
                "The arainthepara blog has 1 post.")
    if task_no == 1:
        rb.step("navigate", "homepage", home)
        rb.step("click", "Explore", BASE + "/explore")
        rb.step("read", "first trending post", BASE + "/explore")
        rb.step("click", "open first post",
                BASE + "/blog/meolog/817505727903137792")
        rb.step("read", "likes/reblogs", BASE + "/blog/meolog/817505727903137792")
        rb.step("navigate", "back to explore", BASE + "/explore")
        rb.step("click", "Older page 2", BASE + "/explore?page=2")
        rb.step("read", "page-2 first post", BASE + "/explore?page=2")
        rb.step("click", "open the page-2 blog", BASE + "/blog/sparth")
        rb.step("read", "sparth title/posts/updated", BASE + "/blog/sparth")
        return ("The first trending post on Explore is by meolog with 3.4K notes; "
                "opened it shows 2,217 likes and 1,172 reblogs. On page 2 the first "
                "post is by sparth with 2.9K notes, opens 'spaceships in red and "
                "white paper, remarkable tablet, and iPad line sketches', and its "
                "first two tags are #concept art and #art. The sparth blog is "
                "titled SPARTH, shows 713 posts, and was updated 7 days ago.")
    if task_no == 2:
        rb.step("navigate", "homepage", home)
        rb.step("type", "search box", BASE + "/", text="pixel art")
        rb.step("click", "search submit", BASE + "/search/pixel%20art")
        rb.step("read", "top results + blog matches", BASE + "/search/pixel%20art")
        rb.step("click", "open the first matching blog", BASE + "/blog/8pxl")
        rb.step("read", "8pxl title/posts/description", BASE + "/blog/8pxl")
        rb.step("navigate", "back to search", BASE + "/search/pixel%20art")
        rb.step("click", "Recent tab", BASE + "/search/pixel%20art?tab=recent")
        rb.step("read", "newest recent post", BASE + "/search/pixel%20art?tab=recent")
        rb.step("click", "open newest post", BASE + "/blog/wqonart/829013306919501824")
        rb.step("read", "tags + likes", BASE + "/blog/wqonart/829013306919501824")
        return ("The Top tab shows 13 results for 'pixel art'; the first two blogs "
                "in the Blogs matching sidebar are 8pxl (PIXEL ART BY @SOFTWARING) "
                "and perplexi (ixel pixel art blog). The 8pxl blog page is titled "
                "PIXEL ART BY @SOFTWARING, shows 2,155 posts, and its description "
                "includes 'JUBILEE / PIXEL ARTIST / MTG ARTIST'. On the Recent tab "
                "the newest post is by wqonart with 0 notes; opened, its first two "
                "tags are #Septembit and #Septembit2026 and it has 0 likes.")
    if task_no == 3:
        rb.step("navigate", "homepage", home)
        rb.step("type", "search box", BASE + "/", text="NASA")
        rb.step("click", "search submit", BASE + "/search/NASA")
        rb.step("click", "open NASA post", BASE + "/blog/nasa/828471464226406400")
        rb.step("click", "open NASA blog", BASE + "/blog/nasa")
        rb.step("read", "title/posts/updated", BASE + "/blog/nasa")
        rb.step("click", "Archive", BASE + "/blog/nasa/archive")
        rb.step("read", "months", BASE + "/blog/nasa/archive")
        rb.step("click", "open newest-month post",
                BASE + "/blog/nasa/828471464226406400")
        rb.step("read", "notes + summary", BASE + "/blog/nasa/828471464226406400")
        rb.step("navigate", "back to the blog page", BASE + "/blog/nasa")
        rb.step("click", "open the second feed post",
                BASE + "/blog/nasa/828110959105245184")
        rb.step("read", "second post notes + first tag",
                BASE + "/blog/nasa/828110959105245184")
        return ("NASA's blog is titled NASA with 1,759 posts, updated 5 days ago. "
                "In its archive April 2026 has the most posts with 13; the newest "
                "month, September 2026, contains 3 posts. From the newest month I "
                "opened the fall-equinox post: 5,592 notes, summary '\"Autumn is a "
                "second spring when every leaf is a flower.\" Sept. 22 is the fall "
                "equinox\u2026'. Back on the blog page, the second post in the feed "
                "(the Observe the Moon Night post) shows 1,157 notes and its first "
                "tag is #nasa.")
    if task_no == 4:
        rb.step("navigate", "homepage", home)
        rb.step("type", "search box", BASE + "/",
                text="reblogs in a chain")
        rb.step("click", "search submit", BASE + "/search/reblogs%20in%20a%20chain")
        rb.step("click", "open the staff post",
                BASE + "/blog/staff/811288138350821376")
        rb.step("read", "counts + opening + notes", BASE + "/blog/staff/811288138350821376")
        rb.step("click", "open staff blog", BASE + "/blog/staff")
        rb.step("read", "blog title/posts/updated", BASE + "/blog/staff")
        rb.step("click", "open the blog's newest post",
                BASE + "/blog/staff/828009069026721792")
        rb.step("read", "newest post first tag",
                BASE + "/blog/staff/828009069026721792")
        return ("The staff post 'Reblogs in a chain now get their own notes' shows "
                "319,748 notes, 101,183 likes and 168,847 reblogs; its opening "
                "line is 'Reblogs in a chain now get their own notes'. The two "
                "most recent likers are suipearlgloss and orlissegrapeangel; "
                "the first reblog shown is sooopap. The Tumblr Staff blog has "
                "2,989 posts, updated 10 days ago; its newest post 'Premium "
                "just got better' carries the first tag tumblr premium.")
    if task_no == 5:
        rb.step("navigate", "homepage", home)
        rb.step("type", "search box", BASE + "/", text="paokai gorgeous")
        rb.step("click", "search submit", BASE + "/search/paokai%20gorgeous")
        rb.step("click", "open the answered ask",
                BASE + "/blog/paokai/750605550915567616")
        rb.step("read", "ask/answer/notes/tags", BASE + "/blog/paokai/750605550915567616")
        rb.step("click", "open paokai blog", BASE + "/blog/paokai")
        rb.step("read", "title/post count", BASE + "/blog/paokai")
        rb.step("click", "Archive", BASE + "/blog/paokai/archive")
        rb.step("read", "newest month", BASE + "/blog/paokai/archive")
        return ("The ask was from obi-bae-kenobi: 'hi there i just wanted to say "
                "your art is gorgeous…'; the answer starts 'Hello! Thank you!!'. "
                "The post has 206 notes and the tags #refs #birds #wings. The "
                "Paokai blog has 148 posts; its archive's newest month is "
                "September 2026 with 4 posts.")
    if task_no == 6:
        rb.step("navigate", "homepage", home)
        rb.step("type", "search box", BASE + "/",
                text="flight test like a NASA engineer")
        rb.step("click", "search submit", BASE + "/search/flight%20test%20like%20a%20NASA%20engineer")
        rb.step("click", "open the video post",
                BASE + "/blog/nasa/793768130342273024")
        rb.step("read", "provider/tags/notes", BASE + "/blog/nasa/793768130342273024")
        rb.step("click", "open NASA blog", BASE + "/blog/nasa")
        rb.step("read", "title/posts/updated", BASE + "/blog/nasa")
        rb.step("click", "Archive", BASE + "/blog/nasa/archive")
        rb.step("read", "newest month", BASE + "/blog/nasa/archive")
        return ("NASA's video post 'Flight Test Like a NASA Engineer!' shows the "
                "provider Video · tumblr under the player, tags #nasa #space "
                "#science #technology (also #stem #engineering #spaceflight "
                "#student challenge), and 582 notes with 459 likes and 117 "
                "reblogs. The NASA blog has 1,759 posts, updated 5 days ago; "
                "its archive's newest month is September 2026 with 3 posts.")
    if task_no == 7:
        rb.step("navigate", "homepage", home)
        rb.step("type", "search box", BASE + "/",
                text="operating CCTV cameras")
        rb.step("click", "search submit", BASE + "/search/operating%20CCTV%20cameras")
        rb.step("click", "open the top-result CCTV post",
                BASE + "/blog/nullenvk/828957539611869184")
        rb.step("read", "trail/summary/counts/tags/opening",
                BASE + "/blog/nullenvk/828957539611869184")
        rb.step("click", "open the original trail blog",
                BASE + "/blog/teaboot")
        rb.step("read", "original blog title/posts/updated", BASE + "/blog/teaboot")
        return ("Searching 'operating CCTV cameras' ranks the CCTV post first. "
                "Its reblog trail is teaboot → teaboot → teaboot; its summary "
                "is 'Maybe I should write that post about how I got an "
                "extra sensory input from a high pitch noise…' and it has "
                "76,622 notes, 44,121 likes and 32,259 reblogs, with tags "
                "#what #just cyborg things #cyberpunk #idk. The trail opens "
                "'My first time operating CCTV cameras I was handed control "
                "over what was essentially 50 independently moving eyes…'. "
                "The original trail blog teaboot is 'I Like Yellow Now' with "
                "42,149 posts, updated 14 hours ago.")
    if task_no == 8:
        rb.step("navigate", "homepage", home)
        rb.step("click", "Log in", login)
        rb.step("type", "email field", login, text="alice.j@test.com")
        rb.step("type", "password field", login, text=PASSWORD)
        rb.step("click", "Log in button", BASE + "/dashboard")
        rb.step("read", "dashboard posts/blogs", BASE + "/dashboard")
        rb.step("click", "open newest post",
                BASE + "/blog/meolog/828475230982930432")
        rb.step("read", "likes/reblogs/notes", BASE + "/blog/meolog/828475230982930432")
        rb.step("navigate", "back to the dashboard", BASE + "/dashboard")
        rb.step("click", "open the second post",
                BASE + "/blog/nasa/828471464226406400")
        rb.step("read", "second post blog/notes/first tag",
                BASE + "/blog/nasa/828471464226406400")
        return ("Alice's dashboard first page shows 8 posts from meolog, nasa, "
                "staff and waneella. The newest post is 'Kodak Ektar 100' with "
                "556 notes; opened it shows 395 likes, 155 reblogs and 556 total "
                "notes. The second post on the page is by nasa ('Autumn is a "
                "second spring when every leaf is a flower.'), shows 5,592 notes "
                "(5.6K on the card), and its first tag is #nasa.")
    if task_no == 9:
        rb.step("navigate", "homepage", home)
        rb.step("click", "Log in", login)
        rb.step("type", "email field", login, text="alice.j@test.com")
        rb.step("type", "password field", login, text=PASSWORD)
        rb.step("click", "Log in button", BASE + "/dashboard")
        rb.step("click", "Likes tab", BASE + "/likes")
        rb.step("read", "total + most recent", BASE + "/likes")
        rb.step("click", "open the post", BASE + "/blog/staff/822057428507049984")
        rb.step("read", "tag/likes/reblogs/notes", BASE + "/blog/staff/822057428507049984")
        return ("Alice has liked 11 posts in total. The most recent is a staff "
                "post: 'In case you're looking for a blog that's gone missing on "
                "Tumblr and didn't see this recent update.' with 12K notes. "
                "Opened, its first tag is #tumblr, with 9,446 likes, 2,092 "
                "reblogs and 12,381 total notes.")
    if task_no == 10:
        rb.step("navigate", "homepage", home)
        rb.step("click", "Log in", login)
        rb.step("type", "email field", login, text="alice.j@test.com")
        rb.step("type", "password field", login, text=PASSWORD)
        rb.step("click", "Log in button", BASE + "/dashboard")
        rb.step("click", "Following tab", BASE + "/following")
        rb.step("read", "six blogs in order", BASE + "/following")
        rb.step("click", "unfollow cabinporn", BASE + "/following",
                detail="follow toggle")
        rb.step("read", "five blogs after unfollow", BASE + "/following")
        rb.step("type", "search box", BASE + "/following", text="cabinporn")
        rb.step("click", "search submit", BASE + "/search/cabinporn")
        rb.step("click", "open cabinporn blog", BASE + "/blog/cabinporn")
        rb.step("click", "follow cabinporn again", BASE + "/blog/cabinporn",
                detail="follow toggle")
        rb.step("click", "Home", BASE + "/dashboard")
        rb.step("click", "Likes tab", BASE + "/likes")
        rb.step("click", "Following tab", BASE + "/following")
        rb.step("read", "restored list", BASE + "/following")
        return ("Alice follows 6 blogs: Cabin Porn® (cabinporn, 2,707 posts), "
                "writing prompts, NASA, Reflections (meolog), WANEELLA pixel art, "
                "and Tumblr Staff. After unfollowing the cabin blog the page "
                "shows 5 blogs; after following it again the page is back to "
                "its original six.")
    if task_no == 11:
        rb.step("navigate", "homepage", home)
        rb.step("click", "Log in", login)
        rb.step("type", "email field", login, text="bob.c@test.com")
        rb.step("type", "password field", login, text=PASSWORD)
        rb.step("click", "Log in button", BASE + "/dashboard")
        rb.step("click", "Explore", BASE + "/explore")
        rb.step("read", "first trending post", BASE + "/explore")
        rb.step("click", "open first trending post",
                BASE + "/blog/meolog/817505727903137792")
        rb.step("read", "current note count", BASE + "/blog/meolog/817505727903137792")
        rb.step("click", "like the post", BASE + "/blog/meolog/817505727903137792",
                detail="like toggle on meolog's post")
        rb.step("read", "count after liking", BASE + "/explore")
        rb.step("click", "Home", BASE + "/dashboard")
        rb.step("click", "Likes tab", BASE + "/likes")
        rb.step("read", "top of likes", BASE + "/likes")
        return ("The first trending post on Explore is by meolog with 3.4K "
                "notes; after liking it the count shows 3,405 notes. The Likes "
                "page now shows that 'Rhododendron' post by meolog at the top.")
    if task_no == 12:
        rb.step("navigate", "homepage", home)
        rb.step("click", "Log in", login)
        rb.step("type", "email field", login, text="carol.d@test.com")
        rb.step("type", "password field", login, text=PASSWORD)
        rb.step("click", "Log in button", BASE + "/dashboard")
        rb.step("click", "Home", BASE + "/dashboard")
        rb.step("click", "Following tab", BASE + "/following")
        rb.step("read", "followed blogs", BASE + "/following")
        rb.step("click", "open waneella blog", BASE + "/blog/waneella")
        rb.step("click", "open newest post",
                BASE + "/blog/waneella/827616468115079168")
        rb.step("read", "newest post", BASE + "/blog/waneella/827616468115079168")
        rb.step("click", "Reblog", BASE + "/post/827616468115079168/reblog")
        rb.step("type", "comment", BASE + "/post/827616468115079168/reblog",
                text="someday.")
        rb.step("click", "publish reblog", BASE + "/blog/carol-d/1790596800000")
        rb.step("click", "open own blog", BASE + "/blog/carol-d")
        rb.step("read", "reblog details", BASE + "/blog/carol-d")
        return ("The pixel-art blog Carol follows is waneella; its newest post "
                "'Shimmer' was reblogged with the comment 'someday.'. On "
                "carol-d's blog the reblog shows the original post's blog "
                "waneella in the trail, the comment someday., and no tags "
                "carried over (the source post has none).")
    if task_no == 13:
        rb.step("navigate", "homepage", home)
        rb.step("click", "Log in", login)
        rb.step("type", "email field", login, text="david.k@test.com")
        rb.step("type", "password field", login, text=PASSWORD)
        rb.step("click", "Log in button", BASE + "/dashboard")
        rb.step("type", "search box", BASE + "/dashboard", text="cyberpunk")
        rb.step("click", "search submit", BASE + "/search/cyberpunk")
        rb.step("read", "blog suggestions", BASE + "/search/cyberpunk")
        rb.step("click", "open scipunk blog", BASE + "/blog/scipunk")
        rb.step("read", "title + description", BASE + "/blog/scipunk")
        rb.step("click", "follow", BASE + "/blog/scipunk", detail="follow toggle")
        rb.step("click", "Home", BASE + "/dashboard")
        rb.step("click", "Following tab", BASE + "/following")
        rb.step("read", "following list", BASE + "/following")
        rb.step("click", "Home", BASE + "/dashboard")
        rb.step("click", "open newest scipunk post",
                BASE + "/blog/scipunk/828771454435852288")
        rb.step("read", "newest post summary",
                BASE + "/blog/scipunk/828771454435852288")
        return ("The last blog suggested for 'cyberpunk' is scipunk, titled "
                "Cyberpunk Aesthetic, described 'Neon Lights - Movies - Games - "
                "Sci-fi - Computers - Megacities - Rain - Glitch Art - Music - "
                "scipunk.bsky.social'. After following it, scipunk appears on "
                "the Following page and its posts show up on the dashboard; "
                "the newest one is 'Alien (1979)'.")
    if task_no == 14:
        rb.step("navigate", "homepage", home)
        rb.step("click", "Log in", login)
        rb.step("type", "email field", login, text="alice.j@test.com")
        rb.step("type", "password field", login, text=PASSWORD)
        rb.step("click", "Log in button", BASE + "/dashboard")
        rb.step("click", "Inbox", BASE + "/inbox")
        rb.step("read", "inbox list", BASE + "/inbox")
        rb.step("click", "open staff conversation", BASE + "/inbox/staff")
        rb.step("read", "thread", BASE + "/inbox/staff")
        rb.step("type", "reply textarea", BASE + "/inbox/staff",
                text="One more question: what is next for Tumblr?")
        rb.step("click", "Send", BASE + "/inbox/staff")
        rb.step("read", "confirmation + thread", BASE + "/inbox/staff")
        rb.step("click", "back to inbox", BASE + "/inbox")
        rb.step("read", "conversations + unread", BASE + "/inbox")
        return ("The last message staff sent is 'Glad to hear it! The tag pages "
                "got a fresh coat of paint this month. Let us know if anything "
                "else comes up.' The reply 'One more question: what is next for "
                "Tumblr?' was sent \u2014 the page confirmed 'Message sent.' and the "
                "message appears in the thread. Back in the inbox, 2 conversations "
                "are listed and the bob-c one shows as unread.")
    if task_no == 15:
        rb.step("navigate", "homepage", home)
        rb.step("click", "Log in", login)
        rb.step("type", "email field", login, text="bob.c@test.com")
        rb.step("type", "password field", login, text=PASSWORD)
        rb.step("click", "Log in button", BASE + "/dashboard")
        rb.step("click", "Following tab", BASE + "/following")
        rb.step("read", "followed blogs", BASE + "/following")
        rb.step("click", "open alice's blog", BASE + "/blog/alice-j")
        rb.step("click", "Ask me anything", BASE + "/blog/alice-j/ask")
        rb.step("type", "ask textarea", BASE + "/blog/alice-j/ask",
                text="Which museum do you visit most often?")
        rb.step("click", "Send ask", BASE + "/blog/alice-j")
        rb.step("read", "confirmation", BASE + "/blog/alice-j")
        rb.step("click", "Log out", home)
        rb.step("click", "Log in", login)
        rb.step("type", "email field", login, text="alice.j@test.com")
        rb.step("type", "password field", login, text=PASSWORD)
        rb.step("click", "Log in button", BASE + "/dashboard")
        rb.step("click", "Inbox", BASE + "/inbox")
        rb.step("read", "inbox", BASE + "/inbox")
        rb.step("click", "open bob conversation", BASE + "/inbox/bob-c")
        rb.step("read", "arrived question", BASE + "/inbox/bob-c")
        return ("Bob's ask was sent: 'Your question has been sent to Alice's "
                "Archive.' After logging out and back in as Alice, the inbox "
                "shows a conversation from bob-c with the question 'Which "
                "museum do you visit most often?'")
    if task_no == 16:
        rb.step("navigate", "homepage", home)
        rb.step("click", "Log in", login)
        rb.step("type", "email field", login, text="alice.j@test.com")
        rb.step("type", "password field", login, text=PASSWORD)
        rb.step("click", "Log in button", BASE + "/dashboard")
        rb.step("read", "activity badge 4", BASE + "/dashboard")
        rb.step("click", "Activity", BASE + "/activity")
        rb.step("read", "all notifications", BASE + "/activity")
        rb.step("click", "open the newest actor's blog", BASE + "/blog/bob-c")
        rb.step("read", "actor blog title + posts", BASE + "/blog/bob-c")
        rb.step("click", "Inbox", BASE + "/inbox")
        rb.step("read", "inbox badge", BASE + "/inbox")
        rb.step("click", "Home", BASE + "/dashboard")
        rb.step("read", "activity badge cleared", BASE + "/dashboard")
        return ("The Activity badge showed 4. Opening Activity lists: bob-c "
                "liked your post \"hello tumblr\"; carol-d reblogged your post "
                "\"hello tumblr\"; david-k started following your blog; bob-c "
                "sent you a message \u2014 the newest happened 2 days ago. The "
                "newest notification's actor blog is bob-c: titled \"bob's "
                "sketchbook\" with 3 posts. The Inbox badge shows 1 unread "
                "message. Back on the home page the Activity badge has cleared.")
    if task_no == 17:
        rb.step("navigate", "homepage", home)
        rb.step("click", "Log in", login)
        rb.step("type", "email field", login, text="carol.d@test.com")
        rb.step("type", "password field", login, text=PASSWORD)
        rb.step("click", "Log in button", BASE + "/dashboard")
        rb.step("click", "New post", BASE + "/new/post")
        rb.step("type", "post title", BASE + "/new/post",
                text="Cabin Wishlist, Part Two")
        rb.step("type", "post body", BASE + "/new/post",
                text="A cast-iron wood stove with a glass door is at the top of "
                     "my cabin wishlist.")
        rb.step("type", "post tags", BASE + "/new/post",
                text="cottagecore, wishlist")
        rb.step("click", "Post", BASE + "/blog/carol-d/1790596800001")
        rb.step("click", "open own blog", BASE + "/blog/carol-d")
        rb.step("read", "title + tags", BASE + "/blog/carol-d")
        rb.step("click", "first tag link", BASE + "/tagged/cottagecore")
        rb.step("read", "tag page posts", BASE + "/tagged/cottagecore")
        return ("Published 'Cabin Wishlist, Part Two' about a wood stove with "
                "the tags #cottagecore and #wishlist. On carol-d's blog the post "
                "shows both tags; the first tag links to the #cottagecore tag "
                "page which shows 10 posts (11 total).")
    if task_no == 18:
        rb.step("navigate", "homepage", home)
        rb.step("click", "Log in", login)
        rb.step("type", "email field", login, text="alice.j@test.com")
        rb.step("type", "password field", login, text=PASSWORD)
        rb.step("click", "Log in button", BASE + "/dashboard")
        rb.step("click", "New post", BASE + "/new/post")
        rb.step("click", "Quote tab", BASE + "/new/post?type=quote")
        rb.step("type", "quote text", BASE + "/new/post?type=quote",
                text="\u201cArt is the only way to run away without leaving "
                     "home.\u201d")
        rb.step("type", "quote source", BASE + "/new/post?type=quote",
                text="Twyla Tharp")
        rb.step("type", "post tags", BASE + "/new/post?type=quote", text="quotes")
        rb.step("click", "Post", BASE + "/blog/alice-j/1790596800002")
        rb.step("click", "open own blog", BASE + "/blog/alice-j")
        rb.step("read", "quote post", BASE + "/blog/alice-j")
        return ("Published the quote post: '\u201cArt is the only way to run away "
                "without leaving home.\u201d — Twyla Tharp' with the tag #quotes. "
                "On alice-j's blog the post shows the quote, the source and the "
                "#quotes tag.")
    if task_no == 19:
        rb.step("navigate", "homepage", home)
        rb.step("click", "Log in", login)
        rb.step("type", "email field", login, text="bob.c@test.com")
        rb.step("type", "password field", login, text=PASSWORD)
        rb.step("click", "Log in button", BASE + "/dashboard")
        rb.step("click", "settings avatar chip", BASE + "/settings")
        rb.step("read", "settings", BASE + "/settings")
        rb.step("type", "blog title", BASE + "/settings", text="bob's art lab")
        rb.step("click", "Save blog settings", BASE + "/settings")
        rb.step("click", "open own blog", BASE + "/blog/bob-c")
        rb.step("read", "title/username/posts/newest", BASE + "/blog/bob-c")
        rb.step("click", "Archive", BASE + "/blog/bob-c/archive")
        rb.step("read", "newest month", BASE + "/blog/bob-c/archive")
        return ("The blog title now reads exactly \"bob's art lab\"; the blog's "
                "username is bob-c, it shows 3 posts, and the newest post's "
                "summary is 'shapes shapes shapes'. The archive's newest month "
                "is September 2026.")
    if task_no == 20:
        rb.step("navigate", "homepage", home)
        rb.step("click", "Sign up", BASE + "/register")
        rb.step("type", "email", BASE + "/register",
                text="harbor.tester@example.com")
        rb.step("type", "username", BASE + "/register", text="harbor-tester")
        rb.step("type", "password", BASE + "/register", text=PASSWORD)
        rb.step("click", "Sign up button", BASE + "/dashboard")
        rb.step("read", "empty dashboard", BASE + "/dashboard")
        rb.step("click", "Explore", BASE + "/explore")
        rb.step("type", "search box", BASE + "/explore", text="NASA")
        rb.step("click", "search submit", BASE + "/search/NASA")
        rb.step("click", "follow nasa", BASE + "/search/NASA",
                detail="follow toggle on a nasa post")
        rb.step("click", "Home", BASE + "/dashboard")
        rb.step("read", "first dashboard post", BASE + "/dashboard")
        return ("After registering harbor-tester the dashboard is empty: 'Posts "
                "from the 0 blogs you follow.' / 'Follow some blogs from "
                "Explore to fill your dashboard.' After following NASA from "
                "Explore the first dashboard post is NASA's 'Autumn is a second "
                "spring when every leaf is a flower…' with 5,592 notes (5.6K).")
    raise AssertionError(task_no)


# ------------------------------------------------------------------ run builders
def honest_run(tmp_path: Path, task_no: int) -> Path:
    seed = acquire_seed()
    run = tmp_path / f"honest_{task_no}"
    run.mkdir(parents=True, exist_ok=True)
    rb = RunBuilder(run, f"Tumblr--{task_no}")
    final_answer = honest_steps(task_no, rb)
    rb.finish(BASE + "/", final_answer)
    apply_state(task_no, seed, run / "after.db")
    copy_db(seed, run / "initial.db")
    return run


def noop_run(tmp_path: Path, task_no: int) -> Path:
    seed = acquire_seed()
    run = tmp_path / f"noop_{task_no}"
    run.mkdir(parents=True, exist_ok=True)
    rb = RunBuilder(run, f"Tumblr--{task_no}")
    rb.step("navigate", "homepage", BASE + "/")
    rb.finish(BASE + "/", "")
    copy_db(seed, run / "initial.db")
    copy_db(seed, run / "after.db")
    return run


def shortcut_run(tmp_path: Path, task_no: int) -> Path:
    """Correct answer + honest DB delta, but homepage-only navigation."""
    seed = acquire_seed()
    run = tmp_path / f"shortcut_{task_no}"
    run.mkdir(parents=True, exist_ok=True)
    scratch = tmp_path / f"_scratch_shortcut_{task_no}"
    scratch.mkdir(parents=True, exist_ok=True)
    answer = honest_steps(task_no, RunBuilder(scratch, f"Tumblr--{task_no}"))
    shutil.rmtree(scratch, ignore_errors=True)
    rb = RunBuilder(run, f"Tumblr--{task_no}")
    rb.step("navigate", "homepage", BASE + "/")
    rb.finish(BASE + "/", answer)
    apply_state(task_no, seed, run / "after.db")
    copy_db(seed, run / "initial.db")
    return run


def wrong_answer_run(tmp_path: Path, task_no: int, wrong: str) -> Path:
    seed = acquire_seed()
    run = tmp_path / f"wrong_{task_no}"
    run.mkdir(parents=True, exist_ok=True)
    rb = RunBuilder(run, f"Tumblr--{task_no}")
    honest_steps(task_no, rb)          # honest navigation...
    rb.finish(BASE + "/", wrong)       # ...but a wrong answer
    apply_state(task_no, seed, run / "after.db")
    copy_db(seed, run / "initial.db")
    return run


def state_mismatch_run(tmp_path: Path, task_no: int) -> Path:
    """Honest answer + navigation but a clean, un-mutated after-DB."""
    seed = acquire_seed()
    run = tmp_path / f"mismatch_{task_no}"
    run.mkdir(parents=True, exist_ok=True)
    rb = RunBuilder(run, f"Tumblr--{task_no}")
    answer = honest_steps(task_no, rb)
    rb.finish(BASE + "/", answer)
    copy_db(seed, run / "initial.db")
    copy_db(seed, run / "after.db")
    return run


def mutated_readonly_run(tmp_path: Path, task_no: int) -> Path:
    """Honest read-only run but the after-DB carries a stray like row."""
    seed = acquire_seed()
    run = tmp_path / f"mutated_{task_no}"
    run.mkdir(parents=True, exist_ok=True)
    rb = RunBuilder(run, f"Tumblr--{task_no}")
    answer = honest_steps(task_no, rb)
    rb.finish(BASE + "/", answer)
    copy_db(seed, run / "initial.db")
    after = copy_db(seed, run / "after.db")
    exec_sql(after, [("INSERT INTO likes (user_id, post_id, created_at)"
                      " VALUES (1, '999999999999999999', ?)", (RUN_TS,))])
    return run


def run_verifier(task_no: int, run_dir: Path, expect_pass: bool) -> dict:
    proc = subprocess.run(
        [sys.executable, str(VERIFY_DIR / f"verify_{task_no}.py"),
         "--run_dir", str(run_dir),
         "--initial_db", str(run_dir / "initial.db"),
         "--after_db", str(run_dir / "after.db"),
         "--no_llm", "True"],
        capture_output=True, text=True, timeout=180)
    try:
        verdict = json.loads(proc.stdout)
    except json.JSONDecodeError:
        raise AssertionError(f"verifier {task_no} produced no JSON: "
                             f"{proc.stdout[:200]} {proc.stderr[:200]}")
    if expect_pass and not verdict["pass"]:
        raise AssertionError(f"verifier {task_no} expected PASS got FAIL "
                             f"({verdict['reason']}): "
                             f"{[e for e in verdict['evidence'] if e.startswith('[FAIL]')][:6]}")
    if not expect_pass and verdict["pass"]:
        raise AssertionError(f"verifier {task_no} expected FAIL got PASS")
    return verdict
