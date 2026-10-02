#!/usr/bin/env python3
"""Deterministic seed builder for the nyse mirror.

Everything materialized here comes from the tracked source_data/*.json
snapshots (captured 2026-09-29/30, see provenance.json) in a fixed, sorted
order; the four benchmark accounts and their watchlists / price alerts are
authored fixtures following the u_s_customs / zara / ziprecruiter / disney
precedent: every symbol they reference is a real captured upstream quote,
and every timestamp is a frozen constant so the SQLite output is
byte-reproducible (PYTHONHASHSEED=0).
"""
import json
import os
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
SOURCE = os.path.join(HERE, 'source_data')

BENCHMARK_HASH = (
    '$2b$12$qSds4Mr9Wo7VwPWLhompEer88SuxxXFDp31P9etY6v7nfRctNO7B.')
MIRROR_TS = '2026-09-29'

MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July',
          'August', 'September', 'October', 'November', 'December']


def _load(name):
    with open(os.path.join(SOURCE, name), encoding='utf-8') as f:
        return json.load(f)


def _num(value):
    if value is None or value == '':
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _int(value):
    n = _num(value)
    return int(n) if n is not None else None


def _ordinal(day):
    if 10 <= day % 100 <= 20:
        suffix = 'th'
    else:
        suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(day % 10, 'th')
    return f'{day}{suffix}'


def _et_datetime(ms):
    """America/New_York wall-clock rendering of an epoch-millisecond stamp
    (the bell events carry timezone America/New_York)."""
    dt = datetime.fromtimestamp(ms / 1000, tz=timezone.utc)
    # Eastern time offset rules for 2024-2027 (DST: Mar second Sunday ..
    # Nov first Sunday) — fixed table keeps the seed deterministic without
    # a tz database dependency.
    year = dt.year
    import calendar
    def second_sunday(month):
        d = datetime(year, month, 1)
        return 1 + ((6 - d.weekday()) % 7) + 7
    def first_sunday(month):
        d = datetime(year, month, 1)
        return 1 + ((6 - d.weekday()) % 7)
    dst_start = second_sunday(3)
    dst_end = first_sunday(11)
    naive = datetime(year, dt.month, dt.day)
    dst = False
    if datetime(year, 3, dst_start) <= naive < datetime(year, 11, dst_end):
        dst = True
    offset_hours = -4 if dst else -5
    local = datetime.fromtimestamp(
        ms / 1000 + offset_hours * 3600, tz=timezone.utc)
    suffix = 'EDT' if dst else 'EST'
    return local, suffix


def bell_labels(start_ms, end_ms):
    start, sfx = _et_datetime(start_ms)
    end, _ = _et_datetime(end_ms)
    date_label = (f'{MONTHS[start.month - 1]} {_ordinal(start.day)}, '
                  f'{start.year}')
    def clock(dt):
        hour = dt.hour % 12 or 12
        ampm = 'AM' if dt.hour < 12 else 'PM'
        return f'{hour}:{dt.minute:02d} {ampm}'
    time_label = f'{clock(start)} - {clock(end)} {sfx}'
    return date_label, time_label


def _quote_ms(ms):
    if not ms or ms <= 0:
        return None
    return int(ms)


def _ms_date(ms):
    if not ms or ms <= 0:
        return None
    dt = datetime.fromtimestamp(ms / 1000, tz=timezone.utc)
    return dt.strftime('%m/%d/%Y')


def _month_label(ms):
    dt = datetime.fromtimestamp(ms / 1000, tz=timezone.utc)
    return f"{MONTHS[dt.month - 1][:3]}'{str(dt.year)[-2:]}"


# ---------------------------------------------------------------- seeding --

def seed_all(db):
    from app import (BellEvent, BoardMember, CmsBlock, DirectoryRow,
                    HomeMeta, IpoBacklog, IpoDeal, IpoLargest, IpoMonthly,
                    IpoSectorStat, MarketMover, OptionContract,
                    OptionExpiry, PriceBar, Quote)

    # ---- listings directory (four instrument-type tabs) ----
    dirs = _load('directories.json')
    rows = []
    for tab in ('equity', 'etf', 'reit', 'index'):
        for r in dirs[tab]:
            rows.append(DirectoryRow(tab=tab, symbol=r['symbol'],
                                     name=r['name'] or r['symbol'],
                                     mic=r['mic'],
                                     quote_url=r['quote_url']))
    db.session.add_all(rows)
    db.session.commit()
    print(f'[seed] directory rows: {len(rows)}', flush=True)

    # ---- quotes: light set then rich set ----
    light = _load('quotes_light.json')
    rich = _load('quotes_rich.json')
    quote_rows = []

    def quote_from_payload(symbol, payload, is_rich):
        q = payload.get('quote') or {}
        company = payload.get('company') or {}
        ret = payload.get('returns') or {}
        quote_rows.append(Quote(
            symbol=symbol, exchg=q.get('exchg'), dispname=q.get('dispname'),
            name=q.get('desc'), last=_num(q.get('last')),
            change=_num(q.get('change')), pctchg=_num(q.get('pctchg')),
            volume=_int(q.get('volume')), quote_time=q.get('time'),
            low=_num(q.get('low')), high=_num(q.get('high')),
            open=_num(q.get('open')), ave_vol=_int(q.get('aveVol')),
            ann_low=_num(q.get('annLow')), ann_high=_num(q.get('annHigh')),
            prev=_num(q.get('prev')), bid=_num(q.get('bid')),
            ask=_num(q.get('ask')), bid_size=_int(q.get('bidSize')),
            ask_size=_int(q.get('askSize')), cusip=q.get('cusip'),
            last_update_time=q.get('lastUpdateTime'),
            wl52date=q.get('wl52date'), wh52date=q.get('wh52date'),
            dividend=_num(q.get('dividend')), div_date=q.get('divDate'),
            div_yield=_num(q.get('divYield')), div_int=_int(q.get('divInt')),
            beta=_num(q.get('beta')), eps=_num(q.get('eps')),
            trade_size=_int(q.get('tradeSize')),
            ceo=company.get('ceo'), country=company.get('country'),
            sector=company.get('sector'), market_cap=_num(company.get('marketCap')),
            shares_outstanding=_num(company.get('sharesOutstanding')),
            website=company.get('website'),
            incorporated_year=company.get('incorporatedYear'),
            ret_1m=_num(ret.get('oneMonth')), ret_3m=_num(ret.get('threeMonth')),
            ret_6m=_num(ret.get('sixMonth')), ret_52w=_num(ret.get('fiftyTwoWeek')),
            ret_3y=_num(ret.get('threeYear')),
            volatility=_num(ret.get('volatility')), rsi=_num(ret.get('rsi')),
            symbol_type=ret.get('symbolType'),
            future_ex_date=str(ret.get('futureExDate') or '') or None,
            is_rich=1 if is_rich else 0,
            history_bars=len(payload.get('history') or []),
            opt_expiries=len((payload.get('options') or {}).get('expiries') or []),
        ))

    for symbol in sorted(light):
        quote_from_payload(symbol, light[symbol], False)
    for symbol in sorted(rich):
        quote_from_payload(symbol, rich[symbol], True)
    db.session.add_all(quote_rows)
    db.session.commit()
    print(f'[seed] quotes: {len(quote_rows)} '
          f'({sum(1 for r in quote_rows if r.is_rich)} rich)', flush=True)

    # ---- board members ----
    board_rows = []
    for symbol in sorted(light):
        for member in light[symbol].get('board') or []:
            board_rows.append(BoardMember(
                symbol=symbol, name=member.get('name'),
                term_in_years=_int(member.get('termInYears'))))
    for symbol in sorted(rich):
        for member in rich[symbol].get('board') or []:
            board_rows.append(BoardMember(
                symbol=symbol, name=member.get('name'),
                term_in_years=_int(member.get('termInYears'))))
    db.session.add_all(board_rows)
    db.session.commit()
    print(f'[seed] board members: {len(board_rows)}', flush=True)

    # ---- price history + option chains for the rich set ----
    bar_rows, exp_rows, opt_rows = [], [], []
    for symbol in sorted(rich):
        payload = rich[symbol]
        for bar in payload.get('history') or []:
            bar_rows.append(PriceBar(symbol=symbol, date=bar[0],
                                     open=_num(bar[1]), high=_num(bar[2]),
                                     low=_num(bar[3]), close=_num(bar[4]),
                                     volume=_int(bar[5])))
        options = payload.get('options') or {}
        for pos, label in enumerate(options.get('expiries') or [], 1):
            exp_rows.append(OptionExpiry(symbol=symbol, position=pos,
                                         label=label))
        for kind, key in (('call', 'callList'), ('put', 'putList')):
            for contract in options.get(key) or []:
                opt_rows.append(OptionContract(
                    symbol=symbol, exp_label=contract.get('exp'),
                    exp_pos=(options.get('expiries') or [])
                                .index(contract.get('exp')) + 1
                    if contract.get('exp') in (options.get('expiries') or [])
                    else 1,
                    kind=kind, strike=_num(contract.get('strikeString')),
                    recent=_num(contract.get('recent')),
                    bid=_num(contract.get('bid')),
                    ask=_num(contract.get('ask')),
                    volume=_int(contract.get('volume')),
                    open_int=_num(contract.get('openInt'))))
    db.session.add_all(bar_rows)
    db.session.commit()
    print(f'[seed] price bars: {len(bar_rows)}', flush=True)
    db.session.add_all(exp_rows)
    db.session.add_all(opt_rows)
    db.session.commit()
    print(f'[seed] option contracts: {len(opt_rows)} '
          f'({len(exp_rows)} expiries)', flush=True)

    # ---- bell calendar ----
    events = _load('bell_events.json')
    event_rows = []
    for e in events:
        date_label, time_label = bell_labels(e['start'], e['end'])
        event_rows.append(BellEvent(
            id=e['id'], title=e['title'], etype=e['type'],
            start_ms=int(e['start']), end_ms=int(e['end']),
            date_label=date_label, time_label=time_label,
            description=e['description'], image=e['image'],
            media_json=json.dumps(e['media'])))
    db.session.add_all(event_rows)
    db.session.commit()
    print(f'[seed] bell events: {len(event_rows)}', flush=True)

    # ---- market movers ----
    movers = _load('market_movers.json')
    mover_rows = []
    for category in ('nyse', 'nyse_american'):
        for m in movers[category]:
            mover_rows.append(MarketMover(
                category=category, symbol=m['symbol'], name=m['name'],
                volume=_int(m['volume']), last_price=_num(m['lastPrice']),
                change=_num(m['change']), pctchg=_num(m['pctchg'])))
    db.session.add_all(mover_rows)
    db.session.commit()
    print(f'[seed] market movers: {len(mover_rows)}', flush=True)

    # ---- IPO center ----
    calendar = _load('ipo_calendar.json')
    deal_rows = []
    for d in calendar['calendarList']:
        deal_rows.append(IpoDeal(
            symbol=d.get('symbol'), issuer=d['issuer_nm'],
            status=d['deal_status_desc'], exchange=d.get('custom_group_exchange_nm'),
            industry=d.get('custom_group_industry_nm'),
            price_date_ms=_quote_ms(d.get('price_dt')),
            price_date=_ms_date(_quote_ms(d.get('price_dt'))),
            filed_date_ms=_quote_ms(d.get('init_file_dt')),
            filed_date=_ms_date(_quote_ms(d.get('init_file_dt'))),
            amended_date_ms=_quote_ms(d.get('amended_file_dt')),
            amended_date=_ms_date(_quote_ms(d.get('amended_file_dt'))),
            offer_price=_num(d.get('offer_px_usd')),
            price_range=d.get('current_file_price_range_usd'),
            range_vs_offer=d.get('amended_filing_vs_offer_px_desc'),
            proceeds=_num(d.get('offer_greenshoe_inc_proceeds_usd_amt')),
            filed_proceeds=_num(
                d.get('current_filed_proceeds_with_overallotment_usd_amt')),
            shares_filed=_int(d.get('current_shares_filed')),
            offer_shares=_int(d.get('offer_size_inc_shoe_qty')),
            bookrunners=d.get('bookrunners_parentCode'),
            expected_date=d.get('expected_dt_report'),
            withdrawn_txt=d.get('withdrawn_postponed_txt')))
    db.session.add_all(deal_rows)
    db.session.commit()
    print(f'[seed] IPO deals: {len(deal_rows)}', flush=True)

    largest = _load('ipo_largest_recent.json')
    largest_rows = []
    for d in largest['largestRecentList']:
        largest_rows.append(IpoLargest(
            symbol=d.get('symbol'), issuer=d['issue_nm'],
            exchange=d.get('custom_group_exchange_nm'),
            industry=d.get('custom_group_custom_group_industry_nm'),
            price_date_ms=_quote_ms(d.get('price_dt')),
            price_date=_ms_date(_quote_ms(d.get('price_dt'))),
            filed_date_ms=_quote_ms(d.get('init_file_dt')),
            filed_date=_ms_date(_quote_ms(d.get('init_file_dt'))),
            offer_1day=_num(d.get('pct_chg_1day')),
            offer_current=_num(d.get('pct_chg_current')),
            range_vs_offer=d.get('amended_filing_vs_offer_px_desc'),
            proceeds=_num(d.get('offer_greenshoe_inc_proceeds_usd_amt')),
            bookrunners=d.get('bookrunners_parentCode'),
            issue_type=d.get('issue_type_cd')))
    db.session.add_all(largest_rows)
    db.session.commit()
    print(f'[seed] largest recent IPOs: {len(largest_rows)}', flush=True)

    monthly = _load('ipo_monthly_execution.json')
    monthly_rows = []
    for m in monthly['monthlyExecutionList']:
        ms = _quote_ms(m.get('groupingDate'))
        monthly_rows.append(IpoMonthly(
            month_ms=ms, month_label=_month_label(ms),
            deals=_int(m.get('count__issue_id')),
            proceeds=_num(m.get('sum__offer_greenshoe_inc_proceeds_usd_amt'))))
    db.session.add_all(monthly_rows)
    db.session.commit()
    print(f'[seed] IPO monthly execution: {len(monthly_rows)}', flush=True)

    sector = _load('ipo_price_perf_by_sector.json')
    sector_rows = []
    for s in sector['pricePerfBySectorList']:
        nm = s.get('SectorPricePerf_custom_group_custom_group_industry_nm')
        sector_rows.append(IpoSectorStat(
            sector=nm, deals=_int(s.get('SectorPricePerf_count__issue_id')),
            priced_above=_int(s.get('PricedAbove_count__issue_id')),
            priced_within=_int(s.get('PricedWithin_count__issue_id')),
            priced_below=_int(s.get('PricedBelow_count__issue_id')),
            pct_above=_int(s.get('calculatedAbove')),
            pct_within=_int(s.get('calculatedWithin')),
            pct_below=_int(s.get('calculatedBelow')),
            avg_1day=_num(s.get('SectorPricePerf_avg__pct_chg_1day')),
            avg_30day=_num(s.get('SectorPricePerf_avg__pct_chg_30days')),
            proceeds=_num(s.get(
                'SectorPricePerf_sum__offer_overallotment_option_proceeds_usd_amt'))))
    db.session.add_all(sector_rows)
    db.session.commit()
    print(f'[seed] IPO sector stats: {len(sector_rows)}', flush=True)

    backlog = _load('ipo_backlog.json')
    backlog_rows = []
    for b in backlog['backlogIPOList']:
        backlog_rows.append(IpoBacklog(
            industry=b['industry'], current_deals=_int(b.get('currDealCount')),
            current_proceeds=_num(b.get('currSumFiledProceeds')),
            historical_deals=_int(b.get('histDealCount')),
            historical_proceeds=_num(b.get('histSumFiledProceeds'))))
    db.session.add_all(backlog_rows)
    db.session.commit()
    print(f'[seed] IPO backlog: {len(backlog_rows)}', flush=True)

    # ---- CMS content ----
    home = _load('home_content.json')
    history = _load('history_content.json')
    listings = _load('listings_content.json')
    bell_c = _load('bell_content.json')
    ipo_c = _load('ipo_content.json')
    meta_rows = [
        HomeMeta(section='hero', payload_json=json.dumps(home['hero'],
                                                         sort_keys=True)),
        HomeMeta(section='article', payload_json=json.dumps(home['article'],
                                                            sort_keys=True)),
        HomeMeta(section='cards', payload_json=json.dumps(home['cards'],
                                                          sort_keys=True)),
        HomeMeta(section='shows', payload_json=json.dumps(home['shows'],
                                                          sort_keys=True)),
        HomeMeta(section='whats_next',
                 payload_json=json.dumps(home['whats_next'], sort_keys=True)),
        HomeMeta(section='collage',
                 payload_json=json.dumps(home['collage'], sort_keys=True)),
        HomeMeta(section='history_images',
                 payload_json=json.dumps(history['images'], sort_keys=True)),
        HomeMeta(section='listings_meta',
                 payload_json=json.dumps(
                     {'hero_image': listings.get('hero_image')},
                     sort_keys=True)),
        HomeMeta(section='bell_intro',
                 payload_json=json.dumps(bell_c, sort_keys=True)),
        HomeMeta(section='ipo_intro',
                 payload_json=json.dumps(ipo_c, sort_keys=True)),
    ]
    block_rows = []
    for slot, section in enumerate(history['sections']):
        block_rows.append(CmsBlock(
            page='history', slot=slot, heading=section['heading'],
            body_json=json.dumps(section['paragraphs'], sort_keys=True)))
    for slot, section in enumerate(listings['sections']):
        block_rows.append(CmsBlock(
            page='listings', slot=slot, heading=section['heading'],
            body_json=json.dumps(section['paragraphs'], sort_keys=True)))
    db.session.add_all(meta_rows)
    db.session.add_all(block_rows)
    db.session.commit()
    print(f'[seed] CMS: {len(meta_rows)} meta sections, '
          f'{len(block_rows)} blocks', flush=True)


def seed_benchmark_users(db):
    from app import PriceAlert, User, WatchItem

    if User.query.filter_by(email='alice.j@test.com').first():
        return

    users = [
        ('alice.j@test.com', 'Alice Johnson',
         ('watchlist: KO, DIS and NKE; one price alert on KO')),
        ('bob.c@test.com', 'Bob Chen',
         'watchlist: AAPL and TSLA; two price alerts on AAPL and TSLA'),
        ('carol.d@test.com', 'Carol Davis',
         'watchlist: AAT only; no alerts yet'),
        ('dana.k@test.com', 'Dana Kim',
         'watchlist: SPY, NIO and AMC; one price alert on NIO'),
    ]
    for email, name, _fixture in users:
        db.session.add(User(email=email, name=name,
                            password_hash=BENCHMARK_HASH, joined=MIRROR_TS))
    db.session.commit()

    def _uid(email):
        return User.query.filter_by(email=email).first().id

    alice = _uid('alice.j@test.com')
    bob = _uid('bob.c@test.com')
    carol = _uid('carol.d@test.com')
    dana = _uid('dana.k@test.com')

    def watch(uid, symbol):
        db.session.add(WatchItem(user_id=uid, symbol=symbol,
                                 added_at=MIRROR_TS))

    watch(alice, 'KO')
    watch(alice, 'DIS')
    watch(alice, 'NKE')
    watch(bob, 'AAPL')
    watch(bob, 'TSLA')
    watch(carol, 'AAT')
    watch(dana, 'SPY')
    watch(dana, 'NIO')
    watch(dana, 'AMC')
    db.session.commit()

    def alert(uid, symbol, direction, threshold, note=None):
        db.session.add(PriceAlert(user_id=uid, symbol=symbol,
                                  direction=direction, threshold=threshold,
                                  note=note, created_at=MIRROR_TS))

    alert(alice, 'KO', 'above', 90.0, 'Add on strength')
    alert(bob, 'AAPL', 'below', 300.0)
    alert(bob, 'TSLA', 'above', 200.0, 'Breakout watch')
    alert(dana, 'NIO', 'above', 5.0)
    db.session.commit()
