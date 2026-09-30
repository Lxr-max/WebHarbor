"""Build-time / boot-time seeder for the super_lawyers mirror.

Loads the tracked source_data/ snapshots (captured from the live
superlawyers.com on 2026-09-26 with Playwright; see provenance.json)
into instance/super_lawyers.db. Every seed function early-returns on a
populated database so /reset/super_lawyers stays byte-identical.

Deterministic: PYTHONHASHSEED=0 + no wall clock + a frozen bcrypt digest
for the benchmark password keep the SQLite output byte-reproducible.
"""
from __future__ import annotations

import json
import pathlib
import re

BASE_DIR = pathlib.Path(__file__).resolve().parent
SOURCE = BASE_DIR / "source_data"
LISTINGS = SOURCE / "listings"
LAWYERS = SOURCE / "lawyers"
FIRMS = SOURCE / "firms"
RESOURCES = SOURCE / "resources"
ANSWERS = SOURCE / "answers"
ARTICLES = SOURCE / "articles"
LAWYER_IMG_DIR = BASE_DIR / "static" / "images" / "lawyers"


def _lawyer_img(uuid: str, suffix: str = "") -> str | None:
    """Resolve the on-disk image variant for a lawyer (ext follows the
    downloaded bytes: f_auto may serve png or jpg)."""
    if not LAWYER_IMG_DIR.exists():
        return None
    for cand in LAWYER_IMG_DIR.glob(f"{uuid}{suffix}.*"):
        return f"images/lawyers/{cand.name}"
    return None

db = None  # injected by app.py before seeding

# Frozen bcrypt digest for the benchmark password 'TestPass123!' (frozen
# rather than re-generated so the seed DB is byte-reproducible).
BENCHMARK_PASSWORD_DIGEST = (
    "$2b$12$mTNQa9oqZyOoIJBpKN.0p.LVaApMSu9gZnYufEZrciM5QgBN7EM7u"
)


def _read(path):
    return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))


def _j(value):
    return json.dumps(value, ensure_ascii=False)


def _year_span(text):
    """'2010, 2013 - 2026' -> (2010, 2026); '2005 - 2006' -> (2005, 2006)."""
    if not text:
        return None
    years = [int(y) for y in re.findall(r"\d{4}", text)]
    return (min(years), max(years)) if years else None


def seed_database():
    if db is None:
        return
    if db.session.execute(db.text("SELECT COUNT(*) FROM lawyers")).scalar():
        return

    # ---- directory taxonomy ----------------------------------------------
    directory = _read(SOURCE / "directory.json")
    for row in directory["states"]:
        db.session.execute(db.text(
            "INSERT INTO states (slug, name) VALUES (:s, :n)"),
            dict(s=row["slug"], n=row["name"]))
    for row in directory["cities"]:
        db.session.execute(db.text(
            "INSERT INTO cities (slug, name, state_slug) VALUES (:s, :n, :st)"),
            dict(s=row["slug"], n=row["name"], st=row["state"]))
    for row in directory["practice_areas"]:
        db.session.execute(db.text(
            "INSERT INTO practice_areas (slug, name) VALUES (:s, :n)"),
            dict(s=row["slug"], n=row["name"]))
    db.session.commit()

    # ---- firms --------------------------------------------------------------
    for path in sorted(FIRMS.glob("*.json")):
        rec = _read(path)
        db.session.execute(db.text(
            "INSERT INTO firms (uuid, slug, name, state_slug, city_slug,"
            " office_json, phone, map_path) VALUES"
            " (:u, :s, :n, :st, :c, :o, :p, :m)"),
            dict(u=path.stem, s=rec.get("slug") or rec.get("url", "").rstrip("/").split("/")[-2],
                 n=rec.get("name") or rec.get("slug") or path.stem,
                 st=rec.get("state") or "", c=rec.get("city") or "",
                 o=_j(rec.get("office") or []),
                 p=rec.get("phone"),
                 m=f"images/maps/{path.stem}.png"))
    db.session.commit()

    # ---- lawyers --------------------------------------------------------------
    for path in sorted(LAWYERS.glob("*.json")):
        rec = _read(path)
        uuid = path.stem
        # the profile URL pins the lawyer's city/state
        m = re.search(r"superlawyers\.com/([a-z0-9-]+)/([a-z0-9-]+)/lawyer/",
                      rec.get("url") or "")
        state_slug = m.group(1) if m else rec.get("state_slug", "")
        city_slug = m.group(2) if m else rec.get("city_slug", "")
        slug = rec.get("slug") or (rec.get("url") or "").rstrip("/").split("/")[-2] \
            if (rec.get("url") or "").rstrip("/").split("/")[-1].startswith(tuple("0123456789abcdef")) \
            else rec.get("slug") or ""
        firm = rec.get("firm") or {}
        photo_full = _lawyer_img(uuid)
        photo_card = _lawyer_img(uuid, "_card")
        photo_top = _lawyer_img(uuid, "_top")
        db.session.execute(db.text(
            "INSERT INTO lawyers (uuid, slug, name, tagline, photo_path,"
            " card_photo_path, top_photo_path, phone, state_slug, city_slug,"
            " firm_uuid, side_practice_areas, licensed_since, education,"
            " sl_years, rs_years, sl_years_count, rs_years_count,"
            " first_admitted, professional_webpage, languages_json,"
            " about_json, practice_areas_json, focus_areas_json,"
            " pa_breakdown_json, honors_json, office_json, findlaw, lawinfo,"
            " online_links_json) VALUES"
            " (:u, :s, :n, :t, :pf, :pc, :pt, :ph, :st, :ci, :fu, :spa,"
            " :ls, :ed, :sly, :rsy, :slc, :rsc, :fa, :pw, :lang, :ab,"
            " :pa, :focus, :pab, :hon, :off, :fl, :li, :ol)"),
            dict(
                u=uuid, s=slug, n=rec.get("name") or "",
                t=rec.get("tagline"), pf=photo_full, pc=photo_card, pt=photo_top,
                ph=rec.get("phone"), st=state_slug, ci=city_slug,
                fu=firm.get("uuid"), spa=rec.get("side_practice_areas"),
                ls=rec.get("licensed_since"), ed=rec.get("education"),
                sly=rec.get("sl_selection") or rec.get("sl_years"),
                rsy=rec.get("rs_selection") or rec.get("rs_years"),
                slc=rec.get("sl_years_count") or 0,
                rsc=rec.get("rs_years_count") or 0,
                fa=rec.get("first_admitted"), pw=rec.get("professional_webpage"),
                lang=_j(rec.get("languages") or []),
                ab=_j(rec.get("about") or []),
                pa=_j(rec.get("practice_areas") or []),
                focus=_j(rec.get("focus_areas") or []),
                pab=_j(rec.get("pa_breakdown") or []),
                hon=_j(rec.get("honors") or []),
                off=_j(rec.get("office") or []),
                fl=1 if rec.get("findlaw") else 0,
                li=1 if rec.get("lawinfo") else 0,
                ol=_j(rec.get("online_links") or []),
            ))
    db.session.commit()

    # ---- listing entries + meta + courts ----------------------------------------
    seen_courts = set()
    for path in sorted(LISTINGS.glob("*.json")):
        rec = _read(path)
        pa, st, ci = rec["practice_slug"], rec["state_slug"], rec["city_slug"]
        db.session.execute(db.text(
            "INSERT INTO listing_meta (practice_slug, state_slug, city_slug,"
            " h1, intro_json, faq_json, nearby_json, related_json) VALUES"
            " (:pa, :st, :ci, :h1, :intro, :faq, :nb, :rel)"),
            dict(pa=pa, st=st, ci=ci, h1=rec.get("h1") or "",
                 intro=_j(rec.get("intro") or []),
                 faq=_j(rec.get("faq") or []),
                 nb=_j(rec.get("nearby_cities") or []),
                 rel=_j(rec.get("related_practice_areas") or [])))
        for pos, card in enumerate(rec.get("cards", [])):
            if not card.get("profile_uuid"):
                continue
            db.session.execute(db.text(
                "INSERT INTO listing_entries (practice_slug, state_slug,"
                " city_slug, position, lawyer_uuid, name, city_line, tagline,"
                " phone, firm_name, sponsored) VALUES"
                " (:pa, :st, :ci, :pos, :u, :nm, :cl, :t, :ph, :fn, :sp)"),
                dict(pa=pa, st=st, ci=ci, pos=pos, u=card["profile_uuid"],
                     nm=card.get("name"), cl=card.get("city_line"),
                     t=card.get("tagline"), ph=card.get("phone"),
                     fn=card.get("firm_name"),
                     sp=1 if card.get("sponsored") else 0))
        for court in rec.get("courts") or []:
            key = (st, ci, court["name"])
            if key in seen_courts:
                continue
            seen_courts.add(key)
            db.session.execute(db.text(
                "INSERT INTO courts (state_slug, city_slug, name, line1,"
                " line2, phone, website) VALUES"
                " (:st, :ci, :n, :l1, :l2, :p, :w)"),
                dict(st=st, ci=ci, n=court["name"], l1=court["line1"],
                     l2=court.get("line2"), p=court["phone"],
                     w=court.get("website")))
    db.session.commit()

    # ---- top lists -------------------------------------------------------------
    toplists = _read(SOURCE / "toplists.json")
    for state_slug, entry in (toplists.get("states") or {}).items():
        for lst in entry.get("lists", []):
            title = lst["title"]
            year_m = re.search(r": (\d{4})", title)
            year = int(year_m.group(1)) if year_m else 2026
            slug = lst["href"].rstrip("/").split("/")[-2]
            db.session.execute(db.text(
                "INSERT INTO top_lists (state_slug, title, slug, year)"
                " VALUES (:st, :t, :s, :y)"), dict(st=state_slug, t=title,
                                                   s=slug, y=year))
            row = db.session.execute(db.text(
                "SELECT id FROM top_lists WHERE state_slug = :st AND"
                " slug = :s"), dict(st=state_slug, s=slug)).fetchone()
            list_id = row[0]
            for pos, lw in enumerate(lst.get("lawyers", [])):
                db.session.execute(db.text(
                    "INSERT INTO top_list_entries (list_id, position,"
                    " lawyer_uuid, firm_name) VALUES (:l, :p, :u, :f)"),
                    dict(l=list_id, p=pos, u=lw["uuid"],
                         f=lw.get("firm")))
    db.session.commit()

    # ---- resources ---------------------------------------------------------------
    for path in sorted((RESOURCES / "topics").glob("*.json")):
        rec = _read(path)
        db.session.execute(db.text(
            "INSERT INTO resource_topics (slug, title, blocks_json,"
            " links_json) VALUES (:s, :t, :b, :l)"),
            dict(s=path.stem, t=rec.get("title") or path.stem,
                 b=_j(rec.get("blocks") or []), l=_j(rec.get("links") or [])))
    for path in sorted((RESOURCES / "articles").glob("*.json")):
        rec = _read(path)
        topic_slug = rec.get("path", "").split("/")[0]
        db.session.execute(db.text(
            "INSERT INTO resource_articles (path, title, topic_slug,"
            " blocks_json) VALUES (:p, :t, :tp, :b)"),
            dict(p=rec.get("path"), t=rec.get("title"),
                 tp=topic_slug, b=_j(rec.get("blocks") or [])))
    db.session.commit()

    # ---- answers --------------------------------------------------------------------
    answerer_photos = _read(SOURCE / "answerer_photos.json") if \
        (SOURCE / "answerer_photos.json").exists() else {}
    for path in sorted(ANSWERS.glob("*.json")):
        rec = _read(path)
        db.session.execute(db.text(
            "INSERT INTO answers (uuid, topic_slug, state_slug, slug,"
            " question, asked_in, asked_on, last_answered_on, answer_count,"
            " answerer_name, answerer_city, answerer_firm, answerer_phone,"
            " answerer_profile_uuid, answerer_photo_path, body_json) VALUES"
            " (:u, :tp, :st, :s, :q, :ai, :ao, :la, :ac, :an, :ac2, :af,"
            "  :ap, :au, :aph, :b)"),
            dict(u=rec.get("uuid"), tp=rec.get("topic"),
                 st=rec.get("state"), s=rec.get("slug"),
                 q=rec.get("question"), ai=rec.get("asked_in"),
                 ao=rec.get("asked_on"), la=rec.get("last_answered_on"),
                 ac=rec.get("answer_count") or 1,
                 an=(rec.get("answerer") or {}).get("name"),
                 ac2=(rec.get("answerer") or {}).get("city"),
                 af=(rec.get("answerer") or {}).get("firm"),
                 ap=(rec.get("answerer") or {}).get("phone"),
                 au=(rec.get("answerer") or {}).get("profile_uuid"),
                 aph=((answerer_photos.get(path.stem) or {}).get("path")
                      or "").removeprefix("static/"),
                 b=_j(rec.get("answer_body") or [])))
    db.session.commit()

    # ---- feature articles --------------------------------------------------------------
    for path in sorted(ARTICLES.glob("*.json")):
        rec = _read(path)
        db.session.execute(db.text(
            "INSERT INTO feature_articles (state_slug, slug, title,"
            " subtitle, blocks_json, featured_json, related_json) VALUES"
            " (:st, :s, :t, :sub, :b, :f, :r)"),
            dict(st=rec.get("state"), s=rec.get("slug"), t=rec.get("title"),
                 sub=rec.get("subtitle"), b=_j(rec.get("blocks") or []),
                 f=_j(rec.get("featured_lawyers") or []),
                 r=_j(rec.get("related") or [])))
    db.session.commit()

    # ---- static pages ---------------------------------------------------------------------
    static_pages = _read(SOURCE / "static_pages.json")
    for key, rec in static_pages.items():
        db.session.execute(db.text(
            "INSERT INTO static_pages (key, title, blocks_json) VALUES"
            " (:k, :t, :b)"),
            dict(k=key, t=rec.get("title") or key,
                 b=_j(rec.get("blocks") or [])))
    db.session.commit()


def seed_benchmark_users():
    if db is None:
        return
    if db.session.execute(db.text(
            "SELECT COUNT(*) FROM users WHERE email = 'alice.j@test.com'")).scalar():
        return
    users = [
        ("alice_j", "alice.j@test.com", "Alice Johnson"),
        ("bob_c", "bob.c@test.com", "Bob Chen"),
        ("carol_d", "carol.d@test.com", "Carol Davis"),
        ("david_k", "david.k@test.com", "David Kim"),
    ]
    ids = {}
    for username, email, display in users:
        db.session.execute(db.text(
            "INSERT INTO users (email, username, display_name,"
            " password_hash, created_at) VALUES"
            " (:e, :u, :d, :p, '2026-06-14 09:30:00')"),
            dict(e=email, u=username, d=display,
                 p=BENCHMARK_PASSWORD_DIGEST))
        db.session.commit()
        row = db.session.execute(db.text(
            "SELECT id FROM users WHERE email = :e"), {"e": email}).fetchone()
        ids[username] = row[0]

    # favorites: alice 5, bob 4, carol 3, david 4 (real lawyers from the seed)
    favs = {
        "alice_j": [
            "084fb116-f66d-4a57-affa-7e99e9c5f3f6",  # Lara Herrmann (Seattle PI)
            "4e476eeb-5f5e-41ed-9f33-c4b18ed2e501",  # Preet Kode (Seattle PI)
            "11574067-209a-4624-af58-d7c9b2f4c1e9",  # Matt Dubin (Seattle PI)
            "a9777c97-4bcf-4881-a936-ef31732de5ec",  # J.P. Pendergast
            "0857df22-a408-41b1-a638-33ce10beea2d",  # Casey Arbenz
        ],
        "bob_c": [
            "9abb5e11-4e2b-4b2f-9d97-cbed2cdfa327",  # Sherri M. Anderson
            "9dfb2633-21bc-44af-9cb7-4b5575069efe",  # Todd W. Gardner
            "a7d4c917-69e1-4d19-acf6-386d53f1e258",  # Thomas B. Vertetis
            "b6022aea-4466-4872-b046-4e2fcd27df48",  # Lora L. Brown
        ],
        "carol_d": [
            "7115d57d-bedb-4359-ac77-bd640ea31c2d",  # Steven W. Fogg
            "5e9bbf78-6bf2-478a-8abc-11c4cee31b35",  # Richard Friedman
            "79eb099d-fcbf-46d6-995e-cc6e62805886",  # Karolyn Hicks
        ],
        "david_k": [
            "f7194492-5877-4d94-9dc0-97fc458ab522",  # Bradley S. Keller
            "59ba3018-4c0a-471e-bce0-2f9f447077b2",  # Felix Gavi Luna
            "0e42c2d8-16b4-46ad-82e3-5957f62897c5",  # Lisa A. Sharpe
            "02409ab8-4b52-4d58-848c-e0db288a71b1",  # Anne Bremner
        ],
    }
    day = 0
    for username, uuids in favs.items():
        for uuid in uuids:
            day += 1
            db.session.execute(db.text(
                "INSERT INTO favorites (user_id, lawyer_uuid, created_at)"
                " VALUES (:u, :l, :c)"),
                dict(u=ids[username], l=uuid,
                     c=f"2026-07-{(day % 28) + 1:02d} 10:00:00"))

    # saved searches: attorney alerts per benchmark user
    searches = [
        ("alice_j", "personal-injury-plaintiff", "washington", "seattle"),
        ("alice_j", "family-law", "illinois", "chicago"),
        ("bob_c", "criminal-defense", "georgia", "atlanta"),
        ("bob_c", "estate-planning-and-probate", "texas", "dallas"),
        ("carol_d", "immigration", "texas", "houston"),
        ("david_k", "employment-and-labor", "massachusetts", "boston"),
        ("david_k", "dui-dwi", "colorado", "denver"),
    ]
    day = 0
    for username, pa, st, ci in searches:
        day += 1
        pa_name = db.session.execute(db.text(
            "SELECT name FROM practice_areas WHERE slug = :s"),
            {"s": pa}).fetchone()
        city = db.session.execute(db.text(
            "SELECT name FROM cities WHERE slug = :c AND state_slug = :st"),
            {"c": ci, "st": st}).fetchone()
        label = f"{pa_name[0] if pa_name else pa} in {city[0] if city else ci}"
        db.session.execute(db.text(
            "INSERT INTO saved_searches (user_id, practice_slug, city_slug,"
            " state_slug, label, alerts, created_at) VALUES"
            " (:u, :p, :c, :st, :l, 1, :dt)"),
            dict(u=ids[username], p=pa, c=ci, st=st, l=label,
                 dt=f"2026-08-{(day % 28) + 1:02d} 09:00:00"))

    # inquiries: contact history for alice + bob
    inquiries = [
        ("alice_j", "084fb116-f66d-4a57-affa-7e99e9c5f3f6",
         "Alice", "Johnson", "alice.j@test.com", "206-555-0134", "Seattle",
         "WA", "I was injured in a rideshare accident on I-5 last month and "
         "would like to discuss my case."),
        ("bob_c", "9abb5e11-4e2b-4b2f-9d97-cbed2cdfa327",
         "Bob", "Chen", "bob.c@test.com", "425-555-0187", "Bellevue",
         "WA", "My mother fell at a nursing home. Can we review her care "
         "agreement and discuss next steps?"),
        ("alice_j", "11574067-209a-4624-af58-d7c9b2f4c1e9",
         "Alice", "Johnson", "alice.j@test.com", "206-555-0134", "Seattle",
         "WA", "Following up on my car accident claim - the insurance "
         "adjuster has made a first offer."),
    ]
    for i, (username, uuid, fn, ln, email, phone, city, st, message) in enumerate(inquiries):
        db.session.execute(db.text(
            "INSERT INTO inquiries (user_id, lawyer_uuid, first_name,"
            " last_name, email, phone, city, state, message, created_at)"
            " VALUES (:u, :l, :fn, :ln, :e, :p, :c, :st, :m, :dt)"),
            dict(u=ids[username], l=uuid, fn=fn, ln=ln, e=email, p=phone,
                 c=city, st=st, m=message,
                 dt=f"2026-09-{(i % 20) + 1:02d} 14:30:00"))
    db.session.commit()
