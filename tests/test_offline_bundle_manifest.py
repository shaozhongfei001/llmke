"""离线包清单自洽性（不需要 wheel 本体也能校验，保证仓库里那份清单是可信的）。"""

import hashlib
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
OFFLINE = ROOT / "docs/design/unified-documents-v2/offline"
MANIFESTS = sorted(OFFLINE.glob("*.manifest.json"))
SHA = re.compile(r"^[0-9a-f]{64}$")


def _sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


@pytest.mark.parametrize("manifest_path", MANIFESTS, ids=lambda p: p.name)
def test_manifest_is_self_consistent(manifest_path):
    doc = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert doc["schema"] == "llmke.offline-bundle.v1"
    assert doc["wheel_count"] == len(doc["wheels"]) > 0
    assert doc["total_bytes"] == sum(w["bytes"] for w in doc["wheels"])
    for wheel in doc["wheels"]:
        assert wheel["file"].endswith(".whl"), wheel
        assert SHA.match(wheel["sha256"]), wheel
        assert wheel["bytes"] > 0
    # 清单里不允许出现同一文件名两次（同名不同内容会让"照清单装"产生歧义）
    names = [w["file"] for w in doc["wheels"]]
    assert len(names) == len(set(names))


@pytest.mark.parametrize("manifest_path", MANIFESTS, ids=lambda p: p.name)
def test_requirements_copy_matches_manifest_hash(manifest_path):
    doc = json.loads(manifest_path.read_text(encoding="utf-8"))
    req = manifest_path.parent / doc["requirements"]["path"]
    assert req.is_file(), f"清单同级缺少冻结清单: {req}"
    assert _sha256(req) == doc["requirements"]["sha256"], "冻结清单被改过但未重新打包"
