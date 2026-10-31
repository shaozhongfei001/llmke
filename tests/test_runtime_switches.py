"""开关登记与代码默认值必须一致（防止文档漂移成"写了但没生效"）。"""

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services/rag-alg/alg_retrieval_service/app"))

from projection_read import DEFAULT_MODE, DEFAULT_PREFIX, MODES  # noqa: E402


def _registry():
    doc = yaml.safe_load((ROOT / "docs/policies/RUNTIME-SWITCHES.yaml").read_text(encoding="utf-8"))
    return {s["key"]: s for s in doc["switches"]}


def test_registry_defaults_match_code():
    reg = _registry()
    assert reg["INGEST_READ_MODE"]["default"] == DEFAULT_MODE
    assert tuple(reg["INGEST_READ_MODE"]["values"]) == MODES
    assert reg["INGEST_READ_PREFIX"]["default"] == DEFAULT_PREFIX


def test_every_switch_has_rollback_and_scope():
    for key, spec in _registry().items():
        assert spec.get("rollback"), key
        assert spec.get("scope"), key
        assert spec.get("module"), key
