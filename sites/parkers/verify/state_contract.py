"""Task-scoped mutation checks; existing rows and unrelated tables are immutable."""
import sqlite3

def rows(path):
    with sqlite3.connect(f'file:{path}?mode=ro', uri=True) as con:
        con.row_factory = sqlite3.Row
        return {t: [dict(r) for r in con.execute(f'SELECT * FROM "{t}" ORDER BY id')]
                for (t,) in con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}

def check(judge, task_id, initial, after):
    before, final = rows(initial), rows(after)
    task = int(task_id.split('--')[-1])
    allowed = {8: 'shortlist_items', 9: 'shortlist_items', 11: 'owner_reviews'}.get(task)
    judge.check('all_unrelated_tables_preserved', set(before) == set(final) and all(
        before[t] == final[t] for t in before if t != allowed), 'Only the task-specific table may change')
    if allowed:
        old = {r['id']: r for r in before[allowed]}
        new = {r['id']: r for r in final[allowed]}
        deleted = set(old) - set(new)
        permitted_deleted = set()
        if task == 9:
            uid = next(r['id'] for r in before['users'] if r['email'] == 'bob.c@test.com')
            permitted_deleted = {k for k, r in old.items() if r['user_id'] == uid and r['listing_id'] == 954}
        judge.check('existing_rows_preserved', deleted == permitted_deleted and all(
            new[k] == r for k, r in old.items() if k not in permitted_deleted), 'Preserve previous rows and other users')
        added = [r for k, r in new.items() if k not in old]
        judge.check('exactly_one_added_row', len(added) == 1, f'added={len(added)}')
        if added and task in (8, 9):
            email = 'alice.j@test.com' if task == 8 else 'bob.c@test.com'
            uid = next(r['id'] for r in before['users'] if r['email'] == email)
            judge.check('added_row_owner_and_listing', added[0]['user_id'] == uid and
                        added[0]['listing_id'] == (740 if task == 8 else 959), 'Requested account and car only')
        if added and task == 11:
            body = added[0]['body_json'].lower()
            judge.check('review_covers_user_experience', 'infotainment' in body and
                        'frustrat' in body and 'comfort' in body and 'driv' in body,
                        'Review includes infotainment frustration and driving comfort')
