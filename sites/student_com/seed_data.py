"""Build-time seed for the student_com mirror.

Reads the tracked source_data/ catalogues (real content captured from
www.student.com — see provenance.json) and materializes them into University /
City / Property / PropertyUniversity / Job rows, plus four benchmark users with
pre-populated saved properties, recently-viewed history and inquiry history.

Deterministic: no wall clock, no random, no hash-order dependence. The
benchmark password hash is frozen and the logical content (schema + every
row) reproduces exactly on every rebuild; the raw SQLite file bytes may still
differ between rebuilds because the physical page layout varies run to run.

Idempotency lives at the function level (each seed_* early-returns on a
populated DB) — wired from app.py's bootstrap.
"""
import json
import os
import shutil
import sys
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SOURCE_DIR = os.path.join(BASE_DIR, "source_data")

# bcrypt hash of 'TestPass123!' (cost 12), frozen so every rebuild carries the
# same identity columns (logical-content determinism; see module docstring).
FROZEN_PASSWORD_HASH = "$2b$12$WtOBgikyE24OU/kuhls4Fuy1s2Kuz/osD0cproGZjpkL713kWy58q"

REFERENCE_DATE = datetime(2026, 9, 26)

BENCHMARK_USERS = [
    {"username": "alice_j", "email": "alice.j@test.com", "first_name": "Alice",
     "last_name": "Johnson", "phone": "(512) 555-0142"},
    {"username": "bob_c", "email": "bob.c@test.com", "first_name": "Bob",
     "last_name": "Chen", "phone": "(404) 555-0187"},
    {"username": "carol_d", "email": "carol.d@test.com", "first_name": "Carol",
     "last_name": "Davis", "phone": "(614) 555-0119"},
    {"username": "david_k", "email": "david.k@test.com", "first_name": "David",
     "last_name": "Kim", "phone": "(352) 555-0163"},
]


def _load(name):
    with open(os.path.join(SOURCE_DIR, name), encoding="utf-8") as handle:
        return json.load(handle)


def run_seed(db, University, City, Property, PropertyUniversity, Job):
    """Materialize catalog + content rows. Called by app.seed_database()."""
    if Property.query.count() > 0:
        return

    # ---- universities ----
    unis = _load("universities.json")
    for slug, u in sorted(unis.items()):
        db.session.add(University(slug=slug, name=u["name"], state=u["state"],
                                  city_slug=u["city_slug"],
                                  has_properties=bool(u.get("has_properties")),
                                  total_properties=int(u.get("total_properties") or 0),
                                  aliases=u.get("aliases") or [],
                                  latitude=float(u["latitude"]) if u.get("latitude") else None,
                                  longitude=float(u["longitude"]) if u.get("longitude") else None))
    db.session.flush()

    # ---- cities ----
    cities = _load("cities.json")
    for slug, c in sorted(cities.items()):
        db.session.add(City(slug=slug, state=c["state"], name=c["name"],
                            headline=c.get("headline"), summary=c.get("summary"),
                            hero=c.get("hero"),
                            meta_description=c.get("meta_description"),
                            content={"editorial_lines": c.get("editorial_lines") or [],
                                     "universities_listed": c.get("universities_listed") or [],
                                     "austin_lines": c.get("austin_lines") or [],
                                     "source_url": c.get("source_url")}))
    db.session.flush()

    # ---- properties + university links ----
    props = _load("properties.json")
    for slug, p in sorted(props.items()):
        if not p.get("city_slug") or not p.get("state_slug"):
            continue
        db.session.add(Property(
            upstream_id=p["id"], slug=slug, name=p["name"],
            city_slug=p["city_slug"], state_slug=p["state_slug"],
            address=p.get("address"), latitude=p.get("latitude"),
            longitude=p.get("longitude"),
            min_price=p.get("min_price"), max_price=p.get("max_price"),
            property_type=p.get("property_type") or "Apartment",
            rating=p.get("rating"),
            user_rating_count=int(p.get("user_rating_count") or 0),
            wheelchair_accessible=bool(p.get("wheelchair_accessible")),
            contact_email=p.get("contact_email"),
            phone_number=p.get("phone_number"), website=p.get("website"),
            google_maps_url=p.get("google_maps_url"),
            property_summary=p.get("property_summary"),
            reviews_summary=p.get("reviews_summary"),
            room_types=p.get("room_types") or [],
            room_details=p.get("room_details") or {},
            amenities=[a for a in (p.get("amenities") or []) if a],
            vibes=p.get("vibes") or [],
            neighbourhood_tags=p.get("neighbourhood_tags") or [],
            office_hours=p.get("office_hours") or [],
            is_featured=bool(p.get("is_featured")),
            hide_contact=bool(p.get("hide_contact")),
            images=p.get("images") or [], reviews=p.get("reviews") or [],
            university_name=p.get("university"),
            university_slug=p.get("university_slug")))
    db.session.flush()

    for slug, p in sorted(props.items()):
        for link in p.get("universities") or []:
            db.session.add(PropertyUniversity(
                property_slug=slug, university_slug=link["slug"],
                distance_miles=link.get("distance_miles"),
                property_index=link.get("property_index")))
    db.session.flush()

    # ---- jobs ----
    jobs = _load("jobs.json")
    for city_slug, block in sorted(jobs.items()):
        for j in block.get("listings") or []:
            db.session.add(Job(upstream_id=j["id"], city_slug=city_slug,
                               title=j["title"], company=j.get("company"),
                               location=j.get("location"), type=j.get("type"),
                               raw_type=j.get("raw_type"), url=j.get("url"),
                               posted_at=j.get("posted_at")))
    db.session.commit()


def run_seed_users(db, User, Property, Bookmark, Enquiry, PropertyView):
    """Seed the four benchmark users with saved/viewed/inquiry history."""
    if User.query.filter_by(email="alice.j@test.com").first():
        return

    def pick(slug):
        return Property.query.filter_by(slug=slug).first()

    # Saved properties (3-6 each), viewed history and past inquiries per user.
    fixtures = {
        "alice.j@test.com": {
            "bookmarks": ["moontower-69d81c", "villas-on-rio-8639e0",
                          "international-house-i-house-fw4un9"],
            "viewed": ["moontower-69d81c", "villas-on-rio-8639e0",
                       "san-jacinto-hall-sjh-xb6krk", "linea-midtown-zb0foh"],
            "enquiries": [
                ("moontower-69d81c", "Hi, I'm looking for a studio with a private "
                 "bathroom for the fall semester. Is it still available?",
                 REFERENCE_DATE - timedelta(days=6)),
                ("villas-on-rio-8639e0", "Could you send me the current availability "
                 "and any move-in specials for 2 bed units?",
                 REFERENCE_DATE - timedelta(days=2)),
            ],
        },
        "bob.c@test.com": {
            "bookmarks": ["moore-hill-hall-dormitory-mhd-qwmhau",
                          "roberts-hall-dormitory-rhd-sy8v2e",
                          "catalyst-s7m7fb", "bower-westside-qbc6j2"],
            "viewed": ["moore-hill-hall-dormitory-mhd-qwmhau",
                       "roberts-hall-dormitory-rhd-sy8v2e", "catalyst-s7m7fb"],
            "enquiries": [
                ("catalyst-s7m7fb", "Do you offer short 9-month leases for grad "
                 "students? Also, is parking included?",
                 REFERENCE_DATE - timedelta(days=9)),
            ],
        },
        "carol.d@test.com": {
            "bookmarks": ["eighth-street-apartments-z0rz15",
                          "university-house-midtown-nyxxvk"],
            "viewed": ["eighth-street-apartments-z0rz15",
                       "university-house-midtown-nyxxvk",
                       "linea-midtown-zb0foh"],
            "enquiries": [
                ("eighth-street-apartments-z0rz15", "I'm an incoming freshman — "
                 "what's included in the rent and how do roommates get matched?",
                 REFERENCE_DATE - timedelta(days=12)),
            ],
        },
        "david.k@test.com": {
            "bookmarks": ["ion-austin-b569f2", "icon-at-austin-7dbeeb",
                          "the-standard-at-atlanta-vesb8v"],
            "viewed": ["ion-austin-b569f2", "icon-at-austin-7dbeeb"],
            "enquiries": [],
        },
    }

    for spec in BENCHMARK_USERS:
        user = User(email=spec["email"], password_hash=FROZEN_PASSWORD_HASH,
                    first_name=spec["first_name"], last_name=spec["last_name"],
                    phone=spec["phone"], created_at=REFERENCE_DATE)
        db.session.add(user)
        db.session.flush()
        fx = fixtures.get(spec["email"], {})
        for i, slug in enumerate(fx.get("bookmarks") or []):
            if pick(slug) is None:
                continue
            db.session.add(Bookmark(user_id=user.id, property_slug=slug,
                                   created_at=REFERENCE_DATE - timedelta(days=10 - i)))
        for i, slug in enumerate(fx.get("viewed") or []):
            if pick(slug) is None:
                continue
            db.session.add(PropertyView(user_id=user.id, session_key=f"seed-{user.id}",
                                        property_slug=slug,
                                        viewed_at=REFERENCE_DATE - timedelta(days=3 - i // 2)))
        for slug, message, when in fx.get("enquiries") or []:
            if pick(slug) is None:
                continue
            db.session.add(Enquiry(user_id=user.id, property_slug=slug,
                                   first_name=spec["first_name"],
                                   last_name=spec["last_name"],
                                   phone=spec["phone"], email=spec["email"],
                                   message=message, marketing_consent=False,
                                   created_at=when))
    db.session.commit()


if __name__ == "__main__":
    # Standalone build mode: (re)build the seed DB and publish it as
    # instance_seed/student_com.db (same contract as the mta / speedo
    # build-generated seeds). The Dockerfile seed gate wipes instance/ before
    # rerunning this.
    base = os.path.dirname(os.path.abspath(__file__))
    os.makedirs(os.path.join(base, "instance"), exist_ok=True)
    sys.path.insert(0, base)
    import app as app_module
    app_db = app_module.db
    with app_module.app.app_context():
        app_db.create_all()
        app_module.seed_database()
        app_module.seed_benchmark_users()
    print("seeded")
    seed_dir = os.path.join(base, "instance_seed")
    os.makedirs(seed_dir, exist_ok=True)
    shutil.copyfile(os.path.join(base, "instance", "student_com.db"),
                    os.path.join(seed_dir, "student_com.db"))
    print("seed complete; copied instance/student_com.db to instance_seed/student_com.db")
