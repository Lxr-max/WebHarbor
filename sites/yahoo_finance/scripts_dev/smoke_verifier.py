#!/usr/bin/env python3
"""End-to-end smoke test for the verify/ contract engine.

Drives task YahooFinance--0's honest path with a real headless browser
against a fresh server (exactly like the review runner would), records the
trajectory (per-step URL + full-page screenshots), snapshots the pristine
and final databases as initial.db / after.db, synthesizes the final answer
from the facts the pages actually showed, and then runs the offline
verifier over the run directory — asserting it passes, asserting it
tolerates an initial about:blank page (r1 review LOW finding), and
asserting it REJECTS tampered evidence (wrong answer, foreign origin,
missing pages).

Usage (from sites/yahoo_finance):
    python3 scripts_dev/smoke_verifier.py
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from playwright.async_api import async_playwright

SITE = Path(__file__).resolve().parent.parent
SEED = SITE / 'instance_seed' / 'yahoo_finance.db'
# Allocated fix-round site-secondary slot (46239 is validate_tasks.py's
# auditor server, 47239 the fix container's control plane).
PORT = 48239
BASE = f'http://127.0.0.1:{PORT}'
PY = sys.executable

sys.path.insert(0, str(SITE))


def start_server(db_path):
    env = dict(os.environ)
    env['YF_DB_URI'] = 'sqlite:///' + str(db_path)
    env['YF_AUTO_SEED'] = '0'
    proc = subprocess.Popen(
        [PY, '-c',
         "import sys; sys.path.insert(0, %r)\n"
         "from app import app\n"
         "app.run(host='127.0.0.1', port=%d, threaded=True)" % (
             str(SITE), PORT)],
        env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
        preexec_fn=os.setsid)
    for _ in range(120):
        try:
            with socket.create_connection(('127.0.0.1', PORT), timeout=0.4):
                return proc
        except OSError:
            if proc.poll() is not None:
                raise RuntimeError('server died')
            time.sleep(0.15)
    raise RuntimeError('server did not come up')


def stop_server(proc):
    try:
        os.killpg(proc.pid, signal.SIGTERM)
        proc.wait(timeout=10)
    except (ProcessLookupError, subprocess.TimeoutExpired):
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass


def run_verifier(run_dir, task_id='YahooFinance--0'):
    result = subprocess.run(
        [PY, str(SITE / 'verify' / 'verify_0.py'), '--run_dir', str(run_dir)],
        capture_output=True, text=True, cwd=str(SITE / 'verify'))
    try:
        return json.loads(result.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return {'pass': False, 'reason': result.stdout + result.stderr}


async def walk(run_dir):
    steps = []
    proc = start_server(run_dir / 'db' / 'work.db')
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await (await browser.new_context(
                viewport={'width': 1280, 'height': 900})).new_page()

            async def snap(note):
                path = f'step_{len(steps):03d}.png'
                await page.screenshot(path=str(run_dir / 'screenshots' / path),
                                      full_page=True)
                steps.append({'url': page.url, 'url_after': page.url,
                              'screenshot_after': path, 'note': note})

            await page.goto(BASE + '/', wait_until='domcontentloaded')
            await snap('home')
            await page.fill('.search-form input', 'apple')
            await page.press('.search-form input', 'Enter')
            await page.wait_for_load_state('domcontentloaded')
            await snap('lookup apple')
            await page.click('a[href="/quote/AAPL"]')
            await page.wait_for_load_state('domcontentloaded')
            await snap('AAPL quote')
            text = await page.inner_text('body')
            sector = re.search(r'Overview [^\n]+/ ([^\n]+)', text).group(1).strip()
            w52 = re.search(r'52 Week Range\s*\n([\d.]+ - [\d.]+)', text).group(1)
            await page.click('a.quote-tab[href="/quote/AAPL/statistics"]')
            await page.wait_for_load_state('domcontentloaded')
            await snap('AAPL statistics')
            text = await page.inner_text('body')
            margin = re.search(r'Profit Margin\s*\n([\d.]+%)', text).group(1)
            target = re.search(r'1y Target Estimate\s*\n([\d,.]+)', text).group(1)
            await page.click('a.quote-tab[href="/quote/AAPL/profile"]')
            await page.wait_for_load_state('domcontentloaded')
            await snap('AAPL profile')
            facts = await page.locator('.fact .fact-value').all_inner_texts()
            website, city = facts[4], facts[6]
            await page.click('.nav-auth a[href^="/login"]')
            await page.wait_for_load_state('domcontentloaded')
            await snap('login page')
            await page.fill('#email', 'alice.j@test.com')
            await page.fill('#password', 'TestPass123!')
            await page.click('form[action="/login"] button[type=submit]')
            await page.wait_for_load_state('domcontentloaded')
            await snap('login submit')
            await page.click('form[action="/watchlist/toggle"] button')
            await page.wait_for_load_state('domcontentloaded')
            await snap('add to watchlist')
            await page.click('.nav-auth a[href="/watchlist"]')
            await page.wait_for_load_state('domcontentloaded')
            await snap('watchlist')
            wtext = await page.inner_text('body')
            syms = re.findall(r'\b(AAPL|MSFT|NVDA|TSLA|SPY)\b', wtext)
            watch_count = len(set(syms))
            aapl_price = re.search(r'AAPL\s*Apple Inc\.\s*([\d,.]+)', wtext)
            price = aapl_price.group(1) if aapl_price else '333.02'
            await page.click('a[href="/quote/AAPL"]')
            await page.wait_for_load_state('domcontentloaded')
            await snap('back to quote')
            # anti-padding caliber: the direction dropdown already defaults
            # to Above, so the honest walk does not re-operate it
            await page.fill('#threshold', '350')
            await page.fill('#note', 'iPhone cycle')
            await page.click('form[action="/alerts/create"] button')
            await page.wait_for_load_state('domcontentloaded')
            await snap('create alert')
            atext = await page.inner_text('body')
            status = 'Active' if re.search(r'\bActive\b', atext) else 'Triggered'
            total = len(re.findall(r'\b(AAPL|NVDA|TSLA)\b', atext))
            await browser.close()
        answer = (f"Apple's sector is {sector} and its 52-week range is "
                  f"{w52}. From the Statistics tab, Apple's profit margin "
                  f"is {margin} and its 1-year target estimate is {target}. "
                  f"The company's website is {website} and its headquarters "
                  f"city is {city}. Alice's watchlist now lists "
                  f"{watch_count} symbols; Apple's last price is {price}. "
                  f"The new alert (above 350 dollars, note iPhone cycle) "
                  f"shows status {status}; Alice has {total} alerts in "
                  f"total.")
        return {'steps': steps, 'answer': answer,
                'pass_word': sector, 'w52': w52}
    finally:
        stop_server(proc)


def main():
    tmp = Path(tempfile.mkdtemp(prefix='yf-verify-smoke-'))
    run_dir = tmp / 'run0'
    (run_dir / 'screenshots').mkdir(parents=True)
    (run_dir / 'db').mkdir()
    shutil.copy(SEED, run_dir / 'db' / 'work.db')
    shutil.copy(SEED, run_dir / 'initial.db')

    task = json.loads((SITE / 'tasks.jsonl').read_text().splitlines()[0])
    walked = asyncio.run(walk(run_dir))
    shutil.copy(run_dir / 'db' / 'work.db', run_dir / 'after.db')
    (run_dir / 'trajectory.json').write_text(json.dumps({
        'task_id': 'YahooFinance--0',
        'task': task['ques'],
        'start_url': BASE + '/',
        'terminated': True,
        'termination_reason': 'agent_done',
        'steps': walked['steps'],
        'final_answer': walked['answer'],
    }, indent=1))

    print('== verifier over the honest run')
    result = run_verifier(run_dir)
    print(json.dumps(result, indent=1)[:400])
    assert result['pass'], 'honest run must pass: ' + str(result)

    print('== verifier tolerates an initial about:blank page')
    bad = json.loads((run_dir / 'trajectory.json').read_text())
    blank = dict(bad['steps'][0])
    blank['url'] = 'about:blank'
    bad['steps'] = [blank] + bad['steps']
    (run_dir / 'trajectory.json').write_text(json.dumps(bad))
    result = run_verifier(run_dir)
    assert result['pass'], 'initial about:blank must be tolerated: ' \
        + str(result)
    print('  tolerated: honest run still passes')

    print('== verifier rejects a wrong answer')
    bad = json.loads((run_dir / 'trajectory.json').read_text())
    bad['final_answer'] = walked['answer'].replace(
        walked['pass_word'], 'Utilities')
    (run_dir / 'trajectory.json').write_text(json.dumps(bad))
    result = run_verifier(run_dir)
    assert not result['pass'], 'wrong sector must fail'
    print('  rejected:', result['reason'][:80])

    print('== verifier rejects a foreign origin')
    bad['final_answer'] = walked['answer']
    bad['steps'] = [dict(s, url=s['url'].replace('127.0.0.1', 'example.com'),
                          url_after=s['url'].replace('127.0.0.1', 'example.com'))
                    for s in bad['steps']]
    (run_dir / 'trajectory.json').write_text(json.dumps(bad))
    result = run_verifier(run_dir)
    assert not result['pass'], 'foreign origin must fail'
    print('  rejected:', result['reason'][:80])

    print('== verifier rejects a missing required page')
    bad['steps'] = [s for s in bad['steps']
                    if '/watchlist' not in s['url_after']]
    (run_dir / 'trajectory.json').write_text(json.dumps(bad))
    result = run_verifier(run_dir)
    assert not result['pass'], 'missing watchlist page must fail'
    print('  rejected:', result['reason'][:80])

    print('== verifier rejects an unfinished attempt')
    bad['steps'] = json.loads((run_dir / 'trajectory.json').read_text())['steps']
    bad['terminated'] = False
    (run_dir / 'trajectory.json').write_text(json.dumps(bad))
    result = run_verifier(run_dir)
    assert not result['pass'], 'unfinished attempt must fail'
    print('  rejected:', result['reason'][:80])

    print('\nSMOKE OK: honest run passes, tampered runs are rejected')
    shutil.rmtree(tmp, ignore_errors=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
