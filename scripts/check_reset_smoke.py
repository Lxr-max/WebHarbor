#!/usr/bin/env python3
"""Check WebHarbor control-plane reset behavior, homepage smoke, and DB MD5s.

The DB parity check hashes whichever DB source is configured and always reports
which one it read (``md5_source``). The control plane resets
``/opt/WebSyn/<site>/instance`` inside the deployment, which is not the repository
checkout when the environment runs in Docker, so a parity verdict is only reported
against a source the caller actually pointed at.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from http.client import HTTPException
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener, urlopen


try:  # Support both `python scripts/tool.py` and package imports.
    from .site_registry import RegistryError, parse_site_array
except ImportError:
    from site_registry import RegistryError, parse_site_array


@dataclass
class Message:
    severity: str
    message: str
    site: str | None = None
    url: str | None = None
    file: str | None = None


@dataclass
class ControlCheck:
    url: str
    status: str
    http_status: int | None
    detail: str


@dataclass
class SiteCheck:
    site: str
    port: int
    homepage_url: str
    reset_status: str
    reset_http_status: int | None
    reset_detail: str
    home_status: str
    home_http_status: int | None
    home_detail: str
    md5_status: str
    md5_source: str
    md5_runtime_db: str | None
    md5_seed_db: str | None
    md5_runtime_hash: str | None
    md5_seed_hash: str | None
    md5_detail: str
    md5_files: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class SmokeResult:
    root: str
    control_url: str
    base_host: str
    timeout: float
    strict: bool
    reset_all: bool
    control_server: ControlCheck
    sites_discovered: int
    sites_checked: int
    site_checks: list[SiteCheck]
    errors: list[Message]
    warnings: list[Message]

    @property
    def exit_code(self) -> int:
        if self.errors:
            return 1
        if self.strict and self.warnings:
            return 1
        return 0

    def summary_counts(self) -> dict[str, int]:
        def count(attr: str, value: str) -> int:
            return sum(1 for site in self.site_checks if getattr(site, attr) == value)

        return {
            "reset_pass": count("reset_status", "PASS"),
            "reset_fail": count("reset_status", "FAIL"),
            "reset_skip": count("reset_status", "SKIP"),
            "home_pass": count("home_status", "PASS"),
            "home_fail": count("home_status", "FAIL"),
            "home_skip": count("home_status", "SKIP"),
            "md5_pass": count("md5_status", "PASS"),
            "md5_fail": count("md5_status", "FAIL"),
            "md5_skip": count("md5_status", "SKIP"),
        }

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "summary": {
                "root": self.root,
                "control_url": self.control_url,
                "base_host": self.base_host,
                "timeout": self.timeout,
                "strict": self.strict,
                "reset_all": self.reset_all,
                "sites_discovered": self.sites_discovered,
                "sites_checked": self.sites_checked,
                "errors": len(self.errors),
                "warnings": len(self.warnings),
                "exit_code": self.exit_code,
                **self.summary_counts(),
            },
            "control_server": asdict(self.control_server),
            "sites": [asdict(check) for check in self.site_checks],
            "errors": [asdict(item) for item in self.errors],
            "warnings": [asdict(item) for item in self.warnings],
        }


class Collector:
    def __init__(self) -> None:
        self.errors: list[Message] = []
        self.warnings: list[Message] = []

    def error(
        self,
        message: str,
        *,
        site: str | None = None,
        url: str | None = None,
        file: str | None = None,
    ) -> None:
        self.errors.append(Message("ERROR", message, site=site, url=url, file=file))

    def warn(
        self,
        message: str,
        *,
        site: str | None = None,
        url: str | None = None,
        file: str | None = None,
    ) -> None:
        self.warnings.append(Message("WARN", message, site=site, url=url, file=file))


def build_port_map(sites: list[str], base_port: int) -> dict[str, int]:
    return {site: base_port + index for index, site in enumerate(sites)}


def _read_registry(root: Path, name: str) -> str:
    try:
        return (root / name).read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        raise RegistryError(f"{name} is missing from {root}") from None
    except OSError as exc:
        raise RegistryError(f"{name} could not be read: {exc}") from None


def discover_sites(root: Path) -> dict[str, int]:
    """Return the registered site -> port map, or raise RegistryError.

    Registry drift is a finding this checker is meant to report, so every failure
    here is raised as RegistryError and rendered as a structured error by main().
    """
    websyn_text = _read_registry(root, "websyn_start.sh")
    control_text = _read_registry(root, "control_server.py")
    websyn_sites, websyn_base = parse_site_array(websyn_text, "websyn_start.sh")
    control_sites, control_base = parse_site_array(control_text, "control_server.py")
    if websyn_sites != control_sites:
        only_websyn = [s for s in websyn_sites if s not in control_sites]
        only_control = [s for s in control_sites if s not in websyn_sites]
        detail = []
        if only_websyn:
            detail.append(f"only in websyn_start.sh: {', '.join(only_websyn)}")
        if only_control:
            detail.append(f"only in control_server.py: {', '.join(only_control)}")
        if not detail:
            detail.append("same sites in a different order")
        raise RegistryError(
            "websyn_start.sh and control_server.py registration lists are "
            f"out of sync ({'; '.join(detail)})"
        )
    if websyn_base != control_base:
        raise RegistryError(
            f"BASE_PORT differs between the registries: websyn_start.sh={websyn_base}, "
            f"control_server.py={control_base}"
        )
    return build_port_map(websyn_sites, websyn_base)


def md5_file(path: Path) -> str:
    hasher = hashlib.md5()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


DOCKER_SITE_ROOT = "/opt/WebSyn"


@dataclass
class DbCheck:
    status: str
    source: str
    runtime_db: str | None
    seed_db: str | None
    runtime_hash: str | None
    seed_hash: str | None
    detail: str
    files: list[dict[str, Any]] = field(default_factory=list)


def db_inventory(directory: Path) -> dict[str, str]:
    """Hash every DB; refuse active SQLite sidecars instead of ignoring writes."""
    if not directory.is_dir():
        raise OSError(f"missing DB directory: {directory}")
    for pattern in ("*.db-wal", "*.db-journal"):
        for sidecar in directory.glob(pattern):
            if sidecar.stat().st_size:
                raise OSError(f"nonempty SQLite sidecar prevents byte-parity verification: {sidecar}")
    paths = sorted(directory.glob("*.db"))
    if not paths:
        raise OSError(f"no DB files in {directory}")
    return {path.name: md5_file(path) for path in paths}


def docker_md5(container: str, dirs: list[str]) -> dict[str, dict[str, str]]:
    """Run the same inventory implementation inside the selected container."""
    import inspect

    script = ("import hashlib, json, sys\nfrom pathlib import Path\n"
              + inspect.getsource(md5_file) + "\n" + inspect.getsource(db_inventory)
              + "\nprint(json.dumps({d: db_inventory(Path(d)) for d in sys.argv[1:]}))\n")
    try:
        proc = subprocess.run(
            ["docker", "exec", container, "python3", "-c", script, *dirs],
            capture_output=True, text=True, timeout=60,
        )
        if proc.returncode:
            raise RuntimeError(proc.stderr.strip() or f"exit {proc.returncode}")
        inventories = json.loads(proc.stdout)
        if not isinstance(inventories, dict) or set(inventories) != set(dirs):
            raise ValueError("unexpected DB inventory directories")
        return inventories
    except (OSError, subprocess.SubprocessError, ValueError) as exc:
        raise RuntimeError(f"docker DB inventory failed: {exc}") from None


def check_db_parity(
    site: str,
    *,
    db_root: str | None,
    docker_container: str | None,
    container_hasher: Any,
    collector: Collector,
    reset_succeeded: bool,
) -> DbCheck:
    if docker_container:
        base = f"{DOCKER_SITE_ROOT}/{site}"
        source = f"docker:{docker_container}:{base}"
    elif db_root is not None:
        base = str(Path(db_root) / site)
        source = f"local:{base}"
    else:
        return DbCheck(
            "SKIP", "none", None, None, None, None,
            "no DB source configured; the control plane resets "
            f"{DOCKER_SITE_ROOT}/{site}/instance inside the deployment. "
            "Pass --docker-container or --db-root to check DB parity.",
        )
    runtime_dir, seed_dir = f"{base}/instance", f"{base}/instance_seed"
    if not reset_succeeded:
        return DbCheck("SKIP", source, runtime_dir, seed_dir, None, None,
                       "no successful reset to verify; DB parity not evaluated")
    try:
        if docker_container:
            inventories = (container_hasher or docker_md5)(docker_container, [runtime_dir, seed_dir])
        else:
            inventories = {d: db_inventory(Path(d)) for d in (runtime_dir, seed_dir)}
        for directory in (runtime_dir, seed_dir):
            entries = inventories[directory]
            if not isinstance(entries, dict) or not entries or any(
                not isinstance(name, str) or Path(name).name != name or not name.endswith(".db")
                or not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{32}", digest)
                for name, digest in entries.items()
            ):
                raise ValueError(f"invalid DB inventory: {directory}")
    except Exception as exc:  # noqa: BLE001 - failures remain structured
        detail = f"could not read {'container' if docker_container else 'local'} DB inventory: {exc}"
        collector.error(detail, site=site, file=getattr(exc, "filename", None) or base)
        return DbCheck("FAIL", source, runtime_dir, seed_dir, None, None, detail)
    runtime, seed = inventories[runtime_dir], inventories[seed_dir]
    files = [
        {"name": name, "runtime_hash": runtime.get(name), "seed_hash": seed.get(name),
         "status": "PASS" if name in runtime and name in seed and runtime[name] == seed[name] else "FAIL"}
        for name in sorted(runtime.keys() | seed.keys())
    ]
    failed = [entry["name"] for entry in files if entry["status"] == "FAIL"]
    detail = (f"DB inventory/hash mismatch: {', '.join(failed)}" if failed else
              f"all {len(files)} runtime DBs match the seed inventory and bytes")
    if failed:
        collector.error(detail, site=site, file=runtime_dir)
    # Preserve the old single-DB fields; multi-DB results use md5_files.
    single = files[0] if len(files) == 1 else None
    return DbCheck(
        "FAIL" if failed else "PASS", source,
        f"{runtime_dir}/{single['name']}" if single else runtime_dir,
        f"{seed_dir}/{single['name']}" if single else seed_dir,
        single["runtime_hash"] if single else None,
        single["seed_hash"] if single else None, detail, files,
    )


class RejectControlRedirects(HTTPRedirectHandler):
    """A control response must come from the configured authenticated endpoint."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def http_request(
    url: str,
    *,
    method: str = "GET",
    timeout: float = 10.0,
    bearer_token: str | None = None,
    control_kind: str | None = None,
    expected_sites: dict[str, int] | None = None,
) -> tuple[bool, int | None, str]:
    request = Request(url, method=method)
    open_request = urlopen
    if bearer_token:
        request.add_unredirected_header("Authorization", f"Bearer {bearer_token}")
    if bearer_token or control_kind:
        open_request = build_opener(RejectControlRedirects()).open
    try:
        with open_request(request, timeout=timeout) as response:
            body = response.read(1024 * 1024 + 1 if control_kind else 512)
            if control_kind:
                try:
                    if response.status != 200 or len(body) > 1024 * 1024:
                        raise ValueError("expected HTTP 200 with a bounded JSON body")
                    validate_control_response(json.loads(body), control_kind, expected_sites or {})
                except (ValueError, TypeError, KeyError) as exc:
                    return False, response.status, f"invalid {control_kind} response: {exc}"
            detail = f"HTTP {response.status}"
            if body:
                detail += f" ({len(body)} byte(s) read)"
            return True, response.status, detail
    except HTTPError as exc:
        return False, exc.code, f"HTTP {exc.code}: {exc.reason}"
    except URLError as exc:
        reason = getattr(exc, "reason", exc)
        detail = str(reason)
        if "Connection refused" in detail or "[WinError 10061]" in detail:
            detail += " (server may not be running)"
        return False, None, detail
    except (OSError, ValueError, HTTPException) as exc:
        detail = str(exc)
        if "Connection refused" in detail or "[WinError 10061]" in detail:
            detail += " (server may not be running)"
        return False, None, detail


def validate_control_response(payload: Any, kind: str, expected: dict[str, int]) -> None:
    if not isinstance(payload, dict):
        raise ValueError("expected an object")
    def reset_entry(entry: Any, site: str) -> bool:
        return (isinstance(entry, dict) and entry.get("site") == site
                and entry.get("ready") is True and not entry.get("error")
                and type(entry.get("pid")) is int and entry["pid"] > 0)
    if kind == "reset":
        if len(expected) != 1 or not reset_entry(payload, next(iter(expected))):
            raise ValueError("reset must identify the requested site and a ready process")
        return
    entries = payload.get("sites")
    if payload.get("ok") is not True or not isinstance(entries, dict) or set(entries) != set(expected):
        raise ValueError("expected ok=true and exactly the registered sites")
    if kind == "reset-all":
        if payload.get("partial") is not False or not all(reset_entry(entries[s], s) for s in expected):
            raise ValueError("every reset result must be ready; partial resets fail")
    elif kind == "health":
        if not all(isinstance(entries[s], dict) and entries[s].get("alive") is True
                   and entries[s].get("ready") is True and entries[s].get("port") == port
                   for s, port in expected.items()):
            raise ValueError("site readiness or registry ports do not match")
    else:
        raise ValueError("unknown control response kind")


def normalize_control_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme and parsed.netloc:
        return url.rstrip("/")
    return f"http://{url.strip().rstrip('/')}"


def build_homepage_url(base_host: str, port: int) -> str:
    host = base_host.strip().strip("/")
    if "://" in host:
        parsed = urlparse(host)
        scheme = parsed.scheme or "http"
        hostname = parsed.hostname or "localhost"
        return f"{scheme}://{hostname}:{port}/"
    return f"http://{host}:{port}/"


def check_control_health(
    control_url: str, timeout: float, collector: Collector,
    control_token: str | None = None,
    expected_sites: dict[str, int] | None = None,
) -> ControlCheck:
    url = f"{control_url}/health"
    ok, status_code, detail = http_request(
        url, timeout=timeout, bearer_token=control_token,
        control_kind="health", expected_sites=expected_sites,
    )
    if ok:
        return ControlCheck(url=url, status="PASS", http_status=status_code, detail=detail)
    collector.error("control server health check failed", url=url)
    return ControlCheck(url=url, status="FAIL", http_status=status_code, detail=detail)


def check_site(
    site: str,
    port: int,
    *,
    control_url: str,
    base_host: str,
    timeout: float,
    collector: Collector,
    use_reset_all: bool,
    reset_all_ok: bool,
    control_token: str | None = None,
    db_root: str | None = None,
    docker_container: str | None = None,
    container_hasher: Any = None,
    host_port: int | None = None,
) -> SiteCheck:
    homepage_url = build_homepage_url(base_host, host_port if host_port is not None else port)

    if use_reset_all:
        if reset_all_ok:
            reset_status = "PASS"
            reset_code = 200
            reset_detail = "covered by successful /reset-all call"
        else:
            reset_status = "FAIL"
            reset_code = None
            # The failure is already recorded once against /reset-all itself; do not
            # repeat it for every registered site.
            reset_detail = "reset-all failed; per-site reset was not attempted"
    else:
        reset_url = f"{control_url}/reset/{site}"
        ok, status_code, detail = http_request(
            reset_url, method="POST", timeout=timeout, bearer_token=control_token,
            control_kind="reset", expected_sites={site: port},
        )
        if ok:
            reset_status = "PASS"
            reset_code = status_code
            reset_detail = detail
        else:
            reset_status = "FAIL"
            reset_code = status_code
            reset_detail = detail
            collector.error("site reset request failed", site=site, url=reset_url)

    home_ok, home_status_code, home_detail = http_request(homepage_url, timeout=timeout)
    if home_ok:
        home_status = "PASS"
    else:
        home_status = "FAIL"
        collector.error("homepage smoke check failed", site=site, url=homepage_url)

    db = check_db_parity(
        site,
        db_root=db_root,
        docker_container=docker_container,
        container_hasher=container_hasher,
        collector=collector,
        reset_succeeded=reset_status == "PASS",
    )

    return SiteCheck(
        site=site,
        port=port,
        homepage_url=homepage_url,
        reset_status=reset_status,
        reset_http_status=reset_code,
        reset_detail=reset_detail,
        home_status=home_status,
        home_http_status=home_status_code,
        home_detail=home_detail,
        md5_status=db.status,
        md5_source=db.source,
        md5_runtime_db=db.runtime_db,
        md5_seed_db=db.seed_db,
        md5_runtime_hash=db.runtime_hash,
        md5_seed_hash=db.seed_hash,
        md5_detail=db.detail,
        md5_files=db.files,
    )


def run_checks(
    root: Path,
    *,
    site: str | None = None,
    control_url: str = "http://localhost:8101",
    control_token: str | None = None,
    base_host: str = "localhost",
    timeout: float = 120.0,
    strict: bool = False,
    reset_all: bool = False,
    db_root: str | None = None,
    docker_container: str | None = None,
    container_hasher: Any = None,
    site_ports: dict[str, int] | None = None,
) -> SmokeResult:
    collector = Collector()
    control_url = normalize_control_url(control_url)

    def empty(detail: str) -> SmokeResult:
        return SmokeResult(
            root=str(root),
            control_url=control_url,
            base_host=base_host,
            timeout=timeout,
            strict=strict,
            reset_all=reset_all,
            control_server=ControlCheck(
                url=f"{control_url}/health",
                status="SKIP",
                http_status=None,
                detail=detail,
            ),
            sites_discovered=0,
            sites_checked=0,
            site_checks=[],
            errors=collector.errors,
            warnings=collector.warnings,
        )

    if site is not None and reset_all:
        collector.error("--site and --reset-all are mutually exclusive; reset-all affects every site")
        return empty("conflicting reset scope; no requests sent")
    if db_root is not None and docker_container is not None:
        collector.error("--db-root and --docker-container are mutually exclusive")
        return empty("conflicting DB sources; no requests sent")
    if not math.isfinite(timeout) or timeout <= 0:
        collector.error("--timeout must be finite and positive")
        return empty("invalid timeout; no requests sent")

    if control_token is not None and (
        len(control_token) < 32 or any(not 33 <= ord(c) <= 126 for c in control_token)
    ):
        collector.error("WEBSYN_CONTROL_TOKEN must contain at least 32 printable ASCII characters without whitespace")
        return empty("invalid control token; no requests sent")

    try:
        site_map = discover_sites(root)
    except RegistryError as exc:
        # Registry drift and unreadable registries are findings, not crashes.
        collector.error(str(exc), file=str(root))
        return empty("site registry could not be resolved")
    site_ports = site_ports or {}
    if any(name not in site_map or type(port) is not int or not 1 <= port <= 65535
           for name, port in site_ports.items()):
        collector.error("--site-port requires a registered site and a host port in 1..65535")
        return empty("invalid host port mapping; no requests sent")
    if site is not None:
        if site not in site_map:
            collector.error(f"unknown site '{site}'")
            return SmokeResult(
                root=str(root),
                control_url=control_url,
                base_host=base_host,
                timeout=timeout,
                strict=strict,
                reset_all=reset_all,
                control_server=ControlCheck(
                    url=f"{control_url}/health",
                    status="SKIP",
                    http_status=None,
                    detail="site lookup failed before control checks",
                ),
                sites_discovered=len(site_map),
                sites_checked=0,
                site_checks=[],
                errors=collector.errors,
                warnings=collector.warnings,
            )
        filtered_sites = {site: site_map[site]}
    else:
        filtered_sites = site_map

    host_ports = [site_ports.get(name, port) for name, port in filtered_sites.items()]
    if len(host_ports) != len(set(host_ports)):
        collector.error("homepage host port mappings overlap")
        return empty("overlapping host ports; no requests sent")
    control = check_control_health(control_url, timeout, collector, control_token, site_map)
    reset_all_ok = False
    if reset_all:
        reset_all_url = f"{control_url}/reset-all"
        ok, status_code, detail = http_request(
            reset_all_url, method="POST", timeout=timeout, bearer_token=control_token,
            control_kind="reset-all", expected_sites=site_map,
        )
        if ok:
            reset_all_ok = True
        else:
            collector.error(f"reset-all request failed: {detail}", url=reset_all_url)
            if status_code == 404:
                collector.warn("control server does not expose /reset-all", url=reset_all_url)

    site_checks = [
        check_site(
            site_slug,
            port,
            control_url=control_url,
            control_token=control_token,
            base_host=base_host,
            timeout=timeout,
            collector=collector,
            use_reset_all=reset_all,
            reset_all_ok=reset_all_ok,
            db_root=db_root,
            docker_container=docker_container,
            container_hasher=container_hasher,
            host_port=site_ports.get(site_slug),
        )
        for site_slug, port in filtered_sites.items()
    ]

    return SmokeResult(
        root=str(root),
        control_url=control_url,
        base_host=base_host,
        timeout=timeout,
        strict=strict,
        reset_all=reset_all,
        control_server=control,
        sites_discovered=len(site_map),
        sites_checked=len(site_checks),
        site_checks=site_checks,
        errors=collector.errors,
        warnings=collector.warnings,
    )


def render_human(result: SmokeResult) -> str:
    counts = result.summary_counts()
    lines = [
        f"Control URL: {result.control_url}",
        f"Base host: {result.base_host}",
        f"Sites discovered: {result.sites_discovered}",
        f"Sites checked: {result.sites_checked}",
        (
            "Reset pass/fail/skip: "
            f"{counts['reset_pass']}/{counts['reset_fail']}/{counts['reset_skip']}"
        ),
        (
            "Homepage pass/fail/skip: "
            f"{counts['home_pass']}/{counts['home_fail']}/{counts['home_skip']}"
        ),
        (
            "MD5 pass/fail/skip: "
            f"{counts['md5_pass']}/{counts['md5_fail']}/{counts['md5_skip']}"
        ),
        f"Errors: {len(result.errors)}  Warnings: {len(result.warnings)}",
        (
            "Control health: "
            f"{result.control_server.status} "
            f"{result.control_server.http_status or ''} "
            f"{result.control_server.detail}"
        ).strip(),
        "",
    ]

    for site in result.site_checks:
        lines.append(
            (
                f"[{site.site}] port={site.port} "
                f"reset={site.reset_status} home={site.home_status} md5={site.md5_status}"
            )
        )
        lines.append(f"  reset: {site.reset_detail}")
        lines.append(f"  home: {site.home_detail}")
        lines.append(f"  md5: [{site.md5_source}] {site.md5_detail}")

    findings = [*result.errors, *result.warnings]
    if findings:
        lines.append("")
        for item in findings:
            parts = [item.severity]
            if item.site:
                parts.append(f"site={item.site}")
            if item.url:
                parts.append(f"url={item.url}")
            if item.file:
                parts.append(f"file={item.file}")
            parts.append(item.message)
            lines.append(" | ".join(parts))

    return "\n".join(lines)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", help="Check only one registered site slug")
    parser.add_argument(
        "--control-url",
        default="http://localhost:8101",
        help=("Control server base URL (default: http://localhost:8101); "
              "authentication reads WEBSYN_CONTROL_TOKEN from the environment"),
    )
    parser.add_argument(
        "--base-host",
        default="localhost",
        help="Hostname used to build per-site homepage URLs (default: localhost)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=120.0,
        help="HTTP timeout in seconds (default: 120; resets can take over 60 seconds)",
    )
    parser.add_argument(
        "--db-root",
        help=(
            "Deployment root holding <site>/instance and <site>/instance_seed, for "
            "sites deployed on this host. There is no default: without this or "
            "--docker-container the DB check is skipped, because this checkout is not "
            "what the control plane resets when the environment runs in Docker."
        ),
    )
    parser.add_argument(
        "--docker-container",
        help=(
            "Hash each site's DBs inside this running container under "
            f"{DOCKER_SITE_ROOT}/<site>, i.e. where the control plane actually resets them."
        ),
    )
    parser.add_argument(
        "--site-port", action="append", default=[], metavar="SITE=PORT",
        help="Override a homepage host port; repeat for non-default published ports",
    )
    parser.add_argument("--strict", action="store_true", help="Treat warnings as failures")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON only")
    parser.add_argument(
        "--reset-all",
        action="store_true",
        help="Call POST /reset-all once instead of per-site POST /reset/<site>",
    )
    return parser


def main(
    argv: list[str] | None = None,
    *,
    root: Path | None = None,
    stdout: Any = None,
) -> int:
    args = build_arg_parser().parse_args(argv)
    target_root = root or Path(__file__).resolve().parents[1]
    site_ports = {}
    for mapping in args.site_port:
        name, separator, value = mapping.partition("=")
        if not separator or not value.isdecimal() or name in site_ports:
            build_arg_parser().error("--site-port must be SITE=PORT with no repeated site")
        site_ports[name] = int(value)
    result = run_checks(
        target_root,
        site=args.site,
        control_url=args.control_url,
        control_token=os.environ.get("WEBSYN_CONTROL_TOKEN"),
        base_host=args.base_host,
        timeout=args.timeout,
        strict=args.strict,
        reset_all=args.reset_all,
        db_root=args.db_root,
        docker_container=args.docker_container,
        site_ports=site_ports,
    )
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
