"""Exact requested state changes; free-text fields use task-specific semantics."""
import json, re, sqlite3
from pathlib import Path
CONTRACTS = json.loads(Path(__file__).with_suffix('.json').read_text())
# Terms belong to the requested goal, not one exact message wording.
DETAILS = {1:['deep','move.out'],2:['four|4','wedding|reception'],4:['mirror'],5:['week','mow'],6:['faucet|tap','leak|drip'],7:['wardrobe','bookcase'],9:['deep','3|three','bed'],10:['studio'],11:['quince|daughter'],14:['ant','kitchen|indoor'],15:['standard','3|three'],16:['twice|two|2','strength'],17:['75','fireplace','cable|wire','sound'],19:['refrigerator','GE']}

def check(judge, task_id, initial, after):
    n = int(task_id.split('--')[-1])
    expected = CONTRACTS[str(n)]
    with sqlite3.connect(f'file:{initial}?mode=ro',uri=True) as a, sqlite3.connect(f'file:{after}?mode=ro',uri=True) as b:
        a.row_factory = b.row_factory = sqlite3.Row
        query = "SELECT type,name,tbl_name,sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' ORDER BY type,name"
        if [tuple(x) for x in a.execute(query)] != [tuple(x) for x in b.execute(query)]:
            judge.fail('After-state schema changed')
        for table in ['projects','project_matches','reviews','saved_pros','threads','messages','users']:
            old = {r['id']:dict(r) for r in a.execute('SELECT * FROM '+table)}
            new = {r['id']:dict(r) for r in b.execute('SELECT * FROM '+table)}
            allowed = expected.get(table,{})
            actual = {str(k) for k in old.keys() | new.keys() if old.get(k)!=new.get(k)}
            # SQLite can reuse deleted max IDs in a saved list; compare semantic membership there.
            if table=='saved_pros':
                def pairs(rows):return {(r['user_id'],r['pro_id']) for r in rows}
                wanted = dict(old)
                for key,change in allowed.items():
                    wanted.pop(int(key),None)
                    if change['after']:wanted[int(key)]=change['after']
                if pairs(new.values()) != pairs(wanted.values()):judge.fail('Unexpected saved-pro membership')
                continue
            if actual != set(allowed):
                judge.fail(f'{table}: unexpected changed records {actual} versus {set(allowed)}')
                continue
            for key,change in allowed.items():
                got = new.get(int(key));want=change['after']
                if want is None:
                    if got is not None:judge.fail(f'{table}: expected removal')
                    continue
                if got is None:judge.fail(f'{table}: missing requested record');continue
                for field,value in want.items():
                    if field in ['created_at','updated_at','password_hash']:continue
                    if table=='project_matches' and field=='response_note':
                        import hashlib
                        pro = a.execute('SELECT service_pk,name FROM pros WHERE id=?', (got['pro_id'],)).fetchone()
                        content = json.loads(a.execute('SELECT payload FROM content_records WHERE id=1').fetchone()[0])
                        notes = content['quote_notes']
                        digest = hashlib.md5(f"note|{pro[0]}|{got['project_id']}".encode()).hexdigest()
                        expected_note = notes[int(digest[:12],16)%len(notes)].format(pro=pro[1]) if got['responded'] else None
                        if got[field]!=expected_note:judge.fail('Unexpected quote response note')
                        continue
                    if table=='users' and change['before'] is None and field=='zip':continue
                    if table=='projects' and field=='answers':
                        # All contributor-required answers must be preserved; additional questionnaire answers are allowed.
                        needed=json.loads(value);observed=json.loads(got[field])
                        if any(pair not in observed for pair in needed):judge.fail('Project questionnaire does not match requested work')
                        continue
                    if table=='projects' and field=='details' and change['before'] is None:
                        if any(not re.search(term,got[field] or '',re.I) for term in DETAILS.get(n,[])):judge.fail('Project description omits requested work')
                        continue
                    if table=='messages' and field=='body' and want['sender']=='user':
                        terms = ['supplies|equipment'] if 'supplies' in value else ['sunday|weekend'] if 'Sunday' in value else ['trial'] if 'trial' in value else ['move.out'] if 'move-out' in value else ['october|oct\.?|10/'] if 'October' in value else ['twice|two|2'] if 'twice' in value else ['leak|faucet|urgent'] if 'leak' in value else []
                        if any(not re.search(term,got[field] or '',re.I) for term in terms):judge.fail('Message does not ask the requested question')
                        continue
                    if table=='reviews' and field=='body':
                        term={1:'move.out',7:'assembl',12:'spotless',14:'ant',17:'cable|wire',19:'refrigerator'}.get(n)
                        if term and not re.search(term,got[field] or '',re.I):judge.fail('Review omits requested feedback')
                        continue
                    if got[field]!=value:judge.fail(f'{table}.{field}: unrequested or incorrect value')
