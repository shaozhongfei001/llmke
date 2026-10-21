#!/usr/bin/env python3
"""Secret & sensitive-artifact scanner (fail-closed).

Detects, in tracked files (git ls-files) or a plain tree walk:
- real passwords / tokens / secrets in assignments (placeholders allowed)
- connection strings with embedded credentials (scheme://user:pass@host)
- private keys
- personal absolute paths (/home/<user>/..., /Users/<user>/...)
- suspected production host addresses (RFC1918 IPs, excluding loopback/doc ranges)
- git-tracked sensitive runtime artifacts (.env, *.sqlite, *.pyc, source_private/)

Exit 1 on any finding. Allowlist: one line per file:substring in
.security-allowlist (optional, must be reviewed).
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SECRET_ASSIGN_RE = re.compile(
    r"(?i)\b(\w*(?:password|passwd|pwd|secret|token|api[_-]?key|private[_-]?key)\w*)\b"
    r"\s*[:=]\s*(['\"]?)([^\s'\"#,)]{4,})"
)
BARE_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
CALL_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_.]*\($")
CONN_STR_RE = re.compile(
    r"(?i)\b[a-z][a-z0-9+.-]*://[^/\s:@]+:[^@\s]+@|jdbc:[a-z]+://\S+"
)
PRIVATE_KEY_RE = re.compile(r"BEGIN (?:RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY")
PERSONAL_PATH_RE = re.compile(r"(?<![\w.])(?:/home|/Users)/[A-Za-z0-9._-]+/")
PROD_HOST_RE = re.compile(
    r"\b(?:10\.\d{1,3}\.\d{1,3}\.\d{1,3}"
    r"|192\.168\.\d{1,3}\.\d{1,3}"
    r"|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3})\b"
)
PLACEHOLDER_RE = re.compile(
    r"^(\$\{?[A-Za-z_][A-Za-z0-9_]*\}?|<[^>]+>|\{\{[^}]+\}\}|\*+|x{4,}|"
    r"(?i:your[-_a-z]*|changeme|example|redacted|placeholder|dummy|"
    r"readonly-user|db-host|service-name|schema))$"
)
SENSITIVE_TRACKED_RE = re.compile(
    r"(^|/)(\.env(?!\.example)|[^/]*\.sqlite|[^/]*\.db|[^/]*\.pyc|"
    r"source_private/|oracle-dumps/|metadata-snapshots/)"
)
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".pytest_cache", ".venv", "venv"}
ALLOWLIST_FILE = ".security-allowlist"


def tracked_files(root: Path) -> list[Path]:
    try:
        out = subprocess.check_output(
            ["git", "-C", str(root), "ls-files"], text=True
        ).splitlines()
        return [root / f for f in out if f.strip()]
    except (subprocess.CalledProcessError, FileNotFoundError):
        files = []
        for p in root.rglob("*"):
            if any(part in SKIP_DIRS for part in p.parts):
                continue
            if p.is_file():
                files.append(p)
        return files


def tree_files(root: Path) -> list[Path]:
    """扫描工作树（跳过 SKIP_DIRS）。

    为什么需要：新仓库尚未提交时 `git ls-files` 为空，
    `security-check` 会以 "0 file(s) scanned" 通过——那是空转，
    不是「没有秘密」。空转不能当作证据。
    """
    files = []
    for p in root.rglob("*"):
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        if p.is_file():
            files.append(p)
    return files


def load_allowlist(root: Path) -> list[str]:
    p = root / ALLOWLIST_FILE
    if not p.is_file():
        return []
    return [
        ln.strip()
        for ln in p.read_text(encoding="utf-8").splitlines()
        if ln.strip() and not ln.startswith("#")
    ]


def is_allowlisted(rel: str, line: str, allowlist: list[str]) -> bool:
    """Allowlist semantics — `file:substring`, or bare `substring`.

    修复说明（llmke，2026-10-20）：原实现为
        any(f"{rel}:{a}" in f"{rel}:{line}" or a in line for a in allowlist)
    而 allowlist 文件写明格式是 `file:substring`。两者不匹配：
    对 `tests/x.py:secret` 这样的条目，`a in line` 永远为假（行里没有文件名），
    `f"{rel}:{a}"` 又变成 `tests/x.py:tests/x.py:secret`，也永远为假。
    结果是白名单形同虚设，而框架自身因为测试文件未被 git 跟踪，
    扫不到这些夹具，「PASS」其实是空转。这里按文档语义实现。
    """
    for entry in allowlist:
        if not entry:
            continue
        if ":" in entry:
            f, _, sub = entry.partition(":")
            if f == rel and sub and sub in line:
                return True
        elif entry in line:
            return True
    return False


def scan_file(path: Path, root: Path, allowlist: list[str]) -> list[str]:
    findings = []
    rel = path.relative_to(root).as_posix()
    if path.name == ALLOWLIST_FILE:
        return findings
    try:
        text = path.read_text(encoding="utf-8", errors="strict")
    except (UnicodeDecodeError, OSError):
        return findings  # binary files skipped
    for i, line in enumerate(text.splitlines(), 1):
        if is_allowlisted(rel, line, allowlist):
            continue
        m = SECRET_ASSIGN_RE.search(line)
        if m:
            quoted, value = m.group(2), m.group(3)
            is_placeholder = PLACEHOLDER_RE.match(value)
            # unquoted bare identifier -> variable reference (e.g. password=password), not a literal
            is_var_ref = path.suffix in {".py", ".java", ".js", ".ts"} and not quoted and BARE_IDENT_RE.match(value)
            # unquoted call expression -> lookup (e.g. password=env("X")), not a literal
            is_call = not quoted and CALL_RE.match(value)
            if not is_placeholder and not is_var_ref and not is_call:
                findings.append(f"{rel}:{i}: REAL_CREDENTIAL: {m.group(1)}=<value>")
        if CONN_STR_RE.search(line):
            findings.append(f"{rel}:{i}: REAL_CONNECTION_STRING: <redacted>")
        if PRIVATE_KEY_RE.search(line):
            findings.append(f"{rel}:{i}: PRIVATE_KEY material")
        m = PERSONAL_PATH_RE.search(line)
        if m:
            findings.append(f"{rel}:{i}: PERSONAL_ABSOLUTE_PATH: {m.group(0)}")
        m = PROD_HOST_RE.search(line)
        if m:
            findings.append(f"{rel}:{i}: SUSPECTED_PROD_HOST: {m.group(0)}")
    return findings


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=ROOT)
    ap.add_argument("--tracked-sensitive", action="store_true",
                    help="also fail on git-tracked sensitive runtime artifacts")
    ap.add_argument("--all-files", action="store_true",
                    help="scan the working tree instead of git ls-files "
                         "(use in a fresh repo, otherwise the scan is vacuous)")
    args = ap.parse_args()
    root = args.root.resolve()
    allowlist = load_allowlist(root)

    findings: list[str] = []
    files = tree_files(root) if args.all_files else tracked_files(root)
    if not files:
        print("FAIL: scope is empty — 0 file(s) to scan; use --all-files "
              "or commit before claiming a clean scan", file=sys.stderr)
        return 1
    for f in files:
        if not f.is_file():
            continue
        findings.extend(scan_file(f, root, allowlist))

    if args.tracked_sensitive:
        for f in files:
            rel = f.relative_to(root).as_posix()
            if SENSITIVE_TRACKED_RE.search(rel) and not is_allowlisted(rel, rel, allowlist):
                findings.append(f"{rel}: SENSITIVE_RUNTIME_ARTIFACT_TRACKED")

    for f_ in findings:
        print(f"FAIL: {f_}")
    if findings:
        print(f"security-check: FAIL ({len(findings)} finding(s))")
        return 1
    print(f"security-check: PASS ({len(files)} file(s) scanned)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
