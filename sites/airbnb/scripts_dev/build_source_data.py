#!/usr/bin/env python3
"""Build the tracked source_data/*.json snapshots from the real upstream
captures under scraped_data/captures/ (see provenance.json).

Everything materialized here traces to a capture file; the builder only
trims (drops fields the mirror does not render) and normalizes shape.
Run with python3.11 (needs bs4 for the amenities-modal parse):
  python3.11 scripts_dev/build_source_data.py
"""
import base64
import json
import os
import re
import sys

try:
    from bs4 import BeautifulSoup
except ImportError:  # pragma: no cover
    BeautifulSoup = None

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.dirname(HERE)
CAP = os.path.join(SITE, 'scraped_data', 'captures')
OUT = os.path.join(SITE, 'source_data')

DESTINATIONS = [
    ('asheville', 'Asheville, North Carolina'),
    ('austin', 'Austin, Texas'),
    ('new-york', 'New York, New York'),
    ('los-angeles', 'Los Angeles, California'),
    ('miami', 'Miami, Florida'),
    ('lake-tahoe', 'Lake Tahoe, California'),
    ('nashville', 'Nashville, Tennessee'),
    ('scottsdale', 'Scottsdale, Arizona'),
]
EXP_CITIES = [('austin', 'Austin'), ('new-york', 'New York'),
              ('los-angeles', 'Los Angeles'), ('miami', 'Miami')]
PHOTOS_PER_LISTING = 7
PHOTOS_PER_EXPERIENCE = 4
IM_WIDTH = 720            # the upstream CDN's own resize parameter


def imw(url):
    """The exact upstream CDN URL the mirror fetches. The im_w resize
    parameter is the upstream site's own CDN parameter for photo-tour
    images; avatar URLs are already sized and are kept verbatim."""
    if not url:
        return None
    base = url.split('?')[0]
    if '/im/pictures/' not in base:
        return url
    return base + f'?im_w={IM_WIDTH}'


def deferred(html):
    m = re.search(r'<script[^>]*id="data-deferred-state-0"[^>]*>(.*?)</script>',
                  html, re.S)
    if not m:
        return None
    return json.loads(m.group(1))


def niobe(html):
    d = deferred(html)
    if not d:
        return None
    for item in d.get('niobeClientData') or []:
        if isinstance(item, list) and len(item) >= 2 and isinstance(item[0], str):
            return item[1]
    return None


def read(path):
    with open(path, encoding='utf-8', errors='replace') as f:
        return f.read()


def ugc(node):
    if not node:
        return None
    return (node.get('localizedStringWithTranslationPreference')
            or node.get('localizedString') or node.get('source'))


def lid_from_b64(demand_id):
    try:
        return base64.b64decode(demand_id).decode().split(':')[-1]
    except Exception:
        return None


def price_lines(sdp):
    """{'total': '$1,311', 'qualifier': 'for 5 nights', 'nightly': '$262.20',
    'nights': 5, 'details': [...]} from a StructuredDisplayPrice."""
    if not sdp:
        return None
    out = {'details': []}
    pl = sdp.get('primaryLine') or {}
    out['total'] = pl.get('price')
    out['qualifier'] = pl.get('qualifier')
    exp = sdp.get('explanationData') or {}
    for group in exp.get('priceDetails') or []:
        for item in group.get('items') or []:
            out['details'].append({'description': item.get('description'),
                                   'price': item.get('priceString')})
            m = re.match(r'(\d+) nights? x \$([0-9.,]+)',
                         item.get('description') or '')
            if m:
                out['nights'] = int(m.group(1))
                out['nightly'] = '$' + m.group(2)
    return out


def parse_filter_panel(panel):
    """Trim the upstream SERP filter panel to the facets the mirror renders."""
    out = {'price': None, 'room_types': [], 'rooms_and_beds': [],
           'standout': [], 'booking': [], 'amenities': [],
           'property_types': [], 'accessibility': []}
    fpc = panel.get('filterPanelSections') or {}
    sections = fpc.get('sections') or []
    for s in sections:
        sid = s.get('sectionId') or ''
        sd = s.get('sectionData') or {}
        items = sd.get('discreteFilterItems') or []
        if sid.endswith('PRICE_RANGE'):
            for it in items:
                out['price'] = {
                    'min': it.get('minValue'),
                    'max': it.get('maxValue'),
                    'histogram': it.get('priceHistogram'),
                    'text': ((it.get('text') or {}).get('title')),
                    'subtitle': ((it.get('text') or {}).get('subtitle')),
                }
        elif sid.endswith('ROOM_TYPE'):
            for it in items:
                for sub in it.get('values') or []:
                    pass
                out['room_types'].append(room_type_item(it))
        elif sid.endswith('ROOMS_AND_BEDS_WITH_SUBCATEGORY'):
            for it in items:
                out['rooms_and_beds'].append(stepper_item(it))
        elif sid.endswith('TOP_TIER_STAYS'):
            for it in items:
                for sub in grid_items(it):
                    out['standout'].append(sub)
        elif sid.endswith('BOOKING_OPTIONS'):
            for it in items:
                out['booking'].append(pill_item(it))
        elif sid.endswith('MORE_FILTERS_AMENITIES_WITH_SUBCATEGORIES'):
            for it in items:
                if it.get('__typename') == 'ExploreTitleFilterItem':
                    continue
                out['amenities'].append(pill_item(it))
        elif sid.endswith('PROPERTY_TYPES_WITH_SUBCATEGORY'):
            for it in items:
                out['property_types'].append(pill_item(it))
        elif sid.endswith('ACCESSIBILITY'):
            for it in items:
                if it.get('__typename') == 'ExploreTitleFilterItem':
                    continue
                out['accessibility'].append(pill_item(it))
    return out


def room_type_item(it):
    sub_items = []
    for sub in it.get('exploreOptions') or []:
        txt = sub.get('exploreFilterItem') or {}
        t = txt.get('filterItemText') or {}
        sp = (txt.get('searchParams') or {}).get('params') or []
        params = {p.get('key'): p.get('value') for p in sp}
        sub_items.append({'title': t.get('title'),
                          'subtitle': t.get('subtitle'),
                          'params': params})
    return {'title': ((it.get('filterItemText') or {}).get('title')),
            'sub_items': sub_items}


def stepper_item(it):
    txt = it.get('filterItemText') or {}
    sp = (it.get('searchParams') or {}).get('params') or []
    params = {p.get('key'): p.get('value') for p in sp}
    return {'title': txt.get('title'), 'params': params}


def grid_items(it):
    outs = []
    for sub in it.get('gridItems') or []:
        txt = sub.get('exploreFilterItem') or {}
        t = (txt.get('filterItemText') or {})
        sp = (txt.get('searchParams') or {}).get('params') or []
        params = {p.get('key'): p.get('value') for p in sp}
        outs.append({'title': t.get('title'), 'subtitle': t.get('subtitle'),
                     'params': params,
                     'icon': (txt.get('icon') or {}).get('localKey')})
    return outs


def pill_item(it):
    t = it.get('filterItemText') or {}
    sp = (it.get('searchParams') or {}).get('params') or []
    params = {p.get('key'): p.get('value') for p in sp}
    return {'title': t.get('title'), 'subtitle': t.get('subtitle'),
            'params': params}


# ------------------------------------------------------------- SERP parsing --

def serp_sections(slug, fname):
    p = os.path.join(CAP, fname)
    if not os.path.exists(p):
        return []
    payload = niobe(read(p))
    if not payload:
        return []
    try:
        res = payload['data']['presentation']['staysSearch']['results']
    except KeyError:
        return []
    return res


def serp_payload(slug, fname):
    p = os.path.join(CAP, fname)
    if not os.path.exists(p):
        return None
    payload = niobe(read(p))
    return payload


def build_destinations():
    dests = {}
    listings = {}
    for slug, label in DESTINATIONS:
        p1 = serp_payload(slug, f'serp_{slug}_p1.html')
        res = p1['data']['presentation']['staysSearch']['results']
        filter_panel = parse_filter_panel(res['filters'])
        seo = res.get('seo') or {}
        sec_cfg = res.get('sectionConfiguration') or {}
        cards = []
        seen_ids = set()
        for fname in (f'serp_{slug}_p1.html', f'serp_{slug}_p2.html'):
            r2 = serp_payload(slug, fname)
            if not r2:
                continue
            try:
                srs = r2['data']['presentation']['staysSearch']['results']['searchResults']
            except KeyError:
                continue
            for sec in srs:
                dsl = sec.get('demandStayListing') or {}
                lid = lid_from_b64(dsl.get('id') or '')
                if not lid or lid in seen_ids:
                    continue
                seen_ids.add(lid)
                cards.append(serp_card(slug, sec, lid))
        # second date range: prices only
        rng = serp_payload(slug, f'serp_{slug}_range2.html')
        range2 = {}
        if rng:
            try:
                srs2 = rng['data']['presentation']['staysSearch']['results']['searchResults']
            except KeyError:
                srs2 = []
            for sec in srs2:
                dsl = sec.get('demandStayListing') or {}
                lid = lid_from_b64(dsl.get('id') or '')
                if lid:
                    range2[lid] = price_lines(sec.get('structuredDisplayPrice'))
        dests[slug] = {
            'slug': slug,
            'label': label,
            'city': label.split(',')[0],
            'region': label.split(', ', 1)[1] if ', ' in label else '',
            'seo_title': seo.get('title'),
            'seo_subtitle': seo.get('subtitle'),
            'filter_panel': filter_panel,
            'upstream_total': upstream_total(res),
            'listing_ids': [c['id'] for c in cards],
        }
        for c in cards:
            c['price_range2'] = range2.get(c['id'])
            listings[c['id']] = c
        print(slug, '->', len(cards), 'listings captured')
    return dests, listings


def upstream_total(res):
    """'1,397 stays' style headline if present."""
    meta = res.get('loggingMetadata') or {}
    txt = None
    sa = res.get('staysSearchAnnouncements') or []
    for a in sa:
        if isinstance(a, dict) and a.get('body'):
            txt = a['body']
            break
    si = res.get('searchInput') or {}
    return {'announcement': txt}


def serp_card(slug, sec, lid):
    sc = sec.get('structuredContent') or {}
    primary = [m.get('body') for m in (sc.get('primaryLine') or [])]
    secondary = [m.get('body') for m in (sc.get('secondaryLine') or [])]
    badges = []
    for b in sec.get('badges') or []:
        badges.append({'text': b.get('text'),
                       'type': ((b.get('loggingContext') or {}).get('badgeType'))})
    dsl = sec.get('demandStayListing') or {}
    loc = dsl.get('location') or {}
    coord = loc.get('coordinate') or {}
    pics = []
    for p in (sec.get('contextualPictures') or [])[:3]:
        pics.append(imw(p.get('picture')))
    price = price_lines(sec.get('structuredDisplayPrice'))
    title = sec.get('title') or ''
    parts = title.split(' in ', 1)
    if len(parts) == 2:
        ptype, city = parts[0], parts[1]
    else:
        ptype, city = '', title
    name = ugc(sec.get('nameLocalized'))
    subtitle = sec.get('subtitle')
    rating = sec.get('avgRatingLocalized')
    return {
        'id': lid,
        'destination': slug,
        'title': title,
        'property_type': ptype,
        'city': city,
        'name': name,
        'subtitle': subtitle,
        'rating': rating if rating != 'New' else None,
        'is_new': rating == 'New',
        'badges': badges,
        'is_superhost': any(b.get('type') == 'SUPERHOST' for b in badges),
        'is_guest_favorite': any(b.get('type') == 'TOP_X_GUEST_FAVORITE'
                                 for b in badges),
        'primary_lines': primary,
        'date_window': secondary[0] if secondary else None,
        'price': price,
        'lat': coord.get('latitude'),
        'lng': coord.get('longitude'),
        'photos': pics,
        'dsl_name': ugc((dsl.get('description') or {}).get('name')),
        'payment_messages': [m.get('text') for m in (sec.get('paymentMessages') or [])],
    }


# ------------------------------------------------------------- PDP parsing --

def amenities_from_dom(dom_html):
    """The grouped amenity tree from the rendered 'Show all amenities'
    modal: every group renders as a heading followed by a
    ul[aria-label=<group>] whose items are the amenity names."""
    if BeautifulSoup is None:
        raise SystemExit('build needs bs4 (python3.11)')
    soup = BeautifulSoup(dom_html, 'html.parser')
    groups = []
    for ul in soup.find_all('ul', attrs={'aria-label': True}):
        label = (ul.get('aria-label') or '').strip()
        if not label:
            continue
        prev = ul.find_previous(['h2', 'h3'])
        if prev is None or prev.get_text(strip=True) != label:
            continue
        items = []
        for li in ul.find_all('li'):
            t = li.get_text(' ', strip=True)
            if t and t not in items:
                items.append(t)
        if items:
            groups.append({'title': label, 'items': items})
    return groups


def pdp_files(lid):
    d = os.path.join(CAP, 'pdp', str(lid))
    out = {}
    if not os.path.isdir(d):
        return out
    for fn in os.listdir(d):
        p = os.path.join(d, fn)
        if fn == 'initial.html':
            out['initial'] = p
        elif fn == 'dom.html':
            out['dom'] = p
        elif fn.endswith('.json') and fn != 'capture.meta.json':
            m = re.match(r'\d+_(GET|POST)_(\w+)\.json', fn)
            if m:
                out.setdefault(m.group(2), p)
    return out


def jsonfile(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def photo_tour(initial_html):
    """PhotoTourModalSection media items: full photo set with captions."""
    d = deferred(initial_html)
    if not d:
        return []
    try:
        secs = d['niobeClientData'][0][1]['data']['presentation'][
            'stayProductDetailPage']['sections']['sections']
    except KeyError:
        return []
    for s in secs:
        inner = s.get('section') or {}
        if inner.get('__typename') == 'PhotoTourModalSection':
            items = inner.get('mediaItems') or []
            photos = []
            for m in items:
                img = m.get('image') or {}
                photos.append({
                    'uri': imw(img.get('uri') or m.get('uri')),
                    'alt': img.get('accessibilityLabel') or m.get('title'),
                    'caption': m.get('title'),
                })
            return photos
    return []


def jsonld(initial_html):
    blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>',
                        initial_html, re.S)
    out = []
    for b in blocks:
        try:
            out.append(json.loads(b))
        except Exception:
            pass
    return out


def listing_detail(lid, card):
    files = pdp_files(lid)
    if 'dom' not in files or 'initial' not in files:
        return None
    detail = {}
    initial = read(files['initial'])
    dom = read(files['dom'])
    lds = jsonld(initial)
    vr = next((x for x in lds if x.get('@type') == 'VacationRental'), {})
    product = next((x for x in lds if x.get('@type') == 'Product'), {})
    detail['ld_name'] = vr.get('name') or product.get('name')
    detail['ld_description'] = vr.get('description') or product.get('description')
    detail['ld_images'] = [imw(u) for u in (vr.get('image') or [])]
    detail['address_locality'] = ((vr.get('address') or {}).get('addressLocality'))
    agg = vr.get('aggregateRating') or {}
    detail['ld_rating'] = agg.get('ratingValue')
    detail['ld_rating_count'] = agg.get('ratingCount')
    detail['photos'] = photo_tour(initial)[:PHOTOS_PER_LISTING]
    if not detail['photos']:
        detail['photos'] = [{'uri': u, 'alt': detail['ld_name'], 'caption': None}
                            for u in detail['ld_images'][:PHOTOS_PER_LISTING]]

    # node payload from the StaysPdpSections POST the page itself issues
    if 'StaysPdpSections' in files:
        d = jsonfile(files['StaysPdpSections'])
        node = (d['response'].get('data') or {}).get('node') or {}
        pdp = node.get('pdpPresentation') or {}
        desc = (pdp.get('descriptions') or {})
        detail['description_html'] = ugc(desc.get('longDescriptionHtml'))
        overview = pdp.get('overview') or {}
        detail['overview_items'] = overview.get('items') or []
        # book-it facts the PDP section payload carries per listing
        try:
            secs = d['response']['data']['presentation']['stayProductDetailPage']['sections']['sections']
        except KeyError:
            secs = []
        for s in secs:
            inner = s.get('section') or {}
            if inner.get('__typename') == 'BookItSection' and inner.get('canInstantBook') is not None:
                detail['instant_book'] = bool(inner.get('canInstantBook'))
                detail['pets_allowed'] = bool(inner.get('petsAllowed'))
                detail['max_guest_capacity'] = inner.get('maxGuestCapacity')
                break
        q = pdp.get('quality') or {}
        lrs = q.get('listingRatingStats') or {}
        detail['quality'] = {
            'is_guest_favorite': q.get('isGuestFavorite'),
            'guest_favorite_description': q.get('guestFavoriteDescription'),
            'percentile': q.get('qualityScorePercentileBucket'),
            'rating_average': ((lrs.get('overallRatingStats') or {}).get('ratingAverage')),
            'rating_count': str((lrs.get('overallRatingStats') or {}).get('ratingCount') or ''),
            'category_ratings': [
                {'category': c.get('categoryTypeA'),
                 'average': ((c.get('value') or {}).get('ratingAverage'))}
                for c in (lrs.get('categoryRatingStats') or [])],
        }
        host = pdp.get('hostInfo') or {}
        detail['host'] = {
            'title': ((host.get('overview') or {}).get('title') or {}).get('text'),
            'items': [i.get('text') for i in
                      ((host.get('overview') or {}).get('items') or [])],
        }
        rules = pdp.get('rules') or {}
        detail['house_rules'] = rules_details(rules)
        safety = pdp.get('safetyAndProperty') or {}
        detail['safety'] = rules_details(safety)
        sa = pdp.get('sleepingArrangements') or {}
        detail['sleeping'] = [
            {'name': s.get('name'),
             'items': [i.get('title') for i in (s.get('items') or [])]}
            for s in (sa.get('stops') or [])]
        detail['person_capacity'] = node.get('personCapacity')
        loc = node.get('location') or {}
        detail['coordinate'] = (loc.get('coordinate') or {})
        sharing = (pdp.get('sharingConfig') or {})
        detail['share_url'] = sharing.get('shareUrl')
        seo = pdp.get('seoLinks') or {}
        detail['explore'] = [
            {'title': l.get('title'), 'subtitle': l.get('subtitle'),
             'path': l.get('path')}
            for l in (seo.get('nearbyCityLinks') or [])[:8]]
        detail['highlights_from_sections'] = [
            {'title': h.get('title'), 'body': h.get('body')}
            for h in (pdp.get('highlights') or [])]

    # things to know (house rules preview) from the policies query
    if 'StaysPdpPoliciesQuery' in files:
        d = jsonfile(files['StaysPdpPoliciesQuery'])
        pdp = ((d['response'].get('data') or {}).get('node') or {}).get('pdpPresentation') or {}
        ttk = pdp.get('thingsToKnow') or []
        detail['things_to_know'] = [
            {'title': x.get('title'), 'preview': x.get('previewItems') or [],
             'type': x.get('type')} for x in ttk]

    # calendar availability (365 days)
    if 'PdpAvailabilityCalendar' in files:
        d = jsonfile(files['PdpAvailabilityCalendar'])
        try:
            months = d['response']['data']['merlin']['pdpAvailabilityCalendar']['calendarMonths']
        except KeyError:
            months = []
        detail['calendar'] = [
            {'date': day['calendarDate'], 'available': bool(day.get('available'))}
            for m in months for day in (m.get('days') or [])]

    # reviews (24 from the page's own query)
    if 'StaysPdpReviewsQuery' in files:
        d = jsonfile(files['StaysPdpReviewsQuery'])
        try:
            rv = d['response']['data']['presentation']['stayProductDetailPage']['reviews']
        except KeyError:
            rv = {}
        meta = rv.get('metadata') or {}
        detail['reviews_meta'] = {
            'count': meta.get('reviewsCount'),
            'tags': [{'name': t.get('localizedName'), 'count': t.get('count')}
                     for t in (meta.get('reviewTags') or [])],
        }
        revs = []
        for r in (rv.get('reviews') or []):
            revs.append({
                'id': r.get('id'),
                'rating': r.get('rating'),
                'comments': r.get('comments'),
                'created_at': r.get('createdAt'),
                'localized_date': r.get('localizedDate'),
                'reviewer': (r.get('reviewer') or {}).get('firstName'),
                'reviewer_location': r.get('localizedReviewerLocation'),
                'reviewer_img': imw((r.get('reviewer') or {}).get('pictureUrl')),
                'host_response': (r.get('response') or {}).get('text') if isinstance(r.get('response'), dict) else None,
                'reviewee_img': imw((r.get('reviewee') or {}).get('pictureUrl')),
            })
        detail['reviews'] = revs

    # similar listings
    if 'SimilarListingsCarouselQuery' in files:
        d = jsonfile(files['SimilarListingsCarouselQuery'])
        try:
            edges = d['response']['data']['node']['similarStays']['stays']['edges']
        except (KeyError, TypeError):
            edges = []
        sim = []
        for e in edges:
            n = e.get('node') or {}
            sim.append({
                'id': lid_from_b64(n.get('id') or '') or n.get('id'),
                'name': ugc((n.get('description') or {}).get('name')),
                'title': n.get('title'),
                'city': n.get('city'),
                'rating': n.get('avgRating'),
                'reviews': n.get('reviewsCount'),
                'price': n.get('price'),
                'photo': imw(n.get('contextualImage')) or imw((n.get('pictures') or [{}])[0].get('picture')),
            })
        detail['similar'] = [s for s in sim if s['id']]

    # amenities (grouped) from the rendered modal
    detail['amenities'] = amenities_from_dom(dom)
    detail['amenity_count'] = 0
    m = re.search(r'Show all (\d+) amenities', dom)
    if m:
        detail['amenity_count'] = int(m.group(1))
    else:
        detail['amenity_count'] = sum(len(g['items']) for g in detail['amenities'])

    # guest favorite hero banner + host name from the rendered DOM
    m = re.search(r'aria-label="([^"]+)"[^>]*>[^<]*<[^>]*>Guest favorite', dom)
    detail['dom_guest_favorite'] = 'Guest favorite' in dom
    return detail


def rules_details(rules):
    out = {'title': rules.get('title'), 'description': rules.get('description'),
           'groups': []}
    for g in (rules.get('groupItems') or []):
        out['groups'].append({
            'title': g.get('title'),
            'items': [{'title': i.get('title'), 'description': i.get('description')}
                      for i in (g.get('items') or [])],
        })
    return out


# ------------------------------------------------------- experiences parsing --

def exp_serp_items(slug):
    p = os.path.join(CAP, f'eserp_{slug}.html')
    payload = niobe(read(p))
    items = []
    panel = None
    if payload:
        res = payload['data']['presentation']['experiencesSearch']['results']
        srs = res.get('searchResults') or []
        header = ''
        for s in srs:
            if s.get('__typename') == 'HeaderInsert':
                header = s.get('title')
        for s in srs:
            if s.get('__typename') != 'ExperienceSearchResult':
                continue
            listing = s.get('listing') or {}
            desc = (listing.get('descriptions') or {})
            name = ugc((desc.get('name') or {}).get('localizedValue'))
            byline = ugc((desc.get('byline') or {}).get('localizedValue'))
            lrs = (listing.get('listingRatingStats') or {}).get('overallRatingStats') or {}
            price = price_lines_exp(s.get('displayPrice'))
            items.append({
                'id': str(s.get('id')),
                'city_slug': slug,
                'name': name,
                'byline': byline,
                'theme': s.get('primaryThemeFormatted'),
                'rating': lrs.get('ratingAverage'),
                'rating_count': str(lrs.get('ratingCount') or ''),
                'price': price,
                'badges': [b.get('texts') for b in (s.get('searchBadges') or [])],
                'photos': [imw(p.get('picture')) for p in (s.get('posterPictures') or [])[:2]],
            })
        fp = (res.get('filters') or {}).get('filterPanel') or {}
        panel = parse_exp_filter_panel(fp)
    return {'header': header, 'items': items, 'filter_panel': panel}


def price_lines_exp(sdp):
    if not sdp:
        return None
    pl = sdp.get('primaryLine') or {}
    comps = [c for c in (pl.get('orderedComponents') or [])]
    price = next((c.get('discountedPrice') or c.get('price') for c in comps
                  if c.get('discountedPrice') or c.get('price')), None)
    qualifier = next((c.get('qualifier') for c in comps if c.get('qualifier')), None)
    leading = next((c.get('leadingContent') for c in comps if c.get('leadingContent')), None)
    return {'price': price, 'qualifier': qualifier, 'leading': leading,
            'accessibility': pl.get('accessibilityLabel')}


def parse_exp_filter_panel(fp):
    out = {'categories': [], 'traveler_type': [], 'time_of_day': [], 'languages': []}
    fpc = fp.get('filterPanelSections') or {}
    for s in (fpc.get('sections') or []):
        sid = s.get('sectionId') or ''
        sd = s.get('sectionData') or {}
        for it in (sd.get('discreteFilterItems') or []):
            t = ((it.get('filterItemText') or {}).get('title')
                 or (it.get('text') or {}).get('title'))
            if sid.endswith('TAXONOMY'):
                out['categories'].append(t)
            elif sid.endswith('EXPERIENCE_TRAVELER_TYPE'):
                out['traveler_type'].append(t)
            elif sid.endswith('EXPERIENCE_TIME_OF_DAY'):
                out['time_of_day'].append(t)
            elif sid.endswith('HOST_LANGUAGE'):
                out['languages'].append(t)
    return out


def exp_detail(eid):
    p = os.path.join(CAP, f'exp_{eid}.html')
    if not os.path.exists(p):
        return None
    t = read(p)
    out = {'id': str(eid)}
    # the embedded activityListing payload
    for m in re.finditer(r'<script[^>]*type="application/json"[^>]*>(.*?)</script>', t, re.S):
        blob = m.group(1)
        if 'activityListing' not in blob:
            continue
        try:
            d = json.loads(blob)
        except Exception:
            continue
        al = find_key(d, 'activityListing')
        if not al:
            continue
        desc = al.get('descriptions') or {}
        out['name'] = ugc((desc.get('name') or {}).get('localizedValue'))
        out['byline'] = ugc((desc.get('byline') or {}).get('localizedValue'))
        out['description'] = ugc((desc.get('description') or {}).get('localizedValue'))
        lrs = (al.get('listingRatingStats') or {}).get('overallRatingStats') or {}
        out['rating'] = lrs.get('ratingAverage')
        out['rating_count'] = str(lrs.get('ratingCount') or '')
        media = al.get('media') or {}
        photos = [imw((media.get('coverImageEntity') or {}).get('uri'))]
        for extra in (media.get('additionalImageEntities') or [])[:PHOTOS_PER_EXPERIENCE - 1]:
            photos.append(imw(extra.get('uri')))
        out['photos'] = [p for p in photos if p]
        owner = al.get('contextualOwner') or {}
        out['host_name'] = owner.get('displayFirstName')
        out['host_type'] = (al.get('pdpHighlights') or [{}])[0].get('localizedName', {}).get('text') if (al.get('pdpHighlights') or [{}])[0].get('type') == 'PROFILE' else None
        hl = []
        for h in (al.get('pdpHighlights') or []):
            hl.append({'type': h.get('type'),
                       'name': ((h.get('localizedName') or {}).get('text')),
                       'text': ugc((h.get('localizedDescription') or {}).get('content')),
                       'image': imw(h.get('imageUrl'))})
        out['highlights'] = hl
        ttk = []
        for x in ((al.get('pdpPresentation') or {}).get('thingsToKnow') or []):
            ttk.append({'title': x.get('title'),
                        'text': (((x.get('localizedDescription') or {}).get('text')))})
        out['things_to_know'] = ttk
        acc = [e.get('node', {}).get('name') for e in
               ((al.get('accessibilityFeatures') or {}).get('edges') or [])]
        out['accessibility'] = acc
        gr = al.get('guestRequirements') or {}
        out['guest_requirements'] = {
            'min_age': (gr.get('minAge') or {}).get('minAge'),
            'children_allowed': (gr.get('childrenAllowed') or {}).get('isEnabled'),
            'infants_allowed': (gr.get('infantsAllowed') or {}).get('isEnabled'),
        }
        # offerings -> upcoming availability instances (dates, times,
        # duration, remaining capacity exactly as the upstream page shows)
        offers = []
        for e in ((al.get('offerings') or {}).get('publishedOfferings') or {}).get('edges') or []:
            n = e.get('node') or {}
            for de in ((n.get('ticketedDayAvailability') or {}).get('edges') or []):
                dn = de.get('node') or {}
                if not dn.get('isAvailable'):
                    continue
                offers.append({
                    'day': dn.get('instanceDay'),
                    'start_time': dn.get('instanceStartTime'),
                    'iso': dn.get('instanceStartTimeWithOffset'),
                    'duration': dn.get('instanceDuration'),
                    'remaining': dn.get('remainingCapacity'),
                })
        out['offerings'] = offers[:12]
        # agenda -> "What you'll do"
        agenda = []
        for e in ((al.get('offerings') or {}).get('publishedOfferings') or {}).get('edges') or []:
            n = e.get('node') or {}
            ag = (n.get('agenda') or {}).get('publishedAgendaItems') or {}
            for ae in (ag.get('edges') or []):
                ai = ae.get('node') or {}
                agenda.append({
                    'title': ai.get('title'),
                    'body': ugc(ai.get('body')),
                    'image': imw(((ai.get('coverImageEntity') or {}).get('uri'))),
                })
            break
        out['agenda'] = agenda
        # reviews
        revs = []
        for e in (al.get('reviewsSearch') or {}).get('edges') or []:
            r = (e.get('node') or {})
            review = r.get('review') or {}
            revs.append({
                'rating': review.get('rating'),
                'comments': r.get('highlightedComment') or ugc(review.get('comments')),
                'localized_date': review.get('localizedDate'),
                'reviewer': (review.get('reviewer') or {}).get('firstName'),
            })
        out['reviews'] = revs[:12]
        out['meeting'] = None
        meeting = al.get('meetingTypes') or []
        out['location'] = ((al.get('location') or {}).get('address') or {})
        break
    # from the rendered HTML: What you'll do paragraphs + where we'll meet
    out['whats_you_doing'] = dom_section_paragraphs(t, 'What you\u2019ll do')
    out['meeting_text'] = dom_section_paragraphs(t, 'Where we\u2019ll meet')
    return out


def dom_section_paragraphs(html_text, header):
    if BeautifulSoup is None:
        raise SystemExit('build needs bs4 (python3.11)')
    soup = BeautifulSoup(html_text, 'html.parser')
    for h in soup.find_all(re.compile(r'^h[1-5]$')):
        if h.get_text(strip=True).replace('\u2019', '\u2019') == header:
            paras = []
            for p in h.find_all_next(['p', 'h3']):
                txt = p.get_text(' ', strip=True)
                if not txt:
                    continue
                if p.name == 'h3' and paras:
                    break
                paras.append(txt)
                if len(paras) > 40:
                    break
            return paras
    return []


def find_key(o, key):
    if isinstance(o, dict):
        for k, v in o.items():
            if k == key:
                return v
            r = find_key(v, key)
            if r is not None:
                return r
    elif isinstance(o, list):
        for v in o:
            r = find_key(v, key)
            if r is not None:
                return r
    return None


def build_home():
    p = os.path.join(CAP, 'home.html')
    payload = niobe(read(p))
    out = {'destinations_label': 'Destinations for you'}
    if payload:
        tvh = payload['data']['presentation']['homepage']['tabbedVerticalHomepage']
        fs = tvh['feedSections']['sections']
        for s in fs:
            sd = s.get('sectionData') or {}
            sid = s.get('sectionId') or ''
            if isinstance(sd.get('title'), dict):
                title = sd['title'].get('text')
            else:
                title = sd.get('title')
            if sid == 'DESTINATION_SUGGESTIONS':
                items = []
                for it in (sd.get('items') or []):
                    items.append(it.get('title'))
                out['destination_suggestions'] = items
                out['destination_suggestions_title'] = title
    return out


def main():
    os.makedirs(OUT, exist_ok=True)
    home = build_home()
    with open(os.path.join(OUT, 'home.json'), 'w') as f:
        json.dump(home, f, indent=1, sort_keys=True)
    print('home.json:', list(home.keys()))

    dests, listings = build_destinations()
    with open(os.path.join(OUT, 'destinations.json'), 'w') as f:
        json.dump(dests, f, indent=1, sort_keys=True)

    details = {}
    missing = []
    for lid, card in listings.items():
        d = listing_detail(lid, card)
        if d is None:
            missing.append(lid)
            continue
        d['id'] = lid
        d['destination'] = card['destination']
        details[lid] = d
    print('listing details:', len(details), 'missing:', len(missing), missing[:8])
    with open(os.path.join(OUT, 'listing_details.json'), 'w') as f:
        json.dump(details, f, indent=1, sort_keys=True)
    with open(os.path.join(OUT, 'listings.json'), 'w') as f:
        json.dump(listings, f, indent=1, sort_keys=True)

    exps = {}
    exp_details = {}
    for slug, city in EXP_CITIES:
        data = exp_serp_items(slug)
        for it in data['items']:
            exps[it['id']] = it
    for eid in exps:
        d = exp_detail(eid)
        if d:
            exp_details[eid] = d
            exps[eid]['name'] = d.get('name') or exps[eid].get('name')
    print('experiences:', len(exps), 'details:', len(exp_details))
    with open(os.path.join(OUT, 'experiences.json'), 'w') as f:
        json.dump(exps, f, indent=1, sort_keys=True)
    with open(os.path.join(OUT, 'experience_details.json'), 'w') as f:
        json.dump(exp_details, f, indent=1, sort_keys=True)


if __name__ == '__main__':
    main()
