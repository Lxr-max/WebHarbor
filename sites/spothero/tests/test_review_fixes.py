"""Regression checks for decoded destination content and monthly booking dates."""
import re
import pytest

@pytest.mark.parametrize('start,end',[('2026-10-01T00:00','2026-11-01T00:00'),('2026-12-01T00:00','2027-01-01T00:00'),('2027-01-31T00:00','2027-02-28T00:00')])
def test_monthly_reservation_covers_calendar_month(client,start,end):
    text=client.get('/purchase/hourly',query_string={'facility':2348,'kind':'monthly','starts':start}).get_data(as_text=True)
    assert 'name="ends" value="'+end+'"' in text

def test_destination_json_is_rendered_as_rows_not_characters(client):
    text=client.get('/destination/seattle/climate-pledge-arena-parking').get_data(as_text=True)
    assert '<p class="muted">[</p>' not in text
    assert '<td></td><td>$ - $</td>' not in text
    assert len(re.findall('<tr>',text)) < 30

def test_redemption_renders_text_without_escaped_tags(client):
    text=client.get('/facility/6075/475-e-huron-st').get_data(as_text=True)
    assert '&lt;p&gt;' not in text and '&lt;b&gt;' not in text
