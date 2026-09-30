"""Offline review contract: browser evidence, scoped claims, and exact state deltas.

Language recognition is finite and deterministic; no LLM or live-state fallback.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import sys
from urllib.parse import urlsplit, unquote
from PIL import Image


def norm(text):
    text = str(text).casefold().replace('®', '').replace('™', '').replace('’', "'").replace('–', '-').replace('—', '-')
    text = re.sub(r'(?<=\d),(?=\d)', '', text)
    text = re.sub(r'\b(zero|one|two|three|four|five|six|seven|eight|nine|ten)\b', lambda m:str(['zero','one','two','three','four','five','six','seven','eight','nine','ten'].index(m[0])),text)
    for old,new in [(r'\bwi fi\b','wi-fi'),(r'\bpounds?\b','lb'),(r'\bhrs?\b','hours'),(r'\bfree of charge\b','free'),(r'\bcomplimentary\b','free'),(r'\bamount charged\b','total charged')]:
        text=re.sub(old,new,text)
    return re.sub(r'\s+', ' ', text).strip()


def database(path):
    if not path.is_file():raise ValueError('Missing saved database: '+path.name)
    with sqlite3.connect('file:'+str(path)+'?mode=ro',uri=True) as con:
        con.row_factory=sqlite3.Row
        if con.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('Corrupt database')
        data={}
        for (table,) in con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"):
            keys=[r[1] for r in sorted(con.execute(f'PRAGMA table_info("{table}")'),key=lambda r:r[5]) if r[5]]
            data[table]={json.dumps([r[k] for k in keys]):dict(r) for r in con.execute(f'SELECT * FROM "{table}"')}
        return data


def digest(data):return hashlib.sha256(json.dumps(data,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def matches(value,expected):
    if isinstance(expected,dict):
        if 'regex' in expected:return re.fullmatch(expected['regex'],str(value),re.I) is not None
        if 'one_of' in expected:return value in expected['one_of']
    return value==expected


def check_state(initial,after,spec):
    if digest(initial)!=spec['initial_digest']:raise ValueError('Initial state does not match reviewed seed')
    if initial.keys()!=after.keys():raise ValueError('Database tables changed')
    for table,old in initial.items():
        new=after[table];rule=spec.get('state',{}).get(table,{})
        if old.keys()-new.keys():raise ValueError('Existing rows removed from '+table)
        added=[r for k,r in new.items() if k not in old]
        expected=rule.get('added',[])
        if len(added)!=len(expected):raise ValueError('Wrong number of new rows in '+table)
        for want in expected:
            hits=[r for r in added if r.keys()==want.keys() and all(matches(r[k],v) for k,v in want.items())]
            if not hits:raise ValueError('Incorrect new '+table+' row')
            added.remove(hits[0])
        for key,before in old.items():
            changes=rule.get('updated',{}).get(key,{})
            for col,value in before.items():
                if not matches(new[key][col],changes.get(col,value)):raise ValueError('Incorrect '+table+'.'+col)
    if 'password' in spec:
        from werkzeug.security import check_password_hash
        users=[r for k,r in after['users'].items() if k not in initial['users']]
        if len(users)!=1:raise ValueError('Expected one new account')
        encoded=users[0]['password_hash']
        if encoded.startswith('$2'):
            import bcrypt
            ok=bcrypt.checkpw(spec['password'].encode(),encoded.encode())
        else:ok=check_password_hash(encoded,spec['password'])
        if not ok:raise ValueError('Wrong account password')


def check_claims(answer,claims):
    text=norm(answer)
    if re.search(r'\b(?:not true|false statement|incorrect answer|ignore these facts)\b',text):raise ValueError('Answer rejects its own claims')
    for label,pattern in claims:
        pattern=pattern.replace('pounds','lb').replace('pound','lb').replace('hrs/day','hours/day')
        hits=list(re.finditer(pattern,text,re.I))
        if not hits:raise ValueError('Missing or incorrect '+label)
        # Reject explicit negation of a positive matched assertion. Negative
        # policy patterns include their own polarity and do not start after "not".
        for m in hits:
            claim=m.group()
            if re.search(r'\b(?:not|never|incorrect|false)\s*$',text[max(0,m.start()-18):m.start()]):
                raise ValueError('Negated '+label)
            # An inserted negation must not turn an expected positive claim into a pass.
            if re.search(r'\b(?:not|never)\s+(?:\$?\d|free|panasonic|approved)',claim) and not re.search(r'not|never',pattern):
                raise ValueError('Contradicted '+label)


def verify(run_dir,task_id):
    run=Path(run_dir).resolve();traj=json.loads((run/'trajectory.json').read_text());spec=json.loads(Path(__file__).with_name('contract.json').read_text())[task_id]
    if traj.get('task_id')!=task_id or traj.get('task',traj.get('ques'))!=spec['task']:raise ValueError('Wrong task identity or wording')
    if not traj.get('terminated') or traj.get('termination_reason')!='agent_done':raise ValueError('Unfinished attempt')
    start=urlsplit(traj.get('start_url',''))
    if start.scheme not in ['http','https'] or start.hostname not in ['localhost','127.0.0.1','::1']:raise ValueError('Invalid local start URL')
    origin=(start.scheme,start.hostname,start.port);urls=[];seen=set();steps=traj.get('steps',[])
    if not steps:raise ValueError('Missing browser evidence')
    for step in steps:
        for key in ['url','url_before','url_after']:
            if key in step:
                u=urlsplit(step[key])
                if (u.scheme,u.hostname,u.port)!=origin:raise ValueError('Browser evidence changes origin')
        u=urlsplit(step.get('url_after',step.get('url','')));urls.append(unquote(u.path))
        name=step.get('screenshot_after',step.get('screenshot'))
        if not name or Path(name).name!=name:raise ValueError('Invalid screenshot reference')
        path=run/'screenshots'/name
        if path not in seen:
            with Image.open(path) as im:
                im.load()
                if im.format!='PNG':raise ValueError('Screenshot is not a PNG')
            seen.add(path)
    for pattern in spec['paths']:
        if not any(re.search(pattern,u,re.I) for u in urls):raise ValueError('Required page evidence missing: '+pattern)
    initial=database(run/'initial.db');after=database(run/'after.db');check_state(initial,after,spec)
    answer=traj.get('final_answer','');check_claims(answer,spec['claims'])
    scoped=spec.get('scoped_claims',[])
    if scoped:
        answer_norm=norm(answer)
        entities='|'.join(re.escape(c['entity']) for c in scoped)
        sections=list(re.finditer(entities,answer_norm))
        for group in scoped:
            chunks=[answer_norm[m.end():sections[i+1].start() if i+1<len(sections) else len(answer_norm)] for i,m in enumerate(sections) if m.group()==group['entity']]
            check_claims(' '.join(chunks),[(group['entity']+' specification '+str(i),p) for i,p in enumerate(group['patterns'])])
    for table,col in spec.get('answer_state',[]):
        rows=[r for k,r in after[table].items() if k not in initial[table]]
        if len(rows)!=1 or str(rows[0][col]).casefold() not in answer.casefold():raise ValueError('Answer does not match saved '+col)
    if spec.get('seat_answer'):
        seat=after['passengers']['[1]']['seat']
        if not re.search(r'\b'+re.escape(seat)+r'\b',answer,re.I):raise ValueError('Reported seat differs from saved seat')
    return {'task_id':task_id,'pass':True,'reason':'Browser evidence, scoped factual claims and exact saved-state contract passed','evidence':[f'{len(seen)} decoded screenshots',f'{len(spec["claims"])} checked claims','Saved initial and final databases compared']}


def main(task_id):
    parser=argparse.ArgumentParser();parser.add_argument('--run_dir',required=True);args=parser.parse_args()
    try:result=verify(args.run_dir,task_id)
    except Exception as exc:result={'task_id':task_id,'pass':False,'reason':str(exc),'evidence':[]}
    print(json.dumps(result));return 0 if result['pass'] else 1
