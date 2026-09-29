#!/usr/bin/env python3
"""Deepen the 10 tasks the review found below the >=15 honest-step standard
(review MAJOR-2), keeping every frozen verifier fact a strict superset.

Each deepened row keeps its id/web/web_name/upstream_url and only rewrites
`ques`. The other 10 rows stay byte-identical. Word budget <= 100 per row,
goal-style wording (no mechanical step-by-step instructions), and every new
asked fact is deterministic against the frozen seed (verified in the fix
receipt's fact table).
"""
import json
import pathlib
import re

TASKS = pathlib.Path(__file__).resolve().parent.parent / "tasks.jsonl"

DEEPENED = {
    # T5 (was 11): census of the city-pass category + cheapest-vs-best-rated
    # comparison + best-rated-experience leg + booking. Frozen facts kept:
    # Go City Orlando Explorer Pass, 4.0, 1 review, highlights, 90-day
    # validity, $128 total, 2026-10-06/2-guest DB row.
    "Trip.com--5": (
        "I'll be in Orlando on 6 October with a friend and want a city pass under $70 per person. "
        "On the Orlando experiences page, filter to city passes and tell me how many are listed and "
        "which is cheapest, with its name and price. Then book the best-rated pass under $70 for two "
        "guests on 6 October. Report its rating, review count and booked count, the two most important "
        "things its highlights promise, and its validity window. Also tell me the highest-rated Orlando "
        "experience of any kind and its rating. Lead traveller: Pat Kim, pat.kim@example.com."
    ),
    # T6 (was 9): full account audit + wishlist + coupons + a rebooking price
    # check on the flight's route before cancelling. Frozen facts kept: 480
    # coins, Harrah's, 16:00 check-in, SFO route, 22:15 outbound, TFALICE1,
    # cancelled/confirmed statuses, flight_bookings-only DB delta.
    "Trip.com--6": (
        "Sign in as Alice Johnson (alice.j@test.com, password TestPass123!). I have a confirmed hotel "
        "stay and a round-trip flight. Report my Trip Coins balance, both bookings' references and "
        "totals, the stay's hotel and its check-in time, and the flight's route, outbound time and "
        "return departure time. Tell me how many hotels my wishlist holds and the priciest one's "
        "nightly rate, and the flights promo code's minimum spend from my coupons page. Check what a "
        "nonstop round trip on the flight's route costs, then cancel the more expensive booking and "
        "report its reference and the status shown for both bookings afterwards."
    ),
    # T9 (was 11): guide leg + two-candidate comparison + booking-form price
    # breakdown. Frozen facts kept: Motto by Hilton, 8.7, 714 reviews, the two
    # review tags, Flex Room With Wall Bed $202, queen bed, breakfast,
    # 11:59 PM Oct 1 deadline, read-only DB.
    "Trip.com--9": (
        "I'm choosing a New York hotel for a work trip on 20 October and need parking. Check the New "
        "York weekend guide: how much lower are Jersey City and Newark rates? Then find the hotels "
        "with more than 500 reviews and parking available, rank them by guest score, and report both "
        "names and scores. For the higher-scored one, report its two review tags and its cheapest "
        "room's price, bed type, breakfast inclusion and free-cancellation deadline, plus the taxes "
        "per night shown on that room's booking form. Report the other hotel's cheapest room name "
        "and price too."
    ),
    # T11 (was 12): two-cheapest comparison + wishlist + coupons. Frozen facts
    # kept: 480 coins, Hyatt Place Miami Airport East, 8.3, room-name tie set,
    # '1 king bed and 1 sofa bed', $105 total, $1.05 coins, read-only DB.
    "Trip.com--11": (
        "Sign in as Carol Davis (carol.d@test.com, password TestPass123!). Check my Trip Coins balance, "
        "then find the two cheapest bookable Miami hotels and report both names, guest scores and "
        "nightly prices. For the cheapest one, report its cheapest room's name, bed type, the total "
        "including taxes for one night 4-5 October, and the Trip Coins that stay would earn. For the "
        "runner-up, report its cheapest room's name and nightly price. Also check my wishlist and "
        "coupons: how many hotels are saved, and which coupon has the highest minimum spend? Don't "
        "book anything."
    ),
    # T13 (was 11): area-filter leg + Strip comparison + booking-form total.
    # Frozen facts kept: Four Queens, Downtown - Fremont Street, 8.7, $104,
    # 11:59 PM Oct 1 deadline, read-only DB.
    "Trip.com--13": (
        "I want to stay in Las Vegas but away from the Strip crowds. Using the area filter, find the "
        "best-rated bookable hotel under $120 a night that is not on the Las Vegas Strip for 13-14 "
        "October, and report its name, area, guest score, star rating and nightly price, plus the "
        "cancellation deadline shown on its cheapest room. Open that room's booking form for those "
        "nights and report the grand total. Then find the best-rated bookable Strip hotel under $120 "
        "and report its name, guest score, nightly price and cheapest room's name. Don't book anything."
    ),
    # T15 (was 7): booking audit + repeat-stay price check + site-search leg +
    # wishlist/coupons. Frozen facts kept: 480 coins, Harrah's, Nov 1, $136,
    # Go City Explorer Pass $121.68, 3 stars, Las Vegas Strip, Room Type
    # Assigned On Arrival $56, 136 coins earned, read-only DB.
    "Trip.com--15": (
        "Sign in as David Kim (david.k@test.com, password TestPass123!). Report my Trip Coins balance "
        "and list every booking with its type, dates and total. Open the hotel booking's hotel page "
        "and report its name, guest score, star rating, area and check-in time, its cheapest room's "
        "name and price, the Trip Coins that booking earned, and that room's total for a repeat "
        "two-night stay 18-20 November. Find the activity I booked via site search and report how "
        "many attractions its highlights let you choose. Check my wishlist and coupons: how many "
        "hotels are saved, and the attractions promo code's minimum spend?"
    ),
    # T16 (was 8): two-room booking-form comparison + one-night leg + a
    # Bellagio cross-check via a second site search. Frozen facts kept: $167
    # nightly, $22 taxes/night, $378 grand total, Room Type Assigned On
    # Arrival, '1 king bed or 2 queen beds', sleeps 2, 11:59 PM Oct 1, 8.6
    # score, 805 reviews, read-only DB.
    "Trip.com--16": (
        "Search for Paris Las Vegas and work out what a two-night stay starting 5 October in its "
        "cheapest room would cost: the nightly rate before tax, taxes and fees per night, and grand "
        "total. Open that room's booking form for 5-7 October to confirm, reporting its name, bed "
        "type, how many guests it sleeps and its free-cancellation deadline. The second-cheapest "
        "room: report its name and grand total for the same nights. Also report the cheapest room's "
        "one-night total for 5-6 October, the hotel's guest score and review count, and the nightly "
        "rate a site search shows for the Bellagio."
    ),
    # T17 (was 10): category census via the filter + most-booked comparison +
    # validity. Frozen facts kept: 4 categories, 35 total, Hung Fook Tong
    # $1.15, Top-Rated Hong Kong Tour, 27 reviews, 610 booked, $153.04 total,
    # 12-Oct/2-guest DB row.
    "Trip.com--17": (
        "Browse things to do in Hong Kong and list every category with at least one activity, use the "
        "category filter to count how many experiences are tours, plus the total number listed. Name "
        "the cheapest one with its price. Find the two most-booked experiences: report both names and "
        "booked counts. Open the most-booked one's page and report its price, review count and "
        "package validity; open the second most-booked's page too and report its package validity. "
        "Then book the most-booked for two people on 12 October. Lead traveller: Leo Ng, "
        "leo.ng@example.com. Report the total paid and booking reference."
    ),
    # T18 (was 12, BLOCKED): Shanghai census + banquet facts + the 3-guest
    # booking the form used to drop. Frozen facts kept: Shanghai imperial
    # banquet, 5.0, Shuyanfu + taste-buds highlights, $48.27 total (now
    # actually recordable: 3 guests on 2026-10-12).
    "Trip.com--18": (
        "I'll be in Shanghai on 12 October with two friends. Find the highest-rated Shanghai activity "
        "that is neither a city pass nor a tour. Report how many Shanghai experiences are listed in "
        "total, how many are in the Activities category, and how many share that top rating. Open the "
        "top one's page and report the two top things its highlights section promises, its review "
        "count, how many people have booked it and its package's validity window. Book it for all "
        "three of us for that date. Lead traveller: Wei Chen, wei.chen@example.com. Report the "
        "activity's name, rating and total paid."
    ),
    # T19 (was 13): guide follow-up + two-cheapest comparison + booking-form
    # total. Frozen facts kept: 11:59 PM deadline, one-to-three-days window,
    # Harrah's, 8.4, 536 reviews, 11:59 PM Oct 1 room deadline, read-only DB.
    "Trip.com--19": (
        "Use the site search to find the guide about free cancellation and report the deadline it "
        "says refundable rates commonly allow and what happens if you cancel after it. Then find the "
        "two cheapest bookable Las Vegas hotels under $60 a night for 20-21 October: report both "
        "names, guest scores and review counts, and the runner-up's cheapest room name. For the "
        "cheapest one, also report its area, whether parking is listed among its amenities, the "
        "cancellation deadline shown on its cheapest room, and that room's total for those nights "
        "from its booking form."
    ),
}


def main():
    rows = [json.loads(l) for l in TASKS.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 20
    changed = 0
    for row in rows:
        new = DEEPENED.get(row["id"])
        if new is None:
            continue
        words = len(re.findall(r"\S+", new))
        assert words <= 100, (row["id"], words)
        row["ques"] = new
        changed += 1
    assert changed == 10, changed
    out = "".join(json.dumps(r, ensure_ascii=False, separators=(", ", ": ")) + "\n"
                  for r in rows)
    TASKS.write_text(out, encoding="utf-8")
    # report word counts
    for row in rows:
        if row["id"] in DEEPENED:
            print(row["id"], len(re.findall(r"\S+", row["ques"])), "words")


if __name__ == "__main__":
    main()
