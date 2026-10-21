#!/usr/bin/env python3
"""Multi-contract registry — SSOT for all contract types.

Contract types: api, events, schema, semantic, ontology, rules,
skills, actions, evidence, evaluation.

Fail-closed rules:
- Every file under contracts/<type-dir>/ must be registered (unregistered -> FAIL).
- Registered contract path must exist and be non-empty.
- Duplicate contract id -> FAIL.
- depends_on must reference existing ids; cycles -> FAIL.
- version must be semver-like; layer must be domain|application|bff.
- registry.yaml is written as JSON-compatible YAML so it parses with
  PyYAML or a plain json fallback (zero-dependency dry-run).
"""
from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = "contracts/registry.yaml"

CONTRACT_TYPES = (
    "api",
    "events",
    "schema",
    "semantic",
    "ontology",
    "rules",
    "skills",
    "actions",
    "evidence",
    "evaluation",
)
LAYERS = ("domain", "application", "bff")
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.\-]+)?$")
# dirs/files inside contracts/ that are not contract payloads
NON_CONTRACT = {"_templates", "build", "README.md", "registry.yaml", ".gitkeep"}


class RegistryError(RuntimeError):
    pass


def _load_yaml_or_json(path: Path):
    from contract_runtime import load
    return load(path)


@dataclass
class Contract:
    id: str
    type: str
    version: str
    owner: str
    path: str
    layer: str = "domain"
    generator: str = ""
    checker: str = ""
    outputs: list = field(default_factory=list)
    depends_on: list = field(default_factory=list)
    compatibility: str = "compatible"


def contracts_dir(root: Path) -> Path:
    return root / "contracts"


def load_registry(root: Path) -> list[Contract]:
    reg_path = root / REGISTRY
    if not reg_path.is_file():
        raise RegistryError(f"MISSING_REGISTRY: {reg_path}")
    raw = _load_yaml_or_json(reg_path)
    if not isinstance(raw, dict) or raw.get("registry_version") != 1:
        raise RegistryError("INVALID_REGISTRY: registry_version: 1 required")
    out = []
    for i, item in enumerate(raw.get("contracts") or []):
        try:
            c = Contract(
                id=str(item["id"]),
                type=str(item["type"]),
                version=str(item["version"]),
                owner=str(item["owner"]),
                path=str(item["path"]),
                layer=str(item.get("layer", "domain")),
                generator=str(item.get("generator", "") or ""),
                checker=str(item.get("checker", "") or ""),
                outputs=list(item.get("outputs") or []),
                depends_on=list(item.get("depends_on") or []),
                compatibility=str(item.get("compatibility", "compatible")),
            )
        except KeyError as e:
            raise RegistryError(f"INVALID_REGISTRY_ENTRY[{i}]: missing {e}")
        out.append(c)
    return out


def _validate_entry(root: Path, c: Contract) -> list[str]:
    errs = []
    if c.type not in CONTRACT_TYPES:
        errs.append(f"{c.id}: unknown type '{c.type}' (allowed: {CONTRACT_TYPES})")
    if c.layer not in LAYERS:
        errs.append(f"{c.id}: unknown layer '{c.layer}' (allowed: {LAYERS})")
    if not SEMVER_RE.match(c.version):
        errs.append(f"{c.id}: version '{c.version}' is not semver-like")
    if not c.owner or "{{" in c.owner:
        errs.append(f"{c.id}: owner missing or unresolved")
    expected_prefix = f"{c.type}/"
    if Path(c.path).is_absolute() or ".." in Path(c.path).parts or not c.path.startswith(expected_prefix):
        errs.append(f"{c.id}: path '{c.path}' must live under contracts/{c.type}/")
    p = contracts_dir(root) / c.path
    if not p.resolve().is_relative_to(contracts_dir(root).resolve()):
        errs.append(f"{c.id}: contract path escapes root")
    if not p.is_file():
        errs.append(f"{c.id}: contract file MISSING: {p}")
    elif p.stat().st_size == 0:
        errs.append(f"{c.id}: contract file EMPTY: {p}")
    for dep_field, val in (("generator", c.generator), ("checker", c.checker)):
        if val:
            if Path(val).is_absolute() or ".." in Path(val).parts:
                errs.append(f"{c.id}: {dep_field} path escapes root: {val}")
    for out in c.outputs:
        if not isinstance(out, str) or not out.startswith("generated/") or ".." in Path(out).parts or Path(out).is_absolute():
            errs.append(f"{c.id}: output must stay under generated/: {out}")
    if c.generator and not c.outputs:
        errs.append(f"{c.id}: generator requires outputs")
    if c.outputs and not c.generator:
        errs.append(f"{c.id}: outputs require generator")
    return errs


def _detect_cycles(contracts: list[Contract]) -> list[str]:
    ids = {c.id for c in contracts}
    errs = []
    graph = {}
    for c in contracts:
        for d in c.depends_on:
            if d not in ids:
                errs.append(f"{c.id}: depends_on references unknown id '{d}'")
            if d == c.id:
                errs.append(f"{c.id}: self dependency")
        graph[c.id] = [d for d in c.depends_on if d in ids]

    WHITE, GRAY, BLACK = 0, 1, 2
    color = {i: WHITE for i in graph}

    def dfs(n, stack):
        color[n] = GRAY
        for m in graph.get(n, []):
            if color[m] == GRAY:
                errs.append("cycle: " + " -> ".join(stack + [n, m]))
            elif color[m] == WHITE:
                dfs(m, stack + [n])
        color[n] = BLACK

    for n in graph:
        if color[n] == WHITE:
            dfs(n, [])
    return errs


def _unregistered_files(root: Path, contracts: list[Contract]) -> list[str]:
    registered = {c.path for c in contracts}
    errs = []
    base = contracts_dir(root)
    if not base.is_dir():
        return errs
    for t in CONTRACT_TYPES:
        tdir = base / t
        if not tdir.is_dir():
            continue
        for f in sorted(tdir.rglob("*")):
            if not f.is_file() or f.name in NON_CONTRACT:
                continue
            rel = f.relative_to(base).as_posix()
            if rel not in registered:
                errs.append(f"UNREGISTERED_CONTRACT: {rel} (register in {REGISTRY})")
    return errs


def validate_registry(root: Path) -> tuple[list[Contract], list[str]]:
    """Returns (contracts, errors). Never raises for content problems."""
    try:
        contracts = load_registry(root)
    except (RegistryError, json.JSONDecodeError) as e:
        return [], [str(e)]
    except Exception as e:  # yaml parser errors etc.
        return [], [f"INVALID_REGISTRY: {e}"]
    errs: list[str] = []
    if not contracts:
        errs.append("EMPTY_REGISTRY")
    outputs = [o for c in contracts for o in c.outputs]
    if len(outputs) != len(set(outputs)):
        errs.append("DUPLICATE_OUTPUT")
    seen = set()
    for c in contracts:
        if c.id in seen:
            errs.append(f"DUPLICATE_ID: {c.id}")
        seen.add(c.id)
        errs.extend(_validate_entry(root, c))
    errs.extend(_detect_cycles(contracts))
    errs.extend(_unregistered_files(root, contracts))
    return contracts, errs


def sha256_file(path: Path) -> str:
    import hashlib

    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


if __name__ == "__main__":
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT
    cs, errors = validate_registry(root)
    for e in errors:
        print(f"FAIL: {e}")
    if errors:
        sys.exit(1)
    print(f"registry OK: {len(cs)} contract(s)")
