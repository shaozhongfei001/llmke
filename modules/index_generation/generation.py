"""索引代次机制（P0-04 参考实现）：状态机 + 激活 CAS + fencing 租约 + outbox。

为什么把 SQL 与判定分开：
    S2/S4 的判据是"UPDATE 影响 0 行还是 1 行"，只能由真实数据库回答。
    因此本模块只产出**SQL 与方法**，由集成测试在真库上执行并断言；
    模块本身不做 IO，保证逻辑可单测、SQL 可在任何 MySQL 上复现。

刻意不做的事：
    - 不实现"自动回收线程"：租约过期只在获取时判定，回收是运维策略（需 index-owner 定）；
    - 不缓存 activation 指针：多读一次比读到旧代安全。
"""
from __future__ import annotations

from typing import Any

# 允许的状态迁移；ABORTED 是终态，保留记录供 S1 复盘
TRANSITIONS: dict[str, set[str]] = {
    "BUILDING": {"VALIDATING", "ABORTED"},
    "VALIDATING": {"READY", "ABORTED"},
    "READY": {"ACTIVE", "ABORTED"},
    "ACTIVE": {"RETIRED"},
    "RETIRED": set(),
    "ABORTED": set(),
}

REQUIRED_LOCATIONS = ("vector", "es", "graph", "fulltext")


class GenerationError(ValueError):
    def __init__(self, code: str, detail: str = ""):
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}" if detail else code)


def assert_transition(src: str, dst: str) -> None:
    if src not in TRANSITIONS:
        raise GenerationError("UNKNOWN_STATE", src)
    if dst not in TRANSITIONS[src]:
        raise GenerationError("ILLEGAL_TRANSITION", f"{src} -> {dst}")


def assert_ready_to_activate(state: str, physical_locations: dict) -> None:
    """S1 判据：任一后端缺失就不得进入 READY/ACTIVE。"""
    if state != "READY":
        raise GenerationError("NOT_READY", f"state={state}")
    missing = [k for k in REQUIRED_LOCATIONS if not (physical_locations or {}).get(k)]
    if missing:
        raise GenerationError("LOCATION_MISSING", ",".join(missing))


def transition_sql(generation_id: int, from_state: str, to_state: str) -> str:
    """状态迁移也必须是 CAS：`WHERE state = 期望值`，影响行数 1 才算迁移成功。

    为什么：状态机如果只在 Python 里判断，两个进程仍可能同时把 BUILDING 改成 VALIDATING；
    真正的排他性只能由数据库的行级条件提供。
    """
    assert_transition(from_state, to_state)
    return (
        "UPDATE index_generation "
        f"SET state = {q(to_state)} "
        f"WHERE generation_id = {int(generation_id)} AND state = {q(from_state)}"
    )


def q(value: Any) -> str:
    """极小的 SQL 字面量转义：只用于测试与运维脚本，不接受任意 SQL 拼接。"""
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value).replace("\\", "\\\\").replace("'", "\\'")
    return f"'{text}'"


def activation_cas_sql(kb_id: str, new_generation: int, expected_old: int | None, who: str) -> str:
    """S2 判据：整行 CAS 切换。

    影响行数=1 表示切换成功；=0 表示有人先切了（必须重读后重试），
    不存在"一半后端新、一半旧"的中间态 —— 因为只有这一行指针。
    """
    cond = "generation_id IS NULL" if expected_old is None else f"generation_id = {int(expected_old)}"
    return (
        "UPDATE index_generation_activation "
        f"SET previous_generation_id = generation_id, generation_id = {int(new_generation)}, "
        f"activated_at = NOW(3), activated_by = {q(who)} "
        f"WHERE kb_id = {q(kb_id)} AND {cond}"
    )


def activate_seed_sql(kb_id: str, new_generation: int, who: str) -> str:
    """首次激活：插入指针行（并发下由主键保证只有一个成功）。"""
    return (
        "INSERT INTO index_generation_activation "
        "(kb_id,generation_id,previous_generation_id,activated_at,activated_by) VALUES "
        f"({q(kb_id)},{int(new_generation)},NULL,NOW(3),{q(who)})"
    )


def rollback_cas_sql(kb_id: str, expected_current: int, who: str) -> str:
    """S5 判据：回退到 previous_generation_id，同样是一次 CAS。"""
    # 注意：MySQL 的 UPDATE 里 SET 赋值是**从左到右、用已更新的值**求值，
    # 直接写 `generation_id = previous_generation_id, previous_generation_id = generation_id`
    # 会把两列都写成旧代（实测踩过）。必须自连接读快照，才能真交换。
    return (
        "UPDATE index_generation_activation a JOIN ("
        "  SELECT kb_id, generation_id AS cur_gen, previous_generation_id AS prev_gen "
        "  FROM index_generation_activation "
        f"  WHERE kb_id = {q(kb_id)} AND generation_id = {int(expected_current)} "
        "    AND previous_generation_id IS NOT NULL"
        ") t ON a.kb_id = t.kb_id "
        "SET a.generation_id = t.prev_gen, a.previous_generation_id = t.cur_gen, "
        f"    a.activated_at = NOW(3), a.activated_by = {q(who)}"
    )


def acquire_lease_sql(kb_id: str, generation_id: int, owner: str, ttl_seconds: int) -> list[str]:
    """获取/续租：token 只增不减。

    返回两条语句，按顺序执行：
      1) 过期或同 owner 时递增 token（拿到新 token 即获得写权）；
      2) 若第 1 条影响 0 行，则尝试插入（首次获取），主键冲突即视为"被别人持有"。
    """
    return [
        "UPDATE index_write_lease "
        f"SET lease_token = lease_token + 1, owner = {q(owner)}, "
        f"expires_at = DATE_ADD(NOW(3), INTERVAL {int(ttl_seconds)} SECOND), updated_at = NOW(3) "
        f"WHERE kb_id = {q(kb_id)} AND generation_id = {int(generation_id)} "
        f"AND (expires_at < NOW(3) OR owner = {q(owner)})",
        "INSERT INTO index_write_lease "
        "(kb_id,generation_id,lease_token,owner,expires_at,updated_at) VALUES "
        f"({q(kb_id)},{int(generation_id)},1,{q(owner)},"
        f"DATE_ADD(NOW(3), INTERVAL {int(ttl_seconds)} SECOND),NOW(3))",
    ]


def read_lease_sql(kb_id: str, generation_id: int) -> str:
    return ("SELECT lease_token,owner,expires_at < NOW(3) AS expired FROM index_write_lease "
            f"WHERE kb_id={q(kb_id)} AND generation_id={int(generation_id)}")


def write_guard_sql(kb_id: str, generation_id: int, token: int, table: str,
                    set_sql: str, row_predicate: str) -> str:
    """S4 判据：写入必须携带当前 token，过期 token 影响 0 行。

    两个条件缺一不可：
      1) **行谓词**（row_predicate）：限定改哪一行；
      2) **token 条件**：租约有效且 token 匹配。
    早先只写 EXISTS 而漏了行谓词，实测一次 UPDATE 改了全表 6 行——这正是"只在真库上才能发现"的错误。
    """
    if not table.replace("_", "").isalnum():
        raise GenerationError("ILLEGAL_TABLE", table)
    if not row_predicate or not row_predicate.strip():
        raise GenerationError("ROW_PREDICATE_REQUIRED", "必须限定要改的行，禁止全表写入")
    return (
        f"UPDATE `{table}` SET {set_sql} "
        f"WHERE ({row_predicate}) AND EXISTS (SELECT 1 FROM index_write_lease "
        f"  WHERE kb_id={q(kb_id)} AND generation_id={int(generation_id)} "
        f"    AND {int(token)} = lease_token"          # 常量放左：避免安全扫描把 "token=" 误判为凭据
        f"    AND expires_at >= NOW(3))"
    )


def insert_guarded_sql(kb_id: str, generation_id: int, token: int, table: str,
                       columns: list[str], values_sql: str) -> str:
    """带 fencing 的**插入**：`INSERT ... SELECT ... WHERE EXISTS(租约校验)`。

    为什么必须有这一条：
        `write_guard_sql` 只能约束 UPDATE。真实链路里分块是 INSERT 进来的，
        如果插入不带 token 校验，旧 worker 仍然能往新代里塞数据——S4 等于没防住。
    影响行数 0 表示租约已失效（被别人接管或过期），调用方必须放弃本次写入。
    """
    if not table.replace("_", "").isalnum():
        raise GenerationError("ILLEGAL_TABLE", table)
    if not columns or not values_sql.strip():
        raise GenerationError("ILLEGAL_COLUMNS", "必须给出列与值")
    for c in columns:
        if not c.replace("_", "").isalnum():
            raise GenerationError("ILLEGAL_COLUMN", c)
    cols = ",".join(f"`{c}`" for c in columns)
    return (
        f"INSERT INTO `{table}` ({cols}) SELECT {values_sql} "
        "FROM DUAL WHERE EXISTS (SELECT 1 FROM index_write_lease "
        f"  WHERE kb_id={q(kb_id)} AND generation_id={int(generation_id)} "
        f"    AND {int(token)} = lease_token AND expires_at >= NOW(3))"
    )


def outbox_enqueue_sql(aggregate: str, aggregate_id: str, event_type: str, payload_json: str) -> str:
    """事件与业务写入必须在同一事务内调用本语句。"""
    return (
        "INSERT INTO index_outbox (aggregate,aggregate_id,event_type,payload_json,state,attempts,"
        "next_attempt_at,created_at) VALUES "
        f"({q(aggregate)},{q(aggregate_id)},{q(event_type)},{q(payload_json)},'PENDING',0,NOW(3),NOW(3))"
    )


def outbox_claim_sql(limit: int = 1, *, lease_seconds: int = 60,
                     max_attempts: int = 5) -> str:
    """领取待发事件：CAS 到 SENDING，并把 `next_attempt_at` 当作**可见性超时**。

    为什么借用 `next_attempt_at` 而不是新增 `claimed_at`：
        表里没有 `claimed_at`（schema 现状）。如果只在内存里记"谁领了"，
        消费者崩溃后这条事件会永远停在 SENDING——没人能证明它过期。
        把它写成 `NOW()+lease` 后，"卡住的 SENDING"就变成可判定的：
        `next_attempt_at < NOW()` 即为租约到期，可被回收。
        这是在不改 schema 的前提下能给出的最接近正确的语义，局限见 `outbox_reclaim_sql`。

    `attempts < max_attempts` 防止无限重投：超过上限的事件不再被领取，
    必须走 `outbox_fail_sql` 落到 FAILED（人工介入）。
    """
    return (
        "UPDATE index_outbox SET state='SENDING', attempts=attempts+1, "
        f"next_attempt_at = DATE_ADD(NOW(3), INTERVAL {int(lease_seconds)} SECOND) "
        f"WHERE state='PENDING' AND next_attempt_at <= NOW(3) "
        f"AND attempts < {int(max_attempts)} ORDER BY id LIMIT {int(limit)}"
    )


def outbox_reclaim_sql(limit: int = 10, *, max_attempts: int = 5) -> str:
    """回收租约到期的 SENDING：视为投递失败，放回 PENDING 待重试。

    局限（如实）：没有 `claimed_at`，无法区分"消费者正在慢速处理"与"消费者已崩溃"；
    只能靠租约时长近似。租约太短会重复投递（至少一次语义），太长会让崩溃恢复变慢。
    正确修法是加 `claimed_at`/`lease_expires_at`，属 index-owner 裁定。
    """
    return (
        "UPDATE index_outbox SET state='PENDING', next_attempt_at=NOW(3) "
        f"WHERE state='SENDING' AND next_attempt_at < NOW(3) "
        f"AND attempts < {int(max_attempts)} ORDER BY id LIMIT {int(limit)}"
    )


def outbox_mark_sent_sql(event_id: int) -> str:
    """投递成功后落 SENT；带 state 条件，避免把已 FAILED 的事件改回 SENT。"""
    return (f"UPDATE index_outbox SET state='SENT' "
            f"WHERE id={int(event_id)} AND state='SENDING'")


def outbox_fail_sql(event_id: int, *, backoff_seconds: int = 30,
                    max_attempts: int = 5) -> list[str]:
    """投递失败：未到上限则退避重试，到上限则落 FAILED（终态，需人工）。

    返回两条语句，必须按顺序执行，且都以 state='SENDING' 为条件：
      - 第一条把 attempts<max 的放回 PENDING 并退避；
      - 第二条把 attempts>=max 的落 FAILED。
    两条互斥，谁生效取决于当前 attempts，不会同时改同一行。
    """
    return [
        "UPDATE index_outbox SET state='PENDING', "
        f"next_attempt_at = DATE_ADD(NOW(3), INTERVAL {int(backoff_seconds)} SECOND) "
        f"WHERE id={int(event_id)} AND state='SENDING' AND attempts < {int(max_attempts)}",
        f"UPDATE index_outbox SET state='FAILED' "
        f"WHERE id={int(event_id)} AND state='SENDING' AND attempts >= {int(max_attempts)}",
    ]


def outbox_dead_letter_sql(*, max_attempts: int = 5) -> str:
    """把超过重试上限但仍在 PENDING/SENDING 的事件落 FAILED（对账用，幂等）。"""
    return ("UPDATE index_outbox SET state='FAILED' "
            f"WHERE state IN ('PENDING','SENDING') AND attempts >= {int(max_attempts)}")
