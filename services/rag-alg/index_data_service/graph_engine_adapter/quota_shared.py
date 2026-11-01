"""跨实例共享配额：MySQL 上的按租户计数窗口。

`quota.py` 的令牌桶只在**单进程内**成立：3 副本部署时每个实例各自计数，
"100 QPS"实际是 3 × 100。要给出真正的全局上限，计数必须放在所有实例都看得见、
且能原子自增的介质上。本机没有可靠的 Redis 客户端，于是用已有 MySQL：
一张以 `(tenant, window_start)` 为主键的表，一次
`INSERT ... ON DUPLICATE KEY UPDATE used = used + n` 完成"读-改-写"。

精度上的取舍：这是**固定窗口**而非严格滑动窗口。固定窗口在边界上允许
最多 2 × limit 的瞬时突发（前一窗口末尾 + 后一窗口开头），换来的是每次计数只有
"一行 UPSERT + 一行 SELECT"，不需要 `SUM over 多个窗口` 或 ZSET。要更严格就该上
"预扣额度 + 下一窗口预留"（GCRA），那是另一套机制，不在本次范围内。

三处最容易写错、因此必须显式处理的地方：

1. **被拒的请求不能永久占额度**。先自增再判断，被拒时必须把这次自增扣回去。
   否则 limit=3 的租户在第 4 次请求之后，本窗口内**永远**不会再放行——
   表现为"明明没跑满却一直被拒"，且只有等下一个窗口才自愈，线上极难定位。
   扣回动作与判断在同一事务里，不会出现"扣了一半"的中间态。
2. **失败必须 fail-closed**。数据库不可用时若"当作放行"，配额等于失效
   （比不做配额更糟：看起来有保护，实际没有）。这里一律抛 `SharedQuotaError`，
   由调用方决定降级（拒绝/503），而不是由本模块猜。
3. **只清理本租户的旧窗口**。全表 `DELETE` 在多租户下会删掉别人正在用的窗口；
   这里按 `tenant` 前缀 + 时间下界删，且同一租户每个窗口只做一次。

刻意不做的事：
- 不引入 Redis（本机没有可靠客户端，引入就多一个必须运维的组件）；
- 不绑定驱动：`connection_factory` 由调用方注入（生产用
  `lease_mysql.make_pymysql_factory`），核心路径 import 不到驱动也能被单测覆盖；
- 不做排队（`take` 绝不阻塞；愿意等到下个窗口的调用方用 `wait_take`）；
- 不改 `quota.py` 的单进程语义：两者是叠加关系，进程内桶仍在最前面挡突发。
"""

import math
import threading
import time
from typing import Any, Callable, Dict, Optional

SCHEMA = "llmke.graph-engine.quota.shared.v1"
TABLE = "v2_quota_window"
# 与表里 VARCHAR(128) 对齐：超长租户名不截断会变成 "Data too long" 的配额故障。
MAX_TENANT_LEN = 128
# 记"每个租户上次清理到哪个窗口"的字典上限，见 `_should_prune`。
_MAX_TRACKED_TENANTS = 4096

DDL = """
CREATE TABLE IF NOT EXISTS v2_quota_window (
  tenant       VARCHAR(128) NOT NULL,
  window_start BIGINT       NOT NULL,
  used         INT          NOT NULL DEFAULT 0,
  PRIMARY KEY (tenant, window_start)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
"""

# 原子自增：靠主键冲突走 UPDATE，一步完成"读-改-写"。
# 不能先 SELECT 再 UPDATE——两个实例同时读到 2，都写 3，额度就凭空多出一份。
SQL_UPSERT = ("INSERT INTO v2_quota_window (tenant, window_start, used) "
              "VALUES (%s, %s, %s) "
              "ON DUPLICATE KEY UPDATE used = used + %s")

SQL_SELECT_USED = ("SELECT used FROM v2_quota_window "
                   "WHERE tenant = %s AND window_start = %s")

# 退款用 GREATEST 兜底：窗口行被清理后重建时若从 0 起算，直接减会变成负数，
# 负值等于凭空多出额度。宁可少退，不能退回成负。
SQL_REFUND = ("UPDATE v2_quota_window SET used = GREATEST(used - %s, 0) "
              "WHERE tenant = %s AND window_start = %s")

# 只删本租户的旧窗口（`tenant` 是主键前缀，这是索引内的范围删）。
SQL_PRUNE = ("DELETE FROM v2_quota_window "
             "WHERE tenant = %s AND window_start < %s")

SQL_STATS = ("SELECT tenant, used FROM v2_quota_window "
             "WHERE window_start = %s ORDER BY tenant")


class SharedQuotaError(RuntimeError):
    """配额计数不可用（fail-closed）。

    语义是"算不出来"而不是"算出来不够"：调用方应当按超限处理（拒绝/503/降级），
    **不能**当作 `allowed=True`——那样配额形同虚设，且故障期间看起来一切正常。
    消息里只有操作名、租户与驱动错误摘要，不含连接串、库名与口令。
    """


def normalize_tenant(tenant: Any) -> str:
    """租户名规范化：空 → `default`，超长截断到 `MAX_TENANT_LEN`。"""
    text = str(tenant or "").strip() or "default"
    return text[:MAX_TENANT_LEN]


def _brief(exc: BaseException) -> str:
    """异常摘要：类型 + 前 200 字符（驱动错误常带冗长前缀，日志里要能一眼看到根因）。"""
    return f"{type(exc).__name__}: {str(exc)[:200]}"


def ensure_schema(connection_factory: Callable[[], Any]) -> None:
    """建表（幂等）。生产上 DDL 权限通常收紧，建表应由 DBA 执行
    `sql/003_shared_quota.sql`；本函数只给测试库与本地环境用。"""
    try:
        conn = connection_factory()
    except Exception as exc:  # noqa: BLE001
        raise SharedQuotaError(f"配额计数不可用（操作=ensure_schema）：{_brief(exc)}") from exc
    try:
        conn.autocommit(False)
        with conn.cursor() as cur:
            cur.execute(DDL)
        conn.commit()
    except Exception as exc:  # noqa: BLE001
        _rollback_quietly(conn)
        raise SharedQuotaError(f"配额计数不可用（操作=ensure_schema）：{_brief(exc)}") from exc
    finally:
        conn.close()


def _rollback_quietly(conn: Any) -> None:
    """回滚失败不能盖掉原始异常：它只是"尽力别留下半截事务"，不是主错误。"""
    try:
        conn.rollback()
    except Exception:  # noqa: BLE001  # pragma: no cover - 驱动已断时的兜底
        pass


class SharedQuotaCounter:
    """按租户的跨实例配额：`limit` 次 / `window_s` 秒，所有实例共用同一份计数。

    `connection_factory` 每次调用返回一条**新的**连接（不能复用长连接：
    配额是热路径，连接被服务端断开后复用会一路报错）；`clock` / `sleep` 可注入，
    测试用假时钟断言窗口滚动，不真等。
    """

    def __init__(self, connection_factory: Callable[[], Any], *,
                 limit: int,
                 window_s: float = 1.0,
                 clock: Optional[Callable[[], float]] = None,
                 sleep: Optional[Callable[[float], None]] = None,
                 retention_windows: int = 60):
        limit = int(limit)
        if limit <= 0:
            # limit=0 会让每个请求都被拒；真要关停该租户应当走白名单/网关，不是配额。
            raise ValueError(f"limit 必须为正：{limit}")
        window_s = float(window_s)
        if not window_s > 0:
            # window_s=0 会让窗口号除零，也会让"下个窗口"永远不到。
            raise ValueError(f"window_s 必须为正：{window_s}")
        retention_windows = int(retention_windows)
        if retention_windows < 1:
            # 0 会把当前窗口自己删掉。
            raise ValueError(f"retention_windows 至少为 1：{retention_windows}")
        self._factory = connection_factory
        self.limit = limit
        self.window_s = window_s
        self.retention_windows = retention_windows
        self._clock = clock or time.time
        self._sleep = sleep or time.sleep
        self._lock = threading.Lock()
        self._last_prune: Dict[str, int] = {}

    # ---------- 内部 ----------
    @staticmethod
    def _check_n(n: Any) -> int:
        if isinstance(n, bool) or not isinstance(n, int):
            raise TypeError(f"n 必须是整数，收到 {type(n).__name__}")
        if n <= 0:
            raise ValueError(f"n 必须为正整数，收到 {n}")
        return n

    def _window_start(self, now: float) -> int:
        """当前窗口编号。用 `floor` 而不是 `int`：时钟为负时 `int` 会向 0 取整，
        相邻两秒会落进同一个窗口。"""
        return int(math.floor(now / self.window_s))

    def _retry_after(self, now: float, window_start: int) -> float:
        """离下一个窗口还有多久（下个窗口才有新额度）。"""
        return max(0.0, (window_start + 1) * self.window_s - now)

    def _threshold(self, window_start: int) -> int:
        """清理下界：保留当前窗口与之前 `retention_windows` 个窗口。"""
        return int(window_start - self.retention_windows * self.window_s)

    def _should_prune(self, name: str, window_start: int) -> bool:
        """同一租户同一窗口只清理一次（DELETE 不该出现在每次请求的热路径上）。

        记录按租户保存，所以必须有上限：租户名来自外部，无上限的 dict 就是内存泄漏
        （`quota.py` 里踩过同一个坑）。超上限时先丢掉已经不在当前窗口的记录，
        还超就整体清空——代价只是下一次多一条幂等 DELETE，不会算错数。
        """
        with self._lock:
            last = self._last_prune.get(name)
            if last is not None and last >= window_start:
                return False
            if len(self._last_prune) >= _MAX_TRACKED_TENANTS:
                for key in [k for k, v in self._last_prune.items() if v < window_start]:
                    del self._last_prune[key]
                if len(self._last_prune) >= _MAX_TRACKED_TENANTS:
                    self._last_prune.clear()
            self._last_prune[name] = window_start
            return True

    def _connect(self, op: str, tenant: str = "") -> Any:
        try:
            conn = self._factory()
            conn.autocommit(False)
            return conn
        except Exception as exc:  # noqa: BLE001
            raise SharedQuotaError(
                f"配额计数不可用（操作={op}，租户={tenant}）：{_brief(exc)}") from exc

    def _fail(self, op: str, tenant: str, conn: Any, exc: BaseException):
        """统一出口：回滚半截事务后抛可读错误，绝不返回值冒充"放行"。"""
        _rollback_quietly(conn)
        return SharedQuotaError(
            f"配额计数不可用（操作={op}，租户={tenant}）：{_brief(exc)}")

    def _consume(self, name: str, window_start: int, count: int, prune: bool):
        """一次事务完成"清理旧窗口 → 自增 → 读值 → 超限退回"，返回 (allowed, used)。

        全部在一个事务里：自增与判断之间不会有别的实例插进来，出错回滚也不会
        留下"只增不退"的脏计数。
        """
        conn = self._connect("take", name)
        try:
            with conn.cursor() as cur:
                if prune:
                    cur.execute(SQL_PRUNE, (name, self._threshold(window_start)))
                cur.execute(SQL_UPSERT, (name, window_start, count, count))
                cur.execute(SQL_SELECT_USED, (name, window_start))
                row = cur.fetchone()
                used = int(row[0]) if row and row[0] is not None else 0
                over = used > self.limit
                if over:
                    # 关键一步：这次自增不许留下，否则本窗口内这个租户再也放不行。
                    cur.execute(SQL_REFUND, (count, name, window_start))
                    cur.execute(SQL_SELECT_USED, (name, window_start))
                    row = cur.fetchone()
                    used = int(row[0]) if row and row[0] is not None else 0
            conn.commit()
            return (not over), used
        except Exception as exc:  # noqa: BLE001
            raise self._fail("take", name, conn, exc) from exc
        finally:
            conn.close()

    # ---------- 对外 ----------
    def ensure_schema(self) -> None:
        ensure_schema(self._factory)

    def take(self, tenant: Any, n: int = 1) -> Dict[str, Any]:
        """尝试取 `n` 个额度。**不阻塞**：不够就立刻返回 allowed=False 与建议重试秒数。

        返回 `used` 是**本次判断之后**的真实计数：被拒时它已经不含本次的 `n`
        （这就是"拒绝不占额度"的可观测形态），所以被拒时 `used <= limit`。
        """
        name = normalize_tenant(tenant)
        count = self._check_n(n)
        now = self._clock()
        window_start = self._window_start(now)
        prune = self._should_prune(name, window_start)
        allowed, used = self._consume(name, window_start, count, prune)
        return {
            "schema": SCHEMA,
            "tenant": name,
            "allowed": allowed,
            "used": used,
            "limit": self.limit,
            "window_start": window_start,
            "retry_after_s": None if allowed else round(self._retry_after(now, window_start), 3),
        }

    def wait_take(self, tenant: Any, n: int = 1,
                  timeout: Optional[float] = None) -> Dict[str, Any]:
        """最多等到下一个窗口再取一次；返回 `take` 的结果 + `waited_s`。

        `timeout` 给定时，若剩余等待超过它就直接返回拒绝，**不睡眠、不占额度**：
        等不到的事别耗着线程。`timeout=None` 表示一直等到窗口滚动。
        """
        out = self.take(tenant, n)
        if out["allowed"]:
            return {**out, "waited_s": 0.0}
        retry = float(out["retry_after_s"] or 0.0)
        if timeout is not None and retry > timeout:
            return {**out, "waited_s": 0.0}
        self._sleep(retry)
        return {**self.take(tenant, n), "waited_s": round(retry, 3)}

    def stats(self) -> Dict[str, Any]:
        """按租户导出当前窗口的 used/limit（供指标层渲染）。

        只读**计数**：不返回请求内容、不返回其它窗口的历史。旧窗口在清理前仍留在表里，
        这里按当前窗口过滤，避免把跨窗口的量加起来算重。
        """
        now = self._clock()
        window_start = self._window_start(now)
        conn = self._connect("stats")
        try:
            with conn.cursor() as cur:
                cur.execute(SQL_STATS, (window_start,))
                rows = cur.fetchall() or []
            conn.commit()
        except Exception as exc:  # noqa: BLE001
            raise self._fail("stats", "*", conn, exc) from exc
        finally:
            conn.close()
        return {
            "schema": SCHEMA,
            "window_start": window_start,
            "window_s": self.window_s,
            "limit": self.limit,
            "tenants": {str(t): {"used": int(u or 0), "limit": self.limit} for t, u in rows},
        }
