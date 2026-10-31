"""A2 冒烟脚本的自检：没有 MinerU 环境时必须**跳过**，不能把"没装"伪装成"通过"。

真正跑模型的是 scripts/v2_mineru_smoke.py；这里只保证：
- 没有 CLI / 没有配置时返回明确状态码（NO_MINERU_CLI / NO_CONFIG_ENV），而不是抛异常或假成功；
- 有环境时才跑真实扫描件（默认跳过，避免 CI 每轮都加载 1.9 GB 权重）。
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/v2_mineru_smoke.py"
PDF = ROOT / "platform/r12/parse/fixtures/generated/cn-scan.pdf"
MINERU_PY = os.environ.get("V2_MINERU_PYTHON", "/home/szf/data/dev/mineru-toolenv/bin/python")
CONFIG = os.environ.get("MINERU_TOOLS_CONFIG_JSON", "/home/szf/data/dev/models/mineru/magic-pdf.json")


def _run(args, env=None):
    proc = subprocess.run([sys.executable, str(SCRIPT)] + args, capture_output=True,
                          text=True, env={**os.environ, **(env or {})})
    return proc


def test_missing_cli_is_reported_not_faked(tmp_path):
    proc = _run(["--pdf", str(PDF), "--magic-pdf", str(tmp_path / "nope")])
    assert proc.returncode == 2
    assert "NO_MINERU_CLI" in proc.stdout


def test_missing_config_env_is_reported(tmp_path, monkeypatch):
    monkeypatch.delenv("MINERU_TOOLS_CONFIG_JSON", raising=False)
    proc = _run(["--pdf", str(PDF), "--magic-pdf", sys.executable])
    assert proc.returncode == 2
    assert "NO_CONFIG_ENV" in proc.stdout


@pytest.mark.skipif(not (os.path.isfile(MINERU_PY) and os.path.isfile(CONFIG)),
                    reason="本机没有 MinerU 环境或配置，跳过真实 OCR（不伪装通过）")
def test_real_scan_extracts_chinese_text(tmp_path):
    out = tmp_path / "smoke.json"
    proc = subprocess.run(
        [MINERU_PY, str(SCRIPT), "--pdf", str(PDF), "--expect", "授信审批意见通知书", "5000 万元",
         "--out", str(out)],
        capture_output=True, text=True,
        env={**os.environ, "MINERU_TOOLS_CONFIG_JSON": CONFIG, "HF_HUB_OFFLINE": "1"})
    assert proc.returncode == 0, proc.stdout[-800:] + proc.stderr[-800:]
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["status"] == "OK"
    assert report["missing"] == []
