#!/usr/bin/env python3
"""Build the tracked source_data snapshots from the raw upstream captures.

Reads scraped_data/captures/*.html (real upstream captures of
https://www.foxsports.com/ and its league sub-sites; see provenance.json)
and emits the JSON snapshots that seed_lib.py materializes into the
SQLite seed at build time. The upstream is a Nuxt SSR site: every page
needed here is fully server-rendered, so plain-HTML parsing with the
stdlib recovers the same data a browser sees.

Every capture carries a .meta.json sidecar with the exact URL, HTTP status
and capture timestamp. Parsing is stdlib-only (html.parser) so the script
also runs inside the Docker build environment without extra deps.
"""
from __future__ import annotations

import html as htmllib
import json
import os
import re
from html.parser import HTMLParser
from pathlib import Path

HERE = Path(__file__).resolve().parent
SITE = HERE.parent
CAP = SITE / 'scraped_data' / 'captures'
OUT = SITE / 'source_data'


def read(name: str) -> str:
    return (CAP / f"{name}.html").read_text(encoding='utf-8', errors='replace')


def meta(name: str) -> dict:
    return json.loads((CAP / f"{name}.meta.json").read_text(encoding='utf-8'))


def emit(name: str, payload) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(payload, indent=1, ensure_ascii=False) +
                            '\n', encoding='utf-8')
    print(f'  wrote {name}')


# --------------------------------------------------------------------------
# Minimal structured HTML extraction (stdlib only)
# --------------------------------------------------------------------------

class Cell:
    __slots__ = ('text', 'links', 'imgs')

    def __init__(self):
        self.text: list[str] = []
        self.links: list[tuple[str, str]] = []   # (href, text)
        self.imgs: list[tuple[str, str]] = []    # (src, alt)

    @property
    def t(self) -> str:
        return re.sub(r'\s+', ' ', ''.join(self.text)).strip()


class Table:
    def __init__(self):
        self.rows: list[list[Cell]] = []

    def __len__(self):
        return len(self.rows)

    def row(self, i: int) -> list[str]:
        return [c.t for c in self.rows[i]]


class GridParser(HTMLParser):
    """Collect <table> grids, heading texts and standalone anchors/images."""

    def __init__(self, html_text: str):
        super().__init__(convert_charrefs=True)
        self.html_text = html_text
        self.tables: list[Table] = []
        self.headings: list[str] = []
        self._table = None
        self._row = None
        self._cell = None
        self._anchor = None
        self._img = None
        self._anchor_text: list[str] = []
        self._anchor_imgs: list[tuple[str, str]] = []
        self.anchors: list[tuple[str, str]] = []
        self.anchor_imgs: list[tuple[str, tuple[str, str]]] = []   # href -> first img
        self._skip = 0
        self.feed(html_text)

    # -- tag handling -----------------------------------------------------
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ('script', 'style'):
            self._skip += 1
            return
        if tag == 'table':
            self._table = Table()
        elif tag == 'tr' and self._table is not None:
            self._row = []
        elif tag in ('td', 'th') and self._table is not None and self._row is not None:
            self._cell = Cell()
            self._row.append(self._cell)
        elif tag == 'a':
            href = a.get('href') or ''
            self._anchor = href
            self._anchor_text = []
        elif tag == 'img':
            src = a.get('src') or a.get('data-src') or ''
            alt = a.get('alt') or ''
            if self._cell is not None:
                self._cell.imgs.append((src, alt))
            elif self._anchor is not None:
                self._anchor_imgs.append((src, alt))
        elif tag in ('h1', 'h2', 'h3', 'h4'):
            self._heading = []
        if tag in ('h1', 'h2', 'h3', 'h4') and not hasattr(self, '_heading'):
            self._heading = []

    def handle_startendtag(self, tag, attrs):
        if tag == 'img':
            self.handle_starttag('img', attrs)

    def handle_endtag(self, tag):
        if tag in ('script', 'style'):
            self._skip = max(0, self._skip - 1)
            return
        if tag == 'table' and self._table is not None:
            if self._table.rows:
                self.tables.append(self._table)
            self._table = None
        elif tag == 'tr' and self._row is not None:
            if self._table is not None and self._row:
                self._table.rows.append(self._row)
            self._row = None
            self._cell = None
        elif tag in ('td', 'th'):
            self._cell = None
        elif tag == 'a' and self._anchor is not None:
            text = re.sub(r'\s+', ' ', ''.join(self._anchor_text)).strip()
            if self._cell is not None:
                self._cell.links.append((self._anchor, text))
            else:
                self.anchors.append((self._anchor, text))
                if self._anchor_imgs:
                    self.anchor_imgs.append((self._anchor, self._anchor_imgs[0]))
            self._anchor = None
            self._anchor_text = []
            self._anchor_imgs = []
        elif tag in ('h1', 'h2', 'h3', 'h4'):
            if getattr(self, '_heading', None):
                text = re.sub(r'\s+', ' ', ''.join(self._heading)).strip()
                if text:
                    self.headings.append(text)
            self._heading = []

    def handle_data(self, data):
        if self._skip:
            return
        if getattr(self, '_heading', None) is not None and self._heading:
            self._heading.append(data)
        if self._anchor is not None:
            self._anchor_text.append(data)
        if self._cell is not None:
            self._cell.text.append(data)


def grid(name: str) -> GridParser:
    return GridParser(read(name))


def plain_text(html_text: str) -> str:
    """Whole-page visible text: scripts/styles removed, every remaining tag
    replaced by a '|' so section fields stay separated for the parsers."""
    text = re.sub(r'<script.*?</script>', ' ', html_text, flags=re.S)
    text = re.sub(r'<style.*?</style>', ' ', text, flags=re.S)
    text = re.sub(r'<!--.*?-->', ' ', text, flags=re.S)
    text = re.sub(r'<br\s*/?>', '|', text, flags=re.I)
    text = re.sub(r'<[^>]+>', '|', text)
    text = htmllib.unescape(text)
    text = re.sub(r'[ \t\r\n]+', ' ', text)
    text = re.sub(r'\s*\|\s*', '|', text)
    text = re.sub(r'\|+', '|', text)
    return text.strip('|')


def split_name(full: str) -> tuple[str, str]:
    """'Kansas City Chiefs' -> ('Kansas City', 'Chiefs') using the last word."""
    parts = full.strip().split()
    if len(parts) < 2:
        return ('', full)
    return (' '.join(parts[:-1]), parts[-1])


TEAM_RE = re.compile(r'^/(nfl|mlb|college-football)/([a-z0-9()-]+)-team$')


def team_slug(href: str) -> str:
    m = TEAM_RE.match(href)
    return m.group(2) if m else None


def league_of(href: str) -> str:
    m = TEAM_RE.match(href)
    return m.group(1) if m else None


def _parse_leaders(html_text: str):
    """TEAM LEADERS comparison rows from the boxscore capture, aligned by
    (label, side).

    The upstream section renders one row per stat label with the away
    leader on the left and the home leader on the right. Two layouts exist:
    the football event pages split names across first-name/last-name spans,
    while the baseball pages put the whole name in a leader-name anchor.
    Parsing the raw HTML keeps each side's leader bound to its own team
    column (the earlier plain-text token parser mis-assigned sides and
    labels whenever the two sides' rows interleaved)."""
    start = html_text.find('<div data-qa="teamLeadersComparison"')
    if start < 0:
        return []
    seg = html_text[start:start + 200000]
    rows = []
    parts = re.split(
        r'<div class="(?:leader-comparison-row|team-comparison-row leaders-row)">',
        seg)
    for part in parts[1:]:
        label_m = re.search(
            r'matchup-comparison-text[^"<]*"[^>]*>(.*?)</span>', part)
        if not label_m:
            continue
        label = re.sub(r'\s+', ' ', label_m.group(1)).strip()
        left, right = part[:label_m.start()], part[label_m.end():]

        def side(chunk: str):
            firsts = re.findall(r'first-name">(?:<[^>]+>)*([^<]*)</span>', chunk)
            lasts = re.findall(r'last-name">(?:<[^>]+>)*([^<]*)</span>', chunk)
            if firsts and lasts:
                name = ' '.join(t.strip() for t in firsts) + ' ' + \
                    ' '.join(t.strip() for t in lasts)
            else:
                names = re.findall(r'leader-name">(.*?)</a>', chunk)
                name = names[0] if names else ''
            values = re.findall(r'stat-val[^>]*>([^<]*)</div>', chunk)
            return name.strip(), (values[0].strip() if values else None)

        away_name, away_val = side(left)
        home_name, home_val = side(right)
        if away_name and away_val:
            rows.append({'side': 'away', 'player': away_name,
                         'value': away_val, 'label': label})
        if home_name and home_val:
            rows.append({'side': 'home', 'player': home_name,
                         'value': home_val, 'label': label})
    return rows




# --------------------------------------------------------------------------
# Leagues + teams
# --------------------------------------------------------------------------

LEAGUES = [
    ('nfl', 'NFL', 'Football'),
    ('college-football', 'College Football', 'Football'),
    ('mlb', 'MLB', 'Baseball'),
    ('nascar', 'NASCAR', 'Racing'),
    ('ufc', 'UFC', 'Fighting'),
]

# capture file prefix per league (the crawler's short names)
CAP_PREFIX = {'nfl': 'nfl', 'college-football': 'cfb', 'mlb': 'mlb'}


def build_teams():
    """Teams from each league's /teams hub: logo anchors carry the alt text
    (full team name) and the b.fssta.com logo; the sibling name anchor
    carries the short display name."""
    teams = []
    seen = set()
    for league, _, _ in LEAGUES[:3]:
        h = read(f'{CAP_PREFIX[league]}-teams')
        found = {}
        for m in re.finditer(
                r'<a\b[^>]*href="(/(?:nfl|mlb|college-football)/([a-z0-9-]+)-team)"[^>]*>(.*?)</a>',
                h, re.S):
            href, slug, body = m.group(1), m.group(2), m.group(3)
            entry = found.setdefault(slug, {'texts': [], 'imgs': []})
            text = re.sub(r'<[^>]+>', ' ', body)
            text = re.sub(r'\s+', ' ', htmllib.unescape(text)).strip()
            if text:
                entry['texts'].append(text)
            for im in re.finditer(r'<img[^>]+>', body):
                tag = im.group(0)
                src = re.search(r'src="([^"]*)"', tag)
                alt = re.search(r'alt="([^"]*)"', tag)
                if src and 'b.fssta.com' in src.group(1):
                    entry['imgs'].append(
                        (htmllib.unescape(src.group(1)),
                         htmllib.unescape(alt.group(1)) if alt else ''))
        for slug, entry in found.items():
            if (league, slug) in seen:
                continue
            seen.add((league, slug))
            logo, alt = entry['imgs'][0] if entry['imgs'] else (None, None)
            full = alt or (entry['texts'][0] if entry['texts'] else slug.replace('-', ' ').title())
            short = None
            for t in entry['texts']:
                if (t.lower() != full.lower() and len(t) < len(full)
                        and re.search(r'[A-Za-z]', t)
                        and not re.fullmatch(r'[\d.,:+\-/ ]+', t.strip())):
                    short = t
            city, last = split_name(full)
            teams.append({
                'league': league, 'slug': slug, 'full_name': full,
                'city': city, 'short': short or last, 'logo': logo,
            })
    teams.sort(key=lambda t: (t['league'], t['slug']))
    emit('teams.json', teams)
    return teams


# --------------------------------------------------------------------------
# Standings (NFL divisions, MLB divisions, CFB AP poll) + NASCAR + UFC
# --------------------------------------------------------------------------

NFL_DIVISIONS = [f'{c} {d}' for c in ('AFC', 'NFC')
                 for d in ('EAST', 'NORTH', 'SOUTH', 'WEST')]
MLB_DIVISIONS = [f'{c} {d}' for c in ('AL', 'NL')
                 for d in ('EAST', 'CENTRAL', 'WEST')]


def _division_tables(g, wanted):
    """Pair each division heading with its standings table. The division
    tables appear in the page in the same order as `wanted`, so the k-th
    standings table (header carrying the record column, team links in the
    body) belongs to the k-th division name."""
    linked = []
    for tbl in g.tables:
        if len(tbl) < 2:
            continue
        header = tbl.row(0)
        if not header or not ('W-L-T' in header or 'W-L' in header):
            continue
        has_teams = any(
            TEAM_RE.match(href)
            for r in range(1, len(tbl))
            for c in tbl.rows[r] for href, _ in c.links)
        if has_teams:
            linked.append(tbl)
    return list(zip(wanted, linked[:len(wanted)]))


def build_standings():
    out = {}

    # ---- NFL: eight division tables ----
    g = grid('nfl-standings')
    nfl = []
    for division, tbl in _division_tables(g, NFL_DIVISIONS):
        for r in range(1, len(tbl)):
            cells = tbl.rows[r]
            vals = [c.t for c in cells]
            team_cell = cells[1] if len(cells) > 1 else None
            if team_cell is None:
                continue
            link = next((ln for ln in team_cell.links if TEAM_RE.match(ln[0])), None)
            if not link:
                continue
            img = team_cell.imgs[0] if team_cell.imgs else (None, None)
            nfl.append({
                'league': 'nfl', 'division': division,
                'slug': team_slug(link[0]),
                'rank': vals[0], 'record': vals[2], 'pct': vals[3],
                'pf': vals[4], 'pa': vals[5], 'home': vals[6], 'away': vals[7],
                'conf': vals[8], 'div': vals[9],
                'strk': vals[10] if len(vals) > 10 else '',
                'logo': img[0], 'full_name': img[1],
            })
    out['nfl'] = nfl

    # ---- MLB: six division tables ----
    g = grid('mlb-standings')
    mlb = []
    for division, tbl in _division_tables(g, MLB_DIVISIONS):
        for r in range(1, len(tbl)):
            cells = tbl.rows[r]
            vals = [c.t for c in cells]
            team_cell = cells[1] if len(cells) > 1 else None
            if team_cell is None:
                continue
            link = next((ln for ln in team_cell.links if TEAM_RE.match(ln[0])), None)
            if not link:
                continue
            img = team_cell.imgs[0] if team_cell.imgs else (None, None)
            name = vals[1]
            clinch = ''
            for mark, label in (('Z', 'clinched_division'),
                                ('X', 'clinched_playoffs')):
                if name.endswith(' ' + mark):
                    clinch = label
                    name = name[:-2].strip()
            mlb.append({
                'league': 'mlb', 'division': division,
                'slug': team_slug(link[0]), 'rank': vals[0], 'name': name,
                'record': vals[2], 'pct': vals[3], 'gb': vals[4],
                'home': vals[5], 'away': vals[6], 'rs': vals[7], 'ra': vals[8],
                'diff': vals[9], 'l10': vals[10],
                'strk': vals[11] if len(vals) > 11 else '',
                'clinch': clinch, 'logo': img[0], 'full_name': img[1],
            })
    out['mlb'] = mlb

    # ---- CFB: the AP Top 25 poll table ----
    g = grid('cfb-standings')
    poll = []
    for tbl in g.tables:
        if len(tbl) < 2 or tbl.row(0)[:1] != ['RANKING']:
            continue
        for r in range(1, len(tbl)):
            cells = tbl.rows[r]
            vals = [c.t for c in cells]
            team_cell = cells[2] if len(cells) > 2 else None
            if team_cell is None:
                continue
            link = next((ln for ln in team_cell.links if TEAM_RE.match(ln[0])), None)
            if not link:
                continue
            blob = vals[2]
            votes = 0
            mv = re.search(r'\((\d+)\)', blob)
            if mv:
                votes = int(mv.group(1))
            rec = re.search(r'(\d+-\d+)\s*$', blob)
            name = re.sub(r'\s*\(\d+\)\s*\d+-\d+\s*$', '', blob).strip()
            if not name:
                name = re.sub(r'\s*\d+-\d+\s*$', '', blob).strip()
            name = re.sub(r'\s+\d+-\d+\s*$', '', name).strip()
            poll.append({
                'rank': int(vals[0]) if vals[0].isdigit() else 0,
                'movement': vals[1], 'team': name,
                'slug': team_slug(link[0]),
                'first_place_votes': votes,
                'record': rec.group(1) if rec else '',
                'points': int(vals[3].replace(',', '')) if len(vals) > 3 and vals[3].replace(',', '').isdigit() else 0,
            })
        break
    out['cfb_poll'] = poll
    emit('standings.json', out)
    return out


# --------------------------------------------------------------------------
# Games: boxscore pages + league schedules
# --------------------------------------------------------------------------

BOX_URL_RE = re.compile(
    r'^/(nfl|mlb|college-football)/(.+)-game-boxscore-(\d+)$')

MONTHS = {'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
          'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12}


def parse_slug_date(slug_body: str):
    """'week-4-...-oct-01-2026' -> (2026, 10, 1)."""
    m = re.search(r'-(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)-'
                  r'(\d{1,2})-(\d{4})$', slug_body)
    if not m:
        return None
    return (int(m.group(3)), MONTHS[m.group(1)], int(m.group(2)))


def box_files():
    """All 2026 boxscore captures: (file_stem, league, slug_body, game_id)."""
    out = []
    for path in sorted(CAP.glob('box-*.html')):
        m = meta(path.stem)
        url = m.get('url', '')
        path_part = '/' + url.split('://', 1)[-1].split('/', 1)[-1] if url else ''
        bm = BOX_URL_RE.match(path_part)
        if not bm:
            continue
        league, slug_body, game_id = bm.group(1), bm.group(2), bm.group(3)
        parsed = parse_slug_date(slug_body)
        # keep the live 2026 seasons only: the current NFL/MLB/CFB seasons
        # start in August 2026; January 2026 dates belong to last season.
        if parsed is None or parsed[0] != 2026 or parsed[1] < 8:
            continue
        out.append((path.stem, league, slug_body, game_id, url))
    return out


def _game_header(text: str):
    """Boxscore header: full team names, records, scores/status, date."""
    m = re.search(
        r'([A-Za-z][A-Za-z0-9 ()&\.\'-]+?)\s+vs\.\s+'
        r'([A-Za-z][A-Za-z0-9 ()&\.\'-]+?):\s*'
        r'([A-Za-z]{3})\s*(\d{1,2}),\s*(\d{4})',
        text)
    if not m:
        return None
    rest = text[m.end():]
    # final: "|7|Miami (FL)|1-0|1-0|45|FINAL|6|1-1|Stanford|1-1|"
    fin = re.search(
        r'(?:\|\d+\|)?\|[^|]+\|([\d\-]+)\|(?:[\d\-]+\|)?'
        r'(\d+)\|FINAL(?:[^|]*)\|(\d+)\|([\d\-]+)\|', rest)
    # upcoming: "|Steelers|2-1|2-1|OCT 2, 12:15AM|AMZN|2-1|Browns|2-1|"
    up = re.search(
        r'(?:\|\d+\|)?\|[^|]+\|([\d\-]+)\|(?:[\d\-]+\|)?'
        r'(?:[A-Z]{3}\s?\d{1,2},\s*)?(\d{1,2}:\d{2}(?:AM|PM))\|([A-Z]{2,5})\|'
        r'([\d\-]+)\|', rest)
    return {
        'away_full': m.group(1).strip(), 'home_full': m.group(2).strip(),
        'date': f"{m.group(3)} {m.group(4)}, {m.group(5)}",
        'final': fin.groups() if fin else None,
        'upcoming': up.groups() if up else None,
    }


def _section(text: str, start: str, end: str):
    """Slice the '|' delimited page text between two section markers."""
    i = text.find(start)
    if i < 0:
        return ''
    j = text.find(end, i + len(start))
    return text[i:j] if j > 0 else text[i:i + 4000]


def _mlb_header(text: str, slug_body: str):
    """MLB boxscore header for both the wild-card postseason format and the
    regular-season format. Returns None when the page is not an MLB game."""
    out = {'series': None, 'series_note': None, 'series_game': None,
           'away_short': None, 'home_short': None,
           'away_full': None, 'home_full': None,
           'final': None, 'upcoming': None, 'recap': None, 'innings': None}
    banner = re.search(
        r"((?:NL|AL) WILD CARD GAME \d+\*? - [^|]+)\|"
        r"([A-Za-z][A-Za-z .\'-]{2,24})\|vs\|?-?\|?"
        r"([A-Za-z][A-Za-z .\'-]{2,24})\|", text)
    if banner:
        note = banner.group(1)
        out['series_note'] = note
        out['series'] = re.sub(r' GAME \d+.*$', '', note)
        gm = re.search(r'GAME (\d+)', note)
        if gm:
            out['series_game'] = int(gm.group(1))
        out['away_short'] = banner.group(2).strip()
        out['home_short'] = banner.group(3).strip()
        rest = text[banner.end():]
        up = re.match(
            r'(?:-\|)*\|?(?:Today at|Tomorrow at|([A-Za-z]{3} \d{1,2}) at)?\s*'
            r'(\d{1,2}:\d{2})\s*(AM|PM)\s*on\|([A-Z]{2,5})\|', rest)
        if up:
            out['upcoming'] = (f'{up.group(2)} {up.group(3)}', up.group(4))
    else:
        fm = re.search(
            r"([A-Za-z][A-Za-z0-9 ()&.\'-]+?)\s+vs\.\s+"
            r"([A-Za-z][A-Za-z0-9 ()&.\'-]+?):\s*"
            r'(?:[A-Za-z]{3}\s*\d{1,2},\s*\d{4})', text)
        if not fm:
            return None
        out['away_full'] = fm.group(1).strip()
        out['home_full'] = fm.group(2).strip()
        # 'Rays|1|1|5|1|0|0|0|1|X|9|12|1' style upcoming rows carry no time
        # pattern; games still scheduled show 'Today at H:MM PM on|NET|'
        up = re.search(
            r'(?:Today|Tomorrow)\s+at\s+(\d{1,2}:\d{2})\s*(AM|PM)\s*on\|([A-Z]{2,5})\|',
            text)
        if up:
            out['upcoming'] = (f'{up.group(1)} {up.group(2)}', up.group(3))
    # final line score: '...|1|2|3|4|5|6|7|8|9|R|H|E|TB|0|0|..|2|6|1|NYY|..|9|12|1|'
    lm = re.search(
        r'9\|R\|H\|E\|([A-Z]{2,4})\|((?:[0-9X]+\|){9})'
        r'([0-9]+)\|([0-9]+)\|([0-9]+)\|'
        r'([A-Z]{2,4})\|((?:[0-9X]+\|){9})'
        r'([0-9]+)\|([0-9]+)\|([0-9]+)\|', text)
    if lm:
        out['final'] = (lm.group(1), lm.group(6),
                        int(lm.group(3)), int(lm.group(8)),
                        lm.group(4), lm.group(9), lm.group(5), lm.group(10))
        out['innings'] = {
            lm.group(1): lm.group(2).rstrip('|').split('|'),
            lm.group(6): lm.group(7).rstrip('|').split('|'),
        }
    rm = re.search(r"\|([^|]{20,140}?)\|KEY PLAYERS\|", text)
    if rm:
        out['recap'] = rm.group(1).strip()
    if out['final'] is None and out['upcoming'] is None and out['series_note'] is None \
            and out['away_full'] is None:
        return None
    return out


def _norm_slug(slug: str) -> str:
    return re.sub(r'[^a-z0-9]', '', slug or '')


def _slug_parts(slug_body: str):
    """'week-4-pittsburgh-steelers-vs-cleveland-browns-oct-01-2026' ->
    ('week-4-pittsburgh-steelers', 'cleveland-browns')."""
    body = re.sub(r'-(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)-'
                  r'\d{1,2}-\d{4}$', '', slug_body)
    if '-vs-' not in body:
        return None, None
    away, home = body.split('-vs-', 1)
    return away, home


def _resolve_team(part, header_name, team_index, name_index):
    """Match a slug fragment or a full team name to a known team."""
    if part:
        norm = _norm_slug(part)
        best = None
        for t in team_index.values():
            ts = _norm_slug(t['slug'])
            if ts and norm.endswith(ts):
                if best is None or len(ts) > len(_norm_slug(best['slug'])):
                    best = t
        if best:
            return best['slug']
    if header_name:
        hit = name_index.get(re.sub(r'[^a-z0-9]', '', header_name.lower()))
        if hit:
            return hit
    return None


def build_games():
    teams = json.load(open(OUT / 'teams.json'))
    team_index = {(t['league'], _norm_slug(t['slug'])): t for t in teams}
    name_index = {}
    short_index = {}
    for t in teams:
        name_index[re.sub(r'[^a-z0-9]', '', t['full_name'].lower())] = t['slug']
        if t.get('short'):
            short_index.setdefault((t['league'], t['short'].lower()), t['slug'])
    # merge the CFB AP-poll teams (slug + display name) before resolving games
    standings = json.load(open(OUT / 'standings.json'))
    for row in standings['cfb_poll']:
        key = ('college-football', _norm_slug(row['slug']))
        if key in team_index:
            continue
        full = row['team']
        new = {'league': 'college-football', 'slug': row['slug'], 'full_name': full,
               'city': split_name(full)[0], 'short': split_name(full)[1], 'logo': None}
        teams.append(new)
        team_index[key] = new
        name_index[re.sub(r'[^a-z0-9]', '', full.lower())] = row['slug']
        short_index.setdefault(('college-football', full.rsplit(' ', 1)[-1].lower()),
                               row['slug'])

    # global logo pool: full name -> team-logo URL (200px variants)
    logo_pool = {}
    for path in sorted(CAP.glob('box-*.html')) + sorted(CAP.glob('team-*.html')):
        h = path.read_text(encoding='utf-8', errors='replace')[:400000]
        for m in re.finditer(r'<img[^>]+>', h):
            tag = m.group(0)
            src = re.search(r'src="([^"]+)"', tag)
            alt = re.search(r'alt="([^"]{3,40})"', tag)
            if not (src and alt and '/team-logos/' in src.group(1)):
                continue
            url = htmllib.unescape(src.group(1))
            name = htmllib.unescape(alt.group(1))
            if '.vresize.200.200.' in url or name not in logo_pool:
                logo_pool.setdefault(name, url)

    def ensure_team(league, part, header_name):
        slug = _resolve_team(part, header_name, team_index, name_index)
        if slug:
            return slug
        frag = re.sub(r'^(?:preseason-)?week-\d+-', '', part or '')
        frag = re.sub(r'^([a-z]{1,3}-)+(?=[a-z]{4,})', '', frag)
        base = frag or re.sub(r'[^a-z0-9]+', '-', (header_name or '').lower()).strip('-')
        if not base:
            return None
        full = header_name or base.replace('-', ' ').title()
        new = {'league': league, 'slug': base, 'full_name': full,
               'city': split_name(full)[0], 'short': split_name(full)[1],
               'logo': logo_pool.get(full)}
        teams.append(new)
        team_index[(league, _norm_slug(base))] = new
        name_index[re.sub(r'[^a-z0-9]', '', full.lower())] = base
        return base

    games = []
    details = {}
    for stem, league, slug_body, game_id, url in box_files():
        text = plain_text(read(stem))
        mlb_head = _mlb_header(text, slug_body) if league == 'mlb' else None
        head = _game_header(text) if mlb_head is None else None
        if mlb_head is None and head is None:
            continue
        away_part, home_part = _slug_parts(slug_body)
        if mlb_head is not None:
            away_hint = mlb_head['away_short'] or mlb_head['away_full']
            home_hint = mlb_head['home_short'] or mlb_head['home_full']
            away_slug = (short_index.get((league, mlb_head['away_short'].lower()))
                         if mlb_head['away_short'] else None) or \
                ensure_team(league, away_part, away_hint)
            home_slug = (short_index.get((league, mlb_head['home_short'].lower()))
                         if mlb_head['home_short'] else None) or \
                ensure_team(league, home_part, home_hint)
        else:
            away_slug = ensure_team(league, away_part, head['away_full'])
            home_slug = ensure_team(league, home_part, head['home_full'])
        year, month, day = parse_slug_date(slug_body)
        date_label = head['date'] if head else \
            f'{["","Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"][month]} {day}, {year}'
        rec = {
            'league': league,
            'slug': f'{slug_body}-game-boxscore-{game_id}',
            'game_id': game_id,
            'date': date_label,
            'date_iso': f'{year:04d}-{month:02d}-{day:02d}',
            'away_team': away_slug,
            'home_team': home_slug,
            'status': 'scheduled',
        }
        if mlb_head is not None:
            rec['series'] = mlb_head['series']
            rec['series_note'] = mlb_head['series_note']
            if mlb_head['series_game']:
                rec['series_game'] = mlb_head['series_game']
            if mlb_head['final']:
                fa, fh, ra, rh, ha, hh, ae, he = mlb_head['final']
                rec.update({'status': 'final',
                            'away_abbr': fa, 'home_abbr': fh,
                            'away_score': ra, 'home_score': rh,
                            'away_hits': int(ha), 'home_hits': int(hh),
                            'away_errors': int(ae), 'home_errors': int(he)})
                if mlb_head.get('recap'):
                    rec['recap'] = mlb_head['recap']
            elif mlb_head['upcoming']:
                rec.update({'status': 'scheduled',
                            'time': mlb_head['upcoming'][0],
                            'broadcaster': mlb_head['upcoming'][1]})
            vm = re.search(r"\|([A-Za-z0-9 &,\.\'-]+?),\|([A-Za-z .-]+),\s*([A-Z]{2})\|MLB\|", text)
            if vm:
                rec['venue'] = vm.group(1).strip()
                rec['venue_city'] = f"{vm.group(2).strip()}, {vm.group(3)}"
        elif head['final']:
            rec.update({'status': 'final',
                        'away_record': head['final'][0],
                        'home_record': head['final'][3],
                        'away_score': int(head['final'][1]),
                        'home_score': int(head['final'][2])})
        elif head['upcoming']:
            rec.update({'status': 'scheduled',
                        'away_record': head['upcoming'][0],
                        'home_record': head['upcoming'][3],
                        'time': head['upcoming'][1],
                        'broadcaster': head['upcoming'][2]})
        wm = re.match(r'(?:preseason-)?week-(\d+)', slug_body)
        if wm and league in ('nfl', 'college-football'):
            rec['week'] = int(wm.group(1))
            rec['phase'] = 'preseason' if slug_body.startswith('preseason') else 'regular'
        # MATCHUP ODDS block: "|Las Vegas Raiders|LV|+3.5|+174|O 44.5|..."
        odds_txt = _section(text, 'MATCHUP ODDS', 'FOX FACTS')
        if odds_txt:
            pv = re.match(r'\|([A-Z][^|]{18,140})\|', odds_txt)
            if pv:
                rec['preview'] = pv.group(1).strip()
        else:
            parts = _section(text, 'MATCHUP', 'TEAM STATS').split('|')
            if len(parts) > 3 and parts[1] == 'ODDS' and parts[2]:
                rec['preview'] = parts[2].strip()
        om = re.findall(
            r'\|([A-Za-z][A-Za-z0-9 ()&\.\'-]{2,40}?)\|([A-Z]{2,4})\|'
            r'([-+][0-9.]+)\|([-+][0-9]+)\|O\s*([0-9.]+)', odds_txt)
        if om:
            rec['spread'] = om[0][2]
            rec['total'] = om[0][4]
            if len(om) >= 2:
                rec['home_ml'] = om[1][3]
                rec['away_ml'] = om[0][3]
        # EVENT INFO block: "|Caesars Superdome|New Orleans, LA|Sep 27, 2026|70006|..."
        ev = _section(text, 'EVENT INFO', 'Top Leagues')
        vm = re.search(r'\|([A-Za-z0-9 &\.\'-]+)\|([A-Za-z .-]+),\s*([A-Z]{2})\|', ev)
        if vm:
            rec['venue'] = vm.group(1).strip()
            rec['venue_city'] = f"{vm.group(2).strip()}, {vm.group(3)}"
        am = re.search(r'\|([\d,]+)\|\d+\s*Hours?\s*\d+\s*Minutes?\|', ev)
        if am:
            rec['attendance'] = int(am.group(1).replace(',', ''))
        games.append(rec)

        # ---- detail payload -----------------------------------------------
        det = {'slug': rec['slug'], 'league': league}
        facts = []
        fx = _section(text, 'FOX FACTS', 'STANDINGS')
        for kind in ('MILESTONE', 'INSIGHT', 'STAT HIGH', 'TEAM TREND', 'H2H'):
            for m in re.finditer(kind + r'\|([^\[\|]{10,240}?)(?=\||$)', fx):
                facts.append({'kind': kind, 'text': m.group(1).strip()})
        det['facts'] = facts[:6]
        stats = []
        sx = _section(text, 'MATCHUP', 'TEAM LEADERS')
        sm = re.findall(r'\|([0-9.]+)\|([A-Z/ ]{3,18})\|([0-9.]+)\|', sx)
        for a, label, b in sm:
            stats.append({'away': a, 'label': label.strip(), 'home': b})
        det['team_stats'] = stats
        # TEAM LEADERS: parse the raw capture HTML so each label row keeps
        # its away and home leaders bound to the correct team columns.
        det['leaders'] = _parse_leaders(read(stem))
        qb = re.findall(
            r"STARTING QUARTERBACKS\|([A-Za-z .\'-]+?)\|#(\d+)\s*·\s*([A-Z]{2,4})\|"
            r'PASSING YDS\|(\d+)\|', text)
        det['starting_qbs'] = [
            {'name': n.strip(), 'number': j, 'team_abbr': a, 'passing_yards': int(y)}
            for n, j, a, y in qb]
        recent = []
        g = grid(stem)
        for tbl in g.tables:
            if len(tbl) < 2:
                continue
            header = tbl.row(0)
            if 'RESULT' not in header or 'ATS' not in header:
                continue
            abbr = header[0] if header else ''
            for r in range(1, len(tbl)):
                vals = tbl.row(r)
                if len(vals) < 4:
                    continue
                recent.append({'side': abbr, 'date': vals[0], 'opponent': vals[2],
                               'result': vals[3], 'ats': vals[4] if len(vals) > 4 else '',
                               'ou': vals[5] if len(vals) > 5 else ''})
        det['recent_games'] = recent
        news = []
        nx = _section(text, 'PLAYER NEWS', 'STANDINGS')
        nm = re.findall(
            r"\|([A-Za-z][A-Za-z .\'-]{3,40}?)\|([A-Z]{2,3}\s*#\d+\s*·\s*[A-Z]{1,2})\|(.*?)"
            r"(?=\|[A-Za-z][A-Za-z .\'-]{3,40}\|[A-Z]{2,3}\s*#\d+|$)", nx)
        for name, meta_line, body in nm:
            news.append({'player': name.strip(), 'meta': meta_line.strip(),
                         'body': body.strip()[:400]})
        det['player_news'] = news[:6]
        if not det.get('odds_notes'):
            det['odds_notes'] = {}
        det['odds_notes'].setdefault('PREVIEW', rec.get('preview') or '')
        if mlb_head is not None:
            det['innings'] = mlb_head.get('innings')
            # KEY PLAYERS: name | team · #num pos | stat line
            key = []
            km = re.findall(
                r"\|([A-Za-z][A-Za-z .\'-]{2,28})\|([A-Z]{2,4}\s*·\s*#\d+\s*[A-Z0-9/ ]{0,6})\|"
                r"([^|]{3,60})\|", _section(text, 'KEY PLAYERS', 'ODDS'))
            key = [{'player': n.strip(), 'meta': m.strip(), 'line': l.strip()}
                   for n, m, l in km]
            det['key_players'] = key[:6]
            # betting result narratives
            odds = {}
            for label in ('RUN LINE', 'TOTAL', 'TEAM TO WIN'):
                om = re.search(label + r'\|([^|]{10,200})\|', text)
                if om:
                    odds[label] = om.group(1).strip()
            odds['PREVIEW'] = rec.get('preview') or ''
            det['odds_notes'] = odds
            # key plays: '|ATL SCORE|PHI 1|ATL 2|Bot 6, 1 out - ...|'
            plays = []
            pm = re.findall(
                r'\|([A-Z]{2,4}(?: KEY PLAY| SCORE))\|([A-Z]{2,4}) (\d+)\|'
                r'([A-Z]{2,4}) (\d+)\|([^|]{10,170})\|', _section(text, 'KEY PLAYS', 'Top Leagues'))
            for kind, a, sa, b, sb, desc in pm:
                plays.append({'kind': kind.strip(), 'away': f'{a} {sa}',
                              'home': f'{b} {sb}', 'text': desc.strip()})
            det['key_plays'] = plays[:10]
            # upcoming: TEAM STATS comparison + TEAM LEADERS (season)
            if rec['status'] == 'scheduled':
                sx = _section(text, 'TEAM STATS', 'TEAM LEADERS')
                sm2 = re.findall(r'\|([0-9.]+)\|([A-Z/ ]{1,18})\|([0-9.]+)\|', sx)
                det['team_stats'] = [{'away': a, 'label': lab.strip(), 'home': b}
                                    for a, lab, b in sm2]
                lx2 = _section(text, 'TEAM LEADERS', 'PREVIOUS GAMES')
                lm2 = re.findall(
                    r"\|PHI\|([A-Za-z][A-Za-z .\'-]{2,26})\|([0-9.]+)\|([A-Z/ ]{1,10})\|"
                    r"([A-Za-z][A-Za-z .\'-]{2,26})\|([0-9.]+)\|", lx2)
                det['mlb_leaders'] = [
                    {'side': 'away', 'player': a, 'value': v, 'label': lab}
                    for a, v, lab, _b, _v in lm2] + [
                    {'side': 'home', 'player': b, 'value': v2, 'label': lab}
                    for _a, _v, lab, b, v2 in lm2]
                pp = re.search(
                    r"PROBABLE STARTING PITCHERS\|#(\d+)\s*([LR]HP)\|([A-Za-z][A-Za-z .\'-]{2,26})\|"
                    r"([0-9-]+)\|([0-9.]+) ERA\|vs\|#(\d+)\s*([LR]HP)\|"
                    r"([A-Za-z][A-Za-z .\'-]{2,26})\|([0-9-]+)\|([0-9.]+) ERA\|", text)
                if pp:
                    det['probable_pitchers'] = {
                        'away': {'number': pp.group(1), 'throws': pp.group(2),
                                 'name': pp.group(3), 'record': pp.group(4),
                                 'era': pp.group(5)},
                        'home': {'number': pp.group(6), 'throws': pp.group(7),
                                 'name': pp.group(8), 'record': pp.group(9),
                                 'era': pp.group(10)}}
        details[rec['slug']] = det

    # fill logos for teams that still lack one
    for t in teams:
        if not t.get('logo'):
            t['logo'] = logo_pool.get(t['full_name'])
    emit('teams.json', teams)

    # ---- upcoming games from league schedule pages --------------------------
    for league, cap_name in (('nfl', 'nfl-schedule'), ('mlb', 'mlb-schedule'),
                             ('college-football', 'cfb-schedule')):
        g = grid(cap_name)
        for tbl in g.tables:
            if len(tbl) < 2:
                continue
            header = tbl.row(0)
            if 'MATCHUP' not in header or 'STATUS' not in header:
                continue
            for r in range(1, len(tbl)):
                cells = tbl.rows[r]
                vals = tbl.row(r)
                links = [ln for c in cells for ln in c.links if BOX_URL_RE.match(ln[0])]
                if not links:
                    continue
                href = links[0][0]
                bm = BOX_URL_RE.match(href)
                slug = f'{bm.group(2)}-game-boxscore-{bm.group(3)}'
                if any(x['slug'] == slug for x in games):
                    continue
                loc = vals[4] if len(vals) > 4 else ''
                venue = city = None
                if ', ' in loc:
                    venue, city = loc.rsplit(', ', 1)[0], loc.rsplit(', ', 1)[1]
                games.append({
                    'league': league, 'slug': slug, 'game_id': bm.group(3),
                    'date': '', 'date_iso': None,
                    'away_team': None, 'home_team': None,
                    'status': 'scheduled', 'time': vals[3] if len(vals) > 3 else '',
                    'venue': venue, 'venue_city': city,
                    'odds_line': vals[5] if len(vals) > 5 else '',
                })

    games.sort(key=lambda x: (x['league'], x['date_iso'] or '9999', x['game_id']))
    emit('games.json', games)
    emit('game_details.json', details)
    return games




# --------------------------------------------------------------------------
# Players: NFL/MLB rosters + stat leaders + player news from team pages
# --------------------------------------------------------------------------

PLAYER_RE = re.compile(r'^/(nfl|mlb|college-football)/([a-z0-9()-]+)-player$')


def build_players():
    players = []
    seen = set()
    for path in sorted(CAP.glob('roster-*.html')):
        stem = path.stem
        team_slug = stem.removesuffix('roster-') if stem.startswith('roster-') else None
        team_slug = stem[len('roster-'):] if stem.startswith('roster-') else None
        league = 'mlb' if (CAP / f'team-{team_slug}.meta.json').exists() and \
            f'"url": "https://www.foxsports.com/mlb/' in (CAP / f'team-{team_slug}.meta.json').read_text() else 'nfl'
        g = grid(stem)
        for tbl in g.tables:
            if len(tbl) < 2:
                continue
            header = tbl.row(0)
            if 'POS' not in header or 'AGE' not in header:
                continue
            group = header[0]
            for r in range(1, len(tbl)):
                cells = tbl.rows[r]
                vals = tbl.row(r)
                if len(vals) < 6 or not vals[0]:
                    continue
                name_num = vals[0]
                link = next((ln for ln in cells[0].links if PLAYER_RE.match(ln[0])), None)
                nm = re.match(r"([A-Za-z][A-Za-z .\\'-]+?)#?(\d{0,3})$", name_num.strip())
                if not nm:
                    continue
                slug = link[0].rsplit('/', 1)[1].removesuffix('-player') if link else \
                    re.sub(r'[^a-z0-9]+', '-', nm.group(1).strip().lower()).strip('-')
                key = (league, slug)
                if key in seen:
                    continue
                seen.add(key)
                players.append({
                    'league': league, 'team': team_slug, 'slug': slug,
                    'name': nm.group(1).strip(), 'number': nm.group(2),
                    'group': group, 'pos': vals[1], 'age': vals[2],
                    'height': vals[3], 'weight': vals[4], 'college': vals[5],
                })
    emit('players.json', players)
    return players


def build_stat_leaders():
    out = {}
    for league, cap_name in (('nfl', 'nfl-players'), ('mlb', 'mlb-players'),
                             ('college-football', 'cfb-players')):
        text = plain_text(read(cap_name))
        rows = []
        section = re.search(r'PLAYER STATS\|(.*?)(?:TEAM STATS|Top Leagues|$)', text)
        block = '|' + section.group(1) if section else ''
        # 'Passing Yards|Bryce Young|CAR|939|PYDS|Passing Touchdowns|...'
        pm = re.findall(
            r'(?<=\|)([A-Za-z][A-Za-z /&-]{2,28})\|([A-Za-z][A-Za-z .\'-]{2,32})\|'
            r'([A-Z]{2,4})\|([0-9.,]+)\|([A-Z][-A-Z /&]{1,14})\|', block)
        for label, player, team, value, abbrev in pm:
            rows.append({'league': league, 'label': label.strip(),
                         'player': player.strip(), 'team_abbr': team,
                         'value': value, 'stat': abbrev.strip()})
        out[league] = rows
        # team stats: 'Passing Yards / Game|Panthers|295.7|PYDS/G|...'
        tm = re.findall(
            r'(?<=\|)([A-Za-z][A-Za-z /&-]{2,28})\|([A-Za-z][A-Za-z .\'-]{2,28})\|'
            r'([0-9.,]+)\|([A-Z][-A-Z /&]{1,14})\|',
            (re.search(r'TEAM STATS\|(.*?)(?:Top Leagues|$)', text).group(1)
             if re.search(r'TEAM STATS\|', text) else ''))
        out[league + '_teams'] = [{'label': l.strip(), 'team': t.strip(),
                                   'value': v, 'stat': a.strip()}
                                  for l, t, v, a in tm]
    emit('player_stats.json', out)
    return out


def build_team_pages():
    """Team page headers: record, standing note, next game + player news."""
    info = {}
    news = []
    for path in sorted(CAP.glob('team-*.html')):
        stem = path.stem
        team_slug = stem[len('team-'):]
        m = json.loads((CAP / f'{stem}.meta.json').read_text())
        url = m.get('url', '')
        league = url.split('.com/')[1].split('/')[0]
        text = plain_text(read(stem))
        tokens = text.split('|')
        rec = {'slug': team_slug, 'league': league}
        # locate the "Next Game ..." token and read the header around it
        idx = next((k for k, tok in enumerate(tokens)
                    if tok.strip().startswith('Next Game')), None)
        if idx is not None:
            parts = [t.strip() for t in tokens[idx:idx + 3]]
            ng = re.match(
                r'Next Game\s+(vs|at)\s+(.+?)\s*·\s*([A-Za-z]{3} \d{1,2}|Today|Tomorrow)?'
                r'\s*([0-9]{1,2}:[0-9]{2}(?:AM|PM)?)?', parts[0])
            if ng:
                rec['next_homeaway'] = ng.group(1)
                rec['next_opponent'] = ng.group(2).strip()
                if ng.group(3):
                    rec['next_day'] = ng.group(3).strip()
                if ng.group(4):
                    rec['next_time'] = ng.group(4)
            odds = re.match(
                r'([A-Z]{2,4})\s*([-+][0-9.]+)\s*TOTAL\s*([0-9.]+)',
                parts[1] if len(parts) > 1 else '')
            if odds:
                rec['next_spread'] = f'{odds.group(1)} {odds.group(2)}'
                rec['next_total'] = odds.group(3)
            # scan back: record/note (duplicated) then the name, maybe a rank
            back = [t.strip() for t in tokens[max(0, idx - 4):idx]]
            rank = None
            if back and re.fullmatch(r'\d{1,2}', back[0]):
                rank = back.pop(0)
            name_tok = None
            recs = []
            for t in back:
                if re.fullmatch(r'\d+-\d+(\s*·\s*[^·]+)?', t):
                    recs.append(t)
                elif t and name_tok is None and t.upper() == t and len(t) > 2:
                    name_tok = t
            if recs:
                first = recs[0]
                rec['record'] = first.split('·')[0].strip()
                rec['note'] = first.split('·')[1].strip() if '·' in first else ''
            if name_tok:
                rec['name'] = name_tok.title()
            if rank:
                rec['rank'] = rank
        info[team_slug] = rec
        # player news: 'Name - Headline|story text|Impact|impact text|TIME AGO|•|SOURCE'
        nx = text.find('PLAYER NEWS', text.find('Built on'))
        if nx < 0:
            continue
        block = text[nx:nx + 16000]
        nm = re.findall(
            r"(?<=\|)([A-Za-z][A-Za-z .\'-]{3,40}?) - ([A-Z][^|]{10,140}?)\|"
            r"([^|]{10,400}?)(?:\|Impact\|([^|]{10,600}?))?\|"
            r"(\d+ (?:MINUTE|HOUR|DAY|WEEK)S? AGO|[A-Z]{3,9} \d{1,2})\|•\|([^|]{2,40})\|",
            block)
        for name, headline, story, impact, ago, source in nm:
            if re.search(r'\d', name) or len(name.strip().split()) < 2:
                continue
            news.append({
                'league': league, 'team': team_slug, 'player': name.strip(),
                'headline': headline.strip(), 'story': story.strip(),
                'impact': (impact or '').strip(),
                'time_ago': ago.strip(), 'source': source.strip(),
            })
    # richer display names from the captured team pages win over the poll
    # display names ('Texas' -> 'Texas Longhorns')
    teams = json.load(open(OUT / 'teams.json'))
    by_slug = {t['slug']: t for t in teams}
    for slug, rec in info.items():
        page_name = rec.get('name')
        if (page_name and slug in by_slug
                and len(page_name.split()) > len(by_slug[slug]['full_name'].split())):
            by_slug[slug]['full_name'] = page_name.replace('(Fl)', '(FL)')
    emit('teams.json', teams)
    emit('team_info.json', info)
    emit('player_news.json', news)
    return info, news


# --------------------------------------------------------------------------
# Stories: cards from the news hubs + full bodies from the story pages
# --------------------------------------------------------------------------

_STORY_CARDS = {}


def _harvest_story_cards():
    """Cards on the hub pages: 'Title|Dek|TIME AGO|•|SOURCE', indexed by
    normalized title prefix."""
    if _STORY_CARDS:
        return
    for hub in ('stories-hub', 'nfl-news', 'mlb-news', 'cfb-news', 'betting-hub',
                'home', 'nfl-home', 'mlb-home', 'cfb-home', 'betting-nfl',
                'betting-mlb'):
        try:
            t = plain_text(read(hub))
        except FileNotFoundError:
            continue
        for m in re.finditer(
                r'\|([^|]{14,200}?)\|([^|]{20,300}?)\|'
                r'(\d+ (?:MINUTE|HOUR|DAY|WEEK)S? AGO|[A-Z]{3,9} \d{1,2})\|•\|'
                r'([^|]{2,40})\|', t):
            title, dek, ago, source = m.groups()
            key = re.sub(r'[^a-z0-9]', '', title.strip()[:40].lower())
            _STORY_CARDS.setdefault(key, (ago.strip(), source.strip()))


def build_stories():
    _harvest_story_cards()
    """Story set: every /stories/<league>/<slug> link on the tracked hub
    pages; title/dek/image/published from each story page's own metadata."""
    links = []
    seen = set()
    for hub in ('stories-hub', 'nfl-news', 'mlb-news', 'cfb-news', 'betting-hub',
                'home', 'nfl-home', 'mlb-home', 'cfb-home', 'betting-nfl',
                'betting-mlb', 'live', 'shows-hub', 'personalities-hub'):
        g = grid(hub)
        for href, _ in g.anchors:
            m = re.match(r'^/stories/(nfl|mlb|college-football|betting)/([a-z0-9-]+)$', href)
            if m and (m.group(1), m.group(2)) not in seen:
                seen.add((m.group(1), m.group(2)))
                links.append((m.group(1), m.group(2)))
    stories = []
    for league, slug in links:
        cap = f'story-{slug}'
        if not (CAP / f'{cap}.html').exists():
            continue
        h = read(cap)
        t = plain_text(h)
        title_m = re.search(r'<meta property="og:title" content="([^"]+)"', h)
        dek_m = re.search(r'<meta name="description" content="([^"]+)"', h)
        img_m = re.search(r'<meta property="og:image" content="([^"]+)"', h)
        pub_m = re.search(r'"datePublished":"([^"]+)"', h)
        author_m = re.search(r'"author":\[\{[^}]*"name":"([^"]+)"', h)
        # card near the top: '...|Title|dek-ish...|X HOURS AGO|•|SOURCE|'
        card = re.search(
            r'\|([A-Z][^|]{14,200}?)\|([A-Z][^|]{20,260}?)\|'
            r'(\d+ (?:MINUTE|HOUR|DAY|WEEK)S? AGO|[A-Z]{3,9} \d{1,2})\|•\|([^|]{2,40})\|',
            t[:12000])
        title = htmllib.unescape(title_m.group(1)) if title_m else \
            (card.group(1) if card else slug.replace('-', ' ').title())
        rec = {
            'league': league, 'slug': slug, 'title': title,
            'dek': htmllib.unescape(dek_m.group(1)) if dek_m else \
                (card.group(2) if card else None),
            'image': img_m.group(1) if img_m else None,
            'published': pub_m.group(1) if pub_m else None,
            'author': htmllib.unescape(author_m.group(1)) if author_m else None,
            'time_ago': card.group(3) if card else None,
            'source': card.group(4).strip() if card else None,
        }
        # card metadata (time_ago + source) from the hub pages, matched
        # by normalized title prefix (hub anchor text is truncated)
        if rec.get('time_ago') is None:
            full = re.sub(r'[^a-z0-9]', '', rec['title'].lower())
            hit = _STORY_CARDS.get(full)
            if hit is None:
                for k, v in _STORY_CARDS.items():
                    if full.startswith(k) or k.startswith(full[:48]):
                        hit = v
                        break
            if hit:
                rec['time_ago'], rec['source'] = hit
        # body: everything between the share bar and the trailing share /
        # recommended block, minus the author byline tokens
        marker = 'share|facebook|x|reddit|link|'
        i = t.find(marker)
        if i < 0:
            i = t.find(title[:40])
            start = i + len(title[:40]) if i >= 0 else 0
        else:
            start = i + len(marker)
        end_candidates = [pos for pos in
                           (t.find('|share|', start + 20),
                            t.find('Top Leagues', start),
                            t.find('recommended|', start + 20)) if pos > 0]
        end = min(end_candidates) if end_candidates else len(t)
        paras = [p.strip() for p in t[start:end].split('|') if p.strip()]
        # drop a leading "Author|Role|" byline pair
        if paras:
            role_words = ('Writer', 'Reporter', 'Analyst', 'Correspondent',
                          'Staff', 'Columnist', 'Host')
            if len(paras) > 1 and len(paras[0]) < 40 and \
                    any(paras[1].endswith(w) for w in role_words):
                paras = paras[2:]
        paras = [p for p in paras if len(p) > 10][:260]
        rec['body'] = paras
        stories.append(rec)
    emit('stories.json', stories)
    return stories


seen_story = set()


# --------------------------------------------------------------------------
# Shows + personalities + home + nascar + ufc + super6
# --------------------------------------------------------------------------

def build_shows():
    shows = []
    g = grid('shows-hub')
    h = read('shows-hub')
    link_for = {}
    for href, text in g.anchors:
        m = re.match(r'^/shows/([a-z0-9-]+)$', href)
        if m:
            link_for[m.group(1)] = text.strip()
    # show artwork: anchors wrapping imgs
    art = {}
    for m in re.finditer(r'<a[^>]*href="/shows/([a-z0-9-]+)"[^>]*>(.*?)</a>', h, re.S):
        slug, body = m.group(1), m.group(2)
        im = re.search(r'<img[^>]+src="([^"]+)"', body)
        if im and slug not in art:
            art[slug] = im.group(1)
    for slug in link_for:
        cap = f'show-{slug}'
        if not (CAP / f'{cap}.html').exists():
            continue
        t = plain_text(read(cap))
        nm = re.search(r'Built on\|([A-Z][A-Z0-9 &\'()\-.]{3,60}?)\|SHOWS\|', t)
        title = nm.group(1).title() if nm else link_for[slug]
        raw = read(cap)
        art_m = re.search(
            r'<img[^>]+alt="' + re.escape(title.upper()) + r'"[^>]*src="([^"]+)"', raw) or \
            re.search(
            r'<img[^>]+src="([^"]+)"[^>]*alt="' + re.escape(title.upper()) + r'"', raw)
        art_url = art_m.group(1) if art_m else art.get(slug)
        # episode thumbnails: img alt == episode title
        thumb_for = {}
        for im in re.finditer(r'<img[^>]+>', raw):
            tag = im.group(0)
            alt_m = re.search(r'alt="([^"]{12,160})"', tag)
            src_m = re.search(r'src="([^"]+)"', tag)
            if alt_m and src_m and ('a57.foxsports.com' in src_m.group(1)):
                thumb_for.setdefault(htmllib.unescape(alt_m.group(1)).strip(),
                                     src_m.group(1))
        episodes = []
        em = re.findall(
            r'\|([^|]{12,150}?)\|(\d+ (?:MINUTE|HOUR|DAY|WEEK)S? AGO|[A-Z]{3,9} \d{1,2})\|•\|'
            r'([^|]{2,40})\|', t)
        ep_links = []
        g2 = grid(cap)
        for href, text in g2.anchors:
            if re.match(r'^/watch/', href) and text.strip():
                ep_links.append(text.strip())
        for (ep_title, ago, source) in em:
            episodes.append({'title': ep_title.strip(), 'time_ago': ago.strip(),
                             'source': source.strip(),
                             'thumb': thumb_for.get(ep_title.strip())})
        # dedupe episode titles
        seen_titles = set()
        eps = []
        for e in episodes:
            if e['title'] not in seen_titles:
                seen_titles.add(e['title'])
                eps.append(e)
        shows.append({'slug': slug, 'title': title or slug.replace('-', ' ').title(),
                      'art': art_url, 'episodes': eps[:16]})
    emit('shows.json', shows)
    return shows


def build_personalities():
    people = []
    g = grid('personalities-hub')
    h = read('personalities-hub')
    link_for = {}
    for href, text in g.anchors:
        m = re.match(r'^/personalities/([a-z0-9-]+)$', href)
        if m:
            link_for[m.group(1)] = text.strip()
    art = {}
    for m in re.finditer(r'<a[^>]*href="/personalities/([a-z0-9-]+)"[^>]*>(.*?)</a>', h, re.S):
        slug, body = m.group(1), m.group(2)
        im = re.search(r'<img[^>]+src="([^"]+)"', body)
        if im and slug not in art:
            art[slug] = im.group(1)
    for slug in link_for:
        cap = f'person-{slug}'
        if not (CAP / f'{cap}.html').exists():
            continue
        t = plain_text(read(cap))
        raw = read(cap)
        og = re.search(r'property="og:title" content="([^"]+)"', raw[:60000])
        person_name, person_role = link_for[slug], ''
        if og:
            label = htmllib.unescape(og.group(1))
            label = re.sub(r'\s*Videos? (& |and )?Stories?\s*$', '', label).strip()
            label = re.sub(r'\s*on FOX Sports\s*$', '', label).strip()
            mrole = re.match(r"([A-Za-z .\'-]{2,40}?)\s*-\s*([A-Za-z0-9 ,&/\'-]{2,40})$",
                             label)
            if mrole:
                person_name, person_role = mrole.group(1).strip(), mrole.group(2).strip()
            else:
                person_name = label
        art_m = None
        if person_name:
            art_m = re.search(
                r'<img[^>]+alt="' + re.escape(person_name.upper()) +
                r'"[^>]*src="(https://[^"]+)"', raw) or re.search(
                r'<img[^>]+src="(https://[^"]+)"[^>]*alt="' +
                re.escape(person_name.upper()) + r'"', raw)
        if not art_m:
            art_m = re.search(
                r'<img[^>]+alt="([^"]{3,60} Logo)"[^>]*src="(https://[^"]+)"', raw)
        art_url = None
        if art_m:
            art_url = art_m.group(art_m.lastindex) if art_m.lastindex == 2 else art_m.group(1)
            if not str(art_url).startswith('http'):
                art_url = art_m.group(1)
        thumb_for = {}
        for im in re.finditer(r'<img[^>]+>', raw):
            tag = im.group(0)
            alt_m = re.search(r'alt="([^"]{12,160})"', tag)
            src_m = re.search(r'src="([^"]+)"', tag)
            if alt_m and src_m and ('a57.foxsports.com' in src_m.group(1)):
                thumb_for.setdefault(htmllib.unescape(alt_m.group(1)).strip(),
                                     src_m.group(1))
        vids = []
        vm = re.findall(
            r'\|([^|]{12,150}?)\|(\d+ (?:MINUTE|HOUR|DAY|WEEK)S? AGO|[A-Z]{3,9} \d{1,2})\|•\|'
            r'([^|]{2,40})\|', t)
        seen_titles = set()
        for title, ago, source in vm:
            if title.strip() not in seen_titles:
                seen_titles.add(title.strip())
                vids.append({'title': title.strip(), 'time_ago': ago.strip(),
                             'source': source.strip(),
                             'thumb': thumb_for.get(title.strip())})
        people.append({'slug': slug, 'name': person_name,
                       'role': person_role,
                       'art': art_url, 'videos': vids[:12]})
    emit('personalities.json', people)
    return people


def build_home():
    text = plain_text(read('home'))
    # scorestrip: 'MLB GM 2 ATL LEADS 1-0|PHI|ATL|6:00PM|NBC|PHI -119|ATL -102|...'
    strip = []
    sm = re.findall(
        r'\|([A-Z]{2,6}(?: GM \d+)?(?: [A-Z]{2,4} LEADS [0-9]-[0-9])?)\|'
        r'([A-Z]{2,4})\|([A-Z]{2,4})\|([^|]{4,22}?)\|'
        r'(?:(?:OCT \d{1,2} )?(\d{1,2}:\d{2}(?:AM|PM))\|)?([A-Z]{2,5})\|'
        r'([A-Z]{2,4} [-+][0-9.]+)\|([A-Z]{2,4} [-+][0-9.]+)\|', text)
    for label, away, home, when, tm, net, o1, o2 in sm:
        strip.append({'label': label.strip(), 'away': away, 'home': home,
                      'when': when or when.strip(), 'network': net,
                      'odds': [o1, o2]})
    # featured stories
    featured = []
    g = grid('home')
    for href, text2 in g.anchors:
        m = re.match(r'^/stories/(nfl|mlb|college-football)/([a-z0-9-]+)$', href)
        if m and (m.group(1), m.group(2)) not in seen_home:
            seen_home.add((m.group(1), m.group(2)))
            featured.append({'league': m.group(1), 'slug': m.group(2)})
    # live tiles
    live = []
    lt = plain_text(read('live'))
    lm = re.findall(r'\|([^|]{10,120}?)\|Watch\|', lt)
    live = [t.strip() for t in lm if t.strip()][:20]
    # recent moments from home text
    moments = []
    i = text.find('LIVE NOW')
    if i >= 0:
        block = text[i:i + 3000]
        moments = [m.strip() for m in re.findall(r'\|([^|]{12,150}?)\|', block)
                   if m.strip() and 'LIVE NOW' not in m and 'RECENT MOMENTS' not in m][:24]
    emit('home.json', {'scorestrip': strip, 'featured': featured,
                       'live_tiles': live, 'moments': moments})
    return strip


seen_home = set()


def build_nascar_ufc():
    g = grid('nascar-cup-standings')
    drivers = []
    for tbl in g.tables:
        if len(tbl) < 2 or tbl.row(0)[:1] != ['DRIVER']:
            continue
        for r in range(1, len(tbl)):
            vals = tbl.row(r)
            if len(vals) < 6:
                continue
            drivers.append({'rank': vals[0], 'driver': vals[1],
                            'points': vals[2], 'back': vals[3],
                            'starts': vals[5], 'wins': vals[6],
                            'top5': vals[7], 'top10': vals[8], 'dnf': vals[9],
                            'stage_wins': vals[10], 'laps_led': vals[11]})
        break
    text = plain_text(read('scores-nascar'))
    races = []
    rm = re.findall(
        r'\|((?:SUN|SAT|SUN|MON), [A-Z]{3} \d{1,2})\|([^|]{4,60}?)\|([^|]{4,50}?)\|'
        r'([^|]{3,40}?)\|(\d{1,2}:\d{2}(?:AM|PM))\|([A-Z]{2,5})\|', text)
    for when, name, track, city, tm, net in rm:
        races.append({'when': when.strip(), 'name': name.strip(), 'track': track.strip(),
                      'city': city.strip(), 'time': tm, 'network': net})
    emit('nascar.json', {'standings': drivers, 'races': races})

    text = plain_text(read('scores-ufc'))
    events = []
    um = re.findall(
        r'\|((?:TUE|WED|THU|FRI|SAT|SUN), [A-Z]{3} \d{1,2})\|([^|]{8,90}?)\|'
        r'([^|]{3,50}?)\|([^|]{3,40}?)\|(?:FINAL\|)?'
        r'([A-Z]\. [A-Z\']{2,20})\|([WL])\|([A-Z]\. [A-Z\']{2,20})\|([WL])\|', text)
    for when, name, venue, city, f1, r1, f2, r2 in um:
        city_s = re.sub(r'(, [A-Z]{2})\1$', r'\1', city.strip())
        events.append({'when': when.strip(), 'name': name.strip(), 'venue': venue.strip(),
                       'city': city_s,
                       'fighter1': f1.strip(), 'result1': r1,
                       'fighter2': f2.strip(), 'result2': r2})
    emit('ufc.json', events)


def build_super6():
    text = plain_text(read('super6'))
    rec = {}
    pm = re.search(r'PRIZE TIERS\|([^|]{10,200}?)\|', text)
    if pm:
        rec['prize_tiers'] = pm.group(1).strip()
    how = re.findall(r'\|([^|]{20,220}?)\|', _section(text, 'HOW TO PLAY', 'DOWNLOAD'))
    rec['how_to_play'] = [h.strip() for h in how if h.strip()][:6]
    rec['status'] = 'No active games. Check back soon for updates.' \
        if 'No active games' in text else 'Active'
    emit('super6.json', rec)
    return rec


if __name__ == '__main__':
    print('== teams')
    build_teams()
    print('== standings')
    build_standings()
    print('== games')
    build_games()
    print('== players')
    build_players()
    print('== stat leaders')
    build_stat_leaders()
    print('== team pages')
    build_team_pages()
    print('== stories')
    build_stories()
    print('== shows')
    build_shows()
    print('== personalities')
    build_personalities()
    print('== home')
    build_home()
    print('== nascar + ufc')
    build_nascar_ufc()
    print('== super6')
    build_super6()
