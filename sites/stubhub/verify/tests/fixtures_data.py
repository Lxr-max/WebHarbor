"""Synthetic control fixtures."""
BASE = 'http://localhost:40105'
SPECS = {'0': {'answer': 'The eight 2026 Seahawks home games at Lumen Field in schedule order: Los Angeles Chargers (10-4-2026) from $236; San '
                 'Francisco 49ers (10-11-2026) from $367; Kansas City Chiefs (10-25-2026) from $364; Chicago Bears (11-2-2026) from $298; '
                 'Arizona Cardinals (11-8-2026) from $194; Dallas Cowboys (12-7-2026) from $297; New York Giants (12-13-2026) from $194; '
                 'Los Angeles Rams (12-25-2026) from $275. The cheapest game overall is Arizona Cardinals at $194; its get-in is 344, Row '
                 'EE. The highest get-in price among the eight games is $367.',
       'urls': ['/',
                '/search?q=seattle+seahawks',
                '/seattle-seahawks-tickets/performer/1945',
                '/seattle-seahawks-seattle-tickets-10-4-2026/event/160436504',
                '/seattle-seahawks-seattle-tickets-10-4-2026/event/160436504?quantity=&price_min=&price_max=&sort=price',
                '/seattle-seahawks-seattle-tickets-10-4-2026/event/160436504',
                '/seattle-seahawks-tickets/performer/1945',
                '/seattle-seahawks-seattle-tickets-10-11-2026/event/160436498',
                '/seattle-seahawks-seattle-tickets-10-11-2026/event/160436498?quantity=&price_min=&price_max=&sort=price',
                '/seattle-seahawks-seattle-tickets-10-11-2026/event/160436498',
                '/seattle-seahawks-tickets/performer/1945',
                '/seattle-seahawks-seattle-tickets-10-25-2026/event/160436501',
                '/seattle-seahawks-seattle-tickets-10-25-2026/event/160436501?quantity=&price_min=&price_max=&sort=price',
                '/seattle-seahawks-seattle-tickets-10-25-2026/event/160436501',
                '/seattle-seahawks-tickets/performer/1945',
                '/seattle-seahawks-seattle-tickets-11-2-2026/event/160436503',
                '/seattle-seahawks-seattle-tickets-11-2-2026/event/160436503?quantity=&price_min=&price_max=&sort=price',
                '/seattle-seahawks-seattle-tickets-11-2-2026/event/160436503',
                '/seattle-seahawks-tickets/performer/1945',
                '/seattle-seahawks-seattle-tickets-11-8-2026/event/160436506',
                '/seattle-seahawks-seattle-tickets-11-8-2026/event/160436506?quantity=&price_min=&price_max=&sort=price',
                '/seattle-seahawks-seattle-tickets-11-8-2026/event/160436506',
                '/seattle-seahawks-tickets/performer/1945',
                '/seattle-seahawks-seattle-tickets-12-7-2026/event/160436508',
                '/seattle-seahawks-seattle-tickets-12-7-2026/event/160436508?quantity=&price_min=&price_max=&sort=price',
                '/seattle-seahawks-seattle-tickets-12-7-2026/event/160436508',
                '/seattle-seahawks-tickets/performer/1945',
                '/seattle-seahawks-seattle-tickets-12-13-2026/event/160436500',
                '/seattle-seahawks-seattle-tickets-12-13-2026/event/160436500?quantity=&price_min=&price_max=&sort=price',
                '/seattle-seahawks-seattle-tickets-12-13-2026/event/160436500',
                '/seattle-seahawks-tickets/performer/1945',
                '/seattle-seahawks-seattle-tickets-12-25-2026/event/160436502',
                '/seattle-seahawks-seattle-tickets-12-25-2026/event/160436502?quantity=&price_min=&price_max=&sort=price']},
 '1': {'answer': '5 listings match all three conditions (4 tickets, clear view, under $400/ticket); the cheapest match is Upper 300-Level, '
                 ', $265 per ticket. The cheapest 4-ticket listing in the 300 Level zone is 307, Row II · Seats 13 - 16, $324 per ticket. '
                 'For four tickets the cheaper option is the clear-view match ($1060 vs $1296).',
       'urls': ['/',
                '/search?q=seattle+seahawks',
                '/seattle-seahawks-tickets/performer/1945',
                '/seattle-seahawks-seattle-tickets-10-4-2026/event/160436504',
                '/seattle-seahawks-seattle-tickets-10-4-2026/event/160436504?quantity=4&price_min=&price_max=400&sort=price&features=Clear+view',
                '/seattle-seahawks-seattle-tickets-10-4-2026/event/160436504',
                '/seattle-seahawks-seattle-tickets-10-4-2026/event/160436504?quantity=4&price_min=&price_max=&sort=price&zone=300+Level']},
 '10': {'answer': "Alice's purchases: Metallica - 2 Day Pass (October 1 & 3) Thu, Oct 1 • 7:55 PM • Sphere at The Venetian Resort Order "
                  '41810907 · placed Sep 23, 2026 Confirmed 2 tickets $2,572.95 | Rush Sun, Oct 11 • 2:30 AM • Climate Pledge Arena Order '
                  '41811044 · placed Sep 5, 2026 Delivered 2 tickets $1,106.95; with delivery methods and totals from the order details: '
                  'Metallica 2 Day Pass order 41810907 — Instant download, total $2,572.95, Confirmed; Rush order 41811044 — Mobile '
                  'transfer, total $1,106.95, Delivered. The largest total is the Metallica 2 Day Pass order ($2,572.95). Her completed '
                  'sales: Seattle Opera - Salome Thu, Oct 29 • 2:30 AM • Marion Oliver McCaw Hall at Seattle Center - Complex 2 tickets · '
                  'SECTION 212 Row 4 · order 41810517 Paid $118.40. Her active listings: Seattle Opera - Salome Thu, Oct 29 • 2:30 AM • '
                  'Marion Oliver McCaw Hall at Seattle Center - Complex SECTION 212 Row 12 · Seats 5 - 8 · 4 tickets $89 each Update. She '
                  'has 1 payment cards on file.',
        'urls': ['/secure/login',
                 '/',
                 '/secure/myaccount/purchases',
                 '/secure/myaccount/purchases/41810907',
                 '/secure/myaccount/purchases',
                 '/secure/myaccount/purchases/41811044',
                 '/secure/myaccount/purchases',
                 '/secure/myaccount/sales',
                 '/secure/myaccount/listings',
                 '/secure/myaccount/payments']},
 '11': {'answer': 'Cards on file before: Visa ••••4242 (exp 08/2028, default) and Mastercard ••••8321 (exp 03/2027). Added a new '
                  "Mastercard in Alice's name (••••4444, exp 11/2029), made it the default, and removed the older non-default Mastercard "
                  '••••8321. Final card list: Buy sports, concert and theater tickets on StubHub! Sports Concerts Theater Festivals Gift '
                  'Cards Explore Sell Favorites My Tickets Card removed. My Tickets Orders My Listings My Sales Payments Payments Cards on '
                  'file Visa ••••4242 Alice Johnson · expires 08/2028 Make default Remove Mastercard ••••4444 Alice Johnson · expires '
                  '11/2029 Default Remove ',
        'sql': ['INSERT INTO "payment_cards" (id, user_id, brand, last4, holder, exp_month, exp_year, is_default) VALUES (8, 1, '
                "'Mastercard', '4444', 'Alice Johnson', 11, 2029, 1)",
                'DELETE FROM "payment_cards" WHERE "id" = 2',
                'UPDATE "payment_cards" SET "is_default" = 0 WHERE "id" = 1'],
        'urls': ['/secure/login', '/', '/secure/myaccount/payments']},
 '12': {'answer': 'Created a new account (jamie.reviewer@example.com) and bought the cheapest single ticket (302, Row EE) to the Oct 11 '
                  '49ers at Seahawks game with instant download delivery, paid with a valid test card. Order reference 41801303, final '
                  "total $369.95. The order appears in the new account's purchase history.",
        'sql': ['INSERT INTO "users" (id, username, email, display_name, password_hash, metro_id) VALUES (5, \'jamie-reviewer\', '
                "'jamie.reviewer@example.com', 'Jamie Reviewer', 'b''$2b$12$60ROaBcYlciRX3SS4ip9Xuy8GCRPhnqoGMD.xi8KmYmtcoHGS7e3i''', 1)",
                'INSERT INTO "orders" (id, order_number, user_id, event_id, listing_id, quantity, unit_price, delivery_method, '
                "delivery_fee, processing_fee, total, status, placed_at, card_last4) VALUES (9, '41801303', 5, 128, 335, 1, 367, "
                "'instant', 0.0, 2.95, 369.95, 'Confirmed', '2026-09-26 12:00:00.000000', 'Visa ••••5556')",
                'UPDATE "listings" SET "is_sold" = 0, "quantity" = "quantity" - 1 WHERE "id" = 335',
                'INSERT INTO "payment_cards" (id, user_id, brand, last4, holder, exp_month, exp_year, is_default) VALUES (8, 5, \'Visa\', '
                "'5556', 'Jamie Reviewer', 9, 2028, 1)",
                'INSERT INTO "notifications" (id, user_id, body, kind, created_at) VALUES (9, 5, \'Order confirmed: San Francisco 49ers at '
                "Seattle Seahawks on Sun, Oct 11.', 'info', '2026-09-26 12:00:00.000000')"],
        'urls': ['/secure/register',
                 '/',
                 '/search?q=seattle+seahawks',
                 '/seattle-seahawks-tickets/performer/1945',
                 '/seattle-seahawks-seattle-tickets-10-11-2026/event/160436498',
                 '/seattle-seahawks-seattle-tickets-10-11-2026/event/160436498?quantity=1&price_min=&price_max=&sort=price',
                 '/seattle-seahawks-seattle-tickets-10-11-2026/event/160436498/listing/335',
                 '/secure/checkout/review',
                 '/secure/checkout/payment',
                 '/secure/checkout/confirm',
                 '/secure/checkout/confirmation/41801303',
                 '/secure/myaccount/purchases']},
 '13': {'answer': 'The Seattle Kraken list 41 home games at Climate Pledge Arena, Seattle, WA. First home game: Calgary Flames '
                  '(10-4-2026), get-in $65. Last home game: Winnipeg Jets (4-3-2027), get-in $90. The next three home games after the '
                  'opener: Vegas Golden Knights (10-6-2026); Detroit Red Wings (10-20-2026); Utah Mammoth (10-22-2026). First: section 2B, '
                  'row 15. Last: section 225, row 19.',
        'urls': ['/',
                 '/search?q=seattle+kraken',
                 '/seattle-kraken-tickets/performer/900000460',
                 '/seattle-kraken-tickets/performer/900000460?page=3',
                 '/seattle-kraken-seattle-tickets-10-4-2026/event/161482397',
                 '/seattle-kraken-seattle-tickets-4-3-2027/event/161482396']},
 '14': {'answer': 'For the Oct 11 49ers at Seahawks game the lowest-priced listing per zone: 100 Level: 150, Row Z, $477; 200 Level: 215, '
                  'Row L · Seats 6 - 9, $645; 300 Level: 302, Row EE, $367. The 300 Level has the cheapest get-in ($367); the gap between '
                  'the cheapest and most expensive zone is $278. The event has 28 total listings across all zones.',
        'urls': ['/',
                 '/search?q=seattle+seahawks',
                 '/seattle-seahawks-tickets/performer/1945',
                 '/seattle-seahawks-seattle-tickets-10-11-2026/event/160436498',
                 '/seattle-seahawks-seattle-tickets-10-11-2026/event/160436498?quantity=&price_min=&price_max=&sort=price&zone=100+Level',
                 '/seattle-seahawks-seattle-tickets-10-11-2026/event/160436498?quantity=&price_min=&price_max=&sort=price&zone=200+Level',
                 '/seattle-seahawks-seattle-tickets-10-11-2026/event/160436498?quantity=&price_min=&price_max=&sort=price&zone=300+Level']},
 '15': {'answer': 'The cheapest 4-ticket listing for the Oct 4 Chargers at Seahawks game is Upper 300-Level,  at $265 per ticket '
                  '(features: 4 tickets together, Clear view; zone Other; a seat view photo appears). Price breakdown at quantity 2: $265 '
                  'x 2 = $530 subtotal, final total $532.95 including the $2.95 processing fee. At quantity 4: subtotal $1060, final total '
                  '$1062.95. The processing fee does not change with quantity; the per-ticket total is $266.48 at qty 2 and $265.74 at qty '
                  '4.',
        'urls': ['/',
                 '/search?q=seattle+seahawks',
                 '/seattle-seahawks-tickets/performer/1945',
                 '/seattle-seahawks-seattle-tickets-10-4-2026/event/160436504',
                 '/seattle-seahawks-seattle-tickets-10-4-2026/event/160436504?quantity=4&price_min=&price_max=&sort=price',
                 '/seattle-seahawks-seattle-tickets-10-4-2026/event/160436504/listing/441']},
 '16': {'answer': 'Sorted by Best deal, the three listings with the largest discounts: 239: now $449 (was $659), saving $210 (32%); '
                  'CLB212: now $485 (was $687), saving $202 (29%); 337: now $244 (was $409), saving $165 (40%). The biggest discount is in '
                  'section 239. The event has 30 total listings.',
        'urls': ['/',
                 '/search?q=seattle+seahawks',
                 '/seattle-seahawks-tickets/performer/1945',
                 '/seattle-seahawks-seattle-tickets-10-4-2026/event/160436504',
                 '/seattle-seahawks-seattle-tickets-10-4-2026/event/160436504?quantity=&price_min=&price_max=&sort=best_deal']},
 '17': {'answer': "Metallica's October 1 Las Vegas event page (single night, get-in $749) shows these nearby events: Thu, Oct 1 • 7:55 PM "
                  'Metallica - 2 Day Pass (October 1 & 3); Sat, Oct 3 • 8:00 PM Metallica; Thu, Oct 8 • 8:25 PM Metallica - 2 Day Pass '
                  '(October 8 & 10); Thu, Oct 8 • 8:30 PM Metallica. Opened each: Thu, Oct 1 • 7:55 PM Metallica - 2 Day Pass (October 1 & '
                  '3): get-in $1137, 29 listings; Sat, Oct 3 • 8:00 PM Metallica: get-in $1124, 10 listings; Thu, Oct 8 • 8:25 PM '
                  'Metallica - 2 Day Pass (October 8 & 10): get-in $1092, 27 listings; Thu, Oct 8 • 8:30 PM Metallica: get-in $725, 25 '
                  'listings. The cheapest nearby get-in is Thu, Oct 8 • 8:30 PM Metallica at $725. The single-night get-in ($749) compares '
                  'with the two-day pass ($1137) covering the same venue: the pass costs more upfront but covers both nights (implied '
                  '$568.50 per night).',
        'urls': ['/',
                 '/search?q=metallica',
                 '/metallica-tickets/performer/8147',
                 '/metallica-las-vegas-tickets-10-1-2026/event/160569378',
                 '/metallica-las-vegas-tickets-10-1-2026/event/160569378?quantity=&price_min=&price_max=&sort=price',
                 '/metallica-las-vegas-tickets-10-1-2026/event/160572545',
                 '/metallica-las-vegas-tickets-10-1-2026/event/160572545?quantity=&price_min=&price_max=&sort=price',
                 '/metallica-las-vegas-tickets-10-1-2026/event/160572545',
                 '/metallica-las-vegas-tickets-10-1-2026/event/160569378?quantity=&price_min=&price_max=&sort=price',
                 '/metallica-las-vegas-tickets-10-3-2026/event/160569380',
                 '/metallica-las-vegas-tickets-10-3-2026/event/160569380?quantity=&price_min=&price_max=&sort=price',
                 '/metallica-las-vegas-tickets-10-3-2026/event/160569380',
                 '/metallica-las-vegas-tickets-10-1-2026/event/160569378?quantity=&price_min=&price_max=&sort=price',
                 '/metallica-las-vegas-tickets-10-8-2026/event/160611325',
                 '/metallica-las-vegas-tickets-10-8-2026/event/160611325?quantity=&price_min=&price_max=&sort=price',
                 '/metallica-las-vegas-tickets-10-8-2026/event/160611325',
                 '/metallica-las-vegas-tickets-10-1-2026/event/160569378?quantity=&price_min=&price_max=&sort=price',
                 '/metallica-las-vegas-tickets-10-8-2026/event/160611244',
                 '/metallica-las-vegas-tickets-10-8-2026/event/160611244?quantity=&price_min=&price_max=&sort=price']},
 '18': {'answer': "The full event catalog's first three events: Pacific Northwest Ballet - Serenade (9-26-2026); Greenshield Industrial "
                  "Supply Season End (9-26-2026); Lovers Rock Reggae Live (9-26-2026). Page 2's first three: Gnash (9-26-2026); Kamelot "
                  '(9-26-2026); Beth Stelling (9-26-2026). The catalog lists 1267 events with tickets available. The earliest event is '
                  'Pacific Northwest Ballet - Serenade with a get-in of $106 and 1 listings. Greenshield Industrial Supply Season End: '
                  '$228, 13 listings. Lovers Rock Reggae Live: $70, 21 listings, cheapest, saving $36 versus Pacific Northwest Ballet - '
                  'Serenade and $158 versus Greenshield.',
        'urls': ['/explore',
                 '/explore?page=2',
                 '/explore?page=1',
                 '/pacific-northwest-ballet-seattle-tickets-9-26-2026/event/161322492',
                 '/pacific-northwest-ballet-seattle-tickets-9-26-2026/event/161322492?quantity=&price_min=&price_max=&sort=price',
                 '/greenshield-industrial-supply-night-monroe-tickets-9-26-2026/event/160622756',
                 '/lovers-rock-new-york-tickets-9-26-2026/event/161326323']},
 '19': {'answer': 'Created a new account (robin.reviewer@example.com), bought a $50 sports-design gift card for Sam Friend '
                  '(sam.friend@example.com) — code SH6ET2TNLHPC, status Sent — and added the Seattle Kraken to favorites (confirmed in the '
                  'Favorites page). The Kraken performer page lists 41 upcoming home games; the next one is Calgary Flames (10-4-2026). '
                  'Delivered to sam.friend@example.com.',
        'sql': ['INSERT INTO "users" (id, username, email, display_name, password_hash, metro_id) VALUES (5, \'robin-reviewer\', '
                "'robin.reviewer@example.com', 'Robin Reviewer', 'b''$2b$12$cd4pwx7SC.QMaPfGhN1vTu/bs6RHhucim/cJJbVsq3prhmkYVEFiu''', 1)",
                'INSERT INTO "gift_card_orders" (id, user_id, amount, recipient_name, recipient_email, message, design, code, status, '
                "created_at) VALUES (5, 5, 50, 'Sam Friend', 'sam.friend@example.com', 'Enjoy the game!', 'sports', 'SH6ET2TNLHPC', "
                "'Delivered', '2026-09-26 12:00:00.000000')"],
        'urls': ['/secure/register',
                 '/',
                 '/gift-cards',
                 '/search?q=seattle+kraken',
                 '/seattle-kraken-tickets/performer/900000460',
                 '/favorites']},
 '2': {'answer': 'Metallica plays Sphere at The Venetian Resort, Las Vegas. The two-day pass (Oct 1 & 3): 29 listings, get-in $1137 '
                 '(implied $568.50 per night), cheapest listing in 310. The Oct 1 single night: 26 listings, get-in $749, cheapest in 407. '
                 'The Oct 3 single night: 10 listings, get-in $1124, cheapest in 110. The two single nights together cost $1873, so the '
                 'two-day pass is the cheaper way to see both shows.',
       'urls': ['/',
                '/search?q=metallica',
                '/metallica-tickets/performer/8147',
                '/metallica-las-vegas-tickets-10-1-2026/event/160572545',
                '/metallica-las-vegas-tickets-10-1-2026/event/160572545?quantity=&price_min=&price_max=&sort=price',
                '/metallica-las-vegas-tickets-10-1-2026/event/160572545',
                '/metallica-tickets/performer/8147',
                '/metallica-las-vegas-tickets-10-1-2026/event/160569378',
                '/metallica-las-vegas-tickets-10-1-2026/event/160569378?quantity=&price_min=&price_max=&sort=price',
                '/metallica-las-vegas-tickets-10-1-2026/event/160569378',
                '/metallica-tickets/performer/8147',
                '/metallica-las-vegas-tickets-10-3-2026/event/160569380',
                '/metallica-las-vegas-tickets-10-3-2026/event/160569380?quantity=&price_min=&price_max=&sort=price']},
 '20': {'answer': 'Kraken: 44,200 followers, 41 upcoming home events, next home game Calgary Flames at Seattle Kraken (10-4-2026) get-in '
                  '$65; Seahawks: 62,800 followers, 8 upcoming home events, next home game Los Angeles Chargers at Seattle Seahawks '
                  '(10-4-2026) get-in $236; Sounders FC: 56,600 followers, 5 upcoming home events, next home game Minnesota United FC at '
                  'Seattle Sounders FC (9-26-2026) get-in $18. The Kraken have the most home events; the Seahawks have the largest '
                  'follower count.',
        'urls': ['/',
                 '/search?q=seattle+kraken',
                 '/seattle-kraken-tickets/performer/900000460',
                 '/search?q=seattle+seahawks',
                 '/seattle-seahawks-tickets/performer/1945',
                 '/search?q=seattle+sounders',
                 '/seattle-sounders-fc-tickets/performer/388488']},
 '3': {'answer': 'Bought 2 tickets to the Nov 8 Cardinals at Seahawks game (344, Row EE) with UPS delivery, paid with a new Visa test card '
                 "in Bob's name. Order reference 41801303; delivery fee $14.95; processing fee $2.95; final total $405.90.",
       'sql': ['INSERT INTO "orders" (id, order_number, user_id, event_id, listing_id, quantity, unit_price, delivery_method, '
               "delivery_fee, processing_fee, total, status, placed_at, card_last4) VALUES (9, '41801303', 2, 134, 453, 2, 194, 'ups', "
               "14.95, 2.95, 405.9, 'Confirmed', '2026-09-26 12:00:00.000000', 'Visa ••••1881')",
               'UPDATE "listings" SET "is_sold" = 1, "quantity" = "quantity" - 2 WHERE "id" = 453',
               'INSERT INTO "notifications" (id, user_id, body, kind, created_at) VALUES (9, 2, \'Order confirmed: Arizona Cardinals at '
               "Seattle Seahawks on Sun, Nov 8.', 'info', '2026-09-26 12:00:00.000000')"],
       'urls': ['/secure/login',
                '/',
                '/search?q=seattle+seahawks',
                '/seattle-seahawks-tickets/performer/1945',
                '/seattle-seahawks-seattle-tickets-11-8-2026/event/160436506',
                '/seattle-seahawks-seattle-tickets-11-8-2026/event/160436506?quantity=2&price_min=&price_max=250&sort=price',
                '/seattle-seahawks-seattle-tickets-11-8-2026/event/160436506/listing/453',
                '/secure/checkout/review',
                '/secure/checkout/payment',
                '/secure/checkout/confirm',
                '/secure/checkout/confirmation/41801303']},
 '4': {'answer': 'Listed 2 tickets together (section 220, row 14, seats 5-6) at $195 each for the Bears at Seahawks game, then updated the '
                 'price to $180 — My Listings now shows the 220 row 14 listing at $180 each. The game is displayed as Mon, Nov 2 at Lumen '
                 'Field at Lumen Field Event - Complex, Seattle. Alice has 2 listings for sale: section 220 row 14 at $180 each and '
                 'SECTION 212 row 12 at $89 each — a combined asking value of $269 per ticket ($716 total across 2 + 4 tickets).',
       'sql': ['INSERT INTO "listings" (id, upstream_id, event_id, section, zone, row, seats, quantity, price, original_price, features, '
               "badges, deal_rating, seat_view_file, seller_id, is_sold, is_sponsored, created_at) VALUES (20886, NULL, 132, '220', '200 "
               'Level\', \'14\', \'5-6\', 2, 180, NULL, \'["2 tickets together"]\', \'[]\', NULL, NULL, 1, 0, 0, \'2026-09-26 '
               "12:00:00.000000')",
               'UPDATE "events" SET "listing_count" = 11, "min_price" = 180 WHERE "id" = 132'],
       'urls': ['/secure/login',
                '/',
                '/selltickets',
                '/selltickets?q=Chicago+Bears+at+Seattle+Seahawks',
                '/selltickets/event/160436503',
                '/secure/myaccount/listings']},
 '5': {'answer': 'The site offers gift card amounts $25/$50/$75/$100/$150/$200/$250/$500 and five designs (classic, birthday, holiday, '
                 'sports, concert). Bought a $150 holiday gift card for Danny (danny.gift@example.com) with a birthday message. Gift card '
                 "code SHSNHALS5USF, status Sent; confirmation: Your $150 gift card for Danny is on its way to danny.. Carol's order "
                 'history now shows 2 gift card orders; the earliest one is the $100 classic gift card purchased Jul 24, 2026. Status: '
                 'Delivered to danny.gift@example.com.',
       'sql': ['INSERT INTO "gift_card_orders" (id, user_id, amount, recipient_name, recipient_email, message, design, code, status, '
               "created_at) VALUES (5, 3, 150, 'Danny', 'danny.gift@example.com', 'Happy birthday Danny!', 'holiday', 'SHSNHALS5USF', "
               "'Delivered', '2026-09-26 12:00:00.000000')"],
       'urls': ['/secure/login', '/', '/gift-cards']},
 '6': {'answer': 'Favorites now shows my three new entries: metallica, Olivia Rodrigo, and the Dec 13 Giants at Seahawks game, alongside '
                 "the two favorites already on the account (katseye, luke bryan) — 5 favorites in total. Each favorited performer's "
                 'upcoming events are listed on their performer pages (metallica 20 events, Olivia Rodrigo with its own schedule), and the '
                 'favorited event shows its date.',
       'sql': ['INSERT INTO "favorites" (id, user_id, performer_id, event_id, created_at) VALUES (14, 4, 393, NULL, \'2026-09-26 '
               "12:00:00.000000')",
               'INSERT INTO "favorites" (id, user_id, performer_id, event_id, created_at) VALUES (15, 4, 436, NULL, \'2026-09-26 '
               "12:00:00.000000')",
               'INSERT INTO "favorites" (id, user_id, performer_id, event_id, created_at) VALUES (16, 4, NULL, 129, \'2026-09-26 '
               "12:00:00.000000')",
               'UPDATE "performers" SET "followers" = 114001 WHERE "id" = 393',
               'UPDATE "performers" SET "followers" = 69001 WHERE "id" = 436'],
       'urls': ['/secure/login',
                '/',
                '/search?q=metallica',
                '/metallica-tickets/performer/8147',
                '/olivia-rodrigo-tickets/performer/101864867',
                '/search?q=seattle+seahawks',
                '/seattle-seahawks-tickets/performer/1945',
                '/seattle-seahawks-seattle-tickets-12-13-2026/event/160436500',
                '/favorites']},
 '7': {'answer': "For 'metal' the search suggestion service proposes: "
                 '[{"name":"metallica","type":"performer","url":"/metallica-tickets/performer/8147"}]. For \'seattle\' it proposes: '
                 'seattle kraken, seattle mariners, seattle opera, seattle seahawks, seattle sounders fc, seattle symphony. Seattle '
                 'Sounders FC: 56,600 followers, 5 upcoming events; next event "Minnesota United FC at Seattle Sounders FC" on 9-26-2026 '
                 'at Lumen Field. Seattle Mariners: 75,200 followers, 2 upcoming events; next event "Los Angeles Angels at Seattle '
                 'Mariners" on 9-26-2026 at T-Mobile Park. The Seattle Sounders FC have more upcoming events than the Mariners (5 vs 2).',
       'urls': ['/',
                '/search?q=metal',
                '/secure/search/getSuggestedSearches?q=metal',
                '/',
                '/search?q=seattle',
                '/secure/search/getSuggestedSearches?q=seattle',
                '/search?q=seattle',
                '/seattle-sounders-fc-tickets/performer/388488',
                '/search?q=seattle',
                '/seattle-mariners-tickets/performer/1043']},
 '8': {'answer': 'The Theater category contains: Musicals, Plays, Comedy, Family, Classical and Opera, Dance / Ballet, Broadway. The three '
                 'soonest Comedy events: The Rocky Horror Show (9-26-2026); Little Shop of Horrors (9-26-2026); Garry Starr (9-26-2026). '
                 'Their event pages report: The Rocky Horror Show: get-in $104, 14 listings, at Sep 26 • 7:00 PM Studio 54; Little Shop of '
                 'Horrors: get-in $400, 3 listings, at Sep 26 • 9:00 PM La Mirada Theatre; Garry Starr: get-in $162, 24 listings, at Sep '
                 '26 • 9:00 PM Studio Seaview. The event with the most available listings is Garry Starr (24 listings).',
       'urls': ['/comedy-tickets/category/209',
                '/the-rocky-horror-show-new-york-tickets-9-26-2026/event/161069710',
                '/the-rocky-horror-show-new-york-tickets-9-26-2026/event/161069710?quantity=&price_min=&price_max=&sort=price',
                '/the-rocky-horror-show-new-york-tickets-9-26-2026/event/161069710',
                '/comedy-tickets/category/209',
                '/little-shop-of-horrors-la-mirada-tickets-9-26-2026/event/161174556',
                '/little-shop-of-horrors-la-mirada-tickets-9-26-2026/event/161174556?quantity=&price_min=&price_max=&sort=price',
                '/little-shop-of-horrors-la-mirada-tickets-9-26-2026/event/161174556',
                '/comedy-tickets/category/209',
                '/garry-starr-new-york-tickets-9-26-2026/event/162068544',
                '/garry-starr-new-york-tickets-9-26-2026/event/162068544?quantity=&price_min=&price_max=&sort=price']},
 '9': {'answer': 'Every Salome event listed on the site: 10-17-2026 get-in $123; 10-23-2026 get-in $120; 10-25-2026 get-in $153; '
                 '10-28-2026 get-in $89; 10-31-2026 get-in $117. Comparing the two earliest: 27 vs 24 listings — Seattle Opera - Salome '
                 'has more listings; the lower get-in belongs to /seattle-opera-seattle-tickets-10-23-2026/event/161306174 ($120). Venue: '
                 'Marion Oliver McCaw Hall at Seattle Center - Complex, Seattle. Cheapest listing sections: 10-17-2026 -> ST 41; '
                 '10-23-2026 -> ST 42.',
       'urls': ['/',
                '/search?q=salome',
                '/seattle-opera-seattle-tickets-10-17-2026/event/161306164',
                '/seattle-opera-seattle-tickets-10-17-2026/event/161306164?quantity=&price_min=&price_max=&sort=price',
                '/seattle-opera-seattle-tickets-10-17-2026/event/161306164',
                '/search?q=salome',
                '/seattle-opera-seattle-tickets-10-23-2026/event/161306174',
                '/seattle-opera-seattle-tickets-10-23-2026/event/161306174?quantity=&price_min=&price_max=&sort=price',
                '/seattle-opera-seattle-tickets-10-23-2026/event/161306174',
                '/search?q=salome',
                '/seattle-opera-seattle-tickets-10-25-2026/event/161306180',
                '/seattle-opera-seattle-tickets-10-25-2026/event/161306180?quantity=&price_min=&price_max=&sort=price',
                '/seattle-opera-seattle-tickets-10-25-2026/event/161306180',
                '/search?q=salome',
                '/seattle-opera-seattle-tickets-10-28-2026/event/161306184',
                '/seattle-opera-seattle-tickets-10-28-2026/event/161306184?quantity=&price_min=&price_max=&sort=price',
                '/seattle-opera-seattle-tickets-10-28-2026/event/161306184',
                '/search?q=salome',
                '/seattle-opera-seattle-tickets-10-31-2026/event/161306189',
                '/seattle-opera-seattle-tickets-10-31-2026/event/161306189?quantity=&price_min=&price_max=&sort=price',
                '/seattle-opera-seattle-tickets-10-31-2026/event/161306189',
                '/search?q=salome']}}

SPECS["18"]["answer"] = "Pacific Northwest Ballet - Serenade: September 26, 2026, Marion Oliver McCaw Hall, $106, 1 listing. Greenshield Industrial Supply Season End: September 26, 2026, Evergreen Speedway, $228, 13 listings. Lovers Rock Reggae Live: September 26, 2026, Sony Hall, $70, 21 listings; cheapest, saving $36 versus Pacific Northwest Ballet and $158 versus Greenshield."
