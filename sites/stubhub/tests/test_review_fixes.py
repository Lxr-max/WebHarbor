"""Regression checks for inventory and payment validation."""
import importlib

def test_partial_purchase_keeps_remaining_ticket(client, alice):
    m=importlib.import_module("app")
    with m.app.app_context():
        e=m.Event.query.filter_by(upstream_id=160436498).one()
        l=m.Listing.query.filter_by(event_id=e.id,is_sold=False).order_by(m.Listing.price).first()
        lid, qty=l.id,l.quantity
    client.post('/secure/checkout/start',data={'listing_id':lid,'quantity':1})
    client.post('/secure/checkout/review',data={'delivery':'instant'})
    client.post('/secure/checkout/payment',data={'card_id':1})
    response=client.post('/secure/checkout/confirm')
    assert response.status_code==302
    with m.app.app_context():
        m.db.session.expire_all();l=m.db.session.get(m.Listing,lid)
        assert l.quantity==qty-1 and not l.is_sold

def test_past_month_in_current_year_is_rejected(client, alice):
    response=client.post('/secure/myaccount/payments',data={'number':'5555555555554444','holder':'Alice Johnson','exp_month':1,'exp_year':2026,'cvv':'123','brand':'Mastercard'},follow_redirects=True)
    assert 'Enter a valid expiry date' in response.get_data(as_text=True)
