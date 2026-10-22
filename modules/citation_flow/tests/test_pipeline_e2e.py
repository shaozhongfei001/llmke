"""切片 F：端到端黄金路径 —— 代次 → 租约 → 写块 → 授权检索 → 证据 → outbox。

为什么单独写这一条：
    前面每块都有自己的测试，但"串起来还成立吗"只能由一条完整链路回答。
    真实事故常发生在接缝上（例如：证据按 id 回表、插入不带 fencing、outbox 与业务不同事务）。

链路：
    BUILDING -(locations ok)-> READY -(CAS)-> ACTIVE
       ↓ 租约 lease_val
    带 fencing 插入分块（旧 lease_val 必须写不进去）
       ↓ 授权谓词
    按 file_scope 取块（越权文件不可见）
       ↓
    构造证据并过契约
       ↓
    同事务写 outbox，再 CAS 领取
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

from modules.authz import compile_chunk_predicate, validate_context
from modules.citation_flow import (assert_chunks_in_scope, build_evidences_from_chunks,
                                   fetch_chunks_sql, rows_to_chunks)
from modules.citation_evidence.assembler import validate_evidence
from modules.index_generation import (acquire_lease_sql, activate_seed_sql, activation_cas_sql,
                                      assert_ready_to_activate, insert_guarded_sql,
                                      outbox_claim_sql, outbox_enqueue_sql, read_lease_sql)

ROOT = Path(__file__).resolve().parents[3]
SOCKET = Path(os.environ.get("LLMKE_MYSQL_SOCKET", "/tmp/mysql-probe/mysql.sock"))
MYSQL = shutil.which("mysql")
SCHEMA = ROOT / "docs/baseline/validation/artifacts/schema-v1.3.sql"
DB = os.environ.get("LLMKE_CI_E2E_DB", "llmke_ci_e2e")

DOC = "第一段内容。第二段内容。"
CH = hashlib.sha256(DOC.encode()).hexdigest()
FUTURE = (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()
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


def ctx(files):
    return validate_context({"request_id": "r", "principal_id": "u", "service": "qa",
                             "kb_scope": ["kb-1"], "file_scope": {"kb-1": files},
                             "authz_version": 1, "expires_at": FUTURE})


@pytest.fixture(scope="module")
def db():
    run("SELECT 1", database=None)
    run(f"DROP DATABASE IF EXISTS `{DB}`", database=None)
    run(f"CREATE DATABASE `{DB}` CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci", database=None)
    with SCHEMA.open("rb") as fh:
        p = subprocess.run([MYSQL, f"--socket={SOCKET}", "-uroot", DB],
                           stdin=fh, capture_output=True, timeout=120)
    assert p.returncode == 0, p.stderr.decode()[:400]
    try:
        yield DB
    finally:
        run(f"DROP DATABASE IF EXISTS `{DB}`", database=None)


def test_golden_path(db):
    # 1) 建代次（BUILDING）并校验 READY 前置
    run("INSERT INTO index_generation (kb_id,content_hash,document_version,parse_version,"
        "chunk_version,embedding_version,physical_locations,manifest_json,state,created_at,created_by) "
        f"VALUES ('kb-1','{CH}','v3','p1','c1','e1','{json.dumps(LOCS)}','{{}}','BUILDING',NOW(3),'ci')")
    gid = int(run("SELECT generation_id FROM index_generation WHERE kb_id='kb-1'")[0].strip())
    assert_ready_to_activate("READY", LOCS)
    run(f"UPDATE index_generation SET state='READY' WHERE generation_id={gid}")

    # 2) 激活（单行 CAS）+ 首次插入指针
    _, seeded = run(activate_seed_sql("kb-1", gid, "ci"))
    assert seeded == 1

    # 3) 获取租约
    upd, ins = acquire_lease_sql("kb-1", gid, "worker-1", 60)
    _, a = run(upd)
    if a == 0:
        run(ins)
    lease_val = int(run(read_lease_sql("kb-1", gid))[0].split("\t")[0])
    assert lease_val == 1

    # 4) 带 fencing 插入分块：先用**错误** lease_val，必须 0 行
    cols = ["chunk_id", "kb_id", "file_id", "document_version", "chunk_index", "offset_start",
            "offset_end", "offset_unit", "text", "text_hash", "content_hash", "parser_version",
            "chunk_strategy", "created_at", "created_by"]
    text = DOC[0:6]
    th = hashlib.sha256(text.encode()).hexdigest()
    values = (f"'k1','kb-1','f-1','v3',0,0,6,'unicode_codepoint','{text}','{th}','{CH}',"
              "'p-1','S1',NOW(3),'ci'")
    _, blocked = run(insert_guarded_sql("kb-1", gid, 999, "document_chunk", cols, values))
    assert blocked == 0, "过期 lease_val 竟然写进去了"

    # 正确 lease_val -> 1 行
    _, ok = run(insert_guarded_sql("kb-1", gid, lease_val, "document_chunk", cols, values))
    assert ok == 1

    # 越权文件的分块（同一租约下写入，用于验证检索过滤）
    vals2 = (f"'k2','kb-1','f-2','v3',1,6,12,'unicode_codepoint','{DOC[6:12]}',"
             f"'{hashlib.sha256(DOC[6:12].encode()).hexdigest()}','{CH}','p-1','S1',NOW(3),'ci'")
    assert run(insert_guarded_sql("kb-1", gid, lease_val, "document_chunk", cols, vals2))[1] == 1

    # 5) 授权检索：只看 f-1
    c = ctx(["f-1"])
    rows = [r.split("\t") for r in run(fetch_chunks_sql(c, "kb-1"))[0].splitlines() if r]
    assert {r[2] for r in rows} == {"f-1"}
    chunks = rows_to_chunks(rows)
    assert_chunks_in_scope(c, "kb-1", chunks)

    # 6) 构造证据并过契约
    evs = build_evidences_from_chunks(DOC, c, "kb-1", chunks)
    assert len(evs) == 1
    validate_evidence(evs[0], ROOT)

    # 7) 同事务写 outbox + CAS 领取
    run(outbox_enqueue_sql("kb", "kb-1", "INDEX_READY", json.dumps({"generation": gid})))
    _, claimed = run(outbox_claim_sql(1))
    assert claimed == 1
    _, again = run(outbox_claim_sql(1))
    assert again == 0, "同一条事件被重复投递"

    # 8) 越权查询：f-2 的块不在结果里（用谓词直接验证）
    pred = compile_chunk_predicate(c, "kb-1")
    files = {r for r in run(f"SELECT DISTINCT file_id FROM document_chunk WHERE {pred}")[0].splitlines() if r}
    assert files == {"f-1"}
