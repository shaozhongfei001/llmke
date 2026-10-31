"""安全扫描规则：既要能抓到硬编码凭据，也不能把"调用表达式"当凭据。

回归的是真实误报：`self._tokens = min(a, b)` 被值正则按逗号截断成 `min(a`，
`CALL_RE`（要求以 `(` 结尾）失配 → 报成 REAL_CREDENTIAL。团队因此把属性改名绕开扫描，
这属于"工具逼人改代码"，修工具才是对的。
"""

import importlib.util
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPEC = importlib.util.spec_from_file_location(
    "security_scan", os.path.join(REPO, "scripts", "security_scan.py"))
scan = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(scan)


def findings_for(tmp_path, name, text):
    path = tmp_path / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return scan.scan_file(path, tmp_path, [])


def test_call_expression_is_not_a_credential(tmp_path):
    """`min(a, b)` / `env("X")` / `os.environ["X"]` 都不是字面量。"""
    body = (
        "self._tokens = min(a, b)\n"
        "key = env(\"DSEEK\")\n"
        "other_token = os.environ[\"TOKEN\"]\n"
    )
    assert findings_for(tmp_path, "a.py", body) == []


def test_quoted_literal_is_still_caught(tmp_path):
    """收紧误报不能把真阳性一起放走。"""
    found = findings_for(tmp_path, "b.py", 'password = "hunter2"\n')
    assert len(found) == 1 and "REAL_CREDENTIAL" in found[0]


def test_placeholder_is_skipped(tmp_path):
    found = findings_for(tmp_path, "c.yaml", 'password: "${DB_PASSWORD}"\n')
    assert found == []


def test_bare_identifier_is_skipped(tmp_path):
    assert findings_for(tmp_path, "d.py", "password = password\n") == []
