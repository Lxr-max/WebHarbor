#!/usr/bin/env python3
"""Build verify/contract.json for the yahoo_finance mirror.

Computes the initial digest straight from the reviewed seed database
(instance_seed/yahoo_finance.db) using the same table/row canonicalization
the contract engine applies at review time, resolves the primary-key tags of
every seeded row a task removes, and emits the per-task spec: exact task
wording, expected state deltas, required page evidence and the checked
claims. Run after the seed is built:

    python3 scripts_dev/build_contract.py
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
VERIFY = HERE / 'verify'
SEED = HERE / 'instance_seed' / 'yahoo_finance.db'


def database(path):
    with sqlite3.connect('file:' + str(path) + '?mode=ro', uri=True) as con:
        con.row_factory = sqlite3.Row
        data = {}
        for (table,) in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%' ORDER BY name"):
            keys = [r[1] for r in sorted(
                con.execute(f'PRAGMA table_info("{table}")'),
                key=lambda r: r[5]) if r[5]]
            data[table] = {json.dumps([r[k] for k in keys]): dict(r)
                           for r in con.execute(f'SELECT * FROM "{table}"')}
        return data


def digest(data):
    return hashlib.sha256(json.dumps(data, sort_keys=True,
                                      separators=(',', ':')).encode()).hexdigest()


def pk_key(table, **where):
    con = sqlite3.connect('file:' + str(SEED) + '?mode=ro', uri=True)
    con.row_factory = sqlite3.Row
    rows = list(con.execute(f'SELECT * FROM "{table}"'))
    con.close()
    for r in rows:
        if all(r[k] == v for k, v in where.items()):
            info = sorted(con_execute_pk(table), key=lambda t: t[5])
            keys = [c[1] for c in info if c[5]]
            return json.dumps([r[k] for k in keys])
    raise SystemExit(f'row not found: {table} {where}')


def con_execute_pk(table):
    con = sqlite3.connect('file:' + str(SEED) + '?mode=ro', uri=True)
    info = list(con.execute(f'PRAGMA table_info("{table}")'))
    con.close()
    return info


def main():
    if not SEED.is_file():
        raise SystemExit('seed database missing — build it first')
    initial = database(SEED)
    initial_digest = digest(initial)

    # primary keys of seeded rows the tasks remove
    carol_unh = pk_key('watch_items', user_id=3, symbol='UNH')
    alice_tsla_alert = pk_key('price_alerts', user_id=1, symbol='TSLA',
                              direction='above', threshold=480.0)
    dana_meta_alert = pk_key('price_alerts', user_id=4, symbol='META')

    tasks = [json.loads(l) for l in
             (HERE / 'tasks.jsonl').read_text().splitlines() if l.strip()]

    MIRROR = '2026-09-30'

    def add_watch(row_id, user, symbol):
        return {'id': row_id, 'user_id': user, 'symbol': symbol,
                'added_at': MIRROR}

    def add_alert(row_id, user, symbol, direction, threshold, note=None):
        return {'id': row_id, 'user_id': user, 'symbol': symbol,
                'direction': direction, 'threshold': threshold,
                'note': note, 'created_at': MIRROR}

    contract = {}

    contract['YahooFinance--0'] = {
        'task': tasks[0]['ques'],
        'state': {'watch_items': {'added': [add_watch(15, 1, 'AAPL')]},
                  'price_alerts': {'added': [
                      add_alert(7, 1, 'AAPL', 'above', 350.0, 'iPhone cycle')]}},
        'paths': [r'/quote/AAPL(?:$|\?)', r'/quote/AAPL/statistics',
                  r'/quote/AAPL/profile', r'/watchlist(?:$|\?)',
                  r'/alerts(?:$|\?)'],
        'claims': [
            ['Apple sector', r'technology'],
            ['Apple 52-week range', r'243\.42\s*(?:-|to|–)?\s*345\.34'],
            ['Apple profit margin', r'27\.62\s*percent'],
            ['Apple 1-year target estimate', r'328\.22'],
            ['Apple website', r'apple\s*\.\s*com'],
            ['Apple headquarters city', r'cupertino'],
            ['watchlist size', r'\b5\s*(?:symbols?|stocks?|entries)\b'],
            ['Apple last price', r'333\.02'],
            ['alert status', r'\bactive\b'],
            ['Alice alert total', r'\b3\s*(?:alerts?|price alerts?)\b'],
        ],
    }

    contract['YahooFinance--1'] = {
        'task': tasks[1]['ques'],
        'state': {
            'users': {'added': [
                {'id': 5, 'email': 'jordan.vale@test.com',
                 'name': 'Jordan Vale', 'joined': MIRROR,
                 'password_hash': {'regex': r'\$2[aby]\$12\$[./A-Za-z0-9]{53}'}}]},
            'watch_items': {'added': [add_watch(15, 5, 'SMCI')]}},
        'paths': [r'/screener(?:$|\?)', r'/quote/SMCI(?:$|\?)',
                  r'/watchlist(?:$|\?)'],
        'claims': [
            ['top gainer', r'\buthr\b'],
            ['top gainer price', r'541\.89'],
            ['top gainer change', r'12\.55\s*percent'],
            ['first filtered result industry', r'computer\s+hardware'],
            ['watchlist symbol', r'\bsmci\b'],
        ],
    }

    contract['YahooFinance--2'] = {
        'task': tasks[2]['ques'],
        'state': {'price_alerts': {'added': [
            add_alert(7, 4, 'COST', 'above', 1000.0, 'Earnings prep')]}},
        'paths': [r'/calendar/earnings\?day=2026-09-20',
                  r'/quote/COST(?:$|\?)', r'/alerts(?:$|\?)'],
        'claims': [
            ['biggest surprise company', r'stitch\s*fix'],
            ['EPS estimate', r'-\s*0\.06|\(?0\.06\)'],
            ['reported EPS', r'-\s*0\.01|\(?0\.01\)'],
            ['surprise percent', r'84\.92\s*percent'],
            ['AMC events count', r'\b2\s*events?\b'],
            ['Costco call time', r'\btas\b'],
            ['Costco EPS estimate', r'6\.53'],
            ['Dana alert total', r'\b2\s*(?:alerts?|price alerts?)\b'],
        ],
    }

    contract['YahooFinance--3'] = {
        'task': tasks[3]['ques'],
        'state': {'watch_items': {'added': [add_watch(15, 3, 'NVDA')]},
                  'price_alerts': {'added': [
                      add_alert(7, 3, 'NVDA', 'below', 200.0, 'Dip buy')]}},
        'paths': [r'/sectors(?:$|\?)', r'/sectors/technology(?:$|\?)',
                  r'/quote/NVDA(?:$|\?)', r'/watchlist(?:$|\?)',
                  r'/alerts(?:$|\?)'],
        'claims': [
            ['largest sector', r'technology'],
            ['sector day change', r'0\.38\s*percent'],
            ['sector top loser', r'\bjbl\b'],
            ['industry with most companies', r'software\s*-\s*infrastructure'],
            ['industry company count', r'\b15\s*(?:companies|stocks)\b'],
            ['NVIDIA P/E', r'28\.87'],
            ['NVIDIA dividend yield', r'0\.44\s*percent'],
            ['NVIDIA 50-day average', r'216\.98'],
            ['watchlist count', r'\b4\s*(?:symbols?|stocks?|entries)\b'],
            ['alert status', r'\bactive\b'],
        ],
    }

    contract['YahooFinance--4'] = {
        'task': tasks[4]['ques'],
        'state': {'price_alerts': {'added': [
            add_alert(7, 4, 'NVDA', 'below', 200.0, 'AI pullback')]}},
        'paths': [r'/news(?:$|\?|/)',
                  r'/technology/ai/articles/ai-driven-edge-security',
                  r'/quote/NVDA(?:$|\?)', r'/alerts(?:$|\?)'],
        'claims': [
            ['match count', r'\b10\s*(?:articles?|results?|stories)\b'],
            ['publisher', r'simply\s*wall\s*st'],
            ['related ticker NVDA', r'\bnvda\b'],
            ['related ticker PANW', r'\bpanw\b'],
            ['related ticker SMTC', r'\bsmtc\b'],
            ['article author', r'sasha\s*jovanovic'],
            ['economy first article title', r'kashkari'],
            ['economy first article publisher', r'\breuters\b'],
            ['alert status', r'\bactive\b'],
            ['Dana alert total', r'\b2\s*(?:alerts?|price alerts?)\b'],
        ],
    }

    contract['YahooFinance--5'] = {
        'task': tasks[5]['ques'],
        'state': {'watch_items': {'added': [add_watch(15, 3, 'MU')]},
                  'price_alerts': {'added': [
                      add_alert(7, 3, 'MU', 'above', 1200.0, 'Memory cycle')]}},
        'paths': [r'/trending(?:$|\?)', r'/quote/MU(?:$|\?|/)',
                  r'/watchlist(?:$|\?)', r'/alerts(?:$|\?)'],
        'claims': [
            ['trending #1', r'\bmu\b'],
            ['trending #2', r'\bgoog\b'],
            ['trending #3', r'\blqda\b'],
            ['#2 change', r'1\.01\s*percent'],
            ['#3 change', r'57\.19\s*percent'],
            ['#1 change', r'mu.{0,40}(?:0(?:\.0*)?\s*percent|flat|unchanged|no change)'],
            ['market cap', r'1\.2\s*t\b'],
            ['52-week range', r'179\.61\s*(?:-|to|–)?\s*1,?255'],
            ['trailing P/E', r'24\.10\b'],
            ['50-day average', r'949\.71'],
            ['watchlist count', r'\b4\s*(?:symbols?|stocks?|entries)\b'],
            ['alert status', r'\bactive\b'],
            ['Carol alert total', r'\b3\s*(?:alerts?|price alerts?)\b'],
            ['LQDA market cap', r'2\.71\s*b\b|2,708,538,880|2\.7\s*b\b'],
        ],
    }

    contract['YahooFinance--6'] = {
        'task': tasks[6]['ques'],
        'state': {'watch_items': {'added': [add_watch(15, 2, 'NVDA')]},
                  'price_alerts': {'added': [
                      add_alert(7, 2, 'NVDA', 'above', 700.0)]}},
        'paths': [r'/quote/AMD/statistics', r'/quote/NVDA/statistics',
                  r'/watchlist(?:$|\?)', r'/alerts(?:$|\?)'],
        'claims': [
            ['AMD P/E', r'154\.88'],
            ['AMD profit margin', r'15\.58\s*percent'],
            ['NVIDIA P/E', r'28\.87'],
            ['NVIDIA profit margin', r'63\.66\s*percent'],
            ['lower P/E company', r'nvidia.{0,80}lower|lower.{0,80}nvidia'],
            ['watchlist symbols', r'jpm.{0,60}xom.{0,60}\bko\b.{0,60}nvda'],
            ['alert status', r'\bactive\b'],
        ],
    }

    contract['YahooFinance--7'] = {
        'task': tasks[7]['ques'],
        'state': {'watch_items': {'added': [add_watch(15, 4, 'NU')]},
                  'price_alerts': {'added': [
                      add_alert(7, 4, 'NU', 'above', 20.0, 'LatAm growth')]}},
        'paths': [r'/screener\?preset=most_actives',
                  r'/quote/NU/history', r'/quote/NU/statistics',
                  r'/watchlist(?:$|\?)'],
        'claims': [
            ['most active symbol', r'\bnu\b'],
            ['volume', r'100\s?,?868\s?,?354|100868354|100\.87\s*m\b'],
            ['percent change', r'2\.51\s*percent'],
            ['latest close', r'12\.66'],
            ['first close', r'14\.46'],
            ['50-day average', r'14\.33'],
            ['watchlist symbols', r'aapl.{0,80}amzn.{0,80}meta.{0,80}qqq.{0,80}\bnu\b'],
            ['industry', r'banks\s*-\s*regional'],
        ],
    }

    contract['YahooFinance--8'] = {
        'task': tasks[8]['ques'],
        'state': {'watch_items': {'added': [add_watch(15, 4, 'NVDA')]}},
        'paths': [r'/news\?[^#]*q=buyback',
                  r'/markets/stocks/articles/stock-market-today-sept-30',
                  r'/quote/NVDA(?:$|\?)', r'/watchlist(?:$|\?)'],
        'claims': [
            ['match count', r'\b2\s*(?:articles?|results?|stories)\b'],
            ['publisher', r'motley\s*fool'],
            ['article author', r'will\s+healy'],
            ['Nvidia closing price in article', r'228\.38'],
            ['Nvidia percent change in article', r'0\.51\s*percent'],
            ['Nvidia trading volume in article',
             r'117\.7\s*(?:m\b|million)'],
            ['earnings topic article', r'cboe.{0,80}surges'],
            ['watchlist count', r'\b5\s*(?:symbols?|stocks?|entries)\b'],
        ],
    }

    contract['YahooFinance--9'] = {
        'task': tasks[9]['ques'],
        'state': {
            'users': {'added': [
                {'id': 5, 'email': 'priya.nair@test.com',
                 'name': 'Priya Nair', 'joined': MIRROR,
                 'password_hash': {'regex': r'\$2[aby]\$12\$[./A-Za-z0-9]{53}'}}]},
            'watch_items': {'added': [add_watch(15, 5, 'AAPL')]}},
        'paths': [r'/quote/AAPL/financials', r'/quote/AAPL/statistics',
                  r'/quote/AAPL/profile', r'/watchlist(?:$|\?)',
                  r'/news\?[^#]*q=Apple',
                  r'/technology/ai/articles/bank-america-warns-apple-investors'],
        'claims': [
            ['fiscal year end', r'2025-09-30|september\s+30,?\s*2025'],
            ['total revenue', r'416\.16\s*b\b|416,161,000,000'],
            ['net income', r'112\.01\s*b\b|112,010,000,000'],
            ['PEG ratio', r'2\.64'],
            ['beta', r'1\.08'],
            ['employees', r'150,?000'],
            ['watchlist symbol', r'\baapl\b'],
            ['Apple news match count', r'\b9\s*(?:articles?|results?|stories)\b'],
            ['Apple news publisher', r'the\s*street'],
            ['Apple news author', r'hillary\s*remy'],
        ],
    }

    contract['YahooFinance--10'] = {
        'task': tasks[10]['ques'],
        'state': {'price_alerts': {'added': [
            add_alert(7, 2, 'PEP', 'above', 100.0, 'Cola wars')]}},
        'paths': [r'/quote/KO/profile', r'/quote/PEP/statistics',
                  r'/alerts(?:$|\?)', r'/watchlist(?:$|\?)'],
        'claims': [
            ['KO sector', r'consumer\s+defensive'],
            ['KO industry', r'beverages\s*-\s*non\s*-\s*alcoholic'],
            ['KO employees', r'65,?900'],
            ['KO website', r'coca\s*-?\s*cola\s*company'],
            ['KO dividend rate', r'2\.12'],
            ['KO dividend yield', r'2\.46\s*percent'],
            ['PEP profit margin', r'10\.79\s*percent'],
            ['PEP P/E', r'16\.61'],
            ['alert status', r'\btriggered\b'],
            ['Bob watchlist count', r'\b3\s*(?:symbols?|stocks?|entries)\b'],
        ],
    }

    contract['YahooFinance--11'] = {
        'task': tasks[11]['ques'],
        'state': {'price_alerts': {'added': [
            add_alert(7, 4, 'AAPL', 'above', 400.0, 'Earnings run')]}},
        'paths': [r'/calendar/earnings\?day=2026-10-04',
                  r'/quote/AAPL(?:$|\?)', r'/quote/AAPL/statistics',
                  r'/alerts(?:$|\?)'],
        'claims': [
            ['busiest day', r'oct(?:ober)?\s*8|2026-10-08'],
            ['busiest day count', r'\b97\s*events?\b'],
            ['this week busiest day', r'oct(?:ober)?\s*1,?\s*2026|2026-10-01|\boct(?:ober)?\s+1\b'],
            ['this week busiest count', r'\b152\s*events?\b'],
            ['Apple earnings date', r'oct(?:ober)?\s*29,?\s*2026|2026-10-29'],
            ['Apple target estimate', r'328\.22'],
            ['Apple 50-day average', r'321\.98'],
            ['alert status', r'\bactive\b'],
            ['Dana alert total', r'\b2\s*(?:alerts?|price alerts?)\b'],
        ],
    }

    contract['YahooFinance--12'] = {
        'task': tasks[12]['ques'],
        'state': {'watch_items': {
                      'removed': [carol_unh],
                      'added': [add_watch(15, 3, 'MRK')]},
                  'price_alerts': {'added': [
                      add_alert(7, 3, 'MRK', 'above', 160.0, 'Pharma rotation')]}},
        'paths': [r'/watchlist(?:$|\?)', r'/quote/MRK(?:$|\?)',
                  r'/alerts(?:$|\?)'],
        'claims': [
            ['initial watchlist', r'lly.{0,60}unh.{0,60}pfe'],
            ['final watchlist', r'lly.{0,60}pfe.{0,60}mrk'],
            ['Merck P/E', r'116\.25'],
            ['Merck 52-week range', r'82\.01\s*(?:-|to|–)?\s*156\.92'],
            ['alert status', r'\bactive\b'],
        ],
    }

    contract['YahooFinance--13'] = {
        'task': tasks[13]['ques'],
        'state': {'price_alerts': {
                      'removed': [alice_tsla_alert],
                      'added': [add_alert(7, 1, 'TSLA', 'above', 900.0,
                                          'Upside breakout')]}},
        'paths': [r'/alerts(?:$|\?)', r'/quote/TSLA(?:$|\?|/)',
                  r'/quote/TSLA/statistics'],
        'claims': [
            ['NVDA alert direction and threshold', r'nvda.{0,40}below.{0,12}150|below.{0,12}150.{0,40}nvda'],
            ['TSLA alert threshold', r'tsla.{0,40}above.{0,12}480|above.{0,12}480.{0,40}tsla'],
            ['new alert status', r'\bactive\b'],
            ['final alert count', r'\b2\s*(?:alerts?|price alerts?)\b'],
            ['Tesla 50-day average', r'347\.45'],
        ],
    }

    contract['YahooFinance--14'] = {
        'task': tasks[14]['ques'],
        'state': {'watch_items': {'added': [add_watch(15, 2, 'UTHR')]}},
        'paths': [r'/screener\?[^#]*sector=Healthcare',
                  r'mcap_min=10000000000', r'mcap_max=200000000000',
                  r'sort=change', r'/quote/UTHR/statistics',
                  r'/watchlist(?:$|\?)'],
        'claims': [
            ['day gainer top', r'\buthr\b'],
            ['day gainer change', r'12\.55\s*percent'],
            ['first filtered symbol', r'\buthr\b'],
            ['second filtered symbol', r'\bibrx\b'],
            ['third filtered symbol', r'\bpfe\b'],
            ['IBRX change', r'6\.91\s*percent'],
            ['UTHR 52-week change', r'8\.58\s*percent'],
            ['watchlist symbols', r'jpm.{0,60}xom.{0,60}\bko\b.{0,60}uthr'],
        ],
    }

    contract['YahooFinance--15'] = {
        'task': tasks[15]['ques'],
        'state': {'watch_items': {'added': [add_watch(15, 4, 'BTC-USD')]},
                  'price_alerts': {'added': [
                      add_alert(7, 4, 'BTC-USD', 'above', 90000.0, 'ETF bid')]}},
        'paths': [r'/quote/BTC-USD(?:$|\?)', r'/news\?[^#]*q=stablecoin',
                  r'/markets/crypto/articles/stripes-bridge-launches-ousd-stablecoin',
                  r'/watchlist(?:$|\?)', r'/alerts(?:$|\?)'],
        'claims': [
            ['bitcoin symbol', r'\bbtc-?usd\b'],
            ['bitcoin price', r'83452\.08'],
            ['bitcoin market cap', r'1\.68\s*t\b'],
            ['bitcoin 52-week range', r'57747\.77\s*(?:-|to|–)?\s*126198\.07'],
            ['stablecoin match count', r'\b2\s*(?:articles?|results?|stories)\b'],
            ['stablecoin article publisher', r'bankless'],
            ['stablecoin article author', r'william\s*peaster'],
            ['reserve custodians',
             r'black\s*rock.{0,60}bny.{0,60}lead\s*bank'],
            ['alert status', r'\bactive\b'],
            ['watchlist count', r'\b5\s*(?:symbols?|stocks?|entries)\b'],
        ],
    }

    contract['YahooFinance--16'] = {
        'task': tasks[16]['ques'],
        'state': {'watch_items': {'added': [add_watch(15, 2, 'JNJ')]},
                  'price_alerts': {'added': [
                      add_alert(7, 2, 'JNJ', 'above', 300.0, 'Dividend value')]}},
        'paths': [r'/sectors/healthcare(?:$|\?)',
                  r'/quote/LLY/statistics', r'/quote/JNJ/statistics',
                  r'/watchlist(?:$|\?)', r'/alerts(?:$|\?)'],
        'claims': [
            ['healthcare company count', r'\b39\s*companies\b'],
            ['top industry', r'\bbiotechnology\b'],
            ['LLY P/E', r'38\.92'],
            ['LLY profit margin', r'33\.53\s*percent'],
            ['JNJ P/E', r'30\.71'],
            ['JNJ profit margin', r'21\.48\s*percent'],
            ['watchlist count', r'\b4\s*(?:symbols?|stocks?|entries)\b'],
            ['alert status', r'\bactive\b'],
        ],
    }

    contract['YahooFinance--17'] = {
        'task': tasks[17]['ques'],
        'state': {'price_alerts': {'added': [
            add_alert(7, 1, 'MSFT', 'above', 600.0, 'Azure wave')]}},
        'paths': [r'/quote/MSFT/history', r'/quote/MSFT/statistics',
                  r'/watchlist(?:$|\?)', r'/alerts(?:$|\?)'],
        'claims': [
            ['latest close', r'512\.90\b'],
            ['first close', r'501\.02'],
            ['50-day average', r'480\.25'],
            ['200-day average', r'432\.30\b'],
            ['watchlist count', r'\b4\s*(?:symbols?|stocks?|entries)\b'],
            ['alert status', r'\bactive\b'],
            ['Alice alert total', r'\b3\s*(?:alerts?|price alerts?)\b'],
        ],
    }

    contract['YahooFinance--18'] = {
        'task': tasks[18]['ques'],
        'state': {'watch_items': {'added': [add_watch(15, 3, 'GC=F')]},
                  'price_alerts': {'added': [
                      add_alert(7, 3, 'GC=F', 'above', 4300.0, 'Rally hedge')]}},
        'paths': [r'/news(?:$|\?|/)', r'/quote/GC\=F(?:$|\?)',
                  r'/watchlist(?:$|\?)', r'/alerts(?:$|\?)'],
        'claims': [
            ['match count', r'\b18\s*(?:articles?|results?|stories)\b'],
            ['publisher', r'\breuters\b'],
            ['author', r'michael\s*s\.?\s*derby'],
            ['gold price', r'4,?183\.20\b'],
            ['gold change', r'0\.08\s*percent'],
            ['alert status', r'\bactive\b'],
            ['watchlist count', r'\b4\s*(?:symbols?|stocks?|entries)\b'],
        ],
    }

    contract['YahooFinance--19'] = {
        'task': tasks[19]['ques'],
        'state': {'watch_items': {'added': [add_watch(15, 4, 'D')]},
                  'price_alerts': {'removed': [dana_meta_alert]}},
        'paths': [r'/screener(?:$|\?)', r'/quote/D(?:$|\?)',
                  r'/alerts(?:$|\?)', r'/watchlist(?:$|\?)'],
        'claims': [
            ['first yield symbol', r'\bduk-?pa\b'],
            ['second yield symbol', r'\bken\b'],
            ['third yield symbol', r'\bd\b.{0,30}dominion|dominion.{0,30}\bd\b'],
            ['first yield', r'6\.59\b'],
            ['third yield', r'4\.40\b'],
            ['Dominion market cap', r'53\.23\s*b\b'],
            ['Dominion earnings date', r'oct(?:ober)?\s*30,?\s*2026|2026-10-30'],
            ['remaining alerts', r'\b(?:0|no)\s*(?:alerts?|price alerts?)\b'],
            ['watchlist count', r'\b5\s*(?:symbols?|stocks?|entries)\b'],
        ],
    }

    for task_id, spec in contract.items():
        spec['initial_digest'] = initial_digest
    (VERIFY / 'contract.json').write_text(json.dumps(contract, indent=1))
    print(f'contract.json written: {len(contract)} tasks, '
          f'initial digest {initial_digest}')


if __name__ == '__main__':
    sys.exit(main())
