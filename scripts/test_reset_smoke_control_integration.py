#!/usr/bin/env python3
"""Real CLI/HTTP/SQLite checks using current control routes and stubbed lifecycle.

Run in the repository Python environment (Flask/Werkzeug required). All state,
servers and credentials belong to temporary fixtures; no live deployment is used.
"""
from __future__ import annotations

import ast
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import threading
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from werkzeug.serving import WSGIRequestHandler, make_server

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_check_reset_smoke import SmokeServer, _SmokeHandler, build_repo

ROOT = Path(__file__).resolve().parents[1]


class QuietHandler(WSGIRequestHandler):
    def log_request(self, *args, **kwargs):
        pass


class ActualControlCliTests(unittest.TestCase):
    def test_real_control_auth_reset_all_and_mapped_homepages(self):
        token = 'fixture-control-token-' + 'x' * 40
        with tempfile.TemporaryDirectory(prefix='reset-smoke-control-') as tmp:
            root = Path(tmp)
            sites = ['amazon', 'apple']
            build_repo(root, sites=sites, with_runtime_db=False, with_seed_db=False)
            for site in sites:
                for sub in ('instance', 'instance_seed'):
                    (root / 'sites' / site / sub).mkdir(parents=True)
                for filename in (f'{site}.db', 'second.db'):
                    with sqlite3.connect(root / 'sites' / site / 'instance_seed' / filename) as db:
                        db.execute('CREATE TABLE state (value TEXT)')
                        db.execute("INSERT INTO state VALUES ('seed')")
                    shutil.copyfile(root / 'sites' / site / 'instance_seed' / filename,
                                    root / 'sites' / site / 'instance' / filename)
            # Configure the actual source's filesystem paths before its top-level mkdir.
            tree = ast.parse((ROOT / 'control_server.py').read_text())
            for node in tree.body:
                if isinstance(node, ast.Assign):
                    names = [t.id for t in node.targets if isinstance(t, ast.Name)]
                    if 'PID_DIR' in names:
                        node.value = ast.Call(func=ast.Name(id='Path', ctx=ast.Load()),
                                              args=[ast.Constant(str(root / 'pids'))], keywords=[])
            ast.fix_missing_locations(tree)
            control = types.ModuleType('fixture_control')
            with patch.dict(os.environ, {'WEBSYN_CONTROL_TOKEN': token}):
                exec(compile(tree, str(ROOT / 'control_server.py'), 'exec'), control.__dict__)
            control.SITES = sites
            control.WEBSYN_DIR = str(root / 'sites')
            control._site_locks = {s: threading.Lock() for s in sites}
            control.reap_exited_children = lambda: None
            control.read_pid_record = lambda s: {'pid': 123}
            control.process_matches_site = lambda *args: True
            control.kill_site = lambda s: None
            control.start_site = lambda s: 123
            control.wait_ready = lambda *args: True
            seen = []
            class Homepage(_SmokeHandler):
                def do_GET(self):
                    seen.append(self.headers.get('Authorization'))
                    super().do_GET()
            with SmokeServer(Homepage) as amazon, SmokeServer(Homepage) as apple:
                ports = {'amazon': amazon.port, 'apple': apple.port}
                control.site_port = lambda s: ports[s]
                # Health reports container ports, while probes use mapped fixture ports.
                original_health = control.app.view_functions['health']
                def mapped_health():
                    response, status = original_health()
                    payload = response.get_json()
                    for index, site in enumerate(sites):
                        payload['sites'][site]['port'] = 40000 + index
                    return control.jsonify(payload), status
                control.app.view_functions['health'] = mapped_health
                server = make_server('127.0.0.1', 0, control.app, threaded=True,
                                     request_handler=QuietHandler)
                thread = threading.Thread(target=server.serve_forever, daemon=True)
                thread.start()
                scripts = root / 'scripts'
                scripts.mkdir()
                shutil.copyfile(ROOT / 'scripts/check_reset_smoke.py', scripts / 'check_reset_smoke.py')
                shutil.copyfile(ROOT / 'scripts/site_registry.py', scripts / 'site_registry.py')
                command = [sys.executable, '-B', str(scripts / 'check_reset_smoke.py'), '--json',
                           '--control-url', f'http://127.0.0.1:{server.server_port}',
                           '--base-host', '127.0.0.1', '--db-root', str(root / 'sites')]
                for site, port in ports.items():
                    command += ['--site-port', f'{site}={port}']
                def run(extra, credential=token):
                    result = subprocess.run(command + extra, capture_output=True, text=True,
                        env={**os.environ, 'WEBSYN_CONTROL_TOKEN': credential}, timeout=30)
                    self.assertEqual(result.stderr, '')
                    self.assertNotIn(token, result.stdout)
                    return result.returncode, json.loads(result.stdout)
                def hash_runtime(site):
                    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                            for p in (root / 'sites' / site / 'instance').glob('*.db')}
                def dirty(site):
                    with sqlite3.connect(root / 'sites' / site / 'instance' / 'second.db') as db:
                        db.execute("UPDATE state SET value='dirty'")
                    (root / 'sites' / site / 'instance' / 'extra.db').write_bytes(b'extra')
                try:
                    for site in sites:
                        dirty(site)
                    before = {s: hash_runtime(s) for s in sites}
                    code, payload = run(['--site', 'amazon', '--reset-all'])
                    self.assertEqual(code, 1)
                    self.assertEqual(payload['summary']['sites_checked'], 0)
                    self.assertEqual(before, {s: hash_runtime(s) for s in sites})
                    code, payload = run(['--site', 'amazon'], credential='wrong-' + 'x' * 40)
                    self.assertEqual(code, 1)
                    self.assertEqual(payload['sites'][0]['md5_status'], 'SKIP')
                    self.assertEqual(before, {s: hash_runtime(s) for s in sites})
                    code, payload = run(['--site', 'amazon'])
                    self.assertEqual(code, 0, payload)
                    self.assertEqual(len(payload['sites'][0]['md5_files']), 2)
                    self.assertEqual(hash_runtime('apple'), before['apple'])
                    self.assertNotEqual(hash_runtime('amazon'), before['amazon'])
                    dirty('amazon')
                    code, payload = run(['--reset-all', '--strict'])
                    self.assertEqual(code, 0, payload)
                    self.assertEqual(payload['summary']['md5_pass'], 2)
                    for site in sites:
                        for db in (root / 'sites' / site / 'instance_seed').glob('*.db'):
                            self.assertEqual(db.read_bytes(),
                                             (root / 'sites' / site / 'instance' / db.name).read_bytes())
                        self.assertFalse((root / 'sites' / site / 'instance/extra.db').exists())
                    # A real backend seed failure returns 503; no parity PASS is possible.
                    shutil.rmtree(root / 'sites/apple/instance_seed')
                    code, payload = run(['--reset-all'])
                    self.assertEqual(code, 1)
                    self.assertEqual(payload['summary']['md5_pass'], 0)
                    self.assertEqual(payload['summary']['reset_fail'], 2)
                    self.assertTrue(seen)
                    self.assertTrue(all(header is None for header in seen))
                finally:
                    server.shutdown()
                    server.server_close()
                    thread.join(timeout=5)


if __name__ == '__main__':
    unittest.main()
