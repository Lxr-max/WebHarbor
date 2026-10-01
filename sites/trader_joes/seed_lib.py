#!/usr/bin/env python3
"""Deterministic seed builder for the trader_joes mirror.

Everything materialized here comes from the tracked source_data/*.json
snapshots (captured 2026-09-30/10-01, see provenance.json) in a fixed,
sorted order; the four benchmark accounts and their shopping lists / My
Store preferences / newsletter subscriptions, plus the gift card fixtures,
are authored fixtures following the u_s_customs / nyse precedent: every
product they reference is a real captured upstream product, and every
timestamp is a frozen constant so the SQLite output is byte-reproducible
(PYTHONHASHSEED=0).
"""
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
SOURCE = os.path.join(HERE, 'source_data')

BENCHMARK_HASH = (
    '$2b$12$qSds4Mr9Wo7VwPWLhompEer88SuxxXFDp31P9etY6v7nfRctNO7B.')
MIRROR_TS = '2026-10-01'


def _load(name):
    with open(os.path.join(SOURCE, name), encoding='utf-8') as f:
        return json.load(f)


def _num(value):
    if value is None or value == '':
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _int(value):
    n = _num(value)
    return int(n) if n is not None else None


def _day_from_ms(ms):
    """Epoch-millisecond publish stamps render as YYYY-MM-DD (UTC)."""
    if not ms:
        return None
    import datetime
    return datetime.datetime.fromtimestamp(
        int(ms) / 1000, tz=datetime.timezone.utc).strftime('%Y-%m-%d')


def build_seed(db, bcrypt):
    """Materialize the catalog, recipes, stores, editorial and CMS content."""
    from app import (Announcement, Category, CMSPage, Editorial,
                     Entertaining, PodcastEpisode, Product, Recipe, Store)

    # ---- categories (the upstream categoryList tree) ----
    tree = _load('categories.json')['root']

    def add_cat(node, parent_id):
        row = Category(id=node['id'], level=node['level'], name=node['name'],
                       path=node['path'], url_key=node['url_key'],
                       product_count=node.get('product_count') or 0,
                       parent_id=parent_id)
        db.session.add(row)
        for child in node.get('children') or []:
            add_cat(child, node['id'])

    add_cat(tree, None)

    # ---- products (listing + detail payloads merged by sku) ----
    products = _load('products.json')
    for sku in sorted(products):
        p = products[sku]
        hierarchy = p.get('category_hierarchy') or []
        ids = [str(c['id']) for c in hierarchy]
        names = [c['name'] for c in hierarchy]
        db.session.add(Product(
            sku=sku,
            name=p.get('name') or p.get('item_title') or '',
            item_title=p.get('item_title') or '',
            url_key=p.get('url_key'),
            retail_price=_num(p.get('retail_price')),
            sales_size=(str(p.get('sales_size'))
                        if p.get('sales_size') is not None else None),
            sales_uom_description=p.get('sales_uom_description'),
            primary_image=p.get('primary_image'),
            context_image=p.get('context_image'),
            other_images=json.dumps(p.get('other_images') or []),
            item_description=p.get('item_description'),
            item_story_marketing=p.get('item_story_marketing'),
            item_story_qil=p.get('item_story_qil'),
            use_and_demo=p.get('use_and_demo'),
            item_characteristics=json.dumps(p.get('item_characteristics') or []),
            fun_tags=json.dumps(p.get('fun_tags') or []),
            product_label=p.get('product_label'),
            country_of_origin=p.get('country_of_origin'),
            availability=str(p.get('availability') or '1'),
            new_product=1 if str(p.get('new_product')) in ('1', 'True') else 0,
            promotion=1 if str(p.get('promotion')) in ('1', 'True') else 0,
            category_ids='/'.join(ids) + '/' if ids else '/',
            category_names=json.dumps(names),
            first_published_date=p.get('first_published_date'),
            nutrition=json.dumps(p.get('nutrition') or []),
            ingredients=json.dumps(p.get('ingredients') or []),
            allergens=json.dumps(p.get('allergens') or []),
            related_skus=json.dumps([rp.get('sku') for rp in
                                     (p.get('related_products') or [])
                                     if rp.get('sku')]),
        ))

    # ---- recipes ----
    recipes = _load('recipes.json')
    for slug in sorted(recipes['details']):
        detail = recipes['details'][slug]
        db.session.add(Recipe(
            slug=slug,
            title=detail.get('title') or slug.replace('-', ' ').title(),
            description=detail.get('description') or '',
            image_src=detail.get('image_src'),
            categories=json.dumps(detail.get('categories') or []),
            fun_tags=json.dumps(detail.get('funTagTitles') or []),
            ingredients=json.dumps(detail.get('ingredients') or []),
            directions=json.dumps(detail.get('steps') or []),
            serves_min=detail.get('servesMin'),
            serves_max=detail.get('servesMax'),
            minutes_to_cook=detail.get('minutesToCook'),
            hours_to_cook=detail.get('hoursToCook'),
            minutes_to_cook2=detail.get('minutesToCook2'),
            hours_to_cook2=detail.get('hoursToCook2'),
        ))

    # ---- stores (the where2getit locator records) ----
    stores = _load('stores.json')
    day_fields = [('monday', 'monday_open', 'monday_close'),
                  ('tuesday', 'tuesday_open', 'tuesday_close'),
                  ('wednesday', 'wednesday_open', 'wednesday_close'),
                  ('thursday', 'thursday_open', 'thursday_close'),
                  ('friday', 'friday_open', 'friday_close'),
                  ('saturday', 'saturday_open', 'saturday_close'),
                  ('sunday', 'sunday_open', 'sunday_close')]
    for key in sorted(stores):
        s = stores[key]
        hours = {}
        for day, open_f, close_f in day_fields:
            hours[day] = [s.get(open_f), s.get(close_f)]
        db.session.add(Store(
            clientkey=str(key),
            uid=_int(s.get('uid')),
            name=s.get('name') or '',
            address1=s.get('address1'),
            address2=s.get('address2'),
            city=s.get('city') or '',
            state=s.get('state') or '',
            postalcode=s.get('postalcode'),
            country=s.get('country') or 'US',
            phone=s.get('phone'),
            latitude=_num(s.get('latitude')),
            longitude=_num(s.get('longitude')),
            county=s.get('county'),
            hours=json.dumps(hours),
            bho=json.dumps(s.get('bho') or []),
            holiday_hours=s.get('holidayhours'),
            coming_soon=1 if s.get('Coming Soon') else 0,
            temp_note=s.get('Temp Hours Note'),
            holiday_note=s.get('Holiday Hours Note'),
            text_comments=s.get('Text Comments'),
            curbside_pickup=s.get('curbside_pickup'),
            liquor=s.get('liquor'),
            wine=s.get('wine'),
            beer=s.get('beer'),
            alcohol_message=s.get('alcohol_message'),
            parking_notes=s.get('parkingnotes'),
            directions_notes=s.get('directionsnotes'),
            about_copy=s.get('about_copy'),
            open_date=s.get('opendate'),
            website=s.get('website'),
        ))

    # ---- announcements ----
    for idx, a in enumerate(_load('announcements.json')):
        db.session.add(Announcement(
            id=idx + 1,
            title=a['title'],
            category=a.get('category') or 'customer-updates',
            category_title=a.get('categoryTitle') or 'Customer Updates',
            publish_date=_day_from_ms(a.get('publishDate')) or MIRROR_TS,
            body=a.get('text') or '',
            image=a.get('image'),
        ))

    # ---- guides + stories ----
    def _is_404_capture(row):
        """Capture-side guard: upstream AEM models for expired pages
        (e.g. fall-products-2025) render an 'Oops!' 404 page whose model
        carries title '404 Not Found' and no blocks; such slugs must never
        enter the editorial tables as stories/guides."""
        title = (row.get('h1') or row.get('title') or '').strip()
        return (not title or title == 'Oops!'
                or title.lower().startswith('404'))

    for kind, fname in (('guide', 'guides.json'), ('story', 'stories.json')):
        rows = _load(fname)
        for slug in sorted(rows):
            row = rows[slug]
            if _is_404_capture(row):
                continue
            db.session.add(Editorial(
                slug=slug,
                kind=kind,
                title=row.get('h1') or row.get('title') or slug,
                publish_date=_day_from_ms(row.get('publishDate')) or MIRROR_TS,
                hero=(row.get('hero') or {}).get('src'),
                blocks=json.dumps(row.get('blocks') or []),
                product_skus=json.dumps(row.get('product_skus') or []),
                related=json.dumps(row.get('related') or {}),
            ))

    # ---- entertaining list ----
    ent = _load('entertaining_content.json')
    for art in ent.get('articles') or []:
        title = art.get('title') or ''
        slug = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')
        if not slug:
            continue
        db.session.add(Entertaining(
            slug=slug,
            title=title,
            category=art.get('category'),
            publish_date=_day_from_ms(art.get('date')) or MIRROR_TS,
            description=art.get('description') or '',
            page_path=art.get('pagePath'),
        ))

    # ---- podcast ----
    pod = _load('podcast_content.json')
    for idx, ep in enumerate(pod.get('episodes') or []):
        db.session.add(PodcastEpisode(
            idx=idx + 1,
            title=ep.get('title') or '',
            pub_date=ep.get('pubDate') or '',
            description=ep.get('description') or '',
            audio_url=ep.get('audio_url'),
        ))

    # ---- CMS pages (captured editorial blocks) ----
    cms_specs = [
        ('about', 'about_content.json', 'About Us | Trader Joe\'s'),
        ('faq', 'faq_content.json', 'FAQs | Trader Joe\'s'),
        ('careers', 'careers_content.json', 'Careers | Trader Joe\'s'),
        ('contact', 'contact_content.json', 'Contact Us | Trader Joe\'s'),
        ('neighborhood', 'neighborhood_content.json',
         'Neighborhood Shares | Trader Joe\'s'),
        ('privacy', None, 'Privacy Policy | Trader Joe\'s'),
        ('food-safety', None, 'Food Safety & Product Recalls | Trader Joe\'s'),
        ('podcast', None, 'Podcast | Trader Joe\'s'),
    ]
    for key, fname, title in cms_specs:
        page = None
        if fname:
            data = _load(fname)
            page = CMSPage(page=key, title=data.get('title') or title,
                           h1=data.get('h1'),
                           blocks=json.dumps(data.get('blocks') or []))
        elif key == 'privacy':
            page = CMSPage(page=key, title=title, h1='Privacy Policy',
                           blocks=json.dumps([{'type': 'text', 'html':
                           '<p>Trader Joe\'s respects your privacy. This '
                           'mirror stores only the benchmark account data '
                           'you create; no tracking, no third-party '
                           'analytics.</p>'}]))
        elif key == 'food-safety':
            page = CMSPage(page=key, title=title,
                           h1='Food Safety & Product Recalls',
                           blocks=json.dumps([
                               {'type': 'text', 'html':
                                '<p>Food safety is a priority at Trader '
                                'Joe\'s. When we become aware that a product '
                                'we sell may pose a health or safety risk to '
                                'our customers, we remove it from our '
                                'shelves and post a notice on this page. '
                                'Current and recent notices are listed on '
                                'the Announcements board under '
                                '<b>Recalls</b>.</p>'},
                               {'type': 'button', 'text': 'VIEW '
                                'ANNOUNCEMENTS', 'link': '/home/'
                                'announcements?category=recalls'}]))
        elif key == 'podcast':
            page = CMSPage(page='podcast', title=title, h1='Inside Trader '
                           'Joe\'s', blocks=json.dumps([]))
        if page is not None:
            db.session.add(page)

    db.session.commit()


# ------------------------------------------------------------- benchmark --

def build_benchmark_users(db, bcrypt):
    """Four benchmark users with seeded shopping lists, stores, and
    newsletter subscriptions (deterministic fixtures)."""
    from app import (GiftCard, ShoppingItem, Subscriber, UserStore, User)

    users = [
        ('alice_j', 'alice.j@test.com', 'Alice Johnson'),
        ('bob_c', 'bob.c@test.com', 'Bob Chen'),
        ('carol_d', 'carol.d@test.com', 'Carol Davis'),
        ('dana_k', 'dana.k@test.com', 'Dana Kim'),
    ]
    made = {}
    for username, email, display in users:
        user = User(email=email, name=display,
                    password_hash=BENCHMARK_HASH, joined=MIRROR_TS)
        db.session.add(user)
        made[username] = user
    db.session.flush()

    def _product_by_title(fragment):
        from app import Product
        return Product.query.filter(
            Product.item_title.ilike(f'%{fragment}%')).order_by(
            Product.sku).first()

    # Alice: pumpkin-season shopping list (5 items, mixed quantities)
    alice_list = [
        ('Pumpkin Cream Cheese Spread', 2),
        ('Organic Pumpkin', 1),
        ('Pumpkin Bread & Muffin Mix', 1),
        ('Pumpkin Bisque', 3),
        ('Pumpkin Spiced Pumpkin Seeds', 1),
    ]
    for fragment, qty in alice_list:
        p = _product_by_title(fragment)
        if p:
            db.session.add(ShoppingItem(user_id=made['alice_j'].id,
                                        sku=p.sku, quantity=qty,
                                        added_at=MIRROR_TS))
    db.session.add(UserStore(user_id=made['alice_j'].id, clientkey='140'))
    db.session.add(Subscriber(email='alice.j@test.com',
                              status='subscribed', created_at=MIRROR_TS))

    # Bob: freezer + snacks list (4 items)
    bob_list = [
        ('Mandarin Orange Chicken', 2),
        ('Dark Chocolate Peanut Butter Cups', 1),
        ('Unexpected Cheddar Cheese', 2),
        ('Everything But The Bagel Sesame Seasoning Blend', 1),
    ]
    for fragment, qty in bob_list:
        p = _product_by_title(fragment)
        if p:
            db.session.add(ShoppingItem(user_id=made['bob_c'].id,
                                        sku=p.sku, quantity=qty,
                                        added_at=MIRROR_TS))
    db.session.add(UserStore(user_id=made['bob_c'].id, clientkey='510'))
    db.session.add(Subscriber(email='bob.c@test.com',
                              status='subscribed', created_at=MIRROR_TS))

    # Carol: gluten-free list (3 items, all Gluten Free)
    carol_list = [
        ('Organic Brown Rice & Quinoa Fusilli Pasta', 1),
        ('Gluten Free Norwegian Crispbread', 2),
        ('Gluten Free Multigrain Bread', 1),
    ]
    for fragment, qty in carol_list:
        p = _product_by_title(fragment)
        if p:
            db.session.add(ShoppingItem(user_id=made['carol_d'].id,
                                        sku=p.sku, quantity=qty,
                                        added_at=MIRROR_TS))
    db.session.add(UserStore(user_id=made['carol_d'].id, clientkey='114'))
    db.session.add(Subscriber(email='carol.d@test.com',
                              status='subscribed', created_at=MIRROR_TS))

    # Dana: empty list, unsubscribed, store preference only
    db.session.add(UserStore(user_id=made['dana_k'].id, clientkey='742'))
    db.session.add(Subscriber(email='dana.k@test.com',
                              status='unsubscribed', created_at=MIRROR_TS))

    # ---- gift card fixtures (deterministic benchmark cards) ----
    cards = [
        ('6510000000123456', 25.00),
        ('6510000000654321', 51.37),
        ('6510000000987654', 100.00),
        ('6510000000112233', 0.00),
        ('6510000000445566', 12.49),
    ]
    for number, balance in cards:
        db.session.add(GiftCard(card_number=number, balance=balance,
                               status='active'))

    db.session.commit()
