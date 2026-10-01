"""Offline review contract: browser evidence, scoped claims, and exact state deltas.

Language recognition is finite and deterministic; no LLM or live-state fallback.
Adapted from the disney/u_s_customs WebHarbor verifier convention.
"""
import argparse
import bcrypt
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import sys
from urllib.parse import urlsplit, unquote, parse_qs
from PIL import Image


def norm(text):
    text = str(text).replace('|', ' ').replace('**', '').casefold().replace('−', '-').replace('®', '').replace('™', '').replace('’', "'").replace('–', '-').replace('—', '-')
    text = text.replace('&', 'and').replace('‑','-').replace('–','-')
    text = re.sub(r'\s+-\s+', ' ', text)
    text = text.replace('noon', '12:00').replace('midnight', '00:00')
    text = re.sub(r'\b(\d{1,2})(?::(\d{2}))?\s*([ap])(?:\.?m\.?)?\b', lambda m:f'{int(m[1])%12+(12 if m[3]=="p" else 0):02d}:{int(m[2] or 0):02d}',text)
    text = re.sub(r'\b(?:mins?|minutes)\b','minutes',text)
    text = re.sub(r'\boz\b','ounces',text)
    text = re.sub(r'\bgb\b','gigabytes',text)
    text = re.sub(r'\bmb\b','megabytes',text)
    text = re.sub(r'\b(?:ram|memory)\b','memory',text)
    text = re.sub(r'(?<!\d)(\d+)\s*(?:h|hours?)\s*(\d+)\s*(?:min|minutes?)\b', lambda m:str(int(m[1])*60+int(m[2]))+' minutes', text)
    text = re.sub(r'(?<!\d):|:(?!\d)', ' ', text)
    text = re.sub(r'(?<=\d),(?=\d)', '', text)
    text = re.sub(r'\b(zero|one|two|three|four|five|six|seven|eight|nine|ten)\b(?!-tone)', lambda m:str(['zero','one','two','three','four','five','six','seven','eight','nine','ten'].index(m[0])),text)
    for old,new in [(r'\bwi fi\b','wi-fi'),(r'\bpounds?\b','lb'),(r'\bhrs?\b','hours'),(r'\bfree of charge\b','free'),(r'\bcomplimentary\b','free'),(r'\bamount charged\b','total charged')]:
        text=re.sub(old,new,text)
    # finance-domain: "$350" -> "350", "84.92%" -> "84.92 percent";
    # a trailing "usd" is only folded away when it follows a number
    # ("350 usd" -> "350") so ticker spellings like BTC-USD survive
    text = re.sub(r'\$\s*', '', text)
    text = text.replace('us dollars', '').replace('dollars', '')
    text = re.sub(r'(\d)\s*%', r'\1 percent', text)
    text = re.sub(r'(?<=\d)\s*usd\b', '', text)
    return re.sub(r'\s+', ' ', text).strip()


def database(path):
    if not path.is_file():raise ValueError('Missing saved database: '+path.name)
    with sqlite3.connect('file:'+str(path)+'?mode=ro',uri=True) as con:
        con.row_factory=sqlite3.Row
        if con.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('Corrupt database')
        data={}
        for (table,) in con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"):
            keys=[r[1] for r in sorted(con.execute(f'PRAGMA table_info("{table}")'),key=lambda r:r[5]) if r[5]]
            data[table]={json.dumps([r[k] for k in keys],default=str):{k:(v.decode() if isinstance(v,bytes) else v) for k,v in dict(r).items()} for r in con.execute(f'SELECT * FROM "{table}"')}
        return data


def digest(data):return hashlib.sha256(json.dumps(data,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def canonical_json(value):
    if isinstance(value, dict):return {k:canonical_json(v) for k,v in value.items()}
    if isinstance(value, list):return sorted([canonical_json(v) for v in value], key=lambda v:json.dumps(v,sort_keys=True))
    return value


def matches(value,expected):
    if isinstance(value,bytes):value=value.decode("utf-8",errors="strict")
    if isinstance(expected,dict):
        if 'bcrypt_password' in expected:
            try:
                return bcrypt.checkpw(expected['bcrypt_password'].encode(), str(value).encode())
            except (ValueError, TypeError):
                return False
        if expected.get('iso_date'):
            from datetime import date
            try:
                return date.fromisoformat(str(value)).isoformat() == value
            except (ValueError, TypeError):
                return False
        if 'json_rows' in expected:
            rows=json.loads(value); wants=list(expected['json_rows'])
            if not isinstance(rows,list) or len(rows)!=len(wants):return False
            for row in rows:
                hits=[w for w in wants if row.keys()==w.keys() and all(matches(row[k],v) for k,v in w.items())]
                if not hits:return False
                wants.remove(hits[0])
            return True
        if 'query' in expected:
            u=urlsplit(value);got={k:sorted(v for v in vs if v) for k,vs in parse_qs(u.query).items()};got={k:v for k,v in got.items() if v}
            return u.path==expected['path'] and got==expected['query']
        if 'regex' in expected:return re.fullmatch(expected['regex'],str(value),re.I) is not None
        if 'one_of' in expected:return value in expected['one_of']
        if 'json_set' in expected:return sorted(json.loads(value))==sorted(expected['json_set'])
        if 'json_value' in expected:return canonical_json(json.loads(value))==canonical_json(expected['json_value'])
    return value==expected


def check_state(initial,after,spec):
    if digest(initial)!=spec['initial_digest']:raise ValueError('Initial state does not match reviewed seed')
    if initial.keys()!=after.keys():raise ValueError('Database tables changed')
    for table,old in initial.items():
        new=after[table];rule=spec.get('state',{}).get(table,{})
        removed=set(rule.get('removed',[]))
        if old.keys()-new.keys()!=removed:raise ValueError('Wrong existing rows removed from '+table)
        added=[r for k,r in new.items() if k not in old]
        expected=rule.get('added',[])
        if len(added)!=len(expected):raise ValueError('Wrong number of new rows in '+table)
        for want in expected:
            hits=[r for r in added if r.keys()==want.keys() and all(matches(r[k],v) for k,v in want.items())]
            if not hits:raise ValueError('Incorrect new '+table+' row')
            added.remove(hits[0])
        for key,before in old.items():
            if key in removed:continue
            changes=rule.get('updated',{}).get(key,{})
            for col,value in before.items():
                if not matches(new[key][col],changes.get(col,value)):raise ValueError('Incorrect '+table+'.'+col)


def check_claims(answer,claims):
    text=norm(answer)
    if re.search(r'\b(?:not true|incorrect answer|ignore these facts|the following is false|these claims are false)\b',text):raise ValueError('Answer rejects its own claims')
    for label,pattern in claims:
        pattern=pattern.replace('pounds','lb').replace('pound','lb').replace('hrs/day','hours/day')
        hits=list(re.finditer(pattern,text,re.I))
        if not hits:raise ValueError('Missing or incorrect '+label)
        # Reject explicit negation of a positive matched assertion. Negative
        # policy patterns include their own polarity and do not start after "not".
        for m in hits:
            claim=m.group()
            # Missing-data statements elsewhere in an entity block do not negate
            # its later positive facts. Preserve all other explicit negations.
            claim=re.sub(r'\bnot yet rated\b', 'unrated', claim)
            claim=re.sub(r'\bnot (?:provided|available|shown|listed|captured|submitted|confirmed)\b(?!\s*$)', 'unavailable', claim)
            if re.search(r'\b(?:reference(?: number| id)?|unrelated number|example amount)\b',claim[-150:]) and not re.search(r'reference|unrelated|example',pattern):raise ValueError('Unrelated value used for '+label)
            if re.search(r'\b(?:not|never|incorrect|false)\s*$',text[max(0,m.start()-18):m.start()]):
                raise ValueError('Negated '+label)
            # An inserted negation must not turn an expected positive claim into a pass.
            if re.search(r"\b(?:not|never|isn't|aren't|doesn't|don't|cannot)\b",claim[-150:]) and not re.search(r'not|never|ineligible|unavailable|prohibit',pattern):
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
                # Tolerate the initial blank page some harnesses record
                # before the first navigation: about:blank carries no
                # origin and no content, so it is skipped by the origin
                # gate (r1 review LOW finding; foreign origins still fail).
                if step[key]=='about:blank':
                    continue
                if (u.scheme,u.hostname,u.port)!=origin:raise ValueError('Browser evidence changes origin')
        u=urlsplit(step.get('url_after',step.get('url','')));urls.append(unquote(u.path+('?' + u.query if u.query else '')))
        name=step.get('screenshot_after',step.get('screenshot'))
        if not name or Path(name).name!=name:raise ValueError('Invalid screenshot reference')
        path=run/'screenshots'/name
        if path not in seen:
            with Image.open(path) as im:
                im.load()
                if im.format!='PNG' or im.width<320 or im.height<200:raise ValueError('Screenshot is not a full browser PNG')
                if len(im.convert('RGB').resize((32,32)).getcolors(1024) or [])<8:raise ValueError('Blank browser screenshot')
            seen.add(path)
    for pattern in spec['paths']:
        if not any(re.search(pattern,u,re.I) for u in urls):raise ValueError('Required page evidence missing: '+pattern)
    initial=database(run/'initial.db');after=database(run/'after.db');check_state(initial,after,spec)
    for check in spec.get('state_checks',[]):
        check_relations(initial,after,check)
    answer=traj.get('final_answer','');check_claims(answer,spec['claims'])
    if spec.get('alternatives'):
        valid = False
        for option in spec['alternatives']:
            if not all(any(re.search(pattern,u,re.I) for u in urls) for pattern in option['paths']):continue
            try:check_claims(answer,option['claims']);valid=True;break
            except ValueError:pass
        if not valid:raise ValueError('No valid tied product with matching detail evidence and facts')
    for pattern in spec.get('forbidden',[]):
        if re.search(pattern,norm(answer),re.I):raise ValueError('Contradictory answer: '+pattern)
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
        if len(rows)!=1:raise ValueError('Expected one saved '+table+' row')
        value=str(rows[0][col]); candidates=[value]
        if not any(norm(v) in norm(answer) for v in candidates):raise ValueError('Answer does not match saved '+col)
    return {'task_id':task_id,'pass':True,'reason':'Browser evidence, scoped factual claims and exact saved-state contract passed','evidence':[f'{len(seen)} decoded screenshots',f'{len(spec["claims"])} checked claims','Saved initial and final databases compared']}


def check_relations(initial, after, check):
    left=[r for k,r in after[check['left']].items() if k not in initial[check['left']]]
    right=[r for k,r in after[check['right']].items() if k not in initial[check['right']]]
    if len(left)!=1 or not right or any(r[check['foreign_key']] != left[0][check.get('key','id')] for r in right):
        raise ValueError('New related records are not linked correctly')


def main(task_id):
    parser=argparse.ArgumentParser();parser.add_argument('--run_dir',required=True);args=parser.parse_args()
    try:result=verify(args.run_dir,task_id)
    except Exception as exc:result={'task_id':task_id,'pass':False,'reason':str(exc),'evidence':[]}
    print(json.dumps(result));return 0 if result['pass'] else 1


if __name__ == "__main__":
    raise SystemExit(main('REPLACE_WITH_TASK_ID'))
