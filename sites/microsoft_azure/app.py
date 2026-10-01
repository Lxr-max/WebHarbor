#!/usr/bin/env python3
"""microsoft_azure — a WebHarbor mirror of https://azure.microsoft.com/

Flask + SQLite mirror of the Microsoft Azure cloud-services product site,
rebuilt from real upstream captures (probe 2026-09-30: HTTP 200):

  * Home — the live hero banner, featured product tiles, global
    infrastructure section and customer-story / blog teasers.
  * Products — the full 138-product catalog across 21 categories with
    category filtering and search, plus 23 fully captured product pages
    (title, description, section copy, documentation links, pricing
    links, related products).
  * Pricing — the 50-card pricing hub, four captured pricing-details
    tables (AKS, Linux VMs, Cosmos DB, Managed Disks), and the 85-item
    free-services catalog with category / period filters.
  * Pricing calculator — a server-side estimate engine over the real
    calculator API data: 55 VM sizes (Linux + Windows, 2,943 regional
    per-hour prices), AKS control-plane tiers plus 22 node sizes, tiered
    block-blob storage prices, and Cosmos DB provisioned / serverless /
    gateway pricing, all across the captured regions and currencies.
    Signed-in users can save estimates.
  * Global infrastructure — the 31 Azure geographies and their regions
    with per-service availability, plus a products-by-region comparison
    view over the calculator price data.
  * Customer stories — 142 real customer stories with industry and
    product facets, full story pages, and search.
  * Blog — 21 captured posts with category filter and excerpts.
  * Cloud computing dictionary — 86 captured terminology articles
    (documentation retrieval) with search.
  * Support — the four support plans.
  * Site-wide search and the account surface (signup, login, saved
    estimates, product favorites).

Every content record and every image under static/images/ comes from the
live upstream (see provenance.json and asset_inventory.json); the only
authored rows are the four benchmark user accounts. The SQLite seed is
materialized deterministically at image build time (PYTHONHASHSEED=0).
"""
import html as H
import json
import os
from datetime import datetime, timezone

from flask import (Flask, abort, flash, jsonify, redirect, render_template,
                   request, session, url_for)
from flask_bcrypt import Bcrypt
from flask_login import (LoginManager, UserMixin, current_user,
                         login_required, login_user, logout_user)
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect
from markupsafe import Markup

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__, instance_path=os.path.join(BASE_DIR, 'instance'))
app.config["SECRET_KEY"] = os.environ.get("AZURE_SECRET_KEY") or \
    "webharbor-microsoft-azure-dev-key"
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'AZURE_DB_URI',
    f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'microsoft_azure.db')}")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['WTF_CSRF_TIME_LIMIT'] = None

os.makedirs(os.path.join(BASE_DIR, 'instance'), exist_ok=True)

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to continue.'
csrf = CSRFProtect(app)

MIRROR_TS = '2026-09-30'
SITE_NAME = 'microsoft_azure'
UPSTREAM = 'https://azure.microsoft.com/'
BRAND = 'Microsoft Azure'
SHORT = 'Azure'
SOURCE = os.path.join(BASE_DIR, 'source_data')
HOURS_PER_MONTH = 730

# bcrypt hash of 'TestPass123!' — frozen so the seed DB is byte-reproducible.
BENCHMARK_PASSWORD_HASH = (
    '$2b$12$qSds4Mr9Wo7VwPWLhompEer88SuxxXFDp31P9etY6v7nfRctNO7B.')


def _load(name):
    with open(os.path.join(SOURCE, name), encoding='utf-8') as f:
        return json.load(f)


def _img(path):
    if not path:
        return url_for('static', filename='images/azure-logo.svg')
    return url_for('static', filename='images/' + path)


# ------------------------------------------------------------------ models --

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text, nullable=False)
    email = db.Column(db.Text, unique=True, nullable=False, )
    pw_hash = db.Column(db.Text, nullable=False)
    role = db.Column(db.Text, default='')

    estimates = db.relationship('Estimate', backref='user', lazy=True)
    favorites = db.relationship('Favorite', backref='user', lazy=True)


class Product(db.Model):
    __tablename__ = 'products'
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.Text, unique=True, nullable=False, )
    name = db.Column(db.Text, nullable=False)
    desc = db.Column(db.Text, default='')
    categories = db.Column(db.Text, nullable=False, default='[]')
    pricing_url = db.Column(db.Text)
    has_page = db.Column(db.Boolean, default=False)

    @property
    def category_list(self):
        return json.loads(self.categories)


class ProductPage(db.Model):
    __tablename__ = 'product_pages'
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.Text, unique=True, nullable=False, )
    title = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text, default='')
    sections = db.Column(db.Text, nullable=False, default='[]')
    docs_urls = db.Column(db.Text, nullable=False, default='[]')
    pricing_url = db.Column(db.Text)
    related = db.Column(db.Text, nullable=False, default='[]')
    hero_image = db.Column(db.Text, default='')
    content_images = db.Column(db.Text, nullable=False, default='[]')

    @property
    def section_list(self):
        return json.loads(self.sections)

    @property
    def docs_list(self):
        return json.loads(self.docs_urls)

    @property
    def related_list(self):
        return json.loads(self.related)

    @property
    def content_image_list(self):
        return json.loads(self.content_images)


class PricingCard(db.Model):
    __tablename__ = 'pricing_cards'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text, nullable=False)
    href = db.Column(db.Text, nullable=False)
    icon = db.Column(db.Text, default='')


class PricingTable(db.Model):
    __tablename__ = 'pricing_tables'
    id = db.Column(db.Integer, primary_key=True)
    page = db.Column(db.Text, nullable=False, )
    idx = db.Column(db.Integer, nullable=False)
    header = db.Column(db.Text, nullable=False)
    rows = db.Column(db.Text, nullable=False)

    @property
    def header_list(self):
        return json.loads(self.header)

    @property
    def row_list(self):
        return json.loads(self.rows)


class Geography(db.Model):
    __tablename__ = 'geographies'
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.Text, unique=True, nullable=False)
    display_name = db.Column(db.Text, nullable=False)


class Region(db.Model):
    __tablename__ = 'regions'
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.Text, unique=True, nullable=False, )
    display_name = db.Column(db.Text, nullable=False)
    geo_slug = db.Column(db.Text, nullable=False, )
    services = db.Column(db.Text, nullable=False, default='{}')

    @property
    def service_map(self):
        return json.loads(self.services)


class Currency(db.Model):
    __tablename__ = 'currencies'
    code = db.Column(db.Text, primary_key=True)
    name = db.Column(db.Text, nullable=False)
    glyph = db.Column(db.Text, nullable=False)
    display_name = db.Column(db.Text, nullable=False)
    conversion = db.Column(db.Float, nullable=False)


class VmSize(db.Model):
    __tablename__ = 'vm_sizes'
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.Text, unique=True, nullable=False, )
    os = db.Column(db.Text, nullable=False)
    size_slug = db.Column(db.Text, nullable=False)
    series = db.Column(db.Text)
    cores = db.Column(db.Integer)
    ram_gb = db.Column(db.Float)
    disk_gb = db.Column(db.Integer)
    prices = db.Column(db.Text, nullable=False, default='{}')

    @property
    def price_map(self):
        return json.loads(self.prices)


class AksControlPlane(db.Model):
    __tablename__ = 'aks_control_plane'
    id = db.Column(db.Integer, primary_key=True)
    tier = db.Column(db.Text, unique=True, nullable=False)
    prices = db.Column(db.Text, nullable=False, default='{}')

    @property
    def price_map(self):
        return json.loads(self.prices)


class AksSize(db.Model):
    __tablename__ = 'aks_sizes'
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.Text, unique=True, nullable=False, )
    os = db.Column(db.Text, nullable=False)
    size_slug = db.Column(db.Text, nullable=False)
    series = db.Column(db.Text)
    cores = db.Column(db.Integer)
    ram_gb = db.Column(db.Float)
    prices = db.Column(db.Text, nullable=False, default='{}')

    @property
    def price_map(self):
        return json.loads(self.prices)


class StorageSku(db.Model):
    __tablename__ = 'storage_skus'
    id = db.Column(db.Integer, primary_key=True)
    sku = db.Column(db.Text, unique=True, nullable=False, )
    unit = db.Column(db.Text, nullable=False)
    graduated = db.Column(db.Boolean, default=False)
    prices = db.Column(db.Text, nullable=False, default='{}')
    tiers = db.Column(db.Text, nullable=False, default='{}')

    @property
    def price_map(self):
        return json.loads(self.prices)

    @property
    def tier_map(self):
        return json.loads(self.tiers)


class CosmosSku(db.Model):
    __tablename__ = 'cosmos_skus'
    id = db.Column(db.Integer, primary_key=True)
    sku = db.Column(db.Text, unique=True, nullable=False, )
    prices = db.Column(db.Text, nullable=False, default='{}')

    @property
    def price_map(self):
        return json.loads(self.prices)


class FreeService(db.Model):
    __tablename__ = 'free_services'
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.Text, unique=True, nullable=False, )
    name = db.Column(db.Text, nullable=False)
    category = db.Column(db.Text, nullable=False, )
    period = db.Column(db.Text, nullable=False, )
    detail = db.Column(db.Text, default='')
    eyebrow = db.Column(db.Text, default='')
    href = db.Column(db.Text, default='')


class Story(db.Model):
    __tablename__ = 'stories'
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.Text, unique=True, nullable=False, )
    title = db.Column(db.Text, nullable=False)
    industries = db.Column(db.Text, nullable=False, default='[]')
    products = db.Column(db.Text, nullable=False, default='[]')
    quote_text = db.Column(db.Text, default='')
    quote_person = db.Column(db.Text, default='')
    quote_role = db.Column(db.Text, default='')
    quote_company = db.Column(db.Text, default='')
    header_image = db.Column(db.Text, default='')
    logo_image = db.Column(db.Text, default='')

    @property
    def industry_list(self):
        return json.loads(self.industries)

    @property
    def product_list(self):
        return json.loads(self.products)


class StoryPage(db.Model):
    __tablename__ = 'story_pages'
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.Text, unique=True, nullable=False, )
    title = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text, default='')
    sections = db.Column(db.Text, nullable=False, default='[]')

    @property
    def section_list(self):
        return json.loads(self.sections)


class BlogPost(db.Model):
    __tablename__ = 'blog_posts'
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.Text, unique=True, nullable=False, )
    title = db.Column(db.Text, nullable=False)
    content_type = db.Column(db.Text, default='')
    date = db.Column(db.Text)
    read_time = db.Column(db.Text, default='')
    image = db.Column(db.Text, default='')
    excerpt = db.Column(db.Text, default='')


class DictArticle(db.Model):
    __tablename__ = 'dict_articles'
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.Text, unique=True, nullable=False, )
    title = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text, default='')
    sections = db.Column(db.Text, nullable=False, default='[]')
    image = db.Column(db.Text, default='')

    @property
    def section_list(self):
        return json.loads(self.sections)


class SupportPlan(db.Model):
    __tablename__ = 'support_plans'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text, nullable=False)
    audience = db.Column(db.Text, default='')
    desc = db.Column(db.Text, default='')
    response = db.Column(db.Text, default='')


class Favorite(db.Model):
    __tablename__ = 'favorites'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    product_slug = db.Column(db.Text, nullable=False)
    created_ts = db.Column(db.Text, nullable=False, default=MIRROR_TS)

    __table_args__ = (db.UniqueConstraint('user_id', 'product_slug',
                                          name='uq_favorite_user_product'),)


class Estimate(db.Model):
    __tablename__ = 'estimates'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.Text, nullable=False)
    service = db.Column(db.Text, nullable=False)
    config = db.Column(db.Text, nullable=False, default='{}')
    monthly_usd = db.Column(db.Float, nullable=False, default=0.0)
    currency = db.Column(db.Text, nullable=False, default='usd')
    monthly_display = db.Column(db.Text, nullable=False, default='$0.00')
    created_ts = db.Column(db.Text, nullable=False, default=MIRROR_TS)

    @property
    def config_map(self):
        return json.loads(self.config)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# -------------------------------------------------------------------- seed --

def _seed_reference_data():
    """Load every tracked source snapshot into the reference tables."""
    site = _load('site.json')
    setting = SiteSetting(key='site', value=json.dumps(site))
    db.session.add(setting)
    free_meta = _load('free_services.json')
    db.session.add(SiteSetting(key='free_services',
                              value=json.dumps({'icons': free_meta.get('icons', [])})))
    regions_meta = _load('regions.json')
    db.session.add(SiteSetting(key='regions',
                              value=json.dumps({'images': regions_meta.get('images', []),
                                                'description': regions_meta.get('description', '')})))
    support_meta = _load('support.json')
    db.session.add(SiteSetting(key='support',
                              value=json.dumps({'images': support_meta.get('images', []),
                                                'description': support_meta.get('description', '')})))

    for p in _load('products.json'):
        db.session.add(Product(slug=p['slug'], name=p['name'], desc=p['desc'],
                               categories=json.dumps(p['categories']),
                               pricing_url=p['pricing_url']))
    page_slugs = set()
    for page in _load('product_pages.json'):
        page_slugs.add(page['slug'])
        db.session.add(ProductPage(
            slug=page['slug'], title=page['title'],
            description=page['description'],
            sections=json.dumps(page['sections']),
            docs_urls=json.dumps(page['docs_urls']),
            pricing_url=page['pricing_url'],
            related=json.dumps(page['related']),
            hero_image=page.get('hero_image') or '',
            content_images=json.dumps(page.get('content_images', []))))
    for prod in Product.query.all():
        prod.has_page = prod.slug in page_slugs

    for c in _load('pricing_cards.json'):
        db.session.add(PricingCard(name=c['name'], href=c['href'], icon=c['icon']))
    for t in _load('pricing_details.json'):
        db.session.add(PricingTable(page=t['page'], idx=t['index'],
                                    header=json.dumps(t['header']),
                                    rows=json.dumps(t['rows'])))

    calc = _load('calculator.json')
    regions_meta = _load('regions.json')
    for g in calc['geographies']:
        db.session.add(Geography(slug=g['slug'], display_name=g['display_name']))
    for g in calc['geographies']:
        for r in g['regions']:
            db.session.add(Region(slug=r, display_name=calc['region_names'][r],
                                  geo_slug=g['slug'],
                                  services=json.dumps(
                                      {svc: counts.get(r, 0) > 0
                                       for svc, counts in
                                       regions_meta['service_availability'].items()})))
    for code, c in calc['currencies'].items():
        db.session.add(Currency(code=code, name=c['name'], glyph=c['glyph'],
                                display_name=c['display_name'],
                                conversion=c['conversion']))
    for s in calc['vm_sizes']:
        db.session.add(VmSize(key=s['key'], os=s['os'], size_slug=s['size_slug'],
                              series=s['series'], cores=s['cores'],
                              ram_gb=s['ram_gb'], disk_gb=s.get('disk_gb'),
                              prices=json.dumps(s['prices'])))
    for tier, prices in calc['aks_control_plane'].items():
        db.session.add(AksControlPlane(tier=tier, prices=json.dumps(prices)))
    for s in calc['aks_sizes']:
        db.session.add(AksSize(key=s['key'], os=s['os'], size_slug=s['size_slug'],
                               series=s['series'], cores=s['cores'],
                               ram_gb=s['ram_gb'], prices=json.dumps(s['prices'])))
    for s in calc['storage_skus']:
        db.session.add(StorageSku(sku=s['sku'], unit=s['unit'],
                                  graduated=bool(s.get('graduated')),
                                  prices=json.dumps(s.get('prices', {})),
                                  tiers=json.dumps(s.get('tiers', {}))))
    for s in calc['cosmos_skus']:
        db.session.add(CosmosSku(sku=s['sku'], prices=json.dumps(s['prices'])))

    for f in _load('free_services.json')['items']:
        slug = f['id']
        if FreeService.query.filter_by(slug=slug).first():
            # The live feed lists a few services twice (once per free period);
            # keep both rows under distinct slugs.
            base, n = slug, 2
            while FreeService.query.filter_by(slug=f'{base}--{n}').first():
                n += 1
            slug = f'{base}--{n}'
        db.session.add(FreeService(slug=slug, name=f['name'],
                                   category=f['category'] or 'General',
                                   period=f['period'], detail=f['detail'],
                                   eyebrow=f['eyebrow'], href=f['href']))

    for s in _load('stories.json'):
        db.session.add(Story(slug=s['slug'], title=s['title'],
                             industries=json.dumps(s['industries']),
                             products=json.dumps(s['products']),
                             quote_text=s['quote_text'],
                             quote_person=s['quote_person'],
                             quote_role=s['quote_role'],
                             quote_company=s['quote_company'],
                             header_image=s['header_image'],
                             logo_image=s['logo_image']))
    for p in _load('story_pages.json'):
        db.session.add(StoryPage(slug=p['slug'], title=p['title'],
                                 description=p['description'],
                                 sections=json.dumps(p['sections'])))
    for b in _load('blog.json'):
        db.session.add(BlogPost(slug=b['slug'], title=b['title'],
                                content_type=b['content_type'], date=b['date'],
                                read_time=b['read_time'], image=b['image'],
                                excerpt=b['excerpt']))
    for d in _load('dictionary.json'):
        db.session.add(DictArticle(slug=d['slug'], title=d['title'],
                                   description=d['description'],
                                   sections=json.dumps(d['sections']),
                                   image=d['image']))
    for sp in _load('support.json')['plans']:
        db.session.add(SupportPlan(name=sp['name'], audience=sp['audience'],
                                   desc=sp['desc'], response=sp['response']))
    db.session.commit()


class SiteSetting(db.Model):
    __tablename__ = 'site_settings'
    key = db.Column(db.Text, primary_key=True)
    value = db.Column(db.Text, nullable=False)

    @property
    def parsed(self):
        return json.loads(self.value)


def _seed_users():
    for u in _load('users.json'):
        db.session.add(User(name=u['name'], email=u['email'],
                            pw_hash=BENCHMARK_PASSWORD_HASH, role=u['role']))
    db.session.commit()


DETERMINISTIC_INDEXES = [
    'CREATE INDEX IF NOT EXISTS ix_aks_sizes_key ON aks_sizes (key)',
    'CREATE INDEX IF NOT EXISTS ix_blog_posts_slug ON blog_posts (slug)',
    'CREATE INDEX IF NOT EXISTS ix_cosmos_skus_sku ON cosmos_skus (sku)',
    'CREATE INDEX IF NOT EXISTS ix_dict_articles_slug ON dict_articles (slug)',
    'CREATE INDEX IF NOT EXISTS ix_free_services_category ON free_services (category)',
    'CREATE INDEX IF NOT EXISTS ix_free_services_period ON free_services (period)',
    'CREATE INDEX IF NOT EXISTS ix_free_services_slug ON free_services (slug)',
    'CREATE INDEX IF NOT EXISTS ix_pricing_tables_page ON pricing_tables (page)',
    'CREATE INDEX IF NOT EXISTS ix_product_pages_slug ON product_pages (slug)',
    'CREATE INDEX IF NOT EXISTS ix_products_slug ON products (slug)',
    'CREATE INDEX IF NOT EXISTS ix_regions_geo_slug ON regions (geo_slug)',
    'CREATE INDEX IF NOT EXISTS ix_regions_slug ON regions (slug)',
    'CREATE INDEX IF NOT EXISTS ix_stories_slug ON stories (slug)',
    'CREATE INDEX IF NOT EXISTS ix_story_pages_slug ON story_pages (slug)',
    'CREATE INDEX IF NOT EXISTS ix_storage_skus_sku ON storage_skus (sku)',
    'CREATE INDEX IF NOT EXISTS ix_users_email ON users (email)',
    'CREATE INDEX IF NOT EXISTS ix_vm_sizes_key ON vm_sizes (key)',
]


def _bootstrap():
    if os.environ.get('WEBSYN_SKIP_BOOTSTRAP'):
        return
    with app.app_context():
        db.create_all()
        # SQLAlchemy's table.indexes set iterates by object identity, so
        # multiple indexes per table would be created in a per-run order;
        # create every index explicitly in sorted name order instead so
        # the seed file is byte-reproducible.
        with db.engine.begin() as conn:
            for stmt in DETERMINISTIC_INDEXES:
                conn.exec_driver_sql(stmt)
        if User.query.count() == 0:
            _seed_users()
        if SiteSetting.query.count() == 0:
            _seed_reference_data()


_bootstrapped = False


def _ensure_bootstrap():
    global _bootstrapped
    if not _bootstrapped:
        _bootstrap()
        _bootstrapped = True


_ensure_bootstrap()


# ------------------------------------------------------------------ helpers --

def _money(value, currency_code='usd'):
    cur = Currency.query.filter_by(code=currency_code).first()
    glyph = H.unescape(cur.glyph) if cur else '$'
    converted = value * (cur.conversion if cur else 1.0)
    return f"{glyph}{converted:,.2f}"


def _now_iso():
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def _graduated_cost(tiers, quantity):
    """Tiered (graduated) pricing: each tier price applies to the quantity
    between the previous limit and this tier's limit (limit=None = infinity)."""
    total = 0.0
    remaining = float(quantity)
    prev_limit = 0.0
    for tier in tiers:
        limit = tier.get('limit_gb')
        span = (limit - prev_limit) if limit is not None else remaining
        span = max(0.0, min(remaining, span))
        total += span * float(tier['price'])
        remaining -= span
        prev_limit = limit if limit is not None else prev_limit
        if remaining <= 0:
            break
    return total


def _compute_vm_estimate(size_key, region, quantity, hours, currency):
    size = VmSize.query.filter_by(key=size_key).first()
    if not size or region not in size.price_map:
        return None
    per_hour = size.price_map[region]
    monthly = per_hour * float(hours or HOURS_PER_MONTH) * int(quantity)
    return {
        'service': 'virtual-machines',
        'lines': [
            {'label': f"{size.size_slug.upper()} ({size.os.capitalize()}) × {quantity} "
                      f"× {hours} h",
             'rate': per_hour, 'amount': monthly},
        ],
        'monthly': monthly,
        'currency': currency,
    }


def _compute_aks_estimate(tier, size_key, region, node_count, hours, currency):
    control = AksControlPlane.query.filter_by(tier=tier).first()
    size = AksSize.query.filter_by(key=size_key).first()
    if not size or region not in size.price_map:
        return None
    control_rate = control.price_map.get(region) if control else None
    if control_rate is None:
        return None
    hrs = float(hours or HOURS_PER_MONTH)
    control_cost = control_rate * hrs
    node_cost = size.price_map[region] * hrs * int(node_count)
    monthly = control_cost + node_cost
    return {
        'service': 'kubernetes-service',
        'lines': [
            {'label': f"Control plane — {tier} ({region})",
             'rate': control_rate, 'amount': control_cost},
            {'label': f"Node pool — {size.size_slug.upper()} ({size.os.capitalize()}) "
                      f"× {node_count} × {hrs} h",
             'rate': size.price_map[region], 'amount': node_cost},
        ],
        'monthly': monthly,
        'currency': currency,
    }


STORAGE_LABELS = {
    'general-purpose-v2-block-blob-structured-hot-lrs': 'Block blob — Hot (LRS)',
    'general-purpose-v2-block-blob-structured-cool-lrs': 'Block blob — Cool (LRS)',
    'general-purpose-v2-block-blob-structured-cool-zrs': 'Block blob — Cool (ZRS)',
    'general-purpose-v2-block-blob-structured-cool-gzrs': 'Block blob — Cool (GZRS)',
    'general-purpose-v2-block-blob-structured-cool-ra-gzrs': 'Block blob — Cool (RA-GZRS)',
    'general-purpose-v2-block-blob-structured-archive-lrs': 'Block blob — Archive (LRS)',
}
WRITE_LABEL = 'Write operations (per 10k)'
READ_LABEL = 'Read operations (per 10k)'


def _compute_storage_estimate(region, capacity_gb, write_10k, read_10k, currency):
    hot = StorageSku.query.filter_by(
        sku='general-purpose-v2-block-blob-structured-hot-lrs').first()
    writes = StorageSku.query.filter_by(
        sku='general-purpose-v2-block-blob-structured-hot-lrs-write-operations').first()
    reads = StorageSku.query.filter_by(
        sku='general-purpose-v2-block-blob-structured-hot-lrs-read-operations').first()
    if not hot or region not in hot.tier_map:
        return None
    capacity_cost = _graduated_cost(hot.tier_map[region], capacity_gb)
    write_cost = (writes.price_map.get(region, 0.0) * float(write_10k)) if writes else 0.0
    read_cost = (reads.price_map.get(region, 0.0) * float(read_10k)) if reads else 0.0
    monthly = capacity_cost + write_cost + read_cost
    return {
        'service': 'storage',
        'lines': [
            {'label': f"Hot block blob capacity — {float(capacity_gb):,.0f} GB "
                      f"(graduated tiers)",
             'rate': None, 'amount': capacity_cost},
            {'label': f"Write operations — {float(write_10k):,.0f} × 10k",
             'rate': writes.price_map.get(region) if writes else None,
             'amount': write_cost},
            {'label': f"Read operations — {float(read_10k):,.0f} × 10k",
             'rate': reads.price_map.get(region) if reads else None,
             'amount': read_cost},
        ],
        'monthly': monthly,
        'currency': currency,
    }


COSMOS_MODES = ('single', 'multiple', 'serverless')


def _compute_cosmos_estimate(region, mode, ru_s, storage_gb, gateway, currency):
    storage_sku = CosmosSku.query.filter_by(sku='storage').first()
    gateway_sku = CosmosSku.query.filter_by(
        sku='dedicated-gateway-d4s').first()
    if mode in ('single', 'multiple'):
        mode_sku = CosmosSku.query.filter_by(sku=mode).first()
        if not mode_sku or region not in mode_sku.price_map.get('perhour', {}):
            return None
        ru_cost = mode_sku.price_map['perhour'][region] * (float(ru_s) / 100.0) \
            * HOURS_PER_MONTH
        ru_label = (f"Provisioned throughput — {float(ru_s):,.0f} RU/s "
                    f"({'single-region' if mode == 'single' else 'multi-region'} writes)")
        ru_rate = mode_sku.price_map['perhour'][region]
    else:
        ru_cost = 0.0
        ru_label = None
        ru_rate = None
    storage_cost = storage_sku.price_map['pergb'].get(region, 0.0) * float(storage_gb) \
        if storage_sku else 0.0
    gateway_cost = 0.0
    gateway_rate = None
    if gateway == 'yes' and gateway_sku and region in gateway_sku.price_map.get('perhour', {}):
        gateway_rate = gateway_sku.price_map['perhour'][region]
        gateway_cost = gateway_rate * HOURS_PER_MONTH
    monthly = ru_cost + storage_cost + gateway_cost
    lines = []
    if ru_label:
        lines.append({'label': ru_label, 'rate': ru_rate, 'amount': ru_cost})
    lines.append({'label': f"Storage — {float(storage_gb):,.0f} GB",
                  'rate': storage_sku.price_map['pergb'].get(region) if storage_sku else None,
                  'amount': storage_cost})
    if gateway_cost:
        lines.append({'label': "Dedicated gateway — D4s",
                      'rate': gateway_rate, 'amount': gateway_cost})
    return {
        'service': 'cosmos-db',
        'lines': lines,
        'monthly': monthly,
        'currency': currency,
    }


# ------------------------------------------------------------------- routes --

@app.context_processor
def _ctx():
    return {
        'brand': BRAND,
        'short': SHORT,
        'upstream': UPSTREAM,
        'mirror_ts': MIRROR_TS,
        'img': _img,
    }


@app.route('/_health')
def health():
    counts = {
        'products': Product.query.count(),
        'product_categories': len(
            {c for p in Product.query.all() for c in p.category_list}),
        'product_pages': ProductPage.query.count(),
        'pricing_cards': PricingCard.query.count(),
        'calc_services': 4,
        'regions': Region.query.count(),
        'free_services': FreeService.query.count(),
        'stories': Story.query.count(),
        'story_industries': len({i for s in Story.query.all()
                                 for i in s.industry_list}),
        'blog_posts': BlogPost.query.count(),
        'dict_articles': DictArticle.query.count(),
        'support_plans': SupportPlan.query.count(),
        'users': User.query.count(),
        'vm_prices': sum(len(v.price_map) for v in VmSize.query.all()),
        'ok': True,
        'site': SITE_NAME,
    }
    return jsonify(counts)


@app.route('/')
def home():
    site = json.loads(SiteSetting.query.filter_by(key='site').first().value)
    featured = []
    for f in site.get('featured_products', []):
        prod = Product.query.filter_by(slug=f['slug']).first()
        if prod:
            featured.append(prod)
    stories = Story.query.order_by(Story.id).limit(6).all()
    posts = BlogPost.query.order_by(BlogPost.date.desc()).limit(3).all()
    regions = Region.query.count()
    geos = Geography.query.count()
    products = Product.query.count()
    return render_template('home.html', site=site, featured=featured,
                           stories=stories, posts=posts, regions=regions,
                           geos=geos, product_count=products,
                           home_images=site.get('home_images', []))


@app.route('/products/')
def products():
    category = request.args.get('category', '').strip()
    q = request.args.get('q', '').strip()
    query = Product.query
    if category:
        query = query.filter(Product.categories.contains(f'"{category}"'))
    if q:
        query = query.filter(Product.name.ilike(f'%{q}%'))
    items = query.order_by(Product.name).all()
    cats = sorted({c for p in Product.query.all() for c in p.category_list})
    site = json.loads(SiteSetting.query.filter_by(key='site').first().value)
    return render_template('products.html', items=items, cats=cats,
                           active_category=category, q=q,
                           hero_image=site.get('products_hero'))


@app.route('/products/<slug>/')
def product_detail(slug):
    prod = Product.query.filter_by(slug=slug).first_or_404()
    page = ProductPage.query.filter_by(slug=slug).first()
    related = [Product.query.filter_by(slug=s).first()
               for s in (page.related_list if page else [])]
    related = [r for r in related if r][:6]
    pricing_card = PricingCard.query.filter(
        PricingCard.href.contains(f'/{slug}/')).first()
    return render_template('product_detail.html', prod=prod, page=page,
                           related=related, pricing_card=pricing_card)


@app.route('/pricing/')
def pricing():
    cards = PricingCard.query.order_by(PricingCard.id).all()
    return render_template('pricing.html', cards=cards)


PRICING_DETAIL_PAGES = {
    'kubernetes-service': 'Azure Kubernetes Service (AKS)',
    'virtual-machines-linux': 'Linux Virtual Machines',
    'cosmos-db': 'Azure Cosmos DB',
    'managed-disks': 'Managed Disks',
}

# The captured pricing hub links the Azure Virtual Machines card to the
# upstream URL /en-us/pricing/details/virtual-machines/; the mirror's
# captured details page for that service is the Linux Virtual Machines
# page, so the canonical VM pricing URL maps to it (301) instead of 404.
PRICING_DETAIL_ALIASES = {
    'virtual-machines': 'virtual-machines-linux',
}


@app.route('/pricing/details/<page>/')
def pricing_details(page):
    page = PRICING_DETAIL_ALIASES.get(page, page)
    if page not in PRICING_DETAIL_PAGES:
        abort(404)
    tables = PricingTable.query.filter_by(page=page).order_by(PricingTable.idx).all()
    return render_template('pricing_details.html', page=page,
                           title=PRICING_DETAIL_PAGES[page], tables=tables)


@app.route('/pricing/details/virtual-machines/')
def pricing_details_vm_alias():
    return redirect(url_for('pricing_details', page='virtual-machines-linux'),
                    code=301)


@app.route('/pricing/free-services/')
def free_services():
    category = request.args.get('category', '').strip()
    period = request.args.get('period', '').strip()
    query = FreeService.query
    if category:
        query = query.filter_by(category=category)
    if period:
        query = query.filter_by(period=period)
    items = query.order_by(FreeService.name).all()
    cats = sorted({c[0] for c in db.session.query(FreeService.category).distinct()
                   if c[0]})
    periods = sorted({p[0] for p in db.session.query(FreeService.period).distinct()
                      if p[0]})
    meta = json.loads(SiteSetting.query.filter_by(key='free_services').first().value)
    return render_template('free_services.html', items=items, cats=cats,
                           periods=periods, active_category=category,
                           active_period=period, icons=meta.get('icons', []))


@app.route('/pricing/calculator/', methods=['GET', 'POST'])
def calculator():
    if request.method == 'POST':
        service = request.form.get('service', '')
    else:
        service = request.args.get('service', 'virtual-machines')
    if service not in ('virtual-machines', 'kubernetes-service', 'storage',
                      'cosmos-db'):
        service = 'virtual-machines'
    vm_sizes = VmSize.query.order_by(VmSize.os.desc(), VmSize.size_slug).all()
    aks_sizes = AksSize.query.order_by(AksSize.os.desc(), AksSize.size_slug).all()
    control_tiers = AksControlPlane.query.order_by(AksControlPlane.id).all()
    regions = Region.query.order_by(Region.slug).all()
    currencies = Currency.query.order_by(Currency.code).all()
    estimate = None
    error = None
    if request.method == 'POST':
        currency = request.form.get('currency', 'usd')
        try:
            if service == 'virtual-machines':
                estimate = _compute_vm_estimate(
                    request.form.get('size', ''), request.form.get('region', ''),
                    request.form.get('quantity', '1'),
                    request.form.get('hours', str(HOURS_PER_MONTH)), currency)
            elif service == 'kubernetes-service':
                estimate = _compute_aks_estimate(
                    request.form.get('tier', 'SLA'),
                    request.form.get('size', ''), request.form.get('region', ''),
                    request.form.get('nodes', '3'),
                    request.form.get('hours', str(HOURS_PER_MONTH)), currency)
            elif service == 'storage':
                estimate = _compute_storage_estimate(
                    request.form.get('region', ''),
                    request.form.get('capacity_gb', '1024'),
                    request.form.get('write_10k', '100'),
                    request.form.get('read_10k', '1000'), currency)
            elif service == 'cosmos-db':
                estimate = _compute_cosmos_estimate(
                    request.form.get('region', ''),
                    request.form.get('mode', 'single'),
                    request.form.get('ru_s', '400'),
                    request.form.get('storage_gb', '100'),
                    request.form.get('gateway', 'no'), currency)
            if estimate is None:
                error = ('That combination is not available in the selected '
                         'region — pick another region, size or tier.')
        except (ValueError, TypeError):
            error = 'Invalid quantity — please enter whole numbers.'
    if estimate is not None:
        estimate['monthly_display'] = _money(estimate['monthly'], estimate['currency'])
    form = request.form if request.method == 'POST' else {}
    return render_template('calculator.html', vm_sizes=vm_sizes,
                           aks_sizes=aks_sizes, control_tiers=control_tiers,
                           regions=regions, currencies=currencies,
                           estimate=estimate, error=error, service=service,
                           form=form)


@app.route('/pricing/calculator/save', methods=['POST'])
@login_required
def save_estimate():
    service = request.form.get('service', '')
    currency = request.form.get('currency', 'usd')
    estimate = None
    if service == 'virtual-machines':
        estimate = _compute_vm_estimate(
            request.form.get('size', ''), request.form.get('region', ''),
            request.form.get('quantity', '1'),
            request.form.get('hours', str(HOURS_PER_MONTH)), currency)
    elif service == 'kubernetes-service':
        estimate = _compute_aks_estimate(
            request.form.get('tier', 'SLA'), request.form.get('size', ''),
            request.form.get('region', ''), request.form.get('nodes', '3'),
            request.form.get('hours', str(HOURS_PER_MONTH)), currency)
    elif service == 'storage':
        estimate = _compute_storage_estimate(
            request.form.get('region', ''),
            request.form.get('capacity_gb', '1024'),
            request.form.get('write_10k', '100'),
            request.form.get('read_10k', '1000'), currency)
    elif service == 'cosmos-db':
        estimate = _compute_cosmos_estimate(
            request.form.get('region', ''), request.form.get('mode', 'single'),
            request.form.get('ru_s', '400'), request.form.get('storage_gb', '100'),
            request.form.get('gateway', 'no'), currency)
    if estimate is None:
        flash('That estimate is not available in the selected region.', 'error')
        return redirect(url_for('calculator'))
    config = {k: v for k, v in request.form.items()
              if k not in ('csrf_token', 'service', 'currency')}
    est = Estimate(user_id=current_user.id,
                   name=request.form.get('name', 'Untitled estimate') or 'Untitled estimate',
                   service=service,
                   config=json.dumps(config, sort_keys=True),
                   monthly_usd=round(estimate['monthly'], 2),
                   currency=currency,
                   monthly_display=_money(estimate['monthly'], currency),
                   created_ts=_now_iso())
    db.session.add(est)
    db.session.commit()
    flash(f"Estimate “{est.name}” saved to your account.", 'success')
    return redirect(url_for('account'))


@app.route('/account/estimates/<int:estimate_id>/delete', methods=['POST'])
@login_required
def delete_estimate(estimate_id):
    est = Estimate.query.filter_by(id=estimate_id, user_id=current_user.id).first_or_404()
    db.session.delete(est)
    db.session.commit()
    flash('Estimate deleted.', 'success')
    return redirect(url_for('account'))


@app.route('/explore/global-infrastructure/geographies/')
def geographies():
    geos = Geography.query.order_by(Geography.display_name).all()
    regions_by_geo = {}
    for g in geos:
        regions_by_geo[g.slug] = Region.query.filter_by(geo_slug=g.slug) \
            .order_by(Region.display_name).all()
    meta = json.loads(SiteSetting.query.filter_by(key='regions').first().value)
    return render_template('geographies.html', geos=geos,
                           regions_by_geo=regions_by_geo,
                           images=meta.get('images', []),
                           description=meta.get('description', ''))


@app.route('/explore/global-infrastructure/geographies/<slug>/')
def geography_detail(slug):
    geo = Geography.query.filter_by(slug=slug).first_or_404()
    regions = Region.query.filter_by(geo_slug=slug).order_by(Region.display_name).all()
    return render_template('geography_detail.html', geo=geo, regions=regions)


PBR_SERVICES = {
    'virtual-machines': ('Virtual Machines', VmSize, 'price_map'),
    'kubernetes-service': ('Kubernetes Service node sizes', AksSize, 'price_map'),
}


@app.route('/explore/global-infrastructure/products-by-region/')
def products_by_region():
    service = request.args.get('service', 'virtual-machines')
    compare = [r for r in request.args.getlist('region') if r][:4]
    if service not in PBR_SERVICES:
        service = 'virtual-machines'
    label, model, _attr = PBR_SERVICES[service]
    # availability: number of SKUs priced per region
    avail = {}
    for row in model.query.all():
        for region_slug in getattr(row, _attr):
            avail.setdefault(region_slug, 0)
            avail[region_slug] += 1
    regions = Region.query.order_by(Region.display_name).all()
    rows = [{'region': r, 'available': avail.get(r.slug, 0)} for r in regions]
    rows.sort(key=lambda x: (-x['available'], x['region'].display_name))
    comparison = []
    if compare:
        if service == 'virtual-machines':
            sizes = VmSize.query.order_by(VmSize.key).all()
        else:
            sizes = AksSize.query.order_by(AksSize.key).all()
        for s in sizes:
            if all(region in s.price_map for region in compare):
                comparison.append({'size': s,
                                    'prices': {r: s.price_map[r] for r in compare}})
    region_names = {r.slug: r.display_name for r in Region.query.all()}
    return render_template('products_by_region.html', service=service,
                           label=label, rows=rows, compare=compare,
                           comparison=comparison,
                           region_names=region_names)


@app.route('/customer-stories/')
def customer_stories():
    industry = request.args.get('industry', '').strip()
    product = request.args.get('product', '').strip()
    q = request.args.get('q', '').strip().lower()
    query = Story.query
    if industry:
        query = query.filter(Story.industries.contains(f'"{industry}"'))
    if product:
        query = query.filter(Story.products.contains(f'"{product}"'))
    items = query.order_by(Story.id).all()
    if q:
        items = [s for s in items if q in s.title.lower()
                 or any(q in p.lower() for p in s.product_list)
                 or any(q in i.lower() for i in s.industry_list)]
    industries = sorted({i for s in Story.query.all() for i in s.industry_list})
    products_facet = sorted({p for s in Story.query.all() for p in s.product_list})
    return render_template('customer_stories.html', items=items,
                           industries=industries, products_facet=products_facet,
                           active_industry=industry, active_product=product, q=q)


@app.route('/customer-stories/<slug>/')
def customer_story(slug):
    story = Story.query.filter_by(slug=slug).first_or_404()
    page = StoryPage.query.filter_by(slug=slug).first()
    related = [s for s in Story.query.filter(
        Story.slug != slug).all()
        if set(s.industry_list) & set(story.industry_list)][:3]
    return render_template('story_detail.html', story=story, page=page,
                           related=related)


@app.route('/blog/')
def blog():
    category = request.args.get('category', '').strip()
    query = BlogPost.query
    if category:
        query = query.filter_by(content_type=category)
    items = query.order_by(BlogPost.date.desc()).all()
    cats = sorted({c[0] for c in db.session.query(BlogPost.content_type).distinct()
                   if c[0]})
    return render_template('blog.html', items=items, cats=cats,
                           active_category=category)


@app.route('/blog/<slug>/')
def blog_post(slug):
    post = BlogPost.query.filter_by(slug=slug).first_or_404()
    return render_template('blog_post.html', post=post)


@app.route('/resources/cloud-computing-dictionary/')
def dictionary():
    q = request.args.get('q', '').strip().lower()
    items = DictArticle.query.order_by(DictArticle.title).all()
    if q:
        items = [a for a in items if q in a.title.lower()
                 or q in a.description.lower()]
    return render_template('dictionary.html', items=items, q=q)


@app.route('/resources/cloud-computing-dictionary/<slug>/')
def dictionary_article(slug):
    article = DictArticle.query.filter_by(slug=slug).first_or_404()
    others = DictArticle.query.filter(DictArticle.slug != slug) \
        .order_by(DictArticle.title).limit(6).all()
    return render_template('dictionary_article.html', article=article,
                           others=others)


@app.route('/support/')
def support():
    plans = SupportPlan.query.order_by(SupportPlan.id).all()
    meta = json.loads(SiteSetting.query.filter_by(key='support').first().value)
    return render_template('support.html', plans=plans,
                           images=meta.get('images', []),
                           description=meta.get('description', ''))


@app.route('/search/')
def search():
    q = request.args.get('q', '').strip()
    results = {'products': [], 'stories': [], 'blog': [], 'dictionary': []}
    if q:
        like = f'%{q}%'
        results['products'] = Product.query.filter(Product.name.ilike(like)) \
            .order_by(Product.name).limit(10).all()
        results['stories'] = Story.query.filter(Story.title.ilike(like)) \
            .order_by(Story.id).limit(10).all()
        results['blog'] = BlogPost.query.filter(BlogPost.title.ilike(like)) \
            .order_by(BlogPost.date.desc()).limit(10).all()
        results['dictionary'] = DictArticle.query.filter(
            DictArticle.title.ilike(like)).order_by(DictArticle.title).limit(10).all()
    total = sum(len(v) for v in results.values())
    return render_template('search.html', q=q, results=results, total=total)


# ----------------------------------------------------------------- accounts --

@app.route('/account/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        if not name or not email or len(password) < 8:
            flash('Name, email and a password of at least 8 characters are required.',
                  'error')
        elif User.query.filter_by(email=email).first():
            flash('An account with that email already exists.', 'error')
        else:
            user = User(name=name, email=email,
                        pw_hash=bcrypt.generate_password_hash(password).decode('utf-8'),
                        role='Member')
            db.session.add(user)
            db.session.commit()
            login_user(user)
            flash(f'Welcome to Azure, {name}! Your account is ready.', 'success')
            return redirect(url_for('account'))
    return render_template('signup.html')


@app.route('/account/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        user = User.query.filter_by(email=email).first()
        if user and bcrypt.check_password_hash(user.pw_hash, password):
            login_user(user)
            flash(f'Signed in as {user.name}.', 'success')
            return redirect(request.args.get('next') or url_for('account'))
        flash('Invalid email or password.', 'error')
    return render_template('login.html')


@app.route('/account/logout')
@login_required
def logout():
    logout_user()
    flash('You have signed out of Azure.', 'success')
    return redirect(url_for('home'))


@app.route('/account/')
@login_required
def account():
    estimates = Estimate.query.filter_by(user_id=current_user.id) \
        .order_by(Estimate.id.desc()).all()
    favorites = Favorite.query.filter_by(user_id=current_user.id).all()
    fav_products = [Product.query.filter_by(slug=f.product_slug).first()
                    for f in favorites]
    fav_products = [p for p in fav_products if p]
    return render_template('account.html', estimates=estimates,
                           favorites=favorites, fav_products=fav_products)


@app.route('/favorites/toggle', methods=['POST'])
@login_required
def toggle_favorite():
    slug = request.form.get('product_slug', '')
    prod = Product.query.filter_by(slug=slug).first()
    if not prod:
        abort(404)
    existing = Favorite.query.filter_by(user_id=current_user.id,
                                         product_slug=slug).first()
    if existing:
        db.session.delete(existing)
        db.session.commit()
        flash(f'Removed {prod.name} from your favorites.', 'success')
    else:
        db.session.add(Favorite(user_id=current_user.id, product_slug=slug,
                                created_ts=_now_iso()))
        db.session.commit()
        flash(f'Added {prod.name} to your favorites.', 'success')
    return redirect(request.form.get('next') or url_for('product_detail', slug=slug))


@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404


# -------------------------------------------------------------------- main --

def main():
    """Build the seed database (idempotent)."""
    _ensure_bootstrap()
    with app.app_context():
        db.create_all()
        if User.query.count() == 0:
            _seed_users()
        if SiteSetting.query.count() == 0:
            _seed_reference_data()
        print('[seed] microsoft_azure reference data ready')


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'serve':
        app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
    else:
        main()
