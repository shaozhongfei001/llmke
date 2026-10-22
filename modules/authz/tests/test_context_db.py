"""授权过滤在 SQL 层生效：真库验证 E1（同 KB 不同文件）与证据同等过滤。

关键点：断言的是"数据库返回了几行"，而不是"Python 里筛掉了几个"——
后者证明不了"进入 LLM 之前已过滤"。
"""
from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from modules.authz import compile_chunk_predicate, compile_evidence_predicate, validate_context

ROOT = Path(__file__).resolve().parents[3]
SOCKET = Path(os.environ.get("LLMKE_MYSQL_SOCKET", "/tmp/mysql-probe/mysql.sock"))
MYSQL = shutil.which("mysql")
SCHEMA = ROOT / "docs/baseline/validation/artifacts/schema-v1.3.sql"
DB = os.environ.get("LLMKE_CI_AUTHZ_DB", "llmke_ci_authz")

DOC = "第一段内容。第二段内容。"
CH = hashlib.sha256(DOC.encode()).hexdigest()
FUTURE = (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()

pytestmark = pytest.mark.skipif(
    MYSQL is None or not SOCKET.exists(),
    reason="需要本机 MySQL 独立实例（coordination/mysql-probe.sh start）与 mysql 客户端",
)


def sql(statement: str, *, database: str | None = DB) -> str:
    cmd = [MYSQL, f"--socket={SOCKET}", "-uroot", "-N", "-B", "-e", statement]
    if database:
        cmd.insert(3, database)
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if p.returncode != 0:
        raise AssertionError(f"SQL 失败: {statement[:80]}...\n{p.stderr.strip()}")
    return p.stdout.strip()


@pytest.fixture(scope="module")
def db():
    sql("SELECT 1", database=None)
    sql(f"DROP DATABASE IF EXISTS `{DB}`", database=None)
    sql(f"CREATE DATABASE `{DB}` CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci", database=None)
    with SCHEMA.open("rb") as fh:
        p = subprocess.run([MYSQL, f"--socket={SOCKET}", "-uroot", DB],
                           stdin=fh, capture_output=True, timeout=120)
    assert p.returncode == 0, p.stderr.decode()[:400]

    rows = []
    for i, (fid, cid) in enumerate((("f-1", "c1"), ("f-1", "c2"), ("f-2", "c3"))):
        start, end = 0, 6
        text = DOC[start:end]
        th = hashlib.sha256(text.encode()).hexdigest()
        rows.append(
            "INSERT INTO document_chunk (chunk_id,kb_id,file_id,document_version,chunk_index,"
            "offset_start,offset_end,offset_unit,text,text_hash,content_hash,parser_version,"
            "chunk_strategy,created_at,created_by) VALUES "
            f"('{cid}','kb-1','{fid}','v3',{i},0,6,'unicode_codepoint','{text}','{th}','{CH}',"
            f"'p-1','S1',NOW(3),'ci')")
        rows.append(
            "INSERT INTO document_evidence (evidence_id,kb_id,file_id,document_version,chunk_id,"
            "content_hash,offset_start,offset_end,offset_unit,text_hash,parser_version,created_at,"
            f"created_by) VALUES ('ev-{cid}','kb-1','{fid}','v3','{cid}','{CH}',0,6,"
            f"'unicode_codepoint','{th}','p-1',NOW(3),'ci')")
    for stmt in rows:
        sql(stmt)
    try:
        yield DB
    finally:
        sql(f"DROP DATABASE IF EXISTS `{DB}`", database=None)


def ctx(**over):
    base = {"request_id": "r", "principal_id": "u", "service": "qa",
            "kb_scope": ["kb-1"], "file_scope": {"kb-1": ["f-1"]},
            "authz_version": 1, "expires_at": FUTURE}
    base.update(over)
    return base


def test_e1_chunk_query_returns_only_authorized_file(db):
    c = validate_context(ctx())
    out = sql(f"SELECT chunk_id,file_id FROM document_chunk WHERE {compile_chunk_predicate(c, 'kb-1')} "
              "ORDER BY chunk_id")
    rows = [r.split("\t") for r in out.splitlines() if r]
    assert rows, "应至少返回授权文件的块"
    assert {r[1] for r in rows} == {"f-1"}, f"出现了未授权文件：{rows}"


def test_e1_evidence_query_returns_only_authorized_file(db):
    c = validate_context(ctx())
    out = sql(f"SELECT evidence_id,file_id FROM document_evidence "
              f"WHERE {compile_evidence_predicate(c, 'kb-1')} ORDER BY evidence_id")
    files = {r.split("\t")[1] for r in out.splitlines() if r}
    assert files == {"f-1"}


def test_wildcard_scope_returns_all_files(db):
    c = validate_context(ctx(file_scope={"kb-1": "*"}))
    out = sql(f"SELECT DISTINCT file_id FROM document_chunk WHERE {compile_chunk_predicate(c, 'kb-1')}")
    assert {r for r in out.splitlines() if r} == {"f-1", "f-2"}


def test_e3_neighbor_expansion_cannot_cross_file(db):
    """扩展相邻块时若加上同一谓词，就不可能跨文件。"""
    c = validate_context(ctx())
    pred = compile_chunk_predicate(c, "kb-1")
    rows = sql(f"SELECT file_id FROM document_chunk WHERE {pred} AND chunk_index BETWEEN 0 AND 5")
    assert set(rows.splitlines()) | {"f-1"} == {"f-1"}
