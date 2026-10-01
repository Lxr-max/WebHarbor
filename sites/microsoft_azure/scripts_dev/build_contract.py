#!/usr/bin/env python3
"""Generate verify/contract.json for the microsoft_azure mirror.

For every task this drives the same honest path as validate_tasks.py on a
fresh database, snapshots the seeded state (initial digest), collects the
rows the task adds (favorites, estimates, signups), and emits the
reviewer-side contract: required page paths, exact state deltas, and
regex claims over the expected answer values. Task prompts contain no
ground truth; everything here is reviewer-only.

Run: python3 scripts_dev/build_contract.py
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import sys
import tempfile
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SITE))
sys.path.insert(0, str(SITE / 'verify'))

import validate_tasks as VT  # noqa: E402


def database_snapshot(path):
    with sqlite3.connect(f'file:{path}?mode=ro', uri=True) as con:
        con.row_factory = sqlite3.Row
        data = {}
        for (table,) in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%' ORDER BY name"):
            keys = [r[1] for r in sorted(con.execute(f'PRAGMA table_info("{table}")'),
                                          key=lambda r: r[5]) if r[5]]
            data[table] = {json.dumps([r[k] for k in keys]): dict(r)
                           for r in con.execute(f'SELECT * FROM "{table}"')}
        return data


def digest(data):
    return hashlib.sha256(
        json.dumps(data, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def money_re(value):
    """Regex for a money answer like $420.48 or €121.44. The engine's
    norm() strips thousands separators from the answer, so the pattern
    must match the unseparated form."""
    v = value.strip()
    cur = v[0]
    num = v[1:].replace(',', '')
    return re.escape(cur) + re.escape(num)


def num_re(value):
    return r'\b' + re.escape(str(value).replace(',', '')) + r'\b'


def build_claims(idx, ans):
    """Regex checkpoints over the expected answers, reviewer-only."""
    claims = []
    def add(label, pattern):
        claims.append([label, pattern])
    if idx == 0:
        add('compute count', num_re(ans['compute_count']))
        add('first product', r'app service')
        add('first description', re.escape('managed PaaS solution').lower())
        add('section count', num_re(ans['section_count']))
        add('second product', r'container apps')
        add('second pricing link', r'no\b|without\b|does not')
        add('vm description', r'scalable, on-demand computing')
        add('kubernetes results', num_re(ans['kubernetes_results']))
        add('favorites count', num_re(ans['favorites']))
    elif idx == 1:
        add('database search count', num_re(ans['database_results']))
        add('databases category count', num_re(ans['databases_count']))
        add('cosmos description', r'serverless nosql vector database')
        add('cosmos pricing tables', num_re(ans['cosmos_tables']))
        add('azure sql description', r'secure, intelligent database')
        add('favorites count', num_re(ans['favorites']))
    elif idx == 2:
        add('usd total', money_re(ans['usd_total']))
        add('saved estimate name', r'production web tier')
        add('saved total matches', money_re(ans['saved_total']))
    elif idx == 3:
        add('control plane cost', money_re(ans['aks_control']))
        add('node pool cost', money_re(ans['aks_nodes']))
        add('aks total', money_re(ans['aks_total']))
        add('vm total', money_re(ans['vm_total']))
        add('difference explanation', r'difference|control[- ]plane|premium|covers')
        add('saved estimate name', r'aks baseline')
        add('saved total', money_re(ans['saved_total']))
    elif idx == 4:
        add('storage free count', num_re(ans['storage_free_count']))
        add('storage 12m count', num_re(ans['storage_12m_count']))
        add('capacity cost', money_re(ans['capacity_cost_1']))
        add('usd total', money_re(ans['total_1']))
        add('eur total', money_re(ans['total_1_eur']))
        add('west europe total', money_re(ans['total_1_we']))
        add('cheaper region', r'east us')
        add('doubled total', money_re(ans['total_2']))
        add('tier explanation', r'50,?000|51200|tier')
    elif idx == 5:
        add('single total', money_re(ans['single_total']))
        add('multi total', money_re(ans['multi_total']))
        add('gateway total', money_re(ans['gateway_total']))
    elif idx == 6:
        for region, rate in ans['rates'].items():
            add(f'rate {region.lower()}', num_re(rate))
        add('cheapest region', re.escape(ans['cheapest'].lower()))
        add('priciest region', re.escape(ans['priciest'].lower()))
        add('usd total', money_re(ans['usd_total']))
        add('eur total', money_re(ans['eur_total']))
        add('priciest total', money_re(ans['priciest_total']))
        add('hourly gap', num_re(f"{ans['hourly_gap']:.4f}".rstrip('0').rstrip('.')))
    elif idx == 7:
        add('sweden regions', num_re(ans['sweden_regions']))
        add('sweden cosmos availability', r'available')
        add('fewest aks region', re.escape(ans['fewest'].lower()))
        add('b2s total', money_re(ans['b2s_total']))
        add('b2s eur', money_re(ans['b2s_eur']))
        add('b2s west europe', money_re(ans['b2s_we']))
    elif idx == 8:
        add('12m databases count', num_re(ans['db_free_count']))
        add('cosmos free allowance', r'400 request units')
        add('throughput cost', money_re(ans['throughput_cost']))
        add('storage cost', money_re(ans['storage_cost']))
        add('single total', money_re(ans['single_total']))
        add('multi total', money_re(ans['multi_total']))
        add('gateway total', money_re(ans['gateway_total']))
        add('gateway eur', money_re(ans['gateway_eur']))
    elif idx == 9:
        add('story count', num_re(ans['story_count']))
        add('quoted person', re.escape(ans['person'].lower().split()[0]))
        add('company', re.escape('wellstar').lower())
        add('second customer', re.escape('beekeeper').lower())
        add('aks sections', num_re(ans['aks_sections']))
        add('node limit', r'up to 5,?000')
        add('favorites count', num_re(ans['favorites']))
    elif idx == 10:
        add('sql articles count', num_re(ans['sql_results']))
        add('named product', r'azure sql')
        add('first section', re.escape(ans['first_section'].lower()[:24]))
        add('azure sql description', r'secure, intelligent database')
        add('usd total', money_re(ans['usd_total']))
        add('west europe total', money_re(ans['west_europe_total']))
        add('west europe more', r'west europe')
    elif idx == 11:
        add('business plan', r'professional direct')
        add('response commitment', r'escalation management')
        add('thought leadership count', num_re(ans['tl_count']))
        add('patch window read time', re.escape(ans['read_time'].lower()))
        add('west us2 total', money_re(ans['west_us2_total']))
        add('west us2 eur', money_re(ans['west_us2_eur']))
        add('east us cheaper', r'east us')
    elif idx == 12:
        add('estimate total', money_re(ans['total']))
        add('saved estimate name', r'edge cache pair')
        add('estimate count', num_re(ans['estimates']))
        add('favorites count', num_re(ans['favorites']))
    elif idx == 13:
        add('pricing cards', num_re(ans['pricing_cards']))
        add('node limit', r'up to 5,?000')
        add('tiers', r'automatic')
        add('unbilled state', r'deleted \(deallocated\)')
        add('estimate total', money_re(ans['total']))
        add('saved estimate name', r'compute pilot')
        add('saved total', money_re(ans['saved_total']))
    elif idx == 14:
        for section, count in ans['section_results'].items():
            add(f'{section.lower()} results', num_re(count))
        add('first section', re.escape(ans['first_section'].lower()[:20]))
        add('aks story count', num_re(ans['aks_story_count']))
        add('quoted person', re.escape(ans['quoted_person'].lower().split()[0]))
        add('containers count', num_re(ans['containers_count']))
        add('container apps description', r'microservices|containers|serverless')
        add('favorites count', num_re(ans['favorites']))
    elif idx == 15:
        add('compute free count', num_re(ans['compute_free_count']))
        add('aks free allowance', r'free')
        add('control cost', money_re(ans['control_cost']))
        add('nodes cost', money_re(ans['nodes_cost']))
        add('usd total', money_re(ans['usd_total']))
        add('eur total', money_re(ans['eur_total']))
        add('vm total', money_re(ans['vm_total']))
        add('difference explanation', r'control[- ]plane|difference')
    elif idx == 16:
        add('announcements count', num_re(ans['announcements']))
        add('post date', re.escape(ans['post_date'].lower()))
        add('read time', re.escape(ans['read_time'].lower()))
        add('trial plan', r'developer')
        add('trial response', r'1 business day')
        add('single total', money_re(ans['single_total']))
        add('multi total', money_re(ans['multi_total']))
        add('gateway total', money_re(ans['gateway_total']))
    elif idx == 17:
        add('story count', num_re(ans['story_count']))
        add('customer', re.escape('zurich').lower())
        add('quoted role', re.escape(ans['quoted_role'].lower().split()[0]))
        add('aks description', r'secure, scalable containerized')
        add('tiers', r'automatic')
        add('unbilled state', r'deleted \(deallocated\)')
        add('favorites count', num_re(ans['favorites']))
        add('control tiers', r'uptime sla')
    elif idx == 18:
        add('article title', r'retrieval[- ]augmented generation')
        add('first section', re.escape(ans['first_section'].lower()[:20]))
        add('foundry description', r'ai app and agent factory')
        add('usd total', money_re(ans['usd_total']))
        add('eur total', money_re(ans['eur_total']))
        add('west europe more', r'west europe')
    elif idx == 19:
        add('aks total', money_re(ans['usd_total']))
        add('saved estimate name', r'k8s pilot')
        add('estimate count', num_re(ans['estimates']))
        add('favorites count', num_re(ans['favorites']))
    return claims


PATHS = {
    0: [r'/products/\?', r'/products/app-service/', r'/products/container-apps/',
        r'/products/virtual-machines/', r'\?q=Kubernetes', r'/account/'],
    1: [r'\?q=database', r'category=Databases', r'/products/cosmos-db/',
        r'/pricing/details/cosmos-db/', r'/products/azure-sql/', r'/account/'],
    2: [r'/pricing/calculator/', r'/account/login', r'/account/'],
    3: [r'service=kubernetes-service', r'service=virtual-machines', r'/account/'],
    4: [r'/pricing/free-services/', r'service=storage'],
    5: [r'service=cosmos-db'],
    6: [r'products-by-region', r'service=virtual-machines'],
    7: [r'/explore/global-infrastructure/geographies/sweden/',
        r'products-by-region', r'service=virtual-machines'],
    8: [r'/pricing/free-services/', r'service=cosmos-db'],
    9: [r'industry=Healthcare', r'/customer-stories/', r'/products/kubernetes-service/',
        r'/pricing/details/kubernetes-service/', r'/account/'],
    10: [r'q=SQL', r'/resources/cloud-computing-dictionary/what-is-sql-database/',
         r'category=Databases', r'/products/azure-sql/', r'service=virtual-machines'],
    11: [r'/support/', r'category=thought-leadership',
         r'the-patch-window-is-collapsing', r'service=virtual-machines'],
    12: [r'/account/signup', r'service=virtual-machines', r'\?q=Functions',
         r'/products/functions/', r'/account/'],
    13: [r'/pricing/$', r'/pricing/details/kubernetes-service/',
         r'/pricing/details/virtual-machines-linux/', r'/account/'],
    14: [r'/search/', r'what-is-kubernetes', r'product=Azure\+Kubernetes\+Service',
         r'category=Containers', r'/products/container-apps/', r'/account/'],
    15: [r'/pricing/free-services/', r'service=kubernetes-service',
         r'service=virtual-machines'],
    16: [r'category=announcements', r'gpt-6-astra', r'/support/',
         r'service=cosmos-db'],
    17: [r'industry=Financial\+Services', r'/customer-stories/',
         r'/products/kubernetes-service/', r'/pricing/details/kubernetes-service/',
         r'/pricing/details/virtual-machines-linux/', r'/account/',
         r'service=kubernetes-service'],
    18: [r'q=rag', r'resources/cloud-computing-dictionary/what-is-retrieval',
         r'\?q=Foundry', r'/products/ai-foundry/', r'service=virtual-machines'],
    19: [r'/account/signup', r'service=kubernetes-service', r'category=Containers',
         r'/products/container-apps/', r'/account/logout', r'/account/'],
}


def main():
    reports = json.loads((SITE / 'scraped_data' / 'expected_answers.json')
                         .read_text(encoding='utf-8'))
    tasks = [json.loads(line) for line in
             (SITE / 'tasks.jsonl').read_text(encoding='utf-8').splitlines()]

    # initial digest: fresh seeded database
    root = Path(tempfile.mkdtemp(prefix='microsoft-azure-contract-', dir='/tmp'))
    os.environ['AZURE_DB_URI'] = f'sqlite:///{root / "microsoft_azure.db"}'
    for mod in list(sys.modules):
        if mod.startswith(('app', 'seed', 'validate_tasks')):
            del sys.modules[mod]
    import app as A  # noqa: E402
    initial = database_snapshot(root / 'microsoft_azure.db')
    initial_digest = digest(initial)

    contract = {}
    for idx, report in enumerate(reports):
        ans = report['answers']
        spec = {
            'task': tasks[idx]['ques'],
            'initial_digest': initial_digest,
            'paths': PATHS[idx],
            'claims': build_claims(idx, ans),
        }
        # state deltas per task (reviewer-only; full-row specs: the shared
        # engine matches the exact key set of every added row)
        ANY_ID = {'regex': '[1-9][0-9]*'}
        ANY_TS = {'regex': '[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9:]+Z'}

        def fav_row(user_id, slug):
            return {'id': ANY_ID, 'user_id': user_id,
                    'product_slug': slug, 'created_ts': ANY_TS}

        def user_row(name, email):
            return {'id': ANY_ID, 'name': name, 'email': email,
                    'pw_hash': {'regex': r'\$2[aby]\$12\$[./A-Za-z0-9]{53}'},
                    'role': 'Member'}

        def est_row(user_id, name, total, service):
            return {'id': ANY_ID, 'user_id': user_id, 'name': name,
                    'service': service,
                    'config': {'regex': '.*'},
                    'monthly_usd': {'regex': r'[0-9.]+'},
                    'currency': 'usd', 'monthly_display': total,
                    'created_ts': ANY_TS}

        state = {}
        if idx in (0, 9, 17):
            state['favorites'] = {'added': [
                fav_row(4 if idx == 9 else 2, 'kubernetes-service')]}
        elif idx in (1, 14):
            slug = 'cosmos-db' if idx == 1 else 'kubernetes-service'
            state['favorites'] = {'added': [fav_row(3, slug)]}
        elif idx == 12:
            state['users'] = {'added': [user_row('Kai Rivera',
                                                 'kai.rivera@test.com')]}
            state['estimates'] = {'added': [
                est_row(ANY_ID, 'Edge cache pair', ans['total'],
                        'virtual-machines')]}
            state['favorites'] = {'added': [fav_row(ANY_ID, 'functions')]}
        elif idx == 19:
            state['users'] = {'added': [user_row('Mira Patel',
                                                 'mira.patel@test.com')]}
            state['estimates'] = {'added': [
                est_row(ANY_ID, 'K8s pilot', ans['usd_total'],
                        'kubernetes-service')]}
            state['favorites'] = {'added': [fav_row(ANY_ID,
                                                    'container-apps')]}
        elif idx in (2, 3, 13):
            name = {2: 'Production web tier', 3: 'AKS baseline',
                    13: 'Compute pilot'}[idx]
            service = {2: 'virtual-machines', 3: 'kubernetes-service',
                      13: 'virtual-machines'}[idx]
            state['estimates'] = {'added': [
                est_row(1 if idx in (2, 3) else 2, name,
                        ans.get('saved_total'), service)]}
        if state:
            spec['state'] = state
        contract[tasks[idx]['id']] = spec

    out = SITE / 'verify' / 'contract.json'
    out.write_text(json.dumps(contract, indent=1, ensure_ascii=False) + '\n',
                   encoding='utf-8')
    print(f'wrote verify/contract.json with {len(contract)} task contracts '
          f'(initial digest {initial_digest[:12]}…)')


if __name__ == '__main__':
    main()
