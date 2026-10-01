#!/usr/bin/env python3
"""Generate reviewer verify_N.py SPEC files from the frozen walk ground truth.

Run from sites/yahoo_finance:  python3 scripts_dev/gen_review_verifiers.py
(Regenerates verify/verify_0.py .. verify_verify_19.py — reviewer track.)
"""
import json
from pathlib import Path

VT = Path(__file__).resolve().parent.parent / 'verify'
TASKS = {json.loads(l)['id']: json.loads(l)['ques']
         for l in (Path(__file__).resolve().parent.parent / 'tasks.jsonl')
         .read_text().splitlines() if l.strip()}

SPECS = {}

SPECS[0] = {
    'paths': [r'/', r'/lookup\?s=Apple', r'/quote/AAPL',
              r'/quote/AAPL/statistics', r'/quote/AAPL/profile', r'/login',
              r'/watchlist', r'/alerts'],
    'claims': [
        ('Apple sector', r'\btechnology\b'),
        ('Apple 52-week range', r'243\.42\s*-\s*345\.34'),
        ('Apple profit margin', r'27\.62\s*percent'),
        ('Apple 1-year target', r'328\.22'),
        ('Apple website', r'apple\.com'),
        ('Apple headquarters city', r'cupertino'),
        ('watchlist symbol count', r'\b5\s*(?:symbols?|companies|stocks)\b'),
        ('Apple last price', r'333\.02'),
        ('new alert status', r'\bactive\b'),
        ('Alice alert total', r'\b3\s*(?:price\s*)?alerts?\b'),
    ],
    'forbidden': [r'\b4\s*(?:symbols?|price\s*alerts?)\b',
                  r'\b(?:6|2)\s*alerts?\b'],
    'added': {
        'price_alerts': [{'user_id': 1, 'symbol': 'AAPL', 'direction': 'above',
                          'threshold': 350.0, 'note': 'iPhone cycle'}],
        'watch_items': [{'user_id': 1, 'symbol': 'AAPL'}],
    },
    'removed': {},
}

SPECS[1] = {
    'paths': [r'/', r'/signup', r'/screener',
              r'/screener\?[^#]*sector=Technology', r'[^#]*pe_min=12',
              r'[^#]*pe_max=40', r'[^#]*sort=pe', r'[^#]*dir=asc',
              r'/quote/SMCI', r'/watchlist'],
    'claims': [
        ('Day Gainers top symbol', r'\buthr\b'),
        ('top price', r'541\.89'),
        ('top percent change', r'\+?12\.55\s*percent'),
        ('first filtered symbol', r'\bsmci\b'),
        ('industry', r'computer\s+hardware'),
        ('watchlist symbols', r'watchlist[^.]{0,80}\bsmci\b|'
                              r'\bsmci\b[^.]{0,80}watchlist'),
    ],
    'forbidden': [r'\buthr\b[^.]{0,40}\bwatchlist\b'],
    'added': {
        'users': [{'name': 'Jordan Vale', 'email': 'jordan.vale@test.com',
                   'joined': '2026-09-30',
                   'password_hash': 'SHAPE:bcrypt:TestPass123!'}],
        'watch_items': [{'user_id': 5, 'symbol': 'SMCI'}],
    },
    'removed': {},
}

SPECS[2] = {
    'paths': [r'/', r'/calendar/earnings\?day=2026-09-20',
              r'/calendar/earnings\?day=2026-09-20[^#]*time=AMC',
              r'/calendar/earnings\?day=2026-09-20[^#]*symbol=COST',
              r'/quote/COST', r'/login', r'/alerts'],
    'claims': [
        ('biggest surprise company', r'stitch\s*fix'),
        ('EPS estimate', r'-\s*0\.06|\b0\.06\b'),
        ('reported EPS', r'-\s*0\.01|\b0\.01\b'),
        ('surprise percent', r'84\.92\s*(?:percent)?'),
        ('after-market-close count', r'\b2\s*\w*\s*(?:events?|reports?)\b|'
                                     r'(?:events?|reports?)[^.]{0,30}\b2\b'),
        ('Costco call time', r'\btas\b'),
        ('Costco EPS estimate', r'6\.53'),
        ('Dana alert total', r'\b2\s*(?:price\s*)?alerts?\b'),
    ],
    'forbidden': [r'\b(?:3|4|5)\s*(?:price\s*)?alerts?\b'],
    'added': {
        'price_alerts': [{'user_id': 4, 'symbol': 'COST', 'direction': 'above',
                          'threshold': 1000.0, 'note': 'Earnings prep'}],
    },
    'removed': {},
}

SPECS[3] = {
    'paths': [r'/', r'/sectors', r'/sectors/technology', r'/quote/NVDA',
              r'/quote/NVDA/statistics', r'/login', r'/alerts',
              r'/watchlist'],
    'claims': [
        ('largest sector', r'\btechnology\b'),
        ('sector day change', r'\+?0\.38\s*percent'),
        ('top loser', r'\bjbl\b[^.]{0,30}-\s*10\.03\s*percent'),
        ('industry with most companies', r'software\s*-\s*infrastructure'),
        ('industry company count', r'\b15\s*companies\b'),
        ('largest company', r'\bnvda\b'),
        ('trailing P/E', r'28\.87'),
        ('dividend rate', r'\b1\s*\(\s*0\.44\s*percent\s*\)'),
        ('50-day average', r'216\.98'),
        ('alert status', r'\bactive\b'),
        ('watchlist count', r'watchlist[^.]{0,60}\b4\b|'
                            r'\b4\b[^.]{0,60}watchlist|'
                            r'\b4\s*(?:symbols?|entries|items|companies|'
                            r'stocks)\b'),
    ],
    'forbidden': [r'\b(?:5|3)\s*(?:symbols?|companies)\s*on\b'],
    'added': {
        'price_alerts': [{'user_id': 3, 'symbol': 'NVDA', 'direction': 'below',
                          'threshold': 200.0, 'note': 'Dip buy'}],
        'watch_items': [{'user_id': 3, 'symbol': 'NVDA'}],
    },
    'removed': {},
}

SPECS[4] = {
    'paths': [r'/', r'/news\?topic=latest&q=Nvidia',
              r'/technology/ai/articles/ai-driven-edge-security-integration',
              r'/news\?topic=economy', r'/login', r'/lookup\?s=NVDA',
              r'/quote/NVDA', r'/alerts'],
    'claims': [
        ('Nvidia article count', r'\b10\s*(?:articles?|results?|matches)\b'),
        ('publisher', r'simply\s*wall\s*st'),
        ('related tickers', r'nvda.{0,10}panw.{0,10}smtc'),
        ('author', r'sasha\s*jovanovic'),
        ('economy first article', r'kashkari'),
        ('new alert status', r'\bactive\b'),
        ('Dana alert total', r'\b2\s*(?:price\s*)?alerts?\b'),
    ],
    'forbidden': [r'\b(?:3|4)\s*(?:price\s*)?alerts?\b'],
    'added': {
        'price_alerts': [{'user_id': 4, 'symbol': 'NVDA', 'direction': 'below',
                          'threshold': 200.0, 'note': 'AI pullback'}],
    },
    'removed': {},
}

SPECS[5] = {
    'paths': [r'/', r'/trending', r'/quote/MU', r'/quote/MU/statistics',
              r'/login', r'/alerts', r'/quote/LQDA', r'/watchlist'],
    'claims': [
        ('trending #1', r'\bmu\b[^.]{0,40}\+?0\.00\s*percent'),
        ('trending #2', r'\bgoog\b[^.]{0,40}\+?1\.01\s*percent'),
        ('trending #3', r'\blqda\b[^.]{0,40}-\s*57\.19\s*percent'),
        ('MU market cap', r'1\.2\s*t'),
        ('MU 52-week range', r'179\.61\s*-\s*1[,]?255\.00'),
        ('MU trailing P/E', r'24\.10'),
        ('MU 50-day average', r'949\.71'),
        ('LQDA market cap', r'2\.71\s*b'),
        ('watchlist count', r'\b4\s*(?:symbols?|companies|stocks)\b'),
        ('Carol alert total', r'\b3\s*(?:price\s*)?alerts?\b'),
    ],
    'forbidden': [r'\b(?:5)\s*(?:symbols?|companies)\b',
                  r'\b(?:2|4)\s*alerts?\b'],
    'added': {
        'price_alerts': [{'user_id': 3, 'symbol': 'MU', 'direction': 'above',
                          'threshold': 1200.0, 'note': 'Memory cycle'}],
        'watch_items': [{'user_id': 3, 'symbol': 'MU'}],
    },
    'removed': {},
}

SPECS[6] = {
    'paths': [r'/', r'/lookup\?s=AMD', r'/quote/AMD',
              r'/quote/AMD/statistics', r'/lookup\?s=NVDA', r'/quote/NVDA',
              r'/quote/NVDA/statistics', r'/login', r'/alerts',
              r'/watchlist'],
    'claims': [
        ('AMD trailing P/E', r'154\.88'),
        ('AMD profit margin', r'15\.58\s*percent'),
        ('NVDA trailing P/E', r'28\.87'),
        ('NVDA profit margin', r'63\.66\s*percent'),
        ('lower P/E company', r'\bnvda\b[^.]{0,60}lower|'
                              r'lower[^.]{0,60}\bnvda\b'),
        ('new alert status', r'\bactive\b'),
        ('Bob watchlist', r'watchlist[^.]{0,120}\bnvda\b|'
                          r'\bnvda\b[^.]{0,120}watchlist'),
    ],
    'forbidden': [r'\bamd\b[^.]{0,40}lower\s*p/?e'],
    'added': {
        'price_alerts': [{'user_id': 2, 'symbol': 'NVDA', 'direction': 'above',
                          'threshold': 700.0, 'note': None}],
        'watch_items': [{'user_id': 2, 'symbol': 'NVDA'}],
    },
    'removed': {},
}

SPECS[7] = {
    'paths': [r'/', r'/screener\?preset=most_actives', r'/quote/NU',
              r'/quote/NU/history', r'/quote/NU/statistics', r'/login',
              r'/alerts', r'/watchlist'],
    'claims': [
        ('most-traded symbol', r'\bnu\b'),
        ('volume', r'100[,]?868[,]?354'),
        ('percent change', r'\+?2\.51\s*percent'),
        ('industry', r'banks\s*-\s*regional'),
        ('most recent close', r'12\.66'),
        ('first captured close', r'14\.46'),
        ('50-day average', r'14\.33'),
        ('watchlist', r'watchlist[^.]{0,150}\bnu\b|'
                      r'\bnu\b[^.]{0,150}watchlist'),
    ],
    'forbidden': [],
    'added': {
        'price_alerts': [{'user_id': 4, 'symbol': 'NU', 'direction': 'above',
                          'threshold': 20.0, 'note': 'LatAm growth'}],
        'watch_items': [{'user_id': 4, 'symbol': 'NU'}],
    },
    'removed': {},
}

SPECS[8] = {
    'paths': [r'/', r'/news\?topic=latest&q=buyback',
              r'/markets/stocks/articles/stock-market-today-sept-30',
              r'/news\?topic=earnings', r'/login', r'/lookup\?s=NVDA',
              r'/quote/NVDA', r'/watchlist'],
    'claims': [
        ('buyback article count', r'\b2\s*\w*\s*(?:articles?|results?|'
                                 r'matches)\b|'
                                 r'\b2\b[^.]{0,30}(?:articles?|results?|'
                                 r'matches)\b'),
        ('article title', r'nvidia\s+authorizes\s+\$?150\s*b(?:illion)?\s*'
                          r'buyback'),
        ('publisher', r'motley\s*fool'),
        ('article author', r'will\s*healy'),
        ('NVDA close', r'228\.38'),
        ('NVDA change', r'up\s*0\.51\s*percent'),
        ('NVDA trading volume', r'117\.7\s*m'),
        ('earnings topic article', r'cboe'),
        ('Dana watchlist count', r'\b5\s*(?:\w+\s+)?(?:symbols?|companies|'
                                r'stocks|entries|items)\b'),
    ],
    'forbidden': [r'\b(?:4|6)\s*(?:symbols?|companies)\b'],
    'added': {
        'watch_items': [{'user_id': 4, 'symbol': 'NVDA'}],
    },
    'removed': {},
}

SPECS[9] = {
    'paths': [r'/', r'/signup', r'/lookup\?s=Apple', r'/quote/AAPL',
              r'/quote/AAPL/financials', r'/quote/AAPL/statistics',
              r'/quote/AAPL/profile', r'/watchlist',
              r'/news\?topic=latest&q=Apple',
              r'/technology/ai/articles/bank-america-warns-apple'],
    'claims': [
        ('fiscal year end', r'2025-09-30|september\s*30[,]?\s*2025'),
        ('total revenue', r'416\.16\s*b'),
        ('net income', r'112\.01\s*b'),
        ('PEG ratio', r'2\.64'),
        ('beta', r'1\.08'),
        ('employees', r'150[,]?000'),
        ('watchlist symbols', r'watchlist[^.]{0,60}\baapl\b|'
                              r'\baapl\b[^.]{0,60}watchlist'),
        ('Apple news match count', r'\b9\s*(?:\w+\s+)?'
                                   r'(?:articles?|results?|matches)\b'),
        ('newest article publisher', r'thestreet'),
        ('newest article author', r'hillary\s*remy'),
    ],
    'forbidden': [],
    'added': {
        'users': [{'name': 'Priya Nair', 'email': 'priya.nair@test.com',
                   'joined': '2026-09-30',
                   'password_hash': 'SHAPE:bcrypt:TestPass123!'}],
        'watch_items': [{'user_id': 5, 'symbol': 'AAPL'}],
    },
    'removed': {},
}

SPECS[10] = {
    'paths': [r'/', r'/lookup\?s=Coca-Cola', r'/quote/KO', r'/quote/KO/profile',
              r'/lookup\?s=PepsiCo', r'/quote/PEP',
              r'/quote/PEP/statistics', r'/login', r'/alerts',
              r'/watchlist'],
    'claims': [
        ('KO sector', r'consumer\s*defensive'),
        ('KO industry', r'beverages\s*-\s*non-alcoholic'),
        ('KO employees', r'65[,]?900'),
        ('KO website', r'coca-colacompany\.com'),
        ('KO forward dividend', r'2\.12\s*\(\s*2\.46\s*percent\s*\)'),
        ('PEP profit margin', r'10\.79\s*percent'),
        ('PEP trailing P/E', r'16\.61'),
        ('PEP alert status', r'\btriggered\b'),
        ('Bob watch count', r'\b3\s*(?:symbols?|companies|stocks)\b'),
    ],
    'forbidden': [r'\b(?:2|4)\s*(?:symbols?|companies)\s*'],
    'added': {
        'price_alerts': [{'user_id': 2, 'symbol': 'PEP', 'direction': 'above',
                          'threshold': 100.0, 'note': 'Cola wars'}],
    },
    'removed': {},
}

SPECS[11] = {
    'paths': [r'/', r'/calendar/earnings\?day=2026-10-04',
              r'/calendar/earnings\?day=2026-09-27', r'/lookup\?s=Apple',
              r'/quote/AAPL', r'/quote/AAPL/statistics', r'/login',
              r'/alerts'],
    'claims': [
        ('next week busiest day', r'october\s*8[,]?\s*2026'),
        ('next week event count', r'\b97\s*(?:events?|earnings?|reports?)\b'),
        ('this week busiest day', r'october\s*1[,]?\s*2026'),
        ('this week event count', r'\b152\s*(?:events?|earnings?|reports?)\b'),
        ('Apple next earnings date', r'october\s*29[,]?\s*2026'),
        ('1-year target', r'328\.22'),
        ('50-day average', r'321\.98'),
        ('new alert status', r'\bactive\b'),
        ('Dana alert total', r'\b2\s*(?:price\s*)?alerts?\b'),
    ],
    'forbidden': [r'\b(?:1|3)\s*(?:price\s*)?alerts?\b'],
    'added': {
        'price_alerts': [{'user_id': 4, 'symbol': 'AAPL', 'direction': 'above',
                          'threshold': 400.0, 'note': 'Earnings run'}],
    },
    'removed': {},
}

SPECS[12] = {
    'paths': [r'/', r'/login', r'/watchlist', r'/lookup\?s=Merck',
              r'/quote/MRK', r'/alerts'],
    'claims': [
        ('initial watchlist', r'lly[^.]{0,40}unh[^.]{0,40}pfe|'
                             r'unh[^.]{0,40}pfe'),
        ('MRK trailing P/E', r'116\.25'),
        ('MRK 52-week range', r'82\.01\s*-\s*156\.92'),
        ('new alert status', r'\bactive\b'),
        ('final watchlist', r'lly[^.]{0,60}pfe[^.]{0,60}mrk'),
    ],
    'forbidden': [r'final[^.]{0,80}\bunh\b'],
    'added': {
        'price_alerts': [{'user_id': 3, 'symbol': 'MRK', 'direction': 'above',
                          'threshold': 160.0, 'note': 'Pharma rotation'}],
        'watch_items': [{'user_id': 3, 'symbol': 'MRK'}],
    },
    'removed': {
        'watch_items': [{'user_id': 3, 'symbol': 'UNH'}],
    },
}

SPECS[13] = {
    'paths': [r'/', r'/login', r'/alerts', r'/lookup\?s=Tesla',
              r'/quote/TSLA', r'/quote/TSLA/statistics'],
    'claims': [
        ('initial alerts', r'\bnvda\b[^.]{0,80}below\s*150|'
                           r'below\s*150[^.]{0,80}\bnvda\b'),
        ('initial Tesla alert', r'\babove\s*480\b'),
        ('new alert status', r'\bactive\b'),
        ('final alert count', r'\b2\s*(?:price\s*)?alerts?\b'),
        ('Tesla 50-day average', r'347\.45'),
    ],
    'forbidden': [r'\b(?:1|3)\s*(?:price\s*)?alerts?\b'],
    'added': {
        'price_alerts': [{'user_id': 1, 'symbol': 'TSLA', 'direction': 'above',
                          'threshold': 900.0, 'note': 'Upside breakout'}],
    },
    'removed': {
        'price_alerts': [{'user_id': 1, 'symbol': 'TSLA', 'direction': 'above',
                          'threshold': 480.0, 'note': None}],
    },
}

SPECS[14] = {
    'paths': [r'/', r'/screener', r'/screener\?[^#]*sector=Healthcare',
              r'[^#]*mcap_min=10000000000', r'[^#]*mcap_max=200000000000',
              r'[^#]*sort=change', r'/quote/UTHR',
              r'/quote/UTHR/statistics', r'/login', r'/watchlist'],
    'claims': [
        ('Day Gainers top', r'\buthr\b[^.]{0,40}\+?12\.55\s*percent'),
        ('first filtered symbol', r'\buthr\b[^.]{0,30}\+?12\.55'),
        ('second filtered symbol', r'\bibrx\b[^.]{0,30}\+?6\.91'),
        ('third filtered symbol', r'\bpfe\b[^.]{0,30}-\s*0\.70'),
        ('52-week change', r'\+?8\.58\s*percent'),
        ('Bob watchlist', r'watchlist[^.]{0,150}\buthr\b|'
                          r'\buthr\b[^.]{0,150}watchlist'),
    ],
    'forbidden': [],
    'added': {
        'watch_items': [{'user_id': 2, 'symbol': 'UTHR'}],
    },
    'removed': {},
}

SPECS[15] = {
    'paths': [r'/', r'/lookup\?s=bitcoin', r'/quote/BTC-USD', r'/news',
              r'/news\?topic=latest&q=stablecoin',
              r'/markets/crypto/articles/stripes-bridge-launches-ousd',
              r'/login', r'/alerts', r'/watchlist'],
    'claims': [
        ('bitcoin matches', r'\bbtc-usd\b'),
        ('BTC price', r'83[,]?452\.08'),
        ('BTC market cap', r'1\.68\s*t'),
        ('BTC 52-week range', r'57[,]?747\.77\s*-\s*126[,]?198\.07'),
        ('stablecoin article count', r'\b2\s*\w*\s*'
                                    r'(?:articles?|results?|matches)\b|'
                                    r'(?:articles?|results?|matches)[^.]{0,30}'
                                    r'\b2\b'),
        ('publisher', r'bankless'),
        ('author', r'william\s*peaster'),
        ('reserve custodians', r'blackrock[^.]{0,40}bny[^.]{0,40}'
                              r'lead\s*bank'),
        ('alert status', r'\bactive\b'),
        ('Dana watchlist count', r'\b5\s*(?:\w+\s+)?(?:symbols?|companies|'
                                r'stocks|entries|items)\b'),
    ],
    'forbidden': [r'\b(?:4|6)\s*(?:symbols?|companies)\b'],
    'added': {
        'price_alerts': [{'user_id': 4, 'symbol': 'BTC-USD',
                          'direction': 'above', 'threshold': 90000.0,
                          'note': 'ETF bid'}],
        'watch_items': [{'user_id': 4, 'symbol': 'BTC-USD'}],
    },
    'removed': {},
}

SPECS[16] = {
    'paths': [r'/', r'/sectors', r'/sectors/healthcare', r'/quote/LLY',
              r'/quote/LLY/statistics', r'/quote/JNJ',
              r'/quote/JNJ/statistics', r'/login', r'/alerts',
              r'/watchlist'],
    'claims': [
        ('Healthcare company count', r'\b39\s*(?:companies|captured|listed)\b'),
        ('biggest industry', r'biotechnology'),
        ('industry member count', r'\b14\s*companies\b'),
        ('largest company', r'\blly\b'),
        ('second largest', r'\bjnj\b'),
        ('LLY trailing P/E', r'38\.92'),
        ('LLY profit margin', r'33\.53\s*percent'),
        ('JNJ trailing P/E', r'30\.71'),
        ('JNJ profit margin', r'21\.48\s*percent'),
        ('alert status', r'\bactive\b'),
        ('watchlist count', r'watchlist[^.]{0,60}\b4\b|'
                            r'\b4\b[^.]{0,60}watchlist|'
                            r'\b4\s*(?:symbols?|entries|items|companies|'
                            r'stocks)\b'),
    ],
    'forbidden': [],
    'added': {
        'price_alerts': [{'user_id': 2, 'symbol': 'JNJ', 'direction': 'above',
                          'threshold': 300.0, 'note': 'Dividend value'}],
        'watch_items': [{'user_id': 2, 'symbol': 'JNJ'}],
    },
    'removed': {},
}

SPECS[17] = {
    'paths': [r'/', r'/lookup\?s=Microsoft', r'/quote/MSFT',
              r'/quote/MSFT/history', r'/quote/MSFT/statistics', r'/login',
              r'/watchlist', r'/alerts'],
    'claims': [
        ('most recent close', r'512\.90'),
        ('first captured close', r'501\.02'),
        ('50-day average', r'480\.25'),
        ('200-day average', r'432\.30'),
        ('Alice watchlist count', r'\b4\s*(?:symbols?|companies|stocks)\b'),
        ('new alert status', r'\bactive\b'),
        ('Alice alert total', r'\b3\s*(?:price\s*)?alerts?\b'),
    ],
    'forbidden': [r'\b(?:2|4)\s*alerts?\b'],
    'added': {
        'price_alerts': [{'user_id': 1, 'symbol': 'MSFT', 'direction': 'above',
                          'threshold': 600.0, 'note': 'Azure wave'}],
    },
    'removed': {},
}

SPECS[18] = {
    'paths': [r'/', r'/news\?topic=latest&q=inflation',
              r'/economy/policy/articles/feds-kashkari-says-central-bank',
              r'/lookup\?s=gold', r'/quote/GC', r'/login', r'/alerts',
              r'/watchlist'],
    'claims': [
        ('inflation article count', r'\b15\s*\w*\s*(?:articles?|results?|'
                                   r'matches)\b|'
                                   r'\b15\b[^.]{0,30}(?:articles?|results?|'
                                   r'matches)\b'),
        ('publisher', r'reuters'),
        ('author', r'michael\s*s\.?\s*derby'),
        ('gold price', r'4[,]?183\.20'),
        ('gold percent change', r'-\s*0\.08\s*percent'),
        ('alert status', r'\bactive\b'),
        ('Carol watchlist count', r'\b4\s*(?:symbols?|companies|stocks)\b'),
    ],
    'forbidden': [r'\b(?:3|5)\s*(?:symbols?|companies)\b'],
    'added': {
        'price_alerts': [{'user_id': 3, 'symbol': 'GC=F', 'direction': 'above',
                          'threshold': 4300.0, 'note': 'Rally hedge'}],
        'watch_items': [{'user_id': 3, 'symbol': 'GC=F'}],
    },
    'removed': {},
}

SPECS[19] = {
    'paths': [r'/', r'/screener', r'/screener\?[^#]*sector=Utilities',
              r'[^#]*yield_min=4', r'[^#]*sort=yield', r'/quote/D',
              r'/login', r'/alerts', r'/watchlist'],
    'claims': [
        ('first utility', r'\bduk-pa\b[^.]{0,30}6\.59'),
        ('second utility', r'\bken\b[^.]{0,30}6\.40'),
        ('third utility', r'\bd\b[^.]{0,30}4\.40'),
        ('D dividend yield', r'2\.67\s*\(\s*4\.40\s*percent\s*\)'),
        ('D market cap', r'53\.23\s*b'),
        ('D next earnings date', r'october\s*30[,]?\s*2026'),
        ('alerts remaining', r'\bno\s*alerts?\b|\b0\s*alerts?\b'),
        ('Dana watchlist count', r'\b5\s*(?:\w+\s+)?(?:symbols?|companies|'
                                r'stocks|entries|items)\b'),
    ],
    'forbidden': [r'\b1\s*alert\s*remains?\b'],
    'added': {
        'watch_items': [{'user_id': 4, 'symbol': 'D'}],
    },
    'removed': {
        'price_alerts': [{'user_id': 4, 'symbol': 'META', 'direction': 'below',
                          'threshold': 600.0, 'note': 'Re-entry'}],
    },
}

TEMPLATE = '''#!/usr/bin/env python3
"""Deterministic reviewer verifier for task YahooFinance--{idx} (yahoo_finance).

Ground truth frozen from the reviewer's honest two-round Chromium walks of
orch/contribute/yahoo_finance @ dacbf663 (review container webharbor:yf-review,
per-task control-plane reset + fresh context; evidence tree
wh-yf-review-evidence/runs/round1|2; every walked fact independently
cross-checked against the frozen in-image seed database).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import verify_lib  # noqa: E402

SPEC = {{
 "task_id": "YahooFinance--{idx}",
 "question": {question!r},
 "paths": {paths!r},
 "claims": {claims!r},
 "forbidden": {forbidden!r},
 "added": {added!r},
 "removed": {removed!r},
}}

if __name__ == "__main__":
    raise SystemExit(verify_lib.main(SPEC))
'''


def main():
    for idx, spec in SPECS.items():
        body = TEMPLATE.format(
            idx=idx,
            question=TASKS[f'YahooFinance--{idx}'],
            paths=spec['paths'],
            claims=[list(c) for c in spec['claims']],
            forbidden=spec['forbidden'],
            added=spec['added'],
            removed=spec['removed'],
        )
        (VT / f'verify_{idx}.py').write_text(body)
        print('wrote', f'verify_{idx}.py')


if __name__ == '__main__':
    main()
