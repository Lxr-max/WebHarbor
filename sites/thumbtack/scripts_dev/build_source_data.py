#!/usr/bin/env python3
"""Build the tracked source-data snapshots for the thumbtack mirror.

Processes the raw Playwright harvest under scraped_data/harvest/ (captured
2026-09-26) into the three deterministic JSON snapshots the seeder reads:

  source_data_categories.json  - the 16 mirrored service categories with their
      real upstream filter-question sets, quote-form questions, descriptions
      and icon assignments.
  source_data_pros.json        - real pro profiles (name, city, rating,
      reviews, portfolio image ids, business hours, payment methods, card
      badges/quotes) captured from the rendered profile pages.
  source_data_content.json     - cost guides, homepage cities, guarantee copy,
      benchmark users, pre-existing user activity, and the deterministic
      pro-reply / quote-note pools.

Also emits image_manifest.json (every managed image with its real upstream
source URL) for the asset downloader + inventory builder.

Idempotent: rerunning produces byte-identical JSON (sorted keys, no clocks).
"""
from __future__ import annotations

import json
import pathlib
import re

HERE = pathlib.Path(__file__).resolve().parent          # sites/thumbtack/scripts_dev
SITE = HERE.parent                                       # sites/thumbtack
HARVEST = SITE / 'scraped_data' / 'harvest'

DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']

# Browse categories kept in the mirror (>=6 real pros each after dedup).
CATEGORIES = {
    'house-cleaning': dict(
        name='House Cleaning', plural='house cleaners',
        h1='House cleaners near you',
        meta_group='Home Improvement',
        description=('House cleaners can refresh every room of your home. '
                     'Professional cleaning helps maintain a healthy living '
                     'environment and protects your home value over time.'),
        cost_slug='house-cleaning-prices',
        icon='icon_house_cleaning.jpg'),
    'affordable-plumbing-services': dict(
        name='Plumbing Pipe Repair', plural='plumbers',
        h1='Affordable plumbing services near you',
        meta_group='Home Improvement',
        description=('Plumbers can repair leaks, clear drains, replace pipes '
                     'and install fixtures. Describe the problem and get '
                     'quotes from licensed local plumbers today.'),
        cost_slug='plumbers-cost',
        icon='icon_plumbing.jpg'),
    'interior-painting': dict(
        name='Interior Painting', plural='interior painters',
        h1='Interior painters near you',
        meta_group='Home Improvement',
        description=('Interior painters can add fresh paint to your home\'s '
                     'walls, ceilings, and trim. Professional painting can '
                     'help protect interior walls and maintain home value '
                     'over time.'),
        cost_slug='cost-to-paint-a-room',
        icon='icon_painting.jpg'),
    'handyman': dict(
        name='Handyman', plural='handymen',
        h1='Handymen near you',
        meta_group='Home Improvement',
        description=('Handymen can handle repairs, installations and small '
                     'projects around your home — from mounting TVs to fixing '
                     'doors, floors and drywall.'),
        cost_slug='handyman-prices',
        icon='icon_handyman.jpg'),
    'lawn-care': dict(
        name='Full Service Lawn Care', plural='lawn care professionals',
        h1='Lawn care professionals near you',
        meta_group='Home Improvement',
        description=('Lawn care professionals can mow, fertilize, aerate and '
                     'edge your yard on a schedule that fits your home.'),
        cost_slug='lawn-service-prices',
        icon='icon_lawn_care.jpg'),
    'appliance-repair': dict(
        name='Appliance Repair or Maintenance', plural='appliance service specialists',
        h1='Appliance service specialists near you',
        meta_group='Home Improvement',
        description=('Appliance service specialists repair refrigerators, '
                     'washers, dryers, ovens and more — often with same-day '
                     'diagnosis.'),
        cost_slug='appliance-repair-cost',
        icon='icon_appliance.jpg'),
    'landscaping': dict(
        name='Outdoor Landscaping and Design', plural='landscapers',
        h1='Landscapers near you',
        meta_group='Home Improvement',
        description=('Landscapers design, install and maintain outdoor spaces: '
                     'patios, fences, sprinklers, garden beds and hardscaping.'),
        cost_slug='landscaping-prices',
        icon='icon_landscaping.jpg'),
    'tv-wall-mount-install': dict(
        name='TV Mounting', plural='TV wall mount installers',
        h1='TV wall mount installers near you',
        meta_group='Home Improvement',
        description=('TV wall mount installers hang your TV safely, conceal '
                     'cables and connect sound systems for a clean finish.'),
        cost_slug='tv-wall-mount-install-cost',
        icon='icon_tv_mount.jpg'),
    'furniture-assembly': dict(
        name='Furniture Assembly', plural='furniture assemblers',
        h1='Furniture assemblers near you',
        meta_group='Home Improvement',
        description=('Furniture assemblers build flat-pack furniture quickly '
                     'and correctly — beds, desks, bookcases, wardrobes.'),
        cost_slug='furniture-assembly-cost',
        icon='icon_furniture.jpg'),
    'roofing': dict(
        name='Roof Repair or Maintenance', plural='roofing professionals',
        h1='Roofing professionals near you',
        meta_group='Home Improvement',
        description=('Roofing professionals repair leaks, replace shingles '
                     'and inspect roofs to protect your home from the '
                     'weather.'),
        cost_slug='roof-repair-cost',
        icon='icon_roofing.jpg'),
    'exterminators': dict(
        name='Pest Control Services', plural='pest exterminators',
        h1='Pest exterminators near you',
        meta_group='Home Improvement',
        description=('Exterminators remove ants, wasps, rodents and other '
                     'pests, and seal entry points so they stay out.'),
        cost_slug='exterminators-prices',
        icon='icon_pest.jpg'),
    'makeup-artists': dict(
        name='Wedding and Event Makeup', plural='makeup artists',
        h1='Makeup artists near you',
        meta_group='Events',
        description=('Makeup artists create flawless looks for weddings, '
                     'proms and photo shoots — on location or in studio.'),
        cost_slug='makeup-artist-prices',
        icon='icon_makeup.jpg'),
    'wedding-photographers': dict(
        name='Wedding and Event Photography', plural='wedding photographers',
        h1='Wedding photographers near you',
        meta_group='Events',
        description=('Wedding photographers capture your day with engagement '
                     'shoots, second shooters and full-day coverage.'),
        cost_slug='wedding-photographer-prices',
        icon='icon_photography.jpg'),
    'personal-trainers': dict(
        name='Personal Training', plural='personal trainers',
        h1='Personal trainers near you',
        meta_group='Wellness',
        description=('Personal trainers build workout plans, coach form and '
                     'keep you accountable — at home, in the gym or online.'),
        cost_slug='personal-trainer-cost',
        icon='icon_training.jpg'),
    'local-movers': dict(
        name='Local Moving (under 50 miles)', plural='local movers',
        h1='Local movers near you',
        meta_group='Home Improvement',
        description=('Local movers pack, load, transport and unpack your '
                     'household within your metro area.'),
        cost_slug='local-movers-cost',
        icon='icon_moving.jpg'),
    'djs': dict(
        name='DJ Services', plural='DJs',
        h1='DJs near you',
        meta_group='Events',
        description=('DJs bring sound, lighting and emcee energy to weddings '
                     'and events — with the music you actually want.'),
        cost_slug='wedding-djs-cost',
        icon='icon_dj.jpg'),
}

# The harvest ran under upstream browse slugs that the mirror renames.
BROWSE_RENAME = {'electrical-repairs': 'appliance-repair'}

# Long-tail upstream URL categories folded into the browse buckets above.
CAT_FOLD = {
    'house-cleaning': 'house-cleaning', 'carpet-cleaning': 'house-cleaning',
    'window-cleaning': 'house-cleaning',
    'affordable-plumbing-services': 'affordable-plumbing-services',
    'repiping-specialists': 'affordable-plumbing-services',
    'pipe-fitting-companies': 'affordable-plumbing-services',
    'drain-cleaning': 'affordable-plumbing-services',
    'toilet-installation': 'affordable-plumbing-services',
    'interior-painting': 'interior-painting', 'exterior-painting': 'interior-painting',
    'interior-designers': 'interior-painting',
    'handyman': 'handyman', 'hardwood-floor-installation': 'handyman',
    'insulation': 'handyman', 'water-damage': 'handyman',
    'general-contractors': 'handyman', 'bathroom-remodeling': 'handyman',
    'tile': 'handyman', 'pro': 'handyman',
    'lawn-care': 'lawn-care', 'gardening': 'lawn-care', 'tree-trimming': 'lawn-care',
    'appliance-repair': 'appliance-repair', 'electrical-repairs': 'appliance-repair',
    'landscaping': 'landscaping', 'masonry-contractors': 'landscaping',
    'concrete-contractors': 'landscaping', 'patios': 'landscaping',
    'fences': 'landscaping',
    'tv-wall-mount-install': 'tv-wall-mount-install',
    'furniture-assembly': 'furniture-assembly',
    'roofing': 'roofing',
    'exterminators': 'exterminators',
    'makeup-artists': 'makeup-artists',
    'wedding-photographers': 'wedding-photographers',
    'personal-trainers': 'personal-trainers',
    'local-movers': 'local-movers',
    'djs': 'djs', 'wedding-djs': 'djs',
}

# Real upstream icon ids captured from the homepage explore menu (2026-09-26)
# mapped to the browse categories; the four popular-card icons are the ones
# whose label mapping was captured directly from the rendered DOM.
ICON_IDS = {
    'house-cleaning': '498412289313030155',
    'plumbing': '557179357397630981',
    'painting': '323234733715669089',
    'pest': '323302143497871457',
    # remaining icon ids come from the homepage explore-menu capture
    'handyman': '302055732073750622',
    'lawn-care': '302055786985382021',
    'appliance': '302055975251869744',
    'landscaping': '302056146185683124',
    'tv-mount': '302056217768902836',
    'furniture': '302056271480946821',
    'roofing': '302056322140643507',
    'makeup': '302056333871431860',
    'photography': '302056478120263859',
    'training': '302056948788437086',
    'moving': '302057049177768086',
    'dj': '302057814491504790',
}


def slugify(text: str) -> str:
    return re.sub(r'[^a-z0-9]+', '-', (text or '').lower()).strip('-')


def parse_card(text: str) -> dict:
    """Parse a rendered pro card into badge/quote fields."""
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    out = {}
    out['top_pro'] = 'Top Pro' in lines
    out['in_high_demand'] = ('In high demand' in lines
                             or 'Limited Availability' in lines)
    out['great_value'] = 'Great value' in lines
    m = re.search(r'(?:Online Now - )?[Rr]esponds in about (\d+) (min|hour)s?', text)
    out['responds_in'] = None
    if m:
        n = int(m.group(1))
        out['responds_in'] = n if m.group(2).startswith('min') else n * 60
    out['online_now'] = bool(re.search(r'Online [Nn]ow', text))
    m = re.search(r'(\d+) hires on Thumbtack', text)
    out['hires'] = int(m.group(1)) if m else 0
    m = re.search(r'(\d+) similar jobs? done near you', text)
    out['similar_jobs'] = int(m.group(1)) if m else 0
    # upstream truncates the snippet without a closing quote: Author says, "text...See more
    m = re.search(r'^(.+?) says, "(.+?)(?: see more)?\.?$', text,
                  re.M | re.I)
    if m:
        out['card_quote_author'] = m.group(1).strip()
        out['card_quote'] = m.group(2).strip().rstrip('.').rstrip('\u2026')
    else:
        out['card_quote_author'] = ''
        out['card_quote'] = ''
    return out


def parse_hours(block):
    """['Sun', 'Closed', 'Mon', '12:00 am - 11:59 pm', ...] -> [[day, hours], ...]"""
    if not block:
        return [['Mon', '8:00 am - 6:00 pm']]
    hours = []
    i = 0
    while i + 1 < len(block):
        day, val = block[i], block[i + 1]
        if day in DAYS and not val.startswith(('Read more', 'Payment')):
            hours.append([day, val])
            i += 2
        else:
            break
    return hours or [['Mon', '8:00 am - 6:00 pm']]


def parse_reviews(pro):
    """Merge ld_reviews (with ratings) with reviews_raw (with Details lines)."""
    raw = pro.get('reviews_raw') or []
    ld = pro.get('ld_reviews') or []
    details = {}
    hired = {}
    for r in raw:
        lines = [l.strip() for l in r.split('\n') if l.strip()]
        if not lines:
            continue
        author = lines[0]
        dm = re.search(r'([A-Z][a-z]{2} \d{1,2}, \d{4})', r)
        if dm:
            details[(author, dm.group(1))] = r
            hired[(author, dm.group(1))] = 'Hired on Thumbtack' in r
    out = []
    for rev in ld:
        body = (rev.get('body') or '').strip()
        author = rev.get('author')
        date = rev.get('date')
        if not body or not author or not date:
            continue
        rating = int(rev.get('rating') or 5)
        det = ''
        hir = False
        chunk = details.get((author, date), '')
        if chunk:
            hir = 'Hired on Thumbtack' in chunk
            dm = re.search(r'Details: ([^\n]+)', chunk)
            if dm:
                det = dm.group(1).strip()
        out.append({'author': author, 'date_str': date, 'rating': rating,
                    'body': body, 'details': det, 'hired': hir})
    # fall back to raw text reviews if ld extraction found nothing
    if not out:
        for r in raw:
            lines = [l.strip() for l in r.split('\n') if l.strip()]
            if len(lines) < 4:
                continue
            author = lines[0]
            dm = re.search(r'([A-Z][a-z]{2} \d{1,2}, \d{4})', r)
            date = dm.group(1) if dm else ''
            body_m = re.search(r'\n\n(.+?)\n\nDetails:', r, re.S)
            body = body_m.group(1).strip() if body_m else ''
            detm = re.search(r'Details: ([^\n]+)', r)
            if not body:
                continue
            out.append({'author': author, 'date_str': date, 'rating': 5,
                        'body': body, 'details': detm.group(1) if detm else '',
                        'hired': 'Hired on Thumbtack' in r})
    out = out[:8]
    def date_key(r):
        try:
            from datetime import datetime
            return datetime.strptime(r['date_str'], '%b %d, %Y')
        except Exception:
            from datetime import datetime
            return datetime(1970, 1, 1)
    out.sort(key=date_key, reverse=True)
    return out


def parse_services_offered(block):
    """['Cleaning type', 'Deep cleaning', '+3 more', ...] -> [[group, [opts]]]"""
    if not block:
        return []
    groups = []
    cur = None
    for line in block:
        if line.startswith('+') and line.endswith(' more'):
            continue
        if re.match(r'^[A-Z][A-Za-z &/]{2,30}$', line) and cur is None:
            cur = [line, []]
        elif cur is not None:
            if re.match(r'^[A-Z][A-Za-z &/]{2,30}$', line) and groups and len(cur[1]) >= 1:
                groups.append(cur)
                cur = [line, []]
            else:
                cur[1].append(line)
    if cur:
        groups.append(cur)
    return [[g, opts[:8]] for g, opts in groups if opts]


def img_id(url):
    m = re.search(r'/i/(\d+)/', url or '')
    return m.group(1) if m else None


def main():
    # ---------------- categories ----------------
    def select_service_questions(slug):
        """Categories whose upstream page uses a 'Select a service' picker."""
        f = HARVEST / f'cat_{slug}_filters.json'
        if not f.exists():
            f = HARVEST / f'cat_{BROWSE_RENAME.get(slug, slug)}_filters.json'
        if not f.exists():
            return []
        try:
            text = json.loads(f.read_text()).get('text', '')
        except Exception:
            return []
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        try:
            fi = next(i for i, l in enumerate(lines) if l == 'Filters')
        except StopIteration:
            return []
        if fi + 2 >= len(lines) or lines[fi + 1] != 'Select a service':
            return []
        opts = []
        for l in lines[fi + 2:]:
            if re.match(r'^[A-Z]', l) and len(l) < 50 and not l[0].isdigit():
                opts.append(l)
            else:
                break
            if len(opts) >= 8:
                break
        return [{'q': 'Select a service', 'opts': opts}] if len(opts) >= 2 else []

    categories = []
    for slug, spec in CATEGORIES.items():
        f = HARVEST / f'cat_{slug}_filters_dom.json'
        questions = json.loads(f.read_text()) if f.exists() else []
        questions = [q for q in questions if q.get('opts')]
        if not questions:
            questions = select_service_questions(slug)
        categories.append({
            'slug': slug, 'name': spec['name'], 'plural': spec['plural'],
            'h1': spec['h1'], 'description': spec['description'],
            'meta_group': spec['meta_group'],
            'icon': f"{slug}_icon.jpg",
            'image': f"{slug}_card.jpg",
            'questions': questions,
            'quote_questions': [],
            'cost_slug': spec['cost_slug'],
        })
    cat_doc = {'captured': '2026-09-26', 'categories': categories}

    # ---------------- pros ----------------
    cards_by_pk = {}
    for f in sorted(HARVEST.glob('cat_*.json')):
        if '_filters' in f.name:
            continue
        doc = json.loads(f.read_text())
        for card in doc.get('cards', []):
            pk = card['href'].rstrip('/').split('/')[-1].split('?')[0]
            if pk not in cards_by_pk:
                cards_by_pk[pk] = (doc['slug'], card)

    pros = []
    image_manifest = {}          # filename -> source_url
    seen_pks = set()
    for f in sorted((HARVEST / 'pros').glob('*.json')):
        pro = json.loads(f.read_text())
        if pro.get('failed'):
            continue
        m = re.match(r'https://www\.thumbtack\.com/([a-z]{2})/([a-z0-9-]+)/([a-z0-9-]+)/([a-z0-9-]+)/service/(\d+)', pro['url'])
        if not m:
            continue
        state, city_slug, url_cat, pro_slug, pk = m.groups()
        if pk in seen_pks:
            continue
        browse = d_browse = pro.get('category_slug') or url_cat
        browse = BROWSE_RENAME.get(browse, browse)
        if browse not in CATEGORIES:
            browse = BROWSE_RENAME.get(CAT_FOLD.get(url_cat), CAT_FOLD.get(url_cat))
        if browse not in CATEGORIES:
            continue
        seen_pks.add(pk)
        card = cards_by_pk.get(pk, (None, None))[1]
        cardinfo = parse_card(card['text']) if card else {
            'top_pro': bool(pro.get('top_pro_status')), 'in_high_demand': False,
            'great_value': False, 'responds_in': None,
            'online_now': False, 'hires': 0, 'similar_jobs': 0,
            'card_quote': '', 'card_quote_author': ''}
        # response time from the captured profile right rail
        raw_text = pro.get('raw_text', '')
        rail = raw_text[raw_text.find('Request estimate'):
                        raw_text.find('Request estimate') + 120] if 'Request estimate' in raw_text else ''
        if cardinfo['responds_in'] is None:
            m = re.search(r'Responds in about (\d+) (min|hour)s?', raw_text)
            if m:
                cardinfo['responds_in'] = int(m.group(1)) * (1 if m.group(2) == 'min' else 60)
            elif re.search(r'Responds within a day', raw_text):
                cardinfo['responds_in'] = 1440
            elif re.search(r'Responds within a few hours', raw_text):
                cardinfo['responds_in'] = 240
            else:
                cardinfo['responds_in'] = 1440
        if not cardinfo['online_now']:
            cardinfo['online_now'] = bool(re.search(r'Online now', rail))
        city = ' '.join(w.capitalize() for w in city_slug.split('-'))
        if city.lower() == 'seattle':
            city = 'Seattle'
        avatar_id = img_id(pro.get('avatar') or '')
        if not avatar_id and card and card.get('avatar'):
            avatar_id = img_id(card['avatar'])
        if not avatar_id:
            continue
        gallery_ids = []
        for g in pro.get('gallery_photos') or []:
            gid = img_id(g)
            if gid and gid != avatar_id and gid not in gallery_ids:
                gallery_ids.append(gid)
        gallery_ids = gallery_ids[:8]
        overview = pro.get('overview') or {}
        hired_m = re.search(r'Hired (\d+) times', overview.get('hired_times') or '')
        hires = int(hired_m.group(1)) if hired_m else cardinfo['hires']
        years_m = re.search(r'(\d+) years in business', overview.get('years') or '')
        emp_m = re.search(r'(\d+) employee', overview.get('employees') or '')
        pay = pro.get('payment_methods') or ''
        pay = pay.replace('This pro accepts payments via ', '').rstrip('.')
        social = []
        for s in (pro.get('social_media') or []):
            if s in ('Instagram', 'Facebook', 'Yelp', 'Website', 'TikTok', 'LinkedIn'):
                social.append(s)
            else:
                break
        top_years = []
        for tok in (pro.get('top_pro_status') or []):
            if re.match(r'^\d{4}$', tok):
                top_years.append(tok)
        tags = []
        for t in (pro.get('review_tags') or []):
            tm = re.match(r'^(.+?)・(\d+)$', t)
            if tm:
                tags.append([tm.group(1), int(tm.group(2))])
        creds = pro.get('credentials') or []
        bg_name = None
        for i, line in enumerate(creds):
            if line == 'Background Check' and i + 1 < len(creds):
                bg_name = creds[i + 1]
        record = {
            'service_pk': pk, 'slug': pro_slug,
            'name': pro['title'].split(' | ')[0].strip(),
            'category': browse,
            'city': city, 'state': state.upper(),
            'rating': round(float(pro.get('rating') or 4.8), 1),
            'review_count': int(pro.get('review_count') or 0),
            'hires': hires,
            'similar_jobs': cardinfo['similar_jobs'],
            'years_in_business': int(years_m.group(1)) if years_m else 5,
            'employees': int(emp_m.group(1)) if emp_m else 1,
            'background_checked': bool(overview.get('background_checked')) or bg_name is not None,
            'top_pro': bool(cardinfo['top_pro']) or bool(top_years),
            'top_pro_years': top_years,
            'responds_in': int(cardinfo['responds_in']),
            'online_now': bool(cardinfo['online_now']),
            'great_value': bool(cardinfo['great_value']),
            'in_high_demand': bool(cardinfo['in_high_demand']),
            'bio': re.sub(r'\s*\.\.\.?Read More\s*$', '',
                          (pro.get('bio') or '').strip()).strip() or
                   'Contact us to learn more about how we can help with your project.',
            'payment_methods': pay or 'Cash, Check, Credit card',
            'social_media': social,
            'avatar': f'av_{avatar_id}.jpg',
            'gallery': [f'ph_{gid}.webp' for gid in gallery_ids],
            'business_hours': parse_hours(pro.get('business_hours')),
            'rating_distribution': pro.get('rating_distribution') or {},
            'review_tags': tags,
            'services_offered': parse_services_offered(pro.get('services_offered')),
            'card_quote': cardinfo['card_quote'],
            'card_quote_author': cardinfo['card_quote_author'],
            'background_check_name': bg_name,
            'credentials_zip': None,
            'reviews': parse_reviews(pro),
        }
        if not record['services_offered']:
            record['services_offered'] = [[
                CATEGORIES[browse]['name'], ['Contact us for a full list of services.']]]
        if record['review_count'] and not record['reviews']:
            continue          # profiles that rendered without reviews are dropped
        if record['name'] in ('Sorry…', 'Sorry...', 'Thumbtack') or not record['rating']:
            continue          # upstream error/redirect pages captured as profiles
        image_manifest['avatars/' + record['avatar']] = (
            f'https://production-next-images-cdn.thumbtack.com/i/{avatar_id}/width/320/aspect/1-1.jpeg')
        for gid, fname in zip(gallery_ids, record['gallery']):
            image_manifest['photos/' + fname] = (
                f'https://production-next-images-cdn.thumbtack.com/i/{gid}/width/640.webp')
        pros.append(record)

    # quote questions: borrow from the first harvested profile of each category
    quote_qs = {}
    for f in sorted((HARVEST / 'pros').glob('*.json')):
        pro = json.loads(f.read_text())
        if pro.get('failed') or not pro.get('quote_form'):
            continue
        browse = pro.get('category_slug')
        if not browse:
            m = re.match(r'https://www\.thumbtack\.com/([a-z]{2})/([a-z0-9-]+)/([a-z0-9-]+)/', pro['url'])
            browse = m.group(3) if m else None
        browse = BROWSE_RENAME.get(browse, browse)
        if browse in CATEGORIES and browse not in quote_qs:
            qf = pro['quote_form']
            groups = []
            cur = None
            for line in qf:
                if line in ('Zip code', 'Select answer', 'Select answer(s)') or line.startswith('Select '):
                    continue
                if re.match(r'^[A-Z][A-Za-z &/]{2,30}$', line) and not re.match(r'^\d+ bedroom', line):
                    if cur and cur[1]:
                        groups.append(cur)
                    cur = [line, []]
                elif cur is not None:
                    cur[1].append(line)
            if cur and cur[1]:
                groups.append(cur)
            parsed = [{'q': g, 'opts': o[:8]} for g, o in groups if o]
            if parsed:
                quote_qs[browse] = parsed
    for cat in cat_doc['categories']:
        # The upstream right rail asks a subset of the same category questions;
        # where the captured rail rendered only dropdowns, fall back to the
        # full captured filter set.
        cat['quote_questions'] = quote_qs.get(cat['slug']) or cat['questions']

    # per-category pro counts; drop categories with <6 pros
    counts = {}
    for p in pros:
        counts[p['category']] = counts.get(p['category'], 0) + 1
    dropped = [s for s, n in counts.items() if n < 5]
    if dropped:
        cat_doc['categories'] = [c for c in cat_doc['categories']
                                 if c['slug'] not in dropped]
        pros = [p for p in pros if p['category'] not in dropped]

    pros_doc = {'captured': '2026-09-26', 'pros': sorted(
        pros, key=lambda p: (p['category'], p['name'].lower()))}

    # ---------------- content ----------------
    content = build_content(pros, image_manifest)

    (SITE / 'source_data_categories.json').write_text(
        json.dumps(cat_doc, indent=1, sort_keys=True, ensure_ascii=False) + '\n')
    (SITE / 'source_data_pros.json').write_text(
        json.dumps(pros_doc, indent=1, sort_keys=True, ensure_ascii=False) + '\n')
    (SITE / 'source_data_content.json').write_text(
        json.dumps(content, indent=1, sort_keys=True, ensure_ascii=False) + '\n')
    (SITE / 'scraped_data' / 'image_manifest.json').write_text(
        json.dumps(image_manifest, indent=1, sort_keys=True) + '\n')

    print(f"categories: {len(cat_doc['categories'])}")
    for c in cat_doc['categories']:
        print(f"  {c['slug']:34s} {counts.get(c['slug'], 0)} pros  questions={len(c['questions'])} quote_qs={len(c['quote_questions'])}")
    print(f"pros: {len(pros)}  images: {len(image_manifest)}")


def build_content(pros, image_manifest):
    """Cost guides, homepage content, users, activity, reply pools."""
    guides = load_cost_guides()

    # homepage cities (captured footer links)
    home_cities = [
        {'slug': 'atlanta', 'state': 'ga', 'name': 'Atlanta'},
        {'slug': 'boston', 'state': 'ma', 'name': 'Boston'},
        {'slug': 'dallas', 'state': 'tx', 'name': 'Dallas'},
        {'slug': 'denver', 'state': 'co', 'name': 'Denver'},
        {'slug': 'houston', 'state': 'tx', 'name': 'Houston'},
        {'slug': 'miami', 'state': 'fl', 'name': 'Miami'},
        {'slug': 'phoenix', 'state': 'az', 'name': 'Phoenix'},
        {'slug': 'san-francisco', 'state': 'ca', 'name': 'San Francisco'},
        {'slug': 'seattle', 'state': 'wa', 'name': 'Seattle'},
        {'slug': 'washington', 'state': 'dc', 'name': 'Washington DC'},
    ]

    # hero + explore card images (real upstream ids)
    image_manifest['hero/hero_home.webp'] = (
        'https://production-next-images-cdn.thumbtack.com/i/581196300008611840/width/1600.webp')
    image_manifest['hero/explore_prices.jpg'] = (
        'https://production-next-images-cdn.thumbtack.com/i/560976066258427904/width/1024.jpeg')
    image_manifest['hero/explore_maintenance.jpg'] = (
        'https://production-next-images-cdn.thumbtack.com/i/560976114082316293/width/1024.jpeg')
    image_manifest['hero/explore_guides.jpg'] = (
        'https://production-next-images-cdn.thumbtack.com/i/560976126317412357/width/1024.jpeg')
    for slug, iid in [('house-cleaning', ICON_IDS['house-cleaning']),
                      ('affordable-plumbing-services', ICON_IDS['plumbing']),
                      ('interior-painting', ICON_IDS['painting']),
                      ('handyman', ICON_IDS['handyman']),
                      ('lawn-care', ICON_IDS['lawn-care']),
                      ('appliance-repair', ICON_IDS['appliance']),
                      ('landscaping', ICON_IDS['landscaping']),
                      ('tv-wall-mount-install', ICON_IDS['tv-mount']),
                      ('furniture-assembly', ICON_IDS['furniture']),
                      ('roofing', ICON_IDS['roofing']),
                      ('exterminators', ICON_IDS['pest']),
                      ('makeup-artists', ICON_IDS['makeup']),
                      ('wedding-photographers', ICON_IDS['photography']),
                      ('personal-trainers', ICON_IDS['training']),
                      ('local-movers', ICON_IDS['moving']),
                      ('djs', ICON_IDS['dj'])]:
        image_manifest[f'icons/{slug}_icon.jpg'] = (
            f'https://production-next-images-cdn.thumbtack.com/i/{iid}/desktop/retina/centered_large_thumb')
        image_manifest[f'icons/{slug}_card.jpg'] = (
            f'https://production-next-images-cdn.thumbtack.com/i/{iid}/desktop/retina/centered_large_thumb')

    guarantee_blocks = [
        ['What\'s covered', 'If you hire a pro on Thumbtack and the job isn\'t completed as agreed, or the pro doesn\'t show up, you may be eligible for up to $2,500 back.'],
        ['How to file', 'Go to your project page, choose the hire that went wrong, and select "Request Guarantee help" within 60 days of the hire date.'],
        ['What\'s not covered', 'Changes you make to the project after hiring, damage from work you did yourself, or jobs you paid for outside Thumbtack.'],
        ['Our commitment', 'We stand behind the pros on our platform. If something goes wrong, our team reviews your case and makes it right.'],
    ]
    how_it_works = [
        ['Tell us what you need', 'Answer a few quick questions about your project — it takes under two minutes.'],
        ['Get matched with pros', 'We show you local pros who fit your project, with ratings, reviews and response times.'],
        ['Hire with confidence', 'Compare quotes, message pros directly, and hire the one you like — backed by the Thumbtack Guarantee.'],
    ]

    benchmark_users = [
        {'username': 'alice_j', 'email': 'alice.j@test.com', 'display_name': 'Alice Johnson',
         'phone': '(206) 555-0142', 'zip': '98052', 'address': '8211 164th Ave NE, Redmond, WA 98052'},
        {'username': 'bob_c', 'email': 'bob.c@test.com', 'display_name': 'Bob Chen',
         'phone': '(206) 555-0184', 'zip': '98101', 'address': '1420 4th Ave, Seattle, WA 98101'},
        {'username': 'carol_d', 'email': 'carol.d@test.com', 'display_name': 'Carol Davis',
         'phone': '(425) 555-0117', 'zip': '98004', 'address': '500 108th Ave NE, Bellevue, WA 98004'},
        {'username': 'david_k', 'email': 'david.k@test.com', 'display_name': 'David Kim',
         'phone': '(425) 555-0198', 'zip': '98033', 'address': '111 Central Way, Kirkland, WA 98033'},
    ]

    by_cat = {}
    for p in pros:
        by_cat.setdefault(p['category'], []).append(p)
    def pick(cat, idx):
        lst = sorted(by_cat.get(cat, []), key=lambda p: (-p['rating'], p['name']))
        return lst[idx % len(lst)] if lst else None
    def pk(cat, idx):
        p = pick(cat, idx)
        return p['service_pk'] if p else None

    user_activity = [
        {'email': 'alice.j@test.com',
         'saved_pros': [pk('house-cleaning', 0), pk('interior-painting', 0), pk('wedding-photographers', 0)],
         'projects': [
             {'category': 'house-cleaning', 'zip': '98052',
              'details': 'One-time deep clean before a family visit.',
              'timeline': 'Within a week',
              'answers': [['Frequency', 'Just once'], ['Number of bedrooms', '3 bedrooms'],
                          ['Cleaning type', 'Deep cleaning'], ['Number of bathrooms', '2 bathrooms'],
                          ['Pets', 'Pets in home']],
              'status': 'completed', 'hired': [pk('house-cleaning', 0)]},
             {'category': 'tv-wall-mount-install', 'zip': '98052',
              'details': 'Mount a 65" TV above the fireplace and hide the cables.',
              'timeline': 'Within 48 hours',
              'answers': [['TV size', 'TV larger than 60 inches'], ['Wall type', 'Drywall'],
                          ['Mount type', 'Tilt (angled up or down)']],
              'status': 'matched'},
         ],
         'threads': [
             {'pro': pk('house-cleaning', 1),
              'messages': [['user', 'Hi! Do you bring your own cleaning supplies, or should I have them ready?'],
                          ['pro', 'Hi! We bring all of our own supplies and equipment — you don\'t need to prepare anything except access to the rooms.']]}]},
        {'email': 'bob.c@test.com',
         'saved_pros': [pk('local-movers', 0), pk('local-movers', 1), pk('appliance-repair', 0), pk('handyman', 0), pk('handyman', 1)],
         'projects': [
             {'category': 'local-movers', 'zip': '98101',
              'details': 'Move a 2-bedroom apartment from Seattle to Bellevue, one flight of stairs.',
              'timeline': 'Within a week',
              'answers': [['Move distance', 'Local (under 50 miles)'], ['Home size', '2 bedrooms']],
              'status': 'matched'},
         ],
         'threads': []},
        {'email': 'carol.d@test.com',
         'saved_pros': [pk('wedding-photographers', 1), pk('djs', 0), pk('makeup-artists', 0)],
         'projects': [
             {'category': 'wedding-photographers', 'zip': '98004',
              'details': 'Wedding photography for an October garden wedding, ~80 guests.',
              'timeline': 'Flexible on timeline',
              'answers': [['Event type', 'Wedding'], ['Coverage needed', 'Full day']],
              'status': 'hired', 'hired': [pk('wedding-photographers', 1)]},
         ],
         'threads': []},
        {'email': 'david.k@test.com',
         'saved_pros': [pk('lawn-care', 0), pk('landscaping', 0)],
         'projects': [
             {'category': 'lawn-care', 'zip': '98033',
              'details': 'Weekly mow and edge for a medium front and back yard.',
              'timeline': 'Within a week',
              'answers': [['Frequency', 'Every week'], ['Yard size', 'Medium']],
              'status': 'matched'},
         ],
         'threads': []},
    ]
    user_activity = [u for u in user_activity if all(
        v is not None for v in u['saved_pros'])]

    pro_replies = {
        'default': {
            'keyword': [
                {'when': ['weekend', 'sunday', 'saturday', 'availability', 'available', 'dates', 'schedule'],
                 'reply': 'Hi! Thanks for reaching out. We do have openings — could you share a couple of dates that work for you?'},
                {'when': ['price', 'cost', 'quote', 'charge', 'how much', 'estimate'],
                 'reply': 'Hello! Pricing depends on the scope, but we can send a firm quote once we know a few more details. Requesting a quote through Thumbtack is the fastest way.'},
                {'when': ['supplies', 'equipment', 'bring', 'materials', 'tools'],
                 'reply': 'Hi! We bring all of our own equipment and materials — you don\'t need to prepare anything.'},
            ],
            'fallback': [
                'Hi, thanks for the message! Yes, we take on projects like this regularly. What\'s your ideal start date?',
                'Hello, {pro} here. Happy to help — tell me a bit more about the job and we\'ll go from there.',
                'Thanks for reaching out! We\'d love to help with that. When would you like us to take a look?',
            ],
        },
        'house-cleaning': {
            'keyword': [
                {'when': ['supplies', 'bring', 'products', 'equipment'],
                 'reply': 'Hi! We bring all of our own supplies and equipment — you don\'t need to prepare anything except access to the rooms.'},
                {'when': ['oven', 'fridge', 'refrigerator', 'laundry', 'window', 'extra'],
                 'reply': 'Hello! Yes, we can add that to the visit — just mention it in your quote request and we\'ll include it in the price.'},
                {'when': ['weekend', 'sunday', 'saturday', 'availability', 'available', 'dates', 'schedule'],
                 'reply': 'Thanks for reaching out! We\'re happy to work around your schedule — including weekends. Which day works best?'},
                {'when': ['supplies', 'insured', 'bonded', 'license'],
                 'reply': 'We\'re insured and bonded, and every visit is backed by the Thumbtack Guarantee.'},
            ],
            'fallback': [
                'Hi! We\'d love to help. Deep cleans for a home your size usually take our team 3-4 hours.',
                'Hello, thanks for the message! We have openings this week — shall I pencil you in?',
            ],
        },
        'affordable-plumbing-services': {
            'keyword': [
                {'when': ['emergency', 'urgent', 'leak', 'burst', 'flood', 'drip', 'tonight', 'asap'],
                 'reply': 'Hi! For a job like this we can usually be there same-day or next-day. Please avoid using that fixture until we\'ve had a look.'},
                {'when': ['price', 'cost', 'charge', 'how much', 'fee'],
                 'reply': 'Hello, {pro} here. We charge a flat diagnostic fee that is waived if you hire us for the repair.'},
            ],
            'fallback': [
                'Thanks for the message! We\'ll bring all the parts we\'re likely to need — does this week work for a visit?',
                'Hi! Happy to help with that. What day suits you for us to come by?',
            ],
        },
        'wedding-photographers': {
            'keyword': [
                {'when': ['october', 'date', 'available', 'availability', 'wedding date'],
                 'reply': 'Hi! Congratulations! We\'d love to shoot your wedding — could you tell me the venue and date so I can check availability?'},
                {'when': ['package', 'price', 'cost', 'pricing', 'how much', 'include'],
                 'reply': 'Hello! Our full-day coverage includes a second shooter and an online gallery within 6 weeks. Happy to send a full pricing guide.'},
            ],
            'fallback': [
                'Thanks for reaching out! Tell me a little about your day and we\'ll tailor a package for you.',
            ],
        },
        'djs': {
            'keyword': [
                {'when': ['october', 'date', 'available', 'availability'],
                 'reply': 'Hi! We\'d love to be part of it — tell me the date and venue and I\'ll confirm availability right away.'},
                {'when': ['package', 'price', 'cost', 'how much', 'hours', 'include'],
                 'reply': 'Hello, {pro} here. Our standard package includes 4 hours of music, MC services, and a full light rig.'},
                {'when': ['music', 'genre', 'song', 'playlist', 'requests'],
                 'reply': 'Great question! We take requests all night — send us your must-play list and we\'ll build the set around it.'},
            ],
            'fallback': [
                'Thanks for the message! We always confirm the must-play and do-not-play lists two weeks before the event.',
            ],
        },
        'makeup-artists': {
            'keyword': [
                {'when': ['october', 'date', 'available', 'availability', 'trial'],
                 'reply': 'Hi! I\'d love to do your makeup — tell me the date and location and I\'ll check my calendar. Trials are available too.'},
            ],
            'fallback': [
                'Hello! Thanks for reaching out. I travel to you and bring everything needed for the look you want.',
            ],
        },
        'personal-trainers': {
            'keyword': [
                {'when': ['week', 'schedule', 'session', 'twice', 'times per week', 'start'],
                 'reply': 'Hi! Great timing — I have morning and evening slots open. Twice a week is a perfect pace to start.'},
            ],
            'fallback': [
                'Hello! Thanks for the message. Tell me your goals and we\'ll build a plan that fits your schedule.',
            ],
        },
    }
    quote_notes = [
        'Happy to help — based on what you described, this quote covers labor and standard materials.',
        'Thanks for the details! This is our estimate for the scope you described; we can adjust after an on-site visit.',
        'We\'d love to take this on. The quote reflects the timeline you asked for, and we can start right away.',
        'Appreciate you reaching out through Thumbtack! This quote includes everything we discussed.',
        'This is our all-in estimate — no hidden fees. Let me know if you\'d like to adjust the scope.',
    ]

    featured = [
        {'name': 'Photographer', 'price': 550},
        {'name': 'Handyman', 'price': 70},
        {'name': 'House Cleaner', 'price': 240},
        {'name': 'Pet Sitter', 'price': 40},
        {'name': 'Yoga Instructor', 'price': 150},
        {'name': 'Personal Trainer', 'price': 80},
        {'name': 'Plumber', 'price': 80},
        {'name': 'Exterminator', 'price': 120},
    ]
    near_me_popular = [
        ['House Cleaning', 'house-cleaning'],
        ['Plumbing Pipe Repair', 'affordable-plumbing-services'],
        ['Interior Painting', 'interior-painting'],
        ['Full Service Lawn Care', 'lawn-care'],
        ['Electrical and Appliance Repair', 'appliance-repair'],
        ['Outdoor Landscaping and Design', 'landscaping'],
        ['Handyman', 'handyman'],
        ['TV Mounting', 'tv-wall-mount-install'],
        ['Furniture Assembly', 'furniture-assembly'],
        ['Appliance Repair or Maintenance', 'appliance-repair'],
        ['Wedding and Event Makeup', 'makeup-artists'],
        ['Wedding and Event Photography', 'wedding-photographers'],
        ['Personal Training', 'personal-trainers'],
        ['Local Moving (under 50 miles)', 'local-movers'],
        ['DJ Services', 'djs'],
        ['Roof Repair or Maintenance', 'roofing'],
        ['Pest Control Services', 'exterminators'],
    ]

    return {
        'cost_guides': guides,
        'home_cities': home_cities,
        'guarantee_blocks': guarantee_blocks,
        'how_it_works': how_it_works,
        'benchmark_users': benchmark_users,
        'user_activity': user_activity,
        'pro_replies': pro_replies,
        'quote_notes': quote_notes,
        'price_featured': featured,
        'near_me_popular': near_me_popular,
    }


def load_cost_guides():
    """Load the scraped cost-guide captures (scraped_data/cost_*.json)."""
    out = []
    d = SITE / 'scraped_data'
    for f in sorted(d.glob('cost_*.json')):
        try:
            out.extend(json.loads(f.read_text()))
        except Exception:
            pass
    return out


if __name__ == '__main__':
    main()
