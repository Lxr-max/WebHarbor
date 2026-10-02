#!/usr/bin/env python3
"""append_rubrics.py — append verifier_path + judge_rubric to ../tasks.jsonl.

The five contributor keys stay byte-identical (each output row is the
original line with the two keys appended); no ``answer`` key is ever
written. The rubrics are pure English grading rules with no ground-truth
anchors (the answers live only in the frozen verifiers). Idempotent.

Run: python3 append_rubrics.py
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
TASKS = HERE.parent / "tasks.jsonl"

# ---------------------------------------------------------------------------
# Judge rubrics: pure rules, no answer values. Every rubric states the
# checkpoints the agent must open and the facts it must report exactly as
# the opened pages show them.
# ---------------------------------------------------------------------------
RUBRICS = {
"Disney--0":
 "FACT CHECKPOINTS: Open All Movies, filter to the Now on Disney+ status and report the "
 "count from the page's own count label, sort by title A-Z and open the first result to "
 "report its rating and runtime. Go back, switch the status filter to Coming Soon and "
 "report the new count, open the alphabetically first Coming Soon movie and report its "
 "release date. Log in as alice.j@test.com / TestPass123!, add that movie to favorites "
 "from its detail page, open the favorites page and report Alice's total favorites "
 "count. PASS requires every count and on-page field exactly as shown. FAIL on any "
 "wrong count, wrong movie, wrong rating/runtime/release date or an empty answer.",
"Disney--1":
 "FACT CHECKPOINTS: Create a new account (name Moana Fan, email moana.fan@test.com, "
 "password of at least 8 characters). On All Movies keep only Coming Soon and report "
 "the count, narrow to the Animation genre and report the count, sort by title A-Z and "
 "open the first result to report its release date and rating. Add it to favorites, log "
 "out, log back in, open the favorites page and report the saved movie's title and the "
 "total number of favorites. PASS requires every count and field exactly as the pages "
 "show them. FAIL on any wrong count, wrong movie or an empty answer.",
"Disney--2":
 "FACT CHECKPOINTS: On All Movies search for 'star' and report the matching movie count. "
 "Clear the search, keep Coming Soon plus Science Fiction and report the count, sort by "
 "title and open the first result to report its release date. Go back, clear the status "
 "filter, keep Science Fiction, sort by release date and open the first result to report "
 "its rating and release date. Sort by title instead and open the first Science Fiction "
 "movie to report its rating and one cast member. PASS requires every count and on-page "
 "field exactly as shown. FAIL on any wrong count, wrong movie, wrong rating or an empty "
 "answer.",
"Disney--3":
 "FACT CHECKPOINTS: On the Disney Shows page keep only Animation and report the count, "
 "keep only Science Fiction instead and report that count, search for 'star' and report "
 "the count, open the first match and report its release year. Go back, clear the "
 "search and the genre filter, open the newer DuckTales series and report its rating "
 "and release year, then open Big Hero 6: The Series. Log in as bob.c@test.com / "
 "TestPass123!, add Big Hero 6: The Series to favorites and report how many favorites "
 "Bob has in total and how many of them are shows. PASS requires every count and field "
 "exactly as the opened pages show them. FAIL on any wrong count or wrong rating.",
"Disney--4":
 "FACT CHECKPOINTS: Search the site for 'mickey' and report how many shows and how many "
 "parks & entertainment results the search page lists. Open the Disney Mickey Mouse "
 "show and report its rating. From the Shows page keep only the Variety genre, report "
 "the count, open the first one and report its release year. Clear the genre filter and "
 "report the total number of shows in the catalog. Log in as carol.d@test.com / "
 "TestPass123!, add the Mickey Mouse show to favorites and report Carol's total "
 "favorites count. Search shows for 'duck' and report how many match. PASS requires "
 "every count exactly as the opened pages show them. FAIL on any wrong count or "
 "invented values.",
"Disney--5":
 "FACT CHECKPOINTS: On the Shows page report the full A-Z catalog count, keep only "
 "Comedy and report the count, keep only Fantasy instead and report that count, open "
 "the first Fantasy show by title and report its release year. Log in as bob.c@test.com "
 "/ TestPass123! and add that show to favorites. Search shows for 'duck' and report how "
 "many match, open DuckTales from the results and report its rating. Keep only Comedy "
 "again, sort by title and open the first Comedy show to report its rating. PASS "
 "requires every count and rating exactly as shown. FAIL on any wrong count, wrong "
 "show or an empty answer.",
"Disney--6":
 "FACT CHECKPOINTS: On the Attractions & Entertainment list filter to Magic Kingdom Park "
 "and Thrill Rides and report the count, add the 40-inch height filter and report the "
 "count, sort by name and open the first result to report its height requirement and "
 "one of its interests. Go back, clear the height filter and report the count again, "
 "filter heights to 48 inches or taller and report how many results remain, open the "
 "remaining result and report its name. Keep only Entertainment for Magic Kingdom Park "
 "and report how many entertainment items the park lists. PASS requires every count "
 "and on-page field exactly as shown. FAIL on any wrong count or wrong attraction.",
"Disney--7":
 "FACT CHECKPOINTS: On the Attractions & Entertainment page keep only Entertainment "
 "with the Character Experiences interest and report the count, narrow to Magic Kingdom "
 "Park and report the count, sort by name and open the first result to report its "
 "name. Go back, clear the park filter, switch the interest to Fireworks and report how "
 "many fireworks events exist across all parks. Open the Heartbeat of Freedom fireworks "
 "show at EPCOT, log in as alice.j@test.com / TestPass123!, add it to favorites and "
 "report Alice's total favorites count. PASS requires every count and name exactly as "
 "the opened pages show them. FAIL on any wrong count or an empty answer.",
"Disney--8":
 "FACT CHECKPOINTS: On the Attractions & Entertainment page keep only Attractions and "
 "report the total, add the 38-inch height filter and report the count, change it to 44 "
 "inches and report the count, then 48 inches and report the count. Sort by height "
 "requirement and report the park of the first result and the park of the last result "
 "on the first page. Clear the height filter and report the total attractions count "
 "again, keep only the Big Drops interest and report how many big-drop attractions "
 "exist. PASS requires every count and park exactly as shown. FAIL on any wrong count "
 "or wrong park.",
"Disney--9":
 "FACT CHECKPOINTS: From Attractions & Entertainment filter to Magic Kingdom Park and "
 "Thrill Rides, open Seven Dwarfs Mine Train and report its height requirement and the "
 "heading of its first description section. Go back, keep the Dark interest for Magic "
 "Kingdom, open Pirates of the Caribbean, open one of its Related Activities and report "
 "that item's name and park. Switch the park filter to EPCOT and the interest to Slow "
 "Rides and report how many remain. Open Soarin' Around the World, log in as "
 "dana.k@test.com / TestPass123!, add it to your favorites and report Dana's total "
 "favorites count. PASS requires every count and on-page field exactly as shown. FAIL "
 "on any wrong value.",
"Disney--10":
 "FACT CHECKPOINTS: In the Disney Store open the Toys collection, sort by price high to "
 "low and report how many products are listed. Open the most expensive product and "
 "report its price and rating, add 2 to your bag, view the bag and report the line "
 "total and bag total. Change the quantity to 1 and report the new line total and bag "
 "total. Check out as a guest with the email toy.buyer@example.com and any name and "
 "address, and report the order total and confirmation code. Open the Toys collection "
 "again, keep only Action Figures and report the count. PASS requires every count, "
 "price and code exactly as the pages show them. FAIL on any wrong total or invented "
 "code.",
"Disney--11":
 "FACT CHECKPOINTS: Open the Sale collection and report how many products are on sale. "
 "Keep only Mickey Mouse character items and report the count. Sort by rating, open the "
 "top-rated product and report its price and its rating. Add one to your bag and report "
 "the bag total. Open the Accessories collection, keep only Bags & Wallets and report "
 "the count. Open the first result, report its price and review count, add one to your "
 "bag and report the new bag total. PASS requires every count and value exactly as the "
 "pages show them. FAIL on invented values or wrong totals.",
"Disney--12":
 "FACT CHECKPOINTS: In the Clothes collection keep only items for Adults and report the "
 "count. Sort by price low to high and open the cheapest item: report its price, "
 "rating, and one bullet from its bare necessities section. Set the quantity to 3 and "
 "add it to your bag. Open the Toys collection, keep only Plush, sort by price low to "
 "high, open the cheapest plush and add 1 to your bag. Report the combined bag total. "
 "PASS requires every count, price and bullet exactly as the opened pages show them. "
 "FAIL on any wrong price or wrong total.",
"Disney--13":
 "FACT CHECKPOINTS: Search the site for 'plush' and report how many products the search "
 "page's Shop section lists. Open the first product, report its price and add 1 to your "
 "bag. Search for 'tote', open the first product and add 2 to your bag. Open the bag, "
 "remove the plush by setting its quantity to 0, and report the new bag total and how "
 "many items remain. Check out with the email shop.compare@example.com and any name and "
 "address, and report the confirmation code and order total. PASS requires every value "
 "exactly as the pages show them. FAIL on invented values.",
"Disney--14":
 "FACT CHECKPOINTS: Open the Disney On Ice schedule, keep only the Magic in the Stars "
 "shows and report how many events remain. Clear the show filter, search the schedule "
 "for 'CA' and report how many California stops appear. Clear the search, sort by "
 "city, open the first event and report its venue and how many performances it lists. "
 "Book 2 tickets for its first performance using the email ice.first@example.com and "
 "any name, and report the confirmation code and the total. PASS requires every count, "
 "venue, code and total exactly as the opened pages show them. FAIL on any wrong count "
 "or invented code.",
"Disney--15":
 "FACT CHECKPOINTS: Search the Disney On Ice schedule for 'Kent' and open the Kent, WA "
 "event: report its venue and date range. Book 3 tickets for its Saturday 11:00 am "
 "performance using your own name and the email skate.fan@example.com, and report the "
 "confirmation code and total. Return to the schedule, keep only Jump In! shows and "
 "report how many stops that tour has. Sort by city, open the first event and report its "
 "city and venue. PASS requires every venue, count, code and total exactly as shown. "
 "FAIL on any wrong venue or invented code.",
"Disney--16":
 "FACT CHECKPOINTS: Open Live Shows and report how many Broadway musicals are listed. "
 "Open the Disney On Ice schedule and report the event total. Keep only Find Your Hero "
 "shows and report the count. Clear the show filter, search for 'TX' and report how "
 "many Texas stops appear. Sort by city and open the last Texas stop: report its venue "
 "and dates. Book 2 tickets for its November 22, 2026 5:00 pm performance with the "
 "email laredo.ice@example.com and any name, and report the confirmation code and "
 "total. Return to the schedule and report how many stops Magic of Family has. PASS "
 "requires every count, venue, dates, booked performance, code and total exactly as "
 "the opened pages show them. FAIL on any wrong count or invented code.",
"Disney--17":
 "FACT CHECKPOINTS: Create a new Disney account (name Game Player, email "
 "game.player@test.com, a password of at least 8 characters). Open the Games page and "
 "report how many games are listed. Search games for 'disney' and report how many "
 "match. Open Disney Illusion Island and report the first sentence of its description "
 "exactly as the page renders it, then add it to your favorites. Open Disney Villains "
 "Cursed Café and add it to your favorites too. Log out and log back in, open your "
 "favorites page and report both saved titles. PASS requires every count and both "
 "titles exactly as the opened pages show them. FAIL on any wrong count, wrong title "
 "or an empty answer.",
"Disney--18":
 "FACT CHECKPOINTS: Search the site for 'frozen' and report how many movies and how "
 "many parks & entertainment results match. Open the Frozen Ever After attraction and "
 "report its park and height requirement exactly as its page shows them. Return to the "
 "search results, open the top movie result and report its rating and release date. Log "
 "in as dana.k@test.com / TestPass123! and add that movie to your favorites, then "
 "report Dana's total favorites count. Search for 'stitch' and report how many products "
 "match. Open the first product, add 1 to your bag and report the bag total. PASS "
 "requires every count and on-page field exactly as shown. FAIL on any wrong count or "
 "invented values.",
"Disney--19":
 "FACT CHECKPOINTS: Open Parks & Travel and report how many parks are listed and which "
 "one has the most attractions & entertainment. Open that park's attractions list, "
 "keep only Attractions and report the count. Sort by name and open the first result to "
 "report its height requirement exactly as its page shows it. Go back, keep only "
 "Entertainment with the Character Experiences interest for the same park and report "
 "how many remain. Open the first result and report its name, then log in as "
 "carol.d@test.com / TestPass123!, add it to your favorites and report Carol's total "
 "favorites count. PASS requires every count and name exactly as the opened pages show "
 "them. FAIL on any wrong count or wrong park.",
}

VERIFIER = {f"Disney--{n}": f"sites/disney/verify/verify_{n}.py" for n in range(20)}


def main():
    rows = [line for line in TASKS.read_text(encoding="utf-8").splitlines() if line.strip()]
    out = []
    for line in rows:
        row = json.loads(line)
        tid = row["id"]
        if tid not in VERIFIER:
            raise SystemExit(f"unknown task id {tid}")
        if "verifier_path" in row:
            out.append(line)  # idempotent: already appended
            continue
        assert set(row) == {"web_name", "id", "ques", "web", "upstream_url"}, row.keys()
        extended = json.loads(line)
        extended["verifier_path"] = VERIFIER[tid]
        extended["judge_rubric"] = RUBRICS[tid]
        # byte-identical contributor keys + two appended keys
        pieces = line[:-1] + f', "verifier_path": {json.dumps(VERIFIER[tid])}' \
                       f', "judge_rubric": {json.dumps(RUBRICS[tid])}}}'
        assert json.loads(pieces) == extended
        out.append(pieces)
    TASKS.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"append_rubrics: {len(out)} rows written (7-key contract)")


if __name__ == "__main__":
    main()
