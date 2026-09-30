#!/usr/bin/env python3
"""Consolidate consecutive RUN steps in the Dockerfile into grouped
`set -e && (...) && (...)` steps so the image stays under the overlay2
max-layer-depth limit (128). Same consolidation the fox_sports
contribution uses. RUN commands containing double-quoted strings are
never merged (they keep their own layer); comments stay attached.
"""
import re
from pathlib import Path

DOCKERFILE = Path(__file__).resolve().parents[3] / "Dockerfile"
GROUP_SIZE = 3

lines = DOCKERFILE.read_text().splitlines(keepends=True)

blocks = []
i = 0
while i < len(lines):
    if lines[i].startswith("RUN "):
        cmd = [lines[i]]
        i += 1
        while i < len(lines) and (lines[i].startswith("    ") or lines[i].startswith("\t")):
            cmd.append(lines[i])
            i += 1
        blocks.append(("run", "".join(cmd)))
    else:
        buf = []
        while i < len(lines) and not lines[i].startswith("RUN "):
            buf.append(lines[i])
            i += 1
        blocks.append(("pre", "".join(buf)))


def body_of(cmd: str) -> str | None:
    """Shell body of a RUN command with continuations joined by single
    spaces; None when the command is unsafe to merge (quotes)."""
    parts = []
    for line in cmd.splitlines():
        line = line.rstrip("\n")
        if line.startswith("RUN "):
            line = line[4:]
        line = line.rstrip("\\").rstrip()
        if line:
            parts.append(line.strip())
    body = " ".join(parts)
    if '"' in body:
        return None
    return re.sub(r"\s+", " ", body).strip()


out = []
pending_pre = None
group = []


def flush():
    global group, pending_pre
    if group:
        if pending_pre:
            out.append(pending_pre)
        bodies = [f"({b})" for b in group]
        out.append("RUN set -e && \\\n    " + " && \\\n    ".join(bodies) + "\n\n")
    elif pending_pre:
        out.append(pending_pre)
    group.clear()
    pending_pre = None


for kind, content in blocks:
    if kind == "pre":
        if content.strip().startswith(("#", "")):
            if group:
                flush()
            pending_pre = (pending_pre or "") + content
        else:
            flush()
            out.append(content)
    else:
        body = body_of(content)
        if body is None:
            # unsafe to merge: flush and emit verbatim
            flush()
            if pending_pre:
                out.append(pending_pre)
                pending_pre = None
            out.append(content)
        else:
            group.append(body)
            if len(group) >= GROUP_SIZE:
                flush()
flush()

DOCKERFILE.write_text("".join(out))
runs = sum(1 for l in out if l.startswith("RUN "))
print(f"consolidated; RUN steps now: {runs}")
