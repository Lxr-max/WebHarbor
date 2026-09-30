#!/usr/bin/env python3
"""Build the tracked source_data/ snapshots from the gitignored scraped_data/
captures (ziprecruiter.com pages captured 2026-09-29 with a headful Chromium
that passed the upstream Cloudflare interstitial).

Every tracked snapshot is a deterministic trim of the real upstream capture;
the trim policy is declared in provenance.json. Re-run: nothing here talks to
the network. The upstream Next.js pages embed their data as RSC flight JSON
(escaped inside <script> strings); the extractor below parses those payloads
plus the LD+JSON blocks — no synthesis, every field traces to a capture file.

Run:  python3 scripts_dev/build_source_data.py
"""
import html as H
import json
import os
import re
import sys
from collections import OrderedDict

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.dirname(HERE)
SCRAPE = os.path.join(SITE, "scraped_data", "captures")
OUT = os.path.join(SITE, "source_data")

EMP_MAP = {
    'EMPLOYMENT_TYPE_NAME_FULL_TIME': 'full_time',
    'EMPLOYMENT_TYPE_NAME_PART_TIME': 'part_time',
    'EMPLOYMENT_TYPE_NAME_CONTRACTOR': 'contract',
    'EMPLOYMENT_TYPE_NAME_TEMPORARY': 'temporary',
    'EMPLOYMENT_TYPE_NAME_PER_DIEM': 'per_diem',
    'EMPLOYMENT_TYPE_NAME_OTHER': 'other',
    'EMPLOYMENT_TYPE_NAME_SEASONAL': 'other',
    'EMPLOYMENT_TYPE_NAME_INTERNSHIP': 'other',
}
LOC_MAP = {
    'LOCATION_TYPE_NAME_REMOTE': 'remote',
    'LOCATION_TYPE_NAME_HYBRID': 'hybrid',
    'LOCATION_TYPE_NAME_IN_PERSON': 'onsite',
    'LOCATION_TYPE_NAME_ONSITE': 'onsite',
}
BENEFIT_MAP = {
    'BENEFIT_TYPE_NAME_MEDICAL': 'Medical',
    'BENEFIT_TYPE_NAME_DENTAL': 'Dental',
    'BENEFIT_TYPE_NAME_VISION': 'Vision',
    'BENEFIT_TYPE_NAME_PAID_TIME_OFF': 'PTO',
    'BENEFIT_TYPE_NAME_401K': '401(k)',
    'BENEFIT_TYPE_NAME_SIGN_ON_BONUS': 'Sign-On Bonus',
    'BENEFIT_TYPE_NAME_RELOCATION': 'Relocation',
    'BENEFIT_TYPE_NAME_WORK_FROM_HOME': 'Work From Home',
    'BENEFIT_TYPE_NAME_FLEXIBLE_SCHEDULE': 'Flexible Schedule',
    'BENEFIT_TYPE_NAME_PET_INSURANCE': 'Pet Insurance',
    'BENEFIT_TYPE_NAME_GYM_MEMBERSHIP': 'Gym Membership',
    'BENEFIT_TYPE_NAME_COMMUTER_BENEFITS': 'Commuter Benefits',
    'BENEFIT_TYPE_NAME_TUITION_ASSISTANCE': 'Tuition Reimbursement',
    'BENEFIT_TYPE_NAME_PROF_DEVELOPMENT': 'Professional Development',
    'BENEFIT_TYPE_NAME_COLLEGE_SAVINGS': 'College Savings Plan',
}

SENIOR_PAT = re.compile(
    r'\b(senior|sr\.?|lead|principal|staff|director|head of|chief|vp\b|'
    r'executive|manager iv|iv\b|v\b|vi\b)\b', re.I)
JUNIOR_PAT = re.compile(
    r'\b(junior|jr\.?|entry[- ]level|associate|trainee|apprentice|'
    r'graduate|intern\b|assistant|coordinator i\b|i\b)\b', re.I)
NOEXP_PAT = re.compile(
    r'no (prior |previous )?experience|entry[- ]level|'
    r'will train|training provided|no degree', re.I)


def load(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def dump(name, data):
    path = os.path.join(OUT, name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1, sort_keys=False)
        f.write("\n")
    print(f"wrote {name} ({os.path.getsize(path)} bytes)")


# ------------------------------------------------------------ RSC utilities --

def extract_balanced(h, start_idx):
    """Extract the balanced {...} JSON fragment starting at start_idx ('{'),
    honoring backslash escapes inside the escaped-RSC stream."""
    depth = 0
    j = start_idx
    while j < len(h):
        c = h[j]
        if c == '\\':
            j += 2
            continue
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                return h[start_idx:j + 1]
        j += 1
    return None


def parse_escaped_json(frag):
    """Unescape a doubled-escaped RSC JSON fragment and parse it."""
    try:
        s = frag.replace('\\"', '"').replace('\\u003c', '<') \
               .replace('\\u003e', '>').replace('\\u0026', '&')
        # fix remaining lone escapes that break json.loads
        s = re.sub(r'\\(?!["\\/bfnrtu])', r'\\\\', s)
        return json.loads(s)
    except Exception:
        return None


def find_job_records(h):
    """All job records found on a page: jobKeysMap entries (SERP/salary/
    company/title pages) plus the single job payload of detail pages."""
    records = []
    for m in re.finditer(r'jobKeysMap\\":\{', h):
        frag = extract_balanced(h, m.end() - 1)
        if not frag:
            continue
        data = parse_escaped_json(frag)
        if isinstance(data, dict):
            for rec in data.values():
                if isinstance(rec, dict) and 'company' in rec:
                    records.append(rec)
    return records


def capture_files():
    files = []
    for fn in sorted(os.listdir(SCRAPE)):
        if fn.endswith('.html') and os.path.exists(
                os.path.join(SCRAPE, fn[:-5] + '.meta.json')):
            with open(os.path.join(SCRAPE, fn[:-5] + '.meta.json')) as f:
                meta = json.load(f)
            if meta.get('ok'):
                files.append((fn, meta))
    # SERP captures are authoritative for a job's card-level fields (they
    # are what the upstream search page rendered); job detail pages then
    # fill descriptions; company pages come last.
    def prio(item):
        fn = item[0]
        if fn.startswith('search_'):
            return (0, fn)
        if fn.startswith('s_'):
            return (1, fn)
        if fn.startswith('jd_'):
            return (2, fn)
        if fn.startswith('jobs_title') or fn.startswith('salary_'):
            return (3, fn)
        if fn.startswith('co_'):
            return (4, fn)
        return (5, fn)
    return [f for f in sorted(files, key=prio)]


def ldjson_nodes(h):
    """Every LD+JSON node, flattened through @graph wrappers."""
    out = []
    for m in re.finditer(r'<script type="application/ld\+json"[^>]*>(.*?)</script>',
                         h, re.S):
        try:
            data = json.loads(m.group(1))
        except Exception:
            continue
        if isinstance(data, dict) and '@graph' in data:
            out.extend(data['@graph'])
        elif isinstance(data, dict):
            out.append(data)
    return out


# ------------------------------------------------------------- job assembly --

def slugify_title(t):
    s = re.sub(r'[^A-Za-z0-9. &/+%-]+', ' ', t)
    s = re.sub(r'\s+', ' ', s).strip()
    return s.replace(' ', '-')


def job_from_record(rec, source_file):
    """Normalize one RSC job record into the tracked job shape."""
    disp = rec.get('display') or {}
    pay = rec.get('pay') or {}
    loc = rec.get('location') or {}
    co = rec.get('company') or {}
    logo = (rec.get('companyLogo') or {}).get('logoUrl') or \
        rec.get('companyLogoUrl')
    url = rec.get('rawCanonicalZipJobPageUrl') or ''
    mj = re.search(r'/c/(.+)/Job/(.+)/-in-([^?]+)\?jid=(\w+)$', url)
    if not mj:
        return None
    co_slug, title_slug, loc_slug, jid = mj.groups()
    title = rec.get('title') or title_slug.replace('-', ' ')
    emp_types = [EMP_MAP.get(b.get('name'), 'other')
                 for b in rec.get('employmentTypes') or []]
    loc_types = [LOC_MAP.get(t.get('name'), 'onsite')
                 for t in rec.get('locationTypes') or []]
    remote = 'remote' if 'remote' in loc_types else (
        'hybrid' if 'hybrid' in loc_types else 'onsite')
    benefits = [BENEFIT_MAP.get(b.get('name'))
                for b in rec.get('benefits') or []]
    benefits = [b for b in benefits if b]
    posted_text = (disp.get('rollingPostedAt') or '').replace('Posted ', '') \
        or None
    status = rec.get('status') or {}
    apply_cfg = rec.get('applyButtonConfig') or {}
    quick_apply = apply_cfg.get('applyButtonType') == 'OPEN_APPLY_FLOW'
    salary_text = ((disp.get('pay') or {}).get('text') or '').replace('$$', '$')
    return {
        'jid': jid,
        'title': title,
        'title_slug': title_slug,
        'company': co.get('name') or co_slug.replace('-', ' '),
        'company_slug': co_slug,
        'city': loc.get('city'),
        'state': loc.get('stateCode'),
        'postal_code': loc.get('postalCode'),
        'employment_types': emp_types or ['full_time'],
        'remote': remote,
        'salary_min': pay.get('minAnnual'),
        'salary_max': pay.get('maxAnnual'),
        'salary_interval': pay.get('interval'),
        'salary_text': salary_text or None,
        'benefits': benefits,
        'posted_text': posted_text,
        'posted_at_utc': status.get('rollingPostedAtUtc') or
        status.get('postedAtUtc'),
        'quick_apply': quick_apply,
        'is_new': bool(rec.get('isNew')) or
        disp.get('newLabel') == 'NEW_LABEL_POSTED_TODAY',
        'short_description': rec.get('shortDescription'),
        'logo_url': logo,
        'source_file': source_file,
    }


def posted_days(job):
    """Deterministic posted-age in days derived from the captured
    rollingPostedAt / rollingPostedAtUtc text."""
    txt = (job.get('posted_at_utc') or '')[:10]
    if txt and re.match(r'\d{4}-\d{2}-\d{2}', txt):
        from datetime import date
        d = date(*[int(x) for x in txt.split('-')])
        return max(0, (date(2026, 9, 29) - d).days)
    pt = (job.get('posted_text') or '').lower()
    m = re.match(r'(\d+)\s*(day|hour|minute|minute)s?\s*ago', pt)
    if m:
        n, unit = int(m.group(1)), m.group(2)
        if unit == 'day':
            return n
        if unit == 'hour':
            return 1 if n >= 24 else 0
        return 0
    if 'today' in pt or 'new' in pt:
        return 0
    return 0


def derive_experience(title, description):
    """Deterministic experience level derived from the captured title and
    description text (upstream computes its filter server-side; the
    per-job value is not in the captured payloads)."""
    t = title or ''
    d = (description or '')[:3000]
    if NOEXP_PAT.search(t) or NOEXP_PAT.search(d):
        return 'none'
    if SENIOR_PAT.search(t):
        return 'senior'
    if JUNIOR_PAT.search(t):
        return 'junior'
    return 'mid'


def extract_entry_content(h):
    """Balanced-div extraction of the WordPress entry-content body."""
    m = re.search(r'<div class="entry-content">', h)
    if not m:
        return None
    i = m.end()
    depth = 1
    j = i
    while j < len(h) and depth > 0:
        if h.startswith('<div', j):
            depth += 1
            j += 4
        elif h.startswith('</div>', j):
            depth -= 1
            j += 6
        else:
            j += 1
    return h[i:j - 6].strip()


def parse_salary_page(h, meta):
    """Extract one salary page: percentiles, histogram, FAQ tables."""
    out = {}
    for node in ldjson_nodes(h):
        if node.get('@type') == 'Occupation':
            est = (node.get('estimatedSalary') or [{}])[0]
            out['name'] = node.get('name')
            out['p10'] = est.get('percentile10')
            out['p25'] = est.get('percentile25')
            out['median'] = est.get('median')
            out['p75'] = est.get('percentile75')
            out['p90'] = est.get('percentile90')
        elif node.get('@type') == 'FAQPage':
            out['faq'] = [
                {'question': q.get('name'),
                 'answer': (q.get('acceptedAnswer') or {}).get('text')}
                for q in node.get('mainEntity') or []]
    # histogram bins from the rendered salary-interval section
    txt = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '|', h))
    bins = []
    for m in re.finditer(r'\$([\d.]+)K - \$([\d.]+)K\|\|(\d+)% of jobs', txt):
        lo = int(round(float(m.group(1)) * 1000))
        hi = int(round(float(m.group(2)) * 1000))
        bins.append([lo, hi, int(m.group(3))])
    out['histogram'] = bins
    # average year/hour from the rendered figures
    m = re.search(r'\$(\d[\d,]+)\|\|?/?year', txt)
    out['avg_year'] = int(m.group(1).replace(',', '')) if m else None
    m = re.search(r'\$(\d+(?:\.\d+)?)\|\|?/?hour', txt)
    out['avg_hour'] = m.group(1) if m else None
    # 25th/75th marker text
    for key, pat in [('p25_text', r'\$([\d.]+)K is the 25th percentile'),
                     ('p75_text', r'\$([\d.]+)K is the 75th percentile'),
                     ('median_text', r'median wage is \$([\d.]+)K')]:
        mm = re.search(pat, txt)
        out[key] = mm.group(1) if mm else None
    # comparison by location: first rows after the heading
    i = txt.find('Salary Comparison by Location')
    if i > 0:
        seg = txt[i:i + 4000]
        comp = re.findall(
            r'\|([A-Za-z][A-Za-z .]{2,28})\|\|([A-Za-z][A-Za-z ]{2,20})\|\|\$([\d,]+)', seg)
        out['comparison'] = [[c[0].strip(), c[1].strip(),
                               int(c[2].replace(',', ''))] for c in comp[:3]]
    # FAQ HTML tables -> top cities + related jobs
    for fq in out.get('faq', []):
        a = fq['answer'] or ''
        rows = re.findall(r'<tr><td>(.*?)</td><td>\$(.*?)</td>', a)
        if 'top 10 cities' in (fq['question'] or '').lower():
            out['top_cities'] = []
            for c, v in rows[:10]:
                name = H.unescape(c).strip()
                city, state = name, ''
                if ',' in name:
                    city, state = [p.strip() for p in name.rsplit(',', 1)]
                out['top_cities'].append(
                    [city, state, int(v.replace(',', ''))])
        if 'related' in (fq['question'] or '').lower():
            out['related'] = [
                [H.unescape(c).strip(), int(v.replace(',', ''))]
                for c, v in rows[:5]]
    # nearby jobs (ItemList URLs)
    for node in ldjson_nodes(h):
        if node.get('@type') == 'ItemList':
            out['nearby'] = [it.get('url') for it in
                             node.get('itemListElement') or []][:6]
    return out


def strip_tags(h):
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '|', h))


def parse_company_block(h, company_name):
    """Parse the About-<company> blocks of a job detail page."""
    out = {}
    txt = H.unescape(strip_tags(h))
    i = txt.find(f'About {company_name}, in their own words')
    if i > 0:
        seg = txt[i: i + 2500]
        j = seg.find('From ')
        m = re.search(r'\|From [^|]+\|(.+?)\|Company values\|', seg)
        if m:
            out['about'] = m.group(1).strip().strip('|').strip()
    j = txt.find(f'About {company_name}')
    j = txt.find('Sourced by ZipRecruiter', j if j > 0 else 0)
    if j > 0:
        seg = txt[j: j + 3000]
        m = re.search(r'\|Sourced by ZipRecruiter\|+([^|][^|]*?)\|\|Industry', seg)
        if m:
            out['sourced_about'] = m.group(1).strip()
        facts = dict(re.findall(
            r'\|\|(Industry|Company size|Headquarters location|Year founded|Website)\|+([^|]+)',
            seg))
        out['industry'] = facts.get('Industry', '').strip() or None
        out['size'] = facts.get('Company size', '').strip() or None
        hq = facts.get('Headquarters location', '').strip() or None
        if hq:
            m2 = re.search(r'^([A-Za-z .]+?),\s*([A-Z]{2})(?:,\s*US)?$', hq)
            if m2:
                out['hq_city'] = m2.group(1).strip()
                out['hq_state'] = m2.group(2)
            else:
                out['hq_city'] = hq
        out['founded'] = facts.get('Year founded', '').strip() or None
        out['website'] = facts.get('Website', '').strip() or None
    # Breakroom rating + findings (structured payload)
    m = re.search(r'\\"breakroomCompany\\":\{', h)
    if m:
        frag = extract_balanced(h, m.end() - 1)
        br = parse_escaped_json(frag) if frag else None
        if br:
            out['breakroom'] = {
                'rating': br.get('rating'),
                'response_count': br.get('latestResponseCount'),
                'highlights': [x.get('label') for x in
                               (br.get('sortedHighlights') or [])
                               if x.get('label')][:6],
                'findings': [
                    {'short': x.get('shortText'),
                     'detail': x.get('secondaryText'),
                     'area': x.get('area'),
                     'opinion': x.get('opinion')}
                    for x in (br.get('sortedFindings') or [])][:10],
                'about': br.get('description'),
                'website': br.get('url'),
            }
    return out


def main():
    files = capture_files()
    print(f"parsing {len(files)} captured pages")

    jobs = OrderedDict()      # jid -> job dict
    companies = OrderedDict()  # slug -> company dict
    serp_totals = []          # captured SERP context rows
    salary_pages = []
    articles = []
    faqs = OrderedDict()
    titles = OrderedDict()

    for fn, meta in files:
        h = load(os.path.join(SCRAPE, fn))
        key = fn[:-5]

        # --- every job record the page carries --------------------------
        for rec in find_job_records(h):
            j = job_from_record(rec, fn)
            if j and j['jid'] not in jobs:
                j['posted_days'] = posted_days(j)
                jobs[j['jid']] = j

        # --- job detail pages: full description + company widget -------
        if key.startswith('jd_'):
            detail_jid = None
            for data in ldjson_nodes(h):
                if data.get('@type') == 'JobPosting':
                    mj = re.search(r'jid=(\w+)', data.get('url', ''))
                    if not mj:
                        continue
                    detail_jid = mj.group(1)
                    um = re.match(r'https://www\.ziprecruiter\.com/c/(.+)/Job/(.+)/'
                                  r'-in-([^?]+)\?jid=(\w+)',
                                  data.get('url', ''))
                    j = jobs.get(detail_jid) or {'jid': detail_jid,
                                                  'source_file': fn}
                    if um:
                        j.setdefault('company_slug', um.group(1))
                        j.setdefault('title_slug', um.group(2))
                        j.setdefault('city', um.group(3).rsplit(',', 1)[0]
                                     .replace('-', ' '))
                        j.setdefault('state', um.group(3).rsplit(',', 1)[1])
                    j['title'] = data.get('title') or j.get('title')
                    j['description_html'] = data.get('description')
                    j['industry'] = data.get('industry')
                    org = data.get('hiringOrganization') or {}
                    j['company'] = org.get('name') or j.get('company')
                    j['company_website'] = org.get('sameAs')
                    j['logo_url'] = org.get('logo') or j.get('logo_url')
                    j['date_posted'] = data.get('datePosted')
                    j['soc_code'] = (data.get('occupationalCategory') or
                                     '').split(':')[0]
                    emp = data.get('employmentType') or ''
                    if isinstance(emp, list):
                        emp = ','.join(str(e) for e in emp)
                    if emp and not j.get('employment_types'):
                        j['employment_types'] = [EMP_MAP.get(
                            'EMPLOYMENT_TYPE_NAME_' + e.strip(), 'full_time')
                            for e in emp.split(',') if e.strip()]
                    jobs[detail_jid] = j
                if data.get('@type') == 'FAQPage':
                    for q in data.get('mainEntity') or []:
                        faqs.setdefault(key, []).append({
                            'question': q.get('name'),
                            'answer': q.get('acceptedAnswer', {}).get('text'),
                        })
            # company widget + About blocks from the RSC payload
            m = re.search(r'companyWidget\\":\{', h)
            if m and detail_jid:
                frag = extract_balanced(h, m.end() - 1)
                widget = parse_escaped_json(frag) if frag else {}
                if widget:
                    j = jobs.setdefault(detail_jid, {'jid': detail_jid,
                                                    'source_file': fn})
                    j['company_widget'] = widget
                    cname = widget.get('displayName')
                    if cname:
                        j['company_block'] = parse_company_block(h, cname)

        # --- SERP pages: captured totals + page-1 order -------------------
        if key.startswith('search_') or key.startswith('s_'):
            mt = re.match(r'(\d+) (.+?) Jobs', meta.get('title') or '')
            qm = re.search(r'search=([^&]+)&location=([^&]+)',
                           meta.get('url') or '')
            if mt and qm:
                import urllib.parse as up
                term = up.unquote_plus(qm.group(1)).lower()
                location = up.unquote_plus(qm.group(2))
                order = []
                for data in ldjson_nodes(h):
                    if data.get('@type') == 'ItemList':
                        for it in data.get('itemListElement') or []:
                            jm = re.search(r'jid=(\w+)', it.get('url', ''))
                            if jm:
                                order.append(jm.group(1))
                serp_totals.append({
                    'term': term,
                    'location': location,
                    'upstream_total': int(mt.group(1)),
                    'page1_order': order,
                })

        # --- salary pages --------------------------------------------------
        if key.startswith('salary_'):
            stat = parse_salary_page(h, meta)
            stat['file'] = fn
            stat['page_title'] = meta.get('title') or ''
            stat['capture_url'] = meta.get('url')
            salary_pages.append(stat)

        # --- blog articles ---------------------------------------------------
        if key.startswith('blog_') and not key.startswith('blog_cat'):
            art = None
            for data in ldjson_nodes(h):
                if data.get('@type') == 'Article':
                    art = data
            if art:
                m = re.search(r'property="article:published_time" content="([^"]+)"', h)
                body = extract_entry_content(h)
                # the article's own categories: articleSection names them;
                # resolve to the deepest matching blog category slug
                cat_slug = None
                cat_name = None
                sections = [s for s in (art.get('articleSection') or [])]
                for cm in re.finditer(
                        r'href="https://www\.ziprecruiter\.com/blog/category/'
                        r'([^"]+?)/?"[^>]*>([^<]{2,50})<', h):
                    if '/' not in cm.group(1):
                        continue
                    if any(cm.group(2).strip().lower() == s.strip().lower()
                           for s in sections):
                        cat_slug = cm.group(1).rstrip('/')
                        cat_name = cm.group(2)
                        break
                body_imgs = re.findall(r'<img[^>]+\ssrc="(https?://[^"\s]+)"',
                                       body or '')
                section = sections[0] if sections else ''
                articles.append({
                    'slug': re.sub(r'^blog_(?:article_)?', '', key),
                    'title': art.get('headline'),
                    'author': ((art.get('author') or {}).get('name')
                               or 'The ZipRecruiter Editors'),
                    'published': (m.group(1) if m else art.get('datePublished')),
                    'modified': art.get('dateModified'),
                    'section': section,
                    'category_slug': cat_slug,
                    'category_name': cat_name,
                    'thumbnail': art.get('thumbnailUrl'),
                    'body_html': body,
                    'body_images': body_imgs,
                })

    # ---- fill description for SERP right-pane jobs (first card per SERP)
    for fn, meta in files:
        h = load(os.path.join(SCRAPE, fn))
        if not (fn.startswith('search_') or fn.startswith('s_')
                or fn.startswith('jobs_title') or fn == 'jobs_near_me.html'):
            continue
        # right-pane job: the RSC chunk with the full description
        for m in re.finditer(r'(\d+):T(\d+),', h):
            chunk_len = int(m.group(2))
            chunk = h[m.end():m.end() + chunk_len]
            if chunk.lstrip().startswith('<'):
                # candidate description chunk; find its jid via openSeatId
                seg = h[max(0, m.start() - 6000):m.start()]
                jid_m = re.search(r'openSeatId\\":\\"(\w+)', seg)
                if jid_m and jid_m.group(1) in jobs and \
                        'description_html' not in jobs[jid_m.group(1)]:
                    txt = chunk.encode().decode('unicode_escape', 'ignore')
                    jobs[jid_m.group(1)]['description_html'] = txt

    print(f"assembled {len(jobs)} jobs")
    dump('jobs_raw.json', jobs)
    dump('serp_totals.json', serp_totals)
    dump('salary_raw.json', salary_pages)
    dump('blog_raw.json', articles)
    dump('faqs_raw.json', faqs)
    finalize(jobs, salary_pages, articles, faqs, serp_totals)


# ------------------------------------------------------------ finalization --

FAMILIES = [
    ('software-engineer', 'Software Engineer'),
    ('registered-nurse', 'Registered Nurse'),
    ('licensed-practical-nurse', 'Licensed Practical Nurse'),
    ('accountant', 'Accountant'),
    ('warehouse-worker', 'Warehouse Worker'),
    ('truck-driver', 'Truck Driver'),
    ('customer-service-representative', 'Customer Service Representative'),
    ('teacher', 'Teacher'),
    ('data-analyst', 'Data Analyst'),
    ('sales-representative', 'Sales Representative'),
    ('electrician', 'Electrician'),
    ('receptionist', 'Receptionist'),
    ('project-manager', 'Project Manager'),
    ('marketing-manager', 'Marketing Manager'),
]


def canonical_family(title):
    """Map a captured job title to its canonical title family."""
    t = (title or '').lower()
    for slug, name in FAMILIES:
        if all(tok in t for tok in name.lower().split()):
            return slug
    return None


def logo_logical_name(url):
    """company/<hash>.png -> co-logo-<hash>"""
    m = re.search(r'company/([0-9a-f]+)\.(?:png|jpeg|jpg)', url or '')
    return f"co-logo-{m.group(1)}" if m else None


def finalize(jobs, salary_pages, articles, faqs, serp_totals):
    # ---- companies --------------------------------------------------
    companies = OrderedDict()
    for j in sorted(jobs.values(), key=lambda x: x['jid']):
        slug = j.get('company_slug') or slugify_title(j.get('company') or '')
        if not slug:
            continue
        co = companies.setdefault(slug, {
            'slug': slug, 'name': j.get('company') or slug.replace('-', ' '),
            'n_jobs': 0, 'jobs': []})
        co['n_jobs'] += 1
        co['jobs'].append(j['jid'])
        w = j.get('company_widget') or {}
        b = j.get('company_block') or {}
        br = b.get('breakroom') or {}
        for src, dst in [
            (w.get('displayName'), 'name'),
            ((w.get('canonicalIndustries') or [None])[0], 'industry'),
            (w.get('companySizeDisplay'), 'size'),
            (w.get('canonicalWebsite'), 'website'),
            (br.get('website'), 'website'),
            (br.get('about'), 'br_about'),
            (b.get('industry'), 'industry'),
            (b.get('size'), 'size'),
            (b.get('hq_city'), 'hq_city'),
            (b.get('hq_state'), 'hq_state'),
            (b.get('founded'), 'founded'),
            (b.get('website'), 'website'),
            (b.get('sourced_about'), 'sourced_about'),
        ]:
            if src and not co.get(dst):
                co[dst] = src
        if br.get('rating') is not None and 'rating_value' not in co:
            co['rating_value'] = str(br.get('rating'))
            co['rating_count'] = br.get('response_count')
            co['rating_highlights'] = br.get('highlights') or []
            co['findings'] = br.get('findings') or []
        logo = logo_logical_name(j.get('logo_url'))
        if logo and not co.get('logo'):
            co['logo'] = logo
            co['logo_url'] = j.get('logo_url')
    # hq from widget's hqLocation ('New York, NY, US')
    for j in jobs.values():
        w = j.get('company_widget') or {}
        slug = j.get('company_slug')
        if slug and slug in companies and not companies[slug].get('hq_city'):
            hq = w.get('hqLocation') or ''
            m = re.match(r'([A-Za-z .]+), ([A-Z]{2})(?:, US)?$', hq)
            if m:
                companies[slug]['hq_city'] = m.group(1).strip()
                companies[slug]['hq_state'] = m.group(2)
    for co in companies.values():
        co.pop('jobs', None)
    dump('companies.json', list(companies.values()))

    # ---- jobs --------------------------------------------------------
    rows = []
    for jid in sorted(jobs):
        j = jobs[jid]
        if not j.get('city') or not j.get('state'):
            continue
        fam = canonical_family(j.get('title') or j.get('title_slug', ''))
        desc = j.get('description_html') or ''
        if not desc and j.get('short_description'):
            desc = '<p>' + H.escape(j['short_description']) + '</p>'
        rows.append({
            'jid': jid,
            'title': j.get('title') or (j.get('title_slug') or '').replace('-', ' '),
            'title_slug': j.get('title_slug'),
            'company_slug': j.get('company_slug') or slugify_title(j.get('company') or ''),
            'city': j['city'],
            'state': j['state'],
            'family': fam,
            'industry': j.get('industry'),
            'employment_types': j.get('employment_types') or ['full_time'],
            'remote': j.get('remote') or 'onsite',
            'experience': derive_experience(j.get('title'), desc),
            'salary_min': j.get('salary_min'),
            'salary_max': j.get('salary_max'),
            'salary_text': j.get('salary_text'),
            'salary_period': (j.get('salary_interval') or
                              '').replace('PAY_INTERVAL_', '').lower() or None,
            'benefits': j.get('benefits') or [],
            'posted_days': j.get('posted_days') if j.get('posted_days') is not None else 0,
            'posted_text': j.get('posted_text'),
            'quick_apply': bool(j.get('quick_apply')),
            'is_new': bool(j.get('is_new')),
            'description_html': desc,
            'soc_code': j.get('soc_code'),
        })
    dump('jobs.json', rows)

    # ---- FAQs per canonical family ------------------------------------
    fam_faqs = OrderedDict()
    for key, qlist in faqs.items():
        jid = key.replace('jd_', '')
        j = jobs.get(jid) or {}
        fam = canonical_family(j.get('title') or j.get('title_slug') or '')
        if not fam:
            continue
        bucket = fam_faqs.setdefault(fam, [])
        for q in qlist:
            qn = q['question'] or ''
            if not (qn.startswith('What skills or qualities') or
                    qn.startswith('What is the career path')):
                continue
            if not any(q['question'] == e['question'] for e in bucket):
                bucket.append({'question': q['question'],
                               'answer_html': '<p>' + H.escape(q['answer'] or '') + '</p>'})
    dump('faqs.json', [{'family': f, 'items': v} for f, v in fam_faqs.items()])

    # ---- salaries -------------------------------------------------------
    sal_rows = []
    for s in salary_pages:
        url = s.get('capture_url') or ''
        if '-Salary-in-' in url:
            m = re.search(r'/Salaries/([\w.-]+)-Salary-in-([\w.-]+),([A-Z]{2})$', url)
            if not m:
                continue
            scope, city, state = 'city', m.group(2).replace('-', ' '), m.group(3)
            slug = m.group(1).lower()
        else:
            m = re.search(r'/Salaries/([\w.-]+)-Salary$', url)
            if not m:
                continue
            scope, city, state, slug = 'national', None, None, m.group(1).lower()
        sal_rows.append({
            'title_slug': slug,
            'scope': scope, 'city': city, 'state': state,
            'name': s.get('name'),
            'avg_year': s.get('avg_year'), 'avg_hour': s.get('avg_hour'),
            'p10': s.get('p10'), 'p25': s.get('p25'), 'median': s.get('median'),
            'p75': s.get('p75'), 'p90': s.get('p90'),
            'histogram': s.get('histogram') or [],
            'top_cities': s.get('top_cities') or [],
            'related': s.get('related') or [],
            'comparison': s.get('comparison') or [],
            'nearby': [re.search(r'jid=(\w+)', u).group(1)
                       for u in (s.get('nearby') or [])
                       if re.search(r'jid=(\w+)', u)],
            'page_title': s.get('page_title'),
        })
    dump('salaries.json', sal_rows)

    # ---- titles ------------------------------------------------------------
    title_rows = []
    have = set()
    for slug, name in FAMILIES:
        title_rows.append({'slug': slug, 'name': name})
        have.add(slug)
    # salary-page-only titles (e.g. related titles with their own page)
    for s in sal_rows:
        if s['scope'] == 'national' and s['title_slug'] not in have:
            title_rows.append({'slug': s['title_slug'], 'name': s['name']})
            have.add(s['title_slug'])
    dump('titles.json', title_rows)

    # ---- blog ---------------------------------------------------------------
    blog_rows = []
    for a in articles:
        blog_rows.append({
            'slug': a['slug'], 'title': a['title'],
            'author': a['author'], 'published': a['published'],
            'modified': a['modified'], 'category_slug': a['category_slug'],
            'category_name': a['section'],
            'thumbnail': a['thumbnail'],
            'body_html': a['body_html'], 'body_images': a['body_images'],
        })
    dump('blog.json', blog_rows)

    # ---- SERP snapshots (term, location, upstream total, page-1 order) -----
    dump('serp_snapshots.json', serp_totals)
    print(f"finalized: {len(rows)} jobs, {len(companies)} companies, "
          f"{len(sal_rows)} salary pages, {len(title_rows)} titles, "
          f"{len(blog_rows)} articles")


if __name__ == '__main__':
    main()
