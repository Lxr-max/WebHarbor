"""Frozen honest fixtures for the trip_com verifier tests.

Extracted from the reviewer's independent live walks: per task the honest
navigation skeleton (action, path), the final answer, and the exact SQLite
delta the walk left on the byte-reproducible seed. No LLM.

r2 re-freeze (2026-09-28): the skeletons, answers and stateful deltas were
re-extracted from the r2 reviewer's honest walks of the FIXED site
(contribution a375a671, container wh-trip-com-rereview). The deepened tasks'
skeletons cover the new legs (city-pass census, guide reads, repeat-stay and
comparison forms, wishlist/coupon audits); T17's booking now records the
submitted 12 October date and T18's records 3 guests on 12 October for
$48.27 (the form fix 1e2ca971 reads request.form first). T2's skeleton keeps
the classic compliant path (the Select link now carries the outbound filters,
so the return page arrives pre-filtered — the re-filter steps are no longer
required, and the naive non-Delta return is still rejected).
"""
BASE = "http://localhost:40111"

SPECS = {
    0: dict(
        steps=[
            ('navigate', '/'),
            ('click', '/deals/'),
            ('click', '/hotels/'),
            ('fill', '/hotels/'),
            ('click', '/hotels/list?city=Las%20Vegas&checkin=2026-10-04&checkout=2026-10-05&adults=2'),
            ('fill', '/hotels/list?city=Las%20Vegas&checkin=2026-10-04&checkout=2026-10-05&adults=2'),
            ('fill', '/hotels/list?city=Las%20Vegas&checkin=2026-10-04&checkout=2026-10-05&adults=2'),
            ('check', '/hotels/list?city=Las%20Vegas&checkin=2026-10-04&checkout=2026-10-05&adults=2'),
            ('check', '/hotels/list?city=Las%20Vegas&checkin=2026-10-04&checkout=2026-10-05&adults=2&maxprice=250&star=5&pool=1'),
            ('click', '/hotels/list?city=Las%20Vegas&checkin=2026-10-04&checkout=2026-10-05&adults=2&maxprice=250&star=5&pool=1'),
            ('click', '/hotels/detail/737533?checkin=2026-10-04&checkout=2026-10-05&adults=2'),
            ('click', '/hotels/book/54?checkin=2026-10-04&checkout=2026-10-05&adults=2'),
            ('fill', '/hotels/book/54?checkin=2026-10-04&checkout=2026-10-05&adults=2'),
            ('fill', '/hotels/book/54?checkin=2026-10-04&checkout=2026-10-05&adults=2'),
            ('fill', '/hotels/book/54?checkin=2026-10-04&checkout=2026-10-05&adults=2'),
            ('fill', '/hotels/book/54?checkin=2026-10-04&checkout=2026-10-05&adults=2'),
            ('fill', '/hotels/book/54?checkin=2026-10-04&checkout=2026-10-05&adults=2'),
            ('fill', '/hotels/book/54?checkin=2026-10-04&checkout=2026-10-05&adults=2'),
            ('click', '/hotels/confirmation/THXTEVU2RJ'),
        ],
        answer=(
            "I booked the Trump International Hotel Las Vegas (5-star, $238/night, outdoor "
            "pool) for Sunday 4 to Monday 5 October. Using the new-user hotel promo code "
            "TRIPNEW20 from the deals page, I reserved its cheapest king-bed room, the "
            "Superior King Room. Booking reference THXTEVU2RJ. Total charged: $216.00."),
        sql=["INSERT INTO hotel_bookings (ref,hotel_id,room_id,user_id,guest_first,guest_last,"
             "email,phone,checkin,checkout,rooms,adults,children,nightly,taxes,total,coins,"
             "promo_code,status,created_at) VALUES ('THXTEVU2RJ',737533,54,NULL,'Jordan',"
             "'Blake','jordan.blake@example.com','+1 555 017 2222','2026-10-04','2026-10-05',"
             "1,2,0,238.0,32.0,216.0,2,'TRIPNEW20','confirmed','2026-09-27')"],
    ),
    1: dict(
        steps=[
            ('navigate', '/'),
            ('click', '/hotels/'),
            ('fill', '/hotels/'),
            ('fill', '/hotels/'),
            ('fill', '/hotels/'),
            ('click', '/hotels/list?city=Las%20Vegas&checkin=2026-10-11&checkout=2026-10-12&adults=2'),
            ('fill', '/hotels/list?city=Las%20Vegas&checkin=2026-10-11&checkout=2026-10-12&adults=2'),
            ('check', '/hotels/list?city=Las%20Vegas&checkin=2026-10-11&checkout=2026-10-12&adults=2&maxprice=150&freecancel=1'),
            ('click', '/hotels/list?city=Las%20Vegas&checkin=2026-10-11&checkout=2026-10-12&adults=2&maxprice=150&freecancel=1'),
            ('click', '/hotels/detail/733224?checkin=2026-10-11&checkout=2026-10-12&adults=2'),
            ('click', '/hotels/book/38?checkin=2026-10-11&checkout=2026-10-12&adults=2'),
            ('fill', '/hotels/book/38?checkin=2026-10-11&checkout=2026-10-12&adults=2'),
            ('fill', '/hotels/book/38?checkin=2026-10-11&checkout=2026-10-12&adults=2'),
            ('fill', '/hotels/book/38?checkin=2026-10-11&checkout=2026-10-12&adults=2'),
            ('fill', '/hotels/book/38?checkin=2026-10-11&checkout=2026-10-12&adults=2'),
            ('fill', '/hotels/book/38?checkin=2026-10-11&checkout=2026-10-12&adults=2'),
            ('click', '/hotels/confirmation/THRBRYG4LZ'),
        ],
        answer=(
            "The two best-rated Las Vegas hotels under $150 a night with free cancellation "
            "were Four Queens Hotel and Casino (8.7, $104) and Planet Hollywood Resort & "
            "Casino (8.5, $72). I booked the cheaper one, Planet Hollywood Resort & Casino, "
            "in its lowest-priced room (Room Type Assigned On Arrival) for 11-12 October. "
            "Guest score 8.5. Total paid: $82.00 (booking THRBRYG4LZ)."),
        sql=["INSERT INTO hotel_bookings (ref,hotel_id,room_id,user_id,guest_first,guest_last,"
             "email,phone,checkin,checkout,rooms,adults,children,nightly,taxes,total,coins,"
             "promo_code,status,created_at) VALUES ('THRBRYG4LZ',733224,38,NULL,'Dana',"
             "'Reyes','dana.reyes@example.com','+1 555 013 3444','2026-10-11','2026-10-12',"
             "1,2,0,72.0,10.0,82.0,0,'','confirmed','2026-09-27')"],
    ),
    2: dict(
        steps=[
            ('navigate', '/'),
            ('click', '/flights/'),
            ('fill', '/flights/'),
            ('fill', '/flights/'),
            ('fill', '/flights/'),
            ('fill', '/flights/'),
            ('click', '/flights/list?triptype=rt&dcity=SFO&acity=JFK&ddate=2026-10-20&rdate=2026-10-27&cabin=Economy'),
            ('check', '/flights/list?triptype=rt&dcity=SFO&acity=JFK&ddate=2026-10-20&rdate=2026-10-27&cabin=Economy'),
            ('check', '/flights/list?triptype=rt&dcity=SFO&acity=JFK&ddate=2026-10-20&rdate=2026-10-27&cabin=Economy&airline=Delta%20Air%20Lines&stops=nonstop'),
            ('click', '/flights/list?triptype=rt&dcity=SFO&acity=JFK&ddate=2026-10-20&rdate=2026-10-27&cabin=Economy&airline=Delta%20Air%20Lines&stops=nonstop&sort=price'),
            ('click', '/flights/select/5?ddate=2026-10-20&rdate=2026-10-27&cabin=Economy'),
            ('check', '/flights/select/5?ddate=2026-10-20&rdate=2026-10-27&cabin=Economy&airline=Delta%20Air%20Lines&stops=nonstop'),
            ('check', '/flights/select/5?ddate=2026-10-20&rdate=2026-10-27&cabin=Economy&airline=Delta%20Air%20Lines&stops=nonstop'),
            ('click', '/flights/select/5?ddate=2026-10-20&rdate=2026-10-27&cabin=Economy&airline=Delta%20Air%20Lines&stops=nonstop'),
            ('click', '/flights/book?out=5&ret=149&cabin=Economy'),
            ('fill', '/flights/book?out=5&ret=149&cabin=Economy'),
            ('fill', '/flights/book?out=5&ret=149&cabin=Economy'),
            ('fill', '/flights/book?out=5&ret=149&cabin=Economy'),
            ('fill', '/flights/book?out=5&ret=149&cabin=Economy'),
            ('fill', '/flights/book?out=5&ret=149&cabin=Economy'),
            ('click', '/flights/confirmation/TF7EEAMUDW'),
        ],
        answer=(
            "I booked the cheapest Delta nonstop round trip from San Francisco to New York, "
            "leaving Tuesday 20 October and returning Tuesday 27 October, economy, one adult "
            "(Maria Santos). Outbound Delta departure 07:00; return Delta departure 07:00. "
            "Total paid $441.00. Booking reference TF7EEAMUDW."),
        sql=["INSERT INTO flight_bookings (ref,outbound_id,return_id,user_id,passenger_first,"
             "passenger_last,email,phone,cabin,trip_type,total,promo_code,status,created_at) "
             "VALUES ('TF7EEAMUDW',5,149,NULL,'Maria','Santos','maria.santos@example.com',"
             "'+1 555 014 4555','Economy','rt',441.0,'','confirmed','2026-09-27')"],
    ),
    3: dict(
        steps=[
            ('navigate', '/'),
            ('click', '/deals/'),
            ('click', '/flights/'),
            ('fill', '/flights/'),
            ('fill', '/flights/'),
            ('fill', '/flights/'),
            ('fill', '/flights/'),
            ('click', '/flights/list?triptype=rt&dcity=SFO&acity=LAS&ddate=2026-10-20&rdate=2026-10-27&cabin=Economy'),
            ('check', '/flights/list?triptype=rt&dcity=SFO&acity=LAS&ddate=2026-10-20&rdate=2026-10-27&cabin=Economy&stops=nonstop'),
            ('click', '/flights/list?triptype=rt&dcity=SFO&acity=LAS&ddate=2026-10-20&rdate=2026-10-27&cabin=Economy&stops=nonstop&sort=price'),
            ('click', '/flights/select/859?ddate=2026-10-20&rdate=2026-10-27&cabin=Economy&stops=nonstop'),
            ('click', '/flights/book?out=859&ret=891&cabin=Economy'),
            ('fill', '/flights/book?out=859&ret=891&cabin=Economy'),
            ('fill', '/flights/book?out=859&ret=891&cabin=Economy'),
            ('fill', '/flights/book?out=859&ret=891&cabin=Economy'),
            ('fill', '/flights/book?out=859&ret=891&cabin=Economy'),
            ('fill', '/flights/book?out=859&ret=891&cabin=Economy'),
            ('click', '/flights/confirmation/TFDUPSCT2U'),
        ],
        answer=(
            "Comparing the six cheap flight deals on the deals page, the cheapest route was "
            "San Francisco (SFO) to Las Vegas (LAS), from $34. I booked the cheapest nonstop "
            "round trip departing 20 October and returning 27 October: Frontier Airlines "
            "outbound and Southwest Airlines return. Total $114.00. Booking reference "
            "TFDUPSCT2U."),
        sql=["INSERT INTO flight_bookings (ref,outbound_id,return_id,user_id,passenger_first,"
             "passenger_last,email,phone,cabin,trip_type,total,promo_code,status,created_at) "
             "VALUES ('TFDUPSCT2U',859,891,NULL,'Alex','Moore','alex.moore@example.com',"
             "'+1 555 016 6677','Economy','rt',114.0,'','confirmed','2026-09-27')"],
    ),
    4: dict(
        steps=[
            ('navigate', '/'),
            ('click', '/flights/'),
            ('select', '/flights/'),
            ('fill', '/flights/'),
            ('fill', '/flights/'),
            ('fill', '/flights/'),
            ('click', '/flights/list?triptype=ow&dcity=ORD&acity=MIA&ddate=2026-10-22&cabin=Economy'),
            ('check', '/flights/list?triptype=ow&dcity=ORD&acity=MIA&ddate=2026-10-22&cabin=Economy&stops=nonstop&dep=morning'),
            ('click', '/flights/list?triptype=ow&dcity=ORD&acity=MIA&ddate=2026-10-22&cabin=Economy&stops=nonstop&dep=morning'),
            ('click', '/flights/book?out=624&cabin=Economy'),
            ('fill', '/flights/book?out=624&cabin=Economy'),
            ('fill', '/flights/book?out=624&cabin=Economy'),
            ('fill', '/flights/book?out=624&cabin=Economy'),
            ('fill', '/flights/book?out=624&cabin=Economy'),
            ('fill', '/flights/book?out=624&cabin=Economy'),
            ('click', '/flights/confirmation/TF9ZGL2RP7'),
        ],
        answer=(
            "The cheapest nonstop flight from Chicago (ORD) to Miami (MIA) on Thursday 22 "
            "October departing before noon was American Airlines departing 08:43 (arriving "
            "12:55). Price: $169 one-way economy. Booked for Sam Patel, booking reference "
            "TF9ZGL2RP7."),
        sql=["INSERT INTO flight_bookings (ref,outbound_id,return_id,user_id,passenger_first,"
             "passenger_last,email,phone,cabin,trip_type,total,promo_code,status,created_at) "
             "VALUES ('TF9ZGL2RP7',624,NULL,NULL,'Sam','Patel','sam.patel@example.com',"
             "'+1 555 018 8888','Economy','ow',169.0,'','confirmed','2026-09-27')"],
    ),
    5: dict(
        steps=[
            ('navigate', '/'),
            ('click', '/things-to-do/'),
            ('click', '/things-to-do/experiences/orlando'),
            ('check', '/things-to-do/experiences/orlando?category=City+passes'),
            ('click', '/things-to-do/experiences/orlando?category=City+passes'),
            ('check', '/things-to-do/experiences/orlando?category='),
            ('click', '/things-to-do/experiences/orlando?category='),
            ('click', '/things-to-do/experiences/orlando?category=&sort=rating'),
            ('check', '/things-to-do/experiences/orlando?category=City+passes'),
            ('click', '/things-to-do/experiences/orlando?category=City+passes'),
            ('click', '/things-to-do/detail/46680654'),
            ('click', '/things-to-do/book/1?date=2026-10-06&guests=2'),
            ('fill', '/things-to-do/book/1?date=2026-10-06&guests=2'),
            ('fill', '/things-to-do/book/1?date=2026-10-06&guests=2'),
            ('fill', '/things-to-do/book/1?date=2026-10-06&guests=2'),
            ('click', '/things-to-do/confirmation/TA9LBLDV8B'),
        ],
        answer=(
            "Orlando lists 3 city passes in the City passes category; the cheapest is the "
            "Orlando: Go City Explorer Pass - Choose 2 to 5 Attractions at $60.84. The "
            "best-rated pass under $70 is the Go City: Orlando Explorer Pass (rating 4.0, "
            "1 review, 12 booked). Highlights: Save up to 50% vs buying individual tickets, "
            "and go at your own pace with 30 days validity from your first attraction "
            "visit. The package is valid for 90 days from the booking date. Booked for two "
            "guests on 6 October (lead traveller Pat Kim). Total paid $128.00, booking "
            "reference TA9LBLDV8B. The highest-rated Orlando experience of any kind is the "
            "St. Augustine guided day trip including a scenic boat cruise, rating 5.0."),
        sql=["INSERT INTO attraction_bookings (ref,attraction_id,package_id,user_id,visit_date,"
             "guests,lead_first,lead_last,email,total,status,created_at) VALUES "
             "('TA9LBLDV8B',46680654,1,NULL,'2026-10-06',2,'Pat','Kim',"
             "'pat.kim@example.com',128.0,'confirmed','2026-09-27')"],
    ),
    6: dict(
        steps=[
            ('navigate', '/'),
            ('click', '/sign-in/'),
            ('fill', '/sign-in/'),
            ('fill', '/sign-in/'),
            ('click', '/account/'),
            ('click', '/account/bookings'),
            ('click', '/hotels/detail/718690'),
            ('click', '/account/'),
            ('click', '/account/wishlist'),
            ('click', '/account/coupons'),
            ('click', '/flights/'),
            ('fill', '/flights/'),
            ('fill', '/flights/'),
            ('click', '/flights/list?triptype=rt&dcity=SFO&acity=JFK&ddate=2026-10-20&rdate=2026-10-27&cabin=Economy'),
            ('check', '/flights/list?triptype=rt&dcity=SFO&acity=JFK&ddate=2026-10-20&rdate=2026-10-27&cabin=Economy'),
            ('click', '/flights/list?triptype=rt&dcity=SFO&acity=JFK&ddate=2026-10-20&rdate=2026-10-27&cabin=Economy&stops=nonstop'),
            ('click', '/flights/select/3?ddate=2026-10-20&rdate=2026-10-27&cabin=Economy&adults=1&stops=nonstop'),
            ('click', '/account/'),
            ('click', '/account/bookings'),
            ('click', '/account/bookings'),
        ],
        answer=(
            "Signed in as Alice Johnson. Trip Coins balance: 480 coins. The hotel stay is at "
            "Harrah's Las Vegas (check-in from 16:00), booking THALICE1, $128.00; the flight "
            "is San Francisco (SFO) to New York (JFK), booking TFALICE1, $422.00, with a "
            "22:15 outbound and an 11:35 return departure. My wishlist holds 3 hotels and "
            "the priciest is the Infinity Hotel San Francisco at $327 a night. The flights "
            "promo code FLYTRIP10 has a minimum spend of $150. A nonstop round trip on the "
            "flight's route currently costs $205 outbound plus $228 return, $433 in total. "
            "The more expensive booking was the flight ($422 vs $128), so I cancelled booking "
            "TFALICE1. Afterwards the hotel booking THALICE1 shows confirmed and the flight "
            "TFALICE1 shows cancelled."),
        sql=["UPDATE flight_bookings SET status='cancelled' WHERE ref='TFALICE1'"],
    ),
    7: dict(
        steps=[
            ('navigate', '/'),
            ('click', '/sign-in/'),
            ('fill', '/sign-in/'),
            ('fill', '/sign-in/'),
            ('click', '/account/'),
            ('click', '/account/wishlist'),
            ('click', '/hotels/'),
            ('fill', '/hotels/'),
            ('fill', '/hotels/'),
            ('fill', '/hotels/'),
            ('click', '/hotels/list?city=San%20Francisco&checkin=2026-10-04&checkout=2026-10-05&adults=2'),
            ('fill', '/hotels/list?city=San%20Francisco&checkin=2026-10-04&checkout=2026-10-05&adults=2'),
            ('click', '/hotels/list?city=San%20Francisco&checkin=2026-10-04&checkout=2026-10-05&adults=2&maxprice=200&sort=rating'),
            ('click', '/hotels/detail/715700?checkin=2026-10-04&checkout=2026-10-05&adults=2'),
            ('click', '/wishlist/toggle/715700'),
            ('navigate', '/account/wishlist'),
            ('click', '/wishlist/toggle/714958'),
            ('navigate', '/account/wishlist'),
        ],
        answer=(
            "I saved the best-rated San Francisco hotel under $200 a night, Hotel Fiona - No "
            "Resort Fee ($187), to the wishlist and removed the more expensive of the two "
            "saved Las Vegas hotels ($57 vs $56). The hotels that remain on the wishlist "
            "are: Hotel 32One at $212 a night, Hotel Fiona - No Resort Fee at $187 a night, "
            "and Horseshoe Las Vegas at $56 a night."),
        sql=["DELETE FROM wishlist_items WHERE user_id=2 AND hotel_id=714958",
             "INSERT INTO wishlist_items (user_id,hotel_id) VALUES (2,715700)"],
    ),
    8: dict(
        steps=[
            ('navigate', '/'),
            ('click', '/deals/'),
            ('click', '/hotels/'),
            ('fill', '/hotels/'),
            ('fill', '/hotels/'),
            ('fill', '/hotels/'),
            ('click', '/hotels/list?city=Paris%20Las%20Vegas&checkin=2026-10-04&checkout=2026-10-05&adults=2'),
            ('click', '/hotels/detail/733090?checkin=2026-10-04&checkout=2026-10-05&adults=2'),
            ('click', '/hotels/book/22?checkin=2026-10-04&checkout=2026-10-05&adults=2'),
            ('fill', '/hotels/book/22?checkin=2026-10-04&checkout=2026-10-05&adults=2'),
            ('fill', '/hotels/book/22?checkin=2026-10-04&checkout=2026-10-05&adults=2'),
            ('fill', '/hotels/book/22?checkin=2026-10-04&checkout=2026-10-05&adults=2'),
            ('fill', '/hotels/book/22?checkin=2026-10-04&checkout=2026-10-05&adults=2'),
            ('fill', '/hotels/book/22?checkin=2026-10-04&checkout=2026-10-05&adults=2'),
            ('fill', '/hotels/book/22?checkin=2026-10-04&checkout=2026-10-05&adults=2'),
            ('click', '/hotels/confirmation/TH9XRLE4GD'),
        ],
        answer=(
            "The promo code that takes 20 percent off hotels is TRIPNEW20, with a minimum "
            "spend of $100. I booked the cheapest room at Paris Las Vegas for 4-5 October "
            "(Room Type Assigned On Arrival, $167 a night). Discount: $37.80. Final total: "
            "$151.20 (booking TH9XRLE4GD)."),
        sql=["INSERT INTO hotel_bookings (ref,hotel_id,room_id,user_id,guest_first,guest_last,"
             "email,phone,checkin,checkout,rooms,adults,children,nightly,taxes,total,coins,"
             "promo_code,status,created_at) VALUES ('TH9XRLE4GD',733090,22,NULL,'Robin',"
             "'Fox','robin.fox@example.com','+1 555 019 9900','2026-10-04','2026-10-05',"
             "1,2,0,167.0,22.0,151.2,1,'TRIPNEW20','confirmed','2026-09-27')"],
    ),
    9: dict(
        steps=[
            ('navigate', '/'),
            ('click', '/guide/'),
            ('click', '/guide/nyc-weekend-midrange'),
            ('click', '/hotels/'),
            ('fill', '/hotels/'),
            ('fill', '/hotels/'),
            ('fill', '/hotels/'),
            ('click', '/hotels/list?city=New+York&checkin=2026-10-20&checkout=2026-10-21&adults=2'),
            ('check', '/hotels/list?city=New+York&checkin=2026-10-20&checkout=2026-10-21&adults=2&parking=1'),
            ('click', '/hotels/list?city=New+York&checkin=2026-10-20&checkout=2026-10-21&adults=2&parking=1&sort=rating'),
            ('click', '/hotels/list?city=New+York&checkin=2026-10-20&checkout=2026-10-21&adults=2&parking=1&sort=rating'),
            ('click', '/hotels/detail/105237897?checkin=2026-10-20&checkout=2026-10-21&adults=2'),
            ('click', '/hotels/book/124?checkin=2026-10-20&checkout=2026-10-21&adults=2&children=0'),
            ('navigate', '/hotels/detail/105237897?checkin=2026-10-20&checkout=2026-10-21&adults=2'),
            ('navigate', '/hotels/list?city=New+York&checkin=2026-10-20&checkout=2026-10-21&adults=2&parking=1&sort=rating'),
            ('click', '/hotels/detail/2192841?checkin=2026-10-20&checkout=2026-10-21&adults=2'),
        ],
        answer=(
            "The New York weekend guide says Jersey City and Newark rates run 30-40% lower "
            "than Manhattan. Among New York hotels with more than 500 reviews and parking, "
            "ranked by guest score: Motto by Hilton New York City Times Square (score 8.7, "
            "714 reviews) and DoubleTree by Hilton New York Downtown (score 8.4, 1956 "
            "reviews). For the higher-scored one, the two review tags on its results card "
            "are 'American breakfast' and 'Great views'. Its cheapest room is the Flex Room "
            "With Wall Bed at $202 per night, 1 queen bed, breakfast not included, and free "
            "cancellation before 11:59 PM, Oct 1; the booking form shows taxes and fees of "
            "$34.00 per night. The other hotel's cheapest room is the King Room With City "
            "View at $175 a night."),
        sql=[],
    ),
    10: dict(
        steps=[
            ('navigate', '/'),
            ('click', '/guide/'),
            ('click', '/guide/orlando-theme-park-planning'),
            ('click', '/things-to-do/'),
            ('click', '/things-to-do/experiences/orlando'),
            ('check', '/things-to-do/experiences/orlando?category=City%20passes'),
            ('click', '/things-to-do/experiences/orlando?category=City%20passes'),
            ('click', '/things-to-do/experiences/orlando?category=City%20passes&sort=price'),
            ('click', '/things-to-do/detail/110625321'),
            ('click', '/things-to-do/book/2?date=2026-10-06&guests=2'),
            ('fill', '/things-to-do/book/2?date=2026-10-06&guests=2'),
            ('fill', '/things-to-do/book/2?date=2026-10-06&guests=2'),
            ('fill', '/things-to-do/book/2?date=2026-10-06&guests=2'),
            ('click', '/things-to-do/confirmation/TAV2UQQMWS'),
        ],
        answer=(
            "The Orlando theme-park planning guide says most travellers need 2 days per "
            "major park. The cheapest city pass is the Orlando: Go City Explorer Pass - "
            "Choose 2 to 5 Attractions ($60.84 per person). Booked for two people for 6 "
            "October (lead traveller Mel Wu). Total paid $121.68, booking reference "
            "TAV2UQQMWS."),
        sql=["INSERT INTO attraction_bookings (ref,attraction_id,package_id,user_id,visit_date,"
             "guests,lead_first,lead_last,email,total,status,created_at) VALUES "
             "('TAV2UQQMWS',110625321,2,NULL,'2026-10-06',2,'Mel','Wu',"
             "'mel.wu@example.com',121.68,'confirmed','2026-09-27')"],
    ),
    11: dict(
        steps=[
            ('navigate', '/'),
            ('click', '/sign-in/'),
            ('fill', '/sign-in/'),
            ('fill', '/sign-in/'),
            ('click', '/account/'),
            ('click', '/hotels/'),
            ('fill', '/hotels/'),
            ('fill', '/hotels/'),
            ('fill', '/hotels/'),
            ('click', '/hotels/list?city=Miami&checkin=2026-10-04&checkout=2026-10-05&adults=2'),
            ('click', '/hotels/list?city=Miami&checkin=2026-10-04&checkout=2026-10-05&adults=2&sort=price'),
            ('click', '/hotels/detail/4648397?checkin=2026-10-04&checkout=2026-10-05&adults=2'),
            ('navigate', '/hotels/list?city=Miami&checkin=2026-10-04&checkout=2026-10-05&adults=2&sort=price'),
            ('click', '/hotels/detail/68493916?checkin=2026-10-04&checkout=2026-10-05&adults=2'),
            ('click', '/account/'),
            ('click', '/account/wishlist'),
            ('click', '/account/coupons'),
        ],
        answer=(
            "Signed in as Carol Davis; Trip Coins balance 480. The two cheapest bookable "
            "Miami hotels are Hyatt Place Miami Airport East (guest score 8.3, $93 a "
            "night) and Kompose Boutique Hotel Miami Airport (guest score 8.3, $100 a "
            "night). The cheapest one's cheapest room is the King Room ($93 per night, $105 "
            "total including taxes for one night 4-5 October): 1 king bed and 1 sofa bed, "
            "and the stay would earn $1.05 in Trip Coins. The runner-up's cheapest room is "
            "the King Room-Accessible-Non-Smoking at $82 a night. My wishlist holds 3 "
            "hotels, and the coupon with the highest minimum spend is SAVE25 ($200). I did "
            "not book anything."),
        sql=[],
    ),
    12: dict(
        steps=[
            ('navigate', '/'),
            ('click', '/hotels/'),
            ('fill', '/hotels/'),
            ('fill', '/hotels/'),
            ('fill', '/hotels/'),
            ('click', '/hotels/list?city=Las%20Vegas&checkin=2026-10-04&checkout=2026-10-05&adults=2'),
            ('click', '/hotels/list?city=Las%20Vegas&checkin=2026-10-04&checkout=2026-10-05&adults=2&sort=price'),
            ('click', '/hotels/detail/718690?checkin=2026-10-04&checkout=2026-10-05&adults=2'),
            ('navigate', '/hotels/'),
            ('fill', '/hotels/'),
            ('fill', '/hotels/'),
            ('fill', '/hotels/'),
            ('click', '/hotels/list?city=New%20York&checkin=2026-10-04&checkout=2026-10-05&adults=2'),
            ('click', '/hotels/list?city=New%20York&checkin=2026-10-04&checkout=2026-10-05&adults=2&sort=price'),
            ('click', '/hotels/detail/2092657?checkin=2026-10-04&checkout=2026-10-05&adults=2'),
        ],
        answer=(
            "For 4-5 October: the cheapest Las Vegas hotel with available rooms is Harrah's "
            "Las Vegas ($56 a night, guest score 8.4) with 5 room choices; the cheapest New "
            "York hotel is HI New York City Hostel ($104 a night, guest score 9.0) with 2 "
            "room choices. The Las Vegas hotel is cheaper by $48."),
        sql=[],
    ),
    13: dict(
        steps=[
            ('navigate', '/'),
            ('click', '/hotels/'),
            ('fill', '/hotels/'),
            ('fill', '/hotels/'),
            ('fill', '/hotels/'),
            ('click', '/hotels/list?city=Las+Vegas&checkin=2026-10-13&checkout=2026-10-14&adults=2'),
            ('fill', '/hotels/list?city=Las+Vegas&checkin=2026-10-13&checkout=2026-10-14&adults=2'),
            ('click', '/hotels/list?city=Las+Vegas&checkin=2026-10-13&checkout=2026-10-14&adults=2&maxprice=120'),
            ('click', '/hotels/list?city=Las+Vegas&checkin=2026-10-13&checkout=2026-10-14&adults=2&maxprice=120&sort=rating'),
            ('click', '/hotels/detail/718623?checkin=2026-10-13&checkout=2026-10-14&adults=2'),
            ('click', '/hotels/book/30?checkin=2026-10-13&checkout=2026-10-14&adults=2&children=0'),
            ('navigate', '/hotels/detail/718623?checkin=2026-10-13&checkout=2026-10-14&adults=2'),
            ('navigate', '/hotels/list?city=Las+Vegas&checkin=2026-10-13&checkout=2026-10-14&adults=2&maxprice=120&sort=rating'),
            ('select', '/hotels/list?city=Las+Vegas&checkin=2026-10-13&checkout=2026-10-14&adults=2&maxprice=120&sort=rating'),
            ('click', '/hotels/list?city=Las+Vegas&checkin=2026-10-13&checkout=2026-10-14&adults=2&maxprice=120&district=Las+Vegas+Strip&sort=rating'),
            ('click', '/hotels/detail/733224?checkin=2026-10-13&checkout=2026-10-14&adults=2'),
        ],
        answer=(
            "Away from the Strip, the best-rated bookable Las Vegas hotel under $120 a night "
            "for 13-14 October is Four Queens Hotel and Casino, in the Downtown - Fremont "
            "Street area: guest score 8.7, 3-star, $104 a night. Its cheapest room (Run Of "
            "House Room) can be cancelled free before 11:59 PM, Oct 1, and its booking-form "
            "grand total for those nights is $73.00. The best-rated bookable Strip hotel "
            "under $120 is Planet Hollywood Resort & Casino: guest score 8.5, $72 a night, "
            "cheapest room Room Type Assigned On Arrival. I did not book anything."),
        sql=[],
    ),
    14: dict(
        steps=[
            ('navigate', '/'),
            ('click', '/deals/'),
            ('click', '/flights/'),
            ('fill', '/flights/'),
            ('fill', '/flights/'),
            ('fill', '/flights/'),
            ('fill', '/flights/'),
            ('click', '/flights/list?triptype=rt&dcity=Miami&acity=New%20York&ddate=2026-10-24&rdate=2026-10-31&cabin=Economy'),
            ('click', '/flights/list?triptype=rt&dcity=MIA&acity=LGA&ddate=2026-10-24&rdate=2026-10-31&cabin=Economy&sort=price'),
            ('click', '/flights/select/783?ddate=2026-10-24&rdate=2026-10-31&cabin=Economy'),
            ('click', '/flights/book?out=783&ret=852&cabin=Economy'),
            ('fill', '/flights/book?out=783&ret=852&cabin=Economy'),
            ('fill', '/flights/book?out=783&ret=852&cabin=Economy'),
            ('fill', '/flights/book?out=783&ret=852&cabin=Economy'),
            ('fill', '/flights/book?out=783&ret=852&cabin=Economy'),
            ('fill', '/flights/book?out=783&ret=852&cabin=Economy'),
            ('fill', '/flights/book?out=783&ret=852&cabin=Economy'),
            ('click', '/flights/confirmation/TF4JPJUT5U'),
        ],
        answer=(
            "I booked the cheapest round trip from Miami to New York, departing 24 October "
            "and returning 31 October, economy, one adult, using the flight promo code "
            "FLYTRIP10 from the deals page. Promo discount: $21.10. Total paid: $189.90. "
            "Booking reference TF4JPJUT5U."),
        sql=["INSERT INTO flight_bookings (ref,outbound_id,return_id,user_id,passenger_first,"
             "passenger_last,email,phone,cabin,trip_type,total,promo_code,status,created_at) "
             "VALUES ('TF4JPJUT5U',783,852,NULL,'Jamie','Lee','jamie.lee@example.com',"
             "'+1 555 015 5566','Economy','rt',189.9,'FLYTRIP10','confirmed','2026-09-27')"],
    ),
    15: dict(
        steps=[
            ('navigate', '/'),
            ('click', '/sign-in/'),
            ('fill', '/sign-in/'),
            ('fill', '/sign-in/'),
            ('click', '/account/'),
            ('click', '/account/bookings'),
            ('click', '/hotels/detail/718690'),
            ('fill', '/hotels/detail/718690'),
            ('fill', '/hotels/detail/718690'),
            ('click', '/hotels/detail/718690?checkin=2026-11-18&checkout=2026-11-20&adults=2'),
            ('click', '/hotels/book/1?checkin=2026-11-18&checkout=2026-11-20&adults=2&children=0'),
            ('navigate', '/hotels/detail/718690?checkin=2026-11-18&checkout=2026-11-20&adults=2'),
            ('fill', '/hotels/detail/718690?checkin=2026-11-18&checkout=2026-11-20&adults=2'),
            ('click', '/search?q=Go+City'),
            ('click', '/things-to-do/detail/110625321'),
            ('click', '/account/'),
            ('click', '/account/wishlist'),
            ('click', '/account/coupons'),
        ],
        answer=(
            "Signed in as David Kim. Trip Coins balance: 480. My bookings: (1) Hotel stay at "
            "Harrah's Las Vegas, Nov 1-3 2026, total $136.00, which earned 136 Trip Coins; "
            "(2) Attraction booking, Orlando: Go City Explorer Pass, Nov 2 2026, total "
            "$121.68. The hotel page shows Harrah's Las Vegas: guest score 8.4, 3-star "
            "rating, Las Vegas Strip area, check-in from 16:00; its cheapest room is Room "
            "Type Assigned On Arrival at $56, and that room's total for a repeat two-night "
            "stay 18-20 November is $128.00. The activity I booked, found via site search, "
            "lets its highlights Choose 2 to 5 Attractions. My wishlist holds 3 hotels, "
            "and the attractions promo code ACTIVITY15 has a minimum spend of $50."),
        sql=[],
    ),
    16: dict(
        steps=[
            ('navigate', '/'),
            ('fill', '/'),
            ('click', '/search?q=Paris+Las+Vegas'),
            ('click', '/hotels/detail/733090'),
            ('fill', '/hotels/detail/733090'),
            ('fill', '/hotels/detail/733090'),
            ('click', '/hotels/detail/733090?checkin=2026-10-05&checkout=2026-10-07&adults=2'),
            ('click', '/hotels/book/22?checkin=2026-10-05&checkout=2026-10-07&adults=2&children=0'),
            ('navigate', '/hotels/detail/733090?checkin=2026-10-05&checkout=2026-10-07&adults=2'),
            ('click', '/hotels/book/24?checkin=2026-10-05&checkout=2026-10-07&adults=2&children=0'),
            ('navigate', '/hotels/detail/733090?checkin=2026-10-05&checkout=2026-10-07&adults=2'),
            ('fill', '/hotels/detail/733090?checkin=2026-10-05&checkout=2026-10-07&adults=2'),
            ('fill', '/hotels/detail/733090?checkin=2026-10-05&checkout=2026-10-07&adults=2'),
            ('click', '/hotels/detail/733090?checkin=2026-10-05&checkout=2026-10-06&adults=2'),
            ('click', '/hotels/book/22?checkin=2026-10-05&checkout=2026-10-06&adults=2&children=0'),
            ('fill', '/hotels/book/22?checkin=2026-10-05&checkout=2026-10-06&adults=2&children=0'),
            ('click', '/search?q=Bellagio'),
        ],
        answer=(
            "A two-night stay at Paris Las Vegas starting 5 October in its cheapest room "
            "(Room Type Assigned On Arrival) costs $167 per night before tax, with $22 in "
            "taxes and fees per night, for a grand total of $378, confirmed on the booking "
            "form for 5-7 October. The room sleeps 2, has 1 king bed or 2 queen beds, and "
            "can be cancelled free before 11:59 PM, Oct 1. The second-cheapest room, the "
            "Bordeaux Room King, has a grand total of $388 for the same nights. The "
            "cheapest room's one-night total for 5-6 October is $189. The hotel's guest "
            "score is 8.6 with 805 reviews, and a site search shows the Bellagio at $467 a "
            "night."),
        sql=[],
    ),
    17: dict(
        steps=[
            ('navigate', '/'),
            ('click', '/things-to-do/'),
            ('click', '/things-to-do/experiences/hong_kong'),
            ('check', '/things-to-do/experiences/hong_kong?category=Tours'),
            ('click', '/things-to-do/experiences/hong_kong?category=Tours'),
            ('check', '/things-to-do/experiences/hong_kong?category='),
            ('click', '/things-to-do/experiences/hong_kong?category='),
            ('click', '/things-to-do/detail/94229569'),
            ('click', '/things-to-do/book/41?date=2026-10-06&guests=2'),
            ('fill', '/things-to-do/book/41?date=2026-10-06&guests=2'),
            ('fill', '/things-to-do/book/41?date=2026-10-06&guests=2'),
            ('fill', '/things-to-do/book/41?date=2026-10-06&guests=2'),
            ('fill', '/things-to-do/book/41?date=2026-10-06&guests=2'),
            ('click', '/things-to-do/confirmation/TACTYCZD6Y'),
            ('navigate', '/things-to-do/experiences/hong_kong'),
            ('click', '/things-to-do/detail/49800455'),
        ],
        answer=(
            "Hong Kong experiences come in four categories with activities: Activities, "
            "City passes, Tickets and Tours - 35 experiences in total, of which 18 are "
            "tours via the category filter. The cheapest is the Hung Fook Tong e-voucher "
            "at $1.15. The two most-booked are the Top-Rated Hong Kong Tour: Priority Peak "
            "Tram, Dim Sum Tasting, Harbour Cruise & Cultural Sights ($76.52, 27 reviews, "
            "610 booked, package valid for 90 days from the booking date) and the Hong "
            "Kong Skyline Tour Victoria Harbour Cruise (603 booked, package valid for 90 "
            "days). Booked the most-booked for two people on 12 October (lead traveller Leo "
            "Ng). Total paid $153.04, booking reference TACTYCZD6Y."),
        sql=["INSERT INTO attraction_bookings (ref,attraction_id,package_id,user_id,visit_date,"
             "guests,lead_first,lead_last,email,total,status,created_at) VALUES "
             "('TACTYCZD6Y',94229569,41,NULL,'2026-10-12',2,'Leo','Ng',"
             "'leo.ng@example.com',153.04,'confirmed','2026-09-27')"],
    ),
    18: dict(
        steps=[
            ('navigate', '/'),
            ('click', '/things-to-do/'),
            ('click', '/things-to-do/experiences/shanghai'),
            ('check', '/things-to-do/experiences/shanghai?category=Activities'),
            ('click', '/things-to-do/experiences/shanghai?category=Activities'),
            ('check', '/things-to-do/experiences/shanghai?category='),
            ('click', '/things-to-do/experiences/shanghai?category='),
            ('click', '/things-to-do/experiences/shanghai?category=&sort=rating'),
            ('click', '/things-to-do/detail/99290859'),
            ('click', '/things-to-do/book/110?date=2026-10-06&guests=2'),
            ('fill', '/things-to-do/book/110?date=2026-10-06&guests=2'),
            ('fill', '/things-to-do/book/110?date=2026-10-06&guests=2'),
            ('fill', '/things-to-do/book/110?date=2026-10-06&guests=2'),
            ('fill', '/things-to-do/book/110?date=2026-10-06&guests=2'),
            ('fill', '/things-to-do/book/110?date=2026-10-06&guests=2'),
            ('click', '/things-to-do/confirmation/TA37X7VUTL'),
        ],
        answer=(
            "The highest-rated Shanghai activity that is neither a city pass nor a tour is "
            "the Shanghai imperial banquet (5.0 rating, 36 reviews, 652 booked, package "
            "valid for 90 days from the booking date). Shanghai lists 35 experiences in "
            "total, 14 in the Activities category, and 4 share the top 5.0 rating. "
            "Highlights: Shuyanfu integrates panoramic immersive ritual and music culture, "
            "and each dish will surprise your taste buds. I booked it for all three of us "
            "for 12 October (lead traveller Wei Chen). Total paid $48.27, booking reference "
            "TA37X7VUTL."),
        sql=["INSERT INTO attraction_bookings (ref,attraction_id,package_id,user_id,visit_date,"
             "guests,lead_first,lead_last,email,total,status,created_at) VALUES "
             "('TA37X7VUTL',99290859,110,NULL,'2026-10-12',3,'Wei','Chen',"
             "'wei.chen@example.com',48.27,'confirmed','2026-09-27')"],
    ),
    19: dict(
        steps=[
            ('navigate', '/'),
            ('fill', '/'),
            ('click', '/search?q=free+cancellation'),
            ('click', '/guide/free-cancellation-guide'),
            ('click', '/hotels/'),
            ('fill', '/hotels/'),
            ('fill', '/hotels/'),
            ('fill', '/hotels/'),
            ('click', '/hotels/list?city=Las+Vegas&checkin=2026-10-20&checkout=2026-10-21&adults=2'),
            ('fill', '/hotels/list?city=Las+Vegas&checkin=2026-10-20&checkout=2026-10-21&adults=2'),
            ('click', '/hotels/list?city=Las+Vegas&checkin=2026-10-20&checkout=2026-10-21&adults=2&maxprice=60'),
            ('click', '/hotels/list?city=Las+Vegas&checkin=2026-10-20&checkout=2026-10-21&adults=2&maxprice=60&sort=price'),
            ('click', '/hotels/detail/718690?checkin=2026-10-20&checkout=2026-10-21&adults=2'),
            ('click', '/hotels/book/1?checkin=2026-10-20&checkout=2026-10-21&adults=2&children=0'),
            ('navigate', '/hotels/detail/718690?checkin=2026-10-20&checkout=2026-10-21&adults=2'),
            ('navigate', '/hotels/list?city=Las+Vegas&checkin=2026-10-20&checkout=2026-10-21&adults=2&maxprice=60&sort=price'),
            ('click', '/hotels/detail/1775443?checkin=2026-10-20&checkout=2026-10-21&adults=2'),
        ],
        answer=(
            "The free-cancellation guide says refundable rates commonly allow cancelling "
            "before 11:59 PM local hotel time, one to three days before check-in; if you "
            "cancel after that you are charged the first night (or the full amount). The "
            "two cheapest bookable Las Vegas hotels under $60 a night for 20-21 October "
            "are Harrah's Las Vegas (guest score 8.4, 536 reviews) and The LINQ Hotel & "
            "Casino (guest score 8.4, 344 reviews); the runner-up's cheapest room is the "
            "Deluxe Two Double Room Non smoking. For the cheapest one: Las Vegas Strip "
            "area, parking is listed among its amenities, its cheapest room can be "
            "cancelled free before 11:59 PM, Oct 1, and that room's total for those nights "
            "from its booking form is $64.00."),
        sql=[],
    ),
}

# One plausible-but-wrong answer per task (flips a key fact).
WRONG_ANSWERS = {
    0: "I booked the Bellagio Hotel & Casino, promo TRIPNEW20, total $199.00, reference THWRONG01.",
    1: "I picked Four Queens Hotel and Casino, guest score 8.7, total $104.00.",
    2: "Delta round trip: outbound 09:00, return 15:00, total $370.00, reference TFWRONG01.",
    3: "The cheapest route was Chicago to Miami; United and American, total $128.00.",
    4: "United Airlines departing 07:30 for $224, reference TFWRONG04.",
    5: "I booked the Orlando: Go City Explorer Pass, rating 4.5 with 12 reviews, total $121.68.",
    6: "Balance 480; I cancelled the hotel booking THALICE1; the flight stays confirmed.",
    7: "The wishlist now has Thunderbird Boutique Hotel ($57), Hotel 32One ($212) and Horseshoe Las Vegas ($56).",
    8: "The minimum spend is $150; the discount was $25.00 and the final total $164.00.",
    9: "DoubleTree by Hilton New York Downtown, score 8.4, 1956 reviews; cheapest room $175.",
    10: "The guide recommends 3 days per major park; I booked the Go City: Orlando Explorer Pass for $128.00.",
    11: "Carol has 240 coins; the cheapest Miami hotel is Kompose Boutique Hotel Miami Airport with score 8.3.",
    12: "Vegas cheapest is The LINQ at $57 with 8 room choices; NY cheapest is the Hilton at $150; NY is cheaper by $93.",
    13: "Las Vegas Serene Hotel, West of The Strip area, score 8.2, $65 a night; cancellation before 6 PM.",
    14: "The promo discount was $21.10 but the total paid was $211.00.",
    15: "David has 360 coins; his hotel booking at The LINQ earned 64 coins.",
    16: "Two nights cost $189 nightly, $27 taxes per night, $432 total; the hotel scores 8.6 with 700 reviews.",
    17: "There are 3 categories and 30 experiences; the cheapest is $4.40; I booked the Skyline Tour for $27.74.",
    18: "The top activity is the Shanghai Xu Feast with 5.0 rating; highlights mention a grand palace spectacle; total $48.27.",
    19: "The guide says cancellation is allowed until 6 PM two days before check-in; the cheapest Vegas hotel is The LINQ.",
}


# Current browser regression fixtures (synthetic unit-test reconstructions; not new browser evidence).
SPECS = {0: {'answer': 'I booked the Trump International Hotel Las Vegas (5-star, $238/night, outdoor pool) for Sunday 4 '
               'to Monday 5 October. Using the new-user hotel promo code TRIPNEW20 from the deals page, I '
               'reserved its cheapest king-bed room, the Superior King Room. Booking reference THRUFTDZQA. Total '
               'charged: $216.00.',
     'sql': ['INSERT INTO "hotel_bookings" ("ref", "hotel_id", "room_id", "user_id", "guest_first", "guest_last", '
             '"email", "phone", "checkin", "checkout", "rooms", "adults", "children", "nightly", "taxes", '
             '"total", "coins", "promo_code", "status", "created_at") VALUES (\'THRUFTDZQA\', 737533, 54, NULL, '
             "'Jordan', 'Blake', 'jordan.blake@example.com', '+1 555 017 2222', '2026-10-04', '2026-10-05', 1, 2, "
             "0, 238.0, 32.0, 216.0, 2, 'TRIPNEW20', 'confirmed', '2026-09-27');"],
     'steps': [('load', '/'),
               ('click', '/deals/'),
               ('click', '/hotels/'),
               ('fill', '/hotels/'),
               ('click', '/hotels/list?city=Las+Vegas&checkin=2026-10-04&checkout=2026-10-05&adults=2'),
               ('fill', '/hotels/list?city=Las+Vegas&checkin=2026-10-04&checkout=2026-10-05&adults=2'),
               ('click', '/hotels/list?city=Las+Vegas&checkin=2026-10-04&checkout=2026-10-05&adults=2'),
               ('click', '/hotels/list?city=Las+Vegas&checkin=2026-10-04&checkout=2026-10-05&adults=2'),
               ('scroll', '/hotels/list?city=Las+Vegas&checkin=2026-10-04&checkout=2026-10-05&adults=2'),
               ('click',
                '/hotels/list?city=Las+Vegas&checkin=2026-10-04&checkout=2026-10-05&adults=2&sort=recommended&pool=1&minprice=&maxprice=250&star=5&rating=&district='),
               ('click', '/hotels/detail/737533?checkin=2026-10-04&checkout=2026-10-05&adults=2'),
               ('click', '/hotels/book/54?checkin=2026-10-04&checkout=2026-10-05&adults=2&children=0'),
               ('fill', '/hotels/book/54?checkin=2026-10-04&checkout=2026-10-05&adults=2&children=0'),
               ('fill', '/hotels/book/54?checkin=2026-10-04&checkout=2026-10-05&adults=2&children=0'),
               ('fill', '/hotels/book/54?checkin=2026-10-04&checkout=2026-10-05&adults=2&children=0'),
               ('fill', '/hotels/book/54?checkin=2026-10-04&checkout=2026-10-05&adults=2&children=0'),
               ('fill', '/hotels/book/54?checkin=2026-10-04&checkout=2026-10-05&adults=2&children=0'),
               ('fill', '/hotels/book/54?checkin=2026-10-04&checkout=2026-10-05&adults=2&children=0'),
               ('fill', '/hotels/book/54?checkin=2026-10-04&checkout=2026-10-05&adults=2&children=0'),
               ('click', '/hotels/confirmation/THRUFTDZQA')]},
 1: {'answer': 'The two best-rated Las Vegas hotels under $150 a night with free cancellation were Four Queens '
               'Hotel and Casino (8.7, $104) and Planet Hollywood Resort & Casino (8.5, $72). I booked the '
               'cheaper one, Planet Hollywood Resort & Casino, in its lowest-priced room (Room Type Assigned On '
               'Arrival) for 11-12 October. Guest score 8.5. Total paid: $82.00 (booking THA7M9KCGV).',
     'sql': ['INSERT INTO "hotel_bookings" ("ref", "hotel_id", "room_id", "user_id", "guest_first", "guest_last", '
             '"email", "phone", "checkin", "checkout", "rooms", "adults", "children", "nightly", "taxes", '
             '"total", "coins", "promo_code", "status", "created_at") VALUES (\'THA7M9KCGV\', 733224, 38, NULL, '
             "'Dana', 'Reyes', 'dana.reyes@example.com', '+1 555 013 3444', '2026-10-11', '2026-10-12', 1, 2, 0, "
             "72.0, 10.0, 82.0, 0, '', 'confirmed', '2026-09-27');"],
     'steps': [('load', '/'),
               ('click', '/hotels/'),
               ('fill', '/hotels/'),
               ('fill', '/hotels/'),
               ('fill', '/hotels/'),
               ('click', '/hotels/list?city=Las+Vegas&checkin=2026-10-11&checkout=2026-10-12&adults=2'),
               ('fill', '/hotels/list?city=Las+Vegas&checkin=2026-10-11&checkout=2026-10-12&adults=2'),
               ('click', '/hotels/list?city=Las+Vegas&checkin=2026-10-11&checkout=2026-10-12&adults=2'),
               ('scroll', '/hotels/list?city=Las+Vegas&checkin=2026-10-11&checkout=2026-10-12&adults=2'),
               ('click',
                '/hotels/list?city=Las+Vegas&checkin=2026-10-11&checkout=2026-10-12&adults=2&sort=recommended&freecancel=1&minprice=&maxprice=150&rating=&district='),
               ('click', '/hotels/detail/733224?checkin=2026-10-11&checkout=2026-10-12&adults=2'),
               ('click', '/hotels/book/38?checkin=2026-10-11&checkout=2026-10-12&adults=2&children=0'),
               ('fill', '/hotels/book/38?checkin=2026-10-11&checkout=2026-10-12&adults=2&children=0'),
               ('fill', '/hotels/book/38?checkin=2026-10-11&checkout=2026-10-12&adults=2&children=0'),
               ('fill', '/hotels/book/38?checkin=2026-10-11&checkout=2026-10-12&adults=2&children=0'),
               ('fill', '/hotels/book/38?checkin=2026-10-11&checkout=2026-10-12&adults=2&children=0'),
               ('fill', '/hotels/book/38?checkin=2026-10-11&checkout=2026-10-12&adults=2&children=0'),
               ('fill', '/hotels/book/38?checkin=2026-10-11&checkout=2026-10-12&adults=2&children=0'),
               ('click', '/hotels/confirmation/THA7M9KCGV')]},
 2: {'answer': 'I booked the cheapest Delta nonstop round trip from San Francisco to New York, leaving Tuesday 20 '
               'October and returning Tuesday 27 October, economy, one adult (Maria Santos). Outbound Delta '
               'departure 07:00; return Delta departure 07:00. Total paid $441.00. Booking reference TF72YHMQ8G.',
     'sql': ['INSERT INTO "flight_bookings" ("ref", "outbound_id", "return_id", "user_id", "passenger_first", '
             '"passenger_last", "email", "phone", "cabin", "trip_type", "total", "promo_code", "status", '
             '"created_at", "departure_date", "return_date") VALUES (\'TF72YHMQ8G\', 5, 149, NULL, \'Maria\', '
             "'Santos', 'maria.santos@example.com', '+1 555 014 4555', 'Economy', 'rt', 441.0, '', 'confirmed', "
             "'2026-09-27', '2026-10-20', '2026-10-27');"],
     'steps': [('load', '/'),
               ('click', '/flights/'),
               ('fill', '/flights/'),
               ('fill', '/flights/'),
               ('click',
                '/flights/list?triptype=rt&dcity=SFO&acity=JFK&ddate=2026-10-20&rdate=2026-10-27&cabin=Economy'),
               ('click',
                '/flights/list?triptype=rt&dcity=SFO&acity=JFK&ddate=2026-10-20&rdate=2026-10-27&cabin=Economy'),
               ('click',
                '/flights/list?triptype=rt&dcity=SFO&acity=JFK&ddate=2026-10-20&rdate=2026-10-27&cabin=Economy'),
               ('click',
                '/flights/list?dcity=SFO&acity=JFK&ddate=2026-10-20&rdate=2026-10-27&triptype=rt&airline=Delta+Air+Lines&stops=nonstop&dep='),
               ('click',
                '/flights/list?triptype=rt&dcity=SFO&acity=JFK&ddate=2026-10-20&rdate=2026-10-27&cabin=Economy'),
               ('scroll',
                '/flights/list?triptype=rt&dcity=SFO&acity=JFK&ddate=2026-10-20&rdate=2026-10-27&cabin=Economy'),
               ('scroll',
                '/flights/list?triptype=rt&dcity=SFO&acity=JFK&ddate=2026-10-20&rdate=2026-10-27&cabin=Economy'),
               ('click', '/flights/select/5?ddate=2026-10-20&rdate=2026-10-27&cabin=Economy&adults=1'),
               ('click', '/flights/select/5?ddate=2026-10-20&rdate=2026-10-27&cabin=Economy&adults=1'),
               ('click', '/flights/select/5?ddate=2026-10-20&rdate=2026-10-27&cabin=Economy&adults=1'),
               ('click',
                '/flights/select/5?ddate=2026-10-20&rdate=2026-10-27&cabin=Economy&airline=Delta+Air+Lines&stops=nonstop'),
               ('click', '/flights/book?out=5&ret=149&cabin=Economy&ddate=2026-10-20&rdate=2026-10-27&adults=1'),
               ('fill', '/flights/book?out=5&ret=149&cabin=Economy&ddate=2026-10-20&rdate=2026-10-27&adults=1'),
               ('fill', '/flights/book?out=5&ret=149&cabin=Economy&ddate=2026-10-20&rdate=2026-10-27&adults=1'),
               ('fill', '/flights/book?out=5&ret=149&cabin=Economy&ddate=2026-10-20&rdate=2026-10-27&adults=1'),
               ('fill', '/flights/book?out=5&ret=149&cabin=Economy&ddate=2026-10-20&rdate=2026-10-27&adults=1'),
               ('fill', '/flights/book?out=5&ret=149&cabin=Economy&ddate=2026-10-20&rdate=2026-10-27&adults=1'),
               ('fill', '/flights/book?out=5&ret=149&cabin=Economy&ddate=2026-10-20&rdate=2026-10-27&adults=1'),
               ('click', '/flights/confirmation/TF72YHMQ8G')]},
 3: {'answer': 'Comparing the six cheap flight deals on the deals page, the cheapest route was San Francisco '
               '(SFO) to Las Vegas (LAS), from $34. I booked the cheapest nonstop round trip departing 20 October '
               'and returning 27 October: Frontier Airlines outbound and Southwest Airlines return. Total '
               '$114.00. Booking reference TF5FLCZ78H.',
     'sql': ['INSERT INTO "flight_bookings" ("ref", "outbound_id", "return_id", "user_id", "passenger_first", '
             '"passenger_last", "email", "phone", "cabin", "trip_type", "total", "promo_code", "status", '
             '"created_at", "departure_date", "return_date") VALUES (\'TF5FLCZ78H\', 859, 891, NULL, \'Alex\', '
             "'Moore', 'alex.moore@example.com', '+1 555 016 6677', 'Economy', 'rt', 114.0, '', 'confirmed', "
             "'2026-09-27', '2026-10-20', '2026-10-27');"],
     'steps': [('load', '/'),
               ('click', '/deals/'),
               ('click', '/flights/'),
               ('fill', '/flights/'),
               ('fill', '/flights/'),
               ('click',
                '/flights/list?triptype=rt&dcity=SFO&acity=LAS&ddate=2026-10-20&rdate=2026-10-27&cabin=Economy'),
               ('click',
                '/flights/list?triptype=rt&dcity=SFO&acity=LAS&ddate=2026-10-20&rdate=2026-10-27&cabin=Economy'),
               ('click',
                '/flights/list?dcity=SFO&acity=LAS&ddate=2026-10-20&rdate=2026-10-27&triptype=rt&airline=&stops=nonstop&dep='),
               ('click',
                '/flights/list?triptype=rt&dcity=SFO&acity=LAS&ddate=2026-10-20&rdate=2026-10-27&cabin=Economy'),
               ('click', '/flights/select/859?ddate=2026-10-20&rdate=2026-10-27&cabin=Economy&adults=1'),
               ('click', '/flights/book?out=859&ret=891&cabin=Economy&ddate=2026-10-20&rdate=2026-10-27&adults=1'),
               ('fill', '/flights/book?out=859&ret=891&cabin=Economy&ddate=2026-10-20&rdate=2026-10-27&adults=1'),
               ('fill', '/flights/book?out=859&ret=891&cabin=Economy&ddate=2026-10-20&rdate=2026-10-27&adults=1'),
               ('fill', '/flights/book?out=859&ret=891&cabin=Economy&ddate=2026-10-20&rdate=2026-10-27&adults=1'),
               ('fill', '/flights/book?out=859&ret=891&cabin=Economy&ddate=2026-10-20&rdate=2026-10-27&adults=1'),
               ('fill', '/flights/book?out=859&ret=891&cabin=Economy&ddate=2026-10-20&rdate=2026-10-27&adults=1'),
               ('fill', '/flights/book?out=859&ret=891&cabin=Economy&ddate=2026-10-20&rdate=2026-10-27&adults=1'),
               ('click', '/flights/confirmation/TF5FLCZ78H')]},
 4: {'answer': 'The cheapest nonstop flight from Chicago (ORD) to Miami (MIA) on Thursday 22 October departing '
               'before noon was American Airlines departing 08:43 (arriving 12:55). Price: $169 one-way economy. '
               'Booked for Sam Patel, booking reference TFGUDSLRRA.',
     'sql': ['INSERT INTO "flight_bookings" ("ref", "outbound_id", "return_id", "user_id", "passenger_first", '
             '"passenger_last", "email", "phone", "cabin", "trip_type", "total", "promo_code", "status", '
             '"created_at", "departure_date", "return_date") VALUES (\'TFGUDSLRRA\', 624, NULL, NULL, \'Sam\', '
             "'Patel', 'sam.patel@example.com', '+1 555 018 8888', 'Economy', 'ow', 169.0, '', 'confirmed', "
             "'2026-09-27', '2026-10-22', NULL);"],
     'steps': [('load', '/'),
               ('click', '/flights/'),
               ('select', '/flights/'),
               ('fill', '/flights/'),
               ('fill', '/flights/'),
               ('fill', '/flights/'),
               ('click',
                '/flights/list?triptype=ow&dcity=ORD&acity=MIA&ddate=2026-10-22&rdate=2026-10-27&cabin=Economy'),
               ('click',
                '/flights/list?triptype=ow&dcity=ORD&acity=MIA&ddate=2026-10-22&rdate=2026-10-27&cabin=Economy'),
               ('click',
                '/flights/list?triptype=ow&dcity=ORD&acity=MIA&ddate=2026-10-22&rdate=2026-10-27&cabin=Economy'),
               ('click',
                '/flights/list?dcity=ORD&acity=MIA&ddate=2026-10-22&rdate=2026-10-27&triptype=ow&airline=&stops=nonstop&dep=morning'),
               ('click', '/flights/book?out=624&cabin=Economy&ddate=2026-10-22'),
               ('fill', '/flights/book?out=624&cabin=Economy&ddate=2026-10-22'),
               ('fill', '/flights/book?out=624&cabin=Economy&ddate=2026-10-22'),
               ('fill', '/flights/book?out=624&cabin=Economy&ddate=2026-10-22'),
               ('fill', '/flights/book?out=624&cabin=Economy&ddate=2026-10-22'),
               ('fill', '/flights/book?out=624&cabin=Economy&ddate=2026-10-22'),
               ('fill', '/flights/book?out=624&cabin=Economy&ddate=2026-10-22'),
               ('click', '/flights/confirmation/TFGUDSLRRA')]},
 5: {'answer': 'Orlando lists 3 city passes in the City passes category; the cheapest is the Orlando: Go City '
               'Explorer Pass - Choose 2 to 5 Attractions at $60.84. The best-rated pass under $70 is the Go '
               'City: Orlando Explorer Pass (rating 4.0, 1 review, 12 booked). Highlights: Save up to 50% vs '
               'buying individual tickets, and go at your own pace with 30 days validity from your first '
               'attraction visit. The package is valid for 1 year from the booking date. Booked for two guests on '
               '6 October (lead traveller Pat Kim). Total paid $128.00, booking reference TA5QX25L3Z. Augustine '
               'guided day trip including a scenic boat cruise, rating 5.0.',
     'sql': ['INSERT INTO "attraction_bookings" ("ref", "attraction_id", "package_id", "user_id", "visit_date", '
             '"guests", "lead_first", "lead_last", "email", "total", "status", "created_at") VALUES '
             "('TA5QX25L3Z', 46680654, 1, NULL, '2026-10-06', 2, 'Pat', 'Kim', 'pat.kim@example.com', 128.0, "
             "'confirmed', '2026-09-27');"],
     'steps': [('load', '/'),
               ('click', '/things-to-do/'),
               ('scroll', '/things-to-do/'),
               ('scroll', '/things-to-do/'),
               ('click', '/things-to-do/experiences/orlando'),
               ('click', '/things-to-do/experiences/orlando'),
               ('click', '/things-to-do/experiences/orlando?category=City+passes'),
               ('click', '/things-to-do/detail/46680654'),
               ('click', '/things-to-do/book/1?date=2026-10-06&guests=2'),
               ('fill', '/things-to-do/book/1?date=2026-10-06&guests=2'),
               ('fill', '/things-to-do/book/1?date=2026-10-06&guests=2'),
               ('fill', '/things-to-do/book/1?date=2026-10-06&guests=2'),
               ('fill', '/things-to-do/book/1?date=2026-10-06&guests=2'),
               ('fill', '/things-to-do/book/1?date=2026-10-06&guests=2'),
               ('click', '/things-to-do/confirmation/TA5QX25L3Z')]},
 6: {'answer': 'My existing San Francisco (SFO)–New York (JFK) flight booking is TFALICE1, $422, with outbound '
               'departure 22:15 and return departure 11:35. The cheapest nonstop replacement for October 20–27 is '
               'Jetblue Airways outbound at 06:00 ($205) and Delta Air Lines returning at 07:00 ($228), for $433 '
               'total. I cancelled TFALICE1 without making a replacement booking. TFALICE1 is cancelled; hotel '
               'reservation THALICE1 remains confirmed.',
     'sql': ['DELETE FROM "flight_bookings" WHERE "ref"=\'TFALICE1\';',
             'INSERT INTO "flight_bookings" ("ref", "outbound_id", "return_id", "user_id", "passenger_first", '
             '"passenger_last", "email", "phone", "cabin", "trip_type", "total", "promo_code", "status", '
             '"created_at", "departure_date", "return_date") VALUES (\'TFALICE1\', 1, 2, 1, \'Alice\', '
             "'Johnson', 'alice.j@test.com', '+1 555 010 0000', 'Economy', 'rt', 422.0, '', 'cancelled', "
             "'2026-09-27', NULL, NULL);"],
     'steps': [('load', '/'),
               ('click', '/sign-in/'),
               ('fill', '/sign-in/'),
               ('fill', '/sign-in/'),
               ('click', '/account/'),
               ('click', '/account/bookings'),
               ('click', '/flights/'),
               ('fill', '/flights/'),
               ('fill', '/flights/'),
               ('click',
                '/flights/list?triptype=rt&dcity=SFO&acity=JFK&ddate=2026-10-20&rdate=2026-10-27&cabin=Economy'),
               ('click',
                '/flights/list?triptype=rt&dcity=SFO&acity=JFK&ddate=2026-10-20&rdate=2026-10-27&cabin=Economy'),
               ('click',
                '/flights/list?dcity=SFO&acity=JFK&ddate=2026-10-20&rdate=2026-10-27&triptype=rt&airline=&stops=nonstop&dep='),
               ('click',
                '/flights/select/3?ddate=2026-10-20&rdate=2026-10-27&cabin=Economy&adults=1&stops=nonstop'),
               ('click', '/account/'),
               ('click', '/account/bookings'),
               ('click', '/account/bookings')]},
 7: {'answer': 'I saved the best-rated San Francisco hotel under $200 a night, Hotel Fiona - No Resort Fee '
               '($187), to the wishlist and removed the more expensive of the two saved Las Vegas hotels ($57 vs '
               '$56). The hotels that remain on the wishlist are: Hotel 32One at $212 a night, Hotel Fiona - No '
               'Resort Fee at $187 a night, and Horseshoe Las Vegas at $56 a night.',
     'sql': ['DELETE FROM "wishlist_items" WHERE "id"=4;',
             'INSERT INTO "wishlist_items" ("id", "user_id", "hotel_id") VALUES (13, 2, 715700);'],
     'steps': [('load', '/'),
               ('click', '/sign-in/'),
               ('fill', '/sign-in/'),
               ('fill', '/sign-in/'),
               ('click', '/account/'),
               ('click', '/account/wishlist'),
               ('click', '/hotels/'),
               ('fill', '/hotels/'),
               ('click', '/hotels/list?city=San+Francisco&checkin=2026-10-04&checkout=2026-10-05&adults=2'),
               ('fill', '/hotels/list?city=San+Francisco&checkin=2026-10-04&checkout=2026-10-05&adults=2'),
               ('scroll', '/hotels/list?city=San+Francisco&checkin=2026-10-04&checkout=2026-10-05&adults=2'),
               ('click',
                '/hotels/list?city=San+Francisco&checkin=2026-10-04&checkout=2026-10-05&adults=2&sort=recommended&minprice=&maxprice=200&rating=&district='),
               ('click', '/hotels/detail/715700?checkin=2026-10-04&checkout=2026-10-05&adults=2'),
               ('click', '/hotels/detail/715700?checkin=2026-10-04&checkout=2026-10-05&adults=2'),
               ('click', '/account/'),
               ('click', '/account/wishlist'),
               ('click', '/account/wishlist'),
               ('click', '/account/wishlist')]},
 8: {'answer': 'The promo code that takes 20 percent off hotels is TRIPNEW20, with a minimum spend of $100. I '
               'booked the cheapest room at Paris Las Vegas for 4-5 October (Room Type Assigned On Arrival, $167 '
               'a night). Discount: $37.80. Final total: $151.20 (booking THX3F3RK4F).',
     'sql': ['INSERT INTO "hotel_bookings" ("ref", "hotel_id", "room_id", "user_id", "guest_first", "guest_last", '
             '"email", "phone", "checkin", "checkout", "rooms", "adults", "children", "nightly", "taxes", '
             '"total", "coins", "promo_code", "status", "created_at") VALUES (\'THX3F3RK4F\', 733090, 22, NULL, '
             "'Robin', 'Fox', 'robin.fox@example.com', '+1 555 019 9900', '2026-10-04', '2026-10-05', 1, 2, 0, "
             "167.0, 22.0, 151.2, 1, 'TRIPNEW20', 'confirmed', '2026-09-27');"],
     'steps': [('load', '/'),
               ('click', '/deals/'),
               ('click', '/hotels/'),
               ('fill', '/hotels/'),
               ('click', '/hotels/list?city=Paris+Las+Vegas&checkin=2026-10-04&checkout=2026-10-05&adults=2'),
               ('click', '/hotels/detail/733090?checkin=2026-10-04&checkout=2026-10-05&adults=2'),
               ('click', '/hotels/book/22?checkin=2026-10-04&checkout=2026-10-05&adults=2&children=0'),
               ('fill', '/hotels/book/22?checkin=2026-10-04&checkout=2026-10-05&adults=2&children=0'),
               ('fill', '/hotels/book/22?checkin=2026-10-04&checkout=2026-10-05&adults=2&children=0'),
               ('fill', '/hotels/book/22?checkin=2026-10-04&checkout=2026-10-05&adults=2&children=0'),
               ('fill', '/hotels/book/22?checkin=2026-10-04&checkout=2026-10-05&adults=2&children=0'),
               ('fill', '/hotels/book/22?checkin=2026-10-04&checkout=2026-10-05&adults=2&children=0'),
               ('fill', '/hotels/book/22?checkin=2026-10-04&checkout=2026-10-05&adults=2&children=0'),
               ('fill', '/hotels/book/22?checkin=2026-10-04&checkout=2026-10-05&adults=2&children=0'),
               ('click', '/hotels/confirmation/THX3F3RK4F')]},
 9: {'answer': 'The New York weekend guide says Jersey City and Newark rates run 30-40% lower than Manhattan. '
               'Among New York hotels with more than 500 reviews and parking, ranked by guest score: Motto by '
               'Hilton New York City Times Square (score 8.7, 714 reviews) and DoubleTree by Hilton New York '
               'Downtown (score 8.4, 1956 reviews). For the higher-scored one, the two review tags on its results '
               "card are 'American breakfast' and 'Great views'. Its cheapest room is the Flex Room With Wall Bed "
               'at $202 per night, 1 queen bed, breakfast not included, and free cancellation before 11:59 PM, '
               "Oct 1; the booking form shows taxes and fees of $34.00 per night. The other hotel's cheapest room "
               'is the King Room With City View at $175 a night.',
     'sql': [],
     'steps': [('load', '/'),
               ('click', '/guide/'),
               ('click', '/guide/nyc-weekend-midrange'),
               ('click', '/hotels/'),
               ('fill', '/hotels/'),
               ('fill', '/hotels/'),
               ('fill', '/hotels/'),
               ('click', '/hotels/list?city=New+York&checkin=2026-10-20&checkout=2026-10-21&adults=2'),
               ('click', '/hotels/list?city=New+York&checkin=2026-10-20&checkout=2026-10-21&adults=2'),
               ('scroll', '/hotels/list?city=New+York&checkin=2026-10-20&checkout=2026-10-21&adults=2'),
               ('click',
                '/hotels/list?city=New+York&checkin=2026-10-20&checkout=2026-10-21&adults=2&sort=recommended&parking=1&minprice=&maxprice=&rating=&district='),
               ('click',
                '/hotels/list?city=New+York&checkin=2026-10-20&checkout=2026-10-21&adults=2&parking=1&minprice=&maxprice=&rating=&district=&sort=rating'),
               ('click', '/hotels/detail/105237897?checkin=2026-10-20&checkout=2026-10-21&adults=2'),
               ('click', '/hotels/book/124?checkin=2026-10-20&checkout=2026-10-21&adults=2&children=0'),
               ('back', '/hotels/detail/105237897?checkin=2026-10-20&checkout=2026-10-21&adults=2'),
               ('back',
                '/hotels/list?city=New+York&checkin=2026-10-20&checkout=2026-10-21&adults=2&parking=1&minprice=&maxprice=&rating=&district=&sort=rating'),
               ('scroll',
                '/hotels/list?city=New+York&checkin=2026-10-20&checkout=2026-10-21&adults=2&parking=1&minprice=&maxprice=&rating=&district=&sort=rating'),
               ('scroll',
                '/hotels/list?city=New+York&checkin=2026-10-20&checkout=2026-10-21&adults=2&parking=1&minprice=&maxprice=&rating=&district=&sort=rating'),
               ('click', '/hotels/detail/2192841?checkin=2026-10-20&checkout=2026-10-21&adults=2')]},
 10: {'answer': 'The Orlando theme-park planning guide says most travellers need 2 days per major park. The '
                'cheapest city pass is the Orlando: Go City Explorer Pass - Choose 2 to 5 Attractions ($60.84 per '
                'person). Booked for two people for 6 October (lead traveller Mel Wu). Total paid $121.68, '
                'booking reference TAK6BVE7R2.',
      'sql': ['INSERT INTO "attraction_bookings" ("ref", "attraction_id", "package_id", "user_id", "visit_date", '
              '"guests", "lead_first", "lead_last", "email", "total", "status", "created_at") VALUES '
              "('TAK6BVE7R2', 110625321, 2, NULL, '2026-10-06', 2, 'Mel', 'Wu', 'mel.wu@example.com', 121.68, "
              "'confirmed', '2026-09-27');"],
      'steps': [('load', '/'),
                ('click', '/guide/'),
                ('click', '/guide/orlando-theme-park-planning'),
                ('click', '/things-to-do/'),
                ('scroll', '/things-to-do/'),
                ('scroll', '/things-to-do/'),
                ('click', '/things-to-do/experiences/orlando'),
                ('click', '/things-to-do/experiences/orlando'),
                ('click', '/things-to-do/experiences/orlando?category=City+passes'),
                ('click', '/things-to-do/experiences/orlando?category=City+passes&sort=price'),
                ('click', '/things-to-do/detail/110625321'),
                ('click', '/things-to-do/book/2?date=2026-10-06&guests=2'),
                ('fill', '/things-to-do/book/2?date=2026-10-06&guests=2'),
                ('fill', '/things-to-do/book/2?date=2026-10-06&guests=2'),
                ('fill', '/things-to-do/book/2?date=2026-10-06&guests=2'),
                ('fill', '/things-to-do/book/2?date=2026-10-06&guests=2'),
                ('fill', '/things-to-do/book/2?date=2026-10-06&guests=2'),
                ('click', '/things-to-do/confirmation/TAK6BVE7R2')]},
 11: {'answer': 'Hyatt Place Miami Airport East has a guest score of 8.3 and an advertised nightly price of $93. '
                'Its King Room has 1 king bed and 1 sofa bed; the booking form totals $105 including taxes for '
                'October 4–5. Kompose Boutique Hotel Miami Airport scores 8.3 and advertises $100 per night, but '
                'its King Room-Accessible-Non-Smoking has 1 king bed and costs $82 before taxes, $93 including '
                'taxes. Kompose is $12 cheaper at checkout. I did not book either room.',
      'sql': [],
      'steps': [('load', '/'),
                ('click', '/hotels/'),
                ('fill', '/hotels/'),
                ('click', '/hotels/list?city=Miami&checkin=2026-10-04&checkout=2026-10-05&adults=2'),
                ('click', '/hotels/list?city=Miami&checkin=2026-10-04&checkout=2026-10-05&adults=2&sort=price'),
                ('scroll', '/hotels/list?city=Miami&checkin=2026-10-04&checkout=2026-10-05&adults=2&sort=price'),
                ('scroll', '/hotels/list?city=Miami&checkin=2026-10-04&checkout=2026-10-05&adults=2&sort=price'),
                ('click', '/hotels/detail/4648397?checkin=2026-10-04&checkout=2026-10-05&adults=2'),
                ('back', '/hotels/list?city=Miami&checkin=2026-10-04&checkout=2026-10-05&adults=2&sort=price'),
                ('scroll', '/hotels/list?city=Miami&checkin=2026-10-04&checkout=2026-10-05&adults=2&sort=price'),
                ('click', '/hotels/detail/68493916?checkin=2026-10-04&checkout=2026-10-05&adults=2'),
                ('click', '/hotels/book/431?checkin=2026-10-04&checkout=2026-10-05&adults=2&children=0'),
                ('back', '/hotels/detail/68493916?checkin=2026-10-04&checkout=2026-10-05&adults=2'),
                ('back', '/hotels/list?city=Miami&checkin=2026-10-04&checkout=2026-10-05&adults=2&sort=price'),
                ('scroll', '/hotels/list?city=Miami&checkin=2026-10-04&checkout=2026-10-05&adults=2&sort=price'),
                ('click', '/hotels/detail/4648397?checkin=2026-10-04&checkout=2026-10-05&adults=2'),
                ('click', '/hotels/book/498?checkin=2026-10-04&checkout=2026-10-05&adults=2&children=0')]},
 12: {'answer': "For 4-5 October: the cheapest Las Vegas hotel with available rooms is Harrah's Las Vegas ($56 a "
                'night, guest score 8.4) with 5 room choices; the cheapest New York hotel is HI New York City '
                'Hostel ($104 a night, guest score 9.0) with 2 room choices. The Las Vegas hotel is cheaper by '
                '$48.',
      'sql': [],
      'steps': [('load', '/'),
                ('click', '/hotels/'),
                ('fill', '/hotels/'),
                ('click', '/hotels/list?city=Las+Vegas&checkin=2026-10-04&checkout=2026-10-05&adults=2'),
                ('click',
                 '/hotels/list?city=Las+Vegas&checkin=2026-10-04&checkout=2026-10-05&adults=2&sort=price'),
                ('click', '/hotels/detail/718690?checkin=2026-10-04&checkout=2026-10-05&adults=2'),
                ('click', '/hotels/'),
                ('fill', '/hotels/'),
                ('click', '/hotels/list?city=New+York&checkin=2026-10-04&checkout=2026-10-05&adults=2'),
                ('click', '/hotels/list?city=New+York&checkin=2026-10-04&checkout=2026-10-05&adults=2&sort=price'),
                ('click', '/hotels/detail/2092657?checkin=2026-10-04&checkout=2026-10-05&adults=2')]},
 13: {'answer': 'Away from the Strip, the best-rated bookable Las Vegas hotel under $120 a night for 13-14 '
                'October is Four Queens Hotel and Casino, in the Downtown - Fremont Street area: guest score 8.7, '
                '3-star, $104 a night. Its cheapest room (Run Of House Room) can be cancelled free before 11:59 '
                'PM, Oct 1, and its booking-form grand total for those nights is $73.00. The best-rated bookable '
                'Strip hotel under $120 is Planet Hollywood Resort & Casino: guest score 8.5, $72 a night, '
                'cheapest room Room Type Assigned On Arrival. I did not book anything.',
      'sql': [],
      'steps': [('load', '/'),
                ('click', '/hotels/'),
                ('fill', '/hotels/'),
                ('fill', '/hotels/'),
                ('fill', '/hotels/'),
                ('click', '/hotels/list?city=Las+Vegas&checkin=2026-10-13&checkout=2026-10-14&adults=2'),
                ('fill', '/hotels/list?city=Las+Vegas&checkin=2026-10-13&checkout=2026-10-14&adults=2'),
                ('scroll', '/hotels/list?city=Las+Vegas&checkin=2026-10-13&checkout=2026-10-14&adults=2'),
                ('click',
                 '/hotels/list?city=Las+Vegas&checkin=2026-10-13&checkout=2026-10-14&adults=2&sort=recommended&minprice=&maxprice=120&rating=&district='),
                ('click',
                 '/hotels/list?city=Las+Vegas&checkin=2026-10-13&checkout=2026-10-14&adults=2&minprice=&maxprice=120&rating=&district=&sort=rating'),
                ('scroll',
                 '/hotels/list?city=Las+Vegas&checkin=2026-10-13&checkout=2026-10-14&adults=2&minprice=&maxprice=120&rating=&district=&sort=rating'),
                ('scroll',
                 '/hotels/list?city=Las+Vegas&checkin=2026-10-13&checkout=2026-10-14&adults=2&minprice=&maxprice=120&rating=&district=&sort=rating'),
                ('click', '/hotels/detail/718623?checkin=2026-10-13&checkout=2026-10-14&adults=2'),
                ('click', '/hotels/book/30?checkin=2026-10-13&checkout=2026-10-14&adults=2&children=0'),
                ('click', '/hotels/'),
                ('fill', '/hotels/'),
                ('fill', '/hotels/'),
                ('fill', '/hotels/'),
                ('click', '/hotels/list?city=Las+Vegas&checkin=2026-10-13&checkout=2026-10-14&adults=2'),
                ('scroll', '/hotels/list?city=Las+Vegas&checkin=2026-10-13&checkout=2026-10-14&adults=2'),
                ('click', '/hotels/detail/733224?checkin=2026-10-13&checkout=2026-10-14&adults=2')]},
 14: {'answer': 'I booked the cheapest round trip from Miami to New York, departing 24 October and returning 31 '
                'October, economy, one adult, using the flight promo code FLYTRIP10 from the deals page. Promo '
                'discount: $21.10. Total paid: $189.90. Booking reference TFHT7TVQSY.',
      'sql': ['INSERT INTO "flight_bookings" ("ref", "outbound_id", "return_id", "user_id", "passenger_first", '
              '"passenger_last", "email", "phone", "cabin", "trip_type", "total", "promo_code", "status", '
              '"created_at", "departure_date", "return_date") VALUES (\'TFHT7TVQSY\', 783, 852, NULL, \'Jamie\', '
              "'Lee', 'jamie.lee@example.com', '+1 555 015 5566', 'Economy', 'rt', 189.9, 'FLYTRIP10', "
              "'confirmed', '2026-09-27', '2026-10-24', '2026-10-31');"],
      'steps': [('load', '/'),
                ('click', '/deals/'),
                ('click', '/flights/'),
                ('fill', '/flights/'),
                ('fill', '/flights/'),
                ('fill', '/flights/'),
                ('fill', '/flights/'),
                ('click',
                 '/flights/list?triptype=rt&dcity=Miami&acity=New+York&ddate=2026-10-24&rdate=2026-10-31&cabin=Economy'),
                ('click',
                 '/flights/list?triptype=rt&dcity=MIA&acity=LGA&ddate=2026-10-24&rdate=2026-10-31&cabin=Economy'),
                ('click', '/flights/select/783?ddate=2026-10-24&rdate=2026-10-31&cabin=Economy&adults=1'),
                ('click',
                 '/flights/book?out=783&ret=852&cabin=Economy&ddate=2026-10-24&rdate=2026-10-31&adults=1'),
                ('fill', '/flights/book?out=783&ret=852&cabin=Economy&ddate=2026-10-24&rdate=2026-10-31&adults=1'),
                ('fill', '/flights/book?out=783&ret=852&cabin=Economy&ddate=2026-10-24&rdate=2026-10-31&adults=1'),
                ('fill', '/flights/book?out=783&ret=852&cabin=Economy&ddate=2026-10-24&rdate=2026-10-31&adults=1'),
                ('fill', '/flights/book?out=783&ret=852&cabin=Economy&ddate=2026-10-24&rdate=2026-10-31&adults=1'),
                ('fill', '/flights/book?out=783&ret=852&cabin=Economy&ddate=2026-10-24&rdate=2026-10-31&adults=1'),
                ('fill', '/flights/book?out=783&ret=852&cabin=Economy&ddate=2026-10-24&rdate=2026-10-31&adults=1'),
                ('fill', '/flights/book?out=783&ret=852&cabin=Economy&ddate=2026-10-24&rdate=2026-10-31&adults=1'),
                ('click', '/flights/confirmation/TFHT7TVQSY')]},
 15: {'answer': "The existing hotel reservation is Harrah's Las Vegas, Nov 1–3, for $136. The hotel scores 8.4, "
                'is on the Las Vegas Strip, and check-in starts at 16:00. For November 18–20, Room Type Assigned '
                'On Arrival costs $56 nightly and $128 total; no bed type is specified. The Mountain Deluxe Queen '
                'Room has 1 queen bed and costs $132 total. The first option saves $8 and the second saves $4 '
                'versus the existing reservation. No bookings were made or cancelled.',
      'sql': [],
      'steps': [('load', '/'),
                ('click', '/sign-in/'),
                ('fill', '/sign-in/'),
                ('fill', '/sign-in/'),
                ('click', '/account/'),
                ('click', '/account/bookings'),
                ('click', '/hotels/detail/718690'),
                ('fill', '/hotels/detail/718690'),
                ('fill', '/hotels/detail/718690'),
                ('click', '/hotels/detail/718690?checkin=2026-11-18&checkout=2026-11-20&adults=2'),
                ('click', '/hotels/book/1?checkin=2026-11-18&checkout=2026-11-20&adults=2&children=0'),
                ('back', '/hotels/detail/718690?checkin=2026-11-18&checkout=2026-11-20&adults=2'),
                ('scroll', '/hotels/detail/718690?checkin=2026-11-18&checkout=2026-11-20&adults=2'),
                ('click', '/hotels/book/2?checkin=2026-11-18&checkout=2026-11-20&adults=2&children=0')]},
 16: {'answer': 'A two-night stay at Paris Las Vegas starting 5 October in its cheapest room (Room Type Assigned '
                'On Arrival) costs $167 per night before tax, with $22 in taxes and fees per night, for a grand '
                'total of $378, confirmed on the booking form for 5-7 October. The room sleeps 2, has 1 king bed '
                'or 2 queen beds, and can be cancelled free before 11:59 PM, Oct 1. The second-cheapest room, the '
                "Bordeaux Room King, has a grand total of $388 for the same nights. The cheapest room's one-night "
                "total for 5-6 October is $189. The hotel's guest score is 8.6 with 805 reviews, and a site "
                'search shows the Bellagio at $467 a night.',
      'sql': [],
      'steps': [('load', '/'),
                ('fill', '/'),
                ('click', '/search?q=Paris+Las+Vegas'),
                ('click', '/hotels/detail/733090'),
                ('fill', '/hotels/detail/733090'),
                ('fill', '/hotels/detail/733090'),
                ('click', '/hotels/detail/733090?checkin=2026-10-05&checkout=2026-10-07&adults=2'),
                ('click', '/hotels/book/22?checkin=2026-10-05&checkout=2026-10-07&adults=2&children=0'),
                ('back', '/hotels/detail/733090?checkin=2026-10-05&checkout=2026-10-07&adults=2'),
                ('scroll', '/hotels/detail/733090?checkin=2026-10-05&checkout=2026-10-07&adults=2'),
                ('click', '/hotels/book/24?checkin=2026-10-05&checkout=2026-10-07&adults=2&children=0'),
                ('back', '/hotels/detail/733090?checkin=2026-10-05&checkout=2026-10-07&adults=2'),
                ('scroll', '/hotels/detail/733090?checkin=2026-10-05&checkout=2026-10-07&adults=2'),
                ('fill', '/hotels/detail/733090?checkin=2026-10-05&checkout=2026-10-07&adults=2'),
                ('click', '/hotels/detail/733090?checkin=2026-10-05&checkout=2026-10-06&adults=2'),
                ('click', '/hotels/book/22?checkin=2026-10-05&checkout=2026-10-06&adults=2&children=0')]},
 17: {'answer': 'The most-booked experience is Top-Rated Hong Kong Tour: Priority Peak Tram, Dim Sum Tasting, '
                'Harbour Cruise & Cultural Sights, with 610 booked, 27 reviews and a $76.52 per-person price. The '
                'runner-up is Hong Kong Skyline Tour Victoria Harbour Cruise, with 603 booked, 40 reviews and a '
                '$13.87 price. Both packages are valid for 90 days from booking. I booked the Top-Rated Hong Kong '
                'Tour for two people on October 12, lead traveller Leo Ng, for $153.04. Booking reference '
                'TAM9BQD72U.',
      'sql': ['INSERT INTO "attraction_bookings" ("ref", "attraction_id", "package_id", "user_id", "visit_date", '
              '"guests", "lead_first", "lead_last", "email", "total", "status", "created_at") VALUES '
              "('TAM9BQD72U', 94229569, 41, NULL, '2026-10-12', 2, 'Leo', 'Ng', 'leo.ng@example.com', 153.04, "
              "'confirmed', '2026-09-27');"],
      'steps': [('load', '/'),
                ('click', '/things-to-do/'),
                ('scroll', '/things-to-do/'),
                ('click', '/things-to-do/experiences/hong_kong'),
                ('click', '/things-to-do/detail/49800455'),
                ('back', '/things-to-do/experiences/hong_kong'),
                ('click', '/things-to-do/detail/94229569'),
                ('scroll', '/things-to-do/detail/94229569'),
                ('click', '/things-to-do/book/41?date=2026-10-06&guests=2'),
                ('fill', '/things-to-do/book/41?date=2026-10-06&guests=2'),
                ('fill', '/things-to-do/book/41?date=2026-10-06&guests=2'),
                ('fill', '/things-to-do/book/41?date=2026-10-06&guests=2'),
                ('fill', '/things-to-do/book/41?date=2026-10-06&guests=2'),
                ('fill', '/things-to-do/book/41?date=2026-10-06&guests=2'),
                ('click', '/things-to-do/confirmation/TAM9BQD72U')]},
 18: {'answer': 'The highest-rated Shanghai activity that is neither a city pass nor a tour is the Shanghai '
                'imperial banquet (5.0 rating, 36 reviews, 652 booked, package valid for 90 days from the booking '
                'date). Highlights: Shuyanfu integrates panoramic immersive ritual and music culture, and each '
                'dish will surprise your taste buds. I booked it for all three of us for 12 October (lead '
                'traveller Wei Chen). Total paid $48.27, booking reference TAJYWP48FZ.',
      'sql': ['INSERT INTO "attraction_bookings" ("ref", "attraction_id", "package_id", "user_id", "visit_date", '
              '"guests", "lead_first", "lead_last", "email", "total", "status", "created_at") VALUES '
              "('TAJYWP48FZ', 99290859, 110, NULL, '2026-10-12', 3, 'Wei', 'Chen', 'wei.chen@example.com', 48.27, "
              "'confirmed', '2026-09-27');"],
      'steps': [('load', '/'),
                ('click', '/things-to-do/'),
                ('scroll', '/things-to-do/'),
                ('click', '/things-to-do/experiences/shanghai'),
                ('click', '/things-to-do/experiences/shanghai'),
                ('click', '/things-to-do/experiences/shanghai?category=Activities'),
                ('click', '/things-to-do/experiences/shanghai?category=Activities&sort=rating'),
                ('click', '/things-to-do/detail/99290859'),
                ('scroll', '/things-to-do/detail/99290859'),
                ('click', '/things-to-do/book/110?date=2026-10-06&guests=2'),
                ('fill', '/things-to-do/book/110?date=2026-10-06&guests=2'),
                ('fill', '/things-to-do/book/110?date=2026-10-06&guests=2'),
                ('fill', '/things-to-do/book/110?date=2026-10-06&guests=2'),
                ('fill', '/things-to-do/book/110?date=2026-10-06&guests=2'),
                ('fill', '/things-to-do/book/110?date=2026-10-06&guests=2'),
                ('click', '/things-to-do/confirmation/TAJYWP48FZ')]},
 19: {'answer': 'The free-cancellation guide says refundable rates commonly allow cancelling before 11:59 PM '
                'local hotel time, one to three days before check-in; if you cancel after that you are charged '
                'the first night (or the full amount). The two cheapest bookable Las Vegas hotels under $60 a '
                "night for 20-21 October are Harrah's Las Vegas (guest score 8.4, 536 reviews) and The LINQ Hotel "
                "& Casino (guest score 8.4, 344 reviews); the runner-up's cheapest room is the Deluxe Two Double "
                'Room Non smoking. For the cheapest one: Las Vegas Strip area, parking is listed among its '
                "amenities, its cheapest room can be cancelled free before 11:59 PM, Oct 1, and that room's total "
                'for those nights from its booking form is $64.00.',
      'sql': [],
      'steps': [('load', '/'),
                ('fill', '/'),
                ('click', '/search?q=free+cancellation'),
                ('scroll', '/search?q=free+cancellation'),
                ('click', '/guide/free-cancellation-guide'),
                ('click', '/hotels/'),
                ('fill', '/hotels/'),
                ('fill', '/hotels/'),
                ('fill', '/hotels/'),
                ('click', '/hotels/list?city=Las+Vegas&checkin=2026-10-20&checkout=2026-10-21&adults=2'),
                ('fill', '/hotels/list?city=Las+Vegas&checkin=2026-10-20&checkout=2026-10-21&adults=2'),
                ('scroll', '/hotels/list?city=Las+Vegas&checkin=2026-10-20&checkout=2026-10-21&adults=2'),
                ('click',
                 '/hotels/list?city=Las+Vegas&checkin=2026-10-20&checkout=2026-10-21&adults=2&sort=recommended&minprice=&maxprice=60&rating=&district='),
                ('click',
                 '/hotels/list?city=Las+Vegas&checkin=2026-10-20&checkout=2026-10-21&adults=2&minprice=&maxprice=60&rating=&district=&sort=price'),
                ('click', '/hotels/detail/718690?checkin=2026-10-20&checkout=2026-10-21&adults=2'),
                ('click', '/hotels/book/1?checkin=2026-10-20&checkout=2026-10-21&adults=2&children=0'),
                ('back', '/hotels/detail/718690?checkin=2026-10-20&checkout=2026-10-21&adults=2'),
                ('back',
                 '/hotels/list?city=Las+Vegas&checkin=2026-10-20&checkout=2026-10-21&adults=2&minprice=&maxprice=60&rating=&district=&sort=price'),
                ('click', '/hotels/detail/1775443?checkin=2026-10-20&checkout=2026-10-21&adults=2')]}}
