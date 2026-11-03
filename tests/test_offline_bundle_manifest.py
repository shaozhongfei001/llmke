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
    if doc.get("schema") != "llmke.offline-bundle.v1":
        pytest.skip("not a wheel bundle manifest")
    assert doc["schema"] == "llmke.offline-bundle.v1"
    files = doc["wheels"]
    assert doc["file_count"] == len(files) > 0
    assert doc["wheel_count"] + doc["sdist_count"] == doc["file_count"]
    assert doc["total_bytes"] == sum(w["bytes"] for w in files)
    for wheel in files:
        assert wheel["kind"] in ("wheel", "sdist"), wheel
        assert wheel["file"].endswith((".whl", ".tar.gz", ".zip")), wheel
        assert SHA.match(wheel["sha256"]), wheel
        assert wheel["bytes"] > 0
    # 清单里不允许出现同一文件名两次（同名不同内容会让"照清单装"产生歧义）
    names = [w["file"] for w in doc["wheels"]]
    assert len(names) == len(set(names))


@pytest.mark.parametrize("manifest_path", MANIFESTS, ids=lambda p: p.name)
def test_requirements_copy_matches_manifest_hash(manifest_path):
    doc = json.loads(manifest_path.read_text(encoding="utf-8"))
    if doc.get("schema") != "llmke.offline-bundle.v1":
        pytest.skip("not a wheel bundle manifest")
    req = manifest_path.parent / doc["requirements"]["path"]
    assert req.is_file(), f"清单同级缺少冻结清单: {req}"
    assert _sha256(req) == doc["requirements"]["sha256"], "冻结清单被改过但未重新打包"


IMAGE_MANIFESTS = sorted(OFFLINE.glob("*.images.manifest.json")) or \
    sorted(p for p in OFFLINE.glob("*.manifest.json") if "image" in p.name)


@pytest.mark.parametrize("manifest_path", IMAGE_MANIFESTS, ids=lambda p: p.name)
def test_image_manifest_is_self_consistent(manifest_path):
    doc = json.loads(manifest_path.read_text(encoding="utf-8"))
    if doc.get("schema") != "llmke.image-bundle.v1":
        pytest.skip("not an image manifest")
    assert doc["images"], "镜像清单为空"
    assert doc["total_bytes"] == sum(i["bytes"] for i in doc["images"])
    for image in doc["images"]:
        assert image["image"].count(":") >= 1, image      # 必须带 tag
        assert image["file"].endswith(".tar"), image
        assert SHA.match(image["sha256"]), image
    assert not doc.get("untracked_tars"), doc.get("untracked_tars")
