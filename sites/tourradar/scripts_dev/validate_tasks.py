#!/usr/bin/env python3
"""Ground-truth computation for all 22 tourradar tasks against the full DB.

Answers are read straight from the seeded SQLite (what the pages render).
Used to prove each task premise holds on the full 210-tour dataset and the
expected answer is unique + stable.
"""
import json
import sqlite3
import sys

db = sqlite3.connect(sys.argv[1] if len(sys.argv) > 1 else 'instance/tourradar.db')
db.row_factory = sqlite3.Row


def rows(q, *a):
    return db.execute(q, a).fetchall()


def one(q, *a):
    return db.execute(q, a).fetchone()


def j(v):
    return json.loads(v or 'null')


print('== T0: cheapest Japan tour under $2500 ==')
r = one("""select t.id, t.name, t.price_current, t.price_from, t.price_basis
           from tours t join destinations d on d.slug='japan'
           where t.dest_slugs like '%japan%'
             and coalesce(t.price_current, t.price_from) < 2500
           order by coalesce(t.price_current, t.price_from) asc, t.id asc""")
print(dict(r) if r else 'NONE')
# ties?
tied = rows("""select id, name, coalesce(price_current, price_from) p from tours
               where dest_slugs like '%japan%' and coalesce(price_current, price_from) < 2500
               order by p asc""")
print('candidates:', [(x['id'], x['name'][:40], x['p']) for x in tied[:5]])
top = tied[0]['p'] if tied else None
print('ties at min:', [x['id'] for x in tied if x['p'] == top])
dep = one("select count(*) c from departures where tour_id=? and status='available'", tied[0]['id'])
print('available departures for cheapest:', dep['c'])

print()
print('== T1: Kenya/Tanzania safari, March 2027, guaranteed, Single room ==')
cands = rows("""select t.id, t.name, t.price_current, t.dest_slugs, d.start_date, d.price, d.guaranteed, d.status
             from tours t join departures d on d.tour_id=t.id
             where (t.dest_slugs like '%kenya%' or t.dest_slugs like '%tanzania%')
               and d.start_date like '2027-03%' and d.guaranteed=1
             order by d.price asc""")
for c in cands[:6]:
    print(dict(c))
print('n candidates:', len(cands))

print()
print('== T2: Alice upcoming confirmed ==')
for b in rows("""select b.ref, b.departure_date, b.status from bookings b
                 join users u on u.id=b.user_id where u.email='alice.j@test.com'"""):
    print(dict(b))

print()
print('== T3: Bob wishlist + cheapest Vietnam ==')
for w in rows("""select w.id, w.tour_id, t.name, t.cities, t.countries from wishlist_items w
                 join users u on u.id=w.user_id join tours t on t.id=w.tour_id
                 where u.email='bob.c@test.com' order by w.id"""):
    print(dict(w))
v = rows("""select id, name, coalesce(price_current, price_from) p from tours
            where dest_slugs like '%vietnam%' order by p asc, id asc""")
print('vietnam cheapest:', [(x['id'], x['name'][:40], x['p']) for x in v[:4]])
print('ties at min:', [x['id'] for x in v if x['p'] == v[0]['p']])

print()
print('== T4: Intrepid vs G Adventures, Nepal tours ==')
for nm in ('Intrepid Travel', 'G Adventures'):
    o = one("select * from operators where name=?", nm)
    ts = rows("""select t.id, t.name, coalesce(t.price_current, t.price_from) p from tours t
                 join operators o on o.id=t.operator_id
                 where o.name=? and (t.dest_slugs like '%nepal%' or t.countries like '%Nepal%')
                 order by p asc""", nm)
    print(o['name'], 'rating', o['rating'], '| nepal tours:', [(x['id'], x['p']) for x in ts])

print()
print('== T5: Machu Picchu tours, most reviews, 2027 sold-out share ==')
mp = rows("""select id, name, review_count from tours
             where cities like '%Machu Picchu%' or name like '%Machu Picchu%'
             order by review_count desc""")
print([(x['id'], x['name'][:44], x['review_count']) for x in mp[:6]])
t5 = mp[0]
d27 = rows("select status, count(*) c from departures where tour_id=? and start_date like '2027%' group by status", t5['id'])
print('2027 departures by status:', [(x['status'], x['c']) for x in d27])

print()
print('== T6: Iceland Northern Lights 5-8d <$2000 instant ==')
il = rows("""select id, name, duration_days, price_current, instant_confirm from tours
             where dest_slugs like '%iceland%' and (name like '%Northern Lights%' or name like '%Aurora%')
               and duration_days between 5 and 8 and coalesce(price_current, price_from) < 2000
             order by coalesce(price_current, price_from) asc""")
print([(x['id'], x['name'][:44], x['duration_days'], x['price_current'], x['instant_confirm']) for x in il])
if il:
    a = one("select start_date from departures where tour_id=? and status='available' order by start_date limit 1", il[0]['id'])
    print('first available:', dict(a) if a else None)

print()
print('== T7/T8: Europe Taster ==')
et = one("select * from tours where name like 'Europe Taster%'")
print(dict(et))
g = rows("select count(*) c from departures where tour_id=? and guaranteed=1", et['id'])
print('guaranteed departures:', g[0]['c'])
revs = rows("""select id, author, rating, traveled_month, month, guide_name, reply, reply_by from reviews
              where tour_id=? and guide_name like '%Dimos%' order by id desc""", et['id'])
for r in revs[:4]:
    print(dict(r))

print()
print('== T9: highest-rated Kenya tour ==')
k = rows("""select id, name, rating, review_count, coalesce(price_current, price_from) p, good_to_know
            from tours where dest_slugs like '%kenya%' order by rating desc, review_count desc""")
for x in k[:5]:
    print(x['id'], x['name'][:44], x['rating'], x['review_count'], x['p'])
gtk = j(k[0]['good_to_know'])
print('gtk keys:', list(gtk.keys()) if gtk else None)

print()
print('== T10: Inca Adventures 7-day Lima->Machu Picchu ==')
ia = rows("select id, name, duration_days, start_city, end_city from tours where name like '%Inca Adventures%'")
print([dict(x) for x in ia])

print()
print('== T11: Japan guide ==')
jp = one("select * from destinations where slug='japan'")
sec = j(jp['sections'])
print('japan sections:', list(sec.keys()) if sec else None)
for m in ('2026-09', '2026-10', '2026-11'):
    c = one("""select count(*) c from departures d join tours t on t.id=d.tour_id
               where t.dest_slugs like '%japan%' and d.start_date like ?""", m + '%')
    print('japan departures', m, c['c'])

print()
print('== T12: Ultimate Egyptian Experience + operator Egypt tours ==')
ue = one("select * from tours where name like 'Ultimate Egyptian Experience%'")
print(dict(ue))
opq = one("select * from operators where id=?", ue['operator_id'])
print('operator:', opq['name'])
epts = rows("""select t.id, t.name, coalesce(t.price_current, t.price_from) p from tours t
               join operators o on o.id=t.operator_id
               where o.name=? and t.dest_slugs like '%egypt%' order by p asc""", opq['name'])
print([(x['id'], x['p']) for x in epts[:5]])

print()
print('== T13: David completed booking ==')
for b in rows("""select b.ref, b.tour_id, t.name, b.status, b.departure_date from bookings b
                 join users u on u.id=b.user_id join tours t on t.id=b.tour_id
                 where u.email='david.k@test.com'"""):
    print(dict(b))

print()
print('== T14: cheapest Europe tour > $1000 ==')
e = rows("""select id, name, coalesce(price_current, price_from) p from tours
            where dest_slugs like '%europe%' and coalesce(price_current, price_from) > 1000
            order by p asc, id asc""")
print([(x['id'], x['name'][:40], x['p']) for x in e[:5]])
print('ties at min:', [x['id'] for x in e if x['p'] == e[0]['p']])

print()
print('== T15: Morocco tours >100 reviews, smallest max group ==')
mo = rows("""select id, name, review_count, group_min, group_max, coalesce(price_current, price_from) p
             from tours where dest_slugs like '%morocco%' and review_count > 100
             order by group_max asc, review_count desc""")
for x in mo[:6]:
    print(dict(x))

print()
print('== T16: Peru Challenging tours ==')
pe = rows("""select id, name, duration_days, start_city, end_city from tours
             where dest_slugs like '%peru%' and physical='Challenging Intensity'
             order by duration_days asc""")
print([dict(x) for x in pe])

print()
print('== T17: Thailand group tours 7-10 days ==')
th = rows("""select id, name, duration_days, group_type, coalesce(price_current, price_from) p from tours
             where dest_slugs like '%thailand%' and duration_days between 7 and 10
               and group_type='Group Tour'
             order by p asc""")
print([(x['id'], x['name'][:40], x['p']) for x in th[:6]])

print()
print('== T18: Greece island tours < $1800 private room ==')
gr = rows("""select id, name, rating, review_count, coalesce(price_current, price_from) p, price_basis, dest_slugs, cities
             from tours where dest_slugs like '%greece%' and coalesce(price_current, price_from) < 1800
             order by rating desc, review_count desc""")
for x in gr[:6]:
    print(x['id'], x['name'][:44], x['rating'], x['p'], x['price_basis'], '|', x['cities'][:60])

print()
print('== T19: search Nile cruise ==')
# mimic the app's scored search
q = rows("""select id, name, operator_id, coalesce(price_current, price_from) p from tours
            where lower(name) like '%nile cruise%' or lower(intro) like '%nile cruise%'
            order by p asc""")
print('name matches:', [(x['id'], x['name'][:44], x['p']) for x in q[:6]])

print()
print('== T20: operator comparison ==')
for nm in ('Expat Explore Travel', 'Intrepid Travel', 'Trafalgar'):
    o = one("select * from operators where name=?", nm)
    c = one("""select count(*) c from tours t join operators o on o.id=t.operator_id where o.name=?""", nm)
    print(o['name'], '| rating', o['rating'], '| resp rate', o['response_rate'], '| resp time', o['response_time'], '| tours', c['c'])

print()
print('== T21: three Egypt tours ==')
for nm in ('Ancient Wonders Egypt', 'Ultimate Egyptian Experience', 'Historic Horizons'):
    t = rows("select id, name, rating, discount_pct, price_from, price_current from tours where name like ?", nm + '%')
    print([(x['id'], x['name'][:44], x['rating'], x['discount_pct'], x['price_from'], x['price_current']) for x in t])
