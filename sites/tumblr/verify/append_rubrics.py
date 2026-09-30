#!/usr/bin/env python3
"""append_rubrics.py — attach verifier_path + judge_rubric to tasks.jsonl.

Contract:
- The original five keys (web_name, id, ques, web, upstream_url) keep their
  exact serialized bytes: each output line is the original JSON object with
  the two new keys appended, so the original prefix is byte-identical.
- No answer/ground-truth data leaks into tasks.jsonl; the rubrics are pure
  English rules (ryanair-style FACT CHECKPOINTS); ground truth stays
  hardcoded in verify/verify_N.py.
- Idempotent: lines that already carry verifier_path are left untouched.

Usage: python3 append_rubrics.py [tasks.jsonl]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

RUBRICS = {
    "Tumblr--0":
        "FACT CHECKPOINTS: (1) The trajectory MUST start at the home page and open "
        "the most-followed card in the Popular tags panel, reporting that tag's "
        "follower count, today's new-post count, and the editorial description the "
        "hub page serves, each exactly as shown. (2) The trajectory MUST open the "
        "first related tag shown in the hub sidebar and report its name and its "
        "new-post count as shown on the related row. (3) The trajectory MUST "
        "return, open the newest post in the tag's feed, report the posting blog, "
        "its note count and the post's first tag, then open that blog and report "
        "its post count. An answer without the matching navigation trail is a FAIL. "
        "Read-only task: any database change is a FAIL.",

    "Tumblr--1":
        "FACT CHECKPOINTS: (1) The trajectory MUST open the Explore page and report "
        "the blog name and note count of the first trending post as shown on its "
        "card. (2) The trajectory MUST open that post and report its like count and "
        "reblog count exactly as displayed. (3) The trajectory MUST return to "
        "Explore, reach page 2 via the pagination, and report the first post's blog "
        "name, note count, opening words and first two tags. An answer without the "
        "Explore and page-2 navigation is a FAIL. Read-only task: any database change "
        "is a FAIL. (4) The trajectory MUST open the page-2 first post's blog and "
        "report its exact title, its total post count, and its 'Updated …' label "
        "exactly as shown.",

    "Tumblr--2":
        "FACT CHECKPOINTS: (1) The trajectory MUST search 'pixel art' via the search "
        "box and report how many results the Top tab shows plus the names of the "
        "first two blogs in the Blogs matching sidebar. (2) The trajectory MUST "
        "switch to the Recent tab and report the blog name of the newest post and its "
        "note count. (3) The trajectory MUST open that post and report its first two "
        "tags and its like count. An answer without the Top and Recent tab navigation "
        "is a FAIL. Read-only task: any database change is a FAIL. (4) The trajectory "
        "MUST open the first matching blog in the sidebar and report its exact title, "
        "its post count, and one phrase from its description.",

    "Tumblr--3":
        "FACT CHECKPOINTS: (1) The trajectory MUST search 'NASA' and open NASA's own "
        "blog from the results, reporting its exact title, its total post count and "
        "its last-updated label as shown on the blog page. (2) The trajectory MUST "
        "open the blog's archive and report which month has the most posts and that "
        "month's post count. (3) The trajectory MUST open one post from the newest "
        "archive month and report that post's true note count and summary. An answer "
        "naming a month or count inconsistent with the archive is a FAIL. Read-only "
        "task: any database change is a FAIL. (4) The trajectory MUST also report how "
        "many posts the archive's newest month contains, then come back to the blog "
        "page, open the second post in its feed, and report that post's note count "
        "and first tag. The second-feed-post navigation is required.",

    "Tumblr--4":
        "FACT CHECKPOINTS: (1) The trajectory MUST find the Tumblr Staff post "
        "announcing that reblogs in a chain now get their own notes and open it, "
        "reporting the exact note count, like count and reblog count shown, plus "
        "the post's opening line, the usernames of the two most recent likers, and "
        "the first reblog shown in its notes. (2) The trajectory MUST open the "
        "posting blog and report its title, total post count and last-updated "
        "label, then open the blog's newest post and report the first tag on that "
        "post. An answer whose first tag belongs to a different post is a FAIL. "
        "Read-only task: any database change is a FAIL.",

    "Tumblr--5":
        "FACT CHECKPOINTS: (1) The trajectory MUST find the answered ask where "
        "someone tells the Paokai blog their art is gorgeous (a search combining "
        "the blog name and 'gorgeous') and open it, reporting the asker's username, "
        "the question, the first line of the answer, the post's note count and its "
        "tags. (2) The trajectory MUST open the posting blog and report its title, "
        "its post count, the newest month shown in its archive and that month's "
        "post count. An answer whose asker or question text does not match the "
        "found ask post is a FAIL. Read-only task: any database change is a FAIL.",

    "Tumblr--6":
        "FACT CHECKPOINTS: (1) The trajectory MUST search 'flight test like a NASA "
        "engineer' and open the result titled 'Flight Test Like a NASA Engineer!' — "
        "the only page-1 result card carrying that title — reporting the video "
        "provider shown under the player on that post, the post's tags, and its "
        "note count, like count, and reblog count. (2) The trajectory MUST open the "
        "posting blog and report its title, total post count, last-updated label, "
        "and the newest month shown in its archive with its number of posts. An "
        "answer reporting a different NASA post is a FAIL. Read-only task: any "
        "database change is a FAIL.",

    "Tumblr--7":
        "FACT CHECKPOINTS: (1) The trajectory MUST search 'operating CCTV cameras' "
        "and open the top result — the post about somebody's first time operating "
        "CCTV cameras — reporting the full chain of blog usernames in its reblog "
        "trail in order, the post's summary text, its total note count, like count, "
        "reblog count and tags, and the opening words of the original post in the "
        "trail. (2) The trajectory MUST open the original blog in the trail and "
        "report its title, total post count, and last-updated label as shown on its "
        "blog page. An answer whose trail chain or note count belongs to a "
        "different CCTV post is a FAIL. Read-only task: any database change is a "
        "FAIL.",

    "Tumblr--8":
        "FACT CHECKPOINTS: (1) The trajectory MUST sign in as alice.j@test.com with "
        "the given password through the visible login form and open the dashboard. "
        "(2) The trajectory MUST report how many posts the first page shows, the name "
        "of every blog appearing on that page, and the summary and note count of the "
        "newest post. (3) The trajectory MUST open that newest post and report its "
        "like count, reblog count and total note count. An answer without the "
        "dashboard navigation is a FAIL. Read-only task: any database change is a "
        "FAIL. (4) The trajectory MUST open the second post on the dashboard and "
        "report its blog name, note count, and first tag. The second-post permalink "
        "navigation is required.",

    "Tumblr--9":
        "FACT CHECKPOINTS: (1) The trajectory MUST sign in as alice.j@test.com and "
        "open the Likes page, reporting the total number of liked posts shown in "
        "the page head and, for the most recent one, the posting blog, its summary "
        "and its note count. (2) The trajectory MUST open that post and report its "
        "first tag, like count, reblog count and total note count. The like count "
        "may read as the raw count or one higher where the page includes Alice's "
        "own like. Read-only task: any database change is a FAIL.",

    "Tumblr--10":
        "FACT CHECKPOINTS: (1) The trajectory MUST sign in as alice.j@test.com, "
        "open the Following page and list every followed blog in the order shown. "
        "(2) The trajectory MUST unfollow the cabin blog, verify it no longer "
        "appears on the page, and report the new follow count. (3) The trajectory "
        "MUST follow the cabin blog again and confirm the page is back to its "
        "original list. State contract: the follow set MUST be identical to the "
        "seed afterwards; the only tolerated database delta is the recreated follow "
        "row's timestamp.",

    "Tumblr--11":
        "FACT CHECKPOINTS: (1) The trajectory MUST sign in as bob.c@test.com, open "
        "Explore, open the first trending post, note its current note count and "
        "like it, reporting the count shown after liking (one higher than before). "
        "(2) The trajectory MUST open the Likes page and confirm the just-liked "
        "post appears at the top, reporting its summary and posting blog. State "
        "contract: exactly one like row for this user on the first trending post is "
        "added, and it must be the user's newest like.",

    "Tumblr--12":
        "FACT CHECKPOINTS: (1) The trajectory MUST sign in as carol.d@test.com, "
        "open the Following page, open the pixel-art blog followed there, then open "
        "that blog's newest post. (2) The trajectory MUST reblog the post with the "
        "exact comment 'someday.' and visit the user's own blog page, reporting the "
        "original post's blog and the comment shown on the reblog. The source post "
        "carries no tags (also upstream), so the honest 'tags carried over' report "
        "is none. State contract: exactly one user-created reblog post with the "
        "comment, one reblog row, and the user blog's post count bumped by one.",

    "Tumblr--13":
        "FACT CHECKPOINTS: (1) The trajectory MUST sign in as david.k@test.com, "
        "search 'cyberpunk' and open the LAST blog suggested in the sidebar, "
        "reporting its title and the description shown on its blog page. (2) The "
        "trajectory MUST follow the blog, confirm it appears on the Following page, "
        "and report the summary of its newest post on the dashboard. State "
        "contract: exactly one follow row for this user on the suggested blog is "
        "added.",

    "Tumblr--14":
        "FACT CHECKPOINTS: (1) The trajectory MUST sign in as alice.j@test.com, open "
        "the inbox and the conversation with the Tumblr Staff blog, and report the "
        "exact text of the last message staff sent. (2) The trajectory MUST reply "
        "asking one more question, confirm the sent confirmation message, and confirm "
        "the agent's own message appears in the thread, reporting its text. State "
        "contract: exactly one outgoing message row appended to the staff "
        "conversation and its updated_at bumped; nothing else. (4) The trajectory "
        "MUST go back to the inbox after the reply and report how many conversations "
        "are listed and which one shows as unread.",

    "Tumblr--15":
        "FACT CHECKPOINTS: (1) The trajectory MUST sign in as bob.c@test.com, reach "
        "Alice's blog, open its ask form, submit a question asking which museum she "
        "visits most, and confirm the ask was sent. (2) The trajectory MUST log "
        "out, sign in as alice.j@test.com, open the inbox and report the exact text "
        "of the question that arrived. State contract: one new conversation for "
        "Alice with the asker and one incoming message containing the museum "
        "question; nothing else.",

    "Tumblr--16":
        "FACT CHECKPOINTS: (1) The trajectory MUST sign in as alice.j@test.com, note "
        "the unread badge count on Activity, open Activity and list every "
        "notification with who acted and what they did, plus how long ago the newest "
        "one happened (deterministic against the frozen mirror date). (2) The "
        "trajectory MUST read the Inbox nav badge and report the unread count it "
        "shows. (3) The trajectory MUST navigate to the home page and confirm the "
        "Activity badge has cleared. State contract: the user's notification rows "
        "flip to read and nothing else changes. (4) The trajectory MUST open the "
        "newest notification's actor blog and report its title and post count. The "
        "actor-blog navigation is required.",

    "Tumblr--17":
        "FACT CHECKPOINTS: (1) The trajectory MUST sign in as carol.d@test.com and "
        "create a text post titled 'Cabin Wishlist, Part Two' with at least one "
        "sentence about a wood stove and the tags cottagecore and wishlist, then "
        "publish it. (2) The trajectory MUST open the user's blog page, report the "
        "post's title and tags, and follow the first tag link to confirm the tag "
        "page shows posts. State contract: exactly one user-created post with the "
        "title, wood-stove body and both tags; the user blog's post count bumped by "
        "one.",

    "Tumblr--18":
        "FACT CHECKPOINTS: (1) The trajectory MUST sign in as alice.j@test.com and "
        "create a quote post quoting 'Art is the only way to run away without "
        "leaving home.' attributed to Twyla Tharp, with the tag quotes, then "
        "publish it. (2) The trajectory MUST open the user's blog page and report "
        "the quote, its source and the tag shown on the post. State contract: "
        "exactly one user-created quote post with the quote, source and tag; the "
        "user blog's post count bumped by one.",

    "Tumblr--19":
        "FACT CHECKPOINTS: (1) The trajectory MUST sign in as bob.c@test.com, open "
        "settings, change the blog title to 'bob's art lab' and save. (2) The "
        "trajectory MUST open the user's blog page and report the new title exactly "
        "as displayed, the blog's username, how many posts it shows and the summary "
        "of its newest post, then open the blog's archive and report the newest "
        "month shown. State contract: only the user's blog row title changes.",

    "Tumblr--20":
        "FACT CHECKPOINTS: (1) The trajectory MUST register a new account with an "
        "email of the agent's choosing, the username harbor-tester and a password "
        "of at least 8 characters, then confirm landing on an empty dashboard and "
        "report the message shown. (2) The trajectory MUST follow NASA's blog "
        "starting from Explore and report the first post that appears on the "
        "dashboard, including its summary and note count. State contract: one new "
        "user row with the pinned username, one new blog row for it, and one follow "
        "row to NASA; nothing else."
}

ORIGINAL_KEYS = ("web_name", "id", "ques", "web", "upstream_url")


def main() -> int:
    path = Path(sys.argv[1] if len(sys.argv) > 1 else
                Path(__file__).resolve().parents[1] / "tasks.jsonl")
    lines = path.read_text(encoding="utf-8").splitlines()
    out_lines = []
    changed = 0
    for line in lines:
        if not line.strip():
            out_lines.append(line)
            continue
        row = json.loads(line)
        if "verifier_path" in row:
            out_lines.append(line)
            continue
        if tuple(row.keys()) != ORIGINAL_KEYS:
            raise SystemExit(f"unexpected key order in tasks.jsonl: {tuple(row.keys())!r}")
        task_no = int(row["id"].rsplit("--", 1)[1])
        new_row = dict(row)
        new_row["verifier_path"] = f"sites/tumblr/verify/verify_{task_no}.py"
        new_row["judge_rubric"] = RUBRICS[row["id"]]
        # byte-preserving append: the original serialization is the prefix
        rendered = json.dumps(new_row, ensure_ascii=False)
        prefix = json.dumps(row, ensure_ascii=False)
        if not rendered.startswith(prefix[:-1]):
            raise SystemExit(f"original bytes not preserved for {row['id']}")
        out_lines.append(rendered)
        changed += 1
    path.write_text("\n".join(out_lines) + "\n", encoding="utf-8")
    print(f"append_rubrics: updated {changed} lines in {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
