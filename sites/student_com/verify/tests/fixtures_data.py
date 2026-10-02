"""Frozen fixtures for the student_com verifier tests.

SPECS: per-task honest trajectories (action + URL sequences + final answers)
extracted verbatim from the reviewer's live Playwright walks of the review
container (wh-student-com-review); SQL: the exact DB after-state deltas the
site writes for that walk; WRONG_ANSWERS: plausible-but-wrong answers for
the adversarial negative tests. No LLM.
"""

BASE = "http://localhost:40107"

SPECS = {
    0: dict(
        steps=[('input', '/'), ('click', '/us/ga/atlanta/u/georgia-institute-of-technology'), ('click', '/us/ga/atlanta/u/georgia-institute-of-technology'), ('check', '/us/ga/atlanta/u/georgia-institute-of-technology'), ('input', '/us/ga/atlanta/u/georgia-institute-of-technology'), ('click', '/us/ga/atlanta/u/georgia-institute-of-technology?max_price=1200&type=Student+Community'), ('click', '/us/ga/atlanta/p/the-rive-atlanta-vbqacu'), ('click', '/us/ga/atlanta/p/the-rive-atlanta-vbqacu'), ('input', '/us/ga/atlanta/p/the-rive-atlanta-vbqacu'), ('input', '/us/ga/atlanta/p/the-rive-atlanta-vbqacu'), ('click', '/us/ga/atlanta/p/the-rive-atlanta-vbqacu'), ('click', '/us/ga/atlanta/p/the-rive-atlanta-vbqacu'), ('done', '/us/ga/atlanta/p/the-rive-atlanta-vbqacu')],
        answer="The Rive Atlanta — 0.7 miles from the Georgia Tech campus — offers amenities including a Gym and a Swimming Pool (also Games Room, Cinema Room, Rooftop Terrace, Wifi, Pet Friendly). Saved to alice.j@test.com's saved properties.",
        sql=['INSERT INTO property_views (user_id, session_key, property_slug, viewed_at) VALUES (NULL, "\'fixture-session\'", \'the-rive-atlanta-vbqacu\', \'2026-09-26 12:00:00\');', "INSERT INTO bookmarks (user_id, property_slug, created_at) VALUES (1, 'the-rive-atlanta-vbqacu', '2026-09-26 12:00:00');"],
    ),
    1: dict(
        steps=[('click', '/budget-calculator'), ('input', '/budget-calculator'), ('input', '/budget-calculator'), ('input', '/budget-calculator'), ('input', '/budget-calculator'), ('input', '/budget-calculator'), ('input', '/budget-calculator'), ('input', '/budget-calculator'), ('input', '/budget-calculator'), ('input', '/budget-calculator'), ('click', '/budget-calculator'), ('click', '/budget-calculator'), ('input', '/budget-calculator'), ('click', '/budget-calculator'), ('input', '/budget-calculator'), ('click', '/search?q=Georgia%20Institute%20of%20Technology'), ('done', '/search?q=Georgia%20Institute%20of%20Technology')],
        answer='Safety buffer: $420 (20% of the $2,100 monthly income). Comfortable monthly rent target: $670. At a monthly rent estimate of $800 you would have $290 left over per month and the calculator\'s verdict is \'Tight but doable\' (above the $670 comfortable target but still breaking even). Searching for Georgia Institute of Technology from the last step, the search results page lists 1 property (Georgia Heights).',
        sql=[],
    ),
    2: dict(
        steps=[('input', '/'), ('click', '/us/tx/austin/u/the-university-of-texas-at-austin'), ('click', '/us/tx/austin/u/the-university-of-texas-at-austin'), ('check', '/us/tx/austin/u/the-university-of-texas-at-austin'), ('click', '/us/tx/austin/u/the-university-of-texas-at-austin?type=Dorm'), ('click', '/us/tx/austin/p/littlefield-hall-kutkl0'), ('click', '/us/tx/austin/p/littlefield-hall-kutkl0'), ('input', '/us/tx/austin/p/littlefield-hall-kutkl0'), ('input', '/us/tx/austin/p/littlefield-hall-kutkl0'), ('click', '/us/tx/austin/p/littlefield-hall-kutkl0'), ('click', '/us/tx/austin/p/littlefield-hall-kutkl0'), ('input', '/us/tx/austin/p/littlefield-hall-kutkl0'), ('click', '/us/tx/austin/p/littlefield-hall-kutkl0'), ('click', '/us/tx/austin/p/littlefield-hall-kutkl0'), ('click', '/us/tx/austin/p/littlefield-hall-kutkl0'), ('click', '/profile/inquiries'), ('done', '/profile/inquiries')],
        answer='The cheapest dorm-style housing near The University of Texas at Austin is Littlefield Hall, starting at $935/mo, and the campus page lists 8 dorm-style homes. Its exact address is 2503 Whitis Ave, Austin, TX 78705, USA, and it offers (among others) Air Conditioning. Inquiry sent as bob.c@test.com with reference INQ-000005; My Inquiries shows it dated September 26, 2026 and Bob now has 2 inquiries in total.',
        sql=['INSERT INTO enquiries (id, user_id, property_slug, first_name, last_name, phone, email, message, marketing_consent, created_at) VALUES (5, 2, \'littlefield-hall-kutkl0\', \'Bob\', \'Chen\', \'(404) 555-0187\', \'bob.c@test.com\', \'Are rooms still available for the fall semester?\', 0, \'2026-09-26 12:00:00\');', 'INSERT INTO property_views (id, user_id, session_key, property_slug, viewed_at) VALUES (13, NULL, \'fixture-session\', \'littlefield-hall-kutkl0\', \'2026-09-26 12:00:00\');'],
    ),
    3: dict(
        steps=[('input', '/'), ('click', '/us/ga/atlanta/u/georgia-institute-of-technology'), ('input', '/us/ga/atlanta/u/georgia-institute-of-technology'), ('click', '/us/ga/atlanta/u/georgia-state-university'), ('click', '/us/ga/atlanta/p/freeman-ford-lofts-5bc863'), ('done', '/us/ga/atlanta/p/freeman-ford-lofts-5bc863')],
        answer='Two homes closest to Georgia Tech: International House (I-House) from $950/mo and Eighth Street Apartments from $1,411/mo. Two closest to Georgia State University: Piedmont Pad Apartments from $500/mo and Freeman Ford Lofts from $1,850/mo. The most expensive of the four is Freeman Ford Lofts, rated 4.7 with 36 Google reviews.',
        sql=['INSERT INTO property_views (user_id, session_key, property_slug, viewed_at) VALUES (NULL, "\'fixture-session\'", \'freeman-ford-lofts-5bc863\', \'2026-09-26 12:00:00\');'],
    ),
    4: dict(
        steps=[('click', '/'), ('input', '/'), ('input', '/'), ('click', '/'), ('click', '/'), ('click', '/profile/history'), ('click', '/us/ga/atlanta/p/eighth-street-apartments-z0rz15'), ('click', '/us/ga/atlanta/p/eighth-street-apartments-z0rz15'), ('click', '/us/ga/atlanta/p/eighth-street-apartments-z0rz15'), ('click', '/profile/bookmarks'), ('done', '/profile/bookmarks')],
        answer='Carol\'s Recently Viewed properties page lists 3 properties: Eighth Street Apartments, University House Midtown and Linea Midtown. The one she remembers is Eighth Street Apartments — $1,411/mo, 36 Google reviews, at 555 8th St NW, Atlanta, GA 30332, USA, rated 4.2. It also appears in the navbar\'s Recently Viewed dropdown, and Carol has 2 properties saved in total.',
        sql=['INSERT INTO property_views (id, user_id, session_key, property_slug, viewed_at) VALUES (13, 3, \'fixture-session\', \'eighth-street-apartments-z0rz15\', \'2026-09-26 12:00:00\');'],
    ),
    5: dict(
        steps=[('input', '/'), ('click', '/us/fl/gainesville'), ('click', '/us/fl/gainesville/internships'), ('click', '/us/fl/gainesville/internships?type=part-time'), ('click', '/jobs'), ('input', '/jobs'), ('click', '/us/fl/gainesville'), ('done', '/us/fl/gainesville')],
        answer='Gainesville lists 5 jobs in total. The newest posting is \'Medical Assistant - Post-Acute & SNF (Temporary)\' by Theoriamedical. 1 job is tagged part-time and 3 are tagged fellowship. The Part-Time filter shows \'Part-Time Assistant Manager - Level 2\' by Boxlunch. From the footer\'s Jobs page, the newest Austin job is \'Operations Associate (Part-Time) - Domain Austin\' by Aloyoga, and the Gainesville city page lists 15 properties.',
        sql=[],
    ),
    6: dict(
        steps=[('input', '/'), ('click', '/us/tx/austin'), ('click', '/us/tx/austin/u/the-university-of-texas-at-austin'), ('select', '/us/tx/austin/u/the-university-of-texas-at-austin?sort=rating'), ('done', '/us/tx/austin/u/the-university-of-texas-at-austin?sort=rating')],
        answer='The Austin FAQ says a non-US citizen needs an F-1 visa from a US embassy or consulate in their home country, and mentions rentals typically ranging $1,000–$1,600 per month. Student.com lists 30 properties in Austin; the popular college shown is The University of Texas at Austin. The average student will need $1,500–$2,500 per month excluding tuition; the Blanton Museum of Art is free for UT Austin students and the Texas State Capitol building offers free tours. The UT Austin homes page shows 20 out of 592 results; after sorting by rating, the highest-rated home is Carothers Residence Hall, from $1,560/mo with a 4.7 rating.',
        sql=[],
    ),
    7: dict(
        steps=[('click', '/'), ('input', '/'), ('input', '/'), ('click', '/'), ('click', '/'), ('click', '/profile/bookmarks'), ('click', '/profile/bookmarks'), ('input', '/profile/bookmarks'), ('click', '/us/oh/columbus/u/the-ohio-state-university'), ('select', '/us/oh/columbus/u/the-ohio-state-university?sort=rating'), ('click', '/us/oh/columbus/p/kenny-road-apartments-d68a14'), ('click', '/us/oh/columbus/p/kenny-road-apartments-d68a14'), ('click', '/us/oh/columbus/p/kenny-road-apartments-d68a14'), ('click', '/profile/bookmarks'), ('done', '/profile/bookmarks')],
        answer='After removing The Standard at Atlanta and adding Kenny Road Apartments (the only 5.0-rated property under $600 near Ohio State, $500/mo), David ends up with 3 saved properties: Ion Austin, Icon At Austin and the newly added Kenny Road Apartments.',
        sql=['INSERT INTO property_views (user_id, session_key, property_slug, viewed_at) VALUES (4, "\'fixture-session\'", \'kenny-road-apartments-d68a14\', \'2026-09-26 12:00:00\');', "DELETE FROM bookmarks WHERE user_id = 4 AND property_slug = 'the-standard-at-atlanta-vesb8v';", "INSERT INTO bookmarks (user_id, property_slug, created_at) VALUES (4, 'kenny-road-apartments-d68a14', '2026-09-26 12:00:00');"],
    ),
    8: dict(
        steps=[('input', '/'), ('click', '/us/fl/orlando/u/university-of-central-florida'), ('click', '/us/fl/orlando/u/university-of-central-florida'), ('input', '/us/fl/orlando/u/university-of-central-florida'), ('click', '/us/fl/orlando/u/university-of-central-florida?max_price=800&type=Apartment'), ('click', '/us/fl/orlando/p/hub-on-campus-orlando-4df3abc0'), ('done', '/us/fl/orlando/p/hub-on-campus-orlando-4df3abc0')],
        answer='The AI search says it filtered the homes by Apartment type with a maximum price of $800/mo. The page showed 20 out of 177 results before the filters and 5 remain after they apply. The cheapest apartment is Hub On Campus Orlando — rated 4.0, at 11012 Hub Plz, Orlando, FL 32826, USA, starting at $500/mo, with 1034 Google reviews, 2.4 miles from campus.',
        sql=['INSERT INTO property_views (id, user_id, session_key, property_slug, viewed_at) VALUES (13, NULL, \'fixture-session\', \'hub-on-campus-orlando-4df3abc0\', \'2026-09-26 12:00:00\');'],
    ),
    9: dict(
        steps=[('input', '/'), ('click', '/us/oh/cleveland/u/case-western-reserve-university'), ('click', '/us/oh/cleveland/p/parkside-dwellings-fex58u'), ('go_back', '/us/oh/cleveland/u/case-western-reserve-university'), ('done', '/us/oh/cleveland/u/case-western-reserve-university')],
        answer='The Case Western Reserve University page shows 20 out of 316 results. In the map view, the property closest to the campus marker is Parkside Dwellings — from $1,360/month, rated 4.3 with 15 Google reviews, at 2040 Stearns Rd, Cleveland, OH 44106, USA, offering a Gym and a Swimming Pool. The property listed second-closest to campus is Skyline on Stokes, from $1,380/month.',
        sql=['INSERT INTO property_views (id, user_id, session_key, property_slug, viewed_at) VALUES (13, NULL, \'fixture-session\', \'parkside-dwellings-fex58u\', \'2026-09-26 12:00:00\');'],
    ),
    10: dict(
        steps=[('click', '/us/tx/u'), ('input', '/us/tx/u'), ('press', '/us/tx/u?q=TAMU'), ('click', '/us/tx/college-station/u/texas-am-university'), ('click', '/us/tx/college-station/p/100-park-554186'), ('go_back', '/us/tx/college-station/u/texas-am-university'), ('done', '/us/tx/college-station/u/texas-am-university')],
        answer='From the Texas college finder, \'TAMU\' is Texas A&M University. The most expensive property within one mile of its campus is 100 Park — from $1,539/month, 0.3 miles from campus, listing a Gym among its amenities, rated 4.1 with 63 Google reviews. The campus page shows 20 out of 141 results, and the cheapest home on it is The Gardens Apartments at $125/month.',
        sql=['INSERT INTO property_views (id, user_id, session_key, property_slug, viewed_at) VALUES (13, NULL, \'fixture-session\', \'100-park-554186\', \'2026-09-26 12:00:00\');'],
    ),
    11: dict(
        steps=[('input', '/'), ('click', '/us/tx/austin/p/villas-on-rio-8639e0'), ('click', '/us/tx/austin/p/villas-on-rio-8639e0'), ('input', '/us/tx/austin/p/villas-on-rio-8639e0'), ('input', '/us/tx/austin/p/villas-on-rio-8639e0'), ('click', '/us/tx/austin/p/villas-on-rio-8639e0'), ('click', '/us/tx/austin/p/villas-on-rio-8639e0'), ('input', '/us/tx/austin/p/villas-on-rio-8639e0'), ('input', '/us/tx/austin/p/villas-on-rio-8639e0'), ('click', '/us/tx/austin/p/villas-on-rio-8639e0'), ('input', '/us/tx/austin/p/villas-on-rio-8639e0'), ('input', '/us/tx/austin/p/villas-on-rio-8639e0'), ('input', '/us/tx/austin/p/villas-on-rio-8639e0'), ('click', '/us/tx/austin/p/villas-on-rio-8639e0'), ('done', '/us/tx/austin/p/villas-on-rio-8639e0')],
        answer="The form rejects the invalid email with 'Invalid email address' and the empty phone with 'Phone number is required'. After correcting them, the inquiry to Villas on Rio was sent with reference INQ-000005.",
        sql=['INSERT INTO property_views (user_id, session_key, property_slug, viewed_at) VALUES (1, "\'fixture-session\'", \'villas-on-rio-8639e0\', \'2026-09-26 12:00:00\');', "INSERT INTO enquiries (id, user_id, property_slug, first_name, last_name, phone, email, message, marketing_consent, created_at) VALUES (5, 1, 'villas-on-rio-8639e0', 'Alice', 'Johnson', '(512) 555-0142', 'alice.j@test.com', 'Is the property currently available?', 0, '2026-09-26 12:00:00');"],
    ),
    12: dict(
        steps=[('input', '/'), ('press', '/search?q=Seminoles'), ('click', '/us/fl/tallahassee/u/florida-state-university'), ('click', '/us/fl/tallahassee/p/southgate-campus-centre-13694141'), ('go_back', '/us/fl/tallahassee/u/florida-state-university'), ('done', '/us/fl/tallahassee/u/florida-state-university')],
        answer='\'Seminoles\' is Florida State University in Tallahassee. The cheapest property near that campus is Southgate Campus Centre — from $455/month, rated 4.3, 0.3 miles from campus, at 675 W Jefferson St, Tallahassee, FL 32304, USA, offering (among others) a Pet Friendly amenity. The campus page lists 20 out of 182 results, and the most expensive home on it is TLH Rent, LLC at $2,200/month.',
        sql=['INSERT INTO property_views (id, user_id, session_key, property_slug, viewed_at) VALUES (13, NULL, \'fixture-session\', \'southgate-campus-centre-13694141\', \'2026-09-26 12:00:00\');'],
    ),
    13: dict(
        steps=[('click', '/guides/avoid-scams-and-fraud'), ('click', '/contact'), ('input', '/contact'), ('click', '/us/tx/austin/u/the-university-of-texas-at-austin'), ('select', '/us/tx/austin/u/the-university-of-texas-at-austin?sort=price_asc'), ('done', '/us/tx/austin/u/the-university-of-texas-at-austin?sort=price_asc')],
        answer='The two matching red flags are \'Off-Platform Payments\' (asked for wire transfers) and \'The \'Ghost\' Landlord\' (\'currently away on vacation\'). The emergency protocol\'s first three steps: 1) Report anything suspicious (call +44 800 316 2918 or email contact@student.com), 2) Trace the Paperwork, 3) External Authorities. The same number and email do appear on the Contact page. The cheapest home near the University of Texas at Austin is College House Nueces at $532/month — below the $1,000–$1,600 typical apartment range the Austin city page mentions.',
        sql=[],
    ),
    14: dict(
        steps=[('click', '/'), ('click', '/'), ('input', '/'), ('input', '/'), ('input', '/'), ('input', '/'), ('click', '/'), ('input', '/'), ('click', '/us/ga/athens/u/university-of-georgia'), ('select', '/us/ga/athens/u/university-of-georgia?sort=rating'), ('click', '/us/ga/athens/p/the-butler-olmq6o'), ('click', '/us/ga/athens/p/the-butler-olmq6o'), ('click', '/us/ga/athens/p/the-butler-olmq6o'), ('input', '/us/ga/athens/p/the-butler-olmq6o'), ('input', '/us/ga/athens/p/the-butler-olmq6o'), ('click', '/us/ga/athens/p/the-butler-olmq6o'), ('done', '/us/ga/athens/p/the-butler-olmq6o')],
        answer='Created the account for Mia Torres (mia.torres@test.com). Near the University of Georgia, the most expensive 5.0-rated property is The Butler ($900/mo). Saved it to the new account and sent an inquiry about spring availability with reference INQ-000005.',
        sql=['INSERT INTO property_views (user_id, session_key, property_slug, viewed_at) VALUES (5, "\'fixture-session\'", \'the-butler-olmq6o\', \'2026-09-26 12:00:00\');', "INSERT INTO users (id, email, password_hash, first_name, last_name, phone, created_at) VALUES (5, 'mia.torres@test.com', '$2b$12$fixturehashfixturehashfixturehash', 'Mia', 'Torres', '(706) 555-0123', '2026-09-26 12:00:00');", "INSERT INTO bookmarks (user_id, property_slug, created_at) VALUES (5, 'the-butler-olmq6o', '2026-09-26 12:00:00');", "INSERT INTO enquiries (id, user_id, property_slug, first_name, last_name, phone, email, message, marketing_consent, created_at) VALUES (5, 5, 'the-butler-olmq6o', 'Mia', 'Torres', '(706) 555-0123', 'mia.torres@test.com', 'Is this property available for spring?', 0, '2026-09-26 12:00:00');"],
    ),
    15: dict(
        steps=[('input', '/'), ('click', '/us/tx/austin/p/moontower-69d81c'), ('input', '/us/tx/austin/p/moontower-69d81c'), ('click', '/us/tx/austin/p/villas-on-rio-8639e0'), ('done', '/us/tx/austin/p/villas-on-rio-8639e0')],
        answer='Moontower: from $700 up to $6,475 per month, 10 photos in its gallery, rated 3.5 with 178 Google reviews, at 2204 San Antonio St, Austin, TX 78705, offering (among others) a Rooftop Terrace. Villas on Rio: from $989, rated 4.3 with 456 Google reviews, offering (among others) a Yoga Studio. Moontower is cheaper to start with ($700 vs $989); Villas on Rio sits closer to the UT Austin campus (0.1 miles vs Moontower\'s 0.4 miles).',
        sql=['INSERT INTO property_views (id, user_id, session_key, property_slug, viewed_at) VALUES (13, NULL, \'fixture-session\', \'moontower-69d81c\', \'2026-09-26 12:00:00\');', 'INSERT INTO property_views (id, user_id, session_key, property_slug, viewed_at) VALUES (14, NULL, \'fixture-session\', \'villas-on-rio-8639e0\', \'2026-09-26 12:00:00\');'],
    ),
    16: dict(
        steps=[('input', '/'), ('click', '/us/fl/tampa/u/university-of-south-florida'), ('click', '/us/fl/tampa/u/university-of-south-florida'), ('check', '/us/fl/tampa/u/university-of-south-florida'), ('input', '/us/fl/tampa/u/university-of-south-florida'), ('input', '/us/fl/tampa/u/university-of-south-florida'), ('click', '/us/fl/tampa/u/university-of-south-florida?min_price=900&max_price=1000&type=Student+Community'), ('select', '/us/fl/tampa/u/university-of-south-florida?sort=price_asc&min_price=900&max_price=1000&type=Student+Community'), ('click', '/us/fl/miami/p/the-retreat-at-tampa'), ('done', '/us/fl/miami/p/the-retreat-at-tampa')],
        answer='1 result matches (Showing 1 out of 348): the only Student Community near the University of South Florida priced between $900 and $1,000 is The Retreat at Tampa ($940/mo, rated 4.0). Its exact street address is 11326 N 46th St, Tampa, FL 33617, USA, and its Explore your neighborhood section shows the vibe labels Coffee & food, Artsy & cultural and Music & nightlife.',
        sql=['INSERT INTO property_views (id, user_id, session_key, property_slug, viewed_at) VALUES (13, NULL, \'fixture-session\', \'the-retreat-at-tampa\', \'2026-09-26 12:00:00\');'],
    ),
    17: dict(
        steps=[('input', '/'), ('click', '/us/tx/lubbock/u/texas-tech-university'), ('click', '/us/tx/lubbock/p/stangel-hall-3-zooq'), ('go_back', '/us/tx/lubbock/u/texas-tech-university'), ('click', '/us/tx/lubbock/p/murray-hall-gcf4nm'), ('go_back', '/us/tx/lubbock/u/texas-tech-university'), ('click', '/us/tx/lubbock/p/murdough-hall-mvhqyi'), ('click', '/us/tx/lubbock/p/murdough-hall-mvhqyi'), ('click', '/us/tx/lubbock/p/murdough-hall-mvhqyi'), ('input', '/us/tx/lubbock/p/murdough-hall-mvhqyi'), ('input', '/us/tx/lubbock/p/murdough-hall-mvhqyi'), ('click', '/us/tx/lubbock/p/murdough-hall-mvhqyi'), ('click', '/us/tx/lubbock/p/murdough-hall-mvhqyi'), ('click', '/profile/history'), ('done', '/profile/history')],
        answer='The Recently Viewed dropdown lists the three browsed properties: Stangel Hall, Murray Hall and Murdough Hall (most recent first). After signing in as carol.d@test.com, all three also appear on her Recently Viewed Properties page (session views carry over), above her seeded views.',
        sql=['INSERT INTO property_views (user_id, session_key, property_slug, viewed_at) VALUES (NULL, "\'fixture-session\'", \'stangel-hall-3-zooq\', \'2026-09-26 12:00:00\');', 'INSERT INTO property_views (user_id, session_key, property_slug, viewed_at) VALUES (NULL, "\'fixture-session\'", \'murray-hall-gcf4nm\', \'2026-09-26 12:00:00\');', 'INSERT INTO property_views (user_id, session_key, property_slug, viewed_at) VALUES (NULL, "\'fixture-session\'", \'murdough-hall-mvhqyi\', \'2026-09-26 12:00:00\');'],
    ),
    18: dict(
        steps=[('input', '/'), ('click', '/us/ga/atlanta/p/catalyst-s7m7fb'), ('click', '/budget-calculator'), ('click', '/budget-calculator'), ('done', '/budget-calculator')],
        answer='Catalyst\'s contact email is catalystmidtown@crm-living.com, phone (855) 677-3286, website https://catalystmidtown.com/. With $2,300 income and $1,180 expenses the calculator\'s comfortable rent target is $660/month — well below Catalyst\'s cheapest room at $1,099/month, so the student could NOT comfortably afford it.',
        sql=['INSERT INTO property_views (id, user_id, session_key, property_slug, viewed_at) VALUES (13, NULL, \'fixture-session\', \'catalyst-s7m7fb\', \'2026-09-26 12:00:00\');'],
    ),
    19: dict(
        steps=[('click', '/'), ('input', '/'), ('input', '/'), ('click', '/'), ('click', '/'), ('click', '/profile/inquiries'), ('click', '/profile/inquiries'), ('click', '/profile/bookmarks'), ('click', '/profile/bookmarks'), ('click', '/profile/history'), ('done', '/profile/history')],
        answer='Alice\'s older inquiry is INQ-000001, sent to Moontower on September 20, 2026, asking: \'Hi, I\'m looking for a studio with a private bathroom for the fall semester. Is it still available?\' Her other inquiry is INQ-000002, sent to Villas on Rio. She has 3 saved properties in total (Moontower, Villas on Rio and International House (I-House)), and her Recently Viewed list shows 4 properties.',
        sql=[],
    ),
    20: dict(
        steps=[('input', '/'), ('click', '/us/fl/tampa/u/university-of-south-florida'), ('click', '/us/fl/tampa/u/university-of-south-florida'), ('check', '/us/fl/tampa/u/university-of-south-florida'), ('input', '/us/fl/tampa/u/university-of-south-florida'), ('input', '/us/fl/tampa/u/university-of-south-florida'), ('click', '/us/fl/tampa/u/university-of-south-florida?min_price=900&max_price=1000&type=Student+Community'), ('click', '/us/fl/miami/p/the-retreat-at-tampa'), ('click', '/us/fl/miami/p/the-retreat-at-tampa'), ('input', '/us/fl/miami/p/the-retreat-at-tampa'), ('input', '/us/fl/miami/p/the-retreat-at-tampa'), ('click', '/us/fl/miami/p/the-retreat-at-tampa'), ('click', '/us/fl/miami/p/the-retreat-at-tampa'), ('done', '/us/fl/miami/p/the-retreat-at-tampa')],
        answer='The only Student Community near the University of South Florida priced between $900 and $1,000 per month is The Retreat at Tampa — $940/mo, rated 4.0 — and its \'Key things to know\' labels are Quiet area, Suburban and Good shopping & grocery. Saved to bob.c@test.com\'s saved properties.',
        sql=['INSERT INTO bookmarks (id, user_id, property_slug, created_at) VALUES (13, 2, \'the-retreat-at-tampa\', \'2026-09-26 12:00:00\');', 'INSERT INTO property_views (id, user_id, session_key, property_slug, viewed_at) VALUES (13, NULL, \'fixture-session\', \'the-retreat-at-tampa\', \'2026-09-26 12:00:00\');'],
    ),
}

WRONG_ANSWERS = {
    0: "The property is Paloma West Midtown — 0.5 miles from campus — offering a Gym and a Pool. Saved to alice's saved properties.",
    1: 'Safety buffer: $500 and the comfortable rent target is $800. At $800 rent you\'d have $150 left over and the verdict is \'Looking good\'. The college search lists 3 properties.',
    2: 'The campus page lists 5 dorm-style homes and the cheapest is Creekside Residence Hall at $995/mo, at 2500 San Jacinto Blvd. Inquiry reference INQ-000009, dated September 24, 2026; Bob has 3 inquiries in total.',
    3: 'Closest to Georgia Tech: International House ($900) and Linea Midtown ($2,000); closest to Georgia State: Piedmont Pad ($600) and Live 8 West ($1,900). The most expensive is Linea Midtown, rated 4.2 with 525 reviews.',
    4: 'Carol\'s history lists 4 properties: Eighth Street Apartments, University House Midtown, Linea Midtown and The Rive. The one she remembers is University House Midtown — $1,115, 460 reviews, at 930 Spring St NW, rated 3.0. She has 3 saved properties.',
    5: 'Gainesville lists 6 jobs. The newest is \'Seasonal Sales Associate\' by Boxlunch. 3 are tagged part-time and 1 fellowship. The Part-Time filter shows \'Sales Associate\' by Boxlunch. The newest Austin job is \'Data Entry Associate, Temporary (Onsite)\' by Weedmaps77. Gainesville lists 12 properties.',
    6: 'The FAQ says you need a B-1 visa; rentals range $800-$1,200; 25 properties; Austin Community College. The average student budget is $1,000-$2,000; the museum is Mexic-Arte and the tours are at the Governor\'s Palace. The UT page shows 500 results; the top-rated home is Inspire On 22nd at $825 with 4.6.',
    7: 'David ends up with 4 saved properties; the added one is University House Midtown.',
    8: 'The AI search filtered by Dorm up to $700/mo. The page showed 10 out of 200 results before the filters and 3 remain after. The cheapest is Lake Hall — rated 5.0, at 4120 Pyxis Ln, from $400/mo, with 12 Google reviews, 0.5 miles from campus.',
    9: 'The page shows 15 out of 300 results. The property closest to the campus marker is University East Apartments — $1,525/mo, rated 5.0, with 20 reviews, at 11328 Euclid Ave, offering a Gym and a Pool. The second-closest is Medley at $1,680.',
    10: 'The most expensive property within a mile is Texas A&M University - Hullabaloo Hall — $1,279, 0.8 miles, no gym, rated 4.5 with 102 reviews. The campus page shows 100 results, and the cheapest home is Aggie Villas at $480.',
    11: "The form says 'Enter a valid email' and 'Phone required'; the corrected inquiry got reference INQ-000009.",
    12: '\'Seminoles\' is Florida State University in Orlando. The cheapest property is Saga Tallahassee — $500, rated 4.4, 0.4 miles, at 123 College Ave, offering a Gym. The campus page shows 15 results, and the most expensive home is StateHouse Woodward at $1,375.',
    13: 'The red flags are \'Suspiciously Low Rent\' and \'The Fake Invoice\'; the steps are: pay the deposit, call the landlord, wire the transfer. The reporting phone is +44 800 316 9999 and the email is help@student.com, which do not appear on the Contact page. The cheapest UT home is Greenwood Towers at $650, above the $1,600 range.',
    14: 'The property is University Village - Building C ($600); inquiry reference INQ-000009.',
    15: 'Moontower is from $750 to $5,000, 8 photos, rated 3.9 with 150 reviews, at 2200 San Antonio St, offering a Pool. Villas on Rio is rated 4.5 with 500 reviews, from $800, offering a Sauna. Villas on Rio is cheaper to start with and Moontower is closer to campus.',
    16: 'The Retreat at Tampa is at 123 Main St, Tampa; vibes are Urban, Social and Fun.',
    17: "The dropdown lists Stangel Hall, Murray Hall and Murdough Hall; they do NOT appear on carol's page.",
    18: 'Email: info@catalyst.com; phone (404) 555-9999; website catalyst.com; rent target $900; the student can comfortably afford it.',
    19: 'The older inquiry is INQ-000002 to Villas on Rio sent September 24, 2026, and the other is INQ-000001 to Moontower. Alice has 2 saved properties (Moontower and Villas on Rio) and 6 recently viewed properties.',
    20: 'The Retreat at Tampa is $900, rated 4.5, Key things to know: Urban, Social, Lively.',
}



# Current browser regression fixtures (synthetic unit-test reconstructions, not new browser evidence).
SPECS = {0: {'answer': 'The Rive Atlanta — 0.7 miles from the Georgia Tech campus — offers amenities including a Gym and '
               'a Swimming Pool (also Games Room, Cinema Room, Rooftop Terrace, Wifi, Pet Friendly). Saved to '
               "alice.j@test.com's saved properties.",
     'sql': ['INSERT INTO "bookmarks" ("id", "user_id", "property_slug", "created_at") VALUES (13, 1, '
             "'the-rive-atlanta-vbqacu', '2026-09-26 00:00:00.000000');",
             'INSERT INTO "property_views" ("id", "user_id", "session_key", "property_slug", "viewed_at") VALUES '
             "(13, NULL, 'c265321118099fffd8c32ce082c15a69', 'the-rive-atlanta-vbqacu', '2026-09-28 "
             "23:18:38.860979');"],
     'steps': [('load', '/'),
               ('fill', '/'),
               ('click', '/us/ga/atlanta/u/georgia-institute-of-technology'),
               ('click', '/us/ga/atlanta/u/georgia-institute-of-technology'),
               ('click', '/us/ga/atlanta/u/georgia-institute-of-technology'),
               ('fill', '/us/ga/atlanta/u/georgia-institute-of-technology'),
               ('click', '/us/ga/atlanta/u/georgia-institute-of-technology?max_price=1200&type=Student+Community'),
               ('select',
                '/us/ga/atlanta/u/georgia-institute-of-technology?sort=rating&max_price=1200&type=Student+Community'),
               ('click', '/us/ga/atlanta/p/the-rive-atlanta-vbqacu'),
               ('scroll', '/us/ga/atlanta/p/the-rive-atlanta-vbqacu'),
               ('scroll', '/us/ga/atlanta/p/the-rive-atlanta-vbqacu'),
               ('scroll', '/us/ga/atlanta/p/the-rive-atlanta-vbqacu'),
               ('click', '/us/ga/atlanta/p/the-rive-atlanta-vbqacu'),
               ('fill', '/us/ga/atlanta/p/the-rive-atlanta-vbqacu'),
               ('fill', '/us/ga/atlanta/p/the-rive-atlanta-vbqacu'),
               ('click', '/us/ga/atlanta/p/the-rive-atlanta-vbqacu'),
               ('click', '/us/ga/atlanta/p/the-rive-atlanta-vbqacu')]},
 1: {'answer': 'Safety buffer: $420 (20% of the $2,100 monthly income). Comfortable monthly rent target: $670. At '
               "a monthly rent estimate of $800 you would have $290 left over per month and the calculator's "
               "verdict is 'Tight but doable' (above the $670 comfortable target but still breaking even).",
     'sql': [],
     'steps': [('load', '/'),
               ('click', '/budget-calculator'),
               ('fill', '/budget-calculator'),
               ('fill', '/budget-calculator'),
               ('scroll', '/budget-calculator'),
               ('fill', '/budget-calculator'),
               ('fill', '/budget-calculator'),
               ('fill', '/budget-calculator'),
               ('fill', '/budget-calculator'),
               ('fill', '/budget-calculator'),
               ('fill', '/budget-calculator'),
               ('fill', '/budget-calculator'),
               ('scroll', '/budget-calculator'),
               ('click', '/budget-calculator'),
               ('click', '/budget-calculator'),
               ('fill', '/budget-calculator')]},
 2: {'answer': 'The cheapest dorm-style housing near The University of Texas at Austin is Littlefield Hall, '
               'starting at $935/mo, and the campus page lists 8 dorm-style homes. Its exact address is 2503 '
               'Whitis Ave, Austin, TX 78705, USA, and it offers (among others) Air Conditioning. Inquiry sent as '
               'bob.c@test.com with reference INQ-000005; My Inquiries shows it dated September 26, 2026 and Bob '
               'now has 2 inquiries in total.',
     'sql': ['INSERT INTO "enquiries" ("id", "user_id", "property_slug", "first_name", "last_name", "phone", '
             '"email", "message", "marketing_consent", "created_at") VALUES (5, 2, \'littlefield-hall-kutkl0\', '
             "'Bob', 'Chen', '(404) 555-0187', 'bob.c@test.com', 'Are rooms still available for the fall "
             "semester?', 0, '2026-09-26 00:00:00.000000');",
             'INSERT INTO "property_views" ("id", "user_id", "session_key", "property_slug", "viewed_at") VALUES '
             "(13, NULL, 'c8abacc64120b3aad0cac8156cb82c48', 'littlefield-hall-kutkl0', '2026-09-28 "
             "23:32:13.877057');"],
     'steps': [('load', '/'),
               ('fill', '/'),
               ('click', '/us/tx/austin/u/the-university-of-texas-at-austin'),
               ('click', '/us/tx/austin/u/the-university-of-texas-at-austin'),
               ('click', '/us/tx/austin/u/the-university-of-texas-at-austin'),
               ('click', '/us/tx/austin/u/the-university-of-texas-at-austin?type=Dorm'),
               ('select', '/us/tx/austin/u/the-university-of-texas-at-austin?sort=price_asc&type=Dorm'),
               ('click', '/us/tx/austin/p/littlefield-hall-kutkl0'),
               ('scroll', '/us/tx/austin/p/littlefield-hall-kutkl0'),
               ('scroll', '/us/tx/austin/p/littlefield-hall-kutkl0'),
               ('scroll', '/us/tx/austin/p/littlefield-hall-kutkl0'),
               ('click', '/us/tx/austin/p/littlefield-hall-kutkl0'),
               ('fill', '/us/tx/austin/p/littlefield-hall-kutkl0'),
               ('fill', '/us/tx/austin/p/littlefield-hall-kutkl0'),
               ('click', '/us/tx/austin/p/littlefield-hall-kutkl0'),
               ('click', '/us/tx/austin/p/littlefield-hall-kutkl0'),
               ('fill', '/us/tx/austin/p/littlefield-hall-kutkl0'),
               ('fill', '/us/tx/austin/p/littlefield-hall-kutkl0'),
               ('fill', '/us/tx/austin/p/littlefield-hall-kutkl0'),
               ('fill', '/us/tx/austin/p/littlefield-hall-kutkl0'),
               ('fill', '/us/tx/austin/p/littlefield-hall-kutkl0'),
               ('click', '/us/tx/austin/p/littlefield-hall-kutkl0'),
               ('click', '/us/tx/austin/p/littlefield-hall-kutkl0'),
               ('click', '/us/tx/austin/p/littlefield-hall-kutkl0'),
               ('click', '/profile/inquiries')]},
 3: {'answer': 'Two homes closest to Georgia Tech: International House (I-House) from $950/mo and Eighth Street '
               'Apartments from $1,411/mo. Two closest to Georgia State University: Piedmont Pad Apartments from '
               '$500/mo and Freeman Ford Lofts from $1,850/mo. The most expensive of the four is Freeman Ford '
               'Lofts, rated 4.7 with 36 Google reviews.',
     'sql': ['INSERT INTO "property_views" ("id", "user_id", "session_key", "property_slug", "viewed_at") VALUES '
             "(13, NULL, 'f7aff3013f5081cb6645a23c1aeec343', 'freeman-ford-lofts-5bc863', '2026-09-28 "
             "23:18:59.242444');"],
     'steps': [('load', '/'),
               ('fill', '/'),
               ('click', '/us/ga/atlanta/u/georgia-institute-of-technology'),
               ('fill', '/us/ga/atlanta/u/georgia-institute-of-technology'),
               ('click', '/us/ga/atlanta/u/georgia-state-university'),
               ('click', '/us/ga/atlanta/p/freeman-ford-lofts-5bc863'),
               ('scroll', '/us/ga/atlanta/p/freeman-ford-lofts-5bc863')]},
 4: {'answer': 'Eighth Street Apartments — $1,411/mo, 36 Google reviews, at 555 8th St NW, Atlanta, GA 30332, '
               'USA, rated 4.2.',
     'sql': ['INSERT INTO "property_views" ("id", "user_id", "session_key", "property_slug", "viewed_at") VALUES '
             "(13, 3, '0edd9501b774437590b67f5c84e917d8', 'eighth-street-apartments-z0rz15', '2026-09-28 "
             "23:15:02.785346');"],
     'steps': [('load', '/'),
               ('click', '/'),
               ('fill', '/'),
               ('fill', '/'),
               ('click', '/'),
               ('click', '/'),
               ('click', '/profile/history'),
               ('click', '/us/ga/atlanta/p/eighth-street-apartments-z0rz15'),
               ('scroll', '/us/ga/atlanta/p/eighth-street-apartments-z0rz15'),
               ('scroll', '/us/ga/atlanta/p/eighth-street-apartments-z0rz15'),
               ('scroll', '/us/ga/atlanta/p/eighth-street-apartments-z0rz15')]},
 5: {'answer': 'Gainesville has 1 part-time opening: Part-Time Assistant Manager - Level 2 at Boxlunch, '
               'Gainesville, FL, posted January 3, 2018. Austin has 15 part-time openings. Two tie for newest, '
               'posted August 18, 2026: Operations Associate (Part-Time) - Domain Austin and Sales Associate '
               '(Part-Time) - Domain Austin, both at Aloyoga, The Domain, Austin, TX (10038).',
     'sql': [],
     'steps': [('load', '/'),
               ('fill', '/'),
               ('click', '/us/fl/gainesville'),
               ('scroll', '/us/fl/gainesville'),
               ('scroll', '/us/fl/gainesville'),
               ('scroll', '/us/fl/gainesville'),
               ('scroll', '/us/fl/gainesville'),
               ('scroll', '/us/fl/gainesville'),
               ('scroll', '/us/fl/gainesville'),
               ('scroll', '/us/fl/gainesville'),
               ('scroll', '/us/fl/gainesville'),
               ('scroll', '/us/fl/gainesville'),
               ('scroll', '/us/fl/gainesville'),
               ('click', '/us/fl/gainesville/internships'),
               ('click', '/us/fl/gainesville/internships?type=part-time'),
               ('fill', '/us/fl/gainesville/internships?type=part-time'),
               ('click', '/us/tx/austin'),
               ('scroll', '/us/tx/austin'),
               ('scroll', '/us/tx/austin'),
               ('scroll', '/us/tx/austin'),
               ('scroll', '/us/tx/austin'),
               ('scroll', '/us/tx/austin'),
               ('scroll', '/us/tx/austin'),
               ('scroll', '/us/tx/austin'),
               ('scroll', '/us/tx/austin'),
               ('scroll', '/us/tx/austin'),
               ('scroll', '/us/tx/austin'),
               ('scroll', '/us/tx/austin'),
               ('scroll', '/us/tx/austin'),
               ('scroll', '/us/tx/austin'),
               ('scroll', '/us/tx/austin'),
               ('scroll', '/us/tx/austin'),
               ('click', '/us/tx/austin/internships'),
               ('click', '/us/tx/austin/internships?type=part-time')]},
 6: {'answer': 'The Austin guide requires an F-1 visa for non-US students. Typical rents are $1,000–$1,600 per '
               'month and the student budget is $1,500–$2,500 excluding tuition. Carothers Residence Hall is '
               'highest rated at 4.7 and starts at $1,560/month, within the guide’s range. Amenities include '
               'Library / Study Area and Air Conditioning.',
     'sql': ['INSERT INTO "property_views" ("id", "user_id", "session_key", "property_slug", "viewed_at") VALUES '
             "(13, NULL, '4ccf06fd75f00b9a3c19abfa6af77c7d', 'carothers-residence-hall-jnfnzu', '2026-09-28 "
             "23:19:31.741549');"],
     'steps': [('load', '/'),
               ('fill', '/'),
               ('click', '/us/tx/austin'),
               ('scroll', '/us/tx/austin'),
               ('scroll', '/us/tx/austin'),
               ('scroll', '/us/tx/austin'),
               ('scroll', '/us/tx/austin'),
               ('scroll', '/us/tx/austin'),
               ('scroll', '/us/tx/austin'),
               ('scroll', '/us/tx/austin'),
               ('scroll', '/us/tx/austin'),
               ('scroll', '/us/tx/austin'),
               ('scroll', '/us/tx/austin'),
               ('scroll', '/us/tx/austin'),
               ('scroll', '/us/tx/austin'),
               ('scroll', '/us/tx/austin'),
               ('scroll', '/us/tx/austin'),
               ('scroll', '/us/tx/austin'),
               ('click', '/us/tx/austin'),
               ('scroll', '/us/tx/austin'),
               ('scroll', '/us/tx/austin'),
               ('scroll', '/us/tx/austin'),
               ('scroll', '/us/tx/austin'),
               ('scroll', '/us/tx/austin'),
               ('scroll', '/us/tx/austin'),
               ('scroll', '/us/tx/austin'),
               ('click', '/us/tx/austin/u/the-university-of-texas-at-austin'),
               ('select', '/us/tx/austin/u/the-university-of-texas-at-austin?sort=rating'),
               ('click', '/us/tx/austin/p/carothers-residence-hall-jnfnzu'),
               ('scroll', '/us/tx/austin/p/carothers-residence-hall-jnfnzu'),
               ('scroll', '/us/tx/austin/p/carothers-residence-hall-jnfnzu'),
               ('scroll', '/us/tx/austin/p/carothers-residence-hall-jnfnzu')]},
 7: {'answer': 'After removing The Standard at Atlanta and adding Kenny Road Apartments (the only 5.0-rated '
               'property under $600 near Ohio State, $500/mo), David ends up with 3 saved properties: Ion Austin, '
               'Icon At Austin and the newly added Kenny Road Apartments.',
     'sql': ['DELETE FROM "bookmarks" WHERE "id"=12;',
             'INSERT INTO "bookmarks" ("id", "user_id", "property_slug", "created_at") VALUES (12, 4, '
             "'kenny-road-apartments-d68a14', '2026-09-26 00:00:00.000000');",
             'INSERT INTO "property_views" ("id", "user_id", "session_key", "property_slug", "viewed_at") VALUES '
             "(13, 4, 'cc0c087da3d339dea4fe587bbdbdcc6d', 'kenny-road-apartments-d68a14', '2026-09-28 "
             "23:19:40.558909');"],
     'steps': [('load', '/'),
               ('click', '/'),
               ('fill', '/'),
               ('fill', '/'),
               ('click', '/'),
               ('click', '/'),
               ('click', '/profile/bookmarks'),
               ('click', '/profile/bookmarks'),
               ('fill', '/profile/bookmarks'),
               ('click', '/us/oh/columbus/u/the-ohio-state-university'),
               ('select', '/us/oh/columbus/u/the-ohio-state-university?sort=rating'),
               ('click', '/us/oh/columbus/p/kenny-road-apartments-d68a14'),
               ('scroll', '/us/oh/columbus/p/kenny-road-apartments-d68a14'),
               ('click', '/us/oh/columbus/p/kenny-road-apartments-d68a14'),
               ('click', '/us/oh/columbus/p/kenny-road-apartments-d68a14'),
               ('click', '/profile/bookmarks')]},
 8: {'answer': 'The AI search says it filtered the homes by Apartment type with a maximum price of $800/mo. The '
               'page showed 20 out of 25 results before the filters and 5 remain after they apply. The cheapest '
               'apartment is Hub On Campus Orlando — rated 4.0, at 11012 Hub Plz, Orlando, FL 32826, USA, '
               'starting at $500/mo, with 1034 Google reviews, 2.4 miles from campus.',
     'sql': ['INSERT INTO "property_views" ("id", "user_id", "session_key", "property_slug", "viewed_at") VALUES '
             "(13, NULL, 'e7fbce1928de378c54954baa51593f61', 'hub-on-campus-orlando-4df3abc0', '2026-09-28 "
             "23:19:48.090501');"],
     'steps': [('load', '/'),
               ('fill', '/'),
               ('click', '/us/fl/orlando/u/university-of-central-florida'),
               ('click', '/us/fl/orlando/u/university-of-central-florida'),
               ('fill', '/us/fl/orlando/u/university-of-central-florida'),
               ('click', '/us/fl/orlando/u/university-of-central-florida'),
               ('wait', '/us/fl/orlando/u/university-of-central-florida?max_price=800&type=Apartment'),
               ('select',
                '/us/fl/orlando/u/university-of-central-florida?sort=price_asc&max_price=800&type=Apartment'),
               ('click', '/us/fl/orlando/p/hub-on-campus-orlando-4df3abc0'),
               ('scroll', '/us/fl/orlando/p/hub-on-campus-orlando-4df3abc0'),
               ('scroll', '/us/fl/orlando/p/hub-on-campus-orlando-4df3abc0'),
               ('scroll', '/us/fl/orlando/p/hub-on-campus-orlando-4df3abc0')]},
 9: {'answer': 'The Case Western Reserve University page shows 20 out of 20 results. In the map view, the '
               'property closest to the campus marker is Parkside Dwellings — from $1,360/month, rated 4.3 with '
               '15 Google reviews, at 2040 Stearns Rd, Cleveland, OH 44106, USA, offering a Gym and a Swimming '
               'Pool. The property listed second-closest to campus is Skyline on Stokes, from $1,380/month.',
     'sql': ['INSERT INTO "property_views" ("id", "user_id", "session_key", "property_slug", "viewed_at") VALUES '
             "(13, NULL, '462fd6c7d8c90d7a93a0fd7078dac545', 'parkside-dwellings-fex58u', '2026-09-28 "
             "23:19:53.173523');"],
     'steps': [('load', '/'),
               ('fill', '/'),
               ('click', '/us/oh/cleveland/u/case-western-reserve-university'),
               ('click', '/us/oh/cleveland/p/parkside-dwellings-fex58u'),
               ('scroll', '/us/oh/cleveland/p/parkside-dwellings-fex58u'),
               ('scroll', '/us/oh/cleveland/p/parkside-dwellings-fex58u'),
               ('scroll', '/us/oh/cleveland/p/parkside-dwellings-fex58u'),
               ('back', '/us/oh/cleveland/u/case-western-reserve-university')]},
 10: {'answer': "From the Texas college finder, 'TAMU' is Texas A&M University. The most expensive property "
                'within one mile of its campus is 100 Park — from $1,539/month, 0.3 miles from campus, listing a '
                'Gym among its amenities, rated 4.1 with 63 Google reviews.',
      'sql': ['INSERT INTO "property_views" ("id", "user_id", "session_key", "property_slug", "viewed_at") VALUES '
              "(13, NULL, '6a8af02ca821af943b169341ec9e907e', '100-park-554186', '2026-09-28 23:19:58.905428');"],
      'steps': [('load', '/'),
                ('click', '/us/tx/u'),
                ('fill', '/us/tx/u'),
                ('press', '/us/tx/u?q=TAMU'),
                ('click', '/us/tx/college-station/u/texas-am-university'),
                ('select', '/us/tx/college-station/u/texas-am-university?sort=price_desc'),
                ('click', '/us/tx/college-station/p/100-park-554186'),
                ('scroll', '/us/tx/college-station/p/100-park-554186'),
                ('scroll', '/us/tx/college-station/p/100-park-554186'),
                ('scroll', '/us/tx/college-station/p/100-park-554186')]},
 11: {'answer': 'Villas on Rio inquiry sent as Alice Johnson (alice.j@test.com, (404) 555-0187), asking which '
                'rooms are available and when I could move in. INQ-000005 is retained in My Inquiries.',
      'sql': ['INSERT INTO "enquiries" ("id", "user_id", "property_slug", "first_name", "last_name", "phone", '
              '"email", "message", "marketing_consent", "created_at") VALUES (5, 1, \'villas-on-rio-8639e0\', '
              "'Alice', 'Johnson', '(404) 555-0187', 'alice.j@test.com', 'Which rooms are currently available, "
              "and when could I move in?', 0, '2026-09-26 00:00:00.000000');",
              'INSERT INTO "property_views" ("id", "user_id", "session_key", "property_slug", "viewed_at") VALUES '
              "(13, 1, 'faaacb36e8dbd454a91dcac2f26d750f', 'villas-on-rio-8639e0', '2026-09-28 "
              "23:32:29.847505');"],
      'steps': [('load', '/'),
                ('click', '/'),
                ('fill', '/'),
                ('fill', '/'),
                ('click', '/'),
                ('fill', '/'),
                ('click', '/us/tx/austin/p/villas-on-rio-8639e0'),
                ('scroll', '/us/tx/austin/p/villas-on-rio-8639e0'),
                ('click', '/us/tx/austin/p/villas-on-rio-8639e0'),
                ('fill', '/us/tx/austin/p/villas-on-rio-8639e0'),
                ('fill', '/us/tx/austin/p/villas-on-rio-8639e0'),
                ('fill', '/us/tx/austin/p/villas-on-rio-8639e0'),
                ('fill', '/us/tx/austin/p/villas-on-rio-8639e0'),
                ('fill', '/us/tx/austin/p/villas-on-rio-8639e0'),
                ('click', '/us/tx/austin/p/villas-on-rio-8639e0'),
                ('click', '/us/tx/austin/p/villas-on-rio-8639e0'),
                ('click', '/us/tx/austin/p/villas-on-rio-8639e0'),
                ('click', '/profile/inquiries')]},
 12: {'answer': "'Seminoles' is Florida State University in Tallahassee. The cheapest property near that campus "
                'is Southgate Campus Centre — from $455/month, rated 4.3, 0.3 miles from campus, at 675 W '
                'Jefferson St, Tallahassee, FL 32304, USA, offering (among others) a Pet Friendly amenity. '
                'Amenities include Gym and Swimming Pool.',
      'sql': ['INSERT INTO "property_views" ("id", "user_id", "session_key", "property_slug", "viewed_at") VALUES '
              "(13, NULL, '29184d6ec5c94380063a8a7233960d12', 'southgate-campus-centre-13694141', '2026-09-28 "
              "23:20:04.106875');"],
      'steps': [('load', '/'),
                ('fill', '/'),
                ('press', '/search?q=Seminoles'),
                ('click', '/us/fl/tallahassee/u/florida-state-university'),
                ('select', '/us/fl/tallahassee/u/florida-state-university?sort=price_asc'),
                ('click', '/us/fl/tallahassee/p/southgate-campus-centre-13694141'),
                ('scroll', '/us/fl/tallahassee/p/southgate-campus-centre-13694141'),
                ('scroll', '/us/fl/tallahassee/p/southgate-campus-centre-13694141'),
                ('scroll', '/us/fl/tallahassee/p/southgate-campus-centre-13694141')]},
 13: {'answer': "The two matching red flags are 'Off-Platform Payments' (asked for wire transfers) and 'The "
                "'Ghost' Landlord' ('currently away on vacation'). The emergency protocol's first three steps: 1) "
                'Report anything suspicious (call +44 800 316 2918 or email contact@student.com), 2) Trace the '
                'Paperwork, 3) External Authorities. The same number and email do appear on the Contact page. The '
                'cheapest home near the University of Texas at Austin is College House Nueces at $532/month — '
                'below the $1,000–$1,600 typical apartment range the Austin city page mentions. A plausible rent '
                'does not make a wire transfer or refusal to allow a viewing safe.',
      'sql': [],
      'steps': [('load', '/'),
                ('scroll', '/'),
                ('scroll', '/'),
                ('scroll', '/'),
                ('scroll', '/'),
                ('scroll', '/'),
                ('scroll', '/'),
                ('click', '/guides/avoid-scams-and-fraud'),
                ('scroll', '/guides/avoid-scams-and-fraud'),
                ('scroll', '/guides/avoid-scams-and-fraud'),
                ('click', '/contact'),
                ('fill', '/contact'),
                ('click', '/us/tx/austin'),
                ('scroll', '/us/tx/austin'),
                ('scroll', '/us/tx/austin'),
                ('scroll', '/us/tx/austin'),
                ('scroll', '/us/tx/austin'),
                ('scroll', '/us/tx/austin'),
                ('scroll', '/us/tx/austin'),
                ('scroll', '/us/tx/austin'),
                ('click', '/us/tx/austin/u/the-university-of-texas-at-austin'),
                ('select', '/us/tx/austin/u/the-university-of-texas-at-austin?sort=price_asc')]},
 14: {'answer': 'Created the account for Mia Torres (mia.torres@test.com). Near the University of Georgia, the '
                'most expensive 5.0-rated property is The Butler ($900/mo). Saved it to the new account and sent '
                'an inquiry about spring availability with reference INQ-000005.',
      'sql': ['INSERT INTO "users" ("id", "email", "password_hash", "first_name", "last_name", "phone", '
              '"created_at") VALUES (5, \'mia.torres@test.com\', '
              "'$2b$12$x5fboE20lhPWt9Pp0bI29uyj910VNPbBZDkTBSJAbP08TmdJeL9Oq', 'Mia', 'Torres', '', '2026-09-26 "
              "00:00:00.000000');",
              'INSERT INTO "bookmarks" ("id", "user_id", "property_slug", "created_at") VALUES (13, 5, '
              "'the-butler-olmq6o', '2026-09-26 00:00:00.000000');",
              'INSERT INTO "enquiries" ("id", "user_id", "property_slug", "first_name", "last_name", "phone", '
              '"email", "message", "marketing_consent", "created_at") VALUES (5, 5, \'the-butler-olmq6o\', '
              "'Mia', 'Torres', '(404) 555-0187', 'mia.torres@test.com', 'Is this property available for "
              "spring?', 0, '2026-09-26 00:00:00.000000');",
              'INSERT INTO "property_views" ("id", "user_id", "session_key", "property_slug", "viewed_at") VALUES '
              "(13, 5, '55e894bdd2bd8ef65aa0ba680dddfc08', 'the-butler-olmq6o', '2026-09-28 23:20:12.958354');"],
      'steps': [('load', '/'),
                ('click', '/'),
                ('click', '/'),
                ('fill', '/'),
                ('fill', '/'),
                ('fill', '/'),
                ('fill', '/'),
                ('click', '/'),
                ('fill', '/'),
                ('click', '/us/ga/athens/u/university-of-georgia'),
                ('select', '/us/ga/athens/u/university-of-georgia?sort=rating'),
                ('click', '/us/ga/athens/p/the-butler-olmq6o'),
                ('scroll', '/us/ga/athens/p/the-butler-olmq6o'),
                ('click', '/us/ga/athens/p/the-butler-olmq6o'),
                ('click', '/us/ga/athens/p/the-butler-olmq6o'),
                ('fill', '/us/ga/athens/p/the-butler-olmq6o'),
                ('fill', '/us/ga/athens/p/the-butler-olmq6o'),
                ('fill', '/us/ga/athens/p/the-butler-olmq6o'),
                ('fill', '/us/ga/athens/p/the-butler-olmq6o'),
                ('fill', '/us/ga/athens/p/the-butler-olmq6o'),
                ('click', '/us/ga/athens/p/the-butler-olmq6o'),
                ('click', '/us/ga/athens/p/the-butler-olmq6o')]},
 15: {'answer': 'Moontower: from $700 up to $6,475 per month, 10 photos in its gallery, rated 3.5 with 178 Google '
                'reviews, at 2204 San Antonio St, Austin, TX 78705, offering (among others) a Rooftop Terrace. '
                'Villas on Rio: from $989, rated 4.3 with 456 Google reviews, offering (among others) a Yoga '
                'Studio. Moontower is cheaper to start with ($700 vs $989); Villas on Rio sits closer to the UT '
                "Austin campus (0.1 miles vs Moontower's 0.4 miles).",
      'sql': ['INSERT INTO "property_views" ("id", "user_id", "session_key", "property_slug", "viewed_at") VALUES '
              "(13, NULL, '04774fbe026fd4e2bcb234b1bbb6c4ab', 'moontower-69d81c', '2026-09-28 23:16:34.236885');",
              'INSERT INTO "property_views" ("id", "user_id", "session_key", "property_slug", "viewed_at") VALUES '
              "(14, NULL, '04774fbe026fd4e2bcb234b1bbb6c4ab', 'villas-on-rio-8639e0', '2026-09-28 "
              "23:16:36.817051');"],
      'steps': [('load', '/'),
                ('fill', '/'),
                ('click', '/us/tx/austin/p/moontower-69d81c'),
                ('scroll', '/us/tx/austin/p/moontower-69d81c'),
                ('scroll', '/us/tx/austin/p/moontower-69d81c'),
                ('scroll', '/us/tx/austin/p/moontower-69d81c'),
                ('fill', '/us/tx/austin/p/moontower-69d81c'),
                ('click', '/us/tx/austin/p/villas-on-rio-8639e0'),
                ('scroll', '/us/tx/austin/p/villas-on-rio-8639e0'),
                ('scroll', '/us/tx/austin/p/villas-on-rio-8639e0'),
                ('scroll', '/us/tx/austin/p/villas-on-rio-8639e0'),
                ('scroll', '/us/tx/austin/p/villas-on-rio-8639e0'),
                ('scroll', '/us/tx/austin/p/villas-on-rio-8639e0')]},
 16: {'answer': '1 result matches (Showing 1 out of 1): the only Student Community near the University of South '
                'Florida priced between $900 and $1,000 is The Retreat at Tampa ($940/mo, rated 4.0). Its exact '
                'street address is 11326 N 46th St, Tampa, FL 33617, USA, and its Explore your neighborhood '
                'section shows the vibe labels Coffee & food, Artsy & cultural and Music & nightlife.',
      'sql': ['INSERT INTO "property_views" ("id", "user_id", "session_key", "property_slug", "viewed_at") VALUES '
              "(13, NULL, 'c94579031d1e98d9807220ef9749cb89', 'the-retreat-at-tampa', '2026-09-28 "
              "23:20:21.823391');"],
      'steps': [('load', '/'),
                ('fill', '/'),
                ('click', '/us/fl/tampa/u/university-of-south-florida'),
                ('click', '/us/fl/tampa/u/university-of-south-florida'),
                ('click', '/us/fl/tampa/u/university-of-south-florida'),
                ('fill', '/us/fl/tampa/u/university-of-south-florida'),
                ('fill', '/us/fl/tampa/u/university-of-south-florida'),
                ('click',
                 '/us/fl/tampa/u/university-of-south-florida?min_price=900&max_price=1000&type=Student+Community'),
                ('select',
                 '/us/fl/tampa/u/university-of-south-florida?sort=price_asc&min_price=900&max_price=1000&type=Student+Community'),
                ('click', '/us/fl/miami/p/the-retreat-at-tampa'),
                ('scroll', '/us/fl/miami/p/the-retreat-at-tampa'),
                ('scroll', '/us/fl/miami/p/the-retreat-at-tampa'),
                ('scroll', '/us/fl/miami/p/the-retreat-at-tampa'),
                ('scroll', '/us/fl/miami/p/the-retreat-at-tampa'),
                ('scroll', '/us/fl/miami/p/the-retreat-at-tampa')]},
 17: {'answer': 'The Recently Viewed dropdown lists the three browsed properties: Stangel Hall, Murray Hall and '
                'Murdough Hall (most recent first). After signing in as carol.d@test.com, all three also appear '
                'on her Recently Viewed Properties page (session views carry over), above her seeded views.',
      'sql': ['INSERT INTO "property_views" ("id", "user_id", "session_key", "property_slug", "viewed_at") VALUES '
              "(13, NULL, '805c1624f68334bec8612dfb9bfd9bcc', 'stangel-hall-3-zooq', '2026-09-28 "
              "23:20:27.822069');",
              'INSERT INTO "property_views" ("id", "user_id", "session_key", "property_slug", "viewed_at") VALUES '
              "(14, NULL, '805c1624f68334bec8612dfb9bfd9bcc', 'murray-hall-gcf4nm', '2026-09-28 "
              "23:20:28.873379');",
              'INSERT INTO "property_views" ("id", "user_id", "session_key", "property_slug", "viewed_at") VALUES '
              "(15, NULL, '805c1624f68334bec8612dfb9bfd9bcc', 'murdough-hall-mvhqyi', '2026-09-28 "
              "23:20:30.140458');"],
      'steps': [('load', '/'),
                ('fill', '/'),
                ('click', '/us/tx/lubbock/u/texas-tech-university'),
                ('click', '/us/tx/lubbock/p/stangel-hall-3-zooq'),
                ('back', '/us/tx/lubbock/u/texas-tech-university'),
                ('click', '/us/tx/lubbock/p/murray-hall-gcf4nm'),
                ('back', '/us/tx/lubbock/u/texas-tech-university'),
                ('click', '/us/tx/lubbock/p/murdough-hall-mvhqyi'),
                ('back', '/us/tx/lubbock/u/texas-tech-university'),
                ('click', '/us/tx/lubbock/u/texas-tech-university'),
                ('fill', '/us/tx/lubbock/u/texas-tech-university'),
                ('fill', '/us/tx/lubbock/u/texas-tech-university'),
                ('click', '/us/tx/lubbock/u/texas-tech-university'),
                ('click', '/us/tx/lubbock/u/texas-tech-university'),
                ('click', '/profile/history')]},
 18: {'answer': "Catalyst's contact email is catalystmidtown@crm-living.com, phone (855) 677-3286, website "
                "https://catalystmidtown.com/. With $2,300 income and $1,180 expenses the calculator's "
                "comfortable rent target is $660/month — well below Catalyst's cheapest room at $1,099/month, so "
                'the student could NOT comfortably afford it.',
      'sql': ['INSERT INTO "property_views" ("id", "user_id", "session_key", "property_slug", "viewed_at") VALUES '
              "(13, NULL, '6cfe8ebf5f05f9ed7084b54a31d376a8', 'catalyst-s7m7fb', '2026-09-28 23:16:59.386665');"],
      'steps': [('load', '/'),
                ('fill', '/'),
                ('click', '/us/ga/atlanta/p/catalyst-s7m7fb'),
                ('scroll', '/us/ga/atlanta/p/catalyst-s7m7fb'),
                ('scroll', '/us/ga/atlanta/p/catalyst-s7m7fb'),
                ('scroll', '/us/ga/atlanta/p/catalyst-s7m7fb'),
                ('scroll', '/us/ga/atlanta/p/catalyst-s7m7fb'),
                ('click', '/budget-calculator'),
                ('scroll', '/budget-calculator'),
                ('scroll', '/budget-calculator'),
                ('click', '/budget-calculator'),
                ('click', '/budget-calculator')]},
 19: {'answer': "Alice's older inquiry INQ-000001 was sent to Moontower on September 20, 2026, asking for a "
                'studio with a private bathroom for the fall semester. Follow-up INQ-000005 asks whether that '
                'room is still available. Both inquiries remain in My Inquiries.',
      'sql': ['INSERT INTO "enquiries" ("id", "user_id", "property_slug", "first_name", "last_name", "phone", '
              '"email", "message", "marketing_consent", "created_at") VALUES (5, 1, \'moontower-69d81c\', '
              "'Alice', 'Johnson', '(404) 555-0187', 'alice.j@test.com', 'Following up: is a studio with a "
              "private bathroom still available for the fall semester?', 0, '2026-09-26 00:00:00.000000');",
              'INSERT INTO "property_views" ("id", "user_id", "session_key", "property_slug", "viewed_at") VALUES '
              "(13, 1, 'c6141b3db9dacbb5503296cd71724ade', 'moontower-69d81c', '2026-09-28 23:32:42.676694');"],
      'steps': [('load', '/'),
                ('click', '/'),
                ('fill', '/'),
                ('fill', '/'),
                ('click', '/'),
                ('click', '/'),
                ('click', '/profile/inquiries'),
                ('click', '/us/tx/austin/p/moontower-69d81c'),
                ('scroll', '/us/tx/austin/p/moontower-69d81c'),
                ('click', '/us/tx/austin/p/moontower-69d81c'),
                ('fill', '/us/tx/austin/p/moontower-69d81c'),
                ('fill', '/us/tx/austin/p/moontower-69d81c'),
                ('fill', '/us/tx/austin/p/moontower-69d81c'),
                ('fill', '/us/tx/austin/p/moontower-69d81c'),
                ('fill', '/us/tx/austin/p/moontower-69d81c'),
                ('click', '/us/tx/austin/p/moontower-69d81c'),
                ('click', '/us/tx/austin/p/moontower-69d81c'),
                ('click', '/us/tx/austin/p/moontower-69d81c'),
                ('click', '/profile/inquiries')]},
 20: {'answer': 'The only Student Community near the University of South Florida priced between $900 and $1,000 '
                "per month is The Retreat at Tampa — $940/mo, rated 4.0 — and its 'Key things to know' labels are "
                "Quiet area, Suburban and Good shopping & grocery. Saved to bob.c@test.com's saved properties.",
      'sql': ['INSERT INTO "bookmarks" ("id", "user_id", "property_slug", "created_at") VALUES (13, 2, '
              "'the-retreat-at-tampa', '2026-09-26 00:00:00.000000');",
              'INSERT INTO "property_views" ("id", "user_id", "session_key", "property_slug", "viewed_at") VALUES '
              "(13, NULL, 'e1d703a871910feec1427913213b214e', 'the-retreat-at-tampa', '2026-09-28 "
              "23:20:42.821579');"],
      'steps': [('load', '/'),
                ('fill', '/'),
                ('click', '/us/fl/tampa/u/university-of-south-florida'),
                ('click', '/us/fl/tampa/u/university-of-south-florida'),
                ('click', '/us/fl/tampa/u/university-of-south-florida'),
                ('fill', '/us/fl/tampa/u/university-of-south-florida'),
                ('fill', '/us/fl/tampa/u/university-of-south-florida'),
                ('click',
                 '/us/fl/tampa/u/university-of-south-florida?min_price=900&max_price=1000&type=Student+Community'),
                ('click', '/us/fl/miami/p/the-retreat-at-tampa'),
                ('scroll', '/us/fl/miami/p/the-retreat-at-tampa'),
                ('scroll', '/us/fl/miami/p/the-retreat-at-tampa'),
                ('scroll', '/us/fl/miami/p/the-retreat-at-tampa'),
                ('scroll', '/us/fl/miami/p/the-retreat-at-tampa'),
                ('scroll', '/us/fl/miami/p/the-retreat-at-tampa'),
                ('click', '/us/fl/miami/p/the-retreat-at-tampa'),
                ('fill', '/us/fl/miami/p/the-retreat-at-tampa'),
                ('fill', '/us/fl/miami/p/the-retreat-at-tampa'),
                ('click', '/us/fl/miami/p/the-retreat-at-tampa'),
                ('click', '/us/fl/miami/p/the-retreat-at-tampa')]}}
