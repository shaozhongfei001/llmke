"""纵向切片 A：引用证据接真库，端到端跑通。

为什么需要这层测试：
    单元测试只能证明"组装出来的对象符合契约"，不能证明"它能落库、能回读、能被 SQL 复核"。
    证据一旦只活在内存里，进程重启就无法复核，也无法做跨请求的重复/重叠检测。

真库从哪来：
    本机 MySQL 独立实例（不用 docker），由 `~/data/dev/coordination/mysql-probe.sh start` 启动，
    默认 socket = /tmp/mysql-probe/mysql.sock，可用 LLMKE_MYSQL_SOCKET 覆盖。
    实例不可用或缺少 mysql 客户端时**整体跳过**（skip），不让开发机环境决定测试红绿。

为什么走 mysql CLI 而不是驱动：
    当前 venv 没有 pymysql/MySQLdb，也没有 pip 可装。用 CLI 是唯一零依赖路径；
    代价是每步一次进程启动（本测试共约 10 次），换来的是"在任何装了 mysql 的机器上可跑"。
"""
from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from modules.citation_evidence.assembler import (
    build_document_evidence, check_evidence_set, text_hash, validate_evidence)

ROOT = Path(__file__).resolve().parents[3]
SOCKET = Path(os.environ.get("LLMKE_MYSQL_SOCKET", "/tmp/mysql-probe/mysql.sock"))
MYSQL = shutil.which("mysql")
BASE_SCHEMA = ROOT / "docs/baseline/validation/artifacts/target-schema-v1.sql"
ADDITIONS = ROOT / "docs/baseline/validation/artifacts/schema-v1.1-additions.sql"
DB = os.environ.get("LLMKE_CI_DB", "llmke_ci_evidence")
DOC = "第一段内容。第二段内容。"

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
    return p.stdout


def apply_file(path: Path) -> None:
    with path.open("rb") as fh:
        p = subprocess.run([MYSQL, f"--socket={SOCKET}", "-uroot", DB],
                           stdin=fh, capture_output=True, timeout=120)
    if p.returncode != 0:
        raise AssertionError(f"应用 {path.name} 失败:\n{p.stderr.decode()[:400]}")


@pytest.fixture(scope="module")
def db():
    sql("SELECT 1", database=None)                      # 探活
    sql(f"DROP DATABASE IF EXISTS `{DB}`", database=None)
    sql(f"CREATE DATABASE `{DB}` CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci", database=None)
    apply_file(BASE_SCHEMA)
    apply_file(ADDITIONS)
    try:
        yield DB
    finally:
        sql(f"DROP DATABASE IF EXISTS `{DB}`", database=None)


def make_src(start: int, end: int, chunk: str, evidence_id: str, pv: str = "p-1.0"):
    return {
        "kb_id": "kb-1", "file_id": "f-1", "document_version": "v3", "chunk_id": chunk,
        "content_hash": hashlib.sha256(DOC.encode()).hexdigest(),
        "offset": {"start": start, "end": end, "unit": "unicode_codepoint",
                   "text_hash": text_hash(DOC[start:end]), "parser_version": pv},
    }, evidence_id


def insert_evidence(ev: dict, who: str = "ci") -> None:
    r = ev["source_ref"]
    o = r["offset"]
    sql(
        "INSERT INTO document_evidence (evidence_id,kb_id,file_id,document_version,chunk_id,"
        "content_hash,offset_start,offset_end,offset_unit,text_hash,parser_version,created_at,created_by) "
        f"VALUES ('{ev['evidence_id']}','{r['kb_id']}','{r['file_id']}','{r['document_version']}',"
        f"'{r['chunk_id']}','{r['content_hash']}',{o['start']},{o['end']},'{o['unit']}',"
        f"'{o['text_hash']}','{o['parser_version']}',NOW(3),'{who}')"
    )


def test_evidence_persists_and_reads_back_consistent(db):
    src, eid = make_src(0, 6, "c-1", "ev-1")
    ev = build_document_evidence(DOC, src, eid)
    validate_evidence(ev, ROOT)                          # 先过契约

    insert_evidence(ev)

    row = sql("SELECT evidence_id,kb_id,file_id,document_version,chunk_id,content_hash,"
              "offset_start,offset_end,offset_unit,text_hash,parser_version "
              "FROM document_evidence WHERE evidence_id='ev-1'").strip().split("\t")
    assert row[0] == "ev-1" and row[6] == "0" and row[7] == "6"
    assert row[9] == ev["source_ref"]["offset"]["text_hash"]

    # 回读后用原文重算哈希：证明"存进去的定位"仍然指向同一段文本
    start, end = int(row[6]), int(row[7])
    assert text_hash(DOC[start:end]) == row[9]


def test_primary_key_prevents_duplicate_evidence_id(db):
    src, eid = make_src(0, 6, "c-1", "ev-dup")
    insert_evidence(build_document_evidence(DOC, src, eid))
    with pytest.raises(AssertionError):                  # 主键冲突必须报错，不是静默覆盖
        insert_evidence(build_document_evidence(DOC, src, eid))


def test_cross_chunk_overlap_detectable_by_sql(db):
    """集合级校验在应用层做；这里证明**数据库侧也能查出来**，便于离线审计。"""
    a, ea = make_src(0, 6, "c-a", "ev-a")
    b, eb = make_src(4, 10, "c-b", "ev-b")
    insert_evidence(build_document_evidence(DOC, a, ea))
    insert_evidence(build_document_evidence(DOC, b, eb))

    rows = sql(
        "SELECT a.evidence_id,b.evidence_id FROM document_evidence a "
        "JOIN document_evidence b "
        "  ON a.kb_id=b.kb_id AND a.file_id=b.file_id AND a.document_version=b.document_version "
        " AND a.evidence_id<b.evidence_id "
        " AND a.offset_start<b.offset_end AND b.offset_start<a.offset_end"
    ).strip()
    assert rows, "SQL 未检出重叠，与应用层 check_evidence_set 的结论不一致"
    assert "ev-a" in rows and "ev-b" in rows


def test_application_layer_rejects_what_db_would_allow(db):
    """两边一致性的反向验证：应用层应在落库**之前**就拒绝重叠，不依赖数据库兜底。"""
    a, ea = make_src(0, 6, "c-a", "ev-a2")
    b, eb = make_src(3, 9, "c-a", "ev-b2")
    with pytest.raises(Exception) as e:
        check_evidence_set([build_document_evidence(DOC, a, ea),
                            build_document_evidence(DOC, b, eb)])
    assert "OVERLAP" in str(e.value)


def test_parser_version_mix_is_rejected_before_db(db):
    a, ea = make_src(0, 6, "c-1", "ev-p1", pv="p-1.0")
    b, eb = make_src(6, 12, "c-2", "ev-p2", pv="p-2.0")
    with pytest.raises(Exception) as e:
        check_evidence_set([build_document_evidence(DOC, a, ea),
                            build_document_evidence(DOC, b, eb)])
    assert "PARSER_VERSION_MIXED" in str(e.value)
