#!/usr/bin/env python3
"""append_rubrics.py — attach verifier_path + judge_rubric to tasks.jsonl.

Contract:
- The original five keys (web_name, id, ques, web, upstream_url) keep their
  exact serialized bytes: each output line is the original JSON object with
  the two new keys appended, so the original prefix is byte-identical.
- No answer/ground-truth data leaks into tasks.jsonl; the rubrics are pure
  English rules (FACT CHECKPOINTS naming the pages that must be opened and
  the facts that must be reported, without the values); ground truth stays
  hardcoded in verify/contract.json + verify_N.py.
- Idempotent: lines that already carry verifier_path are left untouched.

Usage: python3 append_rubrics.py [tasks.jsonl]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

RUBRICS = {
    "iclr--0":
        "FACT CHECKPOINTS: (1) The trajectory MUST open the papers browser from "
        "the conference home, search titles for diffusion and report the match "
        "count, then narrow to the Reinforcement Learning -> Deep RL topic and "
        "report the remaining count. (2) The trajectory MUST open the "
        "alphabetically first result and report its poster position and session "
        "exactly as shown. (3) The trajectory MUST return to the diffusion "
        "search, keep only Accept (Oral) decisions, open the first match, and "
        "report its session, its poster position, whether a poster position "
        "shows, the session's time window from the schedule on that session's "
        "day, and the session's paper count. (4) The trajectory MUST log in as "
        "the named benchmark account with the given password, bookmark the "
        "first result it opened, and report the account's bookmark total under "
        "My Stuff. Stateful task: the bookmark write MUST be the only database "
        "change. An answer without the matching navigation trail is a FAIL.",
    "iclr--1":
        "FACT CHECKPOINTS: (1) The trajectory MUST search the papers browser for "
        "titles containing language model and report the match count, then keep "
        "only Accept (Oral) decisions and report how many remain. (2) The "
        "trajectory MUST open the alphabetically first result and report its "
        "session and whether the page shows a talk slot or a poster position. "
        "(3) The trajectory MUST open the schedule on that session's day and "
        "report the session's day and time window. (4) The trajectory MUST log "
        "in as the named benchmark account, bookmark that first paper, and "
        "report the account's bookmark total under My Stuff. Stateful task: the "
        "bookmark write MUST be the only database change. An answer without the "
        "matching navigation trail is a FAIL.",
    "iclr--2":
        "FACT CHECKPOINTS: (1) The trajectory MUST filter the papers browser to "
        "Poster Session 4 Pavilion 4 and report how many papers it holds, sort "
        "by title, open the first result, and report its poster position and the "
        "institution of its first author. (2) The trajectory MUST open the "
        "schedule on that session's day and report the session's time window. "
        "(3) The trajectory MUST filter the papers browser to Poster Session 1 "
        "Pavilion 4, sort by title, and report the first paper's poster "
        "position. (4) The trajectory MUST log in as the named benchmark "
        "account, bookmark that paper, and report the account's total bookmark "
        "count under My Stuff. Stateful task: the bookmark write MUST be the "
        "only database change. An answer without the matching navigation trail "
        "is a FAIL.",
    "iclr--3":
        "FACT CHECKPOINTS: (1) The trajectory MUST open the schedule on Thursday "
        "April 23 and report how many talks Oral Session 1A LLMs and Reasoning "
        "lists plus the titles of its first and last talks. (2) The trajectory "
        "MUST open the first talk's paper and report its decision and room, and "
        "open the last talk's paper and report its talk slot. (3) The trajectory "
        "MUST report Thursday's Poster Session 1 Pavilion 4 window and its "
        "alphabetically first paper's poster position from the session's paper "
        "list. (4) The trajectory MUST log in as the named benchmark account, "
        "bookmark the last talk's paper, and report the account's bookmark "
        "total and saved-event title under My Stuff. (5) The trajectory MUST "
        "switch the schedule to Friday and report the social count and the "
        "earliest start time. Stateful task: the bookmark write MUST be the only "
        "database change. An answer without the matching navigation trail is a "
        "FAIL.",
    "iclr--4":
        "FACT CHECKPOINTS: (1) The trajectory MUST open the workshops hub and "
        "report how many workshops run on Sunday April 26. (2) The trajectory "
        "MUST open the workshop whose title starts with VerifAI-2 and report "
        "its organizers and how many schedule items its program lists. (3) The "
        "trajectory MUST open the AI for Peace workshop and report the time and "
        "title of its first schedule item. (4) The trajectory MUST log in as the "
        "named benchmark account, add the AI for Mechanism Design and Strategic "
        "Decision Making (AIMS) workshop to the schedule, and report the "
        "account's saved-event total under My Stuff. (5) The trajectory MUST "
        "open the Monday schedule and report the workshop count that day, and "
        "report the project-page domain of I Can't Believe It's Not Better from "
        "its workshop page. Stateful task: the schedule save MUST be the only "
        "database change. An answer without the matching navigation trail is a "
        "FAIL.",
    "iclr--5":
        "FACT CHECKPOINTS: (1) The trajectory MUST open the invited talks hub "
        "and report how many talks are listed. (2) The trajectory MUST open "
        "Images of the Hidden Universe and report the speaker and the first "
        "university mentioned in the bio. (3) The trajectory MUST open Marin: "
        "Open Development of Frontier AI and report the speaker, the day, and "
        "the start time. (4) The trajectory MUST open the Thursday 9:00 AM talk "
        "and report its overflow room, and open Learning while developing and "
        "report its speaker. (5) The trajectory MUST log in as the named "
        "benchmark account, add the Marin talk to the schedule, and report how "
        "many events My Schedule shows for the account. Stateful task: the "
        "schedule save MUST be the only database change. An answer without the "
        "matching navigation trail is a FAIL.",
    "iclr--6":
        "FACT CHECKPOINTS: (1) The trajectory MUST use the site search to look "
        "up Susquehanna and report its tier, and look up Marin, open the "
        "matching schedule event, and report its speaker and start time. "
        "(2) The trajectory MUST open the schedule on that talk's day and "
        "report the Poster Session 6 Pavilion 3 window. (3) The trajectory "
        "MUST open the sponsors page and report the Double Diamond names and "
        "the Diamond tier count, then look up Amazon's tier. (4) The "
        "trajectory MUST open the blog, report the newest announcement's "
        "title and date, open it, and report the author line. (5) The "
        "trajectory MUST return to the blog and open the Test of Time "
        "announcement and report its date. (6) The trajectory MUST open the "
        "awards page and report both Test of Time titles. Read-only task: any "
        "database change is a FAIL. An answer without the matching navigation "
        "trail is a FAIL.",    "iclr--7":
        "FACT CHECKPOINTS: (1) The trajectory MUST open the organizers page and "
        "report the General Chair's name and institution, the Program Chair and "
        "Ethics Review Chair counts, and the Cornell Senior Program Chair's "
        "first research area. (2) The trajectory MUST open the awards page and "
        "report the two Outstanding Paper titles and the Honorable Mention's "
        "title and first author. (3) The trajectory MUST open the blog post "
        "announcing the Outstanding Papers and report its author. (4) The "
        "trajectory MUST search the papers for Polar Express, open the first "
        "match (title-sorted first row), and report its session, decision, and "
        "poster position. (5) The trajectory MUST log in as the named "
        "benchmark account, search for Transformers are Inherently Succinct, "
        "bookmark the first match, and report the account's bookmark count. "
        "Stateful task: the bookmark write MUST be the only database change. "
        "An answer without the matching navigation trail is a FAIL.",    "iclr--8":
        "FACT CHECKPOINTS: (1) The trajectory MUST open the awards page and "
        "report the two Outstanding Paper titles with first authors and the two "
        "Test of Time titles and first authors. (2) The trajectory MUST open "
        "the Outstanding Papers post and report the committee chair, and open "
        "the keynotes announcement and report how many keynote talks it "
        "presents and the first's day and time. (3) The trajectory MUST open "
        "the newest blog post and report its title and the submission limit "
        "announced. (4) The trajectory MUST log in as the named benchmark "
        "account, search the papers browser for Transformers are Inherently "
        "Succinct, open the first match (title-sorted first row), and report "
        "its session, poster position, bookmark state, the session's time "
        "window and paper count. Read-only task: any database change is a "
        "FAIL. An answer without the matching navigation trail is a FAIL.",    "iclr--9":
        "FACT CHECKPOINTS: (1) The trajectory MUST open the registration page "
        "and report the price of one guest banquet ticket and the three "
        "affiliation types offered. (2) The trajectory MUST attempt submitting "
        "with Conference Sessions and Workshops plus a second item checked and "
        "report the error message the page shows. (3) The trajectory MUST "
        "submit a valid registration as Full time student with Conference "
        "Sessions and Workshops, two banquet tickets, and no dietary "
        "preference, and report the registration code and the total in USD "
        "exactly as the confirmation page shows. (4) The trajectory MUST log in "
        "as the named benchmark account and report the code and total of the "
        "existing registration under My Stuff. Stateful task: exactly one "
        "registration row MUST be created and its code MUST appear in the "
        "answer. An answer without the matching navigation trail is a FAIL.",
    "iclr--10":
        "FACT CHECKPOINTS: (1) The trajectory MUST create a new profile with the "
        "given name, email, and a password of at least 8 characters. (2) The "
        "trajectory MUST search the papers browser for Escaping Policy "
        "Contraction, open the match, and report its session and poster "
        "position. (3) The trajectory MUST bookmark it, open My Stuff, and "
        "report the bookmark count. (4) The trajectory MUST log out and log "
        "back in with the same account and report how many bookmarked papers "
        "and saved events the account has, plus the decision type shown for the "
        "bookmarked paper. Stateful task: exactly one new user and one bookmark "
        "row MUST be created. An answer without the matching navigation trail "
        "is a FAIL.",
    "iclr--11":
        "FACT CHECKPOINTS: (1) The trajectory MUST open the FAQ and report the "
        "Badge Replacement Policy's first-replacement fee. (2) The trajectory "
        "MUST search the site for luggage, open the conference site result, "
        "and report the lost badge fee and the April 24-27 luggage check "
        "hours. (3) The trajectory MUST open the dates page and report the "
        "2026 dietary preference and registration cancellation deadlines. "
        "(4) The trajectory MUST search the site for policies, open the "
        "oldest matching announcement, and report its title. (5) The "
        "trajectory MUST open the HelpDesk, send a message to the Workshops "
        "topic with the given name, email, subject and a body asking about "
        "Sunday passes, and report the confirmation the page shows. (6) The "
        "trajectory MUST report which HelpDesk topic handles Visa Support and "
        "which handles Press. Stateful task: exactly one HelpDesk message row "
        "MUST be created. An answer without the matching navigation trail is "
        "a FAIL.",    "iclr--12":
        "FACT CHECKPOINTS: (1) The trajectory MUST open the dates page and "
        "report the ICLR 2027 abstract and paper deadlines and final decision "
        "date, plus the 2026 registration deadlines. (2) The trajectory MUST "
        "search the site for Riocentro and report which result types appear. "
        "(3) The trajectory MUST search for Amazon, open the sponsors page, "
        "and report its tier. (4) The trajectory MUST open the conference "
        "site page and report the lost badge fee and luggage hours, open the "
        "FAQ and report the first-time badge replacement fee, and search the "
        "papers browser for Polar Express and report the first match's "
        "decision. (5) The trajectory MUST log in as the named benchmark "
        "account, open My Stuff, and report the registration code, total, and "
        "bookmark count. Read-only task: any database change is a FAIL. An "
        "answer without the matching navigation trail is a FAIL.",    "iclr--13":
        "FACT CHECKPOINTS: (1) The trajectory MUST use the site search for "
        "Riocentro, open the conference site page result, and report the 2027 "
        "conference location and dates. (2) The trajectory MUST search for "
        "Outstanding, open the newest matching announcement, and report its "
        "date and author. (3) The trajectory MUST search for Amazon and report "
        "its sponsor tier. (4) The trajectory MUST search for Jane Street and "
        "report its tier. (5) The trajectory MUST search for VerifAI, open "
        "the matching workshop, and report its day and start time and how "
        "many schedule items it lists. (6) The trajectory MUST search for "
        "Polar Express, open the first match, and report the paper's "
        "decision. Read-only task: any database change is a FAIL. An answer "
        "without the matching navigation trail is a FAIL.",    "iclr--14":
        "FACT CHECKPOINTS: (1) The trajectory MUST open the schedule on "
        "Wednesday April 22 and report what kind of event is listed that day. "
        "(2) The trajectory MUST switch to Sunday April 26, report how many "
        "workshops are listed, open the first one, and report its organizers. "
        "(3) The trajectory MUST switch to Monday April 27, report how many "
        "workshops run, and open I Can't Believe It's Not Better to report its "
        "start time and first schedule item. (4) The trajectory MUST open "
        "Saturday's Town Hall event and report its start time and abstract. (5) "
        "The trajectory MUST log in as the named benchmark account, add the "
        "Town Hall to the schedule, and report the account's saved-event total "
        "and titles under My Stuff. Stateful task: the schedule save MUST be "
        "the only database change. An answer without the matching navigation "
        "trail is a FAIL.",
    "iclr--15":
        "FACT CHECKPOINTS: (1) The trajectory MUST open the papers browser and "
        "report the total number of accepted papers and how many carry the "
        "Accept (Oral) decision. (2) The trajectory MUST filter to Poster "
        "Session 3 Pavilion 3, report how many papers it holds, sort by title, "
        "open the first result, and report its poster position and first "
        "author's institution. (3) The trajectory MUST log in as the named "
        "benchmark account and report how many bookmarks and saved events the "
        "account has under My Stuff. (4) The trajectory MUST add the first "
        "result to the account's bookmarks and report the new total. Stateful "
        "task: the bookmark write MUST be the only database change. An answer "
        "without the matching navigation trail is a FAIL.",
    "iclr--16":
        "FACT CHECKPOINTS: (1) The trajectory MUST open the awards page and the "
        "Outstanding Paper LLMs Get Lost In Multi-Turn Conversation, then find "
        "it in the papers browser by searching its title, open the first "
        "match (title-sorted first row), and report its session, decision, and "
        "poster position. (2) The trajectory MUST report that session's day "
        "and time window from the schedule, and from its paper list report "
        "the alphabetically first paper's poster position. (3) The trajectory "
        "MUST return to the awards page and report the first author of the "
        "other Outstanding Paper and both Test of Time paper titles. (4) The "
        "trajectory MUST log in as the named benchmark account and report how "
        "many events the My Schedule area lists. Read-only task: any database "
        "change is a FAIL. An answer without the matching navigation trail is "
        "a FAIL.",    "iclr--17":
        "FACT CHECKPOINTS: (1) The trajectory MUST log in as the named benchmark "
        "account and report how many bookmarked papers and saved events the "
        "account has under My Stuff, including the saved-event titles. (2) The "
        "trajectory MUST add the workshop AI for Peace to the schedule and "
        "report the new saved-event total. (3) The trajectory MUST remove the "
        "Marin talk from the schedule and report the final saved-event count. "
        "(4) The trajectory MUST search the papers browser for LLMs Get Lost "
        "In Multi-Turn Conversation, open the first match (title-sorted first "
        "row), bookmark it, and report the final bookmark count. Stateful "
        "task: exactly one schedule save added, one schedule save removed, and "
        "one bookmark added MUST be the only database changes. An answer "
        "without the matching navigation trail is a FAIL.",
    "iclr--18":
        "FACT CHECKPOINTS: (1) The trajectory MUST log in as the named benchmark "
        "account and submit a new registration as Academic with the Sunday "
        "Workshop 1 Day Pass, one banquet ticket, and dietary preference Halal, "
        "and report the registration code and total exactly as the confirmation "
        "page shows. (2) The trajectory MUST open My Stuff and report how many "
        "registrations the account now has and the items on the new one. (3) "
        "The trajectory MUST report the exclusivity rule printed on the "
        "registration page about Conference Sessions and Workshops. (4) The "
        "trajectory MUST report which other registrant name and affiliation "
        "appear in Alice's registration under her My Stuff (the registration "
        "history line renders the registrant name and affiliation). Stateful "
        "task: exactly one registration row MUST be created "
        "and its code MUST appear in the answer. An answer without the "
        "matching navigation trail is a FAIL.",
    "iclr--19":
        "FACT CHECKPOINTS: (1) The trajectory MUST open the conference home and "
        "report the conference city and the workshop days in the banner. (2) "
        "The trajectory MUST open the papers browser, search for Personality "
        "Subnetworks, open the match, and report its session and poster "
        "position. (3) The trajectory MUST log in as the named benchmark "
        "account, report whether the paper already appears among the bookmarks, "
        "remove it, and report the new bookmark total. (4) The trajectory MUST "
        "open the schedule on that paper's session day and report the session's "
        "time window and how many papers it holds. (5) The trajectory MUST "
        "report the first talk in the day's first oral session, open that "
        "paper, and report its decision. Stateful task: exactly one bookmark "
        "row MUST be removed and nothing else may change. An answer without "
        "the matching navigation trail is a FAIL.",
}


def main() -> int:
    path = Path(sys.argv[1] if len(sys.argv) > 1 else
                Path(__file__).resolve().parent.parent / "tasks.jsonl")
    out_lines = []
    changed = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            out_lines.append(line)
            continue
        row = json.loads(line)
        if row.get("verifier_path"):
            out_lines.append(line)
            continue
        task_id = row["id"]
        prefix = line[: line.rindex("}")]
        new = (prefix.rstrip() + ', "verifier_path": '
               + json.dumps(f"sites/iclr/verify/verify_{task_id.split('--')[1]}.py")
               + ', "judge_rubric": ' + json.dumps(RUBRICS[task_id]) + "}")
        # byte-identity check: original prefix untouched, JSON still valid
        assert new.startswith(line[: line.rindex("}")]), "prefix bytes changed"
        assert json.loads(new)["ques"] == row["ques"]
        out_lines.append(new)
        changed += 1
    path.write_text("\n".join(out_lines) + "\n", encoding="utf-8")
    print(f"append_rubrics: {changed} rows updated (verifier_path + "
          f"judge_rubric); 5-key prefix bytes untouched")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
