"""Build-time seed for the Speedo mirror.

Reads source_data.json (real catalog + content captured from speedo.com — see
provenance.json) and materializes it into Department / NavGroup / NavLink /
Collection / CollectionMembership / Product / ProductSize / Athlete / Article /
ContentPage / FaqEntry / DiscountCode rows, plus four benchmark users with
pre-populated carts, wishlists, addresses, cards and order history.

Deterministic: no wall clock, no random, no hash-order dependence. The
benchmark password hash is frozen so rebuilds are byte-identical.

Idempotency lives at the function level (each seed_* early-returns on a
populated DB) — wired from app.py's bootstrap.
"""
import json
import os
from datetime import date, datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SOURCE = os.path.join(BASE_DIR, 'source_data.json')

# bcrypt hash of 'TestPass123!' (cost 12), frozen for byte-identical rebuilds.
FROZEN_PASSWORD_HASH = '$2b$12$WtOBgikyE24OU/kuhls4Fuy1s2Kuz/osD0cproGZjpkL713kWy58q'

REFERENCE_DATE = date(2026, 9, 26)


def _load():
    with open(SOURCE, encoding='utf-8') as f:
        return json.load(f)


def run_seed(db, Department, NavGroup, NavLink, Collection, CollectionMembership,
             Product, ProductSize, Athlete, Article, ContentPage, FaqEntry,
             DiscountCode):
    """Materialize catalog + content rows. Called by app.seed_database()."""
    if Product.query.count() > 0:
        return
    data = _load()

    # ---- departments ----
    for i, dept in enumerate(data['nav']):
        db.session.add(Department(slug=dept['slug'], name=dept['name'],
                                   hub_page=dept.get('hub_page', ''), sort=i))
    db.session.flush()

    # ---- mega menu ----
    for dept in data['nav']:
        for gi, block in enumerate(dept['blocks']):
            group = NavGroup(department_slug=dept['slug'], name=block['name'],
                             kind=block.get('kind', 'collection'), sort=gi)
            db.session.add(group)
            db.session.flush()
            for li, link in enumerate(block['links']):
                db.session.add(NavLink(group_id=group.id, text=link['text'],
                                        href=link['href'],
                                        is_promo=bool(link.get('is_promo')),
                                        promo_image=link.get('promo_image', ''),
                                        promo_heading=link.get('promo_heading', ''),
                                        sort=li))
    db.session.flush()

    # ---- collections ----
    coll_by_slug = {}
    for i, c in enumerate(data['collections']):
        row = Collection(slug=c['slug'], name=c['name'],
                         department_slug=c['department'],
                         in_mega_menu=bool(c.get('in_mega_menu')),
                         facet_set=('goggles' if c['department'] == 'goggles'
                                    else 'accessories' if c['department'] == 'accessories'
                                    else 'swimwear'),
                         sort=i)
        db.session.add(row)
        coll_by_slug[c['slug']] = row
    db.session.flush()

    # ---- products ----
    prod_by_slug = {}
    for idx, rec in enumerate(data['products']):
        p = Product(
            slug=rec['slug'], name=rec['name'], sku=rec['sku'],
            department_slug=rec['department'], category=rec['category'],
            colourway_group=rec['colourway_group'], colour=rec['colour'],
            colour_swatch=rec['colour_swatch'],
            price=rec['price'], compare_at_price=rec['compare_at_price'],
            description=rec['description'], delivery=rec['delivery'],
            specs=json.dumps(rec['specs'], ensure_ascii=False),
            images=json.dumps(rec['images'], ensure_ascii=False),
            activity=rec['activity'], fabric=rec['fabric'],
            back_shape=rec['back_shape'], lens_type=rec['lens_type'],
            collection_line=rec['collection_line'],
            is_new=bool(rec['is_new']), is_sale=bool(rec['is_sale']),
            is_bestseller=bool(rec['is_bestseller']),
            is_exclusive=bool(rec['is_exclusive']),
            sold_out=bool(rec['sold_out']), is_kids=bool(rec['is_kids']),
            upstream_url=rec['upstream_url'],
            sort=idx)
        db.session.add(p)
        prod_by_slug[rec['slug']] = p
    db.session.flush()

    # sizes (second pass now that products have ids)
    for rec in data['products']:
        p = prod_by_slug[rec['slug']]
        for si, s in enumerate(rec['sizes']):
            db.session.add(ProductSize(product_id=p.id, size=s['size'],
                                        sold_out=bool(s['sold_out']), sort=si))
    db.session.flush()

    # ---- collection memberships ----
    for c in data['collections']:
        row = coll_by_slug[c['slug']]
        for pos, slug in enumerate(c['products']):
            p = prod_by_slug.get(slug)
            if p:
                db.session.add(CollectionMembership(collection_id=row.id,
                                                     product_id=p.id, position=pos))
    db.session.flush()

    # ---- athletes ----
    for i, a in enumerate(data['athletes']):
        db.session.add(Athlete(slug=a['slug'], name=a['name'], team=a['team'],
                                quote=a['quote'], bio=a['bio'],
                                hero_image=a['hero_image'],
                                portrait_image=a['portrait_image'],
                                card_image=a['card_image'], sort=i))

    # ---- articles ----
    for i, art in enumerate(data['articles']):
        db.session.add(Article(slug=art['slug'], title=art['title'],
                                published=art['published'], summary=art['summary'],
                                body=art['body'], image=art['image'], sort=i))

    # ---- content pages ----
    for slug, page in data['pages'].items():
        featured = []
        fc = page.get('featured_collection')
        if fc and fc in coll_by_slug:
            for m in coll_by_slug[fc].memberships:
                featured.append(prod_by_slug[
                    db.session.get(Product, m.product_id).slug])
            featured = [p.slug for p in featured[:12]]
        db.session.add(ContentPage(
            slug=slug, title=page['title'],
            body=json.dumps(page['blocks'], ensure_ascii=False),
            hero_image=page.get('hero_image', ''),
            is_hub=bool(page.get('is_hub')),
            hub_department='',
            featured_products=json.dumps(featured),
            sort=0))

    # ---- faqs ----
    for i, f in enumerate(data['faqs']):
        db.session.add(FaqEntry(question=f['question'], answer=f['answer'], sort=i))

    # ---- discounts ----
    for d in data['discounts']:
        db.session.add(DiscountCode(code=d['code'], kind=d['kind'], value=d['value'],
                                     min_spend=d['min_spend'],
                                     description=d['description']))

    db.session.commit()


def run_seed_users(db, User, Address, PaymentCard, CartItem, WishlistItem,
                   Order, OrderItem, Product):
    """Materialize the four benchmark users with pre-populated account data."""
    if User.query.filter_by(email='alice.j@test.com').first():
        return
    prods = {}
    for p in Product.query.order_by(Product.sort).all():
        prods.setdefault(p.slug, p)

    def pick(slug):
        return prods.get(slug)

    def first_size(p):
        for s in p.sizes:
            if not s.sold_out:
                return s.size
        return p.sizes[0].size if p.sizes else ''

    users = [
        dict(email='alice.j@test.com', name='Alice Johnson', phone='+44 7700 900001',
             addresses=[dict(label='Home', line1='12 Marina Way', line2='Flat 3',
                             city='Brighton', postcode='BN1 1AA', is_default=True),
                        dict(label='Work', line1='Speedo House, 40 Pool Road',
                             city='London', postcode='E1 6AN')],
             cards=[dict(label='Personal', brand='Visa', last4='4242', exp_month=11,
                         exp_year=28, is_default=True)],
             cart=['womens-endurance-medalist-swimsuit-black-8134710001',
                   'biofuse-2-0-goggles-black-800233214501'],
             wishlist=['womens-fastskin-lzr-pure-valor-2-0-openback-kneeskin-red-black-815859002',
                       'mens-endurance-jammer-black-8134470001',
                       'adult-fastskin-hyper-elite-mirrored-goggles-smoke-red-812818007',
                       'womens-hyperboom-printed-medalist-swimsuit-blue-pink-8a000244002'],
             orders=[
                 dict(number='SP100001', days_ago=21, status='Dispatched',
                      items=[('womens-endurance-medalist-swimsuit-navy-813471d740', '32', 1),
                             ('womens-endurance-swim-legging-black-8a000125002', 'M', 1)],
                      method='Standard Delivery', shipping=5.99,
                      card='Visa', last4='4242', tracking='SDRM100118234GB',
                      address=('Alice Johnson', '12 Marina Way, Flat 3', 'Brighton', 'BN1 1AA')),
                 dict(number='SP100002', days_ago=6, status='Processing',
                      items=[('biofuse-2-0-goggles-blue-800233214502', 'One Size', 2)],
                      method='Express Delivery', shipping=8.99,
                      card='Visa', last4='4242', tracking='',
                      address=('Alice Johnson', '12 Marina Way, Flat 3', 'Brighton', 'BN1 1AA')),
             ]),
        dict(email='bob.c@test.com', name='Bob Chen', phone='+44 7700 900002',
             addresses=[dict(label='Home', line1='88 Harbour Street',
                             city='Portsmouth', postcode='PO1 3AA', is_default=True)],
             cards=[dict(label='Personal', brand='Mastercard', last4='5309', exp_month=3,
                         exp_year=29, is_default=True)],
             cart=['mens-endurance-jammer-navy-813447d740',
                   'adult-bubble-active-cap-black-8139540001',
                   'mens-essentials-swim-shorts-blue-812433005'],
             wishlist=['mens-fastskin-lzr-pure-intent-2-0-jammer-red-black-815857002',
                       'speedo-iq-vanquisher-3-0-mirror-track-purple-8e000235012',
                       'mens-hyperboom-jammer-black-red-8a000153003',
                       '25l-flex-bag-white-black-8e000215002',
                       'womens-endurance-logo-thinstrap-bikini-set-red-8a000119005'],
             orders=[
                 dict(number='SP100003', days_ago=14, status='Dispatched',
                      items=[('mens-endurance-jammer-black-8134470001', '34', 1),
                             ('adult-hydropure-optical-goggles-black-812670f808', '-2.0', 1)],
                      method='Standard Delivery', shipping=0.0,
                      card='Mastercard', last4='5309', tracking='SDRM100224451GB',
                      address=('Bob Chen', '88 Harbour Street', 'Portsmouth', 'PO1 3AA')),
             ]),
        dict(email='carol.d@test.com', name='Carol Davis', phone='+44 7700 900003',
             addresses=[dict(label='Home', line1='5 Lido Terrace', city='Bristol',
                             postcode='BS1 4TR', is_default=True),
                        dict(label="Mum's", line1='9 Seafront Avenue',
                             city='Plymouth', postcode='PL1 2QQ')],
             cards=[dict(label='Personal', brand='Visa', last4='1881', exp_month=7,
                         exp_year=27, is_default=True),
                    dict(label='Club', brand='Mastercard', last4='6771', exp_month=10,
                         exp_year=28)],
             cart=['girls-endurance-medalist-swimsuit-navy-813457d740',
                   'biofuse-2-0-junior-goggles-clear-blue-800336315947'],
             wishlist=['womens-sculpture-boom-back-swimsuit-black-8a000165002',
                       'womens-plus-size-medalist-placement-swimsuit-navy-blue-8005286002',
                       'adult-fastskin-pure-focus-mirrored-goggles-red-811778004'],
             orders=[
                 dict(number='SP100004', days_ago=30, status='Dispatched',
                      items=[('girls-endurance-medalist-swimsuit-pink-813457b495', '28', 1)],
                      method='Standard Delivery', shipping=5.99,
                      card='Visa', last4='1881', tracking='SDRM100330912GB',
                      address=('Carol Davis', '5 Lido Terrace', 'Bristol', 'BS1 4TR')),
                 dict(number='SP100005', days_ago=17, status='Dispatched',
                      items=[('boys-endurance-jammer-black-8134600001', '26', 1),
                             ('infant-learn-to-swim-chima-swim-cap-blue-red-800232606348', 'One Size', 2)],
                      method='Standard Delivery', shipping=5.99,
                      card='Mastercard', last4='6771', tracking='SDRM100411208GB',
                      address=('Carol Davis', "Mum's, 9 Seafront Avenue", 'Plymouth', 'PL1 2QQ')),
                 dict(number='SP100006', days_ago=3, status='Processing',
                      items=[('womens-quantum-rib-splice-swimsuit-black-blue-8a000107004', '36', 1)],
                      method='Express Delivery', shipping=8.99,
                      card='Visa', last4='1881', tracking='',
                      address=('Carol Davis', '5 Lido Terrace', 'Bristol', 'BS1 4TR')),
             ]),
        dict(email='david.k@test.com', name='David Kim', phone='+44 7700 900004',
             addresses=[dict(label='Home', line1='27 Channel View', city='Southampton',
                             postcode='SO14 3FL', is_default=True)],
             cards=[dict(label='Personal', brand='Visa', last4='9902', exp_month=5,
                         exp_year=28, is_default=True)],
             cart=['mens-fastskin-lzr-pure-valor-2-0-jammer-black-8158610001',
                   'mens-club-training-brief-red-8a000077005',
                   'adult-medium-blade-fin-red-turquoise-800478510558',
                   '35l-team-rucksack-navy-8e000211004'],
             wishlist=['mens-fastskin-lzr-pure-intent-2-0-high-waist-jammer-red-black-815858002',
                       'adult-fastskin-speedo-socket-2-0-mirrored-goggles-red-smoke-810897005',
                       'mens-lookout-printed-swim-shorts-navy-blue-800484501529',
                       'womens-fastskin-lzr-pure-intent-2-0-closedback-kneeskin-red-black-815856002',
                       'speedo-iq-vanquisher-3-0-track-navy-8e000236006',
                       'mens-plus-size-essential-swim-shorts-red-80033506446'],
             orders=[
                 dict(number='SP100007', days_ago=10, status='Dispatched',
                      items=[('mens-fastskin-lzr-pure-valor-2-0-jammer-black-8158610001', '32', 1),
                             ('adult-fastskin-speedo-socket-2-0-mirrored-goggles-red-smoke-810897005', 'One Size', 1)],
                      method='Express Delivery', shipping=8.99,
                      card='Visa', last4='9902', tracking='SDRM100522663GB',
                      address=('David Kim', '27 Channel View', 'Southampton', 'SO14 3FL')),
             ]),
    ]

    for spec in users:
        user = User(email=spec['email'], name=spec['name'], phone=spec['phone'],
                    password_hash=FROZEN_PASSWORD_HASH,
                    created_at=datetime(2026, 1, 15),
                    accepts_marketing=True)
        db.session.add(user)
        db.session.flush()
        for a in spec['addresses']:
            parts = a.get('line1', '').split(', ')
            db.session.add(Address(user_id=user.id, label=a['label'],
                                    first_name=spec['name'].split()[0],
                                    last_name=spec['name'].split()[-1],
                                    line1=parts[0], line2=parts[1] if len(parts) > 1 else '',
                                    city=a['city'], postcode=a['postcode'],
                                    is_default=bool(a.get('is_default'))))
        for c in spec['cards']:
            db.session.add(PaymentCard(user_id=user.id, label=c['label'], brand=c['brand'],
                                        last4=c['last4'], exp_month=c['exp_month'],
                                        exp_year=c['exp_year'],
                                        is_default=bool(c.get('is_default'))))
        for slug in spec['cart']:
            p = pick(slug)
            if p:
                db.session.add(CartItem(user_id=user.id, product_id=p.id,
                                        size=first_size(p), qty=1,
                                        added_at=REFERENCE_DATE.isoformat()))
        for slug in spec['wishlist']:
            p = pick(slug)
            if p:
                db.session.add(WishlistItem(user_id=user.id, product_id=p.id,
                                             added_at=REFERENCE_DATE.isoformat()))
        for o in spec['orders']:
            placed = date(2026, 9, 26)
            placed = date.fromordinal(placed.toordinal() - o['days_ago'])
            items = []
            for slug, size, qty in o['items']:
                p = pick(slug)
                if not p:
                    continue
                items.append((p, size, qty))
            subtotal = round(sum(p.price * qty for p, _s, qty in items), 2)
            total = round(subtotal + o['shipping'], 2)
            first, last = o['address'][0].split(' ', 1)
            order = Order(order_number=o['number'], user_id=user.id,
                          email=spec['email'], status=o['status'],
                          subtotal=subtotal, discount=0.0,
                          shipping_method=o['method'], shipping=o['shipping'],
                          total=total, discount_code='',
                          ship_name=o['address'][0], ship_line1=o['address'][1],
                          ship_line2='', ship_city=o['address'][2],
                          ship_postcode=o['address'][3],
                          ship_country='United Kingdom',
                          card_brand=o['card'], card_last4=o['last4'],
                          tracking_number=o.get('tracking', ''),
                          placed_on=placed.isoformat())
            db.session.add(order)
            db.session.flush()
            for p, size, qty in items:
                db.session.add(OrderItem(order_id=order.id, product_id=p.id,
                                          product_name=p.name, product_slug=p.slug,
                                          size=size, qty=qty, unit_price=p.price))
    db.session.commit()


if __name__ == "__main__":
    # Standalone build mode: (re)build the seed DB and publish it as
    # instance_seed/speedo.db (same contract as the mta / imgur build-generated
    # seeds). The Dockerfile seed gate wipes instance/ before rerunning this.
    import os
    import shutil
    import sys
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
    shutil.copyfile(os.path.join(base, "instance", "speedo.db"),
                   os.path.join(seed_dir, "speedo.db"))
    print("seed complete; copied instance/speedo.db to instance_seed/speedo.db")
