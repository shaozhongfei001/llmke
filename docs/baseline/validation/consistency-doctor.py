#!/usr/bin/env python3
"""一致性体检：找出"单看每张表都对、合起来不对"的数据。

为什么需要：
    代次、分块、证据、租约、outbox 各自有约束，但**跨表的不变量没人守**：
    证据指向一个不存在的分块、激活指针指向未就绪的代次、租约过期却仍在写……
    这些都不是外键能解决的（跨库/软关联），只能定期体检。

检查项（每条都能独立说明"为什么这是错的"）：
    C1 证据指向不存在的分块         —— 引用断裂，无法复核原文
    C2 分块的 text 与 text_hash 不一致 —— 数据被改坏（或绕过应用层写入）
    C3 激活指针指向的代次不是 ACTIVE —— 服务会读到半成品
    C4 ACTIVE 代次的租约已过期       —— 无人持有写权，后续写入会被静默拒绝
    C5 outbox 中 PENDING 超过阈值未发出 —— 事件积压，下游不知道索引已就绪
    C6 同一 (kb,file,version) 的分块区间重叠 —— 同一段原文被计两次

用法：
    python3 docs/baseline/validation/consistency-doctor.py --socket /tmp/mysql-probe/mysql.sock --db llmke
退出码：0 全部通过；2 有发现（便于挂到定时任务）。
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys

CHECKS = [
    ("C1 证据指向不存在的分块",
     "SELECT e.evidence_id FROM document_evidence e "
     "LEFT JOIN document_chunk c ON c.chunk_id = e.chunk_id "
     "WHERE c.chunk_id IS NULL"),
    ("C2 分块 text 与 text_hash 不一致",
     "SELECT chunk_id FROM document_chunk "
     "WHERE text_hash <> SHA2(text, 256)"),
    ("C3 激活指针指向的代次不是 ACTIVE",
     "SELECT a.kb_id, a.generation_id FROM index_generation_activation a "
     "LEFT JOIN index_generation g ON g.generation_id = a.generation_id "
     "WHERE g.generation_id IS NULL OR g.state <> 'ACTIVE'"),
    ("C4 ACTIVE 代次的租约已过期",
     "SELECT g.generation_id FROM index_generation g "
     "JOIN index_write_lease l ON l.generation_id = g.generation_id "
     "WHERE g.state = 'ACTIVE' AND l.expires_at < NOW(3)"),
    ("C5 outbox PENDING 积压超过 10 分钟",
     "SELECT id FROM index_outbox "
     "WHERE state = 'PENDING' AND next_attempt_at < DATE_SUB(NOW(3), INTERVAL 10 MINUTE)"),
    ("C6 同文档版本分块区间重叠",
     "SELECT a.kb_id, a.file_id, a.chunk_id, b.chunk_id FROM document_chunk a "
     "JOIN document_chunk b "
     "  ON a.kb_id = b.kb_id AND a.file_id = b.file_id "
     " AND a.document_version = b.document_version AND a.chunk_id < b.chunk_id "
     " AND a.offset_start < b.offset_end AND b.offset_start < a.offset_end"),
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--socket", default="/tmp/mysql-probe/mysql.sock")
    ap.add_argument("--db", default="llmke")
    ap.add_argument("--user", default="root")
    a = ap.parse_args()

    mysql = shutil.which("mysql")
    if not mysql:
        print("FAIL: 找不到 mysql 客户端")
        return 2

    findings = 0
    for name, sql in CHECKS:
        p = subprocess.run([mysql, f"--socket={a.socket}", f"-u{a.user}", "-N", "-B", a.db,
                            "-e", sql], capture_output=True, text=True, timeout=60)
        if p.returncode != 0:
            print(f"FAIL: {name} —— 查询失败: {p.stderr.strip()[:160]}")
            findings += 1
            continue
        rows = [r for r in p.stdout.splitlines() if r.strip()]
        if rows:
            findings += len(rows)
            print(f"FAIL: {name} —— {len(rows)} 行，前 3 例: {rows[:3]}")
        else:
            print(f"PASS: {name}")

    print(f"\n结论: {'FAIL' if findings else 'PASS'}（发现 {findings} 处不一致）")
    return 2 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
