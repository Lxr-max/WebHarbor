#!/usr/bin/env python3
"""End-to-end walkthrough: drive every task's honest path on a fresh
database, emit a synthetic browser run (trajectory + screenshots + initial
and after database snapshots), grade it with the site's own verify_N.py
contract, and assert the verifier passes. Runs two independent rounds.

This proves the task set is solvable end to end and that the reviewer
contract matches the honest-path evidence exactly.

Run: python3 scripts_dev/walk_tasks.py
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SITE))
sys.path.insert(0, str(SITE / 'verify'))

import validate_tasks as VT  # noqa: E402


ANSWER_TEMPLATES = {
    0: ("{compute_count} products are in the Compute category. The first product, "
        "{first_product}, is described as: {first_desc} Its page has {section_count} "
        "section headings. The second product, {second_product}, has "
        "{second_pricing_answer} pricing details link. Azure Virtual Machines: "
        "{vm_desc} The Kubernetes search returns {kubernetes_results} product. "
        "The account page shows {favorites} favorite."),
    1: ("The database search matches {database_results} products and the Databases "
        "category lists {databases_count}. Azure Cosmos DB: {cosmos_desc} Its pricing "
        "details page shows {cosmos_tables} tables. Azure SQL: {azure_sql_desc} "
        "The account page shows {favorites} favorite."),
    2: ("Three always-on Linux D4s v5 VMs in West US 2 cost {usd_total} per month. "
        "The saved estimate 'Production web tier' lists {saved_total} on the account page."),
    3: ("The AKS cluster costs {aks_control} for the control plane and {aks_nodes} for "
        "the node pool, {aks_total} monthly. Three plain VMs cost {vm_total}; the "
        "{difference_amount} difference covers the managed Kubernetes control plane. "
        "The saved estimate 'AKS baseline' lists {saved_total}."),
    4: ("There are {storage_free_count} always-free storage services and "
        "{storage_12m_count} free for 12 months. 60,000 GB in East US costs "
        "{capacity_cost_1} for capacity, {total_1} monthly ({total_1_eur} in EUR). "
        "West Europe is {we_answer} ({total_1_we}). At 120,000 GB the total is "
        "{total_2}: the first 50,000 GB billed at tier 1, the next 50,000 at tier 2, "
        "and the remaining 20,000 at tier 3."),
    5: ("400 RU/s single-region with 100 GB costs {single_total} monthly. Multi-region "
        "writes raise it to {multi_total}. Adding the D4s dedicated gateway brings the "
        "single-region total to {gateway_total}."),
    6: ("Per-hour rates: {rates_sentence} The cheapest region is {cheapest} "
        "({cheapest_rate}); the most expensive is {priciest}. Two always-on VMs in "
        "{cheapest} cost {usd_total} monthly ({eur_total} in EUR) and in {priciest} "
        "{priciest_total}; the per-hour gap is {hourly_gap}."),
    7: ("The Sweden geography contains {sweden_regions} regions and Cosmos DB is "
        "{sweden_central_cosmos_answer} in Sweden Central. {fewest} offers the fewest "
        "priced AKS node sizes. One always-on Linux B2s in Sweden Central costs "
        "{b2s_total} monthly ({b2s_eur} in EUR) and {b2s_we} in West Europe."),
    8: ("Four database services are free for 12 months; Azure Cosmos DB's allowance is "
        "{cosmos_free} Throughput costs {throughput_cost} and storage {storage_cost}, "
        "{single_total} monthly in total. Multi-region writes raise it to "
        "{multi_total}. With the D4s gateway the total is {gateway_total} "
        "({gateway_eur} in EUR)."),
    9: ("Two Healthcare stories use AKS. The first quotes {person} ({role}) of "
        "{company}; the second is about {second_customer}. The AKS product page has "
        "{aks_sections} section headings and its pricing details show a cluster node "
        "limit of {node_limit}. The account page shows {favorites} favorite."),
    10: ("The SQL dictionary search matches {sql_results} articles. The SQL database "
         "article's first section is '{first_section}' and it names Azure SQL. Azure "
         "SQL: {azure_sql_desc} Three always-on Linux D4s v5 VMs in East US cost "
         "{usd_total} monthly; West Europe costs {west_europe_total}, so West Europe "
         "is {west_europe_answer}."),
    11: ("Professional Direct fits business-critical functions: {response}. There are "
         "{tl_count} thought-leadership posts; the patch-window post takes "
         "{read_time} (published {post_date}). Four always-on Linux E8s v5 VMs in "
         "West US 2 cost {west_us2_total} ({west_us2_eur} in EUR); East US is "
         "{east_us_answer} at {east_us_total}."),
    12: ("Two always-on Linux B2s VMs in East US cost {total} monthly. The estimate "
         "saved as 'Edge cache pair' lists {total} on the account page, which shows "
         "{estimates} estimate and {favorites} favorite."),
    13: ("The pricing hub lists {pricing_cards} cards. The AKS pricing details show a "
         "cluster node limit of {node_limit} and compare the {tiers_sentence} tiers. "
         "The Linux VM pricing details say {unbilled_state} VMs are not billed. Three "
         "always-on Linux D4s v5 VMs cost {total}; the saved estimate 'Compute pilot' "
         "lists {saved_total}."),
    14: ("The site search returns {sections_sentence}. The Kubernetes dictionary "
         "article's first section is '{first_section}'. {aks_story_count} customer "
         "stories use AKS; the first is about {customer} and quotes {quoted_person}. "
         "The Containers category lists {containers_count} products; Azure Container "
         "Apps: {container_apps_desc} The account page shows {favorites} favorite."),
    15: ("There are {compute_free_count} always-free compute services; AKS's free "
         "allowance is {aks_free}. The cluster costs {control_cost} for the control "
         "plane and {nodes_cost} for the nodes, {usd_total} monthly ({eur_total} in "
         "EUR). The same three VMs alone cost {vm_total}; the difference covers the "
         "managed control plane."),
    16: ("There are {announcements} announcements. The GPT-6 Astra, Sol, and Luna post "
         "was published {post_date} and takes {read_time}. The Developer plan suits "
         "trial and testing: {trial_response}. 800 RU/s single-region with 250 GB "
         "costs {single_total} monthly; multi-region writes raise it to "
         "{multi_total}, and the D4s gateway brings the total to {gateway_total}."),
    17: ("One Financial Services story uses AKS. The first is about {customer} and "
         "quotes {person} ({quoted_role}). The AKS product page: {aks_desc} Its "
         "pricing details compare the {tiers_sentence} tiers, and the Linux VM "
         "pricing details say {unbilled_state} VMs are not billed. The account page "
         "shows {favorites} favorite. The calculator's Kubernetes tab offers "
         "{control_tiers_sentence} control-plane tiers."),
    18: ("The article is titled '{article_title}' and its first section is "
         "'{first_section}'. Microsoft Foundry: {foundry_desc} Three always-on Linux "
         "D4s v5 VMs in East US cost {usd_total} monthly ({eur_total} in EUR); West "
         "Europe costs {west_europe_total}, so West Europe is {west_europe_answer}."),
    19: ("The always-on AKS cluster costs {usd_total} monthly, saved as 'K8s pilot'. "
         "After signing back in the account page still shows {estimates} estimate "
         "and {favorites} favorite."),
}


def synthesize(idx, ans):
    t = ANSWER_TEMPLATES[idx]
    subs = dict(ans)
    if idx == 0:
        subs['second_pricing_answer'] = 'no' if not ans['second_has_pricing'] else 'a'
    if idx == 3:
        a = float(ans['aks_total'].replace('$', '').replace(',', ''))
        v = float(ans['vm_total'].replace('$', '').replace(',', ''))
        subs['difference_amount'] = f"${a - v:,.2f}"
    if idx == 4:
        subs['we_answer'] = 'cheaper' if ans['we_cheaper'] else 'more expensive'
    if idx == 6:
        subs['rates_sentence'] = '; '.join(
            f"{r} ${rate}" for r, rate in ans['rates'].items())
        subs['cheapest_rate'] = ans['rates'][ans['cheapest']]
    if idx == 7:
        subs['sweden_central_cosmos_answer'] = (
            'available' if 'Available' in ans['sweden_central_cosmos']
            else 'not available')
    if idx == 10:
        subs['west_europe_answer'] = 'more expensive' if ans['west_europe_more'] \
            else 'cheaper'
    if idx == 11:
        subs['east_us_answer'] = 'cheaper' if ans['east_us_cheaper'] \
            else 'more expensive'
    if idx == 13:
        subs['tiers_sentence'] = ' and '.join(ans['tiers'])
    if idx == 14:
        subs['sections_sentence'] = ', '.join(
            f"{count} {name.lower()}" for name, count in ans['section_results'].items())
    if idx == 17:
        subs['tiers_sentence'] = ' and '.join(ans['tiers'])
        subs['control_tiers_sentence'] = ', '.join(ans['control_tiers'])
    if idx == 18:
        subs['west_europe_answer'] = 'more expensive' if ans['west_europe_more'] \
            else 'cheaper'
    return t.format(**subs)


def make_png(path, seed):
    """A small valid non-blank PNG for the synthetic evidence."""
    from PIL import Image
    img = Image.new('RGB', (320, 200))
    px = img.load()
    for y in range(200):
        for x in range(320):
            px[x, y] = ((x * 7 + seed) % 256, (y * 13 + seed) % 256,
                        (x * y + seed) % 256)
    img.save(path, 'PNG')


def walk_round(tag):
    from contract_engine import verify
    failures = []
    for idx in range(20):
        A, client, root = VT.fresh_client(f'{tag}-t{idx}')
        # record the honest path's urls
        urls = []
        orig_go = VT.Walker.go
        orig_submit = VT.Walker.submit

        BASE = 'http://localhost:40133'

        def go(self, url, note=''):
            urls.append(BASE + url)
            return orig_go(self, url, note=note)

        def submit(self, url, data, note=''):
            urls.append(BASE + url)
            return orig_submit(self, url, data, note=note)

        VT.Walker.go = go
        VT.Walker.submit = submit
        try:
            ans, steps, log = VT.run_task(A, client, idx)
        finally:
            VT.Walker.go = orig_go
            VT.Walker.submit = orig_submit

        answer = synthesize(idx, ans)
        # synthetic run directory
        run = Path(tempfile.mkdtemp(prefix=f'ma-verify-{tag}-t{idx}-', dir='/tmp'))
        (run / 'screenshots').mkdir()
        db_path = root / 'microsoft_azure.db'
        shutil.copy2(db_path, run / 'initial.db')
        # after: the database is already post-task
        shutil.copy2(db_path, run / 'after.db')
        steps_json = []
        for i, u in enumerate(urls):
            shot = f'shot_{i:03d}.png'
            make_png(run / 'screenshots' / shot, idx * 100 + i)
            steps_json.append({'url': u, 'url_after': u,
                               'screenshot_after': shot})
        (run / 'trajectory.json').write_text(json.dumps({
            'task_id': f'Microsoft Azure--{idx}',
            'task': json.loads((SITE / 'tasks.jsonl').read_text()
                               .splitlines()[idx])['ques'],
            'start_url': 'http://localhost:40133/',
            'terminated': True,
            'termination_reason': 'agent_done',
            'steps': steps_json,
            'final_answer': answer,
        }), encoding='utf-8')
        # swap initial.db for a pristine seed copy
        seed_root = Path(tempfile.mkdtemp(prefix='ma-seed-', dir='/tmp'))
        os.environ['AZURE_DB_URI'] = f'sqlite:///{seed_root}/microsoft_azure.db'
        for mod in list(sys.modules):
            if mod.startswith(('app', 'seed', 'validate_tasks')):
                del sys.modules[mod]
        import app as A2  # noqa: F401 - imports seed the pristine DB
        shutil.copy2(seed_root / 'microsoft_azure.db', run / 'initial.db')
        shutil.rmtree(seed_root, ignore_errors=True)
        try:
            result = verify(str(run), f'Microsoft Azure--{idx}')
            status = 'PASS' if result['pass'] else 'FAIL'
            if not result['pass']:
                failures.append((idx, result['reason']))
            print(f'  task {idx:2d}: {status} ({steps} steps, '
                  f'{len(urls)} pages) {"" if result["pass"] else result["reason"]}')
        finally:
            shutil.rmtree(run, ignore_errors=True)
            shutil.rmtree(root, ignore_errors=True)
            for mod in list(sys.modules):
                if mod.startswith(('app', 'seed', 'validate_tasks')):
                    del sys.modules[mod]
    return failures


def main():
    print('walkthrough round 1 ...')
    f1 = walk_round('w1')
    print('walkthrough round 2 ...')
    f2 = walk_round('w2')
    if f1 or f2:
        print('\nFAILURES:', f1 + f2)
        return 1
    print('\nOK: both walkthrough rounds pass the verifier for all 20 tasks')
    return 0


if __name__ == '__main__':
    sys.exit(main())
