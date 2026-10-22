"""切片 E：授权 -> 取块 -> 证据 的组合验证（真库）。

证明三件事：
1. 取块 SQL 恒带授权谓词，chunk_ids 只能收窄不能放宽；
2. 越权块被**显式拒绝**（不是静默丢弃）；
3. 从库里的块产出的证据能过契约，且 hash 与原文一致。
"""
from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from modules.authz import AuthZError, validate_context
from modules.citation_flow import (assert_chunks_in_scope, build_evidences_from_chunks,
                                   fetch_chunks_sql, rows_to_chunks)
from modules.citation_evidence.assembler import validate_evidence

ROOT = Path(__file__).resolve().parents[3]
SOCKET = Path(os.environ.get("LLMKE_MYSQL_SOCKET", "/tmp/mysql-probe/mysql.sock"))
MYSQL = shutil.which("mysql")
SCHEMA = ROOT / "docs/baseline/validation/artifacts/schema-v1.3.sql"
DB = os.environ.get("LLMKE_CI_FLOW_DB", "llmke_ci_flow")

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
    return p.stdout.rstrip("\n")


@pytest.fixture(scope="module")
def db():
    sql("SELECT 1", database=None)
    sql(f"DROP DATABASE IF EXISTS `{DB}`", database=None)
    sql(f"CREATE DATABASE `{DB}` CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci", database=None)
    with SCHEMA.open("rb") as fh:
        p = subprocess.run([MYSQL, f"--socket={SOCKET}", "-uroot", DB],
                           stdin=fh, capture_output=True, timeout=120)
    assert p.returncode == 0, p.stderr.decode()[:400]
    for i, (fid, cid, s, e) in enumerate((("f-1", "k1", 0, 6), ("f-2", "k2", 6, 12))):
        text = DOC[s:e]
        th = hashlib.sha256(text.encode()).hexdigest()
        sql("INSERT INTO document_chunk (chunk_id,kb_id,file_id,document_version,chunk_index,"
            "offset_start,offset_end,offset_unit,text,text_hash,content_hash,parser_version,"
            "chunk_strategy,created_at,created_by) VALUES "
            f"('{cid}','kb-1','{fid}','v3',{i},{s},{e},'unicode_codepoint','{text}','{th}',"
            f"'{CH}','p-1','S1',NOW(3),'ci')")
    try:
        yield DB
    finally:
        sql(f"DROP DATABASE IF EXISTS `{DB}`", database=None)


def ctx(files=("f-1",)):
    # 通配符必须是字符串 "*"，不是 ["*"]（后者是个非法文件名，会被 IN ('*') 匹配不到）
    scope = "*" if files == "*" else list(files)
    return validate_context({"request_id": "r", "principal_id": "u", "service": "qa",
                             "kb_scope": ["kb-1"], "file_scope": {"kb-1": scope},
                             "authz_version": 1, "expires_at": FUTURE})


def fetch(c, chunk_ids=None) -> list[list[str]]:
    out = sql(fetch_chunks_sql(c, "kb-1", chunk_ids))
    return [r.split("\t") for r in out.splitlines() if r]


def test_scope_limits_rows_even_if_ids_requested(db):
    rows = fetch(ctx(), ["k1", "k2"])          # 显式要 k2（越权）
    assert [r[0] for r in rows] == ["k1"]      # SQL 层已经挡掉


def test_wildcard_sees_both(db):
    rows = fetch(ctx("*"))
    assert {r[0] for r in rows} == {"k1", "k2"}


def test_out_of_scope_chunk_is_rejected_not_dropped(db):
    """纵深防御：上游若绕过 SQL 直接塞越权块，必须抛错而不是静默过滤。"""
    rows = fetch(ctx("*"))
    chunks = rows_to_chunks(rows)
    with pytest.raises(AuthZError) as e:
        assert_chunks_in_scope(ctx(), "kb-1", chunks)
    assert e.value.code == "CHUNK_OUT_OF_SCOPE"


def test_evidence_built_from_db_chunks_passes_contract(db):
    rows = fetch(ctx())
    evs = build_evidences_from_chunks(DOC, ctx(), "kb-1", rows_to_chunks(rows))
    assert [e["evidence_id"] for e in evs] == ["ev-k1"]
    for ev in evs:
        validate_evidence(ev, ROOT)
    assert evs[0]["source_ref"]["offset"]["text_hash"] == hashlib.sha256(DOC[0:6].encode()).hexdigest()


def test_tampered_chunk_text_is_caught(db):
    """库里 text 被改坏时，构造证据必须失败（而不是把坏证据送进 Prompt）。"""
    sql("UPDATE document_chunk SET text='被篡改的内容' WHERE chunk_id='k1'")
    try:
        rows = fetch(ctx())          # 篡改后重新取数，否则用的还是篡改前的快照
        with pytest.raises(Exception):
            build_evidences_from_chunks(DOC, ctx(), "kb-1", rows_to_chunks(rows))
    finally:
        sql(f"UPDATE document_chunk SET text='{DOC[0:6]}' WHERE chunk_id='k1'")
