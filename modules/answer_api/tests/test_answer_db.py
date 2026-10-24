"""真库端到端：代次 → 租约 → 写块 → 授权取块 → 证据 → 答案。

与单测的分工：
    单测证明"给定块时不会说错话"；本测试证明"**取块这一步就取不到越权内容**"。
    后者只能在真库上验证，因为过滤是 SQL 谓词，不是 Python 判断。

四个断言对应四种真实风险：
    1. 只授权 f-1 时，答案里不出现 f-2 的任何文本（过滤在取数层）；
    2. 用 chunk_ids 指定越权块，**不能**绕过谓词（收窄不等于放宽）；
    3. 整库授权但只给一个文件的原文 → 拒绝（跨文件共用一份全文会错位）；
    4. 只授权 f-2 时，能正常回答 f-2（防止"拒绝一切"式的假安全）。
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from modules.answer_api import AnswerError, build_answer, fetch_chunks
from modules.index_generation import (acquire_lease_sql, activate_seed_sql, insert_guarded_sql,
                                      read_lease_sql)

ROOT = Path(__file__).resolve().parents[3]
SOCKET = Path(os.environ.get("LLMKE_MYSQL_SOCKET", "/tmp/mysql-probe/mysql.sock"))
MYSQL = shutil.which("mysql")
SCHEMA = ROOT / "docs/baseline/validation/artifacts/schema-v1.3.sql"
DB = os.environ.get("LLMKE_CI_ANSWER_DB", "llmke_ci_answer")

DOC = "第一段内容。第二段内容。"
CH = hashlib.sha256(DOC.encode()).hexdigest()
FUTURE = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()
LOCS = {"vector": "v", "es": "e", "graph": "g", "fulltext": "f"}

pytestmark = pytest.mark.skipif(
    MYSQL is None or not SOCKET.exists(),
    reason="需要本机 MySQL 独立实例（coordination/mysql-probe.sh start）与 mysql 客户端",
)


def run(statement: str, *, database: str | None = DB) -> tuple[str, int]:
    cmd = [MYSQL, f"--socket={SOCKET}", "-uroot", "-N", "-B"]
    if database:
        cmd.insert(3, database)
    p = subprocess.run(cmd, input=f"{statement};\nSELECT ROW_COUNT();\n",
                       capture_output=True, text=True, timeout=60)
    if p.returncode != 0:
        raise AssertionError(f"SQL 失败: {statement[:90]}...\n{p.stderr.strip()}")
    lines = p.stdout.rstrip("\n").split("\n") if p.stdout.strip() else []
    affected = int(lines[-1]) if lines and lines[-1].lstrip("-").isdigit() else 0
    return "\n".join(lines[:-1]), affected


def runner(sql: str) -> list[list[str]]:
    p = subprocess.run([MYSQL, f"--socket={SOCKET}", "-uroot", "-N", "-B", DB],
                       input=sql + ";\n", capture_output=True, text=True, timeout=60)
    if p.returncode != 0:
        raise AssertionError(f"SELECT 失败: {p.stderr.strip()}")
    return [line.split("\t") for line in p.stdout.splitlines() if line]


def ctx(files, kb="kb-1"):
    return {"request_id": "req-db", "principal_id": "user-1", "service": "answer",
            "kb_scope": [kb], "file_scope": {kb: files},
            "authz_version": 1, "expires_at": FUTURE}


@pytest.fixture(scope="module")
def db():
    run("SELECT 1", database=None)
    run(f"DROP DATABASE IF EXISTS `{DB}`", database=None)
    run(f"CREATE DATABASE `{DB}` CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci", database=None)
    with SCHEMA.open("rb") as fh:
        p = subprocess.run([MYSQL, f"--socket={SOCKET}", "-uroot", DB],
                           stdin=fh, capture_output=True, timeout=120)
    assert p.returncode == 0, p.stderr.decode()[:400]

    run("INSERT INTO index_generation (kb_id,content_hash,document_version,parse_version,"
        "chunk_version,embedding_version,physical_locations,manifest_json,state,created_at,created_by) "
        f"VALUES ('kb-1','{CH}','v3','p1','c1','e1','{json.dumps(LOCS)}','{{}}','BUILDING',NOW(3),'ci')")
    gid = int(run("SELECT generation_id FROM index_generation WHERE kb_id='kb-1'")[0].strip())
    run(f"UPDATE index_generation SET state='READY' WHERE generation_id={gid}")
    run(activate_seed_sql("kb-1", gid, "ci"))
    upd, ins = acquire_lease_sql("kb-1", gid, "worker-1", 60)
    if run(upd)[1] == 0:
        run(ins)
    lease = int(run(read_lease_sql("kb-1", gid))[0].split("\t")[0])

    cols = ["chunk_id", "kb_id", "file_id", "document_version", "chunk_index", "offset_start",
            "offset_end", "offset_unit", "text", "text_hash", "content_hash", "parser_version",
            "chunk_strategy", "created_at", "created_by"]
    for cid, fid, idx, s, e in (("k1", "f-1", 0, 0, 6), ("k2", "f-2", 1, 6, 12)):
        text = DOC[s:e]
        values = (f"'{cid}','kb-1','{fid}','v3',{idx},{s},{e},'unicode_codepoint','{text}',"
                  f"'{hashlib.sha256(text.encode()).hexdigest()}','{CH}','p-1','S1',NOW(3),'ci'")
        assert run(insert_guarded_sql("kb-1", gid, lease, "document_chunk", cols, values))[1] == 1
    try:
        yield DB
    finally:
        run(f"DROP DATABASE IF EXISTS `{DB}`", database=None)


def test_authorized_fetch_sees_only_one_file(db):
    chunks, sql = fetch_chunks(runner, ctx(["f-1"]), "kb-1")
    assert {c["file_id"] for c in chunks} == {"f-1"}
    assert "file_id IN ('f-1')" in sql


def test_answer_from_db_cites_only_authorized_file(db):
    chunks, _ = fetch_chunks(runner, ctx(["f-1"]), "kb-1")
    r = build_answer("第一段讲什么", ctx(["f-1"]), "kb-1", chunks, {"f-1": DOC})
    assert r["status"] == "OK"
    assert {c["file_id"] for c in r["citations"]} == {"f-1"}
    # f-2 的原文片段绝不能出现在答案里
    assert "第二段内容" not in r["answer"]["text"]


def test_chunk_ids_cannot_widen_scope(db):
    """指定越权 chunk_id 时，取数仍被谓词挡住 → 0 条 → 拒绝，而不是"回答 f-2"。"""
    chunks, sql = fetch_chunks(runner, ctx(["f-1"]), "kb-1", chunk_ids=["k2"])
    assert chunks == []
    assert "chunk_id IN ('k2')" in sql
    with pytest.raises(AnswerError) as e:
        build_answer("越权试试", ctx(["f-1"]), "kb-1", chunks, {"f-1": DOC})
    assert e.value.code == "NO_EVIDENCE"


def test_whole_kb_scope_requires_per_file_text(db):
    """整库授权会同时取到两个文件；只给一份全文时必须拒绝，而不是拿 f-1 的文本切 f-2 的偏移。"""
    chunks, _ = fetch_chunks(runner, ctx("*"), "kb-1")
    assert {c["file_id"] for c in chunks} == {"f-1", "f-2"}
    with pytest.raises(AnswerError) as e:
        build_answer("两段都看", ctx("*"), "kb-1", chunks, {"f-1": DOC})
    assert e.value.code == "DOCUMENT_TEXT_MISSING"


def test_authorized_f2_answers_normally(db):
    """防止"拒绝一切"式假安全：换授权后就该能回答，且只引用 f-2。"""
    chunks, _ = fetch_chunks(runner, ctx(["f-2"]), "kb-1")
    r = build_answer("第二段讲什么", ctx(["f-2"]), "kb-1", chunks, {"f-2": DOC})
    assert {c["file_id"] for c in r["citations"]} == {"f-2"}
    assert "第一段内容" not in r["answer"]["text"]
