"""Frozen per-task fixture specs for the thumbtack verifier tests (review track).

URLs and honest answers come from the reviewer's live honest walks against the
review container (wh-tt-review @ http://localhost:46100, deterministic seed
md5 0c1320fd…). MUTATIONS reproduces the exact stateful writes the
application performs (new projects get id 6; match ids follow the seed's 25
rows; review id 857 follows the seed's 856 rows; saved_pros id 14 follows the
seed's 13 rows; threads/messages ids follow 1/2). Quote amounts are the
det_hash(project_id=6, service_pk) values the app produces. No LLM.

Round-2 re-freeze (2026-09-27, adversarial re-review): task 5's match row
27 corrected from pro 113 to pro 106 (the app's deterministic seed_matches
picks 106, and 106 is the non-responder) and task 8's honest URL sequence
re-frozen to the real click-through URLs (mountlake-terrace / lynnwood city
slugs, plus the Shark Style profile the honest discovery opens first) —
both verified against fresh honest walks on the round-2 review container
(wh-tt-rereview, same deterministic seed).

Audit-rail re-freeze (2026-09-28, re-sync of re-review observation R1):
the 15 deepened tasks (2,3,6,7,8,9,10,11,12,13,14,16,17,18,19) re-frozen
from the audit walks on the audit container wh-tt-audit @
127.0.0.1:49100 (same deterministic seed md5 0c1320fd…, per-task reset +
fresh context, visible-element interaction only). SPECS urls/answers and
MUTATIONS statements are derived mechanically from those runs'
trajectory.json and initial.db/after.db pairs by
scripts_dev/resync_contract.py. Tasks 0/1/4/5/15 keep the r2-frozen
values (the audit walks pass them unchanged)."""

BASE = "http://localhost:49100"

SPECS = {
    0: dict(
        urls=[BASE + '/', BASE + '/login', BASE + '/search?q=Jeshua+Frees',
              BASE + '/wa/seattle/wedding-photographers/jeshua-frees-clearline-production/service/510542342918987781',
              BASE + '/', BASE + '/search?q=Tanner+Schmidt',
              BASE + '/wa/seattle/wedding-photographers/tanner-schmidt/service/508112018197602315',
              BASE + '/search?q=Jeshua+Frees',
              BASE + '/wa/seattle/wedding-photographers/jeshua-frees-clearline-production/service/510542342918987781',
              BASE + '/account/saved'],
        answer=("Jeshua Frees (Clearline Production) has more Thumbtack hires (69); saved to my "
                "saved pros. They have been in business 7 years and have 19 employees."),
    ),
    1: dict(
        urls=[BASE + '/', BASE + '/login', BASE + '/near-me',
              BASE + '/k/house-cleaning/near-me',
              BASE + '/projects/new?category=house-cleaning',
              BASE + '/projects/6', BASE + '/projects/6/review',
              BASE + '/wa/redmond/house-cleaning/ipanema-cleaning-service/service/532242797099122689'],
        answer=("Hired Ipanema Cleaning Service at $184 (cheapest responder) and left a 5-star "
                "review mentioning the move-out clean."),
    ),
    2: dict(
        urls=[BASE + "/",
              BASE + "/login",
              BASE + "/account",
              BASE + "/",
              BASE + "/prices",
              BASE + "/p/wedding-djs-cost",
              BASE + "/prices",
              BASE + "/p/wedding-photographer-prices",
              BASE + "/",
              BASE + "/k/djs/near-me",
              BASE + "/k/djs/near-me?sort=highest_rated",
              BASE + "/wa/everett/djs/cessionnation/service/376863969460043777",
              BASE + "/message/376863969460043777",
              BASE + "/account/messages/2",
              BASE + "/message/376863969460043777",
              BASE + "/wa/everett/djs/cessionnation/service/376863969460043777",
              BASE + "/projects/new?category=djs&pro=376863969460043777&zip=98052",
              BASE + "/projects/6",
              BASE + "/projects/6"],
        answer="A wedding DJ is more expensive than a wedding photographer: the DJ cost guide shows a national average of $500-$600 (typical cost $550) while the photographer guide shows $122-$450 (national average $150), so the DJ runs roughly $400 more on average. The highest-rated DJ based in Everett is Cessionnation (5.0, 33 reviews); I messaged them about the October wedding date and they replied: \"Hi! We'd love to be part of it \u2014 tell me the date and venue and I'll confirm availability right away.\" I then requested an estimate from them describing our four-hour wedding reception.",
    ),
    3: dict(
        urls=[BASE + "/",
              BASE + "/login",
              BASE + "/account",
              BASE + "/",
              BASE + "/wa/lynnwood/house-cleaning/paty-house-cleaning/service/491085485275881476",
              BASE + "/message/491085485275881476",
              BASE + "/account/messages/2",
              BASE + "/",
              BASE + "/k/house-cleaning/near-me",
              BASE + "/k/house-cleaning/near-me?sort=highest_rated",
              BASE + "/wa/kirkland/house-cleaning/empire-cleaning-services/service/476683242989297681",
              BASE + "/message/476683242989297681",
              BASE + "/account/messages/3",
              BASE + "/",
              BASE + "/account",
              BASE + "/account/messages/2",
              BASE + "/account/messages/2"],
        answer="The word customers mention most often in Paty House Cleaning's reviews is \"clean\" (30 mentions), and the newest review echoes that theme (\"...cleaning the home...\"). Paty replied about supplies: \"Hi! We bring all of our own supplies and equipment \u2014 you don't need to prepare anything except access to the rooms.\" The second house cleaner, Empire Cleaning Services, replied to the same question: \"Hi! We bring all of our own supplies and equipment \u2014 you don't need to prepare anything except access to the rooms.\" And Paty's Sunday follow-up reply: \"Thanks for reaching out! We're happy to work around your schedule \u2014 including weekends. Which day works best?\"",
    ),
    4: dict(
        urls=[BASE + '/', BASE + '/login', BASE + '/account', BASE + '/projects/2',
              BASE + '/', BASE + '/k/handyman/near-me',
              BASE + '/projects/new?category=handyman', BASE + '/projects/6'],
        answer=("Lowest quote on the TV mounting project was $121 from Wa Pro Builders Llc, "
                "with 5 quotes total; project cancelled; replacement handyman request started "
                "in 98033 for hanging a heavy mirror."),
    ),
    5: dict(
        urls=[BASE + '/', BASE + '/login', BASE + '/account', BASE + '/account/profile',
              BASE + '/', BASE + '/k/lawn-care/near-me?sort=highest_rated',
              BASE + '/wa/kirkland/lawn-care/slc-simple-lawn-care/service/230942537935791237',
              BASE + '/projects/new?category=lawn-care&pro=230942537935791237',
              BASE + '/projects/6'],
        answer=("Updated my profile zip to 98033 and my Kirkland address. The highest-rated lawn "
                "care professional serving Kirkland is Slc - Simple Lawn Care (4.8, 65 reviews); "
                "requested a quote for weekly mowing service."),
    ),
    6: dict(
        urls=[BASE + "/",
              BASE + "/login",
              BASE + "/account",
              BASE + "/",
              BASE + "/k/affordable-plumbing-services/near-me",
              BASE + "/k/affordable-plumbing-services/near-me?sort=highest_rated",
              BASE + "/wa/everett/affordable-plumbing-services/velichkoremodels-llc-emergency-restoration-247/service/550902459815264257",
              BASE + "/message/550902459815264257",
              BASE + "/account/messages/2",
              BASE + "/message/550902459815264257",
              BASE + "/wa/everett/affordable-plumbing-services/velichkoremodels-llc-emergency-restoration-247/service/550902459815264257",
              BASE + "/projects/new?category=affordable-plumbing-services&pro=550902459815264257&zip=98052",
              BASE + "/projects/6",
              BASE + "/",
              BASE + "/prices",
              BASE + "/p/plumbers-cost",
              BASE + "/p/plumbers-cost"],
        answer="Velichkoremodels Llc Emergency Restoration 24/7 is the highest-rated plumber who is background checked and accepts Venmo; I saved them to my saved pros and messaged about the urgent leak \u2014 they replied: \"Hi! For a job like this we can usually be there same-day or next-day. Please avoid using that fixture until we've had a look.\" I requested a pipe-repair quote within a week describing the leaky kitchen faucet; the lowest quote was $51, which sits below the cost guide's typical range of $50 - $200 per hour for plumbers.",
    ),
    7: dict(
        urls=[BASE + "/",
              BASE + "/register",
              BASE + "/account",
              BASE + "/",
              BASE + "/k/furniture-assembly/near-me",
              BASE + "/projects/new?category=furniture-assembly",
              BASE + "/projects/6",
              BASE + "/projects/6/review",
              BASE + "/projects/6",
              BASE + "/projects/6"],
        answer="4 pros responded to the wardrobe-and-two-bookcases assembly request in zip 98101; the cheapest quote was $107. I hired that pro, marked the project complete and left a 5-star review mentioning the smooth assembly.",
    ),
    8: dict(
        urls=[BASE + "/",
              BASE + "/login",
              BASE + "/account",
              BASE + "/",
              BASE + "/k/handyman/near-me",
              BASE + "/wa/seattle/handyman/shark-style-llc/service/462308720949968896",
              BASE + "/k/handyman/near-me",
              BASE + "/wa/mountlake-terrace/handyman/evergreen-home-assist-llc/service/559530045965762575",
              BASE + "/wa/lynnwood/handyman/id-handyman/service/557383931483373571",
              BASE + "/message/557383931483373571",
              BASE + "/account/messages/2",
              BASE + "/",
              BASE + "/account",
              BASE + "/account/saved",
              BASE + "/account/saved"],
        answer="Two handymen with Sunday business hours: Evergreen Home Assist Llc (12 reviews, Sun 8:00 am - 8:00 pm) and I.d. Handyman (56 reviews, Sun 12:00 am - 11:59 pm). I saved both, messaged the more-reviewed one (I.d. Handyman) about a Sunday visit \u2014 reply: \"Hi! Thanks for reaching out. We do have openings \u2014 could you share a couple of dates that work for you?\" \u2014 and followed up asking which Sunday time slots they have open \u2014 reply: \"Hi! Thanks for reaching out. We do have openings \u2014 could you share a couple of dates that work for you?\" Then I removed Evergreen Home Assist from my saved list.",
    ),
    9: dict(
        urls=[BASE + "/",
              BASE + "/login",
              BASE + "/account",
              BASE + "/",
              BASE + "/prices",
              BASE + "/p/house-cleaning-prices",
              BASE + "/prices",
              BASE + "/",
              BASE + "/k/house-cleaning/near-me",
              BASE + "/projects/new?category=house-cleaning",
              BASE + "/projects/6",
              BASE + "/projects/6/review",
              BASE + "/projects/6",
              BASE + "/projects/6"],
        answer="According to the cost guide, most people pay $174 - $256 for a one-time house cleaning visit. I requested a one-time deep-cleaning quote for my 3-bedroom, 2-bathroom home in zip 98101; the cheapest quote was $184 from Ipanema Cleaning Service, whom I hired, marked complete and left a 5-star review. Their price falls inside the guide's typical range.",
    ),
    10: dict(
        urls=[BASE + "/",
              BASE + "/login",
              BASE + "/account",
              BASE + "/account/saved",
              BASE + "/",
              BASE + "/account",
              BASE + "/projects/3",
              BASE + "/wa/kent/local-movers/strok-industries-moving-company/service/537096908478578695",
              BASE + "/projects/3",
              BASE + "/",
              BASE + "/k/local-movers/near-me",
              BASE + "/projects/new?category=local-movers",
              BASE + "/projects/6",
              BASE + "/projects/6"],
        answer="Removed the two moving companies (At Moving and John Frank Moving Company) from my saved pros. My pending moving project's lowest quote was $199 from Strok Industries Moving Company, whose profile shows Excellent 4.9 rating and \"Responds within a day\". I cancelled that project and started a much smaller studio-move replacement request in zip 98101, which received 5 quotes this time.",
    ),
    11: dict(
        urls=[BASE + "/",
              BASE + "/login",
              BASE + "/account",
              BASE + "/",
              BASE + "/prices",
              BASE + "/p/makeup-artist-prices",
              BASE + "/prices",
              BASE + "/p/wedding-djs-cost",
              BASE + "/",
              BASE + "/k/makeup-artists/near-me",
              BASE + "/k/makeup-artists/near-me?sort=highest_rated",
              BASE + "/wa/redmond/makeup-artists/mel-mua/service/549098172844007430",
              BASE + "/message/549098172844007430",
              BASE + "/account/messages/2",
              BASE + "/message/549098172844007430",
              BASE + "/wa/redmond/makeup-artists/mel-mua/service/549098172844007430",
              BASE + "/projects/new?category=makeup-artists&pro=549098172844007430&zip=98052",
              BASE + "/projects/6",
              BASE + "/projects/6"],
        answer="A DJ is more expensive than a makeup artist: the DJ cost guide shows $500-$600 (national average $550) while makeup artists average $167 ($156 - $178). The highest-rated Top Pro makeup artist based in Redmond is Mel Mua (4.9, 71 reviews, Top Pro); I messaged her about the October event and she replied: \"Hi! I'd love to do your makeup \u2014 tell me the date and location and I'll check my calendar. Trials are available too.\" I then requested an estimate from her describing the quincea\u00f1era makeup for my daughter.",
    ),
    12: dict(
        urls=[BASE + "/",
              BASE + "/login",
              BASE + "/account",
              BASE + "/projects/1",
              BASE + "/wa/kirkland/house-cleaning/empire-cleaning-services/service/476683242989297681",
              BASE + "/projects/1",
              BASE + "/projects/1/review",
              BASE + "/projects/1",
              BASE + "/wa/kirkland/house-cleaning/empire-cleaning-services/service/476683242989297681",
              BASE + "/message/476683242989297681",
              BASE + "/account/messages/2",
              BASE + "/account/messages/2"],
        answer="My finished house cleaning project hired Empire Cleaning Services at $244; their response note was \"Thanks for the details! This is our estimate for the scope you described; we can adjust after an on-site visit.\" Their profile already had good reviews, and after I left a 5-star review saying they were thorough \u2014 the house is spotless \u2014 my review shows as the most recent one on their profile. I messaged asking whether they could return for a move-out clean next month \u2014 reply: \"Hi! We'd love to help. Deep cleans for a home your size usually take our team 3-4 hours.\" \u2014 and followed up about supplies \u2014 reply: \"Hi! We bring all of our own supplies and equipment \u2014 you don't need to prepare anything except access to the rooms.\"",
    ),
    13: dict(
        urls=[BASE + "/",
              BASE + "/login",
              BASE + "/account",
              BASE + "/account/messages/1",
              BASE + "/",
              BASE + "/k/house-cleaning/near-me",
              BASE + "/k/house-cleaning/near-me?sort=highest_rated",
              BASE + "/wa/kirkland/house-cleaning/empire-cleaning-services/service/476683242989297681",
              BASE + "/message/476683242989297681",
              BASE + "/account/messages/2",
              BASE + "/",
              BASE + "/account",
              BASE + "/account/messages/1",
              BASE + "/account/messages/1"],
        answer="In my existing thread, Ipanema Cleaning Service said: \"Hi! We bring all of our own supplies and equipment \u2014 you don't need to prepare anything except access to the rooms.\" The second cleaner, Empire Cleaning Services, answered the same question the same way \u2014 \"Hi! We bring all of our own supplies and equipment \u2014 you don't need to prepare anything except access to the rooms.\" \u2014 so both bring all their own supplies and equipment. On Sunday availability, Empire replied: \"Thanks for reaching out! We're happy to work around your schedule \u2014 including weekends. Which day works best?\" and Ipanema replied: \"Thanks for reaching out! We're happy to work around your schedule \u2014 including weekends. Which day works best?\" \u2014 both cleaners offer weekend/Sunday scheduling, so their answers match on both questions.",
    ),
    14: dict(
        urls=[BASE + "/",
              BASE + "/login",
              BASE + "/account",
              BASE + "/",
              BASE + "/prices",
              BASE + "/p/exterminators-prices",
              BASE + "/prices",
              BASE + "/",
              BASE + "/k/exterminators/near-me",
              BASE + "/projects/new?category=exterminators",
              BASE + "/projects/6",
              BASE + "/projects/6/review",
              BASE + "/projects/6",
              BASE + "/wa/kirkland/exterminators/super-attic-solutions/service/472430256251617281",
              BASE + "/wa/kirkland/exterminators/super-attic-solutions/service/472430256251617281"],
        answer="An exterminator typically runs $131 - $341 according to the cost guide. I requested indoor ant treatment quotes within a week in zip 98101 from the Top Pro exterminators and hired the responder with the most reviews: Super Attic Solutions (123 reviews), who quoted $315. I marked the project complete, left a 5-star review mentioning the ants, and confirmed on their profile that my review shows as the most recent one.",
    ),
    15: dict(
        urls=[BASE + '/', BASE + '/login', BASE + '/wa/kirkland',
              BASE + '/wa/kirkland/house-cleaning/empire-cleaning-services/service/476683242989297681',
              BASE + '/message/476683242989297681', BASE + '/account/messages/2',
              BASE + '/projects/new?category=house-cleaning&pro=476683242989297681&zip=98033',
              BASE + '/projects/6'],
        answer=("The Kirkland house cleaner with the most reviews is Empire Cleaning Services "
                "(33 reviews). Messaged them asking whether they bring their own supplies; they "
                "replied that they bring all of their own supplies and equipment. Requested a "
                "quote from them for a standard cleaning of my 3-bedroom home."),
    ),
    16: dict(
        urls=[BASE + "/",
              BASE + "/login",
              BASE + "/account",
              BASE + "/",
              BASE + "/prices",
              BASE + "/p/personal-trainer-cost",
              BASE + "/prices",
              BASE + "/",
              BASE + "/k/personal-trainers/near-me",
              BASE + "/k/personal-trainers/near-me?sort=highest_rated",
              BASE + "/wa/bellevue/personal-trainers/gaskill-personal-training/service/285389944820876322",
              BASE + "/message/285389944820876322",
              BASE + "/account/messages/2",
              BASE + "/message/285389944820876322",
              BASE + "/wa/bellevue/personal-trainers/gaskill-personal-training/service/285389944820876322",
              BASE + "/projects/new?category=personal-trainers&pro=285389944820876322&zip=98052",
              BASE + "/projects/6",
              BASE + "/projects/6"],
        answer="Personal training sessions typically cost $40 - $100 (national average $55) according to the cost guide. The highest-rated personal trainer based in Bellevue is Gaskill Personal Training (5.0, 34 reviews); I messaged them to confirm twice-a-week slots and they replied: \"Hi! Great timing \u2014 I have morning and evening slots open. Twice a week is a perfect pace to start.\" I then requested a quote from them describing twice-a-week strength sessions.",
    ),
    17: dict(
        urls=[BASE + "/",
              BASE + "/login",
              BASE + "/account",
              BASE + "/",
              BASE + "/k/tv-wall-mount-install/near-me",
              BASE + "/projects/new?category=tv-wall-mount-install",
              BASE + "/projects/6",
              BASE + "/projects/6/review",
              BASE + "/projects/6",
              BASE + "/projects/6"],
        answer="4 pros responded to the TV mounting request; the lowest quote was $127, and I hired that pro (Mmy). I marked the project complete and left them a 5-star review mentioning the tidy cable work.",
    ),
    18: dict(
        urls=[BASE + "/",
              BASE + "/login",
              BASE + "/account",
              BASE + "/near-me",
              BASE + "/k/makeup-artists/near-me",
              BASE + "/k/makeup-artists/near-me?sort=most_hires",
              BASE + "/wa/redmond/makeup-artists/mel-mua/service/549098172844007430",
              BASE + "/message/549098172844007430",
              BASE + "/account/messages/2",
              BASE + "/message/549098172844007430",
              BASE + "/wa/redmond/makeup-artists/mel-mua/service/549098172844007430",
              BASE + "/wa/redmond/makeup-artists/mel-mua/service/549098172844007430"],
        answer="The top makeup artist by Most hires is Mel Mua with 121 hires and 71 reviews. Her profile shows Top Pro status and \"Responds in about 28 min\". I messaged her about availability for an October 18 event \u2014 reply: \"Hi! I'd love to do your makeup \u2014 tell me the date and location and I'll check my calendar. Trials are available too.\" \u2014 and followed up about a pre-event trial \u2014 reply: \"Hi! I'd love to do your makeup \u2014 tell me the date and location and I'll check my calendar. Trials are available too.\" \u2014 then saved her to my saved pros.",
    ),
    19: dict(
        urls=[BASE + "/",
              BASE + "/login",
              BASE + "/account",
              BASE + "/",
              BASE + "/k/appliance-repair/near-me",
              BASE + "/k/appliance-repair/near-me?sort=fastest_response",
              BASE + "/wa/woodinville/appliance-repair/hotwire-hvac-refrigeration-appliance-repair/service/500453696558571522",
              BASE + "/projects/new?category=appliance-repair&pro=500453696558571522&zip=98052",
              BASE + "/projects/6",
              BASE + "/projects/6/review",
              BASE + "/projects/6",
              BASE + "/projects/6"],
        answer="The appliance repair specialist who responds fastest is Hotwire Hvac Refrigeration & Appliance Repair (responds in about 1 min). I requested an emergency quote describing the GE refrigerator repair; the lowest quote I received was $130, and I hired that pro and left them a 5-star review mentioning the refrigerator.",
    ),
}

# Exact stateful writes the application performs for the honest path.
TS = "2026-09-26 12:00:00.000000"
TSU = "2026-09-26 12:30:00.000000"
TSP = "2026-09-26 12:32:00.000000"
PW = "$2b$12$qSds4Mr9Wo7VwPWLhompEer88SuxxXFDp31P9etY6v7nfRctNO7B."
HC = ("[[\"Frequency\", \"Just once\"], [\"Number of bedrooms\", \"2 bedrooms\"], "
      "[\"Number of bathrooms\", \"2 bathrooms\"], [\"Cleaning type\", \"Deep cleaning\"]]")

MUTATIONS = {
    0: [
        "INSERT INTO saved_pros VALUES (14, 1, 169, '" + TS + "')",
    ],
    1: [
        "INSERT INTO projects VALUES (6, 2, 1, '98101', 'Deep clean before move-out next month.', "
        "'Within a week', '[[\"Frequency\", \"Just once\"], [\"Number of bedrooms\", \"2 bedrooms\"], "
        "[\"Number of bathrooms\", \"2 bathrooms\"], [\"Cleaning type\", \"Deep cleaning\"]]', "
        "'completed', '" + TS + "')",
        "INSERT INTO project_matches VALUES (26, 6, 73, 1, 191, 'Happy to help — based on what you described, this quote covers labor and standard materials.', 1440, 0)",
        "INSERT INTO project_matches VALUES (27, 6, 66, 1, 184, 'Appreciate you reaching out through Thumbtack! This quote includes everything we discussed.', 1440, 1)",
        "INSERT INTO project_matches VALUES (28, 6, 76, 1, 244, 'Happy to help — based on what you described, this quote covers labor and standard materials.', 240, 0)",
        "INSERT INTO project_matches VALUES (29, 6, 67, 1, 245, 'Appreciate you reaching out through Thumbtack! This quote includes everything we discussed.', 1440, 0)",
        "INSERT INTO project_matches VALUES (30, 6, 65, 1, 227, 'Happy to help — based on what you described, this quote covers labor and standard materials.', 1440, 0)",
        "INSERT INTO reviews VALUES (857, 66, 'Bob Chen', 'Sep 26, 2026', 5, "
        "'They were thorough and the place is spotless — perfect move-out deep clean. 5 stars!', "
        "'project:6', 1, 'user')",
    ],
    2: [
        "INSERT INTO projects VALUES (6, 3, 16, '98004', 'Please quote our four-hour wedding reception.', 'Within 48 hours', '[[\"Duration\", \"4 hours\"], [\"Event type\", \"Wedding\"]]', 'matched', '" + TS + "')",
        "INSERT INTO project_matches VALUES (26, 6, 23, 1, 527, 'Thanks for the details! This is our estimate for the scope you described; we can adjust after an on-site visit.', 1440, 0)",
        "INSERT INTO project_matches VALUES (27, 6, 19, 1, 567, 'We''d love to take this on. The quote reflects the timeline you asked for, and we can start right away.', 1440, 0)",
        "INSERT INTO project_matches VALUES (28, 6, 20, 0, NULL, NULL, NULL, 0)",
        "INSERT INTO project_matches VALUES (29, 6, 26, 1, 586, 'Appreciate you reaching out through Thumbtack! This quote includes everything we discussed.', 40, 0)",
        "INSERT INTO project_matches VALUES (30, 6, 22, 1, 520, 'Happy to help \u2014 based on what you described, this quote covers labor and standard materials.', 120, 0)",
        "INSERT INTO threads VALUES (2, 3, 19, NULL, '" + TSP + "')",
        "INSERT INTO messages VALUES (3, 2, 'user', 'Hi! Are you available for an October wedding date? We would love to have you DJ our reception.', '" + TSU + "')",
        "INSERT INTO messages VALUES (4, 2, 'pro', 'Hi! We''d love to be part of it \u2014 tell me the date and venue and I''ll confirm availability right away.', '" + TSP + "')",
    ],
    3: [
        "INSERT INTO threads VALUES (2, 1, 71, NULL, '" + TSP + "')",
        "INSERT INTO threads VALUES (3, 1, 65, NULL, '" + TSP + "')",
        "INSERT INTO messages VALUES (3, 2, 'user', 'Hi Paty! Do you bring your own cleaning supplies when you clean?', '" + TSU + "')",
        "INSERT INTO messages VALUES (4, 2, 'pro', 'Hi! We bring all of our own supplies and equipment \u2014 you don''t need to prepare anything except access to the rooms.', '" + TSP + "')",
        "INSERT INTO messages VALUES (5, 3, 'user', 'Hi! Do you bring your own cleaning supplies when you clean?', '" + TSU + "')",
        "INSERT INTO messages VALUES (6, 3, 'pro', 'Hi! We bring all of our own supplies and equipment \u2014 you don''t need to prepare anything except access to the rooms.', '" + TSP + "')",
        "INSERT INTO messages VALUES (7, 2, 'user', 'Could you come on a Sunday? That would work best for my schedule.', '" + TSU + "')",
        "INSERT INTO messages VALUES (8, 2, 'pro', 'Thanks for reaching out! We''re happy to work around your schedule \u2014 including weekends. Which day works best?', '" + TSP + "')",
    ],
    4: [
        "UPDATE projects SET status = 'cancelled' WHERE id = 2",
        "INSERT INTO projects VALUES (6, 1, 4, '98033', 'Need a handyman to hang a heavy mirror on drywall.', "
        "'Within 48 hours', '[]', 'matched', '" + TS + "')",
        "INSERT INTO project_matches VALUES (26, 6, 61, 1, 80, 'Happy to help — based on what you described, this quote covers labor and standard materials.', 23, 0)",
        "INSERT INTO project_matches VALUES (27, 6, 55, 1, 68, 'Appreciate you reaching out through Thumbtack! This quote includes everything we discussed.', 60, 0)",
        "INSERT INTO project_matches VALUES (28, 6, 63, 1, 77, 'Happy to help — based on what you described, this quote covers labor and standard materials.', 1440, 0)",
        "INSERT INTO project_matches VALUES (29, 6, 54, 1, 75, 'Appreciate you reaching out through Thumbtack! This quote includes everything we discussed.', 60, 0)",
        "INSERT INTO project_matches VALUES (30, 6, 59, 1, 62, 'Happy to help — based on what you described, this quote covers labor and standard materials.', 1440, 0)",
    ],
    5: [
        "UPDATE users SET zip = '98033', address = '123 Main St, Kirkland, WA' WHERE id = 3",
        "INSERT INTO projects VALUES (6, 3, 5, '98033', 'Looking for weekly mowing service in Kirkland.', "
        "'Within a week', '[]', 'matched', '" + TS + "')",
        "INSERT INTO project_matches VALUES (26, 6, 105, 1, 255, 'Happy to help — based on what you described, this quote covers labor and standard materials.', 1440, 0)",
        "INSERT INTO project_matches VALUES (27, 6, 106, 0, NULL, NULL, NULL, 0)",
        "INSERT INTO project_matches VALUES (28, 6, 112, 1, 407, 'Appreciate you reaching out through Thumbtack! This quote includes everything we discussed.', 1, 0)",
        "INSERT INTO project_matches VALUES (29, 6, 107, 1, 194, 'Happy to help — based on what you described, this quote covers labor and standard materials.', 1440, 0)",
        "INSERT INTO project_matches VALUES (30, 6, 110, 1, 378, 'Appreciate you reaching out through Thumbtack! This quote includes everything we discussed.', 1440, 0)",
    ],
    6: [
        "INSERT INTO projects VALUES (6, 4, 2, '98033', 'My kitchen faucet has been dripping for a week \u2014 please quote the leaky faucet repair.', 'Within a week', '[[\"Select a service\", \"Plumbing Pipe Repair\"]]', 'matched', '" + TS + "')",
        "INSERT INTO project_matches VALUES (26, 6, 6, 1, 189, 'This is our all-in estimate \u2014 no hidden fees. Let me know if you''d like to adjust the scope.', 1, 0)",
        "INSERT INTO project_matches VALUES (27, 6, 3, 1, 135, 'Happy to help \u2014 based on what you described, this quote covers labor and standard materials.', 120, 0)",
        "INSERT INTO project_matches VALUES (28, 6, 1, 1, 51, 'We''d love to take this on. The quote reflects the timeline you asked for, and we can start right away.', 1440, 0)",
        "INSERT INTO project_matches VALUES (29, 6, 5, 1, 184, 'This is our all-in estimate \u2014 no hidden fees. Let me know if you''d like to adjust the scope.', 8, 0)",
        "INSERT INTO project_matches VALUES (30, 6, 2, 1, 169, 'We''d love to take this on. The quote reflects the timeline you asked for, and we can start right away.', 1, 0)",
        "INSERT INTO saved_pros VALUES (14, 4, 6, '" + TS + "')",
        "INSERT INTO threads VALUES (2, 4, 6, NULL, '" + TSP + "')",
        "INSERT INTO messages VALUES (3, 2, 'user', 'Hi! My kitchen faucet has been leaking for a week and it is urgent \u2014 can you handle the leak repair quickly?', '" + TSU + "')",
        "INSERT INTO messages VALUES (4, 2, 'pro', 'Hi! For a job like this we can usually be there same-day or next-day. Please avoid using that fixture until we''ve had a look.', '" + TSP + "')",
    ],
    7: [
        "INSERT INTO users VALUES (5, 'nina.p', 'nina.p@test.com', 'Nina Patel', '$2b$12$Tc0gDDErJZObSJHaICL5besFat6itOz5NbWHnrTPVKLGsRQxHuWli', NULL, '98101', NULL, '" + TS + "')",
        "INSERT INTO projects VALUES (6, 5, 9, '98101', 'Need assembly of a large wardrobe and two bookcases.', 'Within 48 hours', '[[\"Number of items\", \"3 items\"], [\"Instructions or make/model provided by client?\", \"Yes, I have assembly instructions or make and model information\"]]', 'completed', '" + TS + "')",
        "INSERT INTO project_matches VALUES (26, 6, 49, 1, 180, 'Thanks for the details! This is our estimate for the scope you described; we can adjust after an on-site visit.', 1440, 0)",
        "INSERT INTO project_matches VALUES (27, 6, 44, 0, NULL, NULL, NULL, 0)",
        "INSERT INTO project_matches VALUES (28, 6, 46, 1, 131, 'This is our all-in estimate \u2014 no hidden fees. Let me know if you''d like to adjust the scope.', 1440, 0)",
        "INSERT INTO project_matches VALUES (29, 6, 52, 1, 107, 'Thanks for the details! This is our estimate for the scope you described; we can adjust after an on-site visit.', 1440, 1)",
        "INSERT INTO project_matches VALUES (30, 6, 50, 1, 144, 'Thanks for the details! This is our estimate for the scope you described; we can adjust after an on-site visit.', 1440, 0)",
        "INSERT INTO reviews VALUES (857, 52, 'Nina Patel', 'Sep 26, 2026', 5, 'Smooth assembly of the wardrobe and both bookcases \u2014 quick and careful work!', 'project:6', 1, 'user')",
    ],
    8: [
        "INSERT INTO saved_pros VALUES (15, 1, 55, '" + TS + "')",
        "INSERT INTO threads VALUES (2, 1, 55, NULL, '" + TSP + "')",
        "INSERT INTO messages VALUES (3, 2, 'user', 'Hi! Can you do a Sunday visit for a small handyman job?', '" + TSU + "')",
        "INSERT INTO messages VALUES (4, 2, 'pro', 'Hi! Thanks for reaching out. We do have openings \u2014 could you share a couple of dates that work for you?', '" + TSP + "')",
        "INSERT INTO messages VALUES (5, 2, 'user', 'Which Sunday time slots do you have open?', '" + TSU + "')",
        "INSERT INTO messages VALUES (6, 2, 'pro', 'Hi! Thanks for reaching out. We do have openings \u2014 could you share a couple of dates that work for you?', '" + TSP + "')",
    ],
    9: [
        "INSERT INTO projects VALUES (6, 2, 1, '98101', 'Deep cleaning for a 3-bedroom, 2-bathroom home.', 'Within 48 hours', '[[\"Frequency\", \"Just once\"], [\"Number of bedrooms\", \"3 bedrooms\"], [\"Cleaning type\", \"Deep cleaning\"], [\"Number of bathrooms\", \"2 bathrooms\"]]', 'completed', '" + TS + "')",
        "INSERT INTO project_matches VALUES (26, 6, 73, 1, 191, 'Thanks for the details! This is our estimate for the scope you described; we can adjust after an on-site visit.', 1440, 0)",
        "INSERT INTO project_matches VALUES (27, 6, 66, 1, 184, 'Thanks for the details! This is our estimate for the scope you described; we can adjust after an on-site visit.', 1440, 1)",
        "INSERT INTO project_matches VALUES (28, 6, 76, 1, 244, 'We''d love to take this on. The quote reflects the timeline you asked for, and we can start right away.', 240, 0)",
        "INSERT INTO project_matches VALUES (29, 6, 67, 1, 245, 'Thanks for the details! This is our estimate for the scope you described; we can adjust after an on-site visit.', 1440, 0)",
        "INSERT INTO project_matches VALUES (30, 6, 65, 1, 227, 'This is our all-in estimate \u2014 no hidden fees. Let me know if you''d like to adjust the scope.', 1440, 0)",
        "INSERT INTO reviews VALUES (857, 66, 'Bob Chen', 'Sep 26, 2026', 5, 'Excellent deep clean \u2014 thorough, professional and quick!', 'project:6', 1, 'user')",
    ],
    10: [
        "UPDATE projects SET status = 'cancelled' WHERE id = 3",
        "DELETE FROM projects WHERE id = 3",
        "INSERT INTO projects VALUES (3, 2, 15, '98101', 'Move a 2-bedroom apartment from Seattle to Bellevue, one flight of stairs.', 'Within a week', '[[\"Move distance\", \"Local (under 50 miles)\"], [\"Home size\", \"2 bedrooms\"]]', 'cancelled', '" + TS + "')",
        "INSERT INTO projects VALUES (6, 2, 15, '98101', 'Much smaller studio apartment move within Seattle.', 'Within 48 hours', '[[\"Move size\", \"Studio\"]]', 'matched', '" + TS + "')",
        "INSERT INTO project_matches VALUES (26, 6, 119, 1, 274, 'We''d love to take this on. The quote reflects the timeline you asked for, and we can start right away.', 1440, 0)",
        "INSERT INTO project_matches VALUES (27, 6, 117, 1, 174, 'Thanks for the details! This is our estimate for the scope you described; we can adjust after an on-site visit.', 32, 0)",
        "INSERT INTO project_matches VALUES (28, 6, 115, 1, 224, 'Happy to help \u2014 based on what you described, this quote covers labor and standard materials.', 1440, 0)",
        "INSERT INTO project_matches VALUES (29, 6, 124, 1, 233, 'This is our all-in estimate \u2014 no hidden fees. Let me know if you''d like to adjust the scope.', 1440, 0)",
        "INSERT INTO project_matches VALUES (30, 6, 118, 1, 261, 'This is our all-in estimate \u2014 no hidden fees. Let me know if you''d like to adjust the scope.', 2, 0)",
        "DELETE FROM saved_pros WHERE id = 4",
        "DELETE FROM saved_pros WHERE id = 5",
    ],
    11: [
        "INSERT INTO projects VALUES (6, 3, 12, '98004', 'Quincea\u00f1era makeup for my daughter \u2014 please quote the event makeup.', 'Within 48 hours', '[[\"Event type\", \"Birthday party\"], [\"Subject age\", \"13 - 17 years old\"]]', 'matched', '" + TS + "')",
        "INSERT INTO project_matches VALUES (26, 6, 129, 1, 159, 'We''d love to take this on. The quote reflects the timeline you asked for, and we can start right away.', 5, 0)",
        "INSERT INTO project_matches VALUES (27, 6, 130, 1, 162, 'Happy to help \u2014 based on what you described, this quote covers labor and standard materials.', 28, 0)",
        "INSERT INTO project_matches VALUES (28, 6, 128, 1, 156, 'Thanks for the details! This is our estimate for the scope you described; we can adjust after an on-site visit.', 1440, 0)",
        "INSERT INTO project_matches VALUES (29, 6, 131, 1, 158, 'Appreciate you reaching out through Thumbtack! This quote includes everything we discussed.', 1440, 0)",
        "INSERT INTO project_matches VALUES (30, 6, 127, 1, 177, 'Thanks for the details! This is our estimate for the scope you described; we can adjust after an on-site visit.', 43, 0)",
        "INSERT INTO threads VALUES (2, 3, 130, NULL, '" + TSP + "')",
        "INSERT INTO messages VALUES (3, 2, 'user', 'Hi Mel! Are you available for an October event? It is my daughter''s quincea\u00f1era.', '" + TSU + "')",
        "INSERT INTO messages VALUES (4, 2, 'pro', 'Hi! I''d love to do your makeup \u2014 tell me the date and location and I''ll check my calendar. Trials are available too.', '" + TSP + "')",
    ],
    12: [
        "INSERT INTO reviews VALUES (857, 65, 'Alice Johnson', 'Sep 26, 2026', 5, 'They were thorough \u2014 the house is spotless. Great job!', 'project:1', 1, 'user')",
        "INSERT INTO threads VALUES (2, 1, 65, NULL, '" + TSP + "')",
        "INSERT INTO messages VALUES (3, 2, 'user', 'Hi! Could you return for a move-out clean next month?', '" + TSU + "')",
        "INSERT INTO messages VALUES (4, 2, 'pro', 'Hi! We''d love to help. Deep cleans for a home your size usually take our team 3-4 hours.', '" + TSP + "')",
        "INSERT INTO messages VALUES (5, 2, 'user', 'Would you bring your own supplies for the move-out clean?', '" + TSU + "')",
        "INSERT INTO messages VALUES (6, 2, 'pro', 'Hi! We bring all of our own supplies and equipment \u2014 you don''t need to prepare anything except access to the rooms.', '" + TSP + "')",
    ],
    13: [
        "UPDATE threads SET updated_at = '" + TSP + "' WHERE id = 1",
        "DELETE FROM threads WHERE id = 1",
        "INSERT INTO threads VALUES (1, 1, 66, NULL, '" + TSP + "')",
        "INSERT INTO threads VALUES (2, 1, 65, NULL, '" + TSP + "')",
        "INSERT INTO messages VALUES (3, 2, 'user', 'Hi! Do you bring your own cleaning supplies, or should I have them ready?', '" + TSU + "')",
        "INSERT INTO messages VALUES (4, 2, 'pro', 'Hi! We bring all of our own supplies and equipment \u2014 you don''t need to prepare anything except access to the rooms.', '" + TSP + "')",
        "INSERT INTO messages VALUES (5, 2, 'user', 'Could you come on a Sunday? That would work best for me.', '" + TSU + "')",
        "INSERT INTO messages VALUES (6, 2, 'pro', 'Thanks for reaching out! We''re happy to work around your schedule \u2014 including weekends. Which day works best?', '" + TSP + "')",
        "INSERT INTO messages VALUES (7, 1, 'user', 'Could you come on a Sunday? That would work best for me.', '" + TSU + "')",
        "INSERT INTO messages VALUES (8, 1, 'pro', 'Thanks for reaching out! We''re happy to work around your schedule \u2014 including weekends. Which day works best?', '" + TSP + "')",
    ],
    14: [
        "INSERT INTO projects VALUES (6, 2, 11, '98101', 'Ants have invaded my kitchen \u2014 need indoor ant treatment.', 'Within a week', '[[\"Select a service\", \"Pest Control Services\"]]', 'completed', '" + TS + "')",
        "INSERT INTO project_matches VALUES (26, 6, 36, 1, 250, 'This is our all-in estimate \u2014 no hidden fees. Let me know if you''d like to adjust the scope.', 1440, 0)",
        "INSERT INTO project_matches VALUES (27, 6, 40, 1, 170, 'This is our all-in estimate \u2014 no hidden fees. Let me know if you''d like to adjust the scope.', 1440, 0)",
        "INSERT INTO project_matches VALUES (28, 6, 32, 1, 207, 'Happy to help \u2014 based on what you described, this quote covers labor and standard materials.', 180, 0)",
        "INSERT INTO project_matches VALUES (29, 6, 41, 1, 137, 'We''d love to take this on. The quote reflects the timeline you asked for, and we can start right away.', 240, 0)",
        "INSERT INTO project_matches VALUES (30, 6, 38, 1, 315, 'Thanks for the details! This is our estimate for the scope you described; we can adjust after an on-site visit.', 1440, 1)",
        "INSERT INTO reviews VALUES (857, 38, 'Bob Chen', 'Sep 26, 2026', 5, 'They took care of the ants quickly and thoroughly \u2014 great service!', 'project:6', 1, 'user')",
    ],
    15: [
        "INSERT INTO threads VALUES (2, 1, 65, NULL, '" + TSP + "')",
        "INSERT INTO messages VALUES (3, 2, 'user', 'Hi! Do you bring your own cleaning supplies?', '" + TSU + "')",
        "INSERT INTO messages VALUES (4, 2, 'pro', 'Hi! We bring all of our own supplies and equipment — you don''t need to prepare anything except access to the rooms.', '" + TSP + "')",
        "INSERT INTO projects VALUES (6, 1, 1, '98033', 'Standard cleaning for my 3-bedroom home.', "
        "'Within a week', '[[\"Number of bedrooms\", \"3 bedrooms\"]]', 'matched', '" + TS + "')",
        "INSERT INTO project_matches VALUES (26, 6, 73, 1, 191, 'Happy to help — based on what you described, this quote covers labor and standard materials.', 1440, 0)",
        "INSERT INTO project_matches VALUES (27, 6, 66, 1, 184, 'Appreciate you reaching out through Thumbtack! This quote includes everything we discussed.', 1440, 0)",
        "INSERT INTO project_matches VALUES (28, 6, 76, 1, 244, 'Happy to help — based on what you described, this quote covers labor and standard materials.', 240, 0)",
        "INSERT INTO project_matches VALUES (29, 6, 67, 1, 245, 'Appreciate you reaching out through Thumbtack! This quote includes everything we discussed.', 1440, 0)",
        "INSERT INTO project_matches VALUES (30, 6, 65, 1, 227, 'Happy to help — based on what you described, this quote covers labor and standard materials.', 1440, 0)",
    ],
    16: [
        "INSERT INTO projects VALUES (6, 4, 14, '98033', 'Looking for twice-a-week strength training sessions this fall.', 'Within 48 hours', '[[\"Frequency\", \"2-3 times a week\"]]', 'matched', '" + TS + "')",
        "INSERT INTO project_matches VALUES (26, 6, 136, 1, 67, 'This is our all-in estimate \u2014 no hidden fees. Let me know if you''d like to adjust the scope.', 1440, 0)",
        "INSERT INTO project_matches VALUES (27, 6, 138, 1, 90, 'We''d love to take this on. The quote reflects the timeline you asked for, and we can start right away.', 120, 0)",
        "INSERT INTO project_matches VALUES (28, 6, 135, 1, 98, 'This is our all-in estimate \u2014 no hidden fees. Let me know if you''d like to adjust the scope.', 120, 0)",
        "INSERT INTO project_matches VALUES (29, 6, 133, 1, 60, 'Thanks for the details! This is our estimate for the scope you described; we can adjust after an on-site visit.', 1440, 0)",
        "INSERT INTO project_matches VALUES (30, 6, 137, 1, 68, 'Thanks for the details! This is our estimate for the scope you described; we can adjust after an on-site visit.', 1440, 0)",
        "INSERT INTO threads VALUES (2, 4, 136, NULL, '" + TSP + "')",
        "INSERT INTO messages VALUES (3, 2, 'user', 'Hi! Do you have twice-a-week training slots available this fall? I want to build strength.', '" + TSU + "')",
        "INSERT INTO messages VALUES (4, 2, 'pro', 'Hi! Great timing \u2014 I have morning and evening slots open. Twice a week is a perfect pace to start.', '" + TSP + "')",
    ],
    17: [
        "INSERT INTO projects VALUES (6, 1, 8, '98052', 'Mount my 75-inch TV above the fireplace with the cables hidden and my sound bar connected.', 'Within 48 hours', '[[\"Conceal cables/wires?\", \"Yes, I need to conceal cables and wires\"], [\"Sound system\", \"Sound bar\"], [\"TV installation location\", \"Wall mount above fireplace\"]]', 'completed', '" + TS + "')",
        "INSERT INTO project_matches VALUES (26, 6, 162, 1, 220, 'This is our all-in estimate \u2014 no hidden fees. Let me know if you''d like to adjust the scope.', 4, 0)",
        "INSERT INTO project_matches VALUES (27, 6, 163, 0, NULL, NULL, NULL, 0)",
        "INSERT INTO project_matches VALUES (28, 6, 160, 1, 127, 'Happy to help \u2014 based on what you described, this quote covers labor and standard materials.', 1440, 1)",
        "INSERT INTO project_matches VALUES (29, 6, 161, 1, 173, 'Happy to help \u2014 based on what you described, this quote covers labor and standard materials.', 1440, 0)",
        "INSERT INTO project_matches VALUES (30, 6, 159, 1, 187, 'Appreciate you reaching out through Thumbtack! This quote includes everything we discussed.', 1440, 0)",
        "INSERT INTO reviews VALUES (857, 160, 'Alice Johnson', 'Sep 26, 2026', 5, 'Tidy cable work \u2014 the TV looks great above the fireplace and the sound bar is perfect!', 'project:6', 1, 'user')",
    ],
    18: [
        "INSERT INTO saved_pros VALUES (14, 3, 130, '" + TS + "')",
        "INSERT INTO threads VALUES (2, 3, 130, NULL, '" + TSP + "')",
        "INSERT INTO messages VALUES (3, 2, 'user', 'Hi Mel! Are you available for an October 18 event?', '" + TSU + "')",
        "INSERT INTO messages VALUES (4, 2, 'pro', 'Hi! I''d love to do your makeup \u2014 tell me the date and location and I''ll check my calendar. Trials are available too.', '" + TSP + "')",
        "INSERT INTO messages VALUES (5, 2, 'user', 'Do you offer a pre-event trial session before the day?', '" + TSU + "')",
        "INSERT INTO messages VALUES (6, 2, 'pro', 'Hi! I''d love to do your makeup \u2014 tell me the date and location and I''ll check my calendar. Trials are available too.', '" + TSP + "')",
    ],
    19: [
        "INSERT INTO projects VALUES (6, 2, 6, '98101', 'Emergency: my GE refrigerator stopped cooling overnight and my food is spoiling \u2014 please quote the repair.', 'Within 48 hours', '[[\"Appliance type\", \"Refrigerator\"], [\"Appliance brand\", \"GE\"]]', 'completed', '" + TS + "')",
        "INSERT INTO project_matches VALUES (26, 6, 11, 1, 275, 'Thanks for the details! This is our estimate for the scope you described; we can adjust after an on-site visit.', 1440, 0)",
        "INSERT INTO project_matches VALUES (27, 6, 9, 1, 328, 'Appreciate you reaching out through Thumbtack! This quote includes everything we discussed.', 60, 0)",
        "INSERT INTO project_matches VALUES (28, 6, 18, 1, 130, 'We''d love to take this on. The quote reflects the timeline you asked for, and we can start right away.', 1440, 1)",
        "INSERT INTO project_matches VALUES (29, 6, 17, 1, 319, 'Thanks for the details! This is our estimate for the scope you described; we can adjust after an on-site visit.', 1440, 0)",
        "INSERT INTO project_matches VALUES (30, 6, 14, 1, 232, 'This is our all-in estimate \u2014 no hidden fees. Let me know if you''d like to adjust the scope.', 15, 0)",
        "INSERT INTO reviews VALUES (857, 18, 'Bob Chen', 'Sep 26, 2026', 5, 'Fast refrigerator repair \u2014 they saved my food! Great work.', 'project:6', 1, 'user')",
    ],
}

WRONG_ANSWERS = {
    0: "Tanner Schmidt has more hires (30); he has been in business 6 years and has 1 employee. Saved him.",
    1: "Hired Sirlene's Cleaning at $191 and left a 5-star review mentioning the deep clean.",
    2: "The wedding photographer is more expensive at $550; DJs average $150. The Everett DJ Cessionnation responds in about 4 hours; no message or estimate was sent.",
    3: "Customers mention 'thorough' most often. Paty said I must provide all cleaning supplies myself; the second cleaner never replied and Paty is closed on Sundays.",
    4: "The lowest quote was $199 from Strok Industries with 2 quotes total; project cancelled.",
    5: "Updated my zip to 98004 and requested a quote from Rhino Landscaping & More.",
    6: "Saved George Gas Piping (no background check) and requested a quote about the dripping faucet; the lowest quote was $200, right at the top of the guide's range.",
    7: "5 pros responded and the cheapest quote was $180; I hired the most expensive one and left a 3-star review.",
    8: "Messaged Evergreen Home Assist Llc (12 reviews); they said they have no Sunday openings. I.d. Handyman was kept in the saved list.",
    9: "A one-time visit typically costs $40-$55 per hour; the cheapest quote $184 is outside that range. I hired Sirlene's Cleaning and left a 4-star review.",
    10: "Removed I.d. Handyman from saved pros; the lowest quote was $241 from At Moving; I cancelled and the studio replacement got 2 quotes.",
    11: "The makeup artist is more expensive at $550; Mel Mua has a 4.8 rating and accepts only cash; no estimate was requested.",
    12: "Left a 4-star review saying the job was fine; it appears at the bottom of the reviews. Empire quoted $184 and never replied to the move-out message.",
    13: "Ipanema said they bring their own supplies; the second cleaner said I must provide everything; only the first cleaner answered the Sunday question.",
    14: "Hired Attic Crawl Inc (110 reviews) with a quote of $207; the guide range is $50-$200; my review does not show on the profile.",
    15: "The Kirkland cleaner with the most reviews is Viviane's Cleaning Service; she asked me to buy supplies.",
    16: "Sessions typically cost $55-$100; requested a quote from Jason Joyce Fitness instead of the Bellevue trainer; no message was sent.",
    17: "5 pros responded and the lowest quote was $220 from Wa Pro Builders; I hired them and left a 4-star review about the price.",
    18: "The top makeup artist is Cessionnation with 121 hires and 71 reviews; she said she is booked and does not do trials; she was not saved.",
    19: "The fastest responder is Fresh Start Pro Llc (15 min); the lowest quote was $232; I hired them and left a 3-star review about the delay.",
}


# Current browser regression fixtures (synthetic unit-test reconstructions; not new browser evidence).
SPECS = {0: {'answer': 'Jeshua Frees (Clearline Production) has more Thumbtack hires (69); saved to my saved pros. They '
               'have been in business 7 years and have 19 employees.',
     'urls': ['/',
              '/login',
              '/account',
              '/search?q=Jeshua+Frees',
              '/wa/seattle/wedding-photographers/jeshua-frees-clearline-production/service/510542342918987781',
              '/search?q=Tanner+Schmidt',
              '/wa/seattle/wedding-photographers/tanner-schmidt/service/508112018197602315',
              '/search?q=Liz+Ong',
              '/wa/seattle/wedding-photographers/liz-ong/service/419445551220367364',
              '/account/saved']},
 1: {'answer': 'Hired Ipanema Cleaning Service at $184 (cheapest responder) and left a 5-star review mentioning '
               'the move-out clean.',
     'urls': ['/',
              '/login',
              '/account',
              '/near-me',
              '/k/house-cleaning/near-me',
              '/projects/new?category=house-cleaning',
              '/projects/6',
              '/projects/6/review',
              '/wa/redmond/house-cleaning/ipanema-cleaning-service/service/532242797099122689']},
 2: {'answer': 'The DJ cost guide gives a typical national cost of $550 and a $500–$600 range. The wedding '
               'photographer guide gives a national average of $150 and a $122–$450 range. Hiring the DJ is about '
               '$400 more expensive on average. The highest-rated DJ based in Everett is Cessionnation (5.0, 33 '
               'reviews); I messaged them about the October wedding date and they replied: "Hi! We\'d love to be '
               'part of it — tell me the date and venue and I\'ll confirm availability right away." I then '
               'requested an estimate from them describing our four-hour wedding reception.',
     'urls': ['/',
              '/login',
              '/account',
              '/prices',
              '/p/wedding-djs-cost',
              '/p/wedding-photographer-prices',
              '/k/djs/near-me',
              '/k/djs/near-me?sort=highest_rated',
              '/wa/everett/djs/cessionnation/service/376863969460043777',
              '/message/376863969460043777',
              '/account/messages/2',
              '/projects/new?category=djs&pro=376863969460043777&zip=98052',
              '/projects/6']},
 3: {'answer': 'The word customers mention most often in Paty House Cleaning\'s reviews is "clean" (30 mentions), '
               'and the newest review echoes that theme ("...cleaning the home..."). Paty replied about supplies: '
               '"Hi! We bring all of our own supplies and equipment — you don\'t need to prepare anything except '
               'access to the rooms." The second house cleaner, Empire Cleaning Services, replied to the same '
               'question: "Hi! We bring all of our own supplies and equipment — you don\'t need to prepare '
               'anything except access to the rooms." And Paty\'s Sunday follow-up reply: "Thanks for reaching '
               'out! We\'re happy to work around your schedule — including weekends. Which day works best?"',
     'urls': ['/',
              '/login',
              '/account',
              '/search?q=paty+house+cleaning',
              '/wa/lynnwood/house-cleaning/paty-house-cleaning/service/491085485275881476',
              '/message/491085485275881476',
              '/account/messages/2',
              '/k/house-cleaning/near-me',
              '/k/house-cleaning/near-me?sort=highest_rated',
              '/wa/kirkland/house-cleaning/empire-cleaning-services/service/476683242989297681',
              '/message/476683242989297681',
              '/account/messages/3']},
 4: {'answer': 'Lowest quote on the TV mounting project was $121 from Wa Pro Builders Llc, with 5 quotes total; '
               'project cancelled; replacement handyman request started in 98033 for hanging a heavy mirror.',
     'urls': ['/',
              '/login',
              '/account',
              '/projects/2',
              '/k/handyman/near-me',
              '/projects/new?category=handyman',
              '/projects/6']},
 5: {'answer': 'Updated my profile zip to 98033 and my Kirkland address. The highest-rated lawn care professional '
               'serving Kirkland is Slc - Simple Lawn Care (4.8, 65 reviews); requested a quote for weekly mowing '
               'service.',
     'urls': ['/',
              '/login',
              '/account',
              '/account/profile',
              '/near-me',
              '/k/lawn-care/near-me',
              '/k/lawn-care/near-me?sort=highest_rated',
              '/wa/kirkland/lawn-care/slc-simple-lawn-care/service/230942537935791237',
              '/projects/new?category=lawn-care&pro=230942537935791237&zip=98052',
              '/projects/6']},
 6: {'answer': 'Velichkoremodels Llc Emergency Restoration 24/7 is the highest-rated plumber who is background '
               'checked and accepts Venmo; I saved them to my saved pros and messaged about the urgent leak — '
               'they replied: "Hi! For a job like this we can usually be there same-day or next-day. Please avoid '
               'using that fixture until we\'ve had a look." I requested a pipe-repair quote within a week '
               "describing the leaky kitchen faucet; the lowest quote was $51, which sits below the cost guide's "
               'typical range of $50 - $200 per hour for plumbers.',
     'urls': ['/',
              '/login',
              '/account',
              '/k/affordable-plumbing-services/near-me',
              '/k/affordable-plumbing-services/near-me?sort=highest_rated',
              '/wa/everett/affordable-plumbing-services/velichkoremodels-llc-emergency-restoration-247/service/550902459815264257',
              '/message/550902459815264257',
              '/account/messages/2',
              '/projects/new?category=affordable-plumbing-services&pro=550902459815264257&zip=98052',
              '/projects/6',
              '/prices',
              '/p/plumbers-cost']},
 7: {'answer': '4 pros responded to the wardrobe-and-two-bookcases assembly request in zip 98101; the cheapest '
               'quote was $107. I hired that pro, marked the project complete and left a 5-star review mentioning '
               'the smooth assembly.',
     'urls': ['/',
              '/register',
              '/account',
              '/k/furniture-assembly/near-me',
              '/projects/new?category=furniture-assembly',
              '/projects/6',
              '/projects/6/review']},
 8: {'answer': 'Two handymen with Sunday business hours: Evergreen Home Assist Llc (12 reviews, Sun 8:00 am - '
               '8:00 pm) and I.d. Handyman (56 reviews, Sun 12:00 am - 11:59 pm). I saved both, messaged the '
               'more-reviewed one (I.d. Handyman) about a Sunday visit — reply: "Hi! Thanks for reaching out. We '
               'do have openings — could you share a couple of dates that work for you?" — and followed up asking '
               'which Sunday time slots they have open — reply: "Hi! Thanks for reaching out. We do have openings '
               '— could you share a couple of dates that work for you?" Then I removed Evergreen Home Assist from '
               'my saved list.',
     'urls': ['/',
              '/login',
              '/account',
              '/k/handyman/near-me',
              '/wa/seattle/handyman/shark-style-llc/service/462308720949968896',
              '/wa/mountlake-terrace/handyman/evergreen-home-assist-llc/service/559530045965762575',
              '/wa/lynnwood/handyman/id-handyman/service/557383931483373571',
              '/message/557383931483373571',
              '/account/messages/2',
              '/account/saved']},
 9: {'answer': 'According to the cost guide, most people pay $174 - $256 for a one-time house cleaning visit. I '
               'requested a one-time deep-cleaning quote for my 3-bedroom, 2-bathroom home in zip 98101; the '
               'cheapest quote was $184 from Ipanema Cleaning Service, whom I hired, marked complete and left a '
               "5-star review. Their price falls inside the guide's typical range.",
     'urls': ['/',
              '/login',
              '/account',
              '/prices',
              '/p/house-cleaning-prices',
              '/k/house-cleaning/near-me',
              '/projects/new?category=house-cleaning',
              '/projects/6',
              '/projects/6/review']},
 10: {'answer': 'Removed the two moving companies (At Moving and John Frank Moving Company) from my saved pros. '
                "My pending moving project's lowest quote was $199 from Strok Industries Moving Company, whose "
                'profile shows Excellent 4.9 rating and "Responds within a day". I cancelled that project and '
                'started a much smaller studio-move replacement request in zip 98101, which received 5 quotes '
                'this time.',
      'urls': ['/',
               '/login',
               '/account',
               '/account/saved',
               '/projects/3',
               '/wa/kent/local-movers/strok-industries-moving-company/service/537096908478578695',
               '/k/local-movers/near-me',
               '/projects/new?category=local-movers',
               '/projects/6']},
 11: {'answer': 'A DJ is more expensive than a makeup artist: the DJ cost guide shows $500-$600 (national average '
                '$550) while makeup artists average $167 ($156 - $178). The highest-rated Top Pro makeup artist '
                'based in Redmond is Mel Mua (4.9, 71 reviews, Top Pro); I messaged her about the October event '
                'and she replied: "Hi! I\'d love to do your makeup — tell me the date and location and I\'ll '
                'check my calendar. Trials are available too." I then requested an estimate from her describing '
                'the quinceañera makeup for my daughter.',
      'urls': ['/',
               '/login',
               '/account',
               '/prices',
               '/p/makeup-artist-prices',
               '/p/wedding-djs-cost',
               '/k/makeup-artists/near-me',
               '/k/makeup-artists/near-me?sort=highest_rated',
               '/wa/redmond/makeup-artists/mel-mua/service/549098172844007430',
               '/message/549098172844007430',
               '/account/messages/2',
               '/projects/new?category=makeup-artists&pro=549098172844007430&zip=98052',
               '/projects/6']},
 12: {'answer': 'My finished house cleaning project hired Empire Cleaning Services at $244; their response note '
                'was "Thanks for the details! This is our estimate for the scope you described; we can adjust '
                'after an on-site visit." Their profile already had good reviews, and after I left a 5-star '
                'review saying they were thorough — the house is spotless — my review shows as the most recent '
                'one on their profile. I messaged asking whether they could return for a move-out clean next '
                'month — reply: "Hi! We\'d love to help. Deep cleans for a home your size usually take our team '
                '3-4 hours." — and followed up about supplies — reply: "Hi! We bring all of our own supplies and '
                'equipment — you don\'t need to prepare anything except access to the rooms."',
      'urls': ['/',
               '/login',
               '/account',
               '/projects/1',
               '/wa/kirkland/house-cleaning/empire-cleaning-services/service/476683242989297681',
               '/projects/1/review',
               '/message/476683242989297681',
               '/account/messages/2']},
 13: {'answer': 'In my existing thread, Ipanema Cleaning Service said: "Hi! We bring all of our own supplies and '
                'equipment — you don\'t need to prepare anything except access to the rooms." The second cleaner, '
                'Empire Cleaning Services, answered the same question the same way — "Hi! We bring all of our own '
                'supplies and equipment — you don\'t need to prepare anything except access to the rooms." — so '
                'both bring all their own supplies and equipment. On Sunday availability, Empire replied: "Thanks '
                "for reaching out! We're happy to work around your schedule — including weekends. Which day works "
                'best?" and Ipanema replied: "Thanks for reaching out! We\'re happy to work around your schedule '
                '— including weekends. Which day works best?" — both cleaners offer weekend/Sunday scheduling, so '
                'their answers match on both questions.',
      'urls': ['/',
               '/login',
               '/account',
               '/account/messages/1',
               '/k/house-cleaning/near-me',
               '/k/house-cleaning/near-me?sort=highest_rated',
               '/wa/kirkland/house-cleaning/empire-cleaning-services/service/476683242989297681',
               '/message/476683242989297681',
               '/account/messages/2']},
 14: {'answer': 'An exterminator typically runs $131 - $341 according to the cost guide. I requested indoor ant '
                'treatment quotes within a week in zip 98101 from the Top Pro exterminators and hired the '
                'responder with the most reviews: Super Attic Solutions (123 reviews), who quoted $315. I marked '
                'the project complete, left a 5-star review mentioning the ants, and confirmed on their profile '
                'that my review shows as the most recent one.',
      'urls': ['/',
               '/login',
               '/account',
               '/prices',
               '/p/exterminators-prices',
               '/k/exterminators/near-me',
               '/projects/new?category=exterminators',
               '/projects/6',
               '/projects/6/review',
               '/wa/kirkland/exterminators/super-attic-solutions/service/472430256251617281']},
 15: {'answer': 'The Kirkland house cleaner with the most reviews is Empire Cleaning Services (33 reviews). '
                'Messaged them asking whether they bring their own supplies; they replied that they bring all of '
                'their own supplies and equipment. Requested a quote from them for a standard cleaning of my '
                '3-bedroom home.',
      'urls': ['/',
               '/login',
               '/account',
               '/wa/kirkland',
               '/wa/kirkland/house-cleaning/empire-cleaning-services/service/476683242989297681',
               '/message/476683242989297681',
               '/account/messages/2',
               '/projects/new?category=house-cleaning&pro=476683242989297681&zip=98033',
               '/projects/6']},
 16: {'answer': 'Personal training sessions typically cost $40 - $100 (national average $55) according to the '
                'cost guide. The highest-rated personal trainer based in Bellevue is Gaskill Personal Training '
                '(5.0, 34 reviews); I messaged them to confirm twice-a-week slots and they replied: "Hi! Great '
                'timing — I have morning and evening slots open. Twice a week is a perfect pace to start." I then '
                'requested a quote from them describing twice-a-week strength sessions.',
      'urls': ['/',
               '/login',
               '/account',
               '/prices',
               '/p/personal-trainer-cost',
               '/k/personal-trainers/near-me',
               '/k/personal-trainers/near-me?sort=highest_rated',
               '/wa/bellevue/personal-trainers/gaskill-personal-training/service/285389944820876322',
               '/message/285389944820876322',
               '/account/messages/2',
               '/projects/new?category=personal-trainers&pro=285389944820876322&zip=98052',
               '/projects/6']},
 17: {'answer': '4 pros responded to the TV mounting request; the lowest quote was $127, and I hired that pro '
                '(Mmy). I marked the project complete and left them a 5-star review mentioning the tidy cable '
                'work.',
      'urls': ['/',
               '/login',
               '/account',
               '/k/tv-wall-mount-install/near-me',
               '/projects/new?category=tv-wall-mount-install',
               '/projects/6',
               '/projects/6/review']},
 18: {'answer': 'The top makeup artist by Most hires is Mel Mua with 121 hires and 71 reviews. Her profile shows '
                'Top Pro status and "Responds in about 28 min". I messaged her about availability for an October '
                '18 event — reply: "Hi! I\'d love to do your makeup — tell me the date and location and I\'ll '
                'check my calendar. Trials are available too." — and followed up about a pre-event trial — reply: '
                '"Hi! I\'d love to do your makeup — tell me the date and location and I\'ll check my calendar. '
                'Trials are available too." — then saved her to my saved pros.',
      'urls': ['/',
               '/login',
               '/account',
               '/near-me',
               '/k/makeup-artists/near-me',
               '/k/makeup-artists/near-me?sort=most_hires',
               '/wa/redmond/makeup-artists/mel-mua/service/549098172844007430',
               '/message/549098172844007430',
               '/account/messages/2']},
 19: {'answer': 'The appliance repair specialist who responds fastest is Hotwire Hvac Refrigeration & Appliance '
                'Repair (responds in about 1 min). I requested an emergency quote describing the GE refrigerator '
                'repair; the lowest quote I received was $130, and I hired that pro and left them a 5-star review '
                'mentioning the refrigerator.',
      'urls': ['/',
               '/login',
               '/account',
               '/k/appliance-repair/near-me',
               '/k/appliance-repair/near-me?sort=fastest_response',
               '/wa/woodinville/appliance-repair/hotwire-hvac-refrigeration-appliance-repair/service/500453696558571522',
               '/projects/new?category=appliance-repair&pro=500453696558571522&zip=98052',
               '/projects/6',
               '/projects/6/review']}}
MUTATIONS = {0: ['INSERT INTO "saved_pros" ("id", "user_id", "pro_id", "created_at") VALUES (14, 1, 169, \'2026-09-26 '
     "12:00:00.000000');"],
 1: ['INSERT INTO "projects" ("id", "user_id", "category_id", "zip", "details", "timeline", "answers", "status", '
     '"created_at") VALUES (6, 2, 1, \'98101\', \'Deep clean before move-out next month.\', \'Within a week\', '
     '\'[["Frequency", "Just once"], ["Number of bedrooms", "2 bedrooms"], ["Cleaning type", "Deep cleaning"], '
     '["Number of bathrooms", "2 bathrooms"]]\', \'completed\', \'2026-09-26 12:00:00.000000\');',
     'INSERT INTO "reviews" ("id", "pro_id", "author", "date_str", "rating", "body", "details", "hired", '
     '"source") VALUES (857, 66, \'Bob Chen\', \'Sep 26, 2026\', 5, \'They were thorough and the place is '
     "spotless — perfect move-out deep clean. 5 stars!', 'project:6', 1, 'user');",
     'INSERT INTO "project_matches" ("id", "project_id", "pro_id", "responded", "quote_amount", "response_note", '
     '"responded_min", "hired") VALUES (26, 6, 73, 1, 191, \'Thanks for the details! This is our estimate for the '
     "scope you described; we can adjust after an on-site visit.', 1440, 0);",
     'INSERT INTO "project_matches" ("id", "project_id", "pro_id", "responded", "quote_amount", "response_note", '
     '"responded_min", "hired") VALUES (27, 6, 66, 1, 184, \'Thanks for the details! This is our estimate for the '
     "scope you described; we can adjust after an on-site visit.', 1440, 1);",
     'INSERT INTO "project_matches" ("id", "project_id", "pro_id", "responded", "quote_amount", "response_note", '
     '"responded_min", "hired") VALUES (28, 6, 76, 1, 244, \'We\'\'d love to take this on. The quote reflects the '
     "timeline you asked for, and we can start right away.', 240, 0);",
     'INSERT INTO "project_matches" ("id", "project_id", "pro_id", "responded", "quote_amount", "response_note", '
     '"responded_min", "hired") VALUES (29, 6, 67, 1, 245, \'Thanks for the details! This is our estimate for the '
     "scope you described; we can adjust after an on-site visit.', 1440, 0);",
     'INSERT INTO "project_matches" ("id", "project_id", "pro_id", "responded", "quote_amount", "response_note", '
     '"responded_min", "hired") VALUES (30, 6, 65, 1, 227, \'This is our all-in estimate — no hidden fees. Let me '
     "know if you''d like to adjust the scope.', 1440, 0);"],
 2: ['INSERT INTO "projects" ("id", "user_id", "category_id", "zip", "details", "timeline", "answers", "status", '
     '"created_at") VALUES (6, 3, 16, \'98004\', \'Please quote our four-hour wedding reception.\', \'Within 48 '
     'hours\', \'[["Duration", "4 hours"], ["Event type", "Wedding"]]\', \'matched\', \'2026-09-26 '
     "12:00:00.000000');",
     'INSERT INTO "project_matches" ("id", "project_id", "pro_id", "responded", "quote_amount", "response_note", '
     '"responded_min", "hired") VALUES (26, 6, 23, 1, 527, \'Thanks for the details! This is our estimate for the '
     "scope you described; we can adjust after an on-site visit.', 1440, 0);",
     'INSERT INTO "project_matches" ("id", "project_id", "pro_id", "responded", "quote_amount", "response_note", '
     '"responded_min", "hired") VALUES (27, 6, 19, 1, 567, \'We\'\'d love to take this on. The quote reflects the '
     "timeline you asked for, and we can start right away.', 1440, 0);",
     'INSERT INTO "project_matches" ("id", "project_id", "pro_id", "responded", "quote_amount", "response_note", '
     '"responded_min", "hired") VALUES (28, 6, 20, 0, NULL, NULL, NULL, 0);',
     'INSERT INTO "project_matches" ("id", "project_id", "pro_id", "responded", "quote_amount", "response_note", '
     '"responded_min", "hired") VALUES (29, 6, 26, 1, 586, \'Appreciate you reaching out through Thumbtack! This '
     "quote includes everything we discussed.', 40, 0);",
     'INSERT INTO "project_matches" ("id", "project_id", "pro_id", "responded", "quote_amount", "response_note", '
     '"responded_min", "hired") VALUES (30, 6, 22, 1, 520, \'Happy to help — based on what you described, this '
     "quote covers labor and standard materials.', 120, 0);",
     'INSERT INTO "threads" ("id", "user_id", "pro_id", "project_id", "updated_at") VALUES (2, 3, 19, NULL, '
     "'2026-09-26 12:32:00.000000');",
     'INSERT INTO "messages" ("id", "thread_id", "sender", "body", "created_at") VALUES (3, 2, \'user\', \'Hi! '
     "Are you available for an October wedding date? We would love to have you DJ our reception.', '2026-09-26 "
     "12:30:00.000000');",
     'INSERT INTO "messages" ("id", "thread_id", "sender", "body", "created_at") VALUES (4, 2, \'pro\', \'Hi! '
     "We''d love to be part of it — tell me the date and venue and I''ll confirm availability right away.', "
     "'2026-09-26 12:32:00.000000');"],
 3: ['INSERT INTO "threads" ("id", "user_id", "pro_id", "project_id", "updated_at") VALUES (2, 1, 71, NULL, '
     "'2026-09-26 12:32:00.000000');",
     'INSERT INTO "threads" ("id", "user_id", "pro_id", "project_id", "updated_at") VALUES (3, 1, 65, NULL, '
     "'2026-09-26 12:32:00.000000');",
     'INSERT INTO "messages" ("id", "thread_id", "sender", "body", "created_at") VALUES (3, 2, \'user\', \'Hi '
     "Paty! Do you bring your own cleaning supplies when you clean?', '2026-09-26 12:30:00.000000');",
     'INSERT INTO "messages" ("id", "thread_id", "sender", "body", "created_at") VALUES (4, 2, \'pro\', \'Hi! We '
     "bring all of our own supplies and equipment — you don''t need to prepare anything except access to the "
     "rooms.', '2026-09-26 12:32:00.000000');",
     'INSERT INTO "messages" ("id", "thread_id", "sender", "body", "created_at") VALUES (5, 3, \'user\', \'Hi! Do '
     "you bring your own cleaning supplies when you clean?', '2026-09-26 12:30:00.000000');",
     'INSERT INTO "messages" ("id", "thread_id", "sender", "body", "created_at") VALUES (6, 3, \'pro\', \'Hi! We '
     "bring all of our own supplies and equipment — you don''t need to prepare anything except access to the "
     "rooms.', '2026-09-26 12:32:00.000000');",
     'INSERT INTO "messages" ("id", "thread_id", "sender", "body", "created_at") VALUES (7, 2, \'user\', \'Could '
     "you come on a Sunday? That would work best for my schedule.', '2026-09-26 12:30:00.000000');",
     'INSERT INTO "messages" ("id", "thread_id", "sender", "body", "created_at") VALUES (8, 2, \'pro\', \'Thanks '
     "for reaching out! We''re happy to work around your schedule — including weekends. Which day works best?', "
     "'2026-09-26 12:32:00.000000');"],
 4: ['DELETE FROM "projects" WHERE "id"=2;',
     'INSERT INTO "projects" ("id", "user_id", "category_id", "zip", "details", "timeline", "answers", "status", '
     '"created_at") VALUES (2, 1, 8, \'98052\', \'Mount a 65" TV above the fireplace and hide the cables.\', '
     '\'Within 48 hours\', \'[["TV size", "TV larger than 60 inches"], ["Wall type", "Drywall"], ["Mount type", '
     '"Tilt (angled up or down)"]]\', \'cancelled\', \'2026-09-26 12:00:00.000000\');',
     'INSERT INTO "projects" ("id", "user_id", "category_id", "zip", "details", "timeline", "answers", "status", '
     '"created_at") VALUES (6, 1, 4, \'98033\', \'Need a handyman to hang a heavy mirror on drywall.\', \'Within '
     "48 hours', '[]', 'matched', '2026-09-26 12:00:00.000000');",
     'INSERT INTO "project_matches" ("id", "project_id", "pro_id", "responded", "quote_amount", "response_note", '
     '"responded_min", "hired") VALUES (26, 6, 61, 1, 80, \'Happy to help — based on what you described, this '
     "quote covers labor and standard materials.', 23, 0);",
     'INSERT INTO "project_matches" ("id", "project_id", "pro_id", "responded", "quote_amount", "response_note", '
     '"responded_min", "hired") VALUES (27, 6, 55, 1, 68, \'We\'\'d love to take this on. The quote reflects the '
     "timeline you asked for, and we can start right away.', 60, 0);",
     'INSERT INTO "project_matches" ("id", "project_id", "pro_id", "responded", "quote_amount", "response_note", '
     '"responded_min", "hired") VALUES (28, 6, 63, 1, 77, \'This is our all-in estimate — no hidden fees. Let me '
     "know if you''d like to adjust the scope.', 1440, 0);",
     'INSERT INTO "project_matches" ("id", "project_id", "pro_id", "responded", "quote_amount", "response_note", '
     '"responded_min", "hired") VALUES (29, 6, 54, 1, 75, \'We\'\'d love to take this on. The quote reflects the '
     "timeline you asked for, and we can start right away.', 60, 0);",
     'INSERT INTO "project_matches" ("id", "project_id", "pro_id", "responded", "quote_amount", "response_note", '
     '"responded_min", "hired") VALUES (30, 6, 59, 1, 62, \'Happy to help — based on what you described, this '
     "quote covers labor and standard materials.', 1440, 0);"],
 5: ['DELETE FROM "users" WHERE "id"=3;',
     'INSERT INTO "users" ("id", "username", "email", "display_name", "password_hash", "phone", "zip", "address", '
     '"created_at") VALUES (3, \'carol_d\', \'carol.d@test.com\', \'Carol Davis\', '
     "'$2b$12$qSds4Mr9Wo7VwPWLhompEer88SuxxXFDp31P9etY6v7nfRctNO7B.', '(425) 555-0117', '98033', '123 Main St, "
     "Kirkland, WA', '2026-09-26 12:00:00.000000');",
     'INSERT INTO "projects" ("id", "user_id", "category_id", "zip", "details", "timeline", "answers", "status", '
     '"created_at") VALUES (6, 3, 5, \'98033\', \'Looking for weekly mowing service in Kirkland.\', \'Within a '
     "week', '[]', 'matched', '2026-09-26 12:00:00.000000');",
     'INSERT INTO "project_matches" ("id", "project_id", "pro_id", "responded", "quote_amount", "response_note", '
     '"responded_min", "hired") VALUES (26, 6, 105, 1, 255, \'This is our all-in estimate — no hidden fees. Let '
     "me know if you''d like to adjust the scope.', 1440, 0);",
     'INSERT INTO "project_matches" ("id", "project_id", "pro_id", "responded", "quote_amount", "response_note", '
     '"responded_min", "hired") VALUES (27, 6, 106, 0, NULL, NULL, NULL, 0);',
     'INSERT INTO "project_matches" ("id", "project_id", "pro_id", "responded", "quote_amount", "response_note", '
     '"responded_min", "hired") VALUES (28, 6, 112, 1, 407, \'This is our all-in estimate — no hidden fees. Let '
     "me know if you''d like to adjust the scope.', 1, 0);",
     'INSERT INTO "project_matches" ("id", "project_id", "pro_id", "responded", "quote_amount", "response_note", '
     '"responded_min", "hired") VALUES (29, 6, 107, 1, 194, \'We\'\'d love to take this on. The quote reflects '
     "the timeline you asked for, and we can start right away.', 1440, 0);",
     'INSERT INTO "project_matches" ("id", "project_id", "pro_id", "responded", "quote_amount", "response_note", '
     '"responded_min", "hired") VALUES (30, 6, 110, 1, 378, \'This is our all-in estimate — no hidden fees. Let '
     "me know if you''d like to adjust the scope.', 1440, 0);"],
 6: ['INSERT INTO "projects" ("id", "user_id", "category_id", "zip", "details", "timeline", "answers", "status", '
     '"created_at") VALUES (6, 4, 2, \'98033\', \'My kitchen faucet has been dripping for a week — please quote '
     'the leaky faucet repair.\', \'Within a week\', \'[["Select a service", "Plumbing Pipe Repair"]]\', '
     "'matched', '2026-09-26 12:00:00.000000');",
     'INSERT INTO "saved_pros" ("id", "user_id", "pro_id", "created_at") VALUES (14, 4, 6, \'2026-09-26 '
     "12:00:00.000000');",
     'INSERT INTO "project_matches" ("id", "project_id", "pro_id", "responded", "quote_amount", "response_note", '
     '"responded_min", "hired") VALUES (26, 6, 6, 1, 189, \'This is our all-in estimate — no hidden fees. Let me '
     "know if you''d like to adjust the scope.', 1, 0);",
     'INSERT INTO "project_matches" ("id", "project_id", "pro_id", "responded", "quote_amount", "response_note", '
     '"responded_min", "hired") VALUES (27, 6, 3, 1, 135, \'Happy to help — based on what you described, this '
     "quote covers labor and standard materials.', 120, 0);",
     'INSERT INTO "project_matches" ("id", "project_id", "pro_id", "responded", "quote_amount", "response_note", '
     '"responded_min", "hired") VALUES (28, 6, 1, 1, 51, \'We\'\'d love to take this on. The quote reflects the '
     "timeline you asked for, and we can start right away.', 1440, 0);",
     'INSERT INTO "project_matches" ("id", "project_id", "pro_id", "responded", "quote_amount", "response_note", '
     '"responded_min", "hired") VALUES (29, 6, 5, 1, 184, \'This is our all-in estimate — no hidden fees. Let me '
     "know if you''d like to adjust the scope.', 8, 0);",
     'INSERT INTO "project_matches" ("id", "project_id", "pro_id", "responded", "quote_amount", "response_note", '
     '"responded_min", "hired") VALUES (30, 6, 2, 1, 169, \'We\'\'d love to take this on. The quote reflects the '
     "timeline you asked for, and we can start right away.', 1, 0);",
     'INSERT INTO "threads" ("id", "user_id", "pro_id", "project_id", "updated_at") VALUES (2, 4, 6, NULL, '
     "'2026-09-26 12:32:00.000000');",
     'INSERT INTO "messages" ("id", "thread_id", "sender", "body", "created_at") VALUES (3, 2, \'user\', \'Hi! My '
     "kitchen faucet has been leaking for a week and it is urgent — can you handle the leak repair quickly?', "
     "'2026-09-26 12:30:00.000000');",
     'INSERT INTO "messages" ("id", "thread_id", "sender", "body", "created_at") VALUES (4, 2, \'pro\', \'Hi! For '
     "a job like this we can usually be there same-day or next-day. Please avoid using that fixture until we''ve "
     "had a look.', '2026-09-26 12:32:00.000000');"],
 7: ['INSERT INTO "users" ("id", "username", "email", "display_name", "password_hash", "phone", "zip", "address", '
     '"created_at") VALUES (5, \'nina.p\', \'nina.p@test.com\', \'Nina Patel\', '
     "'$2b$12$iv7XWaEer7mqxUiDUeVUjud59AdWsmSl9F9ZnQId865Oxo8CcnS.q', NULL, NULL, NULL, '2026-09-26 "
     "12:00:00.000000');",
     'INSERT INTO "projects" ("id", "user_id", "category_id", "zip", "details", "timeline", "answers", "status", '
     '"created_at") VALUES (6, 5, 9, \'98101\', \'Need assembly of a large wardrobe and two bookcases.\', '
     '\'Within 48 hours\', \'[["Number of items", "3 items"], ["Instructions or make/model provided by client?", '
     '"Yes, I have assembly instructions or make and model information"]]\', \'completed\', \'2026-09-26 '
     "12:00:00.000000');",
     'INSERT INTO "reviews" ("id", "pro_id", "author", "date_str", "rating", "body", "details", "hired", '
     '"source") VALUES (857, 52, \'Nina Patel\', \'Sep 26, 2026\', 5, \'Smooth assembly of the wardrobe and both '
     "bookcases — quick and careful work!', 'project:6', 1, 'user');",
     'INSERT INTO "project_matches" ("id", "project_id", "pro_id", "responded", "quote_amount", "response_note", '
     '"responded_min", "hired") VALUES (26, 6, 49, 1, 180, \'Thanks for the details! This is our estimate for the '
     "scope you described; we can adjust after an on-site visit.', 1440, 0);",
     'INSERT INTO "project_matches" ("id", "project_id", "pro_id", "responded", "quote_amount", "response_note", '
     '"responded_min", "hired") VALUES (27, 6, 44, 0, NULL, NULL, NULL, 0);',
     'INSERT INTO "project_matches" ("id", "project_id", "pro_id", "responded", "quote_amount", "response_note", '
     '"responded_min", "hired") VALUES (28, 6, 46, 1, 131, \'This is our all-in estimate — no hidden fees. Let me '
     "know if you''d like to adjust the scope.', 1440, 0);",
     'INSERT INTO "project_matches" ("id", "project_id", "pro_id", "responded", "quote_amount", "response_note", '
     '"responded_min", "hired") VALUES (29, 6, 52, 1, 107, \'Thanks for the details! This is our estimate for the '
     "scope you described; we can adjust after an on-site visit.', 1440, 1);",
     'INSERT INTO "project_matches" ("id", "project_id", "pro_id", "responded", "quote_amount", "response_note", '
     '"responded_min", "hired") VALUES (30, 6, 50, 1, 144, \'Thanks for the details! This is our estimate for the '
     "scope you described; we can adjust after an on-site visit.', 1440, 0);"],
 8: ['INSERT INTO "saved_pros" ("id", "user_id", "pro_id", "created_at") VALUES (14, 1, 55, \'2026-09-26 '
     "12:00:00.000000');",
     'INSERT INTO "threads" ("id", "user_id", "pro_id", "project_id", "updated_at") VALUES (2, 1, 55, NULL, '
     "'2026-09-26 12:32:00.000000');",
     'INSERT INTO "messages" ("id", "thread_id", "sender", "body", "created_at") VALUES (3, 2, \'user\', \'Hi! '
     "Can you do a Sunday visit for a small handyman job?', '2026-09-26 12:30:00.000000');",
     'INSERT INTO "messages" ("id", "thread_id", "sender", "body", "created_at") VALUES (4, 2, \'pro\', \'Hi! '
     "Thanks for reaching out. We do have openings — could you share a couple of dates that work for you?', "
     "'2026-09-26 12:32:00.000000');",
     'INSERT INTO "messages" ("id", "thread_id", "sender", "body", "created_at") VALUES (5, 2, \'user\', \'Which '
     "Sunday time slots do you have open?', '2026-09-26 12:30:00.000000');",
     'INSERT INTO "messages" ("id", "thread_id", "sender", "body", "created_at") VALUES (6, 2, \'pro\', \'Hi! '
     "Thanks for reaching out. We do have openings — could you share a couple of dates that work for you?', "
     "'2026-09-26 12:32:00.000000');"],
 9: ['INSERT INTO "projects" ("id", "user_id", "category_id", "zip", "details", "timeline", "answers", "status", '
     '"created_at") VALUES (6, 2, 1, \'98101\', \'Deep cleaning for a 3-bedroom, 2-bathroom home.\', \'Within 48 '
     'hours\', \'[["Frequency", "Just once"], ["Number of bedrooms", "3 bedrooms"], ["Cleaning type", "Deep '
     'cleaning"], ["Number of bathrooms", "2 bathrooms"]]\', \'completed\', \'2026-09-26 12:00:00.000000\');',
     'INSERT INTO "reviews" ("id", "pro_id", "author", "date_str", "rating", "body", "details", "hired", '
     '"source") VALUES (857, 66, \'Bob Chen\', \'Sep 26, 2026\', 5, \'Excellent deep clean — thorough, '
     "professional and quick!', 'project:6', 1, 'user');",
     'INSERT INTO "project_matches" ("id", "project_id", "pro_id", "responded", "quote_amount", "response_note", '
     '"responded_min", "hired") VALUES (26, 6, 73, 1, 191, \'Thanks for the details! This is our estimate for the '
     "scope you described; we can adjust after an on-site visit.', 1440, 0);",
     'INSERT INTO "project_matches" ("id", "project_id", "pro_id", "responded", "quote_amount", "response_note", '
     '"responded_min", "hired") VALUES (27, 6, 66, 1, 184, \'Thanks for the details! This is our estimate for the '
     "scope you described; we can adjust after an on-site visit.', 1440, 1);",
     'INSERT INTO "project_matches" ("id", "project_id", "pro_id", "responded", "quote_amount", "response_note", '
     '"responded_min", "hired") VALUES (28, 6, 76, 1, 244, \'We\'\'d love to take this on. The quote reflects the '
     "timeline you asked for, and we can start right away.', 240, 0);",
     'INSERT INTO "project_matches" ("id", "project_id", "pro_id", "responded", "quote_amount", "response_note", '
     '"responded_min", "hired") VALUES (29, 6, 67, 1, 245, \'Thanks for the details! This is our estimate for the '
     "scope you described; we can adjust after an on-site visit.', 1440, 0);",
     'INSERT INTO "project_matches" ("id", "project_id", "pro_id", "responded", "quote_amount", "response_note", '
     '"responded_min", "hired") VALUES (30, 6, 65, 1, 227, \'This is our all-in estimate — no hidden fees. Let me '
     "know if you''d like to adjust the scope.', 1440, 0);"],
 10: ['DELETE FROM "projects" WHERE "id"=3;',
      'INSERT INTO "projects" ("id", "user_id", "category_id", "zip", "details", "timeline", "answers", "status", '
      '"created_at") VALUES (3, 2, 15, \'98101\', \'Move a 2-bedroom apartment from Seattle to Bellevue, one '
      'flight of stairs.\', \'Within a week\', \'[["Move distance", "Local (under 50 miles)"], ["Home size", "2 '
      'bedrooms"]]\', \'cancelled\', \'2026-09-26 12:00:00.000000\');',
      'INSERT INTO "projects" ("id", "user_id", "category_id", "zip", "details", "timeline", "answers", "status", '
      '"created_at") VALUES (6, 2, 15, \'98101\', \'Much smaller studio apartment move within Seattle.\', '
      '\'Within 48 hours\', \'[["Move size", "Studio"]]\', \'matched\', \'2026-09-26 12:00:00.000000\');',
      'DELETE FROM "saved_pros" WHERE "id"=4;',
      'DELETE FROM "saved_pros" WHERE "id"=5;',
      'INSERT INTO "project_matches" ("id", "project_id", "pro_id", "responded", "quote_amount", "response_note", '
      '"responded_min", "hired") VALUES (26, 6, 119, 1, 274, \'We\'\'d love to take this on. The quote reflects '
      "the timeline you asked for, and we can start right away.', 1440, 0);",
      'INSERT INTO "project_matches" ("id", "project_id", "pro_id", "responded", "quote_amount", "response_note", '
      '"responded_min", "hired") VALUES (27, 6, 117, 1, 174, \'Thanks for the details! This is our estimate for '
      "the scope you described; we can adjust after an on-site visit.', 32, 0);",
      'INSERT INTO "project_matches" ("id", "project_id", "pro_id", "responded", "quote_amount", "response_note", '
      '"responded_min", "hired") VALUES (28, 6, 115, 1, 224, \'Happy to help — based on what you described, this '
      "quote covers labor and standard materials.', 1440, 0);",
      'INSERT INTO "project_matches" ("id", "project_id", "pro_id", "responded", "quote_amount", "response_note", '
      '"responded_min", "hired") VALUES (29, 6, 124, 1, 233, \'This is our all-in estimate — no hidden fees. Let '
      "me know if you''d like to adjust the scope.', 1440, 0);",
      'INSERT INTO "project_matches" ("id", "project_id", "pro_id", "responded", "quote_amount", "response_note", '
      '"responded_min", "hired") VALUES (30, 6, 118, 1, 261, \'This is our all-in estimate — no hidden fees. Let '
      "me know if you''d like to adjust the scope.', 2, 0);"],
 11: ['INSERT INTO "projects" ("id", "user_id", "category_id", "zip", "details", "timeline", "answers", "status", '
      '"created_at") VALUES (6, 3, 12, \'98004\', \'Quinceañera makeup for my daughter — please quote the event '
      'makeup.\', \'Within 48 hours\', \'[["Event type", "Birthday party"], ["Subject age", "13 - 17 years '
      'old"]]\', \'matched\', \'2026-09-26 12:00:00.000000\');',
      'INSERT INTO "project_matches" ("id", "project_id", "pro_id", "responded", "quote_amount", "response_note", '
      '"responded_min", "hired") VALUES (26, 6, 129, 1, 159, \'We\'\'d love to take this on. The quote reflects '
      "the timeline you asked for, and we can start right away.', 5, 0);",
      'INSERT INTO "project_matches" ("id", "project_id", "pro_id", "responded", "quote_amount", "response_note", '
      '"responded_min", "hired") VALUES (27, 6, 130, 1, 162, \'Happy to help — based on what you described, this '
      "quote covers labor and standard materials.', 28, 0);",
      'INSERT INTO "project_matches" ("id", "project_id", "pro_id", "responded", "quote_amount", "response_note", '
      '"responded_min", "hired") VALUES (28, 6, 128, 1, 156, \'Thanks for the details! This is our estimate for '
      "the scope you described; we can adjust after an on-site visit.', 1440, 0);",
      'INSERT INTO "project_matches" ("id", "project_id", "pro_id", "responded", "quote_amount", "response_note", '
      '"responded_min", "hired") VALUES (29, 6, 131, 1, 158, \'Appreciate you reaching out through Thumbtack! '
      "This quote includes everything we discussed.', 1440, 0);",
      'INSERT INTO "project_matches" ("id", "project_id", "pro_id", "responded", "quote_amount", "response_note", '
      '"responded_min", "hired") VALUES (30, 6, 127, 1, 177, \'Thanks for the details! This is our estimate for '
      "the scope you described; we can adjust after an on-site visit.', 43, 0);",
      'INSERT INTO "threads" ("id", "user_id", "pro_id", "project_id", "updated_at") VALUES (2, 3, 130, NULL, '
      "'2026-09-26 12:32:00.000000');",
      'INSERT INTO "messages" ("id", "thread_id", "sender", "body", "created_at") VALUES (3, 2, \'user\', \'Hi '
      "Mel! Are you available for an October event? It is my daughter''s quinceañera.', '2026-09-26 "
      "12:30:00.000000');",
      'INSERT INTO "messages" ("id", "thread_id", "sender", "body", "created_at") VALUES (4, 2, \'pro\', \'Hi! '
      "I''d love to do your makeup — tell me the date and location and I''ll check my calendar. Trials are "
      "available too.', '2026-09-26 12:32:00.000000');"],
 12: ['INSERT INTO "reviews" ("id", "pro_id", "author", "date_str", "rating", "body", "details", "hired", '
      '"source") VALUES (857, 65, \'Alice Johnson\', \'Sep 26, 2026\', 5, \'They were thorough — the house is '
      "spotless. Great job!', 'project:1', 1, 'user');",
      'INSERT INTO "threads" ("id", "user_id", "pro_id", "project_id", "updated_at") VALUES (2, 1, 65, NULL, '
      "'2026-09-26 12:32:00.000000');",
      'INSERT INTO "messages" ("id", "thread_id", "sender", "body", "created_at") VALUES (3, 2, \'user\', \'Hi! '
      "Could you return for a move-out clean next month?', '2026-09-26 12:30:00.000000');",
      'INSERT INTO "messages" ("id", "thread_id", "sender", "body", "created_at") VALUES (4, 2, \'pro\', \'Hi! '
      "We''d love to help. Deep cleans for a home your size usually take our team 3-4 hours.', '2026-09-26 "
      "12:32:00.000000');",
      'INSERT INTO "messages" ("id", "thread_id", "sender", "body", "created_at") VALUES (5, 2, \'user\', \'Would '
      "you bring your own supplies for the move-out clean?', '2026-09-26 12:30:00.000000');",
      'INSERT INTO "messages" ("id", "thread_id", "sender", "body", "created_at") VALUES (6, 2, \'pro\', \'Hi! We '
      "bring all of our own supplies and equipment — you don''t need to prepare anything except access to the "
      "rooms.', '2026-09-26 12:32:00.000000');"],
 13: ['DELETE FROM "threads" WHERE "id"=1;',
      'INSERT INTO "threads" ("id", "user_id", "pro_id", "project_id", "updated_at") VALUES (1, 1, 66, NULL, '
      "'2026-09-26 12:32:00.000000');",
      'INSERT INTO "threads" ("id", "user_id", "pro_id", "project_id", "updated_at") VALUES (2, 1, 65, NULL, '
      "'2026-09-26 12:32:00.000000');",
      'INSERT INTO "messages" ("id", "thread_id", "sender", "body", "created_at") VALUES (3, 2, \'user\', \'Hi! '
      "Do you bring your own cleaning supplies, or should I have them ready?', '2026-09-26 12:30:00.000000');",
      'INSERT INTO "messages" ("id", "thread_id", "sender", "body", "created_at") VALUES (4, 2, \'pro\', \'Hi! We '
      "bring all of our own supplies and equipment — you don''t need to prepare anything except access to the "
      "rooms.', '2026-09-26 12:32:00.000000');",
      'INSERT INTO "messages" ("id", "thread_id", "sender", "body", "created_at") VALUES (5, 2, \'user\', \'Could '
      "you come on a Sunday? That would work best for me.', '2026-09-26 12:30:00.000000');",
      'INSERT INTO "messages" ("id", "thread_id", "sender", "body", "created_at") VALUES (6, 2, \'pro\', \'Thanks '
      "for reaching out! We''re happy to work around your schedule — including weekends. Which day works best?', "
      "'2026-09-26 12:32:00.000000');",
      'INSERT INTO "messages" ("id", "thread_id", "sender", "body", "created_at") VALUES (7, 1, \'user\', \'Could '
      "you come on a Sunday? That would work best for me.', '2026-09-26 12:30:00.000000');",
      'INSERT INTO "messages" ("id", "thread_id", "sender", "body", "created_at") VALUES (8, 1, \'pro\', \'Thanks '
      "for reaching out! We''re happy to work around your schedule — including weekends. Which day works best?', "
      "'2026-09-26 12:32:00.000000');"],
 14: ['INSERT INTO "projects" ("id", "user_id", "category_id", "zip", "details", "timeline", "answers", "status", '
      '"created_at") VALUES (6, 2, 11, \'98101\', \'Ants have invaded my kitchen — need indoor ant treatment.\', '
      '\'Within a week\', \'[["Select a service", "Pest Control Services"]]\', \'completed\', \'2026-09-26 '
      "12:00:00.000000');",
      'INSERT INTO "reviews" ("id", "pro_id", "author", "date_str", "rating", "body", "details", "hired", '
      '"source") VALUES (857, 38, \'Bob Chen\', \'Sep 26, 2026\', 5, \'They took care of the ants quickly and '
      "thoroughly — great service!', 'project:6', 1, 'user');",
      'INSERT INTO "project_matches" ("id", "project_id", "pro_id", "responded", "quote_amount", "response_note", '
      '"responded_min", "hired") VALUES (26, 6, 36, 1, 250, \'This is our all-in estimate — no hidden fees. Let '
      "me know if you''d like to adjust the scope.', 1440, 0);",
      'INSERT INTO "project_matches" ("id", "project_id", "pro_id", "responded", "quote_amount", "response_note", '
      '"responded_min", "hired") VALUES (27, 6, 40, 1, 170, \'This is our all-in estimate — no hidden fees. Let '
      "me know if you''d like to adjust the scope.', 1440, 0);",
      'INSERT INTO "project_matches" ("id", "project_id", "pro_id", "responded", "quote_amount", "response_note", '
      '"responded_min", "hired") VALUES (28, 6, 32, 1, 207, \'Happy to help — based on what you described, this '
      "quote covers labor and standard materials.', 180, 0);",
      'INSERT INTO "project_matches" ("id", "project_id", "pro_id", "responded", "quote_amount", "response_note", '
      '"responded_min", "hired") VALUES (29, 6, 41, 1, 137, \'We\'\'d love to take this on. The quote reflects '
      "the timeline you asked for, and we can start right away.', 240, 0);",
      'INSERT INTO "project_matches" ("id", "project_id", "pro_id", "responded", "quote_amount", "response_note", '
      '"responded_min", "hired") VALUES (30, 6, 38, 1, 315, \'Thanks for the details! This is our estimate for '
      "the scope you described; we can adjust after an on-site visit.', 1440, 1);"],
 15: ['INSERT INTO "projects" ("id", "user_id", "category_id", "zip", "details", "timeline", "answers", "status", '
      '"created_at") VALUES (6, 1, 1, \'98033\', \'Standard cleaning for my 3-bedroom home.\', \'Within a week\', '
      '\'[["Number of bedrooms", "3 bedrooms"]]\', \'matched\', \'2026-09-26 12:00:00.000000\');',
      'INSERT INTO "project_matches" ("id", "project_id", "pro_id", "responded", "quote_amount", "response_note", '
      '"responded_min", "hired") VALUES (26, 6, 73, 1, 191, \'Thanks for the details! This is our estimate for '
      "the scope you described; we can adjust after an on-site visit.', 1440, 0);",
      'INSERT INTO "project_matches" ("id", "project_id", "pro_id", "responded", "quote_amount", "response_note", '
      '"responded_min", "hired") VALUES (27, 6, 66, 1, 184, \'Thanks for the details! This is our estimate for '
      "the scope you described; we can adjust after an on-site visit.', 1440, 0);",
      'INSERT INTO "project_matches" ("id", "project_id", "pro_id", "responded", "quote_amount", "response_note", '
      '"responded_min", "hired") VALUES (28, 6, 76, 1, 244, \'We\'\'d love to take this on. The quote reflects '
      "the timeline you asked for, and we can start right away.', 240, 0);",
      'INSERT INTO "project_matches" ("id", "project_id", "pro_id", "responded", "quote_amount", "response_note", '
      '"responded_min", "hired") VALUES (29, 6, 67, 1, 245, \'Thanks for the details! This is our estimate for '
      "the scope you described; we can adjust after an on-site visit.', 1440, 0);",
      'INSERT INTO "project_matches" ("id", "project_id", "pro_id", "responded", "quote_amount", "response_note", '
      '"responded_min", "hired") VALUES (30, 6, 65, 1, 227, \'This is our all-in estimate — no hidden fees. Let '
      "me know if you''d like to adjust the scope.', 1440, 0);",
      'INSERT INTO "threads" ("id", "user_id", "pro_id", "project_id", "updated_at") VALUES (2, 1, 65, NULL, '
      "'2026-09-26 12:32:00.000000');",
      'INSERT INTO "messages" ("id", "thread_id", "sender", "body", "created_at") VALUES (3, 2, \'user\', \'Hi! '
      "Do you bring your own cleaning supplies?', '2026-09-26 12:30:00.000000');",
      'INSERT INTO "messages" ("id", "thread_id", "sender", "body", "created_at") VALUES (4, 2, \'pro\', \'Hi! We '
      "bring all of our own supplies and equipment — you don''t need to prepare anything except access to the "
      "rooms.', '2026-09-26 12:32:00.000000');"],
 16: ['INSERT INTO "projects" ("id", "user_id", "category_id", "zip", "details", "timeline", "answers", "status", '
      '"created_at") VALUES (6, 4, 14, \'98033\', \'Looking for twice-a-week strength training sessions this '
      'fall.\', \'Within 48 hours\', \'[["Frequency", "2-3 times a week"]]\', \'matched\', \'2026-09-26 '
      "12:00:00.000000');",
      'INSERT INTO "project_matches" ("id", "project_id", "pro_id", "responded", "quote_amount", "response_note", '
      '"responded_min", "hired") VALUES (26, 6, 136, 1, 67, \'This is our all-in estimate — no hidden fees. Let '
      "me know if you''d like to adjust the scope.', 1440, 0);",
      'INSERT INTO "project_matches" ("id", "project_id", "pro_id", "responded", "quote_amount", "response_note", '
      '"responded_min", "hired") VALUES (27, 6, 138, 1, 90, \'We\'\'d love to take this on. The quote reflects '
      "the timeline you asked for, and we can start right away.', 120, 0);",
      'INSERT INTO "project_matches" ("id", "project_id", "pro_id", "responded", "quote_amount", "response_note", '
      '"responded_min", "hired") VALUES (28, 6, 135, 1, 98, \'This is our all-in estimate — no hidden fees. Let '
      "me know if you''d like to adjust the scope.', 120, 0);",
      'INSERT INTO "project_matches" ("id", "project_id", "pro_id", "responded", "quote_amount", "response_note", '
      '"responded_min", "hired") VALUES (29, 6, 133, 1, 60, \'Thanks for the details! This is our estimate for '
      "the scope you described; we can adjust after an on-site visit.', 1440, 0);",
      'INSERT INTO "project_matches" ("id", "project_id", "pro_id", "responded", "quote_amount", "response_note", '
      '"responded_min", "hired") VALUES (30, 6, 137, 1, 68, \'Thanks for the details! This is our estimate for '
      "the scope you described; we can adjust after an on-site visit.', 1440, 0);",
      'INSERT INTO "threads" ("id", "user_id", "pro_id", "project_id", "updated_at") VALUES (2, 4, 136, NULL, '
      "'2026-09-26 12:32:00.000000');",
      'INSERT INTO "messages" ("id", "thread_id", "sender", "body", "created_at") VALUES (3, 2, \'user\', \'Hi! '
      "Do you have twice-a-week training slots available this fall? I want to build strength.', '2026-09-26 "
      "12:30:00.000000');",
      'INSERT INTO "messages" ("id", "thread_id", "sender", "body", "created_at") VALUES (4, 2, \'pro\', \'Hi! '
      "Great timing — I have morning and evening slots open. Twice a week is a perfect pace to start.', "
      "'2026-09-26 12:32:00.000000');"],
 17: ['INSERT INTO "projects" ("id", "user_id", "category_id", "zip", "details", "timeline", "answers", "status", '
      '"created_at") VALUES (6, 1, 8, \'98052\', \'Mount my 75-inch TV above the fireplace with the cables hidden '
      'and my sound bar connected.\', \'Within 48 hours\', \'[["Conceal cables/wires?", "Yes, I need to conceal '
      'cables and wires"], ["Sound system", "Sound bar"], ["TV installation location", "Wall mount above '
      'fireplace"]]\', \'completed\', \'2026-09-26 12:00:00.000000\');',
      'INSERT INTO "reviews" ("id", "pro_id", "author", "date_str", "rating", "body", "details", "hired", '
      '"source") VALUES (857, 160, \'Alice Johnson\', \'Sep 26, 2026\', 5, \'Tidy cable work — the TV looks great '
      "above the fireplace and the sound bar is perfect!', 'project:6', 1, 'user');",
      'INSERT INTO "project_matches" ("id", "project_id", "pro_id", "responded", "quote_amount", "response_note", '
      '"responded_min", "hired") VALUES (26, 6, 162, 1, 220, \'This is our all-in estimate — no hidden fees. Let '
      "me know if you''d like to adjust the scope.', 4, 0);",
      'INSERT INTO "project_matches" ("id", "project_id", "pro_id", "responded", "quote_amount", "response_note", '
      '"responded_min", "hired") VALUES (27, 6, 163, 0, NULL, NULL, NULL, 0);',
      'INSERT INTO "project_matches" ("id", "project_id", "pro_id", "responded", "quote_amount", "response_note", '
      '"responded_min", "hired") VALUES (28, 6, 160, 1, 127, \'Happy to help — based on what you described, this '
      "quote covers labor and standard materials.', 1440, 1);",
      'INSERT INTO "project_matches" ("id", "project_id", "pro_id", "responded", "quote_amount", "response_note", '
      '"responded_min", "hired") VALUES (29, 6, 161, 1, 173, \'Happy to help — based on what you described, this '
      "quote covers labor and standard materials.', 1440, 0);",
      'INSERT INTO "project_matches" ("id", "project_id", "pro_id", "responded", "quote_amount", "response_note", '
      '"responded_min", "hired") VALUES (30, 6, 159, 1, 187, \'Appreciate you reaching out through Thumbtack! '
      "This quote includes everything we discussed.', 1440, 0);"],
 18: ['INSERT INTO "saved_pros" ("id", "user_id", "pro_id", "created_at") VALUES (14, 3, 130, \'2026-09-26 '
      "12:00:00.000000');",
      'INSERT INTO "threads" ("id", "user_id", "pro_id", "project_id", "updated_at") VALUES (2, 3, 130, NULL, '
      "'2026-09-26 12:32:00.000000');",
      'INSERT INTO "messages" ("id", "thread_id", "sender", "body", "created_at") VALUES (3, 2, \'user\', \'Hi '
      "Mel! Are you available for an October 18 event?', '2026-09-26 12:30:00.000000');",
      'INSERT INTO "messages" ("id", "thread_id", "sender", "body", "created_at") VALUES (4, 2, \'pro\', \'Hi! '
      "I''d love to do your makeup — tell me the date and location and I''ll check my calendar. Trials are "
      "available too.', '2026-09-26 12:32:00.000000');",
      'INSERT INTO "messages" ("id", "thread_id", "sender", "body", "created_at") VALUES (5, 2, \'user\', \'Do '
      "you offer a pre-event trial session before the day?', '2026-09-26 12:30:00.000000');",
      'INSERT INTO "messages" ("id", "thread_id", "sender", "body", "created_at") VALUES (6, 2, \'pro\', \'Hi! '
      "I''d love to do your makeup — tell me the date and location and I''ll check my calendar. Trials are "
      "available too.', '2026-09-26 12:32:00.000000');"],
 19: ['INSERT INTO "projects" ("id", "user_id", "category_id", "zip", "details", "timeline", "answers", "status", '
      '"created_at") VALUES (6, 2, 6, \'98101\', \'Emergency: my GE refrigerator stopped cooling overnight and my '
      'food is spoiling — please quote the repair.\', \'Within 48 hours\', \'[["Appliance type", "Refrigerator"], '
      '["Appliance brand", "GE"]]\', \'completed\', \'2026-09-26 12:00:00.000000\');',
      'INSERT INTO "reviews" ("id", "pro_id", "author", "date_str", "rating", "body", "details", "hired", '
      '"source") VALUES (857, 18, \'Bob Chen\', \'Sep 26, 2026\', 5, \'Fast refrigerator repair — they saved my '
      "food! Great work.', 'project:6', 1, 'user');",
      'INSERT INTO "project_matches" ("id", "project_id", "pro_id", "responded", "quote_amount", "response_note", '
      '"responded_min", "hired") VALUES (26, 6, 11, 1, 275, \'Thanks for the details! This is our estimate for '
      "the scope you described; we can adjust after an on-site visit.', 1440, 0);",
      'INSERT INTO "project_matches" ("id", "project_id", "pro_id", "responded", "quote_amount", "response_note", '
      '"responded_min", "hired") VALUES (27, 6, 9, 1, 328, \'Appreciate you reaching out through Thumbtack! This '
      "quote includes everything we discussed.', 60, 0);",
      'INSERT INTO "project_matches" ("id", "project_id", "pro_id", "responded", "quote_amount", "response_note", '
      '"responded_min", "hired") VALUES (28, 6, 18, 1, 130, \'We\'\'d love to take this on. The quote reflects '
      "the timeline you asked for, and we can start right away.', 1440, 1);",
      'INSERT INTO "project_matches" ("id", "project_id", "pro_id", "responded", "quote_amount", "response_note", '
      '"responded_min", "hired") VALUES (29, 6, 17, 1, 319, \'Thanks for the details! This is our estimate for '
      "the scope you described; we can adjust after an on-site visit.', 1440, 0);",
      'INSERT INTO "project_matches" ("id", "project_id", "pro_id", "responded", "quote_amount", "response_note", '
      '"responded_min", "hired") VALUES (30, 6, 14, 1, 232, \'This is our all-in estimate — no hidden fees. Let '
      "me know if you''d like to adjust the scope.', 15, 0);"]}
