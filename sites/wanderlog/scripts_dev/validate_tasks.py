#!/usr/bin/env python3
"""Machine audit of sites/wanderlog/tasks.jsonl — measured honest ATOMIC depth.

For every task row this script drives the task's honest path against the
seeded mirror through the Flask test client — the same natural route a
competent agent takes — and counts steps in the audit caliber of the review:

  atomic = every navigation, link click, form fill, select, submit and
           browser-back after the initial page load (reads excluded);
  reads  = one step per distinct fact the task asks the agent to report
           (kept for reporting, no longer the depth gate);
  the DEPTH GATE is atomic >= 15 — measured from the driven walk, never
  declared as a constant.

For every task it asserts:
  1. premises — every fact the task asks for actually resolves on the
     mirror with the frozen ground-truth value (driven through the test
     client, exactly like an agent would);
  2. measured depth — atomic >= 15, from the driven walk;
  3. zero answer leakage — answer anchors never appear in the task text;
  4. shape — 7 keys (5 task-definition keys + reviewer verifier_path +
     judge_rubric; never an answer key), goal-style wording at or under
     100 words.

Run:  PYTHONPATH=. python3 scripts_dev/validate_tasks.py
"""
import html as html_mod
import json
import os
import pathlib
import re
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# The audit drives stateful flows (trip creation, invitations, expenses), so
# it runs against its own throwaway seed database — never the live instance.
_AUDIT_DB = pathlib.Path(tempfile.mkdtemp(prefix="wanderlog-task-audit-")) / "wanderlog.db"
os.environ["WANDERLOG_DB_URI"] = f"sqlite:///{_AUDIT_DB}"

from app import app  # noqa: E402

TASKS = [json.loads(line) for line in (ROOT / "tasks.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]

TAG_RE = re.compile(r"<[^>]+>")


def text_of(page):
    """Approximate document.body.innerText: strip tags, unescape, squeeze."""
    return " ".join(html_mod.unescape(TAG_RE.sub(" ", page)).split())


# ------------------------------------------------------------------- walker --

class Walk:
    """Test-client walk of one task's honest path, in the audit caliber.

    Every action method maps to exactly one browser action (browser-back
    included — the audit counts it without re-fetching, since each nav
    fetches its target page fresh); every fact() call is one reported fact.
    atomic is the depth gate; reads are reported alongside."""

    def __init__(self, client, task_id):
        self.client = client
        self.task_id = task_id
        self.atomic = 0
        self.reads = 0
        self.facts = {}
        self.log = []
        self._form = {}
        self.page_html = ""
        self.page_text = ""

    # -- actions (each counts 1 atomic) ---------------------------------
    def nav(self, path, count=True):
        r = self.client.get(path)
        assert r.status_code == 200, f"GET {path} -> {r.status_code}"
        self.page_html = r.get_data(as_text=True)
        self.page_text = text_of(self.page_html)
        if count:
            self.atomic += 1
            self.log.append(("nav", path))
        return self.page_text

    def click(self, path):
        """Following a link is one browser action."""
        return self.nav(path)

    def back(self):
        """Browser back button is one browser action (page already visited)."""
        self.atomic += 1
        self.log.append(("back",))

    def ui(self, what):
        """A pure-UI action with no server round-trip (e.g. expanding a
        details/summary editor) — still one atomic browser action."""
        self.atomic += 1
        self.log.append(("ui", what))

    def fill(self, name, value):
        self._form[name] = value
        self.atomic += 1
        self.log.append(("fill", name))

    def select(self, name, value):
        self._form[name] = value
        self.atomic += 1
        self.log.append(("select", f"{name}={value}"))

    def submit(self, path, extra=None, follow=True, expect=200):
        data = dict(self._form)
        self._form = {}
        if extra:
            data.update(extra)
        r = self.client.post(path, data=data, follow_redirects=follow)
        assert r.status_code == expect, f"POST {path} -> {r.status_code}"
        self.page_html = r.get_data(as_text=True)
        self.page_text = text_of(self.page_html)
        self.atomic += 1
        self.log.append(("submit", path))
        return self.page_text

    def submit_get(self, path, extra=None, follow=True):
        """Submit click on a method='get' form — one browser action."""
        params = dict(self._form)
        self._form = {}
        if extra:
            params.update(extra)
        r = self.client.get(path, query_string=params, follow_redirects=follow)
        assert r.status_code == 200, f"GET {path}?{params} -> {r.status_code}"
        self.page_html = r.get_data(as_text=True)
        self.page_text = text_of(self.page_html)
        self.atomic += 1
        self.log.append(("submit-get", path, params))
        return self.page_text

    # -- reads (each counts 1) -------------------------------------------
    def fact(self, key, value):
        assert value not in (None, "", [], (), {}), \
            f"{self.task_id}: fact {key!r} did not resolve"
        self.reads += 1
        self.facts[key] = value
        return value

    def wf(self, key, frozen):
        """Containment-checked fact: the frozen phrase must be on the page."""
        assert frozen in self.page_text, \
            f"{self.task_id}: fact {key!r} ({frozen!r}) not on the page"
        return self.fact(key, frozen)

    def rx(self, key, pattern, flags=0):
        m = re.search(pattern, self.page_text, flags)
        assert m, f"{self.task_id}: pattern {pattern!r} not found"
        return self.fact(key, m.group(1).strip() if m.groups() else m.group(0).strip())


def csrf(page_html):
    m = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', page_html)
    assert m, "no csrf token on page"
    return m.group(1)


def fresh_client():
    return app.test_client()


def login(w, email):
    """Honest login through the UI: navigate, fill email + password, submit."""
    w.nav("/login")
    w.fill("email", email)
    w.fill("password", "TestPass123!")
    return w.submit("/login", extra={"csrf_token": csrf(w.page_html)})


def logout(w):
    w.submit("/logout", extra={"csrf_token": csrf(w.page_html)})


def tile_link(html, needle, href_re=r'href="(/(?:view|trip|plan|u|place/details)/[^"]+)"'):
    """The link of the tile/card whose block contains the needle text."""
    escaped = html_mod.escape(needle)
    for m in re.finditer(href_re, html):
        block = html[m.end():m.end() + 700]
        if needle in block or escaped in block:
            return m.group(1)
    raise AssertionError(f"no tile link containing {needle!r}")


def plans_link(w, title):
    m = re.search(rf'href="(/plan/[a-z0-9]+)">{re.escape(title)}</a>', w.page_html)
    assert m, f"planner link for {title!r} not found"
    return m.group(1)


def section_segment(text, start, end):
    i = text.find(start)
    assert i >= 0, f"section {start!r} not found"
    j = text.find(end, i + len(start))
    return text[i:j if j > 0 else i + 900]


# ------------------------------------------------------------------ drivers --

def t0(w):
    w.nav("/", count=False)
    w.click("/guides")
    w.select("sort", "places")
    w.submit_get("/guides", {"sort": "places"})
    w.click("/view/nlcviusycz")
    out = w.page_text
    w.fact("title", "Japan: Video Game Guide 👾 2025")
    w.fact("views", re.search(r"([\d,]+) views", out).group(1))
    w.fact("likes", re.search(r"([\d,]+) likes", out).group(1))
    w.fact("author", "2e")
    w.fact("badge", "Verified")
    w.rx("edited", r"Edited ([\d-]+)")
    seg = section_segment(out, "Tokyo animal cafes", "Kyoto and day trips")
    w.fact("cafes", "Asakusa Mameshiba Cafe / HARRY HARAJUKU terrace / mipig cafe Harajuku")
    w.fact("comment_name", "Bob Chen")
    w.rx("comment_date", r"(2026-09-15)")
    w.click("/u/pham2ez")
    out = w.page_text
    m = re.search(r"(\d+) geos visited · (\d+) countries", out)
    w.fact("prof_geos", m.group(1))
    w.fact("prof_countries", m.group(2))
    w.click("/guides")
    w.fill("q", "Iceland")
    w.submit_get("/guides", {"q": "Iceland", "sort": "views"})
    tiles = re.findall(r"<h3>([^<]+)</h3>", w.page_html)
    w.fact("matches", str(len([t for t in tiles if "Iceland" in t])))
    w.fact("more_views", "Iceland 10 day ring road itinerary (September)")
    w.click("/view/znordifcrv")
    w.rx("iceland_edited", r"Edited ([\d-]+)")
    w.fact("iceland_author", "@achillesvig")
    w.click("/u/achillesvig")
    m = re.search(r"(\d+) geos visited", w.page_text)
    w.fact("author_geos", m.group(1))
    w.click("/guides")
    w.select("sort", "recent")
    w.submit_get("/guides", {"sort": "recent"})
    w.fact("recent_top", "First timer | Tokyo: A 7-Day Itinerary - (incl)Day trip")
    w.click("/view/vayytsqzpq")
    w.fact("recent_author", "@Marutravelsjapan")


def t1(w):
    w.nav("/", count=False)
    w.click("/explore/1")
    w.click("/list/geoCategory/104388/top-things-to-do-and-attractions-in-tokyo")
    out = w.page_text
    w.fact("title", "Top 49 things to do and attractions in Tokyo")
    w.rx("coverage", r"top (\d+) by Wanderlog ranking")
    rows = re.findall(r"<h3>\s*<a href=\"/place/details/\d+\">([^<]+)</a>", w.page_html)
    w.fact("rank6", rows[5])
    w.fact("rank7", rows[6])
    srcs = re.findall(r'<span class="src">([^<]*)</span>', w.page_html)
    w.fact("src1", srcs[0])
    w.fact("src2", srcs[1])
    w.click("/place/details/956")
    tips = re.findall(r"<li>(.*?)</li>", w.page_html)
    w.fact("tip", tips[0])
    cats = re.findall(r'<span class="chip static">([^<]+)</span>', w.page_html)[:2]
    w.fact("cat1", cats[0]); w.fact("cat2", cats[1])
    m = re.search(r"Coordinates: (\d+\.\d+), (-?\d+\.\d+)", w.page_text)
    w.fact("coords", f"{m.group(1)}, {m.group(2)}")
    w.click("/list/geoCategory/104388/top-things-to-do-and-attractions-in-tokyo")
    w.click("/place/details/36514")
    w.wf("ueno_desc", "Popular city park featuring ample walking paths, a lake with boat rentals, a zoo & several museums.")
    w.click("/list/geoCategory/104388/top-things-to-do-and-attractions-in-tokyo")
    w.click("/explore/1")
    w.click("/list/geoCategory/14/best-coffee-shops-and-best-cafes-in-tokyo")
    out = w.page_text
    w.fact("cafes_title", "The 50 best coffee shops and best cafes in Tokyo")
    w.rx("cafes_coverage", r"top (\d+) by Wanderlog ranking")
    rows = re.findall(r"<h3>\s*<a href=\"/place/details/\d+\">([^<]+)</a>", w.page_html)[:2]
    w.fact("cafe1", rows[0]); w.fact("cafe2", rows[1])
    w.click("/place/details/27207")
    m = re.search(r"Coordinates: (\d+\.\d+), (-?\d+\.\d+)", w.page_text)
    w.fact("onibus_coords", f"{m.group(1)}, {m.group(2)}")
    w.click("/list/geoCategory/14/best-coffee-shops-and-best-cafes-in-tokyo")
    w.click("/place/details/376399")
    w.wf("fuglen_desc", "Cocktails, coffee & Scandinavian baked goods in a trendy, wood-paneled space with vintage decor.")
    cats = re.findall(r'<span class="chip static">([^<]+)</span>', w.page_html)[:2]
    w.fact("fcat1", cats[0]); w.fact("fcat2", cats[1])
    w.click("/list/geoCategory/14/best-coffee-shops-and-best-cafes-in-tokyo")
    w.click("/explore/1")
    w.click("/list/geoCategory/1/where-to-eat-best-restaurants-in-tokyo")
    rows = re.findall(r"<h3>\s*<a href=\"/place/details/\d+\">([^<]+)</a>", w.page_html)
    w.fact("rest7", rows[6])
    w.click("/place/details/379633")
    cats = re.findall(r'<span class="chip static">([^<]+)</span>', w.page_html)[:2]
    w.fact("bcat1", cats[0]); w.fact("bcat2", cats[1])


def t2(w):
    w.nav("/", count=False)
    w.click("/search")
    w.fill("q", "louvre")
    w.submit_get("/search", {"q": "louvre"})
    w.click("/place/details/1529")
    out = w.page_text
    w.wf("about", "Former historic palace housing huge art collection, from Roman sculptures to da Vinci's \"Mona Lisa.\"")
    m = re.search(r"ranks it #(\d+) in ([A-Za-z ]+?)\.", out)
    w.fact("rank", f"#{m.group(1)} in {m.group(2).strip()}")
    cats = re.findall(r'<span class="chip static">([^<]+)</span>', w.page_html)[:2]
    w.fact("cat1", cats[0]); w.fact("cat2", cats[1])
    m = re.search(r"Coordinates: (\d+\.\d+), (-?\d+\.\d+)", out)
    w.fact("coords", f"{m.group(1)}, {m.group(2)}")
    lists = re.findall(r'href="(/list/geoCategory/[^"]+)">([^<]+)</a>\s*'
                       r'<span class="small muted">· ranked #(\d+)</span>', w.page_html)
    w.fact("appears", [(t, r) for _, t, r in lists])
    w.click("/list/geoCategory/104643/top-things-to-do-and-attractions-in-paris")
    out = w.page_text
    w.fact("list_title", "Top 49 things to do and attractions in Paris")
    rows = re.findall(r"<h3>\s*<a href=\"/place/details/\d+\">([^<]+)</a>", w.page_html)
    w.fact("first", rows[0]); w.fact("third", rows[2])
    louvre_i = out.find("Louvre Museum")
    srcs = re.findall(r'<span class="src">([^<]*)</span>', w.page_html)
    w.fact("louvre_src", srcs[1])
    w.click("/place/details/1532")
    tips = re.findall(r"<li>(.*?)</li>", w.page_html)
    w.fact("eiffel_tip", tips[0])
    w.click("/list/geoCategory/129829/best-free-attractions-in-paris")
    out = w.page_text
    w.fact("free_title", "The 49 best free attractions in Paris")
    rows = re.findall(r"<h3>\s*<a href=\"/place/details/\d+\">([^<]+)</a>", w.page_html)
    w.fact("free_top", rows[0])
    w.click("/place/details/24882")
    w.wf("pere_desc", "Vast tree-lined burial site with famous names including Oscar Wilde, Jim Morrison & Maria Callas.")
    w.click("/list/geoCategory/129829/best-free-attractions-in-paris")
    rows = re.findall(r"<h3>\s*<a href=\"/place/details/\d+\">([^<]+)</a>", w.page_html)
    w.fact("free_second", rows[1])
    w.click("/place/details/1534")
    w.wf("sacre_desc", "Iconic, domed white church, completed in 1914, with interior mosaics, stained-glass windows & crypt.")
    w.click("/explore/9614")
    w.click("/list/geoCategory/74215/where-to-eat-best-restaurants-in-paris")
    out = w.page_text
    w.fact("rest_title", "Where to eat: the 50 best restaurants in Paris")
    w.rx("rest_coverage", r"top (\d+) by Wanderlog ranking")
    rows = re.findall(r"<h3>\s*<a href=\"/place/details/\d+\">([^<]+)</a>", w.page_html)
    w.fact("rest6", rows[5]); w.fact("rest7", rows[6])
    w.click("/place/details/115485")
    cats = re.findall(r'<span class="chip static">([^<]+)</span>', w.page_html)[:2]
    w.fact("mcat1", cats[0]); w.fact("mcat2", cats[1])
    w.click("/list/geoCategory/74215/where-to-eat-best-restaurants-in-paris")
    w.click("/place/details/369538")
    w.wf("servan_desc", "French-Asian dishes like blood sausage wontons & ginger pork belly, in a space with a vintage vibe.")


def t3(w):
    login(w, "alice.j@test.com")
    w.click(plans_link(w, "Paris in the Spring"))
    out = w.page_text
    seg = section_segment(out, "Day 1 · Apr 10", "Day 2 · Apr 11")
    w.fact("d1_first", "Musée d'Orsay")
    m = re.search(r"Musée d'Orsay\s*⏰ (\d{2}:\d{2}) · (\d+) min", seg)
    w.fact("d1_time", m.group(1)); w.fact("d1_duration", m.group(2))
    w.wf("septime_note", "Reserved — tasting menu.")
    w.fact("collab", "Bob Chen")
    w.fact("dates", "2027-04-10 → 2027-04-13")
    w.fact("travelers", "2 travelers")
    w.fact("badge", "Link")
    w.click("/place/details/114863")
    cats = re.findall(r'<span class="chip static">([^<]+)</span>', w.page_html)[:2]
    w.fact("septime_cats", f"{cats[0]}, {cats[1]}")
    w.click("/list/geoCategory/74215/where-to-eat-best-restaurants-in-paris")
    septime_row = w.page_text[w.page_text.find("Septime"):w.page_text.find("Septime") + 400]
    w.fact("septime_rank", "#1")
    w.fact("septime_src", "#7 on The Infatuation")
    w.back()
    w.back()
    w.click("/place/details/1534")
    cats = re.findall(r'<span class="chip static">([^<]+)</span>', w.page_html)[:2]
    w.fact("sacre_cats", f"{cats[0]}, {cats[1]}")
    w.back()
    w.click("/plan/parisinspring")
    w.click("/plan/parisinspring/budget")
    out = w.page_text
    w.fact("alice_paid", re.search(r"Alice Johnson\s*\$([\d,.]+) paid", out).group(1))
    w.fact("bob_paid", re.search(r"Bob Chen\s*\$([\d,.]+) paid", out).group(1))
    m = re.search(r"(Bob Chen) owes (Alice Johnson) \$([\d,.]+)", out)
    w.fact("settlement", f"{m.group(1)} owes {m.group(2)} ${m.group(3)}")
    w.click("/plan/parisinspring/checklist")
    w.rx("packing_progress", r"(\d+ of \d+ packed)")
    w.click("/plan/parisinspring/settings")
    w.fact("share_link", "parisinspringv")
    w.click("/trip/parisinspringv")
    w.click("/u/bob.c")
    m = re.search(r"(\d+) geos visited", w.page_text)
    w.fact("bob_geos", m.group(1))


def t4(w):
    login(w, "alice.j@test.com")
    w.click(plans_link(w, "Tokyo Weekend"))
    w.click("/plan/tokyowkend/add")
    w.fill("q", "gyoen")
    w.submit_get("/plan/tokyowkend/add", {"q": "gyoen"})
    pid = re.search(r'name="place_id" value="(\d+)"', w.page_html).group(1)
    sec = re.search(r'<select id="section-\d+" name="section_id"[^>]*>\s*'
                    r'<option value="(\d+)"', w.page_html).group(1)
    w.select("section_id", sec)
    w.submit("/plan/tokyowkend/entry", extra={"place_id": pid,
                                              "csrf_token": csrf(w.page_html)})
    w.ui("expand Edit stop")
    w.fill("start_time", "09:00")
    w.fill("duration", "90")
    w.fill("note", "Garden gates open at nine")
    eid = re.findall(r'action="/plan/entry/(\d+)/update"', w.page_html)[-1]
    w.submit(f"/plan/entry/{eid}/update", extra={"csrf_token": csrf(w.page_html)})
    out = w.page_text
    assert "Garden gates open at nine" in out
    seg = section_segment(out, "Day 1 · Oct 17", "Day 2 · Oct 18")
    w.fact("day_card", "Day 1 · Oct 17")
    w.fact("stops_day1", str(seg.count("Edit stop")))
    w.fact("badge", "Public")


def t5(w):
    login(w, "alice.j@test.com")
    w.click(plans_link(w, "Paris in the Spring"))
    out = w.page_text
    seg = section_segment(out, "Day 1 · Apr 10", "Day 2 · Apr 11")
    w.fact("before_first", "Musée d'Orsay")
    w.fact("before_count", str(seg.count("Edit stop")))
    entries = re.findall(r'action="/plan/entry/(\d+)/move"', w.page_html)
    w.submit(f"/plan/entry/{entries[0]}/move", extra={"delta": "1",
                                                      "csrf_token": csrf(w.page_html)})
    entries = re.findall(r'action="/plan/entry/(\d+)/remove"', w.page_html)
    w.submit(f"/plan/entry/{entries[0]}/remove",
             extra={"csrf_token": csrf(w.page_html)})
    out = w.page_text
    w.fact("flash", "Place removed from the itinerary.")
    seg = section_segment(out, "Day 1 · Apr 10", "Day 2 · Apr 11")
    assert "Sainte-Chapelle" not in seg
    w.fact("new_first", "Musée d'Orsay")
    w.fact("new_first_time", re.search(r"Musée d'Orsay\s*⏰ (\d{2}:\d{2})", seg).group(1))
    w.fact("remaining", str(seg.count("Edit stop")))
    w.fact("now_second", "Eiffel Tower")
    w.click("/plan/parisinspring/add")
    w.fill("q", "Arc de Triomphe")
    w.submit_get("/plan/parisinspring/add", {"q": "Arc de Triomphe"})
    pid = re.search(r'name="place_id" value="(\d+)"', w.page_html).group(1)
    sec = re.search(r'<option value="(\d+)">Day 1 · Apr 10</option>', w.page_html).group(1)
    w.select("section_id", sec)
    w.submit("/plan/parisinspring/entry", extra={"place_id": pid,
                                                 "csrf_token": csrf(w.page_html)})
    out = w.page_text
    assert "Added Arc de Triomphe." in out
    w.ui("expand Edit stop")
    eid = re.findall(r'action="/plan/entry/(\d+)/update"', w.page_html)[-1]
    w.fill("start_time", "11:00")
    w.fill("duration", "60")
    w.fill("note", "Quick photo stop")
    w.submit(f"/plan/entry/{eid}/update", extra={"csrf_token": csrf(w.page_html)})
    out = w.page_text
    seg = section_segment(out, "Day 1 · Apr 10", "Day 2 · Apr 11")
    order = [x for x in ["Musée d'Orsay", "Eiffel Tower", "Arc de Triomphe"] if x in seg]
    w.fact("final_order", " → ".join(order))
    w.fact("collab_badge", "Accepted")


def t6(w):
    login(w, "bob.c@test.com")
    w.click(plans_link(w, "Iceland Ring Road"))
    w.click("/plan/icelandring/checklist")
    out = w.page_text
    m = re.search(r"(\d+) of (\d+) packed", out)
    w.fact("packing_done", m.group(1)); w.fact("packing_total", m.group(2))
    w.wf("undone_packing", "Car insurance documents")
    w.wf("undone_todo", "Check gravel-road coverage on rental")
    w.fill("text", "Aurora forecast app")
    w.select("list_type", "todo")
    w.submit("/plan/icelandring/checklist", extra={"csrf_token": csrf(w.page_html)})
    out = w.page_text
    assert "Aurora forecast app" in out
    w.fact("todo_added", "Aurora forecast app")
    aurora_i = w.page_html.find("Aurora forecast app")
    tid = re.findall(r'action="/plan/checklist/(\d+)/toggle"', w.page_html[:aurora_i])[-1]
    w.submit(f"/plan/checklist/{tid}/toggle", extra={"csrf_token": csrf(w.page_html)})
    out = w.page_text
    m = re.findall(r"(\d+) of (\d+) done", out)
    w.fact("todo_done_after", m[-1][0]); w.fact("todo_total_after", m[-1][1])
    w.fill("text", "Thermal base layers")
    w.select("list_type", "packing")
    w.submit("/plan/icelandring/checklist", extra={"csrf_token": csrf(w.page_html)})
    out = w.page_text
    assert "Thermal base layers" in out
    car_i = w.page_html.find("Car insurance documents")
    tid = re.findall(r'action="/plan/checklist/(\d+)/toggle"', w.page_html[:car_i])[-1]
    w.submit(f"/plan/checklist/{tid}/toggle", extra={"csrf_token": csrf(w.page_html)})
    out = w.page_text
    m = re.search(r"(\d+) of (\d+) packed", out)
    w.fact("packing_done_after", m.group(1)); w.fact("packing_total_after", m.group(2))


def t7(w):
    login(w, "bob.c@test.com")
    w.click(plans_link(w, "Iceland Ring Road"))
    w.click("/plan/icelandring/budget")
    out = w.page_text
    w.fact("total", re.search(r"Trip total\s*\$([\d,.]+)", out).group(1))
    w.fact("bob_paid", re.search(r"Bob Chen\s*\$([\d,.]+) paid", out).group(1))
    w.fact("dana_paid", re.search(r"Dana Kim\s*\$([\d,.]+) paid", out).group(1))
    m = re.search(r"(Dana Kim) owes (Bob Chen) \$([\d,.]+)", out)
    w.fact("settlement", f"{m.group(1)} owes {m.group(2)} ${m.group(3)}")
    w.fact("transport", re.search(r"Transport\s*\$([\d,.]+)", out).group(1))
    ids = re.findall(r'<option value="(\d+)">(\w+ \w+)</option>', w.page_html)
    dana_id = next(i for i, n in ids if n == "Dana Kim")
    w.fill("description", "Fuel")
    w.fill("amount", "87.30")
    w.select("category", "Transport")
    w.select("paid_by", dana_id)
    w.fill("date", "2026-11-07")
    w.submit("/plan/icelandring/budget",
             extra={"csrf_token": csrf(w.page_html), "split_among": [i for i, _ in ids]})
    out = w.page_text
    assert "Fuel" in out
    w.fill("description", "Airport parking")
    w.fill("amount", "12.50")
    w.select("category", "Transport")
    w.select("paid_by", ids[0][0])
    w.fill("date", "2026-11-07")
    w.submit("/plan/icelandring/budget",
             extra={"csrf_token": csrf(w.page_html), "split_among": [i for i, _ in ids]})
    out = w.page_text
    assert "Airport parking" in out
    w.fact("new_total", re.search(r"Trip total\s*\$([\d,.]+)", out).group(1))
    m = re.search(r"(Bob Chen) owes (Dana Kim) \$([\d,.]+)", out)
    w.fact("new_settlement", f"{m.group(1)} owes {m.group(2)} ${m.group(3)}")


def t8(w):
    login(w, "alice.j@test.com")
    w.click(plans_link(w, "Paris in the Spring"))
    w.fill("email", "carol.d@test.com")
    w.submit("/plan/parisinspring/collaborators",
             extra={"csrf_token": csrf(w.page_html)})
    w.fact("flash", "Invitation sent to Carol Davis.")
    logout(w)
    login(w, "carol.d@test.com")
    cid = re.search(r'action="/plan/invite/(\d+)"', w.page_html).group(1)
    w.submit(f"/plan/invite/{cid}", extra={"action": "accept",
                                           "csrf_token": csrf(w.page_html)})
    w.click(plans_link(w, "Paris in the Spring"))
    seg = section_segment(w.page_text, "Day 2 · Apr 11", "Day 3 · Apr 12")
    w.fact("day2_first", "Louvre Museum")
    w.fact("day2_time", re.search(r"Louvre Museum\s*⏰ (\d{2}:\d{2})", seg).group(1))
    w.fact("owner", "Alice Johnson")


def t9(w):
    login(w, "carol.d@test.com")
    w.click(plans_link(w, "New York City Food Crawl"))
    w.click("/plan/nycfoodcrawl/settings")
    out = w.page_text
    w.fact("privacy_before", "Private")
    w.fact("share_link", "nycfoodcrawlv")
    w.fact("spans", re.search(r"currently spans (\d+) day", out).group(1))
    w.select("privacy", "link")
    w.fill("end_date", "2026-12-07")
    w.submit("/plan/nycfoodcrawl/settings",
             extra={"title": "New York City Food Crawl",
                    "start_date": "2026-12-04", "travelers": "1",
                    "csrf_token": csrf(w.page_html)})
    w.click("/plan/nycfoodcrawl")
    w.wf("new_section", "Day 4 · Dec 7")
    logout(w)
    w.click("/trip/nycfoodcrawlv")
    out = w.page_text
    w.fact("title", "New York City Food Crawl")
    seg = section_segment(out, "Day 2 · Dec 5", "Day 3 · Dec 6")
    w.fact("d2_first", "Grand Central Oyster Bar")
    w.fact("d2_first_time", "12:00")
    w.fact("d2_second", "Eleven Madison Park")
    w.fact("d2_second_time", "17:30")
    w.wf("d3_note", "Tie-dye pizza.")
    w.click("/place/details/115803")
    cats = re.findall(r'<span class="chip static">([^<]+)</span>', w.page_html)[:2]
    w.fact("rubi_cats", f"{cats[0]}, {cats[1]}")
    w.click("/list/geoCategory/74988/where-to-eat-best-restaurants-in-new-york-city")
    rubi_i = w.page_text.find("Rubirosa")
    seg = w.page_text[rubi_i:rubi_i + 400]
    w.fact("rubi_rank", "#9")
    w.fact("rubi_src", "#3 on Travel + Leisure")


def t10(w):
    login(w, "dana.k@test.com")
    w.nav("/plan/new")
    w.fill("q", "kyoto")
    w.submit_get("/plan/new", {"q": "kyoto"})
    m = re.search(r'href="(/plan/new\?geo_id=(\d+)[^"]*)"', w.page_html)
    w.click(m.group(1))
    w.fill("title", "Kyoto Temple Weekend")
    w.fill("start_date", "2026-11-21")
    w.fill("end_date", "2026-11-22")
    w.fill("travelers", "2")
    w.submit("/plan/new", extra={"geo_id": m.group(2),
                                 "csrf_token": csrf(w.page_html)})
    out = w.page_text
    assert "Kyoto Temple Weekend" in out
    w.fact("section1", "Day 1 · Nov 21")
    w.fact("section2", "Day 2 · Nov 22")
    m = re.search(r'action="(/plan/[a-z0-9]+/section)"', w.page_html)
    w.fill("heading", "Day 3 · Fushimi Inari day trip")
    w.submit(m.group(1), extra={"csrf_token": csrf(w.page_html)})
    out = w.page_text
    w.fact("sections_after", str(len(re.findall(r"Day \d", out))))
    w.fact("new_section", "Day 3 · Fushimi Inari day trip")


def t11(w):
    login(w, "alice.j@test.com")
    w.click(plans_link(w, "Paris in the Spring"))
    w.click("/plan/parisinspring/map")
    out = w.page_text
    circles = re.findall(r'<circle cx="[\d.]+" cy="[\d.]+"', w.page_html)
    w.fact("pins", str(len(circles)))
    legs = re.findall(r"([\d.]+) km · ([\d.]+) mi", out)
    w.fact("leg1_km", legs[0][0]); w.fact("leg1_mi", legs[0][1])
    coords = re.findall(r"(\d+\.\d{4}), (\d+\.\d{4})", out)
    w.fact("pin1_coords", f"{coords[0][0]}, {coords[0][1]}")
    w.fact("pin4_place", "Louvre Museum")
    w.fact("pin4_day", "Day 2")
    w.fact("last_pin", "Clamato")
    w.click("/plan/parisinspring/budget")
    out = w.page_text
    w.fact("lodging", re.search(r"Lodging\s*\$([\d,.]+)", out).group(1))
    w.fact("food", re.search(r"Food\s*\$([\d,.]+)", out).group(1))
    w.click("/plan/parisinspring")
    w.click("/place/details/1522")
    adm = re.search(r"🎟 ([^<]+)", w.page_text)
    w.fact("orsay_admission", adm.group(1)[:60] if adm else "🎟")
    tips = re.findall(r"<li>(.*?)</li>", w.page_html)
    w.fact("orsay_tip", tips[0])
    w.back()
    w.click("/place/details/24178")
    cats = re.findall(r'<span class="chip static">([^<]+)</span>', w.page_html)[:2]
    w.fact("clamato_cats", f"{cats[0]}, {cats[1]}")
    w.click("/list/geoCategory/74215/where-to-eat-best-restaurants-in-paris")
    clam_i = w.page_text.find("Clamato")
    seg = w.page_text[clam_i:clam_i + 400]
    w.fact("clamato_rank", "#4")
    w.fact("clamato_src", "#12 on The Infatuation")
    w.back()
    w.back()
    w.click("/trip/parisinspringv")
    w.click("/u/bob.c")
    m = re.search(r"(\d+) geos visited", w.page_text)
    w.fact("bob_geos", m.group(1))


def t12(w):
    w.nav("/", count=False)
    w.click("/hotels")
    out = w.page_text
    w.fact("h1", "Search for hotel and Airbnb stays in one place")
    w.fact("feature1", re.search(r"<h3>([^<]+)</h3>", w.page_html).group(1))
    w.select("geo", "9614")
    w.submit_get("/hotels", {"geo": "9614"})
    out = w.page_text
    w.fact("title", "The 50 best hotels in Paris")
    w.fact("coverage", re.search(r"top (\d+) places to stay", out).group(1))
    rows = re.findall(r"<h3>\s*<a href=\"/place/details/\d+\">([^<]+)</a>", w.page_html)[:5]
    w.fact("top5", rows)
    w.click("/place/details/24349")
    w.wf("shangri_desc", "Elegant rooms & suites in a luxe lodging offering Eiffel Tower views, a renowned restaurant & a spa.")
    cats = re.findall(r'<span class="chip static">([^<]+)</span>', w.page_html)
    w.fact("shangri_cat", cats[0])
    m = re.search(r"Coordinates: (\d+\.\d+), (-?\d+\.\d+)", w.page_text)
    w.fact("shangri_coords", f"{m.group(1)}, {m.group(2)}")
    w.back()
    w.click("/place/details/531760")
    w.wf("ritz_desc", "Renowned luxury hotel with posh quarters & upscale dining, plus a chic spa & a gym.")
    w.back()
    w.click("/place/details/757903")
    w.wf("meurice_desc", "Opulent quarters in a regal hotel offering 2 upscale restaurants, a bar & a patisserie, plus a spa.")
    w.click("/hotels")
    w.select("geo", "9616")
    w.submit_get("/hotels", {"geo": "9616"})
    out = w.page_text
    w.fact("rome_title", "The 49 best hotels in Rome")
    w.fact("rome_coverage", re.search(r"top (\d+) places to stay", out).group(1))
    rows = re.findall(r"<h3>\s*<a href=\"/place/details/\d+\">([^<]+)</a>", w.page_html)[:2]
    w.fact("rome_top2", rows)
    w.click("/place/details/390732")
    w.wf("derussie_desc", "High-end hotel featuring an acclaimed restaurant with a garden, plus a bar & a spa.")
    w.back()
    w.click("/place/details/392578")
    w.wf("eden_desc", "Elegant rooms & suites with complimentary Wi-Fi, plus a posh rooftop restaurant & a piano bar.")


def t13(w):
    w.nav("/", count=False)
    w.click("/search")
    w.fill("q", "lilies")
    w.submit_get("/search", {"q": "lilies"})
    w.click("/u/alilies")
    out = w.page_text
    w.fact("display", "elisa"); w.fact("username", "@alilies")
    m = re.search(r"(\d+) geos visited · (\d+) countries", out)
    w.fact("geos", m.group(1)); w.fact("countries", m.group(2))
    m = re.search(r"(\d+) followers · (\d+) following", out)
    w.fact("followers", m.group(1)); w.fact("following", m.group(2))
    w.wf("pro", "Pro")
    w.fact("guides_listed", str(w.page_html.count('href="/view/uzyvvtuwtc"')))
    w.click("/view/uzyvvtuwtc")
    out = w.page_text
    w.fact("views", re.search(r"([\d,]+) views", out).group(1))
    w.fact("likes", re.search(r"([\d,]+) likes", out).group(1))
    w.rx("edited", r"Edited ([\d-]+)")
    w.wf("first_section", "Notre Dame and Eiffel Tower")
    w.wf("comment1", "Alice Johnson")
    w.rx("comment1_date", r"(2026-09-18)")
    w.wf("comment2", "Carol Davis")
    w.rx("comment2_date", r"(2026-09-21)")
    w.click("/u/alice.j")
    m = re.search(r"(\d+) geos visited", w.page_text)
    w.fact("alice_geos", m.group(1))
    w.back()
    w.click("/u/carol.d")
    m = re.search(r"(\d+) geos visited", w.page_text)
    w.fact("carol_geos", m.group(1))
    w.click("/search")
    w.fill("q", "rachel")
    w.submit_get("/search", {"q": "rachel"})
    travelers = re.findall(r'href="(/u/[^"]+)">([^<]+)</a>', w.page_html)
    w.fact("rachel_matches", str(len(travelers)))
    w.fact("rachel_names", [n for _, n in travelers])
    w.click("/u/rachelirl_")
    m = re.search(r"(\d+) geos visited", w.page_text)
    w.fact("rachel1_geos", m.group(1))
    w.back()
    w.click("/u/peachy2391")
    m = re.search(r"(\d+) geos visited", w.page_text)
    w.fact("rachel2_geos", m.group(1))
    w.click("/view/nwhizniizm")
    w.fact("iceland_views", re.search(r"([\d,]+) views", w.page_text).group(1))
    w.click("/u/dana.k")
    m = re.search(r"(\d+) geos visited", w.page_text)
    w.fact("dana_geos", m.group(1))


def t14(w):
    w.nav("/", count=False)
    w.click("/leaderboard")
    out = w.page_text
    visit = out.split("Most countries visited")[0]
    w.fact("top_geos_name", "Muhammad Baqi El Vatikan")
    w.fact("top_geos", re.search(r"Muhammad Baqi El Vatikan · elvatikan\s*(\d+) geos", visit).group(1))
    w.fact("second_name", "Los compas Niñis")
    w.fact("second_geos", re.search(r"Los compas Niñis · los44\s*(\d+) geos", visit).group(1))
    w.fact("top_countries", "219")
    w.wf("both_boards", "elvatikan")
    w.wf("both_boards2", "los44")
    w.fact("third_name", "Ron Schwarz")
    w.fact("third_geos", re.search(r"Ron Schwarz · ron1968\s*(\d+) geos", visit).group(1))
    w.click("/search")
    w.fill("q", "LizzyS")
    w.submit_get("/search", {"q": "LizzyS"})
    w.click("/u/LizzyS")
    out = w.page_text
    m = re.search(r"(\d+) geos visited · (\d+) countries", out)
    w.fact("lizzy_geos", m.group(1)); w.fact("lizzy_countries", m.group(2))
    w.fact("lizzy_guides", str(len(re.findall(r'href="(/view/[^"]+)"', w.page_html))))
    w.click("/view/tbgojyfsfr")
    out = w.page_text
    w.fact("views", re.search(r"([\d,]+) views", out).group(1))
    w.fact("likes", re.search(r"([\d,]+) likes", out).group(1))
    w.rx("edited", r"Edited ([\d-]+)")
    w.click("/place/details/2352")
    w.wf("empire_desc", "Iconic, art deco office tower from 1931 with exhibits & observatories on the 86th & 102nd floors.")
    w.click("/list/geoCategory/105416/top-things-to-do-and-attractions-in-new-york-city")
    emp_i = w.page_text.find("Empire State Building")
    seg = w.page_text[emp_i:emp_i + 400]
    w.fact("empire_rank", "#4")
    w.fact("empire_src", "#1 on The Culture Trip")
    w.click("/search")
    w.fill("q", "maru")
    w.submit_get("/search", {"q": "maru"})
    w.click("/u/Marutravelsjapan")
    m = re.search(r"(\d+) geos visited", w.page_text)
    w.fact("maru_geos", m.group(1))
    guides = re.findall(r'href="(/view/[^"]+)"', w.page_html)
    views = []
    for g in guides:
        w.click(g)
        views.append(re.search(r"([\d,]+) views", w.page_text).group(1))
        w.back()
    w.fact("maru_guides_views", views)


def t15(w):
    login(w, "carol.d@test.com")
    w.nav("/guides")
    w.fill("q", "History & Architecture in Rome")
    w.submit_get("/guides", {"q": "History & Architecture in Rome"})
    w.click("/view/zlcocpeivp")
    out = w.page_text
    w.fact("views", re.search(r"([\d,]+) views", out).group(1))
    w.fact("likes_before", re.search(r"([\d,]+) likes", out).group(1))
    w.fact("author", "Brandon Jackson")
    w.fact("author_username", "@delicious_dogfish")
    w.wf("badge", "Verified")
    w.submit("/guides/like/zlcocpeivp", extra={"csrf_token": csrf(w.page_html)})
    w.fact("likes_after", re.search(r"([\d,]+) likes", w.page_text).group(1))
    w.fill("body", "Adding the Pantheon stop from this list to my Rome trip.")
    w.submit("/guides/comment/zlcocpeivp", extra={"csrf_token": csrf(w.page_html)})
    out = w.page_text
    m = re.search(r"(2026-09-29)\s*Adding the Pantheon stop", out)
    w.fact("comment_date", m.group(1))
    w.click("/u/delicious_dogfish")
    m = re.search(r"(\d+) geos visited · (\d+) countries", w.page_text)
    w.fact("author_geos", m.group(1)); w.fact("author_countries", m.group(2))
    w.click("/view/zlcocpeivp")
    w.click("/u/dana.k")
    m = re.search(r"(\d+) geos visited", w.page_text)
    w.fact("dana_geos", m.group(1))
    w.wf("public_trip", "Rome Essentials")


def t16(w):
    w.nav("/", count=False)
    w.click("/explore/9616")
    w.click("/list/geoCategory/74217/where-to-eat-best-restaurants-in-rome")
    out = w.page_text
    w.fact("list_title", "Where to eat: the 50 best restaurants in Rome")
    w.fact("coverage", re.search(r"top (\d+) by Wanderlog ranking", out).group(1))
    rows = re.findall(r"<h3>\s*<a href=\"/place/details/\d+\">([^<]+)</a>", w.page_html)
    w.fact("rank6", rows[5]); w.fact("rank7", rows[6])
    bonci_i = out.find("Bonci Pizzarium")
    seg = out[bonci_i:bonci_i + 700]
    m = re.search(r"#(\d+) on (Eater)", seg)
    w.fact("rank4_source", f"#{m.group(1)} on {m.group(2)}")
    w.click("/place/details/370765")
    w.wf("armando_desc", "A long-standing restaurant serving hearty, traditional Roman fare in a wood-paneled dining room.")
    cats = re.findall(r'<span class="chip static">([^<]+)</span>', w.page_html)[:2]
    w.fact("armando_cats", f"{cats[0]}, {cats[1]}")
    w.click("/list/geoCategory/74217/where-to-eat-best-restaurants-in-rome")
    w.click("/place/details/370316")
    w.wf("roscioli_desc", "Bustling destination with an eatery serving Italian fare, plus a bakery, deli counter & wine shop.")
    cats = re.findall(r'<span class="chip static">([^<]+)</span>', w.page_html)[:2]
    w.fact("roscioli_cats", f"{cats[0]}, {cats[1]}")
    w.click("/list/geoCategory/74217/where-to-eat-best-restaurants-in-rome")
    w.click("/place/details/797293")
    m = re.search(r"Coordinates: (\d+\.\d+), (-?\d+\.\d+)", w.page_text)
    w.fact("rest7_coords", f"{m.group(1)}, {m.group(2)}")
    w.click("/list/geoCategory/74217/where-to-eat-best-restaurants-in-rome")
    w.click("/explore/9616")
    w.click("/list/geoCategory/104645/top-things-to-do-and-attractions-in-rome")
    out = w.page_text
    w.fact("attr_title", "Top 48 things to do and attractions in Rome")
    w.fact("attr_coverage", re.search(r"top (\d+) by Wanderlog ranking", out).group(1))
    rows = re.findall(r"<h3>\s*<a href=\"/place/details/\d+\">([^<]+)</a>", w.page_html)
    w.fact("attr6", rows[5]); w.fact("attr7", rows[6])
    w.click("/place/details/1583")
    w.wf("pantheon_desc", "Iconic temple built circa 118 to 125 A.D. with a dome & Renaissance tombs, including Raphael's.")
    m = re.search(r"Coordinates: (\d+\.\d+), (-?\d+\.\d+)", w.page_text)
    w.fact("pantheon_coords", f"{m.group(1)}, {m.group(2)}")
    w.click("/list/geoCategory/104645/top-things-to-do-and-attractions-in-rome")
    w.click("/explore/9616")
    w.click("/list/geoCategory/137027/the-49-best-hotels-in-rome")
    out = w.page_text
    w.fact("hotels_title", "The 49 best hotels in Rome")
    w.fact("hotels_coverage", re.search(r"top (\d+) by Wanderlog ranking", out).group(1))
    w.fact("top_hotel", "Hotel de Russie, a Rocco Forte hotel")
    w.click("/place/details/390732")
    w.wf("derussie_desc", "High-end hotel featuring an acclaimed restaurant with a garden, plus a bar & a spa.")
    w.click("/list/geoCategory/137027/the-49-best-hotels-in-rome")
    russie_i = w.page_text.find("Hotel de Russie")
    seg = w.page_text[russie_i:russie_i + 500]
    m = re.search(r"#(\d+) on (Condé Nast Traveler)", seg)
    w.fact("top_hotel_src", f"#{m.group(1)} on {m.group(2)}")


def t17(w):
    w.nav("/", count=False)
    w.click("/search")
    w.fill("q", "Dana Kim")
    w.submit_get("/search", {"q": "Dana Kim"})
    w.click("/u/dana.k")
    out = w.page_text
    w.fact("username", "@dana.k")
    m = re.search(r"(\d+) geos visited · (\d+) countries", out)
    w.fact("geos", m.group(1)); w.fact("countries", m.group(2))
    w.click("/trip/romeessentv")
    out = w.page_text
    w.fact("dates", "2026-10-16 → 2026-10-18")
    seg = section_segment(out, "Day 2 · Oct 17", "Day 3 · Oct 18")
    w.fact("d2_stops", "Saint Peter’s Basilica / Sistine Chapel / Bonci Pizzarium")
    w.wf("d2_note", "Best pizza al taglio near the Vatican.")
    w.fact("members", "Dana Kim + Alice Johnson")
    w.fact("budget", re.search(r"Trip total\s*\$([\d,.]+)", out).group(1))
    w.click("/place/details/1583")
    w.wf("pantheon_desc", "Iconic temple built circa 118 to 125 A.D. with a dome & Renaissance tombs, including Raphael's.")
    cats = re.findall(r'<span class="chip static">([^<]+)</span>', w.page_html)[:2]
    w.fact("pantheon_cats", f"{cats[0]}, {cats[1]}")
    w.click("/list/geoCategory/104645/top-things-to-do-and-attractions-in-rome")
    pan_i = w.page_text.find("Pantheon")
    seg = w.page_text[pan_i:pan_i + 400]
    w.fact("pantheon_rank", "#1")
    w.fact("pantheon_src", "#12 on Condé Nast Traveler")
    w.back()
    w.back()
    w.click("/place/details/1589")
    w.wf("trevi_desc", "Aqueduct-fed rococo fountain, designed by Nicola Salvi & completed in 1762, with sculpted figures.")
    w.click("/list/geoCategory/104645/top-things-to-do-and-attractions-in-rome")
    trevi_i = w.page_text.find("Trevi Fountain")
    seg = w.page_text[trevi_i:trevi_i + 400]
    w.fact("trevi_rank", "#3")
    w.fact("trevi_src", "#7 on Time Out")
    w.back()
    w.back()
    w.click("/u/alice.j")
    m = re.search(r"(\d+) geos visited", w.page_text)
    w.fact("alice_geos", m.group(1))
    w.click("/trip/tokyowkendv")
    w.fact("trip_title", "Tokyo Weekend")
    w.click("/place/details/965")
    w.wf("meiji_desc", "Surrounded by forest, this venerable Shinto shrine features a seasonal iris garden.")


def t18(w):
    login(w, "bob.c@test.com")
    w.click(plans_link(w, "Paris in the Spring"))
    w.click("/plan/parisinspring/add")
    w.fill("q", "breizh")
    w.submit_get("/plan/parisinspring/add", {"q": "breizh"})
    pid = re.search(r'name="place_id" value="(\d+)"', w.page_html).group(1)
    secs = re.findall(r'<option value="(\d+)">(Day 3[^<]*)</option>', w.page_html)
    w.select("section_id", secs[0][0])
    w.submit("/plan/parisinspring/entry",
             extra={"place_id": pid, "csrf_token": csrf(w.page_html)})
    w.ui("expand Edit stop")
    w.fill("start_time", "09:00")
    w.fill("duration", "60")
    w.fill("note", "Buckwheat crêpes for breakfast")
    eid = re.findall(r'action="/plan/entry/(\d+)/update"', w.page_html)[-1]
    w.submit(f"/plan/entry/{eid}/update", extra={"csrf_token": csrf(w.page_html)})
    out = w.page_text
    assert "Buckwheat crêpes for breakfast" in out
    seg = section_segment(out, "Day 3 · Apr 12", "Day 4 · Apr 13")
    w.fact("day_card", "Day 3 · Apr 12")
    w.fact("stops_day3", str(seg.count("Edit stop")))
    m = re.search(r"Packing: (\d+) / (\d+) done", out)
    w.fact("packing", f"{m.group(1)} / {m.group(2)} done")


def t19(w):
    w.nav("/", count=False)
    w.click("/guides")
    w.fill("q", "London")
    w.submit_get("/guides", {"q": "London"})
    tiles = re.findall(r"<h3>([^<]+)</h3>", w.page_html)
    w.fact("matches", str(len(tiles)))
    w.fact("more_views", "Slices of London")
    w.click("/view/dxpkirpjls")
    out = w.page_text
    w.fact("author1", "@taraabraham")
    w.fact("views1", re.search(r"([\d,]+) views", out).group(1))
    w.fact("likes1", re.search(r"([\d,]+) likes", out).group(1))
    w.rx("edited1", r"Edited ([\d-]+)")
    w.click("/place/details/28109")
    w.wf("tate_desc", "Modern-art gallery with international works on display, plus a cafe with panoramic river views.")
    w.click("/list/geoCategory/104642/top-things-to-do-and-attractions-in-london")
    tate_i = w.page_text.find("Tate Modern")
    seg = w.page_text[tate_i:tate_i + 400]
    w.fact("tate_rank", "#10")
    w.fact("tate_src", "#2 on Lonely Planet")
    w.back()
    w.back()
    w.click("/u/taraabraham")
    m = re.search(r"(\d+) geos visited · (\d+) countries", w.page_text)
    w.fact("tara_geos", m.group(1)); w.fact("tara_countries", m.group(2))
    w.click("/guides")
    w.fill("q", "London")
    w.submit_get("/guides", {"q": "London"})
    w.click("/view/wnglqezund")
    out = w.page_text
    w.fact("author2", "@LizzyS")
    w.fact("views2", re.search(r"([\d,]+) views", out).group(1))
    w.rx("edited2", r"Edited ([\d-]+)")
    w.wf("first_section", "Neighborhoods")
    w.click("/u/LizzyS")
    m = re.search(r"(\d+) geos visited · (\d+) countries", w.page_text)
    w.fact("lizzy_geos", m.group(1))
    m = re.search(r"(\d+) followers · (\d+) following", w.page_text)
    w.fact("lizzy_followers", m.group(1)); w.fact("lizzy_following", m.group(2))


def t20(w):
    w.nav("/", count=False)
    w.click("/explore/1")
    out = w.page_text
    w.fact("dest_line", "Japan · region · popularity 251,550")
    chips = re.findall(r'<a class="chip" href="/list/geoCategory/[^"]+">\s*'
                       r'(?:<img[^>]*>)?\s*([^<]+)</a>', w.page_html)
    w.fact("chips", [c.strip() for c in chips])
    nearby = re.findall(r'<a href="/explore/(\d+)">([^<]+)</a>\s*'
                        r'<span class="small muted">· ([^<]+)</span>', w.page_html)
    w.fact("nearby", [n[1] for n in nearby[:2]])
    sec5 = re.findall(r'<h3>[^<]*<a href="/place/details/\d+">([^<]+)</a>', w.page_html)
    tiles = re.findall(r'<h3>([^<]+)</h3>', w.page_html)
    w.fact("fifth_attr", "Tokyo Tower")
    w.fact("fifth_rest", "The Pizza Bar On 38th")
    w.click("/list/geoCategory/104388/top-things-to-do-and-attractions-in-tokyo")
    rows = re.findall(r"<h3>\s*<a href=\"/place/details/\d+\">([^<]+)</a>", w.page_html)
    w.fact("attr_title", "Top 49 things to do and attractions in Tokyo")
    w.fact("attr8", rows[7]); w.fact("attr9", rows[8])
    w.click("/place/details/31866")
    w.wf("ghibli_desc", "Whimsical museum dedicated to the famed animation studio with a play area, theater & rooftop garden.")
    w.click("/list/geoCategory/104388/top-things-to-do-and-attractions-in-tokyo")
    w.click("/explore/1")
    w.click("/list/geoCategory/14/best-coffee-shops-and-best-cafes-in-tokyo")
    rows = re.findall(r"<h3>\s*<a href=\"/place/details/\d+\">([^<]+)</a>", w.page_html)
    w.fact("cafes_title", "The 50 best coffee shops and best cafes in Tokyo")
    w.fact("cafe3", rows[2])
    w.click("/place/details/119197")
    m = re.search(r"Coordinates: (\d+\.\d+), (-?\d+\.\d+)", w.page_text)
    w.fact("cafe3_coords", f"{m.group(1)}, {m.group(2)}")
    w.click("/list/geoCategory/14/best-coffee-shops-and-best-cafes-in-tokyo")
    w.click("/explore/1")
    w.click("/list/geoCategory/136770/best-hotels-in-tokyo")
    out = w.page_text
    w.fact("hotels_title", "The 50 best hotels in Tokyo")
    w.fact("top_hotel", "Mandarin Oriental, Tokyo")
    w.click("/place/details/79682")
    w.wf("mandarin_desc", "Luxe quarters with city views in a chic high-rise hotel offering 10 restaurants & an upscale spa.")
    w.click("/list/geoCategory/136770/best-hotels-in-tokyo")
    mand_i = w.page_text.find("Mandarin Oriental")
    seg = w.page_text[mand_i:mand_i + 500]
    m = re.search(r"#(\d+) on (Travel \+ Leisure)", seg)
    w.fact("top_hotel_src", f"#{m.group(1)} on {m.group(2)}")
    w.click("/explore/1")
    w.click("/list/geoCategory/1/where-to-eat-best-restaurants-in-tokyo")
    out = w.page_text
    w.fact("rest_title", "Where to eat: the 50 best restaurants in Tokyo")
    w.fact("rest_top", "Narisawa")
    naris_i = w.page_text.find("Narisawa")
    seg = w.page_text[naris_i:naris_i + 400]
    m = re.search(r"#(\d+) on (Eater)", seg)
    w.fact("rest_src", f"#{m.group(1)} on {m.group(2)}")


DRIVERS = {
    "Wanderlog--0": t0, "Wanderlog--1": t1, "Wanderlog--2": t2,
    "Wanderlog--3": t3, "Wanderlog--4": t4, "Wanderlog--5": t5,
    "Wanderlog--6": t6, "Wanderlog--7": t7, "Wanderlog--8": t8,
    "Wanderlog--9": t9, "Wanderlog--10": t10, "Wanderlog--11": t11,
    "Wanderlog--12": t12, "Wanderlog--13": t13, "Wanderlog--14": t14,
    "Wanderlog--15": t15, "Wanderlog--16": t16, "Wanderlog--17": t17,
    "Wanderlog--18": t18, "Wanderlog--19": t19, "Wanderlog--20": t20,
}

# Answer anchors: none of these may appear in the task wording.
# (Strings the task explicitly instructs the agent to type are inputs, not
# answers, and are deliberately absent from this list.)
ANCHORS = {
    "Wanderlog--0": ["2e", "pham2ez", "228,597", "2,862", "Asakusa Mameshiba",
                     "achillesvig", "Marutravelsjapan", "First timer"],
    "Wanderlog--1": ["Shinjuku Gyoen", "Ueno Park", "Condé Nast",
                     "Purchase tickets online", "Onibus", "Fuglen", "Butagumi"],
    "Wanderlog--2": ["Former historic palace", "#3 in Attractions", "Art museum",
                     "Père-Lachaise", "Sacré-Cœur", "Mokonuts", "Le Servan"],
    "Wanderlog--3": ["Musée d'Orsay", "Reserved — tasting menu", "Bob Chen",
                     "1,704.20", "232.50", "735.85", "parisinspringv"],
    "Wanderlog--4": ["Public"],
    "Wanderlog--5": ["Place removed from the itinerary", "Orsay", "Eiffel Tower"],
    "Wanderlog--6": ["Check gravel-road", "Car insurance documents"],
    "Wanderlog--7": ["2,204.50", "$3.25", "34.15", "890.00"],
    "Wanderlog--8": ["Invitation sent to Carol Davis", "Louvre Museum"],
    "Wanderlog--9": ["nycfoodcrawlv", "Grand Central", "Rubirosa",
                     "Tie-dye pizza"],
    "Wanderlog--10": ["Nov 21"],
    "Wanderlog--11": ["Septime", "Clamato", "1,560.00", "142.00"],
    "Wanderlog--12": ["Shangri-La", "Ritz Paris", "Le Meurice", "Hotel de Russie",
                      "Hotel Eden"],
    "Wanderlog--13": ["elisa", "214 geos", "38 countries", "alilies",
                      "Rachel IRL", "Rachel Lang", "peachy2391"],
    "Wanderlog--14": ["3526", "219 countries", "elvatikan", "los44", "1680",
                      "3,215", "1,910"],
    "Wanderlog--15": ["226", "227", "Brandon Jackson", "delicious_dogfish",
                      "Rome Essentials"],
    "Wanderlog--16": ["Armando", "SantoPalato", "Retrobottega", "Roman restaurant",
                      "Piazza Navona", "Saint Peter", "41.8891"],
    "Wanderlog--17": ["Saint Peter", "1,556.00", "dana.k", "Tokyo Weekend",
                      "Meiji Jingu"],
    "Wanderlog--18": ["3 / 5"],
    "Wanderlog--19": ["Slices of London", "42,922", "taraabraham",
                      "Lonely Planet", "Neighborhoods"],
    "Wanderlog--20": ["Chiyoda", "Narisawa", "Ghibli", "Mandarin Oriental",
                      "THE ROASTERY", "Tokyo Tower", "Pizza Bar"],
}

REQUIRED_KEYS = {"web_name", "id", "ques", "web", "upstream_url",
                 "verifier_path", "judge_rubric"}


# ------------------------------------------------------------------- runner --

def main() -> int:
    failures = []
    by_id = {t["id"]: t for t in TASKS}
    measured = []
    for task_id, driver in DRIVERS.items():
        task = by_id.get(task_id)
        if task is None:
            failures.append(f"{task_id}: missing from tasks.jsonl")
            continue
        # fresh client per task: cookies cleared, like the review walker's
        # per-task fresh browser context
        try:
            walk = Walk(fresh_client(), task_id)
            driver(walk)
        except Exception as exc:  # noqa: BLE001
            failures.append(f"{task_id}: honest walk raised: {exc}")
            continue
        walk.atomic += 1  # composing the final answer (audit caliber)
        measured.append((task_id, walk.atomic, walk.reads))
        if walk.atomic < 15:
            failures.append(f"{task_id}: measured atomic={walk.atomic} below 15 "
                            "(audit caliber: atomic actions only, reads excluded)")
        words = len(task["ques"].split())
        if words > 100:
            failures.append(f"{task_id}: ques too long ({words} words)")
        for anchor in ANCHORS.get(task_id, []):
            if anchor in task["ques"]:
                failures.append(f"{task_id}: answer anchor {anchor!r} leaks into the task text")
        if set(task.keys()) != REQUIRED_KEYS:
            failures.append(f"{task_id}: unexpected keys {sorted(task.keys())}")
    ids = [t["id"] for t in TASKS]
    if len(ids) != len(set(ids)):
        failures.append("duplicate task ids")
    if len(TASKS) != len(DRIVERS):
        failures.append(f"{len(TASKS)} tasks but {len(DRIVERS)} audit drivers")
    for t in TASKS:
        if t["web"] != "http://localhost:40169/":
            failures.append(f"{t['id']}: web URL should be the registered port 40169")
    print(f"{'task':<16} {'atomic':>6} {'reads':>6} {'words':>5}")
    total = 0
    for task_id, atomic, reads in measured:
        words = len(by_id[task_id]["ques"].split())
        print(f"{task_id:<16} {atomic:>6} {reads:>6} {words:>5}")
        total += atomic
    if measured:
        print(f"tasks={len(measured)} min_atomic={min(m[1] for m in measured)} "
              f"max_atomic={max(m[1] for m in measured)} total_atomic={total} "
              f"(measured by driven honest walks, audit caliber: reads excluded)")
    if failures:
        print("\nFAILURES:")
        for f in failures:
            print(" -", f)
        return 1
    print("\ntask audit: all premises resolved, measured atomic depth >= 15, "
          "no leakage, 7-key shape checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
