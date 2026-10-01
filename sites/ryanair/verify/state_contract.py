"""Preserve unrelated state and validate complete persisted booking receipts."""
import json
import sqlite3
from pathlib import Path


def read(path):
    with sqlite3.connect(f'file:{path}?mode=ro', uri=True) as con:
        con.row_factory = sqlite3.Row
        return {t: [dict(r) for r in con.execute(f'SELECT * FROM "{t}"')]
                for (t,) in con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}


def check(judge, task_id, initial, after):
    task = int(task_id.split('--')[-1])
    before, final = read(initial), read(after)
    def require(name, condition):
        judge.check(name, condition, 'Exact task-specific state contract')
    def unchanged(table):
        return before[table] == final[table]
    account = task == 8
    checkin_ref = {10: 'R2M6YB', 18: 'K5R7JT'}.get(task)
    booking_task = task not in (8, 9, 10, 11, 18)
    allowed = {'users', 'payment_methods'} if account else ({'bookings'} if checkin_ref else ({'bookings', 'booking_passengers', 'trip_states'} if booking_task else set()))
    require('unrelated_tables_unchanged', set(before) == set(final) and all(unchanged(t) for t in before if t not in allowed))
    if account:
        old = {r['id']: r for r in before['users']}
        new = {r['id']: r for r in final['users']}
        expected = {k: dict(v) for k, v in old.items()}
        alice = next(r for r in expected.values() if r['email'] == 'alice.j@test.com')
        alice.update(phone='+44 7700 900777', address_line1='2 Test Lane', city='Manchester', postcode='M1 1AA')
        require('only_alice_contact_fields_updated', expected == new)
        require('other_users_cards_preserved', [r for r in before['payment_methods'] if r['user_id'] != alice['id']] == [r for r in final['payment_methods'] if r['user_id'] != alice['id']])
        cards = [r for r in final['payment_methods'] if r['user_id'] == alice['id']]
        require('replacement_card_complete', len(cards) == 1 and all(cards[0].get(k) == v for k, v in {'card_type': 'Mastercard', 'last4': '4444', 'holder': 'Alice Johnson', 'expiry': '05/28', 'is_default': 1}.items()))
    elif checkin_ref:
        expected = [dict(r) for r in before['bookings']]
        for row in expected:
            if row['booking_ref'] == checkin_ref:row['checked_in'] = 1
        require('only_requested_checkin_changed', final['bookings'] == expected)
    elif booking_task:
        old = {r['id']: r for r in before['bookings']}
        new = {r['id']: r for r in final['bookings']}
        require('previous_bookings_unchanged', all(new.get(k) == r for k, r in old.items()))
        added = [r for k, r in new.items() if k not in old]
        require('one_confirmed_guest_booking', len(added) == 1 and added[0]['status'] == 'confirmed' and added[0]['user_id'] is None and not added[0]['checked_in'])
        if len(added) != 1:return
        booking = added[0]
        old_pax = {r['id']: r for r in before['booking_passengers']}
        new_pax = {r['id']: r for r in final['booking_passengers']}
        require('previous_passengers_unchanged', all(new_pax.get(k) == r for k, r in old_pax.items()))
        pax = [r for k, r in new_pax.items() if k not in old_pax]
        require('new_passengers_belong_to_booking', len(pax) == booking['adults'] + booking['teens'] + booking['children'] and all(r['booking_id'] == booking['id'] and r['first_name'].strip() and r['last_name'].strip() for r in pax))
        require('no_unrequested_passenger_categories', booking['children'] == booking['infants'] == 0 and booking['teens'] == (1 if task == 15 else 0))
        require('no_unrequested_sms_or_credit', not booking['sms_updates'] and booking['inflight_credit'] == 0)
        require('insurance_choice', booking['insurance_key'] == ('plus' if task in (5, 14) else ('standard' if task == 19 else '')))
        require('promo_choice', booking['promo_code'] == ('RYANAIR10' if task in (6, 20) else ''))
        if task == 0:require('requested_contact_phone', booking['contact_phone'] == '+44 7700 900123')
        expected_ft = task in (2, 3, 5, 19)  # included in the displayed Plus fare
        require('fast_track_both_legs_saved', bool(booking['fast_track_out']) == expected_ft and bool(booking['fast_track_in']) == expected_ft)
        for i, passenger in enumerate(pax):
            for direction in ('out', 'in'):
                active = direction == 'out' or booking['inbound_schedule_id'] is not None
                included = booking['fare_type'] in ('plus', 'flexi_plus')
                bags = int(active and (included or (task in (4, 13) and i == 0)))
                require(f'passenger_{i}_{direction}_bag_quantity', passenger['checkin_20kg_'+direction] == bags and passenger['checkin_10kg_'+direction] == 0 and passenger['checkin_23kg_'+direction] == 0)
                cabin = 'priority' if active and (task == 4 or booking['fare_type'] in ('regular', 'flexi_plus')) else 'small-bag'
                require(f'passenger_{i}_{direction}_cabin_allowance', passenger['cabin_'+direction] == cabin)
                if task not in (3, 19):require(f'passenger_{i}_{direction}_no_paid_seat', not passenger['seat_'+direction])
        require('previous_trip_states_preserved', all(r in final['trip_states'] for r in before['trip_states']))
        trip_additions = [r for r in final['trip_states'] if r not in before['trip_states']]
        require('one_trip_state', len(trip_additions) == 1)
        if len(trip_additions) == 1:
            data = json.loads(trip_additions[0]['data'])
            require('trip_matches_booking', data.get('fare') == booking['fare_type'] and
                    data.get('outboundSchedule') == booking['outbound_schedule_id'] and
                    data.get('dateOut') == booking['outbound_date'])
        subtotal = sum(booking[k] for k in ('flights_total', 'seats_total', 'bags_total', 'extras_total'))
        require('receipt_arithmetic', abs(booking['card_fee'] - round(subtotal * .02, 2)) < .005 and abs(booking['total'] - round(subtotal + booking['card_fee'], 2)) < .005)
