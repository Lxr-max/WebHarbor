#!/usr/bin/env python3
"""Tests for scripts/audit_site_registry.py."""

from __future__ import annotations

import io
import json
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import audit_site_registry as audit  # noqa: E402


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content).lstrip("\n"), encoding="utf-8")


def git_init_and_add(root: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "add", "."], cwd=root, check=True)


def build_repo(
    root: Path,
    *,
    sites: list[str] | None = None,
    site_dirs: list[str] | None = None,
    task_ports: dict[str, int] | None = None,
    docker_expose: str | None = None,
) -> None:
    sites = ["amazon"] if sites is None else sites
    docker_expose = docker_expose or f"EXPOSE 8101 40000-{40000 + len(sites) - 1}"
    site_dirs = list(sites) if site_dirs is None else site_dirs
    task_ports = (
        {site: 40000 + index for index, site in enumerate(sites)}
        if task_ports is None
        else task_ports
    )
    for index, site in enumerate(site_dirs):
        task_ports.setdefault(site, 41000 + index)

    write(
        root / "README.md",
        """
        # WebHarbor

        curl -X POST http://localhost:8101/reset/amazon
        """,
    )
    write(
        root / "CONTRIBUTING.md",
        """
        # Contributing
        """,
    )
    write(
        root / "websyn_start.sh",
        f"""
        #!/bin/bash
        SITES=({' '.join(sites)})
        BASE_PORT=40000
        """,
    )
    quoted_sites = ", ".join(repr(site) for site in sites)
    write(
        root / "control_server.py",
        f"""
        SITES = [{quoted_sites}]
        BASE_PORT = 40000
        """,
    )
    write(
        root / "site_runner.py",
        """
        from app import app
        """,
    )
    write(
        root / "Dockerfile",
        f"""
        FROM python:3.12-slim-bookworm
        {docker_expose}
        """,
    )
    write(
        root / ".assetpaths",
        """
        sites/*/instance_seed/
        sites/*/static/images/
        sites/*/static/external_cache/
        """,
    )

    sites_root = root / "sites"
    sites_root.mkdir(parents=True, exist_ok=True)
    for site in site_dirs:
        site_root = sites_root / site
        write(site_root / "app.py", "from flask import Flask\napp = Flask(__name__)\n")
        write(site_root / "_health.py", "pass\n")
        write(site_root / "templates" / "index.html", "<html></html>\n")
        write(
            site_root / "tasks.jsonl",
            json.dumps(
                {
                    "web_name": site.replace("_", " ").title(),
                    "id": f"{site}--0",
                    "ques": f"Find something on {site}",
                    "web": f"http://localhost:{task_ports[site]}/",
                    "upstream_url": f"https://{site}.example.com/",
                }
            )
            + "\n",
        )

    write(root / '.gitignore', 'sites/*/instance_seed/\nsites/*/static/images/\nsites/*/static/external_cache/\n')
    git_init_and_add(root)


class AuditSiteRegistryTests(unittest.TestCase):
    def test_valid_minimal_registry_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            build_repo(root)
            result = audit.audit_repository(root)
            self.assertEqual(result.exit_code, 0)
            self.assertEqual(len(result.errors), 0)

    def test_duplicate_task_url_ports_fail(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            build_repo(
                root,
                sites=["amazon", "apple"],
                task_ports={"amazon": 40000, "apple": 40000},
            )
            result = audit.audit_repository(root)
            self.assertNotEqual(result.exit_code, 0)
            self.assertTrue(
                any(
                    "task web URL port 40000 is already used by site 'amazon'"
                    in error.message
                    for error in result.errors
                ),
                result.errors,
            )

    def test_site_directory_missing_registration_warns(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            build_repo(root, sites=["amazon"], site_dirs=["amazon", "orphan_site"])
            result = audit.audit_repository(root)
            messages = [warning.message for warning in result.warnings]
            self.assertTrue(
                any("not registered" in message for message in messages),
                messages,
            )
            self.assertEqual(result.exit_code, 0)

    def test_registered_site_missing_directory_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            build_repo(root, sites=["amazon", "apple"], site_dirs=["amazon"])
            result = audit.audit_repository(root)
            messages = [error.message for error in result.errors]
            self.assertTrue(
                any("directory is missing" in message for message in messages),
                messages,
            )

    def test_task_url_port_mismatch_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            build_repo(root, task_ports={"amazon": 49999})
            result = audit.audit_repository(root)
            messages = [error.message for error in result.errors]
            self.assertTrue(
                any("does not match registered port" in message for message in messages),
                messages,
            )
            self.assertEqual(result.exit_code, 1)

    def test_warning_only_exits_zero_but_strict_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            build_repo(root)
            write(root / "sites/amazon/logs/debug.log", "log")
            git_init_and_add(root)
            normal = audit.audit_repository(root, strict=False)
            strict = audit.audit_repository(root, strict=True)
            self.assertEqual(normal.exit_code, 0)
            self.assertEqual(strict.exit_code, 1)

    def test_json_output_is_valid(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            build_repo(root)
            buffer = io.StringIO()
            exit_code = audit.main(["--json"], root=root, stdout=buffer)
            payload = json.loads(buffer.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertIn("summary", payload)
            self.assertIn("sites", payload)
            self.assertIn("ports", payload)

    def test_invalid_task_port_is_reported_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            build_repo(root)
            write(
                root / "sites" / "amazon" / "tasks.jsonl",
                json.dumps(
                    {
                        "web_name": "Amazon",
                        "id": "amazon--0",
                        "ques": "Find something",
                        "web": "http://localhost:not-a-port/",
                        "upstream_url": "https://amazon.example.com/",
                    }
                )
                + "\n",
            )

            result = audit.audit_repository(root)

            self.assertGreater(len(result.errors), 0)
            self.assertTrue(
                any("invalid port" in error.message for error in result.errors),
                result.errors,
            )

    def test_invalid_utf8_task_file_is_reported_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            build_repo(root)
            (root / "sites" / "amazon" / "tasks.jsonl").write_bytes(b"\xff\xfe")

            result = audit.audit_repository(root)

            self.assertEqual(result.exit_code, 1)
            self.assertTrue(
                any("UTF-8" in error.message for error in result.errors),
                result.errors,
            )

    def test_missing_required_repository_file_is_reported_without_traceback(self) -> None:
        required_files = ("websyn_start.sh", "control_server.py", "site_runner.py", "Dockerfile")
        for required_file in required_files:
            with self.subTest(required_file=required_file):
                with tempfile.TemporaryDirectory() as tmpdir:
                    root = Path(tmpdir)
                    build_repo(root)
                    (root / required_file).unlink()

                    result = audit.audit_repository(root)

                    self.assertEqual(result.exit_code, 1)
                    self.assertTrue(
                        any(required_file in error.message for error in result.errors),
                        result.errors,
                    )

    def test_shell_site_array_ignores_comments(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            build_repo(root)
            write(
                root / "websyn_start.sh",
                """
                SITES=(amazon # explanatory comment
                )
                BASE_PORT=40000
                """,
            )

            result = audit.audit_repository(root)

            self.assertEqual(result.exit_code, 0)
            self.assertEqual([site.site for site in result.sites], ["amazon"])

    def test_indented_shell_registry_declarations_are_supported(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            build_repo(root)
            write(
                root / "websyn_start.sh",
                """
                #!/bin/bash
                  SITES=(amazon)
                  BASE_PORT=40000
                """,
            )

            result = audit.audit_repository(root)

            self.assertEqual(result.exit_code, 0)
            self.assertEqual([site.site for site in result.sites], ["amazon"])

    def test_commented_registry_declarations_are_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            build_repo(root)
            write(
                root / "websyn_start.sh",
                """
                # SITES=(wrong_site)
                # BASE_PORT=49999
                SITES=(amazon)
                BASE_PORT=40000
                """,
            )

            result = audit.audit_repository(root)

            self.assertEqual(result.exit_code, 0)
            self.assertEqual([site.site for site in result.sites], ["amazon"])

    def test_function_local_registry_declarations_are_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            build_repo(root)
            write(
                root / "control_server.py",
                """
                def helper():
                    SITES = ["wrong_site"]
                    BASE_PORT = 49999

                SITES = ["amazon"]
                BASE_PORT = 40000
                """,
            )

            result = audit.audit_repository(root)

            self.assertEqual(result.exit_code, 0)
            self.assertEqual([site.site for site in result.sites], ["amazon"])

    def test_malformed_registry_is_reported_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            build_repo(root)
            write(root / "control_server.py", "SITES = [unknown_name]\nBASE_PORT = 40000\n")

            result = audit.audit_repository(root)

            self.assertEqual(result.exit_code, 1)
            self.assertTrue(
                any("control_server.py" in (error.file or "") for error in result.errors),
                result.errors,
            )

    def test_json_output_remains_valid_for_repository_errors(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            build_repo(root)
            (root / "Dockerfile").unlink()
            buffer = io.StringIO()

            exit_code = audit.main(["--json"], root=root, stdout=buffer)
            payload = json.loads(buffer.getvalue())

            self.assertEqual(exit_code, 1)
            self.assertEqual(payload["summary"]["errors"], 1)
            self.assertIn("Dockerfile", payload["errors"][0]["message"])

    def test_runtime_like_regular_file_is_reported_as_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            build_repo(root)
            write(root / "sites" / "amazon" / "logs", "runtime output\n")
            git_init_and_add(root)
            buffer = io.StringIO()

            exit_code = audit.main(["--json", "--strict"], root=root, stdout=buffer)
            payload = json.loads(buffer.getvalue())

            self.assertEqual(exit_code, 1)
            self.assertTrue(
                any(
                    warning["message"] == "runtime-like path is a file: logs"
                    for warning in payload["warnings"]
                ),
                payload["warnings"],
            )

    def test_ignored_runtime_content_does_not_fail_repository_audit(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            build_repo(root)
            write(root / ".gitignore", (root / ".gitignore").read_text() + "sites/*/instance/\n")
            git_init_and_add(root)
            write(root / "sites" / "amazon" / "instance" / "runtime.db", "runtime\n")

            result = audit.audit_repository(root, strict=True)

            self.assertEqual(result.exit_code, 0)
            self.assertFalse(
                any("runtime-like path" in warning.message for warning in result.warnings),
                result.warnings,
            )

    def test_explicit_assetpaths_cover_site_without_wildcard(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            build_repo(root)
            write(
                root / ".assetpaths",
                """
                sites/amazon/instance_seed/
                sites/amazon/static/images/
                sites/amazon/static/external_cache/
                """,
            )

            result = audit.audit_repository(root, strict=True)

            self.assertEqual(result.exit_code, 0)
            self.assertFalse(
                any(".assetpaths" in warning.message for warning in result.warnings),
                result.warnings,
            )

    def test_brand_web_name_does_not_require_slug_match(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            build_repo(root)
            write(
                root / "sites" / "amazon" / "tasks.jsonl",
                json.dumps(
                    {
                        "web_name": "Whole Foods Market",
                        "id": "amazon--0",
                        "ques": "Find something",
                        "web": "http://localhost:40000/",
                        "upstream_url": "https://amazon.example.com/",
                    }
                )
                + "\n",
            )

            result = audit.audit_repository(root, strict=True)

            self.assertEqual(result.exit_code, 0)
            self.assertFalse(
                any("does not look related" in warning.message for warning in result.warnings),
                result.warnings,
            )

    def test_docker_expose_protocol_suffix_is_supported(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            build_repo(root, docker_expose="expose 8101/tcp 40000/tcp")

            result = audit.audit_repository(root)

            self.assertEqual(result.exit_code, 0)
            self.assertEqual(result.ports["docker_exposed_ports"], [8101, 40000])

    def test_descending_docker_port_range_is_an_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            build_repo(root, docker_expose="EXPOSE 8101 40000-39999")

            result = audit.audit_repository(root)

            self.assertEqual(result.exit_code, 1)
            self.assertTrue(
                any("descending EXPOSE range" in error.message for error in result.errors),
                result.errors,
            )

    def test_out_of_range_docker_port_is_an_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            build_repo(root, docker_expose="EXPOSE 8101 40000 70000")

            result = audit.audit_repository(root)

            self.assertEqual(result.exit_code, 1)
            self.assertTrue(
                any("out-of-range EXPOSE token" in error.message for error in result.errors),
                result.errors,
            )

class ReviewRegressionTests(unittest.TestCase):
    def test_hidden_cache_is_not_a_site_but_unregistered_site_still_warns(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            build_repo(root)
            (root / 'sites/.cache/huggingface').mkdir(parents=True)
            result = audit.audit_repository(root, strict=True)
            self.assertEqual(result.exit_code, 0)
            self.assertEqual(result.site_directories_found, 1)
            self.assertEqual([s.site for s in result.sites], ['amazon'])

    def test_web_services_require_tcp_and_protocol_must_be_valid(self):
        for expose in ('EXPOSE 8101/udp 40000/udp', 'EXPOSE 8101/garbage 40000/tcp',
                       'EXPOSE 8101/tcp 40000/tcp 45000/tcp'):
            with self.subTest(expose=expose), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                build_repo(root, docker_expose=expose)
                self.assertEqual(audit.audit_repository(root, strict=True).exit_code, 1)

    def test_http_url_contract_is_shared_by_all_static_checks(self):
        import check_site_registry as compact
        import validate_tasks as tasks
        for url, expected in [('http://localhost:40000/', 0), ('http://127.0.0.1:40000/', 0),
                              ('https://localhost:40000/', 1), ('http://localhost:40001/', 1)]:
            with self.subTest(url=url), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                build_repo(root)
                task_path = root / 'sites/amazon/tasks.jsonl'
                task = json.loads(task_path.read_text())
                task.update(id='Amazon--0', web=url)
                task_path.write_text(json.dumps(task) + '\n')
                self.assertEqual(audit.audit_repository(root, strict=True).exit_code, expected)
                self.assertEqual(tasks.run_validation(root=root)['exit_code'], expected)
                from unittest.mock import patch
                from contextlib import redirect_stdout, redirect_stderr
                with patch.object(compact, 'ROOT', root), redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                    self.assertEqual(compact.main(), expected)

    def test_git_failures_and_non_worktrees_never_look_clean(self):
        from unittest.mock import patch
        import shutil
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            build_repo(root)
            for side_effect in (FileNotFoundError('missing git'), subprocess.TimeoutExpired('git', 30)):
                with self.subTest(error=side_effect), patch.object(audit.subprocess, 'run', side_effect=side_effect):
                    output = io.StringIO()
                    self.assertEqual(audit.main(['--json'], root=root, stdout=output), 1)
                    self.assertIn('Git inspection failed', json.loads(output.getvalue())['errors'][0]['message'])
            shutil.rmtree(root / '.git')
            self.assertEqual(audit.audit_repository(root).exit_code, 1)

    def test_asset_ignores_must_be_in_root_and_effective(self):
        cases = ('missing', 'info-only', 'negated')
        for case in cases:
            with self.subTest(case=case), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                build_repo(root)
                ignore = root / '.gitignore'
                if case != 'negated':
                    contents = ignore.read_text()
                    ignore.write_text('')
                    if case == 'info-only':
                        (root / '.git/info/exclude').write_text(contents)
                else:
                    ignore.write_text(ignore.read_text() + '!sites/amazon/static/images/\n')
                result = audit.audit_repository(root, strict=True)
                self.assertEqual(result.exit_code, 1)
                self.assertTrue(any('not ignored by root .gitignore' in f.message for f in result.errors))

    def test_nested_positive_ignore_and_empty_placeholder_are_supported(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            build_repo(root)
            write(root / 'sites/amazon/.gitignore', 'static/images/\n')
            write(root / 'sites/amazon/static/images/.gitkeep', '')
            subprocess.run(['git', 'add', '-f', 'sites/amazon/static/images/.gitkeep'], cwd=root, check=True)
            self.assertEqual(audit.audit_repository(root, strict=True).exit_code, 0)

    def test_real_tracked_assets_and_nonempty_placeholders_fail(self):
        for filename in ('photo.jpg', '.gitkeep'):
            with self.subTest(filename=filename), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                build_repo(root)
                path = f'sites/amazon/static/images/{filename}'
                write(root / path, 'asset bytes')
                subprocess.run(['git', 'add', '-f', path], cwd=root, check=True)
                result = audit.audit_repository(root, strict=True)
                self.assertEqual(result.exit_code, 1)
                self.assertTrue(any(f.message == 'HF-managed asset is tracked in Git' for f in result.errors))

    def test_tracked_runtime_file_missing_on_disk_still_warns(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            build_repo(root)
            path = root / 'sites/amazon/instance/state.db'
            write(path, 'runtime')
            git_init_and_add(root)
            path.unlink()
            result = audit.audit_repository(root, strict=True)
            self.assertEqual(result.exit_code, 1)
            self.assertTrue(any('runtime-like path' in f.message for f in result.warnings))

    def test_actual_cli_json_exit_and_read_only_behavior(self):
        import hashlib
        import shutil
        for bad in (False, True):
            with self.subTest(bad=bad), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                build_repo(root)
                scripts = root / 'scripts'
                scripts.mkdir()
                for name in ('audit_site_registry.py', 'validate_tasks.py', 'site_registry.py'):
                    shutil.copyfile(Path(__file__).parent / name, scripts / name)
                if bad:
                    (root / '.gitignore').write_text('')
                def hashes():
                    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                            for p in root.rglob('*') if p.is_file()}
                before = hashes()
                result = subprocess.run([sys.executable, '-B', str(scripts / 'audit_site_registry.py'),
                                         '--json', '--strict'], capture_output=True, text=True, cwd=root)
                self.assertEqual(result.stderr, '')
                self.assertEqual(result.returncode, int(bad))
                self.assertEqual(json.loads(result.stdout)['summary']['exit_code'], int(bad))
                self.assertEqual(before, hashes())



if __name__ == "__main__":
    unittest.main()
