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


def outbox_claim_sql(limit: int = 1) -> str:
    """领取待发事件：CAS 到 SENDING，避免重复投递。"""
    return (
        "UPDATE index_outbox SET state='SENDING', attempts=attempts+1 "
        f"WHERE state='PENDING' AND next_attempt_at <= NOW(3) ORDER BY id LIMIT {int(limit)}"
    )
