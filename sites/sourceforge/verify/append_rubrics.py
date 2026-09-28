#!/usr/bin/env python3
"""Rewrite judge_rubric on sites/sourceforge/tasks.jsonl.

The contributor already appended verifier_path and judge_rubric. Those
rubrics named the ground-truth projects, counts, dates, and ticket ids.
The agent reads tasks.jsonl, so a rubric must state the checkpoints only.

This script replaces judge_rubric in place. It does not add an answer key
and it keeps web_name, id, ques, web, upstream_url, and verifier_path.
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
TASKS = HERE.parent / "tasks.jsonl"

KEY_ORDER = (
    "web_name",
    "id",
    "ques",
    "web",
    "upstream_url",
    "verifier_path",
    "judge_rubric",
)

RUBRICS = {
    0: (
        "FACT CHECKPOINTS: (1) The agent MUST search the open source directory "
        "for file compression, sort by Most Popular, and open the top two "
        "result project pages plus 7-Zip, including each project's Reviews "
        "page. (2) The answer MUST name those three projects and, for each, "
        "the weekly download count, registered date, and license from the "
        "project page, plus the average rating and total review count from "
        "the Reviews page, and MUST say which project was updated most "
        "recently. (3) Each number and date MUST be attributed to the correct "
        "project. An empty answer is a FAIL. FAIL if a count, date, rating, "
        "or license is swapped across projects."
    ),
    1: (
        "FACT CHECKPOINTS: (1) The agent MUST open the 7-Zip file browser, "
        "both newest version folders, the project-page download action, the "
        "download confirmation page, and the download statistics for the "
        "daily table and the operating-system breakdown. (2) The answer MUST "
        "list every build in each of those two folders with its file size, "
        "each folder's own weekly download count, the filename the big "
        "Download button starts, the filename the download page confirms, "
        "the peak day in the daily table with that day's count, and the top "
        "operating system with its count. (3) Each size and count MUST be "
        "attributed to the correct folder, file, day, or operating system. "
        "An empty answer is a FAIL. FAIL if a folder weekly is reported as "
        "zero, or if a count is swapped between the two version folders or "
        "between the peak day and the operating system."
    ),
    2: (
        "FACT CHECKPOINTS: (1) The agent MUST open both 7-Zip's and KeePass's "
        "project pages and Reviews pages, and MUST apply the star-filter "
        "views named in the task. (2) The answer MUST give each project's "
        "overall rating, the 5-star and 1-star histogram counts, the featured "
        "Highest Rated review text and author for 7-Zip, the 4-star "
        "filter-view count for 7-Zip, the 5-star and 4-star filter-view "
        "counts for KeePass, and which project shows more total reviews on "
        "its project page. (3) Histogram counts and filter-view counts MUST "
        "stay distinct and attached to the correct project and star level. "
        "An empty answer is a FAIL. FAIL if a histogram count is used as a "
        "filter-view count, or if a rating or count is swapped between 7-Zip "
        "and KeePass."
    ),
    3: (
        "FACT CHECKPOINTS: (1) The agent MUST find the progress-bar ticket in "
        "the 7-Zip Bugs tracker, search that tracker for CVE, open the two "
        "newest CVE tickets and the lowest-numbered CVE ticket, and read the "
        "open-ticket count from the sidebar. (2) The answer MUST report that "
        "ticket's number, summary, status, creator, and priority, summarize "
        "the project owner's reply, the CVE search result count, the two "
        "newest CVE tickets' numbers, summaries, and priorities, the "
        "lowest-numbered CVE ticket's owner and creation date, and the "
        "sidebar open count. (3) Each priority, owner, date, and count MUST "
        "be bound to the ticket or sidebar it came from. An empty answer is "
        "a FAIL. FAIL if a near-miss ticket is substituted for the "
        "progress-bar ticket, or if one ticket's priority is reused for "
        "another."
    ),
    4: (
        "FACT CHECKPOINTS: (1) The agent MUST open 7-Zip's Open Discussion "
        "forum, the dark-mode thread, the older Dark Theme thread, that "
        "forum's highest-viewed thread, the Help forum, and the Help forum's "
        "highest-viewed thread. (2) The answer MUST report the dark-mode "
        "thread's subject, creator, creation date, post count, and view "
        "count, and quote the health reason in its opening post; the Dark "
        "Theme thread's creator, post count, view count, and a quote of its "
        "opening post; the highest-viewed thread's subject, creator, and "
        "exact view count; and the Help forum's name, topic count, and its "
        "highest-viewed thread's subject, creator, and view count. (3) Post "
        "counts and view counts MUST stay attached to the thread they belong "
        "to. An empty answer is a FAIL. FAIL if a count from one thread is "
        "reported for another."
    ),
    5: (
        "FACT CHECKPOINTS: (1) The agent MUST open the Top Downloaded "
        "Projects page, the top three all-time project pages and their "
        "Reviews pages, and 7-Zip's project page and Reviews page. (2) The "
        "answer MUST name the all-time #1 with its displayed figure, the "
        "last-week #1 with its displayed figure, and 7-Zip's all-time rank "
        "with its displayed total; each of the top three's registered date "
        "and weekly downloads; the two #1s' licenses; all three top "
        "projects' average ratings and review counts; and 7-Zip's last "
        "update date, total review count, and Reviews-page average rating. "
        "(3) Ranks, figures, dates, licenses, ratings, and review counts "
        "MUST be attributed to the correct project. An empty answer is a "
        "FAIL. FAIL if an all-time rank is taken from digits inside another "
        "project's download total, or if stats are swapped across the top "
        "three."
    ),
    6: (
        "FACT CHECKPOINTS: (1) The agent MUST browse the Business Software "
        "CRM category, open every listed product's business page, search the "
        "open source directory for CRM sorted by Rating, and open the first "
        "result's project, Reviews, and Support pages. (2) The answer MUST "
        "list every CRM product with its rating and ratings count, each "
        "product's full description and the category label on its business "
        "page, the CRM search result count, and the first result's summary, "
        "license, weekly downloads, last update date, average rating, review "
        "count, and Support-tab help recommendation. (3) Ratings and ratings "
        "counts MUST stay paired with the correct product, and a "
        "business-directory rating MUST not be substituted for the "
        "open-source project's review rating. An empty answer is a FAIL. "
        "FAIL if a product's rating or count is swapped with another's."
    ),
    7: (
        "FACT CHECKPOINTS: (1) The agent MUST log in as the demo account "
        "named in the task, search the directory for password manager, open "
        "the top result, bookmark it, and post a 5-star review that says "
        "the user uses it daily, then confirm both on the account page. (2) "
        "The answer MUST name that top result and its weekly downloads. (3) "
        "The after-state MUST contain exactly one new bookmark by that user "
        "for that project and exactly one new 5-star review by that user "
        "mentioning daily use, with that project's counters updated and "
        "every other table unchanged. An empty answer is a FAIL. FAIL if "
        "the bookmark or review is missing, is for a different project, or "
        "if the weekly count is credited to another project."
    ),
    8: (
        "FACT CHECKPOINTS: (1) The agent MUST open 7-Zip's download "
        "statistics for country, operating system, and the daily table, and "
        "the file-compression directory search sorted by Most Popular, then "
        "open the top three result project pages. (2) The answer MUST report "
        "the top country with its count, the top operating system with its "
        "count, the peak day with that day's count, and for each of the top "
        "three projects the registered date and license, plus which of the "
        "three was updated most recently. (3) Each count, date, and license "
        "MUST be attributed to the correct place or project. An empty answer "
        "is a FAIL. FAIL if the country, operating-system, and peak-day "
        "counts are swapped, or if dates or licenses are swapped across the "
        "three projects."
    ),
    9: (
        "FACT CHECKPOINTS: (1) The agent MUST browse the Games category "
        "including its second page, open the first two projects' pages, "
        "Reviews pages, and Support tabs, and open the Top Downloaded "
        "Projects page. (2) The answer MUST report how many projects the "
        "category lists, the first two names, the second page's project "
        "count and first name, the first project's license, last update, "
        "weekly downloads, average rating, review count, and Support "
        "recommendation, the second project's license, operating systems, "
        "last update, weekly downloads, average rating, and review count, "
        "and the #1 weekly project. (3) Each field MUST stay attached to the "
        "project it came from. An empty answer is a FAIL. FAIL if the two "
        "projects' stats are swapped or if page 1's count is reported as "
        "page 2's."
    ),
    10: (
        "FACT CHECKPOINTS: (1) The agent MUST read the homepage picks, open "
        "the portable software platform from Popular Projects plus both "
        "choice projects, including each Reviews page, and open the Top "
        "Downloaded Projects page. (2) The answer MUST name the Staff Choice "
        "and Community Choice with the review count shown for each, the "
        "portable platform's weekly downloads, registered date, license, "
        "rating, and review count, both choice projects' weekly downloads "
        "and last update dates, each choice's average rating, the Staff "
        "Choice's 5-star and 1-star counts, and the last-week #1. (3) The "
        "5-star count and the 1-star count MUST stay bound to those labels, "
        "and each project's numbers MUST not be credited to another project. "
        "An empty answer is a FAIL. FAIL if the two histogram counts are "
        "swapped or if a choice project's stats are assigned to the other "
        "choice."
    ),
    11: (
        "FACT CHECKPOINTS: (1) The agent MUST search the directory for video "
        "player, open the Android native player and the HTML5 player, apply "
        "the Windows facet, open the first Windows result and its Reviews "
        "page, and re-sort the Windows results by Rating. (2) The answer "
        "MUST report the total result count, which result is the Android "
        "native player and which is the HTML5 player, the Android player's "
        "weekly downloads and update date, the HTML5 player's summary and "
        "update date, the Windows-only result count, the first Windows "
        "result's name, weekly downloads, registered date, and average "
        "rating, and the new first result after sorting by Rating. (3) "
        "Counts and dates MUST stay attached to the result or filter they "
        "came from. An empty answer is a FAIL. FAIL if the unfiltered total "
        "is reported as the Windows count, or if the two players' dates are "
        "swapped."
    ),
    12: (
        "FACT CHECKPOINTS: (1) The agent MUST open the 7-Zip project page, "
        "the developer's user profile, each of the three other projects the "
        "profile associates with that developer, and 7-Zip's Reviews page "
        "with the 1-star and 4-star filter views applied. (2) The answer "
        "MUST report the username, join date, and every associated project, "
        "each of the three other projects' summary, license, and registered "
        "date, 7-Zip's average rating, how many reviews the 1-star and "
        "4-star filter views list, and the total review count on the project "
        "page. (3) Each registered date and filter count MUST be bound to "
        "the correct project or star filter. An empty answer is a FAIL. "
        "FAIL if a date from one side project is reported for another, or if "
        "the 1-star and 4-star list counts are swapped."
    ),
    13: (
        "FACT CHECKPOINTS: (1) The agent MUST register the account named in "
        "the task, set the country to Germany and a display name, confirm "
        "both on the account page, bookmark CrystalDiskInfo from its project "
        "page, and confirm that bookmark. (2) The answer MUST mention the "
        "registration, the Germany country setting, the display name, the "
        "CrystalDiskInfo bookmark, the exact heading text of the two account "
        "pages used, and what My Reviews shows for a brand-new user. (3) The "
        "after-state MUST contain exactly one new user row for that username "
        "and email with country DE and a display name, plus exactly one new "
        "bookmark for CrystalDiskInfo, and no other table changed. An empty "
        "answer is a FAIL. FAIL if the country, display name, or bookmark is "
        "missing, or if a review row was created."
    ),
    14: (
        "FACT CHECKPOINTS: (1) The agent MUST open 7-Zip's Wiki, News, and "
        "Support tabs, the Open Discussion forum and its highest-viewed "
        "thread, and the Help forum. (2) The answer MUST report the archive "
        "formats the wiki Home page lists, its credited author, and the "
        "page's last modification date; the two most recent news posts' "
        "titles, dates, and authors; the forum the Support tab names as the "
        "best way to get help; the Open Discussion highest-viewed thread's "
        "subject, creator, and view count; and the Help forum's name, topic "
        "count, and its highest-viewed thread's subject and creator. (3) "
        "Dates and counts MUST be bound to the page, post, or forum they "
        "came from. An empty answer is a FAIL. FAIL if a calendar day inside "
        "a news date is reported as the Help forum's topic count, or if the "
        "two news posts' dates are swapped."
    ),
    15: (
        "FACT CHECKPOINTS: (1) The agent MUST search the 7-Zip Bugs tracker "
        "for CVE, open the two newest CVE tickets and the lowest-numbered "
        "CVE ticket, open the Open Discussion thread about a vulnerability "
        "scanner flagging version 26.02, and read the tracker sidebar. (2) "
        "The answer MUST report the CVE search count, the two newest "
        "tickets' numbers, summaries, statuses, and priorities, the "
        "lowest-numbered CVE ticket's owner and creation date, that thread's "
        "subject, creator, and post count, and the sidebar open-ticket "
        "count. (3) Each priority and status MUST be bound to its own "
        "ticket. An empty answer is a FAIL. FAIL if one ticket's priority is "
        "reused for the other, or if the sidebar open count is taken from "
        "the search count."
    ),
    16: (
        "FACT CHECKPOINTS: (1) The agent MUST open the LZMA SDK folder, start "
        "a download of the newest SDK file, open the 26.01 and 26.00 "
        "folders, start a download of the 26.00 x64 build, and read the "
        "7-Zip root folder's weekly count. (2) The answer MUST list every "
        "SDK file with size, modification date, and weekly downloads, "
        "identify the newest file, and report the filename the download page "
        "confirms; the SDK folder's own weekly count; each build in 26.01 "
        "and 26.00 with size and weekly downloads; the filename confirmed "
        "for the 26.00 x64 download; and the root folder weekly count. (3) "
        "Each size, date, and weekly count MUST stay attached to the correct "
        "file or folder. An empty answer is a FAIL. FAIL if weekly counts "
        "are swapped between SDK files or between the version-folder builds."
    ),
    17: (
        "FACT CHECKPOINTS: (1) The agent MUST open both KeePass and 7-Zip "
        "project pages, both Reviews pages, both Support tabs, any "
        "discussion forum linked from Support, and the all-time Top list. "
        "(2) The answer MUST report each project's weekly downloads, review "
        "count, registered date, and supported operating systems; each "
        "Reviews page's average rating and 5-star and 1-star histogram "
        "counts; each Support tab's help recommendation; the linked forum's "
        "name and thread count; and which project has the larger all-time "
        "total, with both figures. (3) Every figure MUST be attributed to "
        "the correct project. An empty answer is a FAIL. FAIL if weekly "
        "downloads, ratings, or histogram counts are swapped between KeePass "
        "and 7-Zip."
    ),
    18: (
        "FACT CHECKPOINTS: (1) The agent MUST log in as the demo account "
        "named in the task, review the existing bookmarks, remove the "
        "disk-health tool, add the bootable USB drive tool, post that new "
        "project a 4-star review mentioning USB sticks, and confirm the "
        "final list on the account page. (2) The answer MUST name every "
        "project that was bookmarked at the start and the final bookmark "
        "list. (3) The after-state MUST show that user's bookmark swapped "
        "from the disk-health tool to the bootable USB tool, exactly one "
        "new 4-star review by that user mentioning USB, that project's "
        "counters updated, and every other table unchanged. An empty answer "
        "is a FAIL. FAIL if the removed project is still bookmarked, the "
        "new project is missing, or the review is for the wrong project or "
        "the wrong star count."
    ),
    19: (
        "FACT CHECKPOINTS: (1) The agent MUST open the About, Team, Podcast, "
        "Articles, Case Studies, NinjaOne, and Google Cloud Platform pages, "
        "plus Blog, For Vendors, Create, and Support, and MUST run a "
        "directory search for file compression. (2) The answer MUST report "
        "the About page's founding year and software title count; the first "
        "two Team members' names and titles; the newest podcast episode's "
        "title and date and the newest article's title and date; the Case "
        "Studies featured vendors and the ratings counts on the NinjaOne and "
        "Google Cloud Platform product pages; the newest Blog post's title "
        "and date; what For Vendors offers; the Create page's invitation; "
        "the Support page's fastest way to get help; the footer's "
        "headquarters street address; and how many projects the "
        "file-compression search returns. (3) Dates MUST stay attached to "
        "the podcast, article, or blog item they came from, and the two "
        "product ratings counts MUST stay attached to the named product. An "
        "empty answer is a FAIL. FAIL if one shared date is reused for a "
        "different item, or if the two ratings counts are swapped."
    ),
    20: (
        "FACT CHECKPOINTS: (1) The agent MUST browse the Business Software "
        "ERP category, open both products' business pages, search the open "
        "source directory for erp sorted by Rating, and open the first "
        "result's project, Reviews, and Support pages plus the second "
        "result's project page. (2) The answer MUST list every ERP product "
        "with its rating and ratings count, both business-page descriptions, "
        "the search result count, the first result's summary, license, "
        "weekly downloads, last update, registered date, average rating, "
        "review count, and Support recommendation, and the second result's "
        "registered date. (3) Business-directory ratings MUST stay paired "
        "with the correct product, and the first result's project rating "
        "MUST not be substituted for its business-directory rating. An empty "
        "answer is a FAIL. FAIL if the two products' ratings or counts are "
        "swapped, or if the two registered dates are swapped."
    ),
}


def main() -> None:
    lines = TASKS.read_text(encoding="utf-8").splitlines()
    out_lines = []
    for line in lines:
        row = json.loads(line)
        n = int(row["id"].split("--")[1])
        assert set(row) == set(KEY_ORDER), sorted(row)
        row["judge_rubric"] = RUBRICS[n]
        row["verifier_path"] = f"sites/sourceforge/verify/verify_{n}.py"
        ordered = {key: row[key] for key in KEY_ORDER}
        out_lines.append(json.dumps(ordered, ensure_ascii=False, separators=(", ", ": ")))
    TASKS.write_text("\n".join(out_lines) + "\n", encoding="utf-8")
    print(f"rewrote judge_rubric on {len(out_lines)} tasks")


if __name__ == "__main__":
    main()
