"""索引代次机制：真库验证 S1–S5（本机 MySQL 独立实例）。

这些断言只能在真库上做：
    S2/S4 的判据是"UPDATE 影响 0 行还是 1 行"，内存 mock 无法证明原子性与 token 单调性。
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from modules.index_generation import (GenerationError, acquire_lease_sql, activate_seed_sql,
                                      activation_cas_sql, assert_ready_to_activate,
                                      outbox_claim_sql, outbox_enqueue_sql, read_lease_sql,
                                      rollback_cas_sql, write_guard_sql)

ROOT = Path(__file__).resolve().parents[3]
SOCKET = Path(os.environ.get("LLMKE_MYSQL_SOCKET", "/tmp/mysql-probe/mysql.sock"))
MYSQL = shutil.which("mysql")
SCHEMA = ROOT / "docs/baseline/validation/artifacts/schema-v1.3.sql"
DB = os.environ.get("LLMKE_CI_GEN_DB", "llmke_ci_generation")

pytestmark = pytest.mark.skipif(
    MYSQL is None or not SOCKET.exists(),
    reason="需要本机 MySQL 独立实例（coordination/mysql-probe.sh start）与 mysql 客户端",
)

LOCS = {"vector": "v", "es": "e", "graph": "g", "fulltext": "f"}


def run(statement: str, *, database: str | None = DB) -> tuple[str, int]:
    """执行语句并返回 (输出, 影响行数)。用同一会话取 ROW_COUNT()。"""
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


def new_generation(kb: str, content: str, state: str = "READY", locs: dict | None = None) -> int:
    run(
        "INSERT INTO index_generation (kb_id,content_hash,document_version,parse_version,"
        "chunk_version,embedding_version,physical_locations,manifest_json,state,created_at,created_by) "
        f"VALUES ('{kb}','{content}','v3','p1','c1','e1',"
        f"'{json.dumps(locs if locs is not None else LOCS)}','{{}}','{state}',NOW(3),'ci')"
    )
    out, _ = run(f"SELECT generation_id FROM index_generation WHERE kb_id='{kb}' AND content_hash='{content}'")
    return int(out.strip())


# ---------- S1：部分后端失败 ----------
def test_s1_missing_backend_blocks_readiness(db):
    for locs in ({**LOCS, "graph": None}, {"vector": "v"}, {}):
        with pytest.raises(GenerationError) as e:
            assert_ready_to_activate("READY", locs)
        assert e.value.code == "LOCATION_MISSING"
    assert_ready_to_activate("READY", LOCS)


def test_s1_aborted_generation_is_kept_for_review(db):
    gid = new_generation("kb-s1", "c" * 64, state="ABORTED", locs={})
    out, _ = run(f"SELECT state FROM index_generation WHERE generation_id={gid}")
    assert out.strip() == "ABORTED"


# ---------- S2：切换中断（原子指针） ----------
def test_s2_activation_is_single_row_cas(db):
    g1 = new_generation("kb-s2", "1" * 64)
    g2 = new_generation("kb-s2", "2" * 64)

    _, affected = run(activate_seed_sql("kb-s2", g1, "ops"))
    assert affected == 1

    # 用错误的期望值切换 -> 0 行（有人先切了）
    _, stale = run(activation_cas_sql("kb-s2", g2, g1 + 999, "ops"))
    assert stale == 0

    # 正确期望值 -> 1 行，且 previous 记录旧代
    _, ok = run(activation_cas_sql("kb-s2", g2, g1, "ops"))
    assert ok == 1
    out, _ = run("SELECT generation_id,previous_generation_id FROM index_generation_activation "
                 "WHERE kb_id='kb-s2'")
    cur, prev = out.strip().split("\t")
    assert int(cur) == g2 and int(prev) == g1


# ---------- S3：内容覆盖不串代 ----------
def test_s3_same_content_is_idempotent_but_new_content_keeps_old(db):
    a = new_generation("kb-s3", "a" * 64)
    with pytest.raises(AssertionError):        # 同 kb+content_hash 唯一
        new_generation("kb-s3", "a" * 64)
    b = new_generation("kb-s3", "b" * 64)
    assert a != b
    out, _ = run(f"SELECT COUNT(*) FROM index_generation WHERE kb_id='kb-s3'")
    assert out.strip() == "2"


# ---------- S4：迟到重试（fencing） ----------
def test_s4_stale_token_cannot_write(db):
    gid = new_generation("kb-s4", "4" * 64)
    upd, ins = acquire_lease_sql("kb-s4", gid, "worker-a", 60)
    _, a1 = run(upd)
    if a1 == 0:
        run(ins)
    out, _ = run(read_lease_sql("kb-s4", gid))
    assert out.split("\t")[0] == "1"

    # 让租约过期，worker-b 接管 -> token=2
    run("UPDATE index_write_lease SET expires_at = DATE_SUB(NOW(3), INTERVAL 1 SECOND) "
        f"WHERE kb_id='kb-s4' AND generation_id={gid}")
    _, b1 = run(acquire_lease_sql("kb-s4", gid, "worker-b", 60)[0])
    assert b1 == 1
    out, _ = run(read_lease_sql("kb-s4", gid))
    assert out.split("\t")[0] == "2"

    # 旧 token 写 -> 0 行；新 token 写 -> 1 行
    # 先确认"只改一行"：全表有多个 generation，必须只命中 gid
    _, stale = run(write_guard_sql("kb-s4", gid, 1, "index_generation", "state='ACTIVE'", f"generation_id={gid}"))
    assert stale == 0
    _, fresh = run(write_guard_sql("kb-s4", gid, 2, "index_generation", "state='ACTIVE'", f"generation_id={gid}"))
    assert fresh == 1


# ---------- S5：旧服务回退 ----------
def test_s5_rollback_restores_previous_generation(db):
    g1 = new_generation("kb-s5", "5" * 64)
    g2 = new_generation("kb-s5", "6" * 64)
    run(activate_seed_sql("kb-s5", g1, "ops"))
    run(activation_cas_sql("kb-s5", g2, g1, "ops"))

    _, affected = run(rollback_cas_sql("kb-s5", g2, "ops"))
    assert affected == 1
    out, _ = run("SELECT generation_id,previous_generation_id FROM index_generation_activation "
                 "WHERE kb_id='kb-s5'")
    cur, prev = out.strip().split("\t")
    assert int(cur) == g1 and int(prev) == g2


# ---------- outbox ----------
def test_outbox_enqueue_and_claim_once(db):
    run(outbox_enqueue_sql("kb", "kb-1", "INDEX_READY", '{"generation":1}'))
    _, first = run(outbox_claim_sql(1))
    assert first == 1
    _, second = run(outbox_claim_sql(1))
    assert second == 0                         # 已被 SENDING，不得重复投递
    out, _ = run("SELECT state,attempts FROM index_outbox ORDER BY id DESC LIMIT 1")
    assert out.strip() == "SENDING\t1"
