"""fixtures_data.py — honest-run fixtures for the disney verifier contract.

Every SPECS row was transcribed from the r2 reviewer's independent
Playwright honest-path walks on the wh-disney-r2-review container (per-task
reset + fresh context): ``urls`` is the walked navigation sequence, ``answer`` quotes the
observed page values verbatim, and ``sql`` reproduces the exact after-state
the walk's stateful actions wrote. The confirmation codes are the codes the
walks actually received.
"""
B = "http://localhost:53122"

SPECS = {

"0": {
 "urls": [f"{B}/", f"{B}/movies?q=&status=streaming&genre=&sort=title",
          f"{B}/movies/avatar-the-way-of-water", f"{B}/movies?q=&status=streaming&genre=&sort=title",
          f"{B}/movies?q=&status=coming_soon&genre=&sort=title",
          f"{B}/movies/avengers-doomsday", f"{B}/login", f"{B}/",
          f"{B}/movies?q=&status=coming_soon&genre=&sort=title",
          f"{B}/movies/avengers-doomsday", f"{B}/favorites"],
 "answer": ("6 movies are Now on Disney+. The first by title A-Z is Avatar: The Way of "
            "Water, rated PG-13 with a runtime of 3h 12min. Switching the status filter to "
            "Coming Soon leaves 9 movies. The alphabetically first Coming Soon movie is "
            "Avengers: Doomsday, with release date December 18, 2026. After logging in as "
            "Alice and adding this movie to favorites, Alice has 4 favorites in total."),
 "sql": ("INSERT INTO favorites (user_id, item_type, item_key, added_at) "
         "VALUES (1, 'movie', 'avengers-doomsday', '2026-09-29');"),
},

"1": {
 "urls": [f"{B}/", f"{B}/login", f"{B}/signup", f"{B}/",
          f"{B}/movies?q=&status=coming_soon&genre=Animation&sort=title",
          f"{B}/movies/frozen-3", f"{B}/login", f"{B}/favorites"],
 "answer": ("9 Coming Soon movies; narrowing to the Animation genre leaves 6. The first "
            "by title A-Z is Frozen 3, release date November 24, 2027, rating Not Yet "
            "Rated. After adding it to favorites, logging out and logging back in, the "
            "favorites page shows 1 favorite in total: the movie Frozen 3."),
 "sql": ("INSERT INTO users (email, name, password_hash, joined) VALUES "
         "('moana.fan@test.com', 'Moana Fan', 'x', '2026-09-29'); "
         "INSERT INTO favorites (user_id, item_type, item_key, added_at) "
         "SELECT id, 'movie', 'frozen-3', '2026-09-29' FROM users WHERE email='moana.fan@test.com';"),
},

"2": {
 "urls": [f"{B}/", f"{B}/movies?q=star&status=&genre=&sort=release",
          f"{B}/movies?q=&status=coming_soon&genre=Science+Fiction&sort=title",
          f"{B}/movies/avengers-doomsday",
          f"{B}/movies?q=&status=&genre=Science+Fiction&sort=release",
          f"{B}/movies/star-wars-starfighter",
          f"{B}/movies?q=&status=&genre=Science+Fiction&sort=title",
          f"{B}/movies/avatar-fire-and-ash"],
 "answer": ("2 movies match 'star' (Star Wars: Starfighter and Star Wars: The Mandalorian "
            "and Grogu). Coming Soon plus Science Fiction: 2 movies. Sorted by title the "
            "first is Avengers: Doomsday, release date December 18, 2026. With the status "
            "filter cleared, Science Fiction only, sorted by release date, the most recent "
            "one is Star Wars: Starfighter: rating Not Yet Rated, release date May 28, "
            "2027. Finally sorted by title, the first Science Fiction movie is Avatar: "
            "Fire and Ash, rated PG-13; one of its cast members is Sam Worthington."),
 "sql": None,
},

"3": {
 "urls": [f"{B}/", f"{B}/shows?q=&genre=Animation&sort=title",
          f"{B}/shows?q=&genre=Science+Fiction&sort=title",
          f"{B}/shows?q=star&genre=&sort=title",
          f"{B}/shows/lego-star-wars-droid-tales",
          f"{B}/shows?q=&genre=&sort=title",
          f"{B}/shows/ducktales-products", f"{B}/shows?q=&genre=&sort=title",
          f"{B}/shows/ducktales",
          f"{B}/shows?q=big+hero&genre=&sort=title",
          f"{B}/shows/big-hero-6-the-series", f"{B}/login", f"{B}/",
          f"{B}/shows?q=big+hero&genre=&sort=title",
          f"{B}/shows/big-hero-6-the-series", f"{B}/favorites"],
 "answer": ("25 Animation shows appear; keeping only Science Fiction instead leaves 10. "
            "Searching for 'star' matches 2 shows; the first match LEGO Star Wars: Droid "
            "Tales has release year 2015. Two shows are titled DuckTales; the newer "
            "series is the 2017 one, rated TV-Y7. Big Hero 6: The Series is rated "
            "TV-Y7. After logging in as Bob and adding it to favorites, Bob has 4 "
            "favorites in total and 3 shows saved."),
 "sql": ("INSERT INTO favorites (user_id, item_type, item_key, added_at) "
         "VALUES (2, 'show', 'big-hero-6-the-series', '2026-09-30');"),
},

"4": {
 "urls": [f"{B}/search?q=mickey", f"{B}/shows/disney-mickey-mouse",
          f"{B}/shows?q=&genre=Variety&sort=title",
          f"{B}/shows/disney-mickey-mouse",
          f"{B}/shows?q=&genre=&sort=title", f"{B}/login", f"{B}/search?q=mickey",
          f"{B}/shows/disney-mickey-mouse", f"{B}/favorites",
          f"{B}/shows?q=duck&genre=&sort=title"],
 "answer": ("The 'mickey' search shows 2 shows and 13 parks & entertainment results. "
            "Disney Mickey Mouse is rated TV-G. The Variety genre leaves 3 shows; the "
            "first one is Disney Mickey Mouse with release year 2012. The full catalog "
            "has 54 shows. After logging in as Carol and adding the Mickey Mouse show, "
            "Carol has 3 favorites in total. Searching shows for 'duck' matches 3."),
 "sql": ("INSERT INTO favorites (user_id, item_type, item_key, added_at) "
         "VALUES (3, 'show', 'disney-mickey-mouse', '2026-09-29');"),
},

"5": {
 "urls": [f"{B}/", f"{B}/shows?q=&genre=Comedy&sort=title",
          f"{B}/shows?q=&genre=Fantasy&sort=title",
          f"{B}/shows/adventures-of-the-gummi-bears", f"{B}/login", f"{B}/",
          f"{B}/shows?q=&genre=Fantasy&sort=title",
          f"{B}/shows/adventures-of-the-gummi-bears",
          f"{B}/shows?q=duck&genre=&sort=title", f"{B}/shows/ducktales",
          f"{B}/shows?q=&genre=Comedy&sort=title", f"{B}/shows/austin-ally"],
 "answer": ("The full A-Z catalog has 54 shows. Keeping only Comedy leaves 25; keeping "
            "only Fantasy instead leaves 9. The first Fantasy show by title is Adventures "
            "of the Gummi Bears, release year 1985. Searching for 'duck' matches 3 shows; "
            "DuckTales is rated TV-Y7. Keeping only Comedy again and sorting by title, "
            "the first Comedy show is Austin & Ally, rated TV-G."),
 "sql": ("INSERT INTO favorites (user_id, item_type, item_key, added_at) "
         "VALUES (2, 'show', 'adventures-of-the-gummi-bears', '2026-09-29');"),
},

"6": {
 "urls": [f"{B}/", f"{B}/parks", f"{B}/parks/attractions?q=&park=magic-kingdom&type=&interest=Thrill+Rides&age=&height=&sort=name",
          f"{B}/parks/attractions?q=&park=magic-kingdom&type=&interest=Thrill+Rides&age=&height=40&sort=name",
          f"{B}/parks/attractions/magic-kingdom/space-mountain",
          f"{B}/parks/attractions?q=&park=magic-kingdom&type=&interest=Thrill+Rides&age=&height=48&sort=name",
          f"{B}/parks/attractions/magic-kingdom/tron-lightcycle-run",
          f"{B}/parks/attractions?q=&park=magic-kingdom&type=Entertainment&interest=&age=&height=&sort=name"],
 "answer": ("Magic Kingdom Park plus Thrill Rides leaves 5 results. Adding the 40-inch "
            "height filter leaves 3. Sorted by name, the first result is Space Mountain "
            "with height requirement 44\" or taller and the Thrill Rides interest. "
            "Clearing the height filter leaves 5 again. Filtering heights to 48 inches or "
            "taller leaves 1 result: TRON Lightcycle / Run. Keeping only "
            "Entertainment for Magic Kingdom Park lists 26 entertainment items."),
 "sql": None,
},

"7": {
 "urls": [f"{B}/", f"{B}/parks", f"{B}/parks/attractions?q=&park=&type=Entertainment&interest=Character+Experiences&age=&height=&sort=name",
          f"{B}/parks/attractions?q=&park=magic-kingdom&type=Entertainment&interest=Character+Experiences&age=&height=&sort=name",
          f"{B}/parks/attractions/magic-kingdom/starlight-dream-night-away-parade",
          f"{B}/parks/attractions?q=&park=&type=&interest=Fireworks&age=&height=&sort=name",
          f"{B}/parks/attractions/epcot/heartbeat-of-freedom",
          f"{B}/login", f"{B}/parks/attractions?q=&park=&type=&interest=Fireworks&age=&height=&sort=name",
          f"{B}/parks/attractions/epcot/heartbeat-of-freedom", f"{B}/favorites"],
 "answer": ("44 Entertainment entries with the Character Experiences interest remain; "
            "narrowing to Magic Kingdom Park leaves 12. Sorted by name the first result "
            "is Disney Starlight: Dream the Night Away. Across all parks 6 fireworks "
            "events exist. The Heartbeat of Freedom fireworks show at EPCOT is "
            "favorited; Alice has 4 favorites in total."),
 "sql": ("INSERT INTO favorites (user_id, item_type, item_key, added_at) "
         "VALUES (1, 'attraction', 'epcot/heartbeat-of-freedom', '2026-09-30');"),
},

"8": {
 "urls": [f"{B}/", f"{B}/parks", f"{B}/parks/attractions?q=&park=&type=Attraction&interest=&age=&height=&sort=name",
          f"{B}/parks/attractions?q=&park=&type=Attraction&interest=&age=&height=38&sort=name",
          f"{B}/parks/attractions?q=&park=&type=Attraction&interest=&age=&height=44&sort=name",
          f"{B}/parks/attractions?q=&park=&type=Attraction&interest=&age=&height=48&sort=height",
          f"{B}/parks/attractions/blizzard-beach/downhill-double-dipper",
          f"{B}/parks/attractions/magic-kingdom/tron-lightcycle-run",
          f"{B}/parks/attractions?q=&park=&type=Attraction&interest=Big+Drops&age=&height=&sort=name"],
 "answer": ("160 attractions in total. The 38-inch height filter leaves 22; 44 inches "
            "leaves 8; 48 inches leaves 5. Sorted by height requirement the first result "
            "is Downhill Double Dipper at Disney's Blizzard Beach Water Park, and the "
            "last result on the first page is TRON Lightcycle / Run at Magic Kingdom "
            "Park. Clearing the height filter shows 160 attractions again. Keeping only "
            "Big Drops leaves 8 big-drop attractions."),
 "sql": None,
},

"9": {
 "urls": [f"{B}/", f"{B}/parks", f"{B}/parks/attractions?q=&park=magic-kingdom&type=&interest=Thrill+Rides&age=&height=&sort=name",
          f"{B}/parks/attractions/magic-kingdom/seven-dwarfs-mine-train",
          f"{B}/parks/attractions?q=&park=magic-kingdom&type=&interest=Dark&age=&height=&sort=name",
          f"{B}/parks/attractions/magic-kingdom/pirates-of-the-caribbean",
          f"{B}/parks/attractions/magic-kingdom/pirates-adventures",
          f"{B}/parks/attractions?q=&park=epcot&type=&interest=Slow+Rides&age=&height=&sort=name",
          f"{B}/parks/attractions/epcot/soarin-around-world",
          f"{B}/login", f"{B}/parks",
          f"{B}/parks/attractions?q=&park=epcot&type=&interest=Slow+Rides&age=&height=&sort=name",
          f"{B}/parks/attractions/epcot/soarin-around-world", f"{B}/favorites"],
 "answer": ("Magic Kingdom plus Thrill Rides leaves 5. Seven Dwarfs Mine Train has a "
            "height requirement of 38\" or taller and its first description section is "
            "headed Heigh-Ho, It's Off You Go!. Magic Kingdom Dark leaves 4 results. "
            "Pirates of the Caribbean is at Magic Kingdom Park; its Related Activity A "
            "Pirate's Adventure ~ Treasures of the Seven Seas is also at Magic Kingdom "
            "Park. EPCOT plus Slow Rides leaves 9. Soarin' Around the World is at EPCOT. "
            "After logging in as Dana and adding it, Dana has 4 favorites in total."),
 "sql": ("INSERT INTO favorites (user_id, item_type, item_key, added_at) "
         "VALUES (4, 'attraction', 'epcot/soarin-around-world', '2026-09-30');"),
},

"10": {
 "urls": [f"{B}/", f"{B}/shop", f"{B}/shop/toys?q=&category=&character=&target_age=&sort=price_high",
          f"{B}/shop/products/416120689757", f"{B}/bag", f"{B}/checkout", f"{B}/order/DSA8C3155",
          f"{B}/shop/toys?q=&category=Action+Figures&character=&target_age=&sort=featured"],
 "answer": ("The Toys collection lists 48 products. The most expensive product is the "
            "Disney Princess Classic Doll Collection Gift Set at $149.99 with a 1.0 "
            "rating. Adding 2 to the bag gives a line total of $299.98 and a bag total of "
            "$299.98; changing the quantity to 1 gives a new line total of $149.99 and a "
            "bag total of $149.99. The guest order for toy.buyer@example.com totalled "
            "$149.99 with confirmation code DSA8C3155. Keeping only Action Figures in the "
            "Toys collection leaves 15 products."),
 "sql": ("INSERT INTO shop_orders (confirmation, email, name, items_json, total, placed_at) "
         "VALUES ('DSA8C3155', 'toy.buyer@example.com', 'Toy Buyer', "
         "'[{\"pid\": \"416120689757\", \"name\": \"doll set\", \"qty\": 1, \"line\": 149.99}]', "
         "149.99, '2026-09-29');"),
},

"11": {
 "urls": [f"{B}/", f"{B}/shop/sale?q=&category=&character=Mickey+Mouse&target_age=&sort=rating",
          f"{B}/shop/products/415130694607", f"{B}/bag", f"{B}/shop/sale?q=&category=&character=&target_age=&sort=price_low",
          f"{B}/shop/accessories?q=&category=Bags+%26+Wallets&character=&target_age=&sort=featured",
          f"{B}/shop/products/442111075919", f"{B}/bag",
          f"{B}/shop/accessories?q=&category=Keychains+%26+Bag+Charms&character=&target_age=&sort=featured"],
 "answer": ("6 products are on sale. Keeping only Mickey Mouse character items leaves 3. "
            "Sorted by rating the top-rated one is the Mickey Mouse Halloween 2026 Plush "
            "at $29.99 with a 5.0 rating; the bag total is $29.99. Back on the full Sale "
            "list sorted by price low to high, the cheapest item is the Mickey Mouse "
            "Jack-o'-Lantern Treat Bucket at $24.99. Accessories filtered to Bags & "
            "Wallets leaves 17 products; the first result is the Mickey Mouse Tote by "
            "Harveys at $198.00 with 7 reviews. The new bag total is $227.99. "
            "Keychains & Bag Charms: 15 products."),
 "sql": ("INSERT INTO cart_items (cart_key, product_pid, qty) VALUES "
         "('c-audit11', '415130694607', 1), ('c-audit11', '442111075919', 1);"),
},

"12": {
 "urls": [f"{B}/", f"{B}/shop/clothing?q=&category=&character=&target_age=Adults&sort=featured",
          f"{B}/shop/clothing?q=&category=T-Shirts&character=&target_age=Adults&sort=featured",
          f"{B}/shop/clothing?q=&category=T-Shirts&character=&target_age=Adults&sort=price_low",
          f"{B}/shop/products/5106057431232m", f"{B}/bag", f"{B}/shop/toys",
          f"{B}/shop/toys?q=&category=Plush&character=&target_age=&sort=featured",
          f"{B}/shop/toys?q=&category=Plush&character=&target_age=&sort=price_low",
          f"{B}/shop/products/463521109001", f"{B}/bag"],
 "answer": ("25 clothing products are for Adults; narrowing to T-Shirts leaves 3. "
            "Sorted by price low to high the first result is the Mickey and Minnie Mouse "
            "Cutie Ghost T-Shirt for Women at $36.99 with a 3.5 rating; one bullet from "
            "its bare necessities is 60% cotton / 40% polyester. Setting the quantity to "
            "3 and adding it to the bag. The Toys collection lists 48 products. Keeping "
            "only Plush leaves 13; the cheapest plush is the Mickey Mouse Mini Plush "
            "Magnet at $16.99. Adding 1 gives a combined bag total of $127.96."),
 "sql": ("INSERT INTO cart_items (cart_key, product_pid, qty) VALUES "
         "('c-audit12', '5106057431232m', 3), ('c-audit12', '463521109001', 1);"),
},

"13": {
 "urls": [f"{B}/search?q=plush", f"{B}/shop/products/194735352982",
          f"{B}/search?q=tote", f"{B}/shop/products/442030853759",
          f"{B}/bag", f"{B}/checkout", f"{B}/order/DS1092C71"],
 "answer": ("The site search for 'plush' shows 25 products in the Shop section. The "
            "first product is Blaze Manoukian's Pet Pig Plush with Sound by Mattel at "
            "$32.99. Adding 1 to the bag. "
            "Searching for 'tote', the first product is the Disneyland Canvas Tote; "
            "adding 2 gives a bag total of $122.97. Setting the plush quantity to 0 "
            "leaves a bag total of $89.98 with 1 item remaining. Checking out as "
            "shop.compare@example.com gave confirmation code DS1092C71 and an order "
            "total of $89.98."),
 "sql": ("INSERT INTO shop_orders (confirmation, email, name, items_json, total, placed_at) "
         "VALUES ('DS1092C71', 'shop.compare@example.com', 'Shop Compare', "
         "'[{\"pid\": \"442030853759\", \"name\": \"Disneyland Canvas Tote\", \"qty\": 2, \"line\": 89.98}]', "
         "89.98, '2026-09-29');"),
},

"14": {
 "urls": [f"{B}/", f"{B}/live-shows", f"{B}/live-shows/disney-on-ice?q=&show=Magic+in+the+Stars&sort=date",
          f"{B}/live-shows/disney-on-ice?q=CA&show=&sort=date",
          f"{B}/live-shows/disney-on-ice?q=&show=&sort=city",
          f"{B}/live-shows/disney-on-ice/121030",
          f"{B}/live-shows/disney-on-ice/121030/book?day=Jan+21%2C+2027&time=7%3A00+pm",
          f"{B}/tickets/TK4BCB6AE"],
 "answer": ("15 Magic in the Stars events remain. Searching the schedule for 'CA' shows 8 "
            "California stops. Sorted by city the first event is Albany, NY at the MVP "
            "Arena, listing 4 performances. Booked 2 tickets for its first performance "
            "(Jan 21, 2027, 7:00 pm) with ice.first@example.com: confirmation code "
            "TK4BCB6AE, total $70.00."),
 "sql": ("INSERT INTO ticket_orders (confirmation, email, name, event_id, show_title, "
         "city, venue, day, time, qty, unit_price, total, placed_at) VALUES "
         "('TK4BCB6AE', 'ice.first@example.com', 'Ice First', '121030', 'Find Your Hero', "
         "'Albany, NY', 'MVP Arena', 'Jan 21, 2027', '7:00 pm', 2, 35.0, 70.0, '2026-09-29');"),
},

"15": {
 "urls": [f"{B}/", f"{B}/live-shows", f"{B}/live-shows/disney-on-ice?q=Kent&show=&sort=date",
          f"{B}/live-shows/disney-on-ice/120960",
          f"{B}/live-shows/disney-on-ice/120960/book?day=Oct+24%2C+2026&time=11%3A00+am",
          f"{B}/tickets/TKABA073A", f"{B}/live-shows",
          f"{B}/live-shows/disney-on-ice?q=&show=Jump+In%21&sort=city"],
 "answer": ("The Kent, WA event is at the accesso ShoWare Center, Oct 22-25, 2026. Booked "
            "3 tickets for its Saturday 11:00 am performance (Oct 24, 2026) with "
            "skate.fan@example.com: confirmation code TKABA073A, total $105.00. The Jump "
            "In! tour has 16 stops; sorted by city the first event is Anaheim, CA at the "
            "Honda Center."),
 "sql": ("INSERT INTO ticket_orders (confirmation, email, name, event_id, show_title, "
         "city, venue, day, time, qty, unit_price, total, placed_at) VALUES "
         "('TKABA073A', 'skate.fan@example.com', 'Skate Fan', '120960', 'Jump In!', "
         "'Kent, WA', 'accesso ShoWare Center', 'Oct 24, 2026', '11:00 am', 3, 35.0, 105.0, '2026-09-29');"),
},

"16": {
 "urls": [f"{B}/live-shows", f"{B}/live-shows/disney-on-ice?q=&show=&sort=date",
          f"{B}/live-shows/disney-on-ice?q=&show=Find+Your+Hero&sort=date",
          f"{B}/live-shows/disney-on-ice?q=TX&show=&sort=city",
          f"{B}/live-shows/disney-on-ice/120991",
          f"{B}/live-shows/disney-on-ice/120991/book?day=Nov+22%2C+2026&time=1%3A00+pm",
          f"{B}/tickets/TKFA346BE",
          f"{B}/live-shows/disney-on-ice?q=&show=Magic+of+Family&sort=city"],
 "answer": ("3 Broadway musicals are listed. The Disney On Ice schedule has 89 events "
            "in total. Keeping only Find Your Hero shows leaves 18. Searching for 'TX' "
            "shows 5 Texas stops; sorted by city the last one is Laredo. The Laredo "
            "event is at Sames Auto Arena, Nov 20-22, 2026. Booked 2 tickets for its "
            "Nov 22, 2026 5:00 pm performance with laredo.ice@example.com: "
            "confirmation code TKFA346BE, total $70.00. Back on the schedule, Magic of "
            "Family has 19 stops."),
 "sql": ("INSERT INTO ticket_orders (confirmation, email, name, event_id, show_title, "
         "city, venue, day, time, qty, unit_price, total, placed_at) VALUES "
         "('TKFA346BE', 'laredo.ice@example.com', 'Laredo Ice', '120991', 'Magic in the Stars', "
         "'Laredo, TX', 'Sames Auto Arena', 'Nov 22, 2026', '5:00 pm', 2, 35.0, 70.0, '2026-09-30');"),
},

"17": {
 "urls": [f"{B}/", f"{B}/login", f"{B}/signup", f"{B}/", f"{B}/games",
          f"{B}/games?q=disney", f"{B}/games/disney-illusion-island",
          f"{B}/games", f"{B}/games/disney-villains-cursed-cafe",
          f"{B}/login", f"{B}/favorites"],
 "answer": ("4 games are listed; searching games for 'disney' matches 3. Disney "
            "Illusion Island's description first sentence is: Join Mickey & Friends on "
            "a quest to explore the mysterious island of Monoth and recover three "
            "mystical books to save the world from disaster! Added it to favorites, "
            "then added Disney Villains Cursed Café too. After logging out and logging "
            "back in, the favorites page shows 2 favorites: Disney Illusion Island and "
            "Disney Villains Cursed Café."),
 "sql": ("INSERT INTO users (email, name, password_hash, joined) VALUES "
         "('game.player@test.com', 'Game Player', 'x', '2026-09-29'); "
         "INSERT INTO favorites (user_id, item_type, item_key, added_at) "
         "SELECT id, 'game', 'disney-illusion-island', '2026-09-29' FROM users WHERE email='game.player@test.com'; "
         "INSERT INTO favorites (user_id, item_type, item_key, added_at) "
         "SELECT id, 'game', 'disney-villains-cursed-cafe', '2026-09-29' FROM users WHERE email='game.player@test.com';"),
},

"18": {
 "urls": [f"{B}/search?q=frozen", f"{B}/parks/attractions/epcot/frozen-ever-after",
          f"{B}/search?q=frozen", f"{B}/movies/frozen-3",
          f"{B}/login", f"{B}/search?q=frozen", f"{B}/movies/frozen-3",
          f"{B}/favorites", f"{B}/search?q=stitch",
          f"{B}/shop/products/415161238870", f"{B}/bag"],
 "answer": ("The 'frozen' search shows 1 movie and 3 parks & entertainment results. "
            "Frozen Ever After is at EPCOT with an Any height requirement. The top movie "
            "result is Frozen 3, rated Not Yet Rated with release date November 24, 2027. "
            "After logging in as Dana and adding it, Dana has 4 favorites in total. "
            "Searching for 'stitch' shows 5 products; the first is the Stitch Knit Plush "
            "at $24.99, and adding 1 gives a bag total of $24.99."),
 "sql": ("INSERT INTO favorites (user_id, item_type, item_key, added_at) "
         "VALUES (4, 'movie', 'frozen-3', '2026-09-29'); "
         "INSERT INTO cart_items (cart_key, product_pid, qty) VALUES ('u4', '415161238870', 1);"),
},

"19": {
 "urls": [f"{B}/", f"{B}/parks",
          f"{B}/parks/attractions?q=&park=epcot&type=Attraction&interest=&age=&height=&sort=name",
          f"{B}/parks/attractions/epcot/mission-space-advanced-training-lab",
          f"{B}/parks/attractions?q=&park=epcot&type=Entertainment&interest=Character+Experiences&age=&height=&sort=name",
          f"{B}/parks/attractions/epcot/visa-card-character-experience",
          f"{B}/login", f"{B}/parks",
          f"{B}/parks/attractions?q=&park=epcot&type=Entertainment&interest=Character+Experiences&age=&height=&sort=name",
          f"{B}/parks/attractions/epcot/visa-card-character-experience", f"{B}/favorites"],
 "answer": ("10 parks are listed; EPCOT has the most attractions & entertainment with "
            "72. EPCOT's attractions list keeps 41 attractions. Sorted by name the first "
            "is Advanced Training Lab with an Any height requirement. Keeping only "
            "Entertainment with the Character Experiences interest for EPCOT leaves 15; "
            "the first result is the Disney® Visa® Cardmember Photo Opportunity at EPCOT. "
            "After logging in as Carol and adding it, Carol has 3 favorites in total."),
 "sql": ("INSERT INTO favorites (user_id, item_type, item_key, added_at) "
         "VALUES (3, 'attraction', 'epcot/visa-card-character-experience', '2026-09-30');"),
},
}
