"""Shared static registry and TCP exposure parsing for repository tools.

Never imports or executes startup/control code. Task-only fixtures may omit
BASE_PORT; callers inspecting deployments require it explicitly.
"""
from __future__ import annotations

import ast
import re
import shlex
from pathlib import Path
from typing import Any


class RegistryError(ValueError):
    """A site registry could not be read or the two registries disagree."""


def parse_site_array(text: str, file_label: str, *, require_base: bool = True, allow_duplicates: bool = False) -> tuple[list[str], int]:
    try:
        if file_label.endswith(".sh"):
            # Strip comments lexically; do not execute the startup script.
            lexer = shlex.shlex(text, posix=True, punctuation_chars="()=")
            lexer.whitespace_split = True
            tokens = list(lexer)
            # shlex groups adjacent punctuation; normalize literal assignments.
            expanded = []
            for token in tokens:
                if token and set(token) <= set("()="):
                    expanded.extend(token)
                else:
                    expanded.append(token)
            tokens = expanded
            start = tokens.index("SITES")
            if tokens[start + 1:start + 3] != ["=", "("]:
                raise ValueError("SITES must be a literal array")
            end = tokens.index(")", start + 3)
            sites = tokens[start + 3:end]
            if "BASE_PORT" not in tokens and not require_base:
                base_port = 40000
            else:
                base = tokens.index("BASE_PORT")
                if tokens[base + 1] != "=":
                    raise ValueError("BASE_PORT must be literal")
                base_port = int(tokens[base + 2])
        else:
            values = {}
            for node in ast.parse(text).body:
                if isinstance(node, ast.Assign):
                    names = [target.id for target in node.targets if isinstance(target, ast.Name)]
                elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                    names = [node.target.id]
                else:
                    continue
                for name in names:
                    if name in {"SITES", "BASE_PORT"}:
                        values[name] = ast.literal_eval(node.value)
            sites = values["SITES"]
            base_port = values["BASE_PORT"] if require_base else values.get("BASE_PORT", 40000)
        if not isinstance(sites, list) or not sites or any(
            not isinstance(site, str) or not re.fullmatch(r"[A-Za-z0-9_]+", site)
            for site in sites
        ):
            raise ValueError("SITES must be a nonempty list of valid site names")
        if not allow_duplicates and len(sites) != len(set(sites)):
            raise ValueError("SITES contains duplicate entries")
        if type(base_port) is not int or not 1 <= base_port <= 65536 - len(sites):
            raise ValueError("BASE_PORT or resulting port range is invalid")
        return sites, base_port
    except (ValueError, KeyError, IndexError, TypeError, SyntaxError) as exc:
        raise RegistryError(f"Could not parse SITES / BASE_PORT from {file_label}: {exc}") from None



def parse_docker_ports(dockerfile: Path) -> dict[str, Any]:
    exposed: set[int] = set()
    udp: set[int] = set()
    invalid_expose_tokens: list[str] = []
    text = dockerfile.read_text(encoding="utf-8")
    lines = re.sub(r"\\\s*\n", " ", text).splitlines()
    for line in lines:
        stripped = line.split("#", 1)[0].strip()
        tokens = stripped.split()
        if not tokens or tokens[0].upper() != "EXPOSE":
            continue
        for raw_token in tokens[1:]:
            port_token, separator, protocol = raw_token.partition("/")
            if separator and protocol not in {"tcp", "udp"}:
                invalid_expose_tokens.append(f"invalid EXPOSE token '{raw_token}'")
                continue
            port_match = re.fullmatch(r"(\d+)(?:-(\d+))?", port_token)
            if not port_match:
                invalid_expose_tokens.append(f"invalid EXPOSE token '{raw_token}'")
                continue
            start = int(port_match.group(1))
            end = int(port_match.group(2)) if port_match.group(2) else start
            if end < start:
                invalid_expose_tokens.append(f"descending EXPOSE range '{raw_token}'")
                continue
            if start < 1 or end > 65535:
                invalid_expose_tokens.append(f"out-of-range EXPOSE token '{raw_token}'")
                continue
            (udp if protocol == "udp" else exposed).update(range(start, end + 1))
    return {
        "exposed_ports": sorted(exposed),
        "udp_ports": sorted(udp),
        "invalid_expose_tokens": invalid_expose_tokens,
    }

