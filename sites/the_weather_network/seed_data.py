#!/usr/bin/env python3
"""Deterministic build-time seed for The Weather Network mirror.

Everything is materialized from the tracked source_data_*.json snapshots (real
data captured from thewheathernetwork.com and its public Pelmorex APIs on
2026-09-26/27 — see provenance.json). The output must be byte-identical on
every build: no wall clock, no random salt, fixed insertion order,
PYTHONHASHSEED=0 assumed.

Seed functions are gated as a whole (see run_seed / run_user_seed) so a
populated DB is never re-seeded and /reset stays byte-identical.

This module never imports app.py: the running app injects its db handle and
model classes (db / MODELS) before calling run_seed(), so `python app.py`,
`from app import app` and `python3 seed_data.py` all share one module graph.
"""
import json
import os
import re
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

db = None       # injected by app.py before run_seed() runs
MODELS = {}     # injected by app.py: {'Location': <class>, ...}

# frozen bcrypt hash of BENCHMARK_PASSWORD (verified with
# bcrypt.check_password_hash(hash, 'TestPass123!') == True) so the seed DB is
# byte-reproducible without invoking the (salted) hasher at seed time.
BENCHMARK_PASSWORD_HASH = (
    '$2b$12$SWYN0gslqt1D7QvAZwQ87.aPrk9a4fNQhJq2U2FypvTFgbXSbFlly')
BENCHMARK_PASSWORD = 'TestPass123!'

BENCHMARK_USERS = [
    {'username': 'alice_j', 'email': 'alice.j@test.com', 'display_name': 'Alice Johnson'},
    {'username': 'bob_c', 'email': 'bob.c@test.com', 'display_name': 'Bob Chen'},
    {'username': 'carol_d', 'email': 'carol.d@test.com', 'display_name': 'Carol Davis'},
    {'username': 'david_k', 'email': 'david.k@test.com', 'display_name': 'David Kim'},
]

# Pre-existing saved locations per benchmark user (location url_path slugs).
USER_SAVED = {
    'alice.j@test.com': ['toronto', 'montreal', 'ontario/london', 'blue-mountain-ski-resort'],
    'bob.c@test.com': ['vancouver', 'victoria', 'kelowna', 'banff-national-park-banff'],
    'carol.d@test.com': ['halifax', 'sydney', 'charlottetown', 'moncton'],
    'david.k@test.com': ['calgary', 'edmonton', 'regina', 'whistler-blackcomb'],
}

RISK_SCALE = {'NO': 0, 'LOW': 1, 'MODERATE': 2, 'HIGH': 3}


def _load(name):
    path = os.path.join(BASE_DIR, name)
    with open(path, encoding='utf-8') as fh:
        return json.load(fh)


def _url_path(loc):
    """URL path triple, e.g. ca/ontario/toronto (country code + prov + slug)."""
    parts = loc['friendly_url'].split('/')       # canada/ontario/toronto
    parts[0] = loc['country_code'].lower()
    return '/'.join(parts)


def _num(v):
    return None if v is None else float(v)


def run_seed():
    """Materialize the whole content catalog. Gated: no-op on a populated DB."""
    if db is None or not MODELS:
        raise RuntimeError('seed_data.run_seed() called before app.py injected db/MODELS')
    Location = MODELS['Location']
    Observation = MODELS['Observation']
    HourlyForecast = MODELS['HourlyForecast']
    DailyForecast = MODELS['DailyForecast']
    MonthlyAverage = MODELS['MonthlyAverage']
    WellBeing = MODELS['WellBeing']
    Author = MODELS['Author']
    Article = MODELS['Article']
    Video = MODELS['Video']
    Alert = MODELS['Alert']

    if db.session.query(Location).count() > 0:
        return

    site = _load('source_data_site.json')
    locs = _load('source_data_locations.json')['locations']
    news = _load('source_data_news.json')['articles']
    vids = _load('source_data_videos.json')['videos']
    alerts = _load('source_data_alerts.json')['alerts']

    popular_slugs = set(site.get('city_popular') or []) | set(site.get('home_popular') or [])

    # ---- locations -------------------------------------------------------
    loc_map = {}
    seen_paths = set()
    for loc in locs:
        path = _url_path(loc)
        if (loc['channel'], path) in seen_paths:
            continue        # upstream serves two records for one URL; keep the first
        seen_paths.add((loc['channel'], path))
        rec = Location(
            code=loc['code'], channel=loc['channel'], name=loc['name'],
            prov=loc['prov'], prov_code=loc['prov_code'],
            country=loc['country'], country_code=loc['country_code'],
            friendly_url=loc['friendly_url'], url_path=path,
            lat=loc['lat'], lng=loc['lng'],
            is_popular=any(loc['friendly_url'].endswith(f'/{s}') for s in popular_slugs),
        )
        db.session.add(rec)
        loc_map[loc['code']] = rec
    db.session.flush()

    # ---- weather per location ---------------------------------------------
    for loc in locs:
        rec = loc_map.get(loc['code'])
        if rec is None:
            continue
        o = loc.get('obs')
        if o:
            db.session.add(Observation(
                loc_id=rec.id, time_local=o[0], code=o[1], icon=o[2] or 1,
                text=o[3] or '', temp=_num(o[4]), feels=_num(o[5]), dew=_num(o[6]),
                wind_dir=o[7] or '', wind_speed=_num(o[8]), wind_gust=_num(o[9]),
                wind_deg=o[10], rh=o[11], pressure=_num(o[12]),
                pressure_trend=o[13], visibility=_num(o[14]), ceiling=o[15],
            ))
        for h in loc.get('hourly') or []:
            db.session.add(HourlyForecast(
                loc_id=rec.id, time_local=h[0], icon=h[1] or 1, text=h[2] or '',
                temp=_num(h[3]), feels=_num(h[4]), wind_dir=h[5] or '',
                wind_speed=_num(h[6]), wind_gust=_num(h[7]), rh=h[8], pop=h[9],
                rain=_num(h[10]), rain_range=h[11] or '', snow=_num(h[12]),
                snow_range=h[13] or '', cloud=h[14],
            ))
        for d in loc.get('longterm') or []:
            day_p, night_p = d[1], d[2]
            db.session.add(DailyForecast(
                loc_id=rec.id, date_local=d[0],
                day_icon=(day_p[0] if day_p else 1) or 1,
                day_text=(day_p[1] if day_p else '') or '',
                day_temp=_num(day_p[2] if day_p else None),
                day_feels=_num(day_p[3] if day_p else None),
                day_wind_dir=(day_p[4] if day_p else '') or '',
                day_wind_speed=_num(day_p[5] if day_p else None),
                day_wind_gust=_num(day_p[6] if day_p else None),
                day_rh=day_p[7] if day_p else None,
                day_pop=day_p[8] if day_p else None,
                day_rain=_num(day_p[9] if day_p else None),
                day_rain_range=(day_p[10] if day_p else '') or '',
                day_snow=_num(day_p[11] if day_p else None),
                day_snow_range=(day_p[12] if day_p else '') or '',
                night_icon=(night_p[0] if night_p else 1) or 1,
                night_text=(night_p[1] if night_p else '') or '',
                night_temp=_num(night_p[2] if night_p else None),
                night_feels=_num(night_p[3] if night_p else None),
                night_wind_dir=(night_p[4] if night_p else '') or '',
                night_wind_speed=_num(night_p[5] if night_p else None),
                night_wind_gust=_num(night_p[6] if night_p else None),
                night_rh=night_p[7] if night_p else None,
                night_pop=night_p[8] if night_p else None,
                night_rain=_num(night_p[9] if night_p else None),
                night_rain_range=(night_p[10] if night_p else '') or '',
                night_snow=_num(night_p[11] if night_p else None),
                night_snow_range=(night_p[12] if night_p else '') or '',
                pop=d[3], rain=_num(d[4]), rain_range=d[5] or '',
                snow=_num(d[6]), snow_range=d[7] or '',
                sun_hours=_num(d[8]), day_type=d[9] or '',
            ))
        for month_key, hm in sorted((loc.get('hist') or {}).items()):
            for row in (hm or {}).get('days') or []:
                db.session.add(MonthlyAverage(
                    loc_id=rec.id, month_key=month_key, day=row[0],
                    tmax=_num(row[1]), tmin=_num(row[2]), precip_freq=row[3],
                ))

        # wellbeing tiles (cities carry the full surface)
        aq = loc.get('airquality')
        if aq:
            db.session.add(WellBeing(loc_id=rec.id, kind='airquality',
                                     value=aq.get('value'), label=aq.get('text') or ''))
        uv = loc.get('uv')
        if uv:
            db.session.add(WellBeing(loc_id=rec.id, kind='uv',
                                     value=uv.get('value'), label=uv.get('text') or ''))
        atrgt = loc.get('atrgt') or {}
        if atrgt.get('pollen'):
            db.session.add(WellBeing(loc_id=rec.id, kind='pollen', value=None,
                                     label=atrgt['pollen'].strip().title()))
        health = loc.get('health') or {}
        if health:
            best = 0
            for kind in ('migraine', 'arthritis', 'respiratory'):
                rows = health.get(kind) or []
                if rows:
                    risk = (rows[0] or {}).get('risk') or 'NO'
                    best = max(best, RISK_SCALE.get(risk, 0))
            label = {0: 'Low', 1: 'Low', 2: 'Moderate', 3: 'High'}[best]
            db.session.add(WellBeing(loc_id=rec.id, kind='health', value=None, label=label))
        bug = loc.get('bug') or {}
        bfc = bug.get('bugForecast') or []
        if bfc:
            species = (bfc[0] or {}).get('species') or {}
            worst, worst_label = 0, 'Low'
            for sp in species.values():
                act = (sp or {}).get('activity') or {}
                v = act.get('value') or 0
                if v > worst:
                    worst, worst_label = v, act.get('text') or 'Low'
            db.session.add(WellBeing(loc_id=rec.id, kind='bugs',
                                     value=float(worst), label=worst_label))

    # ---- authors & articles ------------------------------------------------
    authors = {}
    for a in news:
        au = a.get('author') or {}
        slug = au.get('slug') or re.sub(
            r'[^a-z0-9-]', '', (au.get('name') or 'staff').lower().replace(' ', '-')) or 'staff'
        if slug not in authors:
            db.session.add(Author(
                name=au.get('name') or 'The Weather Network',
                title=au.get('title') or '', slug=slug,
                avatar=f"authors/{slug}.webp" if au.get('avatar') else '',
            ))
            authors[slug] = True
    db.session.flush()
    author_ids = {a.slug: a.id for a in db.session.query(Author).all()}

    for a in news:
        au = a.get('author') or {}
        slug = au.get('slug') or re.sub(
            r'[^a-z0-9-]', '', (au.get('name') or 'staff').lower().replace(' ', '-')) or 'staff'
        thumb = (a.get('thumbnail') or {}).get('url') or ''
        db.session.add(Article(
            path=a['path'], slug=a['slug'], headline=a['headline'],
            summary=a.get('summary') or '', body=a.get('body') or '',
            category_key=a['category_path'].split('/')[0],
            subcategory_key=a['category_path'].split('/')[1],
            author_id=author_ids.get(slug), thumb=f"articles/{a['slug']}.webp" if thumb else '',
            effective_date=a.get('effective_date') or '',
            created_at=a.get('created_at') or '',
            updated_at=a.get('updated_at') or '',
            keywords=json.dumps(a.get('keywords') or [], ensure_ascii=False),
            embedded_videos=json.dumps(a.get('embedded_videos') or []),
        ))

    # ---- videos --------------------------------------------------------------
    for v in vids:
        db.session.add(Video(
            mediaid=v['mediaid'], title=v.get('title') or '',
            description=v.get('description') or '',
            duration=v.get('duration') or 0, pubdate=v.get('pubdate') or 0,
            playlists=json.dumps(v.get('playlists') or []),
        ))

    # ---- alerts ----------------------------------------------------------------
    for al in alerts:
        db.session.add(Alert(
            placecode=al['placecode'], location_name=al.get('location') or '',
            region=al.get('region') or '', name=al.get('name') or '',
            condition=al.get('condition') or '', type=al.get('type') or '',
            priority=al.get('priority') or '', status=al.get('status') or 'active',
            treatment=al.get('treatment') or 1,
            source_text=(al.get('source') or {}).get('text') or '',
            issued=al.get('issued') or '', expires=al.get('expires') or '',
            updated=al.get('updated') or '',
            message=al.get('message') or '', recommended=al.get('recommended') or '',
            related=json.dumps(al.get('related') or [], ensure_ascii=False),
        ))

    db.session.commit()


def run_user_seed():
    """Benchmark users + their saved locations. Gated as a whole."""
    if db is None or not MODELS:
        raise RuntimeError('seed_data.run_user_seed() called before app.py injected db/MODELS')
    Location = MODELS['Location']
    SavedLocation = MODELS['SavedLocation']
    User = MODELS['User']

    if db.session.query(User).filter_by(email='alice.j@test.com').first():
        return

    for spec in BENCHMARK_USERS:
        user = User(username=spec['username'], email=spec['email'],
                    display_name=spec['display_name'], unit='metric',
                    created_at=datetime(2026, 1, 15))
        user.password_hash = BENCHMARK_PASSWORD_HASH
        db.session.add(user)
    db.session.flush()

    for i, spec in enumerate(BENCHMARK_USERS):
        user = db.session.query(User).filter_by(email=spec['email']).first()
        day = 15 + i
        for j, slug in enumerate(USER_SAVED.get(spec['email'], [])):
            loc = db.session.query(Location).filter(
                Location.url_path.endswith(f'/{slug}')).first()
            if loc:
                db.session.add(SavedLocation(
                    user_id=user.id, loc_id=loc.id,
                    created_at=datetime(2026, 9, day, 9 + j)))
    db.session.commit()


if __name__ == '__main__':
    # Standalone deterministic rebuild: wipe the DB file, let the app module's
    # bootstrap (imported fresh below) seed it from the source snapshots, and
    # publish the result as the reset seed (instance_seed/). The DB file is
    # deleted (not just drop_all(), which leaves freelist pages and shifts
    # the byte layout) so every build starts from a fresh file and the seed
    # is byte-identical (Dockerfile contract: rm -rf instance instance_seed +
    # PYTHONHASHSEED=0 python3 seed_data.py).
    import shutil
    import sys
    sys.path.insert(0, BASE_DIR)
    os.makedirs(os.path.join(BASE_DIR, 'instance'), exist_ok=True)
    for suffix in ('', '-journal', '-wal', '-shm'):
        p = os.path.join(BASE_DIR, 'instance', f'the_weather_network.db{suffix}')
        if os.path.exists(p):
            os.remove(p)
    from app import app  # noqa: E402,F401 — module-level bootstrap seeds the fresh DB
    seed_dir = os.path.join(BASE_DIR, 'instance_seed')
    os.makedirs(seed_dir, exist_ok=True)
    shutil.copyfile(os.path.join(BASE_DIR, 'instance', 'the_weather_network.db'),
                    os.path.join(seed_dir, 'the_weather_network.db'))
    print('seed complete; copied instance/the_weather_network.db to instance_seed/')
