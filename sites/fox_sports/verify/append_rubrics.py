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
    "FOX Sports--0":
        "FACT CHECKPOINTS: (1) The trajectory MUST open the NFL standings and report "
        "which team leads the AFC West and its record exactly as shown. (2) The "
        "trajectory MUST open that team's page and report its next opponent and the "
        "point spread, then open its roster and report the college of the tallest "
        "player listed on offense. (3) The trajectory MUST log in as the named "
        "benchmark account with the given password, follow that next opponent and that "
        "player, and report how many teams the account follows in total on the "
        "favorites page. Stateful task: exactly those two favorite writes may change "
        "the database. An answer without the matching navigation trail is a FAIL.",
    "FOX Sports--1":
        "FACT CHECKPOINTS: (1) The trajectory MUST open the NFL scores, find the week "
        "the Chiefs beat the Dolphins 24-10, open that boxscore and report the venue "
        "and the attendance. (2) The trajectory MUST open the Chiefs' schedule page, "
        "report the total line for their next game, then open that game and report the "
        "passing-yards leader for each side as displayed in the Team Leaders table and "
        "which network broadcasts it. (3) The trajectory MUST open the home team's page "
        " and report its record, then open the betting hub's NFL page and report the "
        "spread listed for that game. (4) The trajectory MUST log in as the named "
        "benchmark account, follow the Dolphins, and report how many teams the account "
        "follows in total. Stateful task: exactly that one favorite write may change "
        "the database. An answer without the matching navigation trail is a FAIL.",
    "FOX Sports--2":
        "FACT CHECKPOINTS: (1) The trajectory MUST open the Week 4 Steelers-Browns game "
        " page and report the spread, the total, and the away team's passing-yards team "
        " leader with his yardage. (2) The trajectory MUST open the Steelers roster and "
        " report the college of the tallest tight end. (3) The trajectory MUST create a "
        " new account with the given name and email, follow the Steelers, that tight "
        "end, and the Browns, and report how many favorites the new account has and the "
        " Browns' record. Stateful task: the new account row and exactly those three "
        "favorite writes may change the database. An answer without the matching "
        "navigation trail is a FAIL.",
    "FOX Sports--3":
        "FACT CHECKPOINTS: (1) The trajectory MUST open the NFL schedule and report how "
        " many Week 4 games are listed and how many air on CBS. (2) The trajectory MUST "
        " open the Cowboys-Texans game and report its venue, the over/under total, and "
        "which team the spread favors. (3) The trajectory MUST open the favored team's "
        "page and report its record and the headline of its most recent player-news "
        "item, then open the other team's page and report its record. (4) The "
        "trajectory MUST log in as the named benchmark account, follow the favored "
        "team, search for its quarterback C.J. Stroud, follow him, and report how many "
        "teams and players the account follows in total. Stateful task: exactly those "
        "two favorite writes may change the database. An answer without the matching "
        "navigation trail is a FAIL.",
    "FOX Sports--4":
        "FACT CHECKPOINTS: (1) The trajectory MUST open the NFL player stats page and "
        "report the league's passing-yards leader with his yardage and the sacks leader "
        " with his team. (2) The trajectory MUST open the passing-yards leader's player "
        " page and report his position and college, then his team's page and report its "
        " record and next opponent. (3) The trajectory MUST open the sacks leader's "
        "player page and report his jersey number, then his team's page and report its "
        "record. (4) The trajectory MUST report, from the standings, each of those "
        "teams' division and rank. (5) The trajectory MUST log in as the named "
        "benchmark account, follow both leaders, and report the account's total number "
        "of favorites. Stateful task: exactly those two favorite writes may change the "
        "database. An answer without the matching navigation trail is a FAIL.",
    "FOX Sports--5":
        "FACT CHECKPOINTS: (1) The trajectory MUST open the NFL standings and list all "
        "five undefeated teams. (2) The trajectory MUST open the NFC West one's page "
        "and report its next opponent and the point spread, then search for that "
        "opponent and report the headline of its most recent player-news item. (3) The "
        "trajectory MUST log in as the named benchmark account, follow the undefeated "
        "team, and report the account's total number of favorites. (4) The trajectory "
        "MUST open the power rankings story from the NFL news hub and report where it "
        "ranks the Dolphins and their Super Bowl odds. Stateful task: exactly that one "
        "favorite write may change the database. An answer without the matching "
        "navigation trail is a FAIL.",
    "FOX Sports--6":
        "FACT CHECKPOINTS: (1) The trajectory MUST open the MLB standings and report "
        "which AL East team clinched the division, its record and home record, and the "
        "second-place team's games-behind. (2) The trajectory MUST open the clinched "
        "team's page and report its record and streak. (3) The trajectory MUST open the "
        " wild-card Game 1 between the Braves and Phillies and report the final score, "
        "the venue, and whether over bettors won or lost, then open the Braves' page "
        "and report their record. (4) The trajectory MUST open the series' Game 2 and "
        "Game 3 pages and report each start time and network. (5) The trajectory MUST "
        "log in as the named benchmark account, follow the Phillies and the "
        "second-place team, and report how many teams the account follows. Stateful "
        "task: exactly those two favorite writes may change the database. An answer "
        "without the matching navigation trail is a FAIL.",
    "FOX Sports--7":
        "FACT CHECKPOINTS: (1) The trajectory MUST open the AL wild-card game the White "
        " Sox won in Houston and report the final score, the winning pitcher, and the "
        "venue. (2) The trajectory MUST open both teams' pages from that boxscore and "
        "report each record, and report from the AL West standings where the home team "
        "finished. (3) The trajectory MUST open the series' Game 2 and Game 3 pages and "
        " report the day and time each starts, the network carrying Game 3, its "
        "headline preview, and the recap headline of Game 1. (4) The trajectory MUST "
        "log in as the named benchmark account, follow the Astros and the White Sox, "
        "and report how many teams the account follows after that. Stateful task: "
        "exactly those two favorite writes may change the database. An answer without "
        "the matching navigation trail is a FAIL.",
    "FOX Sports--8":
        "FACT CHECKPOINTS: (1) The trajectory MUST open the College Football standings "
        "and report the top three teams with their records, how many first-place votes "
        "the No. 1 team received, and which ranked team moved up two spots to No. 4. "
        "(2) The trajectory MUST open the top four teams' pages and report each next "
        "opponent and the No. 4 team's point spread, then the No. 4 team's schedule and "
        " its next game's kickoff time. (3) The trajectory MUST log in as the named "
        "benchmark account, follow the No. 2 and No. 4 teams, and report how many teams "
        " the account follows in total. Stateful task: exactly those two favorite "
        "writes may change the database. An answer without the matching navigation "
        "trail is a FAIL.",
    "FOX Sports--9":
        "FACT CHECKPOINTS: (1) The trajectory MUST open the College Football scores, "
        "find where Notre Dame plays its next game, open that game's page, and report "
        "the spread and the venue, plus Notre Dame's record from the poll. (2) The "
        "trajectory MUST find the most recent final involving USC, open that boxscore, "
        "and report the final score and the venue. (3) The trajectory MUST search for "
        "USC and report what kinds of results appear. (4) The trajectory MUST log in as "
        " the named benchmark account, follow both USC and Notre Dame's next opponent, "
        "and report the account's total number of favorites. Stateful task: exactly "
        "those two favorite writes may change the database. An answer without the "
        "matching navigation trail is a FAIL.",
    "FOX Sports--10":
        "FACT CHECKPOINTS: (1) The trajectory MUST open The Herd's show page and report "
        " the title of its most recent episode and how long ago it was posted, plus how "
        " many episodes are listed in total. (2) The trajectory MUST open First Things "
        "First and report its newest episode title. (3) The trajectory MUST open Colin "
        "Cowherd's personality page and report the title of his most recent video. (4) "
        "The trajectory MUST log in as the named benchmark account, follow both shows, "
        "and report the account's total favorites count. Stateful task: exactly those "
        "two favorite writes may change the database. An answer without the matching "
        "navigation trail is a FAIL.",
    "FOX Sports--11":
        "FACT CHECKPOINTS: (1) The trajectory MUST open Tom Brady's personality page "
        "and report his role and the title of his most recent video. (2) The trajectory "
        " MUST open the FOX NFL Sunday show page and report how many episodes it lists "
        "and the title of its newest one. (3) The trajectory MUST search the site for "
        "'brady', report how many results appear and what kinds they are, then open the "
        " top result and report what page it lands on. (4) The trajectory MUST log in "
        "as the named benchmark account, follow Tom Brady, and report how many "
        "personalities the account follows. Stateful task: exactly that one favorite "
        "write may change the database. An answer without the matching navigation trail "
        " is a FAIL.",
    "FOX Sports--12":
        "FACT CHECKPOINTS: (1) The trajectory MUST open the betting hub, open the "
        "Cardinals-Giants game with the 44.5 total, and report its spread and kickoff "
        "time. (2) The trajectory MUST log in as the named benchmark account, follow "
        "both the Cardinals and the Giants, and report how many teams the account "
        "follows in total. (3) The trajectory MUST open the NFL news hub's story about "
        "Week 4 offensive player of the year odds, report the favored player in its "
        "headline, then open the newest related story there and report its title. (4) "
        "The trajectory MUST open the MLB betting page and report how many games are "
        "listed and the Phillies-Braves Game 3 date. Stateful task: exactly those two "
        "favorite writes may change the database. An answer without the matching "
        "navigation trail is a FAIL.",
    "FOX Sports--13":
        "FACT CHECKPOINTS: (1) The trajectory MUST log in as the named benchmark "
        "account and enter the NFL Week 3 Pick 6 contest. (2) The trajectory MUST pick "
        "a winner for all six matchups, submit the entry, and report the graded score "
        "shown on the entry page — the reported score MUST match the entry saved in the "
        " database. (3) The trajectory MUST open the leaderboard and report the highest "
        " score on the board, how many entries there are, and which matchup Question 3 "
        "covers. Stateful task: only the account's own contest entry may change. An "
        "answer without the matching navigation trail is a FAIL.",
    "FOX Sports--14":
        "FACT CHECKPOINTS: (1) The trajectory MUST log in as the named benchmark "
        "account and open the NFL Week 3 Pick 6 contest. (2) The trajectory MUST pick "
        "the home team for questions 1, 3 and 5 and the away team for questions 2, 4 "
        "and 6, submit, and report the graded score and how many questions it missed. "
        "(3) The trajectory MUST open its entry page and report the correct pick for "
        "the first question it missed, then open that matchup's page and report its "
        "venue and spread. (4) The trajectory MUST report the entry deadline shown on "
        "the contest page. Stateful task: the account's Super 6 entry row (picks + "
        "graded score) may change and nothing else. An answer whose reported score "
        "contradicts its saved picks is a FAIL.",
    "FOX Sports--15":
        "FACT CHECKPOINTS: (1) The trajectory MUST create a new FOX Sports account with "
        " the given name, email and a password of at least 8 characters. (2) The "
        "trajectory MUST follow the Tampa Bay Rays, the Texas Longhorns and the show "
        "Big Noon Kickoff, then log out and sign back in. (3) The trajectory MUST open "
        "its favorites and report the Rays' record, the Longhorns' record, and the "
        "number of favorites on the page, then unfollow the Longhorns and report the "
        "new total. Stateful task: the new account row and exactly the surviving two "
        "favorite writes may change the database. An answer without the matching "
        "navigation trail is a FAIL.",
    "FOX Sports--16":
        "FACT CHECKPOINTS: (1) The trajectory MUST search the site for 'wild card' and "
        "report how many stories and how many games appear in the results. (2) The "
        "trajectory MUST open the story about wild-card power rankings and report how "
        "many teams it says kick off the playoffs and the date it was published. (3) "
        "The trajectory MUST search again for 'Larson' and report which kinds of "
        "results appear, then open the NASCAR page and report the points leader and his "
        " win total. (4) The trajectory MUST log in as the named benchmark account, "
        "follow the AL East champion from the MLB standings, and report how many teams "
        "the account follows. Stateful task: exactly that one favorite write may change "
        " the database. An answer without the matching navigation trail is a FAIL.",
    "FOX Sports--17":
        "FACT CHECKPOINTS: (1) The trajectory MUST open the NASCAR page and report the "
        "top two drivers with their point totals, the name and track of the next race, "
        "and which network airs it. (2) The trajectory MUST switch to the UFC page and "
        "report the winner of the most recent event's main result, where it took place, "
        " and the winner of the event before it. (3) The trajectory MUST log in as the "
        "named benchmark account, follow the Chiefs and their quarterback Patrick "
        "Mahomes, then from the roster follow tight end Travis Kelce and defensive end "
        "George Karlaftis, and report how many teams and players the account follows in "
        " total. Stateful task: exactly those four favorite writes may change the "
        "database. An answer without the matching navigation trail is a FAIL.",
    "FOX Sports--18":
        "FACT CHECKPOINTS: (1) The trajectory MUST open the news story about the Giants "
        " trading for J.J. McCarthy and report what it says about McCarthy's chances of "
        " replacing Jaxson Dart long-term, plus its publish date. (2) The trajectory "
        "MUST report from the NFL news hub how many stories are listed, then open the "
        "story about plays that stood out in Week 3 and report the two quarterbacks its "
        " opening paragraph names and what it calls Herbert's play. (3) The trajectory "
        "MUST report the source shown on the most recent story in the hub. (4) The "
        "trajectory MUST log in as the named benchmark account, follow the Giants, then "
        " from the roster follow quarterback J.J. McCarthy, and report how many teams "
        "and players the account follows. Stateful task: exactly those two favorite "
        "writes may change the database. An answer without the matching navigation "
        "trail is a FAIL.",
    "FOX Sports--19":
        "FACT CHECKPOINTS: (1) The trajectory MUST find the MLB team that won 98 games "
        "and report its division and home record. (2) The trajectory MUST open its "
        "schedule and report the result of its most recent final game, then open that "
        "game's boxscore and report the venue and the recap headline, and open the "
        "winning team's page and report its record. (3) The trajectory MUST search for "
        "the 98-win team and report what kinds of results appear. (4) The trajectory "
        "MUST log in as the named benchmark account, follow that team and the winning "
        "team, and report how many players and teams the account follows in total. "
        "Stateful task: exactly those two favorite writes may change the database. An "
        "answer without the matching navigation trail is a FAIL.",
}


def main():
    path = Path(sys.argv[1] if len(sys.argv) > 1 else
                Path(__file__).resolve().parent.parent / "tasks.jsonl")
    lines = path.read_text().splitlines()
    out = []
    changed = 0
    for line in lines:
        if not line.strip():
            out.append(line)
            continue
        row = json.loads(line)
        if row.get("verifier_path"):
            out.append(line)
            continue
        n = row["id"].split("--")[-1]
        assert '"answer' not in line, "tasks.jsonl must never carry answers"
        assert line.rstrip().endswith("}"), "unexpected serialization"
        new = (line.rstrip()[:-1] + ', "verifier_path": '
               + json.dumps(f"sites/fox_sports/verify/verify_{n}.py")
               + ', "judge_rubric": ' + json.dumps(RUBRICS[row["id"]]) + "}")
        assert json.loads(new)["ques"] == row["ques"]
        assert new.startswith(line[:line.rindex("}")])
        out.append(new)
        changed += 1
    path.write_text("\n".join(out) + "\n")
    print(f"appended verifier_path + judge_rubric to {changed} rows")


if __name__ == "__main__":
    main()
