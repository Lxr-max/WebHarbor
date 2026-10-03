"""Exact state preservation for the reviewed travel workflows."""
import json
import sqlite3


def check_state(judge, task, initial, final):
    n=int(task.split('--')[-1])
    if n not in {0,1,2,3,6,11,12,13,14,17,21}:return
    before=sqlite3.connect(initial);after=sqlite3.connect(final)
    before.row_factory=after.row_factory=sqlite3.Row
    def rows(db,table):
        return {r['ref'] if table=='bookings' else r['id']:dict(r) for r in db.execute('SELECT * FROM '+table)}
    allowed={0:{'bookings','users'},1:{'bookings','users'},2:{'bookings','wishlist_items'},3:{'wishlist_items'},6:{'bookings','users'},11:{'users','wishlist_items'},12:{'tour_qa'},13:{'reviews'},14:{'bookings','users'},17:{'bookings','users'},21:{'bookings','users'}}[n]
    diffs={}
    try:
        tables=[r[0] for r in before.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
        for table in tables:
            a,b=rows(before,table),rows(after,table)
            new=[b[k] for k in b.keys()-a.keys()];gone=[a[k] for k in a.keys()-b.keys()];changed=[(a[k],b[k]) for k in a.keys()&b.keys() if a[k]!=b[k]]
            diffs[table]=(new,gone,changed)
            if table not in allowed:judge.check('preserved_'+table,a==b,'unrequested table changes')
        for table in allowed:
            new,gone,changed=diffs[table]
            if table=='bookings' and n==2:
                good=len(changed)==1 and not new and not gone
                if good:
                    old,row=changed[0];expected=dict(old,status='cancelled');good=old['ref']=='TR-000010101' and row==expected
                judge.check('exact_cancellation_delta',good,'only the earliest booking status may change')
            elif table=='wishlist_items' and n==3:
                # Logical keys allow legitimate delete-before-add SQLite rowid reuse.
                def pairs(db):return {(r['user_id'],r['tour_id']) for r in db.execute('SELECT * FROM wishlist_items')}
                a,b=pairs(before),pairs(after)
                old=before.execute("SELECT w.tour_id FROM wishlist_items w JOIN tours t ON t.id=w.tour_id WHERE user_id=2 AND t.name LIKE '%Bali%'").fetchone()
                judge.check('exact_wishlist_replacement',old is not None and a-b=={(2,old[0])} and b-a=={(2,271536)},'replace only Bob\'s Bali tour')
            else:
                judge.check('preserved_existing_'+table,not gone and not changed,'all existing records must be retained unchanged')
                judge.check('one_new_'+table,len(new)==1,'exactly one new record')
                if len(new)!=1:continue
                row=new[0]
                if table=='wishlist_items':
                    owner=1 if n==2 else after.execute("SELECT id FROM users WHERE email='autumn@example.com'").fetchone()[0]
                    judge.check('wishlist_owner_and_tour',row['user_id']==owner and row['tour_id']==(22237 if n==2 else 111527),'exact requested saved tour')
                if table=='reviews':
                    judge.check('review_body_saved','guide made every day special' in row['body'].casefold(),'review body must be persisted on the completed tour')
                if table=='tour_qa':
                    judge.check('exact_question_saved',row['question']=='Is airport pickup included on arrival day?' and row['asker']=='Curious Traveler' and row['tour_id']==252256,'exact question, signer and tour')
                if table=='bookings':
                    owner=after.execute('SELECT email,phone FROM users WHERE id=?',(row['user_id'],)).fetchone()
                    judge.check('guest_booking_owner',owner is not None and owner['email']==row['lead_email'] and owner['phone']==row['lead_phone'],'booking belongs to the guest contact record')
    finally:before.close();after.close()
