#!/usr/bin/env python3
"""Deterministic seed builder for the disney mirror.

Everything materialized here comes from the tracked source_data/*.json
snapshots (captured 2026-09-29, see provenance.json) in a fixed, sorted
order; the four benchmark accounts and their favorites / orders are
authored fixtures following the u_s_customs / zara / ziprecruiter
precedent: every movie, show, park entity, product and ice event they
reference is a real captured upstream row, and every timestamp is a
frozen constant so the SQLite output is byte-reproducible
(PYTHONHASHSEED=0).
"""
import hashlib
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
SOURCE = os.path.join(HERE, 'source_data')

BENCHMARK_HASH = (
    '$2b$12$qSds4Mr9Wo7VwPWLhompEer88SuxxXFDp31P9etY6v7nfRctNO7B.')
MIRROR_TS = '2026-09-29'


def _load(name):
    with open(os.path.join(SOURCE, name), encoding='utf-8') as f:
        return json.load(f)


_ASSET_MAP = None


def _asset_map():
    """url -> local filename, resolved from the tracked inventory so the
    saved extension always describes the real bytes (upstream CDNs
    occasionally serve JPEG bytes at .png paths)."""
    global _ASSET_MAP
    if _ASSET_MAP is None:
        _ASSET_MAP = {}
        path = os.path.join(HERE, 'asset_inventory.json')
        if os.path.exists(path):
            with open(path, encoding='utf-8') as f:
                for row in json.load(f).get('assets', []):
                    _ASSET_MAP[row.get('source_url')] = \
                        row['path'].split('/')[-1]
    return _ASSET_MAP


def asset_name(url):
    """Deterministic local filename for an upstream image URL."""
    if not url:
        return None
    mapped = _asset_map().get(url)
    if mapped:
        return mapped
    digest = hashlib.sha256(url.encode('utf-8')).hexdigest()[:20]
    path = url.split('?')[0]
    ext = os.path.splitext(path)[1].lower() or '.jpg'
    if ext not in ('.jpg', '.jpeg', '.png', '.webp', '.gif'):
        ext = '.jpg'
    return digest + ext


def _pipe(values):
    if isinstance(values, str):
        values = [v.strip() for v in values.split(',') if v.strip()]
    return '|'.join(v for v in (values or []) if v)


def _plain_text(fragment):
    """Rendered text of a captured HTML fragment (the hero banner lines
    like '<p><span>AVAILABLE NOW</span></p>'), with tags stripped."""
    if not fragment:
        return None
    text = re.sub(r'<[^>]+>', ' ', fragment)
    text = text.replace('\xa0', ' ')
    return re.sub(r'\s+', ' ', text).strip() or None


def _release_sort(release_date, release_sort=None):
    if release_sort:
        return release_sort
    months = ['January', 'February', 'March', 'April', 'May', 'June',
              'July', 'August', 'September', 'October', 'November',
              'December']
    m = re.search(r'([A-Za-z]+)\s+(\d{1,2}),?\s+(\d{4})', release_date or '')
    if m and m.group(1) in months:
        return f"{m.group(3)}-{months.index(m.group(1)) + 1:02d}-{int(m.group(2)):02d}"
    m = re.search(r'(\d{4})', release_date or '')
    return f"{m.group(1)}-12-31" if m else ''


def seed_all(db):
    from app import (Game, HomeTile, IceEvent, LiveShow, Movie, ParkEntity,
                     Product, Show)

    # ------------------------------------------------------------- home tiles
    for tile in _load('home.json'):
        db.session.add(HomeTile(
            eyebrow=tile.get('eyebrow'), title=tile.get('title'),
            description=tile.get('description'),
            cta_label=tile.get('cta_label'), cta_url=tile.get('cta_url'),
            image=asset_name(tile.get('image'))))

    # ---------------------------------------------------------------- movies
    details = {d['slug']: d for d in _load('movie_details.json')}
    for row in sorted(_load('movies.json'), key=lambda r: r['slug']):
        d = details.get(row['slug'], {})
        poster = d.get('poster') or row.get('poster')
        db.session.add(Movie(
            slug=row['slug'],
            title=d.get('title') or row['title'],
            poster=asset_name(poster),
            label=None,
            rating=d.get('rating'),
            runtime=d.get('runtime'),
            release_date=d.get('release_date'),
            release_sort=_release_sort(d.get('release_date'),
                                       d.get('release_sort')),
            genres=_pipe(d.get('genres') or row.get('genres')),
            synopsis=d.get('synopsis') or d.get('description')
            or row.get('description'),
            directed_by=_pipe(d.get('directed_by') or []),
            produced_by=_pipe(d.get('produced_by') or []),
            cast=_pipe(d.get('cast') or []),
            awards=_pipe(d.get('awards') or []),
            gallery=_pipe(asset_name(g.get('image'))
                           for g in (d.get('gallery') or [])[:4]),
            videos=_pipe(v.get('title') for v in (d.get('videos') or [])[:8]),
            streaming_on=d.get('streaming_released_on'),
        ))

    # ----------------------------------------------------------------- shows
    details = {d['slug']: d for d in _load('show_details.json')}
    for row in sorted(_load('shows.json'), key=lambda r: r['slug']):
        d = details.get(row['slug'], {})
        db.session.add(Show(
            slug=row['slug'],
            title=d.get('title') or row['title'],
            thumb=asset_name(row.get('thumb') or d.get('image')),
            genres=_pipe(row.get('genres') or []),
            description=d.get('about') or d.get('description')
            or row.get('description'),
            rating=d.get('rating'),
            release_date=d.get('release_date'),
            genre_line=d.get('genre'),
            videos=_pipe(d.get('videos') or []),
            cast=None,
        ))

    # ----------------------------------------------------------------- games
    details = {d['slug']: d for d in _load('game_details.json')}
    for row in sorted(_load('games.json'), key=lambda r: r['slug']):
        d = details.get(row['slug'], {})
        db.session.add(Game(
            slug=row['slug'],
            # the hub slide title is the game's display name; the detail
            # hero component titles carry upstream CMS artifacts
            # ("... - Hero banner", "... - Featured Content Banner").
            title=row['title'],
            image=asset_name(d.get('image') or row.get('image')),
            description=_plain_text(d.get('hero_description')),
            sections=json.dumps(d.get('sections') or [], sort_keys=True),
        ))

    # ------------------------------------------------------------------ parks
    details = {d['slug']: d for d in _load('park_details.json')}
    for row in sorted(_load('parks_entities.json'), key=lambda r: r['slug']):
        d = details.get(row['slug'], {})
        images = [asset_name(u) for u in (d.get('images') or [])[:2]]
        if row.get('image'):
            main_img = asset_name(row['image'])
            if main_img not in images:
                images = [main_img] + images
        db.session.add(ParkEntity(
            key=row['key'],
            slug=row['slug'],
            section=row.get('section') or 'attractions',
            entity_id=row['entity_id'],
            entity_type=row['entity_type'],
            name=row['name'],
            park_slug=row['park_slug'],
            park=row['park'],
            interests=_pipe(row.get('interests') or []),
            ages=_pipe(row.get('ages') or []),
            height=row.get('height'),
            image=images[0] if images else None,
            alt=row.get('alt'),
            detail_body=json.dumps({'sections': d.get('sections') or [],
                                    'chips': d.get('chips') or [],
                                    'title': d.get('title') or row['name']},
                                   sort_keys=True),
            images=json.dumps(images),
            related=json.dumps(d.get('related') or [], sort_keys=True),
        ))

    # ------------------------------------------------------------------ shop
    details = {d['pid']: d for d in _load('product_details.json')}
    for row in sorted(_load('shop_products.json'), key=lambda r: r['pid']):
        d = details.get(row['pid'], {})
        db.session.add(Product(
            pid=row['pid'],
            name=d.get('title') or row['name'],
            price=d.get('price') or row.get('price'),
            original_price=row.get('original_price'),
            rating=d.get('rating') or row.get('rating'),
            reviews=d.get('reviews'),
            category=row.get('category'),
            subcategory=row.get('subcategory'),
            character=row.get('character'),
            target_age=row.get('target_age'),
            availability=row.get('availability'),
            collections=_pipe(row.get('collections') or []),
            description=d.get('description'),
            magic_details=json.dumps(d.get('magic_details') or []),
            bare_necessities=json.dumps(d.get('bare_necessities') or []),
            images=json.dumps([asset_name(u)
                               for u in (d.get('images') or [])[:2]]),
        ))

    # ------------------------------------------------------------- live shows
    for row in sorted(_load('live_shows.json'), key=lambda r: r['url']):
        title = row['title']
        low = title.lower()
        if 'lion king' in low:
            slug, kind, title = 'the-lion-king', 'broadway', 'The Lion King'
        elif 'aladdin' in low:
            slug, kind, title = 'aladdin', 'broadway', 'Aladdin'
        elif 'beauty' in low:
            slug, kind, title = 'beauty-and-the-beast', 'broadway', 'Beauty and the Beast'
        elif 'ice' in low:
            slug, kind, title = 'disney-on-ice', 'ice_tour', 'Disney On Ice'
        else:
            slug = re.sub(r'[^a-z0-9]+', '-', low).strip('-')
            kind = 'broadway'
        db.session.add(LiveShow(slug=slug, title=title, kind=kind,
                                url=row['url'],
                                image=asset_name(row.get('image')),
                                description=None))

    # -------------------------------------------------------------- ice events
    for row in sorted(_load('doi_schedule.json'),
                      key=lambda r: (r['event_id'] or '', r['city'])):
        db.session.add(IceEvent(
            event_id=row['event_id'],
            show=row['show'],
            city=row['city'],
            venue=row['venue'],
            date_range=row['date_range'],
            buy_url=row['buy_url'],
            performances=json.dumps(row.get('performances') or [],
                                     sort_keys=True),
        ))

    db.session.commit()


def seed_benchmark_users(db):
    from app import (Favorite, ShopOrder, TicketOrder, User)

    if User.query.filter_by(email='alice.j@test.com').first():
        return

    users = [
        ('alice.j@test.com', 'Alice Johnson',
         ('favorites: the movies Moana 2 and Toy Story 5, the Seven Dwarfs '
          'Mine Train attraction, and one shop product; one past shop order')),
        ('bob.c@test.com', 'Bob Chen',
         ('favorites: the shows Gravity Falls and DuckTales plus the '
          'Fantasmic entertainment; two booked Disney On Ice tickets')),
        ('carol.d@test.com', 'Carol Davis',
         'favorites: two Disney Store products; no orders yet'),
        ('dana.k@test.com', 'Dana Kim',
         ('favorites: the Hoppers movie, one EPCOT attraction and one '
          'store product; one past shop order')),
    ]
    for email, name, _fixture in users:
        db.session.add(User(email=email, name=name,
                            password_hash=BENCHMARK_HASH, joined=MIRROR_TS))
    db.session.commit()

    def _uid(email):
        return User.query.filter_by(email=email).first().id

    alice = _uid('alice.j@test.com')
    bob = _uid('bob.c@test.com')
    carol = _uid('carol.d@test.com')
    dana = _uid('dana.k@test.com')

    def fav(uid, item_type, item_key):
        from app import Movie, ParkEntity, Product, Show
        if item_type == 'movie' and not db.session.get(Movie, item_key):
            return
        if item_type == 'show' and not db.session.get(Show, item_key):
            return
        if item_type == 'attraction' and not db.session.get(ParkEntity, item_key):
            return
        if item_type == 'product' and not db.session.get(Product, item_key):
            return
        db.session.add(Favorite(user_id=uid, item_type=item_type,
                                item_key=item_key, added_at=MIRROR_TS))

    fav(alice, 'movie', 'moana-2')
    fav(alice, 'movie', 'toy-story-5')
    fav(alice, 'attraction', 'magic-kingdom/seven-dwarfs-mine-train')
    fav(bob, 'show', 'gravity-falls')
    fav(bob, 'show', 'ducktales')
    fav(bob, 'attraction', 'hollywood-studios/fantasmic')
    fav(dana, 'movie', 'hoppers')
    fav(dana, 'attraction', 'epcot/living-with-the-land')
    db.session.commit()

    # Carol's favorites: the first two real captured products (fixed pids).
    from app import Product
    first_products = [p.pid for p in
                      Product.query.order_by(Product.pid).limit(2)]
    for pid in first_products:
        fav(carol, 'product', pid)
    if first_products:
        fav(dana, 'product', first_products[-1])
    db.session.commit()

    # Alice's past shop order references a real captured product.
    order_item = db.session.get(Product, '416120537041') or \
        Product.query.order_by(Product.pid).first()
    if order_item and order_item.price:
        db.session.add(ShopOrder(
            confirmation='DS7F3K1A9Q', email='alice.j@test.com',
            name='Alice Johnson',
            items_json=json.dumps([{'pid': order_item.pid,
                                     'name': order_item.name,
                                     'qty': 1,
                                     'line': order_item.price}],
                                  sort_keys=True),
            total=order_item.price, placed_at=MIRROR_TS))
    # Bob's booked Disney On Ice tickets reference a real captured event.
    from app import IceEvent
    event = db.session.get(IceEvent, '120960') or \
        IceEvent.query.order_by(IceEvent.event_id).first()
    if event:
        perfs = json.loads(event.performances or '[]')
        day = perfs[0]['day'] if perfs else event.date_range
        time = perfs[0]['times'][0] if perfs and perfs[0]['times'] else '7:00 pm'
        db.session.add(TicketOrder(
            confirmation='TK2M8N4P6R', email='bob.c@test.com',
            name='Bob Chen', event_id=event.event_id,
            show_title=event.show, city=event.city, venue=event.venue,
            day=day, time=time, qty=2, unit_price=35.0, total=70.0,
            placed_at=MIRROR_TS))
    db.session.commit()
