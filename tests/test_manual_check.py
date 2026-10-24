"""人工验证命令绑定：改脚本必须让证据失效（补 command_digest 的覆盖缺口）。"""
from __future__ import annotations

from fixture_helpers import dump, guard, load, make_loop
from freeze_baseline import run as freeze


def _setup(tmp_path):
    root, d = make_loop(tmp_path)
    script = root / 'docs/baseline/validation/manual.sh'
    script.parent.mkdir(parents=True, exist_ok=True)
    script.write_text('#!/bin/bash\nexit 0\n', encoding='utf-8')
    script.chmod(0o755)
    freeze(root, write=True)
    return root, d, script


def test_record_check_ok_then_tamper_script_fails(tmp_path):
    root, d, script = _setup(tmp_path)
    p = guard(root, 'record-check', '--loop', 'T1', '--name', 'schema',
              '--executor', 'dev-1', '--argv', 'bash', 'docs/baseline/validation/manual.sh')
    assert p.returncode == 0, p.stdout + p.stderr
    assert guard(root, 'evidence-check', '--loop', 'T1').returncode == 0

    script.write_text('#!/bin/bash\nexit 0\n# tampered\n', encoding='utf-8')
    bad = guard(root, 'evidence-check', '--loop', 'T1')
    assert bad.returncode != 0 and 'manual check schema: command changed' in bad.stdout


def test_record_check_nonzero_exit_invalidates(tmp_path):
    root, d, script = _setup(tmp_path)
    script.write_text('#!/bin/bash\nexit 3\n', encoding='utf-8')
    p = guard(root, 'record-check', '--loop', 'T1', '--name', 'schema',
              '--executor', 'dev-1', '--argv', 'bash', 'docs/baseline/validation/manual.sh')
    assert p.returncode != 0
    bad = guard(root, 'evidence-check', '--loop', 'T1')
    assert bad.returncode != 0 and 'exit 3' in bad.stdout


def test_manual_log_tamper_detected(tmp_path):
    root, d, script = _setup(tmp_path)
    guard(root, 'record-check', '--loop', 'T1', '--name', 'schema',
          '--executor', 'dev-1', '--argv', 'bash', 'docs/baseline/validation/manual.sh')
    (d / 'evidence/manual-schema.log').write_text('forged\n', encoding='utf-8')
    bad = guard(root, 'evidence-check', '--loop', 'T1')
    assert bad.returncode != 0 and 'evidence hash mismatch' in bad.stdout
