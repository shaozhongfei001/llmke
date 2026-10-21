#!/usr/bin/env python3
"""Controlled framework installer.

Phases:  PLAN -> VALIDATE -> APPLY -> VERIFY -> MANIFEST
                              └-> ROLLBACK on any failure

Guarantees:
- Default mode is `plan` (shows CREATE/UPDATE/SKIP/CONFLICT/REJECT, writes nothing).
- Existing files with different content -> CONFLICT_STOP (never silently
  overwritten). --force allows overwriting NON-protected files and records
  backups; protected files (Makefile, AI_GUIDE.md, .gitignore) always stop.
- Same-version re-run is idempotent (all SKIP, no manifest rewrite, no nesting).
- Every successful apply writes .framework-manifest.json
  (framework_version, installed_at, per-file sha256).
- Mid-apply failure rolls back every file written in this run.
- Symlinks in the payload, path traversal, absolute paths and target escape
  are rejected before anything is written.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

FW = Path(__file__).resolve().parents[1]

PROTECTED = {"Makefile", "AI_GUIDE.md", ".gitignore", "README.md"}
MANIFEST = ".framework-manifest.json"
BACKUP_DIRNAME = ".framework-backup"

# (source relative to framework root, dest relative to target, install policy)
PAYLOAD_MAP = [
    (".cursor/rules", ".cursor/rules"),
    (".cursor/skills", ".cursor/skills"),
    ("loops", "loops"),
    ("scripts", "scripts"),
    ("contracts", "contracts"),
    ("tests", "tests"),
    ("docs", "docs"),
    (".codebuddy", ".codebuddy"),
    ("VERSION", "VERSION"),
    
    ("Makefile", "Makefile"),
    ("AI_GUIDE.md", "AI_GUIDE.md"),
    ("README.md", "README.framework.md"),
    (".env.example", ".env.example"),
    (".gitignore", ".gitignore"),
    (".security-allowlist", ".security-allowlist"),
    ("requirements.txt", "requirements.txt"),
    ("requirements.lock", "requirements.lock"),
    ("generated", "generated"),
    ("README.md", "README.md"),
]


class InstallError(RuntimeError):
    pass


@dataclass
class Entry:
    src: Path
    dest: Path
    rel: str
    sha256: str
    action: str = ""  # CREATE | UPDATE | SKIP | CONFLICT | OVERWRITE | REJECT


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def framework_version(fw: Path) -> str:
    v = fw / "VERSION"
    return v.read_text(encoding="utf-8").strip() if v.is_file() else "0.0.0-unknown"


def scan_payload(fw: Path) -> list[Entry]:
    entries: list[Entry] = []
    for src_rel, dest_rel in PAYLOAD_MAP:
        src = fw / src_rel
        if not src.exists():
            continue
        if src.is_symlink():
            raise InstallError(f"REJECT: symlink in payload: {src_rel}")
        if src.is_file():
            entries.append(Entry(src, Path(dest_rel), dest_rel, sha256_file(src)))
            continue
        for dirpath, dirnames, filenames in os.walk(src):
            dp = Path(dirpath)
            for d in list(dirnames):
                if (dp / d).is_symlink():
                    raise InstallError(f"REJECT: symlink in payload: {dp / d}")
                if d == "__pycache__":
                    dirnames.remove(d)
            for fn in filenames:
                fp = dp / fn
                if fp.is_symlink():
                    raise InstallError(f"REJECT: symlink in payload: {fp}")
                if fn.endswith((".pyc", ".pyo")):
                    continue
                rel_src = fp.relative_to(src)
                dest = Path(dest_rel) / rel_src
                entries.append(Entry(fp, dest, dest.as_posix(), sha256_file(fp)))
    return entries


def validate_paths(entries: list[Entry], target: Path) -> list[str]:
    errs = []
    treal = os.path.realpath(target)
    for e in entries:
        if e.dest.is_absolute():
            errs.append(f"REJECT: absolute dest path {e.dest}")
            continue
        if ".." in e.dest.parts:
            errs.append(f"REJECT: path traversal in {e.dest}")
            continue
        canon = os.path.realpath(target / e.dest)
        if not (canon == treal or canon.startswith(treal + os.sep)):
            errs.append(f"REJECT: target escape {e.dest}")
    return errs


def plan(entries: list[Entry], target: Path, force: bool) -> tuple[list[Entry], list[str]]:
    conflicts = []
    for e in entries:
        tp = target / e.dest
        if not tp.exists():
            e.action = "CREATE"
            continue
        if tp.is_symlink():
            e.action = "REJECT"
            conflicts.append(f"REJECT: existing symlink at {e.dest}")
            continue
        if not tp.is_file():
            e.action = "REJECT"
            conflicts.append(f"REJECT: {e.dest} exists and is not a regular file")
            continue
        cur = sha256_file(tp)
        if cur == e.sha256:
            e.action = "SKIP"
        elif e.dest.name in PROTECTED or str(e.dest) in PROTECTED:
            e.action = "CONFLICT"
            conflicts.append(
                f"CONFLICT_STOP: protected file differs: {e.dest} (merge manually)"
            )
        elif force:
            e.action = "OVERWRITE"
        else:
            e.action = "CONFLICT"
            conflicts.append(f"CONFLICT_STOP: {e.dest} differs (use --force to overwrite with backup)")
    return entries, conflicts


def print_plan(entries: list[Entry]) -> None:
    by_action: dict[str, list[str]] = {}
    for e in entries:
        by_action.setdefault(e.action, []).append(e.rel)
    for action in ("CREATE", "UPDATE", "OVERWRITE", "SKIP", "CONFLICT", "REJECT"):
        items = by_action.get(action, [])
        print(f"  {action:9s} {len(items):4d}  " + (", ".join(items[:6]) + (" …" if len(items) > 6 else "") if items else ""))


def apply(entries: list[Entry], target: Path, version: str) -> int:
    todo = [e for e in entries if e.action in ("CREATE", "UPDATE", "OVERWRITE")]
    if not todo:
        print("installer: already up to date (all SKIP) — no changes")
        return 0

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_root = target / BACKUP_DIRNAME / ts
    journal: list[tuple[Entry, Path | None]] = []  # (entry, backup_path or None)
    made_dirs: list[Path] = []
    try:
        for e in todo:
            dest = target / e.dest
            dest.parent.mkdir(parents=True, exist_ok=True)
            backup = None
            if dest.exists():
                backup_root.mkdir(parents=True, exist_ok=True)
                backup = backup_root / e.dest
                backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(dest, backup)
            fd, tmpname = tempfile.mkstemp(dir=str(dest.parent), prefix=".install-")
            with os.fdopen(fd, "wb") as fh:
                with e.src.open("rb") as sf:
                    shutil.copyfileobj(sf, fh)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmpname, dest)
            journal.append((e, backup))
    except Exception as exc:
        _rollback(target, journal)
        raise InstallError(f"APPLY failed, rolled back {len(journal)} file(s): {exc}")

    # VERIFY: re-hash everything we wrote
    bad = [e for e, _ in journal if sha256_file(target / e.dest) != e.sha256]
    if bad:
        _rollback(target, journal)
        raise InstallError(
            "VERIFY failed, rolled back: " + ", ".join(e.rel for e in bad)
        )

    manifest = {
        "framework_version": version,
        "installed_at": ts,
        "files": [
            {"path": e.rel, "sha256": e.sha256, "action": e.action} for e, _ in journal
        ],
        "backup_dir": str(backup_root.relative_to(target)) if backup_root.is_dir() else None,
    }
    (target / MANIFEST).write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"installer: applied {len(journal)} file(s); manifest -> {MANIFEST}")
    return 0


def _rollback(target: Path, journal: list[tuple[Entry, Path | None]]) -> None:
    for e, backup in reversed(journal):
        dest = target / e.dest
        try:
            if backup is not None and backup.is_file():
                shutil.copy2(backup, dest)
            else:
                dest.unlink(missing_ok=True)
        except OSError:
            pass
    # prune empty dirs we may have created (deepest first, stop at target)
    dirs = sorted(
        {(target / e.dest).parent for e, _ in journal},
        key=lambda p: len(p.parts),
        reverse=True,
    )
    for d in dirs:
        while d != target and d.is_dir():
            try:
                d.rmdir()
            except OSError:
                break
            d = d.parent


def main() -> int:
    ap = argparse.ArgumentParser(prog="installer")
    ap.add_argument("--target", required=True, type=Path)
    ap.add_argument("--mode", choices=["plan", "apply"], default="plan")
    ap.add_argument("--force", action="store_true",
                    help="overwrite non-protected conflicts (backups recorded)")
    ap.add_argument("--framework-root", type=Path, default=FW)
    args = ap.parse_args()

    fw = args.framework_root.resolve()
    target = args.target.resolve()
    if not target.is_dir():
        print(f"ERROR: {target} is not a directory", file=sys.stderr)
        return 2
    if target == fw or fw.is_relative_to(target) or target.is_relative_to(fw):
        print("ERROR: target must not be the framework root or contain/contained by it",
              file=sys.stderr)
        return 2

    version = framework_version(fw)
    try:
        entries = scan_payload(fw)
    except InstallError as e:
        print(str(e), file=sys.stderr)
        return 3

    path_errs = validate_paths(entries, target)
    if path_errs:
        for e in path_errs:
            print(e, file=sys.stderr)
        return 3

    entries, conflicts = plan(entries, target, args.force)
    print(f"installer PLAN (framework {version} -> {target}):")
    print_plan(entries)
    if conflicts:
        for c in conflicts:
            print(c)
        return 4
    if args.mode == "plan":
        print("mode=plan — nothing written. Re-run with --mode apply to install.")
        return 0

    try:
        return apply(entries, target, version)
    except InstallError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 5


if __name__ == "__main__":
    sys.exit(main())
