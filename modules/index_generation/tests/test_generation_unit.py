"""索引代次机制：状态机与 SQL 构造的单元用例（不做 IO）。"""
import pytest

from modules.index_generation import (GenerationError, acquire_lease_sql,
                                      activation_cas_sql, assert_ready_to_activate,
                                      assert_transition, rollback_cas_sql, write_guard_sql)


def test_legal_and_illegal_transitions():
    assert_transition("BUILDING", "VALIDATING")
    assert_transition("READY", "ACTIVE")
    assert_transition("ACTIVE", "RETIRED")
    for src, dst in (("BUILDING", "ACTIVE"), ("READY", "RETIRED"), ("RETIRED", "ACTIVE"),
                     ("ABORTED", "BUILDING")):
        with pytest.raises(GenerationError) as e:
            assert_transition(src, dst)
        assert e.value.code == "ILLEGAL_TRANSITION"


def test_ready_requires_all_physical_locations():
    with pytest.raises(GenerationError) as e:
        assert_ready_to_activate("READY", {"vector": "x", "es": "y", "graph": "z"})
    assert e.value.code == "LOCATION_MISSING"

    with pytest.raises(GenerationError):
        assert_ready_to_activate("BUILDING", {k: "x" for k in ("vector", "es", "graph", "fulltext")})

    assert_ready_to_activate("READY", {k: "x" for k in ("vector", "es", "graph", "fulltext")})


def test_activation_sql_is_cas_on_expected_value():
    sql = activation_cas_sql("kb-1", 7, 6, "ops")
    assert "WHERE kb_id = 'kb-1' AND generation_id = 6" in sql
    assert "generation_id = 7" in sql
    assert "previous_generation_id = generation_id" in sql


def test_activation_sql_first_time_uses_is_null():
    assert "generation_id IS NULL" in activation_cas_sql("kb-1", 1, None, "ops")


def test_rollback_requires_previous():
    sql = rollback_cas_sql("kb-1", 7, "ops")
    assert "previous_generation_id IS NOT NULL" in sql
    # 必须自连接读快照：直接交换两列会因 MySQL 从左到右求值而双写成旧代（实测）
    assert "a.generation_id = t.prev_gen" in sql and "a.previous_generation_id = t.cur_gen" in sql


def test_write_guard_injects_token_condition():
    sql = write_guard_sql("kb-1", 7, 3, "document_chunk", "state='ACTIVE'", "chunk_id='c-1'")
    assert "chunk_id='c-1'" in sql
    assert "3 = lease_token" in sql and "expires_at >= NOW(3)" in sql


def test_write_guard_requires_row_predicate():
    """没有行谓词就会全表更新——这是实测踩到的错误，必须由接口阻止。"""
    with pytest.raises(GenerationError) as e:
        write_guard_sql("kb-1", 7, 3, "document_chunk", "state='ACTIVE'", "  ")
    assert e.value.code == "ROW_PREDICATE_REQUIRED"


def test_write_guard_rejects_suspicious_table_name():
    with pytest.raises(GenerationError):
        write_guard_sql("kb-1", 7, 3, "chunk; DROP TABLE x", "a=1", "id=1")


def test_lease_sql_increments_monotonically():
    upd, ins = acquire_lease_sql("kb-1", 7, "worker-a", 60)
    assert "lease_token = lease_token + 1" in upd
    assert "expires_at < NOW(3) OR owner = 'worker-a'" in upd
    assert "VALUES ('kb-1',7,1,'worker-a'" in ins
