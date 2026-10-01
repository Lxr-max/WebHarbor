#!/usr/bin/env python3
"""Honest HTTP walkthrough of every dblp mirror task.

Counting convention (aligned with the independent review's honest-step
measurement; the r1 URL-direct counting is gone):

  * reading a value off the current page is FREE — only the actions the
    task text requires are performed and counted;
  * a search-box submission = fill (1) + submit (1) = 2 steps, landing on
    the COMBINED results (the header form submits there from every page
    except the kind search pages, which submit back to their own kind);
  * reaching a kind page's features from the combined results costs the
    section's "all N matches" click = 1 step; the header search-kinds
    nav link to a kind search page = 1 step;
  * link clicks / facet clicks / pagination / back / download = 1 step;
  * a form submission = 1 + 1 per filled field (login = open the login
    page 1 + submit 3; register = login page 1 + register link 1 +
    submit 4);
  * actions the task text does not require are never performed and never
    counted (no tail padding).

Every reported fact is asserted to be present on the page it is read
from, so a passing run doubles as a solvability proof. Run with the
site's base URL as argv[1]; results land in argv[2] as JSON.
"""
import http.cookiejar
import json
import re
import sys
import urllib.parse
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:45191"
REG = {"name": "Walker Dev", "email": "walker.dev.dblp@test.com",
       "password": "Walk3rDev!"}
DEMOS = {9: "alice.j@test.com", 10: "bob.c@test.com", 11: "dana.k@test.com",
         12: "carol.d@test.com", 13: "dana.k@test.com", 14: "alice.j@test.com",
         18: "bob.c@test.com"}
ACCOUNT_PREFIXES = ("/account", "/account/")


class Browser:
    """Minimal headless browser: cookie jar + CSRF form submits."""

    def __init__(self):
        self.cj = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.cj))
        self.steps = 0
        self.facts = {}
        self.log = []
        self.on_account = False

    def _mark(self, path):
        self.on_account = path.startswith(ACCOUNT_PREFIXES)

    def get(self, path, count=1, note=""):
        path = path.replace("&amp;", "&")
        self.steps += count
        self.log.append(f"{self.steps:3d} GET  {path} {note}")
        with self.opener.open(BASE + path, timeout=60) as r:
            body = r.read().decode("utf-8", "replace")
        self._mark(path)
        return body

    def post(self, source_path, action_path, fields, extra_fills, note=""):
        """Submit a form: +1 per filled field +1 submit."""
        page = self.get(source_path, count=0)
        m = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', page)
        assert m, f"no csrf token on {source_path}"
        data = {"csrf_token": m.group(1)}
        data.update(fields)
        self.steps += extra_fills + 1
        self.log.append(f"{self.steps:3d} POST {action_path} {note}")
        req = urllib.request.Request(
            BASE + action_path, data=urllib.parse.urlencode(data).encode())
        with self.opener.open(req, timeout=60) as r:
            body = r.read().decode("utf-8", "replace")
            url = r.geturl()
        self._mark(url[len(BASE):] if url.startswith(BASE) else url)
        return body

    # ---- honest-counting primitives (mirror walk_lib.py) ----------------

    def search(self, q, note=""):
        """Search-box submission: fill + submit = 2, combined results."""
        return self.get(f"/search?q={urllib.parse.quote(q)}", count=2,
                        note=f"search {q!r} {note}")

    def open_kind(self, kind, q, note=""):
        """The section's 'all N matches' click from the combined page."""
        return self.get(f"/search/{kind}?q={urllib.parse.quote(q)}", count=1,
                        note=note or f"open all {kind} matches")

    def nav_search_kind(self, kind, note=""):
        """Header search-kinds nav link to a kind search page."""
        return self.get(f"/search/{kind}", count=1, note=note)

    def open_account_page(self, path, note=""):
        """Account-nav link: dashboard click first when off an account page."""
        if not self.on_account:
            self.get("/account", count=1, note="open the account dashboard")
        return self.get(path, count=1, note=note or f"open {path}")

    def log_out(self):
        if not self.on_account:
            self.get("/account", count=1, note="open the account dashboard")
        self.post("/account", "/authn/logout", {}, 0, note="log out")

    def login(self, email, password="TestPass123!"):
        self.get("/authn/login", count=1, note="open the login page")
        p = self.post("/authn/login", "/authn/login",
                      {"email": email, "password": password}, 2,
                      note=f"log in {email}")
        must("Invalid credentials" not in p, f"login failed for {email}")
        return p

    def register(self):
        self.get("/authn/login", count=1, note="open the login page")
        self.get("/authn/register", count=1, note="open the registration page")
        p = self.post("/authn/register", "/authn/register",
                      {"display_name": REG["name"], "email": REG["email"],
                       "password": REG["password"]}, 3,
                      note="register account")
        must("already registered" not in p, "registration failed")
        return p


def must(cond, msg):
    if not cond:
        raise AssertionError(msg)


def nfound(body):
    m = re.search(r"found ([\d,]+) matches", body)
    return int(m.group(1).replace(",", "")) if m else None


def combined_count(body, kind):
    sec = {"publ": "publ-results", "author": "author-results",
           "venue": "venue-results"}[kind]
    m = re.search(rf'id="{sec}"[\s\S]*?(?:All|found) ([\d,]+) matches', body)
    return int(m.group(1).replace(",", "")) if m else None


def first_record_key(p, nth=0):
    return re.findall(r'class="entry [^"]*" id="((?:conf|journals)/[^"]+)"',
                      p)[nth]


def entry_titles(p, n=1):
    return re.findall(r'class="title">([^<]+)<', p)[:n]


def first_pid_link(p):
    return re.search(r'href="(/pid/[^"]+\.html)"', p).group(1)


def first_venue_link(p):
    return re.search(r'href="(/db/[^"]+/index.html)"', p).group(1)


def newest_edition_link(p):
    return re.search(r'<a href="(/db/[^"]+/[^"]+\.html)">', p).group(1)


def top_coauthor(p):
    m = re.search(r'href="(/pid/[^"]+\.html)\?view=joint"[^>]*>(\d+)</a>'
                  r'</span>\s*<a href="/pid/[^"]+\.html">([^<]+)</a>', p)
    return m


def coauthor_rows(p):
    return re.findall(r'<span class="count"><a[^>]*>(\d+)</a></span>\s*'
                      r'<a href="(/pid/[^"]+\.html)">([^<]+)</a>', p)


def pub_count_of(p):
    return re.search(r"(\d+) publications", p).group(1)


def affiliation_of(p):
    m = re.search(r"affiliation:</em> ([^<]+)<", p)
    return m.group(1) if m else None


def title_of(p):
    return re.search(r"<h1>([^<]+)</h1>", p).group(1)


def record_meta(p, key):
    m = re.search(rf"<dt>{key}</dt><dd>([^<]+)</dd>", p)
    return m.group(1) if m else None


def record_ee_doi(p):
    """Reportable DOI: dblp shows it inside the electronic-edition link
    for records that have no doi field."""
    m = re.search(r'href="https://doi\.org/(10\.[^"]+)"', p)
    return m.group(1) if m else None


def edition_records(p):
    return re.search(r"<li><em>records:</em> (\d+)</li>", p).group(1)


def venue_records(p):
    return re.search(r"\((\d+) records in this mirror\)", p).group(1)


def edition_count(p):
    return len(re.findall(r'class="edition"', p))


def busiest_year(p):
    bars = re.findall(r'<span class="stat-year">(\d{4})</span>\s*'
                      r'<span class="stat-bar-track"><span class="stat-bar" '
                      r'data-count="(\d+)"', p)
    return max(bars, key=lambda x: int(x[1]))[0]


def frequent_authors(p):
    seg = re.search(r'frequent authors</b></p>\s*<ul class="options">(.*?)</ul>',
                    p, re.S).group(1)
    return re.findall(r'href="/pid/[^"]+">([^<]+)</a> \((\d+)\)', seg)


def year_facets(p):
    seg = re.search(r'refine-by year">[\s\S]*?<ul class="options">'
                    r'([\s\S]*?)</ul>', p).group(1)
    return sorted({int(y) for y in re.findall(r'year=(\d+)', seg)})


def venue_list_items(p):
    return re.findall(r'<li><a href="(/db/(?:conf|journals)/[^"]+)">'
                      r'([^<]+)</a>', p)


def watch_rows(p):
    authors = re.findall(r'id="watchlist-authors"[\s\S]*?</ul>', p)
    authors = re.findall(r'href="/pid/[^"]+">([^<]+)</a>', authors[0]) \
        if authors else []
    venues = re.findall(r'id="watchlist-venues"[\s\S]*?</ul>', p)
    venues = re.findall(r'href="/db/[^"]+">([^<]+)</a>', venues[0]) \
        if venues else []
    return authors, venues


def saved_collections(p):
    return [(m.group(1), m.group(2)) for m in re.finditer(
        r"<h2>([^<]+?) \((\d+)\s*records?\)</h2>", p)]


def saved_search_rows(p):
    return re.findall(r'<span class="query">([^<]+)</span>', p)


def history_rows(p):
    seg = re.search(r'history-list">([\s\S]*?)</ul>', p)
    if not seg:
        return []
    return re.findall(r"<li>\s*<a href=\"[^\"]*\">([^<]+)</a>",
                      seg.group(1))


def note_line_of(p):
    m = re.search(r'class="note-line">([^<]+)<', p)
    return m.group(1) if m else None


def venue_info(p, label):
    m = re.search(rf"{label}:</em>\s*([^<]+)", p)
    return m.group(1) if m else None


def entry_authors(p):
    return re.findall(r'href="/pid/[^"]+">([^<]+)</a>', p)


def profile_field(p, name):
    m = re.search(rf'name="{name}"[\s\S]*?value="([^"]*)"', p)
    return m.group(1) if m else None


def save_paper(b, source, key, collection, note_txt=None, note=""):
    fields = {"key": key, "collection": collection, "next": source}
    if note_txt:
        fields["note"] = note_txt
    return b.post(source, "/account/papers/add", fields,
                  1 + (1 if note_txt else 0), note=note)


def open_entry(b, page, nth, note):
    key = first_record_key(page, nth)
    return key, b.get(f"/rec/{key}.html", count=1, note=note)


def open_entry_author(b, page, nth, note):
    seg = re.split(r'class="entry ', page)[nth + 1]
    pid = re.search(r'href="(/pid/[^"]+\.html)"', seg).group(1)
    return b.get(pid, count=1, note=note)


def entry_venue_href(page, nth=0):
    seg = re.split(r'class="entry ', page)[nth + 1]
    return re.search(r'href="(/db/[^"]+/index.html)"', seg).group(1)


# ---------------------------------------------------------------------------


def task0(b):
    p = b.search("graph neural network", "search 'graph neural network'")
    p = b.open_kind("publ", "graph neural network", "open publ search results")
    total = nfound(p)
    must(total and total > 100, "t0: gnn count")
    newest = max(year_facets(p))
    p = b.get(re.search(rf'href="([^"]*year={newest}[^"]*)"', p).group(1),
              count=1, note=f"refine by newest year ({newest})")
    ycount = nfound(p)
    must(ycount and 0 < ycount < total, "t0: year refined")
    year_first = entry_titles(p)[0]
    p = b.get(re.search(r'href="([^"]*)"[^>]*>clear year filter', p).group(1),
              count=1, note="clear year filter")
    p = b.get("/search/publ?q=graph+neural+network&h=30&f=30", count=1,
              note="open results page two")
    page2_title = entry_titles(p)[0]
    page2_venue = entry_venue_href(p)
    key, p = open_entry(b, p, 0, "open that record")
    rtype, mdate = record_meta(p, "type"), record_meta(p, "mdate")
    must(rtype and mdate, "t0: type and mdate")
    bib = b.get(f"/rec/{key}.bib", count=1, note="download BibTeX")
    etype = re.match(r"@(\w+)\{", bib).group(1)
    ven = first_venue_link(p)
    p = b.get(ven, count=1, note="open its venue")
    ven_records = venue_records(p)
    ed = newest_edition_link(p)
    p = b.get(ed, count=1, note="open newest edition")
    ed_title, ed_first = title_of(p), entry_titles(p)[0]
    p = b.search("graph$", "rerun exact-word 'graph'")
    exact = combined_count(p, "publ")
    must(exact and exact > 0, "t0: exact count")
    pid = first_pid_link(re.split(r'id="publ-results"', p)[1])
    p = b.get(pid, count=1, note="open first hit's first author")
    author_pubs = pub_count_of(p)
    author_best = busiest_year(p)
    ven2 = entry_venue_href(p)
    p = b.get(ven2, count=1, note="open newest pub's venue")
    pub_ven_records = venue_records(p)
    ed2 = newest_edition_link(p)
    p = b.get(ed2, count=1, note="open venue's newest edition")
    b.facts["task0"] = {
        "gnn_count": total, "year": newest, "year_count": ycount,
        "year_first_title": year_first, "page2_first_title": page2_title,
        "page2_first_venue": page2_venue, "record_type": rtype,
        "record_mdate": mdate, "bibtex_entry_type": etype,
        "venue_records": ven_records, "edition_title": ed_title,
        "edition_first_title": ed_first, "exact_count": exact,
        "author_pubs": author_pubs, "author_busiest_year": author_best,
        "pub_venue_records": pub_ven_records,
        "pub_venue_edition_records": edition_records(p),
    }


def task1(b):
    p = b.search("jiawei han", "author-search 'Jiawei Han'")
    n = combined_count(p, "author")
    must(n == 2, "t1: two profiles")
    p = b.get("/pid/h/JiaweiHan.html", count=1, note="open the UIUC professor")
    name, aff = title_of(p), affiliation_of(p)
    must(aff and "Illinois" in aff, "t1: UIUC affiliation")
    award = re.search(r"award[^<]*:</em> ([^<]+)<", p)
    npubs, best = pub_count_of(p), busiest_year(p)
    hom = re.search(r'id="homonyms"[\s\S]*?href="(/pid/[^"]+\.html)"', p)
    must(hom, "t1: namesake listed")
    p = b.get(hom.group(1), count=1, note="open the namesake")
    hom_pubs = pub_count_of(p)
    hom_co = top_coauthor(p)
    must(hom_co, "t1: namesake coauthor")
    p = b.get("/pid/h/JiaweiHan.html", count=1, note="return to the professor")
    top = top_coauthor(p)
    must(top, "t1: top coauthor")
    p = b.get(top.group(1), count=1, note="open the professor's top coauthor")
    top2 = top_coauthor(p)
    must(top2, "t1: coauthor's own top coauthor")
    p = b.get(top2.group(1), count=1,
              note="open that coauthor's own top coauthor")
    b.nav_search_kind("author", "open the author search page")
    p = b.search("jiawei$", "rerun exact-word 'jiawei$' on the author page")
    jn = nfound(p)
    must(jn and jn > 50, "t1: jiawei$ matches")
    p = b.get("/pid/h/JiaweiHan.html", count=1,
              note="reopen the professor from the results")
    must(title_of(p).startswith("Jiawei Han 0001"), "t1: reopened professor")
    key, p = open_entry(b, p, 0, "open his newest publication")
    newest_title, newest_venue = title_of(p), record_meta(p, "venue")
    ven = first_venue_link(p)
    p = b.get(ven, count=1, note="open that venue")
    ven_records, ven_best = venue_records(p), busiest_year(p)
    ed = newest_edition_link(p)
    p = b.get(ed, count=1, note="open its newest edition")
    ed_title, ed_records = title_of(p), edition_records(p)
    ed_first = entry_titles(p)[0]
    p = open_entry_author(b, p, 0, "open the first record's first author")
    b.facts["task1"] = {
        "profile_matches": n, "prof_name": name, "prof_affiliation": aff,
        "prof_award": award.group(1) if award else None, "prof_pubs": npubs,
        "prof_busiest_year": best, "homonym_pubs": hom_pubs,
        "homonym_top_coauthor": hom_co.group(3),
        "top_coauthor": top.group(3), "top_coauthor_joint": top.group(2),
        "co_top_coauthor": top2.group(3), "jiawei_exact_matches": jn,
        "newest_title": newest_title, "newest_venue": newest_venue,
        "venue_records": ven_records, "venue_busiest_year": ven_best,
        "ed_title": ed_title,
        "ed_records": ed_records, "ed_first_title": ed_first,
        "first_author_pubs": pub_count_of(p),
    }


def task2(b):
    p = b.search("sigmod", "combined search 'sigmod'")
    na, nv, np_ = (combined_count(p, "author"), combined_count(p, "venue"),
                   combined_count(p, "publ"))
    must(np_ > 700 and nv == 1 and na == 0, "t2: section counts")
    p = open_entry_author(b, re.split(r'id="publ-results"', p)[1], 0,
                          "open the first publication hit's first author")
    author_pubs = pub_count_of(p)
    author_newest = entry_titles(p)[0]
    p = b.search("sigmod", "search venues for 'sigmod'")
    p = b.get("/db/conf/sigmod/index.html", count=1,
              note="open the ACM SIGMOD Conference")
    nl, sigmod_records = note_line_of(p), venue_records(p)
    sigmod_best = busiest_year(p)
    fa = frequent_authors(p)[0]
    ed = newest_edition_link(p)
    p = b.get(ed, count=1, note="open the newest edition")
    ed_title, ed_records = title_of(p), edition_records(p)
    editors = venue_info(p, "editors")
    key, p = open_entry(b, p, 0, "open its first record")
    rec_title, rec_pages = title_of(p), record_meta(p, "pages")
    rec_doi = record_ee_doi(p)
    must(rec_doi, "t2: ee DOI")
    bib = b.get(f"/rec/{key}.bib", count=1, note="download BibTeX")
    etype = re.match(r"@(\w+)\{", bib).group(1)
    p = b.get(first_pid_link(p), count=1, note="open its first author")
    rec_author_pubs = pub_count_of(p)
    top = top_coauthor(p)
    must(top, "t2: top coauthor")
    p = b.get(top.group(1), count=1, note="open their top coauthor")
    co_newest = entry_titles(p)[0]
    ven = entry_venue_href(p)
    p = b.get(ven, count=1,
              note="open the coauthor's newest publication's venue")
    co_ven_records = venue_records(p)
    ed2 = newest_edition_link(p)
    p = b.get(ed2, count=1, note="open its newest edition")
    co_ed_records = edition_records(p)
    p = b.search("sigmod year:2022", "search 'sigmod year:2022'")
    ycount = combined_count(p, "publ")
    yfirst = re.split(r'id="publ-results"', p)[1]
    yfirst = re.search(r'class="title">([^<]+)<', yfirst).group(1)
    b.facts["task2"] = {
        "author_matches": na, "venue_matches": nv, "publ_matches": np_,
        "author_pubs": author_pubs, "author_newest_title": author_newest,
        "note_line": nl, "sigmod_records": sigmod_records,
        "sigmod_busiest_year": sigmod_best,
        "top_frequent_author": fa[0], "top_frequent_count": fa[1],
        "ed_title": ed_title, "ed_editors": editors, "ed_records": ed_records,
        "record_title": rec_title, "record_pages": rec_pages,
        "record_ee_doi": rec_doi, "bibtex_entry_type": etype,
        "rec_author_pubs": rec_author_pubs,
        "rec_top_coauthor": top.group(3), "rec_top_joint": top.group(2),
        "co_newest_title": co_newest, "co_venue_records": co_ven_records,
        "co_venue_ed_records": co_ed_records,
        "year2022_count": ycount, "year2022_first_title": yfirst,
    }


def task3(b):
    p = b.get("/db/conf/", count=1, note="browse the conference list")
    confs = len(re.findall(r'<li><a href="/db/conf/[^"]+"', p))
    must(confs == 12, "t3: conference count")
    p = b.get("/db/conf/nips/index.html", count=1,
              note="open Conference on Neural Information Processing Systems")
    nips_records = venue_records(p)
    fa = frequent_authors(p)[0]
    must(int(fa[1]) > 20, "t3: top frequent author")
    ed = newest_edition_link(p)
    p = b.get(ed, count=1, note="open the newest edition")
    ed_title, ed_records = title_of(p), edition_records(p)
    key, p = open_entry(b, p, 0, "open its first paper")
    first_title = title_of(p)
    authors = entry_authors(p)
    first_venue = record_meta(p, "venue")
    bib = b.get(f"/rec/{key}.bib", count=1, note="download BibTeX")
    bibkey = re.match(r"@\w+\{(DBLP:[^,]+),", bib).group(1)
    p = b.get(first_pid_link(p), count=1, note="open the first author's profile")
    author_pubs = pub_count_of(p)
    top = top_coauthor(p)
    must(top, "t3: top coauthor")
    p = b.get(top.group(1), count=1, note="open their top coauthor")
    co_newest = entry_titles(p)[0]
    ven = entry_venue_href(p)
    p = b.get(ven, count=1,
              note="open that coauthor's newest publication's venue")
    co_ven_records = venue_records(p)
    ed2 = newest_edition_link(p)
    p = b.get(ed2, count=1, note="open its newest edition")
    co_ed_records = edition_records(p)
    p = b.search("attention venue:conf/nips", "search 'attention' in this venue")
    att = combined_count(p, "publ")
    must(att and att > 100, "t3: attention count")
    att_first = re.split(r'id="publ-results"', p)[1]
    att_first = re.search(r'class="title">([^<]+)<', att_first).group(1)
    p = b.open_kind("publ", "attention venue:conf/nips", "open all matches")
    p = b.get("/search/publ?q=attention+venue%3Aconf%2Fnips&h=30&f=30",
              count=1, note="open page two")
    att_p2 = entry_titles(p)[0]
    p = b.search("attention$", "rerun exact-word 'attention$'")
    att_exact = combined_count(p, "publ")
    must(att_exact and att_exact > 300, "t3: attention$ count")
    b.facts["task3"] = {
        "conference_venues": confs, "nips_records": nips_records,
        "top_frequent_author": fa[0], "top_frequent_count": fa[1],
        "ed_title": ed_title, "ed_records": ed_records,
        "first_paper_title": first_title, "first_paper_authors": authors,
        "first_paper_venue": first_venue, "bibtex_key": bibkey,
        "author_pubs": author_pubs, "top_coauthor": top.group(3),
        "top_coauthor_joint": top.group(2), "co_newest_title": co_newest,
        "co_venue_records": co_ven_records,
        "co_venue_ed_records": co_ed_records,
        "att_count": att, "att_first_title": att_first,
        "att_page2_first_title": att_p2, "att_exact_count": att_exact,
    }


def task4(b):
    p = b.get("/db/journals/", count=1, note="browse the journal list")
    journals = len(re.findall(r'<li><a href="/db/journals/[^"]+"', p))
    must(journals == 9, "t4: journal count")
    p = b.get("/db/journals/pvldb/index.html", count=1, note="open PVLDB")
    pvldb_volumes = edition_count(p)
    fa = frequent_authors(p)[0]
    ed = newest_edition_link(p)
    p = b.get(ed, count=1, note="open the newest volume")
    vol_title, vol_records = title_of(p), edition_records(p)
    key, p = open_entry(b, p, 0, "open the first record")
    first_title = title_of(p)
    first_pages, first_mdate = record_meta(p, "pages"), record_meta(p, "mdate")
    must(first_mdate, "t4: mdate (no doi field here)")
    bib = b.get(f"/rec/{key}.bib", count=1, note="download BibTeX")
    etype = re.match(r"@(\w+)\{", bib).group(1)
    jfield = re.search(r"journal\s+= \{(.+?)\}", bib).group(1)
    p = b.get(ed, count=1, note="back to the volume contents")
    key2, p = open_entry(b, p, 1, "open the second record")
    second_title = title_of(p)
    second_authors = len(re.findall(r'href="/pid/[^"]+\.html"', p))
    p = b.get(first_pid_link(p), count=1,
              note="open the second record's first author")
    author_pubs, author_best = pub_count_of(p), busiest_year(p)
    top = top_coauthor(p)
    must(top, "t4: top coauthor")
    p = b.get(top.group(1), count=1, note="open their top coauthor")
    co_newest = entry_titles(p)[0]
    ven = entry_venue_href(p)
    p = b.get(ven, count=1,
              note="open that coauthor's newest publication's venue")
    co_ven_records = venue_records(p)
    ed2 = newest_edition_link(p)
    p = b.get(ed2, count=1, note="open its newest edition")
    co_ed_records, co_ed_first = edition_records(p), entry_titles(p)[0]
    p = open_entry_author(b, p, 0,
                          "open that edition's first record's first author")
    co_first_pubs = pub_count_of(p)
    p = b.search("vldb", "search venues for 'vldb'")
    vmatches = combined_count(p, "venue")
    must(vmatches == 2, "t4: two vldb venues")
    p = b.get("/db/journals/vldb/index.html", count=1,
              note="open The VLDB Journal")
    b.facts["task4"] = {
        "journal_venues": journals, "pvldb_volumes": pvldb_volumes,
        "pvldb_top_author": fa[0], "pvldb_top_count": fa[1],
        "vol_title": vol_title, "vol_records": vol_records,
        "first_title": first_title, "first_pages": first_pages,
        "first_mdate": first_mdate, "bibtex_entry_type": etype,
        "bibtex_journal_field": jfield, "second_title": second_title,
        "second_author_count": second_authors, "author_pubs": author_pubs,
        "author_busiest_year": author_best,
        "author_top_coauthor": top.group(3), "author_top_joint": top.group(2),
        "co_newest_title": co_newest, "co_venue_records": co_ven_records,
        "co_venue_ed_records": co_ed_records, "co_ed_first_title": co_ed_first,
        "co_first_author_pubs": co_first_pubs,
        "vldb_matches": vmatches, "vldbj_records": venue_records(p),
        "vldbj_volumes": edition_count(p),
    }


def task5(b):
    p = b.search("transactions", "search venues for 'transactions'")
    vmatches = combined_count(p, "venue")
    must(vmatches == 4, "t5: four transactions venues")
    seg = re.split(r'id="venue-results"', p)[1].split("</ul>")[0]
    pairs = re.findall(r'href="(/db/journals/[^"]+)">([^<]+)</a>', seg)
    counts, names = [], []
    for href, name in pairs:
        names.append(name)
        if href in ("/db/journals/tods/index.html",
                    "/db/journals/tois/index.html"):
            counts.append(None)      # read inside the main chains below
            continue
        vp = b.get(href, count=1, note=f"open {name}")
        counts.append(venue_records(vp))
        b.get("/search?q=transactions", count=1,
              note="back to the venue results")
    p = b.get("/db/journals/tods/index.html", count=1, note="open TODS")
    tods_iso = venue_info(p, "ISO 4 abbr.")
    tods_volumes, tods_records = edition_count(p), venue_records(p)
    ed = newest_edition_link(p)
    p = b.get(ed, count=1, note="open the newest volume")
    tods_vol, tods_vol_records = title_of(p), edition_records(p)
    key, p = open_entry(b, p, 0, "open the first record")
    tods_first, tods_pages = title_of(p), record_meta(p, "pages")
    p = b.get(first_pid_link(p), count=1,
              note="open that record's first author")
    tods_author_pubs = pub_count_of(p)
    top = top_coauthor(p)
    must(top, "t5: TODS coauthor")
    p = b.get(top.group(1), count=1, note="open their top coauthor")
    tods_co_pubs = pub_count_of(p)
    b.get("/search?q=transactions", count=1,
          note="return to the venue results")
    p = b.get("/db/journals/tois/index.html", count=1, note="open TOIS")
    tois_records, tois_volumes = venue_records(p), edition_count(p)
    ed = newest_edition_link(p)
    p = b.get(ed, count=1, note="open the TOIS newest volume")
    tois_vol = title_of(p)
    key, p = open_entry(b, p, 0, "open the TOIS first record")
    tois_first = title_of(p)
    tois_doi = record_ee_doi(p)
    must(tois_doi, "t5: TOIS ee DOI")
    p = b.get(first_pid_link(p), count=1,
              note="open the TOIS record's first author")
    tois_author_pubs = pub_count_of(p)
    top2 = top_coauthor(p)
    must(top2, "t5: TOIS coauthor")
    p = b.get(top2.group(1), count=1, note="open their top coauthor")
    tois_co_newest = entry_titles(p)[0]
    ven = entry_venue_href(p)
    p = b.get(ven, count=1,
              note="open the coauthor's newest publication's venue")
    b.facts["task5"] = {
        "venue_matches": vmatches, "venue_names": names,
        "venue_record_counts": counts, "tods_iso": tods_iso,
        "tods_volumes": tods_volumes, "tods_records": tods_records,
        "tods_vol_title": tods_vol, "tods_vol_records": tods_vol_records,
        "tods_first_title": tods_first, "tods_first_pages": tods_pages,
        "tods_author_pubs": tods_author_pubs,
        "tods_coauthor": top.group(3), "tods_coauthor_joint": top.group(2),
        "tods_co_pubs": tods_co_pubs,
        "tois_records": tois_records, "tois_volumes": tois_volumes,
        "tois_vol_title": tois_vol, "tois_first_title": tois_first,
        "tois_ee_doi": tois_doi, "tois_author_pubs": tois_author_pubs,
        "tois_coauthor": top2.group(3), "tois_coauthor_joint": top2.group(2),
        "tois_co_newest_title": tois_co_newest,
        "tois_co_venue_records": venue_records(p),
    }


def task6(b):
    p = b.search("query optimization", "search 'query optimization'")
    total = combined_count(p, "publ")
    must(total and total > 40, "t6: count")
    p = b.open_kind("publ", "query optimization",
                    "open the publication search results")
    oldest = min(year_facets(p))
    p = b.get(re.search(rf'href="([^"]*year={oldest}[^"]*)"', p).group(1),
              count=1, note=f"refine by the oldest year ({oldest})")
    ycount = nfound(p)
    yfirst = entry_titles(p)[0]
    p = b.get(re.search(r'href="([^"]*)"[^>]*>clear year filter', p).group(1),
              count=1, note="clear the year filter")
    p = b.get("/search/publ?q=query+optimization&type=article", count=1,
              note="refine by the journal-article type")
    tcount = nfound(p)
    must(tcount and tcount < total, "t6: type refined")
    p = b.get(re.search(r'href="([^"]*)"[^>]*>clear type filter', p).group(1),
              count=1, note="clear the type filter")
    p = b.get(re.search(rf'href="([^"]*year={oldest}[^"]*)"', p).group(1),
              count=1, note="refine by the oldest year again")
    key, p = open_entry(b, p, 0, "open that record")
    rec_doi, rec_pages = record_ee_doi(p), record_meta(p, "pages")
    rec_mdate = record_meta(p, "mdate")
    must(rec_doi and rec_pages and rec_mdate, "t6: ee DOI, pages, mdate")
    bibkey = re.search(r"@\w+\{(DBLP:[^,]+),", p).group(1)
    bib = b.get(f"/rec/{key}.bib", count=1, note="download the .bib")
    etype = re.match(r"@(\w+)\{", bib).group(1)
    vfield = re.search(r"(journal|booktitle)\s+= \{(.+?)\}", bib).group(2)
    p = b.get(first_pid_link(p), count=1,
              note="open the first author's profile")
    author_pubs, author_best = pub_count_of(p), busiest_year(p)
    co_n = len(coauthor_rows(p))
    top = top_coauthor(p)
    must(top, "t6: top coauthor")
    p = b.get(top.group(1), count=1, note="open their top coauthor")
    key2, p = open_entry(b, p, 0, "open the coauthor's newest publication")
    co_newest, co_venue = title_of(p), record_meta(p, "venue")
    ven = first_venue_link(p)
    p = b.get(ven, count=1, note="open its venue")
    co_ven_records = venue_records(p)
    ed = newest_edition_link(p)
    p = b.get(ed, count=1, note="open the venue's newest edition")
    b.facts["task6"] = {
        "count": total, "oldest_year": oldest, "year_count": ycount,
        "year_first_title": yfirst, "type_count": tcount,
        "record_ee_doi": rec_doi, "record_pages": rec_pages,
        "record_mdate": rec_mdate, "bibtex_key": bibkey,
        "entry_type": etype, "venue_field": vfield,
        "author_pubs": author_pubs, "author_busiest_year": author_best,
        "coauthor_index_size": co_n,
        "top_coauthor": top.group(3), "top_coauthor_joint": top.group(2),
        "co_newest_title": co_newest, "co_newest_venue": co_venue,
        "co_venue_records": co_ven_records,
        "co_venue_ed_records": edition_records(p),
    }


def task7(b):
    p = b.search("graph|network", "search 'graph|network'")
    orcount = combined_count(p, "publ")
    must(orcount and orcount > 3000, "t7: OR count")
    p = b.search("network$", "rerun exact-word 'network$'")
    exact = combined_count(p, "publ")
    must(exact and exact < orcount, "t7: exact subset")
    p = b.search("graph|network", "rerun the first search")
    p = b.open_kind("publ", "graph|network",
                    "open the publication search results")
    p = b.get("/search/publ?q=graph%7Cnetwork&type=inproceedings", count=1,
              note="refine by the conference-paper type")
    tcount = nfound(p)
    p = b.get(re.search(r'href="([^"]*)"[^>]*>clear type filter', p).group(1),
              count=1, note="clear the type filter")
    newest = max(year_facets(p))
    p = b.get(re.search(rf'href="([^"]*year={newest}[^"]*)"', p).group(1),
              count=1, note=f"refine by the newest year ({newest})")
    ycount = nfound(p)
    yfirst, yvenue = entry_titles(p)[0], entry_venue_href(p)
    p = b.get("/search/publ?q=graph%7Cnetwork&h=30&f=30", count=1,
              note="open page two")
    p2first, p2venue = entry_titles(p)[0], entry_venue_href(p)
    key, p = open_entry(b, p, 0, "open that record")
    rec_doi, rec_mdate = record_ee_doi(p), record_meta(p, "mdate")
    must(rec_doi and rec_mdate, "t7: ee DOI and mdate")
    bib = b.get(f"/rec/{key}.bib", count=1, note="download BibTeX")
    etype = re.match(r"@(\w+)\{", bib).group(1)
    ven = first_venue_link(p)
    p = b.get(ven, count=1, note="open the record's venue")
    ven_editions = edition_count(p)
    ven_best = busiest_year(p)
    ed = newest_edition_link(p)
    p = b.get(ed, count=1, note="open the newest edition")
    ed_records, ed_first = edition_records(p), entry_titles(p)[0]
    p = open_entry_author(b, p, 0, "open that record's first author")
    author_pubs = pub_count_of(p)
    top = top_coauthor(p)
    must(top, "t7: top coauthor")
    b.facts["task7"] = {
        "or_count": orcount, "exact_count": exact, "type_count": tcount,
        "year": newest, "year_count": ycount,
        "year_first_title": yfirst, "year_first_venue": yvenue,
        "page2_first_title": p2first, "page2_first_venue": p2venue,
        "record_ee_doi": rec_doi, "record_mdate": rec_mdate,
        "bibtex_entry_type": etype, "venue_editions": ven_editions,
        "venue_busiest_year": ven_best, "ed_records": ed_records,
        "ed_first_title": ed_first, "author_pubs": author_pubs,
        "top_coauthor": top.group(3), "top_coauthor_joint": top.group(2),
    }


def task8(b):
    b.register()
    p = b.search("side channel", "search 'side channel'")
    total = combined_count(p, "publ")
    must(total and total > 10, "t8: side channel count")
    seg = re.split(r'id="publ-results"', p)[1]
    keys = re.findall(r'class="entry [^"]*" id="((?:conf|journals)/[^"]+)"',
                      seg)[:2]
    key, p = open_entry(b, seg, 0, "open hit 1's record")
    t1_title = title_of(p)
    save_paper(b, f"/rec/{keys[0]}.html", keys[0], "Security reading",
               "first pick", "save hit 1 to Security reading")
    b.get("/search?q=side+channel", count=1, note="back to search results")
    key2, p = open_entry(b, re.split(r'id="publ-results"',
                                     b.get("/search?q=side+channel",
                                           count=0))[1], 0,
                         "open hit 2's record")
    t2_title = title_of(p)
    save_paper(b, f"/rec/{keys[1]}.html", keys[1], "Security reading",
               None, "save hit 2 to Security reading")
    p = b.open_account_page("/account/papers", "open saved papers")
    colls = saved_collections(p)
    must(colls and colls[0][0] == "Security reading" and
         colls[0][1] == "2", "t8: collection holds both")
    bib = b.get("/account/papers/export.bib?collection=Security+reading",
               count=1, note="export the collection as BibTeX")
    entries = len(re.findall(r"@\w+\{DBLP:", bib))
    first_type = re.match(r"@(\w+)\{", bib).group(1)
    b.log_out()
    p = b.login(REG["email"], REG["password"])
    p = b.open_account_page("/account/papers", "reopen saved papers")
    must("Security reading" in p, "t8: collection persists")
    rid = re.search(r'action="/account/papers/(\d+)/remove"', p).group(1)
    p = b.post("/account/papers", f"/account/papers/{rid}/remove", {}, 0,
               note="remove one record")
    remaining = re.findall(r'class="title">([^<]+)<', p)
    b.facts["task8"] = {
        "count": total, "hit1": t1_title, "hit2": t2_title,
        "collection_name": colls[0][0], "export_entries": entries,
        "first_entry_type": first_type, "remaining_titles": remaining,
    }


def task9(b):
    b.login("alice.j@test.com")
    p = b.open_account_page("/account/watchlist", "open the watchlist")
    seed_authors, seed_venues = watch_rows(p)
    must(len(seed_authors) == 3 and len(seed_venues) == 2,
         "t9: seed watchlist")
    p = b.search("jiawei han", "author-search 'Jiawei Han'")
    p = b.get("/pid/h/JiaweiHan.html", count=1,
              note="open the UIUC professor's profile")
    b.post("/pid/h/JiaweiHan.html", "/account/watchlist/author/add",
           {"pid": "h/JiaweiHan", "next": "/pid/h/JiaweiHan.html"}, 0,
           note="add him to the watchlist")
    p = b.open_account_page("/account/watchlist", "reopen the watchlist")
    authors, venues = watch_rows(p)
    must(len(authors) == 4 and "Jiawei Han 0001" in authors, "t9: added")
    pid = re.search(r'name="pid" value="([^"]+)"',
                    re.split(r'id="watchlist-authors"', p)[1]).group(1)
    p = b.post("/account/watchlist", "/account/watchlist/author/remove",
               {"pid": pid}, 0, note="remove one watched author")
    remaining_authors, _ = watch_rows(p)
    p = b.get("/db/conf/nips/index.html", count=1,
              note="open watched NeurIPS venue")
    nips_records, nips_best = venue_records(p), busiest_year(p)
    ed = newest_edition_link(p)
    p = b.get(ed, count=1, note="open its newest edition")
    nips_ed_records = edition_records(p)
    p = b.open_account_page("/account/watchlist", "back to the watchlist")
    p = b.post("/account/watchlist", "/account/watchlist/venue/remove",
               {"venue_id": "6"}, 0, note="remove the NeurIPS venue")
    _, remaining_venues = watch_rows(p)
    b.facts["task9"] = {
        "seed_authors": seed_authors, "seed_venues": seed_venues,
        "after_add_names": authors, "remaining_authors": remaining_authors,
        "nips_records": nips_records, "nips_busiest_year": nips_best,
        "nips_edition_records": nips_ed_records,
        "remaining_venues": remaining_venues,
    }


def task10(b):
    b.login("bob.c@test.com")
    p = b.open_account_page("/account/watchlist", "open the watchlist")
    _, seed_venues = watch_rows(p)
    must(len(seed_venues) == 3, "t10: bob's seed venues")
    p = b.search("learning", "search venues for 'learning'")
    p = b.get("/db/journals/tmlr/index.html", count=1, note="open TMLR")
    tmlr_records, tmlr_volumes = venue_records(p), edition_count(p)
    fa = frequent_authors(p)[0]
    b.post("/db/journals/tmlr/index.html", "/account/watchlist/venue/add",
           {"stream": "journals/tmlr",
            "next": "/db/journals/tmlr/index.html"}, 0,
           note="add TMLR to the watchlist")
    p = b.open_account_page("/account/watchlist", "reopen the watchlist")
    _, after_venues = watch_rows(p)
    must(len(after_venues) == 4, "t10: TMLR added")
    p = b.get("/db/journals/tmlr/index.html", count=1, note="back to TMLR")
    ed = newest_edition_link(p)
    p = b.get(ed, count=1, note="open the newest volume")
    vol_title, vol_records = title_of(p), edition_records(p)
    key, p = open_entry(b, p, 0, "open the first record")
    first_title, first_mdate = title_of(p), record_meta(p, "mdate")
    must(first_mdate, "t10: mdate (no doi field here)")
    p = b.get(first_pid_link(p), count=1, note="open first author")
    author_pubs = pub_count_of(p)
    b.log_out()
    p = b.get("/account/watchlist", count=1,
              note="open the watchlist after logout")
    b.facts["task10"] = {
        "seed_venues": seed_venues, "tmlr_records": tmlr_records,
        "tmlr_volumes": tmlr_volumes, "tmlr_top_author": fa[0],
        "tmlr_top_count": fa[1], "after_add_venues": after_venues,
        "vol_title": vol_title, "vol_records": vol_records,
        "first_title": first_title, "first_mdate": first_mdate,
        "author_pubs": author_pubs,
        "after_logout_redirected_to_login": "login?next" in p[:2000],
    }


def task11(b):
    b.login("dana.k@test.com")
    p = b.open_account_page("/account/saved-searches",
                            "open saved searches")
    seed = saved_search_rows(p)
    must(seed and "question answering" in seed, "t11: QA saved search")
    run = re.search(r'class="run-link" href="(/search/publ\?q=[^"]+)"',
                    p).group(1)
    p = b.get(run, count=1, note="run the QA search")
    qa_count = nfound(p)
    p = b.search("language model", "search 'language model'")
    p = b.open_kind("publ", "language model", "open publ search results")
    lm_count = nfound(p)
    b.post("/search/publ?q=language+model", "/account/saved-searches/add",
           {"query": "language model", "search_type": "publ",
            "next": "/search/publ?q=language+model"}, 0,
           note="save that search")
    p = b.open_account_page("/account/saved-searches",
                            "report the full table")
    table = saved_search_rows(p)
    must(len(table) == 2, "t11: two saved searches")
    sid = None
    for row in re.findall(r"<li>([\s\S]*?)</li>", p):
        if "question answering" in row:
            sid = re.search(r"/account/saved-searches/(\d+)/delete",
                            row).group(1)
            break
    must(sid, "t11: QA row found")
    p = b.post("/account/saved-searches",
               f"/account/saved-searches/{sid}/delete", {}, 0,
               note="delete the QA search")
    remaining = saved_search_rows(p)
    must(remaining == ["language model"], "t11: QA deleted")
    run = re.search(r'class="run-link" href="(/search/publ\?q=[^"]+)"',
                    p).group(1)
    p = b.get(run, count=1, note="run the remaining search")
    run_count = nfound(p)
    key, p = open_entry(b, p, 0, "open first hit's record")
    first_doi = record_ee_doi(p)
    must(first_doi, "t11: ee DOI")
    b.post(f"/rec/{key}.html", "/account/papers/add",
           {"key": key, "collection": "My Library",
            "next": f"/rec/{key}.html"}, 0,
           note="save that record to your library")
    p = b.open_account_page("/account/papers",
                            "open saved papers to see the collection")
    colls = saved_collections(p)
    b.facts["task11"] = {
        "seed_searches": seed, "qa_count": qa_count, "lm_count": lm_count,
        "table_after_save": table, "remaining_searches": remaining,
        "run_count": run_count, "first_doi": first_doi,
        "collection_landed": colls[0][0] if colls else None,
    }


def task12(b):
    b.login("carol.d@test.com")
    p = b.open_account_page("/account/papers", "open saved papers")
    seed_colls = saved_collections(p)
    must(seed_colls and seed_colls[0][0] == "My Library", "t12: seed library")
    p = b.search("fuzzing", "search 'fuzzing'")
    total = combined_count(p, "publ")
    seg = re.split(r'id="publ-results"', p)[1]
    keys = re.findall(r'class="entry [^"]*" id="((?:conf|journals)/[^"]+)"',
                      seg)[:2]
    key, p = open_entry(b, seg, 0, "open hit 1's record")
    save_paper(b, f"/rec/{keys[0]}.html", keys[0], "Audit queue",
               "must read", "save hit 1 to Audit queue")
    b.get("/search?q=fuzzing", count=1, note="back to search results")
    key2, p = open_entry(b, re.split(r'id="publ-results"',
                                     b.get("/search?q=fuzzing",
                                           count=0))[1], 0,
                         "open hit 2's record")
    save_paper(b, f"/rec/{keys[1]}.html", keys[1], "Audit queue",
               None, "save hit 2 to Audit queue")
    p = b.open_account_page("/account/papers", "open saved papers")
    after = saved_collections(p)
    bib = b.get("/account/papers/export.bib?collection=My+Library",
                count=1, note="export My Library")
    lib_entries = len(re.findall(r"@\w+\{DBLP:", bib))
    bib2 = b.get("/account/papers/export.bib?collection=Audit+queue",
                 count=1, note="export Audit queue")
    audit_entries = len(re.findall(r"@\w+\{DBLP:", bib2))
    m = re.search(r"<h2>Audit queue \(2\s*records?\)</h2>[\s\S]*?"
                  r'action="/account/papers/(\d+)/remove"', p)
    must(m, "t12: audit row present")
    p = b.post("/account/papers", f"/account/papers/{m.group(1)}/remove",
               {}, 0, note="remove one Audit queue record")
    audit_remaining = [c for c in saved_collections(p)
                       if c[0] == "Audit queue"]
    p = b.open_account_page("/account/watchlist", "open the watchlist")
    _, watched = watch_rows(p)
    b.facts["task12"] = {
        "seed_collections": seed_colls, "count": total,
        "after_save_collections": after, "my_library_entries": lib_entries,
        "audit_queue_entries": audit_entries, "audit_remaining": audit_remaining,
        "watched_venues": watched,
    }


def task13(b):
    b.login("dana.k@test.com")
    p = b.open_account_page("/account/history", "open search history")
    seed = history_rows(p)
    must(len(seed) == 5, "t13: seeded history")
    p = b.post("/account/history", "/account/history/clear", {}, 0,
               note="clear the history")
    must("search history is empty" in p, "t13: cleared")
    b.nav_search_kind("publ", "open the publication search page")
    counts = {}
    for q in ("deep learning", "index", "sql"):
        p = b.search(q, f"publication search {q!r}")
        counts[q] = nfound(p)
        must(counts[q], f"t13: {q} count")
    p = b.open_account_page("/account/history", "reopen history")
    rows = history_rows(p)
    must(len(rows) == 3, "t13: three new entries")
    b.nav_search_kind("author", "open the author search page")
    p = b.search("zhang", "author search 'zhang'")
    zmatches = nfound(p)
    must(zmatches and zmatches > 3000, "t13: zhang matches")
    p = b.get(first_pid_link(p), count=1, note="open the first profile")
    zpubs = pub_count_of(p)
    p = b.open_account_page("/account/history", "reopen history")
    final_rows = history_rows(p)
    must(len(final_rows) == 4, "t13: four rows at the end")
    b.facts["task13"] = {
        "seed_history": seed, "search_counts": counts,
        "new_history": rows, "history_total": len(rows),
        "zhang_matches": zmatches, "zhang_first_pubs": zpubs,
        "final_history": final_rows,
    }


def task14(b):
    b.login("alice.j@test.com")
    p = b.open_account_page("/account/profile", "open the profile")
    email = re.search(r"([\w.]+@[\w.]+)", p).group(1)
    m = re.search(r"member since:?\s*([\d-]+)", p, re.I)
    seed = {k: profile_field(p, k)
            for k in ("display_name", "affiliation", "research_interests")}
    p = b.post("/account/profile", "/account/profile",
               {"display_name": "Alice J. Fixer", "affiliation": "MIT CSAIL",
                "research_interests": "graph learning and attention"}, 3,
               note="edit the profile")
    updated = {k: profile_field(p, k)
               for k in ("display_name", "affiliation", "research_interests")}
    must(updated["display_name"] == "Alice J. Fixer" and
         updated["affiliation"] == "MIT CSAIL", "t14: profile updated")
    p = b.open_account_page("/account", "open the dashboard")
    dash_authors = re.search(r"(\d+) watched authors", p).group(1)
    dash_venues = re.search(r"(\d+) watched venues", p).group(1)
    recent = history_rows(p)[:5]
    p = b.open_account_page("/account/watchlist", "open the watchlist")
    authors, _ = watch_rows(p)
    p = b.open_account_page("/account/papers", "open saved papers")
    colls = saved_collections(p)
    p = b.open_account_page("/account/saved-searches", "open saved searches")
    searches = saved_search_rows(p)
    p = b.open_account_page("/account/profile", "back to the profile")
    cur = {k: profile_field(p, k)
           for k in ("display_name", "affiliation", "research_interests")}
    p = b.post("/account/profile", "/account/profile",
               {"display_name": cur["display_name"],
                "affiliation": "Stanford University",
                "research_interests": cur["research_interests"]}, 1,
               note="restore the affiliation")
    final = {k: profile_field(p, k)
             for k in ("display_name", "affiliation", "research_interests")}
    must(final["affiliation"] == "Stanford University", "t14: restored")
    b.facts["task14"] = {
        "profile_email": email,
        "member_since": m.group(1) if m else None,
        "seed_display_name": seed["display_name"],
        "seed_affiliation": seed["affiliation"],
        "seed_interests": seed["research_interests"],
        "updated_display_name": updated["display_name"],
        "updated_affiliation": updated["affiliation"],
        "updated_interests": updated["research_interests"],
        "dashboard_authors": dash_authors, "dashboard_venues": dash_venues,
        "recent_searches": recent, "watchlist_authors": authors,
        "collections": colls, "saved_searches": searches,
        "final_display_name": final["display_name"],
        "final_affiliation": final["affiliation"],
        "final_interests": final["research_interests"],
    }


def task15(b):
    p = b.search("guoliang li", "author-search 'Guoliang Li'")
    n = combined_count(p, "author")
    must(n == 2, "t15: two Guoliang Li profiles")
    seg = re.split(r'id="author-results"', p)[1].split("</ul>")[0]
    lis = re.findall(r'<li>([\s\S]*?)</li>', seg)
    href = [re.search(r'href="(/pid/[^"]+\.html)"', li).group(1)
            for li in lis if "Tsinghua" in li][0]
    p = b.get(href, count=1, note="open the Tsinghua professor")
    name, aff = title_of(p), affiliation_of(p)
    must(aff and "Tsinghua" in aff, "t15: Tsinghua affiliation")
    npubs, best = pub_count_of(p), busiest_year(p)
    top = top_coauthor(p)
    must(top, "t15: top coauthor")
    p = b.get(top.group(1), count=1, note="open his top coauthor")
    p = b.get(href, count=1, note="return to the professor")
    rows = coauthor_rows(p)
    second = rows[1]
    p = b.get(second[1], count=1, note="open the second-highest coauthor")
    second_pubs = pub_count_of(p)
    p = b.get(href, count=1, note="return to the professor")
    key, p = open_entry(b, p, 0, "open the professor's newest publication")
    new_title = title_of(p)
    new_venue, new_pages = record_meta(p, "venue"), record_meta(p, "pages")
    ven = first_venue_link(p)
    p = b.get(ven, count=1, note="open that venue")
    ven_records, ven_best = venue_records(p), busiest_year(p)
    ed = newest_edition_link(p)
    p = b.get(ed, count=1, note="open its newest edition")
    ed_records, ed_first = edition_records(p), entry_titles(p)[0]
    p = open_entry_author(b, p, 0, "open that record's first author")
    rec_pubs = pub_count_of(p)
    top3 = top_coauthor(p)
    must(top3, "t15: record author coauthor")
    p = b.get(top3.group(1), count=1, note="open their top coauthor")
    key2, p = open_entry(b, p, 0,
                         "open that coauthor's newest publication")
    co_newest, co_venue = title_of(p), record_meta(p, "venue")
    ven2 = first_venue_link(p)
    p = b.get(ven2, count=1, note="open its venue")
    co_ven_records = venue_records(p)
    ed2 = newest_edition_link(p)
    p = b.get(ed2, count=1, note="open its newest edition")
    b.facts["task15"] = {
        "author_matches": n, "prof_name": name, "prof_affiliation": aff,
        "prof_pubs": npubs, "prof_busiest_year": best,
        "top_coauthor": top.group(3), "top_coauthor_joint": top.group(2),
        "coauthor_index_size": len(rows),
        "second_coauthor": second[2], "second_joint": second[0],
        "second_pubs": second_pubs, "prof_newest_title": new_title,
        "prof_newest_venue": new_venue, "prof_newest_pages": new_pages,
        "venue_records": ven_records, "venue_busiest_year": ven_best,
        "ed_records": ed_records, "ed_first_title": ed_first,
        "rec_author_pubs": rec_pubs, "rec_top_coauthor": top3.group(3),
        "co_newest_title": co_newest, "co_newest_venue": co_venue,
        "co_venue_records": co_ven_records,
        "co_venue_ed_records": edition_records(p),
    }


def task16(b):
    p = b.get("/", count=0)
    stats = re.findall(r"# of ([\w ]+) : ([\d,]+)", p)
    must(len(stats) == 5, "t16: five counters")
    news = re.search(r"<dt[^>]*>\s*<span>(\d{4}-\d{2}-\d{2}): </span>([^<]+)<",
                     p)
    must(news, "t16: news item")
    p = b.search("sigmod", "search venues for 'sigmod'")
    p = b.get("/db/conf/sigmod/index.html", count=1,
              note="open the ACM SIGMOD Conference")
    nl = note_line_of(p)
    p = b.get("/db/conf/sigmod/sigmod2022.html", count=1,
              note="open the 2022 edition")
    ed_title, ed_records = title_of(p), edition_records(p)
    editors = venue_info(p, "editors")
    key, p = open_entry(b, p, 0, "open that edition's first record")
    rec_title, rec_pages = title_of(p), record_meta(p, "pages")
    rec_doi = record_ee_doi(p)
    must(rec_doi, "t16: ee DOI")
    bib = b.get(f"/rec/{key}.bib", count=1, note="download BibTeX")
    etype = re.match(r"@(\w+)\{", bib).group(1)
    ven = first_venue_link(p)
    p = b.get(ven, count=1, note="follow the record's venue link")
    leads_to = title_of(p)
    p = b.get("/db/conf/sigmod/sigmod2021.html", count=1,
              note="open the 2021 edition")
    ed21_title, ed21_records = title_of(p), edition_records(p)
    p = b.get("/db/conf/sigmod/index.html", count=1, note="return to the venue")
    p = b.get("/db/conf/sigmod/sigmod2022.html", count=1,
              note="reopen the newest edition")
    ed_first = entry_titles(p)[0]
    p = open_entry_author(b, p, 0, "open that record's first author")
    author_pubs = pub_count_of(p)
    top = top_coauthor(p)
    must(top, "t16: top coauthor")
    p = b.get(top.group(1), count=1, note="open their top coauthor")
    co_newest = entry_titles(p)[0]
    ven2 = entry_venue_href(p)
    p = b.get(ven2, count=1, note="open that venue")
    co_ven_records = venue_records(p)
    p = b.search("sigmod year:2022", "search 'sigmod year:2022'")
    ycount = combined_count(p, "publ")
    yfirst = re.split(r'id="publ-results"', p)[1]
    yfirst = re.search(r'class="title">([^<]+)<', yfirst).group(1)
    b.facts["task16"] = {
        "stats": [list(s) for s in stats], "news_date": news.group(1),
        "news_title": news.group(2).strip(), "note_line": nl,
        "ed_title": ed_title, "ed_records": ed_records, "ed_editors": editors,
        "record_title": rec_title, "record_pages": rec_pages,
        "record_ee_doi": rec_doi, "bibtex_entry_type": etype,
        "venue_link_leads_to": leads_to, "ed21_title": ed21_title,
        "ed21_records": ed21_records, "ed_first_title": ed_first,
        "author_pubs": author_pubs, "top_coauthor": top.group(3),
        "co_newest_title": co_newest, "co_venue_records": co_ven_records,
        "year2022_count": ycount, "year2022_first_title": yfirst,
    }


def task17(b):
    p = b.search("transformer year:2025", "search 'transformer year:2025'")
    total = combined_count(p, "publ")
    must(total and total > 400, "t17: transformer count")
    first_title = re.split(r'id="publ-results"', p)[1]
    first_title = re.search(r'class="title">([^<]+)<', first_title).group(1)
    p = open_entry_author(b, re.split(r'id="publ-results"', p)[1], 0,
                          "open the first hit's first author")
    author_pubs, author_best = pub_count_of(p), busiest_year(p)
    author_newest = entry_titles(p)[0]
    ven = entry_venue_href(p)
    p = b.get(ven, count=1, note="open that venue")
    ven_records = venue_records(p)
    ed = newest_edition_link(p)
    p = b.get(ed, count=1, note="open its newest edition")
    ed_first = entry_titles(p)[0]
    p = open_entry_author(b, p, 0, "open that record's first author")
    rec_pubs = pub_count_of(p)
    top = top_coauthor(p)
    must(top, "t17: top coauthor")
    p = b.search("attention year:2025", "search 'attention year:2025'")
    att = combined_count(p, "publ")
    must(att and att > 300, "t17: attention count")
    att_first = re.split(r'id="publ-results"', p)[1]
    att_first = re.search(r'class="title">([^<]+)<', att_first).group(1)
    key, p = open_entry(b, re.split(r'id="publ-results"', p)[1], 0,
                       "open that record")
    att_type, att_mdate = record_meta(p, "type"), record_meta(p, "mdate")
    must(att_type and att_mdate, "t17: type and mdate")
    bib = b.get(f"/rec/{key}.bib", count=1, note="download BibTeX")
    etype = re.match(r"@(\w+)\{", bib).group(1)
    p = b.get(first_pid_link(p), count=1, note="open its first author")
    att_author_pubs = pub_count_of(p)
    att_top = top_coauthor(p)
    must(att_top, "t17: attention coauthor")
    p = b.get(att_top.group(1), count=1, note="open their top coauthor")
    key2, p = open_entry(b, p, 0,
                         "open that coauthor's newest publication")
    att_co_newest, att_co_venue = title_of(p), record_meta(p, "venue")
    ven2 = first_venue_link(p)
    p = b.get(ven2, count=1, note="open its venue")
    att_co_ven_records = venue_records(p)
    ed2 = newest_edition_link(p)
    p = b.get(ed2, count=1, note="open its newest edition")
    b.facts["task17"] = {
        "count": total, "first_title": first_title,
        "author_pubs": author_pubs, "author_busiest_year": author_best,
        "author_newest_title": author_newest, "venue_records": ven_records,
        "ed_first_title": ed_first, "rec_author_pubs": rec_pubs,
        "rec_top_coauthor": top.group(3), "rec_top_joint": top.group(2),
        "att_count": att, "att_first_title": att_first,
        "att_record_type": att_type, "att_record_mdate": att_mdate,
        "bibtex_entry_type": etype, "att_author_pubs": att_author_pubs,
        "att_top_coauthor": att_top.group(3),
        "att_top_joint": att_top.group(2),
        "att_co_newest_title": att_co_newest,
        "att_co_newest_venue": att_co_venue,
        "att_co_venue_records": att_co_ven_records,
        "att_co_venue_ed_records": edition_records(p),
    }


def task18(b):
    b.login("bob.c@test.com")
    p = b.search("learned index", "search 'learned index'")
    total = combined_count(p, "publ")
    must(total and total > 20, "t18: learned index count")
    key, p = open_entry(b, re.split(r'id="publ-results"', p)[1], 0,
                        "open the first hit's record")
    first_doi = record_ee_doi(p)
    first_venue = record_meta(p, "venue")
    must(first_doi, "t18: ee DOI")
    save_paper(b, f"/rec/{key}.html", key, "DB reading list",
               None, "save it to the DB reading list collection")
    p = b.search("neural", "search venues for 'neural'")
    seg = re.split(r'id="venue-results"', p)[1]
    nips_href = re.search(r'href="(/db/conf/nips/index.html)"', seg).group(1)
    p = b.get(nips_href, count=1, note="open the NeurIPS venue")
    nips_records = venue_records(p)
    fa = frequent_authors(p)[0]
    b.post(nips_href, "/account/watchlist/venue/add",
           {"stream": "conf/nips", "next": nips_href}, 0,
           note="add it to the watchlist")
    p = b.open_account_page("/account/papers", "open saved papers")
    db_list = [c for c in saved_collections(p) if c[0] == "DB reading list"]
    must(db_list and db_list[0][1] == "6", "t18: saved to DB reading list")
    bib = b.get("/account/papers/export.bib?collection=DB+reading+list",
                count=1, note="export it")
    export_entries = len(re.findall(r"@\w+\{DBLP:", bib))
    p = b.open_account_page("/account/watchlist", "open the watchlist")
    _, watched = watch_rows(p)
    must(any("Neural Information" in v for v in watched), "t18: NeurIPS watched")
    vid = None
    for row in re.findall(r"<li>([\s\S]*?)</li>",
                          re.split(r'id="watchlist-venues"', p)[1]):
        if "VLDB Endowment" in row:
            vid = re.search(r'name="venue_id" value="(\d+)"', row).group(1)
            break
    must(vid, "t18: VLDB Endowment row")
    p = b.post("/account/watchlist", "/account/watchlist/venue/remove",
               {"venue_id": vid}, 0, note="remove the VLDB Endowment venue")
    _, remaining_venues = watch_rows(p)
    b.facts["task18"] = {
        "count": total, "first_ee_doi": first_doi, "first_venue": first_venue,
        "nips_records": nips_records, "nips_top_author": fa[0],
        "nips_top_count": fa[1], "db_reading_list": db_list,
        "export_entries": export_entries, "watched_venues": watched,
        "remaining_venues": remaining_venues,
    }


def task19(b):
    p = b.search("zhang", "author-search 'Zhang'")
    zmatches = combined_count(p, "author")
    must(zmatches and zmatches > 3000, "t19: zhang matches")
    p = b.open_kind("author", "zhang", "open author search results")
    p = b.get("/search/author?q=zhang&h=30&f=30", count=1,
              note="open results page two")
    seg = re.split(r'<ul class="result-list', p)[1]
    seg = seg.split("</ul>")[0]
    name2 = re.search(r'href="/pid/[^"]+">([^<]+)</a>', seg).group(1)
    pubs2 = re.search(r"(\d+) records", seg).group(1)
    href2 = re.search(r'href="(/pid/[^"]+\.html)"', seg).group(1)
    p = b.get(href2, count=1, note="open that profile")
    best2 = busiest_year(p)
    top = top_coauthor(p)
    must(top, "t19: top coauthor")
    p = b.get(top.group(1), count=1, note="open their top coauthor")
    ven = entry_venue_href(p)
    p = b.get(ven, count=1, note="open that coauthor's newest pub venue")
    co_ven_records = venue_records(p)
    p = b.search("min zhang", "author-search 'Min Zhang'")
    mmatches = combined_count(p, "author")
    must(mmatches and mmatches > 40, "t19: min zhang matches")
    p = b.open_kind("author", "min zhang", "open author search results")
    best_name = best_pubs = best_href = None
    best_page = "/search/author?q=min+zhang"
    while True:
        page_url = best_page if best_pubs is None else page_url
        segs = re.split(r'<ul class="result-list', p)[1:]
        for seg in segs:
            for li in re.findall(r'<li[\s\S]*?</li>', seg):
                m = re.search(r'(\d+) records', li)
                n = int(m.group(1)) if m else -1
                if n > (best_pubs or -1):
                    best_pubs = n
                    best_name = re.search(r'href="/pid/[^"]+">([^<]+)</a>',
                                          li).group(1)
                    best_href = re.search(r'href="(/pid/[^"]+\.html)"',
                                          li).group(1)
                    best_page = page_url
        nxt = re.search(r'href="([^"]*f=\d+[^"]*)"[^>]*>\[next', p)
        if not nxt:
            break
        page_url = nxt.group(1)
        p = b.get(page_url, count=1, note="next results page")
    must(best_pubs and best_pubs > 50, "t19: best min zhang")
    if page_url != best_page:
        p = b.get(best_page, count=1,
                  note="return to the page with the most-records profile")
    p = b.get(best_href, count=1, note="open the Min Zhang with most records")
    min_name = title_of(p)
    min_newest = entry_titles(p)[0]
    ven2 = entry_venue_href(p)
    p = b.get(ven2, count=1, note="open their newest pub's venue")
    min_ven_records = venue_records(p)
    min_ven_best = busiest_year(p)
    ed = newest_edition_link(p)
    p = b.get(ed, count=1, note="open its newest edition")
    min_ed_records, min_ed_first = edition_records(p), entry_titles(p)[0]
    p = open_entry_author(b, p, 0,
                          "open edition first record's first author")
    b.facts["task19"] = {
        "zhang_matches": zmatches, "page2_first_name": name2,
        "page2_first_pubs": pubs2, "page2_first_busiest_year": best2,
        "top_coauthor": top.group(3), "top_coauthor_joint": top.group(2),
        "co_venue_records": co_ven_records, "min_matches": mmatches,
        "min_best_pubs": best_pubs, "min_best_name": min_name,
        "min_newest_title": min_newest, "min_venue_records": min_ven_records,
        "min_venue_busiest_year": min_ven_best,
        "min_edition_records": min_ed_records,
        "min_ed_first_title": min_ed_first,
        "min_rec_author_pubs": pub_count_of(p),
    }


# ---------------------------------------------------------------------------

TASKS = [task0, task1, task2, task3, task4, task5, task6, task7, task8,
         task9, task10, task11, task12, task13, task14, task15, task16,
         task17, task18, task19]

# Honest step counts measured twice with the independent-review counting
# convention (see verify/README.md); the walker self-checks against these.
EXPECTED = {0: 15, 1: 15, 2: 15, 3: 15, 4: 15, 5: 18, 6: 15, 7: 16,
            8: 26, 9: 17, 10: 18, 11: 18, 12: 21, 13: 21, 14: 16,
            15: 15, 16: 15, 17: 15, 18: 18, 19: 16}


def reset_site():
    """Reset the site between tasks (mirrors the independent review's
    per-task reset). Requires WH_CTRL_TOKEN + WH_CONTROL in the env."""
    import os
    import subprocess
    tok = os.environ.get("WH_CTRL_TOKEN", "")
    ctl = os.environ.get("WH_CONTROL", "")
    if not tok or not ctl:
        return False
    r = subprocess.run(["curl", "-s", "-X", "POST",
                        "-H", f"Authorization: Bearer {tok}",
                        f"{ctl}/reset/dblp"], capture_output=True,
                       text=True, timeout=180)
    if '"ok"' not in r.stdout and '"ready"' not in r.stdout:
        raise RuntimeError(f"reset failed: {r.stdout[:200]}")
    for _ in range(90):
        try:
            subprocess.run(["curl", "-sf", f"{BASE}/_health"],
                           capture_output=True, timeout=10)
            return True
        except Exception:
            import time
            time.sleep(1)
    raise RuntimeError("site not healthy after reset")


def main():
    out_path = sys.argv[2] if len(sys.argv) > 2 else "/tmp/dblp_walk.json"
    which = [int(a) for a in sys.argv[3:]] if len(sys.argv) > 3 else \
        list(range(len(TASKS)))
    results = {}
    for i in which:
        reset_site()      # a fresh instance per task, like the review runs
        b = Browser()
        try:
            TASKS[i](b)
            ok = b.steps == EXPECTED[i]
            results[f"dblp--{i}"] = {"steps": b.steps,
                                     "expected": EXPECTED[i],
                                     "facts": b.facts.get(f"task{i}")}
            print(f"task {i:2d}: {b.steps:3d} steps "
                  f"{'OK' if ok else 'MISMATCH (expected %d)' % EXPECTED[i]}",
                  flush=True)
        except Exception as e:
            print(f"task {i:2d}: FAILED {e}", flush=True)
            results[f"dblp--{i}"] = {"steps": b.steps,
                                     "expected": EXPECTED[i],
                                     "error": str(e)}
    with open(out_path, "w") as f:
        json.dump(results, f, indent=1, sort_keys=True)
    total = sum(r["steps"] for r in results.values())
    ok = sum(1 for r in results.values() if "error" not in r)
    print(f"\n{ok}/{len(results)} tasks walked, total {total} steps, "
          f"min {min(r['steps'] for r in results.values())}, "
          f"max {max(r['steps'] for r in results.values())}")


if __name__ == "__main__":
    main()
