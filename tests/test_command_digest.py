"""门禁命令闭包（scheme=4）：被执行的脚本变了，旧证据必须失效。

为什么需要这条
    `docs/baseline/validation/` 是冻结排除前缀，但其中的脚本会被当门禁命令执行。
    实测（R9-T13）：改 `schema-verify.sh` 时 control/code/doc 三个摘要都不变，旧证据仍 PASS。
    也就是说：旧摘要能证明"树没变"，证明不了"当初用来验证的脚本没变"。

本文件锁两件事：
    1. 闭包摘要确实随脚本内容变化（单元）；
    2. 端到端：跑完门禁后改脚本，`evidence-check` 必须 FAIL 且指出 `gate command changed`。
"""
from __future__ import annotations

import sys
from pathlib import Path

import fixture_helpers as fh
from baseline_support import DIGEST_SCHEME, command_digest, command_files
from fixture_helpers import devpass, dump, guard, load, make_loop
from freeze_baseline import run as freeze


def test_command_digest_tracks_script_content(tmp_path):
    script = tmp_path / "gate.sh"
    script.write_text("#!/bin/bash\nexit 0\n", encoding="utf-8")
    argv = ["bash", str(script)]
    before = command_digest(argv, tmp_path)
    assert before != ""

    script.write_text("#!/bin/bash\nexit 0\n# changed\n", encoding="utf-8")
    after = command_digest(argv, tmp_path)
    assert after != before, "脚本内容变化后摘要必须变化"


def test_empty_closure_is_empty_not_pass():
    """没有仓内脚本时返回空串：表示"无对象可绑定"，不是"通过"。"""
    assert command_files(["make", "framework-verify"], Path(".")) == []
    assert command_digest(["make", "framework-verify"], Path(".")) == ""


def test_gate_command_change_invalidates_evidence(tmp_path):
    """端到端：门禁脚本位于排除前缀时，old digests 看不出变化，scheme=4 必须看出。"""
    root, d = make_loop(tmp_path)
    ext = root / "docs/baseline/validation/probe.sh"
    ext.parent.mkdir(parents=True, exist_ok=True)
    ext.write_text("#!/bin/bash\nexit 0\n", encoding="utf-8")
    ext.chmod(0o755)

    argv = ["bash", "docs/baseline/validation/probe.sh"]
    catalog = load(root / "docs/policies/GATE-CATALOG.yaml")
    catalog["gates"]["fixture.dev"]["argv"] = argv
    dump(root / "docs/policies/GATE-CATALOG.yaml", catalog)

    loop = load(d / "LOOP.yaml")
    for g in loop["gates"]:
        if g["id"] == "repo_structure_gate":
            g["argv"] = argv
    dump(d / "LOOP.yaml", loop)
    freeze(root, write=True)

    assert DIGEST_SCHEME >= 4, "本用例需要 scheme>=4"
    p = guard(root, "run-gate", "--loop", "T1", "--gate", "repo_structure_gate",
              "--executor", "dev-1")
    assert p.returncode == 0, p.stdout + p.stderr

    ok = guard(root, "evidence-check", "--loop", "T1")
    assert ok.returncode == 0, ok.stdout + ok.stderr

    # 改脚本（语义无关的一行），旧摘要不会变；scheme=4 必须判失效
    ext.write_text("#!/bin/bash\nexit 0\n# tampered\n", encoding="utf-8")
    bad = guard(root, "evidence-check", "--loop", "T1")
    assert bad.returncode != 0, "门禁脚本被改却仍判有效"
    assert "gate command changed" in bad.stdout, bad.stdout
