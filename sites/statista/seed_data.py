"""Build-time / boot-time seeder for the statista mirror.

Loads the tracked source_data/ snapshots (captured from the live
statista.com on 2026-09-26 with Playwright, see provenance.json) into
instance/statista.db. Every seed function early-returns on a populated
database so /reset/statista stays byte-identical.

The upstream statistics split into two families:
- free statistics whose values are public — these keep their real chart
  data (series, categories+values, or table) and render live charts;
- premium statistics whose values are behind the paywall for anonymous
  visitors — these keep their real titles/metadata/summaries and render
  the upstream masked-preview pattern.
"""
from __future__ import annotations

import json
import pathlib
import re

BASE_DIR = pathlib.Path(__file__).resolve().parent
SOURCE = BASE_DIR / "source_data"

# Frozen bcrypt digest for the benchmark password 'TestPass123!' (frozen
# rather than re-generated so the seed DB is byte-reproducible).
BENCHMARK_PASSWORD_DIGEST = (
    "$2b$12$mTNQa9oqZyOoIJBpKN.0p.LVaApMSu9gZnYufEZrciM5QgBN7EM7u"
)

JUNK_CAT_LINES = (
    "view as data table", "the chart has 1 x axis", "the chart has 1 y axis",
)


def _read_json(path):
    return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))


def _stat_files():
    files = {}
    for path in sorted(SOURCE.glob("*_statistics.json")):
        files[path.name.split("_")[0]] = ("statistic", path)
    for path in sorted(SOURCE.glob("*_forecasts.json")):
        files.setdefault(path.name.split("_")[0], ("forecast", path))
    return files


def _clean_categories(cats, values):
    """Strip helper/axis-title lines from harvested category lists."""
    if not cats:
        return []
    out = []
    n_vals = len(values or [])
    for c in cats:
        if not c:
            continue
        low = c.lower().strip()
        if any(low.startswith(j) for j in JUNK_CAT_LINES):
            continue
        out.append(c.strip())
    # when the axis-title line precedes the real categories it is the first
    # entry and there is one more line than values — drop the surplus head
    if n_vals and len(out) > n_vals:
        out = out[len(out) - n_vals:]
    return out


def _real_values_present(rec):
    """Does the harvested record carry visible (non-masked) data values?"""
    series = rec.get("series") or []
    if len(series) >= 3:
        return True
    table = rec.get("table") or []
    tvals = []
    for row in table[1:]:
        for cell in row[1:]:
            if cell and cell not in ("-", "") and not cell.startswith("*"):
                tvals.append(cell)
    if len(tvals) >= 3:
        return True
    cv = rec.get("chart_values") or []
    cc = _clean_categories(rec.get("chart_categories") or [], cv)
    if len(cv) >= 2 and cc and any(c.lower() not in ("view as data table",) for c in cc):
        return True
    return False


def _series_valid(series):
    """A harvested year-series is valid when years run monotonically and sane."""
    try:
        xs = [float(p[0]) for p in series if p[0] is not None]
        ys = [float(p[1]) for p in series if len(p) > 1 and p[1] is not None]
    except (TypeError, ValueError):
        return False
    if len(xs) < 3:
        return False
    asc = xs == sorted(xs)
    desc = xs == sorted(xs, reverse=True)
    lo, hi = min(xs), max(xs)
    if not ((asc or desc) and 1900 <= lo <= 2100 and 1900 <= hi <= 2100):
        return False
    # reject mis-paired runs where every y value also looks like a year
    if ys and all(1900 <= y <= 2100 for y in ys):
        return False
    return True


def _recovered_category_points(rec):
    """Recover a bar chart when harvested categories append a copy of the
    value list after the labels (and sometimes a leading axis title).

    ``_clean_categories`` treats every extra head row as an axis title and
    drops it, which throws away the region names on statistic 256626 and
    leaves an empty chart. This pass strips a trailing value copy first,
    then one leading axis title, and returns points only when the remaining
    labels line up with the values.
    """
    raw = []
    for cat in rec.get("chart_categories") or []:
        if not cat:
            continue
        low = cat.lower().strip()
        if any(low.startswith(junk) for junk in JUNK_CAT_LINES):
            continue
        raw.append(cat.strip())
    values = [str(v).strip() for v in (rec.get("chart_values") or []) if str(v).strip()]
    if len(values) < 2:
        return None
    if len(raw) >= len(values) and raw[-len(values):] == values:
        raw = raw[:-len(values)]
    if len(raw) == len(values) + 1 and not re.fullmatch(r"[-\d.,%\s]+", raw[0] or ""):
        raw = raw[1:]
    if len(raw) != len(values):
        return None
    if any(re.fullmatch(r"[-\d.,%\s]+", cat or "") for cat in raw):
        return None
    points = []
    for cat, value in zip(raw, values):
        try:
            points.append([cat, float(str(value).replace(",", "").rstrip("%"))])
        except (TypeError, ValueError):
            return None
    return points if len(points) >= 2 else None


def _dummy_axis_values(values):
    """500 / 1000 / 1500-style placeholders, not a real chart."""
    nums = []
    for value in values or []:
        try:
            nums.append(float(str(value).replace(",", "")))
        except (TypeError, ValueError):
            return False
    return len(nums) >= 2 and all(n >= 500 and n % 500 == 0 for n in nums)


def _table_has_unmasked_numbers(table):
    for row in table[1:]:
        for cell in row[1:]:
            text = str(cell or "")
            if not text or text == "-" or "*" in text:
                continue
            if re.search(r"\d", text):
                return True
    return False


def _table_outranks_categories(rec, categories):
    """Prefer a published data table over a dummy category chart whose labels
    are a different widget (statistic 439576 stored Windows / Macintosh /
    Chrome OS instead of the country conversion-rate table).

    Real charts are left alone: YouTube Shorts' 1.5 / 2.0 billion usage
    series must not be replaced by the unrelated ranking table on that page.
    """
    table = rec.get("table") or []
    values = rec.get("chart_values") or []
    if len(table) < 3 or not categories or not _dummy_axis_values(values):
        return False
    if not _table_has_unmasked_numbers(table):
        return False
    labels = set()
    for row in table[1:]:
        if row and row[0]:
            labels.add(str(row[0]).strip().casefold())
    if any(str(c).strip().casefold() in labels for c in categories):
        return False
    return (len(table) - 1) > len(categories)


def _points_from_table(table):
    tvals = []
    for row in table[1:]:
        for cell in row[1:]:
            if cell and cell not in ("-", "") and not str(cell).startswith("*"):
                tvals.append(cell)
    if len(tvals) < 3:
        return None
    pts = []
    for row in table[1:]:
        if len(row) == 2:
            try:
                pts.append([row[0], float(str(row[1]).replace(",", ""))])
            except (TypeError, ValueError):
                continue
    return pts, table, "bar" if pts else "line"


def _norm_points(rec):
    """Normalize chart data into [[x, y], ...] plus optional table rows."""
    series = rec.get("series") or []
    cv = rec.get("chart_values") or []
    cc = _clean_categories(rec.get("chart_categories") or [], cv)
    if _table_outranks_categories(rec, cc):
        from_table = _points_from_table(rec.get("table") or [])
        if from_table:
            return from_table
    # categories must be labels, not numbers: drop numeric-looking entries
    # (harvested blocks sometimes append the value list to the category list)
    cc_labels = [c for c in cc
                 if c and not re.fullmatch(r"[-\d.,%\s]+", c)]
    if len(cc_labels) == len(cv) and len(cv) >= 2:
        cc = cc_labels
    cats_match = (len(cc) == len(cv) and len(cv) >= 2
                  and all(not re.fullmatch(r"[-\d.,%\s]+", c or "") for c in cc))
    if cats_match and not _series_valid(series):
        # category chart (bar) with clean cats — prefer it over a broken series
        pts = []
        for c, v in zip(cc, cv):
            try:
                pts.append([c, float(str(v).replace(",", "").rstrip("%"))])
            except (TypeError, ValueError):
                cats_match = False
                break
        if cats_match and len(pts) >= 2:
            return pts, [], "bar"
    if len(series) >= 3 and _series_valid(series):
        pts = []
        for row in series:
            if isinstance(row, (list, tuple)) and len(row) >= 2:
                x, y = row[0], row[1]
                try:
                    x = int(x)
                except (TypeError, ValueError):
                    x = str(x)
                if y is None:
                    pts.append([x, None])
                else:
                    try:
                        pts.append([x, round(float(y), 2)])
                    except (TypeError, ValueError):
                        continue
        if len(pts) >= 3:
            try:
                xs = [p[0] for p in pts]
                if all(isinstance(x, int) for x in xs) and xs[0] > xs[-1]:
                    pts.reverse()   # upstream tables list newest year first
            except Exception:  # noqa: BLE001
                pass
            return pts, [], "line"
    cv = rec.get("chart_values") or []
    cc = _clean_categories(rec.get("chart_categories") or [], cv)
    if len(cc) == len(cv) + 1 and len(cv) >= 2:
        # the leading non-numeric line is the y-axis title, not a category
        first = cc[0]
        if not re.fullmatch(r"[-\d.,%\s]+", first):
            cc = cc[1:]
    if len(cv) >= 2 and len(cc) == len(cv) \
            and all(not re.fullmatch(r"[-\d.,%\s]+", c or "") for c in cc):
        pts = []
        for c, v in zip(cc, cv):
            try:
                pts.append([c, float(str(v).replace(",", "").rstrip("%"))])
            except (TypeError, ValueError):
                continue
        if len(pts) >= 2:
            return pts, [], "bar"
    recovered = _recovered_category_points(rec)
    if recovered:
        return recovered, [], "bar"
    table = rec.get("table") or []
    tvals = []
    for row in table[1:]:
        for cell in row[1:]:
            if cell and cell not in ("-", "") and not cell.startswith("*"):
                tvals.append(cell)
    if len(tvals) >= 3:
        # keep the table rows for the table view; derive bar points from
        # two-column tables (Characteristic | value)
        pts = []
        for row in table[1:]:
            if len(row) == 2:
                try:
                    pts.append([row[0], float(row[1].replace(",", ""))])
                except (TypeError, ValueError):
                    continue
        return pts, table, "bar" if pts else "line"
    return [], [], "line"


def _value_label(rec):
    m = re.search(r'The chart has 1 Y axis displaying ([^.]+?)\. Data ranges',
                  rec.get("title") or "")
    cats = rec.get("chart_categories") or []
    for c in cats:
        if c and not any(c.lower().startswith(j) for j in JUNK_CAT_LINES):
            # the axis-title line precedes the categories
            low = c.lower()
            if not re.fullmatch(r"(19|20)\d\d¹?\*?", low):
                return c.strip()
    table = rec.get("table") or []
    if table and table[0] and len(table[0]) >= 2:
        return table[0][1]
    return ""


def seed_database():
    if db is None:
        return
    if db.session.execute(db.text("SELECT COUNT(*) FROM statistics")).scalar():
        return

    # ---- statistics --------------------------------------------------------
    stat_meta = {}
    for sid, (ctype, path) in _stat_files().items():
        rec = _read_json(path)
        sid_int = int(sid)
        url = rec.get("url") or ""
        slug = url.rstrip("/").split("/")[-1] if url else f"statistic-{sid}"
        pts, table, chart_type = _norm_points(rec)
        premium = not _real_values_present(rec) or slug in PREMIUM_OVERRIDE
        cats = _clean_categories(rec.get("chart_categories") or [],
                                 rec.get("chart_values") or [])
        label = ""
        cv2 = rec.get("chart_values") or []
        raw_cats = [c for c in (rec.get("chart_categories") or [])
                    if c and not any(c.lower().startswith(j) for j in JUNK_CAT_LINES)]
        if len(cv2) >= 2 and len(raw_cats) == len(cv2) + 1:
            first = raw_cats[0]
            if first and not re.fullmatch(r"[-\d.,%\s]+", first):
                label = first.strip()   # the y-axis title line
        if not label:
            for c in cats:
                low = c.lower()
                if not any(low.startswith(j) for j in JUNK_CAT_LINES) \
                        and not re.fullmatch(r"(19|20)\d\d¹?\*?(\d\d/\d\d)?", low):
                    label = c.strip()
                    break
        raw_table = rec.get("table") or []
        if not label and raw_table and raw_table[0] and len(raw_table[0]) >= 2:
            label = raw_table[0][1]
        if sid_int in LABEL_OVERRIDE:
            label = LABEL_OVERRIDE[sid_int]
        if not label and (rec.get("series") or []):
            label = rec.get("title") or ""
        related = []
        for href in rec.get("related") or []:
            m = re.search(r"/(?:statistics|forecasts)/(\d+)/", href)
            if m:
                rid = int(m.group(1))
                if rid != sid_int and rid not in related:
                    related.append(rid)
        breadcrumb = rec.get("breadcrumb") or []
        industry_slug = ""
        if breadcrumb:
            name = breadcrumb[0]
            industry_slug = INDUSTRY_BY_NAME.get(name, "")
        stat_meta[sid_int] = dict(
            id=sid_int, slug=slug, title=(rec.get("title") or "").strip(),
            value_label=label, content_type=ctype,
            region=(rec.get("region") or "Worldwide").strip(),
            last_update=(rec.get("last_update") or rec.get("release_date") or "").strip(),
            survey_period=(rec.get("survey_period") or "").strip(),
            source=(rec.get("source") or "").strip(),
            details=(rec.get("details") or "").strip(),
            summary=(rec.get("summary") or rec.get("meta_description") or "").strip(),
            description=(rec.get("description") or "").strip(),
            premium=premium, chart_type=chart_type,
            points_json=json.dumps(pts) if pts else "",
            table_json=json.dumps(table) if table else "",
            industry_slug=industry_slug,
            breadcrumb_json=json.dumps(breadcrumb) if breadcrumb else "",
            related_json=json.dumps(related[:20]) if related else "",
            has_thumb=f"stat_{sid}_thumb.png" in THUMBS,
            has_hero=f"stat_{sid}_hero.png" in THUMBS,
        )

    # topic membership: which topic lists each stat
    topic_picks = {}
    topic_recs = {}
    for path in sorted(SOURCE.glob("topic_*.json")):
        rec = _read_json(path)
        tid = int(path.name.split("_")[1].split(".")[0])
        topic_recs[tid] = rec
        for title, href in (rec.get("editor_picks") or []):
            m = re.search(r"/(?:statistics|forecasts)/(\d+)/", href)
            if m:
                topic_picks.setdefault(int(m.group(1)), tid)
    for tid, rec in topic_recs.items():
        for title, href in (rec.get("recommended_stats") or []):
            m = re.search(r"/(?:statistics|forecasts)/(\d+)/", href)
            if m:
                sid = int(m.group(1))
                if sid not in topic_picks:
                    topic_picks[sid] = tid

    for sid_int, meta in stat_meta.items():
        meta["topic_id"] = topic_picks.get(sid_int)
        db.session.execute(db.text(
            "INSERT INTO statistics (id, slug, title, value_label, content_type,"
            " region, last_update, survey_period, publisher, source, details,"
            " summary, description, premium, chart_type, points_json, table_json,"
            " topic_id, industry_slug, breadcrumb_json, related_json, has_thumb,"
            " has_hero) VALUES (:id, :slug, :title, :value_label, :content_type,"
            " :region, :last_update, :survey_period, 'Statista Research Department',"
            " :source, :details, :summary, :description, :premium, :chart_type,"
            " :points_json, :table_json, :topic_id, :industry_slug, :breadcrumb_json,"
            " :related_json, :has_thumb, :has_hero)"), meta)
    db.session.commit()

    # ---- topics ------------------------------------------------------------
    # recommended stats grouped by segment come from the harvested page order:
    # the upstream page lists segments (Overview / Regional overview / ...) as
    # headings interleaved with the stat titles.
    for tid, rec in topic_recs.items():
        url = rec.get("url") or ""
        slug = url.rstrip("/").split("/")[-1] if url else f"topic-{tid}"
        picks = []
        for _t, href in rec.get("editor_picks") or []:
            m = re.search(r"/(?:statistics|forecasts)/(\d+)/", href)
            if m and int(m.group(1)) in stat_meta and int(m.group(1)) not in picks:
                picks.append(int(m.group(1)))
        recs = []
        for _t, href in rec.get("recommended_stats") or []:
            m = re.search(r"/(?:statistics|forecasts)/(\d+)/", href)
            if m and int(m.group(1)) in stat_meta and int(m.group(1)) not in picks \
                    and int(m.group(1)) not in recs:
                recs.append(int(m.group(1)))
        # report on the topic: match a harvested report by name, or by an
        # exact title match against the topic name when the harvest omitted
        # the sidebar module (TikTok, Video gaming worldwide).
        report_id = None
        rep_line = " ".join(rec.get("report") or [])
        if rep_line:
            for rid, rrec in report_recs().items():
                if rrec.get("title") and rrec["title"].lower() in rep_line.lower():
                    report_id = rid
                    break
        if report_id is None:
            topic_name = (rec.get("title") or "").split(" - ")[0].strip().casefold()
            matches = [rid for rid, rrec in report_recs().items()
                       if (rrec.get("title") or "").strip().casefold() == topic_name]
            if len(matches) == 1:
                report_id = matches[0]
        db.session.execute(db.text(
            "INSERT INTO topics (id, slug, name, description, published_by,"
            " published_date, editor_picks_json, recommended_json, key_insights_json,"
            " key_figures_json, related_topics_json, report_id) VALUES"
            " (:id, :slug, :name, :description, :published_by, :published_date,"
            " :picks, :recs, :ki, :kf, :rt, :report_id)"), dict(
                id=tid, slug=slug, name=(rec.get("title") or "").strip(),
                description=(rec.get("description") or "").strip(),
                published_by="Lionel Sujay Vailshery",
                published_date="Jun 10, 2026",
                picks=json.dumps(picks), recs=json.dumps(recs),
                ki=json.dumps(rec.get("key_insights") or []),
                kf=json.dumps(rec.get("key_figures") or []),
                rt=json.dumps(rec.get("related_topics") or []),
                report_id=report_id))
    db.session.commit()

    # ---- reports -----------------------------------------------------------
    for rid, rec in report_recs().items():
        url = rec.get("url") or ""
        slug = url.rstrip("/").split("/")[-1] if url else f"report-{rid}"
        details = rec.get("details") or {}
        stat_ids = []
        for _t, href in rec.get("stat_links") or []:
            m = re.search(r"/(?:statistics|forecasts)/(\d+)/", href)
            if m and int(m.group(1)) in stat_meta and int(m.group(1)) not in stat_ids:
                stat_ids.append(int(m.group(1)))
        price = rec.get("price_usd") or ""
        if not price:
            m = re.search(r"\$([\d,]+)", details.get("Price") or "")
            price = f"${m.group(1)} USD" if m else "$595 USD"
        db.session.execute(db.text(
            "INSERT INTO reports (id, slug, title, subtitle, description,"
            " details_json, toc_json, stat_ids_json, has_cover, price) VALUES"
            " (:id, :slug, :title, :subtitle, :description, :details, :toc,"
            " :stat_ids, :has_cover, :price)"), dict(
                id=rid, slug=slug, title=(rec.get("title") or "").strip(),
                subtitle="", description=(rec.get("description") or "").strip(),
                details=json.dumps(details),
                toc=json.dumps((rec.get("toc") or [])[1:] if (rec.get("toc") or [None])[0] == "Content" else rec.get("toc") or []),
                stat_ids=json.dumps(stat_ids),
                has_cover=f"report_{rid}_cover.png" in THUMBS,
                price=price))
    db.session.commit()

    # ---- industries --------------------------------------------------------
    industries = _read_json(SOURCE / "industries.json")
    stat_by_industry = {}
    for meta in stat_meta.values():
        if meta["industry_slug"]:
            stat_by_industry.setdefault(meta["industry_slug"], []).append(meta["id"])
    for ind in industries:
        trending = stat_by_industry.get(ind["slug"], [])[:10]
        db.session.execute(db.text(
            "INSERT INTO industries (id, slug, name, subs_json, trending_json,"
            " definition) VALUES (:id, :slug, :name, :subs, :trending,"
            " :definition)"), dict(
                id=ind["id"], slug=ind["slug"], name=ind["name"],
                subs=json.dumps(ind["subs"]), trending=json.dumps(trending),
                definition=f"Statistics and facts about the {ind['name']} "
                           f"industry, aggregated from official sources and "
                           f"studies."))
    db.session.commit()

    # ---- outlook markets ---------------------------------------------------
    # Two source families: mob_*.json (mobility, captured first) and
    # seg_<segment>__<path>.json (the other eight segments).
    outlook_content = _read_json(SOURCE / "outlook_market_content.json")
    outlook_files = sorted(SOURCE.glob("mob_*.json")) + sorted(SOURCE.glob("seg_*.json"))
    for path in outlook_files:
        rec = _read_json(path)
        fname = path.stem
        if fname.startswith("mob_"):
            segment = "mobility"
        else:
            segment = fname.split("__")[0].replace("seg_", "", 1).replace("_", "-", 1)
        url = rec.get("url") or ""
        # /outlook/<xmo>/<category>/<market>/<region>/ | /outlook/<xmo>/<market>/<region>/
        parts = url.rstrip("/").split("/")
        region_raw = parts[-1] if len(parts) >= 2 else "worldwide"
        region = {"worldwide": "Worldwide", "united-states": "United States"}.get(region_raw, region_raw.capitalize())
        if len(parts) >= 4:
            category_slug, slug = parts[-3], parts[-2]
        else:
            category_slug, slug = "", parts[-2]
        category_name = category_slug.replace("-", " ").title() if category_slug else ""
        parent = category_slug
        content = outlook_content.get(f"{segment}|{category_slug}|{slug}|{region}", {})
        key_regions = rec.get("key_regions") or []
        key_regions = [r for r in key_regions if r not in ("Currency",)
                       and not r.startswith("USD") and not r.startswith("(")][:5]
        db.session.execute(db.text(
            "INSERT INTO outlook_markets (id, slug, category_slug, category_name,"
            " name, region, segment, revenue_2026, revenue_change, highlights_json,"
            " key_regions_json, definition, analyst_opinion, in_scope_json,"
            " out_scope_json, parent_slug) VALUES (:id, :slug, :cs, :cn, :name,"
            " :region, :segment, :rev, :revchg, :hl, :kr, :definition, :ao,"
            " :ins, :outs, :parent)"), dict(
                id=OUTLOOK_IDS.get(fname, hash(fname) % 100000),
                slug=slug, cs=category_slug, cn=category_name,
                name=(rec.get("title") or "").replace(" - Worldwide", "").replace(" - United States", "").strip(),
                region=region, segment=segment,
                rev=rec.get("revenue_2026") or "",
                revchg=rec.get("revenue_change_2026") or "",
                hl=json.dumps(rec.get("highlights") or []),
                kr=json.dumps(key_regions),
                definition=(content.get("definition") or rec.get("definition") or "").strip(),
                ao=(content.get("analyst_opinion") or rec.get("analyst_opinion") or "").strip(),
                ins=json.dumps(rec.get("in_scope") or []),
                outs=json.dumps(rec.get("out_scope") or []),
                parent=parent))
    db.session.commit()


_report_cache = None


def report_recs():
    global _report_cache
    if _report_cache is None:
        _report_cache = {}
        for path in sorted(SOURCE.glob("report_*.json")):
            rec = _read_json(path)
            rid = int(path.name.split("_")[1].split(".")[0])
            _report_cache[rid] = rec
    return _report_cache


PREMIUM_OVERRIDE = set()  # ids forced premium despite visible values

# y-axis labels for charts whose harvested axis line was lost (hand-verified
# against the upstream pages).
LABEL_OVERRIDE = {
    209641: "Crude oil price per barrel (USD)",
    1330092: "Annual inflation rate",
    237917: "Unemployment rate",
    256626: "Inflation rate compared with the previous year",
    1294062: "Growth",
    1552183: "Market value in billion U.S. dollars",
    1092819: "Market size in billion U.S. dollars",
    501853: "Total prize pool in million U.S. dollars",
    517940: "Prize pool in million U.S. dollars",
    578364: "Audience in millions",
    439576: "Conversion rate",
    267233: "Capacity in gigawatts",
    1394199: "Capacity in gigawatts",
    1044012: "Number of users in millions",
    272014: "Number of active users in millions",
    268173: "Projected GDP in trillion USD (in current prices)",
}

INDUSTRY_BY_NAME = {
    "Economy & Politics": "economy-politics",
    "Energy & Environment": "energy-environment",
    "Technology & Telecommunications": "technology-telecommunications",
    "Internet": "internet",
    "Media": "media",
    "Consumer Goods & FMCG": "consumer-goods-fmcg",
    "E-Commerce": "e-commerce",
    "Health, Pharma & Medtech": "health-pharma-medtech",
    "Transportation & Logistics": "transportation-logistics",
    "Travel, Tourism & Hospitality": "travel-tourism-hospitality",
    "Advertising & Marketing": "advertising-marketing",
    "Finance & Insurance": "finance-insurance",
    "Retail & Trade": "retail-trade",
    "Society": "society",
    "Sports & Recreation": "sports-recreation",
}

OUTLOOK_IDS = {}
_outlook_i = 50000
if SOURCE.exists():
    for _p in sorted(SOURCE.glob("mob_*.json")) + sorted(SOURCE.glob("seg_*.json")):
        OUTLOOK_IDS[_p.stem] = _outlook_i
        _outlook_i += 1

THUMBS = set()
_img_dir = BASE_DIR / "static" / "images"
if _img_dir.exists():
    THUMBS = {p.name for p in _img_dir.iterdir() if p.is_file()}

db = None  # injected by app.py before seed_database() runs


def seed_benchmark_users():
    if db is None:
        return
    if db.session.execute(db.text(
            "SELECT COUNT(*) FROM users WHERE email = 'alice.j@test.com'")).scalar():
        return
    users = [
        ("alice_j", "alice.j@test.com", "Alice Johnson", "Personal"),
        ("bob_c", "bob.c@test.com", "Bob Chen", "Basic"),
        ("carol_d", "carol.d@test.com", "Carol Davis", "Professional"),
        ("david_k", "david.k@test.com", "David Kim", "Starter"),
    ]
    ids = {}
    for username, email, display, account_type in users:
        db.session.execute(db.text(
            "INSERT INTO users (email, username, display_name, password_hash,"
            " account_type, company, created_at) VALUES (:e, :u, :d, :p, :a,"
            " 'Benchmark Labs', '2026-05-14 09:30:00')"), dict(
                e=email, u=username, d=display,
                p=BENCHMARK_PASSWORD_DIGEST, a=account_type))
        db.session.commit()
        row = db.session.execute(db.text(
            "SELECT id FROM users WHERE email = :e"), {"e": email}).fetchone()
        ids[username] = row[0]

    # favorites: alice 5 stats, bob 3, carol 4, david 2
    favs = {
        "alice_j": [256598, 272014, 1474143, 268173, 276629],
        "bob_c": [263710, 1092819, 195768],
        "carol_d": [256598, 541390, 1394199, 267233],
        "david_k": [276629, 1602855],
    }
    day = 0
    for username, stat_ids in favs.items():
        for sid in stat_ids:
            day += 1
            db.session.execute(db.text(
                "INSERT INTO favorites (user_id, stat_id, created_at) VALUES"
                " (:u, :s, :c)"), dict(u=ids[username], s=sid,
                c=f"2026-06-{(day % 20) + 1:02d} 10:00:00"))
    # report favorites
    db.session.execute(db.text(
        "INSERT INTO favorites (user_id, report_id, created_at) VALUES"
        " (:u, :r, '2026-06-18 15:20:00')"),
        dict(u=ids["carol_d"], r=206237))
    db.session.commit()

    # downloads: alice 3 (premium ok), bob 2 (free only), carol 4 + 1 report, david 2
    dls = {
        "alice_j": [(256598, "png"), (272014, "xls"), (1474143, "png")],
        "bob_c": [(263710, "png"), (279777, "pdf")],
        "carol_d": [(256598, "png"), (268173, "xls"), (1394199, "png"), (267233, "ppt")],
        "david_k": [(276629, "png"), (1602855, "pdf")],
    }
    day = 0
    for username, items in dls.items():
        for sid, fmt in items:
            day += 1
            db.session.execute(db.text(
                "INSERT INTO download_events (user_id, stat_id, fmt, created_at)"
                " VALUES (:u, :s, :f, :c)"), dict(u=ids[username], s=sid, f=fmt,
                c=f"2026-07-{(day % 20) + 1:02d} 11:30:00"))
    # carol's report download (Professional)
    db.session.execute(db.text(
        "INSERT INTO download_events (user_id, report_id, fmt, created_at)"
        " VALUES (:u, :r, 'pdf', '2026-07-08 16:45:00')"),
        dict(u=ids["carol_d"], r=206237))
    db.session.commit()


if __name__ == "__main__":
    import os
    import shutil
    import sys
    # The Dockerfile seed gate wipes instance/ and instance_seed/ before
    # rerunning this script, so the instance directory must be (re)created
    # here before the app engine opens instance/statista.db (same contract
    # as the mta / imgur / instructure build-generated seeds).
    os.makedirs(BASE_DIR / "instance", exist_ok=True)
    sys.path.insert(0, str(BASE_DIR))
    # Importing the app module runs the module-level bootstrap
    # (db.create_all() + seed_database() + seed_benchmark_users()) under
    # PYTHONHASHSEED=0, deterministically producing instance/statista.db.
    from app import app  # noqa: E402,F401
    with app.app_context():
        seed_database()
        seed_benchmark_users()
    seed_dir = BASE_DIR / "instance_seed"
    seed_dir.mkdir(exist_ok=True)
    shutil.copyfile(BASE_DIR / "instance" / "statista.db",
                    seed_dir / "statista.db")
    print("seed complete; copied instance/statista.db to instance_seed/statista.db")
