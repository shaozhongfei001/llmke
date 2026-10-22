"""授权上下文：结构校验、SQL 谓词编译、图检索降级（不做 IO）。"""
from datetime import datetime, timedelta, timezone

import pytest

from modules.authz import (AuthZError, can_use_graph, compile_chunk_predicate,
                           compile_evidence_predicate, files_for, validate_context)

FUTURE = (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()


def ctx(**over):
    base = {
        "request_id": "r-1", "principal_id": "u-1", "service": "rag-qa-service",
        "kb_scope": ["kb-1"], "file_scope": {"kb-1": ["f-1"]},
        "authz_version": 3, "expires_at": FUTURE,
    }
    base.update(over)
    return base


def test_valid_context_passes():
    assert validate_context(ctx())["principal_id"] == "u-1"


def test_missing_context_is_rejected_not_anonymous():
    """E6 基础：没有上下文必须拒绝，不能按空权限继续。"""
    with pytest.raises(AuthZError) as e:
        validate_context(None)
    assert e.value.code == "CONTEXT_MISSING"


def test_expired_context_rejected():
    past = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
    with pytest.raises(AuthZError) as e:
        validate_context(ctx(expires_at=past))
    assert e.value.code == "CONTEXT_EXPIRED"


def test_empty_scopes_rejected():
    for bad, code in ((ctx(kb_scope=[]), "KB_SCOPE_EMPTY"),
                      (ctx(file_scope={}), "FILE_SCOPE_EMPTY"),
                      (ctx(file_scope={"kb-1": []}), "FILE_SCOPE_EMPTY"),
                      (ctx(kb_scope=None), "KB_SCOPE_EMPTY")):
        with pytest.raises(AuthZError) as e:
            validate_context(bad)
        assert e.value.code == code


def test_kb_not_in_scope_rejected():
    with pytest.raises(AuthZError) as e:
        files_for(ctx(), "kb-2")
    assert e.value.code == "KB_NOT_AUTHORIZED"


def test_predicate_limits_to_authorized_files():
    """E1 的判据：谓词里必须出现 file_id IN (...) —— 过滤发生在取数阶段。"""
    sql = compile_chunk_predicate(ctx(), "kb-1")
    assert "kb_id = 'kb-1'" in sql
    assert "file_id IN ('f-1')" in sql


def test_wildcard_kb_has_no_file_filter():
    sql = compile_chunk_predicate(ctx(file_scope={"kb-1": "*"}), "kb-1")
    assert sql == "kb_id = 'kb-1'"


def test_evidence_predicate_also_filtered():
    """证据同样会进 Prompt，不能豁免。"""
    assert "file_id IN ('f-1')" in compile_evidence_predicate(ctx(), "kb-1")


def test_graph_disabled_for_file_level_scope():
    """§4 降级：文件级授权不允许走图（技术上也做不到隔离）。"""
    assert can_use_graph(ctx(), "kb-1") is False
    assert can_use_graph(ctx(file_scope={"kb-1": "*"}), "kb-1") is True


def test_identifier_injection_blocked():
    with pytest.raises(AuthZError) as e:
        compile_chunk_predicate(ctx(file_scope={"kb-1": ["f-1' OR '1'='1"]}), "kb-1")
    assert e.value.code in {"BAD_FILE_ID", "BAD_ID"}
