"""Offline task grading: evidence identity, scoped facts and exact database deltas.

Answer recognition is finite and deterministic. Equivalent phrasing is supported
by per-claim alternatives; this is not a general semantic language judge.
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
    text = str(text).casefold().replace('™', '').replace('®', '')
    for a,b in [('’',"'"),('“','"'),('”','"'),('–','-'),('—','-'),('×','x')]:
        text=text.replace(a,b)
    text=re.sub(r'(?<=\d),(?=\d)','',text)
    return re.sub(r'\s+',' ',text).strip()

def database(path):
    if not path.is_file():
        raise ValueError('Missing saved database: '+path.name)
    with sqlite3.connect('file:'+str(path)+'?mode=ro',uri=True) as con:
        con.row_factory=sqlite3.Row
        if con.execute('PRAGMA integrity_check').fetchone()[0]!='ok':
            raise ValueError('Corrupt database')
        result={}
        for (table,) in con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"):
            cols=list(con.execute(f'PRAGMA table_info("{table}")'))
            keys=[r[1] for r in sorted(cols,key=lambda r:r[5]) if r[5]] or [r[1] for r in cols]
            result[table]={json.dumps([r[k] for k in keys],default=str):dict(r) for r in con.execute(f'SELECT * FROM "{table}"')}
        return result

def digest(data):
    return hashlib.sha256(json.dumps(data,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()

def matches(value,want):
    if isinstance(want,dict):
        if 'regex' in want:return re.fullmatch(want['regex'],str(value),re.I) is not None
        if 'one_of' in want:return value in want['one_of']
        if 'json' in want:
            try:return json.loads(value)==want['json']
            except (ValueError,TypeError):return False
    return value==want

def check_state(initial,after,spec):
    if digest(initial)!=spec['initial_digest']:raise ValueError('Initial state differs from reviewed seed')
    if initial.keys()!=after.keys():raise ValueError('Database table set changed')
    for table,old in initial.items():
        new=after[table];rule=spec.get('state',{}).get(table,{})
        removed=set(rule.get('removed',[]))
        if old.keys()-new.keys()!=removed:raise ValueError('Wrong existing rows removed: '+table)
        added=[r for k,r in new.items() if k not in old];expected=rule.get('added',[])
        if len(added)!=len(expected):raise ValueError('Wrong number of added rows: '+table)
        for want in expected:
            hits=[r for r in added if r.keys()==want.keys() and all(matches(r[k],v) for k,v in want.items())]
            if not hits:raise ValueError('Incorrect added row: '+table)
            added.remove(hits[0])
        for key,before in old.items():
            if key in removed:continue
            changes=rule.get('updated',{}).get(key,{})
            if before.keys()!=new[key].keys():raise ValueError('Columns changed: '+table)
            for col,value in before.items():
                if not matches(new[key][col],changes.get(col,value)):raise ValueError('Unrequested change: '+table+'.'+col)

def check_claims(answer,spec):
    text=norm(answer)
    if re.search(r'\b(?:these (?:claims|facts) are false|ignore these facts|incorrect answer|not true)\b',text):
        raise ValueError('Answer disclaims its facts')
    for claim in spec.get('claims',[]):
        scope=text
        if claim.get('scope'):
            m=re.search(claim['scope'],text,re.I)
            if not m:raise ValueError('Missing entity context for '+claim['label'])
            scope=m.group(0)
        hits=list(re.finditer(claim['pattern'],scope,re.I))
        if not hits:raise ValueError('Missing or incorrect '+claim['label'])
        for hit in hits:
            prefix=scope[max(0,hit.start()-24):hit.start()]
            if re.search(r'\b(?:not|never|incorrect|false)\s*$',prefix):raise ValueError('Negated '+claim['label'])
        # A scoped rejection pattern catches wrong values even when the correct
        # value is also pasted elsewhere in the answer.
        for bad in claim.get('forbidden',[]):
            if re.search(bad,scope,re.I):raise ValueError('Contradictory '+claim['label'])
    for pattern in spec.get('forbidden',[]):
        if re.search(pattern,text,re.I):raise ValueError('Contradictory answer')

def verify(run_dir,task_id):
    run=Path(run_dir).resolve();traj=json.loads((run/'trajectory.json').read_text())
    spec=json.loads(Path(__file__).with_name('contract.json').read_text())[task_id]
    if traj.get('task_id')!=task_id or traj.get('task',traj.get('ques'))!=spec['task']:raise ValueError('Wrong task identity or wording')
    if not traj.get('terminated') or traj.get('termination_reason')!='agent_done':raise ValueError('Unfinished attempt')
    start=urlsplit(traj.get('start_url',''))
    if start.scheme not in ('http','https') or start.hostname not in ('localhost','127.0.0.1','::1'):raise ValueError('Invalid local start URL')
    origin=(start.scheme,start.hostname,start.port);urls=[];seen=set()
    for step in traj.get('steps',[]):
        for key in ('url','url_before','url_after'):
            if key not in step or step[key] in ('about:blank',''):continue
            u=urlsplit(step[key])
            if (u.scheme,u.hostname,u.port)!=origin:raise ValueError('Browser evidence changes origin')
        u=urlsplit(step.get('url_after',step.get('url','')));urls.append(unquote(u.path+('?' + u.query if u.query else '')))
        name=step.get('screenshot_after',step.get('screenshot'))
        if not name or Path(name).name!=name:raise ValueError('Invalid screenshot reference')
        path=run/'screenshots'/name
        if path not in seen:
            with Image.open(path) as im:
                im.load()
                if im.format!='PNG' or im.width<320 or im.height<200:raise ValueError('Invalid browser screenshot')
                if len(im.convert('RGB').resize((32,32)).getcolors(1024) or [])<8:raise ValueError('Blank browser screenshot')
            seen.add(path)
    if not seen:raise ValueError('Missing browser evidence')
    for pattern in spec['paths']:
        if not any(re.search(pattern,u,re.I) for u in urls):raise ValueError('Required page evidence missing: '+pattern)
    answer=traj.get('final_answer','')
    if not answer.strip():raise ValueError('Missing final answer')
    check_claims(answer,spec)
    initial=database(run/'initial.db');after=database(run/'after.db');check_state(initial,after,spec)
    for table,col in spec.get('answer_state',[]):
        rows=[r for k,r in after[table].items() if k not in initial[table]]
        if len(rows)!=1 or norm(rows[0][col]) not in norm(answer):raise ValueError('Answer differs from saved '+col)
    return {'task_id':task_id,'pass':True,'reason':'Required browser evidence, factual claims and exact saved-state delta passed','evidence':[f'{len(seen)} decoded screenshots',f'{len(spec.get("claims",[]))} factual checks','Initial seed and all final database rows checked']}

def main(task_id):
    p=argparse.ArgumentParser();p.add_argument('--run_dir',required=True);args=p.parse_args()
    try:result=verify(args.run_dir,task_id)
    except Exception as exc:result={'task_id':task_id,'pass':False,'reason':str(exc),'evidence':[]}
    print(json.dumps(result));return 0 if result['pass'] else 1
