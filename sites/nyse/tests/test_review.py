"""Regression checks for captured-data research and calendar-day chart zoom."""
from datetime import datetime
import re


def test_year_chart_uses_calendar_days(client):
    response = client.get('/quote/XNYS:NIO?zoom=1Y')
    assert response.status_code == 200
    m = re.search(rb'Closing price chart from ([0-9/]+) to ([0-9/]+)', response.data)
    assert m
    first, last = [datetime.strptime(x.decode(), '%Y/%m/%d') for x in m.groups()]
    assert 350 <= (last - first).days <= 365


def test_bell_search_includes_event_purpose(client):
    r = client.get('/bell/calendar?q=IPO&from=2026-01-01&to=2026-06-30&type=Opening+Bell')
    assert r.status_code == 200
    assert b'Pershing Square' in r.data
    assert b'3 bell events' in re.sub(rb'<[^>]+>', b'', r.data)


def test_historical_ipo_search(client):
    r = client.get('/ipo-center/history?q=Aeromexico')
    assert r.status_code == 200
    assert b'Grupo Aeromexico' in r.data
    assert b'222,819,175' in r.data
    assert b'1 matching offerings' in r.data
    assert b'Accelevation' not in r.data
