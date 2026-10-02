#!/usr/bin/env python3
"""Deterministic seed builder for the yahoo_finance mirror.

Everything materialized here comes from the tracked source_data/*.json
snapshots captured from finance.yahoo.com on 2026-10-01 UTC (see
provenance.json) in a fixed, sorted order. The four benchmark accounts and
their watchlists / price alerts are authored fixtures following the
u_s_customs / nyse / disney precedent: every symbol they reference is a
real captured upstream quote, and every timestamp is a frozen constant so
the SQLite output is byte-reproducible (PYTHONHASHSEED=0).
"""
import json
import os
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
SOURCE = os.path.join(HERE, 'source_data')

BENCHMARK_HASH = (
    '$2b$12$qSds4Mr9Wo7VwPWLhompEer88SuxxXFDp31P9etY6v7nfRctNO7B.')
MIRROR_TS = '2026-09-30'
EDT_OFFSET = -4  # hours; the snapshot week sits in America/New_York EDT

MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July',
          'August', 'September', 'October', 'November', 'December']


def _load(name):
    with open(os.path.join(SOURCE, name), encoding='utf-8') as f:
        return json.load(f)


def _num(value):
    if value is None:
        return None
    if isinstance(value, dict):
        value = value.get('raw')
        if value is None:
            return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _int(value):
    n = _num(value)
    return int(n) if n is not None else None


def _raw(value):
    if isinstance(value, dict):
        return value.get('raw')
    return value


def _epoch_date(value):
    n = _num(value)
    if n is None or n <= 0:
        return None
    dt = datetime(1970, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=n)
    return dt.strftime('%Y-%m-%d')


def _epoch_edt(value):
    """Render an epoch the way the live pages do (wall clock in EDT)."""
    n = _num(value)
    if n is None or n <= 0:
        return None
    dt = datetime(1970, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=n)
    dt = dt + timedelta(hours=EDT_OFFSET)
    hour = dt.hour
    ampm = 'AM' if hour < 12 else 'PM'
    h12 = hour % 12 or 12
    mins = f'{dt.minute:02d}'
    secs = f'{dt.second:02d}'
    return (f'{MONTHS[dt.month - 1]} {dt.day} at '
            f'{h12}:{mins}:{secs} {ampm} EDT')


def _pct(fraction):
    """Yahoo stores margins/yields/holdings as fractions; store percent."""
    n = _num(fraction)
    return n * 100 if n is not None else None


def seed_quotes(db):
    snapshot = _load('quote_snapshot.json')
    details = _load('quote_details.json')
    presets = _load('screener_presets.json')

    # sector/industry/logo enrichment from the predefined-screen records
    enrich = {}
    for scr_id in sorted(presets.keys()):
        for row in presets[scr_id]['quotes']:
            sym = row.get('ticker') or row.get('symbol')
            if not sym:
                continue
            rec = enrich.setdefault(sym, {})
            if row.get('sector') and not rec.get('sector'):
                rec['sector'] = row.get('sector')
            if row.get('industry') and not rec.get('industry'):
                rec['industry'] = row.get('industry')
            if row.get('logoUrl') and not rec.get('logo'):
                rec['logo'] = row.get('logoUrl')

    for row in sorted(snapshot, key=lambda r: r['symbol']):
        sym = row['symbol']
        det = details.get(sym) or {}
        profile = det.get('assetProfile') or {}
        summary_profile = det.get('summaryProfile') or {}
        summary = det.get('summaryDetail') or {}
        keys = det.get('defaultKeyStatistics') or {}
        fin = det.get('financialData') or {}
        cal = det.get('calendarEvents') or {}
        rec = enrich.get(sym) or {}

        sector = profile.get('sector') or summary_profile.get('sector') \
            or rec.get('sector')
        industry = profile.get('industry') or summary_profile.get('industry') \
            or rec.get('industry')
        description = (profile.get('businessSummary')
                       or summary_profile.get('longBusinessSummary'))
        address = profile.get('address') or {}
        earnings = (cal.get('earnings') or {})

        from app import Quote
        q = Quote(
            symbol=sym,
            short_name=row.get('shortName') or row.get('displayName'),
            long_name=row.get('longName') or row.get('displayName'),
            quote_type=row.get('quoteType') or 'EQUITY',
            exchange=row.get('exchange'),
            full_exchange=row.get('fullExchangeName'),
            currency=row.get('currency') or 'USD',
            market_state=row.get('marketState'),
            quote_time=_epoch_edt(row.get('regularMarketTime')),
            price=_num(row.get('regularMarketPrice')),
            change=_num(row.get('regularMarketChange')),
            change_pct=_num(row.get('regularMarketChangePercent')),
            prev_close=_num(row.get('regularMarketPreviousClose')),
            open=_num(row.get('regularMarketOpen')),
            bid=_num(row.get('bid')),
            ask=_num(row.get('ask')),
            bid_size=_int(row.get('bidSize')),
            ask_size=_int(row.get('askSize')),
            day_low=_num(row.get('regularMarketDayLow')),
            day_high=_num(row.get('regularMarketDayHigh')),
            volume=_num(row.get('regularMarketVolume')),
            avg_vol_3m=_num(row.get('averageDailyVolume3Month')),
            market_cap=_num(row.get('marketCap')),
            pe_ttm=_num(row.get('trailingPE')),
            pe_forward=_num(row.get('forwardPE')),
            peg_ratio=_num(keys.get('pegRatio')),
            eps_ttm=_num(row.get('epsTrailingTwelveMonths')),
            eps_forward=_num(row.get('epsForward')),
            price_book=_num(row.get('priceToBook')),
            book_value=_num(row.get('bookValue')),
            # The quote page renders dividend fields from summaryDetail
            # (upstream shows "--" when the module carries no data — e.g.
            # foreign ADRs — so no v7 fallback here).
            div_rate=_num(summary.get('dividendRate')),
            div_yield=_pct(summary.get('dividendYield')),
            payout_ratio=_pct(summary.get('payoutRatio')),
            exdiv_date=_epoch_date(summary.get('exDividendDate')),
            beta=_num(summary.get('beta') or keys.get('beta')),
            wk52_low=_num(row.get('fiftyTwoWeekLow')),
            wk52_high=_num(row.get('fiftyTwoWeekHigh')),
            wk52_change_pct=_num(row.get('fiftyTwoWeekChangePercent')),
            day50_avg=_num(row.get('fiftyDayAverage')),
            day200_avg=_num(row.get('twoHundredDayAverage')),
            profit_margin=_pct(fin.get('profitMargins')),
            operating_margin=_pct(fin.get('operatingMargins')),
            roe=_pct(fin.get('returnOnEquity')),
            roa=_pct(fin.get('returnOnAssets')),
            revenue=_num(fin.get('totalRevenue')),
            revenue_growth=_pct(fin.get('revenueGrowth')),
            gross_profit=_num(fin.get('grossProfits')),
            ebitda=_num(fin.get('ebitda')),
            total_cash=_num(fin.get('totalCash')),
            total_debt=_num(fin.get('totalDebt')),
            debt_equity=_num(fin.get('debtToEquity')),
            current_ratio=_num(fin.get('currentRatio')),
            shares_outstanding=_num(row.get('sharesOutstanding')
                                   or keys.get('sharesOutstanding')),
            held_insiders=_pct(keys.get('heldPercentInsiders')),
            held_institutions=_pct(keys.get('heldPercentInstitutions')),
            target_mean=_num(fin.get('targetMeanPrice')),
            recommendation=fin.get('recommendationKey'),
            rec_mean=_num(fin.get('recommendationMean')),
            num_analysts=_int(fin.get('numberOfAnalystOpinions')),
            earnings_date=_epoch_date(
                ((earnings.get('earningsDate') or [None])[0])),
            fiscal_year_end=_epoch_date(keys.get('lastFiscalYearEnd')),
            sector=sector,
            industry=industry,
            website=(profile.get('website') or summary_profile.get('website')),
            country=(profile.get('country')
                     or summary_profile.get('country')),
            employees=_int(profile.get('fullTimeEmployees')
                           or summary_profile.get('fullTimeEmployees')),
            city=profile.get('city') or summary_profile.get('city'),
            state=profile.get('state') or summary_profile.get('state'),
            phone=profile.get('phone') or summary_profile.get('phone'),
            description=description,
            logo_url=rec.get('logo'),
        )
        db.session.add(q)

        hist = det.get('incomeStatementHistory') or {}
        for stmt in sorted(hist.get('incomeStatementHistory') or [],
                           key=lambda s: str(s.get('endDate', {}).get('fmt')
                                             or '')):
            db.session.add(db_session_income(sym, stmt))
    db.session.commit()


def db_session_income(sym, stmt):
    from app import IncomeRow
    end = stmt.get('endDate') or {}
    year_end = end.get('fmt') if isinstance(end, dict) else None
    if not year_end:
        year_end = _epoch_date(end.get('raw')) if isinstance(end, dict) else _raw(end)
    return IncomeRow(
        symbol=sym,
        year_end=year_end or '',
        revenue=_num(stmt.get('totalRevenue')),
        cost_revenue=_num(stmt.get('costOfRevenue')),
        gross_profit=_num(stmt.get('grossProfit')),
        operating_income=_num(stmt.get('operatingIncome')),
        net_income=_num(stmt.get('netIncome')),
        ebitda=_num(stmt.get('ebitda')),
        diluted_eps=_num(stmt.get('dilutedEPS')),
        rd_expense=_num(stmt.get('researchDevelopment')),
    )


def seed_chart_points(db):
    from app import ChartPoint
    series = _load('chart_series.json')
    for sym in sorted(series.keys()):
        chart = series[sym]
        if not chart:
            continue
        stamps = chart.get('timestamp') or []
        closes = ((chart.get('indicators') or {}).get('quote') or [{}])[0] \
            .get('close') or []
        for ts, close in zip(stamps, closes):
            if close is None:
                continue
            dt = datetime(1970, 1, 1, tzinfo=timezone.utc) \
                + timedelta(seconds=int(ts))
            db.session.add(ChartPoint(
                symbol=sym, bar_date=dt.strftime('%Y-%m-%d'),
                close=float(close)))
    db.session.commit()


def seed_earnings(db):
    from app import EarningsEvent
    windows = _load('earnings_calendar.json')
    rows = []
    for window in sorted(windows.keys()):
        for rec in windows[window]:
            rows.append(rec)
    # dedupe on (ticker, start_dt)
    seen = {}
    for rec in rows:
        seen[(rec.get('ticker'), rec.get('startdatetime'))] = rec

    def et_day(rec):
        """The reporting day as the upstream calendar groups it (the
        company's local exchange-day, not the UTC day)."""
        try:
            dt = datetime.strptime(rec['startdatetime'][:19],
                                    '%Y-%m-%dT%H:%M:%S')
            dt = dt - timedelta(milliseconds=rec.get('gmtOffsetMilliSeconds')
                                 or 0)
            return dt.strftime('%Y-%m-%d')
        except (KeyError, ValueError, TypeError):
            return rec['startdatetime'][:10]

    for key in sorted(seen.keys(), key=lambda k: (k[1], k[0])):
        rec = seen[key]
        db.session.add(EarningsEvent(
            ticker=rec.get('ticker') or '',
            company=rec.get('companyshortname'),
            event_name=rec.get('eventname') or 'Earnings Announcement',
            start_dt=(rec.get('startdatetime') or '')[:19] + 'Z',
            day=et_day(rec),
            time_type=rec.get('startdatetimetype'),
            date_is_estimate=1 if rec.get('dateisestimate') else 0,
            eps_estimate=_num(rec.get('epsestimate')),
            eps_actual=_num(rec.get('epsactual')),
            surprise_pct=_num(rec.get('epssurprisepct')),
            market_cap=_num(rec.get('intradaymarketcap')),
            tz=rec.get('timeZoneShortName'),
        ))
    db.session.commit()


def _article_thumb(record):
    """Best thumbnail URL for an article record + its local name."""
    from app import img_name
    for url in (record.get('thumb_resized'), record.get('thumb_original'),
                record.get('thumb_url')):
        if url and img_name(url):
            return url, img_name(url)
    for res in record.get('thumbnail') or []:
        url = res.get('url')
        if url and img_name(url):
            return url, img_name(url)
    return None, None


def seed_news(db):
    from app import NewsArticle
    import hashlib

    articles = _load('news_articles.json')
    symbol_news = _load('symbol_news.json')
    bodies_path = os.path.join(SOURCE, 'news_bodies.json')
    bodies = json.load(open(bodies_path, encoding='utf-8')) \
        if os.path.exists(bodies_path) else {}

    by_upstream = {}
    for art in articles:
        url = art['canonical_url']
        tickers = sorted({t for t in art.get('tickers') or [] if t})
        topics = sorted(art.get('topics') or [])
        thumb_url, thumb_name = _article_thumb(art)
        by_upstream[url] = {
            'key': art['key'],
            'title': art.get('title'),
            'summary': art.get('summary'),
            'provider': art.get('provider'),
            'provider_id': art.get('provider_id'),
            'hosted': 1 if (url.split('//')[1] or '').split('/')[0].endswith(
                'finance.yahoo.com') else 0,
            'live_blog': 1 if art.get('live_blog') else 0,
            'pub_time': (art.get('pub_date') or '')[:19] + 'Z',
            'url_path': art.get('url_path') or url.split('finance.yahoo.com')[-1],
            'upstream_url': url,
            'thumb_url': thumb_url,
            'thumb_name': thumb_name,
            'tickers': json.dumps(tickers),
            'topics': json.dumps(topics),
            'body': json.dumps([p for p in art.get('paragraphs') or [] if p]),
            'author': art.get('author'),
        }

    for item in symbol_news:
        link = item.get('link') or ''
        if link in by_upstream:
            rec = by_upstream[link]
            # merge tickers
            tickers = set(json.loads(rec['tickers']))
            tickers.update(item.get('related_tickers') or [])
            rec['tickers'] = json.dumps(sorted(tickers))
            continue
        ts = item.get('published_ts')
        pub = (datetime(1970, 1, 1, tzinfo=timezone.utc)
               + timedelta(seconds=int(ts))).strftime('%Y-%m-%dT%H:%M:%SZ') \
            if ts else ''
        host = link.split('//')[1].split('/')[0] if '//' in link else link
        hosted = 1 if host.endswith('finance.yahoo.com') else 0
        if hosted:
            url_path = link.split('finance.yahoo.com')[-1]
        else:
            url_path = '/news/' + hashlib.sha1(
                link.encode()).hexdigest()[:12] + '.html'
        thumb_candidates = [r.get('url') for r in item.get('thumbnail') or []]
        thumb_url, thumb_name = None, None
        from app import img_name
        for url in thumb_candidates:
            if url and img_name(url):
                thumb_url, thumb_name = url, img_name(url)
                break
        body = bodies.get(link) or {}
        paragraphs = [p for p in body.get('paragraphs') or [] if p]
        by_upstream[link] = {
            'key': hashlib.sha1(link.encode()).hexdigest()[:12],
            'title': item.get('title'),
            'summary': None,
            'provider': item.get('publisher'),
            'provider_id': None,
            'hosted': hosted,
            'live_blog': 0,
            'pub_time': pub,
            'url_path': url_path,
            'upstream_url': link,
            'thumb_url': thumb_url,
            'thumb_name': thumb_name,
            'tickers': json.dumps(sorted({t for t in
                                          item.get('related_tickers') or [] if t})),
            'topics': '[]',
            'body': json.dumps(paragraphs),
            'author': body.get('author'),
        }

    for url in sorted(by_upstream.keys()):
        rec = by_upstream[url]
        if not rec['title'] or not rec['pub_time']:
            continue
        db.session.add(NewsArticle(**rec))
    db.session.commit()


def seed_presets(db):
    from app import ScreenerPreset
    presets = _load('screener_presets.json')
    for pid in sorted(presets.keys()):
        data = presets[pid]
        db.session.add(ScreenerPreset(
            preset_id=pid,
            title=data.get('title') or pid,
            description=data.get('description') or '',
            total=data.get('total') or len(data.get('quotes') or []),
            rows=json.dumps(data.get('quotes') or []),
        ))
    db.session.commit()


def seed_trending(db):
    from app import TrendingItem
    trending = _load('trending.json')
    quotes = ((trending.get('finance') or {}).get('result') or [{}])[0] \
        .get('quotes') or []
    for rank, row in enumerate(quotes):
        db.session.add(TrendingItem(rank=rank + 1,
                                    symbol=row.get('symbol') or ''))
    db.session.commit()


def seed_all(db):
    seed_quotes(db)
    seed_chart_points(db)
    seed_earnings(db)
    seed_news(db)
    seed_presets(db)
    seed_trending(db)


# ------------------------------------------------- benchmark user fixtures --

def seed_benchmark_users(db):
    from app import PriceAlert, User, WatchItem
    if db.session.query(User).filter_by(email='alice.j@test.com').first():
        return
    users = [
        ('alice.j@test.com', 'Alice Johnson'),
        ('bob.c@test.com', 'Bob Chen'),
        ('carol.d@test.com', 'Carol Davis'),
        ('dana.k@test.com', 'Dana Kim'),
    ]
    ids = {}
    for email, name in users:
        user = User(email=email, name=name,
                    password_hash=BENCHMARK_HASH, joined=MIRROR_TS)
        db.session.add(user)
        db.session.flush()
        ids[email] = user.id
    fixtures = [
        # (email, watchlist, alerts (symbol, direction, threshold, note))
        ('alice.j@test.com',
         ['MSFT', 'NVDA', 'TSLA', 'SPY'],
         [('NVDA', 'below', 150.0, 'Dip target'),
          ('TSLA', 'above', 480.0, None)]),
        ('bob.c@test.com',
         ['JPM', 'XOM', 'KO'],
         [('KO', 'above', 70.0, 'Sell reminder')]),
        ('carol.d@test.com',
         ['LLY', 'UNH', 'PFE'],
         [('LLY', 'below', 900.0, None),
          ('PFE', 'above', 30.0, 'Breakout watch')]),
        ('dana.k@test.com',
         ['AAPL', 'AMZN', 'META', 'QQQ'],
         [('META', 'below', 600.0, 'Re-entry')]),
    ]
    for email, watch, alerts in fixtures:
        for sym in watch:
            db.session.add(WatchItem(user_id=ids[email], symbol=sym,
                                     added_at=MIRROR_TS))
        for sym, direction, threshold, note in alerts:
            db.session.add(PriceAlert(user_id=ids[email], symbol=sym,
                                      direction=direction,
                                      threshold=threshold, note=note,
                                      created_at=MIRROR_TS))
    db.session.commit()
