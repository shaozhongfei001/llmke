"""outbox 投递语义（真库）：领取 → 成功 / 失败退避 / 到限落 FAILED / 租约到期回收。

为什么必须真库
    "谁领到了这条事件""租约到期能不能被回收"都是**影响行数**问题，
    在 Python 里 mock 等于自证。S3（重复投递）与 S4（迟到重试）的判据只能是真实 UPDATE。

本测试暴露并绕开的 schema 事实
    `index_outbox` 没有 `claimed_at`，只有 `next_attempt_at`。
    因此"可见性超时"借用该列表达：领取时写 NOW()+lease，回收时判 < NOW()。
    这只是近似（无法区分"慢消费者"与"已崩溃"），不改变"至少一次"语义。
"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

from modules.index_generation import (outbox_claim_sql, outbox_dead_letter_sql, outbox_enqueue_sql,
                                      outbox_fail_sql, outbox_mark_sent_sql, outbox_reclaim_sql)

ROOT = Path(__file__).resolve().parents[3]
SOCKET = Path(os.environ.get("LLMKE_MYSQL_SOCKET", "/tmp/mysql-probe/mysql.sock"))
MYSQL = shutil.which("mysql")
SCHEMA = ROOT / "docs/baseline/validation/artifacts/schema-v1.3.sql"
DB = os.environ.get("LLMKE_CI_OUTBOX_DB", "llmke_ci_outbox")

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


def one(sql: str) -> tuple[str, int]:
    return run(sql)


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


def enqueue() -> int:
    run(outbox_enqueue_sql("kb", "kb-1", "INDEX_READY", '{"generation": 1}'))
    row = run("SELECT MAX(id) FROM index_outbox")[0].strip()
    return int(row)


def test_claim_then_sent_is_terminal(db):
    eid = enqueue()
    assert one(outbox_claim_sql(1, lease_seconds=60))[1] == 1
    # 已 SENDING：再领一次必须是 0 行（防重复投递）
    assert one(outbox_claim_sql(1))[1] == 0
    assert one(outbox_mark_sent_sql(eid))[1] == 1
    assert run(f"SELECT state, attempts FROM index_outbox WHERE id={eid}")[0].split("\t") == ["SENT", "1"]
    # SENT 不得被再次领取
    assert one(outbox_claim_sql(1))[1] == 0


def test_fail_backs_off_then_dead_letters(db):
    eid = enqueue()
    for i in range(1, 6):                      # max_attempts 默认 5
        assert one(outbox_claim_sql(1))[1] == 1
        run("UPDATE index_outbox SET next_attempt_at = NOW(3) WHERE state='SENDING'")  # 立即到期
        retry, dead = outbox_fail_sql(eid, backoff_seconds=0, max_attempts=5)
        r = one(retry)[1]
        if i < 5:
            assert r == 1, f"第 {i} 次应放回 PENDING"
            run("UPDATE index_outbox SET next_attempt_at = NOW(3) WHERE id=%d" % eid)
        else:
            assert r == 0, "到上限不应再放回 PENDING"
    assert one(outbox_dead_letter_sql(max_attempts=5))[1] >= 0
    state, attempts = run(f"SELECT state, attempts FROM index_outbox WHERE id={eid}")[0].split("\t")
    assert state == "FAILED"
    assert int(attempts) == 5


def test_stale_sending_is_reclaimed(db):
    eid = enqueue()
    assert one(outbox_claim_sql(1, lease_seconds=60))[1] == 1
    # 租约未到期：不可回收
    assert one(outbox_reclaim_sql(10))[1] == 0
    # 模拟租约到期（消费者崩溃后无人续约）
    run(f"UPDATE index_outbox SET next_attempt_at = NOW(3) - INTERVAL 1 SECOND WHERE id={eid}")
    assert one(outbox_reclaim_sql(10))[1] == 1
    assert run(f"SELECT state FROM index_outbox WHERE id={eid}")[0].strip() == "PENDING"
    # 回收后可被重新领取，attempts 累加（至少一次语义）
    assert one(outbox_claim_sql(1))[1] == 1
    assert run(f"SELECT attempts FROM index_outbox WHERE id={eid}")[0].strip() == "2"
