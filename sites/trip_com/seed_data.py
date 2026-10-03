#!/usr/bin/env python3
"""Deterministic build-time seeder for the Trip.com mirror.

Reads the tracked source_data_*.json snapshots (captured from us.trip.com on
2026-09-27) and materializes the SQLite database. Idempotent at the function
level: every seed function early-returns when its table is already populated.
Run with PYTHONHASHSEED=0 for byte-reproducible builds.
"""
import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def _load(name):
    with open(os.path.join(BASE_DIR, name), encoding="utf-8") as fh:
        return json.load(fh)


def build_seed(db):
    """Populate the catalog tables (cities, hotels, rooms, flights, ...)."""
    from app import (Airport, Attraction, AttractionPackage, City, Coupon,
                     Flight, FlightRoute, Guide, Hotel, HotelPhoto, HotelReview,
                     RoomRate)

    cities = _load("source_data_cities.json")
    hotels = _load("source_data_hotels.json")
    flights = _load("source_data_flights.json")
    attractions = _load("source_data_attractions.json")
    content = _load("source_data_content.json")
    images = _load("source_data_images.json")

    for c in cities:
        cimg = images["cities"].get(c["slug"], "")
        db.session.add(City(id=c["id"], name=c["name"], slug=c["slug"],
                            state=c["state"], image=cimg, blurb=c["blurb"]))
    db.session.flush()

    # deterministic image path assignment happens in download_images.py; the
    # source snapshots carry the upstream URL and we mirror that layout under
    # static/images/hotels/<hotel_id>_<n>.jpg
    for h in hotels:
        hotel_paths = images["hotels"].get(str(h["id"]), [])
        img_name = hotel_paths[0] if hotel_paths else ""
        hotel = Hotel(
            id=h["id"], city_id=h["_city_id"],
            name=h["name"], stars=h.get("stars", 0) or 0,
            rating=h.get("rating", 0.0) or 0.0,
            reviews_count=h.get("reviews_count", 0) or 0,
            address=h.get("address", "") or "", district=h.get("district", "") or "",
            near=h.get("near", "") or "",
            price=h.get("price", 0.0) or 0.0, total=h.get("total", 0.0) or 0.0,
            img=img_name,
            amenities=json.dumps(h.get("amenities", [])[:16]),
            tags=json.dumps(h.get("tags", [])[:6]),
            impression=h.get("impression", "") or "",
            bookable=bool(h.get("bookable")),
            checkin_from=h.get("checkin_from", "15:00") or "15:00",
            checkout_by=h.get("checkout_by", "11:00") or "11:00",
        )
        db.session.add(hotel)
        for n, photo_path in enumerate(hotel_paths[:5], start=1):
            db.session.add(HotelPhoto(hotel_id=h["id"], path=photo_path))
        for r in h.get("rooms", [])[:8]:
            if not r.get("price"):
                continue
            db.session.add(RoomRate(
                hotel_id=h["id"], name=r["name"][:110], bed=r.get("bed", "")[:70],
                view=r.get("view", "")[:70], size_sqft=r.get("size_sqft", 0) or 0,
                capacity=r.get("capacity", 2) or 2,
                price=r["price"], total=r.get("total") or r["price"],
                breakfast=bool(r.get("breakfast")),
                free_cancel=bool(r.get("free_cancel", True)),
                note=r.get("label", "")[:150]))
        for rv in h.get("reviews", [])[:5]:
            db.session.add(HotelReview(
                hotel_id=h["id"], rating=rv.get("rating", 8.0),
                text=rv.get("text", "")[:400],
                traveller=rv.get("traveller", "Traveller")[:40],
                review_date=rv.get("review_date", "Sep 2026")))
    db.session.flush()

    for ap in flights["airports"]:
        db.session.add(Airport(code=ap["code"], name=ap["name"], city=ap["city"]))
    for r in flights["routes"]:
        db.session.add(FlightRoute(id=r["id"], origin_code=r["origin_code"],
                                   dest_code=r["dest_code"],
                                   origin_city=r["origin_city"],
                                   dest_city=r["dest_city"]))
    db.session.flush()
    for f in flights["flights"]:
        db.session.add(Flight(
            id=f["id"], route_id=f["route_id"], leg=f["leg"],
            airline=f["airline"], flight_no=f.get("flight_no", ""),
            dep_time=f["dep_time"], dep_terminal=f.get("dep_term", "") or "",
            arr_time=f["arr_time"], arr_terminal=f.get("arr_term", "") or "",
            plus1=bool(f.get("plus1")),
            duration_min=f.get("duration_min", 0) or 0,
            stops=f.get("stops", 0) or 0, stopover=f.get("stopover", "") or "",
            price=f["price"], baggage=f.get("baggage", "Carry-on baggage included")))
    db.session.flush()

    for a in attractions:
        att_paths = images["attractions"].get(str(a["id"]), [])
        img_name = att_paths[0] if att_paths else ""
        db.session.add(Attraction(
            id=a["id"], city_slug=a["city_slug"], name=a["name"][:190],
            category=a.get("category", "Activities"),
            rating=a.get("rating", 0.0) or 0.0,
            reviews_count=a.get("reviews_count", 0) or 0,
            booked_count=a.get("booked_count", 0) or 0,
            price_from=a.get("price_from", 0.0) or 0.0,
            img=img_name, description=a.get("description", ""),
            highlights=a.get("highlights", ""),
            price_unit=a.get("price_unit", "per person"),
            cancellation=a.get("cancellation", "Cancellation terms not specified")))
        for p in a.get("packages", [])[:5]:
            if p.get("price"):
                db.session.add(AttractionPackage(
                    id=p.get("id"), attraction_id=a["id"], name=p["name"][:190],
                    price=p["price"],
                    validity=p.get("validity") or "Validity not specified in this snapshot"))
    db.session.flush()

    for cp in content["coupons"]:
        db.session.add(Coupon(code=cp["code"], kind=cp["kind"], value=cp["value"],
                              scope=cp["scope"], min_spend=cp["min_spend"],
                              description=cp["description"], active=True))
    for g in content["guides"]:
        gimg = images["guides"].get(g["slug"], "")
        db.session.add(Guide(slug=g["slug"], title=g["title"], city=g["city"],
                             img=gimg, body=g["body"]))
    db.session.commit()


def build_benchmark_users(db, bcrypt, password_hash):
    """Seed the four benchmark users with pre-existing bookings and wishlists."""
    from app import (AttractionBooking, AttractionPackage, Flight,
                     FlightBooking, Hotel, HotelBooking, RoomRate, User,
                     WishlistItem)
    from datetime import date

    if User.query.filter_by(email='alice.j@test.com').first():
        return
    USERS = [
        {'username': 'alice_j', 'email': 'alice.j@test.com', 'display_name': 'Alice Johnson'},
        {'username': 'bob_c', 'email': 'bob.c@test.com', 'display_name': 'Bob Chen'},
        {'username': 'carol_d', 'email': 'carol.d@test.com', 'display_name': 'Carol Davis'},
        {'username': 'david_k', 'email': 'david.k@test.com', 'display_name': 'David Kim'},
    ]
    for u in USERS:
        db.session.add(User(email=u["email"], name=u["display_name"],
                            password_hash=password_hash, coins=480, phone="+1 555 010 0000"))
    db.session.flush()

    # deterministic pre-existing bookings, one per user, using seed rows
    rooms = RoomRate.query.order_by(RoomRate.id).limit(8).all()
    flights = Flight.query.order_by(Flight.id).limit(8).all()
    atts = AttractionPackage.query.order_by(AttractionPackage.id).limit(4).all()
    hotels = {r.hotel_id for r in rooms}
    hotel_rows = Hotel.query.filter(Hotel.id.in_(sorted(hotels))).order_by(Hotel.id).all()

    specs = [
        # (user_idx, kind, ref, extras)
        (0, 'hotel', 'THALICE1', dict(checkin=date(2026, 10, 4), checkout=date(2026, 10, 6))),
        (0, 'flight', 'TFALICE1', {}),
        (1, 'hotel', 'THBOBCH1', dict(checkin=date(2026, 10, 11), checkout=date(2026, 10, 12))),
        (1, 'attraction', 'TABOBCH1', dict(visit=date(2026, 10, 5))),
        (2, 'hotel', 'THCAROL1', dict(checkin=date(2026, 10, 18), checkout=date(2026, 10, 20))),
        (2, 'flight', 'TFCAROL1', {}),
        (3, 'hotel', 'THDAVID1', dict(checkin=date(2026, 11, 1), checkout=date(2026, 11, 3))),
        (3, 'attraction', 'TADAVID1', dict(visit=date(2026, 11, 2))),
    ]
    room_i, flight_i, att_i = 0, 0, 0
    for user_idx, kind, ref, extras in specs:
        user = User.query.filter_by(email=USERS[user_idx]['email']).first()
        if kind == 'hotel':
            room = rooms[room_i % len(rooms)]
            room_i += 1
            checkin = extras['checkin']
            checkout = extras['checkout']
            nights = (checkout - checkin).days
            taxes = (room.total - room.price) * nights
            base = room.price * nights + taxes
            db.session.add(HotelBooking(
                ref=ref, hotel_id=room.hotel_id, room_id=room.id, user_id=user.id,
                guest_first=user.name.split()[0], guest_last=user.name.split()[-1],
                email=user.email, phone=user.phone,
                checkin=checkin, checkout=checkout, adults=2, children=0,
                nightly=room.price, taxes=taxes, total=round(base, 2),
                coins=int(base), promo_code='', status='confirmed'))
        elif kind == 'flight':
            out = flights[flight_i % len(flights)]
            ret = flights[(flight_i + 1) % len(flights)]
            flight_i += 2
            total = out.price + ret.price
            db.session.add(FlightBooking(
                ref=ref, outbound_id=out.id, return_id=ret.id, user_id=user.id,
                passenger_first=user.name.split()[0], passenger_last=user.name.split()[-1],
                email=user.email, phone=user.phone, cabin='Economy',
                trip_type='rt', total=round(total, 2), promo_code='',
                status='confirmed'))
        else:
            pkg = atts[att_i % len(atts)]
            att_i += 1
            db.session.add(AttractionBooking(
                ref=ref, attraction_id=pkg.attraction_id, package_id=pkg.id,
                user_id=user.id, visit_date=extras['visit'], guests=2,
                lead_first=user.name.split()[0], lead_last=user.name.split()[-1],
                email=user.email, total=round(pkg.price * 2, 2),
                status='confirmed'))

    # wishlists: 3 saved hotels per user
    all_hotels = Hotel.query.order_by(Hotel.id).limit(24).all()
    for i, u in enumerate(USERS):
        user = User.query.filter_by(email=u['email']).first()
        for h in all_hotels[i * 3:(i * 3 + 3)]:
            db.session.add(WishlistItem(user_id=user.id, hotel_id=h.id))
    db.session.commit()


# ------------------------------------------------------------------- entrypoint --
# Thin wrapper: importing app.py already materializes the seed inside
# `with app.app_context():` (db.create_all + the gated seed_database /
# seed_benchmark_users); __main__ re-runs the same gated path as a no-op so
# this entry point is idempotent. Run with PYTHONHASHSEED=0 during the image
# build so the SQLite output is byte-reproducible: the benchmark users use a
# frozen bcrypt hash and every other row comes from the tracked
# source_data_*.json snapshots in a fixed order.
if __name__ == '__main__':
    from app import app  # noqa: F401  (import triggers the gated bootstrap)
