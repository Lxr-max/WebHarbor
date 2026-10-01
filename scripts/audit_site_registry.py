#!/usr/bin/env python3
"""Audit WebHarbor site registration consistency and port mappings.

This script checks repository-level site registration metadata without touching
runtime state or Hugging Face managed assets.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


try:
    from .site_registry import parse_site_array, parse_docker_ports
    from .validate_tasks import validate_local_web
except ImportError:
    from site_registry import parse_site_array, parse_docker_ports
    from validate_tasks import validate_local_web


RUNTIME_SUBDIRS = (
    "instance",
    "scraped_data",
    "cache",
    "caches",
    "log",
    "logs",
    "screenshots",
)


@dataclass
class Finding:
    severity: str
    message: str
    file: str | None = None
    site: str | None = None
    port: int | None = None
    line: int | None = None
    task_id: str | None = None


@dataclass
class SiteSummary:
    site: str
    in_sites_dir: bool
    in_websyn: bool
    in_control: bool
    websyn_port: int | None
    control_port: int | None
    task_file: str | None
    task_count: int
    task_port: int | None
    task_web_name: str | None
    has_app: bool
    has_seed_data: bool
    has_tasks: bool
    assetpaths_instance_seed: bool
    assetpaths_images: bool
    assetpaths_external_cache: bool
    warnings: int
    errors: int


@dataclass
class AuditResult:
    root: str
    strict: bool
    site_directories_found: int
    registered_sites_found: int
    ports_found: int
    task_files_checked: int
    task_count: int
    errors: list[Finding]
    warnings: list[Finding]
    sites: list[SiteSummary]
    ports: dict[str, Any]

    @property
    def exit_code(self) -> int:
        if self.errors:
            return 1
        if self.strict and self.warnings:
            return 1
        return 0

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "summary": {
                "root": self.root,
                "strict": self.strict,
                "site_directories_found": self.site_directories_found,
                "registered_sites_found": self.registered_sites_found,
                "ports_found": self.ports_found,
                "task_files_checked": self.task_files_checked,
                "task_count": self.task_count,
                "errors": len(self.errors),
                "warnings": len(self.warnings),
                "exit_code": self.exit_code,
            },
            "sites": [asdict(site) for site in self.sites],
            "ports": self.ports,
            "errors": [asdict(finding) for finding in self.errors],
            "warnings": [asdict(finding) for finding in self.warnings],
        }


class FindingCollector:
    def __init__(self) -> None:
        self.errors: list[Finding] = []
        self.warnings: list[Finding] = []

    def error(
        self,
        message: str,
        *,
        file: str | None = None,
        site: str | None = None,
        port: int | None = None,
        line: int | None = None,
        task_id: str | None = None,
    ) -> None:
        self.errors.append(
            Finding(
                severity="ERROR",
                message=message,
                file=file,
                site=site,
                port=port,
                line=line,
                task_id=task_id,
            )
        )

    def warn(
        self,
        message: str,
        *,
        file: str | None = None,
        site: str | None = None,
        port: int | None = None,
        line: int | None = None,
        task_id: str | None = None,
    ) -> None:
        self.warnings.append(
            Finding(
                severity="WARN",
                message=message,
                file=file,
                site=site,
                port=port,
                line=line,
                task_id=task_id,
            )
        )


def incomplete_audit_result(
    root: Path,
    *,
    strict: bool,
    collector: FindingCollector,
    site_directories_found: int = 0,
) -> AuditResult:
    return AuditResult(
        root=str(root),
        strict=strict,
        site_directories_found=site_directories_found,
        registered_sites_found=0,
        ports_found=0,
        task_files_checked=0,
        task_count=0,
        errors=collector.errors,
        warnings=collector.warnings,
        sites=[],
        ports={},
    )


def slug_is_valid(slug: str) -> bool:
    return bool(re.fullmatch(r"[a-z0-9_]+", slug))


def build_port_map(sites: list[str], base_port: int) -> dict[str, int]:
    return {site: base_port + index for index, site in enumerate(sites)}


def parse_assetpaths(assetpaths_path: Path) -> list[str]:
    if not assetpaths_path.exists():
        return []
    patterns: list[str] = []
    for raw_line in assetpaths_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        patterns.append(line.rstrip("/"))
    return patterns


def pattern_covers_site(patterns: list[str], site: str, suffix: str) -> bool:
    suffix = suffix.strip("/").replace("\\", "/")
    explicit = f"sites/{site}/{suffix}"
    wildcard = f"sites/*/{suffix}"
    return explicit in patterns or wildcard in patterns


def parse_readme_reset_examples(readme_path: Path) -> set[str]:
    if not readme_path.exists():
        return set()
    text = readme_path.read_text(encoding="utf-8", errors="replace")
    return set(re.findall(r"/reset/([A-Za-z0-9_]+)", text))


class InspectionError(ValueError):
    """A required read-only repository inspection could not complete."""


def git_read(root: Path, *args: str, data: bytes | None = None,
             allowed_codes: tuple[int, ...] = (0,)) -> bytes:
    try:
        result = subprocess.run(
            ["git", "-c", "core.excludesFile=/dev/null", *args], cwd=root,
            input=data, capture_output=True, timeout=30,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise InspectionError(f"Git inspection failed: {exc}") from None
    if result.returncode not in allowed_codes:
        raise InspectionError(f"Git inspection failed ({args[0]}): "
                              f"{result.stderr.decode(errors='replace').strip()}")
    return result.stdout


def inspect_git(root: Path, sites: list[str], patterns: list[str],
                collector: FindingCollector) -> set[str]:
    top = Path(git_read(root, 'rev-parse', '--show-toplevel').decode().strip()).resolve()
    if top != root.resolve():
        raise InspectionError("audit root must be the Git worktree root")
    tracked = {p.decode() for p in git_read(root, 'ls-files', '-z').split(b'\0') if p}
    # Probe hypothetical children: this needs no downloaded assets or file writes.
    managed = [f"sites/{site}/{suffix}" for site in sites
               for suffix in ('instance_seed', 'static/images', 'static/external_cache')
               if pattern_covers_site(patterns, site, suffix)]
    root_ignore_patterns = parse_assetpaths(root / ".gitignore")
    if managed:
        probes = [f"{directory}/.__webharbor_ignore_probe__" for directory in managed]
        output = git_read(root, 'check-ignore', '--no-index', '--stdin', '-z', '-v',
                          '--non-matching', data=b'\0'.join(p.encode() for p in probes) + b'\0',
                          allowed_codes=(0, 1))
        fields = output.split(b'\0')[:-1]
        if len(fields) != len(probes) * 4:
            raise InspectionError("Git returned an incomplete ignore inspection")
        for index, directory in enumerate(managed):
            source, _, pattern, path = [f.decode() for f in fields[index * 4:index * 4 + 4]]
            if path != probes[index]:
                raise InspectionError("Git ignore result does not match requested path")
            parts = directory.split('/')
            root_covers = pattern_covers_site(root_ignore_patterns, parts[1], '/'.join(parts[2:]))
            repository_rule = source == '.gitignore' or (
                source.endswith('/.gitignore') and not Path(source).is_absolute()
                and '..' not in Path(source).parts
            )
            if not root_covers or not repository_rule or not pattern or pattern.startswith('!'):
                collector.error(f"HF-managed directory is not ignored by root .gitignore: {directory}",
                                file=str(root / '.gitignore'), site=directory.split('/')[1])
    for path in sorted(tracked):
        if Path(path).name == '.gitkeep' and git_read(root, 'cat-file', '-s', ':' + path).strip() == b'0':
            continue  # Empty directory placeholders are also excluded by check_asset_inventory.py.
        if any(path == directory or path.startswith(directory + '/') for directory in managed):
            collector.error("HF-managed asset is tracked in Git", file=path,
                            site=path.split('/')[1])
    return tracked


def parse_tasks_jsonl(
    tasks_path: Path, collector: FindingCollector, site: str, expected_port: int | None = None
) -> tuple[int, int | None, str | None]:
    if not tasks_path.exists():
        collector.error("registered site is missing tasks.jsonl", file=str(tasks_path), site=site)
        return 0, None, None

    task_count = 0
    ports: set[int] = set()
    web_names: set[str] = set()
    seen_task_objects = False

    try:
        task_lines = tasks_path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        collector.error(
            f"could not read tasks.jsonl as UTF-8: {exc}",
            file=str(tasks_path),
            site=site,
        )
        return 0, None, None

    for line_number, raw_line in enumerate(task_lines, start=1):
        if not raw_line.strip():
            continue
        try:
            payload = json.loads(raw_line)
        except json.JSONDecodeError as exc:
            collector.error(
                f"invalid JSONL: {exc.msg}",
                file=str(tasks_path),
                site=site,
                line=line_number,
            )
            continue
        if not isinstance(payload, dict):
            collector.error(
                "task line is not a JSON object",
                file=str(tasks_path),
                site=site,
                line=line_number,
            )
            continue

        seen_task_objects = True
        task_count += 1
        web_name = payload.get("web_name")
        web_url = payload.get("web")
        task_id = payload.get("id")

        if isinstance(web_name, str) and web_name.strip():
            web_names.add(web_name.strip())
        else:
            collector.warn(
                "task is missing a non-empty web_name field",
                file=str(tasks_path),
                site=site,
                line=line_number,
                task_id=str(task_id) if task_id else None,
            )

        if not isinstance(web_url, str) or not web_url.strip():
            collector.warn(
                "task is missing a non-empty web field",
                file=str(tasks_path),
                site=site,
                line=line_number,
                task_id=str(task_id) if task_id else None,
            )
            continue

        try:
            parsed = urlparse(web_url)
            hostname = parsed.hostname
            port = parsed.port
        except ValueError as exc:
            collector.error(
                f"task web URL has an invalid port or host: {exc}",
                file=str(tasks_path),
                site=site,
                line=line_number,
                task_id=str(task_id) if task_id else None,
            )
            continue
        findings = []
        validate_local_web(web_url, site, expected_port, tasks_path, line_number,
                           tasks_path.parents[2], findings, {})
        for finding in findings:
            collector.error(finding.message, file=str(tasks_path), site=site, line=line_number)
        if port is not None:
            ports.add(port)

    if not seen_task_objects:
        collector.error("tasks.jsonl is empty", file=str(tasks_path), site=site)

    if len(web_names) > 1:
        collector.warn(
            f"task file uses multiple web_name values: {sorted(web_names)}",
            file=str(tasks_path),
            site=site,
        )

    task_port = next(iter(ports)) if len(ports) == 1 else None
    if len(ports) > 1:
        collector.warn(
            f"task file uses multiple localhost ports: {sorted(ports)}",
            file=str(tasks_path),
            site=site,
        )

    web_name = next(iter(web_names)) if len(web_names) == 1 else None
    return task_count, task_port, web_name


def human_status(errors: int, warnings: int) -> str:
    if errors:
        return "ERROR"
    if warnings:
        return "WARN"
    return "OK"


def _audit_repository(root: Path, *, site: str | None = None, strict: bool = False) -> AuditResult:
    collector = FindingCollector()

    readme_path = root / "README.md"
    websyn_path = root / "websyn_start.sh"
    control_path = root / "control_server.py"
    site_runner_path = root / "site_runner.py"
    dockerfile_path = root / "Dockerfile"
    assetpaths_path = root / ".assetpaths"
    sites_root = root / "sites"

    if not sites_root.exists():
        collector.error("sites directory is missing", file=str(sites_root))
        return incomplete_audit_result(
            root,
            strict=strict,
            collector=collector,
        )

    site_dirs = sorted(path.name for path in sites_root.iterdir()
                       if path.is_dir() and not path.name.startswith("."))
    required_paths = (websyn_path, control_path, site_runner_path, dockerfile_path)
    for required_path in required_paths:
        if not required_path.is_file():
            collector.error(
                f"required repository file is missing: {required_path.name}",
                file=str(required_path),
            )
    if collector.errors:
        return incomplete_audit_result(
            root,
            strict=strict,
            collector=collector,
            site_directories_found=len(site_dirs),
        )

    websyn_text = websyn_path.read_text(encoding="utf-8", errors="replace")
    control_text = control_path.read_text(encoding="utf-8", errors="replace")
    site_runner_text = site_runner_path.read_text(encoding="utf-8", errors="replace")
    docker_ports = parse_docker_ports(dockerfile_path)
    asset_patterns = parse_assetpaths(assetpaths_path)
    readme_reset_sites = parse_readme_reset_examples(readme_path)

    websyn_registry: tuple[list[str], int] | None = None
    control_registry: tuple[list[str], int] | None = None
    try:
        websyn_registry = parse_site_array(websyn_text, str(websyn_path))
    except (SyntaxError, ValueError) as exc:
        collector.error(str(exc), file=str(websyn_path))
    try:
        control_registry = parse_site_array(control_text, str(control_path))
    except (SyntaxError, ValueError) as exc:
        collector.error(str(exc), file=str(control_path))
    if collector.errors:
        return incomplete_audit_result(
            root,
            strict=strict,
            collector=collector,
            site_directories_found=len(site_dirs),
        )

    assert websyn_registry is not None
    assert control_registry is not None
    websyn_sites, websyn_base_port = websyn_registry
    control_sites, control_base_port = control_registry
    websyn_port_map = build_port_map(websyn_sites, websyn_base_port)
    control_port_map = build_port_map(control_sites, control_base_port)
    exposed_ports = set(docker_ports["exposed_ports"])

    if site is not None:
        all_known_sites = set(site_dirs) | set(websyn_sites) | set(control_sites)
        if site not in all_known_sites:
            collector.error(f"site '{site}' was not found in sites/ or registry lists", site=site)
        sites_to_check = [site]
    else:
        sites_to_check = sorted(set(site_dirs) | set(websyn_sites) | set(control_sites))

    if len(websyn_sites) != len(set(websyn_sites)):
        duplicates = sorted(
            item for item in set(websyn_sites) if websyn_sites.count(item) > 1
        )
        collector.error(
            f"websyn_start.sh contains duplicate site slugs: {duplicates}",
            file=str(websyn_path),
        )

    if len(control_sites) != len(set(control_sites)):
        duplicates = sorted(
            item for item in set(control_sites) if control_sites.count(item) > 1
        )
        collector.error(
            f"control_server.py contains duplicate site slugs: {duplicates}",
            file=str(control_path),
        )

    if websyn_sites != control_sites:
        collector.error(
            "websyn_start.sh and control_server.py site registration lists do not match exactly",
            file=str(websyn_path),
        )

    if websyn_base_port != control_base_port:
        collector.error(
            "websyn_start.sh and control_server.py use different BASE_PORT values",
            file=str(websyn_path),
            port=websyn_base_port,
        )

    if 8101 not in exposed_ports:
        collector.error("Dockerfile is missing EXPOSE 8101", file=str(dockerfile_path), port=8101)
    for invalid_expose_token in docker_ports["invalid_expose_tokens"]:
        collector.error(invalid_expose_token, file=str(dockerfile_path))

    expected_tcp = {8101, *websyn_port_map.values()}
    if exposed_ports - expected_tcp:
        collector.error(f"Dockerfile exposes unregistered TCP ports: {sorted(exposed_ports - expected_tcp)}",
                        file=str(dockerfile_path))

    registered_site_ports = {
        site_slug: websyn_port_map[site_slug] for site_slug in websyn_sites
    }

    if "from app import app" not in site_runner_text:
        collector.warn(
            "site_runner.py no longer imports app.py directly; app.py entrypoint checks may need review",
            file=str(site_runner_path),
        )

    for reset_site in sorted(readme_reset_sites):
        if reset_site not in registered_site_ports:
            collector.warn(
                f"README reset example references unknown site '{reset_site}'",
                file=str(readme_path),
                site=reset_site,
            )

    if not asset_patterns:
        collector.warn(".assetpaths is missing or empty", file=str(assetpaths_path))

    try:
        tracked_files = inspect_git(root, sites_to_check, asset_patterns, collector)
    except (InspectionError, UnicodeError) as exc:
        collector.error(str(exc), file=str(root))
        return incomplete_audit_result(root, strict=strict, collector=collector,
                                       site_directories_found=len(site_dirs))

    site_summaries: list[SiteSummary] = []
    total_task_count = 0
    task_files_checked = 0
    task_ports_seen: dict[int, str] = {}

    for site_slug in sites_to_check:
        site_dir = sites_root / site_slug
        in_sites_dir = site_dir.is_dir()
        in_websyn = site_slug in websyn_port_map
        in_control = site_slug in control_port_map
        websyn_port = websyn_port_map.get(site_slug)
        control_port = control_port_map.get(site_slug)

        if not slug_is_valid(site_slug):
            collector.warn("site slug contains characters outside [a-z0-9_]", site=site_slug)

        if in_sites_dir and not in_websyn and not in_control:
            collector.warn(
                "site directory exists but is not registered in websyn_start.sh or control_server.py",
                file=str(site_dir),
                site=site_slug,
            )

        if (in_websyn or in_control) and not in_sites_dir:
            collector.error(
                "site is registered but its directory is missing under sites/",
                file=str(site_dir),
                site=site_slug,
                port=websyn_port or control_port,
            )

        has_app = (site_dir / "app.py").exists() if in_sites_dir else False
        has_seed_data = (site_dir / "seed_data.py").exists() if in_sites_dir else False
        tasks_path = site_dir / "tasks.jsonl"
        has_tasks = tasks_path.exists() if in_sites_dir else False

        if in_sites_dir and in_websyn and not has_app:
            collector.error(
                "registered site is missing app.py required by site_runner.py",
                file=str(site_dir / "app.py"),
                site=site_slug,
                port=websyn_port,
            )

        assetpaths_instance_seed = pattern_covers_site(asset_patterns, site_slug, "instance_seed")
        assetpaths_images = pattern_covers_site(asset_patterns, site_slug, "static/images")
        assetpaths_external_cache = pattern_covers_site(
            asset_patterns, site_slug, "static/external_cache"
        )

        if in_sites_dir and not assetpaths_instance_seed:
            collector.warn(
                "site is not covered by .assetpaths for instance_seed",
                file=str(assetpaths_path),
                site=site_slug,
            )
        if in_sites_dir and not assetpaths_images:
            collector.warn(
                "site is not covered by .assetpaths for static/images",
                file=str(assetpaths_path),
                site=site_slug,
            )
        if in_sites_dir and not assetpaths_external_cache:
            collector.warn(
                "site is not covered by .assetpaths for static/external_cache",
                file=str(assetpaths_path),
                site=site_slug,
            )

        if in_sites_dir:
            for runtime_subdir in RUNTIME_SUBDIRS:
                prefix = f"sites/{site_slug}/{runtime_subdir}"
                tracked = [p for p in tracked_files if p == prefix or p.startswith(prefix + '/')]
                if tracked:
                    message = (f"runtime-like path is a file: {runtime_subdir}" if prefix in tracked
                               else f"runtime-like path has tracked files: {runtime_subdir}")
                    collector.warn(message, file=str(site_dir / runtime_subdir), site=site_slug)

        task_count = 0
        task_port = None
        task_web_name = None
        if in_sites_dir:
            task_count, task_port, task_web_name = parse_tasks_jsonl(tasks_path, collector, site_slug, websyn_port or control_port)
            total_task_count += task_count
            if tasks_path.exists():
                task_files_checked += 1

            if (
                task_port is not None
                and task_port in task_ports_seen
                and task_ports_seen[task_port] != site_slug
            ):
                collector.error(
                    f"task web URL port {task_port} is already used by site '{task_ports_seen[task_port]}'",
                    file=str(tasks_path),
                    site=site_slug,
                    port=task_port,
                )
            elif task_port is not None:
                task_ports_seen[task_port] = site_slug

            expected_port = websyn_port or control_port
            if expected_port is not None and expected_port not in exposed_ports:
                collector.error(
                    "Dockerfile does not expose the registered site port",
                    file=str(dockerfile_path),
                    site=site_slug,
                    port=expected_port,
                )

        if websyn_port is not None and not (40000 <= websyn_port <= 49999):
            collector.warn(
                "registered port falls outside the expected 40000+ WebHarbor range",
                file=str(websyn_path),
                site=site_slug,
                port=websyn_port,
            )

        site_errors = 0
        site_warnings = 0
        for finding in collector.errors:
            if finding.site == site_slug:
                site_errors += 1
        for finding in collector.warnings:
            if finding.site == site_slug:
                site_warnings += 1

        site_summaries.append(
            SiteSummary(
                site=site_slug,
                in_sites_dir=in_sites_dir,
                in_websyn=in_websyn,
                in_control=in_control,
                websyn_port=websyn_port,
                control_port=control_port,
                task_file=str(tasks_path) if tasks_path.exists() else None,
                task_count=task_count,
                task_port=task_port,
                task_web_name=task_web_name,
                has_app=has_app,
                has_seed_data=has_seed_data,
                has_tasks=has_tasks,
                assetpaths_instance_seed=assetpaths_instance_seed,
                assetpaths_images=assetpaths_images,
                assetpaths_external_cache=assetpaths_external_cache,
                warnings=site_warnings,
                errors=site_errors,
            )
        )

    ports_payload = {
        "websyn_base_port": websyn_base_port,
        "control_base_port": control_base_port,
        "websyn_ports": websyn_port_map,
        "control_ports": control_port_map,
        "docker_exposed_ports": docker_ports["exposed_ports"],
    }

    return AuditResult(
        root=str(root),
        strict=strict,
        site_directories_found=len(site_dirs),
        registered_sites_found=len(set(websyn_sites) | set(control_sites)),
        ports_found=len(set(registered_site_ports.values())),
        task_files_checked=task_files_checked,
        task_count=total_task_count,
        errors=collector.errors,
        warnings=collector.warnings,
        sites=site_summaries,
        ports=ports_payload,
    )


def audit_repository(root: Path, *, site: str | None = None, strict: bool = False) -> AuditResult:
    try:
        return _audit_repository(root, site=site, strict=strict)
    except (OSError, UnicodeError, ValueError) as exc:
        collector = FindingCollector()
        collector.error(f"repository inspection failed: {exc}", file=str(root))
        return incomplete_audit_result(root, strict=strict, collector=collector)


def render_human(result: AuditResult) -> str:
    lines = [
        (
            f"Checked {result.site_directories_found} site directorie(s), "
            f"{result.registered_sites_found} registered site(s), "
            f"{result.ports_found} port(s), "
            f"{result.task_files_checked} task file(s), "
            f"{result.task_count} task(s)"
        ),
        f"Errors: {len(result.errors)}  Warnings: {len(result.warnings)}",
        "",
    ]

    for site in result.sites:
        status = human_status(site.errors, site.warnings)
        port_display = site.websyn_port if site.websyn_port is not None else site.control_port
        lines.append(
            (
                f"[{status}] {site.site}: "
                f"registered={site.in_websyn and site.in_control} "
                f"dir={site.in_sites_dir} "
                f"port={port_display} "
                f"tasks={site.task_count}"
            )
        )

    findings = [*result.errors, *result.warnings]
    if findings:
        lines.append("")
        for finding in findings:
            parts = [finding.severity]
            if finding.file:
                parts.append(f"file={finding.file}")
            if finding.site:
                parts.append(f"site={finding.site}")
            if finding.port is not None:
                parts.append(f"port={finding.port}")
            if finding.line is not None:
                parts.append(f"line={finding.line}")
            if finding.task_id:
                parts.append(f"task_id={finding.task_id}")
            parts.append(finding.message)
            lines.append(" | ".join(parts))

    return "\n".join(lines)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", help="Audit only one site slug under sites/<slug>/")
    parser.add_argument("--strict", action="store_true", help="Treat warnings as failures")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON only")
    return parser


def main(
    argv: list[str] | None = None,
    *,
    root: Path | None = None,
    stdout: Any = None,
) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    target_root = root or Path(__file__).resolve().parents[1]
    result = audit_repository(target_root, site=args.site, strict=args.strict)
    stream = stdout if stdout is not None else sys.stdout

    if args.json:
        json.dump(result.to_json_dict(), stream, indent=2, sort_keys=True)
        stream.write("\n")
    else:
        stream.write(render_human(result))
        stream.write("\n")
    return result.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
