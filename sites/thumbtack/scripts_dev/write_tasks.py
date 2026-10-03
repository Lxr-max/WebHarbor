#!/usr/bin/env python3
"""Write sites/thumbtack/tasks.jsonl (contributor keys only: web_name, id, ques, web, upstream_url)."""
import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
WEB = "http://localhost:40100/"
UP = "https://www.thumbtack.com/"

TASKS = [
    # 1. compare two photographers by hires, save the winner (alice)
    ("Log in with the demo account (email: alice.j@test.com, password: TestPass123!). "
     "I'm choosing between the Seattle wedding photographers Jeshua Frees (Clearline Production) "
     "and Tanner Schmidt. Compare how many Thumbtack hires each of them has, save the one with "
     "more hires to my saved pros, and tell me how many years that pro has been in business "
     "and how many employees they have.",
     ),
    # 2. full deep-clean chain: quotes -> hire cheapest -> review (bob)
    ("Log in with the demo account (email: bob.c@test.com, password: TestPass123!). "
     "My 2-bedroom apartment in zip 98101 needs a deep cleaning before I move out next month. "
     "Request house cleaning quotes for a one-time deep clean of 2 bedrooms and 2 bathrooms, "
     "hire the cheapest pro who responded, and leave them a 5-star review that mentions "
     "\"move-out\".",
     ),
    # 3. wedding budget comparison via cost guides + Everett DJ response time
    ("I'm planning a wedding on a tight budget. Using Thumbtack's cost guides, compare the "
     "national average cost of hiring a wedding DJ with the national average cost of a wedding "
     "photographer, and tell me which service is more expensive and by roughly how much. Then "
     "find the highest-rated DJ based in Everett and tell me how quickly they usually respond.",
     ),
    # 4. Paty review tags + newest review + message about supplies
    ("Log in with the demo account (email: alice.j@test.com, password: TestPass123!). "
     "On Paty House Cleaning's profile, find the word customers mention most often in their "
     "reviews, and check whether that theme also appears in the newest review. Then message "
     "Paty asking whether they bring their own cleaning supplies, and report what their reply "
     "says.",
     ),
    # 5. cancel TV project: cheapest quote + count, then replacement handyman quote
    ("Log in with the demo account (email: alice.j@test.com, password: TestPass123!). "
     "My TV mounting project is on hold — cancel it, but first tell me which pro had quoted the "
     "lowest price and how many quotes the project had received in total. Then start a "
     "replacement request in zip 98033 to hire a handyman for hanging a heavy mirror instead.",
     ),
    # 6. carol moves to Kirkland: profile update + lawn care quote
    ("Log in with the demo account (email: carol.d@test.com, password: TestPass123!). "
     "I've just moved to Kirkland (zip 98033). Update my profile's zip code and address, then "
     "find the highest-rated lawn care professional who serves that area and request a quote "
     "for a weekly mowing service.",
     ),
    # 7. plumber: background-checked + Venmo, save, quote leaky faucet (david)
    ("Log in with the demo account (email: david.k@test.com, password: TestPass123!). "
     "My kitchen faucet has been dripping for a week. Find a plumber who is background checked "
     "and accepts Venmo, save them to my saved pros, and request a quote describing the leaky "
     "faucet.",
     ),
    # 8. registration + furniture assembly quotes
    ("Create a new Thumbtack account (name: Nina Patel, email: nina.p@test.com, password: "
     "NewHome2026!), then request quotes for assembling a large wardrobe and two bookcases in "
     "zip 98101. Tell me how many pros responded and what the cheapest quote was.",
     ),
    # 9. Sunday handymen: find two open Sunday, message the more-reviewed one
    ("Log in with the demo account (email: alice.j@test.com, password: TestPass123!). "
     "I can only be home on Sundays. Find two handymen whose business hours include Sunday, "
     "message the one with more reviews to confirm they can do a Sunday visit, and report "
     "their reply.",
     ),
    # 10. cost guide range + request deep clean + compare to range (bob)
    ("Log in with the demo account (email: bob.c@test.com, password: TestPass123!). "
     "According to Thumbtack's cost guide, what do most people pay for a one-time house "
     "cleaning visit? Then request a deep-cleaning quote for my 3-bedroom, 2-bathroom home in "
     "zip 98101 and tell me whether the cheapest quote falls inside the guide's typical price "
     "range.",
     ),
    # 11. movers cleanup: remove saved movers, report lowest quote, cancel (bob)
    ("Log in with the demo account (email: bob.c@test.com, password: TestPass123!). "
     "I've rented a truck and will move myself after all. Remove the moving companies from my "
     "saved pros, open my pending moving project and tell me which pro quoted the lowest price, "
     "and then cancel that project.",
     ),
    # 12. quinceanera budget: makeup vs DJ guides + Redmond makeup artist
    ("I'm budgeting my daughter's quinceañera. Using Thumbtack's cost guides, compare what a "
     "makeup artist charges with what a DJ charges, and tell me which is more expensive. Then "
     "find the highest-rated Top Pro makeup artist based in Redmond and tell me their exact "
     "rating and which payment methods they accept.",
     ),
    # 13. review for the completed project's hired pro (alice)
    ("Log in with the demo account (email: alice.j@test.com, password: TestPass123!). "
     "My house cleaning project is finished but I never left a review. Leave the pro I hired a "
     "5-star review saying they were thorough, including the word \"spotless\". Then open their "
     "profile and confirm your review appears as the most recent one.",
     ),
    # 14. read supplies thread + ask a different cleaner + report both (alice)
    ("Log in with the demo account (email: alice.j@test.com, password: TestPass123!). "
     "Read my existing message thread about cleaning supplies and tell me exactly what the pro "
     "said they bring. Then ask a different house cleaner the same question and report both "
     "answers.",
     ),
    # 15. exterminator quotes -> hire the responder with most reviews (bob)
    ("Log in with the demo account (email: bob.c@test.com, password: TestPass123!). "
     "Ants have invaded my kitchen. Find the exterminators who are Top Pros, request quotes "
     "for indoor ant treatment in zip 98101, and hire the responder with the most reviews. "
     "Tell me their name and their quote.",
     ),
    # 16. Kirkland city page -> highest-reviewed cleaner -> message + quote (alice)
    ("Log in with the demo account (email: alice.j@test.com, password: TestPass123!). "
     "Using the Kirkland city page, find the house cleaner with the most reviews, message them "
     "asking whether they bring their own supplies, and then request a quote from them for a "
     "standard cleaning of my 3-bedroom home.",
     ),
    # 17. personal trainer: guide range + Bellevue trainer + quote (david)
    ("Log in with the demo account (email: david.k@test.com, password: TestPass123!). "
     "I want to get in shape this fall. Using Thumbtack's cost guide, tell me the typical "
     "price range for personal training sessions. Then find the highest-rated personal trainer "
     "based in Bellevue and request a quote for twice-a-week sessions.",
     ),
    # 18. TV mounting questionnaire quote (alice)
    ("Log in with the demo account (email: alice.j@test.com, password: TestPass123!). "
     "I want my 75-inch TV mounted above the fireplace with the cables hidden. Request TV "
     "mounting quotes in zip 98052, answering the questionnaire to match my setup, and tell me "
     "how many pros responded and which one quoted the lowest.",
     ),
    # 19. near-me Events -> makeup by Most hires -> message (carol)
    ("Log in with the demo account (email: carol.d@test.com, password: TestPass123!). "
     "Starting from the Services near me page, open the Events services group and go to the "
     "wedding and event makeup category. Sort the list by Most hires and tell me the top "
     "makeup artist's name, number of hires, and review count. Then message them asking about "
     "availability for an October 18 event.",
     ),
    # 20. appliance repair: fastest responder + emergency quote (bob)
    ("Log in with the demo account (email: bob.c@test.com, password: TestPass123!). "
     "My refrigerator stopped cooling overnight and my food is spoiling. Find the appliance "
     "repair specialist who responds fastest, request a quote describing the emergency, and "
     "tell me the lowest quote you received.",
     ),
]

rows = []
for i, (ques,) in enumerate(TASKS):
    words = len(ques.split())
    assert words <= 100, f"task {i} too long: {words} words"
    rows.append({"web_name": "Thumbtack", "id": f"Thumbtack--{i}",
                 "ques": ques, "web": WEB, "upstream_url": UP})

out = HERE / "tasks.jsonl"
with out.open("w", encoding="utf-8") as fh:
    for row in rows:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
print(f"wrote {len(rows)} tasks")
for i, row in enumerate(rows):
    print(f"  {row['id']}: {len(row['ques'].split())} words")
