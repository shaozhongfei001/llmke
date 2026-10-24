"""代次守卫（P0-04 接缝）：只有 ACTIVE 代次的块可以被检索到。

为什么这条测试必须连真库
    "取不到旧代次数据"是一个 SQL 语义问题（相关子查询 + NULL 比较），
    在 Python 里 mock 等于自证；只有真库能回答"指针缺失时返回 0 行还是全表"。

四个断言对应四种真实事故：
    1. 代次已切换到 v4 后，v3 的块不能被取到（旧数据泄漏进答案）；
    2. 指针还在但状态不是 ACTIVE（切换中断）→ 0 行，而不是"照旧返回"；
    3. 激活行被删（指针缺失）→ 0 行 → 拒绝（不降级为"用最后一版"）；
    4. 正向：切到 v4 后可正常取到 v4（防止"永远取不到"式假安全）。

已知局限（与 sql_adapter 一致）：`document_chunk` 无 generation_id，
本守卫只能按 `document_version` 对齐；同 KB 多文件版本跨代的情形无法区分。
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

from modules.answer_api import AnswerError, build_answer, fetch_chunks_active
from modules.index_generation import acquire_lease_sql, activate_seed_sql, insert_guarded_sql, read_lease_sql

ROOT = Path(__file__).resolve().parents[3]
SOCKET = Path(os.environ.get("LLMKE_MYSQL_SOCKET", "/tmp/mysql-probe/mysql.sock"))
MYSQL = shutil.which("mysql")
SCHEMA = ROOT / "docs/baseline/validation/artifacts/schema-v1.3.sql"
DB = os.environ.get("LLMKE_CI_GEN_DB", "llmke_ci_genguard")

DOC = "第一段内容。第二段内容。"


def ch(version: str) -> str:
    """代次的内容哈希必须随版本变化：index_generation 有 (kb_id, content_hash) 唯一键，
    同一内容不可能存在两个代次——这一点由首次运行时的 1062 错误实测确认。"""
    return hashlib.sha256((DOC + version).encode()).hexdigest()
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


def ctx(files=("*"), kb="kb-1"):
    return {"request_id": "req-gen", "principal_id": "user-1", "service": "answer",
            "kb_scope": [kb], "file_scope": {kb: files},
            "authz_version": 1, "expires_at": FUTURE}


def _new_generation(version: str, state: str) -> int:
    run("INSERT INTO index_generation (kb_id,content_hash,document_version,parse_version,"
        "chunk_version,embedding_version,physical_locations,manifest_json,state,created_at,created_by) "
        f"VALUES ('kb-1','{ch(version)}','{version}','p1','c1','e1','{json.dumps(LOCS)}','{{}}','BUILDING',NOW(3),'ci')")
    gid = int(run(f"SELECT generation_id FROM index_generation WHERE document_version='{version}'")[0].strip())
    run(f"UPDATE index_generation SET state='{state}' WHERE generation_id={gid}")
    return gid


def _write_chunk(gid: int, chunk_id: str, version: str, start: int, end: int) -> None:
    upd, ins = acquire_lease_sql("kb-1", gid, "worker-1", 60)
    if run(upd)[1] == 0:
        run(ins)
    lease = int(run(read_lease_sql("kb-1", gid))[0].split("\t")[0])
    text = DOC[start:end]
    cols = ["chunk_id", "kb_id", "file_id", "document_version", "chunk_index", "offset_start",
            "offset_end", "offset_unit", "text", "text_hash", "content_hash", "parser_version",
            "chunk_strategy", "created_at", "created_by"]
    values = (f"'{chunk_id}','kb-1','f-1','{version}',0,{start},{end},'unicode_codepoint','{text}',"
              f"'{hashlib.sha256(text.encode()).hexdigest()}','{ch(version)}','p-1','S1',NOW(3),'ci'")
    assert run(insert_guarded_sql("kb-1", gid, lease, "document_chunk", cols, values))[1] == 1


@pytest.fixture(scope="module")
def db():
    run("SELECT 1", database=None)
    run(f"DROP DATABASE IF EXISTS `{DB}`", database=None)
    run(f"CREATE DATABASE `{DB}` CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci", database=None)
    with SCHEMA.open("rb") as fh:
        p = subprocess.run([MYSQL, f"--socket={SOCKET}", "-uroot", DB],
                           stdin=fh, capture_output=True, timeout=120)
    assert p.returncode == 0, p.stderr.decode()[:400]

    g3 = _new_generation("v3", "ACTIVE")
    run(activate_seed_sql("kb-1", g3, "ci"))
    _write_chunk(g3, "k-v3", "v3", 0, 6)

    g4 = _new_generation("v4", "READY")          # 已就绪但未激活
    _write_chunk(g4, "k-v4", "v4", 6, 12)
    try:
        yield {"g3": g3, "g4": g4}
    finally:
        run(f"DROP DATABASE IF EXISTS `{DB}`", database=None)


def test_only_active_generation_chunks_visible(db):
    chunks, sql = fetch_chunks_active(runner, ctx(), "kb-1")
    assert [c["chunk_id"] for c in chunks] == ["k-v3"]
    assert "g.state = 'ACTIVE'" in sql


def test_inconsistent_state_yields_nothing(db):
    """指针还在但代次状态不是 ACTIVE（切换中断）→ 取不到，而不是照旧返回旧数据。"""
    run(f"UPDATE index_generation SET state='READY' WHERE generation_id={db['g3']}")
    chunks, _ = fetch_chunks_active(runner, ctx(), "kb-1")
    assert chunks == []
    run(f"UPDATE index_generation SET state='ACTIVE' WHERE generation_id={db['g3']}")


def test_missing_activation_refuses_instead_of_fallback(db):
    """激活行被删 → 0 行 → build_answer 拒绝；不得降级成"用最后一版"。"""
    run("DELETE FROM index_generation_activation WHERE kb_id='kb-1'")
    chunks, _ = fetch_chunks_active(runner, ctx(), "kb-1")
    assert chunks == []
    with pytest.raises(AnswerError) as e:
        build_answer("第一段讲什么", ctx(), "kb-1", chunks, {"f-1": DOC})
    assert e.value.code == "NO_EVIDENCE"
    run(activate_seed_sql("kb-1", db["g3"], "ci"))


def test_switch_to_new_generation_takes_effect(db):
    """正向：切到 v4 后必须能取到 v4（防止'永远取不到'式假安全）。"""
    run(f"UPDATE index_generation SET state='ACTIVE' WHERE generation_id={db['g4']}")
    run("UPDATE index_generation_activation SET previous_generation_id = generation_id, "
        f"generation_id = {db['g4']} WHERE kb_id='kb-1'")
    chunks, _ = fetch_chunks_active(runner, ctx(), "kb-1")
    assert [c["chunk_id"] for c in chunks] == ["k-v4"]
    r = build_answer("第二段讲什么", ctx(), "kb-1", chunks, {"f-1": DOC})
    assert {c["chunk_id"] for c in r["citations"]} == {"k-v4"}
