"""租约表迁移脚本与代码里的 DDL 不许漂移。

生产 DDL 权限收紧后，建表由 DBA 执行 `sql/002_rebuild_lease.sql`；
如果代码改了 DDL 而 SQL 没改，部署时会出现"本地能跑、线上列缺失"。
"""

import os
import re

from graph_engine_adapter.lease_mysql import DDL

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SQL = os.path.join(REPO, "services", "rag-alg", "index_data_service",
                   "graph_engine_adapter", "sql", "002_rebuild_lease.sql")


def _statements(text):
    """去掉注释与空行，只留可执行语句（分号结尾归一）。"""
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("--"):
            continue
        lines.append(stripped)
    return " ".join(lines).replace(" ;", ";").strip()


def _flat(text):
    """比较前统一空白：换行/缩进不是语义，列顺序与字面才是。"""
    return re.sub(r"\s+", " ", text).strip().rstrip(";").strip()


def test_sql_file_matches_code_ddl():
    with open(SQL, encoding="utf-8") as fh:
        sql = _statements(fh.read())
    assert _flat(sql) == _flat(DDL)


def test_sql_declares_primary_key_on_lease_key():
    """没有主键就没有 `SELECT ... FOR UPDATE` 的行锁语义，多实例互斥不成立。"""
    with open(SQL, encoding="utf-8") as fh:
        text = fh.read()
    assert "PRIMARY KEY (lease_key)" in text
    assert "fencing" in text and "expires_at" in text


def test_sql_is_idempotent():
    """DBA 可能重复执行；没有 IF NOT EXISTS 会在第二次直接失败。"""
    with open(SQL, encoding="utf-8") as fh:
        assert "CREATE TABLE IF NOT EXISTS" in fh.read()
