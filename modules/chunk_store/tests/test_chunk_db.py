"""分块落库：真库往返（本机 MySQL 独立实例，不用 docker）。

重点验证三件事：
1. 落库后回读的 `text` 与 `text_hash` 仍然自洽（没有被截断/编码破坏）；
2. 唯一键 (kb,file,version,chunk_index) 能阻止同版本重复块；
3. **分块能直接产出证据并落库**——这是切片之间的接缝，别让它只在单元测试里"看起来能连"。
"""
from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from modules.chunk_store import build_chunk, check_chunk_set, text_hash, to_evidence_source
from modules.citation_evidence.assembler import build_document_evidence, validate_evidence

ROOT = Path(__file__).resolve().parents[3]
SOCKET = Path(os.environ.get("LLMKE_MYSQL_SOCKET", "/tmp/mysql-probe/mysql.sock"))
MYSQL = shutil.which("mysql")
SCHEMA = ROOT / "docs/baseline/validation/artifacts/schema-v1.2.sql"
DB = os.environ.get("LLMKE_CI_CHUNK_DB", "llmke_ci_chunk")
DOC = "第一段内容。第二段内容。"
CH = hashlib.sha256(DOC.encode()).hexdigest()

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


@pytest.fixture(scope="module")
def db():
    sql("SELECT 1", database=None)
    sql(f"DROP DATABASE IF EXISTS `{DB}`", database=None)
    sql(f"CREATE DATABASE `{DB}` CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci", database=None)
    with SCHEMA.open("rb") as fh:
        p = subprocess.run([MYSQL, f"--socket={SOCKET}", "-uroot", DB],
                           stdin=fh, capture_output=True, timeout=120)
    assert p.returncode == 0, p.stderr.decode()[:400]
    try:
        yield DB
    finally:
        sql(f"DROP DATABASE IF EXISTS `{DB}`", database=None)


def mk_chunk(start, end, idx, cid, strat="S1"):
    return build_chunk(DOC, chunk_id=cid, kb_id="kb-1", file_id="f-1", document_version="v3",
                       chunk_index=idx, start=start, end=end, content_hash=CH,
                       parser_version="p-1.0", chunk_strategy=strat)


def insert_chunk(c: dict, who: str = "ci") -> None:
    o = c["offset"]
    sql(
        "INSERT INTO document_chunk (chunk_id,kb_id,file_id,document_version,chunk_index,"
        "offset_start,offset_end,offset_unit,text,text_hash,content_hash,parser_version,"
        "chunk_strategy,created_at,created_by) VALUES "
        f"('{c['chunk_id']}','{c['kb_id']}','{c['file_id']}','{c['document_version']}',"
        f"{c['chunk_index']},{o['start']},{o['end']},'{o['unit']}','{c['text']}',"
        f"'{c['text_hash']}','{c['content_hash']}','{c['parser_version']}',"
        f"'{c['chunk_strategy']}',NOW(3),'{who}')"
    )


def test_chunk_roundtrip_text_and_hash(db):
    c = mk_chunk(0, 6, 0, "ch-a")
    insert_chunk(c)
    row = sql("SELECT text,text_hash,offset_start,offset_end FROM document_chunk "
              "WHERE chunk_id='ch-a'").rstrip("\n").split("\t")
    assert row[0] == c["text"]
    assert row[1] == text_hash(row[0]) == c["text_hash"]
    assert (row[2], row[3]) == ("0", "6")


def test_unique_key_blocks_same_index(db):
    # 用独立序号，避免与其它用例抢同一个 (kb,file,version,index)
    insert_chunk(mk_chunk(0, 6, 5, "ch-u1"))
    with pytest.raises(AssertionError):
        insert_chunk(mk_chunk(6, 12, 5, "ch-u2"))     # 同版本同序号，必须失败


def test_chunk_to_evidence_end_to_end(db):
    """切片接缝：库里的分块 -> 证据 -> 过契约 -> 落证据表 -> 回读一致。"""
    c = mk_chunk(6, 12, 1, "ch-b", strat="S1")
    insert_chunk(c)

    stored = sql("SELECT text,text_hash,kb_id,file_id,document_version,chunk_index,"
                 "offset_start,offset_end,content_hash,parser_version "
                 "FROM document_chunk WHERE chunk_id='ch-b'").rstrip("\n").split("\t")
    text, th, kb, fid, dv, _idx, s, e, chash, pv = stored
    assert text_hash(text) == th

    rebuilt = build_chunk(DOC, chunk_id="ch-b", kb_id=kb, file_id=fid, document_version=dv,
                          chunk_index=1, start=int(s), end=int(e), content_hash=chash,
                          parser_version=pv, chunk_strategy="S1", declared_text_hash=th)
    ev = build_document_evidence(DOC, to_evidence_source(rebuilt), "ev-from-chunk")
    validate_evidence(ev, ROOT)

    r = ev["source_ref"]
    sql("INSERT INTO document_evidence (evidence_id,kb_id,file_id,document_version,chunk_id,"
        "content_hash,offset_start,offset_end,offset_unit,text_hash,parser_version,created_at,"
        f"created_by) VALUES ('{ev['evidence_id']}','{r['kb_id']}','{r['file_id']}',"
        f"'{r['document_version']}','{r['chunk_id']}','{r['content_hash']}',"
        f"{r['offset']['start']},{r['offset']['end']},'{r['offset']['unit']}',"
        f"'{r['offset']['text_hash']}','{r['offset']['parser_version']}',NOW(3),'ci')")
    got = sql("SELECT text_hash FROM document_evidence WHERE evidence_id='ev-from-chunk'").strip()
    assert got == th


def test_overlap_between_chunks_detected_by_sql(db):
    insert_chunk(mk_chunk(0, 6, 10, "ch-o1"))
    insert_chunk(mk_chunk(4, 10, 11, "ch-o2"))
    rows = sql("SELECT a.chunk_id,b.chunk_id FROM document_chunk a JOIN document_chunk b "
               " ON a.kb_id=b.kb_id AND a.file_id=b.file_id "
               "AND a.document_version=b.document_version AND a.chunk_id<b.chunk_id "
               "AND a.offset_start<b.offset_end AND b.offset_start<a.offset_end").strip()
    assert "ch-o1" in rows and "ch-o2" in rows


def test_application_rejects_overlap_before_db(db):
    with pytest.raises(Exception) as e:
        check_chunk_set([mk_chunk(0, 6, 20, "ch-x"), mk_chunk(3, 9, 21, "ch-y")])
    assert "CHUNK_OVERLAP" in str(e.value)
