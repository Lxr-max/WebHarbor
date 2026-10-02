#!/usr/bin/env python3
"""Deterministic seed builder for the coinmarketcap mirror.

Everything materialized here comes from the tracked source_data/*.json
snapshots (captured from coinmarketcap.com 2026-09-29/30 UTC) in a fixed
order. The four benchmark accounts and their watchlists are authored
fixtures following the u_s_customs/zara/ziprecruiter precedent: every
coin they reference is a real captured upstream row (real CMC id, rank,
price), and every timestamp is a frozen constant so the SQLite output is
byte-reproducible (PYTHONHASHSEED=0, UTC).
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))

# bcrypt hash of 'TestPass123!' — frozen so the seed DB is byte-reproducible
# (identical to the zara / ziprecruiter benchmark hash).
BENCHMARK_HASH = (
    '$2b$12$qSds4Mr9Wo7VwPWLhompEer88SuxxXFDp31P9etY6v7nfRctNO7B.')

BENCHMARK_USERS = [
    ('alice.j@test.com', 'Alice Johnson', ['bitcoin', 'ethereum', 'solana'],
     ['2026-09-20', '2026-09-22', '2026-09-25']),
    ('bob.c@test.com', 'Bob Chen', ['dogecoin', 'xrp', 'cardano'],
     ['2026-09-18', '2026-09-21', '2026-09-24']),
    ('carol.d@test.com', 'Carol Diaz', ['shiba-inu', 'pepe', 'bonk1'],
     ['2026-09-19', '2026-09-23', '2026-09-26']),
    ('dana.l@test.com', 'Dana Lee', ['tether', 'usd-coin', 'multi-collateral-dai', 'chainlink'],
     ['2026-09-17', '2026-09-19', '2026-09-22', '2026-09-27']),
]


def _load(name):
    with open(os.path.join(HERE, 'source_data', name), encoding='utf-8') as f:
        return json.load(f)


def seed_all(db, bcrypt, app):
    """Materialize the seed DB from the tracked snapshots. Idempotent."""
    from app import (Chart, Coin, CoinTag, Content, Conversion, Exchange,
                     ExchangePair, GlobalMetric, GlossaryTerm, MarketPair,
                     MostViewedRow, Ohlcv, Sector, SnapshotRow, Tag,
                     TrendingRow, UpcomingRow, User, WatchlistItem)

    coins = _load('coins.json')
    for c in coins:
        row = Coin(
            id=c['id'], slug=c['slug'], name=c['name'], symbol=c['symbol'],
            category=c['category'], status=c['status'], rank=c['rank'],
            price=c['price'], pct_1h=c['pct_1h'], pct_24h=c['pct_24h'],
            pct_7d=c['pct_7d'], pct_30d=c['pct_30d'], pct_60d=c['pct_60d'],
            pct_90d=c['pct_90d'], pct_1y=c['pct_1y'], pct_ytd=c['pct_ytd'],
            pct_yesterday=c['pct_yesterday'],
            volume_24h=c['volume_24h'], volume_7d=c['volume_7d'],
            volume_30d=c['volume_30d'],
            volume_reported_24h=c['volume_reported_24h'],
            cex_volume=c['cex_volume'], dex_volume=c['dex_volume'],
            market_cap=c['market_cap'], fdv=c['fdv'],
            dominance=c['dominance'], turnover=c['turnover'], roi=c['roi'],
            circulating_supply=c['circulating_supply'],
            self_reported_circulating=c['self_reported_circulating'],
            total_supply=c['total_supply'], max_supply=c['max_supply'],
            supply_source=json.dumps(c['supply_source']),
            market_pair_count=c['market_pair_count'],
            date_added=c['date_added'], date_launched=c['date_launched'],
            launch_price=c['launch_price'], ath=c['ath'],
            ath_pct=c['ath_pct'], ath_ts=c['ath_ts'], atl=c['atl'],
            atl_pct=c['atl_pct'], atl_ts=c['atl_ts'],
            high_24h=c['high_24h'], low_24h=c['low_24h'],
            high_7d=c['high_7d'], low_7d=c['low_7d'],
            high_30d=c['high_30d'], low_30d=c['low_30d'],
            high_52w=c['high_52w'], low_52w=c['low_52w'],
            open_yesterday=c['open_yesterday'],
            close_yesterday=c['close_yesterday'],
            volume_rank=c['volume_rank'], watch_count=c['watch_count'],
            watch_ranking=c['watch_ranking'], description=c['description'],
            urls=json.dumps(c['urls']), tags=json.dumps(c['tags']),
            platforms=json.dumps(c['platforms']),
            holders=json.dumps(c['holders']), similar=json.dumps(c['similar']),
            related=json.dumps(c['related']), ratings=json.dumps(c['ratings']),
            badges=json.dumps(c['badges']),
            is_active=c['is_active'], last_updated=c['last_updated'],
        )
        db.session.add(row)

    # tag dictionary + per-coin tag links
    tag_names = {}
    for c in coins:
        for t in c['tags']:
            tag_names[t['slug']] = (t['name'], t.get('group') or 'OTHERS')
    for slug, (name, group) in sorted(tag_names.items()):
        db.session.add(Tag(slug=slug, name=name, group_name=group))
    for c in coins:
        for t in c['tags']:
            db.session.add(CoinTag(coin_id=c['id'], tag_slug=t['slug']))

    # sectors (category pages)
    cats = _load('categories.json')
    for slug, s in sorted(cats.items()):
        db.session.add(Sector(
            tag_slug=slug, sector_id=s['sector_id'], name=s['name'],
            description=s['description'], market_cap=s['market_cap'],
            market_change=s['market_change'],
            market_volume=s['market_volume'],
            volume_change=s['volume_change'], tokens_num=s['tokens_num'],
            upstream_total=s['upstream_total'],
            stats=json.dumps(s['stats']),
            top_coins=json.dumps(s['top_coins'])))

    # chart series (downsampled honest subsets of the captured points)
    charts = _load('charts.json')
    for slug, ranges in sorted(charts.items()):
        coin = db.session.query(Coin).filter_by(slug=slug).first()
        if not coin:
            continue
        for rng, pts in sorted(ranges.items()):
            db.session.add(Chart(coin_id=coin.id, range_name=rng,
                                  points=json.dumps(pts)))

    # historical OHLCV rows
    ohlcv = _load('ohlcv.json')
    for slug, rows in sorted(ohlcv.items()):
        coin = db.session.query(Coin).filter_by(slug=slug).first()
        if not coin:
            continue
        for r in rows:
            db.session.add(Ohlcv(
                coin_id=coin.id, date=r['date'], open=r['open'],
                high=r['high'], low=r['low'], close=r['close'],
                volume=r['volume'], market_cap=r['market_cap'],
                supply=r['supply']))

    # per-coin market pairs
    pairs = _load('market_pairs.json')
    for slug, data in sorted(pairs.items()):
        coin = db.session.query(Coin).filter_by(slug=slug).first()
        if not coin:
            continue
        for p in data['pairs']:
            db.session.add(MarketPair(
                coin_id=coin.id, rank=p['rank'],
                exchange_name=p['exchange'],
                exchange_slug=p['exchange_slug'], pair=p['pair'],
                category=p['category'], price=p['price'],
                volume_usd=p['volume_usd'], volume_pct=p['volume_pct'],
                market_score=p['market_score'],
                market_reputation=p['market_reputation'],
                fee_type=p['fee_type'], depth_neg_2=p['depth_neg_2'],
                depth_pos_2=p['depth_pos_2'],
                effective_liquidity=p['effective_liquidity'],
                last_updated=p['last_updated'],
                quote_symbol=p['quote_symbol'], market_url=p['market_url']))

    # exchanges: three ranking tables + details + pair tables
    ex = _load('exchanges.json')
    seen = {}
    for kind in ('spot', 'dex', 'derivatives'):
        for e in ex['rankings'][kind]['exchanges']:
            row = seen.setdefault(e['slug'], {
                'id': e['id'], 'slug': e['slug'], 'name': e['name'],
                'dex_status': e['dex_status'], 'score': e['score'],
                'traffic_score': e['traffic_score'], 'visits': e['visits'],
                'liquidity': e['liquidity'], 'maker_fee': e['maker_fee'],
                'taker_fee': e['taker_fee'],
                'spot_vol_24h': e['spot_vol_24h'],
                'derivatives_vol_24h': e['derivatives_vol_24h'],
                'derivatives_pairs': e['derivatives_pairs'],
                'derivatives_open_interest': e['derivatives_open_interest'],
                'filtered_vol_24h': e['filtered_vol_24h'],
                'total_vol_24h': e['total_vol_24h'],
                'total_vol_7d': e['total_vol_7d'],
                'total_vol_30d': e['total_vol_30d'],
                'vol_chg_24h': e['vol_chg_24h'], 'vol_chg_7d': e['vol_chg_7d'],
                'vol_chg_30d': e['vol_chg_30d'],
                'market_share_pct': e['market_share_pct'],
                'num_coins': e['num_coins'], 'num_markets': e['num_markets'],
                'date_launched': e['date_launched'],
                'fiats': e['fiats'], 'countries': e['countries'],
                'status': e['status'], 'por_audit': e['por_audit'],
                'reserves': e['reserves'], 'last_updated': e['last_updated'],
                'spot_rank': None, 'dex_rank': None, 'derivatives_rank': None,
            })
            row[f'{kind}_rank'] = e['rank']
    for slug, d in sorted(ex['details'].items()):
        row = seen.setdefault(slug, {'id': d['id'], 'slug': slug,
                                     'name': d['name']})
        row.update({
            'description': d['description'], 'maker_fee': d['maker_fee'],
            'taker_fee': d['taker_fee'], 'dex_status': d['dex_status'],
            'status': d['status'], 'date_launched': d['date_launched'],
            'urls': d['urls'], 'fiats': d['fiats'],
            'countries': d['countries'], 'tags': d['tags'],
            'net_worth_usd': d['net_worth_usd'], 'quote': d['quote'],
        })
    for slug, row in sorted(seen.items()):
        db.session.add(Exchange(
            id=row['id'], slug=row['slug'], name=row['name'],
            dex_status=row.get('dex_status'), spot_rank=row.get('spot_rank'),
            dex_rank=row.get('dex_rank'),
            derivatives_rank=row.get('derivatives_rank'),
            score=row.get('score'), traffic_score=row.get('traffic_score'),
            visits=row.get('visits'), liquidity=row.get('liquidity'),
            maker_fee=row.get('maker_fee'), taker_fee=row.get('taker_fee'),
            spot_vol_24h=row.get('spot_vol_24h'),
            derivatives_vol_24h=row.get('derivatives_vol_24h'),
            derivatives_pairs=row.get('derivatives_pairs'),
            derivatives_open_interest=row.get('derivatives_open_interest'),
            filtered_vol_24h=row.get('filtered_vol_24h'),
            total_vol_24h=row.get('total_vol_24h'),
            total_vol_7d=row.get('total_vol_7d'),
            total_vol_30d=row.get('total_vol_30d'),
            vol_chg_24h=row.get('vol_chg_24h'),
            vol_chg_7d=row.get('vol_chg_7d'),
            vol_chg_30d=row.get('vol_chg_30d'),
            market_share_pct=row.get('market_share_pct'),
            num_coins=row.get('num_coins'), num_markets=row.get('num_markets'),
            date_launched=row.get('date_launched'),
            fiats=json.dumps(row.get('fiats') or []),
            countries=json.dumps(row.get('countries') or []),
            status=row.get('status'), por_audit=row.get('por_audit'),
            reserves=row.get('reserves'),
            last_updated=row.get('last_updated'),
            description=row.get('description'),
            urls=json.dumps(row.get('urls') or {}),
            tags=json.dumps(row.get('tags') or []),
            net_worth_usd=row.get('net_worth_usd'),
            quote=json.dumps(row.get('quote') or {}),
        ))

    expairs = _load('exchange_pairs.json')
    for slug, rows in sorted(expairs.items()):
        exch = db.session.query(Exchange).filter_by(slug=slug).first()
        if not exch:
            continue
        for p in rows:
            db.session.add(ExchangePair(
                exchange_id=exch.id, rank=p['rank'], pair=p['pair'],
                base=p['base'], quote_sym=p['quote'], price=p['price'],
                volume_24h=p['volume_24h'], volume_pct=p['volume_pct'],
                liquidity_score=p['liquidity_score'],
                market_url=p['market_url'], category=p['category'],
                last_updated=p['last_updated']))

    gm = _load('global_metrics.json')
    latest = dict(gm['latest'])
    latest['page_global_metrics'] = gm.get('page_latest') or {}
    db.session.add(GlobalMetric(
        id=1, latest=json.dumps(latest),
        historical=json.dumps(gm['historical_90d']),
        page_shared=json.dumps(gm['page_shared']),
        trending_top5=json.dumps(gm['trending_top5'])))

    tr = _load('trending.json')
    for i, r in enumerate(tr['rows'], 1):
        db.session.add(TrendingRow(
            rank=i, symbol=r['symbol'], name=r['name'], slug=r['slug'],
            platform=r['platform'], price=float(r['price'] or 0),
            pct_1h=_f(r['pct_1h']), pct_24h=_f(r['pct_24h']),
            pct_7d=_f(r['pct_7d']), pct_30d=_f(r['pct_30d']),
            volume_24h=_f(r['volume_24h']), market_cap=_f(r['market_cap']),
            liquidity=_f(r['liquidity']), txs_24h=_f(r['txs_24h']),
            age_ms=r['age_ms'], risk=r['risk'],
            listing_rank=r['listing_rank']))

    mv = _load('most_viewed.json')
    for r in mv['rows']:
        db.session.add(MostViewedRow(
            rank=r['rank'], slug=r['slug'], name=r['name'],
            price_text=r['price'], pct_24h_text=r['pct_24h'],
            pct_7d_text=r['pct_7d'], pct_30d_text=r['pct_30d'],
            market_cap_text=r['market_cap'],
            volume_text=r['volume_24h']))

    up = _load('upcoming.json')
    for r in up['rows']:
        db.session.add(UpcomingRow(
            rank=r['rank'], coin_slug=r['coinSlug'],
            coin_name=r['coinName'], coin_symbol=r['coinSymbol'],
            launch_time_ms=r['launchTime']))

    snap = _load('snapshot_20260927.json')
    for r in snap['rows']:
        db.session.add(SnapshotRow(
            snapshot_date=snap['date'], rank=r['rank'], symbol=r['symbol'],
            name=r['name'], market_cap_text=r['market_cap'],
            price_text=r['price'],
            supply_text=r['circulating_supply'],
            volume_text=r['volume_24h'], pct_1h_text=r['pct_1h'],
            pct_24h_text=r['pct_24h'], pct_7d_text=r['pct_7d']))

    full_terms = _load('glossary_terms.json')
    for slug, g in sorted(full_terms.items()):
        db.session.add(GlossaryTerm(
            slug=g['slug'], title=g['title'], excerpt=g['excerpt'],
            difficulty=g['difficulty'], content=g['content']))
    for t in _load('glossary_index.json'):
        if t['slug'] in full_terms:
            continue
        db.session.add(GlossaryTerm(
            slug=t['slug'], title=t['title'], excerpt=t['excerpt'],
            difficulty=t['difficulty'], content=None))

    for key, c in sorted(_load('conversions.json').items()):
        db.session.add(Conversion(
            key=key, from_symbol=c['from_symbol'],
            from_name=c['from_name'], amount=c['amount'],
            to_price=c['to_price'], to_symbol=c['to_symbol']))

    db.session.add(Content(key='faq', text=_load('faq.json')['rendered']))
    db.session.add(Content(key='methodology',
                           text=_load('methodology.json')['rendered']))
    am = _load('auth_modals.json')
    db.session.add(Content(key='auth_modals', text=json.dumps(am)))
    db.session.add(Content(key='categories_all',
                           text=json.dumps(_load('categories_all.json'))))
    db.session.commit()


def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def seed_benchmark(db, bcrypt, app):
    """Four benchmark users with watchlist fixtures over real captured coins."""
    from app import Coin, User, WatchlistItem

    for email, display, slugs, dates in BENCHMARK_USERS:
        if db.session.query(User).filter_by(email=email).first():
            continue
        user = User(email=email, display_name=display,
                    password_hash=BENCHMARK_HASH, is_benchmark=True,
                    created_at='2026-09-15')
        db.session.add(user)
        db.session.flush()
        for slug, added in zip(slugs, dates):
            coin = db.session.query(Coin).filter_by(slug=slug).first()
            if not coin:
                raise RuntimeError(f'benchmark fixture references unknown coin {slug}')
            db.session.add(WatchlistItem(user_id=user.id, coin_id=coin.id,
                                         added_at=added))
    db.session.commit()
