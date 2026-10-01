#!/usr/bin/env python3
"""Deterministic build-time seeder for the UPS mirror.

Reads the tracked source_data/ snapshots (captured from www.ups.com on
2026-09-28) and materializes the SQLite database. Every seed function
early-returns when its table is already populated, so re-running the boot
path is a no-op and /reset/ups stays byte-identical. Run with
PYTHONHASHSEED=0 for byte-reproducible builds.
"""
from __future__ import annotations

import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def _load(name):
    with open(os.path.join(BASE_DIR, 'source_data', name), encoding='utf-8') as fh:
        return json.load(fh)


SERVICE_CODE_OF = {
    'UPS Next Day Air\u00ae Early': '1DM',
    'UPS Next Day Air\u00ae': '1DA',
    'UPS Next Day Air Saver\u00ae': '1DP',
    'UPS 2nd Day Air A.M.\u00ae': '2DM',
    'UPS 2nd Day Air\u00ae': '2DA',
    'UPS 3 Day Select\u00ae': '3DS',
    'UPS Ground': 'GND',
}


def seed_services(db):
    from app import Service
    if Service.query.count() > 0:
        return
    data = _load('services.json')
    for i, s in enumerate(data['services']):
        db.session.add(Service(
            code=s['code'], name=s['name'], bucket=s['bucket'],
            tagline=s['tagline'], commitment=s['commitment'],
            guaranteed=s['guaranteed'], days=s['days'],
            max_weight_lb=s['max_weight_lb'], max_length_in=s['max_length_in'],
            saturday_delivery=s['saturday_delivery'],
            latest_pickup=s['latest_pickup'], schedule_by=s['schedule_by'],
            delivered_by_default=s['delivered_by_default'], sort=i))
    db.session.commit()


LANE_COORDS = {
    'nyc_chi': [(40.7537, -73.9992), (41.8858, -87.6429)],
    'nyc_sf': [(40.7537, -73.9992), (37.7898, -122.3942)],
    'chi_atl': [(41.8858, -87.6429), (33.7867, -84.3868)],
    'sf_sea': [(37.7898, -122.3942), (47.6097, -122.3332)],
    'mia_nyc': [(25.7743, -80.1937), (40.7537, -73.9992)],
    'aus_cin': [(30.4021, -97.7200), (39.1031, -84.5099)],
    'den_chi': [(39.7527, -104.9996), (41.8858, -87.6429)],
    'bos_phl': [(42.3555, -71.0530), (39.9517, -75.1638)],
}


def seed_rates(db):
    from app import Lane, RateQuote
    if RateQuote.query.count() > 0:
        return
    data = _load('rates.json')
    for lane_id, lane in data['lanes'].items():
        (olat, olng), (dlat, dlng) = LANE_COORDS.get(
            lane_id, [(0, 0), (0, 0)])
        db.session.add(Lane(lane_id=lane_id,
                           origin_city=lane['origin_city'],
                           origin_zip=lane['origin_zip'],
                           dest_city=lane['dest_city'],
                           dest_zip=lane['dest_zip'],
                           origin_lat=olat, origin_lng=olng,
                           dest_lat=dlat, dest_lng=dlng))
        for q in lane['quotes']:
            weight = q['weight_lb']
            residential = q['residential']
            bmap = {}
            for b in q.get('breakdowns', []):
                code = SERVICE_CODE_OF.get(b['service'])
                if code:
                    bmap[code] = b
            for svc in q['services']:
                code = SERVICE_CODE_OF.get(svc['service'])
                if not code:
                    continue
                b = bmap.get(code, {})
                db.session.add(RateQuote(
                    lane_id=lane_id, weight_lb=weight, residential=residential,
                    service_code=code, service_name=svc['service'],
                    price_usd=svc['price_usd'],
                    days_in_transit=svc['days_in_transit'],
                    delivered_by=svc['delivered_by'],
                    guaranteed=svc['guaranteed'],
                    latest_pickup=svc['latest_pickup'],
                    schedule_by=svc['schedule_by'],
                    billable_weight_lb=svc['billable_weight_lb'],
                    transportation_usd=b.get('transportation_usd'),
                    das_usd=b.get('delivery_area_surcharge_usd'),
                    fuel_usd=b.get('fuel_surcharge_usd')))
    db.session.commit()


def seed_fees(db):
    from app import Fee
    if Fee.query.count() > 0:
        return
    data = _load('fees.json')
    for category, key in [('pickup_options', 'pickup_options'),
                          ('saturday_options', 'saturday_options'),
                          ('delivery_options', 'delivery_options'),
                          ('other_services', 'other_services')]:
        for f in data[key]:
            db.session.add(Fee(category=category, name=f['name'],
                               fee=f['fee'], per=f.get('per', ''),
                               description=f.get('description', '')))
    db.session.commit()


def seed_locations(db):
    from app import Location, ZipGeocode
    if Location.query.count() > 0:
        return
    data = _load('locations.json')
    for loc in data['locations']:
        db.session.add(Location(
            location_id=loc['location_id'], name=loc['name'],
            addr1=loc['addr1'], city=loc['city'], state=loc['state'],
            zip=loc['zip'], phone=loc.get('phone'),
            lat=loc['lat'], lng=loc['lng'],
            type_code=loc['type_code'], type=loc['type'],
            latest_air_dropoff=loc.get('latest_air_dropoff') or '',
            latest_ground_dropoff=loc.get('latest_ground_dropoff') or '',
            comments=loc.get('comments') or '',
            special_instructions=loc.get('special_instructions') or '',
            featured_rank=loc.get('featured_rank'),
            service_offerings=json.dumps(loc.get('service_offerings', [])),
            hours=json.dumps(loc.get('hours', []))))
    # origin geocodes captured per seeded search zip (geocode API responses)
    geo = data.get('search_geocodes') or {}
    for zc, g in geo.items():
        db.session.add(ZipGeocode(zip=zc, lat=g['lat'], lng=g['lng'],
                                  formatted=g.get('formatted', '')))
    db.session.commit()


def seed_articles(db):
    from app import ContentPage, SupportArticle
    if SupportArticle.query.count() > 0:
        return
    data = _load('articles.json')
    for a in data['articles']:
        db.session.add(SupportArticle(
            key=a['key'], category=a['category'], title=a['title'],
            body=a['body'], upstream_url=a['upstream_url']))
    pages = _load('content_pages.json')['pages']
    for key, p in pages.items():
        db.session.add(ContentPage(
            key=key, title=p['title'], body=p['body'],
            upstream_url=p['upstream_url']))
    db.session.commit()


def seed_status_meanings(db):
    from app import StatusMeaning
    if StatusMeaning.query.count() > 0:
        return
    data = _load('tracking_ui.json')
    for status, meaning in data['status_meanings'].items():
        db.session.add(StatusMeaning(status=status, meaning=meaning))
    db.session.commit()


def seed_users(db):
    from app import BENCHMARK_PASSWORD_HASH, User
    if User.query.filter_by(email='alice.j@test.com').first():
        return
    data = _load('shipments.json')
    for u in data['users']:
        addr = u['address']
        db.session.add(User(
            email=u['email'], name=u['name'],
            password_hash=BENCHMARK_PASSWORD_HASH,
            is_business=u['is_business'],
            account_number=(u.get('account') or {}).get('number'),
            account_plan=(u.get('account') or {}).get('plan'),
            address_line1=addr['line1'], city=addr['city'],
            state=addr['state'], zip=addr['zip']))
    db.session.commit()


def seed_shipments(db):
    from app import Shipment, TrackingEvent, User
    if Shipment.query.count() > 0:
        return
    data = _load('shipments.json')
    users = {u['email']: u for u in data['users']}
    for s in data['shipments']:
        owner = None
        if s.get('owner_email'):
            owner = User.query.filter_by(email=s['owner_email']).first()
        shipment = Shipment(
            tracking_number=s['tracking_number'],
            user_id=owner.id if owner else None,
            direction=s.get('direction', 'inbound'),
            service_code=s['service'],
            shipper_name=s.get('shipper_name'),
            from_city=s.get('from_city'), from_state=s.get('from_state'),
            to_name=s.get('to_name'),
            to_city=s.get('to_city'), to_state=s.get('to_state'),
            to_zip=s.get('to_zip'),
            weight_lb=s.get('weight_lb'), packages=s.get('packages', 1),
            signature=s.get('signature'),
            scheduled_delivery=s.get('scheduled_delivery'),
            status=s['status'],
            delivered_on=s.get('delivered_on'),
            delivered_time=s.get('delivered_time'),
            signed_by=s.get('signed_by'), left_at=s.get('left_at'),
            hold_location_id=s.get('hold_location_id'),
            hold_by=s.get('hold_by'),
            is_international=s.get('is_international', False),
            declared_value=s.get('declared_value'),
            multi_package=s.get('multi_package', False),
            exception_note=s.get('exception_note'),
        )
        db.session.add(shipment)
        db.session.flush()
        seq = 0
        for e in s.get('events', []):
            seq += 1
            db.session.add(TrackingEvent(
                shipment_id=shipment.id, seq=seq, day=e['day'], time=e['time'],
                status=e['status'], location=e['location'],
                description=e.get('description', '')))
        for pk in s.get('packages_detail', []):
            for e in pk.get('events', []):
                seq += 1
                db.session.add(TrackingEvent(
                    shipment_id=shipment.id, seq=seq, day=e['day'], time=e['time'],
                    status=e['status'], location=e['location'],
                    description=e.get('description', ''), package_n=pk['n']))
    db.session.commit()


def seed_alerts(db):
    from app import ServiceAlert
    if ServiceAlert.query.count() > 0:
        return
    data = _load('shipments.json')
    for a in data.get('service_alerts', []):
        db.session.add(ServiceAlert(
            alert_id=a['id'], title=a['title'], body=a['body'], link=a['link']))
    db.session.commit()


def seed_all():
    """Populate every table (each helper early-returns when already seeded)."""
    from app import app, db
    with app.app_context():
        db.create_all()
        seed_services(db)
        seed_rates(db)
        seed_fees(db)
        seed_locations(db)
        seed_articles(db)
        seed_status_meanings(db)
        seed_users(db)
        seed_shipments(db)
        seed_alerts(db)


if __name__ == '__main__':
    os.environ.setdefault('WEBSYN_SKIP_BOOTSTRAP', '1')
    seed_all()
    from app import app
    with app.app_context():
        from app import (Claim, Location, PickupRequest, RateQuote, Service,
                         Shipment, SupportArticle, TrackingEvent, User)
        print('services:', Service.query.count())
        print('rate_quotes:', RateQuote.query.count())
        print('locations:', Location.query.count())
        print('shipments:', Shipment.query.count())
        print('tracking_events:', TrackingEvent.query.count())
        print('users:', User.query.count())
        print('articles:', SupportArticle.query.count())
