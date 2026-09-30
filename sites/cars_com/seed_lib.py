#!/usr/bin/env python3
"""Deterministic build-time seeder for the cars_com mirror (see seed_data.py)."""
import json
import os
import re

from markupsafe import Markup

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SOURCE = os.path.join(BASE_DIR, 'source_data')


def _load(name):
    with open(os.path.join(SOURCE, name), encoding='utf-8') as f:
        return json.load(f)


def slugify(text):
    s = re.sub(r"[^A-Za-z0-9]+", "_", (text or "").strip())
    return s.strip("_").lower()


def seed_all(db, bcrypt, app):
    from app import (Listing, Dealer, ModelPage, ComparePair, ValuationVehicle)

    listings = _load('listings.json')
    dealers = _load('dealers.json')
    models = _load('models.json')
    compares = _load('compares.json')
    valuation = _load('valuation.json')

    # ---- dealers first (listings reference them) --------------------------
    dealer_ids = {}
    for row in dealers:
        d = Dealer(
            id=row.get('dealer_id') or _stable_int(row['slug']),
            slug=row['slug'],
            name=row['name'],
            address=row.get('address') or row.get('street'),
            city=row.get('city'),
            state=row.get('state'),
            zip=row.get('zip'),
            phone_new=(row.get('phones') or {}).get('new'),
            phone_used=(row.get('phones') or {}).get('used'),
            phone_service=(row.get('phones') or {}).get('service'),
            rating=row.get('rating'),
            review_count=row.get('review_count'),
            hours=json.dumps(row.get('hours', [])),
            about=row.get('about'),
            highlights=json.dumps(row.get('highlights', [])),
            reviews=json.dumps(row.get('reviews') or row.get('detail_reviews', [])),
            sales_team=json.dumps(row.get('sales_team', [])),
            service_menu=json.dumps(row.get('service_menu', [])),
            distance_miles=row.get('distance_miles'),
            makes_carried=json.dumps(row.get('makes_carried', [])),
            primary_make=row.get('primary_make'),
            awards=row.get('awards'),
        )
        db.session.add(d)
        dealer_ids[row['name']] = d.id
    db.session.flush()

    # ---- listings ----------------------------------------------------------
    for row in listings:
        seller = row.get('dealer_name') or row.get('seller_name')
        dealer_id = dealer_ids.get(seller)
        photos = row.get('_local_photos') or [p for p in (row.get('photos') or [])][:8]
        l = Listing(
            id=row['listing_id'],
            stock_type=row.get('stock_type') or 'Used',
            year=row.get('year') or 0,
            make=row.get('make') or '',
            make_slug=row.get('make_slug') or slugify(row.get('make')),
            model=row.get('model') or '',
            model_slug=row.get('model_slug') or slugify(row.get('model')),
            trim=row.get('trim'),
            price=row.get('price') or 0,
            mileage=row.get('mileage') or 0,
            monthly_est=row.get('monthly_est'),
            monthly_apr=row.get('monthly_apr'),
            monthly_months=row.get('monthly_months'),
            body_style=row.get('body_style'),
            body_style_slug=row.get('body_style_slug'),
            drivetrain=row.get('drivetrain'),
            drivetrain_slug=row.get('drivetrain_slug'),
            fuel_type=row.get('fuel_type'),
            fuel_slug=row.get('fuel_slug'),
            transmission=row.get('transmission'),
            transmission_slug=row.get('transmission_slug'),
            cylinders=row.get('cylinders'),
            exterior_color=row.get('exterior_color'),
            exterior_color_slug=row.get('exterior_color_slug'),
            interior_color=row.get('interior_color'),
            engine_desc=row.get('engine_desc'),
            mpg=row.get('mpg'),
            vin=row.get('vin'),
            stock_number=row.get('stock_number'),
            deal_badge=row.get('deal_badge'),
            deal_badge_desc=row.get('deal_badge_desc'),
            good_deal_low=row.get('good_deal_low'),
            good_deal_high=row.get('good_deal_high'),
            dealer_id=dealer_id,
            seller_name=seller,
            seller_type=row.get('seller_type', 'dealership'),
            city=row.get('city'),
            state=row.get('state'),
            distance_miles=row.get('distance_miles'),
            photos=json.dumps(photos),
            total_photos=row.get('total_photos') or len(photos),
            features=json.dumps(row.get('features', {})),
            seller_notes=row.get('seller_notes'),
            price_breakdown=json.dumps(row.get('price_breakdown', [])),
            price_history=json.dumps(row.get('price_history', [])),
            history=json.dumps(row.get('history')) if row.get('history') else None,
            cpo_program=row.get('cpo_program'),
            consumer_recommend_pct=row.get('consumer_recommend_pct'),
            consumer_rating=row.get('consumer_rating'),
            consumer_review_count=row.get('consumer_review_count'),
            consumer_categories=json.dumps(row.get('consumer_categories'))
                if row.get('consumer_categories') else None,
            consumer_reviews=json.dumps(row.get('consumer_reviews', [])),
            est_apr=row.get('apr'),
            sales_tax_pct=row.get('sales_tax_pct'),
            has_detail=bool(row.get('has_detail')),
            listed_at='2026-10-01',
        )
        db.session.add(l)
    db.session.flush()

    # ---- research model pages ----------------------------------------------
    for row in models:
        p = ModelPage(
            make=row.get('make') or '',
            make_slug=slugify(row.get('make')),
            model=row.get('model') or '',
            model_slug=row.get('model_slug') or slugify(row.get('model')),
            year=row.get('year') or 0,
            slug=row['slug'],
            body_style=row.get('body_style'),
            safety_rating=row.get('safety_rating'),
            safety_review_count=row.get('safety_review_count'),
            starting_price=row.get('starting_price'),
            trims=json.dumps(row.get('trims', [])),
            notable_features=json.dumps(row.get('notable_features', [])),
            good_points=json.dumps(row.get('good_points', [])),
            bad_points=json.dumps(row.get('bad_points', [])),
            expert_take=row.get('expert_take'),
            expert_author=row.get('expert_author'),
            consumer_recommend_pct=row.get('consumer_recommend_pct'),
            consumer_rating=row.get('consumer_rating'),
            consumer_review_count=row.get('consumer_review_count'),
            consumer_categories=json.dumps(row.get('consumer_categories'))
                if row.get('consumer_categories') else None,
            consumer_reviews=json.dumps(row.get('consumer_reviews', [])),
            photos=json.dumps(row.get('_local_photos') or []),
        )
        db.session.add(p)

    # ---- compare pairs ------------------------------------------------------
    # A compare column's model page is matched by (year, make+model) so the
    # pair links to the site's own research page for that model; the
    # captured column (year/name/price/trims) stays verbatim in `columns`.
    page_by_key = {}
    for m in models:
        page_by_key[(m.get('year'), f"{m.get('make')} {m.get('model')}")] = m['slug']
        page_by_key.setdefault((None, f"{m.get('make')} {m.get('model')}"), m['slug'])
    for row in compares:
        cols = row.get('columns', [])
        if len(cols) < 2:
            continue
        slugs = []
        for c in cols[:2]:
            slug = page_by_key.get((c.get('year'), c.get('name'))) or \
                page_by_key.get((None, c.get('name')))
            if not slug:
                parts = str(c.get('name') or '').split(' ', 1)
                slug = f"{slugify(parts[0])}-{slugify(parts[1]) if len(parts) > 1 else ''}".strip('-')
                slug = f"{slug}-{c.get('year')}"
            slugs.append(slug)
        pair = ComparePair(
            slug_a=slugs[0], slug_b=slugs[1],
            slug=row['slug'],
            spec_rows=json.dumps(row.get('rows', {})),
            columns=json.dumps([{k: c.get(k) for k in ('year', 'name', 'price', 'trims')}
                                for c in cols[:2]]),
        )
        db.session.add(pair)
    db.session.flush()

    # ---- valuation vehicles -------------------------------------------------
    for row in valuation.get('vehicles', []):
        initial = row.get('initial_estimate') or [0, 0]
        adjusted = row.get('adjusted_estimate') or initial
        key = f"{row['year']}|{row['make']}|{row['model']}|{row['trim']}"
        v = ValuationVehicle(
            year=row['year'], make=row['make'], model=row['model'], trim=row['trim'],
            key=key,
            options=json.dumps(row.get('options', [])),
            standard_features=json.dumps(row.get('standard_features') or []),
            exterior_color=row.get('color'),
            initial_low=initial[0], initial_high=initial[1],
            est_low=adjusted[0], est_high=adjusted[1],
            est_mileage=row.get('mileage', 60000),
        )
        db.session.add(v)

    db.session.commit()


def seed_benchmark(db, bcrypt, app):
    from app import (User, SavedCar, SavedSearch, Listing,
                     BENCHMARK_PASSWORD_HASH, SEED_STAMP)

    fixtures = _load('benchmark_users.json')
    hash_ = BENCHMARK_PASSWORD_HASH
    users = {}
    for row in fixtures['users']:
        u = User(email=row['email'], display_name=row['display'],
                 password_hash=hash_, is_benchmark=True)
        db.session.add(u)
        users[row['display'].split()[0].lower()] = u
    db.session.flush()

    # Saved cars + saved searches, deterministic picks over the real corpus.
    all_listings = [l.id for l in Listing.query.order_by(Listing.id).all()]
    honda_civics = [l.id for l in Listing.query.filter_by(model_slug='honda-civic').all()]
    rav4s = [l.id for l in Listing.query.filter_by(model_slug='toyota-rav4').all()]
    f150s = [l.id for l in Listing.query.filter_by(model_slug='ford-f_150').all()]
    tesla = [l.id for l in Listing.query.filter_by(model_slug='tesla-model_3').all()]
    cheap = [l.id for l in Listing.query.filter(Listing.price < 20000)
             .order_by(Listing.price).all()]
    suvs = [l.id for l in Listing.query.filter_by(body_style_slug='suv').all()]

    def pick(seq, n, offset=0):
        return [seq[i % len(seq)] for i in range(offset, offset + n)] if seq else []

    plan = {
        'alice': {'saved': pick(honda_civics, 2) + pick(rav4s, 1),
                  'searches': [('Used Honda Civics under $25k',
                                '/shopping/results/?stock_type=used&models[]=honda-civic&list_price_max=25000',
                                'daily')]},
        'bob': {'saved': pick(f150s, 2) + pick(tesla, 1),
                'searches': [('New Toyota RAV4 near Seattle',
                             '/shopping/results/?stock_type=new&models[]=toyota-rav4',
                             'weekly')]},
        'carol': {'saved': pick(cheap, 1) + pick(suvs, 1),
                  'searches': [('Cheap used cars under $15k',
                               '/shopping/results/?stock_type=used&list_price_max=15000',
                               'daily')]},
        'dana': {'saved': pick(suvs, 2),
                 'searches': [('Great Deal SUVs',
                               '/shopping/results/?deal_ratings=great&body_style_slugs=suv',
                               'daily'),
                              ('Electric cars in stock',
                               '/shopping/results/?fuel_slugs=electric',
                               'weekly')]},
    }
    for name, u in users.items():
        spec = plan.get(name, {})
        for lid in spec.get('saved', []):
            db.session.add(SavedCar(user_id=u.id, listing_id=lid, saved_at=SEED_STAMP))
        for sname, qs, freq in spec.get('searches', []):
            db.session.add(SavedSearch(user_id=u.id, name=sname, query_string=qs,
                                       alert_frequency=freq, created_at=SEED_STAMP))
    db.session.commit()


def _stable_int(slug):
    """Deterministic positive int id from a slug (dealers without an upstream id)."""
    h = 0
    for ch in slug:
        h = (h * 31 + ord(ch)) & 0x7FFFFFFF
    return 900000000 + (h % 90000000)
