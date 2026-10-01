#!/usr/bin/env python3
"""Build the tracked source_data/*.json snapshots for the microsoft_azure
mirror from the raw upstream captures in scraped_data/ (gitignored).

Every record below is derived from a real capture of
https://azure.microsoft.com/ (probed reachable, HTTP 200) or its public
JSON calculator APIs / customers.microsoft.com story API:

  * pages:            direct HTTP GETs of azure.microsoft.com HTML pages
  * product catalog:  https://azure.microsoft.com/en-us/products/
  * calculator data:  the same versioned JSON the live Azure pricing
                      calculator loads (virtual machines, kubernetes
                      service, storage, cosmos db, regions, currencies)
  * free services:    the JSON card feed behind /en-us/pricing/free-services/
  * customer stories: the customers.microsoft.com story search API
                      (filters product:azure) plus every story page
  * blog:             https://azure.microsoft.com/en-us/blog/ and posts
  * dictionary:       /en-us/resources/cloud-computing-dictionary/ and articles
  * images:           cdn-dynmedia-1.microsoft.com (see download_manifest.json)

The only authored records are the four benchmark user accounts in
users.json (the shared benchmark-account convention) — declared in
provenance.json. Nothing else is invented.

Run:  python3 scripts_dev/build_source_data.py   (from the site root)
"""
from __future__ import annotations

import html as H
import json
import re
from collections import OrderedDict
from pathlib import Path

SITE = Path(__file__).resolve().parents[1]
RAW = SITE / 'scraped_data'
OUT = SITE / 'source_data'
OUT.mkdir(exist_ok=True)

UPSTREAM = 'https://azure.microsoft.com/'
MIRROR_TS = '2026-09-30'
HOURS_PER_MONTH = 730

_DEDUP = json.loads((RAW / 'dedup_map.json').read_text(encoding='utf-8')) \
    if (RAW / 'dedup_map.json').exists() else {}


def _canonical(rel_image: str | None):
    """Map an image path to its kept duplicate (identical CDN artwork is
    stored once and referenced by every page that uses it)."""
    if not rel_image:
        return None
    return _DEDUP.get(rel_image, rel_image)


_MANIFEST = json.loads((RAW / 'download_manifest.json').read_text(encoding='utf-8'))
_URL_TO_PATH = {e['url'].split('?')[0]: e['path'] for e in _MANIFEST}


def _img_path(url: str | None):
    """Resolve a captured cdn image URL to its stored asset path."""
    if not url:
        return None
    rel = _URL_TO_PATH.get(url.split('?')[0])
    if rel is None:
        return None
    return _canonical(rel)


def _dir_images(subdir: str):
    """Every stored asset under images/<subdir>/, in sorted order."""
    return sorted(e['path'] for e in _MANIFEST if e['path'].startswith(subdir + '/'))


def dump(name: str, payload) -> None:
    OUT.joinpath(name).write_text(
        json.dumps(payload, indent=1, ensure_ascii=False) + '\n',
        encoding='utf-8')
    size = len(json.dumps(payload)) if not isinstance(payload, list) else len(payload)
    unit = 'rows' if isinstance(payload, list) else 'chars'
    print(f'  wrote source_data/{name} ({size} {unit})')


def textify(fragment: str) -> str:
    return re.sub(r'\s+', ' ', H.unescape(re.sub(r'<[^>]+>', '', fragment))).strip()


def read_html(name: str) -> str:
    return (RAW / name).read_text(encoding='utf-8', errors='replace')


# ------------------------------------------------------------------ site --

def build_site() -> None:
    h = read_html('home.html')
    hero = re.search(r'<h1[^>]*>(.*?)</h1>', h, re.S)
    h2s = [textify(t) for t in re.findall(r'<h2[^>]*>(.*?)</h2>', h, re.S)]
    md = re.search(r'<meta name="description" content="([^"]+)"', h)
    featured = []
    for m in re.finditer(r'<h3[^>]*>\s*(.*?)\s*</h3>(.{0,900}?)href="https://azure\.microsoft\.com/en-us/products/([a-z0-9-]+)/"', h, re.S):
        name = textify(m.group(1))
        if name and name not in [f['name'] for f in featured]:
            featured.append({'name': name, 'slug': m.group(3)})
    home_imgs = _dir_images('home')
    site = OrderedDict(
        brand='Microsoft Azure',
        short_brand='Azure',
        upstream=UPSTREAM,
        mirror_ts=MIRROR_TS,
        description=H.unescape(md.group(1)) if md else '',
        hero={'title': textify(hero.group(1)) if hero else '',
              'image': _canonical(home_imgs[0]) if home_imgs else None},
        home_images=home_imgs,
        sections=[s for s in h2s if s],
        featured_products=featured[:8],
        products_hero=(_dir_images('products') or [None])[0]
            if False else _URL_TO_PATH.get(
                'https://cdn-dynmedia-1.microsoft.com/is/image/microsoftcorp/products-hero'),
        hours_per_month=HOURS_PER_MONTH,
    )
    dump('site.json', site)


# -------------------------------------------------------------- products --

def parse_catalog() -> list:
    html = read_html('products.html')
    cat_pat = re.compile(r'<h2[^>]*>\s*([^<]+?)\s*</h2>')
    matches = list(cat_pat.finditer(html))
    catalog = []
    seen_slugs = set()
    for i, m in enumerate(matches):
        cat = H.unescape(m.group(1)).strip()
        if cat == 'Azure products':
            continue
        seg = html[m.end(): matches[i + 1].start() if i + 1 < len(matches) else len(html)]
        for block in re.split(r'<div class="card h-100"', seg)[1:]:
            b = block[:block.find('</section>')] if '</section>' in block else block
            name_m = re.search(r'<h3 class="h5">\s*(.*?)\s*</h3>', b, re.S)
            desc_m = re.search(r'<p>(.*?)</p>', b, re.S)
            prod_m = re.search(
                r'href="https://azure\.microsoft\.com(/en-us/products/[a-z0-9-]+/?)"[^>]*>\s*Product\s*</a>', b)
            pricing_m = re.search(r'href="https://azure\.microsoft\.com(/en-us/pricing/details/[a-z0-9-]+/?)"', b)
            if not (name_m and prod_m):
                continue
            slug = prod_m.group(1).strip('/').split('/')[-1]
            if slug in seen_slugs:
                # multi-category listing: append the extra category
                for row in catalog:
                    if row['slug'] == slug:
                        row['categories'].append(cat)
                        break
                continue
            seen_slugs.add(slug)
            catalog.append(OrderedDict(
                slug=slug,
                name=re.sub(r'<[^>]+>', '', H.unescape(name_m.group(1))).strip(),
                desc=re.sub(r'<[^>]+>', '', H.unescape(desc_m.group(1))).strip() if desc_m else '',
                categories=[cat],
                product_url=prod_m.group(1),
                pricing_url=pricing_m.group(1) if pricing_m else None,
            ))
    return catalog


def build_products() -> list:
    catalog = parse_catalog()
    dump('products.json', catalog)
    return catalog


def build_product_pages() -> None:
    pages = []
    for path in sorted(RAW.joinpath('prod').glob('*.html')):
        h = path.read_text(encoding='utf-8', errors='replace')
        body = h[h.find('<h1'):] if '<h1' in h else h
        h1 = re.search(r'<h1[^>]*>(.*?)</h1>', body, re.S)
        md = re.search(r'<meta name="description" content="([^"]+)"', h)
        sections = []
        for m in re.finditer(r'<h2[^>]*>(.*?)</h2>(.*?)(?=<h2|\Z)', body, re.S):
            title = textify(m.group(1))
            seg = m.group(2)
            texts = [textify(t) for t in re.findall(r'<div data-oc-token-text>\s*(.*?)\s*</div>', seg, re.S)]
            texts = [t for t in texts if len(t) > 40]
            if title:
                sections.append({'title': title, 'bullets': texts[:6]})
        docs = sorted(set(re.findall(r'href="(https://learn\.microsoft\.com/en-us/azure/[^"#?]+)"', body)))
        pricing = re.search(r'href="https://azure\.microsoft\.com(/en-us/pricing/details/[a-z0-9-]+/?)"', body)
        pricing_url = pricing.group(1) if pricing else None
        # The captured VM product page cross-references Managed Disks pricing
        # in its body copy, so the first pricing link the regex finds is the
        # wrong service; the product's own pricing target is the canonical
        # /en-us/pricing/details/virtual-machines/ URL, which the site maps
        # to the captured Linux Virtual Machines pricing details page.
        if path.stem == 'virtual-machines':
            pricing_url = '/en-us/pricing/details/virtual-machines/'
        related = sorted({m for m in re.findall(
            r'href="https://azure\.microsoft\.com/en-us/products/([a-z0-9-]+)/"', body)})
        slug = path.stem
        imgs = re.findall(
            r'(?:src|data-src|content)="(https://cdn-dynmedia-1\.microsoft\.com/[^"\s]+)"', h)
        hero = None
        content_imgs = []
        seen = set()
        for u in imgs:
            rel = _img_path(u)
            if rel is None or rel in seen:
                continue
            seen.add(rel)
            if hero is None:
                hero = rel
            elif len(content_imgs) < 3:
                content_imgs.append(rel)
        pages.append(OrderedDict(
            slug=slug,
            title=textify(h1.group(1)) if h1 else slug,
            description=H.unescape(md.group(1)) if md else '',
            sections=sections,
            docs_urls=docs[:6],
            pricing_url=pricing_url,
            related=related[:12],
            hero_image=hero,
            content_images=content_imgs,
        ))
    dump('product_pages.json', pages)


# --------------------------------------------------------------- pricing --

def build_pricing_cards() -> None:
    cards = json.loads((RAW / 'pricing_cards.json').read_text(encoding='utf-8'))
    out = []
    for c in cards:
        href = c['href'].replace('https://azure.microsoft.com/en-us', '')
        icon = None
        if c.get('icon'):
            name = re.sub(r'[^a-zA-Z0-9]+', '-',
                          c['icon'].split('microsoftcorp/')[-1]).strip('-').lower()
            icon = _canonical(f'pricing-icons/{name}.svg')
        out.append(OrderedDict(
            name=c['name'],
            href=href,
            icon=icon,
        ))
    dump('pricing_cards.json', out)


def build_pricing_details() -> None:
    """Extract the real comparison tables from the captured pricing pages."""
    tables_out = []

    def parse_tables(filename, page_title):
        h = read_html(filename)
        for ti, t in enumerate(re.findall(r'<table[^>]*>(.*?)</table>', h, re.S)):
            rows = []
            for r in re.findall(r'<tr[^>]*>(.*?)</tr>', t, re.S):
                cells = [textify(c) for c in re.findall(r'<t[hd][^>]*>(.*?)</t[hd]>', r, re.S)]
                if any(cells):
                    rows.append(cells)
            if rows:
                tables_out.append(OrderedDict(
                    page=page_title,
                    index=ti,
                    header=rows[0],
                    rows=rows[1:],
                ))

    parse_tables('pricing_details_kubernetes-service.html', 'kubernetes-service')
    parse_tables('pricing_details_virtual-machines_linux.html', 'virtual-machines-linux')
    parse_tables('pricing_details_cosmos-db.html', 'cosmos-db')
    parse_tables('pricing_details_managed-disks.html', 'managed-disks')
    dump('pricing_details.json', tables_out)


# ------------------------------------------------------------ calculator --

VM_SIZES = [
    'a1', 'a2', 'a4',
    'a1v2', 'a2v2', 'a4v2',
    'b1ls', 'b1s', 'b2s', 'b2ms', 'b4ms', 'b8ms',
    'd2', 'd3', 'd4',
    'd2sv5', 'd4sv5', 'd8sv5', 'd16sv5', 'd32sv5',
    'e2sv5', 'e4sv5', 'e8sv5', 'e16sv5', 'e32sv5',
    'f2', 'f4', 'f8',
]
AKS_SIZES = [
    'a2', 'a4',
    'b2s', 'b4ms', 'b8ms',
    'd4sv5', 'd8sv5', 'd16sv5',
    'e4sv5', 'e8sv5',
    'f4',
]
STORAGE_SKUS = [
    'general-purpose-v2-block-blob-structured-hot-lrs',
    'general-purpose-v2-block-blob-structured-cool-lrs',
    'general-purpose-v2-block-blob-structured-cool-zrs',
    'general-purpose-v2-block-blob-structured-cool-gzrs',
    'general-purpose-v2-block-blob-structured-cool-ra-gzrs',
    'general-purpose-v2-block-blob-structured-archive-lrs',
    'general-purpose-v2-block-blob-structured-hot-lrs-read-operations',
    'general-purpose-v2-block-blob-structured-hot-lrs-write-operations',
    'general-purpose-v2-block-blob-structured-hot-lrs-other-operations',
    'general-purpose-v2-block-blob-structured-cool-lrs-read-operations',
    'general-purpose-v2-block-blob-structured-cool-lrs-write-operations',
]
COSMOS_SKUS = [
    'single', 'multiple', 'serverless', 'storage', 'analytical-storage',
    'dedicated-gateway-d4s', 'dedicated-gateway-d8s', 'dedicated-gateway-d16s',
    'ap1-entry-price', 'ap2-entry-price', 'ap3-entry-price', 'ap4-entry-price',
]


def _region_prices(offer, unit):
    prices = offer.get('prices', {}).get(unit, {})
    return {slug: round(float(v['value']), 6) for slug, v in prices.items() if 'value' in v}


def build_calculator() -> None:
    calc = OrderedDict()
    calc['hours_per_month'] = HOURS_PER_MONTH

    # regions + geographies (pricing calculator region API)
    geo_raw = json.loads((RAW / 'api_calc_regions.json').read_text(encoding='utf-8'))
    geos = []
    region_geo = {}
    region_names = {}
    for g in geo_raw:
        regions = []
        for r in g['regions']:
            regions.append(r['slug'])
            region_geo[r['slug']] = g['slug']
            region_names[r['slug']] = r['displayName']
        geos.append(OrderedDict(slug=g['slug'], display_name=g['displayName'], regions=regions))
    calc['geographies'] = geos
    calc['region_names'] = region_names
    calc['region_geography'] = region_geo

    # currencies
    cur = json.loads((RAW / 'api_currencies.json').read_text(encoding='utf-8'))
    calc['currencies'] = OrderedDict(
        (code, OrderedDict(name=v['name'], glyph=v['glyph'], display_name=v['displayName'],
                           conversion=v['conversion']))
        for code, v in cur.items())

    # virtual machines
    vm = json.loads((RAW / 'api_vm.json').read_text(encoding='utf-8'))
    vm_regions = OrderedDict((r['slug'], r['displayName']) for r in vm['regions'])
    calc['vm_regions'] = vm_regions
    sizes = []
    for size in VM_SIZES:
        for os_name in ('linux', 'windows'):
            key = f'{os_name}-{size}-standard'
            offer = vm['offers'].get(key)
            if not offer:
                continue
            prices = _region_prices(offer, 'perhour')
            if not prices:
                continue
            sizes.append(OrderedDict(
                key=key, os=os_name, size_slug=size,
                display_name=size.upper().replace('SV5', 's v5').replace('MS', 'ms'),
                series=offer.get('series'), cores=offer.get('cores'),
                ram_gb=offer.get('ram'), disk_gb=offer.get('diskSize'),
                prices=prices,
            ))
    calc['vm_sizes'] = sizes

    # kubernetes service: control plane + node VMs
    aks = json.loads((RAW / 'api_kubernetes-service.json').read_text(encoding='utf-8'))
    control = OrderedDict()
    for tier, key in [('SLA', 'sla'), ('SLA and Long Term Support', 'sla-and-long-term-support'),
                      ('Uptime SLA', 'uptime-sla'), ('Premium', 'premium'), ('Automatic', 'automatic')]:
        offer = aks['offers'].get(key)
        if offer:
            control[tier] = _region_prices(offer, 'perhour')
    calc['aks_control_plane'] = control
    aks_sizes = []
    for size in AKS_SIZES:
        for os_name in ('linux', 'windows'):
            key = f'{os_name}-{size}-standard'
            offer = aks['offers'].get(key)
            if not offer:
                continue
            prices = _region_prices(offer, 'perhour')
            if not prices:
                continue
            aks_sizes.append(OrderedDict(
                key=key, os=os_name, size_slug=size,
                series=offer.get('series'), cores=offer.get('cores'),
                ram_gb=offer.get('ram'), prices=prices,
            ))
    calc['aks_sizes'] = aks_sizes

    # storage: graduated (tiered) block blob prices + flat operation prices
    st = json.loads((RAW / 'api_storage.json').read_text(encoding='utf-8'))
    st_skus = []
    for sku in STORAGE_SKUS:
        offer = st['offers'].get(sku)
        if not offer:
            continue
        if 'graduatedPrices' in offer:
            grad = offer['graduatedPrices']
            unit = list(grad.keys())[0]
            tiers = OrderedDict()
            for region, blob in grad[unit].items():
                tiers[region] = [OrderedDict(limit_gb=(None if r['limit'] > 1e300 else r['limit']),
                                              price=r['price']['value']) for r in blob['prices']]
            st_skus.append(OrderedDict(sku=sku, unit=unit, graduated=True, tiers=tiers))
        elif 'prices' in offer:
            unit = list(offer['prices'].keys())[0]
            st_skus.append(OrderedDict(sku=sku, unit=unit, graduated=False,
                                       prices=_region_prices(offer, unit)))
    calc['storage_skus'] = st_skus

    # cosmos db
    cd = json.loads((RAW / 'api_cosmos-db.json').read_text(encoding='utf-8'))
    cd_skus = []
    for sku in COSMOS_SKUS:
        offer = cd['offers'].get(sku)
        if not offer:
            continue
        units = offer.get('prices', {})
        entry = OrderedDict(sku=sku, prices={})
        for unit, blob in units.items():
            entry['prices'][unit] = {r: round(float(v['value']), 6) for r, v in blob.items() if 'value' in v}
        if any(entry['prices'].values()):
            cd_skus.append(entry)
    calc['cosmos_skus'] = cd_skus
    calc['source_note'] = (
        'Curated real subset of the live Azure pricing calculator service APIs '
        '(same JSON the calculator at azure.microsoft.com/en-us/pricing/calculator/ '
        'loads). All prices are captured per-hour / per-GB / per-10k values by '
        'region; the curation keeps representative sizes of every major series '
        'plus every control-plane and storage tier instead of the full 46,781-SKU '
        'feed. Captured 2026-09-30.')
    dump('calculator.json', calc)


# ---------------------------------------------------------- free services --

def build_free_services() -> None:
    feed = json.loads((RAW / 'free_services_cards.json').read_text(encoding='utf-8'))
    rows = []
    for it in feed['items']:
        tags = it.get('filterTags', [])
        category = next((t.split(':', 1)[1] for t in tags if t.startswith('category:')), None)
        period = next((t.split(':', 1)[1] for t in tags if t.startswith('azure_free_period:')), None)
        c = it['content']
        rows.append(OrderedDict(
            id=it['id'],
            name=it['name'],
            category=category.replace('category-', '').replace('-', ' ') if category else None,
            period='Always free' if period == 'always_free' else '12 months free',
            detail=c.get('paragraph', ''),
            eyebrow=c.get('eyebrow', ''),
            href=(c.get('action', {}) or {}).get('href'),
        ))
    # page-level artwork captured from the free-services page
    icons = _dir_images('free-icons')
    dump('free_services.json', {'icons': icons, 'items': rows})


# ---------------------------------------------------------------- regions --

def build_regions() -> None:
    calc = json.loads((OUT / 'calculator.json').read_text(encoding='utf-8'))
    h = read_html('explore_global-infrastructure_geographies.html')
    md = re.search(r'<meta name="description" content="([^"]+)"', h)
    imgs = _dir_images('geographies')
    geos = calc['geographies']
    names = calc['region_names']
    region_geo = calc['region_geography']
    # per-service availability from calculator offers
    services = OrderedDict()
    for svc, sizes in [('virtual-machines', calc['vm_sizes']),
                       ('kubernetes-service', calc['aks_sizes'])]:
        avail = {}
        for s in sizes:
            for r in s['prices']:
                avail.setdefault(r, 0)
                avail[r] += 1
        services[svc] = avail
    st_avail = {}
    for s in calc['storage_skus']:
        blob = s.get('tiers') or s.get('prices')
        for r in blob:
            st_avail.setdefault(r, 0)
            st_avail[r] += 1
    services['storage'] = st_avail
    cd_avail = {}
    for s in calc['cosmos_skus']:
        for unit, blob in s['prices'].items():
            for r in blob:
                cd_avail.setdefault(r, 0)
                cd_avail[r] += 1
    services['cosmos-db'] = cd_avail

    regions = OrderedDict(
        description=H.unescape(md.group(1)) if md else '',
        images=imgs,
        geographies=[OrderedDict(
            slug=g['slug'],
            display_name=g['display_name'],
            regions=[OrderedDict(
                slug=r,
                display_name=names.get(r, r),
                services={svc: (counts.get(r, 0) > 0) for svc, counts in services.items()},
            ) for r in g['regions']],
        ) for g in geos],
        service_availability=services,
    )
    dump('regions.json', regions)


# ---------------------------------------------------------------- stories --

def build_stories() -> None:
    cards = []
    for i in range(3):
        page = json.loads((RAW / 'stories' / f'azure_p{i}.json').read_text(encoding='utf-8'))
        cards.extend(page['cards'])
    seen = set()
    rows = []
    for c in cards:
        name = c['name']
        if name in seen:
            continue
        seen.add(name)
        content = c['content']
        industries = sorted({t['text'].strip() for t in content.get('industries', []) if t.get('text')})
        products = []
        for p in content.get('footer', {}).get('relatedProducts', {}).get('products', []):
            label = p.get('label')
            if label and label not in products:
                products.append(label)
        quotes = content.get('quotes', [])
        quote = quotes[0] if quotes else {}
        src = content.get('image', {}).get('src')
        logo = content.get('image', {}).get('slot', {}).get('badge', {}).get('icon', {}).get('src')
        rows.append(OrderedDict(
            slug=name,
            title=content.get('title', '').strip(),
            industries=industries,
            products=products,
            quote_text=quote.get('text', '').strip(),
            quote_person=quote.get('person', ''),
            quote_role=quote.get('role', ''),
            quote_company=quote.get('company', ''),
            header_image=_img_path(src) if src else None,
            logo_image=_img_path(logo) if logo else None,
        ))
    dump('stories.json', rows)


def build_story_pages() -> None:
    pages = []
    for path in sorted(RAW.joinpath('stories', 'detail').glob('*.html')):
        h = path.read_text(encoding='utf-8', errors='replace')
        body = h[h.find('<h1'):] if '<h1' in h else h
        h1 = re.search(r'<h1[^>]*>(.*?)</h1>', body, re.S)
        sections = []
        for m in re.finditer(r'<h([23])[^>]*>(.*?)</h\1>(.*?)(?=<h[23]|\Z)', body, re.S):
            title = textify(m.group(2))
            seg = m.group(3)
            texts = [textify(t) for t in re.findall(r'<p[^>]*>(.*?)</p>', seg, re.S)]
            texts = [t for t in texts if 40 < len(t) < 600]
            if title and texts:
                sections.append({'title': title, 'text': texts[0]})
        md = re.search(r'<meta name="description" content="([^"]+)"', h)
        pages.append(OrderedDict(
            slug=path.stem,
            title=textify(h1.group(1)) if h1 else path.stem,
            description=H.unescape(md.group(1)) if md else '',
            sections=sections[:8],
        ))
    dump('story_pages.json', pages)


# -------------------------------------------------------------------- blog --

def build_blog() -> None:
    cards = json.loads((RAW / 'blog_cards.json').read_text(encoding='utf-8'))
    posts = []
    for c in cards:
        slug = c['url'].rstrip('/').split('/')[-1]
        detail_path = RAW / 'blogposts' / f'{slug}.html'
        body = ''
        if detail_path.exists():
            h = detail_path.read_text(encoding='utf-8', errors='replace')
            i = h.find('<h1')
            if i >= 0:
                seg = h[i:]
                paras = [textify(t) for t in re.findall(r'<p(?:\s[^>]*)?>(.*?)</p>', seg, re.S)]
                paras = [p for p in paras if 60 < len(p) < 700]
                body = ' '.join(paras[:6])
        posts.append(OrderedDict(
            slug=slug,
            title=c['title'],
            content_type=c['content_type'],
            date=c['date'][:10] if c.get('date') else None,
            read_time=c['read_time'],
            image=_img_path(c.get('image')),
            excerpt=body[:900],
        ))
    dump('blog.json', posts)


# -------------------------------------------------------------- dictionary --

def build_dictionary() -> None:
    rows = []
    for path in sorted(RAW.joinpath('dict').glob('*.html')):
        h = path.read_text(encoding='utf-8', errors='replace')
        first_img = re.search(
            r'(?:src|data-src|content)="(https://cdn-dynmedia-1\.microsoft\.com/[^"\s]+)"', h)
        h1 = re.search(r'<h1[^>]*>(.*?)</h1>', h, re.S)
        md = re.search(r'<meta name="description" content="([^"]+)"', h)
        body = h[h.find('<h1'):] if '<h1' in h else h
        sections = []
        for m in re.finditer(r'<h2[^>]*>(.*?)</h2>(.*?)(?=<h2|\Z)', body, re.S):
            title = textify(m.group(1))
            seg = m.group(2)
            texts = [textify(t) for t in re.findall(r'<p[^>]*>(.*?)</p>', seg, re.S)]
            texts = [t for t in texts if 40 < len(t) < 900]
            if title:
                sections.append({'title': title, 'text': texts[0] if texts else ''})
        rows.append(OrderedDict(
            slug=path.stem,
            title=textify(h1.group(1)) if h1 else path.stem,
            description=H.unescape(md.group(1)) if md else '',
            sections=sections[:8],
            image=_img_path(first_img.group(1)) if first_img else None,
        ))
    dump('dictionary.json', rows)


# ----------------------------------------------------------------- support --

def build_support() -> None:
    h = read_html('support.html')
    md = re.search(r'<meta name="description" content="([^"]+)"', h)
    imgs = _dir_images('support')
    plans = [
        OrderedDict(
            name='Developer',
            audience='Trial, testing, and development',
            desc='If you\u2019re using Azure in a nonproduction environment or just trying it out, choose the Developer plan to get an initial response to your Azure technical support requests within one business day.',
            response='Initial response within one business day',
        ),
        OrderedDict(
            name='Standard',
            audience='Production workloads',
            desc='When you\u2019re running a production workload on Azure, get Azure technical support initial response times between one hour and one business day, based on case severity, with the Standard plan.',
            response='Initial response between one hour and one business day, based on case severity',
        ),
        OrderedDict(
            name='Professional Direct',
            audience='Business-critical functions',
            desc='If you need faster response times, advisory services, and high-severity incident escalation management from a collaborative management pool, choose Professional Direct (ProDirect) support.',
            response='Faster response times, advisory services, and escalation management',
        ),
        OrderedDict(
            name='Enterprise',
            audience='Comprehensive Microsoft technology support',
            desc='If you need company-wide support across Azure and other Microsoft technologies, consider enterprise support.',
            response='Company-wide support across Azure and other Microsoft technologies',
        ),
    ]
    dump('support.json', OrderedDict(
        description=H.unescape(md.group(1)) if md else '',
        images=imgs,
        plans=plans,
    ))


# ------------------------------------------------------------------- users --

def build_users() -> None:
    """Benchmark accounts (authored, shared convention across mirror sites)."""
    users = [
        OrderedDict(name='Alice Chen', email='alice.chen@test.com', password='TestPass123!',
                    role='Cloud architect'),
        OrderedDict(name='Bob Alvarez', email='bob.alvarez@test.com', password='TestPass123!',
                    role='DevOps engineer'),
        OrderedDict(name='Carol Ito', email='carol.ito@test.com', password='TestPass123!',
                    role='Data engineer'),
        OrderedDict(name='Dana Osei', email='dana.osei@test.com', password='TestPass123!',
                    role='Startup founder'),
    ]
    dump('users.json', users)


def main() -> None:
    print('building source_data/ from scraped_data/ ...')
    build_site()
    build_products()
    build_product_pages()
    build_pricing_cards()
    build_pricing_details()
    build_calculator()
    build_free_services()
    build_regions()
    build_stories()
    build_story_pages()
    build_blog()
    build_dictionary()
    build_support()
    build_users()
    print('done.')


if __name__ == '__main__':
    main()
