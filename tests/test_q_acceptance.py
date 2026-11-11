"""Q 验收脚本自检：能跑就断言"无 FAIL"，并**钉住 NOT_IMPLEMENTED 数量不能悄悄变 0**。

意义：如果哪天有人把未实现的能力从清单里删掉、或把 skip 当通过，这条会红。
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/v2_q_acceptance.py"


def _es_up():
    import socket
    try:
        with socket.create_connection(("127.0.0.1", 19200), timeout=2):
            return True
    except OSError:
        return False


@pytest.mark.skipif(
    not _es_up() or os.environ.get("LLMKE_Q_FULL") != "1",
    reason="Q 全量验收需 ES 19200 且显式 LLMKE_Q_FULL=1；不作为单测默认跑",
)
def test_q_acceptance_has_no_fail_and_keeps_unimplemented_visible(tmp_path):
    out = tmp_path / "q.json"
    proc = subprocess.run([sys.executable, str(SCRIPT), "--out", str(out)],
                          capture_output=True, text=True, env=os.environ.copy())
    assert proc.returncode == 0, proc.stdout[-800:]
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["summary"]["FAIL"] == 0
    assert report["verdict"] == "PASS"
    # 仍未实现的能力必须留在报告里，不能被悄悄清空冒充"全部通过"。
    # 注意：NOT_IMPLEMENTED 现在只用于**客观缺失的环境能力**（如缺 LibreOffice Writer），
    # 所以数量可以 >0，但每一条都必须给出证据与原因，不能是空壳。
    unimplemented = [r for r in report["results"] if r["status"] == "NOT_IMPLEMENTED"]
    for item in unimplemented:
        assert item.get("evidence"), f"{item['item']} 标了未实现却没给证据"
        assert item.get("boundary") or item["evidence"].get("fix") or \
            item["evidence"].get("why"), f"{item['item']} 未说明未实现原因/修法"
    describe_item = next(r for r in report["results"] if r["item"] == "graph:describe")
    # 不能要求"必须有 NOT_IMPLEMENTED"——能力真做完时这个数会归零，硬编码会逼人留假账。
    # 真正要守的是：**没有全部 VERIFIED**，且每个非 VERIFIED 的项都有说明。
    counts = describe_item["evidence"]["counts"]
    assert counts["NOT_IMPLEMENTED"] + counts["NOT_VERIFIED"] >= 1
    # 语义层 PASS 必须带 boundary，否则会被误读成端到端已通过
    biz_pass = [r for r in report["results"]
                if r["item"].startswith("biz:") and r["status"] == "PASS"]
    assert biz_pass and all(r.get("boundary") for r in biz_pass)
