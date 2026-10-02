#!/usr/bin/env python3
"""Build the deterministic source_data_*.json snapshots from scraped data.

Parses scraped_data/tour_progress.jsonl (tour detail records),
scraped_data/serp_cards.json (catalog cards), scraped_data/pages/*.json
(landing pages), scraped_data/api/*.json (structured API payloads) into:

  source_data_tours.json     one record per tour with days, departures,
                             reviews, Q&A, good-to-know, images
  source_data_catalog.json   operators + destinations
  source_data_content.json   homepage moments, platform reviews, promo codes

Everything is written in a fixed order so the seed build is byte-reproducible.
"""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRAPE = ROOT / "scraped_data"

URL_MAP = {}


def map_image(local, url):
    if local and url:
        URL_MAP.setdefault(local, url)
    return local

MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July',
          'August', 'September', 'October', 'November', 'December']
MONTH_ABBR = {m[:3]: i + 1 for i, m in enumerate(MONTHS)}


def month_abbr_index(abbr):
    return MONTH_ABBR[abbr]

DEST_GROUPS = {
    'Africa': ['egypt', 'morocco', 'south-africa', 'kenya', 'tanzania',
               'namibia', 'africa'],
    'Asia': ['china', 'india', 'japan', 'new-zealand', 'philippines',
             'sri-lanka', 'thailand', 'vietnam', 'indonesia', 'jordan',
             'nepal', 'asia'],
    'Australia': ['australia'],
    'Europe': ['croatia', 'greece', 'iceland', 'ireland', 'italy',
               'portugal', 'scotland', 'spain', 'turkey', 'france',
               'england', 'germany', 'switzerland', 'europe'],
    'Latin America': ['argentina', 'brazil', 'chile', 'peru', 'mexico',
                      'costa-rica', 'latin-america'],
    'North America': ['canada', 'usa'],
}

STYLE_NAMES = {
    'adventure': 'Adventure', 'bicycle': 'Bicycle',
    'hiking-trekking': 'Hiking & Trekking', 'northern-lights': 'Northern Lights',
    'river-cruise': 'River Cruise', 'in-depth-cultural': 'In-Depth Cultural',
    'coach-bus': 'Coach / Bus', 'train-rail': 'Train / Rail',
    'beach': 'Beach', 'family': 'Family', 'private': 'Private',
    'safari': 'Safari', 'sailing': 'Sailing', 'polar': 'Polar',
    'food-culinary': 'Food & Culinary', 'health-spa-wellness': 'Health, Spa & Wellness',
    'overland-truck': 'Overland Truck', 'wildlife': 'Wildlife',
    'festival-events': 'Festival & Events',
}

REGION_NAMES = {
    'south-america': 'South America', 'eastern-europe': 'Eastern Europe',
    'great-britain-uk': 'Great Britain & UK', 'nordic-scandinavia': 'Scandinavia',
}

PLACE_NAMES = {
    'islands-bali': 'Bali', 'islands-greek-islands': 'Greek Islands',
    'islands-sicily': 'Sicily', 'mountain-annapurna': 'Mount Annapurna',
    'mountain-everest': 'Mount Everest', 'mountain-machu-picchu': 'Machu Picchu',
    'mountain-mount-kilimanjaro': 'Mount Kilimanjaro',
    'national-park-grand-canyon': 'Grand Canyon',
    'region-amalfi-coast': 'Amalfi Coast',
    'region-antarctica-south-pole': 'Antarctica & South Pole',
    'region-arctic-north-pole': 'Arctic & North Pole',
    'region-golden-triangle-southeast-asia': 'Golden Triangle Southeast Asia',
    'region-great-barrier-reef': 'Great Barrier Reef',
    'region-holy-land': 'Holy Land', 'region-patagonia': 'Patagonia',
    'region-tuscany': 'Tuscany', 'river-danube': 'Danube River Cruises',
    'river-douro': 'Douro River Cruises', 'river-main': 'Main River Cruises',
    'river-mekong': 'Mekong River Cruises', 'river-nile': 'Nile River Cruises',
    'river-rhine': 'Rhine River Cruises', 'state-alaska': 'Alaska',
    'state-california': 'California',
}


def slugify(value):
    value = re.sub(r"[^\w\s-]", '', value.lower())
    return re.sub(r"[-\s]+", '-', value).strip('-')


# ------------------------------------------------------------- tour parsers --

def _page_min_age(rec):
    m = re.search(r'Ages (\d+)(?: to (\d+))?', rec.get('reviews_raw') or '')
    panel = rec.get('op_panel_raw') or ''
    m2 = re.search(r'Age range\n(\d+)-(\d+)', panel)
    if m2:
        return int(m2.group(1))
    return int(m.group(1)) if m else None


def parse_days(days_raw):
    """days_raw: [{day, text}] -> [{day, title, included, optional, meals,
    landmarks, start_point}]

    Some upstream day blocks were captured with an over-greedy container
    climb: the text starts at the itinerary section header (e.g. "Intro\n
    Introduction\nDay 1\n...") and runs through several following days. When
    a later "Day N" marker appears inside one block, cut the text there so
    each parsed day keeps only its own rows."""
    out = []
    for d in sorted(days_raw or [], key=lambda x: x['day']):
        lines = [l.strip() for l in d['text'].split('\n')]
        # Over-captured blocks start above the day's own heading (section
        # headers, earlier days). Slice from THIS day's "Day N" marker to the
        # next foreign "Day M" marker so each block keeps only its own rows;
        # clean blocks (own marker at index 0, no foreign marker) are intact.
        own = f"Day {d['day']}"
        start = 0
        for i, l in enumerate(lines):
            if l == own:
                start = i
                break
        end = len(lines)
        for i in range(start + 1, len(lines)):
            m = re.fullmatch(r'Day (\d+)', lines[i])
            if m and int(m.group(1)) != d['day']:
                end = i
                break
        lines = lines[start:end]
        # drop the leading "Day N" and the duplicated title
        title = None
        idx = 0
        if lines and lines[0].startswith('Day '):
            idx = 1
        if idx < len(lines):
            title = lines[idx]
            idx += 1
        # skip duplicated title + "Show on map"
        sections = {'included': [], 'optional': [], 'landmarks': [],
                    'meals': None, 'start_point': None}
        current = None
        for line in lines[idx:]:
            if not line:
                continue
            if line == title or line == 'Show on map':
                continue
            if line in ('Included Activities', 'Optional Activities',
                        'Landmarks', 'Meals', 'Start point', 'Accommodation'):
                current = {'Included Activities': 'included',
                           'Optional Activities': 'optional',
                           'Landmarks': 'landmarks'}.get(line, line)
                continue
            if line.startswith('View on map'):
                continue
            if current == 'included':
                sections['included'].append(line)
            elif current == 'optional':
                sections['optional'].append(line)
            elif current == 'landmarks':
                sections['landmarks'].append(line)
            elif current == 'Meals':
                sections['meals'] = (sections['meals'] or '') + line
            elif current == 'Start point':
                sections['start_point'] = (sections['start_point'] or '') + line
            elif current == 'Accommodation':
                sections.setdefault('accommodation', [])
                sections['accommodation'].append(line)
        out.append({'day': d['day'], 'title': title or f"Day {d['day']}",
                    'included': sections['included'],
                    'optional': sections['optional'],
                    'landmarks': sections['landmarks'],
                    'meals': sections['meals'],
                    'start_point': sections['start_point'],
                    'data_id': d.get('data_id')})
    return out


def parse_departures(rows):
    """rows: raw departure li texts -> structured dicts."""
    out = []
    for row in rows or []:
        text = row
        # dates
        m = re.search(r'From (\w+)\n(\d{1,2}) (\w+), (\d{4})\nTo (\w+)\n(\d{1,2}) (\w+), (\d{4})', text)
        if not m:
            continue
        start = f"{m.group(4)}-{month_abbr_index(m.group(3)):02d}-{int(m.group(2)):02d}"
        end = f"{m.group(8)}-{month_abbr_index(m.group(7)):02d}-{int(m.group(6)):02d}"
        sold_out = 'Sold out' in text
        instant = 'Instant Confirmation' in text
        guaranteed = 'Guaranteed departure' in text
        dm = re.search(r'^-(\d+)%', text, re.M)
        discount = int(dm.group(1)) if dm else None
        lang = None
        lm = re.search(r'\n(English|Spanish|German|French|Portuguese)\n', text)
        if lm:
            lang = lm.group(1)
        # prices: "From:\n$2,590\nUS\n$1,735\nper person" or "From:\nUS\n$1,890\nper person"
        was = None
        price = None
        pm = re.search(r'From:\n\$([\d,]+)\nUS\n?\$?([\d,]+)\s*per person', text.replace('\nUS\n', '\nUS\n'))
        if pm:
            was = int(pm.group(1).replace(',', ''))
            price = int(pm.group(2).replace(',', ''))
        else:
            pm2 = re.search(r'From:\nUS\n\$([\d,]+)\s*per person', text)
            if pm2:
                price = int(pm2.group(1).replace(',', ''))
        if price is None:
            pm3 = re.search(r'US\n\$([\d,]+)', text)
            if pm3:
                price = int(pm3.group(1).replace(',', ''))
        if price is None:
            continue
        basis = None
        bm = re.search(r'Price based on ([^\n]+)', text)
        if bm:
            basis = bm.group(1).strip()
        out.append({'start': start, 'end': end,
                    'status': 'sold_out' if sold_out else 'available',
                    'price': price, 'was': was, 'discount': discount,
                    'guaranteed': guaranteed, 'instant': instant,
                    'language': lang, 'basis': basis})
    # dedupe by start date
    seen = set()
    dedup = []
    for d in out:
        if d['start'] in seen:
            continue
        seen.add(d['start'])
        dedup.append(d)
    return dedup


SUBRATING_KEYS = ['Itinerary', 'Transport', 'Guide', 'Accommodation',
                  'Food', 'Tour Operator']


def parse_reviews(reviews_raw):
    """reviews_raw text -> (subratings dict, list of review dicts)."""
    if not reviews_raw:
        return {}, []
    subratings = {}
    for key in SUBRATING_KEYS:
        m = re.search(re.escape(key) + r'\n(\d(?:\.\d)?)', reviews_raw)
        if m:
            subratings[key] = float(m.group(1))
    # cut header
    idx = reviews_raw.find('Sort:')
    if idx < 0:
        return subratings, []
    body = reviews_raw[idx:]
    # split reviews on the "<rating>\n•\n<Month Year>" pattern
    starts = [m.start() for m in re.finditer(r'\n(\d\.\d)\n•\n', body)]
    if not starts:
        return subratings, []
    reviews = []
    for i, s in enumerate(starts):
        chunk = body[s + 1:]
        end = starts[i + 1] if i + 1 < len(starts) else len(body)
        chunk = chunk[:end - s - 1]
        lines = [l.strip() for l in chunk.split('\n')]
        rating = float(lines[0])
        pos = 1
        if pos < len(lines) and lines[pos] == '\u2022':
            pos += 1
        month = None
        if pos < len(lines) and re.fullmatch(r'[A-Z][a-z]+ \d{4}', lines[pos]):
            month = lines[pos]
            pos += 1
        # author: walk back from the split point in previous text
        # (initials + name appear just before the rating)
        # find them in the preceding raw text
        prev = body[:s + 1].rstrip('\n').split('\n')
        author = None
        initials = None
        for back in range(1, 4):
            if len(prev) >= back and prev[-back]:
                pass
        # pattern: ... <INITIALS>\n<Name>\n<rating>  OR  ...<Name>\n<rating>
        if len(prev) >= 2 and prev[-1] and not re.fullmatch(r'\d\.\d', prev[-1]):
            author = prev[-1]
            if len(prev) >= 3 and re.fullmatch(r'[A-Z]{1,3}', prev[-2]):
                initials = prev[-2]
        elif len(prev) >= 2 and re.fullmatch(r'[A-Z]{1,3}', prev[-2]):
            initials = prev[-2]
            author = prev[-3] if len(prev) >= 3 else None
        if author is None and initials:
            author = initials
        # guide
        guide = None
        if pos < len(lines) and lines[pos].startswith('Led by '):
            guide = lines[pos][len('Led by '):]
            pos += 1
        # translated marker
        while pos < len(lines) and (lines[pos].startswith('Automatically translated')
                                     or lines[pos].startswith('Rate this translation')):
            pos += 1
        # title: a short line followed by longer body
        title = None
        rest = [l for l in lines[pos:] if l]
        # remove trailing markers
        cleaned = []
        skip_next = 0
        for j, l in enumerate(rest):
            if l == 'Show more':
                continue
            if l.startswith('Traveled in '):
                break
            if l.startswith('Reply from:'):
                break
            cleaned.append(l)
        reply = None
        reply_by = None
        rm = re.search(r'Reply from: ([^\n]+)\n([\s\S]*?)(?=\n[A-Z]{1,3}\n|\n\d\.\d\n•\n|$)', chunk)
        if rm:
            reply_by = rm.group(1)
            reply = rm.group(2).strip()
        traveled = None
        tm = re.search(r'Traveled in ([A-Z][a-z]+ \d{4})', chunk)
        if tm:
            traveled = tm.group(1)
        if cleaned:
            if len(cleaned) > 1 and len(cleaned[0]) < 80 and len(cleaned[1]) > len(cleaned[0]):
                title = cleaned[0]
                text_body = ' '.join(cleaned[1:])
            else:
                text_body = ' '.join(cleaned)
        else:
            text_body = ''
        text_body = re.sub(r'\s+', ' ', text_body).strip()
        if len(text_body) > 900:
            text_body = text_body[:900].rsplit(' ', 1)[0] + '...'
        if not author:
            author = 'Traveler'
        reviews.append({'author': author, 'initials': initials,
                        'rating': rating, 'month': month,
                        'traveled': traveled, 'title': title,
                        'body': text_body, 'guide': guide,
                        'reply': reply, 'reply_by': reply_by})
    return subratings, reviews


def parse_gtk(raw):
    if not raw:
        return {}
    gtk = {}
    # currencies
    m = re.search(r'Currenc(?:ies|y)\n([\s\S]*?)(?:\nPlugs & Adapters\n|$)', raw)
    if m:
        gtk['currencies'] = re.sub(r'\s+', ' ', m.group(1)).strip()[:600]
    m = re.search(r'Plugs & Adapters\n([\s\S]*?)(?:\nVaccines\n|$)', raw)
    if m:
        gtk['plugs'] = re.sub(r'\s+', ' ', m.group(1)).strip()[:600]
    m = re.search(r'Vaccines\n([\s\S]*?)(?:\nVisa\n|$)', raw)
    if m:
        gtk['vaccines'] = re.sub(r'\s+', ' ', m.group(1)).strip()[:600]
    m = re.search(r'\nVisa\n([\s\S]*)$', raw)
    if m:
        gtk['visa'] = re.sub(r'\s+', ' ', m.group(1)).strip()[:600]
    return gtk


TAG_VOCAB = {'Accommodation', 'Meals', 'Group size', 'Tour Details', 'Flights',
             'Transport', 'Itinerary', 'Booking', 'Payment', 'Visa', 'Insurance',
             'Packing', 'Health', 'Dates', 'Price', 'Guides', 'Activities',
             'Price / Availability', 'Age Range', 'Cancellation', 'Rooms',
             'Tour Style', 'Optional Activities'}


def parse_qa(raw):
    if not raw:
        return []
    qa = []
    # question blocks: "<INIT>\n<Name>\nAsked on <date>\n<question>"
    role_re = re.compile(r'(?:(?P<pre>.*?))(?P<role>Traveler|Operator)\s*[\u2022\u2013-]\s*Written\s+(?P<date>.+)$')
    blocks = re.split(r'\n(?=[A-Z]{1,3}\n\n[^\n]+\n\nAsked on )', raw)
    if len(blocks) <= 1:
        blocks = re.split(r'\n(?=[^\n]{2,60}\n\nAsked on )', raw)
    for block in blocks[1:]:
        lines = [l.strip() for l in block.split('\n') if l.strip()]
        if len(lines) < 3:
            continue
        ai = next((i for i, l in enumerate(lines) if l.startswith('Asked on ')), None)
        if ai is None or ai < 1:
            continue
        asker = lines[ai - 1]
        asked_date = lines[ai][len('Asked on '):]
        rest = lines[ai + 1:]
        q_lines = []
        tags = []
        answer = None
        answer_by = None
        answer_date = None
        i = 0
        while i < len(rest):
            l = rest[i]
            am = role_re.match(l)
            if am:
                name = ''
                pre = (am.group('pre') or '').strip()
                if pre:
                    answer_by = (pre + ' ' + am.group('role')).strip()
                else:
                    name = rest[i - 1] if i >= 1 and rest[i - 1] not in TAG_VOCAB else ''
                    answer_by = ((name + ' ') if name else '') + am.group('role')
                answer_date = am.group('date').strip()
                ans_lines = []
                j = i + 1
                while j < len(rest):
                    if role_re.match(rest[j]) or re.fullmatch(r'\d+ more answers?', rest[j]):
                        break
                    ans_lines.append(rest[j])
                    j += 1
                answer = ' '.join(ans_lines)
                # strip answerer initials/name from the question tail
                if name and q_lines and q_lines[-1] == name:
                    q_lines.pop()
                if q_lines and re.fullmatch(r'[A-Z]{1,3}', q_lines[-1]):
                    q_lines.pop()
                break
            if l in TAG_VOCAB:
                tags.append(l)
                i += 1
                continue
            if re.fullmatch(r'\d+ more answers?', l):
                i += 1
                continue
            q_lines.append(l)
            i += 1
        question = ' '.join(q_lines).strip()
        if not question:
            continue
        if answer:
            answer = re.sub(r'\s+', ' ', answer).strip()
            if len(answer) > 900:
                answer = answer[:900].rsplit(' ', 1)[0] + '...'
        qa.append({'question': question, 'asker': asker,
                   'asked_date': asked_date, 'tags': tags,
                   'answer': answer, 'answer_by': answer_by,
                   'answer_date': answer_date})
    return qa[:4]


def pick_images(rec):
    """Choose hero/gallery/avatar/review-photo paths from the record's image
    list, mapping upstream CDN urls to local static/images paths."""
    imgs = rec.get('images') or []
    tour_id = rec['tour_id']
    hero = None
    gallery = []
    avatars = []
    review_photos = []
    moments_imgs = []
    for img in imgs:
        src = img.get('src') or ''
        alt = img.get('alt') or ''
        if '/s3/tour/360x210/' in src:
            if not hero:
                hero = map_image(f"tours/{tour_id}_card{pathlib.Path(src.split('/')[-1]).suffix}", src)
        elif '/s3/tour/' in src and ('430x252' in src or '720x480' in src):
            fn = src.split('/')[-1]
            gallery.append(map_image(f"tours/{tour_id}_{fn}", src))
        elif '/moments/' in src:
            fn = src.split('/')[-2] + '_' + src.split('/')[-1]
            moments_imgs.append((map_image(f"moments/{fn}", src), alt))
        elif '/s3/traveller/' in src:
            fn = src.split('/')[-1]
            avatars.append((map_image(f"travellers/{fn}", src), alt))
        elif '/s3/review/' in src:
            fn = src.split('/')[-1]
            review_photos.append((map_image(f"reviews/{fn}", src), alt))
        elif '/s3/op/' in src:
            pass  # operator logos handled at catalog level
    return {'hero': hero, 'gallery': gallery[:6], 'avatars': avatars[:6],
            'review_photos': review_photos[:8], 'moments': moments_imgs[:6]}


# ------------------------------------------------------- destination parser --


# membership + keyword proxies for the region / place / collection pages.
# member lists mirror the upstream destination hierarchy (mega-menu groups);
# keyword lists match tours whose name or city list mentions the place.
B_MEMBERS = {
    'south-america': ['argentina', 'brazil', 'chile', 'peru', 'colombia',
                      'ecuador', 'panama', 'costa-rica', 'mexico', 'latin-america'],
    'eastern-europe': ['croatia', 'poland', 'hungary', 'romania', 'bulgaria',
                       'czech-republic', 'slovakia', 'slovenia', 'serbia',
                       'bosnia', 'albania', 'montenegro', 'greece', 'turkey'],
    'great-britain-uk': ['england', 'scotland', 'wales', 'ireland'],
    'nordic-scandinavia': ['iceland', 'norway', 'finland', 'sweden', 'denmark'],
}
V_MEMBERS = {
    'islands-bali': ['indonesia'], 'islands-greek-islands': ['greece'],
    'islands-sicily': ['italy'], 'mountain-annapurna': ['nepal'],
    'mountain-everest': ['nepal'], 'mountain-machu-picchu': ['peru'],
    'mountain-mount-kilimanjaro': ['tanzania'],
    'national-park-grand-canyon': ['usa'], 'region-amalfi-coast': ['italy'],
    'region-antarctica-south-pole': [], 'region-arctic-north-pole': [],
    'region-golden-triangle-southeast-asia': ['thailand', 'vietnam', 'laos', 'cambodia'],
    'region-great-barrier-reef': ['australia'],
    'region-holy-land': ['israel', 'jordan'],
    'region-patagonia': ['argentina', 'chile'], 'region-tuscany': ['italy'],
    'river-danube': ['germany', 'austria', 'slovakia', 'hungary', 'croatia',
                     'serbia', 'romania', 'bulgaria'],
    'river-douro': ['portugal', 'spain'], 'river-main': ['germany'],
    'river-mekong': ['vietnam', 'cambodia', 'laos', 'thailand'],
    'river-nile': ['egypt'],
    'river-rhine': ['germany', 'france', 'switzerland', 'netherlands'],
    'state-alaska': ['usa'], 'state-california': ['usa'],
}
V_KEYWORDS = {
    'islands-bali': ['Bali'], 'islands-greek-islands': ['Greek Island', 'Mykonos', 'Santorini', 'Paros', 'Naxos'],
    'islands-sicily': ['Sicily'], 'mountain-annapurna': ['Annapurna'],
    'mountain-everest': ['Everest'], 'mountain-machu-picchu': ['Machu Picchu'],
    'mountain-mount-kilimanjaro': ['Kilimanjaro'],
    'national-park-grand-canyon': ['Grand Canyon'],
    'region-amalfi-coast': ['Amalfi'], 'region-antarctica-south-pole': ['Antarctica'],
    'region-arctic-north-pole': ['Arctic'],
    'region-golden-triangle-southeast-asia': ['Golden Triangle'],
    'region-great-barrier-reef': ['Barrier Reef'],
    'region-holy-land': ['Holy Land'], 'region-patagonia': ['Patagonia'],
    'region-tuscany': ['Tuscany'], 'river-danube': ['Danube'],
    'river-douro': ['Douro'], 'river-main': ['Rhine-Main', 'Main River'],
    'river-mekong': ['Mekong'], 'river-nile': ['Nile'], 'river-rhine': ['Rhine'],
    'state-alaska': ['Alaska'], 'state-california': ['California'],
}
I_MEMBERS = {'africa-safari': ['kenya', 'tanzania', 'south-africa', 'namibia',
                               'botswana', 'uganda', 'rwanda', 'zambia', 'zimbabwe', 'africa']}
I_KEYWORDS = {'africa-safari': ['Safari']}


def _assign_collection_slugs(tour):
    """Append b/v/i slugs the tour really belongs to."""
    slugs = set(tour.get('dest_slugs') or [])
    name = (tour.get('name') or '').lower()
    city_text = ' '.join(tour.get('cities') or []).lower()
    for slug, members in B_MEMBERS.items():
        if any(m in slugs for m in members):
            slugs.add(slug)
    for slug, members in V_MEMBERS.items():
        kws = [k.lower() for k in V_KEYWORDS.get(slug, [])]
        if (any(m in slugs for m in members)
                and any(k in name or k in city_text for k in kws)) \
                or any(k in name for k in kws):
            slugs.add(slug)
    for slug, members in I_MEMBERS.items():
        kws = [k.lower() for k in I_KEYWORDS.get(slug, [])]
        if (any(m in slugs for m in members) and any(k in name or k in city_text for k in kws)) \
                or any(k in name for k in kws):
            slugs.add(slug)
    tour['dest_slugs'] = sorted(slugs)

def parse_dest_page(page):
    """page: dict from pages/d-<slug>.json -> destination record."""
    text = page['text']
    slug = page['name'].split('-', 1)[1]
    name_m = re.search(r'([A-Z][^\n]+) Tours & Trips\n', text)
    name = name_m.group(1).strip() if name_m else slug.replace('-', ' ').title()
    desc = None
    dm = re.search(r'Tours & Trips\n\n([\s\S]*?)\n\nSelect Date', text)
    if dm:
        desc = dm.group(1).strip()
    hero = None
    for img in page.get('images') or []:
        if '/s3/serp/750x400/' in (img.get('src') or ''):
            hero = map_image(f"destinations/{slug}{pathlib.Path(img['src'].split('/')[-1]).suffix}", img["src"])
            break
    sections = {}
    # budget section
    bm = re.search(r'(Tours for Every Budget[^\n]*)\n([\s\S]*?)(?:\n[A-Z][^\n]{25,}\n|$)', text)
    if bm:
        body = re.sub(r'\n+', ' | ', bm.group(2).strip())[:400]
        sections[bm.group(1).strip()] = body
    # best time to visit: the upstream page prints the heading twice — once
    # as a nav link near the top, once above the real season copy. The real
    # section is the occurrence followed by season words; it runs until the
    # "<dest> travel guides - curated by our experts" card list.
    tm = None
    for m in re.finditer(r'Best time to visit [^\n]*\n', text):
        tail = text[m.end():m.end() + 400]
        if re.search(r'\b(Spring|Summer|Fall|Autumn|Winter)\b', tail):
            tm = m
            break
    if tm:
        rest = text[tm.end():]
        em = re.search(r'\n[^\n]{2,40}travel guides - curated by our experts',
                       rest, re.I)
        body = rest[:em.start()] if em else rest[:4000]
        body = re.sub(r'\n+', ' ', body.strip())
        body = re.sub(r'(\d{4} \d+ tours)', ' | \\1', body)[:2000]
        sections[tm.group(0).strip()] = body
    return {'slug': slug, 'name': name, 'description': desc, 'hero': hero,
            'sections': sections}


# ---------------------------------------------------------- operator parser --

def parse_operator_page(page, op_id):
    text = page['text']
    slug = page['name'].split('-', 1)[1]
    name = None
    nm = re.search(r'\n([A-Z][A-Za-z0-9&.,\'!? -]{2,60})\n\n?(?:Platinum|Gold|Silver|Verified)\n', text)
    if nm:
        name = nm.group(1).strip()
    else:
        nm2 = re.search(r'Home\n/\n([^\n]+)\n', text)
        if nm2:
            name = nm2.group(1).strip()
    # key the operator by its parsed NAME (matches how tours reference
    # operators, via slugify(operator name)) so page-scraped and
    # panel-derived records merge instead of duplicating (o-intrepid.json
    # is 'Intrepid Travel' on the page, not 'Intrepid')
    if name:
        slug = slugify(name) or slug
    rating = None
    reviews = None
    rm = re.search(r'Rating\n(\d\.\d)\n\(([\d,]+) reviews\)', text) or \
        re.search(r'Rating\n(\d\.\d)\nNumber of reviews\n([\d,]+)', text)
    if rm:
        rating = float(rm.group(1))
        reviews = int(rm.group(2).replace(',', ''))
    tours_count = None
    tcm = re.search(r'Number of tours\n(\d[\d,]*)', text)
    if tcm:
        tours_count = int(tcm.group(1).replace(',', ''))
    hq = None
    hqm = re.search(r'Headquarters in ([^\n]+)', text)
    if hqm:
        hq = hqm.group(1).strip()
    rr = None
    rrm = re.search(r'Response rate\n(\d+%)', text)
    if rrm:
        rr = rrm.group(1)
    rt = None
    rtm = re.search(r'Response time\n([^\n]+)', text)
    if rtm:
        rt = rtm.group(1).strip()
    age = None
    am = re.search(r'Age range\n(\d+)-(\d+)', text)
    if am:
        age = (int(am.group(1)), int(am.group(2)))
    about = None
    abm = re.search(r'About\n([\s\S]*?)\nFind Adventures', text)
    if abm:
        about = re.sub(r'\s+', ' ', abm.group(1)).strip()[:900]
    logo = None
    for img in page.get('images') or []:
        if '/s3/op/' in (img.get('src') or ''):
            fn = img['src'].split('/')[-1]
            logo = map_image(f"operators/{fn}", img["src"])
            break
    badge = None
    if 'Platinum' in text[:4000]:
        badge = 'platinum'
    elif 'Gold' in text[:4000]:
        badge = 'gold'
    elif 'Silver' in text[:4000]:
        badge = 'silver'
    return {'id': op_id, 'slug': slug, 'name': name or slug.replace('-', ' ').title(),
            'badge': badge, 'rating': rating, 'reviews_count': reviews,
            'tours_count': tours_count, 'hq': hq, 'response_rate': rr,
            'response_time': rt, 'age': age, 'about': about, 'logo': logo}


# -------------------------------------------------------------------- build --

def main():
    cards = json.loads((SCRAPE / 'serp_cards.json').read_text())
    cards_by_id = {c['tour_id']: c for c in cards}
    tour_dests = json.loads((SCRAPE / 'tour_dests.json').read_text())
    progress = [json.loads(l) for l in
                (SCRAPE / 'tour_progress.jsonl').read_text().splitlines() if l.strip()]
    # merge batch1 goods already folded into progress at scrape time
    api_dir = SCRAPE / 'api'
    api = {}
    if api_dir.exists():
        for f in api_dir.glob('*.json'):
            api[int(f.stem)] = json.loads(f.read_text())

    # ---- operators ----
    operators = {}
    op_id = 1
    pages_dir = SCRAPE / 'pages'
    for f in sorted(pages_dir.glob('o-*.json')):
        page = json.loads(f.read_text())
        rec = parse_operator_page(page, op_id)
        operators[rec['slug']] = rec
        op_id += 1

    def op_for(name):
        slug = slugify(name or '')
        if slug in operators:
            return operators[slug]
        # create from tour op panel data later
        return None

    # collect operator info from tour op panels for operators with no page
    op_panel_cache = {}

    tours = []
    for rec in sorted(progress, key=lambda r: r['tour_id']):
        if not rec.get('title') or rec['title'] in ('403 Forbidden',):
            continue
        tid = rec['tour_id']
        card = cards_by_id.get(tid, {})
        a = api.get(tid, {})
        comp = a.get('comparison') or {}
        itin = a.get('itineraries') or {}
        days = parse_days(rec.get('days_raw'))
        # join API day descriptions. The live endpoint returns
        # {<day-key>: <description str>, 'cityNames': {<day-key>: [cities]}};
        # older captures used {'descriptions': {<day-key>: <str>}} — support both.
        day_keys = sorted([k for k in itin if k.isdigit()
                           and isinstance(itin[k], str)], key=int)
        descs = itin.get('descriptions') or {k: itin[k] for k in day_keys}
        city_names = itin.get('cityNames') or {}
        if descs:
            keys = sorted(descs.keys(), key=int)
            # Join by the day block's data-id when the scrape captured it:
            # the itineraries-descriptions API keys are day-block ids whose
            # numeric order does NOT always match the DOM day order (e.g.
            # 69539 Day 5 -> id 12603 sorts last), so an index join silently
            # scrambles descriptions and cities. Fall back to positional
            # alignment only for older captures without ids.
            for d in days:
                did = d.get('data_id')
                if did and did in descs:
                    d['description'] = descs[did]
                    if did in city_names:
                        d['cities'] = city_names[did]
                else:
                    idx = d['day'] - 1
                    if 0 <= idx < len(keys):
                        d['description'] = descs[keys[idx]]
                        if keys[idx] in city_names:
                            d['cities'] = city_names[keys[idx]]
        for d in days:
            d.pop('data_id', None)
        subratings, reviews = parse_reviews(rec.get('reviews_raw'))
        departures = parse_departures(rec.get('departures_raw'))
        gtk = parse_gtk(rec.get('goodtoknow_raw'))
        qa = parse_qa(rec.get('qa_raw'))
        images = pick_images(rec)
        # operator
        op_name = rec.get('operator') or card.get('operator')
        op_slug = slugify(op_name or '')
        if op_slug and op_slug not in operators:
            # build minimal operator from the tour's op panel
            panel = rec.get('op_panel_raw') or ''
            rating = None
            reviews_n = None
            rm = re.search(r'Rating\n(\d\.\d)\n\(([\d,]+) reviews\)', panel)
            if rm:
                rating = float(rm.group(1))
                reviews_n = int(rm.group(2).replace(',', ''))
            rtm = re.search(r'Response time\n([^\n]+)', panel)
            rrm = re.search(r'Response rate\n(\d+%)', panel)
            hqm = re.search(r'\n([A-Z][^\n]+)\n\n(?:Platinum|Gold|Silver|Verified) Operator', panel)
            logo = None
            for img in rec.get('images') or []:
                if '/s3/op/' in (img.get('src') or ''):
                    logo = map_image(f"operators/{img['src'].split('/')[-1]}", img["src"])
                    break
            operators[op_slug] = {
                'id': None, 'slug': op_slug, 'name': op_name,
                'badge': (rec.get('operator_badge') or '').replace(' Operator', '').lower() or None,
                'rating': rating, 'reviews_count': reviews_n,
                'tours_count': None, 'hq': None,
                'response_rate': rrm.group(1) if rrm else None,
                'response_time': rtm.group(1) if rtm else None,
                'age': None, 'about': None, 'logo': logo}
        # attributes
        attributes = rec.get('attributes') or []
        group_type = None
        guide_type = None
        physical = None
        for at in attributes:
            if at['name'] in ('Group Tour', 'Independent Tour', 'Private Tour'):
                group_type = at['name']
            elif at['name'] in ('Fully Guided', 'Partially Guided', 'Self-Guided'):
                guide_type = at['name']
            elif at['name'].endswith('Intensity'):
                physical = at['name']
        if comp:
            gt = comp.get('group_type') or []
            if gt and not group_type:
                group_type = gt[0]['name'] + (' Tour' if gt[0]['name'] != 'Group' else ' Tour')
            gtp = comp.get('guide_type') or []
            if gtp and not guide_type:
                guide_type = gtp[0]['name']
        # start/end cities
        start_city = comp.get('start_city', {}).get('name') if comp.get('start_city') else None
        end_city = comp.get('end_city', {}).get('name') if comp.get('end_city') else None
        se = rec.get('start_end')
        if se and not start_city:
            m = re.match(r'Start and end in (.+)', se or '')
            if m:
                start_city = end_city = m.group(1).strip()
            else:
                start_city = end_city = se.strip()
        # countries from comparison destinations
        countries = []
        cities = []
        if comp.get('destinations'):
            for c in comp['destinations'].get('cities', []):
                if c.get('name') and c['name'] not in cities:
                    cities.append(c['name'])
            for c in comp['destinations'].get('countries', []):
                if c.get('name') and c['name'] not in countries:
                    countries.append(c['name'])
        if not cities:
            dest_text = (card.get('destinations') or '').replace('\n', ',')
            cities = [x.strip() for x in dest_text.split(',') if x.strip() and len(x.strip()) < 40]
        cities = cities[:8]
        if not countries:
            pass  # filled in the post-pass below (dest_records not built yet)
        # review avatars + photos pairing
        avatar_pool = images['avatars']
        photo_pool = images['review_photos']
        for i, rev in enumerate(reviews):
            if i < len(avatar_pool):
                rev['avatar'] = avatar_pool[i][0]
            if i < len(photo_pool):
                rev['photos'] = [photo_pool[i][0]]
        moments = []
        for img, alt in images['moments']:
            author = None
            for av, av_alt in avatar_pool:
                if av_alt and av_alt.lower() in alt.lower():
                    author = av_alt
                    break
            moments.append({'image': img, 'author': author or 'Traveler',
                            'caption': alt[:160]})
        hero = images['hero']
        if not hero:
            card_img = card.get('image') or ''
            if '/s3/tour/' in card_img:
                hero = map_image(f"tours/{tid}_card{pathlib.Path(card_img.split('/')[-1]).suffix}", card_img)
        tour = {
            'id': tid,
            'name': rec.get('title') or card.get('name'),
            'operator': op_name,
            'duration_days': (rec.get('duration_days')
                              or int(re.match(r'(\d+)', card.get('duration') or '1').group(1))
                              or len(days) or 1),
            'start_city': start_city, 'end_city': end_city,
            'start_end_note': rec.get('start_end'),
            'rating': rec.get('rating') or card.get('rating'),
            'review_count': rec.get('review_count') or card.get('review_count'),
            'subratings': subratings,
            # price fallback chain: page parse -> SERP card -> comparison API
            # (a few upstream tours show no From-price on the page or card;
            # the comparison payload still carries the real base price)
            'price_from': (rec.get('price_from') or card.get('price_from')
                           or ((comp.get('tour') or {}).get('price_from') or {}).get('price_base')),
            'price_current': (rec.get('price_current') or card.get('price_current')
                              or ((comp.get('tour') or {}).get('price_from') or {}).get('price_total')),
            'discount_pct': card.get('discount_pct'),
            'price_basis': card.get('price_basis')
                           or ((comp.get('tour') or {}).get('price_from') or {}).get('based_on'),
            'style': card.get('style'),
            'attributes': attributes,
            'group_min': rec.get('group_min') or (comp.get('max_group_size') and 1),
            'group_max': rec.get('group_max') or comp.get('max_group_size'),
            'min_age': rec.get('min_age') or (comp.get('age_range', {}) or {}).get('strict', {}).get('min_age') or _page_min_age(rec),
            'max_age': (comp.get('age_range', {}) or {}).get('strict', {}).get('max_age'),
            'guided_language': rec.get('guided_language'),
            'group_type': group_type, 'guide_type': guide_type,
            'physical': physical,
            'instant_confirm': (comp.get('price_from', {}).get('is_instant_confirmable')
                                if comp.get('price_from') else
                                (any(d.get('instant') for d in departures) or None)),
            'intro': itin.get('introduction'),
            'summary': card.get('card_quote'),
            'summary_author': card.get('card_quote_author'),
            'cities': cities, 'countries': countries,
            'dest_slugs': tour_dests.get(str(tid), []),
            'days': days,
            'included': {}, 'not_included': {},
            'good_to_know': gtk,
            'videos': [],
            'similar': [int(x.split('/')[-1]) for x in (rec.get('tour_links') or [])
                        if x.startswith('/t/')],
            'hero': hero,
            'gallery': images['gallery'],
            'best_months': a.get('best_months') or {},
            'departures': departures,
            'reviews': reviews,
            'qa': qa,
            'moments': moments,
        }
        tours.append(tour)

    # finalize operators: assign ids deterministically
    ops_sorted = sorted(operators.values(), key=lambda o: o['slug'])
    for i, o in enumerate(ops_sorted, start=1):
        o['id'] = i

    # ---- destinations ----
    destinations = []
    did = 1
    dest_records = {}
    for f in sorted(pages_dir.glob('d-*.json')):
        page = json.loads(f.read_text())
        rec = parse_dest_page(page)
        slug = rec['slug']
        group = None
        for g, slugs in DEST_GROUPS.items():
            if slug in slugs:
                group = g
                break
        rec.update({'id': did, 'kind': 'd', 'group': group, 'parent': None})
        dest_records[slug] = rec
        did += 1
    for slug, name in REGION_NAMES.items():
        dest_records[slug] = {'id': did, 'slug': slug, 'name': name,
                              'kind': 'b', 'group': None, 'parent': None,
                              'hero': None, 'description': None,
                              'sections': {}}
        did += 1
    for slug, name in PLACE_NAMES.items():
        dest_records[slug] = {'id': did, 'slug': slug, 'name': name,
                              'kind': 'v', 'group': None, 'parent': None,
                              'hero': None, 'description': None,
                              'sections': {}}
        did += 1
    for slug, name in STYLE_NAMES.items():
        page_path = pages_dir / f"f-{slug}.json"
        desc = None
        if page_path.exists():
            page = json.loads(page_path.read_text())
            dm = re.search(r'\n\n([\s\S]{80,900}?)\n\nAdventure Style', page['text'])
            if dm:
                desc = dm.group(1).strip()
        dest_records[slug] = {'id': did, 'slug': slug, 'name': name,
                              'kind': 'f', 'group': None, 'parent': None,
                              'hero': None, 'description': desc,
                              'sections': {}}
        did += 1
    # collections + audience + deals
    dest_records['africa-safari'] = {'id': did, 'slug': 'africa-safari',
                                     'name': 'Africa Safari', 'kind': 'i',
                                     'group': None, 'parent': None,
                                     'hero': None, 'description': None,
                                     'sections': {}}
    did += 1
    dest_records['solo'] = {'id': did, 'slug': 'solo',
                            'name': 'Group Tours & Trips for Solo Travelers',
                            'kind': 's', 'group': None, 'parent': None,
                            'hero': None,
                            'description': 'Book on your own, travel with a group. Solo group tours take care of the guides, logistics, and company - so you\u2019re never alone unless you want to be.',
                            'sections': {}}
    did += 1
    for slug in ['europe', 'asia', 'africa', 'latin-america', 'north-america',
                 'australia-oceania']:
        name = {'europe': 'Europe', 'asia': 'Asia', 'africa': 'Africa',
                'latin-america': 'Latin America', 'north-america': 'North America',
                'australia-oceania': 'Australia/Oceania'}[slug]
        dest_records[f'deal-{slug}'] = {'id': did, 'slug': slug,
                                        'name': f'{name} Tour Deals',
                                        'kind': 'deal', 'group': None,
                                        'parent': None, 'hero': None,
                                        'description': f'Up to 55% off {name} tours - early bird and last minute specials.',
                                        'sections': {}}
        did += 1
    dest_records['deal-escape-sale'] = {'id': did, 'slug': 'escape-sale',
                                        'name': 'Escape Sale', 'kind': 'deal',
                                        'group': None, 'parent': None,
                                        'hero': None,
                                        'description': 'Up to 70% off organized adventures across 6 continents.',
                                        'sections': {}}
    did += 1
    destinations = [dest_records[k] for k in sorted(dest_records)]

    # post-pass: countries from dest_slugs (dest_records now built)
    for tour in tours:
        _assign_collection_slugs(tour)
        if not tour.get('countries'):
            tour['countries'] = []
            for slug in tour.get('dest_slugs', []):
                dr = dest_records.get(slug)
                if dr and dr['kind'] == 'd' and dr['name'] not in tour['countries']:
                    tour['countries'].append(dr['name'])

    # ---- content ----
    content = {'moments': [], 'platform_reviews': [], 'promo_codes': [
        {'code': 'ESCAPE10', 'kind': 'pct', 'value': 10, 'min_total': 500,
         'label': 'Escape Sale: 10% off selected departures'},
        {'code': 'TRAVEL50', 'kind': 'amount', 'value': 50, 'min_total': 1000,
         'label': '$50 off adventures over $1,000'},
    ]}
    # moments from the homepage capture
    home_imgs = SCRAPE / 'home_page_imgs.json'
    if home_imgs.exists():
        rows = json.loads(home_imgs.read_text())
        for img in rows:
            src = img.get('src') or ''
            alt = img.get('alt') or ''
            if '/moments/' in src:
                fn = src.split('/')[-2] + '_' + src.split('/')[-1]
                content['moments'].append({
                    'image': map_image(f"moments/{fn}", src), 'author': None,
                    'tour_name': alt[:120],
                    'caption': alt[:160]})
    # platform reviews from the reviews-of-tourradar page
    rev_page = pages_dir / 'reviews-of-tourradar.json'
    if rev_page.exists():
        page = json.loads(rev_page.read_text())
        text = page['text']
        # parse "Excellent\n<name>\n<date>\n<body>"
        blocks = re.findall(r'\n([A-Z][a-zA-Z .-]{2,40})\n(?:Reviewed on |)([A-Z][a-z]+ \d{1,2}(?:st|nd|rd|th)?, \d{4})\n([\s\S]{30,600}?)(?=\n[A-Z][a-zA-Z .-]{2,40}\n|$)',
                            text)
        for name, dt, body in blocks[:20]:
            content['platform_reviews'].append({
                'author': name, 'initials': ''.join(w[0] for w in name.split()[:2]).upper(),
                'rating': 4.6, 'date': dt,
                'body': re.sub(r'\s+', ' ', body).strip()[:400],
                'source': 'Trustpilot', 'tour_name': None})

    # apply extension fixes discovered by the downloader and drop failed assets
    fixes_path = SCRAPE / 'image_ext_fixes.json'
    fails_path = SCRAPE / 'image_failures.json'
    if fixes_path.exists():
        fixes = json.loads(fixes_path.read_text())
        if fixes:
            def _fix_obj(obj):
                if isinstance(obj, str):
                    return fixes.get(obj, obj)
                if isinstance(obj, list):
                    return [_fix_obj(x) for x in obj]
                if isinstance(obj, dict):
                    return {k: _fix_obj(v) for k, v in obj.items()}
                return obj
            for tour in tours:
                for key in ('hero', 'gallery'):
                    if key == 'gallery' and isinstance(tour.get(key), list):
                        tour[key] = [fixes.get(p, p) for p in tour[key]]
                    elif isinstance(tour.get(key), str):
                        tour[key] = fixes.get(tour[key], tour[key])
                for rev in tour.get('reviews', []):
                    if rev.get('avatar'):
                        rev['avatar'] = fixes.get(rev['avatar'], rev['avatar'])
                    if rev.get('photos'):
                        rev['photos'] = [fixes.get(p, p) for p in rev['photos']]
                for mom in tour.get('moments', []):
                    mom['image'] = fixes.get(mom['image'], mom['image'])
            for o in ops_sorted:
                if o.get('logo'):
                    o['logo'] = fixes.get(o['logo'], o['logo'])
            for d in destinations:
                if d.get('hero'):
                    d['hero'] = fixes.get(d['hero'], d['hero'])
            for m in content['moments']:
                m['image'] = fixes.get(m['image'], m['image'])
            for k in list(URL_MAP):
                if k in fixes:
                    URL_MAP[fixes[k]] = URL_MAP.pop(k)
    if fails_path.exists():
        failed = set(json.loads(fails_path.read_text()))
        if failed:
            for tour in tours:
                for rev in tour.get('reviews', []):
                    if rev.get('photos'):
                        rev['photos'] = [p for p in rev['photos'] if p not in failed]
                for mom in tour.get('moments', []):
                    if mom['image'] in failed:
                        mom['image'] = None
            for k in list(URL_MAP):
                if k in failed:
                    del URL_MAP[k]

    # disk-existence sweep: drop every managed-image reference whose file is
    # absent on disk (upstream 403s never materialize, extension fixes can
    # rename a file out from under a stale ref). Keeps the seed from pointing
    # at dead paths regardless of what the failure log recorded. When a missing
    # path has exactly one on-disk twin under a different image extension
    # (the CDN serves the same bytes under .jpeg and .jpg names), the ref is
    # healed onto that twin instead of being dropped.
    img_root = ROOT / 'static' / 'images'
    img_exts = ('.jpg', '.jpeg', '.png', '.webp', '.gif')
    healed_map = {}

    def _heal(rel):
        """Return an on-disk path for rel: itself, a unique extension twin,
        or None when nothing on disk matches."""
        if rel is None:
            return None
        if (img_root / rel).is_file():
            return rel
        stem = rel.rsplit('.', 1)[0]
        twins = [stem + e for e in img_exts
                 if e != rel[rel.rfind('.'):] and (img_root / (stem + e)).is_file()]
        if len(twins) == 1:
            healed_map[rel] = twins[0]
            return twins[0]
        return None

    def _keep(rel):
        return rel if _on_disk(rel) else None

    def _on_disk(rel):
        return rel is None or (img_root / rel).is_file()

    swept = 0
    healed = 0

    def _fix_ref(obj, key, list_key=None):
        nonlocal swept, healed
        val = obj.get(key)
        if list_key:
            if not val:
                return
            keep = [p if (img_root / p).is_file() else _heal(p) for p in val]
            for orig, new in zip(val, keep):
                if new is None:
                    swept += 1
                elif new != orig:
                    healed += 1
            obj[key] = [p for p in keep if p]
        else:
            if not val:
                return
            if (img_root / val).is_file():
                return
            new = _heal(val)
            if new is None:
                obj[key] = None
                swept += 1
            else:
                obj[key] = new
                healed += 1

    for tour in tours:
        _fix_ref(tour, 'hero')
        _fix_ref(tour, 'gallery', list_key=True)
        for rev in tour.get('reviews', []):
            _fix_ref(rev, 'avatar')
            _fix_ref(rev, 'photos', list_key=True)
        for mom in tour.get('moments', []):
            _fix_ref(mom, 'image')
    for o in ops_sorted:
        _fix_ref(o, 'logo')
    for d in destinations:
        _fix_ref(d, 'hero')
    for m in content['moments']:
        _fix_ref(m, 'image')
    for orig, new in healed_map.items():
        if orig in URL_MAP:
            URL_MAP[new] = URL_MAP.pop(orig)

    # write outputs in fixed order
    (ROOT / 'source_data_tours.json').write_text(
        json.dumps(tours, indent=1, ensure_ascii=False, sort_keys=False))
    (ROOT / 'source_data_catalog.json').write_text(
        json.dumps({'operators': ops_sorted,
                    'destinations': destinations}, indent=1,
                   ensure_ascii=False))
    (ROOT / 'source_data_content.json').write_text(
        json.dumps(content, indent=1, ensure_ascii=False))
    (SCRAPE / "image_urls.json").write_text(json.dumps(URL_MAP, indent=1, sort_keys=True))
    print(f"tours={len(tours)} operators={len(ops_sorted)} "
          f"destinations={len(destinations)} moments={len(content['moments'])} "
          f"platform_reviews={len(content['platform_reviews'])} "
          f"swept_refs={swept} healed_refs={healed}")


if __name__ == '__main__':
    main()
