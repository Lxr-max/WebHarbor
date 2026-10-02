"""Frozen per-task fixture specs for the ticketmaster verifier tests (review
track, orch/review/ticketmaster).

URLs and honest answers come from the reviewer's r2 live honest walks against
the review container wh-tm-rereview @ http://localhost:40110 (port-normalized to the registration slot) (deterministic
seed md5 b03a154d…, built PYTHONHASHSEED=0 from the contributor fix commit
73b29ac8). MUTATIONS reproduces the exact stateful writes the application
performs (purchase orders get id 7 following the seed's 6 rows; the bought
listing's qty_available is decremented; card and favorite deltas per the
seed's rows). Order numbers in the fixtures are the reviewer's actual
runtime order numbers, cross-checked by the verifier against the after-DB
row. No LLM."""

BASE = "http://localhost:40110"

SPECS = {
    0: dict(
        urls=[BASE + u for u in (
            "/signin", "/member", "/search?q=knicks+pistons",
            "/event/3B006511E91D862B",
            "/event/3B006511E91D862B/tickets?listing=7053&qty=2",
            "/checkout", "/checkout?step=payment", "/checkout?step=review",
            "/order-confirmation/B502861C5B408E", "/member/orders")],
        inputs=[(0, "alice.j@test.com"), (0, "TestPass123!"),
                (1, "knicks pistons")],
        answer=("Order confirmed in My Account: order B502861C5B408E, seats Sec BALC "
                "Row I (cheapest Standard Admission), all-in total $573.80 for 2 "
                "tickets."),
    ),
    1: dict(
        urls=[BASE + u for u in (
            "/", "/search?q=metallica", "/artist/735647",
            "/discover/concerts?city=Las+Vegas&sort=price",
            "/event/170064550782E86E", "/event/17006455FF52D572",
            "/event/170064550782E874", "/event/1700645AB15DD4DB",
            "/event/1700645AB1CAD5FD",
            "/discover/concerts?city=Las+Vegas&sort=price",
            "/event/17006455FF52D572",
            "/event/17006455FF52D572/tickets?listing=10900&qty=2",
            "/checkout", "/checkout?step=payment", "/checkout?step=review",
            "/order-confirmation/3A7123708F21FD")],
        inputs=[(1, "metallica"), (13, "metallica.fan@example.com"),
                (13, "5555555555554444"), (13, "Guest Guest"),
                (13, "12"), (13, "2029")],
        answer=("Cheapest Standard Admission date is Oct 22, 2026: Sec BALC Row J, "
                "$80.50 per ticket, total charged $161.00 for 2 (order 3A7123708F21FD)."),
    ),
    2: dict(
        urls=[BASE + u for u in (
            "/", "/search?q=lion+king", "/event/0B00650BD65F6C93",
            "/event/0B00650BD68B6CD2", "/event/0B00650BD6966CD7",
            "/event/0B00650BD6C06D07", "/event/0B00650BD66A6C9B",
            "/event/0B00650BD6B66CFE", "/help", "/help/presale")],
        inputs=[(1, "lion king")],
        answer=("The Citi cardmember presale for the Jan 2 show opens 2026-10-25 and "
                "closes 2026-10-29. During checkout you must enter the first 6 digits "
                "of your eligible Citi credit card or Citibank Debit Card as the "
                "presale code, and you must pay with the Citi card. The VIP Package "
                "Presale runs right after (2026-10-30 to 2026-11-03). The theatre's "
                "other January dates list Venue Presales (Jan 9, Jan 10) and an "
                "Artist Fan Club Presale (Jan 17); Jan 3 and Jan 16 list no presale, "
                "so no Citi presale there. One order can contain 8 tickets, and the "
                "help centre says presale tickets are limited and not guaranteed."),
    ),
    3: dict(
        urls=[BASE + u for u in (
            "/", "/search?q=lion+king", "/event/0B00650BD65F6C93",
            "/event/0B00650BD65F6C93?qty=&price_max=&type=Accessible&sort=lowest",
            "/event/0B00650BD65F6C93/tickets?listing=500&qty=2",
            "/event/0B00650BD65F6C93",
            "/event/0B00650BD65F6C93?qty=&price_max=&type=Standard+Admission&sort=lowest",
            "/help", "/help/accessible-tickets")],
        inputs=[(1, "lion king")],
        answer=("The performance lists 1 accessible option: Sec ML, Row W at $23.41 "
                "per ticket incl fees — $46.82 all-in for 2 tickets together, which "
                "is $32.98 cheaper than 2 of the cheapest Standard Admission seats "
                "($39.90 each). The help centre says accessible seating is bought "
                "with the Accessible filter on the event page or by contacting the "
                "venue's accessibility services."),
    ),
    4: dict(
        urls=[BASE + u for u in (
            "/", "/search?q=sphere", "/venue/155762", "/search?q=td+garden",
            "/venue/8337", "/search?q=bruins+jets", "/event/010064EDC5277AB0")],
        inputs=[(1, "sphere"), (3, "td garden"), (5, "bruins jets")],
        answer=("Sphere lists 20 upcoming events and TD Garden lists 18, so TD Garden "
                "has fewer. TD Garden's street address is 100 Legends Way, Boston, MA "
                "02114. The cheapest all-in price for a Standard Admission ticket to "
                "the Bruins vs. Winnipeg Jets game is $81.18."),
    ),
    5: dict(
        urls=[BASE + u for u in (
            "/discover/concerts",
            "/discover/concerts?sub=&city=Las+Vegas&date_from=2026-10-29&date_to=2026-11-01&price_max=&sort=price",
            "/event/170064550781E861", "/event/170064550781E865",
            "/discover/concerts?sub=&city=Las+Vegas&date_from=2026-10-29&date_to=2026-11-01&price_max=&sort=price",
            "/event/170064550781E865")],
        inputs=[(1, "2026-10-29"), (1, "2026-11-01")],
        answer=("Comparing the window's Music events by Standard Admission prices, "
                "the cheapest is Metallica: Life Burns Faster on Sat, Oct 31, 2026: "
                "cheapest Standard Sec BALC Row I at $132.78 per ticket, $265.56 "
                "all-in for 2. Oct 29 is a Thursday and Oct 31 is a Saturday."),
    ),
    6: dict(
        urls=[BASE + u for u in (
            "/giftcards", "/search?q=bruins+jets", "/event/010064EDC5277AB0")],
        inputs=[(0, "HOLIDAY-CHEER-99"), (0, "SUMMER-JAM-55"),
                (0, "SPRING-FLING-77"), (1, "bruins jets")],
        answer=("Balances: HOLIDAY-CHEER-99 $500, SUMMER-JAM-55 $75, SPRING-FLING-77 "
                "$150 — $725 combined, which does cover 2 of the cheapest Standard "
                "Admission tickets for the Bruins vs. Jets game ($162.36). As stated "
                "on this site, a single gift card can carry up to $1000."),
    ),
    7: dict(
        urls=[BASE + u for u in (
            "/signin", "/member", "/member/orders", "/member/orders/TM2609274100",
            "/help", "/help/transfer-tickets", "/help", "/help/mobile-tickets")],
        inputs=[(0, "alice.j@test.com"), (0, "TestPass123!")],
        answer=("Aladdin order TM2609274100: 2 tickets, Sec BALCR Row F, charged to "
                "the Visa ending 4242. Per the help centre: a transfer starts from "
                "the order page in My Account — open the order, select the tickets, "
                "enter the recipient's email; once she accepts, the original barcode "
                "is invalidated. Mobile tickets usually arrive within 24-72 hours of "
                "the event."),
    ),
    8: dict(
        urls=[BASE + u for u in (
            "/signin", "/member", "/member/orders", "/member/orders/TM2609274103",
            "/member/favorites")],
        inputs=[(0, "bob.c@test.com"), (0, "TestPass123!")],
        answer=("Bob bought 3 tickets for THE KEHLANI WORLD TOUR: North America at "
                "Shoreline Amphitheatre, seats Sec BALCR Row I, total $187.83. His two "
                "saved events are Gorillaz - The Mountain Tour and Teddy Swims: The "
                "UGLY Tour."),
    ),
    9: dict(
        urls=[BASE + u for u in (
            "/signin", "/member", "/member/payment")],
        inputs=[(0, "carol.d@test.com"), (0, "TestPass123!"),
                (2, "6011111111118901"), (2, "Carol Davis"), (2, "7"), (2, "2031")],
        answer=("The Discover card ending 8901 was added and confirmed in Payment "
                "Options; after removing the old Visa ending 0341, the Discover ending "
                "8901 remains saved."),
    ),
    10: dict(
        urls=[BASE + u for u in (
            "/signin", "/member", "/member/favorites",
            "/search?q=trans-siberian+orchestra", "/artist/780815",
            "/member/favorites")],
        inputs=[(0, "david.k@test.com"), (0, "TestPass123!"),
                (3, "trans-siberian orchestra")],
        answer=("Removed the Rod Wave tour event and saved the Trans-Siberian "
                "Orchestra artist page. My Favorites now lists: The Book of Mormon "
                "(Touring), Metallica: Life Burns Faster, and Trans-Siberian "
                "Orchestra."),
    ),
    11: dict(
        urls=[BASE + u for u in (
            "/", "/search?q=bruins+jets", "/event/010064EDC5277AB0",
            "/event/010064EDC5277AB0/tickets?listing=15685&qty=2",
            "/checkout", "/checkout?step=payment", "/checkout?step=review",
            "/order-confirmation/9E838C78EE5200")],
        inputs=[(1, "bruins jets"), (5, "sports.fan@example.com"),
                (5, "5555555555554444"), (5, "Guest Guest"), (5, "12"), (5, "2029")],
        answer=("Guest order placed: order 9E838C78EE5200, seats Sec BALC Row I, "
                "total charged $162.36 for 2 Standard Admission tickets."),
    ),
    12: dict(
        urls=[BASE + u for u in (
            "/", "/search?q=aladdin", "/event/030064AEEB451887",
            "/search?q=knicks", "/event/3B006511E9238641",
            "/help", "/help/ticket-limits", "/legal/terms")],
        inputs=[(1, "aladdin"), (3, "knicks")],
        answer=("A single order for Aladdin - The Musical can contain up to 8 "
                "tickets; for the Knicks game at MSG up to 12. The help centre says "
                "orders that exceed the published limit may be cancelled without "
                "notice, including orders associated with the same name, e-mail "
                "address, billing address, or credit card number. The Terms of Use "
                "add that ticket limits are enforced per event and per household."),
    ),
    13: dict(
        urls=[BASE + u for u in (
            "/", "/search?q=power+to+the+people", "/event/150064B8F802C6F9",
            "/event/150064B8F802C6F9/tickets?listing=1189&qty=3",
            "/event/150064B8F802C6F9/tickets?listing=1189&qty=2",
            "/event/150064B8F802C6F9/tickets?listing=1189&qty=1",
            "/event/150064B8F802C6F9",
            "/event/150064B8F802C6F9?qty=&price_max=&type=Standard+Admission&sort=lowest")],
        inputs=[(1, "power to the people")],
        answer=("For 3 Standard Admission tickets in section 202, row G: face value "
                "$138.00, service fees $51.90, order total $189.90. For just 1 ticket "
                "in that row: total $63.30 with $17.30 of service fees. The cheapest "
                "Standard Admission ticket in section 118 is $97.01 per ticket "
                "(Row F)."),
    ),
    14: dict(
        urls=[BASE + u for u in (
            "/", "/search?q=wicked", "/artist/864373", "/event/2D0064FDEC59E76F")],
        inputs=[(1, "wicked")],
        answer=("The first upcoming Wicked (Touring) stop is Mar 31, 2027 at DPAC in "
                "Durham, NC. The tour lists 20 stops in total, the last on Apr 18, "
                "2027. Wicked (Touring) has an average fan rating of 4.7 based on 936 "
                "reviews. The cheapest Standard Admission for the first performance "
                "is Sec BALC Row J at $101.82 all-in per ticket; one order can "
                "contain 8 tickets."),
    ),
    15: dict(
        urls=[BASE + u for u in (
            "/discover/family",
            "/discover/family?sub=&city=&date_from=2027-02-01&date_to=2027-02-28&price_max=50&sort=price",
            "/event/2D0064F6A84FD696")],
        inputs=[(1, "2027-02-01"), (1, "2027-02-28"), (1, "50")],
        answer=("The Family event with the lowest starting price in February 2027 is "
                "Bluey's Big Play in Durham, NC on Feb 28, 2027, starting at $24 "
                "all-in. Its cheapest Standard Admission option is Sec BALC Row G "
                "at $41.97."),
    ),
    16: dict(
        urls=[BASE + u for u in (
            "/", "/search?q=trans-siberian+orchestra", "/artist/780815",
            "/event/1B00651B2A7F1795", "/search?q=wicked", "/artist/864373",
            "/event/2D0064FDEC59E76F", "/event/2D0064FDEC4CE6FE")],
        inputs=[(1, "trans-siberian orchestra"), (4, "wicked")],
        answer=("Trans-Siberian Orchestra: average fan rating 4.6 based on 1617 "
                "reviews, 18 events listed for December 2026, the first one Dec 02, "
                "2026 at Bridgestone Arena. Wicked (Touring): 4.7 from 936 reviews; "
                "its artist page lists 20 tour stops running Mar 31, 2027 through "
                "Apr 18, 2027, so 0 events in 2026. Fans rate Wicked higher."),
    ),
    17: dict(
        urls=[BASE + u for u in (
            "/signin", "/member", "/search?q=weezer+the+gathering",
            "/event/3000646DEDC399B4",
            "/event/3000646DEDC399B4?qty=4&price_max=&type=&sort=lowest",
            "/event/3000646DEDC399B4/tickets?listing=34930&qty=2",
            "/event/3000646DEDC399B4/tickets?listing=34930&qty=3",
            "/event/3000646DEDC399B4/tickets?listing=34930&qty=4",
            "/checkout", "/checkout?step=payment", "/checkout?step=review",
            "/order-confirmation/3CF38362BDE2FD", "/member/orders")],
        inputs=[(0, "alice.j@test.com"), (0, "TestPass123!"),
                (1, "weezer the gathering")],
        answer=("Order confirmed in My Account: order 3CF38362BDE2FD, Sec 201 Row H, "
                "4 Standard Admission tickets together, total $313.72."),
    ),
    18: dict(
        urls=[BASE + u for u in (
            "/", "/search?q=harry+styles+together", "/event/3B00643505768283",
            "/event/3B00643505768283?qty=&price_max=&type=VIP+Package&sort=lowest",
            "/event/3B00643505768283/tickets?listing=21328&qty=2",
            "/event/3B00643505768283/tickets?listing=21328&qty=3",
            "/event/3B00643505768283/tickets?listing=21328&qty=2",
            "/event/3B00643505768283",
            "/event/3B00643505768283?qty=&price_max=&type=Standard+Admission&sort=lowest")],
        inputs=[(1, "harry styles together")],
        answer=("There are 3 VIP package tickets available for the September 30 "
                "show: Sec GA, Row A. Two of them cost $358.70 all-in, of which "
                "$98.02 is service fees — $205.96 more than 2 of the cheapest "
                "Standard Admission seats ($152.74)."),
    ),
    19: dict(
        urls=[BASE + u for u in (
            "/signin", "/member", "/member/orders", "/member/orders/TM2609274105",
            "/sell", "/help", "/help/contact-us")],
        inputs=[(0, "david.k@test.com"), (0, "TestPass123!")],
        answer=("The Karol G order TM2609274105 is confirmed in my order history. "
                "The numbered steps for selling are 1. List (sign in, open the order "
                "in My Account, select the tickets, set your price), 2. Sell, 3. Get "
                "paid. The listing starts from My Account. The phone number this "
                "site's help centre gives for ordering tickets by phone is "
                "1-800-745-3000."),
    ),
}

# Stateful tasks and the exact DB writes the application performs.
def _purchase(order_id, order_no, user_id, event_id, listing_id, section,
              section_desc, row, qty, unit_price, face_total, fee_total, total,
              card_last4, card_brand, guest_email, listing_qty_after):
    return [
        ("INSERT INTO orders (id, order_no, user_id, event_id, listing_id, section,"
         " section_desc, row, qty, unit_price, face_total, fee_total, total,"
         " delivery, card_last4, card_brand, status, guest_email, created_at,"
         " placed_at) VALUES"
         f" ({order_id}, '{order_no}', {user_id}, '{event_id}', {listing_id},"
         f" '{section}', '{section_desc}', '{row}', {qty}, {unit_price},"
         f" {face_total}, {fee_total}, {total}, 'mobile', '{card_last4}',"
         f" '{card_brand}', 'confirmed', {guest_email}, '2026-09-27T12:00:00Z',"
         " '2026-09-27T12:00:00Z')"),
        (f"UPDATE ticket_listings SET qty_available = {listing_qty_after} "
         f"WHERE id = {listing_id}"),
    ]


MUTATIONS = {
    # T0: alice buys 2x the cheapest Standard Admission (BALC I, $286.90)
    0: _purchase(7, "B502861C5B408E", 1, "3B006511E91D862B", 7053, "BALC",
                 "Balcony", "I", 2, 286.90, 417.00, 156.80, 573.80,
                 "4242", "Visa", "NULL", 2),
    # T1: guest buys 2x cheapest Standard (Oct 22 BALC J, $80.50)
    1: _purchase(7, "3A7123708F21FD", "NULL", "17006455FF52D572", 10900, "BALC",
                 "Balcony", "J", 2, 80.50, 117.00, 44.00, 161.00,
                 "4242", "Visa", "'metallica.fan@example.com'", 3),
    # T9: carol adds Discover 8901, removes the old Visa 0341 (row id 5)
    9: [
        ("INSERT INTO payment_methods (id, user_id, brand, last4, exp_month,"
         " exp_year, holder) VALUES (7, 3, 'Discover', '8901', 7, 2031,"
         " 'Carol Davis')"),
        "DELETE FROM payment_methods WHERE id = 5",
    ],
    # T10: david removes the Rod Wave event favorite (id 13), adds TSO artist
    10: [
        "DELETE FROM favorites WHERE id = 13",
        ("INSERT INTO favorites (id, user_id, artist_id, event_id, created_at)"
         " VALUES (16, 4, '780815', NULL, '2026-09-27T12:00:00Z')"),
    ],
    # T11: guest buys 2x cheapest Standard Bruins (BALC I, $81.18)
    11: _purchase(7, "9E838C78EE5200", "NULL", "010064EDC5277AB0", 15685, "BALC",
                  "Balcony", "I", 2, 81.18, 118.00, 44.36, 162.36,
                  "4242", "Visa", "'sports.fan@example.com'", 3),
    # T17: alice buys 4x the cheapest Standard with >=4 seats (201 H, $78.43;
    # the former 202 F tie was de-tied in the seed, 202 F is now $78.45)
    17: _purchase(7, "3CF38362BDE2FD", 1, "3000646DEDC399B4", 34930, "201",
                  "Upper Level 201", "H", 4, 78.43, 228.00, 85.72, 313.72,
                  "4242", "Visa", "NULL", 2),
}

WRONG_ANSWERS = {
    0: "Order B502861C5B408E, Sec FLR A Row C, total $500.00.",
    1: "Cheapest date is Nov 5: Sec BALC Row W, total $95.90.",
    2: "The presale window closes 2026-12-01; enter the code VENUE123; every January date has a Citi presale; the limit is 4 and presales guarantee tickets.",
    3: "There are 5 accessible options: Sec ORCH Row A, $120.00 for 2, $10 more than Standard; buy by calling any box office.",
    4: "Sphere has 18 events, TD Garden 20; address is 1 Arena Way; cheapest Standard $99.00.",
    5: "The cheapest window show is Jingle Ball on Oct 29 (Thursday); Sec BALC Row K, 2 tickets total $269.70; Oct 31 is a Sunday.",
    6: "The balances are $300, $50 and $75 ($425 combined), which cannot cover the $200 tickets; the max card amount is $500.",
    7: "Order TM2609274101 covers 1 ticket in Sec ORCH Row A charged to Amex 0001; transfers start from the homepage, the recipient pays, the original ticket stays valid forever, and mobile tickets arrive a month early.",
    8: "Bob bought 3 tickets for Gorillaz at Yankee Stadium, Sec 100 Row A, $300.00.",
    9: "The Visa ending 0341 remains saved.",
    10: "My Favorites now lists only Rod Wave and Gorillaz.",
    11: "Order 9E838C78EE5200, Sec 101 Row B, total $200.00.",
    12: "The limits are 4 for Aladdin and 6 for the Knicks; excess orders are refunded automatically; no details are checked; the Terms of Use say nothing.",
    13: "Face value $100.00, fees $20.00, total $120.00; for 1 ticket total $40.00 with $5.00 fees; section 118 from $50.00.",
    14: "First stop is Apr 10 at MSG in New York; the tour lists 5 stops, the last in May; rating 3.9 from 500 reviews; cheapest Standard Sec 100 Row A $50.00; limit 20.",
    15: "The event is Sesame Street Live in Duluth on Feb 14 starting at $60; cheapest Standard Sec 200 Row W at $75.00.",
    16: "TSO is rated 3.9 from 500 reviews with 5 December events, first Dec 25 at the Opera House; Wicked is 4.7 from 936 with 10 events in 2026; TSO is rated higher.",
    17: "Order 3CF38362BDE2FD, Sec 202 Row F, 4 tickets, total $900.00.",
    18: "There are 10 VIP seats; Sec FLR A Row C; 2 cost $1000.00 with $50.00 fees, $10.00 more than Standard.",
    19: "The sell steps start from the Help page; the phone number is 1-800-555-0199.",
}



# Current browser regression fixtures (synthetic unit-test reconstructions; not new browser evidence).
SPECS = {0: {'answer': 'Order confirmed in My Account: order 40F0E6D6A9F291, seats Sec BALC Row I (cheapest Standard '
               'Admission), all-in total $573.80 for 2 tickets.',
     'inputs': [(0, 'alice.j@test.com'), (0, 'TestPass123!'), (1, 'knicks pistons')],
     'urls': ['/',
              '/signin',
              '/member',
              '/search?q=knicks+pistons',
              '/event/3B006511E91D862B',
              '/event/3B006511E91D862B/tickets?listing=7053&qty=2',
              '/checkout',
              '/checkout?step=payment',
              '/checkout?step=review',
              '/order-confirmation/40F0E6D6A9F291',
              '/member/orders']},
 1: {'answer': 'Cheapest Standard Admission date is Oct 22, 2026: Sec BALC Row J, $80.50 per ticket, total '
               'charged $161.00 for 2 (order 2976B471EA3EE5).',
     'inputs': [(1, 'metallica'),
                (13, 'metallica.fan@example.com'),
                (13, '5555555555554444'),
                (13, 'Guest Guest'),
                (13, '12'),
                (13, '2029')],
     'urls': ['/',
              '/search?q=metallica',
              '/artist/735647',
              '/discover/concerts',
              '/discover/concerts?sub=&city=Las+Vegas&date_from=&date_to=&price_max=&sort=price',
              '/event/170064550782E86E',
              '/event/17006455FF52D572',
              '/event/170064550782E874',
              '/event/1700645AB15DD4DB',
              '/event/1700645AB1CAD5FD',
              '/event/17006455FF52D572/tickets?listing=10900&qty=2',
              '/checkout',
              '/checkout?step=payment',
              '/checkout?step=review',
              '/order-confirmation/2976B471EA3EE5']},
 2: {'answer': 'The Citi cardmember presale for the Jan 2 show opens 2026-10-25 and closes 2026-10-29. During '
               'checkout you must enter the first 6 digits of your eligible Citi credit card or Citibank Debit '
               'Card as the presale code, and you must pay with the Citi card. The VIP Package Presale runs right '
               "after (2026-10-30 to 2026-11-03). The theatre's other January dates list Venue Presales (Jan 9, "
               'Jan 10) and an Artist Fan Club Presale (Jan 17); Jan 3 and Jan 16 list no presale, so no Citi '
               'presale there. One order can contain 8 tickets, and the help centre says presale tickets are '
               'limited and not guaranteed.',
     'inputs': [(1, 'lion king')],
     'urls': ['/',
              '/search?q=lion+king',
              '/event/0B00650BD65F6C93',
              '/event/0B00650BD68B6CD2',
              '/event/0B00650BD6966CD7',
              '/event/0B00650BD6C06D07',
              '/event/0B00650BD66A6C9B',
              '/event/0B00650BD6B66CFE',
              '/help',
              '/help/presale']},
 3: {'answer': 'The performance lists 1 accessible option: Sec ML, Row W at $23.41 per ticket incl fees — $46.82 '
               'all-in for 2 tickets together, which is $32.98 cheaper than 2 of the cheapest Standard Admission '
               'seats ($39.90 each). The help centre says accessible seating is bought with the Accessible filter '
               "on the event page or by contacting the venue's accessibility services.",
     'inputs': [(1, 'lion king')],
     'urls': ['/',
              '/search?q=lion+king',
              '/event/0B00650BD65F6C93',
              '/event/0B00650BD65F6C93?qty=&price_max=&type=Accessible&sort=lowest',
              '/event/0B00650BD65F6C93/tickets?listing=500&qty=2',
              '/event/0B00650BD65F6C93?qty=&price_max=&type=Standard+Admission&sort=lowest',
              '/help',
              '/help/accessible-tickets']},
 4: {'answer': 'The cheapest Standard Admission ticket is section BALC, row I: face value $59, service fee '
               '$22.18, all-in price $81.18 per ticket. The next-cheapest is section BALC, row H: face value $60, '
               'service fee $22.56, all-in price $82.56 per ticket. The upgrade costs $2.76 extra for two people. '
               'TD Garden is at 100 Legends Way.',
     'inputs': [(1, 'sphere'), (3, 'td garden'), (5, 'bruins jets')],
     'urls': ['/',
              '/search?q=bruins+jets',
              '/event/010064EDC5277AB0',
              '/event/010064EDC5277AB0/tickets?listing=15685&qty=2',
              '/event/010064EDC5277AB0/tickets?listing=15684&qty=2',
              '/venue/8337']},
 5: {'answer': "Comparing the window's Music events by Standard Admission prices, the cheapest is Metallica: Life "
               'Burns Faster on Sat, Oct 31, 2026: cheapest Standard Sec BALC Row I at $132.78 per ticket, '
               '$265.56 all-in for 2. Oct 29 is a Thursday and Oct 31 is a Saturday.',
     'inputs': [(1, '2026-10-29'), (1, '2026-11-01')],
     'urls': ['/',
              '/discover/concerts',
              '/discover/concerts?sub=&city=Las+Vegas&date_from=2026-10-29&date_to=2026-11-01&price_max=&sort=price',
              '/event/170064550781E861',
              '/event/170064550781E865']},
 6: {'answer': 'Balances: HOLIDAY-CHEER-99 $500, SUMMER-JAM-55 $75, SPRING-FLING-77 $150 — $725 combined, which '
               'does cover 2 of the cheapest Standard Admission tickets for the Bruins vs. Jets game ($162.36). '
               'As stated on this site, a single gift card can carry up to $1000.',
     'inputs': [(0, 'HOLIDAY-CHEER-99'), (0, 'SUMMER-JAM-55'), (0, 'SPRING-FLING-77'), (1, 'bruins jets')],
     'urls': ['/', '/giftcards', '/search?q=bruins+jets', '/event/010064EDC5277AB0']},
 7: {'answer': 'Aladdin order TM2609274100: 2 tickets, Sec BALCR Row F, charged to the Visa ending 4242. Per the '
               'help centre: a transfer starts from the order page in My Account — open the order, select the '
               "tickets, enter the recipient's email; once she accepts, the original barcode is invalidated. "
               'Mobile tickets usually arrive within 24-72 hours of the event.',
     'inputs': [(0, 'alice.j@test.com'), (0, 'TestPass123!')],
     'urls': ['/',
              '/signin',
              '/member',
              '/member/orders',
              '/member/orders/TM2609274100',
              '/help',
              '/help/transfer-tickets',
              '/help/mobile-tickets']},
 8: {'answer': 'My three-ticket order is TM2609274103 for THE KEHLANI WORLD TOUR: North America at Shoreline '
               'Amphitheatre. The seats are section BALCR, row I, and the total charged was $187.83.',
     'inputs': [(0, 'bob.c@test.com'), (0, 'TestPass123!')],
     'urls': ['/', '/signin', '/member', '/member/orders', '/member/orders/TM2609274103']},
 9: {'answer': 'The Discover card ending 8901 was added and confirmed in Payment Options; after removing the old '
               'Visa ending 0341, the Discover ending 8901 remains saved.',
     'inputs': [(0, 'carol.d@test.com'),
                (0, 'TestPass123!'),
                (2, '6011111111118901'),
                (2, 'Carol Davis'),
                (2, '7'),
                (2, '2031')],
     'urls': ['/', '/signin', '/member', '/member/payment']},
 10: {'answer': 'Removed the Rod Wave tour event and saved the Trans-Siberian Orchestra artist page. My Favorites '
                'now lists: The Book of Mormon (Touring), Metallica: Life Burns Faster, and Trans-Siberian '
                'Orchestra.',
      'inputs': [(0, 'david.k@test.com'), (0, 'TestPass123!'), (3, 'trans-siberian orchestra')],
      'urls': ['/',
               '/signin',
               '/member',
               '/member/favorites',
               '/search?q=trans-siberian+orchestra',
               '/artist/780815']},
 11: {'answer': 'Guest order placed: order 8E88F4EAF875E6, seats Sec BALC Row I, total charged $162.36 for 2 '
                'Standard Admission tickets.',
      'inputs': [(1, 'bruins jets'),
                 (5, 'sports.fan@example.com'),
                 (5, '5555555555554444'),
                 (5, 'Guest Guest'),
                 (5, '12'),
                 (5, '2029')],
      'urls': ['/',
               '/search?q=bruins+jets',
               '/event/010064EDC5277AB0',
               '/event/010064EDC5277AB0/tickets?listing=15685&qty=2',
               '/checkout',
               '/checkout?step=payment',
               '/checkout?step=review',
               '/order-confirmation/8E88F4EAF875E6']},
 12: {'answer': 'A single order for Aladdin - The Musical can contain up to 8 tickets; for the Knicks game at MSG '
                'up to 12. The help centre says orders that exceed the published limit may be cancelled without '
                'notice, including orders associated with the same name, e-mail address, billing address, or '
                'credit card number. The Terms of Use add that ticket limits are enforced per event and per '
                'household.',
      'inputs': [(1, 'aladdin'), (3, 'knicks')],
      'urls': ['/',
               '/search?q=aladdin',
               '/event/030064AEEB451887',
               '/search?q=knicks',
               '/event/3B006511E9238641',
               '/help',
               '/help/ticket-limits',
               '/legal/terms']},
 13: {'answer': 'For 3 Standard Admission tickets in section 202, row G: face value $138.00, service fees $51.90, '
                'order total $189.90. For just 1 ticket in that row: total $63.30 with $17.30 of service fees. '
                'The cheapest Standard Admission ticket in section 118 is $97.01 per ticket (Row F).',
      'inputs': [(1, 'power to the people')],
      'urls': ['/',
               '/search?q=power+to+the+people',
               '/event/150064B8F802C6F9',
               '/event/150064B8F802C6F9/tickets?listing=1189&qty=2',
               '/event/150064B8F802C6F9/tickets?listing=1189&qty=3',
               '/event/150064B8F802C6F9/tickets?listing=1189&qty=1',
               '/event/150064B8F802C6F9?qty=&price_max=&type=Standard+Admission&sort=lowest']},
 14: {'answer': 'The first upcoming Wicked (Touring) stop is Mar 31, 2027 at DPAC in Durham, NC. The tour lists '
                '20 stops in total, the last on Apr 18, 2027. Wicked (Touring) has an average fan rating of 4.7 '
                'based on 936 reviews. The cheapest Standard Admission for the first performance is Sec BALC Row '
                'J at $101.82 all-in per ticket; one order can contain 8 tickets.',
      'inputs': [(1, 'wicked')],
      'urls': ['/', '/search?q=wicked', '/artist/864373', '/event/2D0064FDEC59E76F']},
 15: {'answer': "The Family event with the lowest starting price in February 2027 is Bluey's Big Play in Durham, "
                'NC on Feb 28, 2027, starting at $24 all-in. Its cheapest Standard Admission option is Sec BALC '
                'Row G at $41.97.',
      'inputs': [(1, '2027-02-01'), (1, '2027-02-28'), (1, '50')],
      'urls': ['/',
               '/discover/family',
               '/discover/family?sub=&city=&date_from=2027-02-01&date_to=2027-02-28&price_max=50&sort=price',
               '/event/2D0064F6A84FD696']},
 16: {'answer': 'Trans-Siberian Orchestra: average fan rating 4.6 based on 1617 reviews, 18 events listed for '
                'December 2026, the first one Dec 02, 2026 at Bridgestone Arena. Wicked (Touring): 4.7 from 936 '
                'reviews; its artist page lists 20 tour stops running Mar 31, 2027 through Apr 18, 2027, so 0 '
                'events in 2026. Fans rate Wicked higher.',
      'inputs': [(1, 'trans-siberian orchestra'), (4, 'wicked')],
      'urls': ['/',
               '/search?q=trans-siberian+orchestra',
               '/artist/780815',
               '/event/1B00651B2A7F1795',
               '/search?q=wicked',
               '/artist/864373',
               '/event/2D0064FDEC59E76F',
               '/event/2D0064FDEC4CE6FE']},
 17: {'answer': 'Order confirmed in My Account: order C32AF1C5928F69, Sec 201 Row H, 4 Standard Admission tickets '
                'together, total $313.72.',
      'inputs': [(0, 'alice.j@test.com'), (0, 'TestPass123!'), (1, 'weezer the gathering')],
      'urls': ['/',
               '/signin',
               '/member',
               '/search?q=weezer+the+gathering',
               '/event/3000646DEDC399B4',
               '/event/3000646DEDC399B4?qty=4&price_max=&type=&sort=lowest',
               '/event/3000646DEDC399B4/tickets?listing=34930&qty=2',
               '/event/3000646DEDC399B4/tickets?listing=34930&qty=3',
               '/event/3000646DEDC399B4/tickets?listing=34930&qty=4',
               '/checkout',
               '/checkout?step=payment',
               '/checkout?step=review',
               '/order-confirmation/C32AF1C5928F69',
               '/member/orders']},
 18: {'answer': 'There are 3 VIP package tickets available for the September 30 show: Sec GA, Row A. Two of them '
                'cost $358.70 all-in, of which $98.02 is service fees — $205.96 more than 2 of the cheapest '
                'Standard Admission seats ($152.74).',
      'inputs': [(1, 'harry styles together')],
      'urls': ['/',
               '/search?q=harry+styles+together',
               '/event/3B00643505768283',
               '/event/3B00643505768283?qty=&price_max=&type=VIP+Package&sort=lowest',
               '/event/3B00643505768283/tickets?listing=21328&qty=2',
               '/event/3B00643505768283?qty=&price_max=&type=Standard+Admission&sort=lowest']},
 19: {'answer': 'The Karol G order TM2609274105 is confirmed in my order history. The selling steps are: 1. List: '
                'sign in, open the order in My Account, select tickets and set the asking price. 2. Sell: the '
                'listing appears to buyers; I can edit the price or remove it before it sells. 3. Get paid: '
                'Ticketmaster transfers sold tickets to the buyer and deposits the payout in my bank account.',
      'inputs': [(0, 'david.k@test.com'), (0, 'TestPass123!')],
      'urls': ['/', '/signin', '/member', '/member/orders', '/member/orders/TM2609274105', '/sell']}}
MUTATIONS = {0: ['DELETE FROM "ticket_listings" WHERE "id"=7053;',
     'INSERT INTO "ticket_listings" ("id", "event_id", "section", "section_desc", "row", "qty_available", '
     '"face_value", "ticket_type", "accessible") VALUES (7053, \'3B006511E91D862B\', \'BALC\', \'Balcony\', '
     "'I', 2, 208.5, 'Standard Admission', 0);",
     'INSERT INTO "orders" ("id", "order_no", "user_id", "event_id", "listing_id", "section", "section_desc", '
     '"row", "qty", "unit_price", "face_total", "fee_total", "total", "delivery", "card_last4", "card_brand", '
     '"status", "guest_email", "created_at", "placed_at") VALUES (7, \'40F0E6D6A9F291\', 1, \'3B006511E91D862B\', '
     "7053, 'BALC', 'Balcony', 'I', 2, 286.9, 417.0, 156.8, 573.8, 'mobile', '4242', 'Visa', 'confirmed', NULL, "
     "'2026-09-29T00:19:01Z', '2026-09-29T00:19:01Z');"],
 1: ['DELETE FROM "ticket_listings" WHERE "id"=10900;',
     'INSERT INTO "ticket_listings" ("id", "event_id", "section", "section_desc", "row", "qty_available", '
     '"face_value", "ticket_type", "accessible") VALUES (10900, \'17006455FF52D572\', \'BALC\', \'Balcony\', '
     "'J', 3, 58.5, 'Standard Admission', 0);",
     'INSERT INTO "orders" ("id", "order_no", "user_id", "event_id", "listing_id", "section", "section_desc", '
     '"row", "qty", "unit_price", "face_total", "fee_total", "total", "delivery", "card_last4", "card_brand", '
     '"status", "guest_email", "created_at", "placed_at") VALUES (7, \'2976B471EA3EE5\', NULL, '
     "'17006455FF52D572', 10900, 'BALC', 'Balcony', 'J', 2, 80.5, 117.0, 44.0, 161.0, 'mobile', '4444', 'Visa', "
     "'confirmed', 'metallica.fan@example.com', '2026-09-29T00:19:16Z', '2026-09-29T00:19:16Z');"],
 9: ['DELETE FROM "payment_methods" WHERE "id"=5;',
     'INSERT INTO "payment_methods" ("id", "user_id", "brand", "last4", "exp_month", "exp_year", "holder") VALUES '
     "(7, 3, 'Discover', '8901', 7, 2031, 'Carol Davis');"],
 10: ['DELETE FROM "favorites" WHERE "id"=13;',
      'INSERT INTO "favorites" ("id", "user_id", "artist_id", "event_id", "created_at") VALUES (16, 4, '
      "'780815', NULL, '2026-09-29T00:20:24Z');"],
 11: ['DELETE FROM "ticket_listings" WHERE "id"=15685;',
      'INSERT INTO "ticket_listings" ("id", "event_id", "section", "section_desc", "row", "qty_available", '
      '"face_value", "ticket_type", "accessible") VALUES (15685, \'010064EDC5277AB0\', \'BALC\', \'Balcony\', '
      "'I', 3, 59.0, 'Standard Admission', 0);",
      'INSERT INTO "orders" ("id", "order_no", "user_id", "event_id", "listing_id", "section", "section_desc", '
      '"row", "qty", "unit_price", "face_total", "fee_total", "total", "delivery", "card_last4", "card_brand", '
      '"status", "guest_email", "created_at", "placed_at") VALUES (7, \'8E88F4EAF875E6\', NULL, '
      "'010064EDC5277AB0', 15685, 'BALC', 'Balcony', 'I', 2, 81.18, 118.0, 44.36, 162.36, 'mobile', '4444', "
      "'Visa', 'confirmed', 'sports.fan@example.com', '2026-09-29T00:20:33Z', '2026-09-29T00:20:33Z');"],
 17: ['DELETE FROM "ticket_listings" WHERE "id"=34930;',
      'INSERT INTO "ticket_listings" ("id", "event_id", "section", "section_desc", "row", "qty_available", '
      '"face_value", "ticket_type", "accessible") VALUES (34930, \'3000646DEDC399B4\', \'201\', \'Upper Level '
      "201', 'H', 2, 57.0, 'Standard Admission', 0);",
      'INSERT INTO "orders" ("id", "order_no", "user_id", "event_id", "listing_id", "section", "section_desc", '
      '"row", "qty", "unit_price", "face_total", "fee_total", "total", "delivery", "card_last4", "card_brand", '
      '"status", "guest_email", "created_at", "placed_at") VALUES (7, \'C32AF1C5928F69\', 1, '
      "'3000646DEDC399B4', 34930, '201', 'Upper Level 201', 'H', 4, 78.43, 228.0, 85.72, 313.72, 'mobile', "
      "'4242', 'Visa', 'confirmed', NULL, '2026-09-29T00:21:15Z', '2026-09-29T00:21:15Z');"]}
